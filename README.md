# Student Management System

A web application for managing student information, built with Python, Django, HTML and CSS.
It grew out of an earlier menu-driven Python console project and was rebuilt as a full web app.

## Features

- Admin login and logout (Django sessions)
- Dashboard with total students, total courses and recent additions
- Add, view, update and delete students
- Course management (add, edit, delete)
- Search and filter by name, roll number or course
- Pagination on the student list (10 per page)
- Form validation with clear error messages
- Attendance tracking: single-day records, bulk marking for a whole course, filters and attendance percentage per student
- Exams and marks: create exams, enter marks in bulk or individually, edit/delete marks and view exam results
- Results: per-student marksheets, grades, pass/fail status and an overall ranking

## Tech stack

- Backend: Python 3, Django
- Frontend: HTML5, CSS3
- Database: SQLite

## Getting started

1. Install Django:

   ```bash
   pip install -r requirements.txt
   ```

2. Apply database migrations:

   ```bash
   python manage.py migrate
   ```

3. Create an administrator account (used to log in at `/login/`):

   ```bash
   python manage.py createsuperuser
   ```

4. Start the development server:

   ```bash
   python manage.py runserver
   ```

5. Open <http://127.0.0.1:8000/> in a browser and log in with the account from step 3.

## Attendance and results

- **Attendance:** open *Attendance* → *Mark attendance*, choose a course and date, then set
  Present / Absent / Late / Excused for every student. Existing records for that date are
  pre-filled, so re-saving updates them instead of creating duplicates. Individual records
  can be added, edited or deleted from the attendance list. Only one record per student per
  date is allowed, and future dates are rejected.
- **Exams and marks:** open *Exams* to add an exam (course, date and maximum marks), then use
  *Enter marks* for a bulk entry sheet. Empty cells remove a previously saved mark. Marks can
  also be added, edited or deleted from a student's marksheet. Marks cannot be negative or
  higher than the exam maximum, and students must belong to the exam's course.
- **Results:** *Results* ranks students by overall percentage across recorded exams.
  Each student's marksheet shows per-exam grades plus attendance. Grades are based on the
  percentage: A+ ≥ 90, A ≥ 80, B+ ≥ 70, B ≥ 60, C ≥ 50, D ≥ 40, F below 40; 40% is the
  passing threshold.

## Running the tests

```bash
python manage.py test students
```

## Project layout

```
student_management/   Django project settings and root URLs
students/             Application (models, forms, views, URLs, tests)
  templates/students/ HTML templates
  static/students/    CSS stylesheet
db.sqlite3            SQLite database (created by migrate)
```

## Notes

- `SECRET_KEY` and `DEBUG = True` are for local development. Change them before deploying.
- Deleting a course also deletes the students enrolled in it; the confirmation page shows
  how many records will be affected.
