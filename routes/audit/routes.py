from flask import Blueprint, render_template
from flask_login import login_required

from config.auth_config import module_permission_required
from database.db import get_connection

audit_bp = Blueprint('audit', __name__, url_prefix='/system/audit')

# event_type → Polish label
EVENT_LABELS = {
    'login_ok': 'Logowanie', 'login_failed': 'Nieudane logowanie', 'logout': 'Wylogowanie',
    'password_changed': 'Zmiana hasła', 'password_set_first': 'Ustawienie pierwszego hasła',
    'user_create': 'Utworzenie użytkownika', 'user_update': 'Edycja użytkownika',
    'user_toggle_active': 'Zmiana aktywności konta', 'user_password_reset': 'Reset hasła',
    'employee_create': 'Utworzenie pracownika', 'employee_update': 'Edycja pracownika',
    'employee_delete': 'Usunięcie pracownika', 'employee_sync_mosys': 'Synchronizacja MOSYS',
    'role_create': 'Utworzenie roli', 'role_update': 'Edycja roli', 'role_delete': 'Usunięcie roli',
    'action_plan_create': 'Utworzenie planu działań', 'action_plan_update': 'Edycja planu działań',
    'action_plan_delete': 'Usunięcie planu działań',
    'item_create': 'Utworzenie pozycji', 'item_update': 'Edycja pozycji',
    'item_delete': 'Usunięcie pozycji',
    'subtask_create': 'Utworzenie podzadania', 'subtask_update': 'Edycja podzadania',
    'subtask_delete': 'Usunięcie podzadania', 'subtask_status': 'Zmiana statusu podzadania',
}

# event_type → badge CSS class
EVENT_CLASSES = {
    'login_ok': 'badge-ok', 'login_failed': 'badge-nok', 'logout': 'badge-na',
    'password_changed': 'badge-na', 'password_set_first': 'badge-na',
    'user_create': 'badge-ok', 'user_update': 'badge-na',
    'user_toggle_active': 'badge-na', 'user_password_reset': 'badge-na',
    'employee_create': 'badge-ok', 'employee_update': 'badge-na',
    'employee_delete': 'badge-nok', 'employee_sync_mosys': 'badge-ok',
    'role_create': 'badge-ok', 'role_update': 'badge-na', 'role_delete': 'badge-nok',
    'action_plan_create': 'badge-ok', 'action_plan_update': 'badge-na', 'action_plan_delete': 'badge-nok',
    'item_create': 'badge-ok', 'item_update': 'badge-na', 'item_delete': 'badge-nok',
    'subtask_create': 'badge-ok', 'subtask_update': 'badge-na',
    'subtask_delete': 'badge-nok', 'subtask_status': 'badge-na',
}


@audit_bp.route('/')
@login_required
@module_permission_required('audit')
def audit_list():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY occurred_at DESC LIMIT 500"
        ).fetchall()
    events = []
    for r in rows:
        events.append({
            'occurred_at': r['occurred_at'],
            'user_name': r['user_name'],
            'user_email': r['user_email'],
            'event_type': r['event_type'],
            'label': EVENT_LABELS.get(r['event_type'], r['event_type']),
            'badge_class': EVENT_CLASSES.get(r['event_type'], 'badge-na'),
            'entity_type': r['entity_type'],
            'entity_id': r['entity_id'],
            'detail': r['detail'],
            'ip_address': r['ip_address'],
        })
    return render_template('audit/list.html', events=events)
