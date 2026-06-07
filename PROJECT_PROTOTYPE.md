# Internal Marks Management System
## UI Prototype & Project Documentation

---

| **Project Title** | Internal Marks Management System (IA Marks) |
|-------------------|---------------------------------------------|
| **Department**    | MCA (Master of Computer Applications)       |
| **Technology**    | Python Flask, HTML, CSS, JavaScript, SQLite |
| **Version**       | Prototype 1.0                               |
| **Date**          | June 2026                                   |

---

## 1. Introduction

The **Internal Marks Management System** is a web-based application designed to manage internal assessment marks for the MCA department. It supports three user roles — **Admin**, **Faculty**, and **Student** — each with dedicated dashboards and workflows.

The system allows admins to manage students, faculties, subjects, and allocations. Faculty can enter marks (Assignments, Lab, Theory) for their allocated subjects. Students can view subject-wise marks and semester averages after login.

---

## 2. Objectives

- Centralize internal marks management for MCA department
- Allow admin to upload and manage student/faculty data via CSV
- Allocate subjects to faculty members
- Enable faculty to enter marks manually or via bulk CSV upload
- Provide students with a clear view of subject-wise marks and overall average
- Maintain activity logs for audit purposes

---

## 3. Technology Stack

| Layer        | Technology                          |
|--------------|-------------------------------------|
| Backend      | Python 3, Flask                     |
| Frontend     | HTML5, CSS3, JavaScript             |
| Database     | SQLite (`ia_marks.db`)              |
| Templates    | Jinja2                              |
| Font         | Inter (Google Fonts)                |
| Server       | Flask development server (port 5000)|

---

## 4. User Roles

| Role    | Login URL              | Credentials                          |
|---------|------------------------|--------------------------------------|
| Admin   | `/login`               | Username: `admin` / Password: `admin123` |
| Faculty | `/faculty/login`       | Email (uploaded by admin) / Password: `faculty123` |
| Student | `/student/login`       | USN (uploaded by admin) / Password: `student123` |

---

## 5. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     BROWSER (Client)                        │
│              HTML + CSS + JavaScript UI                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   Flask Application (app.py)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Admin   │  │ Faculty  │  │ Student  │  │   Auth   │  │
│  │  Routes  │  │  Routes  │  │  Routes  │  │ Sessions │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Database Layer (database.py)                   │
│                    SQLite Database                          │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. UI Design Guidelines

### 6.1 Color Palette

| Element           | Color Code   | Usage                    |
|-------------------|--------------|--------------------------|
| Sidebar Background| `#0b1a33`    | Dark navy navigation     |
| Page Background   | `#f0f2f7`    | Light gray content area  |
| Card Background   | `#ffffff`    | White cards with shadow  |
| Primary Accent    | `#4f46e5`    | Buttons, active nav link |
| Purple            | `#7c3aed`    | Students, assignments    |
| Green             | `#059669`    | Faculties, lab marks     |
| Yellow            | `#d97706`    | Subjects, overall avg    |
| Blue              | `#2563eb`    | MCA department, theory   |

### 6.2 Layout Structure

**Admin Layout:**
```
┌──────────────┬──────────────────────────────────────────────┐
│              │  Welcome, Admin 👋          [🔔] [Profile ▾] │
│   SIDEBAR    ├──────────────────────────────────────────────┤
│   (250px)    │  [Stat Cards Row — 4 cards]                  │
│              ├──────────────────────────────────────────────┤
│  Dashboard   │  [Main Content Panels / Tables / Forms]      │
│  Students    │                                              │
│  Faculties   │                                              │
│  Subjects    │                                              │
│  Allocations │                                              │
│  Departments │                                              │
│  Reports     │                                              │
│  Profile     │                                              │
│  Logout      │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

**Faculty / Student Layout:**
```
┌─────────────────────────────────────────────────────────────┐
│  [Logo] Internal Marks          [Avatar] Name  [Logout]     │
├─────────────────────────────────────────────────────────────┤
│  Welcome, User Name 👋                                      │
│  [Stat Cards]                                               │
│  [Content Panels / Tables]                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Screen-by-Screen UI Prototype

