from datetime import UTC, datetime
from logging import Logger
import re
from typing import Optional

from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError
from sqlmodel import Field, Session, SQLModel, select

from questions.db import engine
from questions.types import AssetDB, PaperDB, QuestionDB


class UserDB(SQLModel, table=True):
    __tablename__ = "users"

    user_id: str = Field(primary_key=True)
    username: str = Field(unique=True, nullable=False)
    email: str = Field(unique=True, nullable=False)
    password_hash: str = Field(nullable=False)
    totp_secret: str | None = None
    totp_enabled: int = Field(default=0)
    avatar_url: str | None = None
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
        user_id: str,
        username: str,
        email: str,
        password_hash: str = "",
        totp_secret: Optional[str] = None,
        totp_enabled: bool = False,
    ) -> str:
        with Session(engine) as session:
            user = UserDB(
                user_id=user_id,
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

    def update_avatar_url(self, user_id, avatar_url: str | None) -> None:
        with Session(engine) as session:
            user = session.get(UserDB, user_id)
            if user:
                user.avatar_url = avatar_url
                session.commit()

    def get_user_by_username(self, username: str) -> Optional[dict]:
        with Session(engine) as session:
            user = session.exec(
                select(UserDB).where(UserDB.username == username)
            ).first()
            if not user:
                return None
            return {
                "user_id": user.user_id,
                "username": user.username,
                "email": user.email,
            }

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

    def sync_supabase_user(
        self,
        *,
        user_id: str,
        email: str,
        metadata: dict | None = None,
    ) -> dict:
        metadata = metadata or {}
        for attempt in range(2):
            try:
                return self._sync_supabase_user_once(
                    user_id=user_id,
                    email=email,
                    metadata=metadata,
                )
            except (IntegrityError, StaleDataError):
                if attempt == 1:
                    raise
        raise RuntimeError("Unable to sync Supabase user")

    def _sync_supabase_user_once(
        self,
        *,
        user_id: str,
        email: str,
        metadata: dict,
    ) -> dict:
        with Session(engine) as session:
            user = session.get(UserDB, user_id)
            user_by_email = session.exec(
                select(UserDB).where(UserDB.email == email)
            ).first()

            if user_by_email and user_by_email.user_id != user_id:
                if user:
                    self._reassign_owned_records(
                        session,
                        old_user_id=user_by_email.user_id,
                        new_user_id=user_id,
                    )
                    session.delete(user_by_email)
                    session.flush()
                else:
                    self._reassign_owned_records(
                        session,
                        old_user_id=user_by_email.user_id,
                        new_user_id=user_id,
                    )
                    user_by_email.user_id = user_id
                    user = user_by_email

            username = self._unique_username(
                session,
                self._preferred_username(email, metadata, user_id),
                user_id,
            )

            if user:
                user.email = email
                if not user.username:
                    user.username = username
                user.last_login = datetime.now(UTC)
            else:
                user = UserDB(
                    user_id=user_id,
                    username=username,
                    email=email,
                    password_hash="",
                    last_login=datetime.now(UTC),
                )
                session.add(user)

            session.commit()
            session.refresh(user)
            return user.model_dump()

    def _reassign_owned_records(
        self,
        session: Session,
        *,
        old_user_id: str,
        new_user_id: str,
    ) -> None:
        if old_user_id == new_user_id:
            return
        session.exec(
            update(PaperDB)
            .where(PaperDB.author_id == old_user_id)
            .values(author_id=new_user_id)
        )
        session.exec(
            update(QuestionDB)
            .where(QuestionDB.author_id == old_user_id)
            .values(author_id=new_user_id)
        )
        session.exec(
            update(AssetDB)
            .where(AssetDB.uploader_id == old_user_id)
            .values(uploader_id=new_user_id)
        )

    def _preferred_username(
        self,
        email: str,
        metadata: dict,
        user_id: str,
    ) -> str:
        raw = (
            metadata.get("username")
            or metadata.get("user_name")
            or metadata.get("preferred_username")
            or metadata.get("name")
            or email.split("@", 1)[0]
            or f"user-{user_id[:8]}"
        )
        username = re.sub(r"[^A-Za-z0-9_-]+", "-", str(raw)).strip("-_")
        return username[:32] or f"user-{user_id[:8]}"

    def _unique_username(
        self,
        session: Session,
        preferred: str,
        user_id: str,
    ) -> str:
        existing = session.exec(
            select(UserDB).where(UserDB.username == preferred)
        ).first()
        if not existing or existing.user_id == user_id:
            return preferred

        suffix = user_id.replace("-", "")[:8]
        base = preferred[: max(1, 32 - len(suffix) - 1)]
        return f"{base}-{suffix}"
