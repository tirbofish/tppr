from datetime import UTC, datetime, timedelta
from typing import Optional

from sqlalchemy import or_
from sqlmodel import Session, select

from auth.db import UserDB
from questions.db import engine
from questions.types import PaperDB

from .models import FriendshipDB, UserPresenceDB
from .time import as_utc

ONLINE_WINDOW = timedelta(seconds=90)


def _public_user_dict(user: UserDB, since: Optional[datetime] = None) -> dict:
    body = {
        "user_id": user.user_id,
        "username": user.username,
        "avatar_url": user.avatar_url,
    }
    if since is not None:
        body["since"] = since.isoformat() if since else None
    return body


def _presence_dict(
    presence: UserPresenceDB | None,
    paper: PaperDB | None,
    *,
    now: datetime,
) -> dict | None:
    if not presence:
        return None

    last_seen_at = as_utc(presence.last_seen_at)
    session_started_at = as_utc(presence.session_started_at)
    active_paper_started_at = as_utc(presence.active_paper_started_at)
    is_online = now - last_seen_at <= ONLINE_WINDOW if last_seen_at else False
    body = {
        "online": is_online,
        "session_started_at": session_started_at.isoformat()
        if session_started_at
        else None,
        "last_seen_at": last_seen_at.isoformat()
        if last_seen_at
        else None,
        "seconds_on_site": max(
            0,
            int((now - session_started_at).total_seconds()),
        )
        if is_online and session_started_at
        else 0,
        "active_paper": None,
        "active_seconds": 0,
    }
    if (
        is_online
        and paper
        and paper.visibility == "public"
        and active_paper_started_at
    ):
        body["active_paper"] = {
            "id": paper.id,
            "title": paper.title,
            "subject": paper.subject,
            "visibility": paper.visibility,
        }
        body["active_seconds"] = max(
            0,
            int((now - active_paper_started_at).total_seconds()),
        )
    return body


