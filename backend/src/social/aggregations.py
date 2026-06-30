"""Derived per-user statistics shared by the leaderboard and stats dashboard.

There are no score/streak/attempt tables; all metrics are aggregated from the
existing ``papers`` and ``questions`` tables, grouped by ``author_id``.

"Completed" papers are authored papers where every question carries a
non-empty answer (i.e. the author has finished writing the worked solutions).
"Answered" questions are individual questions with a non-empty answer.
"Timing" is the sum of each authored paper's nominal ``duration_minutes``.
"""

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, aliased

from questions.types import PaperDB, QuestionDB

ZERO_STATS = {
    "paper_count": 0,
    "public_paper_count": 0,
    "completed_paper_count": 0,
    "question_count": 0,
    "answered_question_count": 0,
    "total_marks": 0,
    "total_duration_minutes": 0,
    "remixes_received": 0,
}


def _entry(stats: dict[str, dict], user_id) -> dict:
    return stats.setdefault(str(user_id), dict(ZERO_STATS))


def compute_many(session: Session, user_ids: list[str]) -> dict[str, dict]:
    """Compute stats for a set of users in a handful of grouped queries.

    Returns ``{user_id: {paper_count, public_paper_count, completed_paper_count,
    question_count, answered_question_count, total_marks, total_duration_minutes,
    remixes_received}}``. Users with no activity get zero stats.
    """
    stats: dict[str, dict] = {uid: dict(ZERO_STATS) for uid in user_ids}
    if not user_ids:
        return stats

    # Papers authored (exclude taken-down papers). Capture per-paper metadata so
    # we can later decide which papers are "completed".
    paper_rows = session.execute(
        select(
            PaperDB.id,
            PaperDB.author_id,
            PaperDB.visibility,
            PaperDB.duration_minutes,
        )
        .where(PaperDB.author_id.in_(user_ids))
        .where(PaperDB.visibility != "removed")
    ).all()

    authored_paper_ids: list[str] = []
    paper_author: dict[str, str] = {}
    for pid, author_id, visibility, duration in paper_rows:
        entry = _entry(stats, author_id)
        entry["paper_count"] += 1
        if visibility == "public":
            entry["public_paper_count"] += 1
        if duration:
            entry["total_duration_minutes"] += int(duration)
        authored_paper_ids.append(pid)
        paper_author[pid] = str(author_id)

    # Questions authored + total marks across them, plus answered-question count.
    answered_expr = case(
        (
            and_(
                QuestionDB.answer.isnot(None),
                func.length(QuestionDB.answer) > 0,
            ),
            1,
        ),
        else_=0,
    )
    question_rows = session.execute(
        select(
            QuestionDB.author_id,
            func.count(QuestionDB.id),
            func.coalesce(func.sum(answered_expr), 0),
            func.coalesce(func.sum(QuestionDB.marks), 0),
        )
        .where(QuestionDB.author_id.in_(user_ids))
        .group_by(QuestionDB.author_id)
    ).all()
    for author_id, q_count, answered_count, marks in question_rows:
        entry = _entry(stats, author_id)
        entry["question_count"] = int(q_count) if q_count is not None else 0
        entry["answered_question_count"] = (
            int(answered_count) if answered_count is not None else 0
        )
        entry["total_marks"] = int(marks) if marks is not None else 0

    # Completed papers: authored papers whose every question has a non-empty
    # answer (and which have at least one question).
    if authored_paper_ids:
        per_paper_rows = session.execute(
            select(
                QuestionDB.paper_id,
                func.count(QuestionDB.id),
                func.coalesce(func.sum(answered_expr), 0),
            )
            .where(QuestionDB.paper_id.in_(authored_paper_ids))
            .group_by(QuestionDB.paper_id)
        ).all()
        for pid, total, answered in per_paper_rows:
            author_id = paper_author.get(pid)
            if not author_id:
                continue
            if total and int(total) > 0 and int(answered) == int(total):
                _entry(stats, author_id)["completed_paper_count"] += 1

    # Remixes received: papers whose `remixed` points at one of the user's papers.
    source = aliased(PaperDB)
    remix_rows = session.execute(
        select(source.author_id, func.count(PaperDB.id))
        .join(source, PaperDB.remixed == source.id)
        .where(source.author_id.in_(user_ids))
        .group_by(source.author_id)
    ).all()
    for author_id, remix_count in remix_rows:
        _entry(stats, author_id)["remixes_received"] = (
            int(remix_count) if remix_count is not None else 0
        )

    return stats


def compute_user_stats(session: Session, user_id: str) -> dict:
    """Stats for a single user."""
    return compute_many(session, [user_id]).get(user_id, dict(ZERO_STATS))