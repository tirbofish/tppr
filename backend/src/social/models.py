from datetime import UTC, datetime

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class FriendshipDB(SQLModel, table=True):
    """A directed friend request between two users.

    ``requester_id`` sent the request to ``addressee_id``. ``status`` is one of
    ``"pending"``, ``"accepted"``, or ``"declined"``. An accepted row in either
    direction means the two users are friends.
    """

    __tablename__ = "friendships"
    __table_args__ = (
        UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),
    )

    id: int | None = Field(default=None, primary_key=True)
    requester_id: str = Field(foreign_key="users.user_id", index=True)
    addressee_id: str = Field(foreign_key="users.user_id", index=True)
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))