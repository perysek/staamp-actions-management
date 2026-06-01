from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from config.auth_config import role_required
from repositories.roles.role_repository import RoleRepository, ALL_MODULES, MODULE_DISPLAY_NAMES
from database.db import log_event

roles_bp = Blueprint('roles', __name__, url_prefix='/system/roles')

_role_repo = RoleRepository()


# ── Page routes ──────────────────────────────────────────────────────────────

@roles_bp.route('/')
@login_required
@role_required('superuser')
def roles_list():
    return render_template('roles/list.html')


@roles_bp.route('/create')
@login_required
@role_required('superuser')
def create_role():
    return render_template('roles/create.html',
                           all_modules=ALL_MODULES,
                           module_display_names=MODULE_DISPLAY_NAMES)


@roles_bp.route('/<int:role_id>/edit')
@login_required
@role_required('superuser')
def edit_role(role_id: int):
    role = _role_repo.get_by_id(role_id)
    if not role:
        flash('Rola nie istnieje', 'error')
        return redirect(url_for('roles.roles_list'))
    permissions = _role_repo.get_permissions(role_id)
    return render_template('roles/edit.html', role=role, permissions=permissions,
                           all_modules=ALL_MODULES, module_display_names=MODULE_DISPLAY_NAMES)


# ── API routes ────────────────────────────────────────────────────────────────

@roles_bp.route('/api', methods=['GET'])
@login_required
@role_required('superuser')
def api_list():
    rows = _role_repo.get_all()
    roles = []
    for r in rows:
        permissions = _role_repo.get_permissions(r['id'])
        roles.append({
            'id': r['id'],
            'name': r['name'],
            'display_name': r['display_name'],
            'is_protected': bool(r['is_protected']),
            'permissions': permissions,
            'access_count': r['access_count'],
        })
    return jsonify({'roles': roles})


@roles_bp.route('/api', methods=['POST'])
@login_required
@role_required('superuser')
def api_create():
    data = request.get_json() or {}
    name = data.get('name', '').strip().lower()
    display_name = data.get('display_name', '').strip()
    permissions = data.get('permissions', {})

    if not name or not display_name:
        return jsonify({'success': False, 'error': 'Nazwa i wyświetlana nazwa są wymagane'}), 400

    import re
    if not re.match(r'^[a-z_]+$', name):
        return jsonify({'success': False, 'error': 'Nazwa może zawierać tylko małe litery i podkreślenia'}), 400

    try:
        role_id = _role_repo.create(name, display_name)
        _role_repo.set_permissions(role_id, permissions)
        log_event('role_create', user_id=current_user.id, user_email=current_user.email,
                  user_name=current_user.full_name, entity_type='role', entity_id=role_id,
                  detail=name, ip_address=request.remote_addr)
        return jsonify({'success': True, 'role_id': role_id}), 201
    except Exception as e:
        if 'UNIQUE' in str(e):
            return jsonify({'success': False, 'error': 'Rola o tej nazwie już istnieje'}), 409
        return jsonify({'success': False, 'error': 'Błąd tworzenia roli'}), 500


@roles_bp.route('/api/<int:role_id>', methods=['PUT'])
@login_required
@role_required('superuser')
def api_update(role_id: int):
    role = _role_repo.get_by_id(role_id)
    if not role:
        return jsonify({'success': False, 'error': 'Rola nie istnieje'}), 404

    data = request.get_json() or {}
    display_name = data.get('display_name', '').strip()
    permissions = data.get('permissions', {})

    if not display_name:
        return jsonify({'success': False, 'error': 'Wyświetlana nazwa jest wymagana'}), 400

    _role_repo.update(role_id, display_name)
    _role_repo.set_permissions(role_id, permissions)
    log_event('role_update', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='role', entity_id=role_id,
              detail=display_name, ip_address=request.remote_addr)
    return jsonify({'success': True})


@roles_bp.route('/api/<int:role_id>', methods=['DELETE'])
@login_required
@role_required('superuser')
def api_delete(role_id: int):
    deleted = _role_repo.delete(role_id)
    if not deleted:
        return jsonify({'success': False, 'error': 'Nie można usunąć chronionej lub nieistniejącej roli'}), 400
    log_event('role_delete', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='role', entity_id=role_id,
              ip_address=request.remote_addr)
    return jsonify({'success': True})
