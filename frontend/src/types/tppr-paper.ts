// Generated from docs/tppr-paper-meta.json, tppr-paper.json, tppr-question.json
// CONVERSION MADE WITH AI

// ---------- Shared enums ----------

export type PaperSource = "hsc" | "trial" | "internal" | "practice" | "custom";

export type CourseLevel =
    | "standard"
    | "advanced"
    | "extension_1"
    | "extension_2";

export type Visibility = "private" | "public" | "removed";

export type VerificationRequestStatus = "pending" | "approved" | "rejected";

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

/** Answer material for a question or sub-part. */
export interface QuestionAnswer {
    /** Correct option label for multiple-choice questions. */
    option_label?: string;
    /** Concise final answer or answer summary. */
    summary?: string;
    /** Worked solution or answer content. */
    content?: ContentBlock[];
    /** Alternative valid answer forms or solution paths. */
    alternatives?: ContentBlock[][];
}

/** A marking criterion or mark band from a marking guide. */
export interface RubricCriterion {
    /** Optional criterion label or band name. */
    label?: string;
    /** Exact marks awarded when this criterion is met. */
    marks?: number;
    /** Lower bound for a mark range. */
    min_marks?: number;
    /** Upper bound for a mark range. */
    max_marks?: number;
    /** Criterion description, including any mathematical notation or tables. */
    description: ContentBlock[];
}

/** Mark allocation and criteria for a question or sub-part. */
export interface QuestionRubric {
    criteria: RubricCriterion[];
    /** Additional marking notes not tied to a single criterion. */
    notes?: ContentBlock[];
}

/**
 * A sub-part of a question. Parts may nest arbitrarily deep, producing compound
 * numbering like "1.a.i": the top-level question is `1`, its parts are `a, b`,
 * their parts are `i, ii`, and so on. `label` holds only the leaf segment
 * (e.g. "a", "i", "1"); compound labels are derived from the path of labels.
 *
 * A part is either a **leaf** (has `content` + `marks` + an optional answer) or
 * a **container** (has `parts`; carries its own `stimulus` and optional intro
 * `content` but no standalone answer — its marks equal the sum of its children).
 */
export interface QuestionPart {
    /** Leaf label segment (e.g. "a", "i", "1", "A"). */
    label: string;
    stimulus?: ContentBlock[];
    /** Question text for a leaf, or optional intro text for a container. */
    content?: ContentBlock[];
    marks?: number;
    /** True if this part stands alone from the previous part's context. */
    is_independent?: boolean;
    /** Answer material for this sub-part (only meaningful on leaves). */
    answer?: string | QuestionAnswer | null;
    /** Mark allocation and criteria for this sub-part. */
    rubric?: QuestionRubric;
    /** General marking guidelines, feedback, common errors or comments. */
    guidelines?: ContentBlock[];
    /** Nested sub-parts (makes this a container part). */
    parts?: QuestionPart[];
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
    /** Correct answer, answer key or worked solution material (author-only). */
    answer?: string | QuestionAnswer | null;
    /** Mark allocation and criteria for this question. */
    rubric?: QuestionRubric;
    /** General marking guidelines, feedback, common errors or comments. */
    guidelines?: ContentBlock[];
    /** Topic tags, e.g. ["kinematics", "projectile motion"]. */
    topics?: string[];
    syllabus_points?: SyllabusPoint[];
    difficulty?: Difficulty;
    remixed_from?: string;
    source_question_id?: string;
    source_paper_id?: string;
    source_removed?: boolean;
    /** True when this verified paper's current question differs from its verified snapshot. */
    verified_changed?: boolean;
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
    /** Primary syllabus this paper targets (e.g. "hsc-physics-2025"). */
    syllabus_id?: string;
    year?: number;
    source?: PaperSource;
    /** School name, relevant for trial/internal papers. */
    school?: string;
    /** Course level tier, applicable to Mathematics and English. */
    course_level?: CourseLevel;
    /** Aggregate topic tags across all questions. */
    topics?: string[];
    /** Paper-level outcome tags/codes. */
    outcomes?: string[];
    visibility: Visibility;
    question_count: number;
    total_marks: number;
    duration_minutes?: number;
    created_at: string;
    updated_at: string;
    remixed?: string;
    verified?: boolean;
    verified_source_name?: string | null;
    verified_source_url?: string | null;
    verified_at?: string | null;
    verified_by?: string | null;
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
    outcomes?: string[];
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
    verified?: boolean;
    verified_source_name?: string | null;
    verified_source_url?: string | null;
    verified_at?: string | null;
    verified_by?: string | null;
    /** Full ordered list of questions in the paper. */
    questions: Question[];
}

export interface PaperVerificationRequest {
    id: string;
    paper_id: string;
    requester_id: string;
    source_name: string;
    source_url?: string | null;
    note?: string | null;
    status: VerificationRequestStatus;
    created_at: string;
    updated_at: string;
    resolved_at?: string | null;
    resolved_by?: string | null;
    admin_note?: string | null;
}
