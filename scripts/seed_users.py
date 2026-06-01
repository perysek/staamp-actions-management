"""
Dev/staging seed script — creates default user accounts.
Run from project root: python scripts/seed_users.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import initialize_database
from repositories.users.user_repository import UserRepository

initialize_database()

TEST_USERS = [
    {'email': 'owner@dmc.local',    'password': 'Super123!', 'full_name': 'Właściciel',    'role': 'superuser'},
    {'email': 'operator@dmc.local', 'password': 'Oper123!',  'full_name': 'Operator Zmiany', 'role': 'operator'},
]

repo = UserRepository()
for u in TEST_USERS:
    if not repo.get_by_email(u['email']):
        repo.create_user(**u)
        print(f"Utworzono: {u['email']} (rola: {u['role']})")
    else:
        print(f"Istnieje:  {u['email']}")
