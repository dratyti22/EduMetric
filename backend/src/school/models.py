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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "name", "subject"],
                name="unique_teacher_class_subject"
            )
        ]

    def __str__(self) -> str:
        return f"{self.name}"
