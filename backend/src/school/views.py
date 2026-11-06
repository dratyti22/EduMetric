from django.db.models import QuerySet
from rest_framework.generics import (
    DestroyAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    get_object_or_404,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.viewsets import ModelViewSet
from school.models import SchoolClass, Student
from school.serializers import SchoolClassSerializer, StudentSerializer


class SchoolClassView(ModelViewSet):
    serializer_class = SchoolClassSerializer

    def get_queryset(self) -> QuerySet:
        return SchoolClass.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer) -> None:
        serializer.save(teacher=self.request.user)


class ClassStudentListCreatedView(ListCreateAPIView):
    serializer_class = StudentSerializer

    def get_school_class(self):
        return get_object_or_404(SchoolClass, pk=self.kwargs["class_id"], teacher=self.request.user)

    def get_queryset(self) -> QuerySet:
        return Student.objects.filter(school_class=self.get_school_class())

    def perform_create(self, serializer) -> None:
        serializer.save(school_class=self.get_school_class())


class ClassStudentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = StudentSerializer

    def get_queryset(self) -> QuerySet:
        return Student.objects.filter(
            school_class__teacher=self.request.user
        )
