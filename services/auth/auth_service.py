from typing import Tuple, Optional
from database.models import User
from repositories.users.user_repository import UserRepository


class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    def authenticate(self, email: str, password: str) -> Tuple[bool, Optional[User], Optional[str]]:
        user = self.user_repo.get_by_email(email)
        if not user:
            return False, None, "Nieprawidłowy e-mail lub hasło"
        if not user.is_active:
            return False, None, "Konto jest nieaktywne. Skontaktuj się z administratorem."
        if not self.user_repo.verify_password(user, password):
            return False, None, "Nieprawidłowy e-mail lub hasło"
        self.user_repo.update_last_login(user.id)
        return True, user, None

    def authenticate_by_employee_id(self, mosys_employee_id: str, password: str) -> Tuple[bool, Optional[User], Optional[str]]:
        user = self.user_repo.get_by_mosys_employee_id(mosys_employee_id.strip())
        if not user:
            return False, None, "Nieprawidłowy nr pracownika lub hasło"
        if not user.is_active:
            return False, None, "Konto jest nieaktywne. Skontaktuj się z administratorem."
        if not self.user_repo.verify_password(user, password):
            return False, None, "Nieprawidłowy nr pracownika lub hasło"
        self.user_repo.update_last_login(user.id)
        return True, user, None

    def change_password(self, user_id: int, old_password: str, new_password: str) -> Tuple[bool, Optional[str]]:
        row = self.user_repo.get_by_id(user_id)
        if not row:
            return False, "Użytkownik nie istnieje"
        user = self.user_repo.row_to_user(row)
        if not self.user_repo.verify_password(user, old_password):
            return False, "Nieprawidłowe aktualne hasło"
        if len(new_password) < 8:
            return False, "Hasło musi mieć co najmniej 8 znaków"
        self.user_repo.update_password(user_id, new_password)
        return True, None
