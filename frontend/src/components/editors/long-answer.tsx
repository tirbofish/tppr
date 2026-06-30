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
import {
    addPartAtPath,
    compoundLabel,
    isLeaf,
    MAX_PARTS,
    newLeafPart,
    relabelParts,
    removePartAtPath,
    sumQuestionMarks,
    totalPartMarks,
    updatePartAtPath,
} from "@/lib/parts";

/** Navigate to the part at `path` (list of sibling indices). */
function partAtPath(parts: QuestionPart[], path: number[]): QuestionPart | undefined {
    let cursor: QuestionPart[] = parts;
    let part: QuestionPart | undefined;
    for (const i of path) {
        part = cursor[i];
        if (!part) return undefined;
        cursor = part.parts ?? [];
    }
    return part;
}

/** Recursively drop now-empty `parts` arrays (containers with no children revert to leaves). */
function pruneEmpty(parts: QuestionPart[]): QuestionPart[] {
    return parts.map((p) => {
        if (!p.parts) return p;
        const sub = pruneEmpty(p.parts);
        return sub.length ? { ...p, parts: sub } : { ...p, parts: undefined };
    });
}

function defaultParts(count = 2): QuestionPart[] {
    return relabelParts(
        Array.from({ length: count }, () => newLeafPart()),
        1,
    );
}

