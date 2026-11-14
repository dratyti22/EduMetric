from django.db import transaction
from rest_framework import serializers

from school.models import SchoolClass
from .models import Exam, ExamTemplate, ExamTask, StudentResult, TaskResult
from .services import create_exam, calculate_student_result, current_academic_year


class ExamTemplateTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamTemplate.tasks.field.model  # ExamTemplateTask
        fields = ("id", "number", "max_score")


class ScoreConversionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamTemplate.score_conversions.field.model
        fields = ("primary_score", "test_score")


class ExamTemplateSerializer(serializers.ModelSerializer):
    tasks = ExamTemplateTaskSerializer(many=True, read_only=True)
    task_count = serializers.IntegerField(read_only=True)
    max_primary_score = serializers.IntegerField(read_only=True)

    class Meta:
        model = ExamTemplate
        fields = (
            "id",
            "subject",
            "year",
            "title",
            "default_passing_secondary",
            "task_count",
            "max_primary_score",
            "tasks",
        )


class ExamTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamTask
        fields = ("id", "number", "max_score")


class ExamSerializer(serializers.ModelSerializer):
    tasks = ExamTaskSerializer(many=True, read_only=True)
    task_count = serializers.IntegerField(read_only=True)
    max_primary_score = serializers.IntegerField(read_only=True)
    school_class_name = serializers.CharField(
        source="school_class.name", read_only=True
    )

    class Meta:
        model = Exam
        fields = (
            "id",
            "title",
            "source",
            "variant",
            "school_class",
            "school_class_name",
            "template",
            "subject",
            "academic_year",
            "date",
            "status",
            "passing_score_secondary",
            "use_proportional_conversion",
            "task_count",
            "max_primary_score",
            "tasks",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "status",
            "task_count",
            "max_primary_score",
            "created_at",
            "updated_at",
        )


class ExamTaskInputSerializer(serializers.Serializer):
    number = serializers.IntegerField(min_value=1)
    max_score = serializers.IntegerField(min_value=1, max_value=50)


class ExamCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    source = serializers.CharField(max_length=255, required=False, allow_blank=True)
    variant = serializers.CharField(max_length=100, required=False, allow_blank=True)
    school_class = serializers.PrimaryKeyRelatedField(
        queryset=SchoolClass.objects.none()
    )
    subject = serializers.ChoiceField(choices=[])  # заполним в get_fields
    template = serializers.PrimaryKeyRelatedField(
        queryset=ExamTemplate.objects.all(), required=False, allow_null=True
    )
    tasks = ExamTaskInputSerializer(many=True, required=False)
    academic_year = serializers.CharField(max_length=20, required=False)
    date = serializers.DateField(required=False)
    passing_score_secondary = serializers.IntegerField(
        min_value=0, max_value=100, required=False
    )
    use_proportional_conversion = serializers.BooleanField(required=False, default=False)

    def get_fields(self):
        fields = super().get_fields()
        user = self.context["request"].user
        fields["school_class"].queryset = SchoolClass.objects.filter(teacher=user)
        from school.enum import Subject
        fields["subject"].choices = Subject.choices
        return fields

    def validate(self, attrs):
        template = attrs.get("template")
        tasks = attrs.get("tasks")
        subject = attrs["subject"]

        if not template and not tasks:
            raise serializers.ValidationError(
                "Укажите template или список tasks."
            )

        if template and template.subject != subject:
            raise serializers.ValidationError(
                {"template": "Предмет шаблона не совпадает с subject."}
            )

        if tasks:
            numbers = [t["number"] for t in tasks]
            if len(numbers) != len(set(numbers)):
                raise serializers.ValidationError(
                    {"tasks": "Номера заданий должны быть уникальными."}
                )

        return attrs

    def create(self, validated_data):
        return create_exam(**validated_data)


class TaskResultSerializer(serializers.ModelSerializer):
    task_id = serializers.UUIDField(source="task.id", read_only=True)
    task_number = serializers.IntegerField(source="task.number", read_only=True)
    max_score = serializers.IntegerField(source="task.max_score", read_only=True)

    class Meta:
        model = TaskResult
        fields = ("id", "task_id", "task_number", "max_score", "score")


class StudentResultSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_id = serializers.UUIDField(source="student.id", read_only=True)
    task_results = TaskResultSerializer(many=True, read_only=True)
    summary = serializers.SerializerMethodField()
    # Удобный словарь number -> score (как на фронте)
    scores_by_number = serializers.SerializerMethodField()

    class Meta:
        model = StudentResult
        fields = (
            "id",
            "student_id",
            "student_name",
            "task_results",
            "scores_by_number",
            "summary",
        )

    def get_student_name(self, obj):
        s = obj.student
        return " ".join(filter(None, [s.last_name, s.first_name, s.middle_name]))

    def get_summary(self, obj):
        return calculate_student_result(obj)

    def get_scores_by_number(self, obj):
        return {
            tr.task.number: tr.score
            for tr in obj.task_results.all()
            if tr.score is not None
        }


class ScoreInputSerializer(serializers.Serializer):
    # Можно передавать либо task_id, либо task_number
    task_id = serializers.UUIDField(required=False)
    task_number = serializers.IntegerField(required=False, min_value=1)
    score = serializers.IntegerField(min_value=0, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("task_id") and not attrs.get("task_number"):
            raise serializers.ValidationError(
                "Нужно указать task_id или task_number."
            )
        return attrs


class BulkScoreSerializer(serializers.Serializer):
    scores = ScoreInputSerializer(many=True)

    def validate_scores(self, value):
        # Проверка уникальности
        ids = [item.get("task_id") for item in value if item.get("task_id")]
        numbers = [item.get("task_number") for item in value if item.get("task_number")]
        if len(ids) != len(set(ids)) or len(numbers) != len(set(numbers)):
            raise serializers.ValidationError("Дубликаты заданий.")
        return value

    @transaction.atomic
    def save(self, **kwargs):
        student_result = self.context["student_result"]
        exam = student_result.exam

        if exam.status == Exam.Status.COMPLETED:
            raise serializers.ValidationError(
                "Завершённый пробник нельзя изменять."
            )

        submitted = self.validated_data["scores"]
        tasks_by_id = {t.id: t for t in exam.tasks.all()}
        tasks_by_number = {t.number: t for t in exam.tasks.all()}

        results_qs = TaskResult.objects.select_for_update().filter(
            student_result=student_result
        )
        results_by_task_id = {r.task_id: r for r in results_qs}

        updated = []
        for item in submitted:
            task = None
            if item.get("task_id"):
                task = tasks_by_id.get(item["task_id"])
            elif item.get("task_number"):
                task = tasks_by_number.get(item["task_number"])

            if not task:
                raise serializers.ValidationError("Задание не найдено.")

            result = results_by_task_id.get(task.id)
            if not result:
                raise serializers.ValidationError("Результат по заданию не найден.")

            score = item["score"]
            if score is not None and score > task.max_score:
                raise serializers.ValidationError(
                    {str(task.number): f"Балл превышает максимум ({task.max_score})."}
                )

            result.score = score
            updated.append(result)

        TaskResult.objects.bulk_update(updated, ["score"])

        if submitted and exam.status == Exam.Status.DRAFT:
            exam.status = Exam.Status.IN_PROGRESS
            exam.save(update_fields=["status", "updated_at"])

        return student_result
