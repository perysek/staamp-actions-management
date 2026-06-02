import math
import re
from datetime import date, timedelta

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user

from config.auth_config import module_permission_required, manage_actions_required
from repositories.items.item_repository import ItemRepository
from repositories.subtasks.subtask_repository import SubtaskRepository
from repositories.roles.role_repository import RoleRepository
from database.db import log_event

items_bp = Blueprint('items', __name__, url_prefix='/items')

_item_repo = ItemRepository()
_subtask_repo = SubtaskRepository()
_role_repo = RoleRepository()

# ── Domain vocabulary (value, Polish label) ──────────────────────────────────
ITEM_TYPE_OPTIONS = [('task', 'Zadanie'), ('project', 'Projekt'),
                     ('action', 'Działanie'), ('goal', 'Cel')]
ITEM_STATUS_OPTIONS = [('open', 'Otwarte'), ('in_progress', 'W toku'),
                       ('on_hold', 'Wstrzymane'), ('done', 'Zakończone'),
                       ('cancelled', 'Anulowane')]
SUBTASK_STATUS_OPTIONS = [('not_started', 'Nie rozpoczęte'), ('in_progress', 'W toku'),
                          ('blocked', 'Zablokowane'), ('done', 'Zakończone'),
                          ('cancelled', 'Anulowane')]

ITEM_TYPES = [v for v, _ in ITEM_TYPE_OPTIONS]
ITEM_STATUSES = [v for v, _ in ITEM_STATUS_OPTIONS]
SUBTASK_STATUSES = [v for v, _ in SUBTASK_STATUS_OPTIONS]


# ── Due-date warning indicator ────────────────────────────────────────────────
# Terminal statuses never warn — a finished/cancelled action is not "late".
_WARN_SUPPRESSED_STATUSES = ('done', 'cancelled')


def _parse_ymd(value):
    """'YYYY-MM-DD' (optionally with a trailing ' HH:MM:SS') → date, parsed as a
    LOCAL calendar date. Returns None for empty/malformed values. Avoids the
    new Date('YYYY-MM-DD')-as-UTC pitfall by never going through a tz-aware path."""
    if not value:
        return None
    parts = str(value)[:10].split('-')
    if len(parts) != 3:
        return None
    try:
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, TypeError):
        return None


def _due_warning(due_date, earliest_start, created_at, status) -> str:
    """Warning level shown after the date in the actions list 'Termin' column.

    finish-date = the action's due_date (the value displayed in the column).
    start-date  = earliest subtask start_date, falling back to the action's
                  created_at when it has no scheduled subtasks.

      'overdue' (red)  — today is past the finish date.
      'soon'    (yellow) — today is within the final 10% of the start→finish
                  span, and that span is longer than 2 days (short-lived
                  actions never warn). The finish day itself counts as 'soon'.
      'none'    — otherwise, or for done/cancelled actions.
    """
    if status in _WARN_SUPPRESSED_STATUSES:
        return 'none'
    finish = _parse_ymd(due_date)
    if finish is None:
        return 'none'
    today = date.today()
    if today > finish:
        return 'overdue'
    start = _parse_ymd(earliest_start) or _parse_ymd(created_at)
    if start is None:
        return 'none'
    span = (finish - start).days
    if span <= 2:
        return 'none'
    warn_window = math.ceil(span * 0.1)
    if today >= finish - timedelta(days=warn_window):
        return 'soon'
    return 'none'


def _subtask_to_dict(row) -> dict:
    return {
        'id': row['id'],
        'item_id': row['item_id'],
        'title': row['title'],
        'description': row['description'],
        'responsible_user_id': row['responsible_user_id'],
        'responsible_name': row['responsible_name'] if 'responsible_name' in row.keys() else None,
        'start_date': row['start_date'],
        'finish_date': row['finish_date'],
        'status': row['status'],
        'color': row['color'] if 'color' in row.keys() else None,
        'sort_order': row['sort_order'],
    }


# ── Page routes ───────────────────────────────────────────────────────────────
@items_bp.route('/')
@login_required
@module_permission_required('actions')
def items_list():
    return render_template('items/list.html')


@items_bp.route('/<int:item_id>')
@login_required
@module_permission_required('actions')
def item_detail(item_id: int):
    item = _item_repo.get_by_id(item_id)
    if not item:
        flash('Pozycja nie istnieje', 'error')
        return redirect(url_for('items.items_list'))
    responsibles = _item_repo.get_responsibles(item_id)
    active_users = _item_repo.get_active_users()
    can_manage = current_user.role in ('superuser', 'manager')
    can_update_own = _role_repo.role_has_flag(current_user.role, 'subtasks_update_assigned_only')
    subtask_count = _item_repo.count_subtasks(item_id)
    return render_template('items/detail.html', item=item, responsibles=responsibles,
                           active_users=active_users, can_manage=can_manage,
                           can_update_own=can_update_own,
                           subtask_status_options=SUBTASK_STATUS_OPTIONS,
                           subtask_count=subtask_count)


