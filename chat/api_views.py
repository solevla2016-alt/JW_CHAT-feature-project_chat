import os
import uuid

from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.db.models import Exists, F, OuterRef, Q
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.request import Request
from rest_framework.response import Response

from users.api_views import CsrfExemptSessionAuthentication

from .models import ChatRoom, Message, RoomBan, Server
from .permissions import (
    ban_user,
    can_ban,
    can_delete_message,
    is_admin,
    is_banned,
    unban_user,
)
from .serializers import (
    ChatRoomCreateSerializer,
    ChatRoomSerializer,
    MessageSerializer,
    ServerCreateSerializer,
    ServerSerializer,
)

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"}
AUDIO_TYPES = {"audio/mpeg", "audio/ogg", "audio/wav", "audio/webm", "audio/mp4", "audio/aac"}
VIDEO_TYPES = {"video/mp4", "video/webm", "video/ogg", "video/quicktime"}

ATTACHMENT_MAP = {
    **{t: "image" for t in IMAGE_TYPES},
    **{t: "audio" for t in AUDIO_TYPES},
    **{t: "video" for t in VIDEO_TYPES},
}


@api_view(["GET"])
def rooms_list_view(request: Request) -> Response:
    rooms = (
        ChatRoom.objects
        .filter(Q(is_private=False) | Q(members=request.user) | Q(owner=request.user))
        .distinct()
        .select_related("owner", "server")
        .prefetch_related("members", "messages")
        .annotate(has_messages=Exists(Message.objects.filter(room=OuterRef("pk"))))
        .order_by(
            F("has_messages").desc(),
            F("created_at").desc(),
        )
    )
    serializer = ChatRoomSerializer(rooms, many=True, context={"request": request})
    return Response(serializer.data)


