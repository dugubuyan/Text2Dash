"""
Generate test data for medical school database
Creates 30-50 rows of realistic test data for each table
"""

import random
import string
from datetime import datetime, timedelta
from typing import List, Tuple

# Configuration
STUDENTS_COUNT = 50
FACULTY_COUNT = 30
COURSES_COUNT = 40
DEPARTMENTS_COUNT = 8
PROGRAMS_COUNT = 5

# Helper functions
def random_date(start_year=2018, end_year=2024):
    """Generate a random date between start_year and end_year"""
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = end - start
    random_days = random.randint(0, delta.days)
    return (start + timedelta(days=random_days)).strftime('%Y-%m-%d')

def random_id(prefix, length=6):
    """Generate a random ID with prefix"""
    return f"{prefix}{random.randint(10**(length-1), 10**length-1)}"

def random_phone():
    """Generate a random Chinese phone number"""
    return f"1{random.randint(3, 9)}{random.randint(100000000, 999999999)}"

def random_email(name):
    """Generate an email address"""
    domains = ['gmail.com', 'qq.com', '163.com', 'outlook.com']
    return f"{name.lower().replace(' ', '.')}@{random.choice(domains)}"

def sql_escape(value):
    """Escape single quotes in SQL strings"""
    if value is None:
        return 'NULL'
    if isinstance(value, str):
        return f"'{value.replace(chr(39), chr(39)+chr(39))}'"
    return str(value)

# Chinese names
SURNAMES = ['王', '李', '张', '刘', '陈', '杨', '黄', '赵', '周', '吴', '徐', '孙', '马', '朱', '胡', '郭', '何', '林', '罗', '高']
GIVEN_NAMES = ['伟', '芳', '娜', '秀英', '敏', '静', '丽', '强', '磊', '军', '洋', '勇', '艳', '杰', '涛', '明', '超', '秀兰', '霞', '平']

def random_chinese_name():
    """Generate a random Chinese name"""
    return random.choice(SURNAMES) + random.choice(GIVEN_NAMES) + (random.choice(GIVEN_NAMES) if random.random() > 0.5 else '')


# Data generation functions
def generate_students():
    """Generate student records"""
    students = []
    statuses = ['Active', 'Graduated', 'Suspended', 'Withdrawn']
    genders = ['M', 'F']
    
    for i in range(STUDENTS_COUNT):
        student_id = f"S{2020000 + i}"
        name = random_chinese_name()
        gender = random.choice(genders)
        dob = random_date(1995, 2005)
        id_card = f"{random.randint(100000, 999999)}{random_date(1995, 2005).replace('-', '')}{random.randint(1000, 9999)}"
        phone = random_phone()
        email = random_email(f"student{i}")
        admission = random_date(2018, 2023)
        graduation = random_date(2022, 2024) if random.random() > 0.6 else None
        status = random.choice(statuses)
        
        students.append((student_id, name, gender, dob, id_card, phone, email, admission, graduation, status))
    
    return students

def generate_departments():
    """Generate department records"""
    dept_names = [
        '基础医学系', '临床医学系', '预防医学系', '药学系',
        '护理学系', '医学检验系', '医学影像系', '口腔医学系'
    ]
    departments = []
    
    for i, name in enumerate(dept_names):
        dept_id = f"DEPT{i+1:03d}"
        head_faculty = f"F{random.randint(1, 30):03d}"
        building = f"Building {chr(65+i)}"
        phone = random_phone()
        email = random_email(f"dept{i}")
        established = random_date(1980, 2010)
        
        departments.append((dept_id, name, head_faculty, building, phone, email, established))
    
    return departments

def generate_programs():
    """Generate program records"""
    programs = [
        ('PROG001', '临床医学本科', 'Bachelor', 5, 240, 'DEPT002'),
        ('PROG002', '基础医学硕士', 'Master', 3, 90, 'DEPT001'),
        ('PROG003', '预防医学本科', 'Bachelor', 5, 240, 'DEPT003'),
        ('PROG004', '药学本科', 'Bachelor', 4, 180, 'DEPT004'),
        ('PROG005', '护理学本科', 'Bachelor', 4, 160, 'DEPT005')
    ]
    
    return programs

