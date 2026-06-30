import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
    Paper,
    Question as QuestionData,
    QuestionPart,
} from "@/types/tppr-paper";
import { ContentBlocks } from "@/components/question";
import { compoundLabel, flattenLeaves } from "@/lib/parts";
import { ArrowLeft, ArrowRight, BarChart3, BookOpen, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    Tabs,
    TabsList,
    TabsTrigger,
} from "@/components/ui/tabs";
import Confetti from "react-confetti";
import { useWindowSize } from "react-use";
import { useAuth } from "@/api/auth";
import {
    completeAttempt,
    recordQuestionTime,
    startAttempt,
    updateAttempt,
} from "@/api/progress";
import { clearActivePaperPresence, heartbeatPresence } from "@/api/social";

type FocusSlide =
    | { kind: "cover"; paper: Paper }
    | {
        kind: "question";
        question: QuestionData;
        /** Path of sibling indices from the top-level part down to the leaf. */
        partPath?: number[];
    }
    | { kind: "complete"; paper: Paper };

/** Read the part at `path` (list of sibling indices) from a question's part tree. */
function partAt(q: QuestionData, path: number[]): QuestionPart | undefined {
    let cursor: QuestionPart[] | undefined = q.parts;
    let part: QuestionPart | undefined;
    for (const i of path) {
        if (!cursor) return undefined;
        part = cursor[i];
        if (!part) return undefined;
        cursor = part.parts;
    }
    return part;
}

function buildSlides(paper: Paper): FocusSlide[] {
    const slides: FocusSlide[] = [{ kind: "cover", paper }];
    for (const q of paper.questions) {
        if (q.type === "long_answer" && q.parts?.length) {
            const leaves = flattenLeaves(q);
            if (leaves.length) {
                for (const leaf of leaves) {
                    slides.push({
                        kind: "question",
                        question: q,
                        partPath: leaf.path,
                    });
                }
            } else {
                slides.push({ kind: "question", question: q });
            }
        } else {
            slides.push({ kind: "question", question: q });
        }
    }
    slides.push({ kind: "complete", paper });
    return slides;
}

/** Returns a unique question index (0-based) from a slide index. */
function questionIndexFromSlide(
    slides: FocusSlide[],
    slideIndex: number,
): number {
    let qIdx = -1;
    let lastQId = "";
    for (let i = 0; i <= slideIndex; i++) {
        const s = slides[i];
        if (s.kind === "question" && s.question.id !== lastQId) {
            qIdx++;
            lastQId = s.question.id;
        }
    }
    return qIdx;
}

/** Stable key for a question slide (question id + leaf part path). */
function slideKey(slide: FocusSlide | undefined): string | null {
    if (!slide || slide.kind !== "question") return null;
    const path = slide.partPath?.join(".") ?? "";
    return `${slide.question.id}:${path}`;
}

interface QuestionBucket {
    questionId: string;
    partPath?: number[];
    seconds: number;
    revealedAnswer: boolean;
    revealCount: number;
    views: number;
}

interface FocusMetrics {
    elapsedSeconds: number;
    questionsSeen: number;
    answersChecked: number;
    revealCount: number;
    currentSlide: number;
    totalSlides: number;
    currentQuestion: string;
}

function CoverSlide({ paper }: { paper: Paper }) {
    return (
        <div className="flex flex-col items-center justify-center gap-6 text-center">
            <h1 className="text-4xl font-bold">{paper.title}</h1>
            <p className="text-lg text-muted-foreground">{paper.subject}</p>
            <div className="flex flex-wrap items-center justify-center gap-3">
                <Badge variant="secondary" className="text-base px-3 py-1">
                    {paper.question_count}{" "}
                    question{paper.question_count !== 1 ? "s" : ""}
                </Badge>
                <Badge variant="secondary" className="text-base px-3 py-1">
                    {paper.total_marks} mark{paper.total_marks !== 1 ? "s" : ""}
                </Badge>
                {paper.duration_minutes && (
                    <Badge variant="secondary" className="text-base px-3 py-1">
                        {paper.duration_minutes} min
                    </Badge>
                )}
            </div>
            <p className="mt-8 text-sm text-muted-foreground">
                Press{" "}
                <kbd className="rounded border px-1.5 py-0.5 font-mono text-xs">
                    →
                </kbd>{" "}
                to start
            </p>
        </div>
    );
}

