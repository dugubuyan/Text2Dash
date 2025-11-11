# 医学院校管理系统数据库结构说明

## 数据库概述

这是一个完整的医学院校管理系统数据库，涵盖学生管理、课程管理、教师管理、临床实习、学术研究、财务管理等多个业务领域。数据库共包含约100个表，采用关系型设计，表之间通过外键建立关联关系。

---

## 核心业务模块

### 1. 学生信息管理模块

**核心表：students（学生基本信息表）**
- 主键：student_id（学生ID）
- 核心字段：姓名、性别、出生日期、身份证号、联系方式、入学日期、毕业日期、学生状态（在读/毕业/休学/退学）

**关联的扩展信息表：**
- **student_addresses**：学生地址信息（家庭/宿舍/紧急联系地址）
- **student_emergency_contacts**：紧急联系人信息
- **student_family_info**：家庭信息（父母职业、家庭收入水平）
- **student_health_records**：健康档案（血型、过敏史、慢性病、疫苗接种状态）
- **student_photos**：学生照片（证件照/毕业照）
- **student_enrollment_history**：入学历史记录
- **student_id_cards**：学生证信息（卡号、发放日期、有效期、状态）
- **student_previous_education**：既往教育经历
- **student_scholarships**：奖学金记录

**关联关系：**
所有扩展表通过 `student_id` 外键关联到 `students` 表，形成一对多关系。

---

### 2. 学术项目与专业管理模块

**核心表结构：**

**programs（学术项目表）**
- 主键：program_id
- 字段：项目名称、学位类型（学士/硕士/博士/证书）、学制年限、总学分要求、所属院系

**departments（院系表）**
- 主键：department_id
- 字段：院系名称、系主任、办公楼、联系方式、成立日期

**majors（专业表）**
- 主键：major_id
- 外键：program_id（所属项目）、department_id（所属院系）
- 字段：专业名称、描述

**specializations（专业方向表）**
- 主键：specialization_id
- 外键：major_id（所属专业）
- 字段：方向名称、描述

**关联表：**
- **student_majors**：学生与专业的关联（支持双学位，is_primary标识主专业）
- **student_specializations**：学生与专业方向的关联
- **program_requirements**：项目要求（学分、课程要求）
- **program_milestones**：项目里程碑（典型年份的重要节点）

**层级关系：**
```
departments（院系）
    ↓
programs（学术项目）
    ↓
majors（专业）
    ↓
specializations（专业方向）
```

---

### 3. 课程管理模块

**核心表：courses（课程表）**
- 主键：course_id
- 字段：课程名称、课程代码、学分、所属院系、课程级别（本科/研究生/通用）

**课程相关表：**
- **course_prerequisites**：课程先修关系（自关联表，记录课程之间的前置要求）
- **course_sections**：课程班级（学期、年份、班级号、容量、已注册人数）
- **course_schedules**：课程时间表（星期、上课时间、教室）
- **course_materials**：课程教材（教材类型、书名、作者、ISBN、是否必需）
- **course_objectives**：课程目标
- **course_topics**：课程主题（按周次组织）
- **course_evaluations**：课程评价（学生对课程的评分和评论）
- **course_categories**：课程分类
- **course_category_mappings**：课程与分类的映射关系

**关联关系：**
- courses → course_sections（一对多）
- course_sections → course_schedules（一对多）
- courses → course_prerequisites（多对多，自关联）

---

### 4. 教师管理模块

**核心表：faculty（教师表）**
- 主键：faculty_id
- 字段：姓名、职称（教授/副教授/助理教授/讲师）、所属院系、联系方式、办公地点、入职日期

**教师扩展信息表：**
- **faculty_qualifications**：教师学历资质
- **faculty_research_interests**：研究兴趣领域
- **faculty_publications**：学术发表（论文、期刊、引用次数）
- **faculty_office_hours**：办公时间
- **faculty_awards**：获奖记录
- **faculty_teaching_loads**：教学负荷（每学期授课学分和学生数）

**教师角色关联表：**
- **section_instructors**：教师授课关联（主讲/助教/客座）
- **academic_advisors**：学术导师信息
- **student_advisor_assignments**：学生与导师的分配关系
- **faculty_committees**：教师委员会
- **faculty_committee_memberships**：教师委员会成员关系

