from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Модель пользователя JOIN WORK!."""

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

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.username
