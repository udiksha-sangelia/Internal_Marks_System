# IA Marks System

A Flask-based Internal Assessment (IA) Marks Management System for managing students, faculty, subjects, marks, and activities.

## Features

- Admin, Faculty, and Student Login
- Student & Faculty Management
- Subject Allocation
- IA Marks Management
- Activities Management
- MySQL Database Support
- Railway Deployment Support

---

# Technology Stack

- Python 3.12+
- Flask
- SQLAlchemy
- PyMySQL
- HTML5
- CSS3
- JavaScript
- MySQL
- Railway

---

# Project Structure

```
IA Marks System/
│
├── app.py
├── database.py
├── requirements.txt
├── Procfile
├── static/
├── templates/
├── uploads/
└── README.md
```

---

# Installation

Clone the repository

```bash
git clone https://github.com/<USERNAME>/Internal_Marks_System.git
cd Internal_Marks_System
```

Create a virtual environment

### Windows

```powershell
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# Database Configuration

The application automatically reads the database connection from the following environment variables.

Priority:

1. DATABASE_URL
2. MYSQL_URL

---

## Local MySQL

Example:

```text
mysql+pymysql://root:yourpassword@localhost:3306/ia_marks_db
```

Windows PowerShell

```powershell
$env:DATABASE_URL="mysql+pymysql://root:yourpassword@localhost:3306/ia_marks_db"
```

Permanent

```powershell
setx DATABASE_URL "mysql+pymysql://root:yourpassword@localhost:3306/ia_marks_db"
```

---

## Railway MySQL

When deployed on Railway, the application automatically uses the Railway database.

Set the following environment variable inside Railway:

```
DATABASE_URL
```

Example

```text
mysql+pymysql://root:password@mysql.railway.internal:3306/railway
```

> **Note:** The hostname `mysql.railway.internal` only works inside Railway.

For local development, use:

```text
mysql+pymysql://root:password@localhost:3306/ia_marks_db
```

or Railway's **Public Connection**.

---

# Create Local Database

Run the following SQL commands:

```sql
CREATE DATABASE ia_marks_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'ia_user'@'localhost'
IDENTIFIED BY 'StrongP@ss!';

GRANT ALL PRIVILEGES
ON ia_marks_db.*
TO 'ia_user'@'localhost';

FLUSH PRIVILEGES;
```

---

# Running the Application

```bash
python app.py
```

The application automatically creates missing tables on startup.

Open

```
http://127.0.0.1:5000
```

---

# Deploying on Railway

## 1. Push project to GitHub

```bash
git init
git add .
git commit -m "Initial Commit"
git push origin main
```

---

## 2. Create Railway Project

- Login to Railway
- Create a New Project
- Select **Deploy from GitHub**
- Choose this repository

---

## 3. Create Railway MySQL

Inside the same Railway project:

```
New
→ Database
→ MySQL
```

---

## 4. Configure Environment Variables

In the Flask service, add:

```
DATABASE_URL=<Railway MySQL URL>
```

Example:

```text
mysql+pymysql://root:password@mysql.railway.internal:3306/railway
```

---

## 5. Procfile

```
web: gunicorn app:app
```

---

## 6. Redeploy

Railway automatically redeploys after every push to GitHub.

---

# Viewing the Database

## Local

Open MySQL Workbench

Connect using

Host

```
localhost
```

Port

```
3306
```

Database

```
ia_marks_db
```

---

## Railway

To inspect the Railway database locally, use the **Public Networking** connection details shown in Railway.

Do **not** use:

```
mysql.railway.internal
```

outside Railway, because it is only accessible from services running inside the same Railway project.

---

# Common Errors

### Can't connect to mysql.railway.internal

Cause:

Using Railway's private hostname on your local computer.

Solution:

Use:

- localhost (local MySQL), or
- Railway Public Connection.

---

### Could not parse SQLAlchemy URL

Ensure the URL starts with

```text
mysql+pymysql://
```

not

```text
mysql+pymysql//
```

---

### ModuleNotFoundError

Install dependencies

```bash
pip install -r requirements.txt
```

---

### Access denied

Verify:

- Username
- Password
- Host
- Port
- Database Name

---

# Contributors

- Project Leader
- Team Member 1
- Team Member 2
- Team Member 3

---

# License

This project is developed for educational purposes.
