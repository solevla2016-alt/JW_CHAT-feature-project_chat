from rest_framework import permissions, serializers
from rest_framework.request import Request

from .models import ChatRoom, Message, Reaction, ReadStatus


class MessageSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    avatar = serializers.SerializerMethodField()
    reply_to = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ("id", "username", "avatar", "text", "reply_to", "is_edited", "created_at", "updated_at", "reactions", "attachment_type", "attachment_url", "attachment_name", "duration", "pinned", "transcription")

    def get_avatar(self, obj: Message) -> str | None:
        if obj.user.avatar:
            return obj.user.avatar.url
        return None

    def get_reply_to(self, obj: Message) -> dict | None:
        if not obj.reply_to:
            return None
        return {
            "id": obj.reply_to.id,
            "username": obj.reply_to.user.username,
            "text": obj.reply_to.text[:100],
        }

    def get_reactions(self, obj: Message) -> list[dict]:
        return [
            {
                "emoji": r.emoji,
                "username": r.user.username,
            }
            for r in obj.reactions.select_related("user")
        ]


class ChatRoomSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source="owner.username", read_only=True)
    member_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ("id", "name", "description", "avatar", "is_private", "owner", "member_count", "last_message", "unread_count", "created_at")

    def get_member_count(self, obj: ChatRoom) -> int:
        return obj.members.count() + 1

    def get_unread_count(self, obj: ChatRoom) -> int:
        user = self.context.get("request").user
        if not user or user.is_anonymous:
            return 0
        read_ids = (
            ReadStatus.objects
            .filter(user=user, message__room=obj)
            .values_list("message_id", flat=True)
        )
        last_read = obj.messages.filter(id__in=read_ids).order_by("-id").values_list("id", flat=True).first()
        if not last_read:
            return obj.messages.exclude(user=user).count()
        return obj.messages.filter(id__gt=last_read).exclude(user=user).count()

    def get_last_message(self, obj: ChatRoom) -> dict | None:
        last = obj.messages.select_related("user").order_by("-created_at").first()
        if not last:
            return None
        return {
            "text": last.text[:100],
            "username": last.user.username,
            "created_at": last.created_at.isoformat(),
        }


class ChatRoomCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatRoom
        fields = ("name", "description", "is_private")

    def create(self, validated_data: dict) -> ChatRoom:
        room = ChatRoom.objects.create(
            owner=self.context["request"].user,
            **validated_data,
        )
        room.members.add(self.context["request"].user)
        return room
