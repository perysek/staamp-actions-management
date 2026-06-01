# Implementation Plan — STAAMP Actions Management

## Context

The company needs an internal Flask web app to manage **tasks / projects / actions / goals**, each decomposable into **subtasks** with a responsible user, start/finish dates, status, and inter-subtask dependencies, plus a **Gantt-style timeline** view with a live "now" marker. The real-world artifact driving this is `management-review-actions-2026.xlsx` — an ISO/IATF *Management Review* action tracker (columns: `#, Topic-Area, Action, Responsible, Scheduled_at, Completed_at, COMMENTS, PDCA`).

The repo was seeded by copy-pasting the **DMC Validator** project (a barcode scanner app). That copy brought a *complete and high-quality* auth/RBAC layer (matching `FLASK-RBAC-GOLDEN-BOOK.md`) but **omitted its foundation**:

- ❌ The entire `database/` package is **missing** — there is no `database/db.py` and no `database/models.py`, yet *every* repository, service, and route imports from them (`from database.db import get_connection, log_event`, `from database.models import User`). **The app cannot start today.**
- ❌ `routes/main_routes.py` (the `main` blueprint) and `routes/audit/` are missing, but `base.html` and `routes/auth/routes.py` reference `main.index`, `main.history`, `main.help_page`, `main.operator_card`, and `audit.audit_list`.
- ❌ `app.py` never registers `main_bp` / `audit_bp` (left as a `TODO`).
- ⚠️ All RBAC vocabulary and UI are **DMC-specific** (`dmc_validation`, `manual_mode`, `tryb_korekty`; sidebar branded "DMC Validator", "Skaner DMC"). These must be re-scoped to the actions domain.
- ⚠️ `templates/components/` and `templates/macros/` exist but are **empty**; `base.html` currently inlines flash messages, sidebar, modal CSS (works without macros).

Intended outcome: a runnable, RBAC-secured actions-management app that follows `GUI-GOLDEN-BOOK.md` (refined-minimal, System A / 2px) and `FLASK-RBAC-GOLDEN-BOOK.md` (MOSYS-ID login, first-login, on-screen reset tokens — kept **exactly** as specified), pre-loaded with the 2026 actions.

## Decisions locked (from user)

1. **Data model**: generic typed `items` (task/project/action/goal) + `subtasks`. **No** PDCA / Topic-Area columns. (Topic-Area + comments preserved inside imported item `description` so no source data is lost.)
2. **Seed**: import the **actions only** from `management-review-actions-2026.xlsx`; responsibles assigned later via the UI.
3. **RBAC**: 4 roles (`superuser`, `manager`, `contributor`, `viewer`) + 2 **toggleable per-role flags** rendered in the role editor:
   - `actions_view_assigned_only` — user sees only main items where they're responsible for ≥1 subtask.
   - `subtasks_update_assigned_only` — user may update only subtasks where they are the responsible (status field only).
4. **Subtask status**: `not_started | in_progress | blocked | done | cancelled`. **Dependencies**: multiple predecessors combined by a per-subtask **AND/OR** combinator; each predecessor edge has a type `finish_to_start | start_to_start`.

---

## Start-here notes (read before writing any code)

This plan is the **sole source of truth** for a fresh, empty session. Do this first:

1. **Read the two golden books in the repo root** — they contain copy-ready code:
   - `FLASK-RBAC-GOLDEN-BOOK.md` → §1 (full SQL for `roles, role_permissions, users, employees, password_reset_tokens, audit_log`), §2 (`get_connection`, `log_event`), §3 (`User`/`Employee` dataclasses), §1 `_seed_roles_and_permissions()`. **Copy these verbatim** into `database/db.py` and `database/models.py`, then adapt only the module/role vocabulary (Phase 2).
   - `GUI-GOLDEN-BOOK.md` → §5 System A (2px), §6 buttons, §7 form fields, §9 layout, §11 tables, §12 modals, §13 notifications. All new UI follows it.
