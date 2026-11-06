from rest_framework import serializers

from school.models import SchoolClass


class SchoolClassSerializer(serializers.ModelSerializer):
    teacher = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = SchoolClass
        fields = (
            "id",
            "name",
            "subject",
            "teacher",
            "created_at"
        )
        read_only_fields = ("id", "teacher", "created_at")
