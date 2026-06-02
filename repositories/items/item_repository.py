from typing import Any, Optional
from database.db import get_connection

# Shared SELECT — items enriched with subtask count + comma-joined responsible names.
_LIST_SELECT = """
    SELECT i.id, i.item_type, i.title, i.description, i.status, i.due_date,
           i.created_by, i.created_at, i.updated_at,
           (SELECT COUNT(*) FROM subtasks s WHERE s.item_id = i.id) AS subtask_count,
           (SELECT MIN(s.start_date) FROM subtasks s
             WHERE s.item_id = i.id AND s.start_date IS NOT NULL AND s.start_date != '')
             AS earliest_start,
           (SELECT GROUP_CONCAT(u.full_name, ', ')
              FROM item_responsibles ir JOIN users u ON u.id = ir.user_id
             WHERE ir.item_id = i.id) AS responsibles
    FROM items i
"""

_LIST_ORDER = " ORDER BY (i.due_date IS NULL), i.due_date, i.id DESC"


class ItemRepository:

    def get_all(self) -> list:
        with get_connection() as conn:
            return conn.execute(_LIST_SELECT + _LIST_ORDER).fetchall()

    def get_for_user(self, user_id: int, assigned_only: bool) -> list:
        """If assigned_only, scope to items where the user is responsible for ≥1 subtask
        or is listed in item_responsibles. Otherwise behaves like get_all()."""
        if not assigned_only:
            return self.get_all()
        query = _LIST_SELECT + """
            WHERE EXISTS (SELECT 1 FROM subtasks s
                           WHERE s.item_id = i.id AND s.responsible_user_id = ?)
               OR EXISTS (SELECT 1 FROM item_responsibles ir
                           WHERE ir.item_id = i.id AND ir.user_id = ?)
        """ + _LIST_ORDER
        with get_connection() as conn:
            return conn.execute(query, (user_id, user_id)).fetchall()

    def get_by_id(self, item_id: int) -> Optional[Any]:
        with get_connection() as conn:
            return conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()

    def create(self, item_type: str, title: str, description: Optional[str],
               status: str, due_date: Optional[str], created_by: Optional[int]) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO items (item_type, title, description, status, due_date, created_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (item_type, title.strip(), description, status, due_date or None, created_by),
            )
            return cursor.lastrowid

    def update(self, item_id: int, item_type: str, title: str, description: Optional[str],
               status: str, due_date: Optional[str]):
        with get_connection() as conn:
            conn.execute(
                """UPDATE items
                   SET item_type = ?, title = ?, description = ?, status = ?,
                       due_date = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (item_type, title.strip(), description, status, due_date or None, item_id),
            )

    def delete(self, item_id: int) -> bool:
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
            return cursor.rowcount > 0

    def set_responsibles(self, item_id: int, user_ids: list) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM item_responsibles WHERE item_id = ?", (item_id,))
            for uid in user_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO item_responsibles (item_id, user_id) VALUES (?, ?)",
                    (item_id, int(uid)),
                )

    def get_responsibles(self, item_id: int) -> list:
        query = """
            SELECT u.id, u.full_name
            FROM item_responsibles ir JOIN users u ON u.id = ir.user_id
            WHERE ir.item_id = ?
            ORDER BY u.full_name
        """
        with get_connection() as conn:
            return conn.execute(query, (item_id,)).fetchall()

    def count_subtasks(self, item_id: int) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM subtasks WHERE item_id = ?", (item_id,)
            ).fetchone()
        return row['c'] if row else 0

    def get_active_users(self) -> list:
        """Active users for responsible pickers."""
        with get_connection() as conn:
            return conn.execute(
                "SELECT id, full_name FROM users WHERE is_active = 1 ORDER BY full_name"
            ).fetchall()