2. **The app does NOT run yet** — first action is Phase 1 (create `database/`), because every existing module imports `from database.db import ...`. Confirm with: `.venv\Scripts\python.exe -c "import app"` (should fail with `ModuleNotFoundError: database` *before* Phase 1, succeed after Phase 1+4).
3. **Reusable as-is** (do not rewrite — only swap vocabulary/branding text): `repositories/users|roles|employees/*`, `services/auth/auth_service.py`, `services/mosys_service.py`, `routes/auth|users|roles|employees/routes.py`, `config/auth_config.py` decorators, `config/settings.py`, `run_dev.py`, all `static/js/*` (`Modals`, `Notifications`, `SearchableSelect`, `escapeHtml`, `table-utils`), and the inline shell CSS in `base.html`.
4. **Environment**: Windows + PowerShell. **Always invoke Python via `.venv\Scripts\python.exe`** (not bare `python`). `.env` is optional for dev — `config/settings.py` has working defaults; `DATABASE_PATH` defaults to `data/database.db` and `get_connection()` auto-creates the `data/` dir. `pip install` via `.venv\Scripts\python.exe -m pip install -r requirements.txt`.
5. **CSS caveat (golden book §1/§23)**: `static/css/output.css` is a prebuilt Tailwind file and is **not rebuilt** here. Any *new* Tailwind utility class you put in a template may not exist in `output.css`. **Prefer inline `style="…"` with the design tokens** (already defined in `base.html` `:root`) or the existing component classes (`.refined-table`, `.btn-press`, `.badge-*`, `.page-title`, etc.). Do not assume arbitrary Tailwind classes resolve.
6. **Endpoint names are contractual** — `base.html` builds `url_for(...)`; use these exact blueprint + function names: `main.index`, `items.items_list`, `items.item_detail`, `items.create_item`, `items.edit_item`, `timeline.timeline_index`, `timeline.timeline_view`, `audit.audit_list`, plus existing `users.users_list`, `employees.employees_list`, `roles.roles_list`, `auth.login`, `auth.logout`.
7. **Date rule** (global): never `new Date('YYYY-MM-DD')` (parses UTC → off-by-one). In JS parse as local: `const [y,m,d]=s.split('-').map(Number); new Date(y, m-1, d);`. In Python store/compare as `'%Y-%m-%d'` strings.

---

## Architecture & file map

Reuse the intact layer as-is (only vocabulary/branding edits): `repositories/users|roles|employees`, `services/auth`, `services/mosys_service.py`, `routes/auth|users|roles|employees`, `config/auth_config.py` (decorators), `config/settings.py`, `run_dev.py`, the `static/js/*` library, and `base.html` shell CSS.

```
database/                         ← CREATE (entire package missing)
  __init__.py
  db.py                           get_connection(), initialize_database(), log_event(), _seed_roles_and_permissions()
  models.py                       User(UserMixin), Employee, + Item, Subtask dataclasses
repositories/
  items/__init__.py + item_repository.py          ← CREATE
  subtasks/__init__.py + subtask_repository.py     ← CREATE
services/
  items/__init__.py + item_service.py              ← CREATE (dependency gating + authz helpers)
routes/
  main_routes.py                  ← CREATE (main_bp: dashboard/index)
  items/__init__.py + routes.py   ← CREATE (items_bp, pages + JSON API)
  timeline/__init__.py + routes.py ← CREATE (timeline_bp, page + JSON API)
  audit/__init__.py + routes.py   ← CREATE (audit_bp, event log list)
templates/
  base.html                       ← MODIFY (rebrand + new sidebar nav/gates)
  components/form_fields.html     ← CREATE (golden-book form macros)
  items/list.html|detail.html|create.html|edit.html  ← CREATE
  timeline/view.html              ← CREATE
  audit/list.html                 ← CREATE
  auth/*.html, users/*, roles/*, employees/* ← MODIFY (text rebrand only)
config/auth_config.py             ← MODIFY (MODULE_PERMISSIONS, ROLE_HIERARCHY)
repositories/roles/role_repository.py ← MODIFY (ALL_MODULES, ALL_FLAGS, display names)
app.py                            ← MODIFY (register main/items/timeline/audit blueprints)
scripts/seed_users.py             ← MODIFY (4-role dev accounts)
scripts/import_actions_2026.py    ← CREATE (xlsx → items importer)
run_production.py                 ← CREATE (Waitress entry point for NSSM service)
requirements.txt                  ← MODIFY (add openpyxl)
```

