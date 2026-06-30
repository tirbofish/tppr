import type { PaperMeta } from "@/types/tppr-paper";
import { apiFetch } from "./client";

export type ReportReason =
    | "false_information"
    | "copyright"
    | "inappropriate"
    | "broken_content"
    | "spam"
    | "other";

export type ReportStatus = "open" | "reviewing" | "resolved" | "dismissed";

export interface PaperReport {
    id: number;
    paper_id: string;
    reporter_id: string;
    reason: ReportReason;
    details: string | null;
    status: ReportStatus;
    created_at: string | null;
    updated_at: string | null;
    paper?: PaperMeta;
}

export interface ReportsResponse {
    reports: PaperReport[];
    total: number;
    page: number;
    per_page: number;
}

async function jsonOrThrow<T>(res: Response, fallback: string): Promise<T> {
    if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.message ?? fallback);
    }
    return res.json() as Promise<T>;
}

export function reportPaper(
    paperId: string,
    data: { reason: ReportReason; details?: string },
): Promise<PaperReport> {
    return apiFetch(`/api/papers/${paperId}/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    }).then((r) => jsonOrThrow(r, "Failed to submit report"));
}

export function getAdminReports(params?: {
    paper_id?: string;
    status?: ReportStatus | "all";
    page?: number;
    per_page?: number;
}): Promise<ReportsResponse> {
    const qs = new URLSearchParams();
    if (params?.paper_id) qs.set("paper_id", params.paper_id);
    if (params?.status) qs.set("status", params.status);
    if (params?.page) qs.set("page", String(params.page));
    if (params?.per_page) qs.set("per_page", String(params.per_page));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return apiFetch(`/api/admin/reports${suffix}`).then((r) =>
        jsonOrThrow(r, "Failed to load reports"),
    );
}

export function updateReportStatus(
    reportId: number,
    status: ReportStatus,
): Promise<PaperReport> {
    return apiFetch(`/api/admin/reports/${reportId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status }),
    }).then((r) => jsonOrThrow(r, "Failed to update report"));
}
