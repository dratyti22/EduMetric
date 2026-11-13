from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from school.models import Student
from .models import Exam, ExamTask, StudentResult, TaskResult, ScoreConversion


@transaction.atomic
def create_exam(*, school_class, template, title, source="", variant="", date=None):
    template_tasks = list(template.tasks.all())
    if not template_tasks:
        raise ValidationError("Шаблон ЕГЭ не содержит заданий.")
    if school_class.subject != template.subject:
        raise ValidationError("Предмет класса не соответствует шаблону.")
    exam = Exam.objects.create(
        title=title,
        source=source,
        variant=variant,
        school_class=school_class,
        template=template,
        subject=template.subject,
        year=template.year,
        **({"date": date} if date else {}),
    )
    tasks = ExamTask.objects.bulk_create(
        [ExamTask(exam=exam, number=t.number, max_score=t.max_score) for t in template_tasks]
    )
    students = list(Student.objects.filter(school_class=school_class))
    results = StudentResult.objects.bulk_create(
        [StudentResult(exam=exam, student=s) for s in students]
    )
    TaskResult.objects.bulk_create(
        [TaskResult(student_result=r, task=t) for r in results for t in tasks]
    )
    return exam


@transaction.atomic
def sync_exam_students(exam):
    existing_ids = StudentResult.objects.filter(exam=exam).values_list("student_id", flat=True)
    students = Student.objects.filter(school_class=exam.school_class).exclude(id__in=existing_ids)
    results = StudentResult.objects.bulk_create(
        [StudentResult(exam=exam, student=s) for s in students]
    )
    tasks = list(exam.tasks.all())
    TaskResult.objects.bulk_create(
        [TaskResult(student_result=r, task=t) for r in results for t in tasks]
    )
    return len(results)


def calculate_student_result(student_result):
    results = list(student_result.task_results.select_related("task"))
    total_tasks = student_result.exam.tasks.count()
    checked = sum(r.score is not None for r in results)

    if checked == 0:
        return {
            "primary_score": None,
            "test_score": None,
            "checked_tasks": 0,
            "total_tasks": total_tasks,
            "is_complete": False,
        }

    primary = sum(r.score for r in results if r.score is not None)
    complete = total_tasks > 0 and checked == total_tasks

    test_score = (
        ScoreConversion.objects.filter(template=student_result.exam.template, primary_score=primary)
        .values_list("test_score", flat=True)
        .first()
    )

    return {
        "primary_score": primary,
        "test_score": test_score,
        "checked_tasks": checked,
        "total_tasks": total_tasks,
        "is_complete": complete,
    }

def current_exam_year() -> int:
    today = timezone.localdate()
    return today.year+1 if today.month>=9 else today.year