> **Deployment is the `/windows-server-deploy:windows-server-deploy` skill** (Flask + Waitress + NSSM on Windows Server `10.52.10.101`, git-clone method, SQLite, port **8093**). Full parameters in **Phase 7** below — invoke that skill for exact commands when developing/deploying.

---

## Phase 1 — Restore the data foundation (makes the app boot)

**`database/db.py`** — implement exactly per FLASK-RBAC-GOLDEN-BOOK §1–2:
- `get_connection()` → `sqlite3.connect(DATABASE_PATH)`, `row_factory = sqlite3.Row`, `PRAGMA journal_mode=WAL`, ensures parent dir exists. (`DATABASE_PATH` already defined in `config/settings.py`.)
- `log_event(...)` module-level helper, wrapped in try/except (audit must never crash a request).
- `initialize_database()` → `CREATE TABLE IF NOT EXISTS` for the RBAC tables (`roles`, `role_permissions`, `users`, `employees`, `password_reset_tokens`, `audit_log` — copy verbatim from golden book §1) **plus the new domain tables below**, then safe `ALTER TABLE` migration list, then `_seed_roles_and_permissions()`.

New domain schema (append inside `initialize_database`):
```sql
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_type   TEXT NOT NULL DEFAULT 'action',   -- task|project|action|goal
    title       TEXT NOT NULL,
    description TEXT,
    status      TEXT NOT NULL DEFAULT 'open',      -- open|in_progress|on_hold|done|cancelled
    due_date    TEXT,                              -- 'YYYY-MM-DD'
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
    start_date          TEXT,                      -- 'YYYY-MM-DD'
    finish_date         TEXT,                      -- 'YYYY-MM-DD'
    status              TEXT NOT NULL DEFAULT 'not_started',
    dependency_logic    TEXT NOT NULL DEFAULT 'AND', -- AND|OR over predecessors
    sort_order          INTEGER DEFAULT 0,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_subtasks_item ON subtasks(item_id);
CREATE TABLE IF NOT EXISTS subtask_dependencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subtask_id            INTEGER NOT NULL REFERENCES subtasks(id) ON DELETE CASCADE,
    depends_on_subtask_id INTEGER NOT NULL REFERENCES subtasks(id) ON DELETE CASCADE,
    dependency_type       TEXT NOT NULL DEFAULT 'finish_to_start', -- finish_to_start|start_to_start
    UNIQUE (subtask_id, depends_on_subtask_id)
);
CREATE INDEX IF NOT EXISTS ix_subtask_deps ON subtask_dependencies(subtask_id);
```

**`database/models.py`** — copy `User(UserMixin)` and `Employee` dataclasses verbatim from golden book §3 (the repos depend on `row_to_user()` → `User(...)`). Add lightweight `Item` and `Subtask` dataclasses (optional convenience; repos may return `sqlite3.Row` dicts like the existing ones do — keep that pattern for consistency).

> Invariant: keep `must_change_password` column + the safe-migration try/except pattern; the existing `UserRepository` already selects `must_change_password`.

## Phase 2 — Re-scope RBAC vocabulary

**`repositories/roles/role_repository.py`**:
```python
ALL_MODULES = ['actions', 'timeline', 'admin', 'audit']
ALL_FLAGS   = ['actions_view_assigned_only', 'subtasks_update_assigned_only']
MODULE_DISPLAY_NAMES = {
    'actions':  'Działania',
    'timeline': 'Oś czasu',
    'admin':    'Administracja',
    'audit':    'Dziennik zdarzeń',
}
FLAG_DISPLAY_NAMES = {
    'actions_view_assigned_only':     'Widok: tylko pozycje z moim podzadaniem',
    'subtasks_update_assigned_only':  'Edycja: tylko moje podzadania (status)',
}
```
- `set_permissions` / `get_permissions` iterate over `ALL_MODULES + ALL_FLAGS` (flags live in the same `role_permissions` table — no new table).
- Add `role_has_flag(role_name, flag) -> bool` (used by item/subtask services).

