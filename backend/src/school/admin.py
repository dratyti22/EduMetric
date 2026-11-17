from django.contrib import admin

from school.models import ClassJoinRequest, SchoolClass, Student


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "teacher", "join_code", "created_at")
    search_fields = ("name", "join_code")
    readonly_fields = ("join_code",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("last_name", "first_name", "school_class", "user", "created_at")
    search_fields = ("last_name", "first_name", "user__email")
    list_filter = ("school_class",)


@admin.register(ClassJoinRequest)
class ClassJoinRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "school_class", "matched_student", "status", "created_at")
    list_filter = ("status",)
