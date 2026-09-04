from django.contrib.auth import authenticate, get_user_model, login, logout
from django.views.decorators.csrf import csrf_exempt
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes, permission_classes
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

    if not username or not password:
        return Response({"error": "Username и пароль обязательны"}, status=status.HTTP_400_BAD_REQUEST)

    if password != password2:
        return Response({"error": "Пароли не совпадают"}, status=status.HTTP_400_BAD_REQUEST)

    if len(password) < 6:
        return Response({"error": "Пароль минимум 6 символов"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({"error": "Пользователь уже существует"}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, email=email, password=password)
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
    users = User.objects.exclude(id=request.user.id).values("id", "username", "avatar", "status")[:100]
    return Response(list(users))


def _user_data(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "avatar": user.avatar.url if user.avatar else None,
        "status": user.status,
    }
