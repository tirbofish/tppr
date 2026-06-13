import { useState } from "react";
import { ChevronDown, ImageIcon } from "lucide-react";
import { FileUpload, FileUploadDropzone } from "@/components/ui/file-upload";
import { Field, FieldLabel } from "@/components/ui/field";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { paperStore } from "@/lib/paper";
import type { ContentBlock, Question } from "@/types/tppr-paper";
import { firstText, withFirstText } from "./helpers";

export function StimulusSection({ question, onChange }: {
    question: Question;
    onChange: (q: Question) => void;
}) {
    const [open, setOpen] = useState(false);

    async function addImage(file: File) {
        const assetId = await paperStore.saveAsset(question.paper_id, file);
        onChange({
            ...question,
            stimulus: [
                ...(question.stimulus ?? []),
                { kind: "image", url: `asset://${assetId}`, mime_type: file.type },
            ],
        });
    }

    function removeImage(index: number) {
        onChange({
            ...question,
            stimulus: question.stimulus?.filter((_, i) => i !== index),
        });
    }

    const images = (question.stimulus ?? [])
        .map((b, i) => [b, i] as const)
        .filter((entry): entry is [Extract<ContentBlock, { kind: "image" }>, number] =>
            entry[0].kind === "image"
        );

    return (
        <section className="rounded-md border">
            <button
                type="button"
                className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium"
                onClick={() => setOpen(!open)}
            >
                Stimulus
                <ChevronDown
                    className={`size-4 transition-transform ${open ? "rotate-180" : ""}`}
                />
            </button>

            {open && (
                <div
                    className="space-y-4 border-t p-3"
                    // Paste an image anywhere inside the section
                    onPaste={(e) => {
                        const file = Array.from(e.clipboardData.files).find((f) =>
                            f.type.startsWith("image/")
                        );
                        if (file) {
                            e.preventDefault();
                            addImage(file);
                        }
                    }}
                >
                    <Field>
                        <FieldLabel htmlFor="q-stimulus">Stimulus text</FieldLabel>
                        <Textarea
                            id="q-stimulus"
                            value={firstText(question.stimulus)}
                            onChange={(e) =>
                                onChange({
                                    ...question,
                                    stimulus: withFirstText(
                                        question.stimulus,
                                        e.target.value,
                                    ),
                                })}
                        />
                    </Field>

                    {/* Click, drag+drop, or paste */}
                    <FileUpload
                        accept="image/*"
                        onAccept={(files) => files[0] && addImage(files[0])}
                    >
                        <FileUploadDropzone>
                            <ImageIcon className="size-6 text-muted-foreground" />
                            <p className="text-sm font-medium">
                                Drop, paste, or click to add an image
                            </p>
                        </FileUploadDropzone>
                    </FileUpload>

                    {/* Existing images */}
                    {images.map(([img, i]) => (
                        <div key={i} className="flex items-center justify-between rounded-md border p-2 text-sm">
                            <span className="truncate text-muted-foreground">{img.url}</span>
                            <Button
                                type="button"
                                variant="ghost"
                                size="sm"
                                onClick={() => removeImage(i)}
                            >
                                Remove
                            </Button>
                        </div>
                    ))}
                </div>
            )}
        </section>
    );
}