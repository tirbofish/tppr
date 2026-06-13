// frontend/src/components/question.tsx
import {
    createElement,
    Fragment,
    memo,
    type ReactNode,
    useEffect,
    useMemo,
    useState,
} from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { paperStore } from "@/lib/paper";
import type {
    ContentBlock,
    QuestionAnswer,
    Question as QuestionData,
    QuestionRubric,
} from "@/types/tppr-paper";
import { Copy, Eye, EyeOff, Pencil, Trash2 } from "lucide-react";
import { Button } from "./ui/button";
import { MathText } from "./math-text";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Resolves asset:// URLs from IndexedDB to object URLs. */
function useAssetUrl(url: string): string | undefined {
    const [resolvedAsset, setResolvedAsset] = useState<
        { source: string; objectUrl: string } | undefined
    >();

    useEffect(() => {
        if (!url.startsWith("asset://")) return;

        let objectUrl: string | undefined;
        let cancelled = false;

        paperStore.getAsset(url.slice("asset://".length)).then((asset) => {
            if (!asset || cancelled) return;
            objectUrl = URL.createObjectURL(asset.blob);
            setResolvedAsset({ source: url, objectUrl });
        });

        return () => {
            cancelled = true;
            if (objectUrl) URL.revokeObjectURL(objectUrl);
        };
    }, [url]);

    if (!url.startsWith("asset://")) return url;
    return resolvedAsset?.source === url ? resolvedAsset.objectUrl : undefined;
}

function AssetImage({
    url,
    alt,
    width,
    height,
}: { url: string; alt?: string; width?: number; height?: number }) {
    const src = useAssetUrl(url);
    if (!src) return null;
    return (
        <img
            src={src}
            alt={alt ?? ""}
            width={width}
            height={height}
            className="mx-auto block max-w-full rounded-md"
        />
    );
}

const remarkPlugins = [remarkGfm];
const HTML_TAG_PATTERN =
    /<\/?(a|b|blockquote|br|code|dd|del|details|div|dl|dt|em|h[1-6]|hr|i|li|mark|ol|p|pre|s|small|span|strong|sub|summary|sup|table|tbody|td|tfoot|th|thead|tr|u|ul|script|style|iframe|object)(\s|>|\/)/i;
const LIST_ITEM_PATTERN = /^\s{0,8}([-+*]|\d+[.)])\s+/;
const SAFE_HTML_TAGS = new Set([
    "a",
    "b",
    "blockquote",
    "br",
    "code",
    "dd",
    "del",
    "details",
    "div",
    "dl",
    "dt",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "i",
    "li",
    "mark",
    "ol",
    "p",
    "pre",
    "s",
    "small",
    "span",
    "strong",
    "sub",
    "summary",
    "sup",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "u",
    "ul",
]);
const DROPPED_HTML_TAGS = new Set(["script", "style", "iframe", "object"]);
const SAFE_GLOBAL_ATTRS = new Set(["aria-label", "title"]);
const SAFE_TABLE_ATTRS = new Set(["colspan", "rowspan", "scope"]);
const VOID_HTML_TAGS = new Set(["br", "hr"]);

function normalizeMarkdownText(text: string): string {
    const lines = text.replace(/\r\n?/g, "\n").split("\n");
    const normalized: string[] = [];

    for (const line of lines) {
        const previous = normalized.at(-1);
        const currentIsListItem = LIST_ITEM_PATTERN.test(line);
        const previousIsListItem = previous
            ? LIST_ITEM_PATTERN.test(previous)
            : false;

        if (
            currentIsListItem &&
            previous?.trim() &&
            !previousIsListItem
        ) {
            normalized.push("");
        }

        normalized.push(line);
    }

    return normalized.join("\n");
}

function isSafeUrl(value: string): boolean {
    if (value.startsWith("#") || value.startsWith("/")) return true;
    try {
        const url = new URL(value, window.location.origin);
        return ["http:", "https:", "mailto:", "tel:"].includes(url.protocol);
    } catch {
        return false;
    }
}

