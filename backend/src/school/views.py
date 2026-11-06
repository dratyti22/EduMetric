from django.db.models import QuerySet
from rest_framework.viewsets import ModelViewSet

from school.models import SchoolClass
from school.serializers import SchoolClassSerializer


class SchoolClassView(ModelViewSet):
    serializer_class = SchoolClassSerializer

    def get_queryset(self)->QuerySet:
        return SchoolClass.objects.filter(teacher=self.request.user)

    def perform_create(self, serializer) -> None:
        serializer.save(teacher=self.request.user)
