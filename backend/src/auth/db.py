from datetime import UTC, datetime
from logging import Logger
from typing import Optional

from sqlalchemy import or_
from sqlmodel import Field, Session, SQLModel, select

from questions.db import engine


class UserDB(SQLModel, table=True):
    __tablename__ = "users"

    user_id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, nullable=False)
    email: str = Field(unique=True, nullable=False)
    password_hash: str = Field(nullable=False)
    totp_secret: str | None = None
    totp_enabled: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_login: datetime | None = None


class AuthenticationDB:
    def prepare(self, log: Logger):
        log.info("Preparing auth database tables")
        SQLModel.metadata.create_all(engine)
        log.info("Users table ready")

    def get_user_by_email(self, email: str) -> Optional[dict]:
        with Session(engine) as session:
            user = session.exec(
                select(UserDB).where(UserDB.email == email)
            ).first()
            return user.model_dump() if user else None

    def get_user_by_email_or_username(self, identifier: str) -> Optional[dict]:
        with Session(engine) as session:
            user = session.exec(
                select(UserDB).where(
                    or_(UserDB.email == identifier, UserDB.username == identifier)
                )
            ).first()
            if not user:
                return None
            return {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
                "password_hash": user.password_hash,
                "totp_secret": user.totp_secret,
                "totp_enabled": user.totp_enabled,
            }

    def user_exists(self, email: str, username: str) -> bool:
        with Session(engine) as session:
            user = session.exec(
                select(UserDB.user_id).where(
                    or_(UserDB.email == email, UserDB.username == username)
                )
            ).first()
            return user is not None

    def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        totp_secret: Optional[str] = None,
        totp_enabled: bool = False,
    ) -> int | None:
        with Session(engine) as session:
            user = UserDB(
                username=username,
                email=email,
                password_hash=password_hash,
                totp_secret=totp_secret,
                totp_enabled=1 if totp_enabled else 0,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user.user_id

    def get_user_by_id(
        self, user_id, fields: Optional[list[str]] = None
    ) -> Optional[dict]:
        with Session(engine) as session:
            user = session.get(UserDB, user_id)
            if not user:
                return None
            if fields:
                return {f: getattr(user, f) for f in fields}
            return user.model_dump()

    def is_username_taken(self, username: str, exclude_user_id=None) -> bool:
        with Session(engine) as session:
            stmt = select(UserDB.user_id).where(UserDB.username == username)
            if exclude_user_id is not None:
                stmt = stmt.where(UserDB.user_id != exclude_user_id)
            return session.exec(stmt).first() is not None

    def update_username(self, user_id, new_username: str) -> None:
        with Session(engine) as session:
            user = session.get(UserDB, user_id)
            if user:
                user.username = new_username
                session.commit()

    def update_password(self, user_id, password_hash: str) -> None:
        with Session(engine) as session:
            user = session.get(UserDB, user_id)
            if user:
                user.password_hash = password_hash
                session.commit()

    def delete_user(self, user_id) -> bool:
        with Session(engine) as session:
            user = session.get(UserDB, user_id)
            if not user:
                return False
            session.delete(user)
            session.commit()
            return True

    def update_last_login(self, user_id) -> None:
        with Session(engine) as session:
            user = session.get(UserDB, user_id)
            if user:
                user.last_login = datetime.now(UTC)
                session.commit()

    def enable_totp(self, user_id, totp_secret: str) -> None:
        with Session(engine) as session:
            user = session.get(UserDB, user_id)
            if user:
                user.totp_secret = totp_secret
                user.totp_enabled = 1
                session.commit()

    def disable_totp(self, user_id) -> None:
        with Session(engine) as session:
            user = session.get(UserDB, user_id)
            if user:
                user.totp_secret = None
                user.totp_enabled = 0
                session.commit()
