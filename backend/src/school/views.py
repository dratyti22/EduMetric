from django.db.models import Count, QuerySet
from rest_framework import status
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from school.models import ClassJoinRequest, SchoolClass, Student
from school.permissions import IsStudent, IsTeacher
from school.serializers import (
    ClassJoinRequestSerializer,
    JoinClassSerializer,
    SchoolClassSerializer,
    StudentClassSerializer,
    StudentSerializer,
)
from school.services import (
    approve_join_request,
    create_school_class,
    join_class_by_code,
    reject_join_request,
)


class SchoolClassView(ModelViewSet):
    serializer_class = SchoolClassSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self) -> QuerySet:
        return SchoolClass.objects.filter(teacher=self.request.user).annotate(
            students_count=Count("students")
        )

    def perform_create(self, serializer) -> None:
        school_class = create_school_class(
            teacher=self.request.user,
            name=serializer.validated_data["name"],
            subject=serializer.validated_data["subject"],
        )
        serializer.instance = school_class


class ClassStudentListCreatedView(ListCreateAPIView):
    serializer_class = StudentSerializer
    permission_classes = [IsTeacher]

    def get_school_class(self):
        return get_object_or_404(SchoolClass, pk=self.kwargs["class_id"], teacher=self.request.user)

    def get_queryset(self) -> QuerySet:
        return Student.objects.filter(school_class=self.get_school_class())

    def perform_create(self, serializer) -> None:
        serializer.save(school_class=self.get_school_class())


class ClassStudentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = StudentSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self) -> QuerySet:
        return Student.objects.filter(school_class__teacher=self.request.user)


class MyClassesView(ListAPIView):
    serializer_class = StudentClassSerializer
    permission_classes = [IsStudent]

    def get_queryset(self) -> QuerySet:
        return SchoolClass.objects.filter(students__user=self.request.user).distinct()


class JoinClassView(APIView):
    permission_classes = [IsStudent]

    def post(self, request):
        serializer = JoinClassSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = join_class_by_code(user=request.user, code=serializer.validated_data["code"])

        payload = {
            "status": result["status"],
            "school_class": StudentClassSerializer(result["school_class"]).data,
        }
        http_status = status.HTTP_200_OK
        if result["status"] == "joined":
            payload["student"] = StudentSerializer(result["student"]).data
            http_status = status.HTTP_201_CREATED
        elif result["status"] == "already_member":
            payload["student"] = StudentSerializer(result["student"]).data
        else:
            payload["request"] = ClassJoinRequestSerializer(result["request"]).data
            http_status = status.HTTP_202_ACCEPTED
        return Response(payload, status=http_status)


class JoinRequestListView(ListAPIView):
    serializer_class = ClassJoinRequestSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self) -> QuerySet:
        qs = ClassJoinRequest.objects.filter(
            school_class__teacher=self.request.user
        ).select_related("user", "matched_student", "school_class")
        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)
        class_id = self.request.query_params.get("class_id")
        if class_id:
            qs = qs.filter(school_class_id=class_id)
        return qs


class JoinRequestApproveView(APIView):
    permission_classes = [IsTeacher]

    def post(self, request, pk):
        join_request = get_object_or_404(
            ClassJoinRequest.objects.select_related("matched_student", "school_class", "user"),
            pk=pk,
            school_class__teacher=request.user,
        )
        student = approve_join_request(join_request)
        return Response(StudentSerializer(student).data)


class JoinRequestRejectView(APIView):
    permission_classes = [IsTeacher]

    def post(self, request, pk):
        join_request = get_object_or_404(
            ClassJoinRequest, pk=pk, school_class__teacher=request.user
        )
        join_request = reject_join_request(join_request)
        return Response(ClassJoinRequestSerializer(join_request).data)
