# Placement Portal (v1)

A role-based web application for managing campus placement workflows among institute administrators, companies, and students.

## Overview

The application supports registration and authentication for company and student accounts, admin approval of companies and placement drives, drive posting and applicant review by companies, and drive browsing and application tracking by students. Access is restricted by role. Blacklisted accounts cannot log in.

## Roles

- **Admin**: Approves or rejects company registrations and placement drives; searches companies and students; blacklists or unblacklists accounts; views aggregate placement statistics.
- **Company**: Registers for admin approval; creates placement drives; views applicants; updates application status.
- **Student**: Registers and maintains a profile (including resume upload); browses approved drives; applies to drives; tracks application status.

## Domain model

Five SQLite tables define the domain:

| Entity | Purpose |
|--------|---------|
| `User` | Shared authentication record with role (`admin`, `company`, `student`) |
| `Company` | Company profile linked one-to-one to a user |
| `Student` | Student profile linked one-to-one to a user |
| `PlacementDrive` | Job posting created by a company |
| `Application` | Student application to a drive (unique per student–drive pair) |

## Tech stack

- Flask, Flask-SQLAlchemy, Flask-Login
- Jinja2 templates with Bootstrap 5
- SQLite
- Werkzeug password hashing and secure file uploads

The UI is server-rendered. There is no separate REST API layer.

## Project structure

```
.gitignore
README.md
requirements.txt
app.py                 # Application factory and routes
models.py              # SQLAlchemy models
config.py              # Configuration
extensions.py          # Flask extensions
templates/
  base.html
  login.html
  register.html
  view_student.html
  admin/               # Admin dashboards and management views
  company/             # Company dashboards and drive views
  student/             # Student dashboards and profile views
static/
  css/style.css
  uploads/             # Resume uploads (contents ignored)
```

## Setup

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

The application seeds a default admin account on first run (`admin` / `admin123`). Change this credential before any non-local use.

## Course Context

This repository contains the course project submitted for **Modern Application Development I** (Application Development 1) at IIT Madras, January 2026 term. It implements the placement portal milestone requirements using a monolithic Flask application with session-based authentication and server-rendered templates.
