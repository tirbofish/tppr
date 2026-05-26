import json
import sqlite3
from datetime import datetime
from hashlib import sha256
from uuid import uuid4

from shared import DB_PATH


class UploadStatusJobQueueYaddaYaddaDo:
    JOB_COLUMNS = {
        "upload_id",
        "paper_id",
        "user_id",
        "status",
        "stage",
        "progress",
        "message",
        "filename",
        "kind",
        "content_type",
        "sha256",
        "size_bytes",
        "storage_path",
        "seaweedfs_url",
        "signed_share_url",
        "signed_share_expires_at",
        "result_url",
        "error",
        "details",
        "ocr_page_count",
        "created_at",
        "updated_at",
        "completed_at",
    }

    TOKEN_COLUMNS = {
        "token_id",
        "upload_id",
        "token_hash",
        "token",
        "token_type",
        "storage_path",
        "filename",
        "content_type",
        "expires_at",
        "created_at",
        "revoked_at",
    }

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.prepare()

    def connect(self, row_factory=True):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        if row_factory:
            conn.row_factory = sqlite3.Row
        return conn

    def prepare(self):
        conn = self.connect(row_factory=False)
        try:
            cur = conn.cursor()
            self._create_tables(cur)
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_job(self, user_id, upload_id=None, paper_id=None, **fields):
        upload_id = upload_id or str(uuid4())
        now = self._utcnow()
        data = {
            "upload_id": upload_id,
            "paper_id": paper_id,
            "user_id": str(user_id),
            "status": fields.pop("status", "pending"),
            "stage": fields.pop("stage", "created"),
            "progress": fields.pop("progress", 0),
            "created_at": fields.pop("created_at", now),
            "updated_at": now,
            **fields,
        }
        return self._upsert_job(data)

    def get_job(self, upload_id):
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM upload_jobs WHERE upload_id = ?", (upload_id,))
            return self._job_from_row(cur.fetchone())
        finally:
            conn.close()

    def update_job(self, upload_id, **updates):
        existing = self.get_job(upload_id)
        if not existing:
            raise KeyError(f"Upload job not found: {upload_id}")

        updates["upload_id"] = upload_id
        updates["updated_at"] = self._utcnow()
        if updates.get("status") in {"complete", "failed"} and not updates.get(
            "completed_at"
        ):
            updates["completed_at"] = updates["updated_at"]

        return self._upsert_job(updates, existing=existing)

    def set_progress(self, upload_id, stage=None, progress=None, message=None, **updates):
        if stage is not None:
            updates["stage"] = stage
        if progress is not None:
            updates["progress"] = progress
        if message is not None:
            updates["message"] = message
        if "status" not in updates:
            updates["status"] = "processing"
        return self.update_job(upload_id, **updates)

    def complete_job(self, upload_id, message="Upload job complete.", **updates):
        return self.update_job(
            upload_id,
            status="complete",
            stage=updates.pop("stage", "ready"),
            progress=updates.pop("progress", 100),
            message=message,
            completed_at=self._utcnow(),
            **updates,
        )

    def fail_job(self, upload_id, message, error=None, **updates):
        return self.update_job(
            upload_id,
            status="failed",
            stage=updates.pop("stage", "failed"),
            progress=updates.pop("progress", 100),
            message=message,
            error=error,
            completed_at=self._utcnow(),
            **updates,
        )

    def list_jobs(self, user_id=None, status=None, limit=50, offset=0):
        clauses = []
        values = []

        if user_id is not None:
            clauses.append("user_id = ?")
            values.append(str(user_id))
        if status is not None:
            clauses.append("status = ?")
            values.append(status)

        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        values.extend([int(limit), int(offset)])

        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT * FROM upload_jobs
                {where}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                values,
            )
            return [self._job_from_row(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def delete_job(self, upload_id):
        conn = self.connect(row_factory=False)
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM upload_jobs WHERE upload_id = ?", (upload_id,))
            conn.commit()
            return cur.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_token(
        self,
        token,
        upload_id=None,
        token_type="share",
        storage_path=None,
        filename=None,
        content_type=None,
        expires_at=None,
        **metadata,
    ):
        data = {
            "upload_id": upload_id,
            "token_hash": self.hash_token(token),
            "token": token,
            "token_type": token_type,
            "storage_path": storage_path,
            "filename": filename,
            "content_type": content_type,
            "expires_at": expires_at,
            "created_at": self._utcnow(),
            "metadata_json": self._encode_metadata(metadata),
        }

        columns = list(data.keys())
        placeholders = ", ".join("?" for _ in columns)
        update_columns = [column for column in columns if column != "token_hash"]
        update_clause = ", ".join(
            f"{column} = excluded.{column}" for column in update_columns
        )

        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO upload_job_tokens ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(token_hash) DO UPDATE SET {update_clause}
                """,
                [data[column] for column in columns],
            )
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

        return self.get_token(token)

    def get_token(self, token):
        return self.get_token_by_hash(self.hash_token(token))

    def get_token_by_hash(self, token_hash):
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM upload_job_tokens WHERE token_hash = ?",
                (token_hash,),
            )
            return self._token_from_row(cur.fetchone())
        finally:
            conn.close()

    def list_tokens(self, upload_id):
        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT * FROM upload_job_tokens
                WHERE upload_id = ?
                ORDER BY created_at DESC
                """,
                (upload_id,),
            )
            return [self._token_from_row(row) for row in cur.fetchall()]
        finally:
            conn.close()

    def revoke_token(self, token):
        conn = self.connect(row_factory=False)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE upload_job_tokens
                SET revoked_at = ?
                WHERE token_hash = ?
                """,
                (self._utcnow(), self.hash_token(token)),
            )
            conn.commit()
            return cur.rowcount > 0
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def delete_expired_tokens(self, now_epoch=None):
        cutoff = int(now_epoch if now_epoch is not None else datetime.utcnow().timestamp())
        conn = self.connect(row_factory=False)
        try:
            cur = conn.cursor()
            cur.execute(
                """
                DELETE FROM upload_job_tokens
                WHERE expires_at IS NOT NULL AND expires_at < ?
                """,
                (cutoff,),
            )
            conn.commit()
            return cur.rowcount
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def hash_token(self, token):
        return sha256(token.encode("utf-8")).hexdigest()

    def _create_tables(self, cur):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS upload_jobs (
                upload_id TEXT PRIMARY KEY,
                paper_id TEXT,
                user_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                stage TEXT,
                progress INTEGER NOT NULL DEFAULT 0,
                message TEXT,
                filename TEXT,
                kind TEXT,
                content_type TEXT,
                sha256 TEXT,
                size_bytes INTEGER,
                storage_path TEXT,
                seaweedfs_url TEXT,
                signed_share_url TEXT,
                signed_share_expires_at TEXT,
                result_url TEXT,
                error TEXT,
                details TEXT,
                ocr_page_count INTEGER,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_upload_jobs_user_id
            ON upload_jobs(user_id);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_upload_jobs_status
            ON upload_jobs(status);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_upload_jobs_sha256
            ON upload_jobs(sha256);
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS upload_job_tokens (
                token_id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id TEXT,
                token_hash TEXT UNIQUE NOT NULL,
                token TEXT NOT NULL,
                token_type TEXT NOT NULL DEFAULT 'share',
                storage_path TEXT,
                filename TEXT,
                content_type TEXT,
                expires_at INTEGER,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                revoked_at TEXT,
                FOREIGN KEY(upload_id) REFERENCES upload_jobs(upload_id)
                    ON DELETE CASCADE
            );
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_upload_job_tokens_upload_id
            ON upload_job_tokens(upload_id);
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_upload_job_tokens_expires_at
            ON upload_job_tokens(expires_at);
            """
        )

    def _upsert_job(self, fields, existing=None):
        direct, metadata = self._split_fields(fields, self.JOB_COLUMNS)
        if existing:
            existing_direct = {
                column: existing.get(column)
                for column in self.JOB_COLUMNS
                if existing.get(column) is not None
            }
            existing_direct.update(direct)
            direct = existing_direct

            existing_metadata = {
                key: value for key, value in existing.items() if key not in self.JOB_COLUMNS
            }
            existing_metadata.update(metadata)
            metadata = existing_metadata

        direct["metadata_json"] = self._encode_metadata(metadata)
        columns = list(direct.keys())
        placeholders = ", ".join("?" for _ in columns)
        update_columns = [column for column in columns if column != "upload_id"]
        update_clause = ", ".join(
            f"{column} = excluded.{column}" for column in update_columns
        )

        conn = self.connect()
        try:
            cur = conn.cursor()
            cur.execute(
                f"""
                INSERT INTO upload_jobs ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT(upload_id) DO UPDATE SET {update_clause}
                """,
                [direct[column] for column in columns],
            )
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

        return self.get_job(direct["upload_id"])

    def _split_fields(self, fields, columns):
        direct = {}
        metadata = {}

        for key, value in fields.items():
            if key in columns:
                direct[key] = value
            elif key == "metadata" and isinstance(value, dict):
                metadata.update(value)
            else:
                metadata[key] = value

        return direct, metadata

    def _job_from_row(self, row):
        if row is None:
            return None
        data = dict(row)
        metadata = self._decode_metadata(data.pop("metadata_json", "{}"))
        data.update(metadata)
        return data

    def _token_from_row(self, row):
        if row is None:
            return None
        data = dict(row)
        metadata = self._decode_metadata(data.pop("metadata_json", "{}"))
        data.update(metadata)
        return data

    def _encode_metadata(self, value):
        if not value:
            return "{}"
        return json.dumps(value, separators=(",", ":"), sort_keys=True)

    def _decode_metadata(self, value):
        if not value:
            return {}
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _utcnow(self):
        return datetime.utcnow().isoformat()