---

### 7.1 Admin Login Page
**URL:** `/login`

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│              [Gradient Dark Blue Background]                │
│                                                             │
│         ┌─────────────────────────────────┐                 │
│         │  [IM Logo]  Internal Marks      │                 │
│         │             Management System   │                 │
│         │                                 │                 │
│         │  Admin Login                    │                 │
│         │  Sign in to access dashboard    │                 │
│         │                                 │                 │
│         │  Username: [________________]   │                 │
│         │  Password: [________________]   │                 │
│         │                                 │                 │
│         │       [ Login Button ]          │                 │
│         │                                 │                 │
│         │  Student Login | Faculty Login  │                 │
│         └─────────────────────────────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**UI Elements:**
- Centered white login card with rounded corners
- Brand logo (IM) with gradient purple background
- Username and password input fields
- Purple gradient login button
- Links to Student and Faculty login pages

---

### 7.2 Admin Dashboard
**URL:** `/dashboard`

```
┌──────────────┬──────────────────────────────────────────────┐
│ SIDEBAR      │  Welcome, Admin 👋                           │
│              ├──────────────────────────────────────────────┤
│ ▶ Dashboard  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌────┐│
│   Students   │  │ 👥 320  │ │ 👨‍🏫 28  │ │ 📚 48   │ │ 🏛 1││
│   Faculties  │  │Students │ │Faculties│ │Subjects │ │Dept││
│   Subjects   │  └─────────┘ └─────────┘ └─────────┘ └────┘│
│   Allocations├──────────────────────────────────────────────┤
│   Departments│  Departments Overview                        │
│   Reports    │  ┌──────────────────────────────────────┐    │
│              │  │ 💻 MCA                               │    │
│ USER         │  │    X Students | Y Subjects           │    │
│   Profile    │  │    Click to manage →                 │    │
│   Logout     │  └──────────────────────────────────────┘    │
│              ├──────────────────────┬───────────────────────┤
│              │ Recent Faculties     │ Recent Activities     │
│              │ • Prof. Anitha       │ • Added student...    │
│              │ • Prof. Rahul        │ • Allocated DBMS...   │
│              │   [View All]         │                       │
└──────────────┴──────────────────────┴───────────────────────┘
```

**Features:**
- Live stats from database (no dummy data)
- Single MCA department card (clickable)
- Recent faculties list with department tags
- Recent activity log with timestamps

---

### 7.3 MCA Department Hub
**URL:** `/departments/mca`

```
┌──────────────┬──────────────────────────────────────────────┐
│ SIDEBAR      │  ← Back to Dashboard                         │
│              │  MCA Department                              │
│              ├──────────────────────────────────────────────┤
│              │  ┌──────────────────┐ ┌──────────────────┐ │
│              │  │ 👥 Students      │ │ 👨‍🏫 Faculties     │ │
│              │  │ X students       │ │ Y faculty members│ │
│              │  │ Manage Students →│ │ Manage Faculties→│ │
│              │  └──────────────────┘ └──────────────────┘ │
└──────────────┴──────────────────────────────────────────────┘
```

---

### 7.4 Students Management
**URL:** `/students`

```
┌──────────────┬──────────────────────────────────────────────┐
│ SIDEBAR      │  MCA Students                                │
│              │  Manage student records — add or upload CSV  │
│              ├──────────────────────┬───────────────────────┤
│              │ Add Student          │ Upload CSV            │
│              │ USN:    [________]   │ [Choose CSV file]     │
│              │ Name:   [________]   │ [Upload]              │
│              │ Email:  [________]   │ Columns: usn,name,    │
│              │ Sem:    [▼ Sem 1 ]   │ email,semester        │
│              │ [Add Student]        │                       │
│              ├──────────────────────┴───────────────────────┤
│              │ Student List (N)                             │
│              │ ┌────┬──────────┬────────┬───────┬─────────┐ │
│              │ │ #  │ USN      │ Name   │ Email │ Delete  │ │
│              │ ├────┼──────────┼────────┼───────┼─────────┤ │
│              │ │ 1  │1MS22MC001│ Amit K │ ...   │[Delete] │ │
│              │ └────┴──────────┴────────┴───────┴─────────┘ │
└──────────────┴──────────────────────────────────────────────┘
```

