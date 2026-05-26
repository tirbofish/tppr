import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from werkzeug.utils import secure_filename


@dataclass(frozen=True)
class SeaweedFile:
    storage_path: str
    seaweedfs_url: str
    content_type: str | None = None
    size_bytes: int | None = None

    def as_dict(self):
        data = {
            "storage_path": self.storage_path,
            "seaweedfs_url": self.seaweedfs_url,
        }
        if self.content_type:
            data["content_type"] = self.content_type
        if self.size_bytes is not None:
            data["size_bytes"] = self.size_bytes
        return data


class SeaweedFS:
    def __init__(self, filer_url=None, bucket=None, timeout=60):
        self.filer_url = (
            filer_url or os.getenv("SEAWEEDFS_FILER_URL", "http://localhost:8888")
        ).rstrip("/")
        self.bucket = bucket or os.getenv("SEAWEEDFS_S3_BUCKET", "tppr")
        self.timeout = timeout

    @classmethod
    def from_env(cls):
        return cls()

    def bucket_path(self, *parts):
        clean_parts = [self._clean_path_part(part) for part in parts if part]
        suffix = "/".join(part for part in clean_parts if part)
        return f"/buckets/{self.bucket}/{suffix}" if suffix else f"/buckets/{self.bucket}"

    def upload_path(self, filename, upload_id=None, date=None):
        safe_name = secure_filename(filename or "upload") or "upload"
        prefix = (date or datetime.utcnow()).strftime("%Y/%m/%d")
        stored_name = f"{upload_id}-{safe_name}" if upload_id else safe_name
        return self.bucket_path("uploads", prefix, stored_name)

    def pdf_path_for_hash(self, file_hash):
        return self.bucket_path("uploads", "pdf-sha256", f"{file_hash.lower()}.pdf")

    def url(self, storage_path):
        normalized = self.normalize_path(storage_path).lstrip("/")
        return f"{self.filer_url}/{quote(normalized, safe='/')}"

    def exists(self, storage_path):
        req = Request(self.url(storage_path), method="HEAD")

        try:
            with urlopen(req, timeout=self.timeout) as response:
                response.read()
            return True
        except HTTPError as exc:
            if exc.code == 404:
                return False
            raise

    def read(self, storage_path):
        with urlopen(self.url(storage_path), timeout=self.timeout) as response:
            return response.read()

    def write(self, storage_path, data, content_type="application/octet-stream"):
        body = self._coerce_bytes(data)
        req = Request(
            self.url(storage_path),
            data=body,
            method="PUT",
            headers={
                "Content-Type": content_type or "application/octet-stream",
                "Content-Length": str(len(body)),
            },
        )

        with urlopen(req, timeout=self.timeout) as response:
            response.read()

        return SeaweedFile(
            storage_path=self.normalize_path(storage_path),
            seaweedfs_url=self.url(storage_path),
            content_type=content_type,
            size_bytes=len(body),
        )

    def write_file(self, storage_path, file_path, content_type="application/octet-stream"):
        return self.write(storage_path, Path(file_path).read_bytes(), content_type)

    def upload_file(
        self,
        file_path,
        filename,
        content_type="application/octet-stream",
        upload_id=None,
        storage_path=None,
    ):
        target_path = storage_path or self.upload_path(filename, upload_id=upload_id)
        return self.write_file(target_path, file_path, content_type)

    def delete(self, storage_path):
        req = Request(self.url(storage_path), method="DELETE")

        try:
            with urlopen(req, timeout=self.timeout) as response:
                response.read()
            return True
        except HTTPError as exc:
            if exc.code == 404:
                return False
            raise

    def normalize_path(self, storage_path):
        if not storage_path:
            raise ValueError("storage_path is required.")

        normalized = str(storage_path).replace("\\", "/").strip()
        if not normalized.startswith("/"):
            normalized = "/" + normalized

        return normalized

    def _clean_path_part(self, value):
        return str(value).replace("\\", "/").strip("/")

    def _coerce_bytes(self, data):
        if isinstance(data, bytes):
            return data
        if isinstance(data, bytearray):
            return bytes(data)
        if isinstance(data, str):
            return data.encode("utf-8")
        raise TypeError("SeaweedFS.write expects bytes, bytearray, or str data.")
