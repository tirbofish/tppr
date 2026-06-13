import type { Paper } from "@/types/tppr-paper";
import { paperStore } from "./paper";

let syncTimeout: ReturnType<typeof setTimeout> | null = null;
let pendingPaper: Paper | null = null;

async function pushToServer(paper: Paper): Promise<void> {
    const res = await fetch(`/api/papers/${paper.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(paper),
    });

    if (res.status === 404) {
        const createRes = await fetch("/api/papers", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify(paper),
        });
        if (!createRes.ok) throw new Error(`Create failed: ${createRes.status}`);
    } else if (!res.ok) {
        throw new Error(`Sync failed: ${res.status}`);
    }
}

export async function syncPaper(paper: Paper): Promise<void> {
    await paperStore.savePaper(paper);
    pendingPaper = paper;

    if (syncTimeout) clearTimeout(syncTimeout);
    syncTimeout = setTimeout(async () => {
        if (!pendingPaper) return;
        try {
            await pushToServer(pendingPaper);
        } catch (e) {
            console.warn(e);
        }
        pendingPaper = null;
    }, 1500); // debounce of 1500ms
}

export async function flushSync(): Promise<void> {
    if (syncTimeout) {
        clearTimeout(syncTimeout);
        syncTimeout = null;
    }
    if (pendingPaper) {
        await pushToServer(pendingPaper);
        pendingPaper = null;
    }
}

export async function publishPaper(paperId: string): Promise<void> {
    const paper = await paperStore.getPaper(paperId);
    if (!paper) throw new Error("Paper not found locally");

    const res = await fetch(`/api/papers/${paperId}/publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(paper),
    });
    if (!res.ok) throw new Error(`Publish failed: ${res.status}`);
}

export async function unpublishPaper(paperId: string): Promise<void> {
    const res = await fetch(`/api/papers/${paperId}/publish`, {
        method: "DELETE",
        credentials: "include",
    });
    if (!res.ok) throw new Error(`Unpublish failed: ${res.status}`);
}