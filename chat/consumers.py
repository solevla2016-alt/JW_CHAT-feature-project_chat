import json
import os
from typing import Any

import redis.asyncio as aioredis
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from django.conf import settings
from django.contrib.auth import get_user_model

from .ai_service import build_history, get_ai_answer
from .models import ChatRoom, Message, Reaction, ReadStatus
from .validators import validate_message

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer для чата JOIN WORK!."""

    redis_pool: aioredis.Redis | None = None

    @classmethod
    async def _get_redis(cls) -> aioredis.Redis:
        if cls.redis_pool is None:
            cls.redis_pool = aioredis.from_url(
                f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', '6379')}",
                decode_responses=True,
            )
        return cls.redis_pool

    @property
    def presence_key(self) -> str:
        return f"presence:chat_{self.room.id}"

    @property
    def user_key(self) -> str:
        return f"presence:user_{self.scope['user'].id}"

    async def connect(self) -> None:
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return

        self.room_name: str = self.scope["url_route"]["kwargs"]["room_name"]
        self.room = await self._get_room(self.room_name)

        if self.room is None:
            await self.close()
            return

        if not await self._has_access(user):
            await self.close()
            return

        self.room_group_name = f"chat_{self.room.id}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        redis = await self._get_redis()
        await redis.sadd(self.presence_key, self.channel_name)
        await redis.sadd(self.user_key, self.channel_name)
        await redis.set(f"presence:chan:{self.channel_name}", user.username)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "user_status",
                "action": "join",
                "username": user.username,
                "channel_name": self.channel_name,
            },
        )

        await self._broadcast_online_users()
        await self._send_history()

    async def disconnect(self, close_code: int) -> None:
        if not hasattr(self, "room_group_name"):
            return

        user = self.scope["user"]
        if not user.is_anonymous:
            redis = await self._get_redis()
            await redis.srem(self.presence_key, self.channel_name)
            await redis.srem(self.user_key, self.channel_name)
            await redis.delete(f"presence:chan:{self.channel_name}")

            still_online = await redis.scard(self.user_key)

            if still_online == 0:
                await self._mark_offline(user.id)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "user_status",
                        "action": "leave",
                        "username": user.username,
                        "channel_name": self.channel_name,
                    },
                )

            await self._broadcast_online_users()

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if text_data is None:
            return

        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._send_error("Некорректный JSON")
            return

        action = data.get("action", "message")

        if action == "message":
            await self._handle_message(data)
        elif action == "typing":
            await self._handle_typing(data)
        elif action == "edit":
            await self._handle_edit(data)
        elif action == "read":
            await self._handle_read(data)
        elif action == "reaction":
            await self._handle_reaction(data)
        elif action == "ai_request":
            await self._handle_ai_request(data)
        elif action == "pin":
            await self._handle_pin(data)

    async def _handle_message(self, data: dict[str, Any]) -> None:
        message_text, error = validate_message(json.dumps(data))
        if error:
            await self._send_error(error)
            return

        user = self.scope["user"]
        reply_to_id = data.get("reply_to_id")

        if not await self._can_dm(user, self.room):
            return

        if reply_to_id:
            reply_valid = await self._validate_reply(reply_to_id)
            if not reply_valid:
                await self._send_error("Сообщение для ответа не найдено")
                return

        attachment_type = data.get("attachment_type", "none")
        attachment_url = data.get("attachment_url")
        attachment_name = data.get("attachment_name", "")
        duration = data.get("duration")

        message = await self._create_message(
            user_id=user.id,
            room_id=self.room.id,
            text=message_text,
            reply_to_id=reply_to_id,
            attachment_type=attachment_type,
            attachment_url=attachment_url,
            attachment_name=attachment_name,
            duration=duration,
        )

        reply_data = None
        if message.reply_to:
            reply_data = await self._serialize_message(message.reply_to)

        avatar_url = user.avatar.url if user.avatar else None

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "id": message.id,
                "username": user.username,
                "avatar": avatar_url,
                "message": message.text,
                "created_at": message.created_at.isoformat(),
                "is_edited": False,
                "reply_to": reply_data,
                "sender_channel": self.channel_name,
                "attachment_type": message.attachment_type,
                "attachment_url": message.attachment_url.url if message.attachment_url else None,
                "attachment_name": message.attachment_name,
                "duration": message.duration,
                "transcription": message.transcription,
            },
        )

    async def _handle_typing(self, data: dict[str, Any]) -> None:
        user = self.scope["user"]
        is_typing = data.get("is_typing", False)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "typing_indicator",
                "username": user.username,
                "is_typing": is_typing,
                "channel_name": self.channel_name,
            },
        )

    async def _handle_edit(self, data: dict[str, Any]) -> None:
        message_id = data.get("message_id")
        new_text = data.get("text", "").strip()

        if not message_id or not new_text:
            await self._send_error("message_id и text обязательны")
            return

        user = self.scope["user"]
        success = await self._edit_message(message_id, user.id, new_text)

        if not success:
            await self._send_error("Не удалось отредактировать сообщение")
            return

        message = await self._get_message_by_id(message_id)

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "message_edited",
                "id": message.id,
                "message": message.text,
                "updated_at": message.updated_at.isoformat(),
            },
        )

    async def _handle_read(self, data: dict[str, Any]) -> None:
        user = self.scope["user"]
        last_id = data.get("last_message_id")
        await self._mark_read(user.id, last_id)

    async def _handle_reaction(self, data: dict[str, Any]) -> None:
        message_id = data.get("message_id")
        emoji = data.get("emoji", "").strip()

        if not message_id or not emoji:
            await self._send_error("message_id и emoji обязательны")
            return

        user = self.scope["user"]
        toggled = await self._toggle_reaction(message_id, user.id, emoji)

        if toggled is None:
            await self._send_error("Сообщение не найдено")
            return

        message = await self._get_message_by_id(message_id)
        if message is None:
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "message_reaction",
                "id": message.id,
                "reactions": await self._get_reactions(message_id),
            },
        )

    async def _handle_ai_request(self, data: dict[str, Any]) -> None:
        prompt = (data.get("prompt") or "").strip()
        if not prompt:
            await self._send_error("Укажите вопрос для AI")
            return

        # Показываем индикатор "AI печатает"
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "ai_typing", "is_typing": True},
        )

        try:
            history_msgs = await self._get_recent_messages(self.room.id, settings.AI_CONTEXT_MESSAGES)
            history = build_history(history_msgs)
            answer = await get_ai_answer(prompt, history)
        finally:
            await self.channel_layer.group_send(
                self.room_group_name,
                {"type": "ai_typing", "is_typing": False},
            )

        ai_user = await self._get_ai_user()
        message = await self._create_message(
            user_id=ai_user.id,
            room_id=self.room.id,
            text=answer,
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "ai_response",
                "id": message.id,
                "username": ai_user.username,
                "avatar": ai_user.avatar.url if ai_user.avatar else None,
                "message": message.text,
                "created_at": message.created_at.isoformat(),
                "is_edited": False,
                "reply_to": None,
                "sender_channel": self.channel_name,
                "attachment_type": "none",
                "attachment_url": None,
                "attachment_name": "",
                "duration": None,
            },
        )

    async def _handle_pin(self, data: dict[str, Any]) -> None:
        message_id = data.get("message_id")
        if not message_id:
            await self._send_error("message_id обязателен")
            return

        user = self.scope["user"]
        pinned = await self._toggle_pin(message_id, user.id)
        if pinned is None:
            await self._send_error("Сообщение не найдено")
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "message_pinned",
                "id": message_id,
                "pinned": pinned,
                "pinned_by": user.username,
            },
        )

    # --- Group message handlers ---

    async def chat_message(self, event: dict[str, Any]) -> None:
        reply_to = event.get("reply_to")
        await self.send(text_data=json.dumps({
            "type": "message",
            "id": event["id"],
            "username": event["username"],
            "avatar": event.get("avatar"),
            "message": event["message"],
            "created_at": event["created_at"],
            "is_edited": event.get("is_edited", False),
            "reply_to": reply_to,
            "is_own": event.get("sender_channel") == self.channel_name,
            "attachment_type": event.get("attachment_type", "none"),
            "attachment_url": event.get("attachment_url"),
            "attachment_name": event.get("attachment_name", ""),
            "duration": event.get("duration"),
            "transcription": event.get("transcription", ""),
        }))

    async def typing_indicator(self, event: dict[str, Any]) -> None:
        if event.get("channel_name") == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            "type": "typing",
            "username": event["username"],
            "is_typing": event["is_typing"],
        }))

    async def user_status(self, event: dict[str, Any]) -> None:
        if event.get("channel_name") == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            "type": "user_status",
            "action": event["action"],
            "username": event["username"],
        }))

    async def online_users(self, event: dict[str, Any]) -> None:
        await self.send(text_data=json.dumps({
            "type": "online_users",
            "users": event["users"],
        }))

    async def message_edited(self, event: dict[str, Any]) -> None:
        await self.send(text_data=json.dumps({
            "type": "message_edited",
            "id": event["id"],
            "message": event["message"],
            "updated_at": event["updated_at"],
        }))

    async def message_reaction(self, event: dict[str, Any]) -> None:
        await self.send(text_data=json.dumps({
            "type": "reaction",
            "id": event["id"],
            "reactions": event["reactions"],
        }))

    async def ai_typing(self, event: dict[str, Any]) -> None:
        await self.send(text_data=json.dumps({
            "type": "ai_typing",
            "is_typing": event.get("is_typing", False),
        }))

    async def ai_response(self, event: dict[str, Any]) -> None:
        await self.send(text_data=json.dumps({
            "type": "message",
            "id": event["id"],
            "username": event["username"],
            "avatar": event.get("avatar"),
            "message": event["message"],
            "created_at": event["created_at"],
            "is_edited": event.get("is_edited", False),
            "reply_to": event.get("reply_to"),
            "is_own": event.get("sender_channel") == self.channel_name,
            "is_ai": True,
            "attachment_type": event.get("attachment_type", "none"),
            "attachment_url": event.get("attachment_url"),
            "attachment_name": event.get("attachment_name", ""),
            "duration": event.get("duration"),
            "transcription": event.get("transcription", ""),
        }))

    async def message_pinned(self, event: dict[str, Any]) -> None:
        await self.send(text_data=json.dumps({
            "type": "pinned",
            "id": event["id"],
            "pinned": event["pinned"],
            "pinned_by": event.get("pinned_by"),
        }))

    # --- Helpers ---

    async def _send_history(self) -> None:
        messages = await self._get_messages(self.room.id)
        await self.send(text_data=json.dumps({
            "type": "history",
            "messages": messages,
        }))

    async def _send_error(self, message: str) -> None:
        await self.send(text_data=json.dumps({
            "type": "error",
            "message": message,
        }))

    @database_sync_to_async
    def _get_room(self, room_name: str) -> ChatRoom | None:
        try:
            return ChatRoom.objects.get(name=room_name)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def _get_ai_user(self):
        username = settings.AI_ASSISTANT_USERNAME
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "email": "ai@joinwork.local",
                "status": "AI",
            },
        )
        return user

    @database_sync_to_async
    def _get_recent_messages(self, room_id: int, limit: int) -> list[dict[str, Any]]:
        messages = (
            Message.objects
            .filter(room_id=room_id)
            .select_related("user")
            .order_by("-created_at")[:limit]
        )
        messages = list(reversed(messages))
        return [
            {
                "message": m.text,
                "username": m.user.username,
                "is_ai": m.user.username == settings.AI_ASSISTANT_USERNAME,
            }
            for m in messages
        ]

    @database_sync_to_async
    def _has_access(self, user) -> bool:
        if self.room.owner_id == user.id:
            return True
        if not self.room.is_private:
            return True
        return self.room.members.filter(id=user.id).exists()

    @database_sync_to_async
    def _create_message(
        self,
        user_id: int,
        room_id: int,
        text: str,
        reply_to_id: int | None = None,
        attachment_type: str = "none",
        attachment_url: str | None = None,
        attachment_name: str = "",
        duration: int | None = None,
    ) -> Message:
        return Message.objects.create(
            user_id=user_id,
            room_id=room_id,
            text=text,
            reply_to_id=reply_to_id,
            attachment_type=attachment_type,
            attachment_url=attachment_url,
            attachment_name=attachment_name,
            duration=duration,
        )

    @database_sync_to_async
    def _get_messages(self, room_id: int) -> list[dict]:
        messages = (
            Message.objects
            .filter(room_id=room_id)
            .select_related("user", "reply_to", "reply_to__user")
            .order_by("-created_at")[:50]
        )
        messages = list(reversed(messages))
        return [self._serialize_message_sync(m) for m in messages]

    @database_sync_to_async
    def _serialize_message(self, message: Message) -> dict:
        return self._serialize_message_sync(message)

    def _serialize_message_sync(self, message: Message) -> dict:
        reply_data = None
        if message.reply_to:
            reply_data = {
                "id": message.reply_to.id,
                "username": message.reply_to.user.username,
                "text": message.reply_to.text[:100],
            }
        return {
            "id": message.id,
            "username": message.user.username,
            "avatar": message.user.avatar.url if message.user.avatar else None,
            "message": message.text,
            "created_at": message.created_at.isoformat(),
            "is_edited": message.is_edited,
            "reply_to": reply_data,
            "reactions": self._get_reactions_sync(message.id),
            "attachment_type": message.attachment_type,
            "attachment_url": message.attachment_url.url if message.attachment_url else None,
            "attachment_name": message.attachment_name,
            "duration": message.duration,
            "is_ai": message.user.username == settings.AI_ASSISTANT_USERNAME,
            "pinned": message.pinned,
            "transcription": message.transcription,
        }

    @staticmethod
    def _get_reactions_sync(message_id: int) -> list[dict]:
        return [
            {
                "emoji": r.emoji,
                "username": r.user.username,
            }
            for r in Reaction.objects.filter(message_id=message_id).select_related("user")
        ]

    @database_sync_to_async
    def _can_dm(self, user, room: ChatRoom) -> bool:
        if room.room_type != "direct":
            return True
        for other in room.members.exclude(id=user.pk):
            if other.username == settings.AI_ASSISTANT_USERNAME:
                continue
            if other.message_privacy == User.MessagePrivacy.NOBODY:
                return False
        return True

    def _validate_reply(self, reply_to_id: int) -> bool:
        return Message.objects.filter(id=reply_to_id, room_id=self.room.id).exists()

    @database_sync_to_async
    def _edit_message(self, message_id: int, user_id: int, new_text: str) -> bool:
        updated = (
            Message.objects
            .filter(id=message_id, user_id=user_id, room_id=self.room.id)
            .update(text=new_text, is_edited=True)
        )
        return updated > 0

    @database_sync_to_async
    def _get_message_by_id(self, message_id: int) -> Message | None:
        try:
            return Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return None

    @database_sync_to_async
    def _toggle_reaction(self, message_id: int, user_id: int, emoji: str) -> bool | None:
        message = Message.objects.filter(id=message_id, room_id=self.room.id).first()
        if message is None:
            return None

        reaction = Reaction.objects.filter(
            message_id=message_id,
            user_id=user_id,
            emoji=emoji,
        ).first()

        if reaction is not None:
            reaction.delete()
        else:
            Reaction.objects.get_or_create(
                message_id=message_id,
                user_id=user_id,
                emoji=emoji,
            )
        return True

    @database_sync_to_async
    def _toggle_pin(self, message_id: int, user_id: int) -> bool | None:
        message = Message.objects.filter(id=message_id, room_id=self.room.id).first()
        if message is None:
            return None
        if message.user_id != user_id:
            return None
        message.pinned = not message.pinned
        from django.utils import timezone
        message.pinned_at = timezone.now() if message.pinned else None
        message.save(update_fields=["pinned", "pinned_at"])
        return message.pinned

    @database_sync_to_async
    def _get_reactions(self, message_id: int) -> list[dict]:
        return [
            {
                "emoji": r.emoji,
                "username": r.user.username,
            }
            for r in Reaction.objects.filter(message_id=message_id).select_related("user")
        ]

    @database_sync_to_async
    def _mark_read(self, user_id: int, last_id: int | None) -> None:
        qs = Message.objects.filter(room_id=self.room.id).exclude(user_id=user_id)
        if last_id:
            qs = qs.filter(id__lte=last_id)
        for m in qs.only("id")[:200]:
            ReadStatus.objects.get_or_create(message_id=m.id, user_id=user_id)

    async def _broadcast_online_users(self) -> None:
        redis = await self._get_redis()
        channel_names = await redis.smembers(self.presence_key)
        usernames: list[str] = []
        for channel in channel_names:
            username = await redis.get(f"presence:chan:{channel}")
            if username:
                usernames.append(username)
        await self.channel_layer.group_send(
            self.room_group_name,
            {"type": "online_users", "users": sorted(set(usernames))},
        )

    @database_sync_to_async
    def _mark_offline(self, user_id: int) -> None:
        from users.models import User

        User.objects.filter(id=user_id).update(status="")

