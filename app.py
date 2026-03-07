from flask import Flask, render_template
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
    """Create default admin user if one does not already exist."""
    from models import User
    from werkzeug.security import generate_password_hash

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


@app.route('/')
def home():
    return '<h1>Placement Portal - Running</h1>'


if __name__ == '__main__':
    app.run(debug=True)