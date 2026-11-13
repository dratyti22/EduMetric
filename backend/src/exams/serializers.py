from django.db import transaction
from rest_framework import serializers
from school.models import SchoolClass
from .models import Exam, ExamTemplate, ExamTask, StudentResult, TaskResult
from .services import create_exam, calculate_student_result, current_exam_year


class ExamTemplateSerializer(serializers.ModelSerializer):
    task_count = serializers.SerializerMethodField()
    max_primary_score = serializers.SerializerMethodField()

    class Meta:
        model = ExamTemplate
        fields = ("id", "subject", "year", "task_count", "max_primary_score")

    def get_task_count(self, obj):
        return obj.tasks.count()

    def get_max_primary_score(self, obj):
        return sum(t.max_score for t in obj.tasks.all())


class ExamTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamTask
        fields = ("id", "number", "max_score")


class ExamSerializer(serializers.ModelSerializer):
    task_count = serializers.IntegerField(read_only=True)
    max_primary_score = serializers.IntegerField(read_only=True)

    class Meta:
        model = Exam
        fields = (
            "id",
            "title",
            "source",
            "variant",
            "school_class",
            "subject",
            "year",
            "date",
            "status",
            "task_count",
            "max_primary_score",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "school_class",
            "subject",
            "year",
            "status",
            "task_count",
            "max_primary_score",
            "created_at",
            "updated_at",
        )


class ExamCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    source = serializers.CharField(max_length=255, required=False, allow_blank=True)
    variant = serializers.CharField(max_length=100, required=False, allow_blank=True)
    school_class = serializers.PrimaryKeyRelatedField(queryset=SchoolClass.objects.none())
    year = serializers.IntegerField(min_value=2020,required=False, default=current_exam_year)
    date = serializers.DateField(required=False)

    def get_fields(self):
        fields = super().get_fields()
        fields["school_class"].queryset = SchoolClass.objects.filter(
            teacher=self.context["request"].user, subject="informatics"
        )
        return fields

    def validate(self, attrs):
        try:
            template = ExamTemplate.objects.get(
                subject=attrs["school_class"].subject, year=attrs["year"]
            )
        except ExamTemplate.DoesNotExist:
            raise serializers.ValidationError({"year": "Шаблон ЕГЭ за этот год не найден."})
        attrs["template"] = template
        return attrs

    def create(self, validated_data):
        validated_data.pop("year")
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
    task_results = TaskResultSerializer(many=True, read_only=True)
    summary = serializers.SerializerMethodField()

    class Meta:
        model = StudentResult
        fields = ("id", "student", "student_name", "task_results", "summary")

    def get_student_name(self, obj):
        s = obj.student
        return " ".join(filter(None, [s.last_name, s.first_name, s.middle_name]))

    def get_summary(self, obj):
        return calculate_student_result(obj)


class ScoreInputSerializer(serializers.Serializer):
    task_id = serializers.UUIDField()
    score = serializers.IntegerField(min_value=0, allow_null=True)


class BulkScoreSerializer(serializers.Serializer):
    scores = ScoreInputSerializer(many=True)

    def validate_scores(self, value):
        ids = [item["task_id"] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Одно задание передано несколько раз.")
        return value

    @transaction.atomic
    def save(self, **kwargs):
        student_result = self.context["student_result"]
        if student_result.exam.status == Exam.Status.COMPLETED:
            raise serializers.ValidationError("Завершённый пробник нельзя изменять.")
        submitted = self.validated_data["scores"]
        ids = [item["task_id"] for item in submitted]
        results = {
            r.task_id: r
            for r in TaskResult.objects.select_for_update()
            .select_related("task")
            .filter(student_result=student_result, task_id__in=ids)
        }
        if len(results) != len(ids):
            raise serializers.ValidationError("Одно или несколько заданий не найдены.")
        updated = []
        for item in submitted:
            result = results[item["task_id"]]
            score = item["score"]
            if score is not None and score > result.task.max_score:
                raise serializers.ValidationError(
                    {str(result.task.number): "Балл превышает максимум задания."}
                )
            result.score = score
            updated.append(result)
        TaskResult.objects.bulk_update(updated, ["score"])
        if submitted and student_result.exam.status == Exam.Status.DRAFT:
            student_result.exam.status = Exam.Status.IN_PROGRESS
            student_result.exam.save(update_fields=["status", "updated_at"])
        return student_result
