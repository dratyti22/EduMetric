from collections import defaultdict
from dataclasses import dataclass

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

    # Ведомость сразу для всех, кто уже в классе. Кто вступит позже — попадёт при публикации.
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


def get_exam_analytics(exam: Exam, threshold: int | None = None) -> ClassAnalyticsDTO:
    from school.models import Student

    students = list(Student.objects.filter(school_class=exam.school_class))
    total_students = len(students)

    results = (
        StudentResult.objects.filter(exam=exam)
        .prefetch_related("task_results__task")
        .select_related("student")
    )

    scored = []
    for sr in results:
        calc = calculate_student_result(sr)
        if calc["primary_score"] is None:
            continue
        scored.append(
            {
                "primary": calc["primary_score"],
                "secondary": calc["secondary_score"] or 0,
            }
        )

    attended = len(scored)
    passing = threshold if threshold is not None else exam.passing_score_secondary

    empty_distribution = [
        {"range": "0–39", "count": 0, "percent": 0},
        {"range": "40–59", "count": 0, "percent": 0},
        {"range": "60–79", "count": 0, "percent": 0},
        {"range": "80–100", "count": 0, "percent": 0},
    ]
    empty_solvability = [
        {
            "task_number": t.number,
            "max_score": t.max_score,
            "avg_score": 0,
            "percent": 0,
        }
        for t in exam.tasks.all().order_by("number")
    ]

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
            score_distribution=empty_distribution,
            task_solvability=empty_solvability,
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
            "range": name,
            "count": cnt,
            "percent": round(cnt / attended * 100),
        }
        for name, cnt in buckets.items()
    ]

    # Решаемость
    task_scores: dict[int, list[int]] = defaultdict(list)
    task_max: dict[int, int] = {}
    for sr in results:
        for tr in sr.task_results.all():
            if tr.score is not None:
                task_scores[tr.task.number].append(tr.score)
                task_max[tr.task.number] = tr.task.max_score
    task_solvability = []
    for task in exam.tasks.all().order_by("number"):
        scores = task_scores.get(task.number, [])
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


def get_class_dynamics(class_id, user, limit: int = 10) -> list[dict]:
    """
    Динамика средних баллов по пробникам класса (от старых к новым).
    """
    exams = (
        Exam.objects.filter(school_class_id=class_id, school_class__teacher=user)
        .prefetch_related("tasks", "student_results__task_results")
        .order_by("date", "created_at")[:limit]
    )

    dynamics = []
    for exam in exams:
        analytics = get_exam_analytics(exam)
        dynamics.append(
            {
                "exam_id": str(exam.id),
                "title": exam.title,
                "date": exam.date.isoformat(),
                "subject": exam.subject,
                "avg_primary": analytics.avg_primary,
                "avg_secondary": analytics.avg_secondary,
                "attended_students": analytics.attended_students,
                "passed_percent": analytics.passed_percent,
                "max_primary_score": exam.max_primary_score,
            }
        )
    return dynamics


def publish_exam(exam: Exam) -> int:
    """Открывает пробник ученикам и создаёт им пустые ведомости."""
    if exam.status == Exam.Status.COMPLETED:
        raise ValidationError("Завершённый пробник нельзя опубликовать.")
    if exam.tasks.count() == 0:
        raise ValidationError("В пробнике нет заданий.")

    added = sync_exam_students(exam)
    if exam.status == Exam.Status.DRAFT:
        exam.status = Exam.Status.IN_PROGRESS
        exam.save(update_fields=["status", "updated_at"])
    return added


def student_exam_queryset(user):
    return Exam.objects.filter(
        status__in=(Exam.Status.IN_PROGRESS, Exam.Status.COMPLETED),
        school_class__students__user=user,
    ).distinct()


def get_linked_student(user, school_class_id):
    return Student.objects.filter(user=user, school_class_id=school_class_id).first()


def get_student_history(student_id, user) -> list[dict]:
    """
    История пробников конкретного ученика.
    """
    from school.models import Student

    if getattr(user, "is_student", False):
        student = Student.objects.filter(id=student_id, user=user).first()
    else:
        student = Student.objects.filter(id=student_id, school_class__teacher=user).first()
    if not student:
        return []

    results = (
        StudentResult.objects.filter(student=student)
        .select_related("exam", "exam__template")
        .prefetch_related("task_results__task")
        .order_by("exam__date", "exam__created_at")
    )

    history = []
    for sr in results:
        calc = calculate_student_result(sr)
        if calc["primary_score"] is None:
            continue

        scores = {tr.task.number: tr.score for tr in sr.task_results.all() if tr.score is not None}

        history.append(
            {
                "test_id": str(sr.exam.id),
                "title": sr.exam.title,
                "date": sr.exam.date.isoformat(),
                "subject": sr.exam.subject,
                "primary_score": calc["primary_score"],
                "secondary_score": calc["secondary_score"],
                "max_primary_score": sr.exam.max_primary_score,
                "scores": scores,
                "is_complete": calc["is_complete"],
            }
        )
    return history
