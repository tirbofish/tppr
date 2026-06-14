import type { PaperMeta } from "@/types/tppr-paper";

interface AdminPapersResponse {
    papers: PaperMeta[];
    total: number;
    page: number;
    per_page: number;
}

export interface AdminPaperFilters {
    q?: string;
    page?: number;
    per_page?: number;
}

export async function getTakenDownPapers(
    filters: AdminPaperFilters = {},
): Promise<AdminPapersResponse> {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) {
        if (value !== undefined && value !== "") params.set(key, String(value));
    }

    const res = await fetch(`/api/admin/takedowns?${params}`, {
        credentials: "include",
    });
    if (!res.ok) throw new Error(`Failed to fetch takedowns: ${res.status}`);
    return res.json();
}

export async function restoreTakenDownPaper(paperId: string): Promise<void> {
    const res = await fetch(`/api/admin/takedown/${paperId}`, {
        method: "DELETE",
        credentials: "include",
    });
    if (!res.ok) throw new Error(`Failed to restore takedown: ${res.status}`);
}
