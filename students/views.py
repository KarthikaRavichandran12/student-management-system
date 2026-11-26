from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    AttendanceBulkForm,
    AttendanceRecordForm,
    CourseForm,
    ExamForm,
    MarkForm,
    MarksEntryForm,
    StudentForm,
)
from .models import (
    AttendanceRecord,
    Course,
    Exam,
    Mark,
    PASS_PERCENTAGE,
    Student,
    grade_for_percentage,
)


def login_view(request):
    """Authenticate an administrator and start a session."""
    if request.user.is_authenticated:
        return redirect("students:dashboard")

    next_url = request.GET.get("next", "") or request.POST.get("next", "")
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            messages.success(request, f"Welcome back, {user.get_username()}!")
            return redirect("students:dashboard")
    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "students/login.html",
        {"form": form, "next": next_url},
    )


@require_POST
def logout_view(request):
    """End the current administrator session."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("students:login")


@login_required
def dashboard(request):
    """Show headline numbers and the most recently added students."""
    context = {
        "total_students": Student.objects.count(),
        "total_courses": Course.objects.count(),
        "recent_students": Student.objects.select_related("course").order_by(
            "-created_at"
        )[:5],
        "courses": Course.objects.annotate(student_count=Count("students")).order_by(
            "name"
        ),
    }
    return render(request, "students/dashboard.html", context)


@login_required
def student_list(request):
    """List students with search, course filtering and pagination."""
    students = Student.objects.select_related("course").all()
    query = request.GET.get("q", "").strip()
    course_id = request.GET.get("course", "").strip()

    if query:
        students = students.filter(
            Q(name__icontains=query)
            | Q(roll_number__icontains=query)
            | Q(email__icontains=query)
            | Q(course__name__icontains=query)
        )
    if course_id.isdigit():
        students = students.filter(course_id=int(course_id))

    page_obj = Paginator(students, 10).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    return render(
        request,
        "students/student_list.html",
        {
            "page_obj": page_obj,
            "students": page_obj.object_list,
            "query": query,
            "course_id": course_id,
            "courses": Course.objects.all(),
            "querystring": params.urlencode(),
        },
    )


@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student.objects.select_related("course"), pk=pk)
    marks = student.marks.select_related("exam", "exam__course").all()
    obtained = sum((mark.marks_obtained for mark in marks), Decimal("0"))
    maximum = sum((mark.exam.max_marks for mark in marks), Decimal("0"))
    percentage = obtained / maximum * 100 if maximum else None
    return render(
        request,
        "students/student_detail.html",
        {
            "student": student,
            "attendance": student.attendance_summary(),
            "marks": marks,
            "obtained_marks": obtained,
            "maximum_marks": maximum,
            "percentage": percentage,
            "grade": grade_for_percentage(percentage),
        },
    )


@login_required
def student_create(request):
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(request, f"Added student {student.name}.")
            return redirect("students:student_detail", pk=student.pk)
    else:
        form = StudentForm()

    return render(
        request,
        "students/student_form.html",
        {
            "form": form,
            "title": "Add student",
            "submit_label": "Save student",
            "has_courses": Course.objects.exists(),
        },
    )


@login_required
def student_update(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            student = form.save()
            messages.success(request, f"Updated student {student.name}.")
            return redirect("students:student_detail", pk=student.pk)
    else:
        form = StudentForm(instance=student)

    return render(
        request,
        "students/student_form.html",
        {
            "form": form,
            "student": student,
            "title": "Edit student",
            "submit_label": "Save changes",
            "has_courses": Course.objects.exists(),
        },
    )


@login_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        name = student.name
        student.delete()
        messages.success(request, f"Deleted student {name}.")
        return redirect("students:student_list")

    return render(
        request,
        "students/student_confirm_delete.html",
        {"student": student},
    )


@login_required
def course_list(request):
    query = request.GET.get("q", "").strip()
    courses = Course.objects.annotate(student_count=Count("students")).all()
    if query:
        courses = courses.filter(
            Q(name__icontains=query) | Q(code__icontains=query)
        )
    return render(
        request,
        "students/course_list.html",
        {"courses": courses, "query": query},
    )


@login_required
def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, f"Added course {course.name}.")
            return redirect("students:course_list")
    else:
        form = CourseForm()

    return render(
        request,
        "students/course_form.html",
        {"form": form, "title": "Add course", "submit_label": "Save course"},
    )


@login_required
def course_update(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            course = form.save()
            messages.success(request, f"Updated course {course.name}.")
            return redirect("students:course_list")
    else:
        form = CourseForm(instance=course)

    return render(
        request,
        "students/course_form.html",
        {
            "form": form,
            "course": course,
            "title": "Edit course",
            "submit_label": "Save changes",
        },
    )


@login_required
def course_delete(request, pk):
    course = get_object_or_404(
        Course.objects.annotate(student_count=Count("students")), pk=pk
    )
    if request.method == "POST":
        name = course.name
        student_count = course.students.count()
        course.delete()
        messages.success(
            request,
            f"Deleted course {name}"
            + (f" and its {student_count} student(s)." if student_count else "."),
        )
        return redirect("students:course_list")

    return render(
        request,
        "students/course_confirm_delete.html",
        {"course": course},
    )


def _querystring_without_page(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


# ---------------------------------------------------------------------------
# Attendance tracking
# ---------------------------------------------------------------------------


@login_required
def attendance_list(request):
    """List attendance records with course, student, status and date filters."""
    records = AttendanceRecord.objects.select_related(
        "student", "student__course"
    ).all()
    course_id = request.GET.get("course", "").strip()
    student_id = request.GET.get("student", "").strip()
    status = request.GET.get("status", "").strip()
    raw_from = request.GET.get("from", "").strip()
    raw_to = request.GET.get("to", "").strip()
    date_from = parse_date(raw_from) if raw_from else None
    date_to = parse_date(raw_to) if raw_to else None

    if (raw_from and date_from is None) or (raw_to and date_to is None):
        messages.warning(request, "Invalid date filter ignored. Use YYYY-MM-DD.")

    if course_id.isdigit():
        records = records.filter(student__course_id=int(course_id))
    if student_id.isdigit():
        records = records.filter(student_id=int(student_id))
    if status in dict(AttendanceRecord.STATUS_CHOICES):
        records = records.filter(status=status)
    if date_from:
        records = records.filter(date__gte=date_from)
    if date_to:
        records = records.filter(date__lte=date_to)

    summary = records.aggregate(
        total=Count("id"),
        present=Count(
            "id",
            filter=Q(
                status__in=(
                    AttendanceRecord.STATUS_PRESENT,
                    AttendanceRecord.STATUS_LATE,
                )
            ),
        ),
        absent=Count("id", filter=Q(status=AttendanceRecord.STATUS_ABSENT)),
    )
    summary["percentage"] = (
        (Decimal(summary["present"]) / Decimal(summary["total"]) * 100).quantize(
            Decimal("0.1")
        )
        if summary["total"]
        else None
    )

    page_obj = Paginator(records, 15).get_page(request.GET.get("page"))
    return render(
        request,
        "students/attendance_list.html",
        {
            "records": page_obj.object_list,
            "page_obj": page_obj,
            "summary": summary,
            "courses": Course.objects.all(),
            "students": Student.objects.all(),
            "status_choices": AttendanceRecord.STATUS_CHOICES,
            "course_id": course_id,
            "student_id": student_id,
            "status": status,
            "date_from": raw_from,
            "date_to": raw_to,
            "querystring": _querystring_without_page(request),
        },
    )


@login_required
def attendance_create(request):
    if request.method == "POST":
        form = AttendanceRecordForm(request.POST)
        if form.is_valid():
            record = form.save()
            messages.success(
                request,
                f"Recorded {record.student.name} as "
                f"{record.get_status_display().lower()} on {record.date}.",
            )
            return redirect("students:attendance_list")
    else:
        form = AttendanceRecordForm(
            initial={
                "date": timezone.localdate(),
                "status": AttendanceRecord.STATUS_PRESENT,
            }
        )

    return render(
        request,
        "students/attendance_form.html",
        {"form": form, "title": "Add attendance record", "submit_label": "Save record"},
    )


@login_required
def attendance_update(request, pk):
    record = get_object_or_404(AttendanceRecord, pk=pk)
    if request.method == "POST":
        form = AttendanceRecordForm(request.POST, instance=record)
        if form.is_valid():
            record = form.save()
            messages.success(request, "Attendance record updated.")
            return redirect("students:attendance_list")
    else:
        form = AttendanceRecordForm(instance=record)

    return render(
        request,
        "students/attendance_form.html",
        {
            "form": form,
            "record": record,
            "title": "Edit attendance record",
            "submit_label": "Save changes",
        },
    )


@login_required
def attendance_delete(request, pk):
    record = get_object_or_404(
        AttendanceRecord.objects.select_related("student"), pk=pk
    )
    if request.method == "POST":
        record.delete()
        messages.success(request, "Attendance record deleted.")
        return redirect("students:attendance_list")

    return render(
        request, "students/attendance_confirm_delete.html", {"record": record}
    )


@login_required
def attendance_bulk_mark(request):
    """Mark attendance for a whole course on a chosen date."""
    params = request.POST if request.method == "POST" else request.GET
    course_id = params.get("course", "").strip()
    raw_date = params.get("date", "").strip()
    selected_date = parse_date(raw_date) if raw_date else timezone.localdate()
    if selected_date is None:
        selected_date = timezone.localdate()

    course = (
        Course.objects.filter(pk=course_id).first() if course_id.isdigit() else None
    )
    students = list(course.students.all()) if course else []
    existing = (
        {
            record.student_id: record
            for record in AttendanceRecord.objects.filter(
                date=selected_date, student__in=students
            )
        }
        if students
        else {}
    )

    initial = {
        "course": course.pk if course else "",
        "date": raw_date or selected_date.isoformat(),
    }
    for student in students:
        record = existing.get(student.pk)
        initial[f"status_{student.pk}"] = (
            record.status if record else AttendanceRecord.STATUS_PRESENT
        )
        initial[f"notes_{student.pk}"] = record.notes if record else ""

    form = AttendanceBulkForm(
        request.POST if request.method == "POST" else None,
        students=students,
        initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        saved_date = form.cleaned_data["date"]
        count = 0
        for student in students:
            AttendanceRecord.objects.update_or_create(
                student=student,
                date=saved_date,
                defaults={
                    "status": form.cleaned_data[f"status_{student.pk}"],
                    "notes": form.cleaned_data[f"notes_{student.pk}"],
                },
            )
            count += 1
        messages.success(
            request,
            f"Saved attendance for {count} student(s) on {saved_date}.",
        )
        return redirect("students:attendance_list")

    rows = [
        {
            "student": student,
            "status": form[f"status_{student.pk}"],
            "notes": form[f"notes_{student.pk}"],
        }
        for student in students
    ]
    return render(
        request,
        "students/attendance_bulk.html",
        {
            "form": form,
            "rows": rows,
            "course": course,
            "course_id": course_id,
            "courses": Course.objects.all(),
            "selected_date": selected_date,
        },
    )


# ---------------------------------------------------------------------------
# Exams, marks and results
# ---------------------------------------------------------------------------


@login_required
def exam_list(request):
    query = request.GET.get("q", "").strip()
    course_id = request.GET.get("course", "").strip()
    exams = Exam.objects.select_related("course").annotate(
        students_enrolled=Count("course__students"),
    )
    if query:
        exams = exams.filter(Q(name__icontains=query) | Q(course__name__icontains=query))
    if course_id.isdigit():
        exams = exams.filter(course_id=int(course_id))

    return render(
        request,
        "students/exam_list.html",
        {
            "exams": exams,
            "query": query,
            "course_id": course_id,
            "courses": Course.objects.all(),
        },
    )


@login_required
def exam_create(request):
    if request.method == "POST":
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save()
            messages.success(request, f"Added exam {exam.name}.")
            return redirect("students:exam_list")
    else:
        form = ExamForm()

    return render(
        request,
        "students/exam_form.html",
        {"form": form, "title": "Add exam", "submit_label": "Save exam"},
    )


@login_required
def exam_update(request, pk):
    exam = get_object_or_404(Exam, pk=pk)
    if request.method == "POST":
        form = ExamForm(request.POST, instance=exam)
        if form.is_valid():
            exam = form.save()
            messages.success(request, f"Updated exam {exam.name}.")
            return redirect("students:exam_list")
    else:
        form = ExamForm(instance=exam)

    return render(
        request,
        "students/exam_form.html",
        {
            "form": form,
            "exam": exam,
            "title": "Edit exam",
            "submit_label": "Save changes",
        },
    )


@login_required
def exam_delete(request, pk):
    exam = get_object_or_404(Exam.objects.select_related("course"), pk=pk)
    if request.method == "POST":
        name = exam.name
        mark_count = exam.marks.count()
        exam.delete()
        messages.success(
            request,
            f"Deleted exam {name}"
            + (f" and its {mark_count} mark(s)." if mark_count else "."),
        )
        return redirect("students:exam_list")

    return render(request, "students/exam_confirm_delete.html", {"exam": exam})


@login_required
def marks_entry(request, pk):
    exam = get_object_or_404(Exam.objects.select_related("course"), pk=pk)
    students = list(exam.course.students.all())
    existing = {mark.student_id: mark for mark in exam.marks.all()}
    initial = {
        f"mark_{student.pk}": (
            existing[student.pk].marks_obtained if student.pk in existing else ""
        )
        for student in students
    }
    form = MarksEntryForm(
        request.POST if request.method == "POST" else None,
        exam=exam,
        students=students,
        initial=initial,
    )
    if request.method == "POST" and form.is_valid():
        count = 0
        for student in students:
            marks = form.cleaned_data[f"mark_{student.pk}"]
            if marks is None:
                Mark.objects.filter(student=student, exam=exam).delete()
            else:
                Mark.objects.update_or_create(
                    student=student, exam=exam, defaults={"marks_obtained": marks}
                )
                count += 1
        messages.success(
            request, f"Saved marks for {count} student(s) in {exam.name}."
        )
        return redirect("students:exam_results", pk=exam.pk)

    rows = [
        {"student": student, "marks": form[f"mark_{student.pk}"]}
        for student in students
    ]
    return render(
        request,
        "students/marks_entry.html",
        {"exam": exam, "form": form, "rows": rows},
    )


@login_required
def exam_results(request, pk):
    exam = get_object_or_404(Exam.objects.select_related("course"), pk=pk)
    marks = list(exam.marks.select_related("student").all())
    average = (
        (sum((mark.marks_obtained for mark in marks), Decimal("0")) / len(marks)).quantize(
            Decimal("0.01")
        )
        if marks
        else None
    )
    return render(
        request,
        "students/exam_results.html",
        {
            "exam": exam,
            "marks": marks,
            "enrolled": exam.course.students.count(),
            "average": average,
            "pass_percentage": PASS_PERCENTAGE,
        },
    )


@login_required
def mark_create(request, student_pk):
    student = get_object_or_404(Student.objects.select_related("course"), pk=student_pk)
    if request.method == "POST":
        form = MarkForm(request.POST, student=student)
        if form.is_valid():
            mark = form.save()
            messages.success(request, f"Added marks for {student.name}.")
            return redirect("students:student_results", pk=student.pk)
    else:
        form = MarkForm(student=student)

    return render(
        request,
        "students/mark_form.html",
        {
            "form": form,
            "student": student,
            "title": "Add marks",
            "submit_label": "Save marks",
        },
    )


@login_required
def mark_update(request, pk):
    mark = get_object_or_404(
        Mark.objects.select_related("student", "exam"), pk=pk
    )
    if request.method == "POST":
        form = MarkForm(request.POST, instance=mark)
        if form.is_valid():
            form.save()
            messages.success(request, "Marks updated.")
            return redirect("students:student_results", pk=mark.student_id)
    else:
        form = MarkForm(instance=mark)

    return render(
        request,
        "students/mark_form.html",
        {"form": form, "mark": mark, "title": "Edit marks", "submit_label": "Save changes"},
    )


@login_required
def mark_delete(request, pk):
    mark = get_object_or_404(
        Mark.objects.select_related("student", "exam"), pk=pk
    )
    if request.method == "POST":
        student_id = mark.student_id
        mark.delete()
        messages.success(request, "Marks deleted.")
        return redirect("students:student_results", pk=student_id)

    return render(request, "students/mark_confirm_delete.html", {"mark": mark})


@login_required
def results_list(request):
    """Rank students by their overall percentage across recorded exams."""
    students = (
        Student.objects.select_related("course")
        .annotate(
            marks_recorded=Count("marks"),
            obtained=Sum("marks__marks_obtained"),
            maximum=Sum("marks__exam__max_marks"),
        )
        .filter(marks_recorded__gt=0)
    )
    query = request.GET.get("q", "").strip()
    course_id = request.GET.get("course", "").strip()
    if query:
        students = students.filter(
            Q(name__icontains=query) | Q(roll_number__icontains=query)
        )
    if course_id.isdigit():
        students = students.filter(course_id=int(course_id))

    rows = []
    for student in students:
        percentage = (
            student.obtained / student.maximum * 100 if student.maximum else None
        )
        rows.append(
            {
                "student": student,
                "obtained": student.obtained,
                "maximum": student.maximum,
                "percentage": percentage,
                "grade": grade_for_percentage(percentage),
            }
        )
    rows.sort(
        key=lambda row: row["percentage"]
        if row["percentage"] is not None
        else Decimal("-1"),
        reverse=True,
    )

    page_obj = Paginator(rows, 10).get_page(request.GET.get("page"))
    return render(
        request,
        "students/results_list.html",
        {
            "rows": page_obj.object_list,
            "page_obj": page_obj,
            "courses": Course.objects.all(),
            "query": query,
            "course_id": course_id,
            "querystring": _querystring_without_page(request),
            "pass_percentage": PASS_PERCENTAGE,
        },
    )


@login_required
def student_results(request, pk):
    student = get_object_or_404(Student.objects.select_related("course"), pk=pk)
    marks = list(student.marks.select_related("exam", "exam__course").all())
    obtained = sum((mark.marks_obtained for mark in marks), Decimal("0"))
    maximum = sum((mark.exam.max_marks for mark in marks), Decimal("0"))
    percentage = obtained / maximum * 100 if maximum else None

    return render(
        request,
        "students/student_results.html",
        {
            "student": student,
            "marks": marks,
            "obtained": obtained,
            "maximum": maximum,
            "percentage": percentage,
            "grade": grade_for_percentage(percentage),
            "attendance": student.attendance_summary(),
            "pass_percentage": PASS_PERCENTAGE,
        },
    )
