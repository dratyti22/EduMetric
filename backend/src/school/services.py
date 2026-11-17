from django.db import IntegrityError, transaction
from rest_framework.exceptions import ValidationError

from school.codes import generate_join_code
from school.models import ClassJoinRequest, SchoolClass, Student


def normalize_name(value: str | None) -> str:
    return (value or "").strip().casefold()


def names_match(student: Student, user) -> bool:
    return (
        normalize_name(student.last_name) == normalize_name(user.last_name)
        and normalize_name(student.first_name) == normalize_name(user.first_name)
        and normalize_name(student.middle_name) == normalize_name(user.middle_name)
    )


def generate_unique_join_code() -> str:
    for _ in range(20):
        code = generate_join_code()
        if not SchoolClass.objects.filter(join_code=code).exists():
            return code
    raise ValidationError("Не удалось сгенерировать уникальный код класса.")


def find_manual_match(school_class: SchoolClass, user) -> Student | None:
    candidates = Student.objects.filter(school_class=school_class, user__isnull=True)
    for student in candidates:
        if names_match(student, user):
            return student
    return None


@transaction.atomic
def join_class_by_code(*, user, code: str) -> dict:
    if not user.is_student:
        raise ValidationError("В класс по коду может вступить только ученик.")

    normalized = (code or "").strip()
    school_class = SchoolClass.objects.filter(join_code=normalized).first()
    if school_class is None:
        raise ValidationError({"code": "Класс с таким кодом не найден."})

    existing = Student.objects.filter(school_class=school_class, user=user).first()
    if existing is not None:
        return {"status": "already_member", "school_class": school_class, "student": existing}

    pending = ClassJoinRequest.objects.filter(
        school_class=school_class,
        user=user,
        status=ClassJoinRequest.Status.PENDING,
    ).first()
    if pending is not None:
        return {"status": "pending", "school_class": school_class, "request": pending}

    match = find_manual_match(school_class, user)
    if match is not None:
        join_request = ClassJoinRequest.objects.create(
            school_class=school_class,
            user=user,
            matched_student=match,
        )
        return {"status": "pending", "school_class": school_class, "request": join_request}

    student = Student.objects.create(
        school_class=school_class,
        user=user,
        first_name=user.first_name,
        last_name=user.last_name,
        middle_name=user.middle_name or "",
    )
    return {"status": "joined", "school_class": school_class, "student": student}


def enroll_student_in_open_exams(student: Student) -> None:
    """Подключает ученика к уже опубликованным пробникам класса."""
    from exams.models import Exam
    from exams.services import sync_exam_students

    exams = Exam.objects.filter(
        school_class=student.school_class,
        status=Exam.Status.IN_PROGRESS,
    )
    for exam in exams:
        sync_exam_students(exam)


@transaction.atomic
def approve_join_request(join_request: ClassJoinRequest) -> Student:
    if join_request.status != ClassJoinRequest.Status.PENDING:
        raise ValidationError("Запрос уже обработан.")

    locked = ClassJoinRequest.objects.select_for_update().get(pk=join_request.pk)
    student = locked.matched_student
    if student is None or student.user_id is not None:
        raise ValidationError("Карточка ученика уже привязана или удалена.")
    if student.school_class_id != locked.school_class_id:
        raise ValidationError("Карточка ученика больше не относится к этому классу.")

    user = locked.user
    if Student.objects.filter(school_class=locked.school_class, user=user).exists():
        raise ValidationError("Ученик уже состоит в этом классе.")

    student.user = user
    student.save(update_fields=["user"])
    locked.status = ClassJoinRequest.Status.APPROVED
    locked.save(update_fields=["status"])

    ClassJoinRequest.objects.filter(
        school_class=locked.school_class,
        user=user,
        status=ClassJoinRequest.Status.PENDING,
    ).exclude(pk=locked.pk).update(status=ClassJoinRequest.Status.REJECTED)

    enroll_student_in_open_exams(student)
    return student


@transaction.atomic
def reject_join_request(join_request: ClassJoinRequest) -> ClassJoinRequest:
    if join_request.status != ClassJoinRequest.Status.PENDING:
        raise ValidationError("Запрос уже обработан.")

    locked = ClassJoinRequest.objects.select_for_update().get(pk=join_request.pk)
    locked.status = ClassJoinRequest.Status.REJECTED
    locked.save(update_fields=["status"])
    return locked


def create_school_class(*, teacher, name: str, subject: str) -> SchoolClass:
    last_error: IntegrityError | None = None
    for _ in range(5):
        try:
            return SchoolClass.objects.create(
                teacher=teacher,
                name=name,
                subject=subject,
                join_code=generate_unique_join_code(),
            )
        except IntegrityError as exc:
            last_error = exc
    raise ValidationError("Не удалось создать класс.") from last_error
