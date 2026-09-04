from django.conf import settings
from django.db import models


class ChatRoom(models.Model):
    """Комната чата JOIN WORK!."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, default="")
    avatar = models.ImageField(upload_to="chat_rooms/", blank=True, null=True)
    is_private = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_rooms",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="chat_rooms",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class Message(models.Model):
    """Сообщение в чате."""

    class AttachmentType(models.TextChoices):
        NONE = "none", "Нет"
        IMAGE = "image", "Изображение"
        AUDIO = "audio", "Аудио"
        VIDEO = "video", "Видео"
        FILE = "file", "Файл"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    text = models.TextField(blank=True, default="")
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
    )
    is_edited = models.BooleanField(default=False)
    attachment_type = models.CharField(
        max_length=10,
        choices=AttachmentType.choices,
        default=AttachmentType.NONE,
    )
    attachment_url = models.FileField(
        upload_to="attachments/",
        blank=True,
        null=True,
    )
    attachment_name = models.CharField(max_length=255, blank=True, default="")
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Длительность аудио/видео в секундах",
    )
    pinned = models.BooleanField(default=False)
    pinned_at = models.DateTimeField(null=True, blank=True)
    transcription = models.TextField(blank=True, default="", help_text="Транскрипция голосового сообщения")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["room", "created_at"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:
        prefix = f"[{self.attachment_type}] " if self.attachment_type != "none" else ""
        return f"{prefix}{self.user.username}: {self.text[:50]}"


class ReadStatus(models.Model):
    """Отметка о прочтении сообщения пользователем."""

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="read_statuses",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="read_statuses",
    )
    read_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user"],
                name="unique_message_user_read",
            )
        ]
        indexes = [
            models.Index(fields=["message"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} read msg {self.message_id}"


class Reaction(models.Model):
    """Реакция (эмодзи) на сообщение."""

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reactions",
    )
    emoji = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "user", "emoji"],
                name="unique_message_user_emoji",
            )
        ]
        indexes = [
            models.Index(fields=["message"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username}: {self.emoji} on {self.message_id}"