**`config/auth_config.py`**: update `MODULE_PERMISSIONS` (static fallback) and `ROLE_HIERARCHY` to the 4 roles + 4 module keys. Decorators (`role_required`, `module_permission_required`, `get_user_module_permissions`) are unchanged in logic.

**`database/db.py` → `_seed_roles_and_permissions()`** seed:
| role | actions | timeline | admin | audit | view_assigned_only | update_assigned_only | protected |
|---|---|---|---|---|---|---|---|
| superuser | 1 | 1 | 1 | 1 | 0 | 0 | 1 |
| manager | 1 | 1 | 0 | 1 | 0 | 0 | 0 |
| contributor | 1 | 1 | 0 | 0 | 1 | 1 | 0 |
| viewer | 1 | 1 | 0 | 0 | 1 | 0 | 0 |

**Authorization rules** (enforced in routes/services):
- *View* items/timeline → `module_permission_required('actions' / 'timeline')`; if caller's role has `actions_view_assigned_only`, repository scopes the list to items where the user is responsible for ≥1 subtask (or in `item_responsibles`).
- *Create/edit/delete* items & subtasks → roles `superuser`, `manager` only.
- *Contributor exception*: if role has `subtasks_update_assigned_only`, the subtask-status endpoint accepts updates **only** to subtasks where `responsible_user_id == current_user.id`, and **only** the `status` field.
- *Viewer*: read-only (has neither write role nor the contributor flag).

## Phase 3 — Domain repositories & service

**`repositories/items/item_repository.py`** — mirror the style of `repositories/employees/employee_repository.py` (raw SQL, `with get_connection()`):
- `get_all()`, `get_for_user(user_id, assigned_only: bool)`, `get_by_id(id)`, `create(...)`, `update(...)`, `delete(id)`, `set_responsibles(item_id, [user_ids])`, `get_responsibles(item_id)`, `count_subtasks(item_id)`.
- `get_active_users()` helper (active users for responsible pickers): `SELECT u.id, u.full_name FROM users u WHERE u.is_active=1 ORDER BY full_name`.

**`repositories/subtasks/subtask_repository.py`**:
- CRUD; `get_for_item(item_id)`; `set_dependencies(subtask_id, [{depends_on, type}])`; `get_dependencies(subtask_id)`; `update_status(subtask_id, status)`; `get_responsible(subtask_id)`.

**`services/items/item_service.py`** — dependency gating (the AND/OR logic):
```
predecessor_satisfied(pred_status, dep_type):
    finish_to_start -> pred_status == 'done'
    start_to_start  -> pred_status in ('in_progress','blocked','done','cancelled')  # i.e. has started
can_start(subtask):
    deps = get_dependencies(subtask)
    if not deps: return True
    results = [predecessor_satisfied(pred.status, d.type) for d in deps]
    return all(results) if subtask.dependency_logic == 'AND' else any(results)
```
- On a status change to `in_progress`/`done`, if `can_start()` is False → reject (server) and the UI shows the subtask as blocked. Also a cheap **cycle guard** in `set_dependencies` (reject if the new edge would make `depends_on` reachable back to `subtask_id`).

## Phase 4 — Blueprints & wiring

**`routes/main_routes.py`** (`main_bp = Blueprint('main', __name__)`, no prefix): function **`index()`** on `GET /` → `main.index` = dashboard → render a small summary (counts by status) or redirect to `items.items_list`. This satisfies the many `url_for('main.index')` references in `base.html` and `routes/auth/routes.py`.

