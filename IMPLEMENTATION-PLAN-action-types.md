# Implementation Plan — Action Plans (DB-backed grouping for action-items)

> **Status: AWAITING YOUR ACCEPTANCE.** No feature code will be written until you approve.
> Created 2026-06-03. Replaces the hardcoded "action type" vocabulary with a managed
> **Action Plans** table (PL: *Plany działań*) + admin CRUD, and wires it through the GUI.

---

## 1. Goal & concept

The four hardcoded "action types" — *task / project / action / goal* — never matched the
real use case. What's actually needed is a **grouping of action-items by initiative / area
of activity** — a top-level **Action Plan** that several main-items belong to. Examples:

- *Przegląd zarządzania 2026* — the items currently in the DB (defined during the 2026
  company management review).
- *Działania korygujące — audit IATF 2026* (corrective actions after the IATF
  certification audit).

So we replace the fixed type field with a **user-managed Action Plan** that a superuser can
list / create / edit / delete through new admin page-views (with create/edit forms). Each
action-item is linked to **exactly one** Action Plan. Plan names may be up to **200
characters**. Every GUI element that showed/selected the old "type" now shows/selects the
Action Plan.

**Standalone items via a general bucket.** Actions don't need their own dedicated initiative
— but rather than model "no plan" as a nullable orphan, the superuser keeps a general
catch-all plan (e.g. *Ogólne działania 2026*) and links lonely items to it. Every item still
belongs to a plan, so there are no NULL branches anywhere, yet standalone actions have a
natural home. (Flexibility for the user; fewer code paths for us.)

**Naming (chosen — your call to tweak):**

| | Polish | English |
|---|--------|---------|
| Entity (singular) | **Plan działań** | **Action Plan** |
| Entity (plural / page) | **Plany działań** | **Action Plans** |
| On the action form / list column | **Plan działań** | **Action Plan** |

## 2. Decisions confirmed

| # | Decision | Choice |
|---|----------|--------|
| D1 | **Bilingual handling** | **Single `name`** (≤200 chars). The 4 hardcoded PL→EN type entries are removed from `static/js/i18n.js`; plan names render as-authored in both languages (the admin page chrome stays fully bilingual). |
| D2 | **Data model / FK** | **Integer FK + migrate** *(confirmed)*: new `action_plans(id …)`, add `items.action_plan_id` FK, migrate the 14 existing rows. The `name` is free to rename anytime without disturbing linked items. |
| D3 | **Permissions** | **Superuser only** — "System" sidebar section beside Roles; `role_required('superuser')`. |
| D4 | **Lifecycle** | **Block delete if in use + active toggle.** A plan linked to ≥1 item → `409`. `is_active=0` retires a plan: hidden from new/edit dropdowns, still shown on existing items. |
| D5 | **Obsolete importer** | `scripts/import_actions_2026.py` **deleted** (one-off, already used; no runtime references). |
| D6 | **Plan required** *(confirmed)* | Every action-item belongs to **exactly one** plan (`action_plan_id` NOT NULL, app-enforced). Standalone items go into a general catch-all plan — no nullable/"unassigned" state. |
| D7 | **No description field; no tests** *(confirmed)* | Plan = `name` only (≤200). Verification stays manual (repo has no test framework). |

**Defaults taken:**
- **One-time seed (two plans):** **"Ogólne działania 2026"** (general catch-all bucket, starts empty) + **"Przegląd zarządzania 2026"** (the 14 existing items are linked to this one). Seed runs *exactly once* (see §5 insight); you'll rename either via the GUI.
- `sort_order` column controls dropdown/list ordering; names are **unique, case-insensitive**.
- Page at `/system/action-plans`, sidebar icon `account_tree`.
- Legacy `items.item_type` TEXT column is **kept but unused** after migration (dropping deferred — §11).

## 3. Scope

**In:** new `action_plans` table + one-time migration/backfill; new repository, blueprint
(pages + JSON API), 3 templates (mirroring **Roles**); rewire the 5 hardcoded type sites to
read the plan from the DB; GUI updates (actions list, detail, action create/edit, timeline
picker, sidebar nav, audit labels, i18n).

