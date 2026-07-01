import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import NavBar from "@/components/navbar";
import { PaperCard } from "@/components/paper-card";
import { deletePaper, getPapers } from "@/api/papers";
import { paperStore } from "@/lib/paper";
import { importPaperFromJsonFile } from "@/lib/paper-import";
import { FileQuestion } from "lucide-react";
import { toast } from "sonner";
import type { PaperMeta } from "@/types/tppr-paper";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/api/auth";
import { loginPath } from "@/lib/routes";

type ListedPaper = PaperMeta & { isLocal?: boolean };

export function PapersViewer() {
    const [papers, setPapers] = useState<ListedPaper[]>([]);
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [dragging, setDragging] = useState(false);
    const importInputRef = useRef<HTMLInputElement>(null);
    const { user, loading: authLoading } = useAuth();
    const [importing, setImporting] = useState(false);
    const [deletingIds, setDeletingIds] = useState<Set<string>>(
        () => new Set(),
    );

    useEffect(() => {
        if (!authLoading && !user) {
            navigate(loginPath("/papers"));
        }
    }, [user, authLoading, navigate]);

    useEffect(() => {
        if (authLoading || !user) return;
        const currentUser = user;

        async function load() {
            try {
                const [remote, local] = await Promise.all([
                    getPapers().catch(() => [] as PaperMeta[]),
                    paperStore.listPapers().catch(() => []),
                ]);

                const merged = new Map<string, ListedPaper>();
                for (const paper of remote) merged.set(paper.id, paper);
                for (const paper of local) {
                    merged.set(paper.id, { ...paper, isLocal: true });
                }

                const userId = String(currentUser.user_id);
                setPapers(
                    [...merged.values()]
                        .filter((paper) => paper.author_id === userId)
                        .sort((a, b) =>
                            b.updated_at.localeCompare(a.updated_at)
                        ),
                );
            } finally {
                setLoading(false);
            }
        }

        void load();
    }, [user, authLoading]);

    const handleImportFile = useCallback(async (file: File | undefined) => {
        if (!user || !file) return;

        setImporting(true);
        try {
            const imported = await importPaperFromJsonFile(
                file,
                String(user.user_id),
                papers,
            );

            setPapers((prev) => [
                { ...imported, isLocal: true },
                ...prev,
            ]);
            toast.success(`Imported "${imported.title}" successfully!`);
        } catch (error) {
            console.warn(error);
            toast.error(
                error instanceof Error
                    ? error.message
                    : "Failed to import paper. Please try again.",
            );
        } finally {
            setImporting(false);
        }
    }, [papers, user]);

    useEffect(() => {
        function handleKeyDown(e: KeyboardEvent) {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "i") {
                e.preventDefault();
                importInputRef.current?.click();
            }
        }

        document.addEventListener("keydown", handleKeyDown);
        return () => document.removeEventListener("keydown", handleKeyDown);
    }, []);

    const handleDrop = useCallback(
        async (e: React.DragEvent) => {
            e.preventDefault();
            setDragging(false);
            await handleImportFile(e.dataTransfer.files[0]);
        },
        [handleImportFile],
    );

    async function handleDelete(paper: ListedPaper) {
        setDeletingIds((prev) => new Set(prev).add(paper.id));
        try {
            const [localDelete, remoteDelete] = await Promise.allSettled([
                paperStore.deletePaper(paper.id),
                deletePaper(paper.id),
            ]);
            if (
                localDelete.status === "rejected" &&
                remoteDelete.status === "rejected"
            ) {
                throw new Error("Both local and remote deletion failed");
            }

            setPapers((prev) => prev.filter((p) => p.id !== paper.id));
            toast.success("Paper deleted");
        } catch {
            toast.error("Failed to delete paper");
        } finally {
            setDeletingIds((prev) => {
                const next = new Set(prev);
                next.delete(paper.id);
                return next;
            });
        }
    }

    async function handleEdit(updated: PaperMeta) {
        setPapers((prev) =>
            prev.map((paper) =>
                paper.id === updated.id ? { ...paper, ...updated } : paper
            )
        );

        const stored = await paperStore.getPaper(updated.id).catch(() => undefined);
        if (stored) {
            await paperStore.savePaper({ ...stored, ...updated });
        }
    }

    return (
        <>
            <NavBar />
            <input
                ref={importInputRef}
                type="file"
                accept=".json,application/json"
                className="hidden"
                onChange={(e) => {
                    void handleImportFile(e.target.files?.[0]);
                    e.target.value = "";
                }}
            />
            <main
                className="mx-auto w-full max-w-6xl px-6 py-8"
                onDragOver={(e) => {
                    e.preventDefault();
                    setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
            >
                <h1 className="mb-6 text-2xl font-bold">My Papers</h1>

                {importing && (
                    <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-background/60 backdrop-blur-sm">
                        <div className="flex flex-col items-center gap-2">
                            <Spinner className="size-8" />
                            <p className="text-sm font-medium">Importing...</p>
                        </div>
                    </div>
                )}

                {dragging && (
                    <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-background/60 backdrop-blur-sm">
                        <div className="rounded-xl border-2 border-dashed border-primary p-12 text-center">
                            <p className="text-lg font-medium">
                                Drop your TPPR JSON to import it
                            </p>
                        </div>
                    </div>
                )}

                {loading
                    ? (
                        <div className="flex flex-col items-center gap-2 py-24 text-muted-foreground">
                            <Spinner className="size-8" />
                            <p>Loading...</p>
                        </div>
                    )
                    : papers.length === 0
                    ? (
                        <div className="flex flex-col items-center gap-2 py-24 text-muted-foreground">
                            <FileQuestion className="size-10" />
                            <p>No papers yet. Create one from the navbar.</p>
                        </div>
                    )
                    : (
                        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                            {papers.map((paper) => (
                                <PaperCard
                                    key={paper.id}
                                    paper={paper}
                                    onOpen={() =>
                                        navigate(`/papers/${paper.id}`)}
                                    onEdit={(updated) => {
                                        void handleEdit(updated);
                                    }}
                                    onDelete={() => handleDelete(paper)}
                                    deleting={deletingIds.has(paper.id)}
                                />
                            ))}
                        </div>
                    )}
            </main>
        </>
    );
}
