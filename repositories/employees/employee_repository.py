from typing import Any, Optional
from database.db import get_connection


class EmployeeRepository:

    def get_all(self) -> list:
        query = """
            SELECT e.id, e.first_name, e.last_name, e.employee_no, e.mosys_employee_id,
                   e.user_id, e.created_at,
                   u.full_name AS user_full_name, u.email AS user_email
            FROM employees e
            LEFT JOIN users u ON u.id = e.user_id
            ORDER BY e.last_name, e.first_name
        """
        with get_connection() as conn:
            return conn.execute(query).fetchall()

    def get_by_id(self, employee_id: int) -> Optional[Any]:
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM employees WHERE id = ?", (employee_id,)
            ).fetchone()

    def get_by_mosys_id(self, mosys_id: str) -> Optional[Any]:
        with get_connection() as conn:
            return conn.execute(
                "SELECT * FROM employees WHERE mosys_employee_id = ?", (mosys_id,)
            ).fetchone()

    def create(self, first_name: str, last_name: str,
               employee_no: Optional[str] = None,
               mosys_employee_id: Optional[str] = None) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO employees (first_name, last_name, employee_no, mosys_employee_id)
                   VALUES (?, ?, ?, ?)""",
                (first_name.strip(), last_name.strip(),
                 employee_no.strip() if employee_no else None,
                 mosys_employee_id.strip() if mosys_employee_id else None),
            )
            return cursor.lastrowid

    def update(self, employee_id: int, first_name: str, last_name: str,
               employee_no: Optional[str], mosys_employee_id: Optional[str]):
        with get_connection() as conn:
            conn.execute(
                """UPDATE employees
                   SET first_name = ?, last_name = ?, employee_no = ?, mosys_employee_id = ?
                   WHERE id = ?""",
                (first_name.strip(), last_name.strip(),
                 employee_no.strip() if employee_no else None,
                 mosys_employee_id.strip() if mosys_employee_id else None,
                 employee_id),
            )

    def delete(self, employee_id: int) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT user_id FROM employees WHERE id = ?", (employee_id,)
            ).fetchone()
            if not row:
                return False
            if row['user_id']:
                raise ValueError("Nie można usunąć pracownika powiązanego z kontem użytkownika")
            cursor = conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
            return cursor.rowcount > 0

    def sync_from_mosys(self, mosys_employees: list[dict]) -> dict:
        """
        Upsert employees by mosys_employee_id.
        Returns {'added': int, 'updated': int, 'skipped': int}.
        """
        added = updated = skipped = 0
        with get_connection() as conn:
            for emp in mosys_employees:
                mosys_id = emp['mosys_id']
                existing = conn.execute(
                    "SELECT id FROM employees WHERE mosys_employee_id = ?", (mosys_id,)
                ).fetchone()

                if existing:
                    # Update name fields only — don't overwrite manual edits to employee_no
                    conn.execute(
                        "UPDATE employees SET first_name = ?, last_name = ? WHERE mosys_employee_id = ?",
                        (emp['first_name'], emp['last_name'], mosys_id),
                    )
                    updated += 1
                else:
                    conn.execute(
                        """INSERT INTO employees (first_name, last_name, mosys_employee_id)
                           VALUES (?, ?, ?)""",
                        (emp['first_name'], emp['last_name'], mosys_id),
                    )
                    added += 1

        return {'added': added, 'updated': updated, 'skipped': skipped}
