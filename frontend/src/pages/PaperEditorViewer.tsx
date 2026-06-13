import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import NavBar from "@/components/navbar";
import { PaperCard } from "@/components/paper-card";
import { deletePaper, getPapers } from "@/api/papers";
import { paperStore } from "@/lib/paper";
import { FileQuestion } from "lucide-react";
import { toast } from "sonner";
import type { Paper, PaperMeta } from "@/types/tppr-paper";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/api/auth";
import { syncService } from "@/lib/cloud";

type ListedPaper = PaperMeta & { isLocal?: boolean };

function isValidTpprPaper(data: unknown): data is Paper {
    if (typeof data !== "object" || data === null) return false;
    const d = data as Record<string, unknown>;
    return (
        typeof d.id === "string" &&
        typeof d.title === "string" &&
        typeof d.subject === "string" &&
        typeof d.visibility === "string" &&
        ["private", "public"].includes(d.visibility as string) &&
        typeof d.question_count === "number" &&
        typeof d.total_marks === "number" &&
        typeof d.created_at === "string" &&
        typeof d.updated_at === "string" &&
        Array.isArray(d.questions)
    );
}

export function PapersViewer() {
    const [papers, setPapers] = useState<ListedPaper[]>([]);
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [dragging, setDragging] = useState(false);
    const { user, loading: authLoading } = useAuth();

    useEffect(() => {
        if (!authLoading && !user) {
            navigate(`/login?redirect=${encodeURIComponent("/papers")}`);
        }
    }, [user, authLoading, navigate]);

    useEffect(() => {
        if (authLoading || !user) return;
        async function load() {
            try {
                const [remote, local] = await Promise.all([
                    getPapers().catch(() => [] as PaperMeta[]),
                    paperStore.listPapers().catch(() => []),
                ]);

                const merged = new Map<string, ListedPaper>();
                for (const p of remote) merged.set(p.id, p);
                for (const p of local) {
                    merged.set(p.id, { ...p, isLocal: true });
                }

                const userId = String(user?.user_id);
                setPapers(
                    [...merged.values()]
                        .filter((p) => p.author_id === userId)
                        .sort((a, b) =>
                            b.updated_at.localeCompare(a.updated_at)
                        ),
                );
            } finally {
                setLoading(false);
            }
        }
        load();
    }, [user, authLoading]);

    const handleDrop = useCallback(
        async (e: React.DragEvent) => {
            e.preventDefault();
            setDragging(false);

            if (!user) return;

            const file = e.dataTransfer.files[0];
            if (!file || !file.name.endsWith(".json")) {
                toast.error("Please drop a .json file.");
                return;
            }

            try {
                const text = await file.text();
                const data = JSON.parse(text);

                if (!isValidTpprPaper(data)) {
                    toast.error(
                        "Invalid file — does not match the TPPR paper format.",
                    );
                    return;
                }

                const alreadyExists = papers.some(
                    (p) =>
                        p.title === data.title &&
                        p.subject === data.subject,
                );
                if (alreadyExists) {
                    toast.error(
                        `A paper called "${data.title}" already exists.`,
                    );
                    return;
                }

                const now = new Date().toISOString();
                const imported: Paper = {
                    ...data,
                    id: crypto.randomUUID(),
                    author_id: String(user.user_id),
                    visibility: "private",
                    created_at: now,
                    updated_at: now,
                    questions: data.questions.map((q) => ({
                        ...q,
                        author_id: String(user.user_id),
                        paper_id: "",
                    })),
                };
                imported.questions = imported.questions.map((q) => ({
                    ...q,
                    paper_id: imported.id,
                }));

                await syncService.sync(imported);

                setPapers((prev) => [
                    { ...imported, isLocal: true },
                    ...prev,
                ]);
                toast.success(`Imported "${imported.title}" successfully!`);
            } catch {
                toast.error(
                    "Failed to read file — make sure it's valid JSON.",
                );
            }
        },
        [user],
    );

    async function handleDelete(paper: ListedPaper) {
        try {
            await paperStore.deletePaper(paper.id).catch(() => {});
            await deletePaper(paper.id).catch(() => {});

            setPapers((prev) => prev.filter((p) => p.id !== paper.id));
            toast.success("Paper deleted");
        } catch {
            toast.error("Failed to delete paper");
        }
    }

    return (
        <>
            <NavBar />
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

                {dragging && (
                    <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center bg-background/60 backdrop-blur-sm">
                        <div className="rounded-xl border-2 border-dashed border-primary p-12 text-center">
                            <p className="text-lg font-medium">
                                Drop your tppr json to import it
                            </p>
                        </div>
                    </div>
                )}

                {loading
                    ? (
                        <div className="flex flex-col items-center gap-2 py-24 text-muted-foreground">
                            <Spinner className="size-8" />
                            <p>Loading…</p>
                        </div>
                    )
                    : papers.length === 0
                    ? (
                        <div className="flex flex-col items-center gap-2 py-24 text-muted-foreground">
                            <FileQuestion className="size-10" />
                            <p>No papers yet. Create one from the navbar!</p>
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
                                        setPapers((prev) =>
                                            prev.map((p) =>
                                                p.id === updated.id
                                                    ? { ...p, ...updated }
                                                    : p
                                            )
                                        );
                                        paperStore.savePaper(updated as any);
                                    }}
                                    onDelete={() => handleDelete(paper)}
                                />
                            ))}
                        </div>
                    )}
            </main>
        </>
    );
}
