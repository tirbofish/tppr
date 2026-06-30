import { apiFetch } from "./client";

export interface PublicUser {
    user_id: string;
    username: string;
    avatar_url?: string | null;
}

export interface FriendRequest extends PublicUser {
    id: number;
    created_at?: string;
}

export interface Friend extends PublicUser {
    since?: string | null;
}

export interface LeaderboardEntry extends PublicUser {
    rank: number;
    paper_count: number;
    public_paper_count: number;
    question_count: number;
    total_marks: number;
    remixes_received: number;
}

async function readError(res: Response, fallback: string): Promise<Error> {
    const body = await res.json().catch(() => null);
    return new Error(body?.message ?? fallback);
}

async function jsonOrThrow<T>(res: Response, fallback: string): Promise<T> {
    if (!res.ok) throw await readError(res, fallback);
    return res.json() as Promise<T>;
}

export async function sendFriendRequest(
    username: string,
): Promise<{ message: string }> {
    const res = await apiFetch("/api/friends/requests", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username }),
    });
    return jsonOrThrow(res, "Failed to send friend request");
}

export async function listIncomingRequests(): Promise<{ requests: FriendRequest[] }> {
    const res = await apiFetch("/api/friends/requests/incoming");
    return jsonOrThrow(res, "Failed to load friend requests");
}

export async function listOutgoingRequests(): Promise<{ requests: FriendRequest[] }> {
    const res = await apiFetch("/api/friends/requests/outgoing");
    return jsonOrThrow(res, "Failed to load sent requests");
}

export async function acceptFriendRequest(id: number): Promise<{ message: string }> {
    const res = await apiFetch(`/api/friends/requests/${id}/accept`, {
        method: "POST",
    });
    return jsonOrThrow(res, "Failed to accept request");
}

export async function declineFriendRequest(id: number): Promise<{ message: string }> {
    const res = await apiFetch(`/api/friends/requests/${id}/decline`, {
        method: "POST",
    });
    return jsonOrThrow(res, "Failed to decline request");
}

export async function cancelFriendRequest(id: number): Promise<{ message: string }> {
    const res = await apiFetch(`/api/friends/requests/${id}`, {
        method: "DELETE",
    });
    return jsonOrThrow(res, "Failed to cancel request");
}

export async function listFriends(): Promise<{ friends: Friend[] }> {
    const res = await apiFetch("/api/friends");
    return jsonOrThrow(res, "Failed to load friends");
}

export async function removeFriend(userId: string): Promise<{ message: string }> {
    const res = await apiFetch(`/api/friends/${userId}`, { method: "DELETE" });
    return jsonOrThrow(res, "Failed to remove friend");
}

export async function getLeaderboard(
    scope?: "friends",
): Promise<{ entries: LeaderboardEntry[] }> {
    const qs = scope ? `?scope=${scope}` : "";
    const res = await apiFetch(`/api/leaderboard${qs}`);
    return jsonOrThrow(res, "Failed to load leaderboard");
}