function safeHtmlNodeToReact(node: Node, key: string): ReactNode {
    if (node.nodeType === Node.TEXT_NODE) {
        return <MathText key={key} text={node.textContent ?? ""} />;
    }

    if (node.nodeType !== Node.ELEMENT_NODE) return null;

    const element = node as Element;
    const tag = element.tagName.toLowerCase();

    if (DROPPED_HTML_TAGS.has(tag)) return null;

    const children = Array.from(element.childNodes)
        .map((child, i) => safeHtmlNodeToReact(child, `${key}-${i}`))
        .filter((child): child is ReactNode => child !== null);

    if (!SAFE_HTML_TAGS.has(tag)) {
        return <Fragment key={key}>{children}</Fragment>;
    }

    const props: Record<string, string | number | boolean> = { key };

    for (const attr of Array.from(element.attributes)) {
        const name = attr.name.toLowerCase();
        const value = attr.value;

        if (name.startsWith("on")) continue;
        if (name === "href") {
            if (tag !== "a" || !isSafeUrl(value)) continue;
            props.href = value;
            props.rel = "noreferrer";
            continue;
        }
        if (name === "target") {
            if (tag === "a" && value === "_blank") props.target = "_blank";
            continue;
        }
        if (SAFE_GLOBAL_ATTRS.has(name)) {
            props[name] = value;
            continue;
        }
        if (SAFE_TABLE_ATTRS.has(name)) {
            props[name === "colspan" ? "colSpan" : name === "rowspan" ? "rowSpan" : name] =
                /^\d+$/.test(value) ? Number(value) : value;
        }
    }

    return createElement(
        tag,
        props,
        VOID_HTML_TAGS.has(tag) ? undefined : children,
    );
}

function SafeHtml({ html }: { html: string }) {
    const children = useMemo(() => {
        if (typeof DOMParser === "undefined") return [<MathText key="0" text={html} />];
        const document = new DOMParser().parseFromString(html, "text/html");
        return Array.from(document.body.childNodes).map((node, i) =>
            safeHtmlNodeToReact(node, String(i))
        );
    }, [html]);

    return <>{children}</>;
}

type TableAlignment = "left" | "center" | "right" | undefined;

interface MarkdownTableData {
    headers: string[];
    alignments: TableAlignment[];
    rows: string[][];
}

function splitMarkdownTableRow(line: string): string[] {
    const trimmed = line.trim().replace(/^\|/, "").replace(/\|$/, "");
    const cells: string[] = [];
    let current = "";
    let escaped = false;

    for (const char of trimmed) {
        if (escaped) {
            current += char;
            escaped = false;
            continue;
        }
        if (char === "\\") {
            escaped = true;
            continue;
        }
        if (char === "|") {
            cells.push(current.trim());
            current = "";
            continue;
        }
        current += char;
    }

    cells.push(current.trim());
    return cells;
}

function parseMarkdownTable(text: string): MarkdownTableData | undefined {
    const lines = text.replace(/\r\n?/g, "\n").split("\n").filter((line) =>
        line.trim().length > 0
    );

    if (lines.length < 3 || !lines[0].includes("|")) return undefined;

    const headers = splitMarkdownTableRow(lines[0]);
    const separators = splitMarkdownTableRow(lines[1]);

    if (
        headers.length < 2 ||
        separators.length !== headers.length ||
        !separators.every((cell) => /^:?-{3,}:?$/.test(cell.trim()))
    ) {
        return undefined;
    }

    const rows = lines.slice(2).map(splitMarkdownTableRow);
    if (rows.some((row) => row.length !== headers.length)) return undefined;

    return {
        headers,
        alignments: separators.map((cell) => {
            const trimmed = cell.trim();
            if (trimmed.startsWith(":") && trimmed.endsWith(":")) return "center";
            if (trimmed.endsWith(":")) return "right";
            return "left";
        }),
        rows,
    };
}

