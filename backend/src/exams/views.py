from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Exam, ExamTemplate, StudentResult
from .serializers import (
    BulkScoreSerializer,
    ClassDynamicsItemSerializer,
    ExamAnalyticsSerializer,
    ExamCreateSerializer,
    ExamSerializer,
    ExamTaskSerializer,
    ExamTemplateSerializer,
    StudentHistoryItemSerializer,
    StudentResultSerializer,
)
from .services import (
    get_class_dynamics,
    get_exam_analytics,
    get_student_history,
    sync_exam_students,
)


def exam_queryset(user):
    return Exam.objects.filter(school_class__teacher=user)


class ExamTemplateListView(generics.ListAPIView):
    serializer_class = ExamTemplateSerializer

    def get_queryset(self):
        qs = ExamTemplate.objects.prefetch_related("tasks", "score_conversions")
        subject = self.request.query_params.get("subject")
        year = self.request.query_params.get("year")
        if subject:
            qs = qs.filter(subject=subject)
        if year:
            qs = qs.filter(year=year)
        return qs.order_by("-year", "subject")


class ExamListCreateView(generics.ListCreateAPIView):
    def get_queryset(self):
        qs = (
            exam_queryset(self.request.user)
            .select_related("school_class", "template")
            .prefetch_related("tasks")
        )
        class_id = self.request.query_params.get("class_id")
        if class_id:
            qs = qs.filter(school_class_id=class_id)
        return qs

    def get_serializer_class(self):
        return ExamCreateSerializer if self.request.method == "POST" else ExamSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        exam = serializer.save()
        return Response(ExamSerializer(exam).data, status=status.HTTP_201_CREATED)


class ExamDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExamSerializer

    def get_queryset(self):
        return exam_queryset(self.request.user).prefetch_related("tasks")

    def perform_update(self, serializer):
        if serializer.instance.status == Exam.Status.COMPLETED:
            raise serializers.ValidationError("Завершённый пробник нельзя редактировать.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.status == Exam.Status.COMPLETED:
            raise serializers.ValidationError("Завершённый пробник нельзя удалить.")
        instance.delete()


class ExamTaskListView(generics.ListAPIView):
    serializer_class = ExamTaskSerializer

    def get_queryset(self):
        exam = get_object_or_404(exam_queryset(self.request.user), pk=self.kwargs["exam_id"])
        return exam.tasks.all()


class ExamResultListView(generics.ListAPIView):
    serializer_class = StudentResultSerializer

    def get_queryset(self):
        exam = get_object_or_404(exam_queryset(self.request.user), pk=self.kwargs["exam_id"])
        return (
            StudentResult.objects.filter(exam=exam)
            .select_related("student", "exam", "exam__template")
            .prefetch_related("task_results__task")
            .order_by("student__last_name", "student__first_name")
        )


class StudentResultDetailView(generics.RetrieveAPIView):
    serializer_class = StudentResultSerializer

    def get_queryset(self):
        return (
            StudentResult.objects.filter(exam__school_class__teacher=self.request.user)
            .select_related("student", "exam", "exam__template")
            .prefetch_related("task_results__task")
        )


class StudentScoreUpdateView(APIView):
    def patch(self, request, pk):
        with transaction.atomic():
            result = get_object_or_404(
                StudentResult.objects.select_for_update().select_related("exam"),
                pk=pk,
                exam__school_class__teacher=request.user,
            )
            serializer = BulkScoreSerializer(data=request.data, context={"student_result": result})
            serializer.is_valid(raise_exception=True)
            serializer.save()

        result = get_object_or_404(
            StudentResult.objects.select_related(
                "student", "exam", "exam__template"
            ).prefetch_related("task_results__task"),
            pk=result.pk,
        )
        return Response(StudentResultSerializer(result).data)


class ExamSyncStudentsView(APIView):
    def post(self, request, pk):
        with transaction.atomic():
            exam = get_object_or_404(exam_queryset(request.user).select_for_update(), pk=pk)
            if exam.status == Exam.Status.COMPLETED:
                return Response({"detail": "Пробник уже завершён."}, status=400)
            added = sync_exam_students(exam)
        return Response({"added_students": added})


class ExamCompleteView(APIView):
    def post(self, request, pk):
        with transaction.atomic():
            exam = get_object_or_404(exam_queryset(request.user).select_for_update(), pk=pk)
            if exam.status == Exam.Status.COMPLETED:
                return Response({"detail": "Пробник уже завершён."}, status=400)
            results = StudentResult.objects.filter(exam=exam)
            if not results.exists():
                return Response({"detail": "В пробнике нет учеников."}, status=400)
            if exam.tasks.count() == 0:
                return Response({"detail": "В пробнике нет заданий."}, status=400)
            has_scores = results.filter(task_results__score__isnull=False).exists()
            if not has_scores:
                return Response({"detail": "Не выставлено ни одного балла."}, status=400)
            exam.status = Exam.Status.COMPLETED
            exam.save(update_fields=["status", "updated_at"])
        return Response({"id": str(exam.id), "status": exam.status})


class ExamAnalyticsView(APIView):
    """
    GET /api/exams/{exam_id}/analytics/?threshold=27
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        exam = get_object_or_404(
            exam_queryset(request.user).prefetch_related("tasks"),
            pk=pk,
        )
        threshold_param = request.query_params.get("threshold")
        threshold = int(threshold_param) if threshold_param is not None else None

        data = get_exam_analytics(exam, threshold=threshold)
        serializer = ExamAnalyticsSerializer(data.dict)
        return Response(serializer.data)


class ClassDynamicsView(APIView):
    """
    GET /api/classes/{class_id}/dynamics/
    Динамика средних баллов по пробникам класса.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, class_id):
        # Проверяем, что класс принадлежит учителю
        from school.models import SchoolClass

        get_object_or_404(SchoolClass, pk=class_id, teacher=request.user)

        limit = int(request.query_params.get("limit", 10))
        data = get_class_dynamics(class_id, request.user, limit=limit)
        serializer = ClassDynamicsItemSerializer(data, many=True)
        return Response(serializer.data)


class StudentHistoryView(APIView):
    """
    GET /api/students/{student_id}/history/
    История пробников ученика.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        data = get_student_history(student_id, request.user)
        serializer = StudentHistoryItemSerializer(data, many=True)
        return Response(serializer.data)
