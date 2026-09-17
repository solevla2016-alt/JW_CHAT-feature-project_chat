from __future__ import annotations

import asyncio
import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status

from chat import permissions
from chat.ai_service import ask_openrouter, build_history, get_ai_answer
from chat.consumers import ChatConsumer
from chat.models import ChatRoom, Message, Reaction, RoomBan, Server
from chat.serializers import ChatRoomSerializer, MessageSerializer
from chat.validators import validate_message

User = get_user_model()


def _msg(room, user, text="hello") -> Message:
    return Message.objects.create(room=room, user=user, text=text)


@pytest.mark.django_db()
class TestPermissionsUnit:
    def test_author_deletes_own(self, group_room, owner_message, owner):
        assert permissions.can_delete_message(owner, owner_message)

    def test_member_cannot_delete_other(self, group_room, owner_message, member):
        assert not permissions.can_delete_message(member, owner_message)

    def test_moderator_can_delete_in_room(self, group_room, member_message, moderator):
        assert permissions.can_moderate(moderator, group_room)
        assert permissions.can_delete_message(moderator, member_message)

    def test_moderator_cannot_delete_room_owner(self, group_room, owner_message, moderator):
        assert not permissions.can_delete_message(moderator, owner_message)

    def test_moderator_cannot_delete_admin_author(self, group_room, admin, moderator):
        admin_msg = _msg(group_room, admin, "admin said")
        assert not permissions.can_delete_message(moderator, admin_msg)

    def test_owner_can_delete_member(self, group_room, member_message, owner):
        assert permissions.can_delete_message(owner, member_message)

    def test_admin_can_delete_any(self, group_room, owner_message, admin):
        assert permissions.can_delete_message(admin, owner_message)

    def test_stranger_no_access(self, group_room, owner_message, stranger):
        assert not permissions.can_delete_message(stranger, owner_message)

    def test_server_owner_can_delete_in_room(self, member, owner, stranger):
        server = Server.objects.create(name="srv", owner=owner, description="")
        room = ChatRoom.objects.create(name="srv-room", owner=member, room_type="group", server=server)
        room.members.add(owner, member, stranger)
        plain = _msg(room, stranger, "plain")
        assert permissions.can_delete_message(owner, plain)
        room_owner_msg = _msg(room, member, "room owner msg")
        assert not permissions.can_delete_message(owner, room_owner_msg)

    def test_can_ban_member_by_moderator(self, group_room, moderator, member):
        assert permissions.can_ban(moderator, group_room, member)

    def test_cannot_ban_self(self, group_room, moderator):
        assert not permissions.can_ban(moderator, group_room, moderator)

    def test_cannot_ban_admin(self, group_room, admin, moderator):
        assert not permissions.can_ban(moderator, group_room, admin)

    def test_cannot_ban_room_owner(self, group_room, owner, moderator):
        assert not permissions.can_ban(moderator, group_room, owner)

    def test_ban_lifecycle(self, group_room, owner, member):
        ban = permissions.ban_user(group_room, member, owner, reason="spam")
        assert ban.is_active
        assert permissions.is_banned(group_room, member)
        assert member not in group_room.members.all()
        permissions.unban_user(group_room, member)
        assert not permissions.is_banned(group_room, member)

    def test_expired_ban_inactive(self, group_room, owner, member):
        ban = RoomBan.objects.create(
            room=group_room,
            user=member,
            banned_by=owner,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        assert not ban.is_active
        assert not permissions.is_banned(group_room, member)


@pytest.mark.django_db()
class TestValidator:
    def test_valid(self):
        msg, err = validate_message(json.dumps({"message": "hi"}))
        assert msg == "hi"
        assert err is None

    def test_empty_message(self):
        _, err = validate_message(json.dumps({"message": "  "}))
        assert err is not None

    def test_too_long(self):
        _, err = validate_message(json.dumps({"message": "x" * 2001}))
        assert err is not None

    def test_bad_json(self):
        _, err = validate_message("not json")
        assert err is not None

    def test_not_dict(self):
        _, err = validate_message(json.dumps(["list"]))
        assert err is not None

    def test_missing_message_field(self):
        _, err = validate_message(json.dumps({"text": "hi"}))
        assert err is not None


@pytest.mark.django_db()
class TestMessageDeleteApi:
    def test_delete_own(self, api_client, group_room, owner, owner_message):
        api_client.force_authenticate(user=owner)
        resp = api_client.delete(f"/api/chat/rooms/{group_room.id}/messages/{owner_message.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        assert not Message.objects.filter(id=owner_message.id).exists()

    def test_delete_other_denied(self, api_client, group_room, owner, member, owner_message):
        api_client.force_authenticate(user=member)
        resp = api_client.delete(f"/api/chat/rooms/{group_room.id}/messages/{owner_message.id}/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_moderator_can_delete(self, api_client, group_room, moderator, member_message):
        api_client.force_authenticate(user=moderator)
        resp = api_client.delete(f"/api/chat/rooms/{group_room.id}/messages/{member_message.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_owner_can_delete_other(self, api_client, group_room, owner, member_message):
        api_client.force_authenticate(user=owner)
        resp = api_client.delete(f"/api/chat/rooms/{group_room.id}/messages/{member_message.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_admin_can_delete_any(self, api_client, group_room, admin, owner_message):
        api_client.force_authenticate(user=admin)
        resp = api_client.delete(f"/api/chat/rooms/{group_room.id}/messages/{owner_message.id}/")
        assert resp.status_code == status.HTTP_204_NO_CONTENT

    def test_moderator_cannot_delete_owner(self, api_client, group_room, moderator, owner_message):
        api_client.force_authenticate(user=moderator)
        resp = api_client.delete(f"/api/chat/rooms/{group_room.id}/messages/{owner_message.id}/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_not_found(self, api_client, group_room, owner):
        api_client.force_authenticate(user=owner)
        resp = api_client.delete(f"/api/chat/rooms/{group_room.id}/messages/99999/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_room_not_found(self, api_client, owner):
        api_client.force_authenticate(user=owner)
        resp = api_client.delete("/api/chat/rooms/99999/messages/1/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_stranger_cannot_delete(self, api_client, group_room, stranger, owner_message):
        api_client.force_authenticate(user=stranger)
        resp = api_client.delete(f"/api/chat/rooms/{group_room.id}/messages/{owner_message.id}/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db()
class TestBanApi:
    def test_owner_bans_member(self, api_client, group_room, owner, member):
        api_client.force_authenticate(user=owner)
        resp = api_client.post(
            f"/api/chat/rooms/{group_room.id}/bans/",
            {"username": member.username, "reason": "bad"},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data["username"] == member.username
        assert permissions.is_banned(group_room, member)
        assert member not in group_room.members.all()

    def test_moderator_bans_member(self, api_client, group_room, moderator, member):
        api_client.force_authenticate(user=moderator)
        resp = api_client.post(
            f"/api/chat/rooms/{group_room.id}/bans/",
            {"username": member.username},
            format="json",
        )
        assert resp.status_code == status.HTTP_201_CREATED

    def test_member_denied(self, api_client, group_room, member, owner):
        api_client.force_authenticate(user=member)
        resp = api_client.post(
            f"/api/chat/rooms/{group_room.id}/bans/",
            {"username": owner.username},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_ban_self(self, api_client, group_room, owner):
        api_client.force_authenticate(user=owner)
        resp = api_client.post(
            f"/api/chat/rooms/{group_room.id}/bans/",
            {"username": owner.username},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_ban_admin(self, api_client, group_room, owner, admin):
        api_client.force_authenticate(user=owner)
        resp = api_client.post(
            f"/api/chat/rooms/{group_room.id}/bans/",
            {"username": admin.username},
            format="json",
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_ban_unknown_user(self, api_client, group_room, owner):
        api_client.force_authenticate(user=owner)
        resp = api_client.post(
            f"/api/chat/rooms/{group_room.id}/bans/",
            {"username": "ghost"},
            format="json",
        )
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_ban_missing_username(self, api_client, group_room, owner):
        api_client.force_authenticate(user=owner)
        resp = api_client.post(
            f"/api/chat/rooms/{group_room.id}/bans/",
            {"reason": "spam"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_ban_invalid_expires_at(self, api_client, group_room, owner, member):
        api_client.force_authenticate(user=owner)
        resp = api_client.post(
            f"/api/chat/rooms/{group_room.id}/bans/",
            {"username": member.username, "expires_at": "not-a-date"},
            format="json",
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_unban_success(self, api_client, group_room, owner, member):
        permissions.ban_user(group_room, member, owner)
        api_client.force_authenticate(user=owner)
        resp = api_client.delete(f"/api/chat/rooms/{group_room.id}/bans/{member.id}/")
        assert resp.status_code == status.HTTP_200_OK
        assert not permissions.is_banned(group_room, member)

    def test_unban_not_banned(self, api_client, group_room, owner, member):
        api_client.force_authenticate(user=owner)
        resp = api_client.delete(f"/api/chat/rooms/{group_room.id}/bans/{member.id}/")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_bans(self, api_client, group_room, owner, member):
        permissions.ban_user(group_room, member, owner, reason="spam")
        api_client.force_authenticate(user=owner)
        resp = api_client.get(f"/api/chat/rooms/{group_room.id}/bans/")
        assert resp.status_code == status.HTTP_200_OK
        assert any(b["username"] == member.username for b in resp.data)


class TestAiService:
    async def test_build_history_shape(self):
        raw = [{"message": "q", "username": "u", "is_ai": False}]
        h = build_history(raw)
        assert h == [{"text": "q", "username": "u", "is_ai": False}]

    async def test_get_ai_help(self):
        result = await get_ai_answer("/help", [])
        assert "Python" in result

    async def test_local_fallback(self, settings):
        settings.OPENROUTER_API_KEY = ""
        result = await get_ai_answer("что такое yield", [])
        assert "Генератор" in result

    async def test_unknown_query_fallback(self, settings):
        settings.OPENROUTER_API_KEY = ""
        result = await get_ai_answer("абракадабра", [])
        assert "ментор" in result

    async def test_local_matching_prefers_specific_topic(self, settings):
        settings.OPENROUTER_API_KEY = ""
        result = await get_ai_answer("как сделать сортировку в python?", [])
        assert "сортировк" in result.lower()
        assert "декоратор" not in result.lower()

    async def test_ask_openrouter_no_key(self, settings):
        settings.OPENROUTER_API_KEY = ""
        result = await ask_openrouter("test", [])
        assert result is None

    async def test_ask_openrouter_success(self, settings):
        settings.OPENROUTER_API_KEY = "test-key"

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"choices": [{"message": {"content": "ok"}}]}

        with patch("chat.ai_service.httpx.AsyncClient") as mock_client:
            ctx = AsyncMock()
            ctx.post.return_value = fake_resp
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = ctx
            result = await ask_openrouter("test", [])
        assert result == "ok"

    async def test_ask_openrouter_no_choices(self, settings):
        settings.OPENROUTER_API_KEY = "test-key"

        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"error": {"message": "overloaded"}}
        fake_resp.text = "overloaded"

        with patch("chat.ai_service.httpx.AsyncClient") as mock_client, \
             patch("chat.ai_service.asyncio.sleep", new_callable=AsyncMock):
            ctx = AsyncMock()
            ctx.post.return_value = fake_resp
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = ctx
            result = await ask_openrouter("test", [])
        assert result is None

    async def test_ask_openrouter_http_error(self, settings):
        settings.OPENROUTER_API_KEY = "test-key"

        fake_resp = MagicMock()
        fake_resp.status_code = 429
        fake_resp.text = "rate limited"

        with patch("chat.ai_service.httpx.AsyncClient") as mock_client, \
             patch("chat.ai_service.asyncio.sleep", new_callable=AsyncMock):
            ctx = AsyncMock()
            ctx.post.return_value = fake_resp
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = ctx
            result = await ask_openrouter("test", [])
        assert result is None


async def _drain_until(communicator, expected_type, timeout=3):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise TimeoutError(f"Timed out waiting for {expected_type}")
        msg = await communicator.receive_json_from(timeout=max(remaining, 0.1))
        if msg.get("type") == expected_type:
            return msg


@pytest.mark.django_db(transaction=True)
class TestModerationWs:
    async def test_delete_own_message_broadcasts(self, group_room, owner, member, owner_message, ws_connect):
        owner_client, ok1 = await ws_connect(owner, group_room.name)
        assert ok1
        member_client, ok2 = await ws_connect(member, group_room.name)
        assert ok2
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await owner_client.send_json_to({"action": "delete", "message_id": owner_message.id})
        payload = await _drain_until(member_client, "message_deleted", timeout=3)
        assert payload["id"] == owner_message.id
        await owner_client.disconnect()
        await member_client.disconnect()

    async def test_member_cannot_delete_other(self, group_room, owner, member, owner_message, ws_connect):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await member_client.send_json_to({"action": "delete", "message_id": owner_message.id})
        await _drain_until(member_client, "error", timeout=3)
        exists = await sync_to_async(Message.objects.filter(id=owner_message.id).exists)()
        assert exists
        await owner_client.disconnect()
        await member_client.disconnect()

    async def test_banned_cannot_connect(self, group_room, owner, member, ws_connect):
        await sync_to_async(permissions.ban_user)(group_room, member, owner)
        client, ok = await ws_connect(member, group_room.name)
        assert not ok

    async def test_banned_sends_error(self, group_room, owner, member, ws_connect):
        client, _ = await ws_connect(owner, group_room.name)
        await _drain_until(client, "history")
        member_client, _ = await ws_connect(member, group_room.name)
        await _drain_until(member_client, "history")
        await sync_to_async(permissions.ban_user)(group_room, member, owner)
        await member_client.send_json_to({"action": "message", "message": "hi"})
        err = await _drain_until(member_client, "error", timeout=3)
        assert "забанены" in err.get("message", "")
        await client.disconnect()
        await member_client.disconnect()

    async def test_message_flow(self, group_room, owner, member, ws_connect):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await member_client.send_json_to({"action": "message", "message": "ws test"})
        payload = await _drain_until(owner_client, "message", timeout=3)
        assert payload.get("message") == "ws test"
        await owner_client.disconnect()
        await member_client.disconnect()

    async def test_edit_broadcast(self, group_room, owner, member, owner_message, ws_connect):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await owner_client.send_json_to({"action": "edit", "message_id": owner_message.id, "text": "edited text"})
        payload = await _drain_until(member_client, "message_edited", timeout=3)
        assert payload["message"] == "edited text"
        await owner_client.disconnect()
        await member_client.disconnect()

    async def test_reaction_broadcast(self, group_room, owner, member, owner_message, ws_connect):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await member_client.send_json_to({"action": "reaction", "message_id": owner_message.id, "emoji": "🔥"})
        payload = await _drain_until(owner_client, "reaction", timeout=3)
        assert any(r["emoji"] == "🔥" for r in payload["reactions"])
        await owner_client.disconnect()
        await member_client.disconnect()

    async def test_pin_broadcast(self, group_room, owner, member, owner_message, ws_connect):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await owner_client.send_json_to({"action": "pin", "message_id": owner_message.id})
        payload = await _drain_until(member_client, "pinned", timeout=3)
        assert payload["pinned"] is True
        await owner_client.disconnect()
        await member_client.disconnect()

    async def test_typing_broadcast(self, group_room, owner, member, ws_connect):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await owner_client.send_json_to({"action": "typing", "is_typing": True})
        payload = await _drain_until(member_client, "typing", timeout=3)
        assert payload["username"] == owner.username
        await owner_client.disconnect()
        await member_client.disconnect()

    async def test_screen_share_broadcast(self, group_room, owner, member, ws_connect):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await owner_client.send_json_to({"action": "screen_share_start"})
        payload = await _drain_until(member_client, "screen_start", timeout=3)
        assert payload["broadcaster"] == owner.username
        await owner_client.send_json_to({"action": "screen_share_stop"})
        await _drain_until(member_client, "screen_stop", timeout=3)
        await owner_client.disconnect()
        await member_client.disconnect()

    async def test_signal_relay(self, group_room, owner, member, ws_connect):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await owner_client.send_json_to({
            "action": "webrtc_offer",
            "target": member.username,
            "sdp": {"type": "offer", "sdp": "x"},
        })
        payload = await _drain_until(member_client, "signal", timeout=3)
        assert payload["signal_type"] == "webrtc_offer"
        assert payload["from"] == owner.username
        await owner_client.disconnect()
        await member_client.disconnect()

    async def test_call_start_relays_incoming(self, group_room, owner, member, ws_connect):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await owner_client.send_json_to({
            "action": "call_start",
            "target": member.username,
            "call_id": "call-1",
            "mode": "audio",
        })
        payload = await _drain_until(member_client, "call_incoming", timeout=3)
        assert payload["call_id"] == "call-1"
        assert payload["from"] == owner.username
        assert payload["mode"] == "audio"
        await owner_client.disconnect()
        await member_client.disconnect()

    async def test_call_accept_then_hangup(self, group_room, owner, member, ws_connect, fake_redis):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await owner_client.send_json_to({
            "action": "call_start", "target": member.username, "call_id": "call-2", "mode": "video",
        })
        await _drain_until(member_client, "call_incoming", timeout=3)
        await member_client.send_json_to({
            "action": "call_accept", "target": owner.username, "call_id": "call-2",
        })
        accepted = await _drain_until(owner_client, "call_accept", timeout=3)
        assert accepted["from"] == member.username
        assert "call-2" in await fake_redis.smembers(f"call:user:{member.id}")
        await owner_client.send_json_to({
            "action": "call_hangup", "target": member.username, "call_id": "call-2",
        })
        hung = await _drain_until(member_client, "call_hangup", timeout=3)
        assert hung["call_id"] == "call-2"
        assert await fake_redis.smembers(f"call:act:{group_room.id}") == set()
        assert await fake_redis.smembers(f"call:user:{member.id}") == set()
        await owner_client.disconnect()
        await member_client.disconnect()

    async def test_call_busy_when_target_in_call(self, group_room, owner, member, moderator, ws_connect):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        moderator_client, _ = await ws_connect(moderator, group_room.name)
        for c in (owner_client, member_client, moderator_client):
            await _drain_until(c, "history")
        await owner_client.send_json_to({
            "action": "call_start", "target": member.username, "call_id": "call-3", "mode": "audio",
        })
        await _drain_until(member_client, "call_incoming", timeout=3)
        await member_client.send_json_to({
            "action": "call_accept", "target": owner.username, "call_id": "call-3",
        })
        await _drain_until(owner_client, "call_accept", timeout=3)
        # третий участник звонит member, который уже в активном звонке
        await moderator_client.send_json_to({
            "action": "call_start", "target": member.username, "call_id": "call-4", "mode": "audio",
        })
        busy = await _drain_until(moderator_client, "call_busy", timeout=3)
        assert busy["from"] == member.username
        await owner_client.disconnect()
        await member_client.disconnect()
        await moderator_client.disconnect()

    async def test_call_start_relays_to_user_outside_room(self, group_room, owner, stranger, ws_connect):
        await sync_to_async(
            lambda: ChatRoom.objects.create(name="stranger-room", owner=stranger, room_type="group")
        )()
        owner_client, _ = await ws_connect(owner, group_room.name)
        stranger_client, _ = await ws_connect(stranger, "stranger-room")
        await _drain_until(owner_client, "history")
        await _drain_until(stranger_client, "history")
        await owner_client.send_json_to({
            "action": "call_start", "target": stranger.username, "call_id": "call-5", "mode": "audio",
        })
        payload = await _drain_until(stranger_client, "call_incoming", timeout=3)
        assert payload["call_id"] == "call-5"
        assert payload["from"] == owner.username
        await owner_client.disconnect()
        await stranger_client.disconnect()

    async def test_disconnect_ends_active_call(self, group_room, owner, member, ws_connect):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await owner_client.send_json_to({
            "action": "call_start", "target": member.username, "call_id": "call-6", "mode": "audio",
        })
        await _drain_until(member_client, "call_incoming", timeout=3)
        await member_client.send_json_to({
            "action": "call_accept", "target": owner.username, "call_id": "call-6",
        })
        await _drain_until(owner_client, "call_accept", timeout=3)
        await owner_client.disconnect()
        hung = await _drain_until(member_client, "call_hangup", timeout=3)
        assert hung["call_id"] == "call-6"
        await member_client.disconnect()

    async def test_relay_skips_stale_user_channels(self, group_room, owner, member, ws_connect, fake_redis):
        owner_client, _ = await ws_connect(owner, group_room.name)
        member_client, _ = await ws_connect(member, group_room.name)
        live_channel = next(iter(await fake_redis.smembers(f"presence:user_{member.id}")))
        stale_channel = "specific.dead!stale1"
        await fake_redis.sadd(f"presence:user_{member.id}", stale_channel)
        await _drain_until(owner_client, "history")
        await _drain_until(member_client, "history")
        await owner_client.send_json_to({
            "action": "call_start",
            "target": member.username,
            "call_id": "call-7",
            "mode": "audio",
        })
        await _drain_until(member_client, "call_incoming", timeout=3)
        assert stale_channel not in await fake_redis.smembers(f"presence:user_{member.id}")
        assert live_channel in await fake_redis.smembers(f"presence:user_{member.id}")
        await owner_client.disconnect()
        await member_client.disconnect()

    async def test_prune_stale_user_sets(self, group_room, member, ws_connect, fake_redis):
        stale = "specific.dead!stale2"
        await fake_redis.sadd(f"presence:user_{member.id}", stale)
        client, _ = await ws_connect(member, group_room.name)
        await _drain_until(client, "history")
        _prune = ChatConsumer._prune_stale_user_sets
        await _prune(client, await ChatConsumer._get_redis())
        assert stale not in await fake_redis.smembers(f"presence:user_{member.id}")
        await client.disconnect()

    async def test_ai_request_empty_prompt(self, group_room, owner, ws_connect):
        client, _ = await ws_connect(owner, group_room.name)
        await _drain_until(client, "history")
        await client.send_json_to({"action": "ai_request", "prompt": "  "})
        err = await _drain_until(client, "error", timeout=3)
        assert "вопрос" in err.get("message", "")
        await client.disconnect()


@pytest.mark.django_db()
class TestSerializers:
    def test_room_serializer_members_fields(self, group_room, member, owner):
        _msg(group_room, member, "last one")
        ctx = {"request": SimpleNamespace(user=member)}
        data = ChatRoomSerializer(group_room, context=ctx).data
        usernames = {m["username"] for m in data["members"]}
        assert owner.username in usernames
        assert member.username in usernames
        moder = next(m for m in data["members"] if m["username"] == "moderator")
        assert moder["role"] == "moderator"
        assert data["member_count"] == data["member_count"]
        assert data["last_message"]["text"] == "last one"
        assert data["unread_count"] == 0
        assert data["server"] is None

    def test_admin_member_role_serialized(self, group_room, admin):
        group_room.members.add(admin)
        data = ChatRoomSerializer(group_room, context={"request": SimpleNamespace(user=admin)}).data
        admin_member = next(m for m in data["members"] if m["username"] == admin.username)
        assert admin_member["role"] == "admin"

    def test_message_serializer_reply_and_reactions(self, group_room, member, owner):
        parent = _msg(group_room, owner, "parent")
        reply = _msg(group_room, member, "child")
        reply.reply_to = parent
        reply.save(update_fields=["reply_to"])
        Reaction.objects.create(message=reply, user=owner, emoji="👍")
        data = MessageSerializer(reply).data
        assert data["reply_to"]["id"] == parent.id
        assert data["reactions"][0]["emoji"] == "👍"
        assert data["username"] == member.username
        assert data["avatar"] is None


@pytest.mark.django_db()
class TestRoomApi:
    def test_rooms_list_includes_public_and_owned(self, api_client, group_room, member):
        api_client.force_authenticate(user=member)
        resp = api_client.get("/api/chat/rooms/")
        assert resp.status_code == 200
        assert any(r["name"] == group_room.name for r in resp.data)

    def test_servers_list(self, api_client, owner):
        Server.objects.create(name="Team", owner=owner, description="d")
        api_client.force_authenticate(user=owner)
        resp = api_client.get("/api/chat/servers/")
        assert resp.status_code == 200
        assert any(s["name"] == "Team" for s in resp.data)
        assert resp.data[0]["member_count"] == resp.data[0]["member_count"]

    def test_room_messages_view(self, api_client, group_room, member, owner_message):
        api_client.force_authenticate(user=member)
        resp = api_client.get(f"/api/chat/rooms/{group_room.id}/messages/")
        assert resp.status_code == 200
        assert any(m["text"] == "hello from owner" for m in resp.data)

    def test_room_messages_404(self, api_client, member):
        api_client.force_authenticate(user=member)
        assert api_client.get("/api/chat/rooms/99999/messages/").status_code == 404

    def test_room_search(self, api_client, group_room, member, owner_message):
        api_client.force_authenticate(user=member)
        resp = api_client.get(f"/api/chat/rooms/{group_room.id}/search/?q=owner")
        assert resp.status_code == 200
        assert any(m["text"] == "hello from owner" for m in resp.data)

    def test_room_search_empty_query(self, api_client, group_room, member):
        api_client.force_authenticate(user=member)
        resp = api_client.get(f"/api/chat/rooms/{group_room.id}/search/?q=")
        assert resp.status_code == 400

    def test_room_search_404(self, api_client, member):
        api_client.force_authenticate(user=member)
        assert api_client.get("/api/chat/rooms/99999/search/?q=hi").status_code == 404

    def test_room_create_group(self, api_client, owner):
        api_client.force_authenticate(user=owner)
        resp = api_client.post(
            "/api/chat/rooms/create/",
            {"name": "new-room", "room_type": "group"},
            format="json",
        )
        assert resp.status_code == 201
        assert ChatRoom.objects.filter(name="new-room", owner=owner).exists()

    def test_room_create_invalid(self, api_client, owner):
        api_client.force_authenticate(user=owner)
        resp = api_client.post("/api/chat/rooms/create/", {}, format="json")
        assert resp.status_code == 400

    def test_room_join_and_leave(self, api_client, group_room, owner_message, stranger):
        api_client.force_authenticate(user=stranger)
        assert api_client.post(f"/api/chat/rooms/{group_room.id}/join/").status_code == 200
        assert stranger in group_room.members.all()
        assert api_client.post(f"/api/chat/rooms/{group_room.id}/leave/").status_code == 200
        assert stranger not in group_room.members.all()

    def test_owner_cannot_leave(self, api_client, group_room, owner):
        api_client.force_authenticate(user=owner)
        resp = api_client.post(f"/api/chat/rooms/{group_room.id}/leave/")
        assert resp.status_code == 400

    def test_private_room_join_denied(self, api_client, owner, stranger):
        room = ChatRoom.objects.create(name="private-room", owner=owner, room_type="group", is_private=True)
        room.members.add(owner)
        api_client.force_authenticate(user=stranger)
        resp = api_client.post(f"/api/chat/rooms/{room.id}/join/")
        assert resp.status_code == 403

    def test_add_member_owner_only(self, api_client, group_room, owner, stranger):
        api_client.force_authenticate(user=owner)
        resp = api_client.post(
            f"/api/chat/rooms/{group_room.id}/members/",
            {"user_id": stranger.id},
            format="json",
        )
        assert resp.status_code == 200
        assert stranger in group_room.members.all()

    def test_add_member_forbidden(self, api_client, group_room, member, stranger):
        api_client.force_authenticate(user=member)
        resp = api_client.post(
            f"/api/chat/rooms/{group_room.id}/members/",
            {"user_id": stranger.id},
            format="json",
        )
        assert resp.status_code == 403

    def test_upload_image(self, api_client, group_room, member):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (5, 5), "blue").save(buf, format="PNG")
        buf.seek(0)
        api_client.force_authenticate(user=member)
        resp = api_client.post(
            f"/api/chat/rooms/{group_room.id}/upload/",
            {"file": SimpleUploadedFile("x.png", buf.read(), content_type="image/png")},
            format="multipart",
        )
        assert resp.status_code == 201
        assert resp.data["attachment_type"] == "image"


@pytest.mark.django_db()
class TestServerApi:
    def test_server_create(self, api_client, owner):
        api_client.force_authenticate(user=owner)
        resp = api_client.post(
            "/api/chat/servers/create/",
            {"name": "NewServer", "description": "d"},
            format="json",
        )
        assert resp.status_code == 201
        server = Server.objects.get(name="NewServer")
        assert server.owner == owner

    def test_server_invite_owner(self, api_client, owner, member):
        server = Server.objects.create(name="S", owner=owner, description="")
        server.members.add(owner, member)
        api_client.force_authenticate(user=member)
        resp = api_client.get(f"/api/chat/servers/{server.id}/invite/")
        assert resp.status_code == 200
        assert str(server.invite_token) in resp.data["token"]

    def test_server_invite_forbidden(self, api_client, owner, stranger):
        server = Server.objects.create(name="S2", owner=owner, description="")
        server.members.add(owner)
        api_client.force_authenticate(user=stranger)
        resp = api_client.get(f"/api/chat/servers/{server.id}/invite/")
        assert resp.status_code == 403

    def test_server_join_invalid_token(self, api_client, member):
        api_client.force_authenticate(user=member)
        resp = api_client.post("/api/chat/servers/join/not-a-token/")
        assert resp.status_code == 404

    def test_server_join_valid_token(self, api_client, owner, stranger):
        server = Server.objects.create(name="Join", owner=owner, description="")
        server.members.add(owner)
        api_client.force_authenticate(user=stranger)
        resp = api_client.post(f"/api/chat/servers/join/{server.invite_token}/")
        assert resp.status_code == 200
        assert stranger in server.members.all()