/** Stimulus field, reused at every nesting depth. */
function PartStimulusField({
    part,
    path,
    question,
    onPatch,
}: {
    part: QuestionPart;
    path: number[];
    question: Question;
    onPatch: (path: number[], patch: Partial<QuestionPart>) => void;
}) {
    const fieldId = `part-${path.join("-")}-stimulus`;
    return (
        <Field>
            <FieldLabel htmlFor={fieldId}>Stimulus</FieldLabel>
            <Textarea
                id={fieldId}
                value={firstText(part.stimulus)}
                onChange={(e) =>
                    onPatch(path, {
                        stimulus: withFirstText(part.stimulus, e.target.value),
                    })}
                onPaste={(e) => {
                    const file = Array.from(e.clipboardData.files)
                        .find((f) => f.type.startsWith("image/"));
                    if (file) {
                        e.preventDefault();
                        paperStore.saveAsset(question.paper_id, file).then((assetId) => {
                            void syncService.uploadAsset(question.paper_id, assetId);
                            onPatch(path, {
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
                    if (!files[0]) return;
                    paperStore.saveAsset(question.paper_id, files[0]).then((assetId) => {
                        void syncService.uploadAsset(question.paper_id, assetId);
                        onPatch(path, {
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
                .filter(
                    (entry): entry is [
                        Extract<ContentBlock, { kind: "image" }>,
                        number,
                    ] => entry[0].kind === "image",
                )
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
                                onPatch(path, {
                                    stimulus: part.stimulus?.filter((_, j) => j !== idx),
                                })}
                        >
                            Remove
                        </Button>
                    </div>
                ))}
        </Field>
    );
}

/** Sample answer + worked solution, for leaf parts. */
function PartAnswerFields({
    part,
    path,
    onPatch,
}: {
    part: QuestionPart;
    path: number[];
    onPatch: (path: number[], patch: Partial<QuestionPart>) => void;
}) {
    return (
        <>
            <Field>
                <div className="flex items-center justify-between gap-2">
                    <FieldLabel htmlFor={`part-${path.join("-")}-answer-summary`}>
                        Sample answer
                    </FieldLabel>
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        disabled={!part.answer}
                        onClick={() => onPatch(path, { answer: undefined })}
                    >
                        <X /> Clear
                    </Button>
                </div>
                <Textarea
                    id={`part-${path.join("-")}-answer-summary`}
                    value={answerSummary(part.answer)}
                    onChange={(e) =>
                        onPatch(path, {
                            answer: withAnswerSummary(part.answer, e.target.value),
                        })}
                />
            </Field>
            <Field>
                <FieldLabel htmlFor={`part-${path.join("-")}-answer-working`}>
                    Worked solution / marking notes
                </FieldLabel>
                <Textarea
                    id={`part-${path.join("-")}-answer-working`}
                    value={answerContentText(part.answer)}
                    onChange={(e) =>
                        onPatch(path, {
                            answer: withAnswerContentText(part.answer, e.target.value),
                        })}
                />
            </Field>
        </>
    );
}

function PartEditor({
    question,
    parts,
    path,
    depth,
    onPatch,
    onAddChild,
    onRemove,
}: {
    question: Question;
    parts: QuestionPart[];
    path: number[];
    depth: number;
    onPatch: (path: number[], patch: Partial<QuestionPart>) => void;
    onAddChild: (containerPath: number[]) => void;
    onRemove: (path: number[]) => void;
}) {
    const part = partAtPath(parts, path);
    if (!part) return null;
    const leaf = isLeaf(part);
    const label = compoundLabel(question, path, parts);
    const children = part.parts ?? [];
    const canRemove = !(path.length === 1 && parts.length <= 1);
    const childCount = children.length;
    const canAddChild = childCount < MAX_PARTS;

    return (
        <div className="space-y-3 rounded-md border p-3">
            <div className="flex items-center justify-between">
                <span className="text-sm font-semibold">
                    {depth === 1 ? "Part" : "Sub-part"} ({label})
                </span>
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    disabled={!canRemove}
                    onClick={() => onRemove(path)}
                >
                    <X />
                </Button>
            </div>

            <PartStimulusField
                part={part}
                path={path}
                question={question}
                onPatch={onPatch}
            />

            <Field>
                <FieldLabel htmlFor={`part-${path.join("-")}-content`}>
                    {leaf ? "Question text" : "Intro text (optional)"}
                </FieldLabel>
                <Textarea
                    id={`part-${path.join("-")}-content`}
                    value={firstText(part.content)}
                    onChange={(e) =>
                        onPatch(path, {
                            content: withFirstText(part.content, e.target.value),
                        })}
                />
            </Field>

            <div className="flex items-center gap-6">
                <Field className="w-24">
                    <FieldLabel htmlFor={`part-${path.join("-")}-marks`}>
                        Marks
                    </FieldLabel>
                    {leaf
                        ? (
                            <Input
                                id={`part-${path.join("-")}-marks`}
                                type="number"
                                min={1}
                                value={part.marks ?? 1}
                                onChange={(e) =>
                                    onPatch(path, {
                                        marks: Number(e.target.value),
                                    })}
                            />
                        )
                        : (
                            <Input
                                id={`part-${path.join("-")}-marks`}
                                type="number"
                                readOnly
                                disabled
                                value={totalPartMarks(part)}
                            />
                        )}
                </Field>

                <label
                    htmlFor={`part-${path.join("-")}-independent`}
                    className="flex items-center gap-2 pt-5 text-sm"
                >
                    <input
                        id={`part-${path.join("-")}-independent`}
                        type="checkbox"
                        className="size-4 accent-primary"
                        checked={part.is_independent ?? false}
                        onChange={(e) =>
                            onPatch(path, {
                                is_independent: e.target.checked,
                            })}
                    />
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <span>Is independent?</span>
                            </TooltipTrigger>
                            <TooltipContent className="max-w-xs">
                                An independent part stands alone from the previous
                                parts' context. Together with the root stimulus, it
                                can be treated as its own question. For example, when
                                another user selects individual questions from this
                                paper.
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>
                </label>
            </div>

            {leaf && (
                <>
                    <Separator />
                    <PartAnswerFields part={part} path={path} onPatch={onPatch} />
                </>
            )}

            {!leaf && (
                <div className="ml-4 space-y-3 border-l border-border pl-3">
                    {children.map((_, ci) => (
                        <PartEditor
                            key={ci}
                            question={question}
                            parts={parts}
                            path={[...path, ci]}
                            depth={depth + 1}
                            onPatch={onPatch}
                            onAddChild={onAddChild}
                            onRemove={onRemove}
                        />
                    ))}
                </div>
            )}

            <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={!canAddChild}
                onClick={() => onAddChild(path)}
            >
                <Plus /> Add sub-part
            </Button>
        </div>
    );
}

export function LongAnswerEditor({ question, onChange }: {
    question: Question;
    onChange: (q: Question) => void;
}) {
    const parts = question.parts ?? defaultParts();

    function commit(next: QuestionPart[]) {
        const relabeled = relabelParts(next, 1);
        const marks = sumQuestionMarks({ ...question, parts: relabeled });
        onChange({ ...question, parts: relabeled, marks });
    }

    function patchPart(path: number[], patch: Partial<QuestionPart>) {
        commit(updatePartAtPath(parts, path, patch));
    }

    function removePart(path: number[]) {
        if (path.length === 1 && parts.length <= 1) return;
        commit(pruneEmpty(removePartAtPath(parts, path)));
    }

    function addChild(containerPath: number[]) {
        const container = partAtPath(parts, containerPath);
        const wasLeaf = container ? isLeaf(container) : false;
        let next = addPartAtPath(parts, containerPath, newLeafPart());
        if (wasLeaf) {
            // A container has no standalone answer of its own.
            next = updatePartAtPath(next, containerPath, {
                answer: undefined,
                rubric: undefined,
                guidelines: undefined,
            });
        }
        commit(next);
    }

    function addTopPart() {
        if (parts.length >= MAX_PARTS) return;
        commit([...parts, newLeafPart()]);
    }

    return (
        <div className="space-y-4">
            {parts.map((_, i) => (
                <PartEditor
                    key={i}
                    question={question}
                    parts={parts}
                    path={[i]}
                    depth={1}
                    onPatch={patchPart}
                    onAddChild={addChild}
                    onRemove={removePart}
                />
            ))}

            <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={parts.length >= MAX_PARTS}
                onClick={addTopPart}
            >
                <Plus /> Add part
            </Button>
        </div>
    );
}