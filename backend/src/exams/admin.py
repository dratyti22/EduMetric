from django.contrib import admin
from .models import (
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
    extra = 1
    ordering = ("number",)


class ScoreConversionInline(admin.TabularInline):
    model = ScoreConversion
    extra = 5
    ordering = ("primary_score",)


@admin.register(ExamTemplate)
class ExamTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "year",
        "title",
        "default_passing_secondary",
        "task_count_display",
        "max_primary_display",
    )
    list_filter = ("subject", "year")
    search_fields = ("title",)
    inlines = [ExamTemplateTaskInline, ScoreConversionInline]

    @admin.display(description="Заданий")
    def task_count_display(self, obj):
        return obj.task_count

    @admin.display(description="Макс. первичный")
    def max_primary_display(self, obj):
        return obj.max_primary_score


class ExamTaskInline(admin.TabularInline):
    model = ExamTask
    extra = 0
    ordering = ("number",)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "school_class",
        "subject",
        "date",
        "status",
        "passing_score_secondary",
    )
    list_filter = ("subject", "status", "date")
    search_fields = ("title",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [ExamTaskInline]


@admin.register(StudentResult)
class StudentResultAdmin(admin.ModelAdmin):
    list_display = ("student", "exam", "updated_at")
    list_filter = ["exam__subject", "exam__status"]


@admin.register(TaskResult)
class TaskResultAdmin(admin.ModelAdmin):
    list_display = ("student_result", "task", "score")