function MarkdownTable({ table }: { table: MarkdownTableData }) {
    return (
        <table>
            <thead>
                <tr>
                    {table.headers.map((header, i) => (
                        <th
                            key={i}
                            style={{ textAlign: table.alignments[i] }}
                        >
                            <SafeHtml html={header} />
                        </th>
                    ))}
                </tr>
            </thead>
            <tbody>
                {table.rows.map((row, rowIndex) => (
                    <tr key={rowIndex}>
                        {row.map((cell, cellIndex) => (
                            <td
                                key={cellIndex}
                                style={{
                                    textAlign: table.alignments[cellIndex],
                                }}
                            >
                                <SafeHtml html={cell} />
                            </td>
                        ))}
                    </tr>
                ))}
            </tbody>
        </table>
    );
}

function RichText({ text }: { text: string }) {
    const table = parseMarkdownTable(text);
    if (table) return <MarkdownTable table={table} />;

    return HTML_TAG_PATTERN.test(text)
        ? <SafeHtml html={text} />
        : (
            <ReactMarkdown
                remarkPlugins={remarkPlugins}
                components={markdownComponents}
            >
                {normalizeMarkdownText(text)}
            </ReactMarkdown>
        );
}

function renderWithMath(children: ReactNode): ReactNode {
    if (typeof children === "string") {
        return <MathText text={children} />;
    }
    if (Array.isArray(children)) {
        return children.map((child, i) =>
            typeof child === "string"
                ? <MathText key={i} text={child} />
                : child
        );
    }
    return children;
}

const markdownComponents = {
    p: ({ children }: { children?: ReactNode }) => (
        <p>{renderWithMath(children)}</p>
    ),
    li: ({ children }: { children?: ReactNode }) => (
        <li>{renderWithMath(children)}</li>
    ),
    td: ({ children }: { children?: ReactNode }) => (
        <td>{renderWithMath(children)}</td>
    ),
    th: ({ children }: { children?: ReactNode }) => (
        <th>{renderWithMath(children)}</th>
    ),
};

/** Deals with the rendering stuff */
export const ContentBlocks = memo(function ContentBlocks(
    { blocks, className }: { blocks?: ContentBlock[]; className?: string },
) {
    if (!blocks?.length) return null;
    return (
        <div className={`space-y-2 ${className ?? ""}`}>
            {blocks.map((block, i) => {
                switch (block.kind) {
                    case "text":
                        return (
                            <div
                                key={i}
                                className="prose prose-sm max-w-none text-inherit dark:prose-invert [&_p]:whitespace-pre-wrap"
                            >
                                <RichText text={block.text} />
                            </div>
                        );
                    case "image":
                        return (
                            <AssetImage
                                key={i}
                                url={block.url}
                                alt={block.alt}
                                width={block.width}
                                height={block.height}
                            />
                        );
                    case "table":
                        return (
                            <div
                                key={i}
                                className="prose prose-sm max-w-none overflow-x-auto text-inherit dark:prose-invert"
                            >
                                <SafeHtml html={block.html} />
                            </div>
                        );
                }
            })}
        </div>
    );
});

function hasContentBlocks(blocks?: ContentBlock[]): boolean {
    return !!blocks?.some((block) =>
        block.kind !== "text" || block.text.trim().length > 0
    );
}

function hasAnswerValue(answer?: string | QuestionAnswer): boolean {
    if (!answer) return false;
    if (typeof answer === "string") return answer.trim().length > 0;
    return !!(
        answer.option_label ||
        answer.summary?.trim() ||
        hasContentBlocks(answer.content) ||
        answer.alternatives?.some(hasContentBlocks)
    );
}

function hasRubric(rubric?: QuestionRubric): boolean {
    return !!rubric?.criteria.length || hasContentBlocks(rubric?.notes);
}