@api_view(["GET"])
def servers_list_view(request: Request) -> Response:
    servers = (
        Server.objects
        .filter(Q(members=request.user) | Q(owner=request.user))
        .distinct()
        .select_related("owner")
        .prefetch_related("members")
    )
    serializer = ServerSerializer(servers, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def server_invite_view(request: Request, server_id: int) -> Response:
    try:
        server = Server.objects.get(id=server_id)
    except Server.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if server.owner_id != request.user.id and not server.members.filter(id=request.user.id).exists():
        return Response({"error": "Нет доступа"}, status=status.HTTP_403_FORBIDDEN)

    if server.invite_token is None:
        server.invite_token = uuid.uuid4()
        server.save(update_fields=["invite_token"])

    return Response({"token": str(server.invite_token)})


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
def server_join_view(request: Request, token: str) -> Response:
    try:
        server = Server.objects.get(invite_token=token)
    except (Server.DoesNotExist, ValueError, TypeError, ValidationError):
        return Response({"error": "Приглашение недействительно"}, status=status.HTTP_404_NOT_FOUND)

    server.members.add(request.user)
    return Response(ServerSerializer(server).data)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
def server_create_view(request: Request) -> Response:
    serializer = ServerCreateSerializer(data=request.data, context={"request": request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    server = serializer.save()
    return Response(ServerSerializer(server).data, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
def room_create_view(request: Request) -> Response:
    serializer = ChatRoomCreateSerializer(data=request.data, context={"request": request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    room = serializer.save()
    return Response(ChatRoomSerializer(room, context={"request": request}).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def room_messages_view(request: Request, room_id: int) -> Response:
    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    messages = (
        Message.objects
        .filter(room=room)
        .select_related("user", "reply_to", "reply_to__user")
        .order_by("-created_at")[:100]
    )
    messages = list(reversed(messages))
    serializer = MessageSerializer(messages, many=True)
    return Response(serializer.data)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
def room_join_view(request: Request, room_id: int) -> Response:
    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if room.is_private:
        return Response({"error": "Приватная комната"}, status=status.HTTP_403_FORBIDDEN)

    room.members.add(request.user)
    return Response({"success": True})


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
def room_leave_view(request: Request, room_id: int) -> Response:
    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if room.owner_id == request.user.id:
        return Response({"error": "Владелец не может покинуть комнату"}, status=status.HTTP_400_BAD_REQUEST)

    room.members.remove(request.user)
    return Response({"success": True})


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
def room_add_member_view(request: Request, room_id: int) -> Response:
    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if room.owner_id != request.user.id:
        return Response({"error": "Только владелец добавляет участников"}, status=status.HTTP_403_FORBIDDEN)

    user_id = request.data.get("user_id")
    if not user_id:
        return Response({"error": "user_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

    from users.models import User
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

    room.members.add(user)

    if room.server_id and not room.server.members.filter(id=user.id).exists():
        room.server.members.add(user)

    _notify_room_added(user, room)
    return Response({"success": True})


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def room_upload_view(request: Request, room_id: int) -> Response:
    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if not (room.owner_id == request.user.id or room.members.filter(id=request.user.id).exists()):
        return Response({"error": "Нет доступа к комнате"}, status=status.HTTP_403_FORBIDDEN)

    file = request.FILES.get("file")
    if not file:
        return Response({"error": "Файл не прикреплён"}, status=status.HTTP_400_BAD_REQUEST)

    from django.conf import settings as djsettings

    if file.size > getattr(djsettings, "FILE_UPLOAD_MAX_SIZE", 100 * 1024 * 1024):
        return Response({"error": "Файл слишком большой"}, status=status.HTTP_400_BAD_REQUEST)

    content_type = file.content_type or ""
    attachment_type = ATTACHMENT_MAP.get(content_type, "file")

    ext = os.path.splitext(file.name)[1].lower()
    path = f"uploads/{uuid.uuid4().hex}{ext}"
    if hasattr(default_storage, "path"):
        os.makedirs(os.path.dirname(default_storage.path(path)), exist_ok=True)
    with default_storage.open(path, "wb") as dst:
        for chunk in file.chunks():
            dst.write(chunk)

    return Response(
        {
            "attachment_url": path,
            "attachment_name": file.name,
            "attachment_type": attachment_type,
            "duration": None,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def room_search_view(request: Request, room_id: int) -> Response:
    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    query = request.query_params.get("q", "").strip()
    if not query:
        return Response(status=status.HTTP_400_BAD_REQUEST)

    messages = (
        Message.objects
        .filter(room=room, text__icontains=query)
        .select_related("user", "reply_to", "reply_to__user")
        .order_by("-created_at")[:50]
    )
    messages = list(reversed(messages))
    serializer = MessageSerializer(messages, many=True)
    return Response(serializer.data)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def room_transcribe_view(request: Request, room_id: int) -> Response:
    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    message_id = request.data.get("message_id")
    if not message_id:
        return Response({"error": "message_id обязателен"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        message = Message.objects.get(id=message_id, room=room)
    except Message.DoesNotExist:
        return Response({"error": "Сообщение не найдено"}, status=status.HTTP_404_NOT_FOUND)

    if not message.attachment_url or message.attachment_type != "audio":
        return Response({"error": "Сообщение не содержит аудио"}, status=status.HTTP_400_BAD_REQUEST)

    from .speech_service import transcribe_audio

    message.attachment_url.open("rb")
    text = transcribe_audio(message.attachment_url)
    message.attachment_url.close()

    message.transcription = text
    message.save(update_fields=["transcription"])

    return Response({"transcription": text}, status=status.HTTP_200_OK)


def _room_for_user(request: Request, room_id: int) -> tuple[ChatRoom | None, Response | None]:
    try:
        room = ChatRoom.objects.get(id=room_id)
    except ChatRoom.DoesNotExist:
        return None, Response(status=status.HTTP_404_NOT_FOUND)
    if is_admin(request.user):
        return room, None
    if room.owner_id != request.user.id and not room.members.filter(id=request.user.id).exists():
        return None, Response({"error": "Нет доступа к комнате"}, status=status.HTTP_403_FORBIDDEN)
    return room, None


@api_view(["DELETE"])
def room_message_delete_view(request: Request, room_id: int, message_id: int) -> Response:
    room, error = _room_for_user(request, room_id)
    if error is not None:
        return error

    try:
        message = Message.objects.get(id=message_id, room=room)
    except Message.DoesNotExist:
        return Response({"error": "Сообщение не найдено"}, status=status.HTTP_404_NOT_FOUND)

    if not can_delete_message(request.user, message):
        return Response({"error": "Недостаточно прав"}, status=status.HTTP_403_FORBIDDEN)

    message.delete()
    _broadcast_message_deleted(room, message_id)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
def room_ban_view(request: Request, room_id: int) -> Response:
    room, error = _room_for_user(request, room_id)
    if error is not None:
        return error

    from users.models import User

    if request.method == "GET":
        bans = RoomBan.objects.filter(room=room).select_related("user", "banned_by")
        return Response(
            [
                {
                    "username": b.user.username,
                    "user_id": b.user.id,
                    "banned_by": b.banned_by.username,
                    "reason": b.reason,
                    "created_at": b.created_at.isoformat(),
                    "expires_at": b.expires_at.isoformat() if b.expires_at else None,
                    "is_active": b.is_active,
                }
                for b in bans
            ]
        )

    username = (request.data.get("username") or "").strip()
    if not username:
        return Response({"error": "username обязателен"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        target = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

    if not can_ban(request.user, room, target):
        return Response({"error": "Недостаточно прав"}, status=status.HTTP_403_FORBIDDEN)

    reason = (request.data.get("reason") or "").strip()[:300]
    expires_at = request.data.get("expires_at")
    if expires_at:
        from django.utils.dateparse import parse_datetime
        parsed = parse_datetime(str(expires_at))
        if parsed is None:
            return Response({"error": "Некорректный expires_at"}, status=status.HTTP_400_BAD_REQUEST)
        expires_at = parsed

    ban = ban_user(room, target, request.user, reason=reason, expires_at=expires_at)
    return Response(
        {
            "username": target.username,
            "banned_by": request.user.username,
            "reason": ban.reason,
            "created_at": ban.created_at.isoformat(),
            "expires_at": ban.expires_at.isoformat() if ban.expires_at else None,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["DELETE"])
def room_unban_view(request: Request, room_id: int, user_id: int) -> Response:
    room, error = _room_for_user(request, room_id)
    if error is not None:
        return error

    from users.models import User

    try:
        target = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

    if not can_ban(request.user, room, target):
        return Response({"error": "Недостаточно прав"}, status=status.HTTP_403_FORBIDDEN)

    if not is_banned(room, target):
        return Response({"error": "Пользователь не забанен"}, status=status.HTTP_400_BAD_REQUEST)

    unban_user(room, target)
    return Response({"success": True})


def _broadcast_message_deleted(room: ChatRoom, message_id: int) -> None:
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)(
            f"chat_{room.id}",
            {
                "type": "message_deleted",
                "id": message_id,
            },
        )


def _notify_room_added(user, room: ChatRoom) -> None:
    """Шлёт online-клиентам пользователя событие о подключении к комнате/серверу."""
    import os

    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    try:
        import redis as sync_redis

        r = sync_redis.from_url(
            f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6379')}",
            decode_responses=True,
        )
        channels = list(r.smembers(f"presence:user_{user.id}"))
    except Exception:
        return

    for channel in channels:
        try:
            async_to_sync(channel_layer.send)(
                channel,
                {
                    "type": "room_added",
                    "room_id": room.id,
                    "room_name": room.name,
                    "room_type": room.room_type,
                    "server_id": room.server_id,
                    "server_name": room.server.name if room.server_id else None,
                },
            )
        except Exception:  # noqa: S110 — одиночный канал не должен ломать рассылку
            pass
