import os
import tempfile
import threading
from dataclasses import dataclass
from hashlib import sha256
from urllib.error import URLError
from urllib.parse import urlparse
from uuid import uuid4

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from imohash import hashfile
from jobs import UploadStatusJobQueueYaddaYaddaDo
from seaweed import SeaweedFS
from share import PDFShareService
from tppr_paper_utils.providers import OCRInput
from tppr_paper_utils.providers.mistral import MistralOCRProvider
from werkzeug.utils import secure_filename

bp = Blueprint("tppr-upload", __name__)

CHUNK_SIZE = 1024 * 1024
PDF_MIME_TYPE = "application/pdf"
JSON_MIME_TYPE = "application/json"

storage = SeaweedFS.from_env()
share_service = PDFShareService(seaweedfs=storage)
job_queue = UploadStatusJobQueueYaddaYaddaDo()


@dataclass(frozen=True)
class UploadedFile:
    temp_path: str
    file_hash: str
    imo_hash: str
    size_bytes: int
    kind: str
    filename: str
    content_type: str


@dataclass(frozen=True)
class StoredPDF:
    storage_path: str
    seaweedfs_url: str
    signed_share_url: str
    signed_share_expires_at: str
    sha256: str
    reused_existing_pdf: bool

    def as_dict(self):
        return {
            "storage_path": self.storage_path,
            "seaweedfs_url": self.seaweedfs_url,
            "signed_share_url": self.signed_share_url,
            "signed_share_expires_at": self.signed_share_expires_at,
            "sha256": self.sha256,
            "reused_existing_pdf": self.reused_existing_pdf,
        }


def is_public_https_url(value):
    parsed = urlparse(value)
    return parsed.scheme == "https" and parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }


def is_sha256_hash(value):
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdefABCDEF" for char in value)
    )


def file_imohash(
    file_path,
    sample_threshhold=131072,
    sample_size=16384,
    hexdigest=True,
):
    return hashfile(
        file_path,
        sample_threshhold=sample_threshhold,
        sample_size=sample_size,
        hexdigest=hexdigest,
    )


def detect_upload_kind(file, first_chunk):
    filename = (file.filename or "").lower()
    mimetype = file.mimetype or ""
    head = first_chunk.lstrip()

    if first_chunk.startswith(b"%PDF"):
        return "pdf"
    if head.startswith((b"{", b"[")):
        return "json"
    if mimetype == PDF_MIME_TYPE or filename.endswith(".pdf"):
        return "pdf"
    if mimetype == JSON_MIME_TYPE or filename.endswith(".json"):
        return "json"

    return None


def error_response(error, message, status_code, **details):
    return jsonify({"error": error, "message": message, **details}), status_code


def receive_upload(file, first_chunk, kind):
    suffix = ".pdf" if kind == "pdf" else ".json"
    hasher = sha256()
    total_bytes = 0

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        temp_path = tmp.name
        chunk = first_chunk

        while chunk:
            total_bytes += len(chunk)
            hasher.update(chunk)
            tmp.write(chunk)
            chunk = file.stream.read(CHUNK_SIZE)

    return UploadedFile(
        temp_path=temp_path,
        file_hash=hasher.hexdigest(),
        imo_hash=file_imohash(temp_path),
        size_bytes=total_bytes,
        kind=kind,
        filename=file.filename or f"{uuid4()}{suffix}",
        content_type=file.mimetype
        or (PDF_MIME_TYPE if kind == "pdf" else JSON_MIME_TYPE),
    )


def cleanup_temp_file(temp_path):
    if not temp_path:
        return
    try:
        os.remove(temp_path)
    except OSError:
        pass


def store_pdf(uploaded_file):
    storage_path = storage.pdf_path_for_hash(uploaded_file.file_hash)
    reused_existing_pdf = storage.exists(storage_path)

    if not reused_existing_pdf:
        stored_file = storage.upload_file(
            uploaded_file.temp_path,
            uploaded_file.filename,
            uploaded_file.content_type,
            storage_path=storage_path,
        )
        seaweedfs_url = stored_file.seaweedfs_url
    else:
        seaweedfs_url = storage.url(storage_path)

    share = share_service.create_pdf_share(
        storage_path,
        uploaded_file.filename,
        uploaded_file.content_type,
    )

    return StoredPDF(
        storage_path=storage_path,
        seaweedfs_url=seaweedfs_url,
        signed_share_url=share.url,
        signed_share_expires_at=share.expires_at_iso(),
        sha256=uploaded_file.file_hash,
        reused_existing_pdf=reused_existing_pdf,
    ), share.token, share.expires_at


def ocr_source(temp_path, storage_path, signed_share_url, content_type):
    if is_public_https_url(signed_share_url):
        return OCRInput(type="url", value=signed_share_url, mime_type=content_type)

    if temp_path and os.path.exists(temp_path):
        return OCRInput(type="file_path", value=temp_path, mime_type=content_type)

    return OCRInput(
        type="bytes",
        value=storage.read(storage_path),
        mime_type=content_type,
    )


