from django.contrib.auth import authenticate, get_user_model, login, logout
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

User = get_user_model()


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
    users = (
        User.objects.exclude(id=request.user.id)
        .only("id", "username", "avatar", "status")[:100]
    )
    return Response(
        [
            {
                "id": u.id,
                "username": u.username,
                "avatar": u.avatar.url if u.avatar else None,
                "status": u.status,
            }
            for u in users
        ]
    )


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
    }


@csrf_exempt
@api_view(["POST"])
@authentication_classes([CsrfExemptSessionAuthentication])
@permission_classes([permissions.IsAdminUser])
def set_role_view(request: Request) -> Response:
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
