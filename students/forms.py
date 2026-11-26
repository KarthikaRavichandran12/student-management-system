import re
from decimal import Decimal

from django import forms
from django.utils import timezone

from .models import AttendanceRecord, Course, Exam, Mark, Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            "name",
            "roll_number",
            "email",
            "course",
            "date_of_birth",
            "phone",
            "address",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Aarav Sharma"}),
            "roll_number": forms.TextInput(attrs={"placeholder": "e.g. STU-1001"}),
            "email": forms.EmailInput(attrs={"placeholder": "aarav@example.com"}),
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "phone": forms.TextInput(attrs={"placeholder": "e.g. 9876543210"}),
            "address": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional"}),
        }
        help_texts = {
            "roll_number": "Letters, numbers and hyphens only.",
            "email": "Each student must have a unique email address.",
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise forms.ValidationError("Name must be at least 2 characters long.")
        return name

    def clean_roll_number(self):
        roll_number = self.cleaned_data["roll_number"].strip().upper()
        if not re.fullmatch(r"[A-Z0-9-]+", roll_number):
            raise forms.ValidationError(
                "Roll number may contain only letters, numbers and hyphens."
            )
        duplicates = Student.objects.filter(roll_number__iexact=roll_number)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError(
                "A student with this roll number already exists."
            )
        return roll_number

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        duplicates = Student.objects.filter(email__iexact=email)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("A student with this email already exists.")
        return email

    def clean_date_of_birth(self):
        date_of_birth = self.cleaned_data.get("date_of_birth")
        if date_of_birth and date_of_birth > timezone.localdate():
            raise forms.ValidationError("Date of birth cannot be in the future.")
        return date_of_birth

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone and not re.fullmatch(r"[0-9()+\-\s]{7,20}", phone):
            raise forms.ValidationError(
                "Enter a valid phone number (7-20 digits or +, -, spaces, brackets)."
            )
        return phone


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["name", "code", "description"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Computer Science"}),
            "code": forms.TextInput(attrs={"placeholder": "e.g. CS-101"}),
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Optional course description"}
            ),
        }
        help_texts = {
            "code": "Letters, numbers and hyphens only, up to 20 characters.",
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise forms.ValidationError("Course name must be at least 2 characters long.")
        duplicates = Course.objects.filter(name__iexact=name)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("A course with this name already exists.")
        return name

    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        if not re.fullmatch(r"[A-Z0-9-]{2,20}", code):
            raise forms.ValidationError(
                "Code must be 2-20 characters: letters, numbers and hyphens only."
            )
        duplicates = Course.objects.filter(code__iexact=code)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError("A course with this code already exists.")
        return code


class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        fields = ["student", "date", "status", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3, "placeholder": "Optional"}),
        }

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date > timezone.localdate():
            raise forms.ValidationError("Attendance date cannot be in the future.")
        return date

    def clean_notes(self):
        return self.cleaned_data.get("notes", "").strip()

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get("student")
        date = cleaned_data.get("date")
        if student and date:
            duplicates = AttendanceRecord.objects.filter(student=student, date=date)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error(
                    "date",
                    "Attendance for this student on this date is already recorded. "
                    "Edit the existing record instead.",
                )
        return cleaned_data


