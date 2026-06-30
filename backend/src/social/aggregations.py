"""Derived per-user statistics shared by the leaderboard and stats dashboard.

There are no score/streak/attempt tables; all metrics are aggregated from the
existing ``papers`` and ``questions`` tables, grouped by ``author_id``.
"""

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, aliased

from questions.types import PaperDB, QuestionDB

ZERO_STATS = {
    "paper_count": 0,
    "public_paper_count": 0,
    "question_count": 0,
    "total_marks": 0,
    "remixes_received": 0,
}


def compute_many(session: Session, user_ids: list[str]) -> dict[str, dict]:
    """Compute stats for a set of users in a handful of grouped queries.

    Returns ``{user_id: {paper_count, public_paper_count, question_count,
    total_marks, remixes_received}}``. Users with no activity get zero stats.
    """
    stats: dict[str, dict] = {uid: dict(ZERO_STATS) for uid in user_ids}
    if not user_ids:
        return stats

    # Papers authored (exclude taken-down papers).
    paper_rows = session.execute(
        select(
            PaperDB.author_id,
            func.count(PaperDB.id),
            func.coalesce(func.sum(case((PaperDB.visibility == "public", 1), else_=0)), 0),
        )
        .where(PaperDB.author_id.in_(user_ids))
        .where(PaperDB.visibility != "removed")
        .group_by(PaperDB.author_id)
    ).all()
    for author_id, total, public_total in paper_rows:
        entry = stats.setdefault(str(author_id), dict(ZERO_STATS))
        entry["paper_count"] = int(total) if total is not None else 0
        entry["public_paper_count"] = int(public_total) if public_total is not None else 0

    # Questions authored + total marks across them.
    question_rows = session.execute(
        select(
            QuestionDB.author_id,
            func.count(QuestionDB.id),
            func.coalesce(func.sum(QuestionDB.marks), 0),
        )
        .where(QuestionDB.author_id.in_(user_ids))
        .group_by(QuestionDB.author_id)
    ).all()
    for author_id, q_count, marks in question_rows:
        entry = stats.setdefault(str(author_id), dict(ZERO_STATS))
        entry["question_count"] = int(q_count) if q_count is not None else 0
        entry["total_marks"] = int(marks) if marks is not None else 0

    # Remixes received: papers whose `remixed` points at one of the user's papers.
    source = aliased(PaperDB)
    remix_rows = session.execute(
        select(source.author_id, func.count(PaperDB.id))
        .join(source, PaperDB.remixed == source.id)
        .where(source.author_id.in_(user_ids))
        .group_by(source.author_id)
    ).all()
    for author_id, remix_count in remix_rows:
        entry = stats.setdefault(str(author_id), dict(ZERO_STATS))
        entry["remixes_received"] = int(remix_count) if remix_count is not None else 0

    return stats


def compute_user_stats(session: Session, user_id: str) -> dict:
    """Stats for a single user."""
    return compute_many(session, [user_id]).get(user_id, dict(ZERO_STATS))