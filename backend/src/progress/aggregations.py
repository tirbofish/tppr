"""Student-centric aggregations derived from focus-mode attempts.

These power the dashboard and leaderboard: how many papers a student has
practised/completed, how long they've studied, how many answers they've
checked, and day streaks.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from questions.types import PaperDB

from .models import PaperAttemptDB

ZERO_STUDENT_STATS = {
    "attempts_count": 0,
    "papers_attempted": 0,
    "papers_completed": 0,
    "questions_answered": 0,
    "total_study_seconds": 0,
    "reveal_count": 0,
    "current_streak": 0,
    "longest_streak": 0,
    "last_active_at": None,
}


def _entry(stats: dict[str, dict], uid) -> dict:
    return stats.setdefault(str(uid), dict(ZERO_STUDENT_STATS))


def _streaks(days: set[date], today: date) -> tuple[int, int]:
    """Return (current_streak, longest_streak) for a set of active dates."""
    if not days:
        return 0, 0

    # Current streak: count back from today (or yesterday if today is quiet).
    cursor = today if today in days else today - timedelta(days=1)
    current = 0
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)

    # Longest streak: scan sorted dates for consecutive runs.
    longest = 0
    run = 0
    prev: date | None = None
    for d in sorted(days):
        if prev is not None and d == prev + timedelta(days=1):
            run += 1
        else:
            run = 1
        longest = max(longest, run)
        prev = d
    return current, longest


def compute_many_students(
    session: Session,
    user_ids: list[str],
    *,
    today: date | None = None,
) -> dict[str, dict]:
    """Compute student stats for a set of users."""
    stats: dict[str, dict] = {uid: dict(ZERO_STUDENT_STATS) for uid in user_ids}
    if not user_ids:
        return stats

    # Per-user rollups over all attempts.
    rollup = session.execute(
        select(
            PaperAttemptDB.user_id,
            func.count(PaperAttemptDB.id),
            func.coalesce(func.sum(PaperAttemptDB.elapsed_seconds), 0),
            func.coalesce(func.sum(PaperAttemptDB.questions_answered), 0),
            func.coalesce(func.sum(PaperAttemptDB.reveal_count), 0),
            func.max(PaperAttemptDB.last_active_at),
        )
        .where(PaperAttemptDB.user_id.in_(user_ids))
        .group_by(PaperAttemptDB.user_id)
    ).all()
    for uid, count, secs, answered, reveals, last_active in rollup:
        entry = _entry(stats, uid)
        entry["attempts_count"] = int(count)
        entry["total_study_seconds"] = int(secs)
        entry["questions_answered"] = int(answered)
        entry["reveal_count"] = int(reveals)
        entry["last_active_at"] = last_active.isoformat() if last_active else None

    # Distinct papers attempted.
    attempted = session.execute(
        select(
            PaperAttemptDB.user_id,
            func.count(func.distinct(PaperAttemptDB.paper_id)),
        )
        .where(PaperAttemptDB.user_id.in_(user_ids))
        .group_by(PaperAttemptDB.user_id)
    ).all()
    for uid, distinct_papers in attempted:
        _entry(stats, uid)["papers_attempted"] = int(distinct_papers)

    # Distinct papers completed (at least one completed attempt).
    completed = session.execute(
        select(
            PaperAttemptDB.user_id,
            func.count(func.distinct(PaperAttemptDB.paper_id)),
        )
        .join(PaperDB, PaperDB.id == PaperAttemptDB.paper_id)
        .where(PaperAttemptDB.user_id.in_(user_ids))
        .where(
            or_(
                PaperAttemptDB.completed.is_(True),
                PaperAttemptDB.max_slide >= PaperDB.question_count + 1,
            )
        )
        .group_by(PaperAttemptDB.user_id)
    ).all()
    for uid, distinct_papers in completed:
        _entry(stats, uid)["papers_completed"] = int(distinct_papers)

    # Streaks from distinct active days (UTC date of started_at).
    today = today or datetime.now(timezone.utc).date()
    day_rows = session.execute(
        select(
            PaperAttemptDB.user_id,
            func.date(PaperAttemptDB.started_at),
        )
        .where(PaperAttemptDB.user_id.in_(user_ids))
        .distinct()
    ).all()
    days_by_user: dict[str, set[date]] = {}
    for uid, d in day_rows:
        if d is None:
            continue
        if isinstance(d, str):
            d = date.fromisoformat(d)
        days_by_user.setdefault(str(uid), set()).add(d)
    for uid, days in days_by_user.items():
        current, longest = _streaks(days, today)
        e = _entry(stats, uid)
        e["current_streak"] = current
        e["longest_streak"] = longest

    return stats


def compute_student_stats(session: Session, user_id: str) -> dict:
    return compute_many_students(session, [user_id]).get(
        user_id, dict(ZERO_STUDENT_STATS)
    )
