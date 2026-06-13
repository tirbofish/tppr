import { useEffect, useState } from "react";
import { syncService, type SyncStatus } from "@/lib/cloud";

export function useOnline() {
    const [online, setOnline] = useState(() => syncService.getStatus() !== "offline");
    useEffect(() => syncService.subscribe((s) => setOnline(s !== "offline")), []);
    return online;
}

export function useSyncStatus() {
    const [status, setStatus] = useState<SyncStatus>(() => syncService.getStatus());
    useEffect(() => syncService.subscribe(setStatus), []);
    return status;
}