**关联关系：**
- faculty → section_instructors → course_sections（教师授课关系）
- faculty → academic_advisors → student_advisor_assignments → students（导师指导关系）

---

### 5. 选课与注册管理模块

**核心表：student_enrollments（学生选课表）**
- 主键：enrollment_id
- 外键：student_id、section_id
- 字段：选课日期、选课状态（已选/已退/已完成/已撤销）、成绩、绩点

**选课相关表：**
- **enrollment_waitlists**：选课等待列表（位置、状态）
- **enrollment_permissions**：选课权限（特殊批准）
- **credit_transfers**：学分转换（外校学分认定）
- **course_drops**：退课记录（退课日期、原因、退款金额）
- **course_withdrawals**：撤课记录（需要批准）
- **grade_changes**：成绩变更记录（旧成绩、新成绩、变更原因）
- **incomplete_grades**：未完成成绩（截止日期、状态）
- **audit_enrollments**：旁听选课
- **pass_fail_enrollments**：通过/不通过制选课

**关联关系：**
```
students + course_sections → student_enrollments（核心选课关系）
    ↓
course_drops / course_withdrawals / grade_changes（选课后续操作）
```

---

### 6. 考核评估模块

#### 6.1 考试管理
**exams（考试表）**
- 外键：section_id
- 字段：考试类型（期中/期末/测验/实践/口试）、考试日期、时长、总分、权重

**exam_scores（考试成绩表）**
- 外键：exam_id、student_id
- 字段：得分、百分比、等级

**exam_questions（考试题目表）**
- 外键：exam_id
- 字段：题号、题目内容、题型、分值

#### 6.2 作业管理
**assignments（作业表）**
- 外键：section_id
- 字段：作业名称、描述、截止日期、总分、权重

**assignment_submissions（作业提交表）**
- 外键：assignment_id、student_id
- 字段：提交日期、得分、反馈、迟交天数

#### 6.3 项目管理
**projects（项目表）**
- 外键：section_id
- 字段：项目名称、开始日期、截止日期、总分、是否小组项目

**project_submissions（项目提交表）**
- 外键：project_id、student_id

#### 6.4 实验报告管理
**lab_reports（实验报告表）**
- 外键：section_id
- 字段：实验编号、标题、截止日期、总分

**lab_report_submissions（实验报告提交表）**
- 外键：report_id、student_id

#### 6.5 课堂参与
**participation_grades（课堂参与成绩表）**
- 外键：section_id、student_id
- 字段：成绩、评论、评分周期

**关联关系：**
所有考核表都通过 `section_id` 关联到课程班级，通过 `student_id` 关联到学生。

---

### 7. 考勤管理模块

**核心表：class_sessions（课堂会话表）**
- 主键：session_id
- 外键：section_id
- 字段：上课日期、课次、主题、备注

**attendance_records（考勤记录表）**
- 外键：session_id、student_id
- 字段：状态（出席/缺席/迟到/请假）、签到时间、备注

**考勤相关表：**
- **absence_requests**：请假申请（原因、是否批准）
- **late_arrivals**：迟到记录（迟到分钟数、原因）
- **attendance_policies**：考勤政策（最大缺席次数、迟到政策、惩罚说明）
- **attendance_summaries**：考勤汇总（总课次、出席次数、缺席次数、出勤率）
- **attendance_warnings**：考勤警告
- **lab_attendance**：实验课考勤
- **clinical_rotation_attendance**：临床轮转考勤
- **seminar_attendance**：研讨会考勤

**关联关系：**
```
course_sections → class_sessions → attendance_records
                                        ↓
                            absence_requests / late_arrivals
```

---

### 8. 毕业管理模块

**graduation_requirements（毕业要求表）**
- 外键：program_id
- 字段：要求类型、描述、所需学分

**student_graduation_status（学生毕业状态表）**
- 外键：student_id
- 字段：已获学分、GPA、是否满足要求、预期毕业日期、实际毕业日期

**graduation_applications（毕业申请表）**
- 外键：student_id
- 字段：申请日期、预期毕业日期、状态（待审/批准/拒绝/完成）

**degree_conferrals（学位授予表）**
- 外键：student_id、major_id
- 字段：学位类型、授予日期、荣誉等级（最优等/优等/荣誉/无）

