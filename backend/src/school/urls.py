from django.urls import include, path
from rest_framework.routers import DefaultRouter
from school.views import ClassStudentDetailView, ClassStudentListCreatedView, SchoolClassView

router = DefaultRouter()
router.register("classes", SchoolClassView, basename="school")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "classes/<uuid:class_id>/students/",
        ClassStudentListCreatedView.as_view(),
        name="class-students",
    ),
    path("students/<uuid:pk>/", ClassStudentDetailView.as_view(), name="student-detail"),
]
