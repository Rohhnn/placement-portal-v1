from extensions import db
from flask_login import UserMixin
from datetime import datetime


class User(db.Model, UserMixin):
    """Unified user table for all roles: admin, company, student."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'company', 'student'
    is_active_user = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # One-to-one links to role-specific profiles
    company = db.relationship('Company', backref='user', uselist=False)
    student = db.relationship('Student', backref='user', uselist=False)


class Company(db.Model):
    """Company profile, linked to a User with role='company'."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_name = db.Column(db.String(150), nullable=False)
    industry = db.Column(db.String(100))
    website = db.Column(db.String(200))
    hr_contact = db.Column(db.String(100))
    description = db.Column(db.Text)
    approval_status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'rejected'
    is_blacklisted = db.Column(db.Boolean, default=False)

    # A company can create many placement drives
    drives = db.relationship('PlacementDrive', backref='company', lazy=True)


class Student(db.Model):
    """Student profile, linked to a User with role='student'."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    education = db.Column(db.String(200))
    skills = db.Column(db.Text)
    resume_path = db.Column(db.String(300))
    is_blacklisted = db.Column(db.Boolean, default=False)

    # A student can have many applications
    applications = db.relationship('Application', backref='student', lazy=True)


class PlacementDrive(db.Model):
    """A recruitment drive created by a company."""
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    job_title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text)
    eligibility_criteria = db.Column(db.Text)
    skills_required = db.Column(db.Text)
    salary_range = db.Column(db.String(100))
    application_deadline = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'approved', 'closed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # A drive can receive many applications
    applications = db.relationship('Application', backref='drive', lazy=True)


class Application(db.Model):
    """A record of a student applying to a placement drive."""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drive.id'), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='applied')  # 'applied', 'shortlisted', 'selected', 'rejected'

    # Prevent duplicate applications: same student cannot apply to same drive twice
    __table_args__ = (
        db.UniqueConstraint('student_id', 'drive_id', name='unique_student_drive'),
    )