import bcrypt
from datetime import datetime
from typing import Optional, Any
from database.db import get_connection
from database.models import User


class UserRepository:

    _columns = 'id, email, password_hash, full_name, role, is_active, must_change_password, last_login, created_at, updated_at'

    def _validate_role(self, role: str):
        with get_connection() as conn:
            row = conn.execute("SELECT 1 FROM roles WHERE name = ?", (role,)).fetchone()
            if not row:
                raise ValueError(f"Rola '{role}' nie istnieje")

    def row_to_user(self, row: Any) -> User:
        return User(
            id=row['id'],
            email=row['email'],
            password_hash=row['password_hash'],
            full_name=row['full_name'],
            role=row['role'],
            is_active=bool(row['is_active']),
            must_change_password=bool(row['must_change_password']),
            last_login=row['last_login'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
        )

    def create_user(self, email: str, password: str, full_name: str, role: str = 'operator',
                    must_change_password: bool = False) -> int:
        self._validate_role(role)
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO users (email, password_hash, full_name, role, must_change_password) VALUES (?, ?, ?, ?, ?)",
                (email.strip().lower(), password_hash, full_name.strip(), role, int(must_change_password)),
            )
            return cursor.lastrowid

    def clear_must_change_password(self, user_id: int):
        from datetime import datetime
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET must_change_password = 0, updated_at = ? WHERE id = ?",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id),
            )

    def get_by_id(self, user_id: int) -> Optional[Any]:
        with get_connection() as conn:
            return conn.execute(
                f"SELECT {self._columns} FROM users WHERE id = ?", (user_id,)
            ).fetchone()

    def get_by_email(self, email: str) -> Optional[User]:
        with get_connection() as conn:
            row = conn.execute(
                f"SELECT {self._columns} FROM users WHERE email = ?", (email.strip().lower(),)
            ).fetchone()
        return self.row_to_user(row) if row else None

    def get_all(self) -> list:
        with get_connection() as conn:
            return conn.execute(
                f"SELECT {self._columns} FROM users ORDER BY full_name"
            ).fetchall()

    def get_all_with_employee(self) -> list:
        query = """
            SELECT u.id, u.email, u.full_name, u.role, u.is_active,
                   u.last_login, u.created_at,
                   e.id AS employee_id,
                   e.mosys_employee_id AS employee_mosys_id,
                   e.first_name AS employee_first_name,
                   e.last_name AS employee_last_name
            FROM users u LEFT JOIN employees e ON e.user_id = u.id
            ORDER BY u.full_name
        """
        with get_connection() as conn:
            return conn.execute(query).fetchall()

    def get_by_mosys_employee_id(self, mosys_id: str) -> Optional[User]:
        cols = ', '.join(f'u.{c.strip()}' for c in self._columns.split(','))
        with get_connection() as conn:
            row = conn.execute(
                f"""SELECT {cols}
                   FROM users u
                   INNER JOIN employees e ON e.user_id = u.id
                   WHERE e.mosys_employee_id = ?""",
                (mosys_id,),
            ).fetchone()
        return self.row_to_user(row) if row else None

    def get_employee_for_user(self, user_id: int) -> Optional[Any]:
        with get_connection() as conn:
            return conn.execute(
                """SELECT id, first_name, last_name, employee_no, mosys_employee_id
                   FROM employees WHERE user_id = ?""",
                (user_id,),
            ).fetchone()

    def get_login_employees(self) -> list:
        """Employee IDs with linked active accounts — shown in the login dropdown."""
        with get_connection() as conn:
            return conn.execute(
                """SELECT e.mosys_employee_id, u.full_name
                   FROM employees e
                   INNER JOIN users u ON u.id = e.user_id
                   WHERE e.mosys_employee_id IS NOT NULL AND e.mosys_employee_id != ''
                     AND u.is_active = 1
                   ORDER BY e.mosys_employee_id""",
            ).fetchall()

    def verify_password(self, user: User, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8'))

    def update_last_login(self, user_id: int):
        from datetime import datetime
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id),
            )

    def update_password(self, user_id: int, new_password: str):
        from datetime import datetime
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        with get_connection() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?",
                (password_hash, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id),
            )

    def update_user(self, user_id: int, full_name: str, role: str, is_active: bool):
        from datetime import datetime
        self._validate_role(role)
        with get_connection() as conn:
            conn.execute(
                """UPDATE users SET full_name = ?, role = ?, is_active = ?,
                   updated_at = ? WHERE id = ?""",
                (full_name.strip(), role, int(is_active),
                 datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user_id),
            )

    def toggle_active(self, user_id: int) -> bool:
        with get_connection() as conn:
            row = conn.execute("SELECT is_active FROM users WHERE id = ?", (user_id,)).fetchone()
            if not row:
                raise ValueError('Użytkownik nie istnieje')
            new_state = 0 if row['is_active'] else 1
            conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (new_state, user_id))
            return bool(new_state)

    def get_available_employees(self) -> list:
        """Employees not yet linked to any user account."""
        with get_connection() as conn:
            return conn.execute(
                "SELECT id, first_name, last_name, employee_no, mosys_employee_id FROM employees WHERE user_id IS NULL ORDER BY last_name"
            ).fetchall()

    def link_employee(self, employee_id: int, user_id: int):
        with get_connection() as conn:
            conn.execute(
                "UPDATE employees SET user_id = ? WHERE id = ?", (user_id, employee_id)
            )

    def unlink_employee(self, user_id: int):
        with get_connection() as conn:
            conn.execute(
                "UPDATE employees SET user_id = NULL WHERE user_id = ?", (user_id,)
            )
