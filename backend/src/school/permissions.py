from rest_framework.permissions import BasePermission


class IsTeacher(BasePermission):
    message = "Доступно только учителю."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_teacher)


class IsStudent(BasePermission):
    message = "Доступно только ученику."

    def has_permission(self, request, view) -> bool:
        user = request.user
        return bool(user and user.is_authenticated and user.is_student)
