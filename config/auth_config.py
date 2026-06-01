from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user

ROLE_HIERARCHY = {
    'superuser': 2,
    'operator': 1,
}

# Static fallback — DB role_permissions is the real source of truth
MODULE_PERMISSIONS = {
    'dmc_validation': ['superuser', 'operator'],
    'history':        ['superuser', 'operator'],
    'admin':          ['superuser'],
    'audit':          ['superuser'],
    'manual_mode':    ['superuser'],
    'tryb_korekty':   ['superuser'],
}

# TODO: MODULE_PERMISSIONS, ROLE_HIERARCHY - to redefine according the project scope and reqs


def role_required(*roles):
    """Decorator — requires exact role name match."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Musisz być zalogowany', 'error')
                return redirect(url_for('auth.login'))
            if current_user.role not in roles:
                flash('Brak uprawnień', 'error')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def module_permission_required(*module_names):
    """Decorator — DB lookup with static fallback. OR logic across module names."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Musisz być zalogowany', 'error')
                return redirect(url_for('auth.login'))

            has_access = False
            try:
                from repositories.roles.role_repository import RoleRepository
                repo = RoleRepository()
                for mod in module_names:
                    if repo.role_has_module_access(current_user.role, mod):
                        has_access = True
                        break
            except Exception:
                for mod in module_names:
                    if current_user.role in MODULE_PERMISSIONS.get(mod, []):
                        has_access = True
                        break

            if not has_access:
                flash(f'Brak dostępu do modułu: {module_names[0]}', 'error')
                return redirect(url_for('main.index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def get_user_module_permissions(role_name: str) -> dict:
    """Returns {module: bool} for a role — used by context processor."""
    try:
        from repositories.roles.role_repository import RoleRepository
        return RoleRepository().get_user_module_permissions(role_name)
    except Exception:
        return {
            module: role_name in allowed_roles
            for module, allowed_roles in MODULE_PERMISSIONS.items()
        }
