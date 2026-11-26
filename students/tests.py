from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    AttendanceRecord,
    Course,
    Exam,
    Mark,
    Student,
    grade_for_percentage,
)


class StudentManagementTests(TestCase):
    def setUp(self):
        self.password = "Testpass123!"
        self.user = get_user_model().objects.create_user(
            username="admin", password=self.password
        )
        self.client.login(username="admin", password=self.password)
        self.course = Course.objects.create(name="Computer Science", code="CS-101")

    def student_payload(self, roll_number="STU-1001", email="student@example.com"):
        return {
            "name": "Aarav Sharma",
            "roll_number": roll_number,
            "email": email,
            "course": self.course.pk,
            "date_of_birth": "2004-05-14",
            "phone": "9876543210",
            "address": "12 Main Street",
        }

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("students:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("students:login"), response.url)

    def test_login_and_logout(self):
        self.client.logout()
        response = self.client.post(
            reverse("students:login"),
            {"username": "admin", "password": self.password},
        )
        self.assertRedirects(response, reverse("students:dashboard"))
        self.assertEqual(
            self.client.get(reverse("students:logout")).status_code, 405
        )
        self.assertRedirects(
            self.client.post(reverse("students:logout")),
            reverse("students:login"),
        )

    def test_dashboard_statistics(self):
        for index in range(12):
            Student.objects.create(
                name=f"Student {index}",
                roll_number=f"STU-{index:04d}",
                email=f"student{index}@example.com",
                course=self.course,
            )
        response = self.client.get(reverse("students:dashboard"))
        self.assertEqual(response.context["total_students"], 12)
        self.assertEqual(response.context["total_courses"], 1)
        self.assertEqual(len(response.context["recent_students"]), 5)

    def test_student_create_update_and_delete(self):
        response = self.client.post(
            reverse("students:student_create"), self.student_payload()
        )
        student = Student.objects.get(roll_number="STU-1001")
        self.assertRedirects(
            response, reverse("students:student_detail", args=[student.pk])
        )
        self.assertEqual(student.name, "Aarav Sharma")

        response = self.client.post(
            reverse("students:student_update", args=[student.pk]),
            self.student_payload(email="updated@example.com"),
        )
        self.assertRedirects(
            response, reverse("students:student_detail", args=[student.pk])
        )
        student.refresh_from_db()
        self.assertEqual(student.email, "updated@example.com")

        response = self.client.post(
            reverse("students:student_delete", args=[student.pk])
        )
        self.assertRedirects(response, reverse("students:student_list"))
        self.assertFalse(Student.objects.filter(pk=student.pk).exists())

    def test_duplicate_roll_number_is_rejected(self):
        payload = self.student_payload(email="first@example.com")
        payload["course"] = self.course
        Student.objects.create(**payload)
        response = self.client.post(
            reverse("students:student_create"),
            self.student_payload(email="second@example.com"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")

    def test_invalid_roll_number_is_rejected(self):
        response = self.client.post(
            reverse("students:student_create"),
            self.student_payload(roll_number="bad number!"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "only letters, numbers and hyphens")

    def test_search_filter_and_pagination(self):
        for index in range(12):
            Student.objects.create(
                name="Aarav Sharma" if index == 0 else f"Student {index}",
                roll_number=f"STU-{index:04d}",
                email=f"student{index}@example.com",
                course=self.course,
            )
        first_page = self.client.get(reverse("students:student_list"))
        self.assertEqual(len(first_page.context["students"]), 10)
        self.assertTrue(first_page.context["page_obj"].has_next())

        second_page = self.client.get(reverse("students:student_list"), {"page": 2})
        self.assertEqual(len(second_page.context["students"]), 2)

        search = self.client.get(reverse("students:student_list"), {"q": "Aarav"})
        self.assertEqual(search.context["page_obj"].paginator.count, 1)

        filtered = self.client.get(
            reverse("students:student_list"), {"course": self.course.pk}
        )
        self.assertEqual(filtered.context["page_obj"].paginator.count, 12)

    def test_all_pages_render(self):
        payload = self.student_payload()
        payload["course"] = self.course
        student = Student.objects.create(**payload)
        urls = [
            reverse("students:dashboard"),
            reverse("students:student_list"),
            reverse("students:student_create"),
            reverse("students:student_detail", args=[student.pk]),
            reverse("students:student_update", args=[student.pk]),
            reverse("students:student_delete", args=[student.pk]),
            reverse("students:course_list"),
            reverse("students:course_create"),
            reverse("students:course_update", args=[self.course.pk]),
            reverse("students:course_delete", args=[self.course.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("students:login")).status_code, 200)

    def test_course_create_edit_and_delete(self):
        response = self.client.post(
            reverse("students:course_create"),
            {"name": "Mathematics", "code": "MA-201", "description": "Algebra"},
        )
        self.assertRedirects(response, reverse("students:course_list"))
        course = Course.objects.get(code="MA-201")

        response = self.client.post(
            reverse("students:course_update", args=[course.pk]),
            {"name": "Applied Mathematics", "code": "MA-201", "description": ""},
        )
        self.assertRedirects(response, reverse("students:course_list"))
        course.refresh_from_db()
        self.assertEqual(course.name, "Applied Mathematics")

        response = self.client.post(
            reverse("students:course_delete", args=[course.pk])
        )
        self.assertRedirects(response, reverse("students:course_list"))
        self.assertFalse(Course.objects.filter(pk=course.pk).exists())

    def test_student_form_explains_missing_courses(self):
        Course.objects.all().delete()
        response = self.client.get(reverse("students:student_create"))
        self.assertFalse(response.context["has_courses"])
        self.assertContains(response, "Add a course first")


class AttendanceAndResultsTests(TestCase):
    def setUp(self):
        self.password = "Testpass123!"
        self.user = get_user_model().objects.create_user(
            username="registrar", password=self.password
        )
        self.client.login(username="registrar", password=self.password)
        self.course = Course.objects.create(name="Mathematics", code="MA-201")
        self.student1 = Student.objects.create(
            name="Aarav Sharma",
            roll_number="STU-2001",
            email="aarav@example.com",
            course=self.course,
        )
        self.student2 = Student.objects.create(
            name="Neha Verma",
            roll_number="STU-2002",
            email="neha@example.com",
            course=self.course,
        )
        self.date = (timezone.localdate() - timedelta(days=1)).isoformat()

    def attendance_payload(self, **overrides):
        payload = {
            "student": self.student1.pk,
            "date": self.date,
            "status": "present",
            "notes": "On time",
        }
        payload.update(overrides)
        return payload

    def exam_payload(self, **overrides):
        payload = {
            "name": "Midterm exam",
            "course": self.course.pk,
            "exam_date": "2026-12-15",
            "max_marks": "100",
        }
        payload.update(overrides)
        return payload

    def test_attendance_record_create_edit_delete_and_duplicates(self):
        response = self.client.post(
            reverse("students:attendance_create"), self.attendance_payload()
        )
        self.assertRedirects(response, reverse("students:attendance_list"))
        record = AttendanceRecord.objects.get(student=self.student1, date=self.date)
        self.assertEqual(record.status, "present")

        response = self.client.post(
            reverse("students:attendance_create"), self.attendance_payload()
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already recorded")

        response = self.client.post(
            reverse("students:attendance_update", args=[record.pk]),
            self.attendance_payload(status="absent"),
        )
        self.assertRedirects(response, reverse("students:attendance_list"))
        record.refresh_from_db()
        self.assertEqual(record.status, "absent")

        response = self.client.post(
            reverse("students:attendance_delete", args=[record.pk])
        )
        self.assertRedirects(response, reverse("students:attendance_list"))
        self.assertFalse(AttendanceRecord.objects.filter(pk=record.pk).exists())

    def test_attendance_rejects_future_dates(self):
        future = (timezone.localdate() + timedelta(days=1)).isoformat()
        response = self.client.post(
            reverse("students:attendance_create"),
            self.attendance_payload(date=future),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cannot be in the future")

    def test_bulk_attendance_creates_and_updates_a_whole_class(self):
        url = reverse("students:attendance_bulk_mark")
        response = self.client.get(url, {"course": self.course.pk, "date": self.date})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["rows"]), 2)

        payload = {
            "course": self.course.pk,
            "date": self.date,
            f"status_{self.student1.pk}": "present",
            f"notes_{self.student1.pk}": "",
            f"status_{self.student2.pk}": "absent",
            f"notes_{self.student2.pk}": "Sick leave",
        }
        response = self.client.post(url, payload)
        self.assertRedirects(response, reverse("students:attendance_list"))
        self.assertEqual(AttendanceRecord.objects.count(), 2)
        self.assertEqual(
            AttendanceRecord.objects.get(student=self.student2).notes, "Sick leave"
        )

        payload[f"status_{self.student2.pk}"] = "late"
        self.client.post(url, payload)
        self.assertEqual(AttendanceRecord.objects.count(), 2)
        self.assertEqual(
            AttendanceRecord.objects.get(student=self.student2).status, "late"
        )

    def test_attendance_list_filters_and_summary(self):
        AttendanceRecord.objects.create(
            student=self.student1, date=self.date, status="present"
        )
        AttendanceRecord.objects.create(
            student=self.student2, date=self.date, status="absent"
        )
        url = reverse("students:attendance_list")

        response = self.client.get(url, {"course": self.course.pk})
        self.assertEqual(len(response.context["records"]), 2)
        self.assertEqual(response.context["summary"]["present"], 1)
        self.assertEqual(response.context["summary"]["absent"], 1)

        response = self.client.get(url, {"status": "absent"})
        self.assertEqual(len(response.context["records"]), 1)
        self.assertEqual(response.context["records"][0].student, self.student2)

        response = self.client.get(url, {"student": self.student1.pk})
        self.assertEqual(len(response.context["records"]), 1)

        response = self.client.get(
            url, {"from": "2099-01-01", "to": "2099-01-31"}
        )
        self.assertEqual(len(response.context["records"]), 0)

    def test_exam_create_edit_delete_and_validation(self):
        response = self.client.post(
            reverse("students:exam_create"), self.exam_payload()
        )
        self.assertRedirects(response, reverse("students:exam_list"))
        exam = Exam.objects.get(name="Midterm exam")

        response = self.client.post(
            reverse("students:exam_create"), self.exam_payload()
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")

        response = self.client.post(
            reverse("students:exam_create"), self.exam_payload(max_marks="0")
        )
        self.assertContains(response, "greater than zero")

        response = self.client.post(
            reverse("students:exam_update", args=[exam.pk]),
            self.exam_payload(name="Final exam"),
        )
        self.assertRedirects(response, reverse("students:exam_list"))
        exam.refresh_from_db()
        self.assertEqual(exam.name, "Final exam")

        response = self.client.post(
            reverse("students:exam_delete", args=[exam.pk])
        )
        self.assertRedirects(response, reverse("students:exam_list"))
        self.assertFalse(Exam.objects.filter(pk=exam.pk).exists())

    def test_marks_entry_validation_and_editing(self):
        exam = Exam.objects.create(
            name="Midterm exam",
            course=self.course,
            exam_date="2026-12-15",
            max_marks=Decimal("100"),
        )
        url = reverse("students:marks_entry", args=[exam.pk])
        payload = {
            f"mark_{self.student1.pk}": "85.5",
            f"mark_{self.student2.pk}": "35",
        }

        response = self.client.post(url, payload)
        self.assertRedirects(
            response, reverse("students:exam_results", args=[exam.pk])
        )
        self.assertEqual(Mark.objects.count(), 2)
        results = self.client.get(reverse("students:exam_results", args=[exam.pk]))
        self.assertEqual(results.context["average"], Decimal("60.25"))

        payload[f"mark_{self.student1.pk}"] = "150"
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "less than or equal")
        self.assertEqual(
            Mark.objects.get(student=self.student1).marks_obtained, Decimal("85.5")
        )

        payload[f"mark_{self.student1.pk}"] = ""
        self.client.post(url, payload)
        self.assertFalse(Mark.objects.filter(student=self.student1, exam=exam).exists())

        mark = Mark.objects.create(
            student=self.student1, exam=exam, marks_obtained=Decimal("90")
        )
        response = self.client.post(
            reverse("students:mark_update", args=[mark.pk]),
            {
                "student": self.student1.pk,
                "exam": exam.pk,
                "marks_obtained": "92",
            },
        )
        self.assertRedirects(
            response, reverse("students:student_results", args=[self.student1.pk])
        )
        mark.refresh_from_db()
        self.assertEqual(mark.marks_obtained, Decimal("92"))

        response = self.client.post(reverse("students:mark_delete", args=[mark.pk]))
        self.assertRedirects(
            response, reverse("students:student_results", args=[self.student1.pk])
        )
        self.assertFalse(Mark.objects.filter(pk=mark.pk).exists())

    def test_results_ranking_grades_and_adding_a_mark(self):
        exam = Exam.objects.create(
            name="Final exam",
            course=self.course,
            exam_date="2026-12-15",
            max_marks=Decimal("100"),
        )
        Mark.objects.create(
            student=self.student1, exam=exam, marks_obtained=Decimal("92")
        )
        Mark.objects.create(
            student=self.student2, exam=exam, marks_obtained=Decimal("35")
        )

        top = self.client.get(
            reverse("students:student_results", args=[self.student1.pk])
        )
        self.assertEqual(top.context["grade"], "A+")
        self.assertTrue(top.context["marks"][0].passed)

        bottom = self.client.get(
            reverse("students:student_results", args=[self.student2.pk])
        )
        self.assertEqual(bottom.context["grade"], "F")
        self.assertFalse(bottom.context["marks"][0].passed)

        ranking = self.client.get(reverse("students:results_list"))
        self.assertEqual(len(ranking.context["rows"]), 2)
        self.assertEqual(ranking.context["rows"][0]["student"], self.student1)

        self.assertEqual(grade_for_percentage(Decimal("89.99")), "A")
        self.assertEqual(grade_for_percentage(Decimal("79.99")), "B+")
        self.assertEqual(grade_for_percentage(Decimal("40")), "D")
        self.assertEqual(grade_for_percentage(None), "—")

        quiz = Exam.objects.create(
            name="Quiz",
            course=self.course,
            exam_date="2026-12-20",
            max_marks=Decimal("20"),
        )
        response = self.client.post(
            reverse("students:mark_create", args=[self.student1.pk]),
            {"student": self.student1.pk, "exam": quiz.pk, "marks_obtained": "18"},
        )
        self.assertRedirects(
            response, reverse("students:student_results", args=[self.student1.pk])
        )
        self.assertTrue(Mark.objects.filter(student=self.student1, exam=quiz).exists())

    def test_all_new_pages_render_and_require_login(self):
        AttendanceRecord.objects.create(
            student=self.student1, date=self.date, status="present"
        )
        exam = Exam.objects.create(
            name="Midterm exam",
            course=self.course,
            exam_date="2026-12-15",
            max_marks=Decimal("100"),
        )
        mark = Mark.objects.create(
            student=self.student1, exam=exam, marks_obtained=Decimal("80")
        )
        urls = [
            reverse("students:attendance_list"),
            reverse("students:attendance_create"),
            reverse("students:attendance_bulk_mark"),
            reverse("students:attendance_update", args=[1]),
            reverse("students:attendance_delete", args=[1]),
            reverse("students:exam_list"),
            reverse("students:exam_create"),
            reverse("students:exam_update", args=[exam.pk]),
            reverse("students:exam_delete", args=[exam.pk]),
            reverse("students:marks_entry", args=[exam.pk]),
            reverse("students:exam_results", args=[exam.pk]),
            reverse("students:mark_create", args=[self.student1.pk]),
            reverse("students:mark_update", args=[mark.pk]),
            reverse("students:mark_delete", args=[mark.pk]),
            reverse("students:results_list"),
            reverse("students:student_results", args=[self.student1.pk]),
            reverse("students:student_detail", args=[self.student1.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

        self.client.logout()
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("students:login"), response.url)
