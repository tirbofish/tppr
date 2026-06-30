import { useState, type FormEvent } from "react";
import { Flag } from "lucide-react";
import { toast } from "sonner";

import { reportPaper, type ReportReason } from "@/api/reports";
import { useAuth } from "@/api/auth";
import { Button } from "@/components/ui/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
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
import {
    Select,
    SelectContent,
    SelectGroup,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";

const REPORT_REASON_LABELS: Record<ReportReason, string> = {
    false_information: "False or misleading information",
    copyright: "Copyright or ownership concern",
    inappropriate: "Inappropriate content",
    broken_content: "Broken formatting, missing assets, or unusable questions",
    spam: "Spam or low-quality upload",
    other: "Something else",
};

interface ReportPaperButtonProps {
    paperId: string;
}

export function ReportPaperButton({ paperId }: ReportPaperButtonProps) {
    const { user } = useAuth();
    const [open, setOpen] = useState(false);
    const [reason, setReason] = useState<ReportReason>("false_information");
    const [details, setDetails] = useState("");
    const [submitting, setSubmitting] = useState(false);

    async function handleSubmit(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        if (!user) {
            toast.error("Log in to report papers");
            return;
        }
        if (reason === "other" && details.trim().length < 10) {
            toast.error("Add a short explanation for this report");
            return;
        }

        setSubmitting(true);
        try {
            await reportPaper(paperId, {
                reason,
                details: details.trim() || undefined,
            });
            toast.success("Report submitted");
            setOpen(false);
            setReason("false_information");
            setDetails("");
        } catch (error) {
            toast.error(
                error instanceof Error ? error.message : "Failed to submit report",
            );
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
                <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Report paper"
                >
                    <Flag />
                </Button>
            </DialogTrigger>
            <DialogContent className="max-h-[min(90vh,640px)] overflow-y-auto sm:max-w-lg">
                <form onSubmit={handleSubmit} className="min-w-0">
                    <DialogHeader>
                        <DialogTitle>Report paper</DialogTitle>
                        <DialogDescription>
                            Reports help admins review inaccurate, unsafe, or
                            broken public material.
                        </DialogDescription>
                    </DialogHeader>

                    <FieldGroup className="mt-4">
                        <Field>
                            <FieldLabel htmlFor="report-reason">
                                Reason
                            </FieldLabel>
                            <Select
                                value={reason}
                                onValueChange={(value) =>
                                    setReason(value as ReportReason)}
                            >
                                <SelectTrigger
                                    id="report-reason"
                                    className="w-full"
                                >
                                    <SelectValue placeholder="Select a reason" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectGroup>
                                        {Object.entries(REPORT_REASON_LABELS).map((
                                            [value, label],
                                        ) => (
                                            <SelectItem key={value} value={value}>
                                                {label}
                                            </SelectItem>
                                        ))}
                                    </SelectGroup>
                                </SelectContent>
                            </Select>
                        </Field>

                        <Field>
                            <FieldLabel htmlFor="report-details">
                                Details
                            </FieldLabel>
                            <Textarea
                                id="report-details"
                                value={details}
                                onChange={(e) => setDetails(e.target.value)}
                                maxLength={2000}
                                rows={5}
                                placeholder="Point admins to the exact question, issue, or source of concern."
                            />
                            <FieldDescription>
                                Include enough context for an admin to review it.
                            </FieldDescription>
                        </Field>
                    </FieldGroup>

                    <DialogFooter className="mt-4">
                        <Button
                            type="button"
                            variant="outline"
                            onClick={() => setOpen(false)}
                        >
                            Cancel
                        </Button>
                        <Button type="submit" disabled={submitting}>
                            {submitting ? "Submitting..." : "Submit report"}
                        </Button>
                    </DialogFooter>
                </form>
            </DialogContent>
        </Dialog>
    );
}