def generate_faculty():
    """Generate faculty records"""
    faculty = []
    titles = ['Professor', 'Associate Professor', 'Assistant Professor', 'Lecturer', 'Instructor']
    
    for i in range(FACULTY_COUNT):
        faculty_id = f"F{i+1:03d}"
        name = random_chinese_name()
        title = random.choice(titles)
        dept_id = f"DEPT{random.randint(1, DEPARTMENTS_COUNT):03d}"
        email = random_email(f"faculty{i}")
        phone = random_phone()
        office = f"Room {random.randint(100, 999)}"
        hire_date = random_date(2000, 2023)
        
        faculty.append((faculty_id, name, title, dept_id, email, phone, office, hire_date))
    
    return faculty

def generate_courses():
    """Generate course records"""
    course_names = [
        '人体解剖学', '生理学', '病理学', '药理学', '内科学', '外科学', '儿科学', '妇产科学',
        '预防医学', '流行病学', '卫生统计学', '医学微生物学', '医学免疫学', '生物化学',
        '组织胚胎学', '医学遗传学', '医学影像学', '临床诊断学', '急救医学', '全科医学',
        '中医学基础', '针灸学', '推拿学', '医学伦理学', '医学心理学', '医患沟通',
        '临床技能训练', '医学英语', '医学文献检索', '循证医学', '医学统计软件应用',
        '分子生物学', '细胞生物学', '神经生物学', '医学遗传咨询', '康复医学',
        '老年医学', '精神病学', '皮肤性病学', '眼科学', '耳鼻喉科学'
    ]
    
    courses = []
    levels = ['Undergraduate', 'Graduate', 'Both']
    
    for i in range(COURSES_COUNT):
        course_id = f"C{i+1:04d}"
        course_name = course_names[i] if i < len(course_names) else f"Course {i+1}"
        course_code = f"MED{random.randint(1000, 9999)}"
        credits = random.choice([2, 3, 4, 5])
        dept_id = f"DEPT{random.randint(1, DEPARTMENTS_COUNT):03d}"
        description = f"{course_name}课程描述"
        level = random.choice(levels)
        
        courses.append((course_id, course_name, course_code, credits, dept_id, description, level))
    
    return courses

def generate_sql_inserts(table_name: str, columns: List[str], data: List[Tuple]) -> str:
    """Generate SQL INSERT statements"""
    if not data:
        return ""
    
    sql_lines = [f"\n-- Insert data into {table_name}"]
    
    for row in data:
        values = []
        for val in row:
            if val is None:
                values.append('NULL')
            elif isinstance(val, (int, float)):
                values.append(str(val))
            else:
                # Escape single quotes
                escaped = str(val).replace("'", "''")
                values.append(f"'{escaped}'")
        
        sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});"
        sql_lines.append(sql)
    
    return '\n'.join(sql_lines)