---

### 7.5 Faculties Management
**URL:** `/faculties`

```
┌──────────────┬──────────────────────────────────────────────┐
│ SIDEBAR      │  MCA Faculties                               │
│              ├──────────────────────┬───────────────────────┤
│              │ Add Faculty          │ Upload CSV            │
│              │ Name:  [________]    │ [Choose CSV file]     │
│              │ Email: [________]    │ Columns: name, email  │
│              │ [Add Faculty]        │                       │
│              ├──────────────────────┴───────────────────────┤
│              │ Faculty List (N)                             │
│              │ # | Name | Email | Department | [Delete]     │
└──────────────┴──────────────────────────────────────────────┘
```

---

### 7.6 Subjects Management
**URL:** `/subjects`

```
┌──────────────┬──────────────────────────────────────────────┐
│ SIDEBAR      │  Subjects                                    │
│              ├──────────────────────────────────────────────┤
│              │ Add Subject                                  │
│              │ Code: [____] Name: [________] Sem: [▼] [Add] │
│              ├──────────────────────────────────────────────┤
│              │ Subject List                                 │
│              │ # | Code | Name | Semester | Dept | Delete   │
└──────────────┴──────────────────────────────────────────────┘
```

---

### 7.7 Subject Allocations
**URL:** `/allocations`

```
┌──────────────┬──────────────────────────────────────────────┐
│ SIDEBAR      │  Subject Allocations                         │
│              │  Assign each MCA subject to a faculty member │
│              ├──────────────────────────────────────────────┤
│              │ Allocate Subject to Faculty                  │
│              │ Faculty: [▼ Select faculty    ]             │
│              │ Subject: [▼ Select subject    ] [Allocate]   │
│              ├──────────────────────────────────────────────┤
│              │ Current Allocations (N)                      │
│              │ Faculty | Email | Code | Subject | Sem | X   │
└──────────────┴──────────────────────────────────────────────┘
```

**Business Rule:** Each subject can be allocated to only one faculty.

---

### 7.8 Faculty Login
**URL:** `/faculty/login`

