import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { PanelRightClose, PanelRightOpen, ShieldAlert } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/api/auth";
import { apiFetch } from "@/api/client";
import { updatePaperVerification } from "@/api/papers";
import {
    getAdminReports,
    type PaperReport,
    type ReportStatus,
    updateReportStatus,
} from "@/api/reports";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import type { PaperMeta } from "@/types/tppr-paper";

interface AdminSidebarProps {
    paperId: string;
    isTakenDown?: boolean;
    paper?: PaperMeta;
    onPaperUpdate?: (paper: PaperMeta) => void;
}

const REPORT_REASON_LABELS: Record<PaperReport["reason"], string> = {
    false_information: "False info",
    copyright: "Copyright",
    inappropriate: "Inappropriate",
    broken_content: "Broken content",
    spam: "Spam",
    other: "Other",
};

const REPORT_STATUS_OPTIONS: ReportStatus[] = [
    "reviewing",
    "resolved",
    "dismissed",
];

export function AdminSidebar(
    { paperId, isTakenDown, paper, onPaperUpdate }: AdminSidebarProps,
) {
    const { user } = useAuth();
    const [open, setOpen] = useState(true);
    const [loading, setLoading] = useState(false);
    const [reports, setReports] = useState<PaperReport[]>([]);
    const [reportsLoading, setReportsLoading] = useState(false);
    const [updatingReportId, setUpdatingReportId] = useState<number | null>(
        null,
    );
    const [sourceName, setSourceName] = useState(
        paper?.verified_source_name ?? "",
    );
    const [sourceUrl, setSourceUrl] = useState(paper?.verified_source_url ?? "");
    const [verifying, setVerifying] = useState(false);

    useEffect(() => {
        setSourceName(paper?.verified_source_name ?? "");
        setSourceUrl(paper?.verified_source_url ?? "");
    }, [paper?.verified_source_name, paper?.verified_source_url]);

    useEffect(() => {
        if (!user?.admin || !open) return;

        let cancelled = false;
        setReportsLoading(true);
        getAdminReports({ paper_id: paperId, status: "all", per_page: 5 })
            .then((data) => {
                if (!cancelled) setReports(data.reports);
            })
            .catch((error) => {
                if (!cancelled) {
                    toast.error(
                        error instanceof Error
                            ? error.message
                            : "Failed to load reports",
                    );
                }
            })
            .finally(() => {
                if (!cancelled) setReportsLoading(false);
            });

        return () => {
            cancelled = true;
        };
    }, [open, paperId, user?.admin]);

    if (!user?.admin) return null;

    async function handleTakedown() {
        if (
            !confirm(
                "This will take down this paper and ALL its remixes. Continue?",
            )
        ) return;

        setLoading(true);
        try {
            const res = await apiFetch(`/api/admin/takedown/${paperId}`, {
                method: "POST",
            });
            const data = await res.json();
            if (!res.ok) {
                toast.error(data.message || "Takedown failed");
                return;
            }
            toast.success(data.message);
            window.location.reload();
        } catch {
            toast.error("An error occurred during takedown");
        } finally {
            setLoading(false);
        }
    }

    async function handleRevert() {
        if (!confirm("Restore this paper and all its remixes?")) return;

        setLoading(true);
        try {
            const res = await apiFetch(`/api/admin/takedown/${paperId}`, {
                method: "DELETE",
            });
            const data = await res.json();
            if (!res.ok) {
                toast.error(data.message || "Revert failed");
                return;
            }
            toast.success(data.message);
            window.location.reload();
        } catch {
            toast.error("An error occurred during revert");
        } finally {
            setLoading(false);
        }
    }

    async function handleReportStatus(reportId: number, status: ReportStatus) {
        setUpdatingReportId(reportId);
        try {
            const updated = await updateReportStatus(reportId, status);
            setReports((current) =>
                current.map((report) =>
                    report.id === reportId ? updated : report
                )
            );
            toast.success("Report updated");
        } catch (error) {
            toast.error(
                error instanceof Error
                    ? error.message
                    : "Failed to update report",
            );
        } finally {
            setUpdatingReportId(null);
        }
    }

    async function handleVerification(verified: boolean) {
        setVerifying(true);
        try {
            const updated = await updatePaperVerification(paperId, {
                verified,
                source_name: sourceName.trim(),
                source_url: sourceUrl.trim() || undefined,
            });
            onPaperUpdate?.(updated);
            toast.success(verified ? "Paper verified" : "Verification removed");
        } catch (error) {
            toast.error(
                error instanceof Error
                    ? error.message
                    : "Failed to update verification",
            );
        } finally {
            setVerifying(false);
        }
    }

    if (!open) {
        return (
            <Button
                variant="outline"
                size="icon"
                className="fixed right-4 bottom-4 z-50 size-10 rounded-full border-primary shadow-lg"
                onClick={() => setOpen(true)}
            >
                <PanelRightOpen className="size-4 text-primary" />
            </Button>
        );
    }

    return (
        <aside className="fixed right-4 bottom-4 z-50 flex max-h-[min(80vh,720px)] w-[min(calc(100vw-2rem),22rem)] flex-col rounded-lg border bg-background shadow-lg">
            <div className="flex items-center justify-between border-b px-4 py-3">
                <h2 className="flex items-center gap-2 text-sm font-semibold text-primary">
                    <ShieldAlert className="size-4" />
                    Admin Actions
                </h2>
                <Button
                    variant="ghost"
                    size="icon"
                    className="size-6"
                    onClick={() => setOpen(false)}
                >
                    <PanelRightClose className="size-3.5" />
                </Button>
            </div>
            <div className="flex flex-col gap-4 overflow-y-auto p-4">
                {isTakenDown
                    ? (
                        <div className="flex flex-col gap-2">
                            <Button
                                variant="outline"
                                size="sm"
                                className="w-full"
                                onClick={handleRevert}
                                disabled={loading}
                            >
                                {loading ? "Restoring..." : "Revert takedown"}
                            </Button>
                            <p className="text-xs text-muted-foreground">
                                Restores this paper and all remixes to private.
                            </p>
                        </div>
                    )
                    : (
                        <div className="flex flex-col gap-2">
                            <Button
                                variant="destructive"
                                size="sm"
                                className="w-full"
                                onClick={handleTakedown}
                                disabled={loading}
                            >
                                {loading ? "Taking down..." : "Take down paper"}
                            </Button>
                            <p className="text-xs text-muted-foreground">
                                Removes this paper and all remixes from public
                                access.
                            </p>
                        </div>
                    )}
                <Separator />
                <div className="flex flex-col gap-3">
                    <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            Verification
                        </h3>
                        <p className="mt-1 text-xs text-muted-foreground">
                            Mark official source-backed papers after manual
                            review.
                        </p>
                    </div>
                    <Input
                        value={sourceName}
                        onChange={(event) => setSourceName(event.target.value)}
                        placeholder="Source, e.g. THSC"
                        disabled={verifying}
                    />
                    <Input
                        value={sourceUrl}
                        onChange={(event) => setSourceUrl(event.target.value)}
                        placeholder="Original source URL"
                        disabled={verifying}
                    />
                    <div className="flex flex-wrap gap-2">
                        <Button
                            size="sm"
                            className="flex-1"
                            disabled={verifying || !sourceName.trim()}
                            onClick={() => handleVerification(true)}
                        >
                            {paper?.verified ? "Update" : "Verify"}
                        </Button>
                        {paper?.verified && (
                            <Button
                                size="sm"
                                variant="outline"
                                disabled={verifying}
                                onClick={() => handleVerification(false)}
                            >
                                Remove
                            </Button>
                        )}
                    </div>
                </div>

                <Separator />
                <div>
                    <div className="mb-2 flex items-center justify-between gap-2">
                        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                            Reports
                        </h3>
                        <Badge variant="outline">{reports.length}</Badge>
                    </div>
                    {reportsLoading
                        ? (
                            <p className="text-xs text-muted-foreground">
                                Loading reports...
                            </p>
                        )
                        : reports.length === 0
                        ? (
                            <p className="text-xs text-muted-foreground">
                                No reports for this paper.
                            </p>
                        )
                        : (
                            <div className="flex flex-col gap-3">
                                {reports.map((report) => (
                                    <div
                                        key={report.id}
                                        className="rounded-md border p-3"
                                    >
                                        <div className="flex flex-wrap items-center gap-2">
                                            <Badge variant="secondary">
                                                {REPORT_REASON_LABELS[
                                                    report.reason
                                                ]}
                                            </Badge>
                                            <Badge variant="outline">
                                                {report.status}
                                            </Badge>
                                        </div>
                                        {report.details && (
                                            <p className="mt-2 line-clamp-3 break-words text-xs text-muted-foreground">
                                                {report.details}
                                            </p>
                                        )}
                                        <div className="mt-3 flex flex-wrap gap-1">
                                            {REPORT_STATUS_OPTIONS.map((
                                                status,
                                            ) => (
                                                <Button
                                                    key={status}
                                                    type="button"
                                                    variant="outline"
                                                    size="sm"
                                                    className="h-7 px-2 text-xs"
                                                    disabled={updatingReportId ===
                                                            report.id ||
                                                        report.status ===
                                                            status}
                                                    onClick={() =>
                                                        handleReportStatus(
                                                            report.id,
                                                            status,
                                                        )}
                                                >
                                                    {status}
                                                </Button>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                </div>
            </div>
        </aside>
    );
}
