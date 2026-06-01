from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from config.auth_config import role_required
from repositories.employees.employee_repository import EmployeeRepository
from database.db import log_event

employees_bp = Blueprint('employees', __name__, url_prefix='/system/employees')

_emp_repo = EmployeeRepository()


@employees_bp.route('/')
@login_required
@role_required('superuser')
def employees_list():
    return render_template('employees/list.html')


# ── API ───────────────────────────────────────────────────────────────────────

@employees_bp.route('/api', methods=['GET'])
@login_required
@role_required('superuser')
def api_list():
    rows = _emp_repo.get_all()
    employees = []
    for r in rows:
        employees.append({
            'id': r['id'],
            'first_name': r['first_name'],
            'last_name': r['last_name'],
            'full_name': f"{r['last_name']} {r['first_name']}".strip(),
            'employee_no': r['employee_no'],
            'mosys_employee_id': r['mosys_employee_id'],
            'user_id': r['user_id'],
            'user_full_name': r['user_full_name'],
            'user_email': r['user_email'],
            'created_at': r['created_at'],
        })
    return jsonify({'employees': employees, 'count': len(employees)})


@employees_bp.route('/api', methods=['POST'])
@login_required
@role_required('superuser')
def api_create():
    data = request.get_json() or {}
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    employee_no = data.get('employee_no', '').strip() or None
    mosys_id = data.get('mosys_employee_id', '').strip() or None

    if not last_name:
        return jsonify({'success': False, 'error': 'Nazwisko jest wymagane'}), 400

    try:
        emp_id = _emp_repo.create(first_name, last_name, employee_no, mosys_id)
        log_event('employee_create', user_id=current_user.id, user_email=current_user.email,
                  user_name=current_user.full_name, entity_type='employee', entity_id=emp_id,
                  detail=f'{last_name} {first_name}', ip_address=request.remote_addr)
        return jsonify({'success': True, 'employee_id': emp_id}), 201
    except Exception as e:
        if 'UNIQUE' in str(e):
            return jsonify({'success': False, 'error': 'Pracownik z tym ID MOSYS już istnieje'}), 409
        return jsonify({'success': False, 'error': 'Błąd tworzenia pracownika'}), 500


@employees_bp.route('/api/<int:employee_id>', methods=['PUT'])
@login_required
@role_required('superuser')
def api_update(employee_id: int):
    data = request.get_json() or {}
    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    employee_no = data.get('employee_no', '').strip() or None
    mosys_id = data.get('mosys_employee_id', '').strip() or None

    if not last_name:
        return jsonify({'success': False, 'error': 'Nazwisko jest wymagane'}), 400

    try:
        _emp_repo.update(employee_id, first_name, last_name, employee_no, mosys_id)
        log_event('employee_update', user_id=current_user.id, user_email=current_user.email,
                  user_name=current_user.full_name, entity_type='employee', entity_id=employee_id,
                  detail=f'{last_name} {first_name}', ip_address=request.remote_addr)
        return jsonify({'success': True})
    except Exception as e:
        if 'UNIQUE' in str(e):
            return jsonify({'success': False, 'error': 'Ten ID MOSYS jest już przypisany innemu pracownikowi'}), 409
        return jsonify({'success': False, 'error': 'Błąd aktualizacji'}), 500


@employees_bp.route('/api/<int:employee_id>', methods=['DELETE'])
@login_required
@role_required('superuser')
def api_delete(employee_id: int):
    try:
        deleted = _emp_repo.delete(employee_id)
        if not deleted:
            return jsonify({'success': False, 'error': 'Pracownik nie istnieje'}), 404
        log_event('employee_delete', user_id=current_user.id, user_email=current_user.email,
                  user_name=current_user.full_name, entity_type='employee', entity_id=employee_id,
                  ip_address=request.remote_addr)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@employees_bp.route('/api/sync-mosys', methods=['POST'])
@login_required
@role_required('superuser')
def api_sync_mosys():
    from services.mosys_service import get_all_employees
    try:
        mosys_employees = get_all_employees()
    except Exception as e:
        return jsonify({'success': False, 'error': f'Błąd połączenia z MOSYS: {e}'}), 503

    if not mosys_employees:
        return jsonify({'success': False, 'error': 'MOSYS nie zwrócił żadnych operatorów (CODICE LIKE 9%)'}), 503

    result = _emp_repo.sync_from_mosys(mosys_employees)
    log_event('employee_sync_mosys', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name,
              detail=f"added={result['added']}, updated={result['updated']}, total={len(mosys_employees)}",
              ip_address=request.remote_addr)
    return jsonify({
        'success': True,
        'added': result['added'],
        'updated': result['updated'],
        'total_mosys': len(mosys_employees),
    })
