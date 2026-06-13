import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { paperStore } from "@/lib/paper";
import type {
    ChoiceOption,
    ContentBlock,
    Question,
    QuestionType,
} from "@/types/tppr-paper";

export function optionLabel(index: number): string {
    return String.fromCharCode(65 + index);
}

export function defaultOptions(count = 4): ChoiceOption[] {
    return Array.from({ length: count }, (_, i) => ({
        label: optionLabel(i),
        content: [{ kind: "text", text: "" }],
    }));
}

/** Re-letters options A, B, C… after add/remove. */
export function relabelOptions(options: ChoiceOption[]): ChoiceOption[] {
    return options.map((opt, i) => ({ ...opt, label: optionLabel(i) }));
}

/** Reads the first text block's text (or ""). */
export function firstText(blocks?: ContentBlock[]): string {
    const block = blocks?.find((b) => b.kind === "text");
    return block?.kind === "text" ? block.text : "";
}

/** Returns blocks with the first text block replaced (or prepended). */
export function withFirstText(blocks: ContentBlock[] | undefined, text: string): ContentBlock[] {
    const next = [...(blocks ?? [])];
    const i = next.findIndex((b) => b.kind === "text");
    if (i === -1) next.unshift({ kind: "text", text });
    else next[i] = { kind: "text", text };
    return next;
}