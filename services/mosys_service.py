"""
Queries the company Pervasive (ODBC) database for production order data.
Falls back to mock/empty data when USE_MOCK_DB=true or connection unavailable.
"""
from __future__ import annotations

from datetime import date, timedelta
from config.settings import PERVASIVE_DSN, USE_MOCK_DB


def _get_pervasive(query: str, params: tuple) -> list[dict]:
    if USE_MOCK_DB:
        raise RuntimeError("Mock mode — skipping Pervasive connection")
    import pyodbc
    conn = pyodbc.connect(
        f"DSN={PERVASIVE_DSN};ArrayFetchOn=1;ArrayBufferSize=8;TransportHint=TCP;DecimalSymbol=,;",
        readonly=True,
    )
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return [
            {col: (v.strip() if isinstance(v, str) else v) for col, v in zip(columns, row)}
            for row in rows
        ]
    finally:
        conn.close()


def get_all_employees() -> list[dict]:
    """
    Fetch operators from MOSYS. Only CODICE starting with '9' are production operators.
    Returns list of {mosys_id, last_name, first_name, full_name}.
    Raises on connection failure so callers can surface a real error message.
    """
    query = "SELECT CODICE, DENOMINAZIONE FROM STAAMPDB.OPERATORI WHERE CODICE LIKE ?"
    rows = _get_pervasive(query, ("9%",))

    result = []
    for row in rows:
        code = str(row.get("CODICE", "")).strip()
        denom = str(row.get("DENOMINAZIONE", "")).strip()
        if not code:
            continue
        # DENOMINAZIONE is stored as "COGNOME NOME" (surname first)
        parts = denom.split(" ", 1)
        last_name = parts[0].title() if parts else denom
        first_name = parts[1].title() if len(parts) > 1 else ""
        result.append({
            "mosys_id": code,
            "last_name": last_name,
            "first_name": first_name,
            "full_name": denom,
        })
    return result
