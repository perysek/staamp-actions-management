from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from flask_login import UserMixin


@dataclass
class User(UserMixin):
    email: str
    password_hash: str
    full_name: str
    role: str = 'viewer'
    is_active: bool = True
    must_change_password: bool = False
    id: Optional[int] = None
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = field(default_factory=datetime.now)

    def get_id(self):           # required by Flask-Login
        return str(self.id)

    @property
    def is_authenticated(self):  # always True — Flask-Login requirement
        return True

    @property
    def is_anonymous(self):     # always False
        return False

    def has_role(self, *roles):
        return self.role in roles


@dataclass
class Employee:
    first_name: str
    last_name: str
    employee_no: Optional[str] = None
    mosys_employee_id: Optional[str] = None
    user_id: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = field(default_factory=datetime.now)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


# ── Domain convenience dataclasses (repos may also return sqlite3.Row) ──────────
@dataclass
class Item:
    title: str
    item_type: str = 'action'
    description: Optional[str] = None
    status: str = 'open'
    due_date: Optional[str] = None          # 'YYYY-MM-DD'
    created_by: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class Subtask:
    item_id: int
    title: str
    description: Optional[str] = None
    responsible_user_id: Optional[int] = None
    start_date: Optional[str] = None        # 'YYYY-MM-DD'
    finish_date: Optional[str] = None       # 'YYYY-MM-DD'
    status: str = 'not_started'
    sort_order: int = 0
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