**Out:** per-plan colour/icon, plan-scoped permissions/reporting; translating custom plan
names (declined — D1); editing the `status`/subtask-status vocabularies (only the type field
was in scope); automated tests (repo has none — see §10; optional Phase 6).

---

## 4. Current state — every place the old type vocabulary lives

| # | File:line | Form | Action |
|---|-----------|------|--------|
| 1 | `routes/items/routes.py:21-22,30` | `ITEM_TYPE_OPTIONS` + derived `ITEM_TYPES` | **Remove**; replace with Action-Plan lookups |
| 2 | `static/js/i18n.js:80-84` | DICT: `'Zadanie':'Task'` … `'Cel':'Goal'` | **Remove** those 4 entries (D1) |
| 3 | `templates/items/list.html:60,96` | `const TYPE_LABELS`; `TYPE_LABELS[it.item_type]` | **Remove**; render `it.plan_name` |
| 4 | `templates/timeline/index.html:8,35` | `{% set type_labels %}`; `.get(it.item_type)` | **Remove**; render `it.plan_name` |
| 5 | `templates/items/detail.html:11,18` | `{% set type_labels %}`; `.get(item['item_type'])` | **Remove**; render `item['plan_name']` |

Storage today: `items.item_type TEXT NOT NULL DEFAULT 'action'` (`database/db.py:123`). Live
DB: **14 items, all `item_type='action'`** → all map to the single seeded plan.

Reference CRUD to mirror: **Roles** — `routes/roles/routes.py`,
`repositories/roles/role_repository.py`, `templates/roles/{list,create,edit}.html`.

---

## 5. Target architecture

```
database/
  db.py                          + action_plans table in _SCHEMA
                                 + ALTER items ADD COLUMN action_plan_id  (migrations list)
                                 + _seed_action_plans()  (ONE-TIME: starter plan + link 14 rows)
repositories/
  action_plans/                  ← NEW package
    __init__.py
    action_plan_repository.py     get_all/get_active/get_by_id/create/update/delete/usage_count/name_exists
  items/item_repository.py        JOIN action_plans → expose plan_name + action_plan_id;
                                  create()/update() take action_plan_id
routes/
  action_plans/                  ← NEW package (mirrors routes/roles)
    __init__.py
    routes.py                    action_plans_bp  (pages + JSON API, superuser-gated)
  items/routes.py                drop ITEM_TYPE_OPTIONS; build options from DB; validate action_plan_id
  timeline/routes.py             include plan_name in the picker payload
  audit/routes.py                + action_plan_create/update/delete in EVENT_LABELS / EVENT_CLASSES
templates/
  action_plans/                  ← NEW: list.html, create.html, edit.html
  items/{list,detail,create,edit}.html   read plan from DB (no inline maps); labels "Plan działań"
  timeline/index.html            read plan_name (no inline map)
  base.html                      + sidebar link (System section, superuser, icon account_tree)
static/js/i18n.js                remove 4 type entries; add Action-Plans page + audit strings;
                                 retitle the items/timeline "Typ" column → "Plan działań"
app.py                           register action_plans_bp
```

### Schema (added to `database/db.py` `_SCHEMA`)
```sql
CREATE TABLE IF NOT EXISTS action_plans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,                 -- ≤200 chars (enforced app-side)
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_action_plans_name ON action_plans(name COLLATE NOCASE);
```

### Migration (added to the `migrations` list, ~`database/db.py:161`)
```python
"ALTER TABLE items ADD COLUMN action_plan_id INTEGER REFERENCES action_plans(id)",
```
> Nullable at DB level (SQLite `ADD COLUMN` can't add NOT NULL without a default on existing
> rows); **NOT NULL enforced in the app**. The existing try/except migration loop keeps
> re-runs idempotent.

