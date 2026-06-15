import type { Paper, PaperMeta } from "@/types/tppr-paper";

interface PapersListResponse {
    papers: PaperMeta[];
    total: number;
    page: number;
    per_page: number;
}

export async function getPapers(): Promise<PaperMeta[]> {
    const res = await fetch("/api/papers", { credentials: "include" });
    if (!res.ok) throw new Error(`Failed to fetch papers: ${res.status}`);
    const data: PapersListResponse = await res.json();
    return data.papers;
}

export async function getPaper(id: string): Promise<Paper> {
    const res = await fetch(`/api/papers/${id}`, { credentials: "include" });
    if (!res.ok) throw new Error(`Failed to fetch paper: ${res.status}`);
    return res.json();
}

export async function deletePaper(id: string): Promise<void> {
    const res = await fetch(`/api/papers/${id}`, {
        method: "DELETE",
        credentials: "include",
    });
    if (!res.ok) throw new Error(`Failed to delete paper: ${res.status}`);
}

export async function remixQuestionIntoPaper(
    paperId: string,
    questionId: string,
    targetPaperId: string,
): Promise<Paper> {
    const res = await fetch(`/api/papers/${paperId}/questions/${questionId}/remix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ target_paper_id: targetPaperId }),
    });
    if (!res.ok) throw new Error(`Failed to remix question: ${res.status}`);
    return res.json();
}
