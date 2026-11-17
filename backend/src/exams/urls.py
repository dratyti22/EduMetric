from django.urls import path

from exams.views import (
    ClassDynamicsView,
    ExamAnalyticsView,
    ExamCompleteView,
    ExamDetailView,
    ExamListCreateView,
    ExamPublishView,
    ExamResultListView,
    ExamSyncStudentsView,
    ExamTaskListView,
    ExamTemplateListView,
    MyExamListView,
    MyExamResultView,
    MyExamScoreUpdateView,
    StudentHistoryView,
    StudentResultDetailView,
    StudentScoreUpdateView,
)

urlpatterns = [
    path("exam-templates/", ExamTemplateListView.as_view(), name="exam-templates"),
    path("exams/", ExamListCreateView.as_view(), name="exam-list-create"),
    path("exams/mine/", MyExamListView.as_view(), name="my-exams"),
    path("exams/mine/<uuid:pk>/", MyExamResultView.as_view(), name="my-exam-result"),
    path(
        "exams/mine/<uuid:pk>/scores/",
        MyExamScoreUpdateView.as_view(),
        name="my-exam-scores",
    ),
    path("exams/<uuid:pk>/", ExamDetailView.as_view(), name="exam-detail"),
    path("exams/<uuid:exam_id>/tasks/", ExamTaskListView.as_view(), name="exam-tasks"),
    path(
        "exams/<uuid:exam_id>/results/",
        ExamResultListView.as_view(),
        name="exam-results",
    ),
    path(
        "exams/<uuid:pk>/sync-students/",
        ExamSyncStudentsView.as_view(),
        name="exam-sync-students",
    ),
    path(
        "exams/<uuid:pk>/publish/",
        ExamPublishView.as_view(),
        name="exam-publish",
    ),
    path(
        "exams/<uuid:pk>/complete/",
        ExamCompleteView.as_view(),
        name="exam-complete",
    ),
    path(
        "results/<uuid:pk>/",
        StudentResultDetailView.as_view(),
        name="student-result-detail",
    ),
    path(
        "results/<uuid:pk>/scores/",
        StudentScoreUpdateView.as_view(),
        name="student-score-update",
    ),
    path(
        "exams/<uuid:pk>/analytics/",
        ExamAnalyticsView.as_view(),
        name="exam-analytics",
    ),
    path(
        "classes/<uuid:class_id>/dynamics/",
        ClassDynamicsView.as_view(),
        name="class-dynamics",
    ),
    path(
        "students/<uuid:student_id>/history/",
        StudentHistoryView.as_view(),
        name="student-history",
    ),
]
