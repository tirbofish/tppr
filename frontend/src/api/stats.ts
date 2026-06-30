import { apiFetch } from "./client";
import type { LeaderboardEntry } from "./social";

export interface MyStats {
    user_id: string;
    username: string;
    avatar_url?: string | null;
    joined_at?: string | null;
    paper_count: number;
    public_paper_count: number;
    question_count: number;
    total_marks: number;
    remixes_received: number;
}

export type AllUserStats = LeaderboardEntry;

async function jsonOrThrow<T>(res: Response, fallback: string): Promise<T> {
    if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.message ?? fallback);
    }
    return res.json() as Promise<T>;
}

export async function getMyStats(): Promise<MyStats> {
    const res = await apiFetch("/api/stats/me");
    return jsonOrThrow(res, "Failed to load your stats");
}

export async function getAllUserStats(): Promise<{ users: AllUserStats[] }> {
    const res = await apiFetch("/api/stats/users");
    return jsonOrThrow(res, "Failed to load user stats");
}