# Medical School Test Database

This directory contains the test database for the Business Report Generator system.

## Files

- `schema.sql` - Database schema with 100 tables covering medical school student management
- `test_data.sql` - Test data with 30-50 rows per table (generated)
- `generate_test_data.py` - Python script to generate test data
- `init_database.py` - Python script to initialize the database
- `test_medical.db` - SQLite database file (generated)

## Database Schema

The test database contains 100 tables organized into the following categories:

### 1. Student Basic Information (10 tables)
- students, student_addresses, student_emergency_contacts, student_family_info
- student_health_records, student_photos, student_enrollment_history
- student_id_cards, student_previous_education, student_scholarships

### 2. Academic Programs (10 tables)
- programs, departments, majors, student_majors, program_requirements
- specializations, student_specializations, academic_advisors
- student_advisor_assignments, program_milestones

### 3. Courses (10 tables)
- courses, course_prerequisites, course_sections, course_schedules
- course_materials, course_objectives, course_topics, course_evaluations
- course_categories, course_category_mappings

### 4. Faculty and Instructors (10 tables)
- faculty, faculty_qualifications, faculty_research_interests
- faculty_publications, section_instructors, faculty_office_hours
- faculty_awards, faculty_committees, faculty_committee_memberships
- faculty_teaching_loads

### 5. Enrollments (10 tables)
- student_enrollments, enrollment_waitlists, enrollment_permissions
- credit_transfers, course_drops, course_withdrawals, grade_changes
- incomplete_grades, audit_enrollments, pass_fail_enrollments

### 6. Exams and Assessments (10 tables)
- exams, exam_scores, exam_questions, assignments
- assignment_submissions, projects, project_submissions
- lab_reports, lab_report_submissions, participation_grades

### 7. Attendance (10 tables)
- class_sessions, attendance_records, absence_requests, late_arrivals
- attendance_policies, attendance_summaries, lab_attendance
- clinical_rotation_attendance, seminar_attendance, attendance_warnings

### 8. Graduation and Career (10 tables)
- graduation_requirements, student_graduation_status, graduation_applications
- degree_conferrals, alumni_records, career_placements, internships
- residency_placements, job_search_activities, career_counseling_sessions

### 9. Financial and Administrative (10 tables)
- tuition_fees, payments, financial_aid, student_loans, rooms
- room_reservations, library_resources, library_checkouts
- student_organizations, organization_memberships

### 10. Clinical and Research (10 tables)
- clinical_rotations, student_clinical_assignments, clinical_evaluations
- research_projects, student_research_participation, thesis_submissions
- thesis_committee_members, medical_licenses, certifications
- student_achievements

## Test Data

The database contains realistic test data:
- 50 students
- 30 faculty members
- 40 courses
- 8 departments
- 5 programs
- And many more related records across all 100 tables

## Usage

### Initialize the Database

To create a fresh database with schema and test data:

```bash
python data/init_database.py
```

This will:
1. Remove any existing `test_medical.db` file
2. Create a new SQLite database
3. Execute the schema SQL to create all 100 tables
4. Insert test data into the tables
5. Verify the database was created successfully

### Regenerate Test Data

To regenerate the test data SQL file:

```bash
python data/generate_test_data.py
```

This will create a new `test_data.sql` file with randomized test data.

### Query the Database

You can query the database using sqlite3:

```bash
sqlite3 data/test_medical.db "SELECT * FROM students LIMIT 5;"
```

Or use it with the Business Report Generator application by configuring it as a data source.

## Example Queries

### Get all active students with their majors:
```sql
SELECT s.name, s.student_id, m.major_name, s.admission_date
FROM students s
LEFT JOIN student_majors sm ON s.student_id = sm.student_id
LEFT JOIN majors m ON sm.major_id = m.major_id
WHERE s.status = 'Active';
```

### Get average exam scores by course:
```sql
SELECT c.course_name, AVG(es.score) as avg_score, COUNT(*) as num_students
FROM courses c
JOIN course_sections cs ON c.course_id = cs.course_id
JOIN exams e ON cs.section_id = e.section_id
JOIN exam_scores es ON e.exam_id = es.exam_id
GROUP BY c.course_id, c.course_name;
```

### Get student attendance summary:
```sql
SELECT s.name, s.student_id,
       COUNT(CASE WHEN ar.status = 'Present' THEN 1 END) as present,
       COUNT(CASE WHEN ar.status = 'Absent' THEN 1 END) as absent,
       COUNT(CASE WHEN ar.status = 'Late' THEN 1 END) as late
FROM students s
JOIN attendance_records ar ON s.student_id = ar.student_id
GROUP BY s.student_id, s.name;
```

### Get graduation status:
```sql
SELECT s.name, s.student_id, sgs.total_credits_earned, sgs.gpa,
       sgs.expected_graduation_date, sgs.requirements_met
FROM students s
JOIN student_graduation_status sgs ON s.student_id = sgs.student_id
WHERE sgs.requirements_met = 1;
```

## Notes

- The database uses SQLite format for easy portability and testing
- All dates are in YYYY-MM-DD format
- Student IDs follow the pattern S2020000-S2020049
- Faculty IDs follow the pattern F001-F030
- Course IDs follow the pattern C0001-C0040
- Chinese names and locations are used for realistic medical school data
