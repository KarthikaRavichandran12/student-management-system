from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


PASS_PERCENTAGE = 40

# Highest threshold first; evaluated top-down by grade_for_percentage().
GRADE_THRESHOLDS = (
    (Decimal("90"), "A+"),
    (Decimal("80"), "A"),
    (Decimal("70"), "B+"),
    (Decimal("60"), "B"),
    (Decimal("50"), "C"),
    (Decimal("40"), "D"),
)


def grade_for_percentage(percentage):
    """Return a letter grade for a percentage (or an em dash when unavailable)."""
    if percentage is None:
        return "—"
    for threshold, grade in GRADE_THRESHOLDS:
        if percentage >= threshold:
            return grade
    return "F"


class Course(models.Model):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"

    def get_absolute_url(self):
        return reverse("students:course_list")


class Student(models.Model):
    name = models.CharField(max_length=120)
    roll_number = models.CharField(max_length=30, unique=True)
    email = models.EmailField(max_length=254, unique=True)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="students",
    )
    date_of_birth = models.DateField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["roll_number"]

    def __str__(self):
        return f"{self.name} - {self.roll_number}"

    def get_absolute_url(self):
        return reverse("students:student_detail", args=[self.pk])

    def attendance_summary(self):
        """Count attendance days and compute the present percentage."""
        records = self.attendance_records.all()
        total = records.count()
        present = records.filter(
            status__in=(AttendanceRecord.STATUS_PRESENT, AttendanceRecord.STATUS_LATE)
        ).count()
        return {
            "total": total,
            "present": present,
            "absent": records.filter(status=AttendanceRecord.STATUS_ABSENT).count(),
            "percentage": (
                (Decimal(present) / Decimal(total) * 100).quantize(Decimal("0.1"))
                if total
                else None
            ),
        }


class AttendanceRecord(models.Model):
    STATUS_PRESENT = "present"
    STATUS_ABSENT = "absent"
    STATUS_LATE = "late"
    STATUS_EXCUSED = "excused"
    STATUS_CHOICES = (
        (STATUS_PRESENT, "Present"),
        (STATUS_ABSENT, "Absent"),
        (STATUS_LATE, "Late"),
        (STATUS_EXCUSED, "Excused"),
    )

    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PRESENT,
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-date", "student__roll_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "date"],
                name="unique_attendance_per_student_and_date",
            )
        ]

    def __str__(self):
        return f"{self.student} - {self.date}: {self.get_status_display()}"


class Exam(models.Model):
    name = models.CharField(max_length=120)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="exams",
    )
    exam_date = models.DateField()
    max_marks = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )

    class Meta:
        ordering = ["-exam_date", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "course", "exam_date"],
                name="unique_exam_name_course_and_date",
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.course.code} ({self.exam_date})"

    @property
    def marks_count(self):
        return self.marks.count()


class Mark(models.Model):
    student = models.ForeignKey(
        Student,
        on_delete=models.CASCADE,
        related_name="marks",
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="marks",
    )
    marks_obtained = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
    )

    class Meta:
        ordering = ["exam__exam_date", "student__roll_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "exam"],
                name="unique_mark_per_student_and_exam",
            )
        ]

    def __str__(self):
        return f"{self.student} - {self.exam.name}: {self.marks_obtained}"

    @property
    def percentage(self):
        if not self.exam.max_marks:
            return None
        return self.marks_obtained / self.exam.max_marks * 100

    @property
    def grade(self):
        return grade_for_percentage(self.percentage)

    @property
    def passed(self):
        percentage = self.percentage
        return percentage is not None and percentage >= PASS_PERCENTAGE

    def get_absolute_url(self):
        return reverse("students:exam_results", args=[self.exam_id])
