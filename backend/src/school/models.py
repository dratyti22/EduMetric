import uuid

from django.conf import settings
from django.db import models

from school.enum import Subject


class SchoolClass(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name = models.CharField(max_length=100)
    subject = models.CharField(max_length=30, choices=Subject.choices)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="school_classes"
    )
    join_code = models.CharField(
        max_length=16,
        unique=True,
        null=True,
        blank=True,
        help_text="Код для вступления ученика, например EX-7K4p9M2A",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "name", "subject"], name="unique_teacher_class_subject"
            )
        ]

    def __str__(self) -> str:
        return f"{self.name}"


class Student(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    school_class = models.ForeignKey(
        "SchoolClass", on_delete=models.CASCADE, related_name="students"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student_profiles",
        help_text="Аккаунт ученика. Пусто, если карточку завёл учитель вручную.",
    )

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    middle_name = models.CharField(max_length=150, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["school_class", "user"],
                condition=models.Q(user__isnull=False),
                name="unique_student_user_per_class",
            )
        ]

    def __str__(self) -> str:
        return f"{self.last_name} {self.first_name}"

    @property
    def is_linked(self) -> bool:
        return self.user_id is not None


class ClassJoinRequest(models.Model):
    """Запрос на привязку аккаунта к уже существующей ручной карточке ученика."""

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        APPROVED = "approved", "Подтверждён"
        REJECTED = "rejected", "Отклонён"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="join_requests"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="class_join_requests"
    )
    matched_student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="join_requests",
        help_text="Ручная карточка с тем же ФИО.",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["school_class", "user"],
                condition=models.Q(status="pending"),
                name="unique_pending_join_request",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.school_class} ({self.status})"
