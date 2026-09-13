from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Модель пользователя JOIN WORK!."""

    class MessagePrivacy(models.TextChoices):
        EVERYONE = "everyone", "Все"
        CONTACTS = "contacts", "Контакты"
        NOBODY = "nobody", "Никто"

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