@items_bp.route('/create')
@login_required
@manage_actions_required
def create_item():
    active_users = _item_repo.get_active_users()
    return render_template('items/create.html', active_users=active_users,
                           item_type_options=ITEM_TYPE_OPTIONS,
                           item_status_options=ITEM_STATUS_OPTIONS)


@items_bp.route('/<int:item_id>/edit')
@login_required
@manage_actions_required
def edit_item(item_id: int):
    item = _item_repo.get_by_id(item_id)
    if not item:
        flash('Pozycja nie istnieje', 'error')
        return redirect(url_for('items.items_list'))
    active_users = _item_repo.get_active_users()
    responsible_ids = [r['id'] for r in _item_repo.get_responsibles(item_id)]
    return render_template('items/edit.html', item=item, active_users=active_users,
                           responsible_ids=responsible_ids,
                           item_type_options=ITEM_TYPE_OPTIONS,
                           item_status_options=ITEM_STATUS_OPTIONS)


# ── Item API ────────────────────────────────────────────────────────────────
@items_bp.route('/api', methods=['GET'])
@login_required
@module_permission_required('actions')
def api_list():
    assigned_only = _role_repo.role_has_flag(current_user.role, 'actions_view_assigned_only')
    rows = _item_repo.get_for_user(current_user.id, assigned_only)
    items = [{
        'id': r['id'], 'item_type': r['item_type'], 'title': r['title'],
        'status': r['status'], 'due_date': r['due_date'],
        'subtask_count': r['subtask_count'], 'responsibles': r['responsibles'],
        'due_warning': _due_warning(r['due_date'], r['earliest_start'],
                                    r['created_at'], r['status']),
    } for r in rows]
    return jsonify({'items': items, 'count': len(items)})


@items_bp.route('/api', methods=['POST'])
@login_required
@manage_actions_required
def api_create():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    item_type = data.get('item_type', 'action')
    status = data.get('status', 'open')
    if not title:
        return jsonify({'success': False, 'error': 'Tytuł jest wymagany'}), 400
    if item_type not in ITEM_TYPES or status not in ITEM_STATUSES:
        return jsonify({'success': False, 'error': 'Nieprawidłowy typ lub status'}), 400
    item_id = _item_repo.create(item_type, title, data.get('description'),
                                status, data.get('due_date'), current_user.id)
    responsibles = data.get('responsibles') or []
    if responsibles:
        _item_repo.set_responsibles(item_id, responsibles)
    log_event('item_create', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='item', entity_id=item_id,
              detail=title, ip_address=request.remote_addr)
    return jsonify({'success': True, 'item_id': item_id}), 201


@items_bp.route('/api/<int:item_id>', methods=['PUT'])
@login_required
@manage_actions_required
def api_update(item_id: int):
    item = _item_repo.get_by_id(item_id)
    if not item:
        return jsonify({'success': False, 'error': 'Pozycja nie istnieje'}), 404
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    item_type = data.get('item_type', item['item_type'])
    status = data.get('status', item['status'])
    if not title:
        return jsonify({'success': False, 'error': 'Tytuł jest wymagany'}), 400
    if item_type not in ITEM_TYPES or status not in ITEM_STATUSES:
        return jsonify({'success': False, 'error': 'Nieprawidłowy typ lub status'}), 400
    _item_repo.update(item_id, item_type, title, data.get('description'),
                      status, data.get('due_date'))
    if 'responsibles' in data:
        _item_repo.set_responsibles(item_id, data.get('responsibles') or [])
    log_event('item_update', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='item', entity_id=item_id,
              detail=title, ip_address=request.remote_addr)
    return jsonify({'success': True})


@items_bp.route('/api/<int:item_id>', methods=['DELETE'])
@login_required
@manage_actions_required
def api_delete(item_id: int):
    deleted = _item_repo.delete(item_id)
    if not deleted:
        return jsonify({'success': False, 'error': 'Pozycja nie istnieje'}), 404
    log_event('item_delete', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='item', entity_id=item_id,
              ip_address=request.remote_addr)
    return jsonify({'success': True})


@items_bp.route('/api/<int:item_id>/responsibles', methods=['PUT'])
@login_required
@manage_actions_required
def api_set_responsibles(item_id: int):
    if not _item_repo.get_by_id(item_id):
        return jsonify({'success': False, 'error': 'Pozycja nie istnieje'}), 404
    data = request.get_json() or {}
    _item_repo.set_responsibles(item_id, data.get('responsibles') or [])
    log_event('item_update', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='item', entity_id=item_id,
              detail='responsibles', ip_address=request.remote_addr)
    return jsonify({'success': True})


# ── Subtask API ───────────────────────────────────────────────────────────────
@items_bp.route('/api/<int:item_id>/subtasks', methods=['GET'])
@login_required
@module_permission_required('actions')
def api_subtasks_list(item_id: int):
    rows = _subtask_repo.get_for_item(item_id)
    return jsonify({'subtasks': [_subtask_to_dict(r) for r in rows]})


