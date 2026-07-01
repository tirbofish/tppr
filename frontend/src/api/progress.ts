import { apiFetch } from "./client";

export interface AttemptPaperMeta {
    title: string | null;
    subject: string | null;
    visibility: string;
    question_count: number;
    total_marks: number;
    duration_minutes: number | null;
    available: boolean;
}

export interface QuestionTime {
    question_id: string;
    part_path?: string | null;
    seconds: number;
    revealed_answer: boolean;
    reveal_count: number;
    views: number;
}

export interface Attempt {
    id: string;
    paper_id: string;
    paper: AttemptPaperMeta | null;
    started_at: string | null;
    last_active_at: string | null;
    completed_at: string | null;
    elapsed_seconds: number;
    completed: boolean;
    questions_seen: number;
    questions_answered: number;
    reveal_count: number;
    max_slide: number;
}

export interface AttemptDetail extends Attempt {
    question_times: QuestionTime[];
}

export interface AttemptListResponse {
    attempts: Attempt[];
    total: number;
    page: number;
    per_page: number;
}

export interface PaperFocusStats {
    paper_id: string;
    attempt_count: number;
    completed_attempt_count: number;
    completion_rate: number;
    average_completed_seconds: number | null;
    median_completed_seconds: number | null;
    average_reveal_count: number | null;
    average_questions_seen: number | null;
    user_best_completed_seconds: number | null;
    user_average_reveal_count: number | null;
    user_average_questions_seen: number | null;
}

async function jsonOrThrow<T>(res: Response, fallback: string): Promise<T> {
    if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.message ?? fallback);
    }
    return res.json() as Promise<T>;
}

export function startAttempt(paperId: string): Promise<Attempt> {
    return apiFetch("/api/attempts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paper_id: paperId }),
    }).then((r) => jsonOrThrow(r, "Failed to start attempt"));
}

export function getAttempt(id: string): Promise<AttemptDetail> {
    return apiFetch(`/api/attempts/${id}`).then((r) =>
        jsonOrThrow(r, "Failed to load attempt"),
    );
}

export function listAttempts(params?: {
    page?: number;
    per_page?: number;
    paper_id?: string;
    completed?: boolean;
}): Promise<AttemptListResponse> {
    const qs = new URLSearchParams();
    if (params?.page) qs.set("page", String(params.page));
    if (params?.per_page) qs.set("per_page", String(params.per_page));
    if (params?.paper_id) qs.set("paper_id", params.paper_id);
    if (typeof params?.completed === "boolean") {
        qs.set("completed", String(params.completed));
    }
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return apiFetch(`/api/attempts${suffix}`).then((r) =>
        jsonOrThrow(r, "Failed to load attempts"),
    );
}

export function updateAttempt(
    id: string,
    patch: Partial<{
        elapsed_seconds: number;
        questions_seen: number;
        questions_answered: number;
        reveal_count: number;
        max_slide: number;
    }>,
): Promise<Attempt> {
    return apiFetch(`/api/attempts/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
    }).then((r) => jsonOrThrow(r, "Failed to update attempt"));
}

export function recordQuestionTime(
    id: string,
    data: {
        question_id: string;
        part_path?: number[];
        seconds: number;
        revealed_answer: boolean;
        reveal_count: number;
        views: number;
    },
): Promise<QuestionTime> {
    return apiFetch(`/api/attempts/${id}/questions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    }).then((r) => jsonOrThrow(r, "Failed to record question time"));
}

export function completeAttempt(
    id: string,
    data: {
        elapsed_seconds: number;
        questions_seen?: number;
        questions_answered?: number;
        reveal_count?: number;
        max_slide?: number;
        question_times?: Array<{
            question_id: string;
            part_path?: number[];
            seconds: number;
            revealed_answer: boolean;
            reveal_count: number;
            views: number;
        }>;
    },
): Promise<AttemptDetail> {
    return apiFetch(`/api/attempts/${id}/complete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    }).then((r) => jsonOrThrow(r, "Failed to complete attempt"));
}

export function deleteAttempt(id: string): Promise<void> {
    return apiFetch(`/api/attempts/${id}`, { method: "DELETE" }).then((r) => {
        if (!r.ok) throw new Error("Failed to delete attempt");
    });
}

export function getPaperFocusStats(paperId: string): Promise<PaperFocusStats> {
    return apiFetch(`/api/papers/${paperId}/focus-stats`).then((r) =>
        jsonOrThrow(r, "Failed to load focus stats")
    );
}
