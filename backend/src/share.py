import base64
import hmac
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from urllib.error import HTTPError, URLError
from urllib.parse import quote

from flask import Response, jsonify, request
from seaweed import SeaweedFS
from werkzeug.utils import secure_filename


class ShareLinkError(ValueError):
    pass


@dataclass(frozen=True)
class ShareLink:
    token: str
    url: str
    expires_at: int

    def expires_at_iso(self):
        return datetime.fromtimestamp(self.expires_at).isoformat()


class PDFShareService:
    """
    Allows for a PDF (or anything within seaweed) to be public for a certain amount of time.
    """

    def __init__(
        self,
        seaweedfs=None,
        secret=None,
        public_base_url=None,
        ttl_seconds=None,
    ):
        self.seaweedfs = seaweedfs or SeaweedFS.from_env()
        self.secret = (secret or self._secret_from_env()).encode("utf-8")
        self.public_base_url = public_base_url
        self.ttl_seconds = ttl_seconds or self._ttl_from_env()

    def create_pdf_share(self, storage_path, filename=None, content_type=None):
        token, expires_at = self.create_token(
            storage_path=storage_path,
            filename=filename or "document.pdf",
            content_type=content_type or "application/pdf",
        )
        return ShareLink(
            token=token,
            url=f"{self.get_public_base_url()}/api/share/{quote(token, safe='')}",
            expires_at=expires_at,
        )

    def create_token(self, storage_path, filename=None, content_type=None):
        expires_at = int(time.time()) + self.ttl_seconds
        payload = {
            "path": self.seaweedfs.normalize_path(storage_path),
            "filename": secure_filename(filename or "document.pdf") or "document.pdf",
            "content_type": content_type or "application/pdf",
            "exp": expires_at,
        }
        payload_bytes = json.dumps(
            payload, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        encoded_payload = self._base64url_encode(payload_bytes)
        signature = hmac.new(
            self.secret, encoded_payload.encode("ascii"), sha256
        ).digest()

        return f"{encoded_payload}.{self._base64url_encode(signature)}", expires_at

    def verify_token(self, token):
        try:
            encoded_payload, encoded_signature = token.split(".", 1)
        except ValueError as exc:
            raise ShareLinkError("Malformed share link.") from exc

        expected_signature = hmac.new(
            self.secret, encoded_payload.encode("ascii"), sha256
        ).digest()
        actual_signature = self._base64url_decode(encoded_signature)

        if not hmac.compare_digest(actual_signature, expected_signature):
            raise ShareLinkError("Invalid share link signature.")

        payload = json.loads(self._base64url_decode(encoded_payload).decode("utf-8"))
        storage_path = payload.get("path", "")

        if int(payload.get("exp", 0)) < int(time.time()):
            raise ShareLinkError("Share link has expired.")

        if not storage_path.startswith("/buckets/"):
            raise ShareLinkError("Share link points to an invalid storage path.")

        return payload

    def read_pdf(self, token):
        payload = self.verify_token(token)
        return self.seaweedfs.read(payload["path"]), payload

    def pdf_response(self, token):
        try:
            body, payload = self.read_pdf(token)
        except ShareLinkError:
            return jsonify({"error": "invalid_share_link"}), 403
        except HTTPError as exc:
            if exc.code == 404:
                return jsonify({"error": "not_found"}), 404
            return jsonify({"error": "storage_unavailable"}), 502
        except URLError:
            return jsonify({"error": "storage_unavailable"}), 502

        filename = (
            secure_filename(payload.get("filename") or "document.pdf") or "document.pdf"
        )
        response = Response(
            body, mimetype=payload.get("content_type") or "application/pdf"
        )
        response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
        response.headers["Cache-Control"] = "private, max-age=0, no-store"
        return response

    def get_public_base_url(self):
        configured_url = (
            self.public_base_url
            or os.getenv("BACKEND_PUBLIC_URL")
            or os.getenv("PUBLIC_BASE_URL")
        )

        if configured_url:
            return configured_url.rstrip("/")

        return request.url_root.rstrip("/")

    def _secret_from_env(self):
        return (
            os.getenv("PDF_SHARE_LINK_SECRET")
            or os.getenv("JWT_SECRET_KEY")
            or os.getenv("SECRET_KEY")
            or "dev-share-link-secret"
        )

    def _ttl_from_env(self):
        try:
            return int(os.getenv("PDF_SHARE_LINK_TTL_SECONDS", "3600"))
        except ValueError:
            return 3600

    def _base64url_encode(self, data):
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    def _base64url_decode(self, value):
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)


def pdf_share_service():
    return PDFShareService()