**`routes/items/routes.py`** (`items_bp = Blueprint('items', __name__, url_prefix='/items')`) — page routes (`@login_required` + `@module_permission_required('actions')`) with these exact function names: **`items_list`** (`GET /`), **`item_detail`** (`GET /<int:item_id>`), **`create_item`** (`GET /create`), **`edit_item`** (`GET /<int:item_id>/edit`). JSON API:
- `GET /items/api` (scoped by flag), `POST /items/api`, `PUT/DELETE /items/api/<id>`
- `PUT /items/api/<id>/responsibles`
- `GET /items/api/<id>/subtasks`, `POST .../subtasks`, `PUT/DELETE .../subtasks/<sid>`
- `PUT .../subtasks/<sid>/status` (contributor-exception aware)
- `PUT .../subtasks/<sid>/dependencies`
- Every mutation calls `log_event(...)` (new event types below) and returns `{success, ...}` JSON, matching the users/roles route style.

**`routes/timeline/routes.py`** (`timeline_bp = Blueprint('timeline', __name__, url_prefix='/timeline')`, `@module_permission_required('timeline')`): **`timeline_index`** (`GET /`, item picker / list of items linking to each gantt), **`timeline_view`** (`GET /<int:item_id>`, gantt page), **`api_timeline`** (`GET /api/<int:item_id>`) → `{item, subtasks:[{id,title,responsible_name,start_date,finish_date,status,deps}]}`.

**`routes/audit/routes.py`** (`audit_bp = Blueprint('audit', __name__, url_prefix='/system/audit')`, `@module_permission_required('audit')`): function **`audit_list`** (`GET /`) lists `audit_log` ordered by `occurred_at DESC` with `EVENT_LABELS`/`EVENT_CLASSES` maps (golden book §12/§14). New event types to add: `item_create|item_update|item_delete`, `subtask_create|subtask_update|subtask_delete|subtask_status`.

**Write-authz helper** (add to `config/auth_config.py`): `manage_actions_required = role_required('superuser', 'manager')` — decorate all item create/update/delete and subtask create/delete/edit endpoints with it. The subtask **status** endpoint is the exception: it uses `module_permission_required('actions')` and then, inside the handler, branches on `role_has_flag(current_user.role, 'subtasks_update_assigned_only')` to restrict non-managers to their own subtasks' status only.

**`app.py`**: import & `register_blueprint` for `main_bp, items_bp, timeline_bp, audit_bp` (in addition to the existing auth/users/roles/employees). Remove the `# TODO` blueprint comment. `app_name` is already `'Staamp Global Actions Management'`.

## Phase 5 — GUI (follows GUI-GOLDEN-BOOK, System A / 2px, Polish UI)

**`templates/base.html`** (MODIFY): replace logo block (`qr_code_scanner` / "DMC Validator" / "Sensor Cover Quality") with an actions identity (e.g. icon `checklist`, title "Zarządzanie działaniami", sub "STAAMP"). Rewrite sidebar nav:
- Section **Działania**: `items.items_list` (`assignment`), `timeline.timeline_index` (`timeline`) — gated by `user_permissions.actions` / `.timeline`.
- Section **System** (role `superuser`): users, employees, roles (already present).
- `audit.audit_list` gated by `user_permissions.audit`.
- **Remove** the DMC links (`main.history`, `main.help_page`, `main.operator_card`). Update footer text. Keep the `current_mosys_employee_id` footer + logout (still valid).

**`templates/components/form_fields.html`** (CREATE): minimal macros per golden book §7 — `text_input`, `textarea_input`, `date_input`, `select_input`, `form_section`, `form_actions` — with System A overrides (`border-radius:2px`, `font-weight:300`). Used by item/subtask forms.

**`templates/items/list.html`** (CREATE): refined full-height table (Pattern A), API-driven exactly like `templates/users/list.html` (fetch `/items/api`, render with `escHtml`, status badges via status colors, `SearchableSelect` on filters). Columns: Typ · Tytuł · Status · Termin · Odpowiedzialni · Podzadania · akcje. "Nowe działanie" CTA in `page_actions`.

