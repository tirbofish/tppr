import type { Paper } from "@/types/tppr-paper";
import { syncService } from "@/lib/cloud";
import { paperStore } from "@/lib/paper";

function isValidTpprPaper(data: unknown): data is Paper {
    if (typeof data !== "object" || data === null) return false;
    const d = data as Record<string, unknown>;
    return (
        typeof d.id === "string" &&
        typeof d.title === "string" &&
        typeof d.subject === "string" &&
        typeof d.visibility === "string" &&
        ["private", "public", "removed"].includes(d.visibility) &&
        typeof d.question_count === "number" &&
        typeof d.total_marks === "number" &&
        typeof d.created_at === "string" &&
        typeof d.updated_at === "string" &&
        Array.isArray(d.questions)
    );
}

export async function importPaperFromJsonFile(
    file: File,
    authorId: string,
    existingPapers: Pick<Paper, "title" | "subject">[] = [],
): Promise<Paper> {
    if (!file.name.toLowerCase().endsWith(".json")) {
        throw new Error("Please choose a .json file.");
    }

    let data: unknown;
    try {
        data = JSON.parse(await file.text());
    } catch (error) {
        const message = error instanceof Error
            ? error.message
            : "Could not parse the selected file.";
        throw new Error(`Invalid JSON: ${message}`, { cause: error });
    }

    if (!isValidTpprPaper(data)) {
        throw new Error("Invalid file - does not match the TPPR paper format.");
    }

    const alreadyExists = existingPapers.some(
        (paper) => paper.title === data.title && paper.subject === data.subject,
    );
    if (alreadyExists) {
        throw new Error(`A paper called "${data.title}" already exists.`);
    }

    const now = new Date().toISOString();
    const imported: Paper = {
        ...data,
        id: crypto.randomUUID(),
        author_id: authorId,
        visibility: "private",
        created_at: now,
        updated_at: now,
        questions: data.questions.map((question) => ({
            ...question,
            author_id: authorId,
            paper_id: "",
        })),
    };
    imported.questions = imported.questions.map((question) => ({
        ...question,
        paper_id: imported.id,
    }));

    await paperStore.savePaper(imported);
    await syncService.sync(imported);
    await syncService.flush();

    return imported;
}
