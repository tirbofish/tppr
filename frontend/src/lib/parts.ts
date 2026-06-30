import type { Question, QuestionPart } from "@/types/tppr-paper";

/** Minimum siblings per part group; maximum siblings per part group. */
export const MIN_PARTS = 1;
export const MAX_PARTS = 8;

/**
 * Pure helpers for arbitrarily-nested LAQ sub-parts. Parts nest via
 * `QuestionPart.parts`; a part with no `parts` is a leaf. Compound numbering
 * like "1.a.i" is derived from the question number plus the path of part
 * labels — `label` stores only the leaf segment.
 */

// --- label schemes (cycled per depth) --------------------------------------

/** Bijective base-26 letters: 0->a, 1->b, …, 25->z, 26->aa, 27->ab, … */
function toLetters(n: number, upper = false): string {
    let s = "";
    let i = n;
    do {
        s = String.fromCharCode((upper ? 65 : 97) + (i % 26)) + s;
        i = Math.floor(i / 26) - 1;
    } while (i >= 0);
    return s;
}

/** Lowercase roman numeral for n >= 1. */
function toRoman(n: number, upper = false): string {
    if (n < 1) return "";
    const table: [number, string][] = [
        [1000, "M"], [900, "CM"], [500, "D"], [400, "CD"],
        [100, "C"], [90, "XC"], [50, "L"], [40, "XL"],
        [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"],
    ];
    let s = "";
    let rem = n;
    for (const [value, glyph] of table) {
        while (rem >= value) {
            s += glyph;
            rem -= value;
        }
    }
    return upper ? s : s.toLowerCase();
}

/**
 * Leaf label segment for a part at `depth` (1-based) with sibling `index`
 * (0-based). Schemes cycle every five levels:
 *   1 -> a, b, c …  |  2 -> i, ii, iii …  |  3 -> 1, 2, 3 …
 *   4 -> A, B, C …  |  5 -> I, II, III …  |  6+ repeats.
 */
export function labelForDepth(depth: number, index: number): string {
    const scheme = ((depth - 1) % 5 + 5) % 5;
    switch (scheme) {
        case 0:
            return toLetters(index, false); // a, b, c
        case 1:
            return toRoman(index + 1, false); // i, ii, iii
        case 2:
            return String(index + 1); // 1, 2, 3
        case 3:
            return toLetters(index, true); // A, B, C
        case 4:
        default:
            return toRoman(index + 1, true); // I, II, III
    }
}

/** Recompute `label` for every part in the tree by depth + sibling index. */
export function relabelParts(parts: QuestionPart[], depth = 1): QuestionPart[] {
    return parts.map((part, i) => ({
        ...part,
        label: labelForDepth(depth, i),
        parts: part.parts ? relabelParts(part.parts, depth + 1) : part.parts,
    }));
}

// --- structure / marks -----------------------------------------------------

export function isLeaf(part: QuestionPart): boolean {
    return !part.parts || part.parts.length === 0;
}

/** Marks for a part: its own marks if a leaf, else the recursive sum of children. */
export function totalPartMarks(part: QuestionPart): number {
    if (isLeaf(part)) return part.marks ?? 0;
    return (part.parts ?? []).reduce((sum, child) => sum + totalPartMarks(child), 0);
}

/** Total marks for a question (recursive sum of leaf marks for LAQ). */
export function sumQuestionMarks(q: Question): number {
    if (q.type !== "long_answer") return q.marks;
    return (q.parts ?? []).reduce((sum, p) => sum + totalPartMarks(p), 0);
}

/** A fresh default leaf part. */
export function newLeafPart(): QuestionPart {
    return { label: "", content: [{ kind: "text", text: "" }], marks: 1 };
}

// --- compound labels -------------------------------------------------------

/** Compound label for a part reached via `path` (list of sibling indices). */
export function compoundLabel(
    q: Question,
    path: number[],
    parts: QuestionPart[],
): string {
    const segments: string[] = [String(q.number)];
    let cursor = parts;
    for (const i of path) {
        const part = cursor[i];
        if (!part) break;
        segments.push(part.label);
        cursor = part.parts ?? [];
    }
    return segments.join(".");
}

export interface LeafNode {
    /** Path of sibling indices from the top-level part down to the leaf. */
    path: number[];
    leaf: QuestionPart;
    /** Compound label, e.g. "1.a.i". */
    label: string;
}

/** Flatten a question's part tree into one entry per leaf, in document order. */
export function flattenLeaves(q: Question): LeafNode[] {
    const out: LeafNode[] = [];
    const walk = (parts: QuestionPart[], prefix: number[]) => {
        parts.forEach((part, i) => {
            const path = [...prefix, i];
            if (isLeaf(part)) {
                out.push({ path, leaf: part, label: compoundLabel(q, path, q.parts ?? []) });
            } else {
                walk(part.parts ?? [], path);
            }
        });
    };
    walk(q.parts ?? [], []);
    return out;
}

// --- immutable tree operations (path = list of sibling indices) -----------

export function updatePartAtPath(
    parts: QuestionPart[],
    path: number[],
    patch: Partial<QuestionPart>,
): QuestionPart[] {
    const [i, ...rest] = path;
    if (i === undefined) return parts;
    return parts.map((part, idx) => {
        if (idx !== i) return part;
        if (rest.length === 0) return { ...part, ...patch };
        return { ...part, parts: updatePartAtPath(part.parts ?? [], rest, patch) };
    });
}

export function removePartAtPath(
    parts: QuestionPart[],
    path: number[],
): QuestionPart[] {
    const [i, ...rest] = path;
    if (i === undefined) return parts;
    if (rest.length === 0) return parts.filter((_, idx) => idx !== i);
    return parts.map((part, idx) =>
        idx === i ? { ...part, parts: removePartAtPath(part.parts ?? [], rest) } : part,
    );
}

/** Append `newPart` as a new child of the container at `path`
 *  (an empty `path` appends to the top-level parts array). */
export function addPartAtPath(
    parts: QuestionPart[],
    path: number[],
    newPart: QuestionPart,
): QuestionPart[] {
    if (path.length === 0) return [...parts, newPart];
    const [i, ...rest] = path;
    return parts.map((part, idx) => {
        if (idx !== i) return part;
        if (rest.length === 0) {
            return { ...part, parts: [...(part.parts ?? []), newPart] };
        }
        return { ...part, parts: addPartAtPath(part.parts ?? [], rest, newPart) };
    });
}