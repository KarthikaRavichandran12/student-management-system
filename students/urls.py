from django.urls import path

from . import views

app_name = "students"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("students/", views.student_list, name="student_list"),
    path("students/add/", views.student_create, name="student_create"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),
    path("students/<int:pk>/edit/", views.student_update, name="student_update"),
    path("students/<int:pk>/delete/", views.student_delete, name="student_delete"),
    path("courses/", views.course_list, name="course_list"),
    path("courses/add/", views.course_create, name="course_create"),
    path("courses/<int:pk>/edit/", views.course_update, name="course_update"),
    path("courses/<int:pk>/delete/", views.course_delete, name="course_delete"),
    path("attendance/", views.attendance_list, name="attendance_list"),
    path("attendance/add/", views.attendance_create, name="attendance_create"),
    path(
        "attendance/mark/", views.attendance_bulk_mark, name="attendance_bulk_mark"
    ),
    path(
        "attendance/<int:pk>/edit/", views.attendance_update, name="attendance_update"
    ),
    path(
        "attendance/<int:pk>/delete/", views.attendance_delete, name="attendance_delete"
    ),
    path("exams/", views.exam_list, name="exam_list"),
    path("exams/add/", views.exam_create, name="exam_create"),
    path("exams/<int:pk>/edit/", views.exam_update, name="exam_update"),
    path("exams/<int:pk>/delete/", views.exam_delete, name="exam_delete"),
    path("exams/<int:pk>/marks/", views.marks_entry, name="marks_entry"),
    path("exams/<int:pk>/results/", views.exam_results, name="exam_results"),
    path("marks/add/<int:student_pk>/", views.mark_create, name="mark_create"),
    path("marks/<int:pk>/edit/", views.mark_update, name="mark_update"),
    path("marks/<int:pk>/delete/", views.mark_delete, name="mark_delete"),
    path("results/", views.results_list, name="results_list"),
    path("results/<int:pk>/", views.student_results, name="student_results"),
]
