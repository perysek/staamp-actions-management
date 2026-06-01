from flask import Blueprint, render_template
from flask_login import login_required, current_user

from repositories.items.item_repository import ItemRepository
from repositories.roles.role_repository import RoleRepository

main_bp = Blueprint('main', __name__)

_item_repo = ItemRepository()
_role_repo = RoleRepository()

# Status → Polish label (kept in sync with routes/items/routes.py).
_ITEM_STATUS_LABELS = {
    'open': 'Otwarte', 'in_progress': 'W toku', 'on_hold': 'Wstrzymane',
    'done': 'Zakończone', 'cancelled': 'Anulowane',
}


@main_bp.route('/')
@login_required
def index():
    """Dashboard — counts of items by status (scoped by the assigned-only flag)."""
    assigned_only = _role_repo.role_has_flag(current_user.role, 'actions_view_assigned_only')
    items = _item_repo.get_for_user(current_user.id, assigned_only)

    counts = {key: 0 for key in _ITEM_STATUS_LABELS}
    for it in items:
        counts[it['status']] = counts.get(it['status'], 0) + 1

    summary = [
        {'status': key, 'label': label, 'count': counts.get(key, 0)}
        for key, label in _ITEM_STATUS_LABELS.items()
    ]
    return render_template('main/dashboard.html', summary=summary, total=len(items))
