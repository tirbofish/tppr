import type { PaperMeta, PaperVerificationRequest } from "@/types/tppr-paper";
import { apiFetch } from "./client";

interface AdminPapersResponse {
    papers: PaperMeta[];
    total: number;
    page: number;
    per_page: number;
}

export interface AdminPaperFilters {
    q?: string;
    status?: string;
    page?: number;
    per_page?: number;
}

export interface AdminVerificationRequest extends PaperVerificationRequest {
    paper: PaperMeta | null;
}

interface AdminVerificationRequestsResponse {
    requests: AdminVerificationRequest[];
    total: number;
    page: number;
    per_page: number;
}

export async function getTakenDownPapers(
    filters: AdminPaperFilters = {},
): Promise<AdminPapersResponse> {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
        if (value !== undefined && value !== "") params.set(key, String(value));
    }

    const res = await apiFetch(`/api/admin/takedowns?${params}`);
    if (!res.ok) throw new Error(`Failed to fetch takedowns: ${res.status}`);
    return res.json();
}

export async function restoreTakenDownPaper(paperId: string): Promise<void> {
    const res = await apiFetch(`/api/admin/takedown/${paperId}`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error(`Failed to restore takedown: ${res.status}`);
}

export async function getVerificationRequests(
    filters: AdminPaperFilters = {},
): Promise<AdminVerificationRequestsResponse> {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
        if (value !== undefined && value !== "") params.set(key, String(value));
    }

    const res = await apiFetch(`/api/admin/verification-requests?${params}`);
    if (!res.ok) {
        throw new Error(`Failed to fetch verification requests: ${res.status}`);
    }
    return res.json();
}

export async function resolveVerificationRequest(
    requestId: string,
    data: { status: "approved" | "rejected"; admin_note?: string },
): Promise<AdminVerificationRequest> {
    const res = await apiFetch(`/api/admin/verification-requests/${requestId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.message ?? "Failed to resolve verification request");
    }
    return res.json();
}