@items_bp.route('/api/<int:item_id>/subtasks', methods=['POST'])
@login_required
@manage_actions_required
def api_subtask_create(item_id: int):
    if not _item_repo.get_by_id(item_id):
        return jsonify({'success': False, 'error': 'Pozycja nie istnieje'}), 404
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    status = data.get('status', 'not_started')
    if not title:
        return jsonify({'success': False, 'error': 'Tytuł jest wymagany'}), 400
    if status not in SUBTASK_STATUSES:
        return jsonify({'success': False, 'error': 'Nieprawidłowy status'}), 400
    sid = _subtask_repo.create(
        item_id, title, data.get('description'), data.get('responsible_user_id') or None,
        data.get('start_date'), data.get('finish_date'), status,
        int(data.get('sort_order') or 0),
    )
    log_event('subtask_create', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='subtask', entity_id=sid,
              detail=title, ip_address=request.remote_addr)
    return jsonify({'success': True, 'subtask_id': sid}), 201


@items_bp.route('/api/<int:item_id>/subtasks/<int:sid>', methods=['PUT'])
@login_required
@manage_actions_required
def api_subtask_update(item_id: int, sid: int):
    """Partial update — only the provided fields change; the rest keep their current values.
    Used by both the detail-page modal (full payload) and the Gantt inline editors."""
    subtask = _subtask_repo.get_by_id(sid)
    if not subtask:
        return jsonify({'success': False, 'error': 'Podzadanie nie istnieje'}), 404
    data = request.get_json() or {}

    title = (data.get('title', subtask['title']) or '').strip()
    if not title:
        return jsonify({'success': False, 'error': 'Tytuł jest wymagany'}), 400
    status = data.get('status', subtask['status'])
    if status not in SUBTASK_STATUSES:
        return jsonify({'success': False, 'error': 'Nieprawidłowy status'}), 400

    description = data.get('description', subtask['description'])
    responsible = data.get('responsible_user_id', subtask['responsible_user_id'])
    responsible = int(responsible) if responsible else None
    start_date = data.get('start_date', subtask['start_date'])
    finish_date = data.get('finish_date', subtask['finish_date'])

    _subtask_repo.update(sid, title, description, responsible, start_date, finish_date, status)
    log_event('subtask_update', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='subtask', entity_id=sid,
              detail=title, ip_address=request.remote_addr)
    return jsonify({'success': True})


@items_bp.route('/api/<int:item_id>/subtasks/<int:sid>', methods=['DELETE'])
@login_required
@manage_actions_required
def api_subtask_delete(item_id: int, sid: int):
    deleted = _subtask_repo.delete(sid)
    if not deleted:
        return jsonify({'success': False, 'error': 'Podzadanie nie istnieje'}), 404
    log_event('subtask_delete', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='subtask', entity_id=sid,
              ip_address=request.remote_addr)
    return jsonify({'success': True})


@items_bp.route('/api/<int:item_id>/subtasks/<int:sid>/status', methods=['PUT'])
@login_required
@module_permission_required('actions')
def api_subtask_status(item_id: int, sid: int):
    """Status-only update. Contributor-exception aware:
    managers/superusers update any subtask; users with the
    subtasks_update_assigned_only flag may update only their own; others are blocked."""
    subtask = _subtask_repo.get_by_id(sid)
    if not subtask:
        return jsonify({'success': False, 'error': 'Podzadanie nie istnieje'}), 404

    role = current_user.role
    is_manager = role in ('superuser', 'manager')
    has_update_flag = _role_repo.role_has_flag(role, 'subtasks_update_assigned_only')

    if not is_manager and not has_update_flag:
        return jsonify({'success': False, 'error': 'Brak uprawnień do zmiany statusu'}), 403
    if not is_manager and has_update_flag:
        if _subtask_repo.get_responsible(sid) != current_user.id:
            return jsonify({'success': False, 'error': 'Możesz zmieniać status tylko swoich podzadań'}), 403

    data = request.get_json() or {}
    new_status = data.get('status', '')
    if new_status not in SUBTASK_STATUSES:
        return jsonify({'success': False, 'error': 'Nieprawidłowy status'}), 400

    _subtask_repo.update_status(sid, new_status)
    log_event('subtask_status', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='subtask', entity_id=sid,
              detail=new_status, ip_address=request.remote_addr)
    return jsonify({'success': True})


@items_bp.route('/api/<int:item_id>/subtasks/<int:sid>/color', methods=['PUT'])
@login_required
@manage_actions_required
def api_subtask_color(item_id: int, sid: int):
    if not _subtask_repo.get_by_id(sid):
        return jsonify({'success': False, 'error': 'Podzadanie nie istnieje'}), 404
    data = request.get_json() or {}
    color = data.get('color')
    if color is not None:
        if not re.match(r'^#[0-9a-fA-F]{6}$', str(color)):
            return jsonify({'success': False, 'error': 'Nieprawidłowy kolor (oczekiwano #rrggbb)'}), 400
    _subtask_repo.update_color(sid, color)
    log_event('subtask_update', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, entity_type='subtask', entity_id=sid,
              detail=f'color={color}', ip_address=request.remote_addr)
    return jsonify({'success': True})
