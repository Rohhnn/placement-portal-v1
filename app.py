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


# ---- Home route ----

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

        # Company must be approved before logging in
        if user.role == 'company' and user.company:
            if user.company.approval_status != 'approved':
                flash('Your company registration is pending admin approval.', 'warning')
                return redirect(url_for('login'))
            if user.company.is_blacklisted:
                flash('Your company has been blacklisted.', 'danger')
                return redirect(url_for('login'))

        # Student blacklist check
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
        db.session.flush()  # Get user.id before committing

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
            # Handle resume upload
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


# ---- Dashboard placeholders ----

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    return render_template('admin/dashboard.html')


@app.route('/company/dashboard')
@login_required
def company_dashboard():
    if current_user.role != 'company':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    return render_template('company/dashboard.html')


@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    return render_template('student/dashboard.html')


if __name__ == '__main__':
    app.run(debug=True)