**`templates/items/detail.html`** (CREATE): item header (type/title/status/due/responsibles) + **subtasks table** + "Dodaj podzadanie" + per-subtask edit. Subtask create/edit uses `Modals.show` (modals.js) with: title, responsible (`SearchableSelect` of **active** users), start/finish `date_input`, status `select`, and a **dependencies editor** — add predecessor rows (`SearchableSelect` over sibling subtasks + type select `finish_to_start|start_to_start`) and an overall **AND/OR** radio. A "Pokaż oś czasu" button links to `/timeline/<id>`. Deletes use `Modals.confirm`.

**`templates/items/create.html` & `items/edit.html`** (CREATE): card form (Pattern B) using the `components/form_fields.html` macros — `text_input('title')`, `select_input('item_type', [task,project,action,goal])`, `select_input('status', [open,in_progress,on_hold,done,cancelled])`, `date_input('due_date')`, `textarea_input('description')`. **Responsibles = multi-select**: render a checkbox list of **active users** (from `item_repo.get_active_users()`, passed by the route), pre-checked on edit; submit collects the checked `user_id`s and the form POSTs/PUTs JSON to `items.api_create` / `items.api_update` then `PUT .../responsibles`. (Per GUI §8, `SearchableSelect` is single-value, so use the checkbox-list pattern for the many-to-many responsibles, not `SearchableSelect`.) Cancel → `items.items_list`.

**`templates/timeline/view.html`** (CREATE) — requirement #2, vanilla JS + SVG/CSS (no chart lib, per golden book "Vanilla ES6"):
- Fetch `/timeline/api/<id>`. Compute date range `[min(start), max(finish)]`; choose `pxPerDay`; map date→x.
- One row per subtask: left sticky label = subtask title; horizontal **bar** from `start_date`→`finish_date`; bar fill by status color; **responsible name** tag rendered on/after the bar.
- **Vertical "now" line**: `x = dateToX(new Date())` using **local time**. ⚠️ Per the date-formatting rule, parse `YYYY-MM-DD` as local — `const [y,m,d]=s.split('-').map(Number); new Date(y, m-1, d);` — never `new Date(s)` (UTC shift). The now-line uses the live local clock and a top "Teraz HH:MM" label; refresh position every 60 s.
- Top axis with day/week ticks + date labels; horizontal scroll for long ranges; optional dependency connector lines between bars.

**`templates/audit/list.html`** (CREATE): refined table of events with `badge-ok/nok/na` classes (already defined in `base.html`).

**Rebrand text only** in `auth/*`, `users/*`, `roles/*`, `employees/*` (titles/labels mentioning DMC). `roles/create.html` & `roles/edit.html`: render module toggles from `all_modules` **and** a separate "Ograniczenia" section for `ALL_FLAGS` (pass `all_flags`, `flag_display_names` from the roles routes).

## Phase 6 — Seed & import

**`requirements.txt`**: add `openpyxl==3.1.5`.

**`scripts/import_actions_2026.py`** (CREATE, one-off): `initialize_database()`, ensure a seed `superuser` exists (for `created_by`), then `openpyxl.load_workbook('management-review-actions-2026.xlsx', data_only=True)`, sheet `Arkusz1`. **Row 1 = headers; iterate from row 2.** Columns: `A=#, B=Topic-Area, C=Action, D=Responsible, E=Scheduled_at, F=Completed_at, G=COMMENTS, H=PDCA`. Skip rows where `Action` (col C) is blank. For each data row create one item:
- `item_type='action'`, `title = Action` (trim to ~140 chars; full text kept in description), `description = "[Obszar: {Topic-Area}]\n\n{full Action}\n\nUwagi: {COMMENTS}"` (preserves dropped MR fields),
- `due_date = Scheduled_at` → **a `_to_date_str(cell)` helper**: if value is a `datetime`/`date` → `.strftime('%Y-%m-%d')`; if it's an `int`/`float` (Excel serial) → `(date(1899,12,30)+timedelta(days=int(v))).strftime('%Y-%m-%d')`; else `None`. (openpyxl with `data_only=True` usually returns `datetime` for date-formatted cells, but handle the serial fallback so the script never crashes.)
- `status` from PDCA: `A`→`done`, `C`/`D`→`in_progress`, `P`/blank→`open`; override to `done` if `Completed_at` is present,
- **no responsibles** (assigned later via UI), `created_by = superuser.id`. Idempotent: skip if an item with the same `title` already exists. Print `f"Imported {n} actions"` at the end.

