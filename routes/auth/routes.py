import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from repositories.users.user_repository import UserRepository
from services.auth.auth_service import AuthService
from database.db import get_connection, log_event

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

_user_repo = UserRepository()
_auth_service = AuthService(_user_repo)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    employee_id = ''
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', '').strip()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        ok, user, error = _auth_service.authenticate_by_employee_id(employee_id, password)
        if ok:
            login_user(user, remember=remember)
            log_event('login_ok', user_id=user.id, user_email=user.email,
                      user_name=user.full_name, ip_address=request.remote_addr)
            if user.must_change_password:
                return redirect(url_for('auth.set_first_password'))
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        log_event('login_failed', detail=f"employee_id={employee_id}: {error}",
                  ip_address=request.remote_addr)
        flash(error, 'error')

    login_employees = _user_repo.get_login_employees()
    return render_template('auth/login.html', employee_id=employee_id,
                           login_employees=login_employees)


@auth_bp.route('/logout')
@login_required
def logout():
    log_event('logout', user_id=current_user.id, user_email=current_user.email,
              user_name=current_user.full_name, ip_address=request.remote_addr)
    logout_user()
    flash('Wylogowano pomyślnie', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/api/needs-setup')
def api_needs_setup():
    mosys_id = request.args.get('mosys_id', '').strip()
    if not mosys_id:
        return jsonify({'needs_setup': False})
    user = _user_repo.get_by_mosys_employee_id(mosys_id)
    if user and user.is_active and user.must_change_password:
        return jsonify({'needs_setup': True, 'full_name': user.full_name})
    return jsonify({'needs_setup': False})


@auth_bp.route('/first-login', methods=['POST'])
def first_login():
    mosys_id = request.form.get('mosys_id', '').strip()
    new_pw = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')

    user = _user_repo.get_by_mosys_employee_id(mosys_id)
    if not user or not user.is_active or not user.must_change_password:
        flash('Nieprawidłowe żądanie zmiany hasła.', 'error')
        return redirect(url_for('auth.login'))

    if len(new_pw) < 8:
        flash('Hasło musi mieć co najmniej 8 znaków.', 'error')
        return redirect(url_for('auth.login'))

    if new_pw != confirm:
        flash('Hasła nie są identyczne.', 'error')
        return redirect(url_for('auth.login'))

    _user_repo.update_password(user.id, new_pw)
    _user_repo.clear_must_change_password(user.id)
    login_user(user)
    log_event('password_set_first', user_id=user.id, user_email=user.email,
              user_name=user.full_name, ip_address=request.remote_addr)
    flash('Hasło zostało ustawione. Witaj w systemie!', 'success')
    return redirect(url_for('main.index'))


@auth_bp.route('/set-first-password', methods=['GET', 'POST'])
@login_required
def set_first_password():
    if not current_user.must_change_password:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        new_pw = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        if len(new_pw) < 8:
            flash('Hasło musi mieć co najmniej 8 znaków', 'error')
        elif new_pw != confirm:
            flash('Hasła nie są identyczne', 'error')
        else:
            _user_repo.update_password(current_user.id, new_pw)
            _user_repo.clear_must_change_password(current_user.id)
            log_event('password_set_first', user_id=current_user.id, user_email=current_user.email,
                      user_name=current_user.full_name, ip_address=request.remote_addr)
            flash('Hasło zostało ustawione. Witaj w systemie!', 'success')
            return redirect(url_for('main.index'))

    return render_template('auth/set_first_password.html')


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_pw = request.form.get('old_password', '')
        new_pw = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')

        if new_pw != confirm:
            flash('Nowe hasła nie są identyczne', 'error')
        else:
            ok, error = _auth_service.change_password(current_user.id, old_pw, new_pw)
            if ok:
                log_event('password_changed', user_id=current_user.id, user_email=current_user.email,
                          user_name=current_user.full_name, ip_address=request.remote_addr)
                flash('Hasło zostało zmienione', 'success')
                return redirect(url_for('main.index'))
            flash(error, 'error')

    return render_template('auth/change_password.html')


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    reset_url = None
    if request.method == 'POST':
        mosys_id = request.form.get('mosys_employee_id', '').strip()
        user = _user_repo.get_by_mosys_employee_id(mosys_id)
        if user:
            with get_connection() as conn:
                conn.execute(
                    "UPDATE password_reset_tokens SET used = 1 WHERE user_id = ? AND used = 0",
                    (user.id,),
                )
                token = secrets.token_urlsafe(32)
                expires_at = datetime.now() + timedelta(hours=1)
                conn.execute(
                    "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (?, ?, ?)",
                    (user.id, token, expires_at),
                )
            reset_url = url_for('auth.reset_password', token=token, _external=True)
        # Always render the same neutral message to avoid email enumeration
        flash('Jeśli adres e-mail istnieje w systemie, link do resetowania hasła jest widoczny poniżej.', 'info')

    return render_template('auth/forgot_password.html', reset_url=reset_url)


@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token: str):
    with get_connection() as conn:
        token_row = conn.execute(
            """SELECT * FROM password_reset_tokens
               WHERE token = ? AND used = 0 AND expires_at > datetime('now', 'localtime')""",
            (token,),
        ).fetchone()

    if not token_row:
        flash('Link wygasł lub został już wykorzystany.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_password = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        if len(new_password) < 8:
            flash('Hasło musi mieć co najmniej 8 znaków', 'error')
        elif new_password != confirm:
            flash('Hasła nie są identyczne', 'error')
        else:
            _user_repo.update_password(token_row['user_id'], new_password)
            with get_connection() as conn:
                conn.execute(
                    "UPDATE password_reset_tokens SET used = 1 WHERE token = ?", (token,)
                )
            flash('Hasło zostało zmienione. Możesz się teraz zalogować.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)