```
┌─────────────────────────────────────────────────────────────┐
│              [Same gradient background as admin login]        │
│         ┌─────────────────────────────────┐                 │
│         │  Faculty Login                  │                 │
│         │  Use email uploaded by admin    │                 │
│         │  Default password: faculty123   │                 │
│         │                                 │                 │
│         │  Email:    [________________]   │                 │
│         │  Password: [________________]   │                 │
│         │       [ Login Button ]          │                 │
│         │  Admin Login | Student Login    │                 │
│         └─────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

### 7.9 Faculty Dashboard
**URL:** `/faculty/dashboard`

```
┌─────────────────────────────────────────────────────────────┐
│ [Logo] Internal Marks        [Avatar] Prof. Name  [Logout]  │
├─────────────────────────────────────────────────────────────┤
│ Welcome, Prof. Name 👋                                      │
│ Faculty Dashboard — MCA Department                          │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐             │
│ │ 3 Subjects  │ │ 45 Students │ │ MCA Dept    │             │
│ │ Allocated   │ │ (your subs) │ │             │             │
│ └─────────────┘ └─────────────┘ └─────────────┘             │
├─────────────────────────────────────────────────────────────┤
│ My Profile: Name | Email | Department                       │
├─────────────────────────────────────────────────────────────┤
│ My Allocated Subjects                                       │
│ # | Code | Subject | Sem | Students | Marks Entered | Act  │
│ 1 | MCA101 | DBMS  | 1  |    30    |   25/30       |[Manage Marks]│
└─────────────────────────────────────────────────────────────┘
```

---

### 7.10 Faculty Marks Entry
**URL:** `/faculty/subject/<id>/marks`

```
┌─────────────────────────────────────────────────────────────┐
│ ← Back to Dashboard                                         │
│ Database Management Systems (MCA101)                        │
│ Semester 1 — Assignments (/10), Lab (/10), Theory (/20)     │
├──────────────────────┬──────────────────────────────────────┤
│ Upload Marks CSV     │ Mark Components                      │
│ [Choose CSV] [Upload]│ Assignments: Max 10                  │
│ usn, assignment,     │ Lab: Max 10                          │
│ lab_marks, theory    │ Theory: Max 20                       │
├──────────────────────┴──────────────────────────────────────┤
│ Student List & Marks                                        │
│ # | USN | Name | Assignments | Lab | Theory                 │
│ 1 | ... | Amit | [  8  ]     |[ 9 ]|[  16  ]                │
│ 2 | ... | Priya| [  7  ]     |[ 8 ]|[  18  ]                │
│                                      [ Save All Marks ]     │
└─────────────────────────────────────────────────────────────┘
```

**Mark Components:**

| Component   | Max Marks |
|-------------|-----------|
| Assignments | 10        |
| Lab         | 10        |
| Theory      | 20        |

---

### 7.11 Student Login
**URL:** `/student/login`

```
┌─────────────────────────────────────────────────────────────┐
│         ┌─────────────────────────────────┐                 │
│         │  Student Login                  │                 │
│         │  Sign in with USN and password  │                 │
│         │                                 │                 │
│         │  USN:      [________________]   │                 │
│         │  Password: [________________]   │                 │
│         │       [ Login Button ]          │                 │
│         │  Admin Login | Faculty Login    │                 │
│         └─────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────┘
```

---

### 7.12 Student Dashboard
**URL:** `/student/dashboard`

```
┌─────────────────────────────────────────────────────────────┐
│ [Logo] Internal Marks        [Avatar] Student Name [Logout] │
├─────────────────────────────────────────────────────────────┤
│ Welcome, Student Name 👋                                    │
│ Student Dashboard — MCA — Semester 1                        │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐     │
│ │ Sem 1       │ │ 6 Subjects  │ │ Overall Average: 16.5│    │
│ │ Current Sem │ │             │ │ (highlighted card)  │    │
│ └─────────────┘ └─────────────┘ └─────────────────────┘     │
├─────────────────────────────────────────────────────────────┤
│ Subject-wise Marks — Semester 1                           │
│ ┌────┬──────┬─────────┬─────────┬─────┬────────┬─────────┐ │
│ │ #  │ Code │ Subject │ Assign  │ Lab │ Theory │ Average │ │
│ ├────┼──────┼─────────┼─────────┼─────┼────────┼─────────┤ │
│ │ 1  │MCA101│ DBMS    │  [ 8 ]  │ [9] │  [16]  │  11.0   │ │
│ │ 2  │MCA102│ Java    │  [ 7 ]  │ [8] │  [18]  │  11.0   │ │
│ ├────┴──────┴─────────┴─────────┴─────┴────────┼─────────┤ │
│ │              Overall Semester Average          │  11.0   │ │
│ └────────────────────────────────────────────────┴─────────┘ │
├─────────────────────────────────────────────────────────────┤
│ My Profile: USN | Name | Email | Department                 │
└─────────────────────────────────────────────────────────────┘
```

**Average Calculation:**
- **Subject Average** = Mean of entered components (Assignments, Lab, Theory)
- **Overall Average** = Mean of all subject averages for the semester

---

## 8. User Flow Diagrams

### 8.1 Admin Workflow

```
Login → Dashboard → Manage Data
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
     Students    Faculties    Subjects
         │            │            │
         └────────────┼────────────┘
                      ▼
                 Allocations
              (Assign faculty to subject)
```

### 8.2 Faculty Workflow

```
Login (email) → Dashboard → Select Subject
                                  │
                                  ▼
                           Manage Marks
                         ┌──────┴──────┐
                         ▼             ▼
                   Manual Entry    CSV Upload
                   (per student)   (bulk marks)
```

### 8.3 Student Workflow

```
Login (USN) → Dashboard → View Subject-wise Marks
                              │
                              ▼
                    Assignments | Lab | Theory
                              │
                              ▼
                      Overall Semester Average
