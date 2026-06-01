import secrets
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from config.auth_config import role_required
from repositories.users.user_repository import UserRepository
from repositories.roles.role_repository import RoleRepository
from database.db import log_event

users_bp = Blueprint('users', __name__, url_prefix='/system/users')

_user_repo = UserRepository()
_role_repo = RoleRepository()


# ── Page routes ──────────────────────────────────────────────────────────────

@users_bp.route('/')
@login_required
@role_required('superuser')
def users_list():
    return render_template('users/list.html')


@users_bp.route('/create')
@login_required
@role_required('superuser')
def create_user():
    roles = _role_repo.get_all()
    available_employees = [dict(e) for e in _user_repo.get_available_employees()]
    return render_template('users/create.html', roles=roles, available_employees=available_employees)


@users_bp.route('/<int:user_id>/edit')
@login_required
@role_required('superuser')
def edit_user(user_id: int):
    user_row = _user_repo.get_by_id(user_id)
    if not user_row:
        flash('Użytkownik nie istnieje', 'error')
        return redirect(url_for('users.users_list'))

    if user_row['role'] == 'superuser' and current_user.id != user_id:
        flash('Nie możesz edytować konta właściciela', 'error')
        return redirect(url_for('users.users_list'))

    roles = _role_repo.get_all()
    available_employees = _user_repo.get_available_employees()
    current_employee = _user_repo.get_employee_for_user(user_id)
    return render_template('users/edit.html', user=user_row, roles=roles,
                           available_employees=available_employees,
                           current_employee=current_employee)


# ── API routes ────────────────────────────────────────────────────────────────

@users_bp.route('/api', methods=['GET'])
@login_required
@role_required('superuser')
def api_list():
    rows = _user_repo.get_all_with_employee()
    users = []
    for r in rows:
        emp_name = None
        if r['employee_first_name']:
            emp_name = f"{r['employee_first_name']} {r['employee_last_name']}"
        users.append({
            'id': r['id'],
            'email': r['email'],
            'full_name': r['full_name'],
            'role': r['role'],
            'is_active': bool(r['is_active']),
            'last_login': r['last_login'],
            'created_at': r['created_at'],
            'employee_id': r['employee_id'],
            'employee_mosys_id': r['employee_mosys_id'],
            'employee_name': emp_name,
        })
    return jsonify({'users': users, 'count': len(users)})


@users_bp.route('/api', methods=['POST'])
@login_required
@role_required('superuser')
def api_create():
    data = request.get_json() or {}
    mosys_employee_id = data.get('mosys_employee_id', '').strip()
    full_name = data.get('full_name', '').strip()
    role = data.get('role', '')
    employee_id = data.get('employee_id')

    if not all([mosys_employee_id, full_name, role]):
        return jsonify({'success': False, 'error': 'Wszystkie pola są wymagane'}), 400

    email = f"{mosys_employee_id}@dmc.local"
    temp_password = secrets.token_urlsafe(12)

    try:
        user_id = _user_repo.create_user(email, temp_password, full_name, role, must_change_password=True)
        if employee_id:
            _user_repo.link_employee(int(employee_id), user_id)
        log_event('user_create', user_id=current_user.id, user_email=current_user.email,
                  user_name=current_user.full_name, entity_type='user', entity_id=user_id,
                  detail=f'nr {mosys_employee_id} ({full_name})', ip_address=request.remote_addr)
        return jsonify({'success': True, 'user_id': user_id}), 201
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        if 'UNIQUE' in str(e):
            return jsonify({'success': False, 'error': 'Ten numer pracownika jest już zajęty'}), 409
        return jsonify({'success': False, 'error': 'Błąd tworzenia użytkownika'}), 500


@users_bp.route('/api/<int:user_id>', methods=['PUT'])
@login_required
@role_required('superuser')
def api_update(user_id: int):
    existing = _user_repo.get_by_id(user_id)
    if not existing:
        return jsonify({'success': False, 'error': 'Użytkownik nie istnieje'}), 404

    if existing['role'] == 'superuser' and current_user.id != user_id:
        return jsonify({'success': False, 'error': 'Nie możesz edytować konta właściciela'}), 403

    data = request.get_json() or {}
    full_name = data.get('full_name', '').strip()
    role = data.get('role', '')
    is_active = bool(data.get('is_active', True))
    employee_id = data.get('employee_id')

    if not all([full_name, role]):
        return jsonify({'success': False, 'error': 'Wymagane pola są puste'}), 400

    try:
        _user_repo.unlink_employee(user_id)
        _user_repo.update_user(user_id, full_name, role, is_active)
        if employee_id:
            _user_repo.link_employee(int(employee_id), user_id)
        log_event('user_update', user_id=current_user.id, user_email=current_user.email,
                  user_name=current_user.full_name, entity_type='user', entity_id=user_id,
                  detail=full_name, ip_address=request.remote_addr)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': 'Błąd aktualizacji użytkownika'}), 500


@users_bp.route('/api/<int:user_id>/toggle-active', methods=['PUT'])
@login_required
@role_required('superuser')
def api_toggle_active(user_id: int):
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Nie możesz dezaktywować swojego konta'}), 400
    try:
        new_state = _user_repo.toggle_active(user_id)
        log_event('user_toggle_active', user_id=current_user.id, user_email=current_user.email,
                  user_name=current_user.full_name, entity_type='user', entity_id=user_id,
                  detail=f'active={new_state}', ip_address=request.remote_addr)
        return jsonify({'success': True, 'is_active': new_state})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404


@users_bp.route('/api/<int:user_id>/reset-password', methods=['POST'])
@login_required
@role_required('superuser')
def api_reset_password(user_id: int):
    data = request.get_json() or {}
    new_password = data.get('password', '')
    if len(new_password) < 8:
        return jsonify({'success': False, 'error': 'Hasło musi mieć co najmniej 8 znaków'}), 400
    _user_repo.update_password(user_id, new_password)
    log_event('user_password_reset', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='user', entity_id=user_id,
              ip_address=request.remote_addr)
    return jsonify({'success': True})