def process_pdf_job(
    upload_id, paper_id, temp_path, signed_share_url, storage_path, content_type
):
    try:
        job_queue.set_progress(
            upload_id,
            stage="ocr",
            progress=40,
            message="Running Mistral OCR...",
            signed_share_url=signed_share_url,
        )

        ocr_result = MistralOCRProvider.from_env().extract(
            ocr_source(temp_path, storage_path, signed_share_url, content_type)
        )
        if ocr_result is None:
            raise RuntimeError("Mistral OCR provider returned no result.")

        job_queue.set_progress(
            upload_id,
            stage="ocr_complete",
            progress=70,
            message="Mistral OCR completed.",
            ocr_page_count=len(ocr_result.pages),
        )

        # TODO: store ocr_result.raw, parse questions, then store questions in SQL.
        job_queue.set_progress(
            upload_id,
            stage="parsing",
            progress=75,
            message="Parsing questions...",
        )

        job_queue.complete_job(
            upload_id,
            message="Paper processed successfully.",
            result_url=f"/api/papers/{paper_id}/questions",
        )
    except Exception as exc:
        job_queue.fail_job(upload_id, message=str(exc), error=type(exc).__name__)
    finally:
        cleanup_temp_file(temp_path)


def start_pdf_job(upload_id, paper_id, temp_path, stored_pdf, content_type):
    thread = threading.Thread(
        target=process_pdf_job,
        args=(
            upload_id,
            paper_id,
            temp_path,
            stored_pdf.signed_share_url,
            stored_pdf.storage_path,
            content_type or PDF_MIME_TYPE,
        ),
        daemon=True,
    )
    thread.start()


def queue_existing_pdf_job(file_hash, filename, content_type, user_id):
    if not is_sha256_hash(file_hash):
        return error_response(
            "invalid_sha256",
            "A valid PDF SHA-256 hash is required.",
            400,
        )

    storage_path = storage.pdf_path_for_hash(file_hash)

    try:
        exists = storage.exists(storage_path)
    except URLError as exc:
        return error_response(
            "seaweedfs_unavailable",
            "Could not check SeaweedFS for the PDF.",
            503,
            details=str(getattr(exc, "reason", exc)),
        )

    if not exists:
        return error_response(
            "pdf_not_found",
            "This PDF is not stored in SeaweedFS yet.",
            404,
            sha256=file_hash.lower(),
            exists=False,
        )

    upload_id = str(uuid4())
    paper_id = str(uuid4())
    safe_filename = secure_filename(filename or "document.pdf") or "document.pdf"
    content_type = content_type or PDF_MIME_TYPE
    share = share_service.create_pdf_share(
        storage_path,
        safe_filename,
        content_type,
    )
    stored_pdf = StoredPDF(
        storage_path=storage_path,
        seaweedfs_url=storage.url(storage_path),
        signed_share_url=share.url,
        signed_share_expires_at=share.expires_at_iso(),
        sha256=file_hash.lower(),
        reused_existing_pdf=True,
    )

    job_queue.create_job(
        user_id=user_id,
        upload_id=upload_id,
        paper_id=paper_id,
        status="processing",
        stage="stored_seaweedfs",
        progress=35,
        message="Reusing PDF already stored in SeaweedFS.",
        filename=safe_filename,
        kind="pdf",
        content_type=content_type,
        **stored_pdf.as_dict(),
    )
    job_queue.create_token(
        share.token,
        upload_id=upload_id,
        storage_path=storage_path,
        filename=safe_filename,
        content_type=content_type,
        expires_at=share.expires_at,
    )

    start_pdf_job(upload_id, paper_id, None, stored_pdf, content_type)

    return jsonify(
        {
            "upload_id": upload_id,
            "paper_id": paper_id,
            "status": "processing",
            "stage": "queued",
            "progress": 35,
            "progress_url": f"/api/upload/{upload_id}/status",
            "result_url": f"/api/papers/{paper_id}/questions",
            **stored_pdf.as_dict(),
        }
    ), 202


@bp.route("/api/share/<token>", methods=["GET"])
def serve_signed_share(token):
    return share_service.pdf_response(token)


@bp.route("/api/upload/pdf/<file_hash>/status", methods=["GET"])
@jwt_required()
def stored_pdf_status(file_hash):
    if not is_sha256_hash(file_hash):
        return error_response(
            "invalid_sha256",
            "A valid PDF SHA-256 hash is required.",
            400,
        )

    storage_path = storage.pdf_path_for_hash(file_hash)

    try:
        exists = storage.exists(storage_path)
    except URLError as exc:
        return error_response(
            "seaweedfs_unavailable",
            "Could not check SeaweedFS for the PDF.",
            503,
            details=str(getattr(exc, "reason", exc)),
        )

    response = {
        "exists": exists,
        "sha256": file_hash.lower(),
        "storage_path": storage_path,
    }

    if exists:
        response["seaweedfs_url"] = storage.url(storage_path)

    return jsonify(response), 200


