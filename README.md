# IA Marks

This Flask project stores academic data and can use either SQLite or MySQL.

## Requirements

- Python 3.12+
- Flask
- MySQL

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Database configuration

The project reads the database connection from an environment variable.

- `DATABASE_URL` is preferred
- `MYSQL_URL` is also supported

### MySQL URL format

Use the SQLAlchemy MySQL URL format:

```text
mysql+pymysql://<username>:<password>@<host>:<port>/<database>
```

Example:

```text
mysql+pymysql://ia_user:StrongP%40ss%21@localhost:3306/ia_marks_db
```

> If your password contains special characters, URL-encode them. For example `@` becomes `%40` and `!` becomes `%21`.

### Set `DATABASE_URL` in PowerShell

For the current session:

```powershell
$env:DATABASE_URL = "mysql+pymysql://ia_user:StrongP%40ss%21@localhost:3306/ia_marks_db"
```

To save permanently on Windows:

```powershell
setx DATABASE_URL "mysql+pymysql://ia_user:StrongP%40ss%21@localhost:3306/ia_marks_db"
```

## Create the MySQL database and user

Run these SQL statements in MySQL Workbench or via the MySQL CLI:

```sql
CREATE DATABASE ia_marks_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ia_user'@'localhost' IDENTIFIED BY 'StrongP@ss!';
GRANT ALL PRIVILEGES ON ia_marks_db.* TO 'ia_user'@'localhost';
FLUSH PRIVILEGES;
```

If you need remote access from any host:

```sql
CREATE USER 'ia_user'@'%' IDENTIFIED BY 'StrongP@ss!';
GRANT ALL PRIVILEGES ON ia_marks_db.* TO 'ia_user'@'%';
FLUSH PRIVILEGES;
```

## Connect using MySQL Workbench

1. Open MySQL Workbench.
2. Create a new connection.
3. Set:
   - Connection Name: `IA Marks`
   - Hostname: `localhost` (or your MySQL host)
   - Port: `3306`
   - Username: `ia_user`
   - Password: `StrongP@ss!`
4. Test the connection and save.
5. Open the connection, then open the `ia_marks_db` schema.

## Run the app

```powershell
python app.py
```

If the database exists and the URL is correct, the app will create missing tables automatically when it starts.

## View stored data

If using MySQL Workbench, open `ia_marks_db` and inspect tables such as:

- `students`
- `faculties`
- `subjects`
- `marks`
- `allocations`
- `activities`

Or use the MySQL CLI:

```bash
mysql -u ia_user -p -h localhost -P 3306 ia_marks_db
SHOW TABLES;
SELECT * FROM students LIMIT 20;
```
