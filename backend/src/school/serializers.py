from rest_framework import serializers

from school.models import ClassJoinRequest, SchoolClass, Student


class SchoolClassSerializer(serializers.ModelSerializer):
    teacher = serializers.PrimaryKeyRelatedField(read_only=True)
    students_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = SchoolClass
        fields = (
            "id",
            "name",
            "subject",
            "teacher",
            "join_code",
            "students_count",
            "created_at",
        )
        read_only_fields = ("id", "teacher", "join_code", "students_count", "created_at")


class StudentClassSerializer(serializers.ModelSerializer):
    """Класс глазами ученика: без кода вступления."""

    class Meta:
        model = SchoolClass
        fields = ("id", "name", "subject", "created_at")


class StudentSerializer(serializers.ModelSerializer):
    school_class = serializers.PrimaryKeyRelatedField(read_only=True)
    is_linked = serializers.BooleanField(read_only=True)

    class Meta:
        model = Student
        fields = (
            "id",
            "first_name",
            "last_name",
            "middle_name",
            "school_class",
            "is_linked",
            "created_at",
        )
        read_only_fields = ("id", "school_class", "is_linked", "created_at")


class JoinClassSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=16)


class ClassJoinRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    user_email = serializers.EmailField(source="user.email", read_only=True)
    matched_student_name = serializers.SerializerMethodField()
    class_name = serializers.CharField(source="school_class.name", read_only=True)

    class Meta:
        model = ClassJoinRequest
        fields = (
            "id",
            "school_class",
            "class_name",
            "user",
            "user_email",
            "user_name",
            "matched_student",
            "matched_student_name",
            "status",
            "created_at",
        )
        read_only_fields = fields

    def get_user_name(self, obj):
        return " ".join(
            filter(None, [obj.user.last_name, obj.user.first_name, obj.user.middle_name])
        )

    def get_matched_student_name(self, obj):
        student = obj.matched_student
        if student is None:
            return ""
        return " ".join(filter(None, [student.last_name, student.first_name, student.middle_name]))
