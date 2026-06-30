import { apiFetch } from "./client";
import type { Attempt } from "./progress";
import type { LeaderboardEntry } from "./social";

export interface MyStats {
    user_id: string;
    username: string;
    avatar_url?: string | null;
    joined_at?: string | null;
    attempts_count: number;
    papers_attempted: number;
    papers_completed: number;
    questions_answered: number;
    total_study_seconds: number;
    reveal_count: number;
    current_streak: number;
    longest_streak: number;
    last_active_at?: string | null;
    recent_attempts?: Attempt[];
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