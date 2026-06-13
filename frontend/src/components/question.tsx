// frontend/src/components/question.tsx
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { paperStore } from "@/lib/paper";
import type {
    ContentBlock,
    Question as QuestionData,
} from "@/types/tppr-paper";
import { Copy, Pencil, Trash2 } from "lucide-react";
import { Button } from "./ui/button";
import { MathText } from "./math-text";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Resolves asset:// URLs from IndexedDB to object URLs. */
function useAssetUrl(url: string): string | undefined {
    const [resolved, setResolved] = useState<string>();
    useEffect(() => {
        if (!url.startsWith("asset://")) {
            setResolved(url);
            return;
        }
        let objectUrl: string | undefined;
        paperStore.getAsset(url.slice("asset://".length)).then((asset) => {
            if (asset) {
                objectUrl = URL.createObjectURL(asset.blob);
                setResolved(objectUrl);
            }
        });
        return () => {
            if (objectUrl) URL.revokeObjectURL(objectUrl);
        };
    }, [url]);
    return resolved;
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

function renderWithMath(children: React.ReactNode): React.ReactNode {
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

/** Deals with the rendering stuff */
export function ContentBlocks(
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
                                className="prose prose-sm max-w-none dark:prose-invert [&_p]:whitespace-pre-wrap text-inherit"
                            >
                                <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    components={{
                                        p: ({ children }) => (
                                            <p>{renderWithMath(children)}</p>
                                        ),
                                        li: ({ children }) => (
                                            <li>{renderWithMath(children)}</li>
                                        ),
                                        td: ({ children }) => (
                                            <td>{renderWithMath(children)}</td>
                                        ),
                                        th: ({ children }) => (
                                            <th>{renderWithMath(children)}</th>
                                        ),
                                    }}
                                >
                                    {block.text}
                                </ReactMarkdown>
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
                }
            })}
        </div>
    );
}

export function Question(
    { question, onChange, onDelete, onEdit, onDuplicate }: {
        question: QuestionData;
        onChange?: (q: QuestionData) => void;
        onDelete?: () => void;
        onEdit?: () => void;
        onDuplicate?: () => void;
    },
) {
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
                        {onEdit && (
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={onEdit}
                            >
                                <Pencil />
                            </Button>
                        )}
                        {onDuplicate && (
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={onDuplicate}
                            >
                                <Copy />
                            </Button>
                        )}
                        {onDelete && (
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={onDelete}
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

                {/* Multiple choice: options A–D */}
                {question.type === "multiple_choice" && question.options && (
                    <div className="grid gap-2 sm:grid-cols-2">
                        {question.options.map((opt) => (
                            <div
                                key={opt.label}
                                className="flex gap-3 rounded-md border p-3"
                            >
                                <span className="font-semibold">
                                    {opt.label}.
                                </span>
                                <ContentBlocks blocks={opt.content} />
                            </div>
                        ))}
                    </div>
                )}

                {/* Long answer: parts a, b, c… */}
                {question.type === "long_answer" && question.parts && (
                    <div className="space-y-4">
                        {question.parts.map((part, i) => (
                            <div key={part.label}>
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
                                    {part.marks != null && (
                                        <span className="text-sm text-muted-foreground">
                                            {part.marks}{" "}
                                            mark{part.marks === 1 ? "" : "s"}
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </CardContent>
        </Card>
    );
}
