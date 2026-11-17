from django.urls import include, path
from rest_framework.routers import DefaultRouter

from school.views import (
    ClassStudentDetailView,
    ClassStudentListCreatedView,
    JoinClassView,
    JoinRequestApproveView,
    JoinRequestListView,
    JoinRequestRejectView,
    MyClassesView,
    SchoolClassView,
)

router = DefaultRouter()
router.register("classes", SchoolClassView, basename="school")

urlpatterns = [
    path("classes/join/", JoinClassView.as_view(), name="class-join"),
    path("classes/mine/", MyClassesView.as_view(), name="my-classes"),
    path("join-requests/", JoinRequestListView.as_view(), name="join-requests"),
    path(
        "join-requests/<uuid:pk>/approve/",
        JoinRequestApproveView.as_view(),
        name="join-request-approve",
    ),
    path(
        "join-requests/<uuid:pk>/reject/",
        JoinRequestRejectView.as_view(),
        name="join-request-reject",
    ),
    path("", include(router.urls)),
    path(
        "classes/<uuid:class_id>/students/",
        ClassStudentListCreatedView.as_view(),
        name="class-students",
    ),
    path("students/<uuid:pk>/", ClassStudentDetailView.as_view(), name="student-detail"),
]
