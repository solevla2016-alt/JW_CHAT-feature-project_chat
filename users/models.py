from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Модель пользователя JOIN WORK!."""

    class Role(models.TextChoices):
        MEMBER = "member", "Пользователь"
        MODERATOR = "moderator", "Модератор"
        ADMIN = "admin", "Администратор"

    class MessagePrivacy(models.TextChoices):
        EVERYONE = "everyone", "Все"
        CONTACTS = "contacts", "Контакты"
        NOBODY = "nobody", "Никто"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        help_text="Роль пользователя в сервисе",
    )

    avatar = models.ImageField(
        upload_to="avatars/%Y/%m",
        blank=True,
        null=True,
    )
    status = models.CharField(
        max_length=200,
        blank=True,
        default="",
    )
    birth_date = models.DateField(
        blank=True,
        null=True,
        help_text="Дата рождения",
    )
    message_privacy = models.CharField(
        max_length=20,
        choices=MessagePrivacy.choices,
        default=MessagePrivacy.EVERYONE,
        help_text="Кто может отправлять мне сообщения",
    )

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.username


class PasswordResetToken(models.Model):
    """Одноразовый токен восстановления пароля (ссылка из письма Resend)."""

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Reset token {self.user_id} ({self.token[:8]}…)"
