from datetime import UTC, datetime

from app.models.user import User
from app.repositories.auth_repository import AuthRepository
from app.utils.ids import new_id
from app.utils.security import hash_password


class AuthService:
    def __init__(self, repository: AuthRepository) -> None:
        self.repository = repository

    def login(self, email: str, password: str) -> User:
        normalized_email = email.lower().strip()
        password_hash = hash_password(password)

        user = self.repository.get_user_by_email(normalized_email)
        if user is None:
            raise ValueError("User not found")

        if user.password_hash != password_hash:
            raise ValueError("Invalid credentials")

        return user
    
    def register(self, email: str, password: str) -> User:
        normalized_email = email.lower().strip()
        password_hash = hash_password(password)

        existing_user = self.repository.get_user_by_email(normalized_email)
        if existing_user is not None:
            raise ValueError("Email already in use")

        user = User(
            id=new_id(),
            email=normalized_email,
            password_hash=password_hash,
            created_at=datetime.now(UTC),
        )
        return self.repository.create_user(user)
