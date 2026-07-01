import type {
    ChoiceOption,
    ContentBlock,
    QuestionAnswer,
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

type AnswerValue = string | QuestionAnswer | null | undefined;

function hasBlocks(blocks?: ContentBlock[]): boolean {
    return !!blocks?.some((block) =>
        block.kind !== "text" || block.text.trim().length > 0
    );
}

function toStructuredAnswer(answer: AnswerValue): QuestionAnswer {
    return typeof answer === "object" && answer
        ? answer
        : typeof answer === "string" && answer
        ? { summary: answer }
        : {};
}

function compactAnswer(answer: QuestionAnswer): QuestionAnswer | undefined {
    const next: QuestionAnswer = {
        ...answer,
        summary: answer.summary?.trim() ? answer.summary : undefined,
        content: hasBlocks(answer.content) ? answer.content : undefined,
        alternatives: answer.alternatives?.length ? answer.alternatives : undefined,
    };

    return next.option_label || next.summary || next.content || next.alternatives
        ? next
        : undefined;
}

export function answerOptionLabel(answer: AnswerValue): string {
    return typeof answer === "object" && answer != null
        ? answer.option_label ?? ""
        : "";
}

export function answerSummary(answer: AnswerValue): string {
    return typeof answer === "string" ? answer : answer?.summary ?? "";
}

export function answerContentText(answer: AnswerValue): string {
    return typeof answer === "object" && answer != null ? firstText(answer.content) : "";
}

export function withAnswerOptionLabel(
    answer: AnswerValue,
    optionLabel: string,
): QuestionAnswer | undefined {
    return compactAnswer({
        ...(typeof answer === "object" && answer ? answer : {}),
        option_label: optionLabel,
    });
}

export function withAnswerSummary(
    answer: AnswerValue,
    summary: string,
): QuestionAnswer | undefined {
    return compactAnswer({
        ...toStructuredAnswer(answer),
        summary,
    });
}

export function withAnswerContentText(
    answer: AnswerValue,
    text: string,
): QuestionAnswer | undefined {
    const existing = toStructuredAnswer(answer);
    return compactAnswer({
        ...existing,
        content: text.trim() ? withFirstText(existing.content, text) : undefined,
    });
}
