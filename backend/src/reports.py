from datetime import UTC, datetime
from typing import Literal

from flask import Blueprint, jsonify, request
from sqlmodel import Field, SQLModel, col, select

from admin import is_admin
from auth.supabase import get_current_user_id, supabase_auth_required
from questions.db import get_session
from questions.types import PaperDB, paper_db_to_meta_read

reports_bp = Blueprint("tppr-reports", __name__)

ReportReason = Literal[
    "false_information",
    "copyright",
    "inappropriate",
    "broken_content",
    "spam",
    "other",
]

REPORT_REASONS = {
    "false_information",
    "copyright",
    "inappropriate",
    "broken_content",
    "spam",
    "other",
}

REPORT_STATUSES = {"open", "reviewing", "resolved", "dismissed"}


class PaperReportDB(SQLModel, table=True):
    __tablename__ = "paper_reports"

    id: int | None = Field(default=None, primary_key=True)
    paper_id: str
    reporter_id: str
    reason: str
    details: str | None = None
    status: str = Field(default="open")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def _report_dict(report: PaperReportDB, paper: PaperDB | None = None) -> dict:
    data = {
        "id": report.id,
        "paper_id": report.paper_id,
        "reporter_id": report.reporter_id,
        "reason": report.reason,
        "details": report.details,
        "status": report.status,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
    }
    if paper:
        data["paper"] = paper_db_to_meta_read(paper).model_dump(mode="json")
    return data


@reports_bp.route("/api/papers/<string:paper_id>/reports", methods=["POST"])
@supabase_auth_required()
def report_paper(paper_id):
    user_id = str(get_current_user_id())
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip()
    details = (data.get("details") or "").strip()

    if reason not in REPORT_REASONS:
        return jsonify({"message": "Invalid report reason"}), 400
    if reason == "other" and len(details) < 10:
        return jsonify({"message": "Please include a short explanation"}), 400
    if len(details) > 2000:
        return jsonify({"message": "Report details are too long"}), 400

    with get_session() as session:
        paper = session.get(PaperDB, paper_id)
        if not paper or paper.visibility == "removed":
            return jsonify({"message": "Paper not found"}), 404

        report = PaperReportDB(
            paper_id=paper_id,
            reporter_id=user_id,
            reason=reason,
            details=details or None,
        )
        session.add(report)
        session.commit()
        session.refresh(report)
        return jsonify(_report_dict(report)), 201


@reports_bp.route("/api/admin/reports", methods=["GET"])
@supabase_auth_required()
def list_reports():
    user_id = str(get_current_user_id())
    if not is_admin(user_id):
        return jsonify({"message": "Forbidden"}), 403

    status = (request.args.get("status") or "open").strip()
    paper_id = (request.args.get("paper_id") or "").strip()
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(max(int(request.args.get("per_page", 20)), 1), 100)

    with get_session() as session:
        stmt = select(PaperReportDB, PaperDB).outerjoin(
            PaperDB,
            PaperDB.id == PaperReportDB.paper_id,
        )
        if status != "all":
            if status not in REPORT_STATUSES:
                return jsonify({"message": "Invalid report status"}), 400
            stmt = stmt.where(PaperReportDB.status == status)
        if paper_id:
            stmt = stmt.where(PaperReportDB.paper_id == paper_id)

        rows = session.exec(
            stmt.order_by(col(PaperReportDB.created_at).desc())
        ).all()
        total = len(rows)
        start = (page - 1) * per_page
        paged = rows[start:start + per_page]

        return jsonify({
            "reports": [_report_dict(report, paper) for report, paper in paged],
            "total": total,
            "page": page,
            "per_page": per_page,
        }), 200


@reports_bp.route("/api/admin/reports/<int:report_id>", methods=["PATCH"])
@supabase_auth_required()
def update_report(report_id):
    user_id = str(get_current_user_id())
    if not is_admin(user_id):
        return jsonify({"message": "Forbidden"}), 403

    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip()
    if status not in REPORT_STATUSES:
        return jsonify({"message": "Invalid report status"}), 400

    with get_session() as session:
        report = session.get(PaperReportDB, report_id)
        if not report:
            return jsonify({"message": "Report not found"}), 404
        report.status = status
        report.updated_at = datetime.now(UTC)
        session.add(report)
        session.commit()
        session.refresh(report)
        return jsonify(_report_dict(report)), 200
