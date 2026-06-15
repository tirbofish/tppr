const CSRF_COOKIE_NAME = "csrf_access_token";
const CSRF_HEADER_NAME = "X-CSRF-TOKEN";
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function readCookie(name: string): string | null {
    const prefix = `${name}=`;
    const cookie = document.cookie
        .split(";")
        .map((part) => part.trim())
        .find((part) => part.startsWith(prefix));

    if (!cookie) return null;
    return decodeURIComponent(cookie.slice(prefix.length));
}

export function apiFetch(input: RequestInfo | URL, init: RequestInit = {}) {
    const method = (init.method ?? "GET").toUpperCase();
    const headers = new Headers(init.headers);

    if (UNSAFE_METHODS.has(method) && !headers.has(CSRF_HEADER_NAME)) {
        const csrfToken = readCookie(CSRF_COOKIE_NAME);
        if (csrfToken) headers.set(CSRF_HEADER_NAME, csrfToken);
    }

    return fetch(input, {
        ...init,
        headers,
        credentials: init.credentials ?? "include",
    });
}
