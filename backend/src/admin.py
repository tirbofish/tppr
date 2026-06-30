from datetime import UTC, datetime

from flask import Blueprint, jsonify, request
from auth.supabase import (
    get_current_user_id,
    supabase_auth_required,
)

from questions.db import get_session
from questions.types import PaperDB, paper_db_to_meta_read
from sqlmodel import Field, SQLModel, col, select

from auth.db import AuthenticationDB

_active_admins: set[str] = set()

admin_bp = Blueprint("tppr-admin", __name__)
db = AuthenticationDB()


class UserRoleDB(SQLModel, table=True):
    __tablename__ = "user_roles"

    user_id: str = Field(foreign_key="users.user_id", primary_key=True)
    role: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PaperTakedownState(SQLModel, table=True):
    __tablename__ = "paper_takedown_states"

    paper_id: str = Field(primary_key=True, foreign_key="papers.id")
    previous_visibility: str


def _get_child_remixes(session, paper_id: str) -> list[PaperDB]:
    return list(
        session.exec(select(PaperDB).where(PaperDB.remixed == paper_id)).all()
    )


def init_admins():
    _active_admins.clear()
    print("  Admin roles loaded from public.user_roles.")


def has_admin_role(user_id: str | None) -> bool:
    if not user_id:
        return False
    with get_session() as session:
        role = session.get(UserRoleDB, (str(user_id), "admin"))
        return role is not None


def is_admin(user_id: str) -> bool:
    if user_id not in _active_admins:
        return False
    if not db.get_user_by_id(user_id, fields=["user_id"]):
        _active_admins.discard(user_id)
        return False
    return user_id in _active_admins


def teardown_admins():
    _active_admins.clear()


@admin_bp.route("/api/admin/verify", methods=["POST"])
@supabase_auth_required(sync_user=True)
def verify_admin():
    user_id = get_current_user_id()
    if not has_admin_role(user_id):
        return jsonify({"message": "Admin role required"}), 403

    _active_admins.add(user_id)
    return jsonify({
        "message": "Admin mode activated",
        "admin": True,
        "admin_available": True,
    }), 200


@admin_bp.route("/api/admin/status", methods=["GET"])
@supabase_auth_required()
def admin_status():
    user_id = get_current_user_id()
    return jsonify({
        "admin": is_admin(user_id),
        "admin_available": has_admin_role(user_id),
    }), 200


@admin_bp.route("/api/admin/takedowns", methods=["GET"])
@supabase_auth_required()
def list_takedowns():
    user_id = get_current_user_id()
    if not is_admin(user_id):
        return jsonify({"message": "Forbidden"}), 403

    q = request.args.get("q")
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)

    with get_session() as session:
        statement = select(PaperDB).where(PaperDB.visibility == "removed")

        if q and q.strip():
            like_query = q.strip()
            search_expr = (
                col(PaperDB.title).contains(like_query)
                | col(PaperDB.subject).contains(like_query)
                | col(PaperDB.school).contains(like_query)
                | col(PaperDB.source).contains(like_query)
                | col(PaperDB.id).contains(like_query)
                | col(PaperDB.author_id).contains(like_query)
            )
            if like_query.isdigit():
                search_expr = search_expr | (PaperDB.year == int(like_query))
            statement = statement.where(search_expr)

        papers = session.exec(statement).all()
        papers.sort(key=lambda paper: paper.updated_at, reverse=True)
        total = len(papers)
        start = (page - 1) * per_page
        paged = papers[start:start + per_page]

        return jsonify({
            "papers": [
                paper_db_to_meta_read(paper).model_dump(mode="json")
                for paper in paged
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        }), 200

@admin_bp.route("/api/admin/takedown/<string:paper_id>", methods=["POST"])
@supabase_auth_required()
def takedown_paper(paper_id):
    """Takes down a paper and all of the remixes (recursively)"""
    user_id = get_current_user_id()
    if not is_admin(user_id):
        return jsonify({"message": "Forbidden"}), 403

    with get_session() as session:
        paper = session.get(PaperDB, paper_id)
        if not paper:
            return jsonify({"message": "Paper not found"}), 404

        taken_down = []
        to_process = [paper_id]
        processed = set()

        while to_process:
            current_id = to_process.pop()
            if current_id in processed:
                continue
            processed.add(current_id)

            p = session.get(PaperDB, current_id)
            if not p or p.visibility == "removed":
                continue

            if not session.get(PaperTakedownState, current_id):
                session.add(
                    PaperTakedownState(
                        paper_id=current_id,
                        previous_visibility=p.visibility,
                    )
                )
            p.visibility = "removed"
            p.updated_at = datetime.now(UTC)
            session.add(p)
            taken_down.append(current_id)

            for remix in _get_child_remixes(session, current_id):
                to_process.append(remix.id)

        session.commit()
        return jsonify({
            "message": f"Taken down {len(taken_down)} paper(s)",
            "taken_down": taken_down,
        }), 200

@admin_bp.route("/api/admin/takedown/<string:paper_id>", methods=["DELETE"])
@supabase_auth_required()
def revert_takedown(paper_id):
    """Revert a takedown 
    
    This restores paper and all its remixes to private.
    """
    user_id = get_current_user_id()
    if not is_admin(user_id):
        return jsonify({"message": "Forbidden"}), 403

    with get_session() as session:
        paper = session.get(PaperDB, paper_id)
        if not paper:
            return jsonify({"message": "Paper not found"}), 404
        if paper.visibility != "removed":
            return jsonify({"message": "Paper is not taken down"}), 409

        restored = []
        to_process = [paper_id]
        processed = set()

        while to_process:
            current_id = to_process.pop()
            if current_id in processed:
                continue
            processed.add(current_id)

            p = session.get(PaperDB, current_id)
            if not p or p.visibility != "removed":
                continue

            state = session.get(PaperTakedownState, current_id)
            if current_id != paper_id and not state:
                continue

            p.visibility = (
                state.previous_visibility
                if state and state.previous_visibility != "removed"
                else "private"
            )
            p.updated_at = datetime.now(UTC)
            session.add(p)
            if state:
                session.delete(state)
            restored.append(current_id)

            for remix in _get_child_remixes(session, current_id):
                to_process.append(remix.id)

        session.commit()
        return jsonify({
            "message": f"Restored {len(restored)} paper(s) to private",
            "restored": restored,
        }), 200
