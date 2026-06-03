import os
from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

login_manager = LoginManager()


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    from database.db import initialize_database
    initialize_database()

    # Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Musisz być zalogowany, aby uzyskać dostęp do tej strony.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        try:
            from repositories.users.user_repository import UserRepository
            repo = UserRepository()
            row = repo.get_by_id(int(user_id))
            return repo.row_to_user(row) if row else None
        except Exception:
            return None

    # Blueprints
    from routes.auth.routes import auth_bp
    from routes.users.routes import users_bp
    from routes.roles.routes import roles_bp
    from routes.employees.routes import employees_bp
    from routes.main_routes import main_bp
    from routes.items.routes import items_bp
    from routes.timeline.routes import timeline_bp
    from routes.audit.routes import audit_bp
    from routes.action_plans.routes import action_plans_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(roles_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(timeline_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(action_plans_bp)

    @app.context_processor
    def inject_globals():
        from datetime import datetime
        from flask_login import current_user
        from config.auth_config import get_user_module_permissions

        user_permissions = {}
        if current_user.is_authenticated:
            try:
                user_permissions = get_user_module_permissions(current_user.role)
            except Exception:
                pass

        current_mosys_employee_id = None
        if current_user.is_authenticated:
            try:
                from repositories.users.user_repository import UserRepository
                emp = UserRepository().get_employee_for_user(current_user.id)
                current_mosys_employee_id = emp['mosys_employee_id'] if emp else None
            except Exception:
                pass

        return {
            'now': datetime.now,
            'app_version': '1.0.0',
            'app_name': 'Staamp Global Actions Management',
            'user_permissions': user_permissions,
            'current_mosys_employee_id': current_mosys_employee_id,
        }

    return app
