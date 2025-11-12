# Medical School Database Schema

## Overview
100 tables covering student lifecycle: admission → enrollment → assessment → clinical training → research → graduation → career placement → alumni tracking.

## Core Entities & Relationships

### Students Hub
**students** (PK: student_id)
- Extensions: addresses, emergency_contacts, family_info, health_records, photos, id_cards, previous_education, scholarships
- Links to: majors, advisors, enrollments, clinical_assignments, research, payments, graduation

### Academic Structure
**departments** → **programs** (degree_type: Bachelor/Master/PhD) → **majors** → **specializations**
- program_requirements, program_milestones
- student_majors (supports dual majors via is_primary flag)

### Courses
**courses** (PK: course_id, course_name, course_code, credits, level)
- **course_prerequisites** (FK: course_id → courses, FK: prerequisite_course_id → courses)
  - Self-referencing: to find prerequisites, JOIN courses twice
- **course_sections** (PK: section_id, FK: course_id, semester, year, capacity, enrolled_count)
  - course_schedules (day, time, room_id)
  - **section_instructors** (FK: section_id → course_sections, FK: faculty_id → faculty, role: Primary/Assistant/Guest)
- course_materials, objectives, topics, categories, evaluations

### Faculty
**faculty** (PK: faculty_id, name, title, department_id)
- Extensions: qualifications, research_interests, publications, office_hours, awards, teaching_loads
- Roles: section_instructors, academic_advisors, committee_memberships, thesis_committee_members

### Academic Advisors (导师系统)
**academic_advisors** (PK: advisor_id, FK: faculty_id → faculty)
- Links faculty to their advisor role
- **student_advisor_assignments** (FK: advisor_id → academic_advisors, FK: student_id → students)
- To query advisor-student relationships: academic_advisors JOIN faculty ON faculty_id, then LEFT JOIN student_advisor_assignments ON advisor_id

### Enrollment
**student_enrollments** (PK: enrollment_id, FK: student_id → students, FK: section_id → course_sections, status, grade, grade_points)
- Core table linking students to course sections
- enrollment_waitlists, enrollment_permissions
- credit_transfers, course_drops, course_withdrawals
- grade_changes, incomplete_grades
- audit_enrollments, pass_fail_enrollments

### Assessment
**Exams**: exams → exam_scores, exam_questions (type: Midterm/Final/Quiz/Practical/Oral)
**Assignments**: assignments → assignment_submissions (late_days tracked)
**Projects**: projects → project_submissions (is_group_project flag)
**Labs**: lab_reports → lab_report_submissions
**Participation**: participation_grades (by grading_period)
All link to: section_id + student_id

### Attendance
**class_sessions** (section_id, date, topic) → **attendance_records** (status: Present/Absent/Late/Excused)
- absence_requests (approval workflow)
- late_arrivals (minutes_late)
- attendance_policies, attendance_summaries (calculated metrics)
- Specialized: lab_attendance, clinical_rotation_attendance, seminar_attendance
- attendance_warnings

### Clinical Training (Medical-Specific)
**clinical_rotations** (duration_weeks, required_hours) → **student_clinical_assignments** (hospital, supervisor) → **clinical_evaluations** (clinical_skills_score, professionalism_score, communication_score)
- clinical_rotation_attendance

### Research
**research_projects** (PI, department_id, funding, status) → **student_research_participation** (FK: student_id, FK: project_id, role, hours)
**thesis_submissions** (PK: thesis_id, FK: student_id, FK: advisor_id → faculty, defense_date, status) → **thesis_committee_members** (FK: thesis_id, FK: faculty_id → faculty, role: Chair/Member/External)

### Graduation
**graduation_requirements** (program_id, credits_required)
**student_graduation_status** (total_credits_earned, gpa, requirements_met)
**graduation_applications** (status: Pending/Approved/Denied/Completed) → **degree_conferrals** (honors: Summa/Magna/Cum Laude)
**alumni_records** (current_employer, position)

### Career Services
**career_placements** (employer, position, salary_range, employment_type)
**internships** (organization, hours_completed, evaluation_score)
**residency_placements** (hospital, specialty, match_status) - Medical-specific
**job_search_activities** (type: Application/Interview/Offer/Rejection)
**career_counseling_sessions**

### Finance
**tuition_fees** (semester, year, total_amount, due_date)
**payments** (payment_method: Cash/Credit/Transfer/Scholarship, reference_number)
**financial_aid** (type: Grant/Loan/Scholarship/Work-Study, academic_year)
**student_loans** (lender, interest_rate, repayment_start_date)

### Resources
**rooms** (building, capacity, type: Classroom/Lab/Lecture Hall/Office) → **room_reservations**
**library_resources** (type: Book/Journal/Database/Media, available_copies) → **library_checkouts** (due_date, fine_amount)

### Organizations
**student_organizations** (advisor_faculty_id) → **organization_memberships** (role, status)

### Credentials (Medical-Specific)
**medical_licenses** (license_number, issuing_authority, expiry_date)
**certifications** (certification_number, expiry_date)
**student_achievements** (type: Award/Publication/Presentation/Competition/Honor)

## Key Relationships

```
students
  ├→ student_enrollments → course_sections → courses
  ├→ student_majors → majors → programs → departments
  ├→ student_advisor_assignments → academic_advisors → faculty
  ├→ exam_scores → exams → course_sections
  ├→ attendance_records → class_sessions → course_sections
  ├→ student_clinical_assignments → clinical_rotations
  ├→ student_research_participation → research_projects
  ├→ tuition_fees / payments
  └→ graduation_applications → degree_conferrals

faculty
  ├→ section_instructors → course_sections
  ├→ academic_advisors → student_advisor_assignments
  └→ thesis_committee_members → thesis_submissions

course_sections
  ├→ course_schedules → rooms
  ├→ section_instructors → faculty
  ├→ student_enrollments → students
  ├→ exams / assignments / projects / lab_reports
  └→ class_sessions → attendance_records
```

## Common Query Patterns

**Student transcript**: students + student_enrollments + course_sections + courses + exam_scores + assignment_submissions + attendance_summaries

**Course roster**: course_sections + courses + student_enrollments + students + section_instructors + faculty

**Faculty workload**: faculty + section_instructors + course_sections + student_enrollments + faculty_teaching_loads + student_advisor_assignments

**Clinical evaluation**: students + student_clinical_assignments + clinical_rotations + clinical_evaluations + clinical_rotation_attendance

**Financial statement**: students + tuition_fees + payments + financial_aid + student_scholarships

## Design Features

- **Extensibility**: Main tables + extension tables pattern (students → 9 extension tables)
- **Audit trail**: grade_changes, enrollment_history, attendance_warnings
- **Flexible assessment**: Multiple evaluation types with configurable weights
- **Medical focus**: Clinical rotations, residency placements, medical licenses
- **Lifecycle coverage**: Admission → Alumni with complete tracking
- **Multi-valued**: Supports dual majors, multiple instructors, committee memberships
- **Constraints**: CHECK (status values), UNIQUE (id_card_number, course_code), DEFAULT (timestamps, counts)

## Table Count by Module
- Student info: 11 tables
- Academic structure: 8 tables
- Courses: 10 tables
- Faculty: 10 tables
- Enrollment: 10 tables
- Assessment: 13 tables
- Attendance: 10 tables
- Graduation: 5 tables
- Career: 6 tables
- Finance: 4 tables
- Resources: 4 tables
- Organizations: 2 tables
- Clinical: 4 tables
- Research: 4 tables
- Credentials: 3 tables