**`scripts/seed_users.py`** (MODIFY): keep dev accounts but align to the 4 roles (`superuser`, `manager`, `contributor`, `viewer`) — email-login dev accounts (not MOSYS-linked), per golden book §16 note.

---

## Phase 7 — Production deployment (company Windows Server)

> **Source of truth: the `/windows-server-deploy:windows-server-deploy` skill.** Invoke it for the exact, current commands — the values below are this project's locked parameters. Stack: **Flask + Waitress + NSSM**, direct LAN port (no reverse proxy). Claude has **SSH access** to run deploy commands directly.

**Locked deployment parameters:**

| Value | This project |
|---|---|
| GitHub repo | `github.com/perysek/staamp-actions-management` |
| Service name (NSSM) | `staamp-actions` |
| Display name | `STAAMP Actions Management` |
| Port | **8093** (matches `.env.example`; next-free per skill's Port Registry) |
| App directory | `C:\Apps\staamp-actions` |
| Logs directory | `C:\Logs\staamp-actions` |
| Deploy method | **git clone** → updates via `git pull origin main` |
| Database | **SQLite** at `C:\Apps\staamp-actions\data\database.db` (NOT Postgres) |
| OCR / Playwright / Alembic / Tailwind-build | **None** — skip skill Steps 5, 7, and the Alembic path in 9 |
| Server | `10.52.10.101`, SSH `administrator@10.52.10.101`, key `/c/Users/piotrperesiak/.ssh/id_ed25519_server` |

**Why SQLite (not the skill's default Postgres):** the whole reusable RBAC layer + `FLASK-RBAC-GOLDEN-BOOK.md` are SQLite, and the sibling **DMC Validator** (SQLite) is already deployed on this same server (`dmc-validate`, port 8092). Keeping SQLite avoids rewriting every repository and is a proven path here. (A future Postgres migration would touch every `repositories/*` file — out of scope.)

**`run_production.py`** (CREATE — Waitress entry point, per skill Step 10; `run_dev.py` is dev-only):
```python
import os
from dotenv import load_dotenv
load_dotenv()
from waitress import serve
from app import create_app

PORT = int(os.environ.get("SERVER_PORT", 8093))
if __name__ == "__main__":
    app = create_app()
    print(f"Starting production server on port {PORT}")
    serve(app, host="0.0.0.0", port=PORT, threads=4,
          connection_limit=100, channel_timeout=180, url_scheme="http")
```
`requirements.txt` already pins `waitress==3.0.1` ✓ (skill requires waitress, not gunicorn).

**Deploy sequence** (first install — run via SSH per skill §"New App Deployment"):
1. `git clone https://github.com/perysek/staamp-actions-management.git C:\Apps\staamp-actions`
2. `python -m venv .venv` → `.venv\Scripts\python.exe -m pip install -r requirements.txt`
3. Create `C:\Apps\staamp-actions\data` and `C:\Logs\staamp-actions` (skill Step 6).
4. `copy .env.example .env`; set `SECRET_KEY` (`python -c "import secrets; print(secrets.token_hex(32))"`), `FLASK_ENV=production`, keep `DATABASE_PATH=data/database.db`, `SERVER_PORT=8093`. Ensure `DEBUG`/`USE_MOCK_DB` are not `true`.
5. Init DB + seed: `python -c "from database.db import initialize_database; initialize_database()"`, then `python scripts/seed_users.py` and `python scripts/import_actions_2026.py`.
6. Test `python run_production.py` (expect "Starting production server on port 8093"), then install the NSSM service (skill Step 11: AppDirectory, AutoStart, AppStdout/Stderr to `C:\Logs\staamp-actions`, AppExit Restart) and open the firewall for TCP 8093 (skill Step 12).
7. Verify: `Get-Service staamp-actions` Running; `http://10.52.10.101:8093/` responds; logs writing.

**CSS note:** there is no Node/Tailwind build pipeline in this repo (no `package.json`), and the app relies on inline styles + a committed `static/css/output.css`. Therefore **commit `static/css/output.css`** (do NOT gitignore it) so the server's clone has styles — skill Step 5 is skipped.

## Implementation order (dependency-correct)

1. `database/db.py` + `database/models.py` (unblocks imports; app boots).
2. `repositories/roles` vocabulary + `config/auth_config.py` + role seed.
3. `repositories/items`, `repositories/subtasks`, `services/items`.
4. `routes/main_routes.py`, `routes/items`, `routes/timeline`, `routes/audit`; register in `app.py`.
5. `base.html` rebrand + `components/form_fields.html`.
6. `items/*` templates → `timeline/view.html` → `audit/list.html`; rebrand auth/users/roles/employees text + role-editor flags.
7. `requirements.txt`, `scripts/seed_users.py`, `scripts/import_actions_2026.py`.
8. `run_production.py` + deploy via the `/windows-server-deploy` skill (Phase 7) — service `staamp-actions`, port 8093, git-clone to `C:\Apps\staamp-actions`.

## Verification

> Windows / PowerShell: invoke Python as `.venv\Scripts\python.exe`. Commands below assume CWD = project root.

1. **Boot**: `.venv\Scripts\python.exe -m pip install -r requirements.txt`; `.venv\Scripts\python.exe -c "from app import create_app; create_app()"` → no `ModuleNotFoundError: database`. DB file created at `data/database.db`; verify tables exist via `.venv\Scripts\python.exe -c "import sqlite3; print([r[0] for r in sqlite3.connect('data/database.db').execute(\"SELECT name FROM sqlite_master WHERE type='table'\")])"` (expect roles, role_permissions, users, employees, password_reset_tokens, audit_log, items, item_responsibles, subtasks, subtask_dependencies).
2. **Seed + import**: `.venv\Scripts\python.exe scripts/seed_users.py` then `.venv\Scripts\python.exe scripts/import_actions_2026.py` → prints count of imported actions; `items` row count matches xlsx data rows.
3. **Run**: `.venv\Scripts\python.exe run_dev.py` → `http://localhost:5001/auth/login` (dev accounts use email login per golden book §16).
4. **Auth/RBAC**: log in as dev `superuser`; confirm sidebar shows Działania/Oś czasu/System/Dziennik. Log in as `contributor` → only items where they own a subtask are listed; they can change status only on their own subtasks; cannot create items. `viewer` → read-only.
5. **MOSYS-ID flow** (golden book): create a user via `/system/users/create` (4-digit MOSYS id) → first login shows set-password form → password set → login works. Forgot/reset token flow works.
6. **Items/subtasks**: create an item, add responsibles (multi), add subtasks with start/finish/responsible; create a `finish_to_start` dependency and an `AND`/`OR` group across two predecessors; verify a subtask with an unmet dependency is rejected when set to `in_progress`.
7. **Timeline**: open `/timeline/<id>` → bars span correct dates, responsible names shown, and the **vertical now-line** sits at the correct local-time position (verify no off-by-one by setting a subtask spanning today). 
8. **Audit**: mutations appear in `/system/audit` with correct labels/badges.

## Assumptions (flagged for review)

- **4-role scheme chosen** (the role question was left unselected); roles are editable in-app afterward, and the two scoping flags are toggleable per role.
- UI language stays **Polish** (consistent with golden book + existing templates); imported action *content* remains English as in the source file.
- AND/OR dependency logic is a **single flat combinator per subtask** (covers "A done OR B done"); nested boolean expressions are out of scope.
- Topic-Area / PDCA / Comments from the xlsx are **preserved in `description`**, not as structured columns (per the "generic only" choice).
