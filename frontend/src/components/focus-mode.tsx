import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
    Paper,
    Question as QuestionData,
    QuestionPart,
} from "@/types/tppr-paper";
import { ContentBlocks } from "@/components/question";
import { compoundLabel, flattenLeaves } from "@/lib/parts";
import { ArrowLeft, ArrowRight, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Confetti from "react-confetti";
import { useWindowSize } from "react-use";

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
    const slides = useMemo(() => buildSlides(paper), [paper]);
    const [index, setIndex] = useState(0);
    const startedAt = useRef<number | null>(null);
    const [completedSeconds, setCompletedSeconds] = useState<number | null>(
        null,
    );
    const [showAnswer, setShowAnswer] = useState(false);
    const { width, height } = useWindowSize();

    const goNext = useCallback(() => {
        const nextIndex = Math.min(index + 1, slides.length - 1);
        if (nextIndex !== index) {
            setShowAnswer(false);
        }
        if (startedAt.current == null && nextIndex > 0) {
            startedAt.current = Date.now();
        }
        if (slides[nextIndex]?.kind === "complete" && completedSeconds == null) {
            setCompletedSeconds(
                Math.floor(
                    (Date.now() - (startedAt.current ?? Date.now())) / 1000,
                ),
            );
        }
        setIndex(nextIndex);
    }, [completedSeconds, index, slides]);
    const goPrev = useCallback(
        () => {
            setShowAnswer(false);
            setIndex((i) => Math.max(i - 1, 0));
        },
        [],
    );

    useEffect(() => {
        function onKey(e: KeyboardEvent) {
            if (e.key === "Escape") onExit();
            if (e.key === "ArrowRight") goNext();
            if (e.key === "ArrowLeft") goPrev();
            if (e.key === " ") {
                e.preventDefault();
                setShowAnswer((v) => !v);
            }
        }
        document.addEventListener("keydown", onKey);
        return () => document.removeEventListener("keydown", onKey);
    }, [onExit, goNext, goPrev]);

    const slide = slides[index];
    const questionCount = paper.questions.length;
    const isCompleteSlide = slide.kind === "complete";
    const currentQuestionIdx = isCompleteSlide
        ? questionCount
        : questionIndexFromSlide(slides, index);

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
            <div className="flex items-center justify-between border-b px-4 py-3">
                <ProgressBar
                    total={questionCount}
                    current={currentQuestionIdx}
                />
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onExit}
                    aria-label="Exit focus mode"
                    className="ml-4"
                >
                    <X className="size-5" />
                </Button>
            </div>

            {/* Main content */}
            <div className="relative flex-1 overflow-y-auto px-8 py-6">
                <div className="mx-auto flex min-h-full max-w-3xl items-center justify-center">
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
                </div>

                {/* Right-side part dots for LAQ */}
                {showPartDots && (
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
