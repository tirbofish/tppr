import urllib.error
import urllib.parse
import urllib.request

import settings


def delete_supabase_auth_user(user_id: str) -> None:
    """Delete a Supabase Auth user with the server-side secret key."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SECRET_KEY:
        raise RuntimeError("Supabase admin deletion is not configured")

    quoted_user_id = urllib.parse.quote(user_id, safe="")
    req = urllib.request.Request(
        f"{settings.SUPABASE_URL}/auth/v1/admin/users/{quoted_user_id}",
        method="DELETE",
        headers={
            "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
            "apikey": settings.SUPABASE_SECRET_KEY,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status not in (200, 204):
                raise RuntimeError(
                    f"Supabase Auth delete failed: HTTP {response.status}"
                )
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return
        raise RuntimeError(f"Supabase Auth delete failed: HTTP {e.code}") from e
