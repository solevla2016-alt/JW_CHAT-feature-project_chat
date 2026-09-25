import logging
from datetime import timedelta

import httpx
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.request import Request
from rest_framework.response import Response

from .models import PasswordResetToken

User = get_user_model()
logger = logging.getLogger(__name__)


class CsrfExemptSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([permissions.AllowAny])
def register_view(request: Request) -> Response:
    username = request.data.get("username", "").strip()
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "")
    password2 = request.data.get("password2", "")
    birth_date = request.data.get("birth_date") or None

    if not username or not password:
        return Response({"error": "Username и пароль обязательны"}, status=status.HTTP_400_BAD_REQUEST)

    if password != password2:
        return Response({"error": "Пароли не совпадают"}, status=status.HTTP_400_BAD_REQUEST)

    if len(password) < 6:
        return Response({"error": "Пароль минимум 6 символов"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({"error": "Пользователь уже существует"}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, email=email, password=password)
    if birth_date:
        try:
            from datetime import date
            user.birth_date = date.fromisoformat(birth_date)
            user.save(update_fields=["birth_date"])
        except ValueError:
            return Response({"error": "Некорректная дата рождения"}, status=status.HTTP_400_BAD_REQUEST)
    login(request, user)
    return Response(_user_data(user), status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([permissions.AllowAny])
def login_view(request: Request) -> Response:
    username = request.data.get("username", "").strip()
    password = request.data.get("password", "")
    user = authenticate(request, username=username, password=password)
    if user is None:
        user = _authenticate_case_insensitive(request, username, password)
    if user is None and "@" in username:
        for email_user in User.objects.filter(email__iexact=username):
            user = authenticate(request, username=email_user.username, password=password)
            if user is not None:
                break
    if user is None:
        return Response({"error": "Неверный логин или пароль"}, status=status.HTTP_400_BAD_REQUEST)
    login(request, user)
    return Response(_user_data(user))


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
def logout_view(request: Request) -> Response:
    logout(request)
    return Response({"success": True})


@api_view(["GET"])
def me_view(request: Request) -> Response:
    if request.user.is_anonymous:
        return Response({"authenticated": False}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(_user_data(request.user))


@api_view(["GET"])
def users_list_view(request: Request) -> Response:
    ai_username = settings.AI_ASSISTANT_USERNAME
    ai_user, _ = User.objects.get_or_create(
        username=ai_username,
        defaults={"email": "ai@joinwork.local", "status": "AI"},
    )
    ai_data = {
        "id": ai_user.id,
        "username": ai_user.username,
        "avatar": ai_user.avatar.url if ai_user.avatar else None,
        "status": ai_user.status,
        "is_ai": True,
    }
    users = (
        User.objects
        .exclude(id__in=[request.user.id, ai_user.id])
        .only("id", "username", "avatar", "status")[:100]
    )
    result = [
        {
            "id": u.id,
            "username": u.username,
            "avatar": u.avatar.url if u.avatar else None,
            "status": u.status,
        }
        for u in users
    ]
    return Response([ai_data, *result])


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
def profile_update_view(request: Request) -> Response:
    user = request.user
    data = request.data

    status_text = data.get("status")
    if status_text is not None:
        user.status = str(status_text)[:200]

    birth_date = data.get("birth_date")
    if birth_date:
        try:
            from datetime import date
            user.birth_date = date.fromisoformat(str(birth_date))
        except ValueError:
            return Response({"error": "Некорректная дата рождения"}, status=status.HTTP_400_BAD_REQUEST)
    elif birth_date == "":
        user.birth_date = None

    privacy = data.get("message_privacy")
    if privacy and privacy in dict(User.MessagePrivacy.choices):
        user.message_privacy = privacy

    user.save()
    return Response(_user_data(user))


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
def avatar_upload_view(request: Request) -> Response:
    user = request.user
    avatar = request.FILES.get("avatar")
    if not avatar:
        return Response({"error": "Файл не передан"}, status=status.HTTP_400_BAD_REQUEST)

    ext = avatar.name.lower().rsplit(".", 1)[-1] if "." in avatar.name else ""
    allowed = {"jpg", "jpeg", "png", "gif", "webp"}
    if ext not in allowed:
        return Response({"error": "Формат файла не поддерживается"}, status=status.HTTP_400_BAD_REQUEST)

    user.avatar = avatar
    user.save()
    return Response(_user_data(user))


def _authenticate_case_insensitive(request, login: str, password: str):
    from django.contrib.auth import authenticate

    user = None
    try:
        found = User.objects.get(username__iexact=login)
        user = authenticate(request, username=found.username, password=password)
    except (User.DoesNotExist, User.MultipleObjectsReturned):
        pass
    return user


def _user_data(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "avatar": user.avatar.url if user.avatar else None,
        "status": user.status,
        "birth_date": user.birth_date.isoformat() if user.birth_date else None,
        "message_privacy": user.message_privacy,
        "role": user.role,
        "is_staff": user.is_staff,
    }


def _can_manage_roles(user: User) -> bool:
    """Назначать роли может администратор: staff или пользователь с ролью «admin»."""
    return bool(user.is_staff or user.role == User.Role.ADMIN)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
def set_role_view(request: Request) -> Response:
    if not _can_manage_roles(request.user):
        return Response(
            {"error": "Недостаточно прав"},
            status=status.HTTP_403_FORBIDDEN,
        )

    username = request.data.get("username", "").strip()
    role = request.data.get("role", "").strip()

    if role not in dict(User.Role.choices):
        return Response({"error": "Некорректная роль"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(username__iexact=username)
    except User.DoesNotExist:
        return Response({"error": "Пользователь не найден"}, status=status.HTTP_404_NOT_FOUND)

    if user.role == role:
        return Response(_user_data(user))

    user.role = role
    user.save(update_fields=["role"])
    return Response(_user_data(user))


# ----------------------------------------------------------------------
# Восстановление пароля через Resend (п.3)
# ----------------------------------------------------------------------

def _send_reset_email(to_email: str, reset_url: str, username: str) -> None:
    """Транзакционное письмо с итоговой ссылкой сброса пароля через Resend API."""
    if not settings.RESEND_API_KEY:
        return

    html = f"""<!doctype html>
<html lang="ru">
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:24px;">
    <tr><td align="center">
      <table role="presentation" width="520" cellpadding="0" cellspacing="0" style="max-width:520px;width:100%;background:#ffffff;border-radius:16px;padding:32px;">
        <tr><td style="font-size:13px;color:#6b7280;padding-bottom:4px;">JOIN WORK!</td></tr>
        <tr><td style="padding-top:4px;padding-bottom:16px;font-size:22px;font-weight:700;color:#111827;">Восстановление пароля</td></tr>
        <tr><td style="font-size:14px;line-height:20px;color:#374151;padding-bottom:20px;">Здравствуйте, <b>{username}</b>! Для сброса пароля нажмите кнопку ниже (ссылка действует 1 час):</td></tr>
        <tr><td style="padding-bottom:24px;">
          <a href="{reset_url}" style="display:inline-block;background:#4f46e5;color:#ffffff;padding:12px 24px;border-radius:10px;font-size:14px;font-weight:600;text-decoration:none;">Сбросить пароль</a>
        </td></tr>
        <tr><td style="font-size:12px;color:#9ca3af;">Если вы не запрашивали сброс — просто проигнорируйте это письмо.</td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    try:
        httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"{settings.RESEND_FROM_NAME} <{settings.RESEND_FROM_EMAIL}>",
                "to": [to_email],
                "subject": "JOIN WORK: восстановление пароля",
                "html": html,
            },
            timeout=15,
        )
    except Exception:
        logger.exception("Не удалось отправить письмо восстановления на %s", to_email)


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([permissions.AllowAny])
def password_reset_request_view(request: Request) -> Response:
    """Принимает email, создаёт одноразовый токен и шлёт письмо через Resend."""
    email = request.data.get("email", "").strip()
    if not email:
        return Response({"error": "Укажите email"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response({"error": "Пользователь с таким email не найден"}, status=status.HTTP_404_NOT_FOUND)

    PasswordResetToken.objects.filter(user=user, used=False).update(used=True)

    raw_token = get_random_string(48)
    token = PasswordResetToken.objects.create(
        user=user,
        token=raw_token,
        expires_at=timezone.now() + timedelta(hours=1),
    )

    reset_url = (
        f"{settings.FRONTEND_URL}/reset-password?uid={urlsafe_base64_encode(str(user.pk).encode())}"
        f"&token={raw_token}"
    )
    _send_reset_email(user.email, reset_url, user.username)

    return Response({"ok": True, "token_id": token.pk})


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([permissions.AllowAny])
def password_reset_confirm_view(request: Request) -> Response:
    """Проверяет токен и устанавливает новый пароль."""
    uid = request.data.get("uid", "")
    token = request.data.get("token", "").strip()
    password = request.data.get("password", "")
    password2 = request.data.get("password2", "")

    if not password or password != password2:
        return Response({"error": "Пароли не совпадают"}, status=status.HTTP_400_BAD_REQUEST)
    if len(password) < 6:
        return Response({"error": "Пароль минимум 6 символов"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_pk = int(urlsafe_base64_decode(uid).decode())
    except Exception:
        return Response({"error": "Ссылка некорректна"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        reset_token = PasswordResetToken.objects.get(
            user_id=user_pk,
            token=token,
            used=False,
        )
    except PasswordResetToken.DoesNotExist:
        return Response({"error": "Ссылка недействительна"}, status=status.HTTP_400_BAD_REQUEST)

    if reset_token.expires_at < timezone.now():
        return Response({"error": "Ссылка истекла"}, status=status.HTTP_400_BAD_REQUEST)

    user = reset_token.user
    user.set_password(password)
    user.save(update_fields=["password"])
    reset_token.used = True
    reset_token.save(update_fields=["used"])

    return Response({"ok": True, "username": user.username})
