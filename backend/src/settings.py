import os

def env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, "").split(",") if item.strip()]


def env_url(name: str) -> str:
    return os.getenv(name, "").strip().rstrip("/")


def required_secret(name: str, fallback: str) -> str:
    value = os.getenv(name)
    if not PRODUCTION:
        return value or fallback

    weak_values = {"", fallback, "dev-secret", "dev-jwt-secret", "your-secret-key-here", "your-jwt-secret-here"}
    if value is None or value.strip() in weak_values or len(value.strip()) < 32:
        raise RuntimeError(f"{name} must be set to a strong secret when PRODUCTION=1")
    return value


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
ASSETS_DIR = os.getenv("BACKEND_ASSETS_DIR", os.path.join(BACKEND_DIR, "assets"))
PACKAGED_FRONTEND_DIST_DIR = os.path.join(ASSETS_DIR, "site")
SOURCE_FRONTEND_DIST_DIR = os.path.join(PROJECT_ROOT, "frontend", "dist")
FRONTEND_DIST_DIR = os.getenv(
    "FRONTEND_DIST_DIR",
    PACKAGED_FRONTEND_DIST_DIR
    if os.path.isfile(os.path.join(PACKAGED_FRONTEND_DIST_DIR, "index.html"))
    else SOURCE_FRONTEND_DIST_DIR,
)
DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    os.path.join(PROJECT_ROOT, "database.db"),
)

API_ONLY_FLAG = "--api-only"
PRODUCTION = env_flag("PRODUCTION")
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT = int(os.getenv("PORT", os.getenv("BACKEND_PORT", "5000")))
BACKEND_DEBUG = False if PRODUCTION else env_flag("BACKEND_DEBUG_MODE", env_flag("BACKEND_DEBUG", True))

APP_NAME = "TPPR"
SECRET_KEY = required_secret("SECRET_KEY", "dev-secret")
SESSION_COOKIE_SAMESITE = os.getenv(
    "SESSION_COOKIE_SAMESITE",
    "None" if PRODUCTION else "Lax",
)
if SESSION_COOKIE_SAMESITE not in {"Strict", "Lax", "None"}:
    raise RuntimeError("SESSION_COOKIE_SAMESITE must be Strict, Lax, or None")

BACKEND_ALLOWED_ORIGINS = env_list("BACKEND_ALLOWED_ORIGINS")
if PRODUCTION:
    if "*" in BACKEND_ALLOWED_ORIGINS:
        raise RuntimeError("BACKEND_ALLOWED_ORIGINS cannot contain '*' when PRODUCTION=1")
    insecure_origins = [
        origin for origin in BACKEND_ALLOWED_ORIGINS if not origin.startswith("https://")
    ]
    if insecure_origins:
        raise RuntimeError(
            "BACKEND_ALLOWED_ORIGINS must contain only https:// origins when PRODUCTION=1"
        )
elif not BACKEND_ALLOWED_ORIGINS:
    BACKEND_ALLOWED_ORIGINS = ["http://localhost:5173"]

PUBLIC_API_DOCS = env_flag("PUBLIC_API_DOCS", True)
SHOW_ERROR_CAUSES = not PRODUCTION
RATELIMIT_DEFAULT = os.getenv(
    "RATELIMIT_DEFAULT",
    "60 per minute" if PRODUCTION else "200 per minute",
)
RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")

TOTP_ISSUER_NAME = os.getenv("TOTP_ISSUER_NAME", APP_NAME)
TOTP_VALID_WINDOW = int(os.getenv("TOTP_VALID_WINDOW", "1"))
QR_CODE_VERSION = int(os.getenv("QR_CODE_VERSION", "1"))
QR_CODE_BOX_SIZE = int(os.getenv("QR_CODE_BOX_SIZE", "10"))
QR_CODE_BORDER = int(os.getenv("QR_CODE_BORDER", "5"))
QR_CODE_FILL_COLOR = os.getenv("QR_CODE_FILL_COLOR", "black")
QR_CODE_BACK_COLOR = os.getenv("QR_CODE_BACK_COLOR", "white")
QR_CODE_IMAGE_FORMAT = os.getenv("QR_CODE_IMAGE_FORMAT", "PNG")

