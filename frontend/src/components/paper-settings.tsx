import {
    Dialog,
    DialogClose,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
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
import { memo, useState } from "react";
import type {
    CourseLevel,
    PaperMeta,
    PaperSource,
    Visibility,
} from "@/types/tppr-paper";
import { Settings } from "lucide-react";
import { toast } from "sonner";
import { syncService } from "@/lib/cloud";
import { Link } from "react-router-dom";

interface PaperSettingsProps {
    paper: PaperMeta;
    onSave: (updated: PaperMeta) => void;
    onOpenChange?: (open: boolean) => void;
}

function sameSettingsPaper(a: PaperMeta, b: PaperMeta) {
    return a.id === b.id &&
        a.title === b.title &&
        a.subject === b.subject &&
        a.course_level === b.course_level &&
        a.year === b.year &&
        a.source === b.source &&
        a.visibility === b.visibility;
}

export const PaperSettings = memo(function PaperSettings(
    { paper, onSave, onOpenChange }: PaperSettingsProps,
) {
    const [open, setOpen] = useState(false);
    const [title, setTitle] = useState(paper.title);
    const [subject, setSubject] = useState(paper.subject);
    const [courseLevel, setCourseLevel] = useState(paper.course_level ?? "");
    const [year, setYear] = useState(paper.year?.toString() ?? "");
    const [source, setSource] = useState(paper.source ?? "");
    const [visibility, setVisibility] = useState<Visibility>(paper.visibility);
    const [showPublishWarning, setShowPublishWarning] = useState(false);
    const [showUnpublishWarning, setShowUnpublishWarning] = useState(false);
    const [duration, setDuration] = useState(
        paper.duration_minutes?.toString() ?? "",
    );

    const showCourseLevel = subject === "Mathematics" || subject === "English";

    function handleOpen(isOpen: boolean) {
        if (isOpen) {
            setTitle(paper.title);
            setSubject(paper.subject);
            setCourseLevel(paper.course_level ?? "");
            setYear(paper.year?.toString() ?? "");
            setSource(paper.source ?? "");
            setVisibility(paper.visibility);
            setDuration(paper.duration_minutes?.toString() ?? "");
        }
        setShowPublishWarning(false);
        setShowUnpublishWarning(false);
        setOpen(isOpen);
        onOpenChange?.(isOpen);
    }

    function handleSubmit(e: React.SubmitEvent) {
        e.preventDefault();
        if (paper.visibility === "private" && visibility === "public") {
            setShowPublishWarning(true);
            return;
        }
        if (paper.visibility === "public" && visibility === "private") {
            setShowUnpublishWarning(true);
            return;
        }
        onOpenChange?.(false);
        save();
    }

    async function save() {
        const isPublishing = paper.visibility === "private" &&
            visibility === "public";
        const isUnpublishing = paper.visibility === "public" &&
            visibility === "private";

        const updated: PaperMeta = {
            ...paper,
            title,
            subject,
            course_level: showCourseLevel
                ? (courseLevel as CourseLevel) || undefined
                : undefined,
            year: year ? Number(year) : undefined,
            source: (source as PaperSource) || undefined,
            visibility,
            duration_minutes: duration ? Number(duration) : undefined,
            updated_at: new Date().toISOString(),
        };

        try {
            if (isPublishing) {
                await syncService.publish(paper.id);
                toast.success(`${title} is now public!`);
            } else if (isUnpublishing) {
                await syncService.unpublish(paper.id);
                toast.success(`${title} is now private.`);
            }
        } catch {
            toast.error("Failed to update visibility. Please try again.");
            return;
        }

        onSave(updated);
        setShowPublishWarning(false);
        setShowUnpublishWarning(false);
        setOpen(false);
    }

    return (
        <>
            <Dialog open={open} onOpenChange={handleOpen}>
                <DialogTrigger asChild>
                    <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Paper settings"
                    >
                        <Settings />
                    </Button>
                </DialogTrigger>
                <DialogContent>
                    <form onSubmit={handleSubmit}>
                        <DialogHeader>
                            <DialogTitle>Paper Settings</DialogTitle>
                        </DialogHeader>

                        <FieldGroup>
                            <Field>
                                <FieldLabel htmlFor="settings-title">
                                    Title
                                </FieldLabel>
                                <Input
                                    id="settings-title"
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                    required
                                />
                            </Field>

                            <div className="grid grid-cols-2 gap-4">
                                <Field
                                    className={showCourseLevel
                                        ? ""
                                        : "col-span-2"}
                                >
                                    <FieldLabel htmlFor="settings-subject">
                                        Subject
                                    </FieldLabel>
                                    <Select
                                        value={subject}
                                        onValueChange={setSubject}
                                    >
                                        <SelectTrigger
                                            id="settings-subject"
                                            className="w-full"
                                        >
                                            <SelectValue placeholder="Select a subject" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <AllNESASubjectsList />
                                        </SelectContent>
                                    </Select>
                                </Field>

                                {showCourseLevel && (
                                    <Field>
                                        <FieldLabel htmlFor="settings-level">
                                            Level
                                        </FieldLabel>
                                        <Select
                                            value={courseLevel}
                                            onValueChange={setCourseLevel}
                                        >
                                            <SelectTrigger
                                                id="settings-level"
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

                            <div className="grid grid-cols-3 gap-4">
                                <Field>
                                    <FieldLabel htmlFor="settings-year">
                                        Year
                                    </FieldLabel>
                                    <Input
                                        id="settings-year"
                                        type="number"
                                        min={1990}
                                        value={year}
                                        onChange={(e) =>
                                            setYear(e.target.value)}
                                        placeholder="2026"
                                    />
                                </Field>
                                <Field>
                                    <FieldLabel htmlFor="settings-duration">
                                        Duration (min)
                                    </FieldLabel>
                                    <Input
                                        id="settings-duration"
                                        type="number"
                                        min={1}
                                        max={600}
                                        value={duration}
                                        onChange={(e) =>
                                            setDuration(e.target.value)}
                                        placeholder="180"
                                    />
                                </Field>
                                <Field>
                                    <FieldLabel htmlFor="settings-source">
                                        Source
                                    </FieldLabel>
                                    <Select
                                        value={source}
                                        onValueChange={setSource}
                                    >
                                        <SelectTrigger
                                            id="settings-source"
                                            className="w-full"
                                        >
                                            <SelectValue placeholder="Source" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="hsc">
                                                HSC
                                            </SelectItem>
                                            <SelectItem value="trial">
                                                Trial
                                            </SelectItem>
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
                                    onValueChange={(v) =>
                                        setVisibility(v as Visibility)}
                                    className="flex gap-6"
                                >
                                    <div className="flex items-center gap-2">
                                        <RadioGroupItem
                                            value="private"
                                            id="settings-private"
                                        />
                                        <FieldLabel htmlFor="settings-private">
                                            Private
                                        </FieldLabel>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <RadioGroupItem
                                            value="public"
                                            id="settings-public"
                                        />
                                        <FieldLabel htmlFor="settings-public">
                                            Public
                                        </FieldLabel>
                                    </div>
                                </RadioGroup>
                                <FieldDescription>
                                    Public papers appear in the shared question
                                    pool.
                                </FieldDescription>
                            </Field>
                        </FieldGroup>

                        <DialogFooter className="mt-4">
                            <DialogClose asChild>
                                <Button type="button" variant="outline">
                                    Cancel
                                </Button>
                            </DialogClose>
                            <Button type="submit">Save</Button>
                        </DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>

            {/* publish paper (private->public) */}
            <Dialog
                open={showPublishWarning}
                onOpenChange={setShowPublishWarning}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            You are about to publish {title}
                        </DialogTitle>
                    </DialogHeader>
                    <p className="text-sm text-muted-foreground">
                        Good to see you want your creation to be seen by the
                        world, but be aware of the implications of publishing:
                    </p>
                    <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                        <li>
                            By publishing, anyone who uses Thribhus Past Paper
                            Repository will be able to see your paper.
                        </li>
                        <li>
                            Your paper can be copied and remixed by anyone.
                        </li>
                        <li>
                            Your paper aligns with the{" "}
                            <Link
                                to="/legal/copyright"
                                className="underline text-primary"
                            >
                                COPYRIGHT.md
                            </Link>{" "}
                            document, and you are aware that you may risk
                            deletion if in violation.
                        </li>
                    </ul>
                    <p className="text-sm font-medium">Continue?</p>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setShowPublishWarning(false)}
                        >
                            Nevermind
                        </Button>
                        <Button onClick={save}>
                            Carry on!
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* unpublish paper (public->private) */}
            <Dialog
                open={showUnpublishWarning}
                onOpenChange={setShowUnpublishWarning}
            >
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>
                            You are about to unpublish {title}
                        </DialogTitle>
                    </DialogHeader>
                    <p className="text-sm text-muted-foreground">
                        Unfortunate to see your creation get removed, but to
                        each their own. Understand the implications:
                    </p>
                    <ul className="list-disc pl-5 text-sm text-muted-foreground space-y-1">
                        <li>
                            Your paper will no longer appear in search results
                            or the shared question pool.
                        </li>
                        <li>
                            Anyone who previously had access will no longer be
                            able to view it.
                        </li>
                    </ul>
                    <p className="text-sm font-medium">Continue?</p>
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setShowUnpublishWarning(false)}
                        >
                            Nevermind
                        </Button>
                        <Button onClick={save}>
                            Yeah go ahead!
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </>
    );
}, (prev, next) =>
    sameSettingsPaper(prev.paper, next.paper) &&
    prev.onSave === next.onSave &&
    prev.onOpenChange === next.onOpenChange);
