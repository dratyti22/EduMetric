from dataclasses import dataclass
from typing import Optional

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


@dataclass
class ClassAnalyticsDTO:
    total_students: int
    attended_students: int
    avg_primary: float
    avg_secondary: float
    max_secondary: int
    min_secondary: int
    passing_threshold: int
    passed_count: int
    passed_percent: int
    high_achievers_count: int
    high_achievers_percent: int
    score_distribution: list[dict]
    task_solvability: list[dict]


def get_exam_analytics(exam: Exam, threshold: Optional[int] = None) -> ClassAnalyticsDTO:
    from school.models import Student

    students = list(Student.objects.filter(school_class=exam.school_class))
    total_students = len(students)

    # Все результаты с хотя бы одним выставленным баллом
    results = (
        StudentResult.objects.filter(exam=exam)
        .prefetch_related("task_results__task")
        .select_related("student")
    )

    # Считаем primary/secondary для каждого ученика
    scored = []
    for sr in results:
        calc = calculate_student_result(sr)
        if calc["primary_score"] is None:
            continue  # нет ни одного балла — считаем неявка
        scored.append(
            {
                "primary": calc["primary_score"],
                "secondary": calc["secondary_score"] or 0,
                "is_complete": calc["is_complete"],
            }
        )

    attended = len(scored)
    passing = threshold if threshold is not None else exam.passing_score_secondary

    if attended == 0:
        return ClassAnalyticsDTO(
            total_students=total_students,
            attended_students=0,
            avg_primary=0,
            avg_secondary=0,
            max_secondary=0,
            min_secondary=0,
            passing_threshold=passing,
            passed_count=0,
            passed_percent=0,
            high_achievers_count=0,
            high_achievers_percent=0,
            score_distribution=[
                {"range": "0–39", "count": 0, "percent": 0},
                {"range": "40–59", "count": 0, "percent": 0},
                {"range": "60–79", "count": 0, "percent": 0},
                {"range": "80–100", "count": 0, "percent": 0},
            ],
            task_solvability=[
                {
                    "task_number": t.number,
                    "max_score": t.max_score,
                    "avg_score": 0,
                    "percent": 0,
                }
                for t in exam.tasks.all()
            ],
        )

    primaries = [s["primary"] for s in scored]
    secondaries = [s["secondary"] for s in scored]

    avg_primary = round(sum(primaries) / attended, 1)
    avg_secondary = round(sum(secondaries) / attended, 1)
    max_sec = max(secondaries)
    min_sec = min(secondaries)

    passed_count = sum(1 for s in secondaries if s >= passing)
    passed_percent = round(passed_count / attended * 100)

    high_count = sum(1 for s in secondaries if s >= 80)
    high_percent = round(high_count / attended * 100)

    # Распределение
    buckets = {"0–39": 0, "40–59": 0, "60–79": 0, "80–100": 0}
    for v in secondaries:
        if v < 40:
            buckets["0–39"] += 1
        elif v < 60:
            buckets["40–59"] += 1
        elif v < 80:
            buckets["60–79"] += 1
        else:
            buckets["80–100"] += 1

    score_distribution = [
        {
            "range": range_name,
            "count": count,
            "percent": round(count / attended * 100),
        }
        for range_name, count in buckets.items()
    ]

    # Решаемость заданий
    task_solvability = []
    for task in exam.tasks.all().order_by("number"):
        scores = [
            tr.score
            for sr in results
            for tr in sr.task_results.all()
            if tr.task_id == task.id and tr.score is not None
        ]
        if not scores:
            task_solvability.append(
                {
                    "task_number": task.number,
                    "max_score": task.max_score,
                    "avg_score": 0,
                    "percent": 0,
                }
            )
            continue

        avg_score = round(sum(scores) / len(scores), 2)
        max_possible = task.max_score * len(scores)
        percent = round(sum(scores) / max_possible * 100) if max_possible else 0

        task_solvability.append(
            {
                "task_number": task.number,
                "max_score": task.max_score,
                "avg_score": avg_score,
                "percent": percent,
            }
        )

    return ClassAnalyticsDTO(
        total_students=total_students,
        attended_students=attended,
        avg_primary=avg_primary,
        avg_secondary=avg_secondary,
        max_secondary=max_sec,
        min_secondary=min_sec,
        passing_threshold=passing,
        passed_count=passed_count,
        passed_percent=passed_percent,
        high_achievers_count=high_count,
        high_achievers_percent=high_percent,
        score_distribution=score_distribution,
        task_solvability=task_solvability,
    )
