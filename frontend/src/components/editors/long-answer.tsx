import { ImageIcon, Plus, X } from "lucide-react";
import type { ContentBlock, Question, QuestionPart } from "@/types/tppr-paper";
import { Button } from "../ui/button";
import { Field, FieldLabel } from "../ui/field";
import { Input } from "../ui/input";
import { Separator } from "../ui/separator";
import { Textarea } from "../ui/textarea";
import {
    answerContentText,
    answerSummary,
    firstText,
    withAnswerContentText,
    withAnswerSummary,
    withFirstText,
} from "./helpers";
import {
    Tooltip,
    TooltipContent,
    TooltipProvider,
    TooltipTrigger,
} from "../ui/tooltip";
import { FileUpload, FileUploadDropzone } from "../ui/file-upload";
import { paperStore } from "@/lib/paper";
import { syncService } from "@/lib/cloud";

const MIN_PARTS = 1;
const MAX_PARTS = 8;

/** a, b, c ... */
function partLabel(index: number): string {
    return String.fromCharCode(97 + index);
}

function defaultParts(count = 2): QuestionPart[] {
    return Array.from({ length: count }, (_, i) => ({
        label: partLabel(i),
        content: [{ kind: "text", text: "" }],
        marks: 1,
    }));
}

/** Re-letters parts a, b, c… after add/remove. */
function relabelParts(parts: QuestionPart[]): QuestionPart[] {
    return parts.map((p, i) => ({ ...p, label: partLabel(i) }));
}

/** Sum of part marks, for keeping question.marks in sync. */
function totalPartMarks(parts: QuestionPart[]): number {
    return parts.reduce((sum, p) => sum + (p.marks ?? 0), 0);
}

