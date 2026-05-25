import os
import tempfile
import threading
from datetime import datetime
from hashlib import sha256
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

bp = Blueprint("tppr-upload", __name__)

UPLOAD_JOBS = {}


def set_progress(upload_id, **updates):
    job = UPLOAD_JOBS.get(upload_id, {})
    job.update(updates)
    job["updated_at"] = datetime.now().isoformat()
    UPLOAD_JOBS[upload_id] = job


def detect_upload_kind(file, first_chunk):
    filename = (file.filename or "").lower()
    mimetype = file.mimetype or ""
    head = first_chunk.lstrip()

    if first_chunk.startswith(b"%PDF"):
        return "pdf"

    if head.startswith((b"{", b"[")):
        return "json"

    if mimetype == "application/pdf" or filename.endswith(".pdf"):
        return "pdf"

    if mimetype == "application/json" or filename.endswith(".json"):
        return "json"

    return None


def upload_file_to_seaweedfs(temp_path, filename, content_type, upload_id):
    filer_url = os.getenv("SEAWEEDFS_FILER_URL", "http://localhost:8888").rstrip("/")
    bucket = os.getenv("SEAWEEDFS_S3_BUCKET", "tppr")
    safe_name = secure_filename(filename) or "upload"
    date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
    storage_path = f"buckets/{bucket}/uploads/{date_prefix}/{upload_id}-{safe_name}"
    url = f"{filer_url}/{quote(storage_path)}"

    with open(temp_path, "rb") as handle:
        data = handle.read()

    req = Request(
        url,
        data=data,
        method="PUT",
        headers={
            "Content-Type": content_type or "application/octet-stream",
            "Content-Length": str(len(data)),
        },
    )

    with urlopen(req, timeout=60) as response:
        response.read()

    return {
        "storage_path": f"/{storage_path}",
        "seaweedfs_url": url,
    }


def process_pdf_job(upload_id, paper_id, temp_path, user_id):
    try:
        set_progress(
            upload_id,
            status="processing",
            stage="ocr",
            progress=40,
            message="Running OCR...",
        )

        # TODO:
        # upload temp path to mistral ocr
        # get the ocr result
        # store the raw json result
        # then parse into questions
        # then store questions into sql

        # essentially i would have

        set_progress(
            upload_id,
            status="processing",
            stage="parsing",
            progress=75,
            message="Parsing questions...",
        )

        # TODO: parse OCR JSON here.

        set_progress(
            upload_id,
            status="complete",
            stage="ready",
            progress=100,
            message="Paper processed successfully.",
            result_url=f"/api/papers/{paper_id}/questions",
        )

    except Exception as exc:
        set_progress(
            upload_id,
            status="failed",
            stage="failed",
            progress=100,
            message=str(exc),
        )

    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


@bp.route("/api/upload", methods=["POST"])
@jwt_required()
def upload():
    user_id = get_jwt_identity()

    file = request.files.get("file")

    if not file:
        return jsonify({"error": "no_file", "message": "No file uploaded."}), 400

    upload_id = str(uuid4())
    paper_id = str(uuid4())
    first_chunk = file.stream.read(1024 * 1024)
    kind = detect_upload_kind(file, first_chunk)

    if kind is None:
        return jsonify(
            {
                "error": "unsupported_file_type",
                "message": f"Unsupported file type: {file.mimetype}",
            }
        ), 400

    if kind == "pdf" and not first_chunk.startswith(b"%PDF"):
        return jsonify(
            {
                "error": "invalid_pdf",
                "message": "Uploaded file must be a valid PDF.",
            }
        ), 400

    set_progress(
        upload_id,
        paper_id=paper_id,
        user_id=user_id,
        status="uploading",
        stage="receiving",
        progress=0,
        message="Receiving upload...",
        filename=file.filename,
        kind=kind,
        content_type=file.mimetype,
        created_at=datetime.utcnow().isoformat(),
    )

    hasher = sha256()
    total_bytes = 0

    suffix = ".pdf" if kind == "pdf" else ".json"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = tmp.name

        chunk = first_chunk
        while chunk:
            if not chunk:
                break

            total_bytes += len(chunk)
            hasher.update(chunk)
            tmp.write(chunk)
            chunk = file.stream.read(1024 * 1024)  # 1 MB

    file_hash = hasher.hexdigest()

    set_progress(
        upload_id,
        status="processing",
        stage="stored_temp",
        progress=25,
        message="Upload received. Preparing processing...",
        sha256=file_hash,
        size_bytes=total_bytes,
    )

    try:
        storage = upload_file_to_seaweedfs(
            temp_path,
            file.filename or f"{upload_id}{suffix}",
            file.mimetype,
            upload_id,
        )
    except URLError as exc:
        error_detail = str(getattr(exc, "reason", exc))

        try:
            os.remove(temp_path)
        except OSError:
            pass

        set_progress(
            upload_id,
            status="failed",
            stage="storage_failed",
            progress=100,
            message="Could not upload to SeaweedFS.",
            error=error_detail,
        )

        return jsonify(
            {
                "error": "seaweedfs_unavailable",
                "message": "Could not upload to SeaweedFS.",
                "details": error_detail,
            }
        ), 503

    set_progress(
        upload_id,
        stage="stored_seaweedfs",
        progress=35,
        message="Upload stored in SeaweedFS.",
        **storage,
    )

    if kind == "pdf":
        thread = threading.Thread(
            target=process_pdf_job,
            args=(upload_id, paper_id, temp_path, user_id),
            daemon=True,
        )
        thread.start()

        return jsonify(
            {
                "upload_id": upload_id,
                "paper_id": paper_id,
                "status": "processing",
                "stage": "queued",
                "progress_url": f"/api/upload/{upload_id}/status",
                "result_url": f"/api/papers/{paper_id}/questions",
                **storage,
            }
        ), 202

    try:
        os.remove(temp_path)
    except OSError:
        pass

    set_progress(
        upload_id,
        status="complete",
        stage="stored",
        progress=100,
        message="Upload stored successfully.",
    )

    return jsonify(
        {
            "upload_id": upload_id,
            "paper_id": paper_id,
            "status": "complete",
            "sha256": file_hash,
            "size_bytes": total_bytes,
            **storage,
        }
    ), 201


@bp.route("/api/upload/<upload_id>/status", methods=["GET"])
@jwt_required()
def upload_status(upload_id):
    user_id = get_jwt_identity()

    job = UPLOAD_JOBS.get(upload_id)

    if not job:
        return jsonify({"error": "not_found", "message": "Upload job not found."}), 404

    if job.get("user_id") != user_id:
        return jsonify(
            {"error": "forbidden", "message": "You do not have access to this upload."}
        ), 403

    return jsonify(job), 200
