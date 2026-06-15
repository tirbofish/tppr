const basePath = import.meta.env.BASE_URL || "/";

function stripBasePath(path: string): string {
    if (basePath === "/" || !path.startsWith(basePath)) return path;
    const withoutBase = path.slice(basePath.length - 1);
    return withoutBase || "/";
}

export function safeRedirectPath(
    redirect: string | null | undefined,
    fallback = "/",
): string {
    if (!redirect) return fallback;

    const trimmed = redirect.trim();
    if (
        !trimmed ||
        trimmed.startsWith("//") ||
        /^[a-z][a-z0-9+.-]*:/i.test(trimmed)
    ) {
        return fallback;
    }

    if (!trimmed.startsWith("/")) return fallback;
    return stripBasePath(trimmed);
}

export function loginPath(redirect: string | null | undefined): string {
    const safeRedirect = safeRedirectPath(redirect);
    return safeRedirect === "/"
        ? "/login"
        : `/login?redirect=${encodeURIComponent(safeRedirect)}`;
}

export function signupPath(redirect: string | null | undefined): string {
    const safeRedirect = safeRedirectPath(redirect);
    return safeRedirect === "/"
        ? "/signup"
        : `/signup?redirect=${encodeURIComponent(safeRedirect)}`;
}
