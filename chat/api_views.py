import uuid

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from users.api_views import CsrfExemptSessionAuthentication

from .models import ChatRoom, Message, Server
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

    content_type = file.content_type or ""
    attachment_type = ATTACHMENT_MAP.get(content_type, "file")

    msg = Message.objects.create(
        user=request.user,
        room=room,
        text=request.data.get("text", ""),
        attachment_type=attachment_type,
        attachment_url=file,
        attachment_name=file.name,
    )

    serializer = MessageSerializer(msg)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


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