**alumni_records（校友记录表）**
- 外键：student_id
- 字段：毕业年份、当前雇主、职位、联系方式

---

### 9. 就业与职业发展模块

**career_placements（职业安置表）**
- 外键：student_id
- 字段：雇主名称、职位、开始日期、薪资范围、雇佣类型

**internships（实习表）**
- 外键：student_id
- 字段：机构名称、职位、开始/结束日期、完成小时数、导师、评估分数

**residency_placements（住院医师安置表）**
- 外键：student_id
- 字段：医院名称、专科、开始日期、年限、匹配状态

**job_search_activities（求职活动表）**
- 外键：student_id
- 字段：活动类型（申请/面试/录用/拒绝）、公司名称、职位、日期

**career_counseling_sessions（职业咨询会话表）**
- 外键：student_id
- 字段：咨询师、日期、讨论主题、是否需要跟进

---

### 10. 财务管理模块

**tuition_fees（学费表）**
- 外键：student_id
- 字段：学期、年份、学费金额、其他费用、总金额、截止日期

**payments（缴费记录表）**
- 外键：student_id
- 字段：缴费日期、金额、支付方式（现金/信用卡/银行转账/奖学金）、参考号

**financial_aid（助学金表）**
- 外键：student_id
- 字段：资助类型（助学金/贷款/奖学金/勤工俭学）、金额、学年、状态

**student_loans（学生贷款表）**
- 外键：student_id
- 字段：贷款机构、贷款金额、利率、发放日期、还款开始日期

---

### 11. 设施资源管理模块

**rooms（教室表）**
- 主键：room_id
- 字段：建筑、房间号、容量、房间类型（教室/实验室/讲堂/办公室/自习室）、设备

**room_reservations（教室预订表）**
- 外键：room_id
- 字段：预订人、预订日期、开始/结束时间、用途

**library_resources（图书馆资源表）**
- 主键：resource_id
- 字段：标题、作者、资源类型（图书/期刊/数据库/媒体）、ISBN、可用/总副本数

**library_checkouts（图书借阅表）**
- 外键：student_id、resource_id
- 字段：借出日期、到期日期、归还日期、罚款金额

---

### 12. 学生组织管理模块

**student_organizations（学生组织表）**
- 主键：organization_id
- 字段：组织名称、类别、成立日期、指导教师、描述

**organization_memberships（组织成员表）**
- 外键：student_id、organization_id
- 字段：加入日期、角色、状态（活跃/不活跃）

---

### 13. 临床实习管理模块（医学特色）

**clinical_rotations（临床轮转表）**
- 主键：rotation_id
- 字段：轮转名称、科室、持续周数、要求小时数、描述

**student_clinical_assignments（学生临床分配表）**
- 外键：student_id、rotation_id
- 字段：医院名称、开始/结束日期、导师姓名

**clinical_evaluations（临床评估表）**
- 外键：assignment_id
- 字段：评估日期、临床技能分数、专业素养分数、沟通分数、总分、评论

**关联关系：**
```
clinical_rotations → student_clinical_assignments → clinical_evaluations
                            ↓
                    clinical_rotation_attendance（考勤）
```

---

### 14. 科研管理模块

**research_projects（科研项目表）**
- 主键：project_id
- 外键：department_id
- 字段：项目标题、首席研究员、开始/结束日期、资助金额、状态

**student_research_participation（学生科研参与表）**
- 外键：student_id、project_id
- 字段：角色、开始/结束日期、贡献小时数

**thesis_submissions（论文提交表）**
- 外键：student_id
- 字段：标题、提交日期、答辩日期、导师ID、状态（进行中/已提交/已批准/已拒绝）

**thesis_committee_members（论文委员会成员表）**
- 外键：thesis_id、faculty_id
- 字段：角色（主席/成员/外部专家）

---

### 15. 资质认证管理模块（医学特色）

**medical_licenses（医疗执照表）**
- 外键：student_id
- 字段：执照类型、执照号、发放日期、到期日期、发放机构

**certifications（认证表）**
- 外键：student_id
- 字段：认证名称、发放机构、发放/到期日期、认证号

**student_achievements（学生成就表）**
- 外键：student_id
- 字段：成就类型（奖项/发表/演讲/竞赛/荣誉）、标题、描述、获得日期、机构