@bp.route("/api/upload/pdf/reuse", methods=["POST"])
@jwt_required()
def reuse_stored_pdf():
    body = request.get_json(silent=True) or {}
    return queue_existing_pdf_job(
        body.get("sha256"),
        body.get("filename"),
        body.get("content_type") or PDF_MIME_TYPE,
        get_jwt_identity(),
    )


@bp.route("/api/upload", methods=["POST"])
@jwt_required()
def upload():
    user_id = get_jwt_identity()
    file = request.files.get("file")

    if not file:
        return error_response("no_file", "No file uploaded.", 400)

    upload_id = str(uuid4())
    paper_id = str(uuid4())
    first_chunk = file.stream.read(CHUNK_SIZE)
    kind = detect_upload_kind(file, first_chunk)

    if kind is None:
        return error_response(
            "unsupported_file_type",
            f"Unsupported file type: {file.mimetype}",
            400,
        )

    if kind == "pdf" and not first_chunk.startswith(b"%PDF"):
        return error_response("invalid_pdf", "Uploaded file must be a valid PDF.", 400)

    job_queue.create_job(
        user_id=user_id,
        upload_id=upload_id,
        paper_id=paper_id,
        status="uploading",
        stage="receiving",
        progress=0,
        message="Receiving upload...",
        filename=file.filename,
        kind=kind,
        content_type=file.mimetype,
    )

    uploaded_file = receive_upload(file, first_chunk, kind)

    job_queue.set_progress(
        upload_id,
        stage="stored_temp",
        progress=25,
        message="Upload received. Preparing processing...",
        sha256=uploaded_file.file_hash,
        imohash=uploaded_file.imo_hash,
        size_bytes=uploaded_file.size_bytes,
    )

    try:
        if kind == "pdf":
            stored_pdf, token, expires_at = store_pdf(uploaded_file)
            storage_payload = stored_pdf.as_dict()
            job_queue.create_token(
                token,
                upload_id=upload_id,
                storage_path=stored_pdf.storage_path,
                filename=uploaded_file.filename,
                content_type=uploaded_file.content_type,
                expires_at=expires_at,
            )
        else:
            storage_payload = storage.upload_file(
                uploaded_file.temp_path,
                uploaded_file.filename,
                uploaded_file.content_type,
                upload_id=upload_id,
            ).as_dict()
    except URLError as exc:
        cleanup_temp_file(uploaded_file.temp_path)
        error_detail = str(getattr(exc, "reason", exc))
        job_queue.fail_job(
            upload_id,
            message="Could not upload to SeaweedFS.",
            error=error_detail,
            stage="storage_failed",
        )
        return error_response(
            "seaweedfs_unavailable",
            "Could not upload to SeaweedFS.",
            503,
            details=error_detail,
        )

    job_queue.set_progress(
        upload_id,
        stage="stored_seaweedfs",
        progress=35,
        message="Upload stored in SeaweedFS.",
        **storage_payload,
    )

    if kind == "pdf":
        stored_pdf = StoredPDF(**storage_payload)
        start_pdf_job(
            upload_id,
            paper_id,
            uploaded_file.temp_path,
            stored_pdf,
            uploaded_file.content_type,
        )
        return jsonify(
            {
                "upload_id": upload_id,
                "paper_id": paper_id,
                "status": "processing",
                "stage": "queued",
                "progress_url": f"/api/upload/{upload_id}/status",
                "result_url": f"/api/papers/{paper_id}/questions",
                **storage_payload,
            }
        ), 202

    cleanup_temp_file(uploaded_file.temp_path)
    job_queue.complete_job(
        upload_id,
        message="Upload stored successfully.",
        stage="stored",
        sha256=uploaded_file.file_hash,
        imohash=uploaded_file.imo_hash,
        size_bytes=uploaded_file.size_bytes,
    )

    return jsonify(
        {
            "upload_id": upload_id,
            "paper_id": paper_id,
            "status": "complete",
            "sha256": uploaded_file.file_hash,
            "imohash": uploaded_file.imo_hash,
            "size_bytes": uploaded_file.size_bytes,
            **storage_payload,
        }
    ), 201


@bp.route("/api/upload/<upload_id>/status", methods=["GET"])
@jwt_required()
def upload_status(upload_id):
    user_id = get_jwt_identity()
    job = job_queue.get_job(upload_id)

    if not job:
        return error_response("not_found", "Upload job not found.", 404)

    if job.get("user_id") != user_id:
        return error_response(
            "forbidden",
            "You do not have access to this upload.",
            403,
        )

    return jsonify(job), 200
