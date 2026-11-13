from django.contrib import admin
from exams.models import (
    Exam,
    ExamTask,
    ExamTemplate,
    ExamTemplateTask,
    ScoreConversion,
    StudentResult,
    TaskResult,
)


class ExamTemplateTaskInline(admin.TabularInline):
    model = ExamTemplateTask
    extra = 0


class ScoreConversionInline(admin.TabularInline):
    model = ScoreConversion
    extra = 0


@admin.register(ExamTemplate)
class ExamTemplateAdmin(admin.ModelAdmin):
    list_display = ("subject", "year")
    list_filter = ("subject", "year")
    inlines = [ExamTemplateTaskInline, ScoreConversionInline]


class ExamTaskInline(admin.TabularInline):
    model = ExamTask
    extra = 0
    readonly_fields = ("number", "max_score")
    can_delete = False


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("title", "school_class", "subject", "year", "status", "date")
    list_filter = ("subject", "year", "status")
    search_fields = ("title",)
    inlines = [ExamTaskInline]


@admin.register(StudentResult)
class StudentResultAdmin(admin.ModelAdmin):
    list_display = ("student", "exam")


@admin.register(TaskResult)
class TaskResultAdmin(admin.ModelAdmin):
    list_display = ("student_result", "task", "score")
