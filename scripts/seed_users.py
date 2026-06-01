"""
Dev/staging seed script — creates the single default admin account.
Run from project root: .venv\\Scripts\\python.exe scripts/seed_users.py

NOTE: This app's login route authenticates by MOSYS employee-id, and per
FLASK-RBAC-GOLDEN-BOOK.md only CODICE/MOSYS ids starting with "9" are valid
operators. The dev account is therefore linked to an `employees` row carrying a
"9"-prefixed MOSYS id. Log in with that id + the password below.
Created with must_change_password=False for immediate dev login.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import initialize_database
from repositories.users.user_repository import UserRepository
from repositories.employees.employee_repository import EmployeeRepository

initialize_database()

# mosys id (must start with 9) | first | last | role | password
DEV_USERS = [
    {'mosys': '9012', 'first': 'Anna', 'last': 'Administrator', 'role': 'superuser', 'password': 'Super123!'},
]

user_repo = UserRepository()
emp_repo = EmployeeRepository()

for u in DEV_USERS:
    email = f"{u['mosys']}@staamp.local"
    full_name = f"{u['first']} {u['last']}"
    if user_repo.get_by_email(email):
        print(f"Istnieje:  {email} (rola: {u['role']})")
        continue

    # Ensure a linked employee carrying the MOSYS id exists (login is by MOSYS id).
    existing_emp = emp_repo.get_by_mosys_id(u['mosys'])
    emp_id = existing_emp['id'] if existing_emp else emp_repo.create(
        u['first'], u['last'], employee_no=None, mosys_employee_id=u['mosys'])

    user_id = user_repo.create_user(email, u['password'], full_name, u['role'],
                                    must_change_password=False)
    user_repo.link_employee(emp_id, user_id)
    print(f"Utworzono: MOSYS {u['mosys']} / {full_name} (rola: {u['role']}, hasło: {u['password']})")

print("\nLogowanie: użyj numeru MOSYS 9012 i hasła Super123!")
