from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from config.auth_config import role_required
from repositories.action_plans.action_plan_repository import ActionPlanRepository, NAME_MAX_LEN
from database.db import log_event

action_plans_bp = Blueprint('action_plans', __name__, url_prefix='/system/action-plans')

_plan_repo = ActionPlanRepository()


def _validate_name(data: dict, exclude_id: int = None):
    """Returns (name, error_response_tuple). error is None when valid."""
    name = (data.get('name') or '').strip()
    if not name:
        return None, (jsonify({'success': False, 'error': 'Nazwa jest wymagana'}), 400)
    if len(name) > NAME_MAX_LEN:
        return None, (jsonify({'success': False,
                               'error': f'Nazwa może mieć maksymalnie {NAME_MAX_LEN} znaków'}), 400)
    if _plan_repo.name_exists(name, exclude_id=exclude_id):
        return None, (jsonify({'success': False,
                               'error': 'Plan działań o tej nazwie już istnieje'}), 409)
    return name, None


# ── Page routes ──────────────────────────────────────────────────────────────

@action_plans_bp.route('/')
@login_required
@role_required('superuser')
def plans_list():
    return render_template('action_plans/list.html')


@action_plans_bp.route('/create')
@login_required
@role_required('superuser')
def create_plan():
    return render_template('action_plans/create.html')


@action_plans_bp.route('/<int:plan_id>/edit')
@login_required
@role_required('superuser')
def edit_plan(plan_id: int):
    plan = _plan_repo.get_by_id(plan_id)
    if not plan:
        flash('Plan działań nie istnieje', 'error')
        return redirect(url_for('action_plans.plans_list'))
    return render_template('action_plans/edit.html', plan=plan)


# ── API routes ────────────────────────────────────────────────────────────────

@action_plans_bp.route('/api', methods=['GET'])
@login_required
@role_required('superuser')
def api_list():
    rows = _plan_repo.get_all()
    plans = [{
        'id': r['id'],
        'name': r['name'],
        'sort_order': r['sort_order'],
        'is_active': bool(r['is_active']),
        'usage_count': r['usage_count'],
    } for r in rows]
    return jsonify({'plans': plans})


@action_plans_bp.route('/api', methods=['POST'])
@login_required
@role_required('superuser')
def api_create():
    data = request.get_json() or {}
    name, err = _validate_name(data)
    if err:
        return err
    sort_order = int(data.get('sort_order') or 0)
    is_active = bool(data.get('is_active', True))
    try:
        plan_id = _plan_repo.create(name, sort_order, is_active)
    except Exception as e:
        if 'UNIQUE' in str(e):
            return jsonify({'success': False, 'error': 'Plan działań o tej nazwie już istnieje'}), 409
        return jsonify({'success': False, 'error': 'Błąd tworzenia planu działań'}), 500
    log_event('action_plan_create', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='action_plan', entity_id=plan_id,
              detail=name, ip_address=request.remote_addr)
    return jsonify({'success': True, 'plan_id': plan_id}), 201


@action_plans_bp.route('/api/<int:plan_id>', methods=['PUT'])
@login_required
@role_required('superuser')
def api_update(plan_id: int):
    plan = _plan_repo.get_by_id(plan_id)
    if not plan:
        return jsonify({'success': False, 'error': 'Plan działań nie istnieje'}), 404
    data = request.get_json() or {}
    name, err = _validate_name(data, exclude_id=plan_id)
    if err:
        return err
    sort_order = int(data.get('sort_order') or 0)
    is_active = bool(data.get('is_active', True))
    _plan_repo.update(plan_id, name, sort_order, is_active)
    log_event('action_plan_update', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='action_plan', entity_id=plan_id,
              detail=name, ip_address=request.remote_addr)
    return jsonify({'success': True})


@action_plans_bp.route('/api/<int:plan_id>', methods=['DELETE'])
@login_required
@role_required('superuser')
def api_delete(plan_id: int):
    plan = _plan_repo.get_by_id(plan_id)
    if not plan:
        return jsonify({'success': False, 'error': 'Plan działań nie istnieje'}), 404
    used = _plan_repo.usage_count(plan_id)
    if used > 0:
        return jsonify({'success': False,
                        'error': f'Nie można usunąć planu przypisanego do pozycji ({used})'}), 409
    _plan_repo.delete(plan_id)
    log_event('action_plan_delete', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='action_plan', entity_id=plan_id,
              detail=plan['name'], ip_address=request.remote_addr)
    return jsonify({'success': True})