function formatElapsed(seconds: number): string {
    const safeSeconds = Math.max(0, Math.floor(seconds));
    const hours = Math.floor(safeSeconds / 3600);
    const minutes = Math.floor((safeSeconds % 3600) / 60);
    const remainder = safeSeconds % 60;
    const parts: string[] = [];

    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0 || hours > 0) parts.push(`${minutes}m`);
    const secondsLabel = parts.length > 0
        ? `${String(remainder).padStart(2, "0")}s`
        : `${remainder}s`;
    parts.push(secondsLabel);

    return parts.join(" ");
}

function CompletionSlide(
    { paper, elapsedSeconds }: { paper: Paper; elapsedSeconds: number },
) {
    const tooSlow = paper.duration_minutes != null &&
        elapsedSeconds > paper.duration_minutes * 60;

    return (
        <div className="flex flex-col items-center justify-center gap-4 text-center">
            <p className="text-4xl font-bold leading-tight">
                Hooray! You completed {paper.title} in{" "}
                {formatElapsed(elapsedSeconds)}
            </p>
            {tooSlow && (
                <p className="text-2xl italic text-muted-foreground">
                    Lock in!
                </p>
            )}
        </div>
    );
}

function FocusDataPanel(
    { paper, metrics }: { paper: Paper; metrics: FocusMetrics },
) {
    const cards = [
        { label: "Elapsed", value: formatElapsed(metrics.elapsedSeconds) },
        { label: "Questions seen", value: metrics.questionsSeen },
        { label: "Answers checked", value: metrics.answersChecked },
        { label: "Reveals", value: metrics.revealCount },
    ];

    return (
        <div className="flex w-full max-w-3xl flex-col gap-4">
            <div>
                <h2 className="text-2xl font-semibold">Focus data</h2>
                <p className="text-sm text-muted-foreground">{paper.title}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {cards.map((card) => (
                    <Card key={card.label}>
                        <CardHeader className="pb-2">
                            <CardTitle className="text-sm font-medium text-muted-foreground">
                                {card.label}
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <p className="text-2xl font-semibold tabular-nums">
                                {card.value}
                            </p>
                        </CardContent>
                    </Card>
                ))}
            </div>
            <Card>
                <CardHeader>
                    <CardTitle className="text-base">Current position</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                    <div className="flex items-center justify-between gap-4 text-sm">
                        <span className="text-muted-foreground">Slide</span>
                        <span className="font-medium tabular-nums">
                            {metrics.currentSlide} / {metrics.totalSlides}
                        </span>
                    </div>
                    <div className="flex items-center justify-between gap-4 text-sm">
                        <span className="text-muted-foreground">Question</span>
                        <span className="font-medium">{metrics.currentQuestion}</span>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}

function QuestionSlide(
    { question, partPath, showAnswer }: {
        question: QuestionData;
        partPath?: number[];
        showAnswer: boolean;
    },
) {
    const leaf = partPath ? partAt(question, partPath) : undefined;
    const answer = leaf?.answer ?? question.answer;
    const rubric = leaf?.rubric ?? question.rubric;
    const guidelines = leaf?.guidelines ?? question.guidelines;
    const label = partPath
        ? compoundLabel(question, partPath, question.parts ?? [])
        : undefined;

    // Stimulus from every ancestor part down to the leaf, in document order.
    const ancestorStimuli: { blocks: QuestionPart["stimulus"]; depth: number }[] =
        [];
    if (partPath) {
        let cursor: QuestionPart[] | undefined = question.parts;
        for (let d = 0; d < partPath.length; d++) {
            const part = cursor?.[partPath[d]];
            if (!part) break;
            if (part.stimulus) ancestorStimuli.push({ blocks: part.stimulus, depth: d });
            cursor = part.parts;
        }
    }

    return (
        <div className="flex w-full max-w-3xl flex-col gap-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <span className="text-lg font-semibold">
                    Question {label ?? question.number}
                </span>
                <Badge variant="secondary">
                    {leaf?.marks ?? question.marks}{" "}
                    mark{(leaf?.marks ?? question.marks) !== 1 ? "s" : ""}
                </Badge>
            </div>

            {/* Root stimulus */}
            <ContentBlocks
                blocks={question.stimulus}
                className="text-muted-foreground"
            />

            {/* Ancestor + leaf part stimuli, indented by depth */}
            {ancestorStimuli.map((s, i) => (
                <ContentBlocks
                    key={i}
                    blocks={s.blocks}
                    className="text-muted-foreground"
                />
            ))}

            {/* Question content */}
            {leaf
                ? <ContentBlocks blocks={leaf.content} />
                : <ContentBlocks blocks={question.content} />}

            {/* MCQ options */}
            {question.type === "multiple_choice" && question.options && (
                <div className="grid gap-3 sm:grid-cols-2">
                    {question.options.map((opt) => (
                        <div
                            key={opt.label}
                            className="flex gap-3 rounded-md border p-3"
                        >
                            <span className="font-semibold">{opt.label}.</span>
                            <ContentBlocks blocks={opt.content} />
                        </div>
                    ))}
                </div>
            )}

            {/* Answer guide (toggled with spacebar) */}
            {showAnswer && (answer || rubric || guidelines) && (
                <div className="space-y-3 rounded-md border border-dashed border-green-500/40 bg-green-50/50 p-4 dark:bg-green-950/20">
                    <span className="text-xs font-semibold uppercase tracking-wide text-green-700 dark:text-green-400">
                        Answer / Marking Guidelines
                    </span>

                    {answer && (
                        <div className="space-y-2">
                            {typeof answer === "string"
                                ? (
                                    <ContentBlocks
                                        blocks={[{
                                            kind: "text",
                                            text: answer,
                                        }]}
                                    />
                                )
                                : (
                                    <>
                                        {answer.option_label && (
                                            <p className="font-medium">
                                                Correct option:{" "}
                                                {answer.option_label}
                                            </p>
                                        )}
                                        {answer.summary && (
                                            <ContentBlocks
                                                blocks={[{
                                                    kind: "text",
                                                    text: answer.summary,
                                                }]}
                                            />
                                        )}
                                        <ContentBlocks
                                            blocks={answer.content}
                                        />
                                    </>
                                )}
                        </div>
                    )}

                    {!!rubric?.criteria.length && (
                        <div className="space-y-1">
                            <span className="text-xs font-medium text-muted-foreground">
                                Marking Criteria
                            </span>
                            <table className="w-full text-sm">
                                <tbody>
                                    {rubric.criteria.map((c, i) => (
                                        <tr
                                            key={i}
                                            className="border-b last:border-0"
                                        >
                                            <td className="py-1 pr-2">
                                                <ContentBlocks
                                                    blocks={c.description}
                                                />
                                            </td>
                                            <td className="w-12 py-1 text-right font-medium">
                                                {c.marks ??
                                                    `${c.min_marks}-${c.max_marks}`}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    <ContentBlocks blocks={guidelines} />
                </div>
            )}
        </div>
    );
}

/** Progress bar showing overall question position */
function ProgressBar(
    { total, current }: { total: number; current: number },
) {
    return (
        <div className="flex w-full max-w-md items-center gap-1">
            {Array.from({ length: total }, (_, i) => (
                <div
                    key={i}
                    className={`h-1.5 flex-1 rounded-full transition-colors ${
                        i === current
                            ? "bg-primary"
                            : i < current
                            ? "bg-primary/40"
                            : "bg-muted-foreground/20"
                    }`}
                />
            ))}
        </div>
    );
}

/** Vertical dots for LAQ part index */
function PartDots(
    { total, current }: { total: number; current: number },
) {
    return (
        <div className="flex flex-col items-center gap-2">
            {Array.from({ length: total }, (_, i) => (
                <div
                    key={i}
                    className={`size-2.5 rounded-full border transition-colors ${
                        i === current
                            ? "border-primary bg-primary"
                            : "border-muted-foreground/40 bg-transparent"
                    }`}
                />
            ))}
        </div>
    );
}

export function FocusMode(
    { paper, onExit }: { paper: Paper; onExit: () => void },
) {
    const { user } = useAuth();
    const slides = useMemo(() => buildSlides(paper), [paper]);
    const [index, setIndex] = useState(0);
    const [viewTab, setViewTab] = useState<"paper" | "data">("paper");
    const [metricsTick, setMetricsTick] = useState(0);
    const [completedSeconds, setCompletedSeconds] = useState<number | null>(
        null,
    );
    const [showAnswer, setShowAnswer] = useState(false);
    const { width, height } = useWindowSize();

    // --- Progress tracking refs -------------------------------------------
    const attemptIdRef = useRef<string | null>(null);
    const persistRef = useRef<boolean>(!!user);
    const slideEnteredAtRef = useRef<number | null>(null);
    const currentKeyRef = useRef<string | null>(null);
    const bucketsRef = useRef<Map<string, QuestionBucket>>(new Map());
    const elapsedRef = useRef<number>(0);
    const indexRef = useRef<number>(0);
    const finishedRef = useRef<boolean>(false);
    const showAnswerRef = useRef<boolean>(false);

    const bumpMetrics = useCallback(() => {
        setMetricsTick((tick) => tick + 1);
    }, []);

    // Keep persistRef in sync if the user logs in/out mid-session.
    useEffect(() => {
        persistRef.current = !!user;
    }, [user]);

    useEffect(() => {
        indexRef.current = index;
    }, [index]);

    useEffect(() => {
        const timer = window.setInterval(bumpMetrics, 1000);
        return () => window.clearInterval(timer);
    }, [bumpMetrics]);

    // Start a backend attempt on mount (best-effort).
    useEffect(() => {
        let cancelled = false;
        if (user) {
            startAttempt(paper.id)
                .then((attempt) => {
                    if (!cancelled) attemptIdRef.current = attempt.id;
                })
                .catch(() => {
                    // Offline / error — keep working locally without persisting.
                });
        }
        return () => {
            cancelled = true;
        };
    }, [user, paper.id]);

    useEffect(() => {
        if (!user) return;

        heartbeatPresence(paper.id).catch(() => {});
        const timer = window.setInterval(() => {
            heartbeatPresence(paper.id).catch(() => {});
        }, 30000);

        return () => {
            window.clearInterval(timer);
            clearActivePaperPresence().catch(() => {});
        };
    }, [paper.id, user]);

    // Track when each slide is entered + its key.
    useEffect(() => {
        slideEnteredAtRef.current = Date.now();
        currentKeyRef.current = slideKey(slides[index]);
        // Count a view when a question slide is first entered.
        const key = currentKeyRef.current;
        if (key) {
            const existing = bucketsRef.current.get(key);
            if (existing) {
                existing.views += 1;
            } else {
                const slide = slides[index];
                bucketsRef.current.set(key, {
                    questionId: (slide as { question: QuestionData }).question.id,
                    partPath: (slide as { partPath?: number[] }).partPath,
                    seconds: 0,
                    revealedAnswer: false,
                    revealCount: 0,
                    views: 1,
                });
            }
            bumpMetrics();
        }
    }, [bumpMetrics, index, slides]);

    const flushCurrentSlide = useCallback(() => {
        const key = currentKeyRef.current;
        const enteredAt = slideEnteredAtRef.current;
        if (!key || enteredAt == null) return;
        const elapsedMs = Date.now() - enteredAt;
        const delta = elapsedMs > 0 ? Math.max(1, Math.floor(elapsedMs / 1000)) : 0;
        if (delta <= 0) return;
        const bucket = bucketsRef.current.get(key);
        if (!bucket) return;
        bucket.seconds += delta;
        elapsedRef.current += delta;
        slideEnteredAtRef.current = Date.now();
        bumpMetrics();

        const attemptId = attemptIdRef.current;
        if (persistRef.current && attemptId) {
            recordQuestionTime(attemptId, {
                question_id: bucket.questionId,
                part_path: bucket.partPath,
                seconds: bucket.seconds,
                revealed_answer: bucket.revealedAnswer,
                reveal_count: bucket.revealCount,
                views: bucket.views,
            }).catch(() => {});
        }
    }, [bumpMetrics]);

    const markRevealCurrent = useCallback(() => {
        const key = currentKeyRef.current;
        if (!key) return;
        const bucket = bucketsRef.current.get(key);
        if (!bucket) return;
        bucket.revealedAnswer = true;
        bucket.revealCount += 1;
        bumpMetrics();
    }, [bumpMetrics]);

    const aggregatedPayload = useCallback(() => {
        const buckets = [...bucketsRef.current.values()];
        return {
            elapsed_seconds: elapsedRef.current,
            questions_seen: buckets.length,
            questions_answered: buckets.filter((b) => b.revealedAnswer).length,
            reveal_count: buckets.reduce((s, b) => s + b.revealCount, 0),
            max_slide: indexRef.current,
        };
    }, []);

    const finishSession = useCallback(
        (completed: boolean) => {
            if (finishedRef.current) return;
            flushCurrentSlide();
            const attemptId = attemptIdRef.current;
            if (!persistRef.current || !attemptId) {
                finishedRef.current = true;
                return;
            }
            finishedRef.current = true;
            const payload = aggregatedPayload();
            const buckets = [...bucketsRef.current.values()];
            if (completed) {
                completeAttempt(attemptId, {
                    ...payload,
                    questions_seen: buckets.length,
                    question_times: buckets.map((b) => ({
                        question_id: b.questionId,
                        part_path: b.partPath,
                        seconds: b.seconds,
                        revealed_answer: b.revealedAnswer,
                        reveal_count: b.revealCount,
                        views: b.views,
                    })),
                }).finally(() => {
                    clearActivePaperPresence().catch(() => {});
                });
            } else {
                updateAttempt(attemptId, payload).catch(() => {});
            }
        },
        [aggregatedPayload, flushCurrentSlide],
    );

    // Flush a heartbeat periodically so partial progress is never lost.
    useEffect(() => {
        const timer = window.setInterval(() => {
            const attemptId = attemptIdRef.current;
            if (!persistRef.current || !attemptId) return;
            // Update "now" for the currently-occupied slide before reporting.
            flushCurrentSlide();
            updateAttempt(attemptId, aggregatedPayload()).catch(() => {});
        }, 20000);
        return () => window.clearInterval(timer);
    }, [aggregatedPayload, flushCurrentSlide]);

    // On unmount, persist a final non-completing update if not already done.
    useEffect(() => {
        return () => finishSession(false);
    }, [finishSession]);

    const goNext = useCallback(() => {
        const nextIndex = Math.min(index + 1, slides.length - 1);
        if (nextIndex !== index) {
            flushCurrentSlide();
            setShowAnswer(false);
            showAnswerRef.current = false;
        }
        // Reached the completion slide?
        if (slides[nextIndex]?.kind === "complete") {
            if (completedSeconds == null) {
                setCompletedSeconds(elapsedRef.current);
            }
            indexRef.current = nextIndex;
            finishSession(true);
        }
        setIndex(nextIndex);
    }, [completedSeconds, finishSession, flushCurrentSlide, index, slides]);

    const goPrev = useCallback(() => {
        flushCurrentSlide();
        setShowAnswer(false);
        showAnswerRef.current = false;
        setIndex((i) => Math.max(i - 1, 0));
    }, [flushCurrentSlide]);

    useEffect(() => {
        function onKey(e: KeyboardEvent) {
            if (e.key === "Escape") {
                finishSession(false);
                onExit();
            }
            if (e.key === "ArrowRight") goNext();
            if (e.key === "ArrowLeft") goPrev();
            if (e.key === " " && viewTab === "paper") {
                e.preventDefault();
                const next = !showAnswerRef.current;
                setShowAnswer(next);
                showAnswerRef.current = next;
                if (next) markRevealCurrent();
            }
        }
        document.addEventListener("keydown", onKey);
        return () => document.removeEventListener("keydown", onKey);
    }, [
        onExit,
        goNext,
        goPrev,
        markRevealCurrent,
        finishSession,
        viewTab,
    ]);

    const slide = slides[index];
    const questionCount = paper.questions.length;
    const isCompleteSlide = slide.kind === "complete";
    const currentQuestionIdx = isCompleteSlide
        ? questionCount
        : questionIndexFromSlide(slides, index);
    const metrics = useMemo<FocusMetrics>(() => {
        void metricsTick;
        const key = currentKeyRef.current;
        const enteredAt = slideEnteredAtRef.current;
        const liveDelta = key && enteredAt != null
            ? Math.max(0, Math.floor((Date.now() - enteredAt) / 1000))
            : 0;
        const buckets = [...bucketsRef.current.values()];
        const questionLabel = slide.kind === "question"
            ? `Question ${
                slide.partPath
                    ? compoundLabel(slide.question, slide.partPath, slide.question.parts ?? [])
                    : slide.question.number
            }`
            : slide.kind === "complete"
            ? "Complete"
            : "Cover";

        return {
            elapsedSeconds: elapsedRef.current + liveDelta,
            questionsSeen: buckets.length,
            answersChecked: buckets.filter((b) => b.revealedAnswer).length,
            revealCount: buckets.reduce((sum, b) => sum + b.revealCount, 0),
            currentSlide: Math.min(index, slides.length - 1),
            totalSlides: Math.max(0, slides.length - 2),
            currentQuestion: questionLabel,
        };
    }, [index, metricsTick, slide, slides.length]);

    // For LAQ part dots: reflect the leaf's immediate sibling group.
    const partPath = slide.kind === "question" ? slide.partPath : undefined;
    const showPartDots = slide.kind === "question" && partPath != null;
    let totalParts = 0;
    let currentPart = 0;
    if (showPartDots && partPath && partPath.length > 0) {
        const parentPath = partPath.slice(0, -1);
        const parent = parentPath.length
            ? partAt(slide.question, parentPath)
            : undefined;
        const siblings = parent?.parts ?? slide.question.parts ?? [];
        totalParts = siblings.length;
        currentPart = partPath[partPath.length - 1] ?? 0;
    }

    return (
        <div className="fixed inset-0 z-50 flex flex-col bg-background">
            {isCompleteSlide && (
                <>
                    <Confetti
                        width={width || window.innerWidth}
                        height={height || window.innerHeight}
                        style={{
                            position: "fixed",
                            inset: 0,
                            pointerEvents: "none",
                            zIndex: 60,
                        }}
                        recycle={false}
                        numberOfPieces={140}
                        confettiSource={{
                            x: 0,
                            y: height || window.innerHeight,
                            w: 10,
                            h: 0,
                        }}
                        initialVelocityX={{ min: 5, max: 15 }}
                        initialVelocityY={{ min: -35, max: -15 }}
                    />
                    <Confetti
                        width={width || window.innerWidth}
                        height={height || window.innerHeight}
                        style={{
                            position: "fixed",
                            inset: 0,
                            pointerEvents: "none",
                            zIndex: 60,
                        }}
                        recycle={false}
                        numberOfPieces={140}
                        confettiSource={{
                            x: (width || window.innerWidth) - 10,
                            y: height || window.innerHeight,
                            w: 10,
                            h: 0,
                        }}
                        initialVelocityX={{ min: -15, max: -5 }}
                        initialVelocityY={{ min: -35, max: -15 }}
                    />
                </>
            )}

            {/* Top bar */}
            <div className="flex items-center justify-between gap-4 border-b px-4 py-3">
                <div className="flex min-w-0 flex-1 items-center gap-4">
                    <ProgressBar
                        total={questionCount}
                        current={currentQuestionIdx}
                    />
                    <Tabs
                        value={viewTab}
                        onValueChange={(value) =>
                            setViewTab(value as "paper" | "data")}
                    >
                        <TabsList>
                            <TabsTrigger value="paper">
                                <BookOpen data-icon="inline-start" />
                                Paper
                            </TabsTrigger>
                            <TabsTrigger value="data">
                                <BarChart3 data-icon="inline-start" />
                                Data
                            </TabsTrigger>
                        </TabsList>
                    </Tabs>
                </div>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                        finishSession(false);
                        onExit();
                    }}
                    aria-label="Exit focus mode"
                    className="ml-4"
                >
                    <X className="size-5" />
                </Button>
            </div>

            {/* Main content */}
            <div className="relative flex-1 overflow-y-auto px-8 py-6">
                <div className="mx-auto flex min-h-full max-w-3xl items-center justify-center">
                    {viewTab === "data"
                        ? <FocusDataPanel paper={paper} metrics={metrics} />
                        : (
                            <>
                                {slide.kind === "cover" && (
                                    <CoverSlide paper={slide.paper} />
                                )}
                                {slide.kind === "question" && (
                                    <QuestionSlide
                                        question={slide.question}
                                        partPath={slide.partPath}
                                        showAnswer={showAnswer}
                                    />
                                )}
                                {slide.kind === "complete" && (
                                    <CompletionSlide
                                        paper={slide.paper}
                                        elapsedSeconds={completedSeconds ?? 0}
                                    />
                                )}
                            </>
                        )}
                </div>

                {/* Right-side part dots for LAQ */}
                {viewTab === "paper" && showPartDots && (
                    <div className="absolute right-6 top-1/2 -translate-y-1/2">
                        <PartDots total={totalParts} current={currentPart} />
                    </div>
                )}
            </div>

            {/* Bottom navigation */}
            <div className="flex items-center justify-center gap-4 border-t px-4 py-3">
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={goPrev}
                    disabled={index === 0}
                    aria-label="Previous"
                >
                    <ArrowLeft className="size-5" />
                </Button>
                <span className="text-sm text-muted-foreground">
                    {index} / {slides.length - 2}
                </span>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={goNext}
                    disabled={index === slides.length - 1}
                    aria-label="Next"
                >
                    <ArrowRight className="size-5" />
                </Button>
                {slide.kind === "question" && (
                    <span className="ml-4 text-xs text-muted-foreground">
                        <kbd className="rounded border px-1.5 py-0.5 font-mono text-xs">
                            Space
                        </kbd>{" "}
                        {showAnswer ? "hide" : "show"} answer
                    </span>
                )}
            </div>
        </div>
    );
}
