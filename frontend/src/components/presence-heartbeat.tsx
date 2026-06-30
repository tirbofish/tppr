import { useEffect } from "react";

import { useAuth } from "@/api/auth";
import { heartbeatPresence } from "@/api/social";

const HEARTBEAT_MS = 30000;

export function PresenceHeartbeat() {
    const { user } = useAuth();

    useEffect(() => {
        if (!user) return;

        let cancelled = false;
        const tick = () => {
            heartbeatPresence().catch(() => {
                // Presence is best-effort and should never interrupt studying.
            });
        };

        tick();
        const timer = window.setInterval(() => {
            if (!cancelled) tick();
        }, HEARTBEAT_MS);

        return () => {
            cancelled = true;
            window.clearInterval(timer);
        };
    }, [user]);

    return null;
}