function AnswerValue({ answer }: { answer?: string | QuestionAnswer }) {
    if (!hasAnswerValue(answer)) return null;
    if (typeof answer === "string") {
        return (
            <div className="space-y-1">
                <p className="font-medium">Answer:</p>
                <RichText text={answer} />
            </div>
        );
    }
    if (!answer) return null;

    return (
        <div className="space-y-2">
            {answer.option_label && (
                <p className="font-medium">
                    Correct option: {answer.option_label}
                </p>
            )}
            {answer.summary && <RichText text={answer.summary} />}
            <ContentBlocks blocks={answer.content} />
            {answer.alternatives?.map((alternative, i) => (
                <div key={i} className="rounded-md border bg-background/60 p-2">
                    <ContentBlocks blocks={alternative} />
                </div>
            ))}
        </div>
    );
}

function RubricBlock({ rubric }: { rubric?: QuestionRubric }) {
    if (!hasRubric(rubric)) return null;

    return (
        <div className="space-y-1">
            <span className="text-xs font-medium text-muted-foreground">
                Marking Criteria
            </span>
            <table className="w-full text-sm">
                <tbody>
                    {rubric?.criteria.map((criterion, i) => (
                        <tr key={i} className="border-b last:border-0">
                            <td className="py-1 pr-2">
                                <ContentBlocks blocks={criterion.description} />
                            </td>
                            <td className="w-12 py-1 text-right font-medium">
                                {criterion.marks ??
                                    `${criterion.min_marks}-${criterion.max_marks}`}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            <ContentBlocks blocks={rubric?.notes} />
        </div>
    );
}

export const Question = memo(function Question(
    { question, onDelete, onEdit, onDuplicate, onChange }: {
        question: QuestionData;
        onDelete?: (id: string) => void;
        onEdit?: (id: string) => void;
        onDuplicate?: (id: string) => void;
        onChange?: (q: QuestionData) => void;
    },
) {
    const [showAnswer, setShowAnswer] = useState(false);
    const [openPartAnswers, setOpenPartAnswers] = useState<Set<string>>(
        () => new Set(),
    );
    const [selectedOption, setSelectedOption] = useState<string | null>(null);
    const [flashLabel, setFlashLabel] = useState<string | null>(null);
    const hasQuestionAnswer =
        hasAnswerValue(question.answer) ||
        hasRubric(question.rubric) ||
        hasContentBlocks(question.guidelines);
    const hasAnswer =
        hasQuestionAnswer ||
        !!question.parts?.some((part) =>
            hasAnswerValue(part.answer) ||
            hasRubric(part.rubric) ||
            hasContentBlocks(part.guidelines)
        );
    const showGroupedPartAnswers = false;

    return (
        <Card>
            <CardHeader className="border-b">
                <CardTitle className="flex items-center justify-between">
                    <span>Question {question.number}</span>
                    <span className="flex items-center gap-1">
                        {question.difficulty && (
                            <Badge variant="outline">
                                {question.difficulty}
                            </Badge>
                        )}
                        <Badge variant="secondary">
                            {question.marks}{" "}
                            {question.marks === 1 ? "mark" : "marks"}
                        </Badge>

                        {/** show answers */}
                        {question.type !== "long_answer" && hasAnswer && (
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => setShowAnswer((v) => !v)}
                                aria-label={showAnswer
                                    ? "Hide answer"
                                    : "Show answer"}
                            >
                                {showAnswer
                                    ? <EyeOff className="size-4" />
                                    : <Eye className="size-4" />}
                            </Button>
                        )}

                        {/** edit */}
                        {onEdit && (
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => onEdit(question.id)}
                            >
                                <Pencil />
                            </Button>
                        )}

                        {/** duplicate */}
                        {onDuplicate && (
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => onDuplicate(question.id)}
                            >
                                <Copy />
                            </Button>
                        )}

                        {/** delete */}
                        {onDelete && (
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => onDelete(question.id)}
                            >
                                <Trash2 />
                            </Button>
                        )}
                    </span>
                </CardTitle>
            </CardHeader>

            <CardContent className="space-y-4">
                {/* Stimulus (text + assets) */}
                <ContentBlocks
                    blocks={question.stimulus}
                    className="text-muted-foreground"
                />

                {/* Question body */}
                <ContentBlocks blocks={question.content} />

                {/* Multiple choice */}
                {question.type === "multiple_choice" && question.options && (
                    <div className="grid gap-2 sm:grid-cols-2">
                        {question.options.map((opt) => {
                            const correctLabel =
                                typeof question.answer === "object"
                                    ? question.answer?.option_label
                                    : typeof question.answer === "string"
                                    ? question.answer
                                    : undefined;
                            const isCorrect = showAnswer &&
                                correctLabel === opt.label;
                            const isSelected = selectedOption === opt.label;

                            return (
                                <div
                                    key={opt.label}
                                    className={`flex gap-3 rounded-md border p-3 cursor-pointer transition-all duration-500 ${
                                        flashLabel === opt.label
                                            ? "border-green-500 bg-green-200 dark:bg-green-900/50"
                                            : isCorrect
                                            ? "border-green-500 bg-green-50 dark:bg-green-950/30"
                                            : isSelected
                                            ? "border-primary bg-primary/5"
                                            : "hover:border-muted-foreground/40"
                                    }`}
                                    onClick={(e) => {
                                        if (e.ctrlKey && onChange) {
                                            // ctrl+click selects answer
                                            const answer =
                                                typeof question.answer ===
                                                        "object"
                                                    ? {
                                                        ...question.answer,
                                                        option_label: opt.label,
                                                    }
                                                    : {
                                                        option_label: opt.label,
                                                    };
                                            onChange({ ...question, answer });
                                            setFlashLabel(opt.label);
                                            setTimeout(
                                                () => setFlashLabel(null),
                                                600,
                                            );
                                        } else {
                                            setSelectedOption((prev) =>
                                                prev === opt.label
                                                    ? null
                                                    : opt.label
                                            );
                                        }
                                    }}
                                >
                                    <span className="font-semibold">
                                        {opt.label}.
                                    </span>
                                    <ContentBlocks blocks={opt.content} />
                                </div>
                            );
                        })}
                    </div>
                )}

                {/* Long answer */}
                {question.type === "long_answer" && question.parts && (
                    <div className="space-y-4">
                        {question.parts.map((part, i) => (
                            <div key={part.label}>
                                {(() => {
                                    const partHasAnswer =
                                        hasAnswerValue(part.answer) ||
                                        hasRubric(part.rubric) ||
                                        hasContentBlocks(part.guidelines);
                                    const partAnswerOpen = openPartAnswers.has(
                                        part.label,
                                    );

                                    return (
                                        <>
                                {i > 0 && part.is_independent && (
                                    <Separator className="mb-4" />
                                )}
                                <div className="flex gap-3">
                                    <span className="font-semibold">
                                        ({part.label})
                                    </span>
                                    <div className="flex-1 space-y-2">
                                        <ContentBlocks blocks={part.stimulus} />
                                        <ContentBlocks blocks={part.content} />
                                    </div>
                                    <span className="flex items-center gap-1">
                                        {part.marks != null && (
                                            <span className="text-sm text-muted-foreground">
                                                {part.marks}{" "}
                                                mark{part.marks === 1
                                                    ? ""
                                                    : "s"}
                                            </span>
                                        )}
                                        {partHasAnswer && (
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="size-8"
                                                onClick={() =>
                                                    setOpenPartAnswers(
                                                        (current) => {
                                                            const next =
                                                                new Set(
                                                                    current,
                                                                );
                                                            if (
                                                                next.has(
                                                                    part.label,
                                                                )
                                                            ) {
                                                                next.delete(
                                                                    part.label,
                                                                );
                                                            } else {
                                                                next.add(
                                                                    part.label,
                                                                );
                                                            }
                                                            return next;
                                                        },
                                                    )}
                                                aria-label={partAnswerOpen
                                                    ? `Hide part ${part.label} answer`
                                                    : `Show part ${part.label} answer`}
                                            >
                                                {partAnswerOpen
                                                    ? (
                                                        <EyeOff className="size-4" />
                                                    )
                                                    : (
                                                        <Eye className="size-4" />
                                                    )}
                                            </Button>
                                        )}
                                    </span>
                                </div>
                                {partAnswerOpen && partHasAnswer && (
                                    <>
                                        <Separator className="my-3 ml-7" />
                                        <div className="ml-7 space-y-2 rounded-md border border-dashed border-green-500/40 bg-green-50/50 p-3 dark:bg-green-950/20">
                                            <AnswerValue answer={part.answer} />
                                            <RubricBlock rubric={part.rubric} />
                                            <ContentBlocks
                                                blocks={part.guidelines}
                                            />
                                        </div>
                                    </>
                                )}
                                        </>
                                    );
                                })()}
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>

            {/* Answer / Rubric / Guidelines — hidden by default */}
            {showAnswer && hasQuestionAnswer && (
                <>
                    <Separator className="my-4" />
                    <div className="space-y-3 rounded-md border border-dashed border-green-500/40 bg-green-50/50 p-3 dark:bg-green-950/20">
                        <span className="text-xs font-semibold uppercase tracking-wide text-green-700 dark:text-green-400">
                            Answer / Marking Guidelines
                        </span>

                        <AnswerValue answer={question.answer} />

                        {/* Rubric criteria */}
                        {question.rubric && (
                            <div className="space-y-1">
                                <span className="text-xs font-medium text-muted-foreground">
                                    Marking Criteria
                                </span>
                                <table className="w-full text-sm">
                                    <tbody>
                                        {question.rubric.criteria.map((
                                            c,
                                            i,
                                        ) => (
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
                                                        `${c.min_marks}–${c.max_marks}`}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                                <ContentBlocks blocks={question.rubric.notes} />
                            </div>
                        )}

                        {/* Guidelines / feedback */}
                        <ContentBlocks blocks={question.guidelines} />

                        {/* Per-part answers for long_answer */}
                        {showGroupedPartAnswers &&
                            question.type === "long_answer" &&
                            question.parts?.some((p) =>
                                p.answer || p.rubric || p.guidelines
                            ) && (
                            <div className="space-y-3 pt-2">
                                {question.parts?.filter((p) =>
                                    p.answer || p.rubric || p.guidelines
                                ).map((part) => (
                                    <div key={part.label} className="space-y-1">
                                        <span className="text-xs font-semibold">
                                            ({part.label})
                                        </span>
                                        {typeof part.answer === "string" && (
                                            <p>{part.answer}</p>
                                        )}
                                        {typeof part.answer === "object" &&
                                            part.answer && (
                                            <div className="space-y-2">
                                                {part.answer.summary && (
                                                    <p>{part.answer.summary}</p>
                                                )}
                                                <ContentBlocks
                                                    blocks={part.answer.content}
                                                />
                                            </div>
                                        )}
                                        {part.rubric && (
                                            <table className="w-full text-sm">
                                                <tbody>
                                                    {part.rubric.criteria.map((
                                                        c,
                                                        i,
                                                    ) => (
                                                        <tr
                                                            key={i}
                                                            className="border-b last:border-0"
                                                        >
                                                            <td className="py-1 pr-2">
                                                                <ContentBlocks
                                                                    blocks={c
                                                                        .description}
                                                                />
                                                            </td>
                                                            <td className="w-12 py-1 text-right font-medium">
                                                                {c.marks ??
                                                                    `${c.min_marks}–${c.max_marks}`}
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        )}
                                        <ContentBlocks
                                            blocks={part.guidelines}
                                        />
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </>
            )}
        </Card>
    );
});