### One-time seed + backfill (new `_seed_action_plans()`, called from `initialize_database()`)
```python
def _seed_action_plans() -> None:
    """ONE-TIME: seed two starter plans and link pre-existing items, then stay inert.
    Unlike roles (fixed reference data seeded with INSERT OR IGNORE), Action Plans are
    user data — seeding by name would re-create a duplicate after the user renames it.
    So the guard is table-emptiness, NOT name."""
    with get_connection() as conn:
        if conn.execute("SELECT COUNT(*) AS c FROM action_plans").fetchone()['c'] > 0:
            return                                   # already initialised / user-managed
        # General catch-all bucket for standalone items (starts empty).
        conn.execute("INSERT INTO action_plans (name, sort_order) VALUES (?, ?)",
                     ('Ogólne działania 2026', 1))
        # Management-review plan — receives the pre-existing items.
        cur = conn.execute("INSERT INTO action_plans (name, sort_order) VALUES (?, ?)",
                           ('Przegląd zarządzania 2026', 2))
        conn.execute("UPDATE items SET action_plan_id = ? WHERE action_plan_id IS NULL",
                     (cur.lastrowid,))
```

---

## 6. Phased task breakdown

Windows + PowerShell; always run Python via `.venv\Scripts\python.exe`. Ordered so the app
stays runnable after every phase.

### Phase 1 — Data layer
1. `database/db.py`: add `action_plans` to `_SCHEMA`; add the `ALTER … action_plan_id` migration; add `_seed_action_plans()` and call it from `initialize_database()`.
2. `repositories/action_plans/action_plan_repository.py` (NEW): `ActionPlanRepository` —
   `get_all()` (with `usage_count` subquery), `get_active()`, `get_by_id()`,
   `create(name, sort_order, is_active)`, `update(id, name, sort_order, is_active)`,
   `delete(id)` (only when `usage_count == 0`), `name_exists(name, exclude_id=None)`.
3. `repositories/items/item_repository.py`: `_LIST_SELECT` + `get_by_id()`
   `LEFT JOIN action_plans p ON p.id = i.action_plan_id`, select `p.name AS plan_name` and
   `i.action_plan_id`; `create()`/`update()` take `action_plan_id`.
- **Verify:** `.venv\Scripts\python.exe -c "from app import create_app; create_app(); print('OK')"`; DB check (§10) → **2 plans seeded**; all 14 items linked to *Przegląd zarządzania 2026* (non-null `action_plan_id`); *Ogólne działania 2026* empty.

### Phase 2 — Action Plans backend (blueprint + API)
4. `routes/action_plans/routes.py` (NEW), mirroring Roles:
   - Pages: `plans_list` (`GET /`), `create_plan` (`GET /create`), `edit_plan` (`GET /<id>/edit`).
   - API: `api_list` (`GET /api`), `api_create` (`POST /api`), `api_update` (`PUT /api/<id>`), `api_delete` (`DELETE /api/<id>`).
   - All `@login_required @role_required('superuser')`. url_prefix `/system/action-plans`.
   - Validation: `name` required, **trimmed length ≤ 200**, unique (case-insensitive) → `409`; delete blocked when in use → `409` with item count.
   - `log_event('action_plan_create'|'action_plan_update'|'action_plan_delete', …)`.
5. `app.py`: import + `register_blueprint(action_plans_bp)`.
- **Verify:** `import app` smoke; `GET /system/action-plans/api` as superuser → JSON lists 2 plans (*Przegląd zarządzania 2026* `usage_count=14`, *Ogólne działania 2026* `=0`).

