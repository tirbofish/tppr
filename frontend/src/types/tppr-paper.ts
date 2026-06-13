// Generated from docs/tppr-paper-meta.json, tppr-paper.json, tppr-question.json
// CONVERSION MADE WITH AI

// ---------- Shared enums ----------

export type PaperSource = "hsc" | "trial" | "internal" | "practice" | "custom";

export type CourseLevel =
    | "standard"
    | "advanced"
    | "extension_1"
    | "extension_2";

export type Visibility = "private" | "public";

export type QuestionType = "multiple_choice" | "short_answer" | "long_answer";

export type Difficulty = "easy" | "medium" | "hard";

// ---------- Content blocks (tppr-question.json $defs) ----------

export interface TextBlock {
    kind: "text";
    text: string;
}

export interface ImageBlock {
    kind: "image";
    url: string;
    mime_type?: string;
    alt?: string;
    /** Display width in pixels. */
    width?: number;
    /** Display height in pixels. */
    height?: number;
}

export interface TableBlock {
    kind: "table";
    html: string;
}

export type ContentBlock = TextBlock | ImageBlock | TableBlock;

// ---------- Question sub-structures ----------

/** A reference to a specific syllabus dot point. */
export interface SyllabusPoint {
    /** e.g. "hsc-physics-2025" */
    syllabus_id: string;
    /** e.g. "PH12-4.1.3" */
    point_code: string;
    label?: string;
}

export interface ChoiceOption {
    /** Option letter (A, B, C, D, etc.). */
    label: string;
    content: ContentBlock[];
}

/** A sub-part of a question (e.g. part a, b, c). */
export interface QuestionPart {
    /** Part label (e.g. "a", "b", "ii"). */
    label: string;
    stimulus?: ContentBlock[];
    content: ContentBlock[];
    marks?: number;
    /** True if this part stands alone from the previous part's context. */
    is_independent?: boolean;
}

// ---------- Question (tppr-question.json) ----------

export interface Question {
    id: string;
    paper_id: string;
    author_id: string;
    /** Question number within the paper (1-based). */
    number: number;
    type: QuestionType;
    marks: number;
    /** Stimulus material shown before the question. */
    stimulus?: ContentBlock[];
    /** The question body content. */
    content?: ContentBlock[];
    /** Sub-parts if the question is multi-part. */
    parts?: QuestionPart[];
    /** Answer choices (for multiple_choice type). */
    options?: ChoiceOption[];
    /** Correct answer label or short text (author-only). */
    answer?: string;
    /** Topic tags, e.g. ["kinematics", "projectile motion"]. */
    topics?: string[];
    syllabus_points?: SyllabusPoint[];
    difficulty?: Difficulty;
    created_at: string;
    updated_at: string;
}

// ---------- Paper metadata (tppr-paper-meta.json) ----------

/** Minimal paper metadata for listing, searching, and previews. */
export interface PaperMeta {
    id: string;
    title: string;
    author_id: string;
    /** e.g. "Physics", "Mathematics" */
    subject: string;
    year?: number;
    source?: PaperSource;
    /** School name, relevant for trial/internal papers. */
    school?: string;
    /** Course level tier, applicable to Mathematics and English. */
    course_level?: CourseLevel;
    /** Aggregate topic tags across all questions. */
    topics?: string[];
    visibility: Visibility;
    question_count: number;
    total_marks: number;
    duration_minutes?: number;
    created_at: string;
    updated_at: string;
    remixed?: string;
}

// ---------- Full paper (tppr-paper.json) ----------

/** Full paper: metadata plus the complete list of questions. */
export interface Paper {
    id: string;
    title: string;
    author_id: string;
    subject: string;
    /** Primary syllabus this paper targets (e.g. "hsc-physics-2025"). */
    syllabus_id?: string;
    topics?: string[];
    visibility: Visibility;
    question_count: number;
    total_marks: number;
    duration_minutes?: number;
    created_at: string;
    updated_at: string;
    year?: number;
    source?: PaperSource;
    course_level?: CourseLevel;
    school?: string;
    remixed?: string;
    /** Full ordered list of questions in the paper. */
    questions: Question[];
}