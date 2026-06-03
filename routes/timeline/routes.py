from flask import Blueprint, render_template, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from config.auth_config import module_permission_required
from repositories.items.item_repository import ItemRepository
from repositories.subtasks.subtask_repository import SubtaskRepository
from repositories.roles.role_repository import RoleRepository

timeline_bp = Blueprint('timeline', __name__, url_prefix='/timeline')

_item_repo = ItemRepository()
_subtask_repo = SubtaskRepository()
_role_repo = RoleRepository()


@timeline_bp.route('/')
@login_required
@module_permission_required('timeline')
def timeline_index():
    """Item picker — list items (scoped by flag) each linking to its gantt."""
    assigned_only = _role_repo.role_has_flag(current_user.role, 'actions_view_assigned_only')
    rows = _item_repo.get_for_user(current_user.id, assigned_only)
    items = [{
        'id': r['id'], 'plan_name': r['plan_name'], 'title': r['title'],
        'status': r['status'], 'due_date': r['due_date'], 'subtask_count': r['subtask_count'],
    } for r in rows]
    return render_template('timeline/index.html', items=items)


@timeline_bp.route('/<int:item_id>')
@login_required
@module_permission_required('timeline')
def timeline_view(item_id: int):
    item = _item_repo.get_by_id(item_id)
    if not item:
        flash('Pozycja nie istnieje', 'error')
        return redirect(url_for('timeline.timeline_index'))
    can_manage = current_user.role in ('superuser', 'manager')
    active_users = _item_repo.get_active_users()
    return render_template('timeline/view.html', item=item,
                           can_manage=can_manage, active_users=active_users)


@timeline_bp.route('/api/<int:item_id>', methods=['GET'])
@login_required
@module_permission_required('timeline')
def api_timeline(item_id: int):
    item = _item_repo.get_by_id(item_id)
    if not item:
        return jsonify({'success': False, 'error': 'Pozycja nie istnieje'}), 404
    rows = _subtask_repo.get_for_item(item_id)
    subtasks = []
    for r in rows:
        subtasks.append({
            'id': r['id'],
            'title': r['title'],
            'responsible_user_id': r['responsible_user_id'],
            'responsible_name': r['responsible_name'],
            'start_date': r['start_date'],
            'finish_date': r['finish_date'],
            'status': r['status'],
            'color': r['color'] if 'color' in r.keys() else None,
        })
    return jsonify({
        'item': {'id': item['id'], 'title': item['title'],
                 'item_type': item['item_type'], 'status': item['status'],
                 'due_date': item['due_date']},
        'subtasks': subtasks,
    })
