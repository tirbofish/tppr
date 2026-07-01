# THIS FILE IS AI GENERATED.
#
# DigitalOcean Functions (serverless) entry point for the tppr backend.
#
# tppr is a Flask monolith, which is not a natural fit for FaaS. This adapter
# wraps the existing Flask WSGI application in a single HTTP-triggered function
# (`packages/tppr/api`) so the whole API surface runs serverlessly without
# rewriting the blueprints. The static SPA is NOT served from here by default
# (host it from DigitalOcean Spaces CDN / your existing tppr.online frontend).
#
# The backend source + the local `tppr_paper_extractor` package are vendored
# into this function directory at deploy time by `launch.py --deploy do-fns`,
# so imports like `import settings`, `from questions.db import ...` and
# `from tppr_paper_extractor import extract_paper` resolve at runtime.
#
# Known serverless caveats (see deploy/functions/README.md):
#   * flask-limiter uses in-memory storage -> rate limits are per warm instance.
#   * initialize_runtime() connects to Supabase Postgres on every cold start.
#   * Binary responses (PDFs, images) are returned base64-encoded; DO Functions
#     decodes these when the response Content-Type is a binary MIME.

import base64
import io
import os
import sys
import traceback
from urllib.parse import urlencode, unquote

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND_SRC = os.path.join(HERE, "backend_src")

# backend_src provides top-level modules (settings, main, auth, questions, ...).
# HERE provides the vendored tppr_paper_extractor package.
for _p in (BACKEND_SRC, HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_APP = None


def _get_app():
    """Lazily import and cache the Flask app so warm invocations reuse it."""
    global _APP
    if _APP is None:
        import main as backend_main  # noqa: runs initialize_runtime() once
        _APP = backend_main.app
    return _APP


_TEXTISH_PREFIXES = (
    "text/",
    "application/json",
    "application/javascript",
    "application/xml",
    "application/x-www-form-urlencoded",
    "application/ld+json",
    "image/svg+xml",
)


def _is_text(content_type):
    ct = (content_type or "").split(";", 1)[0].strip().lower()
    return any(ct.startswith(p) for p in _TEXTISH_PREFIXES) or ct == ""


def _header_value(value):
    if isinstance(value, (list, tuple)):
        return value[0] if value else ""
    return "" if value is None else str(value)


def _decode_body(body, content_type):
    """Recover the raw request body bytes from the DO Functions event."""
    if body is None:
        return b""
    if isinstance(body, (bytes, bytearray)):
        return bytes(body)
    if isinstance(body, (dict, list)):
        import json as _json
        return _json.dumps(body).encode("utf-8")
    # str: text content-types arrive raw; binary content-types arrive base64.
    if isinstance(body, str):
        if _is_text(content_type):
            return body.encode("utf-8")
        try:
            return base64.b64decode(body)
        except Exception:
            return body.encode("utf-8")
    return str(body).encode("utf-8")


def _build_environ(args):
    method = _header_value(args.get("__ow_method") or args.get("method") or "get").upper()
    headers = args.get("__ow_headers") or {}
    if not isinstance(headers, dict):
        headers = {}
    headers = {str(k).lower(): _header_value(v) for k, v in headers.items()}

    ow_path = args.get("__ow_path")
    path_info = unquote(_header_value(ow_path)) if ow_path is not None else "/"
    if not path_info.startswith("/"):
        path_info = "/" + path_info

    query = args.get("__ow_query")
    if isinstance(query, dict):
        query_string = urlencode(query, doseq=True)
    elif isinstance(query, str):
        query_string = query
    else:
        query_string = ""

    host = headers.get("host", "tppr.functions.ondigitalocean.app")
    scheme = "https"
    content_type = headers.get("content-type", "")
    body = _decode_body(args.get("__ow_body"), content_type)

    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path_info,
        "QUERY_STRING": query_string,
        "SERVER_NAME": host.split(":", 1)[0],
        "SERVER_PORT": headers.get("x-forwarded-port", "443"),
        "SERVER_PROTOCOL": "HTTP/1.1",
        "REMOTE_ADDR": (headers.get("x-forwarded-for", "").split(",")[0].strip()
                        or "127.0.0.1"),
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": scheme,
        "wsgi.input": io.BytesIO(body),
        "wsgi.errors": sys.stderr,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(body)),
    }
    for key, value in headers.items():
        if key in ("content-type", "content-length"):
            continue
        environ["HTTP_" + key.upper().replace("-", "_")] = value
    return environ


def _build_response(status_line, response_headers, body_bytes):
    status_code = int(status_line.split(" ", 1)[0])
    headers = {}
    cookies = []
    for name, value in response_headers:
        lname = name.lower()
        if lname == "set-cookie":
            cookies.append(value)
            continue
        headers[name] = value
    if cookies:
        # Browsers accept multiple cookies comma-separated in one header.
        headers["Set-Cookie"] = ", ".join(cookies)

    content_type = headers.get("Content-Type", headers.get("content-type", ""))
    if _is_text(content_type):
        body_out = body_bytes.decode("utf-8", "replace")
    else:
        body_out = base64.b64encode(body_bytes).decode("ascii")
    # Normalise header keys to DO's expected casing.
    out_headers = {}
    for k, v in headers.items():
        if k.lower() == "content-type":
            out_headers["Content-Type"] = v
        elif k.lower() == "content-length":
            # Let the platform set the transfer length.
            continue
        else:
            out_headers[k] = v
    return {"statusCode": status_code, "headers": out_headers, "body": body_out}


def main(args):
    try:
        app = _get_app()
        environ = _build_environ(args)
        status = {}
        response_headers = []

        def start_response(status_line, headers, exc_info=None):
            if exc_info:
                try:
                    raise exc_info[1].with_traceback(exc_info[2])
                finally:
                    exc_info = None
            status["line"] = status_line
            response_headers[:] = headers
            return lambda data: None

        chunks = app(environ, start_response)
        try:
            body_bytes = b"".join(chunks)
        finally:
            close = getattr(chunks, "close", None)
            if close:
                close()

        return _build_response(status["line"], response_headers, body_bytes)
    except Exception:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": '{"message":"internal server error","cause":'
                    + __import__("json").dumps(traceback.format_exc())
                    + '}',
        }
