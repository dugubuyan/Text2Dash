-- Medical School Database Schema
-- 100 tables covering student management, courses, exams, attendance, and graduation tracking

-- ============================================
-- SECTION 1: Student Basic Information (10 tables)
-- ============================================

-- 1. Students - Core student information
CREATE TABLE students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    gender TEXT CHECK(gender IN ('M', 'F', 'Other')),
    date_of_birth DATE NOT NULL,
    id_card_number TEXT UNIQUE,
    phone TEXT,
    email TEXT,
    admission_date DATE NOT NULL,
    graduation_date DATE,
    status TEXT CHECK(status IN ('Active', 'Graduated', 'Suspended', 'Withdrawn')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Student addresses
CREATE TABLE student_addresses (
    address_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    address_type TEXT CHECK(address_type IN ('Home', 'Dorm', 'Emergency')),
    street TEXT,
    city TEXT,
    province TEXT,
    postal_code TEXT,
    country TEXT DEFAULT 'China',
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 3. Student emergency contacts
CREATE TABLE student_emergency_contacts (
    contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    relationship TEXT,
    phone TEXT NOT NULL,
    email TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 4. Student family background
CREATE TABLE student_family_info (
    family_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    father_name TEXT,
    father_occupation TEXT,
    mother_name TEXT,
    mother_occupation TEXT,
    family_income_level TEXT CHECK(family_income_level IN ('Low', 'Medium', 'High')),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 5. Student health records
CREATE TABLE student_health_records (
    health_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    blood_type TEXT,
    allergies TEXT,
    chronic_conditions TEXT,
    vaccination_status TEXT,
    last_checkup_date DATE,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 6. Student photos
CREATE TABLE student_photos (
    photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    photo_url TEXT,
    photo_type TEXT CHECK(photo_type IN ('ID', 'Graduation', 'Other')),
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 7. Student enrollment history
CREATE TABLE student_enrollment_history (
    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    enrollment_year INTEGER NOT NULL,
    enrollment_semester TEXT,
    program_id TEXT,
    status TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 8. Student ID cards
CREATE TABLE student_id_cards (
    card_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    card_number TEXT UNIQUE NOT NULL,
    issue_date DATE NOT NULL,
    expiry_date DATE,
    status TEXT CHECK(status IN ('Active', 'Expired', 'Lost', 'Replaced')),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 9. Student previous education
CREATE TABLE student_previous_education (
    education_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    school_name TEXT NOT NULL,
    degree_level TEXT,
    graduation_year INTEGER,
    major TEXT,
    gpa REAL,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 10. Student scholarships
CREATE TABLE student_scholarships (
    scholarship_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    scholarship_name TEXT NOT NULL,
    amount REAL NOT NULL,
    award_date DATE NOT NULL,
    academic_year TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- ============================================
-- SECTION 2: Academic Programs (10 tables)
-- ============================================

-- 11. Programs
CREATE TABLE programs (
    program_id TEXT PRIMARY KEY,
    program_name TEXT NOT NULL,
    degree_type TEXT CHECK(degree_type IN ('Bachelor', 'Master', 'PhD', 'Certificate')),
    duration_years INTEGER NOT NULL,
    total_credits_required INTEGER,
    department_id TEXT,
    description TEXT
);

-- 12. Departments
CREATE TABLE departments (
    department_id TEXT PRIMARY KEY,
    department_name TEXT NOT NULL,
    head_faculty_id TEXT,
    building TEXT,
    phone TEXT,
    email TEXT,
    established_date DATE
);

-- 13. Majors
CREATE TABLE majors (
    major_id TEXT PRIMARY KEY,
    major_name TEXT NOT NULL,
    program_id TEXT,
    department_id TEXT,
    description TEXT,
    FOREIGN KEY (program_id) REFERENCES programs(program_id),
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

-- 14. Student major assignments
CREATE TABLE student_majors (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    major_id TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    is_primary BOOLEAN DEFAULT 1,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (major_id) REFERENCES majors(major_id)
);

-- 15. Program requirements
CREATE TABLE program_requirements (
    requirement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id TEXT NOT NULL,
    requirement_type TEXT,
    description TEXT,
    credits_required INTEGER,
    FOREIGN KEY (program_id) REFERENCES programs(program_id)
);

-- 16. Specializations
CREATE TABLE specializations (
    specialization_id TEXT PRIMARY KEY,
    specialization_name TEXT NOT NULL,
    major_id TEXT,
    description TEXT,
    FOREIGN KEY (major_id) REFERENCES majors(major_id)
);

-- 17. Student specializations
CREATE TABLE student_specializations (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    specialization_id TEXT NOT NULL,
    start_date DATE NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (specialization_id) REFERENCES specializations(specialization_id)
);

-- 18. Academic advisors
CREATE TABLE academic_advisors (
    advisor_id TEXT PRIMARY KEY,
    faculty_id TEXT NOT NULL,
    department_id TEXT,
    specialization TEXT,
    max_students INTEGER DEFAULT 20
);

-- 19. Student advisor assignments
CREATE TABLE student_advisor_assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    advisor_id TEXT NOT NULL,
    assignment_date DATE NOT NULL,
    end_date DATE,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (advisor_id) REFERENCES academic_advisors(advisor_id)
);

-- 20. Program milestones
CREATE TABLE program_milestones (
    milestone_id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id TEXT NOT NULL,
    milestone_name TEXT NOT NULL,
    typical_year INTEGER,
    description TEXT,
    FOREIGN KEY (program_id) REFERENCES programs(program_id)
);

-- ============================================
-- SECTION 3: Courses (10 tables)
-- ============================================

-- 21. Courses
CREATE TABLE courses (
    course_id TEXT PRIMARY KEY,
    course_name TEXT NOT NULL,
    course_code TEXT UNIQUE NOT NULL,
    credits INTEGER NOT NULL,
    department_id TEXT,
    description TEXT,
    level TEXT CHECK(level IN ('Undergraduate', 'Graduate', 'Both')),
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

-- 22. Course prerequisites
CREATE TABLE course_prerequisites (
    prerequisite_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    prerequisite_course_id TEXT NOT NULL,
    is_mandatory BOOLEAN DEFAULT 1,
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    FOREIGN KEY (prerequisite_course_id) REFERENCES courses(course_id)
);

-- 23. Course sections
CREATE TABLE course_sections (
    section_id TEXT PRIMARY KEY,
    course_id TEXT NOT NULL,
    semester TEXT NOT NULL,
    year INTEGER NOT NULL,
    section_number TEXT NOT NULL,
    max_capacity INTEGER,
    enrolled_count INTEGER DEFAULT 0,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- 24. Course schedules
CREATE TABLE course_schedules (
    schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id TEXT NOT NULL,
    day_of_week TEXT CHECK(day_of_week IN ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday')),
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    room_id TEXT,
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 25. Course materials
CREATE TABLE course_materials (
    material_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    material_type TEXT CHECK(material_type IN ('Textbook', 'Reference', 'Online', 'Lab Manual')),
    title TEXT NOT NULL,
    author TEXT,
    isbn TEXT,
    is_required BOOLEAN DEFAULT 1,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- 26. Course objectives
CREATE TABLE course_objectives (
    objective_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    objective_text TEXT NOT NULL,
    order_number INTEGER,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- 27. Course topics
CREATE TABLE course_topics (
    topic_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    topic_name TEXT NOT NULL,
    week_number INTEGER,
    hours INTEGER,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- 28. Course evaluations
CREATE TABLE course_evaluations (
    evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    rating INTEGER CHECK(rating BETWEEN 1 AND 5),
    comments TEXT,
    evaluation_date DATE,
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 29. Course categories
CREATE TABLE course_categories (
    category_id TEXT PRIMARY KEY,
    category_name TEXT NOT NULL,
    description TEXT
);

-- 30. Course category mappings
CREATE TABLE course_category_mappings (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    FOREIGN KEY (category_id) REFERENCES course_categories(category_id)
);

-- ============================================
-- SECTION 4: Faculty and Instructors (10 tables)
-- ============================================

-- 31. Faculty
CREATE TABLE faculty (
    faculty_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    title TEXT CHECK(title IN ('Professor', 'Associate Professor', 'Assistant Professor', 'Lecturer', 'Instructor')),
    department_id TEXT,
    email TEXT,
    phone TEXT,
    office_location TEXT,
    hire_date DATE,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

-- 32. Faculty qualifications
CREATE TABLE faculty_qualifications (
    qualification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id TEXT NOT NULL,
    degree_type TEXT,
    field_of_study TEXT,
    institution TEXT,
    graduation_year INTEGER,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)
);

-- 33. Faculty research interests
CREATE TABLE faculty_research_interests (
    interest_id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id TEXT NOT NULL,
    research_area TEXT NOT NULL,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)
);

-- 34. Faculty publications
CREATE TABLE faculty_publications (
    publication_id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id TEXT NOT NULL,
    title TEXT NOT NULL,
    publication_type TEXT,
    journal_name TEXT,
    publication_year INTEGER,
    citation_count INTEGER DEFAULT 0,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)
);

-- 35. Section instructors
CREATE TABLE section_instructors (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id TEXT NOT NULL,
    faculty_id TEXT NOT NULL,
    role TEXT CHECK(role IN ('Primary', 'Assistant', 'Guest')),
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id),
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)
);

-- 36. Faculty office hours
CREATE TABLE faculty_office_hours (
    office_hour_id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id TEXT NOT NULL,
    day_of_week TEXT,
    start_time TIME,
    end_time TIME,
    location TEXT,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)
);

-- 37. Faculty awards
CREATE TABLE faculty_awards (
    award_id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id TEXT NOT NULL,
    award_name TEXT NOT NULL,
    awarding_organization TEXT,
    award_date DATE,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)
);

-- 38. Faculty committees
CREATE TABLE faculty_committees (
    committee_id TEXT PRIMARY KEY,
    committee_name TEXT NOT NULL,
    purpose TEXT,
    established_date DATE
);

-- 39. Faculty committee memberships
CREATE TABLE faculty_committee_memberships (
    membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id TEXT NOT NULL,
    committee_id TEXT NOT NULL,
    role TEXT,
    start_date DATE,
    end_date DATE,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id),
    FOREIGN KEY (committee_id) REFERENCES faculty_committees(committee_id)
);

-- 40. Faculty teaching loads
CREATE TABLE faculty_teaching_loads (
    load_id INTEGER PRIMARY KEY AUTOINCREMENT,
    faculty_id TEXT NOT NULL,
    semester TEXT NOT NULL,
    year INTEGER NOT NULL,
    total_credits INTEGER,
    total_students INTEGER,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)
);

-- ============================================
-- SECTION 5: Enrollments (10 tables)
-- ============================================

-- 41. Student enrollments
CREATE TABLE student_enrollments (
    enrollment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    enrollment_date DATE NOT NULL,
    enrollment_status TEXT CHECK(enrollment_status IN ('Enrolled', 'Dropped', 'Completed', 'Withdrawn')),
    grade TEXT,
    grade_points REAL,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 42. Enrollment waitlists
CREATE TABLE enrollment_waitlists (
    waitlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    position INTEGER,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT CHECK(status IN ('Waiting', 'Enrolled', 'Expired')),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 43. Enrollment permissions
CREATE TABLE enrollment_permissions (
    permission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    granted_by TEXT,
    granted_date DATE,
    reason TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 44. Credit transfers
CREATE TABLE credit_transfers (
    transfer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    source_institution TEXT NOT NULL,
    course_name TEXT NOT NULL,
    credits_transferred INTEGER,
    equivalent_course_id TEXT,
    approval_date DATE,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (equivalent_course_id) REFERENCES courses(course_id)
);

-- 45. Course drops
CREATE TABLE course_drops (
    drop_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    drop_date DATE NOT NULL,
    reason TEXT,
    refund_amount REAL,
    FOREIGN KEY (enrollment_id) REFERENCES student_enrollments(enrollment_id)
);

-- 46. Course withdrawals
CREATE TABLE course_withdrawals (
    withdrawal_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    withdrawal_date DATE NOT NULL,
    reason TEXT,
    approved_by TEXT,
    FOREIGN KEY (enrollment_id) REFERENCES student_enrollments(enrollment_id)
);

-- 47. Grade changes
CREATE TABLE grade_changes (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    old_grade TEXT,
    new_grade TEXT,
    change_date DATE NOT NULL,
    changed_by TEXT,
    reason TEXT,
    FOREIGN KEY (enrollment_id) REFERENCES student_enrollments(enrollment_id)
);

-- 48. Incomplete grades
CREATE TABLE incomplete_grades (
    incomplete_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    assigned_date DATE NOT NULL,
    completion_deadline DATE,
    reason TEXT,
    status TEXT CHECK(status IN ('Pending', 'Completed', 'Expired')),
    FOREIGN KEY (enrollment_id) REFERENCES student_enrollments(enrollment_id)
);

-- 49. Audit enrollments
CREATE TABLE audit_enrollments (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    enrollment_date DATE NOT NULL,
    completion_status TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 50. Pass/Fail enrollments
CREATE TABLE pass_fail_enrollments (
    pf_id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER NOT NULL,
    request_date DATE NOT NULL,
    approved BOOLEAN,
    final_result TEXT CHECK(final_result IN ('Pass', 'Fail', 'Pending')),
    FOREIGN KEY (enrollment_id) REFERENCES student_enrollments(enrollment_id)
);

-- ============================================
-- SECTION 6: Exams and Assessments (10 tables)
-- ============================================

-- 51. Exams
CREATE TABLE exams (
    exam_id TEXT PRIMARY KEY,
    section_id TEXT NOT NULL,
    exam_type TEXT CHECK(exam_type IN ('Midterm', 'Final', 'Quiz', 'Practical', 'Oral')),
    exam_date DATE NOT NULL,
    start_time TIME,
    duration_minutes INTEGER,
    total_points REAL NOT NULL,
    weight_percentage REAL,
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 52. Exam scores
CREATE TABLE exam_scores (
    score_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    score REAL,
    percentage REAL,
    grade TEXT,
    submitted_date TIMESTAMP,
    FOREIGN KEY (exam_id) REFERENCES exams(exam_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 53. Exam questions
CREATE TABLE exam_questions (
    question_id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id TEXT NOT NULL,
    question_number INTEGER,
    question_text TEXT,
    question_type TEXT CHECK(question_type IN ('Multiple Choice', 'Essay', 'Short Answer', 'True/False')),
    points REAL,
    FOREIGN KEY (exam_id) REFERENCES exams(exam_id)
);

-- 54. Assignments
CREATE TABLE assignments (
    assignment_id TEXT PRIMARY KEY,
    section_id TEXT NOT NULL,
    assignment_name TEXT NOT NULL,
    description TEXT,
    due_date DATE NOT NULL,
    total_points REAL NOT NULL,
    weight_percentage REAL,
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 55. Assignment submissions
CREATE TABLE assignment_submissions (
    submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    submission_date TIMESTAMP,
    score REAL,
    feedback TEXT,
    late_days INTEGER DEFAULT 0,
    FOREIGN KEY (assignment_id) REFERENCES assignments(assignment_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 56. Projects
CREATE TABLE projects (
    project_id TEXT PRIMARY KEY,
    section_id TEXT NOT NULL,
    project_name TEXT NOT NULL,
    description TEXT,
    start_date DATE,
    due_date DATE NOT NULL,
    total_points REAL NOT NULL,
    is_group_project BOOLEAN DEFAULT 0,
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 57. Project submissions
CREATE TABLE project_submissions (
    submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    submission_date TIMESTAMP,
    score REAL,
    feedback TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(project_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 58. Lab reports
CREATE TABLE lab_reports (
    report_id TEXT PRIMARY KEY,
    section_id TEXT NOT NULL,
    lab_number INTEGER,
    title TEXT NOT NULL,
    due_date DATE NOT NULL,
    total_points REAL NOT NULL,
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 59. Lab report submissions
CREATE TABLE lab_report_submissions (
    submission_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    submission_date TIMESTAMP,
    score REAL,
    feedback TEXT,
    FOREIGN KEY (report_id) REFERENCES lab_reports(report_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 60. Participation grades
CREATE TABLE participation_grades (
    participation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    grade REAL,
    comments TEXT,
    grading_period TEXT,
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- ============================================
-- SECTION 7: Attendance (10 tables)
-- ============================================

-- 61. Class sessions
CREATE TABLE class_sessions (
    session_id TEXT PRIMARY KEY,
    section_id TEXT NOT NULL,
    session_date DATE NOT NULL,
    session_number INTEGER,
    topic TEXT,
    notes TEXT,
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 62. Attendance records
CREATE TABLE attendance_records (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    student_id TEXT NOT NULL,
    status TEXT CHECK(status IN ('Present', 'Absent', 'Late', 'Excused')),
    check_in_time TIME,
    notes TEXT,
    FOREIGN KEY (session_id) REFERENCES class_sessions(session_id),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 63. Absence requests
CREATE TABLE absence_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    request_date DATE NOT NULL,
    approved BOOLEAN,
    approved_by TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (session_id) REFERENCES class_sessions(session_id)
);

-- 64. Late arrivals
CREATE TABLE late_arrivals (
    late_id INTEGER PRIMARY KEY AUTOINCREMENT,
    attendance_id INTEGER NOT NULL,
    minutes_late INTEGER,
    reason TEXT,
    FOREIGN KEY (attendance_id) REFERENCES attendance_records(attendance_id)
);

-- 65. Attendance policies
CREATE TABLE attendance_policies (
    policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id TEXT NOT NULL,
    max_absences INTEGER,
    late_policy TEXT,
    penalty_description TEXT,
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 66. Attendance summaries
CREATE TABLE attendance_summaries (
    summary_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    total_sessions INTEGER,
    present_count INTEGER,
    absent_count INTEGER,
    late_count INTEGER,
    excused_count INTEGER,
    attendance_percentage REAL,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 67. Lab attendance
CREATE TABLE lab_attendance (
    lab_attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    lab_date DATE NOT NULL,
    status TEXT CHECK(status IN ('Present', 'Absent', 'Late')),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- 68. Clinical rotation attendance
CREATE TABLE clinical_rotation_attendance (
    rotation_attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    rotation_id TEXT NOT NULL,
    date DATE NOT NULL,
    hours_completed REAL,
    status TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 69. Seminar attendance
CREATE TABLE seminar_attendance (
    seminar_attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    seminar_id TEXT NOT NULL,
    attendance_date DATE NOT NULL,
    status TEXT CHECK(status IN ('Present', 'Absent')),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 70. Attendance warnings
CREATE TABLE attendance_warnings (
    warning_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    section_id TEXT NOT NULL,
    warning_date DATE NOT NULL,
    warning_type TEXT,
    message TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (section_id) REFERENCES course_sections(section_id)
);

-- ============================================
-- SECTION 8: Graduation and Career (10 tables)
-- ============================================

-- 71. Graduation requirements
CREATE TABLE graduation_requirements (
    requirement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    program_id TEXT NOT NULL,
    requirement_type TEXT,
    description TEXT,
    credits_required INTEGER,
    FOREIGN KEY (program_id) REFERENCES programs(program_id)
);

-- 72. Student graduation status
CREATE TABLE student_graduation_status (
    status_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    total_credits_earned REAL,
    gpa REAL,
    requirements_met BOOLEAN DEFAULT 0,
    expected_graduation_date DATE,
    actual_graduation_date DATE,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 73. Graduation applications
CREATE TABLE graduation_applications (
    application_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    application_date DATE NOT NULL,
    intended_graduation_date DATE,
    status TEXT CHECK(status IN ('Pending', 'Approved', 'Denied', 'Completed')),
    reviewed_by TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 74. Degree conferrals
CREATE TABLE degree_conferrals (
    conferral_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    degree_type TEXT NOT NULL,
    major_id TEXT,
    conferral_date DATE NOT NULL,
    honors TEXT CHECK(honors IN ('Summa Cum Laude', 'Magna Cum Laude', 'Cum Laude', 'None')),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (major_id) REFERENCES majors(major_id)
);

-- 75. Alumni records
CREATE TABLE alumni_records (
    alumni_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    graduation_year INTEGER NOT NULL,
    current_employer TEXT,
    current_position TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 76. Career placements
CREATE TABLE career_placements (
    placement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    employer_name TEXT NOT NULL,
    position_title TEXT,
    start_date DATE,
    salary_range TEXT,
    employment_type TEXT CHECK(employment_type IN ('Full-time', 'Part-time', 'Contract', 'Internship')),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 77. Internships
CREATE TABLE internships (
    internship_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    organization_name TEXT NOT NULL,
    position TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    hours_completed REAL,
    supervisor_name TEXT,
    evaluation_score REAL,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 78. Residency placements
CREATE TABLE residency_placements (
    residency_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    hospital_name TEXT NOT NULL,
    specialty TEXT,
    start_date DATE NOT NULL,
    duration_years INTEGER,
    match_status TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 79. Job search activities
CREATE TABLE job_search_activities (
    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    activity_type TEXT CHECK(activity_type IN ('Application', 'Interview', 'Offer', 'Rejection')),
    company_name TEXT,
    position TEXT,
    activity_date DATE,
    notes TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 80. Career counseling sessions
CREATE TABLE career_counseling_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    counselor_name TEXT,
    session_date DATE NOT NULL,
    topics_discussed TEXT,
    follow_up_needed BOOLEAN DEFAULT 0,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- ============================================
-- SECTION 9: Financial and Administrative (10 tables)
-- ============================================

-- 81. Tuition fees
CREATE TABLE tuition_fees (
    fee_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    semester TEXT NOT NULL,
    year INTEGER NOT NULL,
    tuition_amount REAL NOT NULL,
    other_fees REAL DEFAULT 0,
    total_amount REAL NOT NULL,
    due_date DATE NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 82. Payments
CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    payment_date DATE NOT NULL,
    amount REAL NOT NULL,
    payment_method TEXT CHECK(payment_method IN ('Cash', 'Credit Card', 'Bank Transfer', 'Scholarship')),
    reference_number TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 83. Financial aid
CREATE TABLE financial_aid (
    aid_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    aid_type TEXT CHECK(aid_type IN ('Grant', 'Loan', 'Scholarship', 'Work-Study')),
    amount REAL NOT NULL,
    academic_year TEXT NOT NULL,
    status TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 84. Student loans
CREATE TABLE student_loans (
    loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    lender_name TEXT NOT NULL,
    loan_amount REAL NOT NULL,
    interest_rate REAL,
    disbursement_date DATE,
    repayment_start_date DATE,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 85. Rooms and facilities
CREATE TABLE rooms (
    room_id TEXT PRIMARY KEY,
    building TEXT NOT NULL,
    room_number TEXT NOT NULL,
    capacity INTEGER,
    room_type TEXT CHECK(room_type IN ('Classroom', 'Lab', 'Lecture Hall', 'Office', 'Study Room')),
    equipment TEXT
);

-- 86. Room reservations
CREATE TABLE room_reservations (
    reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id TEXT NOT NULL,
    reserved_by TEXT NOT NULL,
    reservation_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    purpose TEXT,
    FOREIGN KEY (room_id) REFERENCES rooms(room_id)
);

-- 87. Library resources
CREATE TABLE library_resources (
    resource_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    resource_type TEXT CHECK(resource_type IN ('Book', 'Journal', 'Database', 'Media')),
    isbn TEXT,
    available_copies INTEGER DEFAULT 1,
    total_copies INTEGER DEFAULT 1
);

-- 88. Library checkouts
CREATE TABLE library_checkouts (
    checkout_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    checkout_date DATE NOT NULL,
    due_date DATE NOT NULL,
    return_date DATE,
    fine_amount REAL DEFAULT 0,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (resource_id) REFERENCES library_resources(resource_id)
);

-- 89. Student organizations
CREATE TABLE student_organizations (
    organization_id TEXT PRIMARY KEY,
    organization_name TEXT NOT NULL,
    category TEXT,
    established_date DATE,
    advisor_faculty_id TEXT,
    description TEXT
);

-- 90. Organization memberships
CREATE TABLE organization_memberships (
    membership_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    organization_id TEXT NOT NULL,
    join_date DATE NOT NULL,
    role TEXT,
    status TEXT CHECK(status IN ('Active', 'Inactive')),
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (organization_id) REFERENCES student_organizations(organization_id)
);

-- ============================================
-- SECTION 10: Clinical and Research (10 tables)
-- ============================================

-- 91. Clinical rotations
CREATE TABLE clinical_rotations (
    rotation_id TEXT PRIMARY KEY,
    rotation_name TEXT NOT NULL,
    department TEXT,
    duration_weeks INTEGER,
    required_hours INTEGER,
    description TEXT
);

-- 92. Student clinical assignments
CREATE TABLE student_clinical_assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    rotation_id TEXT NOT NULL,
    hospital_name TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    supervisor_name TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (rotation_id) REFERENCES clinical_rotations(rotation_id)
);

-- 93. Clinical evaluations
CREATE TABLE clinical_evaluations (
    evaluation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL,
    evaluation_date DATE NOT NULL,
    clinical_skills_score REAL,
    professionalism_score REAL,
    communication_score REAL,
    overall_score REAL,
    comments TEXT,
    FOREIGN KEY (assignment_id) REFERENCES student_clinical_assignments(assignment_id)
);

-- 94. Research projects
CREATE TABLE research_projects (
    project_id TEXT PRIMARY KEY,
    project_title TEXT NOT NULL,
    principal_investigator TEXT,
    department_id TEXT,
    start_date DATE,
    end_date DATE,
    funding_amount REAL,
    status TEXT CHECK(status IN ('Active', 'Completed', 'Suspended')),
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

-- 95. Student research participation
CREATE TABLE student_research_participation (
    participation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    role TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    hours_contributed REAL,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (project_id) REFERENCES research_projects(project_id)
);

-- 96. Thesis submissions
CREATE TABLE thesis_submissions (
    thesis_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    title TEXT NOT NULL,
    submission_date DATE NOT NULL,
    defense_date DATE,
    advisor_id TEXT,
    status TEXT CHECK(status IN ('In Progress', 'Submitted', 'Approved', 'Rejected')),
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 97. Thesis committee members
CREATE TABLE thesis_committee_members (
    committee_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    thesis_id INTEGER NOT NULL,
    faculty_id TEXT NOT NULL,
    role TEXT CHECK(role IN ('Chair', 'Member', 'External')),
    FOREIGN KEY (thesis_id) REFERENCES thesis_submissions(thesis_id),
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)
);

-- 98. Medical licenses
CREATE TABLE medical_licenses (
    license_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    license_type TEXT NOT NULL,
    license_number TEXT UNIQUE,
    issue_date DATE NOT NULL,
    expiry_date DATE,
    issuing_authority TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 99. Certifications
CREATE TABLE certifications (
    certification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    certification_name TEXT NOT NULL,
    issuing_organization TEXT,
    issue_date DATE NOT NULL,
    expiry_date DATE,
    certification_number TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);

-- 100. Student achievements
CREATE TABLE student_achievements (
    achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    achievement_type TEXT CHECK(achievement_type IN ('Award', 'Publication', 'Presentation', 'Competition', 'Honor')),
    title TEXT NOT NULL,
    description TEXT,
    date_achieved DATE NOT NULL,
    organization TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
);
