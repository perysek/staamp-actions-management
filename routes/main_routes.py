from flask import Blueprint, redirect, url_for
from flask_login import login_required

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    return redirect(url_for('items.items_list'))
