import { useState } from "react";
import { Button } from "@/components/ui/button";
import { PanelRightClose, PanelRightOpen, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/api/auth";

interface AdminSidebarProps {
    paperId: string;
    isTakenDown?: boolean;
}

export function AdminSidebar({ paperId, isTakenDown }: AdminSidebarProps) {
    const { user } = useAuth();
    const [open, setOpen] = useState(true);
    const [loading, setLoading] = useState(false);

    if (!user?.admin) return null;

    async function handleTakedown() {
        if (
            !confirm(
                "This will take down this paper and ALL its remixes. Continue?",
            )
        ) return;

        setLoading(true);
        try {
            const res = await fetch(`/api/admin/takedown/${paperId}`, {
                method: "POST",
                credentials: "include",
            });
            const data = await res.json();
            if (!res.ok) {
                toast.error(data.message || "Takedown failed");
                return;
            }
            toast.success(data.message);
            window.location.reload();
        } catch {
            toast.error("An error occurred during takedown");
        } finally {
            setLoading(false);
        }
    }

    async function handleRevert() {
        if (!confirm("Restore this paper and all its remixes?")) return;

        setLoading(true);
        try {
            const res = await fetch(`/api/admin/takedown/${paperId}`, {
                method: "DELETE",
                credentials: "include",
            });
            const data = await res.json();
            if (!res.ok) {
                toast.error(data.message || "Revert failed");
                return;
            }
            toast.success(data.message);
            window.location.reload();
        } catch {
            toast.error("An error occurred during revert");
        } finally {
            setLoading(false);
        }
    }

    if (!open) {
        return (
            <Button
                variant="outline"
                size="icon"
                className="fixed right-4 bottom-4 z-50 size-10 rounded-full border-primary shadow-lg"
                onClick={() => setOpen(true)}
            >
                <PanelRightOpen className="size-4 text-primary" />
            </Button>
        );
    }

    return (
        <aside className="fixed right-4 bottom-4 z-50 w-64 rounded-lg border bg-background shadow-lg">
            <div className="flex items-center justify-between border-b px-4 py-3">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-primary">
                    <ShieldAlert className="size-4" />
                    Admin Actions
                </h2>
                <Button
                    variant="ghost"
                    size="icon"
                    className="size-6"
                    onClick={() => setOpen(false)}
                >
                    <PanelRightClose className="size-3.5" />
                </Button>
            </div>
            <div className="p-4 space-y-2">
                {isTakenDown
                    ? (
                        <>
                            <Button
                                variant="outline"
                                size="sm"
                                className="w-full"
                                onClick={handleRevert}
                                disabled={loading}
                            >
                                {loading ? "Restoring..." : "Revert takedown"}
                            </Button>
                            <p className="text-xs text-muted-foreground">
                                Restores this paper and all remixes to private.
                            </p>
                        </>
                    )
                    : (
                        <>
                            <Button
                                variant="destructive"
                                size="sm"
                                className="w-full"
                                onClick={handleTakedown}
                                disabled={loading}
                            >
                                {loading ? "Taking down..." : "Take down paper"}
                            </Button>
                            <p className="text-xs text-muted-foreground">
                                Removes this paper and all remixes from public
                                access.
                            </p>
                        </>
                    )}
            </div>
        </aside>
    );
}
