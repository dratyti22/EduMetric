import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from school.enum import Subject
from school.models import SchoolClass, Student


class ExamTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.CharField(max_length=30, choices=Subject.choices)
    year = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "year"], name="unique_exam_template_subject_year"
            )
        ]

    def __str__(self):
        return f"{self.subject} — {self.year}"


class ExamTemplateTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(ExamTemplate, on_delete=models.CASCADE, related_name="tasks")
    number = models.PositiveIntegerField()
    max_score = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "number"], name="unique_template_task_number"
            )
        ]


class Exam(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        IN_PROGRESS = "in_progress", "В процессе"
        COMPLETED = "completed", "Завершён"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    source = models.CharField(max_length=255, blank=True)
    variant = models.CharField(max_length=100, blank=True)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="exams")
    template = models.ForeignKey(ExamTemplate, on_delete=models.PROTECT, related_name="exams")
    subject = models.CharField(max_length=30, choices=Subject.choices)
    year = models.PositiveIntegerField()
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    @property
    def task_count(self):
        return self.tasks.count()

    @property
    def max_primary_score(self):
        return self.tasks.aggregate(total=models.Sum("max_score"))["total"] or 0

    def __str__(self) -> str:
        return self.title


class ExamTask(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="tasks")
    number = models.PositiveIntegerField()
    max_score = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(fields=["exam", "number"], name="unique_exam_task_number")
        ]


class ScoreConversion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(
        ExamTemplate, on_delete=models.CASCADE, related_name="score_conversions"
    )
    primary_score = models.PositiveIntegerField()
    test_score = models.PositiveIntegerField(validators=[MaxValueValidator(100)])

    class Meta:
        ordering = ["primary_score"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "primary_score"], name="unique_template_primary_score"
            )
        ]


class StudentResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="student_results")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="exam_results")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["exam", "student"], name="unique_exam_student_result")
        ]


class TaskResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student_result = models.ForeignKey(
        StudentResult, on_delete=models.CASCADE, related_name="task_results"
    )
    task = models.ForeignKey(ExamTask, on_delete=models.CASCADE, related_name="student_scores")
    score = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student_result", "task"], name="unique_student_task_result"
            )
        ]