export function LongAnswerEditor({ question, onChange }: {
    question: Question;
    onChange: (q: Question) => void;
}) {
    const parts = question.parts ?? defaultParts();

    function setParts(next: QuestionPart[]) {
        onChange({
            ...question,
            parts: next,

            marks: totalPartMarks(next),
        });
    }

    function updatePart(index: number, patch: Partial<QuestionPart>) {
        setParts(parts.map((p, i) => (i === index ? { ...p, ...patch } : p)));
    }

    function addPart() {
        if (parts.length >= MAX_PARTS) return;
        setParts(relabelParts([
            ...parts,
            { label: "", content: [{ kind: "text", text: "" }], marks: 1 },
        ]));
    }

    function removePart(index: number) {
        if (parts.length <= MIN_PARTS) return;
        setParts(relabelParts(parts.filter((_, i) => i !== index)));
    }

    return (
        <div className="space-y-4">
            {parts.map((part, i) => (
                <div key={i} className="space-y-3 rounded-md border p-3">
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold">
                            Part ({part.label})
                        </span>
                        <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            disabled={parts.length <= MIN_PARTS}
                            onClick={() =>
                                removePart(i)}
                        >
                            <X />
                        </Button>
                    </div>

                    <Field>
                        <FieldLabel htmlFor={`part-${i}-stimulus`}>
                            Stimulus
                        </FieldLabel>
                        <Textarea
                            id={`part-${i}-stimulus`}
                            value={firstText(part.stimulus)}
                            onChange={(e) =>
                                updatePart(i, {
                                    stimulus: withFirstText(
                                        part.stimulus,
                                        e.target.value,
                                    ),
                                })}
                            onPaste={(e) => {
                                const file = Array.from(e.clipboardData.files)
                                    .find((f) =>
                                        f.type.startsWith("image/")
                                    );
                                if (file) {
                                    e.preventDefault();
                                    paperStore.saveAsset(
                                        question.paper_id,
                                        file,
                                    ).then((assetId) => {
                                        void syncService.uploadAsset(
                                            question.paper_id,
                                            assetId,
                                        );
                                        updatePart(i, {
                                            stimulus: [
                                                ...(part.stimulus ?? []),
                                                {
                                                    kind: "image",
                                                    url: `asset://${assetId}`,
                                                    mime_type: file.type,
                                                },
                                            ],
                                        });
                                    });
                                }
                            }}
                        />
                        <FileUpload
                            accept="image/*"
                            onAccept={(files) => {
                                if (!files[0]) {
                                    return;
                                }
                                paperStore.saveAsset(
                                    question.paper_id,
                                    files[0],
                                ).then((assetId) => {
                                    void syncService.uploadAsset(
                                        question.paper_id,
                                        assetId,
                                    );
                                    updatePart(i, {
                                        stimulus: [
                                            ...(part.stimulus ?? []),
                                            {
                                                kind: "image",
                                                url: `asset://${assetId}`,
                                                mime_type: files[0].type,
                                            },
                                        ],
                                    });
                                });
                            }}
                        >
                            <FileUploadDropzone className="py-2">
                                <ImageIcon className="size-4 text-muted-foreground" />
                                <p className="text-xs text-muted-foreground">
                                    Drop, paste or click to add an image
                                </p>
                            </FileUploadDropzone>
                        </FileUpload>
                        {(part.stimulus ?? [])
                            .map((b, idx) => [b, idx] as const)
                            .filter((
                                entry,
                            ): entry is [
                                Extract<ContentBlock, { kind: "image" }>,
                                number,
                            ] => entry[0].kind === "image")
                            .map(([img, idx]) => (
                                <div
                                    key={idx}
                                    className="flex items-center justify-between rounded-md border p-2 text-xs"
                                >
                                    <span className="truncate text-muted-foreground">
                                        {img.url}
                                    </span>
                                    <Button
                                        type="button"
                                        variant="ghost"
                                        size="sm"
                                        onClick={() =>
                                            updatePart(i, {
                                                stimulus: part.stimulus?.filter(
                                                    (_, j) => j !== idx,
                                                ),
                                            })}
                                    >
                                        Remove
                                    </Button>
                                </div>
                            ))}
                    </Field>

                    <Field>
                        <FieldLabel htmlFor={`part-${i}-content`}>
                            Question text
                        </FieldLabel>
                        <Textarea
                            id={`part-${i}-content`}
                            value={firstText(part.content)}
                            onChange={(e) =>
                                updatePart(i, {
                                    content: withFirstText(
                                        part.content,
                                        e.target.value,
                                    ),
                                })}
                        />
                    </Field>

                    <div className="flex items-center gap-6">
                        <Field className="w-24">
                            <FieldLabel htmlFor={`part-${i}-marks`}>
                                Marks
                            </FieldLabel>
                            <Input
                                id={`part-${i}-marks`}
                                type="number"
                                min={1}
                                value={part.marks ?? 1}
                                onChange={(e) =>
                                    updatePart(i, {
                                        marks: Number(e.target.value),
                                    })}
                            />
                        </Field>

                        <label
                            htmlFor={`part-${i}-independent`}
                            className="flex items-center gap-2 pt-5 text-sm"
                        >
                            <input
                                id={`part-${i}-independent`}
                                type="checkbox"
                                className="size-4 accent-primary"
                                checked={part.is_independent ?? false}
                                onChange={(e) =>
                                    updatePart(i, {
                                        is_independent: e.target.checked,
                                    })}
                            />
                            <TooltipProvider>
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <span>Is independent?</span>
                                    </TooltipTrigger>
                                    <TooltipContent className="max-w-xs">
                                        An independent part stands alone from
                                        the previous parts' context. Together
                                        with the root stimulus, it can be
                                        treated as its own question. For
                                        example, when another user selects
                                        individual questions from this paper.
                                    </TooltipContent>
                                </Tooltip>
                            </TooltipProvider>
                        </label>
                    </div>

                    <Separator />

                    <Field>
                        <div className="flex items-center justify-between gap-2">
                            <FieldLabel htmlFor={`part-${i}-answer-summary`}>
                                Sample answer
                            </FieldLabel>
                            <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                disabled={!part.answer}
                                onClick={() =>
                                    updatePart(i, { answer: undefined })}
                            >
                                <X /> Clear
                            </Button>
                        </div>
                        <Textarea
                            id={`part-${i}-answer-summary`}
                            value={answerSummary(part.answer)}
                            onChange={(e) =>
                                updatePart(i, {
                                    answer: withAnswerSummary(
                                        part.answer,
                                        e.target.value,
                                    ),
                                })}
                        />
                    </Field>

                    <Field>
                        <FieldLabel htmlFor={`part-${i}-answer-working`}>
                            Worked solution / marking notes
                        </FieldLabel>
                        <Textarea
                            id={`part-${i}-answer-working`}
                            value={answerContentText(part.answer)}
                            onChange={(e) =>
                                updatePart(i, {
                                    answer: withAnswerContentText(
                                        part.answer,
                                        e.target.value,
                                    ),
                                })}
                        />
                    </Field>
                </div>
            ))}

            <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={parts.length >= MAX_PARTS}
                onClick={addPart}
            >
                <Plus /> Add part
            </Button>
        </div>
    );
}
