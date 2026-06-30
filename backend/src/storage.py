"""Server-side Supabase Storage helpers.

Raw ``urllib`` calls against the Storage REST API, authenticated with the
project secret key (``SUPABASE_SECRET_KEY``). The secret key bypasses Row
Level Security, so these helpers are for server-side use only — the key must
never reach the browser.

When Storage is not configured (no secret key), callers fall back to their
previous behaviour (avatars as inline ``data:`` URLs, question assets as bytes
in Postgres), so local development without Storage keeps working.
"""

import urllib.error
import urllib.request

import settings


def storage_configured() -> bool:
    """True when both the project URL and the server-side secret key are set."""
    return bool(settings.SUPABASE_URL and settings.SUPABASE_SECRET_KEY)


def _public_base(bucket: str) -> str:
    return f"{settings.SUPABASE_URL}/storage/v1/object/public/{bucket}"


def _api_base(bucket: str) -> str:
    return f"{settings.SUPABASE_URL}/storage/v1/object/{bucket}"


def public_url(bucket: str, path: str) -> str:
    """Public URL for an object in a public bucket."""
    return f"{_public_base(bucket)}/{path}"


def upload_object(bucket: str, path: str, mime: str, data: bytes) -> None:
    """Upload bytes to a Storage bucket (upsert). Raises ``RuntimeError`` on failure."""
    req = urllib.request.Request(
        f"{_api_base(bucket)}/{path}",
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
            "Content-Type": mime,
            "x-upsert": "true",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as _:
            pass
    except urllib.error.HTTPError as e:
        # 409 (already exists) is fine because we set x-upsert, but be defensive.
        if e.code not in (200, 201, 409):
            raise RuntimeError(f"Supabase Storage upload failed: HTTP {e.code}")


def delete_object(bucket: str, path: str) -> None:
    """Best-effort removal of a Storage object. Never raises."""
    req = urllib.request.Request(
        f"{_api_base(bucket)}/{path}",
        method="DELETE",
        headers={
            "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as _:
            pass
    except Exception:
        # Deletion is best-effort; stale objects are harmless and overwritten on next upload.
        pass