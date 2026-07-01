"""Avatar image storage.

When Supabase Storage is configured (``SUPABASE_URL`` + ``SUPABASE_SECRET_KEY``)
the image bytes are uploaded to the avatar bucket (``SUPABASE_AVATAR_BUCKET``)
and the public URL is returned. Otherwise the bytes are returned as a base64
``data:`` URL so avatars keep working in local development without any Storage
setup.
"""

import base64
import time
from urllib.parse import urlsplit

import settings
from storage import (
    delete_object,
    public_url as storage_public_url,
    storage_configured,
    upload_object,
)

# Extension lookup for the storage object path.
_EXT_FOR_MIME = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
}

ALLOWED_AVATAR_MIME = set(_EXT_FOR_MIME)
MAX_AVATAR_BYTES = 1_000_000


def _object_path(user_id: str, mime: str) -> str:
    ext = _EXT_FOR_MIME.get(mime, "png")
    return f"{user_id}.{ext}"


def _public_url(path: str) -> str:
    return storage_public_url(settings.SUPABASE_AVATAR_BUCKET, path)


def _data_url(mime: str, data: bytes) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def store_avatar(user_id: str, mime: str, data: bytes) -> str:
    """Persist avatar bytes and return a renderable URL.

    When Storage is configured the bytes are uploaded to
    ``<avatar bucket>/<user_id>.<ext>`` and the public URL is returned.
    Otherwise a ``data:`` URL is returned for inline storage in the ``users``
    table.
    """
    if storage_configured():
        path = _object_path(user_id, mime)
        upload_object(settings.SUPABASE_AVATAR_BUCKET, path, mime, data)
        return f"{_public_url(path)}?v={time.time_ns()}"
    return _data_url(mime, data)


def delete_avatar(user_id: str, stored_url: str | None) -> None:
    """Remove a previously-stored avatar. Best-effort; never raises."""
    if not stored_url or not storage_configured():
        return
    # Only Storage URLs map back to a deletable object; data URLs are inline and
    # cleared simply by nulling the column.
    prefix = _public_url("")  # ".../object/public/<bucket>/"
    parsed = urlsplit(stored_url)
    clean_url = parsed._replace(query="", fragment="").geturl()
    if not clean_url.startswith(prefix):
        return
    path = clean_url[len(prefix):]
    if path:
        delete_object(settings.SUPABASE_AVATAR_BUCKET, path)