### Phase 3 — Action Plans frontend (3 templates + nav)
6. `templates/action_plans/list.html` — table: **Nazwa**, **Pozycje** (usage count), **Status** (Aktywny/Nieaktywny), edit/delete buttons. In-use delete surfaces the 409 message via `Notifications.error`.
7. `templates/action_plans/create.html` & `edit.html` — fields: **Nazwa \*** (`maxlength="200"`), **Kolejność** (sort_order), **Aktywny** (toggle, reuse Roles' `.toggle` CSS). `fetch` JSON submit → redirect to list.
8. `templates/base.html`: sidebar link in the superuser **System** section, icon `account_tree`, label **"Plany działań"**, active when `request.blueprint == 'action_plans'`.
- **Verify (manual):** create / edit / deactivate a plan; delete the in-use seeded plan → blocked; delete an unused plan → succeeds.

### Phase 4 — Wire Action Plans into the actions GUI
9. `routes/items/routes.py`:
   - Remove `ITEM_TYPE_OPTIONS`/`ITEM_TYPES`.
   - `create_item`: `plan_options = [(p['id'], p['name']) for p in active_plans]`; default = first active id; pass a `has_plans` flag.
   - `edit_item`: options = active plans **+ the item's current plan even if inactive** (suffixed " (nieaktywny)"); `value = item['action_plan_id']`.
   - `api_create`/`api_update`: read `action_plan_id`; validate exists + active (update may keep the *current* inactive plan; rejects switching **to** an inactive one).
   - `api_list`: return `'plan_name': r['plan_name']` (drop `item_type`).
10. `templates/items/create.html` & `edit.html`: field `action_plan_id` via `select_input`, label **"Plan działań"**; JS payload `action_plan_id: parseInt(...)`; handle "no active plans" (disable submit + hint). Update the page subtitle prose to be plan-aware.
11. `templates/items/list.html`: drop `TYPE_LABELS`; header **"Plan działań"**; render `escHtml(it.plan_name)`; add `plan_name` to the client search filter.
12. `templates/items/detail.html`: drop `{% set type_labels %}`; badge → `item['plan_name']`.
13. `routes/timeline/routes.py` + `templates/timeline/index.html`: include `plan_name` in the picker payload; drop the inline map; header **"Plan działań"**; render `it.plan_name`.
- **Verify (manual):** create an action assigned to a plan; the list, detail badge, and timeline picker all show the plan name; renaming a plan in admin propagates everywhere on refresh.

### Phase 5 — i18n, audit labels
14. `static/js/i18n.js`: remove the 4 type entries (lines 80-84); add DICT entries for the Action-Plans pages (title/subtitle, "+ Nowy plan", "Edytuj plan", headers, confirm/error strings), the nav label `'Plany działań':'Action Plans'`, the new column header `'Plan działań':'Action Plan'`, the reworked form subtitles, and audit labels (`'Utworzenie planu działań':'Action plan created'`, etc.).
15. `routes/audit/routes.py`: add `action_plan_create/update/delete` to `EVENT_LABELS` (PL) and `EVENT_CLASSES` (`badge-ok`/`badge-na`/`badge-nok`).
- **Verify (manual):** PL/EN toggle translates the whole Action-Plans page; plan names render as-authored in both; audit log shows readable labels for plan events.

---

## 7. New page-views — GUI spec (follows `GUI-GOLDEN-BOOK.md` / Roles pattern)

**List (`/system/action-plans`)** — `refined-page` + `refined-table`:

| Nazwa | Pozycje | Status | (actions) |
|-------|---------|--------|-----------|
| Ogólne działania 2026 | 0 | ● Aktywny | ✎  🗑 |
| Przegląd zarządzania 2026 | 14 | ● Aktywny | ✎  🗑 (409 if clicked — in use) |

- Header: title **"Plany działań"**, subtitle e.g. **"Grupowanie działań według inicjatyw / obszarów"**, **"+ Nowy plan"** (gold `ff-btn-primary`).
- Inactive plans → grey `badge-na` "Nieaktywny".

**Create / Edit** — `ff-section` card (~620px, Roles layout):
- **Nazwa \*** — `text_input`, `maxlength="200"`, helper "maks. 200 znaków".
- **Kolejność** — number (sort_order), helper "kolejność na listach i w polach wyboru".
- **Aktywny** — toggle (default on).
- Buttons: **Utwórz plan** / **Zapisz zmiany** + **Anuluj**.

**Messages (PL — EN added to i18n):** "Nazwa jest wymagana" · "Nazwa może mieć maksymalnie
200 znaków" · "Plan działań o tej nazwie już istnieje" (409) · "Nie można usunąć planu
przypisanego do pozycji (N)" (409) · "Usunięto plan" / "Zapisano".

---

## 8. Edge cases handled

| Case | Behaviour |
|------|-----------|
| No active plans exist (rare — general bucket normally exists) | Safety net: create-action form disables submit + "Najpierw utwórz plan działań". |
| Editing an item whose plan was retired (`is_active=0`) | Current plan stays selectable (suffixed "(nieaktywny)") so saving doesn't silently re-assign it. |
| Switching an item **to** an inactive plan | Rejected (`400`). |
| Deleting a plan in use | `409`, never deleted (app pre-check **and** DB FK `RESTRICT`; `PRAGMA foreign_keys=ON` is set). |
| Deactivating a plan in use | Allowed (retire). Existing items still render its name (LEFT JOIN; row still exists). |
| Duplicate name (any case) | `409` via `UNIQUE … COLLATE NOCASE` + app pre-check. |
| Name > 200 chars | `400` (server) + `maxlength` (client). |
| Re-running migration after the seed plan is renamed | No duplicate — seed is guarded to run only when the table is empty (§5). |

---

## 9. Files created / modified

**Created (6):** `repositories/action_plans/__init__.py`,
`repositories/action_plans/action_plan_repository.py`, `routes/action_plans/__init__.py`,
`routes/action_plans/routes.py`, `templates/action_plans/{list,create,edit}.html`.

**Modified (10):** `database/db.py`, `repositories/items/item_repository.py`,
`routes/items/routes.py`, `routes/timeline/routes.py`, `routes/audit/routes.py`, `app.py`,
`static/js/i18n.js`, `templates/base.html`, `templates/items/{list,detail,create,edit}.html`,
`templates/timeline/index.html`.

**Deleted (1, done):** `scripts/import_actions_2026.py`.

---

## 10. Verification plan (no test framework in repo — matches project practice)

1. **Smoke / migration:** `.venv\Scripts\python.exe -c "from app import create_app; create_app(); print('OK')"`
2. **Data check:**
   ```python
   import sqlite3; c = sqlite3.connect('data/database.db'); c.row_factory = sqlite3.Row
   print('plans:', [(r['id'], r['name'], r['is_active']) for r in c.execute('SELECT * FROM action_plans ORDER BY sort_order')])
   print('null action_plan_id:', c.execute('SELECT COUNT(*) FROM items WHERE action_plan_id IS NULL').fetchone()[0])  # expect 0
   ```
3. **Manual UI** (superuser): CRUD a plan; delete blocked for the seeded plan (in use); create/edit an action assigned to a plan; verify list / detail / timeline show plan names; rename a plan → propagation; PL/EN toggle; audit log labels.
4. **Regression:** existing actions still open/edit/appear on the timeline; status vocabulary unchanged.

> Optional **Phase 6**: a minimal `pytest` (repository + migration), adding `pytest` to
> `requirements.txt`. Excluded by default (repo has no tests today).

---

## 11. Rollback & deferred

- **Rollback:** additive at the DB level (new table + nullable column). Reverting code
  restores the old vocabulary; the extra table/column are harmless if left. Copy
  `data/database.db` before first run as a safety net.
- **Deferred:** dropping the now-unused `items.item_type` TEXT column (SQLite `DROP COLUMN`
  3.35+) — a later best-effort migration once all paths run on `action_plan_id`.
- **Deploy (per memory):** prod runs as an NSSM service on port 8093 at `C:\Apps\staamp-actions`,
  updated by git-pull; the migration runs on service start (`create_app()` →
  `initialize_database()`). Recommend a DB copy before the pull.

---

## 12. Decisions locked (2026-06-03)

All open questions are resolved — see D1–D7 in §2. Summary:

1. **FK design** — integer FK + migrate (`items.action_plan_id`). ✅
2. **Required vs optional** — required; standalone items live in a general catch-all plan. ✅
3. **Starter seed** — two plans: *Ogólne działania 2026* (empty) + *Przegląd zarządzania 2026* (14 items), linked during migration. ✅
4. **Description field** — no; name only. ✅
5. **Tests** — none; manual verification. ✅
6. **Naming/icon/URL** — *Plany działań* / *Action Plans*, `/system/action-plans`, icon `account_tree`. ✅

→ **Final go/no-go:** reply **"approved"** and I'll execute Phases 1→5 in order. (Per your
instruction, no feature code is written until you give this explicit green light.)
