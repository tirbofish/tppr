"""Student progress tables.

These track what a student *does* with papers (study sessions in focus mode),
independent of authoring. ``paper_id``/``question_id`` are stored as plain
strings rather than foreign keys so a student's study history survives an
author deleting the source paper.
"""

from datetime import UTC, datetime

from sqlalchemy import Column, Index, Text
from sqlmodel import Field, Relationship, SQLModel


class PaperAttemptDB(SQLModel, table=True):
    """One focus-mode study session on a paper."""

    __tablename__ = "paper_attempts"
    __table_args__ = (
        Index("ix_paper_attempts_user_id", "user_id"),
        Index("ix_paper_attempts_paper_id", "paper_id"),
        Index("ix_paper_attempts_completed", "completed"),
        Index("ix_paper_attempts_started_at", "started_at"),
    )

    id: str = Field(primary_key=True)
    user_id: str
    paper_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_active_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    elapsed_seconds: int = Field(default=0)
    completed: bool = Field(default=False)
    questions_seen: int = Field(default=0)
    questions_answered: int = Field(default=0)
    reveal_count: int = Field(default=0)
    max_slide: int = Field(default=0)

    question_times: list["QuestionAttemptDB"] = Relationship(
        back_populates="attempt",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "lazy": "selectin",
        },
    )


class QuestionAttemptDB(SQLModel, table=True):
    """Time spent on a single question (or LAQ leaf) within an attempt."""

    __tablename__ = "question_attempts"
    __table_args__ = (
        Index("ix_question_attempts_attempt_id", "attempt_id"),
        Index("ix_question_attempts_question_id", "question_id"),
    )

    id: int | None = Field(default=None, primary_key=True)
    attempt_id: str = Field(foreign_key="paper_attempts.id")
    question_id: str
    part_path: str | None = Field(default=None, sa_column=Column(Text))
    seconds: int = Field(default=0)
    revealed_answer: bool = Field(default=False)
    reveal_count: int = Field(default=0)
    views: int = Field(default=0)

    attempt: PaperAttemptDB | None = Relationship(back_populates="question_times")