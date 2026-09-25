from datetime import timedelta
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

REGISTER_URL = "/api/auth/register/"
LOGIN_URL = "/api/auth/login/"
ME_URL = "/api/auth/me/"
LOGOUT_URL = "/api/auth/logout/"
PROFILE_URL = "/api/auth/profile/"
AVATAR_URL = "/api/auth/avatar/"
SET_ROLE_URL = "/api/auth/set-role/"


def _make_png() -> BytesIO:
    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, format="PNG")
    buf.seek(0)
    return buf


@pytest.mark.django_db()
class TestAuthApi:
    def test_register_creates_user(self, api_client):
        resp = api_client.post(
            REGISTER_URL,
            {"username": "newbie", "password": "secret123", "password2": "secret123"},
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["username"] == "newbie"
        assert resp.data["role"] == "member"
        assert User.objects.filter(username="newbie").exists()

    def test_register_requires_passwords(self, api_client):
        resp = api_client.post(
            REGISTER_URL,
            {"username": "newbie", "password": "secret123"},
            format="json",
        )
        assert resp.status_code == 400

    def test_register_password_mismatch(self, api_client):
        resp = api_client.post(
            REGISTER_URL,
            {"username": "newbie", "password": "secret123", "password2": "other123"},
            format="json",
        )
        assert resp.status_code == 400

    def test_register_short_password(self, api_client):
        resp = api_client.post(
            REGISTER_URL,
            {"username": "newbie", "password": "123", "password2": "123"},
            format="json",
        )
        assert resp.status_code == 400

    def test_register_duplicate_username(self, api_client, user):
        resp = api_client.post(
            REGISTER_URL,
            {"username": user.username, "password": "secret123", "password2": "secret123"},
            format="json",
        )
        assert resp.status_code == 400

    def test_login_success(self, api_client, user):
        resp = api_client.post(
            LOGIN_URL,
            {"username": user.username, "password": "pass12345"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.data["username"] == user.username

    def test_login_wrong_password(self, api_client, user):
        resp = api_client.post(
            LOGIN_URL,
            {"username": user.username, "password": "wrong-password"},
            format="json",
        )
        assert resp.status_code == 400

    def test_me_authenticated(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.get(ME_URL)
        assert resp.status_code == 200
        assert resp.data["role"] == "member"

    def test_me_anonymous(self, api_client):
        resp = api_client.get(ME_URL)
        assert resp.status_code == 403

    def test_users_list_includes_ai_assistant(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.get("/api/auth/users/")
        assert resp.status_code == 200
        assert len(resp.data) >= 1
        assert resp.data[0]["username"] == "AI Assistant"
        assert resp.data[0]["is_ai"] is True
        assert all(u["username"] != "AI Assistant" for u in resp.data[1:])

    def test_logout(self, api_client, user):
        api_client.force_authenticate(user=user)
        assert api_client.post(LOGOUT_URL).status_code == 200


@pytest.mark.django_db()
class TestProfileApi:
    def test_update_status_and_privacy(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            PROFILE_URL,
            {"status": "РІ СЂР°Р±РѕС‚Рµ", "message_privacy": "contacts"},
            format="json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.status == "РІ СЂР°Р±РѕС‚Рµ"
        assert user.message_privacy == "contacts"

    def test_update_invalid_birth_date(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            PROFILE_URL,
            {"birth_date": "not-a-date"},
            format="json",
        )
        assert resp.status_code == 400

    def test_clear_birth_date(self, api_client, user):
        user.birth_date = "2000-01-01"
        user.save()
        api_client.force_authenticate(user=user)
        resp = api_client.post(PROFILE_URL, {"birth_date": ""}, format="json")
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.birth_date is None

    def test_avatar_upload(self, api_client, user):
        from django.core.files.uploadedfile import SimpleUploadedFile

        api_client.force_authenticate(user=user)
        resp = api_client.post(
            AVATAR_URL,
            {"avatar": SimpleUploadedFile("a.png", _make_png().read(), content_type="image/png")},
            format="multipart",
        )
        assert resp.status_code == 200
        assert resp.data["avatar"]

    def test_avatar_bad_format(self, api_client, user):
        from django.core.files.uploadedfile import SimpleUploadedFile

        api_client.force_authenticate(user=user)
        resp = api_client.post(
            AVATAR_URL,
            {"avatar": SimpleUploadedFile("a.exe", b"MZ...", content_type="application/octet-stream")},
            format="multipart",
        )
        assert resp.status_code == 400


@pytest.mark.django_db()
class TestSetRoleApi:
    def test_superuser_promotes_moderator(self, api_client, superuser, user):
        api_client.force_authenticate(user=superuser)
        resp = api_client.post(
            SET_ROLE_URL,
            {"username": user.username, "role": "moderator"},
            format="json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.role == "moderator"

    def test_member_forbidden(self, api_client, user, member):
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            SET_ROLE_URL,
            {"username": member.username, "role": "admin"},
            format="json",
        )
        assert resp.status_code == 403

    def test_app_admin_can_promote_moderator(self, api_client, admin, user):
        api_client.force_authenticate(user=admin)
        resp = api_client.post(
            SET_ROLE_URL,
            {"username": user.username, "role": "moderator"},
            format="json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.role == "moderator"

    def test_invalid_role(self, api_client, superuser, user):
        api_client.force_authenticate(user=superuser)
        resp = api_client.post(
            SET_ROLE_URL,
            {"username": user.username, "role": "king"},
            format="json",
        )
        assert resp.status_code == 400

    def test_missing_user(self, api_client, superuser):
        api_client.force_authenticate(user=superuser)
        resp = api_client.post(
            SET_ROLE_URL,
            {"username": "ghost", "role": "admin"},
            format="json",
        )
        assert resp.status_code == 404


PASSWORD_RESET_REQUEST_URL = "/api/auth/password-reset/request/"
PASSWORD_RESET_CONFIRM_URL = "/api/auth/password-reset/confirm/"


@pytest.mark.django_db()
class TestPasswordReset:
    def test_request_creates_token_and_sends_email(self, api_client, user, monkeypatch):
        user.email = "reset@example.com"
        user.save(update_fields=["email"])

        sent = {}

        def _fake_post(url, headers=None, json=None, timeout=None):
            sent["url"] = url
            sent["json"] = json
            return None

        monkeypatch.setattr("users.api_views.httpx.post", _fake_post)
        monkeypatch.setattr(
            "users.api_views.settings.RESEND_API_KEY",
            "test-key",
            raising=False,
        )

        resp = api_client.post(
            PASSWORD_RESET_REQUEST_URL,
            {"email": "reset@example.com"},
            format="json",
        )
        assert resp.status_code == 200
        assert sent["url"] == "https://api.resend.com/emails"
        assert sent["json"]["to"] == ["reset@example.com"]
        assert sent["json"]["from"].startswith("JW CHAT <")

    def test_request_unknown_email_returns_404(self, api_client):
        resp = api_client.post(
            PASSWORD_RESET_REQUEST_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        assert resp.status_code == 404

    def test_request_missing_email_returns_400(self, api_client):
        resp = api_client.post(PASSWORD_RESET_REQUEST_URL, {}, format="json")
        assert resp.status_code == 400

    def test_confirm_sets_new_password(self, api_client, user, monkeypatch):
        from django.utils.http import urlsafe_base64_encode

        from .models import PasswordResetToken

        user.email = "reset@example.com"
        user.save(update_fields=["email"])

        raw = "testtoken123"
        PasswordResetToken.objects.create(
            user=user,
            token=raw,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        uid = urlsafe_base64_encode(str(user.pk).encode())

        resp = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "uid": uid,
                "token": raw,
                "password": "newpass123",
                "password2": "newpass123",
            },
            format="json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.check_password("newpass123")
        assert PasswordResetToken.objects.filter(token=raw, used=True).exists()

    def test_confirm_expired_token_fails(self, api_client, user):
        from django.utils.http import urlsafe_base64_encode

        from .models import PasswordResetToken

        raw = "expiredtoken"
        PasswordResetToken.objects.create(
            user=user,
            token=raw,
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        uid = urlsafe_base64_encode(str(user.pk).encode())

        resp = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "uid": uid,
                "token": raw,
                "password": "newpass123",
                "password2": "newpass123",
            },
            format="json",
        )
        assert resp.status_code == 400
        user.refresh_from_db()
        assert not user.check_password("newpass123")

    def test_confirm_invalid_token_fails(self, api_client, user):
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(str(user.pk).encode())
        resp = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "uid": uid,
                "token": "nonexistent",
                "password": "newpass123",
                "password2": "newpass123",
            },
            format="json",
        )
        assert resp.status_code == 400

    def test_confirm_mismatched_passwords_fails(self, api_client, user):
        from django.utils.http import urlsafe_base64_encode

        from .models import PasswordResetToken

        raw = "mismatchtoken"
        PasswordResetToken.objects.create(
            user=user,
            token=raw,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        uid = urlsafe_base64_encode(str(user.pk).encode())

        resp = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "uid": uid,
                "token": raw,
                "password": "newpass123",
                "password2": "different123",
            },
            format="json",
        )
        assert resp.status_code == 400
