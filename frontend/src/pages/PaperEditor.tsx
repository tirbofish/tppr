import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
    createQuestion,
    paperStore,
    withRecalculatedTotals,
} from "@/lib/paper";
import type { Paper, Question as QuestionData } from "@/types/tppr-paper";
import NavBar from "@/components/navbar";
import { Question } from "@/components/question";
import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { ArrowLeft, Plus, Shell } from "lucide-react";
import { QuestionEditor } from "@/components/question-editor";
import { EditableNumber } from "@/components/editable-number";
import { toast } from "sonner";
import { useAuth } from "@/api/auth";
import Unauthorized from "./Unauthorised";
import { PaperSettings } from "@/components/paper-settings";
import { syncService } from "@/lib/cloud";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "@/components/ui/tooltip";

export default function PaperEditor() {
    const { id } = useParams<{ id: string }>();
    const [paper, setPaper] = useState<Paper | null>(null);
    const [loading, setLoading] = useState(true);

    const [selectedId, setSelectedId] = useState<string | null>(null);
    const selected = paper?.questions.find((q) => q.id === selectedId) ?? null;

    const navigate = useNavigate();
    const [syncing, setSyncing] = useState(false);

    const { user, loading: authLoading } = useAuth();

    const [authorName, setAuthorName] = useState<string | null>(null);
    const isOwner = !!user && String(user.user_id) === paper?.author_id;

    const [remixSource, setRemixSource] = useState<
        { title: string; author: string } | null
    >(null);

    useEffect(() => {
        if (!paper?.remixed) return;
        fetch(`/api/papers/${paper.remixed}`, { credentials: "include" })
            .then((res) => res.ok ? res.json() : Promise.reject())
            .then(async (data) => {
                const authorRes = await fetch(
                    `/api/whotf?user_id=${data.author_id}`,
                );
                const authorData = await authorRes.json();
                setRemixSource({
                    title: data.title,
                    author: authorData.username ?? "Unknown",
                });
            })
            .catch(() => setRemixSource(null));
    }, [paper?.remixed]);

    useEffect(() => {
        if (!paper) return;
        fetch(`/api/whotf?user_id=${paper.author_id}`)
            .then((res) => res.ok ? res.json() : Promise.reject())
            .then((data) => setAuthorName(data.username))
            .catch(() => setAuthorName("Unknown"));
    }, [paper?.author_id]);

    useEffect(() => {
        if (!id) return;
        async function load() {
            // local first
            const local = await paperStore.getPaper(id!);
            if (local) {
                setPaper(local);
                setLoading(false);
                return;
            }

            // server fallback
            try {
                const res = await fetch(`/api/papers/${id}`, {
                    credentials: "include",
                });
                if (!res.ok) {
                    setPaper(null);
                    return;
                }
                const data = await res.json();
                setPaper(data);
                // cache locally for future access
                await paperStore.savePaper(data);
            } catch {
                setPaper(null);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, [id]);

    async function handleRemix() {
        if (!paper) return;
        const res = await fetch(`/api/papers/${paper.id}/remix`, {
            method: "POST",
            credentials: "include",
        });
        if (!res.ok) {
            toast.error("Failed to remix paper");
            return;
        }
        const remixed = await res.json();
        await paperStore.savePaper(remixed);
        toast.success("Remixed!");
        navigate(`/papers/${remixed.id}`);
    }

    async function updatePaper(next: Paper) {
        const stamped = withRecalculatedTotals(next);
        setPaper(stamped);
        await syncService.sync(stamped);
    }

    async function handleBack() {
        if (paper && isOwner) {
            setSyncing(true);
            try {
                await syncService.flush();
            } catch {
                toast.error("Sync failed — changes are saved locally.");
            } finally {
                setSyncing(false);
            }
        }
        navigate(-1);
    }

    function addQuestion() {
        if (!paper) return;
        updatePaper({
            ...paper,
            questions: [...paper.questions, createQuestion(paper)],
        });
    }

    function handleQuestionChange(updated: QuestionData) {
        if (!paper) return;
        updatePaper({
            ...paper,
            questions: paper.questions.map((q) =>
                q.id === updated.id ? updated : q
            ),
        });
    }

    function handleQuestionDelete(qid: string) {
        if (!paper) return;
        updatePaper({
            ...paper,
            questions: paper.questions
                .filter((q) => q.id !== qid)
                .map((q, i) => ({ ...q, number: i + 1 })),
        });
    }

    function handleNumberChange(qid: string, newNumber: number) {
        if (!paper) return;
        const from = paper.questions.findIndex((q) => q.id === qid);
        if (from === -1) return;
        const to = Math.min(
            Math.max(newNumber - 1, 0),
            paper.questions.length - 1,
        );

        const questions = [...paper.questions];
        const [moved] = questions.splice(from, 1);
        questions.splice(to, 0, moved);

        updatePaper({
            ...paper,
            questions: questions.map((q, i) => ({ ...q, number: i + 1 })),
        });
    }

    if (loading || authLoading) {
        return (
            <>
                <NavBar />
                <p className="py-24 text-center text-muted-foreground">
                    Loading…
                </p>
            </>
        );
    }

    if (!paper) {
        return (
            <>
                <NavBar />
                <p className="py-24 text-center text-muted-foreground">
                    Paper not found.
                </p>
            </>
        );
    }

    if (
        paper.visibility === "private" &&
        (!user || String(user.user_id) !== paper.author_id)
    ) {
        return <Unauthorized />;
    }

    return (
        <>
            <NavBar />
            <main className="mx-auto w-full max-w-3xl px-6 py-8">
                <div className="mb-6 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={handleBack}
                            disabled={syncing}
                            aria-label="Back to papers"
                        >
                            <ArrowLeft />
                        </Button>
                        <div>
                            <h1 className="text-2xl font-bold">
                                {paper.title}
                            </h1>
                            {paper.remixed && (
                                <Link
                                    to={`/papers/${paper.remixed}`}
                                    className="flex items-center gap-1 text-xs text-muted-foreground hover:underline"
                                >
                                    <Shell className="size-3" /> Remixed from "
                                    {remixSource
                                        ? `${remixSource.author}/${remixSource.title}`
                                        : "…"}
                                    "
                                </Link>
                            )}
                        </div>
                        {isOwner && (
                            <PaperSettings
                                paper={paper}
                                onSave={(meta) =>
                                    updatePaper({ ...paper, ...meta })}
                            />
                        )}

                        {/** Remix button */}
                        {!isOwner && paper.visibility === "public" &&
                            !paper.remixed && (
                                user
                                    ? (
                                        <TooltipProvider>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <Button
                                                        onClick={handleRemix}
                                                        variant="ghost"
                                                        size="icon"
                                                        className="size-8"
                                                    >
                                                        <Shell className="size-4" />
                                                    </Button>
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                    Remix this and create your
                                                    own editable copy
                                                </TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>
                                    )
                                    : (
                                        <TooltipProvider>
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <Button
                                                        variant="ghost"
                                                        size="icon"
                                                        className="size-8 text-muted-foreground"
                                                        onClick={(e) => {
                                                            e.currentTarget
                                                                .classList.add(
                                                                    "animate-[shake_0.3s_ease-in-out]",
                                                                );
                                                            setTimeout(() =>
                                                                e.currentTarget
                                                                    .classList
                                                                    .remove(
                                                                        "animate-[shake_0.3s_ease-in-out]",
                                                                    ), 300);
                                                        }}
                                                    >
                                                        <Shell className="size-4" />
                                                    </Button>
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                    You gotta log in to remix
                                                    this paper
                                                </TooltipContent>
                                            </Tooltip>
                                        </TooltipProvider>
                                    )
                            )}
                    </div>
                    <span className="text-sm text-muted-foreground">
                        {!isOwner && authorName && <>by {authorName} ·</>}
                        {paper.question_count}{" "}
                        question{paper.question_count === 1 ? "" : "s"} ·{" "}
                        {paper.total_marks}{" "}
                        mark{paper.total_marks === 1 ? "" : "s"}
                    </span>
                </div>

                {paper.questions.length === 0
                    ? (
                        <p className="text-muted-foreground">
                            No questions yet.
                        </p>
                    )
                    : (
                        <div className="space-y-4">
                            {paper.questions.map((q) => (
                                <Question
                                    key={q.id}
                                    question={q}
                                    onChange={isOwner
                                        ? handleQuestionChange
                                        : undefined}
                                    onDelete={isOwner
                                        ? () => handleQuestionDelete(q.id)
                                        : undefined}
                                    onEdit={isOwner
                                        ? () => setSelectedId(q.id)
                                        : undefined}
                                />
                            ))}
                        </div>
                    )}

                {isOwner && (
                    <Button onClick={addQuestion} className="mt-6">
                        <Plus /> Add question
                    </Button>
                )}
            </main>

            <Sheet
                open={selected !== null}
                onOpenChange={(open) => !open && setSelectedId(null)}
            >
                <SheetContent
                    side="right"
                    className="w-full sm:max-w-md overflow-y-auto"
                >
                    {selected && (
                        <>
                            <SheetHeader>
                                <SheetTitle>
                                    Edit Question{" "}
                                    <EditableNumber
                                        value={selected.number}
                                        onCommit={(n) =>
                                            handleNumberChange(selected.id, n)}
                                    />
                                </SheetTitle>
                            </SheetHeader>
                            <QuestionEditor
                                question={selected}
                                onChange={handleQuestionChange}
                            />
                        </>
                    )}
                </SheetContent>
            </Sheet>
        </>
    );
}