class AttendanceBulkForm(forms.Form):
    """Mark every student in a course as present/absent/late/excused on one date."""

    course = forms.ModelChoiceField(queryset=Course.objects.all())
    date = forms.DateField(
        initial=timezone.localdate,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, students=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.students = list(students)
        for student in self.students:
            self.fields[f"status_{student.pk}"] = forms.TypedChoiceField(
                label=f"{student.name} ({student.roll_number})",
                choices=AttendanceRecord.STATUS_CHOICES,
                coerce=str,
                initial=AttendanceRecord.STATUS_PRESENT,
            )
            self.fields[f"notes_{student.pk}"] = forms.CharField(
                label="Note",
                required=False,
                widget=forms.TextInput(attrs={"placeholder": "Optional"}),
            )

    def clean_date(self):
        date = self.cleaned_data["date"]
        if date > timezone.localdate():
            raise forms.ValidationError("Attendance date cannot be in the future.")
        return date

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("course") and not self.students:
            self.add_error(
                "course",
                "This course has no students yet. Add students before marking attendance.",
            )
        return cleaned_data


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ["name", "course", "exam_date", "max_marks"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Midterm exam"}),
            "exam_date": forms.DateInput(attrs={"type": "date"}),
            "max_marks": forms.NumberInput(
                attrs={"min": "0.01", "step": "0.01", "placeholder": "e.g. 100"}
            ),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if len(name) < 2:
            raise forms.ValidationError("Exam name must be at least 2 characters long.")
        return name

    def clean_max_marks(self):
        max_marks = self.cleaned_data["max_marks"]
        if max_marks <= 0:
            raise forms.ValidationError("Maximum marks must be greater than zero.")
        return max_marks

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name")
        course = cleaned_data.get("course")
        exam_date = cleaned_data.get("exam_date")
        if name and course and exam_date:
            duplicates = Exam.objects.filter(
                name__iexact=name, course=course, exam_date=exam_date
            )
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error(
                    "name",
                    "An exam with this name already exists for the course on that date.",
                )
        return cleaned_data


class MarkForm(forms.ModelForm):
    class Meta:
        model = Mark
        fields = ["student", "exam", "marks_obtained"]
        widgets = {
            "marks_obtained": forms.NumberInput(
                attrs={"min": "0", "step": "0.01", "placeholder": "e.g. 85.5"}
            ),
        }

    def __init__(self, *args, student=None, exam=None, **kwargs):
        super().__init__(*args, **kwargs)
        instance_student = self.instance.student if self.instance.pk else None
        instance_exam = self.instance.exam if self.instance.pk else None
        student = student or instance_student
        exam = exam or instance_exam

        if student is not None:
            self.fields["student"].queryset = Student.objects.filter(pk=student.pk)
            self.fields["student"].initial = student
            if exam is None:
                self.fields["exam"].queryset = Exam.objects.filter(course=student.course)
        if exam is not None:
            self.fields["exam"].queryset = Exam.objects.filter(pk=exam.pk)
            self.fields["exam"].initial = exam
            if student is None:
                self.fields["student"].queryset = exam.course.students.all()

    def clean_marks_obtained(self):
        marks = self.cleaned_data["marks_obtained"]
        if marks < 0:
            raise forms.ValidationError("Marks cannot be negative.")
        return marks

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get("student")
        exam = cleaned_data.get("exam")
        marks = cleaned_data.get("marks_obtained")
        if exam and marks is not None and marks > exam.max_marks:
            self.add_error(
                "marks_obtained",
                f"Marks cannot exceed the maximum of {exam.max_marks}.",
            )
        if student and exam and student.course_id != exam.course_id:
            self.add_error(
                "student",
                "This student is not enrolled in the course the exam belongs to.",
            )
        if student and exam:
            duplicates = Mark.objects.filter(student=student, exam=exam)
            if self.instance.pk:
                duplicates = duplicates.exclude(pk=self.instance.pk)
            if duplicates.exists():
                self.add_error("exam", "Marks for this student and exam already exist.")
        return cleaned_data


class MarksEntryForm(forms.Form):
    """Enter marks for every student enrolled in an exam's course."""

    def __init__(self, *args, exam=None, students=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.exam = exam
        self.students = list(students)
        if exam is None:
            return
        for student in self.students:
            self.fields[f"mark_{student.pk}"] = forms.DecimalField(
                label=f"{student.name} ({student.roll_number})",
                max_digits=6,
                decimal_places=2,
                min_value=Decimal("0"),
                max_value=exam.max_marks,
                required=False,
                widget=forms.NumberInput(
                    attrs={
                        "min": "0",
                        "max": str(exam.max_marks),
                        "step": "0.01",
                        "placeholder": "—",
                    }
                ),
            )
