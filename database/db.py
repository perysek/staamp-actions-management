import sqlite3
from datetime import datetime
from pathlib import Path

from config.settings import DATABASE_PATH


# ── Connection ────────────────────────────────────────────────────────────────
def get_connection() -> sqlite3.Connection:
    """Always use sqlite3.Row — rows accessed as row['column'], not positional."""
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ── Audit log helper (module-level, never raises) ───────────────────────────────
def log_event(
    event_type: str,
    user_id: "int | None" = None,
    user_email: "str | None" = None,
    user_name: "str | None" = None,
    detail: "str | None" = None,
    entity_type: "str | None" = None,
    entity_id: "int | None" = None,
    ip_address: "str | None" = None,
) -> None:
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO audit_log
                   (occurred_at, user_id, user_email, user_name, event_type,
                    entity_type, entity_id, detail, ip_address)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (now, user_id, user_email, user_name, event_type,
                 entity_type, entity_id, detail, ip_address),
            )
    except Exception:
        pass  # audit failures must never break the main flow


# ── Schema ──────────────────────────────────────────────────────────────────────
_SCHEMA = """
-- ── Roles ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    is_protected INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── Module permissions (RBAC pivot; also holds per-role flags) ──────────
CREATE TABLE IF NOT EXISTS role_permissions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id     INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    module_name TEXT NOT NULL,
    has_access  INTEGER DEFAULT 1,
    UNIQUE (role_id, module_name)
);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role_id);

-- ── Users ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    email               TEXT UNIQUE NOT NULL,
    password_hash       TEXT NOT NULL,
    full_name           TEXT NOT NULL,
    role                TEXT NOT NULL DEFAULT 'viewer',
    is_active           INTEGER NOT NULL DEFAULT 1,
    last_login          TIMESTAMP,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);

-- ── Employees (links users ↔ MOSYS OPERATORI) ─────────────────────────
CREATE TABLE IF NOT EXISTS employees (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name        TEXT NOT NULL,
    last_name         TEXT NOT NULL,
    employee_no       TEXT,
    user_id           INTEGER UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    mosys_employee_id TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_employees_mosys_id
    ON employees(mosys_employee_id) WHERE mosys_employee_id IS NOT NULL;

-- ── Password reset tokens ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    used       INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_prt_token ON password_reset_tokens(token);

-- ── Audit log ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    user_email   TEXT,
    user_name    TEXT,
    event_type   TEXT NOT NULL,
    entity_type  TEXT,
    entity_id    INTEGER,
    detail       TEXT,
    ip_address   TEXT
);
CREATE INDEX IF NOT EXISTS ix_audit_occurred ON audit_log(occurred_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_user     ON audit_log(user_id);

-- ── Domain: items (task|project|action|goal) ───────────────────────────
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type   TEXT NOT NULL DEFAULT 'action',
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'open',
    due_date    TEXT,
    created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS item_responsibles (
    item_id INTEGER NOT NULL REFERENCES items(id)  ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
    PRIMARY KEY (item_id, user_id)
);

CREATE TABLE IF NOT EXISTS subtasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id             INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    description         TEXT,
    responsible_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    start_date          TEXT,
    finish_date         TEXT,
    status              TEXT NOT NULL DEFAULT 'not_started',
    sort_order          INTEGER DEFAULT 0,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_subtasks_item ON subtasks(item_id);
"""


def initialize_database() -> None:
    with get_connection() as conn:
        conn.executescript(_SCHEMA)

        # Safe migrations — each in its own try/except (column-already-exists = no-op)
        migrations = [
            "ALTER TABLE users ADD COLUMN must_change_password INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE subtasks ADD COLUMN color TEXT",
            # Dependency feature removed — drop its table/column where present (best-effort).
            "DROP TABLE IF EXISTS subtask_dependencies",
            "ALTER TABLE subtasks DROP COLUMN dependency_logic",
        ]
        for sql in migrations:
            try:
                conn.execute(sql)
            except Exception:
                pass

    _seed_roles_and_permissions()


def _seed_roles_and_permissions() -> None:
    """Idempotent seed of the 4-role scheme + 4 module keys + 2 per-role flags.

    Flags (actions_view_assigned_only, subtasks_update_assigned_only) live in the
    same role_permissions table — they are just additional module_name rows.
    """
    roles = [
        ('superuser',   'Administrator',      1),  # is_protected=1
        ('manager',     'Kierownik',          0),
        ('contributor', 'Wykonawca',          0),
        ('viewer',      'Obserwator',         0),
    ]
    # module/flag → has_access per role (matches ALL_MODULES + ALL_FLAGS in role_repository)
    role_perms = {
        'superuser':   {'actions': 1, 'timeline': 1, 'admin': 1, 'audit': 1,
                        'actions_view_assigned_only': 0, 'subtasks_update_assigned_only': 0},
        'manager':     {'actions': 1, 'timeline': 1, 'admin': 0, 'audit': 1,
                        'actions_view_assigned_only': 0, 'subtasks_update_assigned_only': 0},
        'contributor': {'actions': 1, 'timeline': 1, 'admin': 0, 'audit': 0,
                        'actions_view_assigned_only': 1, 'subtasks_update_assigned_only': 1},
        'viewer':      {'actions': 1, 'timeline': 1, 'admin': 0, 'audit': 0,
                        'actions_view_assigned_only': 1, 'subtasks_update_assigned_only': 0},
    }
    with get_connection() as conn:
        for name, display_name, is_protected in roles:
            conn.execute(
                "INSERT OR IGNORE INTO roles (name, display_name, is_protected) VALUES (?, ?, ?)",
                (name, display_name, is_protected),
            )
        for role_name, perms in role_perms.items():
            row = conn.execute("SELECT id FROM roles WHERE name = ?", (role_name,)).fetchone()
            if row:
                for module, has_access in perms.items():
                    conn.execute(
                        "INSERT OR IGNORE INTO role_permissions (role_id, module_name, has_access) VALUES (?, ?, ?)",
                        (row['id'], module, has_access),
                    )