def main():
    """Generate all test data and create SQL file"""
    output_file = 'data/test_data.sql'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("-- Medical School Test Data\n")
        f.write("-- Generated test data for all tables\n")
        f.write(f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Generate and write students
        students = generate_students()
        sql = generate_sql_inserts('students', 
            ['student_id', 'name', 'gender', 'date_of_birth', 'id_card_number', 
             'phone', 'email', 'admission_date', 'graduation_date', 'status'],
            students)
        f.write(sql + '\n')
        
        # Generate and write departments
        departments = generate_departments()
        sql = generate_sql_inserts('departments',
            ['department_id', 'department_name', 'head_faculty_id', 'building', 
             'phone', 'email', 'established_date'],
            departments)
        f.write(sql + '\n')
        
        # Generate and write programs
        programs = generate_programs()
        sql = generate_sql_inserts('programs',
            ['program_id', 'program_name', 'degree_type', 'duration_years', 
             'total_credits_required', 'department_id'],
            programs)
        f.write(sql + '\n')
        
        # Generate and write faculty
        faculty = generate_faculty()
        sql = generate_sql_inserts('faculty',
            ['faculty_id', 'name', 'title', 'department_id', 'email', 
             'phone', 'office_location', 'hire_date'],
            faculty)
        f.write(sql + '\n')
        
        # Generate and write courses
        courses = generate_courses()
        sql = generate_sql_inserts('courses',
            ['course_id', 'course_name', 'course_code', 'credits', 
             'department_id', 'description', 'level'],
            courses)
        f.write(sql + '\n')
        
        # Generate student addresses (30-50 records)
        addresses = []
        address_types = ['Home', 'Dorm', 'Emergency']
        cities = ['北京', '上海', '广州', '深圳', '杭州', '南京', '武汉', '成都']
        provinces = ['北京市', '上海市', '广东省', '浙江省', '江苏省', '湖北省', '四川省']
        
        for i in range(40):
            student_id = f"S{2020000 + random.randint(0, STUDENTS_COUNT-1)}"
            addr_type = random.choice(address_types)
            street = f"{random.choice(['中山路', '人民路', '解放路', '建设路'])}{random.randint(1, 999)}号"
            city = random.choice(cities)
            province = random.choice(provinces)
            postal = f"{random.randint(100000, 999999)}"
            
            addresses.append((student_id, addr_type, street, city, province, postal, 'China'))
        
        sql = generate_sql_inserts('student_addresses',
            ['student_id', 'address_type', 'street', 'city', 'province', 'postal_code', 'country'],
            addresses)
        f.write(sql + '\n')
        
        # Generate emergency contacts (30-50 records)
        contacts = []
        relationships = ['父亲', '母亲', '配偶', '兄弟', '姐妹', '其他亲属']
        
        for i in range(45):
            student_id = f"S{2020000 + random.randint(0, STUDENTS_COUNT-1)}"
            contact_name = random_chinese_name()
            relationship = random.choice(relationships)
            phone = random_phone()
            email = random_email(f"contact{i}") if random.random() > 0.3 else None
            
            contacts.append((student_id, contact_name, relationship, phone, email))
        
        sql = generate_sql_inserts('student_emergency_contacts',
            ['student_id', 'contact_name', 'relationship', 'phone', 'email'],
            contacts)
        f.write(sql + '\n')
        
        # Generate course sections (35 records)
        sections = []
        semesters = ['Fall', 'Spring', 'Summer']
        years = [2022, 2023, 2024]
        
        for i in range(35):
            section_id = f"SEC{i+1:04d}"
            course_id = f"C{random.randint(1, COURSES_COUNT):04d}"
            semester = random.choice(semesters)
            year = random.choice(years)
            section_num = f"{random.randint(1, 5):02d}"
            max_cap = random.choice([30, 40, 50, 60])
            enrolled = random.randint(20, max_cap)
            
            sections.append((section_id, course_id, semester, year, section_num, max_cap, enrolled))
        
        sql = generate_sql_inserts('course_sections',
            ['section_id', 'course_id', 'semester', 'year', 'section_number', 
             'max_capacity', 'enrolled_count'],
            sections)
        f.write(sql + '\n')
        
        # Generate student enrollments (50 records)
        enrollments = []
        statuses = ['Enrolled', 'Completed', 'Dropped', 'Withdrawn']
        grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D', 'F']
        
        for i in range(50):
            student_id = f"S{2020000 + random.randint(0, STUDENTS_COUNT-1)}"
            section_id = f"SEC{random.randint(1, 35):04d}"
            enroll_date = random_date(2022, 2024)
            status = random.choice(statuses)
            grade = random.choice(grades) if status == 'Completed' else None
            grade_points = {'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7, 
                          'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D': 1.0, 'F': 0.0}.get(grade)
            
            enrollments.append((student_id, section_id, enroll_date, status, grade, grade_points))
        
        sql = generate_sql_inserts('student_enrollments',
            ['student_id', 'section_id', 'enrollment_date', 'enrollment_status', 
             'grade', 'grade_points'],
            enrollments)
        f.write(sql + '\n')
        
        # Generate exams (40 records)
        exams = []
        exam_types = ['Midterm', 'Final', 'Quiz', 'Practical', 'Oral']
        
        for i in range(40):
            exam_id = f"E{i+1:04d}"
            section_id = f"SEC{random.randint(1, 35):04d}"
            exam_type = random.choice(exam_types)
            exam_date = random_date(2023, 2024)
            start_time = f"{random.randint(8, 16):02d}:00:00"
            duration = random.choice([60, 90, 120, 180])
            total_points = random.choice([100, 150, 200])
            weight = random.choice([0.2, 0.3, 0.4, 0.5])
            
            exams.append((exam_id, section_id, exam_type, exam_date, start_time, 
                         duration, total_points, weight))
        
        sql = generate_sql_inserts('exams',
            ['exam_id', 'section_id', 'exam_type', 'exam_date', 'start_time', 
             'duration_minutes', 'total_points', 'weight_percentage'],
            exams)
        f.write(sql + '\n')
        
        # Generate exam scores (50 records)
        exam_scores = []
        
        for i in range(50):
            exam_id = f"E{random.randint(1, 40):04d}"
            student_id = f"S{2020000 + random.randint(0, STUDENTS_COUNT-1)}"
            score = random.uniform(50, 100)
            percentage = score
            grade = 'A' if score >= 90 else 'B' if score >= 80 else 'C' if score >= 70 else 'D' if score >= 60 else 'F'
            submitted = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            exam_scores.append((exam_id, student_id, round(score, 2), round(percentage, 2), 
                              grade, submitted))
        
        sql = generate_sql_inserts('exam_scores',
            ['exam_id', 'student_id', 'score', 'percentage', 'grade', 'submitted_date'],
            exam_scores)
        f.write(sql + '\n')
        
        # Generate class sessions (35 records)
        sessions = []
        
        for i in range(35):
            session_id = f"SESS{i+1:04d}"
            section_id = f"SEC{random.randint(1, 35):04d}"
            session_date = random_date(2023, 2024)
            session_num = i + 1
            topic = f"Topic {i+1}"
            notes = f"Session notes for topic {i+1}"
            
            sessions.append((session_id, section_id, session_date, session_num, topic, notes))
        
        sql = generate_sql_inserts('class_sessions',
            ['session_id', 'section_id', 'session_date', 'session_number', 'topic', 'notes'],
            sessions)
        f.write(sql + '\n')
        
        # Generate attendance records (50 records)
        attendance = []
        statuses = ['Present', 'Absent', 'Late', 'Excused']
        
        for i in range(50):
            session_id = f"SESS{random.randint(1, 35):04d}"
            student_id = f"S{2020000 + random.randint(0, STUDENTS_COUNT-1)}"
            status = random.choice(statuses)
            check_in = f"{random.randint(8, 10):02d}:{random.randint(0, 59):02d}:00" if status in ['Present', 'Late'] else None
            notes = "Late arrival" if status == 'Late' else None
            
            attendance.append((session_id, student_id, status, check_in, notes))
        
        sql = generate_sql_inserts('attendance_records',
            ['session_id', 'student_id', 'status', 'check_in_time', 'notes'],
            attendance)
        f.write(sql + '\n')
        
        # Generate student majors (45 records)
        student_majors = []
        majors_list = ['MAJ001', 'MAJ002', 'MAJ003', 'MAJ004', 'MAJ005']
        
        for i in range(45):
            student_id = f"S{2020000 + random.randint(0, STUDENTS_COUNT-1)}"
            major_id = random.choice(majors_list)
            start_date = random_date(2020, 2023)
            end_date = random_date(2023, 2025) if random.random() > 0.7 else None
            is_primary = 1
            
            student_majors.append((student_id, major_id, start_date, end_date, is_primary))
        
        # First, generate majors data
        majors = [
            ('MAJ001', '临床医学', 'PROG001', 'DEPT002', '临床医学专业'),
            ('MAJ002', '基础医学', 'PROG002', 'DEPT001', '基础医学专业'),
            ('MAJ003', '预防医学', 'PROG003', 'DEPT003', '预防医学专业'),
            ('MAJ004', '药学', 'PROG004', 'DEPT004', '药学专业'),
            ('MAJ005', '护理学', 'PROG005', 'DEPT005', '护理学专业')
        ]
        
        sql = generate_sql_inserts('majors',
            ['major_id', 'major_name', 'program_id', 'department_id', 'description'],
            majors)
        f.write(sql + '\n')
        
        sql = generate_sql_inserts('student_majors',
            ['student_id', 'major_id', 'start_date', 'end_date', 'is_primary'],
            student_majors)
        f.write(sql + '\n')
        
        # Generate graduation status (40 records)
        grad_status = []
        
        for i in range(40):
            student_id = f"S{2020000 + random.randint(0, STUDENTS_COUNT-1)}"
            credits = random.uniform(120, 240)
            gpa = random.uniform(2.5, 4.0)
            req_met = 1 if credits >= 180 and gpa >= 2.0 else 0
            expected = random_date(2024, 2026)
            actual = random_date(2024, 2025) if req_met and random.random() > 0.5 else None
            
            grad_status.append((student_id, round(credits, 1), round(gpa, 2), 
                              req_met, expected, actual))
        
        sql = generate_sql_inserts('student_graduation_status',
            ['student_id', 'total_credits_earned', 'gpa', 'requirements_met', 
             'expected_graduation_date', 'actual_graduation_date'],
            grad_status)
        f.write(sql + '\n')
        
        # Generate career placements (30 records)
        placements = []
        employers = ['北京协和医院', '上海瑞金医院', '广州中山医院', '深圳人民医院', 
                    '杭州第一医院', '南京鼓楼医院', '武汉同济医院', '成都华西医院']
        positions = ['住院医师', '主治医师', '医学研究员', '临床医生', '全科医生']
        emp_types = ['Full-time', 'Part-time', 'Contract', 'Internship']
        
        for i in range(30):
            student_id = f"S{2020000 + random.randint(0, STUDENTS_COUNT-1)}"
            employer = random.choice(employers)
            position = random.choice(positions)
            start_date = random_date(2023, 2024)
            salary = random.choice(['5000-8000', '8000-12000', '12000-20000', '20000+'])
            emp_type = random.choice(emp_types)
            
            placements.append((student_id, employer, position, start_date, salary, emp_type))
        
        sql = generate_sql_inserts('career_placements',
            ['student_id', 'employer_name', 'position_title', 'start_date', 
             'salary_range', 'employment_type'],
            placements)
        f.write(sql + '\n')
        
        # Generate tuition fees (45 records)
        tuition = []
        semesters = ['Fall', 'Spring']
        
        for i in range(45):
            student_id = f"S{2020000 + random.randint(0, STUDENTS_COUNT-1)}"
            semester = random.choice(semesters)
            year = random.choice([2022, 2023, 2024])
            tuition_amt = random.choice([15000, 18000, 20000, 25000])
            other_fees = random.uniform(500, 2000)
            total = tuition_amt + other_fees
            due_date = f"{year}-{3 if semester == 'Spring' else 9}-01"
            
            tuition.append((student_id, semester, year, tuition_amt, 
                          round(other_fees, 2), round(total, 2), due_date))
        
        sql = generate_sql_inserts('tuition_fees',
            ['student_id', 'semester', 'year', 'tuition_amount', 'other_fees', 
             'total_amount', 'due_date'],
            tuition)
        f.write(sql + '\n')
        
        # Generate scholarships (35 records)
        scholarships = []
        scholarship_names = ['国家奖学金', '校级奖学金', '优秀学生奖学金', '学业进步奖', '科研创新奖']
        
        for i in range(35):
            student_id = f"S{2020000 + random.randint(0, STUDENTS_COUNT-1)}"
            name = random.choice(scholarship_names)
            amount = random.choice([3000, 5000, 8000, 10000])
            award_date = random_date(2022, 2024)
            academic_year = f"{random.choice([2022, 2023])}-{random.choice([2023, 2024])}"
            
            scholarships.append((student_id, name, amount, award_date, academic_year))
        
        sql = generate_sql_inserts('student_scholarships',
            ['student_id', 'scholarship_name', 'amount', 'award_date', 'academic_year'],
            scholarships)
        f.write(sql + '\n')
        
        # Generate section instructors (40 records)
        instructors = []
        roles = ['Primary', 'Assistant', 'Guest']
        
        for i in range(40):
            section_id = f"SEC{random.randint(1, 35):04d}"
            faculty_id = f"F{random.randint(1, FACULTY_COUNT):03d}"
            role = random.choice(roles)
            
            instructors.append((section_id, faculty_id, role))
        
        sql = generate_sql_inserts('section_instructors',
            ['section_id', 'faculty_id', 'role'],
            instructors)
        f.write(sql + '\n')
        
        # Generate rooms (30 records)
        rooms = []
        buildings = ['A', 'B', 'C', 'D', 'E']
        room_types = ['Classroom', 'Lab', 'Lecture Hall', 'Office', 'Study Room']
        
        for i in range(30):
            room_id = f"R{i+1:03d}"
            building = random.choice(buildings)
            room_num = f"{random.randint(100, 999)}"
            capacity = random.choice([30, 40, 50, 60, 100, 200])
            room_type = random.choice(room_types)
            equipment = "Projector, Whiteboard" if room_type in ['Classroom', 'Lecture Hall'] else "Lab Equipment"
            
            rooms.append((room_id, building, room_num, capacity, room_type, equipment))
        
        sql = generate_sql_inserts('rooms',
            ['room_id', 'building', 'room_number', 'capacity', 'room_type', 'equipment'],
            rooms)
        f.write(sql + '\n')
        
        # Generate clinical rotations (30 records)
        rotations = []
        rotation_names = ['内科轮转', '外科轮转', '儿科轮转', '妇产科轮转', '急诊轮转', 
                         '影像科轮转', '检验科轮转', '病理科轮转']
        
        for i in range(len(rotation_names)):
            rotation_id = f"ROT{i+1:03d}"
            name = rotation_names[i]
            dept = random.choice(['内科', '外科', '儿科', '妇产科', '急诊科'])
            duration = random.choice([4, 6, 8, 12])
            required_hours = duration * 40
            description = f"{name}临床实习"
            
            rotations.append((rotation_id, name, dept, duration, required_hours, description))
        
        sql = generate_sql_inserts('clinical_rotations',
            ['rotation_id', 'rotation_name', 'department', 'duration_weeks', 
             'required_hours', 'description'],
            rotations)
        f.write(sql + '\n')
        
        # Generate student clinical assignments (35 records)
        clinical_assignments = []
        hospitals = ['北京协和医院', '上海瑞金医院', '广州中山医院', '深圳人民医院']
        
        for i in range(35):
            student_id = f"S{2020000 + random.randint(0, STUDENTS_COUNT-1)}"
            rotation_id = f"ROT{random.randint(1, len(rotation_names)):03d}"
            hospital = random.choice(hospitals)
            start_date = random_date(2023, 2024)
            end_date = random_date(2024, 2025)
            supervisor = random_chinese_name()
            
            clinical_assignments.append((student_id, rotation_id, hospital, 
                                        start_date, end_date, supervisor))
        
        sql = generate_sql_inserts('student_clinical_assignments',
            ['student_id', 'rotation_id', 'hospital_name', 'start_date', 
             'end_date', 'supervisor_name'],
            clinical_assignments)
        f.write(sql + '\n')
        
        # Generate assignments (30 records)
        assignments = []
        
        for i in range(30):
            assignment_id = f"A{i+1:04d}"
            section_id = f"SEC{random.randint(1, 35):04d}"
            name = f"Assignment {i+1}"
            description = f"Complete assignment {i+1}"
            due_date = random_date(2023, 2024)
            total_points = random.choice([50, 100, 150])
            weight = random.choice([0.1, 0.15, 0.2])
            
            assignments.append((assignment_id, section_id, name, description, 
                              due_date, total_points, weight))
        
        sql = generate_sql_inserts('assignments',
            ['assignment_id', 'section_id', 'assignment_name', 'description', 
             'due_date', 'total_points', 'weight_percentage'],
            assignments)
        f.write(sql + '\n')
        
        # Generate academic advisors (20 records)
        advisors = []
        specializations = ['临床医学', '基础医学', '预防医学', '药学', '护理学', '医学影像', '医学检验']
        
        for i in range(20):
            advisor_id = f"ADV{i+1:03d}"
            faculty_id = f"F{i+1:03d}"  # Use first 20 faculty as advisors
            dept_id = f"DEPT{random.randint(1, DEPARTMENTS_COUNT):03d}"
            specialization = random.choice(specializations)
            max_students = random.choice([15, 20, 25, 30])
            
            advisors.append((advisor_id, faculty_id, dept_id, specialization, max_students))
        
        sql = generate_sql_inserts('academic_advisors',
            ['advisor_id', 'faculty_id', 'department_id', 'specialization', 'max_students'],
            advisors)
        f.write(sql + '\n')
        
        # Generate student advisor assignments (50 records - one per student)
        advisor_assignments = []
        
        for i in range(STUDENTS_COUNT):
            student_id = f"S{2020000 + i}"
            advisor_id = f"ADV{random.randint(1, 20):03d}"  # Use advisor_id instead of faculty_id
            assignment_date = random_date(2020, 2023)
            end_date = random_date(2024, 2025) if random.random() > 0.8 else None
            
            advisor_assignments.append((student_id, advisor_id, assignment_date, end_date))
        
        sql = generate_sql_inserts('student_advisor_assignments',
            ['student_id', 'advisor_id', 'assignment_date', 'end_date'],
            advisor_assignments)
        f.write(sql + '\n')
        
        # Generate course schedules (40 records)
        schedules = []
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
        
        for i in range(40):
            section_id = f"SEC{random.randint(1, 35):04d}"
            day = random.choice(days)
            start_hour = random.randint(8, 16)
            start_time = f"{start_hour:02d}:00:00"
            end_time = f"{start_hour + random.choice([1, 2, 3]):02d}:00:00"
            room_id = f"R{random.randint(1, 30):03d}"
            
            schedules.append((section_id, day, start_time, end_time, room_id))
        
        sql = generate_sql_inserts('course_schedules',
            ['section_id', 'day_of_week', 'start_time', 'end_time', 'room_id'],
            schedules)
        f.write(sql + '\n')
        
        # Generate course materials (35 records)
        materials = []
        material_types = ['Textbook', 'Reference', 'Online', 'Lab Manual']
        
        for i in range(35):
            course_id = f"C{random.randint(1, COURSES_COUNT):04d}"
            mat_type = random.choice(material_types)
            title = f"Medical {mat_type} {i+1}"
            author = random_chinese_name()
            isbn = f"978-{random.randint(1000000000, 9999999999)}"
            is_required = 1 if random.random() > 0.3 else 0
            
            materials.append((course_id, mat_type, title, author, isbn, is_required))
        
        sql = generate_sql_inserts('course_materials',
            ['course_id', 'material_type', 'title', 'author', 'isbn', 'is_required'],
            materials)
        f.write(sql + '\n')
        
        # Generate course prerequisites (25 records)
        prerequisites = []
        
        for i in range(25):
            course_id = f"C{random.randint(5, COURSES_COUNT):04d}"  # Advanced courses
            prereq_id = f"C{random.randint(1, 20):04d}"  # Basic courses
            is_mandatory = 1 if random.random() > 0.2 else 0
            
            prerequisites.append((course_id, prereq_id, is_mandatory))
        
        sql = generate_sql_inserts('course_prerequisites',
            ['course_id', 'prerequisite_course_id', 'is_mandatory'],
            prerequisites)
        f.write(sql + '\n')
        
        print(f"Test data SQL file generated: {output_file}")
        print(f"Generated data for:")
        print(f"  - {len(students)} students")
        print(f"  - {len(departments)} departments")
        print(f"  - {len(programs)} programs")
        print(f"  - {len(faculty)} faculty members")
        print(f"  - {len(courses)} courses")
        print(f"  - {len(advisors)} academic advisors")
        print(f"  - {len(advisor_assignments)} advisor assignments")
        print(f"  - {len(schedules)} course schedules")
        print(f"  - {len(materials)} course materials")
        print(f"  - {len(prerequisites)} course prerequisites")
        print(f"  - And many more related records...")

if __name__ == '__main__':
    main()
