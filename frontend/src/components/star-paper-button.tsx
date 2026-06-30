import { useEffect, useState, type MouseEvent } from "react";
import { Star } from "lucide-react";
import { toast } from "sonner";

import { getStarStatus, setPaperStarred } from "@/api/stars";
import { useAuth } from "@/api/auth";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface StarPaperButtonProps {
    paperId: string;
    initialStarred?: boolean;
    className?: string;
    onChange?: (starred: boolean) => void;
}

export function StarPaperButton({
    paperId,
    initialStarred = false,
    className,
    onChange,
}: StarPaperButtonProps) {
    const { user } = useAuth();
    const [starred, setStarred] = useState(initialStarred);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        let cancelled = false;
        if (!user) {
            setStarred(false);
            return;
        }
        setStarred(initialStarred);

        getStarStatus(paperId)
            .then((next) => {
                if (!cancelled) setStarred(next);
            })
            .catch(() => {
                if (!cancelled) setStarred(false);
            });

        return () => {
            cancelled = true;
        };
    }, [initialStarred, paperId, user]);

    async function toggle(e: MouseEvent<HTMLButtonElement>) {
        e.preventDefault();
        e.stopPropagation();

        if (!user) {
            toast.error("Log in to star papers");
            return;
        }

        const next = !starred;
        setLoading(true);
        setStarred(next);
        try {
            const saved = await setPaperStarred(paperId, next);
            setStarred(saved);
            onChange?.(saved);
        } catch (error) {
            setStarred(!next);
            toast.error(
                error instanceof Error ? error.message : "Failed to update star",
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <Button
            variant="ghost"
            size="icon"
            className={cn("size-8", starred && "text-primary", className)}
            onClick={toggle}
            disabled={loading}
            aria-pressed={starred}
            aria-label={starred ? "Unstar paper" : "Star paper"}
        >
            <Star className={cn(starred && "fill-current")} />
        </Button>
    );
}
