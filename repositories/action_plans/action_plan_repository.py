from typing import Any, Optional

from database.db import get_connection

# Application-level cap on the plan name (DB column is plain TEXT).
NAME_MAX_LEN = 200


class ActionPlanRepository:
    """CRUD for action_plans — the user-managed grouping each item belongs to.

    Deletion is usage-guarded (a plan linked to ≥1 item cannot be removed); the
    `is_active` flag retires a plan without deleting it (hidden from new-item
    dropdowns, still shown on existing items).
    """

    def get_all(self) -> list:
        """All plans + how many items reference each (for the admin list)."""
        query = """
            SELECT p.id, p.name, p.sort_order, p.is_active, p.created_at,
                   (SELECT COUNT(*) FROM items i WHERE i.action_plan_id = p.id) AS usage_count
            FROM action_plans p
            ORDER BY p.sort_order, p.name COLLATE NOCASE
        """
        with get_connection() as conn:
            return conn.execute(query).fetchall()

    def get_active(self) -> list:
        """Active plans only — used to populate the action create/edit dropdown."""
        with get_connection() as conn:
            return conn.execute(
                """SELECT id, name, sort_order, is_active
                   FROM action_plans WHERE is_active = 1
                   ORDER BY sort_order, name COLLATE NOCASE"""
            ).fetchall()

    def get_by_id(self, plan_id: int) -> Optional[Any]:
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM action_plans WHERE id = ?", (plan_id,)
            ).fetchone()

    def create(self, name: str, sort_order: int = 0, is_active: bool = True) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO action_plans (name, sort_order, is_active)
                   VALUES (?, ?, ?)""",
                (name.strip(), int(sort_order), int(bool(is_active))),
            )
            return cursor.lastrowid

    def update(self, plan_id: int, name: str, sort_order: int, is_active: bool) -> None:
        with get_connection() as conn:
            conn.execute(
                """UPDATE action_plans
                   SET name = ?, sort_order = ?, is_active = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (name.strip(), int(sort_order), int(bool(is_active)), plan_id),
            )

    def usage_count(self, plan_id: int) -> int:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM items WHERE action_plan_id = ?", (plan_id,)
            ).fetchone()
        return row['c'] if row else 0

    def delete(self, plan_id: int) -> bool:
        """Delete only when no item references the plan. Returns False if in use/missing."""
        if self.usage_count(plan_id) > 0:
            return False
        with get_connection() as conn:
            cursor = conn.execute("DELETE FROM action_plans WHERE id = ?", (plan_id,))
            return cursor.rowcount > 0

    def name_exists(self, name: str, exclude_id: Optional[int] = None) -> bool:
        """Case-insensitive name check (the UNIQUE index is COLLATE NOCASE)."""
        query = "SELECT 1 FROM action_plans WHERE name = ? COLLATE NOCASE"
        params: list = [name.strip()]
        if exclude_id is not None:
            query += " AND id != ?"
            params.append(exclude_id)
        with get_connection() as conn:
            return conn.execute(query, tuple(params)).fetchone() is not None
