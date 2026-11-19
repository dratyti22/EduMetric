from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from exams.models import Exam
from exams.services import publish_exam, student_exam_queryset


class PublicationTests(SimpleTestCase):
    @patch("exams.services.sync_exam_students", return_value=1)
    def test_publication_syncs_students_and_opens_draft(self, sync):
        exam = Mock(status=Exam.Status.DRAFT)
        exam.tasks.count.return_value = 2
        self.assertEqual(publish_exam(exam), 1)
        sync.assert_called_once_with(exam)
        self.assertEqual(exam.status, Exam.Status.IN_PROGRESS)
        exam.save.assert_called_once_with(update_fields=["status", "updated_at"])

    @patch("exams.services.Exam.objects.filter")
    def test_student_list_only_contains_published_class_exams(self, filter_exams):
        user = Mock()
        student_exam_queryset(user)
        filter_exams.assert_called_once_with(
            status__in=(Exam.Status.IN_PROGRESS, Exam.Status.COMPLETED),
            school_class__students__user=user,
        )
