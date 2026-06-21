// THIS IS MADE WITH AI, EXPECT TO READY FOR DEPLOYMENT
const backendUrl = (
    localStorage.getItem("tppr-custom-backend-url") ||
    import.meta.env.VITE_BACKEND_URL || ""
).trim().replace(/\/+$/, "");

function withBackendUrl(input: RequestInfo | URL): RequestInfo | URL {
    if (!backendUrl) return input;

    if (typeof input === "string") {
        return input.startsWith("/api") ? `${backendUrl}${input}` : input;
    }

    if (input instanceof URL) {
        if (input.origin === window.location.origin && input.pathname.startsWith("/api")) {
            return new URL(`${backendUrl}${input.pathname}${input.search}${input.hash}`);
        }
        return input;
    }

    const requestUrl = new URL(input.url);
    if (requestUrl.origin !== window.location.origin || !requestUrl.pathname.startsWith("/api")) {
        return input;
    }

    return new Request(
        `${backendUrl}${requestUrl.pathname}${requestUrl.search}${requestUrl.hash}`,
        input,
    );
}

export function installBackendUrlFetch() {
    if (!backendUrl) return;

    const originalFetch = window.fetch.bind(window);
    window.fetch = (input, init) => originalFetch(withBackendUrl(input), init);
}
