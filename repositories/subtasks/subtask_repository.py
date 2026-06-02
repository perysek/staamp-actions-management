from typing import Any, Optional
from database.db import get_connection


class SubtaskRepository:

    def get_for_item(self, item_id: int) -> list:
        query = """
            SELECT s.*, u.full_name AS responsible_name
            FROM subtasks s
            LEFT JOIN users u ON u.id = s.responsible_user_id
            WHERE s.item_id = ?
            ORDER BY CASE WHEN s.start_date IS NULL OR s.start_date = '' THEN 1 ELSE 0 END,
                     s.start_date,
                     s.created_at,
                     s.id
        """
        with get_connection() as conn:
            return conn.execute(query, (item_id,)).fetchall()

    def get_by_id(self, subtask_id: int) -> Optional[Any]:
        with get_connection() as conn:
            return conn.execute("SELECT * FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()

    def create(self, item_id: int, title: str, description: Optional[str],
               responsible_user_id: Optional[int], start_date: Optional[str],
               finish_date: Optional[str], status: str = 'not_started',
               sort_order: int = 0) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO subtasks
                   (item_id, title, description, responsible_user_id, start_date,
                    finish_date, status, sort_order)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (item_id, title.strip(), description, responsible_user_id,
                 start_date or None, finish_date or None, status, sort_order),
            )
            return cursor.lastrowid

    def update(self, subtask_id: int, title: str, description: Optional[str],
               responsible_user_id: Optional[int], start_date: Optional[str],
               finish_date: Optional[str], status: str):
        with get_connection() as conn:
            conn.execute(
                """UPDATE subtasks
                   SET title = ?, description = ?, responsible_user_id = ?,
                       start_date = ?, finish_date = ?, status = ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (title.strip(), description, responsible_user_id, start_date or None,
                 finish_date or None, status, subtask_id),
            )

    def update_status(self, subtask_id: int, status: str):
        with get_connection() as conn:
            conn.execute(
                "UPDATE subtasks SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, subtask_id),
            )

    def update_color(self, subtask_id: int, color: "str | None"):
        with get_connection() as conn:
            conn.execute(
                "UPDATE subtasks SET color = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (color, subtask_id),
            )

    def delete(self, subtask_id: int) -> bool:
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM subtasks WHERE id = ?", (subtask_id,))
            return cursor.rowcount > 0

    def get_responsible(self, subtask_id: int) -> Optional[int]:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT responsible_user_id FROM subtasks WHERE id = ?", (subtask_id,)
            ).fetchone()
        return row['responsible_user_id'] if row else None
