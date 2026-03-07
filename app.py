import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from config import Config
from extensions import db, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        from models import User, Company, Student, PlacementDrive, Application
        db.create_all()
        seed_admin()

    return app


def seed_admin():
    from models import User
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            username='admin',
            password=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))


app = create_app()


# ---- Home ----

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for(current_user.role + '_dashboard'))
    return redirect(url_for('login'))


# ---- Auth routes ----

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(current_user.role + '_dashboard'))

    if request.method == 'POST':
        from models import User
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))

        if not user.is_active_user:
            flash('Your account has been deactivated. Contact admin.', 'danger')
            return redirect(url_for('login'))

        if user.role == 'company' and user.company:
            if user.company.approval_status != 'approved':
                flash('Your company registration is pending admin approval.', 'warning')
                return redirect(url_for('login'))
            if user.company.is_blacklisted:
                flash('Your company has been blacklisted.', 'danger')
                return redirect(url_for('login'))

        if user.role == 'student' and user.student:
            if user.student.is_blacklisted:
                flash('Your account has been blacklisted.', 'danger')
                return redirect(url_for('login'))

        login_user(user)
        flash('Logged in successfully.', 'success')
        return redirect(url_for(user.role + '_dashboard'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(current_user.role + '_dashboard'))

    if request.method == 'POST':
        from models import User, Company, Student
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if role not in ['company', 'student']:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('register'))

        user = User(
            username=username,
            password=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.flush()

        if role == 'company':
            company = Company(
                user_id=user.id,
                company_name=request.form.get('company_name'),
                industry=request.form.get('industry'),
                website=request.form.get('website'),
                hr_contact=request.form.get('hr_contact'),
                description=request.form.get('description'),
                approval_status='pending'
            )
            db.session.add(company)

        elif role == 'student':
            resume_path = None
            if 'resume' in request.files:
                file = request.files['resume']
                if file.filename:
                    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                    filename = secure_filename(f"{username}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    resume_path = filename

            student = Student(
                user_id=user.id,
                full_name=request.form.get('full_name'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                education=request.form.get('education'),
                skills=request.form.get('skills'),
                resume_path=resume_path
            )
            db.session.add(student)

        db.session.commit()

        if role == 'company':
            flash('Registration successful. Please wait for admin approval.', 'info')
        else:
            flash('Registration successful. You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))


# ---- Admin routes ----

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import Company, Student, PlacementDrive, Application
    stats = {
        'total_companies': Company.query.count(),
        'total_students': Student.query.count(),
        'total_drives': PlacementDrive.query.count(),
        'total_applications': Application.query.count(),
        'pending_companies': Company.query.filter_by(approval_status='pending').count(),
        'pending_drives': PlacementDrive.query.filter_by(status='pending').count()
    }
    return render_template('admin/dashboard.html', stats=stats)


@app.route('/admin/companies')
@login_required
def admin_companies():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import Company
    search = request.args.get('search', '')
    if search:
        companies = Company.query.filter(
            (Company.company_name.ilike(f'%{search}%')) |
            (Company.industry.ilike(f'%{search}%'))
        ).all()
    else:
        companies = Company.query.all()
    return render_template('admin/companies.html', companies=companies, search=search)


@app.route('/admin/company/<int:company_id>/approve')
@login_required
def admin_approve_company(company_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import Company
    company = Company.query.get_or_404(company_id)
    company.approval_status = 'approved'
    db.session.commit()
    flash(f'{company.company_name} has been approved.', 'success')
    return redirect(url_for('admin_companies'))


@app.route('/admin/company/<int:company_id>/reject')
@login_required
def admin_reject_company(company_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import Company
    company = Company.query.get_or_404(company_id)
    company.approval_status = 'rejected'
    db.session.commit()
    flash(f'{company.company_name} has been rejected.', 'warning')
    return redirect(url_for('admin_companies'))


@app.route('/admin/company/<int:company_id>/blacklist')
@login_required
def admin_blacklist_company(company_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import Company
    company = Company.query.get_or_404(company_id)
    company.is_blacklisted = not company.is_blacklisted
    db.session.commit()
    status = 'blacklisted' if company.is_blacklisted else 'unblacklisted'
    flash(f'{company.company_name} has been {status}.', 'info')
    return redirect(url_for('admin_companies'))


@app.route('/admin/students')
@login_required
def admin_students():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import Student
    search = request.args.get('search', '')
    if search:
        students = Student.query.filter(
            (Student.full_name.ilike(f'%{search}%')) |
            (Student.email.ilike(f'%{search}%')) |
            (Student.phone.ilike(f'%{search}%'))
        ).all()
    else:
        students = Student.query.all()
    return render_template('admin/students.html', students=students, search=search)


@app.route('/admin/student/<int:student_id>/blacklist')
@login_required
def admin_blacklist_student(student_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import Student
    student = Student.query.get_or_404(student_id)
    student.is_blacklisted = not student.is_blacklisted
    db.session.commit()
    status = 'blacklisted' if student.is_blacklisted else 'unblacklisted'
    flash(f'{student.full_name} has been {status}.', 'info')
    return redirect(url_for('admin_students'))


@app.route('/admin/drives')
@login_required
def admin_drives():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import PlacementDrive
    drives = PlacementDrive.query.all()
    return render_template('admin/drives.html', drives=drives)


@app.route('/admin/drive/<int:drive_id>/approve')
@login_required
def admin_approve_drive(drive_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import PlacementDrive
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'approved'
    db.session.commit()
    flash(f'Drive "{drive.job_title}" has been approved.', 'success')
    return redirect(url_for('admin_drives'))


@app.route('/admin/drive/<int:drive_id>/reject')
@login_required
def admin_reject_drive(drive_id):
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import PlacementDrive
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'rejected'
    db.session.commit()
    flash(f'Drive "{drive.job_title}" has been rejected.', 'warning')
    return redirect(url_for('admin_drives'))


@app.route('/admin/applications')
@login_required
def admin_applications():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import Application
    applications = Application.query.all()
    return render_template('admin/applications.html', applications=applications)


# ---- Company routes ----

@app.route('/company/dashboard')
@login_required
def company_dashboard():
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import PlacementDrive
    company = current_user.company
    drives = PlacementDrive.query.filter_by(company_id=company.id).all()
    return render_template('company/dashboard.html', company=company, drives=drives)


@app.route('/company/create-drive', methods=['GET', 'POST'])
@login_required
def company_create_drive():
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import PlacementDrive
    from datetime import datetime

    if request.method == 'POST':
        deadline_str = request.form.get('application_deadline')
        deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date() if deadline_str else None

        drive = PlacementDrive(
            company_id=current_user.company.id,
            job_title=request.form.get('job_title'),
            job_description=request.form.get('job_description'),
            eligibility_criteria=request.form.get('eligibility_criteria'),
            skills_required=request.form.get('skills_required'),
            salary_range=request.form.get('salary_range'),
            application_deadline=deadline,
            status='pending'
        )
        db.session.add(drive)
        db.session.commit()
        flash('Placement drive created. Waiting for admin approval.', 'info')
        return redirect(url_for('company_dashboard'))

    return render_template('company/create_drive.html')


@app.route('/company/drive/<int:drive_id>/close')
@login_required
def company_close_drive(drive_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import PlacementDrive
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('company_dashboard'))

    drive.status = 'closed'
    db.session.commit()
    flash(f'Drive "{drive.job_title}" has been closed.', 'info')
    return redirect(url_for('company_dashboard'))


@app.route('/company/drive/<int:drive_id>/reopen')
@login_required
def company_reopen_drive(drive_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import PlacementDrive
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('company_dashboard'))

    drive.status = 'approved'
    db.session.commit()
    flash(f'Drive "{drive.job_title}" has been reopened.', 'info')
    return redirect(url_for('company_dashboard'))


@app.route('/company/drive/<int:drive_id>/applications')
@login_required
def company_view_applications(drive_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import PlacementDrive, Application
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('company_dashboard'))

    applications = Application.query.filter_by(drive_id=drive.id).all()
    return render_template('company/view_applications.html', drive=drive, applications=applications)


@app.route('/company/application/<int:app_id>/update', methods=['POST'])
@login_required
def company_update_application(app_id):
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))

    from models import Application
    application = Application.query.get_or_404(app_id)
    if application.drive.company_id != current_user.company.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('company_dashboard'))

    new_status = request.form.get('status')
    if new_status in ['shortlisted', 'selected', 'rejected']:
        application.status = new_status
        db.session.commit()
        flash(f'Application status updated to {new_status}.', 'success')

    return redirect(url_for('company_view_applications', drive_id=application.drive_id))


# ---- Student dashboard placeholder ----

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    return render_template('student/dashboard.html')


if __name__ == '__main__':
    app.run(debug=True)