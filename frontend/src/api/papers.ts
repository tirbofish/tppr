import type { Paper, PaperMeta } from "@/types/tppr-paper";
import { apiFetch } from "./client";

interface PapersListResponse {
    papers: PaperMeta[];
    total: number;
    page: number;
    per_page: number;
}

export async function getPapers(): Promise<PaperMeta[]> {
    const res = await apiFetch("/api/papers", { credentials: "include" });
    if (!res.ok) throw new Error(`Failed to fetch papers: ${res.status}`);
    const data: PapersListResponse = await res.json();
    return data.papers;
}

export async function getPaper(id: string): Promise<Paper> {
    const res = await apiFetch(`/api/papers/${id}`, { credentials: "include" });
    if (!res.ok) throw new Error(`Failed to fetch paper: ${res.status}`);
    return res.json();
}

export async function deletePaper(id: string): Promise<void> {
    const res = await apiFetch(`/api/papers/${id}`, {
        method: "DELETE",
    });
    if (!res.ok) throw new Error(`Failed to delete paper: ${res.status}`);
}

export async function remixQuestionIntoPaper(
    paperId: string,
    questionId: string,
    targetPaperId: string,
): Promise<Paper> {
    const res = await apiFetch(`/api/papers/${paperId}/questions/${questionId}/remix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_paper_id: targetPaperId }),
    });
    if (!res.ok) throw new Error(`Failed to remix question: ${res.status}`);
    return res.json();
}

export async function updatePaperVerification(
    paperId: string,
    data: {
        verified: boolean;
        source_name?: string;
        source_url?: string;
    },
): Promise<PaperMeta> {
    const res = await apiFetch(`/api/admin/papers/${paperId}/verification`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.message ?? "Failed to update verification");
    }
    return res.json();
}