PDF_MIME_TYPE = "application/pdf"
JSON_MIME_TYPE = "application/json"
FORM_MIME_TYPE = "application/x-www-form-urlencoded"
BINARY_MIME_TYPE = "application/octet-stream"
HTML_MIME_TYPE = "text/html"
MARKDOWN_MIME_TYPE = "text/markdown"

DEFAULT_PDF_FILENAME = os.getenv("DEFAULT_PDF_FILENAME", "document.pdf")
DEFAULT_UPLOAD_FILENAME = os.getenv("DEFAULT_UPLOAD_FILENAME", "upload")
UPLOAD_CHUNK_SIZE_BYTES = int(os.getenv("UPLOAD_CHUNK_SIZE_BYTES", str(1024 * 1024)))
IMOHASH_SAMPLE_THRESHOLD_BYTES = int(
    os.getenv("IMOHASH_SAMPLE_THRESHOLD_BYTES", "131072")
)
IMOHASH_SAMPLE_SIZE_BYTES = int(os.getenv("IMOHASH_SAMPLE_SIZE_BYTES", "16384"))
SHA256_HEX_LENGTH = 64

LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "::1"}
SEAWEEDFS_DEFAULT_FILER_URL = os.getenv(
    "SEAWEEDFS_FILER_URL",
    "http://localhost:8888",
)
SEAWEEDFS_DEFAULT_BUCKET = os.getenv("SEAWEEDFS_S3_BUCKET", "tppr")
SEAWEEDFS_TIMEOUT_SECONDS = int(os.getenv("SEAWEEDFS_TIMEOUT_SECONDS", "60"))
SEAWEEDFS_BUCKETS_PREFIX = "buckets"
SEAWEEDFS_UPLOADS_PREFIX = "uploads"
SEAWEEDFS_PDF_HASH_PREFIX = "pdf-sha256"

PDF_SHARE_LINK_SECRET = (
    os.getenv("PDF_SHARE_LINK_SECRET")
    or SECRET_KEY
    or "dev-share-link-secret"
)
PDF_SHARE_LINK_TTL_SECONDS = int(os.getenv("PDF_SHARE_LINK_TTL_SECONDS", "3600"))
PDF_SHARE_ROUTE_PREFIX = "/api/share"
PDF_SHARE_STORAGE_PREFIX = "/buckets/"
PDF_RESPONSE_CACHE_CONTROL = "private, max-age=0, no-store"

UPLOAD_STATUS_TERMINAL = {"complete", "failed"}
UPLOAD_PROGRESS_CHECKING_STORAGE = 5
UPLOAD_PROGRESS_RECEIVED = 25
UPLOAD_PROGRESS_STORED = 35
UPLOAD_PROGRESS_OCR_STARTED = 40
UPLOAD_PROGRESS_OCR_COMPLETE = 70
UPLOAD_PROGRESS_PARSING = 75
UPLOAD_PROGRESS_DONE = 100

SUPABASE_URL = env_url("SUPABASE_URL") or env_url("VITE_SUPABASE_URL")
SUPABASE_JWKS_URL = (
    env_url("SUPABASE_JWKS_URL")
    or (f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else "")
)
SUPABASE_JWT_ISSUER = (
    env_url("SUPABASE_JWT_ISSUER")
    or (f"{SUPABASE_URL}/auth/v1" if SUPABASE_URL else "")
)
SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET")
SUPABASE_JWT_AUDIENCE = os.getenv("SUPABASE_JWT_AUDIENCE", "authenticated").strip()
# Secret key for server-side Supabase Storage operations (avatar and
# question-asset uploads). This is the project's secret key (sb_secret_...);
# it bypasses Row Level Security, so it must NEVER be exposed to the browser.
# When unset, avatars fall back to inline data URLs and question assets stay
# as bytes in Postgres (the local/no-Storage development path).
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
SUPABASE_AVATAR_BUCKET = os.getenv("SUPABASE_AVATAR_BUCKET", "avatars")
SUPABASE_QUESTION_ASSET_BUCKET = os.getenv(
    "SUPABASE_QUESTION_ASSET_BUCKET", "tppr-question-assets"
)
if PRODUCTION and not SUPABASE_JWKS_URL and not SUPABASE_JWT_SECRET:
    raise RuntimeError(
        "SUPABASE_URL or SUPABASE_JWKS_URL must be set when PRODUCTION=1"
    )
