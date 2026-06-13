import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import NavBar from "@/components/navbar";
import { PaperCard } from "@/components/paper-card";
import { deletePaper, getPapers } from "@/api/papers";
import { paperStore } from "@/lib/paper";
import { FileQuestion } from "lucide-react";
import { toast } from "sonner";
import type { PaperMeta } from "@/types/tppr-paper";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/api/auth";

type ListedPaper = PaperMeta & { isLocal?: boolean };

export function PapersViewer() {
    const [papers, setPapers] = useState<ListedPaper[]>([]);
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const { user, loading: authLoading } = useAuth();

    useEffect(() => {
        if (!authLoading && !user) {
            navigate("/login");
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

    async function handleDelete(paper: ListedPaper) {
        try {
            if (paper.isLocal) {
                await paperStore.deletePaper(paper.id);
            } else {
                await deletePaper(paper.id);
            }
            setPapers((prev) => prev.filter((p) => p.id !== paper.id));
            toast.success("Paper deleted");
        } catch {
            toast.error("Failed to delete paper");
        }
    }

    return (
        <>
            <NavBar />
            <main className="mx-auto w-full max-w-6xl px-6 py-8">
                <h1 className="mb-6 text-2xl font-bold">My Papers</h1>

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
