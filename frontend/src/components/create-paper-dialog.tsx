import {
    DialogClose,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import {
    Field,
    FieldDescription,
    FieldGroup,
    FieldLabel,
} from "@/components/ui/field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { AllNESASubjectsList } from "@/lib/subjects";
import { useRef, useState } from "react";
import { toast } from "sonner";
import type { CourseLevel, PaperSource, Visibility } from "@/types/tppr-paper";
import { createLocalPaper } from "@/lib/paper";
import { importPaperFromJsonFile } from "@/lib/paper-import";
import { useAuth } from "@/api/auth";
import { useNavigate } from "react-router-dom";
import { FileJson, FilePlus2 } from "lucide-react";

export function CreatePaperDialog({ onCreated }: { onCreated?: () => void }) {
    const { user } = useAuth();
    const navigate = useNavigate();
    const importInputRef = useRef<HTMLInputElement>(null);
    
    const [mode, setMode] = useState<"choose" | "create">("choose");
    const [subject, setSubject] = useState("");
    const [courseLevel, setCourseLevel] = useState("");
    const [source, setSource] = useState("");
    const [visibility, setVisibility] = useState("private");
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState("");
    const showCourseLevel = subject === "Mathematics" || subject === "English";

    async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        if (!user) {
            setError("You gotta be logged in to create a paper");
            return;
        }
        if (!subject) {
            setError("Choose a subject before creating the paper");
            return;
        }
        setError("");
        setSubmitting(true);

        const formData = new FormData(e.currentTarget);

        try {
            const paper = await createLocalPaper({
                title: String(formData.get("title")),
                subject,
                course_level: showCourseLevel
                    ? (courseLevel as CourseLevel) || null
                    : null,
                year: formData.get("year") ? Number(formData.get("year")) : null,
                source: (source as PaperSource) || null,
                visibility: visibility as Visibility,
            }, user.user_id);
            toast.success("Paper created");
            onCreated?.();
            navigate(`/papers/${paper.id}`);
        } catch {
            setError("Failed to create paper locally");
        } finally {
            setSubmitting(false);
        }
    }

    async function handleImportFile(file: File | undefined) {
        if (!file) return;
        if (!user) {
            setError("You gotta be logged in to import a paper");
            return;
        }

        setError("");
        setSubmitting(true);
        try {
            const paper = await importPaperFromJsonFile(file, String(user.user_id));
            toast.success(`Imported "${paper.title}"`);
            onCreated?.();
            navigate(`/papers/${paper.id}`);
        } catch (error) {
            const message = error instanceof Error
                ? error.message
                : "Failed to import paper";
            setError(message);
            toast.error(message);
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <DialogContent onCloseAutoFocus={() => setMode("choose")}>
            {mode === "choose" && (
                <>
                    <DialogHeader>
                        <DialogTitle>Add Paper</DialogTitle>
                        <DialogDescription>
                            Import an existing TPPR JSON file or start with a blank paper.
                        </DialogDescription>
                    </DialogHeader>

                    <input
                        ref={importInputRef}
                        type="file"
                        accept=".json,application/json"
                        className="hidden"
                        onChange={(e) => {
                            void handleImportFile(e.target.files?.[0]);
                            e.target.value = "";
                        }}
                    />

                    <div className="grid gap-3 sm:grid-cols-2">
                        <Button
                            type="button"
                            variant="outline"
                            className="h-auto flex-col items-start gap-2 p-4 text-left whitespace-normal"
                            disabled={submitting}
                            onClick={() => importInputRef.current?.click()}
                        >
                            <FileJson data-icon="inline-start" />
                            <span className="font-medium">Import JSON</span>
                            <span className="text-sm font-normal text-muted-foreground">
                                Upload a saved TPPR paper file.
                            </span>
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            className="h-auto flex-col items-start gap-2 p-4 text-left whitespace-normal"
                            disabled={submitting}
                            onClick={() => setMode("create")}
                        >
                            <FilePlus2 data-icon="inline-start" />
                            <span className="font-medium">Create Blank</span>
                            <span className="text-sm font-normal text-muted-foreground">
                                Set up a new paper from scratch.
                            </span>
                        </Button>
                    </div>

                    {error && (
                        <p className="text-sm text-destructive">
                            {error}
                        </p>
                    )}
                </>
            )}

            {mode === "create" && (
                <form onSubmit={handleSubmit}>
                <DialogHeader>
                    <DialogTitle>Create New Paper</DialogTitle>
                    <DialogDescription>
                        Create a new paper to share with yourself and the world!
                    </DialogDescription>
                </DialogHeader>

                <FieldGroup>
                    <Field>
                        <FieldLabel htmlFor="title">Title</FieldLabel>
                        <Input
                            id="title"
                            name="title"
                            placeholder="e.g. 2024 Physics Trial"
                            required
                        />
                    </Field>

                    <div className="grid grid-cols-2 gap-4">
                        <Field className={showCourseLevel ? "" : "col-span-2"}>
                            <FieldLabel htmlFor="subject">Subject</FieldLabel>
                            <Select value={subject} onValueChange={setSubject}>
                                <SelectTrigger id="subject" className="w-full">
                                    <SelectValue placeholder="Select a subject" />
                                </SelectTrigger>
                                <SelectContent>
                                    <AllNESASubjectsList />
                                </SelectContent>
                            </Select>
                        </Field>

                        {showCourseLevel && (
                            <Field>
                                <FieldLabel htmlFor="course-level">
                                    Level
                                </FieldLabel>
                                <Select
                                    value={courseLevel}
                                    onValueChange={setCourseLevel}
                                >
                                    <SelectTrigger
                                        id="course-level"
                                        className="w-full"
                                    >
                                        <SelectValue placeholder="Select level" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="standard">
                                            Standard
                                        </SelectItem>
                                        <SelectItem value="advanced">
                                            Advanced
                                        </SelectItem>
                                        <SelectItem value="extension_1">
                                            Extension 1
                                        </SelectItem>
                                        <SelectItem value="extension_2">
                                            Extension 2
                                        </SelectItem>
                                    </SelectContent>
                                </Select>
                            </Field>
                        )}
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <Field>
                            <FieldLabel htmlFor="year">Year</FieldLabel>
                            <Input
                                id="year"
                                name="year"
                                type="number"
                                min={1990}
                                placeholder="2024"
                            />
                        </Field>
                        <Field>
                            <FieldLabel htmlFor="source">Source</FieldLabel>
                            <Select value={source} onValueChange={setSource}>
                                <SelectTrigger id="source" className="w-full">
                                    <SelectValue placeholder="Source" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="hsc">HSC</SelectItem>
                                    <SelectItem value="trial">Trial</SelectItem>
                                    <SelectItem value="internal">
                                        Internal
                                    </SelectItem>
                                    <SelectItem value="practice">
                                        Practice
                                    </SelectItem>
                                    <SelectItem value="custom">
                                        Custom
                                    </SelectItem>
                                </SelectContent>
                            </Select>
                        </Field>
                    </div>

                    <Field>
                        <FieldLabel>Visibility</FieldLabel>
                        <RadioGroup
                            value={visibility}
                            onValueChange={setVisibility}
                            className="flex gap-6"
                        >
                            <div className="flex items-center gap-2">
                                <RadioGroupItem value="private" id="private" />
                                <FieldLabel htmlFor="private">
                                    Private
                                </FieldLabel>
                            </div>
                            <div className="flex items-center gap-2">
                                <RadioGroupItem value="public" id="public" />
                                <FieldLabel htmlFor="public">Public</FieldLabel>
                            </div>
                        </RadioGroup>
                        <FieldDescription>
                            Public papers appear in the shared question pool.
                        </FieldDescription>
                    </Field>
                </FieldGroup>

                <DialogFooter className="mt-4">
                    {error && (
                        <p className="self-center text-sm text-destructive">
                            {error}
                        </p>
                    )}
                    <DialogClose asChild>
                        <Button type="button" variant="outline">
                            Cancel
                        </Button>
                    </DialogClose>
                    <Button type="submit" disabled={submitting}>
                        {submitting ? "Creating…" : "Create Paper"}
                    </Button>
                </DialogFooter>
                </form>
            )}
        </DialogContent>
    );
}