---

## 核心关联关系图

### 主要实体关系

```
students（学生）
    ├─→ student_enrollments（选课）→ course_sections（课程班级）→ courses（课程）
    ├─→ student_majors（专业）→ majors（专业）→ programs（项目）→ departments（院系）
    ├─→ student_advisor_assignments（导师分配）→ academic_advisors（导师）→ faculty（教师）
    ├─→ exam_scores（考试成绩）→ exams（考试）→ course_sections
    ├─→ assignment_submissions（作业提交）→ assignments（作业）→ course_sections
    ├─→ attendance_records（考勤）→ class_sessions（课堂）→ course_sections
    ├─→ student_clinical_assignments（临床分配）→ clinical_rotations（临床轮转）
    ├─→ student_research_participation（科研参与）→ research_projects（科研项目）
    ├─→ tuition_fees / payments（学费/缴费）
    ├─→ graduation_applications（毕业申请）→ degree_conferrals（学位授予）
    └─→ career_placements / internships / residency_placements（就业/实习/住院医）

faculty（教师）
    ├─→ section_instructors（授课）→ course_sections（课程班级）
    ├─→ academic_advisors（导师）→ student_advisor_assignments（指导学生）
    ├─→ faculty_publications（学术发表）
    ├─→ faculty_committee_memberships（委员会成员）→ faculty_committees（委员会）
    └─→ thesis_committee_members（论文委员会）→ thesis_submissions（学生论文）

course_sections（课程班级）
    ├─→ course_schedules（时间表）→ rooms（教室）
    ├─→ section_instructors（授课教师）→ faculty
    ├─→ student_enrollments（选课学生）→ students
    ├─→ exams / assignments / projects / lab_reports（各类考核）
    ├─→ class_sessions（课堂会话）→ attendance_records（考勤）
    └─→ course_evaluations（课程评价）
```

---

## 数据库设计特点

### 1. 模块化设计
数据库按业务领域划分为15个主要模块，每个模块内部高内聚，模块之间通过外键建立松耦合关系。

### 2. 扩展性设计
- 学生信息采用主表+扩展表模式，便于添加新的信息类型
- 考核方式多样化（考试、作业、项目、实验报告、课堂参与）
- 支持多种特殊选课模式（旁听、通过/不通过制）

### 3. 医学院校特色
- 临床轮转管理（clinical_rotations, student_clinical_assignments, clinical_evaluations）
- 住院医师安置（residency_placements）
- 医疗执照管理（medical_licenses）
- 健康档案（student_health_records）

### 4. 完整的生命周期管理
从学生入学（admission）→ 选课学习（enrollment）→ 考核评估（exams/assignments）→ 临床实习（clinical rotations）→ 科研参与（research）→ 毕业（graduation）→ 就业（career placement）→ 校友（alumni），覆盖学生完整生命周期。

### 5. 审计与追踪
- 成绩变更记录（grade_changes）
- 选课历史（enrollment_history）
- 考勤警告（attendance_warnings）
- 请假审批（absence_requests）

### 6. 多对多关系处理
通过中间表处理复杂关系：
- student_majors（学生-专业）
- student_enrollments（学生-课程）
- section_instructors（教师-课程）
- organization_memberships（学生-组织）
- thesis_committee_members（教师-论文）

---

## 关键业务流程

### 流程1：学生选课流程
1. 学生查看 `course_sections`（课程班级）
2. 检查 `course_prerequisites`（先修课程要求）
3. 如果班级已满，加入 `enrollment_waitlists`（等待列表）
4. 如果需要特殊权限，申请 `enrollment_permissions`
5. 成功选课后记录到 `student_enrollments`
6. 更新 `course_sections.enrolled_count`

### 流程2：课程考核流程
1. 教师在 `exams/assignments/projects` 中创建考核任务
2. 学生提交到 `exam_scores/assignment_submissions/project_submissions`
3. 教师评分并记录反馈
4. 系统根据权重计算最终成绩，更新 `student_enrollments.grade`

### 流程3：临床实习流程
1. 学校在 `clinical_rotations` 中定义轮转项目
2. 将学生分配到医院，记录到 `student_clinical_assignments`
3. 记录每日考勤到 `clinical_rotation_attendance`
4. 导师评估记录到 `clinical_evaluations`
5. 完成后更新学生的临床实习学分

