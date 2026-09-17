from io import BytesIO

import pytest
from django.contrib.auth import get_user_model

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

    def test_logout(self, api_client, user):
        api_client.force_authenticate(user=user)
        assert api_client.post(LOGOUT_URL).status_code == 200


@pytest.mark.django_db()
class TestProfileApi:
    def test_update_status_and_privacy(self, api_client, user):
        api_client.force_authenticate(user=user)
        resp = api_client.post(
            PROFILE_URL,
            {"status": "в работе", "message_privacy": "contacts"},
            format="json",
        )
        assert resp.status_code == 200
        user.refresh_from_db()
        assert user.status == "в работе"
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