```

---

## 9. Database Schema

```
students
├── id (PK)
├── usn (UNIQUE)
├── name
├── email
├── semester
├── department
├── password
└── created_at

faculties
├── id (PK)
├── name
├── email (UNIQUE)
├── department
├── password
└── created_at

subjects
├── id (PK)
├── code (UNIQUE)
├── name
├── semester
├── department
└── created_at

allocations
├── id (PK)
├── faculty_id (FK → faculties)
├── subject_id (FK → subjects, UNIQUE)
└── created_at

marks
├── id (PK)
├── student_id (FK → students)
├── subject_id (FK → subjects)
├── marks (theory)
├── assignment_marks
├── lab_marks
├── updated_at
└── UNIQUE(student_id, subject_id)

activities
├── id (PK)
├── action
└── created_at
```

---

## 10. CSV Upload Formats

### Students CSV
```csv
usn,name,email,semester
1MS22MC001,Amit Kumar,amit@college.edu,1
1MS22MC002,Priya Sharma,priya@college.edu,1
```

### Faculties CSV
```csv
name,email
Prof. Anitha,anitha@college.edu
Prof. Rahul,rahul@college.edu
```

### Marks CSV (Faculty)
```csv
usn,assignment_marks,lab_marks,theory_marks
1MS22MC001,8,9,16
1MS22MC002,7,8,18
```

---

## 11. Navigation Map

| Page              | Admin | Faculty | Student |
|-------------------|:-----:|:-------:|:-------:|
| Admin Login       |   ✓   |         |         |
| Admin Dashboard   |   ✓   |         |         |
| Students          |   ✓   |         |         |
| Faculties         |   ✓   |         |         |
| Subjects          |   ✓   |         |         |
| Allocations       |   ✓   |         |         |
| Departments       |   ✓   |         |         |
| Reports           |   ✓   |         |         |
| Profile           |   ✓   |         |         |
| Faculty Login     |       |    ✓    |         |
| Faculty Dashboard |       |    ✓    |         |
| Faculty Marks     |       |    ✓    |         |
| Student Login     |       |         |    ✓    |
| Student Dashboard |       |         |    ✓    |

---

## 12. Project File Structure

```
IA Marks/
├── app.py                      # Flask routes & logic
├── database.py                 # SQLite operations
├── requirements.txt            # Python dependencies
├── ia_marks.db                 # SQLite database (auto-created)
├── PROJECT_PROTOTYPE.md        # This document
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── students.html
│   ├── faculties.html
│   ├── subjects.html
│   ├── allocations.html
│   ├── departments.html
│   ├── department_mca.html
│   ├── reports.html
│   ├── profile.html
│   ├── faculty_login.html
│   ├── faculty_dashboard.html
│   ├── faculty_subject_marks.html
│   ├── student_login.html
│   ├── student_dashboard.html
│   └── partials/
│       ├── admin_sidebar.html
│       └── flash.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── main.js
```

---

## 13. How to Run

```powershell
cd "C:\Users\Udiksha\OneDrive\Desktop\IA Marks"
pip install flask
python app.py
```

Open browser: **http://127.0.0.1:5000**

---

## 14. Future Enhancements

| # | Feature                          | Priority |
|---|----------------------------------|----------|
| 1 | Password change for faculty/student | High  |
| 2 | Export marks report as PDF/Excel | Medium   |
| 3 | Email notifications to students  | Low      |
| 4 | Semester-wise filtering on admin | Medium   |
| 5 | Role-based password hashing      | High     |
| 6 | Graphical analytics on Reports   | Medium   |
| 7 | Multi-department support         | Low      |

---

## 15. Conclusion

This prototype document describes the complete UI and functional design of the **Internal Marks Management System** for the MCA department. The application provides role-based dashboards, CSV bulk uploads, subject allocation, and a structured marks entry system with Assignments, Lab, and Theory components.

The implemented prototype is fully functional and can be extended for production deployment with authentication hardening and reporting features.

---

*Document generated for Internal Marks Management System — MCA Department Prototype v1.0*