### 流程4：毕业审核流程
1. 系统计算学生总学分，更新 `student_graduation_status`
2. 检查 `graduation_requirements`（毕业要求）
3. 学生提交 `graduation_applications`（毕业申请）
4. 审核通过后记录 `degree_conferrals`（学位授予）
5. 更新 `students.status` 为 'Graduated'
6. 创建 `alumni_records`（校友记录）

---

## 数据查询场景示例

### 场景1：查询学生的完整学业档案
需要关联的表：
- students（基本信息）
- student_majors → majors（专业）
- student_enrollments → course_sections → courses（选课记录）
- exam_scores, assignment_submissions（考核成绩）
- student_graduation_status（毕业状态）

### 场景2：生成课程成绩单
需要关联的表：
- course_sections → courses（课程信息）
- section_instructors → faculty（授课教师）
- student_enrollments（选课和成绩）
- exams, assignments, projects（各项考核）
- attendance_summaries（出勤情况）

### 场景3：教师工作量统计
需要关联的表：
- faculty（教师信息）
- section_instructors → course_sections（授课班级）
- student_enrollments（学生数量）
- faculty_teaching_loads（教学负荷汇总）
- academic_advisors → student_advisor_assignments（指导学生数）

### 场景4：临床实习评估报告
需要关联的表：
- students（学生信息）
- student_clinical_assignments → clinical_rotations（实习分配）
- clinical_evaluations（评估结果）
- clinical_rotation_attendance（考勤记录）

### 场景5：财务对账
需要关联的表：
- students（学生信息）
- tuition_fees（应缴费用）
- payments（实际缴费）
- financial_aid（助学金）
- student_scholarships（奖学金）

---

## 数据完整性约束

### 主键约束
所有表都定义了主键，确保记录唯一性。

### 外键约束
- 所有关联表都通过外键维护引用完整性
- 级联删除需要谨慎处理（如删除学生时相关记录的处理）

### 检查约束（CHECK）
- 性别限制：gender IN ('M', 'F', 'Other')
- 学生状态：status IN ('Active', 'Graduated', 'Suspended', 'Withdrawn')
- 考试类型：exam_type IN ('Midterm', 'Final', 'Quiz', 'Practical', 'Oral')
- 考勤状态：status IN ('Present', 'Absent', 'Late', 'Excused')

### 唯一性约束（UNIQUE）
- students.id_card_number（身份证号）
- courses.course_code（课程代码）
- student_id_cards.card_number（学生证号）
- medical_licenses.license_number（执照号）

### 默认值约束（DEFAULT）
- created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- enrolled_count INTEGER DEFAULT 0
- is_primary BOOLEAN DEFAULT 1

---

## 使用建议

### 1. 查询优化
- 在高频查询字段上建立索引（student_id, course_id, section_id等）
- 对于复杂统计查询，考虑创建物化视图
- 使用汇总表（如attendance_summaries）减少实时计算

### 2. 数据归档
- 定期归档历史学期数据
- 毕业学生数据可移至归档库
- 保留必要的审计日志

### 3. 权限控制
- 学生只能查看自己的记录
- 教师可以查看所授课程的学生信息
- 管理员拥有完整权限
- 财务数据需要特殊权限

### 4. 数据一致性维护
- 使用事务确保选课、退课操作的原子性
- 成绩计算需要考虑各项考核的权重
- 毕业审核需要检查所有必修课程和学分要求

---

## 总结

这是一个设计完善的医学院校管理系统数据库，具有以下优势：

1. **全面性**：覆盖学生管理、教学管理、临床实习、科研、就业等全业务流程
2. **专业性**：包含医学院校特有的临床轮转、住院医师安置、医疗执照等模块
3. **可扩展性**：采用模块化设计，便于后续功能扩展
4. **规范性**：遵循数据库设计范式，合理使用外键约束和检查约束
5. **实用性**：包含丰富的辅助表（考勤汇总、教学负荷等），便于统计分析

该数据库可以作为LLM分析的知识库，通过自然语言描述替代直接发送SQL schema，使LLM更容易理解业务逻辑和表之间的关联关系。
