import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from school.enum import Subject
from school.models import SchoolClass, Student


class ExamTemplate(models.Model):
    """Стандарт ФИПИ: задания + шкала перевода. Редактируется в админке."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.CharField(max_length=30, choices=Subject.choices)
    year = models.PositiveIntegerField()
    title = models.CharField(max_length=255, blank=True, help_text="Например: ЕГЭ 2026")
    default_passing_secondary = models.PositiveIntegerField(
        default=36, validators=[MaxValueValidator(100)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["subject", "year"], name="unique_exam_template_subject_year"
            )
        ]
        ordering = ["-year", "subject"]

    def __str__(self):
        return f"{self.get_subject_display()} — {self.year}"

    @property
    def max_primary_score(self) -> int:
        return self.tasks.aggregate(total=models.Sum("max_score"))["total"] or 0

    @property
    def task_count(self) -> int:
        return self.tasks.count()


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

    def __str__(self):
        return f"№{self.number} (макс. {self.max_score})"


class ScoreConversion(models.Model):
    """Шкала перевода первичный -> вторичный балл (для шаблона)."""

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
                fields=["template", "primary_score"],
                name="unique_template_primary_score",
            )
        ]

    def __str__(self):
        return f"{self.primary_score} → {self.test_score}"


class Exam(models.Model):
    """Пробник. Может быть создан по шаблону или полностью кастомный."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        IN_PROGRESS = "in_progress", "В процессе"
        COMPLETED = "completed", "Завершён"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    source = models.CharField(max_length=255, blank=True)
    variant = models.CharField(max_length=100, blank=True)
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name="exams")
    # Если указан — берём шкалу перевода отсюда. Задания всё равно копируются в ExamTask.
    template = models.ForeignKey(
        ExamTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exams",
    )
    subject = models.CharField(max_length=30, choices=Subject.choices)
    academic_year = models.CharField(max_length=20, default="2025/2026")
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    passing_score_secondary = models.PositiveIntegerField(
        default=36, validators=[MaxValueValidator(100)]
    )
    # Если template=None и нужны свои баллы — можно хранить свою шкалу (опционально)
    use_proportional_conversion = models.BooleanField(
        default=False,
        help_text="Если True и нет шаблона — secondary = round(primary / max * 100)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def task_count(self) -> int:
        return self.tasks.count()

    @property
    def max_primary_score(self) -> int:
        return self.tasks.aggregate(total=models.Sum("max_score"))["total"] or 0

    def convert_primary_to_secondary(self, primary: int) -> int | None:
        if primary <= 0:
            return 0
        max_p = self.max_primary_score
        if max_p <= 0:
            return 0
        if primary >= max_p:
            return 100

        if self.template_id:
            conv = (
                ScoreConversion.objects.filter(template_id=self.template_id, primary_score=primary)
                .values_list("test_score", flat=True)
                .first()
            )
            if conv is not None:
                return conv

        if self.use_proportional_conversion or not self.template_id:
            return round(min(1.0, primary / max_p) * 100)

        return None


class ExamTask(models.Model):
    """Задание конкретного пробника (может отличаться от шаблона)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="tasks")
    number = models.PositiveIntegerField()
    max_score = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["number"]
        constraints = [
            models.UniqueConstraint(fields=["exam", "number"], name="unique_exam_task_number")
        ]

    def __str__(self):
        return f"№{self.number} (макс. {self.max_score})"


class StudentResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="student_results")
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="exam_results")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["exam", "student"], name="unique_exam_student_result")
        ]

    def __str__(self):
        return f"{self.student} — {self.exam}"


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
                fields=["student_result", "task"],
                name="unique_student_task_result",
            )
        ]