class SocialDB:
    """Persistence layer for friend requests and the social graph."""

    def _existing_pair(self, session: Session, a: str, b: str) -> Optional[FriendshipDB]:
        return session.exec(
            select(FriendshipDB).where(
                or_(
                    (FriendshipDB.requester_id == a)
                    & (FriendshipDB.addressee_id == b),
                    (FriendshipDB.requester_id == b)
                    & (FriendshipDB.addressee_id == a),
                )
            )
        ).first()

    def send_request(
        self, requester_id: str, addressee_id: str
    ) -> tuple[bool, str]:
        if requester_id == addressee_id:
            return False, "You cannot befriend yourself"

        with Session(engine) as session:
            addressee = session.get(UserDB, addressee_id)
            if not addressee:
                return False, "User not found"

            existing = self._existing_pair(session, requester_id, addressee_id)
            if existing:
                if existing.status == "accepted":
                    return False, "You are already friends"
                if existing.status == "pending":
                    return False, "A friend request is already pending"
                # previously declined — allow a fresh request
                session.delete(existing)
                session.commit()

            friendship = FriendshipDB(
                requester_id=requester_id,
                addressee_id=addressee_id,
                status="pending",
            )
            session.add(friendship)
            session.commit()
            return True, "Friend request sent"

    def _get_request(self, session: Session, friendship_id: int) -> Optional[FriendshipDB]:
        return session.get(FriendshipDB, friendship_id)

    def accept_request(self, friendship_id: int, current_user_id: str) -> tuple[bool, str]:
        with Session(engine) as session:
            friendship = self._get_request(session, friendship_id)
            if not friendship:
                return False, "Request not found"
            if friendship.addressee_id != current_user_id:
                return False, "Not authorized to accept this request"
            if friendship.status != "pending":
                return False, "Request is no longer pending"

            friendship.status = "accepted"
            friendship.updated_at = datetime.now(UTC)
            session.add(friendship)
            session.commit()
            return True, "You are now friends"

    def decline_request(self, friendship_id: int, current_user_id: str) -> tuple[bool, str]:
        with Session(engine) as session:
            friendship = self._get_request(session, friendship_id)
            if not friendship:
                return False, "Request not found"
            if friendship.addressee_id != current_user_id:
                return False, "Not authorized to decline this request"
            if friendship.status != "pending":
                return False, "Request is no longer pending"

            friendship.status = "declined"
            friendship.updated_at = datetime.now(UTC)
            session.add(friendship)
            session.commit()
            return True, "Request declined"

    def cancel_outgoing(self, friendship_id: int, current_user_id: str) -> tuple[bool, str]:
        """Cancel a request the current user sent."""
        with Session(engine) as session:
            friendship = self._get_request(session, friendship_id)
            if not friendship:
                return False, "Request not found"
            if friendship.requester_id != current_user_id:
                return False, "Not authorized to cancel this request"
            if friendship.status != "pending":
                return False, "Request is no longer pending"
            session.delete(friendship)
            session.commit()
            return True, "Request cancelled"

    def list_incoming(self, user_id: str) -> list[dict]:
        with Session(engine) as session:
            rows = session.exec(
                select(FriendshipDB)
                .where(FriendshipDB.addressee_id == user_id)
                .where(FriendshipDB.status == "pending")
            ).all()
            result = []
            for f in rows:
                requester = session.get(UserDB, f.requester_id)
                if not requester:
                    continue
                result.append(
                    {
                        "id": f.id,
                        **_public_user_dict(requester),
                        "created_at": f.created_at.isoformat() if f.created_at else None,
                    }
                )
            return result

    def list_outgoing(self, user_id: str) -> list[dict]:
        with Session(engine) as session:
            rows = session.exec(
                select(FriendshipDB)
                .where(FriendshipDB.requester_id == user_id)
                .where(FriendshipDB.status == "pending")
            ).all()
            result = []
            for f in rows:
                addressee = session.get(UserDB, f.addressee_id)
                if not addressee:
                    continue
                result.append(
                    {
                        "id": f.id,
                        **_public_user_dict(addressee),
                        "created_at": f.created_at.isoformat() if f.created_at else None,
                    }
                )
            return result

    def list_friends(self, user_id: str) -> list[dict]:
        with Session(engine) as session:
            now = datetime.now(UTC)
            rows = session.exec(
                select(FriendshipDB)
                .where(FriendshipDB.status == "accepted")
                .where(
                    or_(
                        FriendshipDB.requester_id == user_id,
                        FriendshipDB.addressee_id == user_id,
                    )
                )
            ).all()
            result = []
            for f in rows:
                other_id = (
                    f.addressee_id if f.requester_id == user_id else f.requester_id
                )
                other = session.get(UserDB, other_id)
                if not other:
                    continue
                body = _public_user_dict(other, since=f.updated_at)
                presence = session.get(UserPresenceDB, other_id)
                paper = (
                    session.get(PaperDB, presence.active_paper_id)
                    if presence and presence.active_paper_id
                    else None
                )
                body["presence"] = _presence_dict(presence, paper, now=now)
                result.append(body)
            return result

    def list_friend_user_ids(self, user_id: str) -> list[str]:
        with Session(engine) as session:
            rows = session.exec(
                select(FriendshipDB)
                .where(FriendshipDB.status == "accepted")
                .where(
                    or_(
                        FriendshipDB.requester_id == user_id,
                        FriendshipDB.addressee_id == user_id,
                    )
                )
            ).all()
            ids = []
            for f in rows:
                ids.append(
                    f.addressee_id if f.requester_id == user_id else f.requester_id
                )
            return ids

    def remove_friend(self, user_id: str, other_id: str) -> tuple[bool, str]:
        with Session(engine) as session:
            friendship = self._existing_pair(session, user_id, other_id)
            if not friendship or friendship.status != "accepted":
                return False, "Not friends"
            session.delete(friendship)
            session.commit()
            return True, "Friend removed"

    def are_friends(self, a: str, b: str) -> bool:
        with Session(engine) as session:
            friendship = self._existing_pair(session, a, b)
            return friendship is not None and friendship.status == "accepted"
