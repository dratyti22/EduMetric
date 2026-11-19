from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from exams.services import ClassAnalyticsDTO
from exams.views import ClassDynamicsView, ExamAnalyticsView


class AnalyticsViewTests(SimpleTestCase):
    @patch("exams.views.exam_queryset")
    @patch("exams.views.get_object_or_404")
    @patch("exams.views.get_exam_analytics")
    def test_serializes_dataclass_report(self, analytics, get_exam, queryset):
        analytics.return_value = ClassAnalyticsDTO(
            total_students=1,
            attended_students=1,
            avg_primary=7,
            avg_secondary=70,
            max_secondary=70,
            min_secondary=70,
            passing_threshold=40,
            passed_count=1,
            passed_percent=100,
            high_achievers_count=0,
            high_achievers_percent=0,
            score_distribution=[],
            task_solvability=[],
        )
        request = APIRequestFactory().get("/", {"threshold": 40})
        force_authenticate(request, user=SimpleNamespace(is_authenticated=True, is_teacher=True))
        response = ExamAnalyticsView.as_view()(request, pk="exam-id")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["avg_secondary"], 70)
        self.assertEqual(response.data["passed_percent"], 100)
        analytics.assert_called_once_with(get_exam.return_value, threshold=40)

    def test_students_cannot_access_class_reports(self):
        for view, kwargs in (
            (ExamAnalyticsView, {"pk": "exam-id"}),
            (ClassDynamicsView, {"class_id": "class-id"}),
        ):
            request = APIRequestFactory().get("/")
            force_authenticate(
                request,
                user=SimpleNamespace(is_authenticated=True, is_teacher=False, is_student=True),
            )
            self.assertEqual(view.as_view()(request, **kwargs).status_code, 403)
