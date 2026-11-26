from django.contrib import admin

from .models import AttendanceRecord, Course, Exam, Mark, Student


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "created_at")
    search_fields = ("name", "code")
    list_filter = ("created_at",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("name", "roll_number", "course", "email", "created_at")
    search_fields = ("name", "roll_number", "email")
    list_filter = ("course", "created_at")
    list_select_related = ("course",)


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("student", "date", "status")
    search_fields = ("student__name", "student__roll_number")
    list_filter = ("status", "date", "student__course")
    list_select_related = ("student",)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("name", "course", "exam_date", "max_marks")
    search_fields = ("name", "course__name")
    list_filter = ("course", "exam_date")
    list_select_related = ("course",)


@admin.register(Mark)
class MarkAdmin(admin.ModelAdmin):
    list_display = ("student", "exam", "marks_obtained")
    search_fields = ("student__name", "student__roll_number", "exam__name")
    list_filter = ("exam__course", "exam")
    list_select_related = ("student", "exam")
