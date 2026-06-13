import {
    useCallback,
    useEffect,
    useRef,
    useState,
    type PointerEvent as ReactPointerEvent,
} from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
    createQuestion,
    paperStore,
    withRecalculatedTotals,
} from "@/lib/paper";
import type {
    Paper,
    PaperMeta,
    Question as QuestionData,
} from "@/types/tppr-paper";
import NavBar from "@/components/navbar";
import { Question } from "@/components/question";
import { Button } from "@/components/ui/button";
import {
    Sheet,
    SheetContent,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import {
    ArrowLeft,
    Check,
    CloudOff,
    CloudUpload,
    Download,
    Loader2,
    Plus,
    Shell,
} from "lucide-react";
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
import { useSyncStatus } from "@/lib/hooks";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";

const EDITOR_MIN_WIDTH = 384;
const EDITOR_DEFAULT_WIDTH = 448;
const EDITOR_MAX_MARGIN = 96;
const EDITOR_KEYBOARD_STEP = 48;

function clampEditorWidth(width: number) {
    const viewportMax = typeof window === "undefined"
        ? 896
        : Math.max(EDITOR_MIN_WIDTH, window.innerWidth - EDITOR_MAX_MARGIN);
    return Math.min(Math.max(width, EDITOR_MIN_WIDTH), viewportMax);
}

export default function PaperEditor() {
    const { id } = useParams<{ id: string }>();
    const [paper, setPaper] = useState<Paper | null>(null);
    const paperRef = useRef<Paper | null>(null);
    const [loading, setLoading] = useState(true);

    const [selectedId, setSelectedId] = useState<string | null>(null);
    const [editorWidth, setEditorWidth] = useState(EDITOR_DEFAULT_WIDTH);
    const selected = paper?.questions.find((q) => q.id === selectedId) ?? null;

    const navigate = useNavigate();
    const [syncing, setSyncing] = useState(false);

    const { user, loading: authLoading } = useAuth();

    const [authorName, setAuthorName] = useState<string | null>(null);
    const isOwner = !!user && String(user.user_id) === paper?.author_id;
    const authorId = paper?.author_id;

    const [remixSource, setRemixSource] = useState<
        { title: string; author: string } | null
    >(null);

    const [showSaveHint, setShowSaveHint] = useState(false);
    const [showExportDialog, setShowExportDialog] = useState(false);
    const saveCountRef = useRef(0);
    const saveTimerRef = useRef<ReturnType<typeof setTimeout>>(null);

    useEffect(() => {
        function handleKeyDown(e: KeyboardEvent) {
            if ((e.ctrlKey || e.metaKey) && e.key === "s") {
                e.preventDefault();
                saveCountRef.current += 1;

                // Reset counter after 3s of no presses
                if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
                saveTimerRef.current = setTimeout(() => {
                    saveCountRef.current = 0;
                }, 3000);

                if (saveCountRef.current >= 5) {
                    saveCountRef.current = 0;
                    setShowSaveHint(false);
                    setShowExportDialog(true);
                } else {
                    setShowSaveHint(true);
                    setTimeout(() => setShowSaveHint(false), 2500);
                }
            }
        }
        document.addEventListener("keydown", handleKeyDown);
        return () => document.removeEventListener("keydown", handleKeyDown);
    }, []);

    function handleExportJson() {
        if (!paper) return;
        const blob = new Blob([JSON.stringify(paper, null, 2)], {
            type: "application/json",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${paper.title.replace(/[^a-z0-9]/gi, "_")}.json`;
        a.click();
        URL.revokeObjectURL(url);
        setShowExportDialog(false);
    }

    const syncStatus = useSyncStatus();

    useEffect(() => {
        paperRef.current = paper;
    }, [paper]);

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
        if (!authorId) return;
        fetch(`/api/whotf?user_id=${authorId}`)
            .then((res) => res.ok ? res.json() : Promise.reject())
            .then((data) => setAuthorName(data.username))
            .catch(() => setAuthorName("Unknown"));
    }, [authorId]);

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

    const updatePaper = useCallback((
        nextPaper: Paper | ((current: Paper) => Paper),
    ) => {
        const current = paperRef.current;
        if (!current) return;

        const next = typeof nextPaper === "function"
            ? nextPaper(current)
            : nextPaper;
        if (next === current) return;

        const stamped = withRecalculatedTotals(next);
        paperRef.current = stamped;
        setPaper(stamped);
        void syncService.sync(stamped);
    }, []);

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

    const addQuestion = useCallback(() => {
        updatePaper((current) => ({
            ...current,
            questions: [...current.questions, createQuestion(current)],
        }));
    }, [updatePaper]);

    const handleQuestionChange = useCallback((updated: QuestionData) => {
        updatePaper((current) => ({
            ...current,
            questions: current.questions.map((q) =>
                q.id === updated.id ? updated : q
            ),
        }));
    }, [updatePaper]);

    const handleQuestionDelete = useCallback((qid: string) => {
        updatePaper((current) => ({
            ...current,
            questions: current.questions
                .filter((q) => q.id !== qid)
                .map((q, i) => ({ ...q, number: i + 1 })),
        }));
    }, [updatePaper]);

    const handleDuplicate = useCallback((qid: string) => {
        updatePaper((current) => {
            const source = current.questions.find((q) => q.id === qid);
            if (!source) return current;
            const idx = current.questions.indexOf(source);
            const clone: QuestionData = {
                ...structuredClone(source),
                id: crypto.randomUUID(),
            };
            const questions = [...current.questions];
            questions.splice(idx + 1, 0, clone);
            return {
                ...current,
                questions: questions.map((q, i) => ({ ...q, number: i + 1 })),
            };
        });
    }, [updatePaper]);

    const handleNumberChange = useCallback((qid: string, newNumber: number) => {
        updatePaper((current) => {
            const from = current.questions.findIndex((q) => q.id === qid);
            if (from === -1) return current;
            const to = Math.min(
                Math.max(newNumber - 1, 0),
                current.questions.length - 1,
            );

            const questions = [...current.questions];
            const [moved] = questions.splice(from, 1);
            questions.splice(to, 0, moved);

            return {
                ...current,
                questions: questions.map((q, i) => ({ ...q, number: i + 1 })),
            };
        });
    }, [updatePaper]);

    const handleSettingsSave = useCallback((meta: PaperMeta) => {
        updatePaper((current) => ({ ...current, ...meta }));
    }, [updatePaper]);

    const handleQuestionEdit = useCallback((qid: string) => {
        setSelectedId(qid);
    }, []);

    const handleEditorResizeStart = useCallback((
        e: ReactPointerEvent<HTMLDivElement>,
    ) => {
        e.preventDefault();
        e.currentTarget.setPointerCapture(e.pointerId);
        const startX = e.clientX;
        const startWidth = editorWidth;

        function handlePointerMove(moveEvent: PointerEvent) {
            const delta = startX - moveEvent.clientX;
            setEditorWidth(clampEditorWidth(startWidth + delta));
        }

        function handlePointerUp() {
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
            window.removeEventListener("pointermove", handlePointerMove);
            window.removeEventListener("pointerup", handlePointerUp);
        }

        document.body.style.cursor = "col-resize";
        document.body.style.userSelect = "none";
        window.addEventListener("pointermove", handlePointerMove);
        window.addEventListener("pointerup", handlePointerUp);
    }, [editorWidth]);

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
                                onSave={handleSettingsSave}
                            />
                        )}

                        {isOwner && (
                            <Popover
                                open={showSaveHint}
                                onOpenChange={setShowSaveHint}
                            >
                                <PopoverTrigger asChild>
                                    <span className="ml-2">
                                        {syncStatus === "synced" && (
                                            <Check className="size-4 text-green-500" />
                                        )}
                                        {syncStatus === "syncing" && (
                                            <Loader2 className="size-4 animate-spin text-blue-500" />
                                        )}
                                        {syncStatus === "pending" && (
                                            <CloudUpload className="size-4 text-yellow-500" />
                                        )}
                                        {syncStatus === "offline" && (
                                            <CloudOff className="size-4 text-destructive" />
                                        )}
                                    </span>
                                </PopoverTrigger>
                                <PopoverContent className="w-auto px-3 py-2 text-xs">
                                    {syncStatus !== "offline"
                                        ? "Don't worry, everything is automatically saved"
                                        : "Well this is awkward... At least it's available locally"}
                                </PopoverContent>
                            </Popover>
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
                                        ? handleQuestionDelete
                                        : undefined}
                                    onEdit={isOwner
                                        ? handleQuestionEdit
                                        : undefined}
                                    onDuplicate={isOwner
                                        ? handleDuplicate
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
                    className="w-[calc(100vw-16px)] max-w-none overflow-y-auto sm:w-auto"
                    style={{
                        width: `min(${editorWidth}px, calc(100vw - 16px))`,
                        maxWidth: "none",
                    }}
                >
                    {selected && (
                        <>
                            <div
                                role="separator"
                                aria-orientation="vertical"
                                aria-label="Resize question editor"
                                tabIndex={0}
                                className="group absolute inset-y-0 left-0 z-20 w-4 -translate-x-1/2 cursor-col-resize touch-none focus-visible:outline-none"
                                onPointerDown={handleEditorResizeStart}
                                onKeyDown={(e) => {
                                    if (e.key === "ArrowLeft") {
                                        e.preventDefault();
                                        setEditorWidth((width) =>
                                            clampEditorWidth(
                                                width +
                                                    EDITOR_KEYBOARD_STEP,
                                            ));
                                    }
                                    if (e.key === "ArrowRight") {
                                        e.preventDefault();
                                        setEditorWidth((width) =>
                                            clampEditorWidth(
                                                width -
                                                    EDITOR_KEYBOARD_STEP,
                                        ));
                                    }
                                }}
                            >
                                <span className="absolute inset-y-0 left-1/2 w-px bg-border transition group-hover:bg-primary/70 group-focus-visible:bg-primary" />
                                <span className="absolute left-1/2 top-1/2 h-10 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-border/80 transition group-hover:bg-primary/70 group-focus-visible:bg-primary" />
                            </div>
                            <SheetHeader className="pr-12">
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

            <Dialog open={showExportDialog} onOpenChange={setShowExportDialog}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            You really don't trust the cloud, do you? Hmph.
                        </DialogTitle>
                        <DialogDescription>
                            Here, you can save it locally or whatever… its not
                            like I'm doing this because I care.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setShowExportDialog(false)}
                        >
                            Nevermind
                        </Button>
                        <Button onClick={handleExportJson}>
                            <Download className="size-4" /> Export as JSON
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}
