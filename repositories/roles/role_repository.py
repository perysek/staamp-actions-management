from typing import Any, Optional
from database.db import get_connection

ALL_MODULES = ['dmc_validation', 'history', 'admin', 'audit', 'manual_mode', 'tryb_korekty']

MODULE_DISPLAY_NAMES = {
    'dmc_validation': 'Skaner DMC',
    'history':        'Historia skanów',
    'admin':          'Administracja',
    'audit':          'Dziennik zdarzeń',
    'manual_mode':    'Tryb manualny',
    'tryb_korekty':   'Tryb korekty',
}


class RoleRepository:

    def get_all(self) -> list:
        query = """
            SELECT r.id, r.name, r.display_name, r.is_protected, r.created_at,
                   COUNT(rp.id) FILTER (WHERE rp.has_access = 1) AS access_count
            FROM roles r
            LEFT JOIN role_permissions rp ON rp.role_id = r.id
            GROUP BY r.id, r.name, r.display_name, r.is_protected, r.created_at
            ORDER BY r.id
        """
        with get_connection() as conn:
            return conn.execute(query).fetchall()

    def get_by_id(self, role_id: int) -> Optional[Any]:
        with get_connection() as conn:
            return conn.execute("SELECT * FROM roles WHERE id = ?", (role_id,)).fetchone()

    def get_by_name(self, name: str) -> Optional[Any]:
        with get_connection() as conn:
            return conn.execute("SELECT * FROM roles WHERE name = ?", (name,)).fetchone()

    def create(self, name: str, display_name: str) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO roles (name, display_name, is_protected) VALUES (?, ?, 0)",
                (name, display_name),
            )
            return cursor.lastrowid

    def update(self, role_id: int, display_name: str):
        with get_connection() as conn:
            conn.execute("UPDATE roles SET display_name = ? WHERE id = ?", (display_name, role_id))

    def delete(self, role_id: int) -> bool:
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM roles WHERE id = ? AND is_protected = 0", (role_id,)
            )
            return cursor.rowcount > 0

    def get_permissions(self, role_id: int) -> dict:
        """Returns {module: bool} for all known modules (missing ones default to False)."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT module_name, has_access FROM role_permissions WHERE role_id = ?",
                (role_id,),
            ).fetchall()
        db_perms = {row['module_name']: bool(row['has_access']) for row in rows}
        return {m: db_perms.get(m, False) for m in ALL_MODULES}

    def set_permissions(self, role_id: int, permissions: dict):
        """Upsert permissions for all known modules."""
        with get_connection() as conn:
            for module in ALL_MODULES:
                conn.execute(
                    """INSERT INTO role_permissions (role_id, module_name, has_access) VALUES (?, ?, ?)
                       ON CONFLICT (role_id, module_name) DO UPDATE SET has_access = excluded.has_access""",
                    (role_id, module, int(bool(permissions.get(module, False)))),
                )

    def role_has_module_access(self, role_name: str, module_name: str) -> bool:
        """Used by module_permission_required decorator."""
        query = """
            SELECT rp.has_access FROM role_permissions rp
            JOIN roles r ON r.id = rp.role_id
            WHERE r.name = ? AND rp.module_name = ?
        """
        with get_connection() as conn:
            row = conn.execute(query, (role_name, module_name)).fetchone()
        if row is None:
            from config.auth_config import MODULE_PERMISSIONS
            return role_name in MODULE_PERMISSIONS.get(module_name, [])
        return bool(row['has_access'])

    def get_user_module_permissions(self, role_name: str) -> dict:
        """Returns {module_name: bool} — used by context processor."""
        query = """
            SELECT rp.module_name, rp.has_access FROM role_permissions rp
            JOIN roles r ON r.id = rp.role_id WHERE r.name = ?
        """
        with get_connection() as conn:
            rows = conn.execute(query, (role_name,)).fetchall()
        db_perms = {row['module_name']: bool(row['has_access']) for row in rows}
        from config.auth_config import MODULE_PERMISSIONS
        return {
            m: db_perms[m] if m in db_perms else (role_name in MODULE_PERMISSIONS.get(m, []))
            for m in ALL_MODULES
        }
