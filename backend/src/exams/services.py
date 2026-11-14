from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from school.models import Student

from .models import Exam, ExamTask, ExamTemplate, StudentResult, TaskResult


def current_academic_year() -> str:
    today = timezone.localdate()
    if today.month >= 9:
        return f"{today.year}/{today.year + 1}"
    return f"{today.year - 1}/{today.year}"


@transaction.atomic
def create_exam(
    *,
    school_class,
    title: str,
    subject: str,
    template: ExamTemplate | None = None,
    tasks: list[dict] | None = None,  # [{"number": 1, "max_score": 1}, ...]
    source: str = "",
    variant: str = "",
    date=None,
    academic_year: str | None = None,
    passing_score_secondary: int | None = None,
    use_proportional_conversion: bool = False,
) -> Exam:
    """
    Создаёт пробник.
    - Если передан template — копируем задания из него (можно переопределить tasks).
    - Если tasks передан — используем кастомные задания.
    - Хотя бы одно из template / tasks обязательно.
    """
    if not template and not tasks:
        raise ValidationError("Нужно указать шаблон или список заданий.")

    if template and template.subject != subject:
        raise ValidationError("Предмет шаблона не совпадает с предметом пробника.")

    if school_class.subject != subject:
        # Можно ослабить, если хотите разрешить любой предмет в классе
        pass

    final_tasks = []
    if tasks:
        final_tasks = sorted(tasks, key=lambda t: t["number"])
    elif template:
        final_tasks = [{"number": t.number, "max_score": t.max_score} for t in template.tasks.all()]

    if not final_tasks:
        raise ValidationError("Нет заданий для пробника.")

    exam = Exam.objects.create(
        title=title.strip(),
        source=source,
        variant=variant,
        school_class=school_class,
        template=template,
        subject=subject,
        academic_year=academic_year or current_academic_year(),
        date=date or timezone.localdate(),
        passing_score_secondary=(
            passing_score_secondary
            if passing_score_secondary is not None
            else (template.default_passing_secondary if template else 36)
        ),
        use_proportional_conversion=use_proportional_conversion or (template is None),
    )

    exam_tasks = ExamTask.objects.bulk_create(
        [ExamTask(exam=exam, number=t["number"], max_score=t["max_score"]) for t in final_tasks]
    )

    # Создаём пустые результаты для всех учеников класса
    students = list(Student.objects.filter(school_class=school_class))
    results = StudentResult.objects.bulk_create(
        [StudentResult(exam=exam, student=s) for s in students]
    )
    TaskResult.objects.bulk_create(
        [TaskResult(student_result=r, task=t) for r in results for t in exam_tasks]
    )

    return exam


@transaction.atomic
def sync_exam_students(exam: Exam) -> int:
    """Добавляет в пробник новых учеников класса, которых ещё нет."""
    existing_ids = set(StudentResult.objects.filter(exam=exam).values_list("student_id", flat=True))
    students = list(
        Student.objects.filter(school_class=exam.school_class).exclude(id__in=existing_ids)
    )
    if not students:
        return 0

    results = StudentResult.objects.bulk_create(
        [StudentResult(exam=exam, student=s) for s in students]
    )
    tasks = list(exam.tasks.all())
    TaskResult.objects.bulk_create(
        [TaskResult(student_result=r, task=t) for r in results for t in tasks]
    )
    return len(results)


def calculate_student_result(student_result: StudentResult) -> dict:
    results = list(student_result.task_results.select_related("task"))
    total_tasks = student_result.exam.tasks.count()
    checked = sum(1 for r in results if r.score is not None)

    if checked == 0:
        return {
            "primary_score": None,
            "secondary_score": None,
            "checked_tasks": 0,
            "total_tasks": total_tasks,
            "is_complete": False,
        }

    primary = sum(r.score for r in results if r.score is not None)
    complete = total_tasks > 0 and checked == total_tasks
    secondary = student_result.exam.convert_primary_to_secondary(primary)

    return {
        "primary_score": primary,
        "secondary_score": secondary,
        "checked_tasks": checked,
        "total_tasks": total_tasks,
        "is_complete": complete,
    }
