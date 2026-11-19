from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase

from school.serializers import StudentClassSerializer


class StudentClassSerializerTests(SimpleTestCase):
    def test_counts_all_students_without_exposing_roster_or_join_code(self):
        students = Mock()
        students.count.return_value = 3
        school_class = SimpleNamespace(
            id="550e8400-e29b-41d4-a716-446655440000",
            name="11А",
            subject="math_profile",
            created_at=None,
            students=students,
            join_code="private-code",
        )
        data = StudentClassSerializer(school_class).data
        self.assertEqual(data["students_count"], 3)
        self.assertNotIn("join_code", data)
        self.assertNotIn("students", data)
