from rest_framework import serializers

from school.models import SchoolClass, Student


class SchoolClassSerializer(serializers.ModelSerializer):
    teacher = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = SchoolClass
        fields = ("id", "name", "subject", "teacher", "created_at")
        read_only_fields = ("id", "teacher", "created_at")


class StudentSerializer(serializers.ModelSerializer):
    school_class = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Student
        fields = ("id", "first_name", "last_name", "middle_name", "school_class", "created_at")
        read_only_fields = ("id", "school_class", "created_at")
