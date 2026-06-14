// MADE WITH AI, DO NOT MARK

import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
    ExternalLink,
    RotateCcw,
    Search as SearchIcon,
    ShieldAlert,
} from "lucide-react";
import { toast } from "sonner";

import { getTakenDownPapers, restoreTakenDownPaper } from "@/api/admin";
import { useAuth } from "@/api/auth";
import NavBar from "@/components/navbar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { GenericError } from "@/pages/errors/GenericError";
import type { PaperMeta } from "@/types/tppr-paper";

const PER_PAGE = 20;

function formatDate(value: string) {
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value));
}

export default function AdminTakedowns() {
    const { user, loading: authLoading } = useAuth();
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();

    const [query, setQuery] = useState(searchParams.get("q") ?? "");
    const [papers, setPapers] = useState<PaperMeta[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(Number(searchParams.get("page")) || 1);
    const [loading, setLoading] = useState(true);
    const [restoringId, setRestoringId] = useState<string | null>(null);

    const totalPages = useMemo(
        () => Math.max(1, Math.ceil(total / PER_PAGE)),
        [total],
    );

    async function load(nextPage = page, nextQuery = query) {
        setLoading(true);
        try {
            const data = await getTakenDownPapers({
                q: nextQuery || undefined,
                page: nextPage,
                per_page: PER_PAGE,
            });
            setPapers(data.papers);
            setTotal(data.total);
            setPage(data.page);
        } catch {
            toast.error("Failed to load takedowns");
            setPapers([]);
            setTotal(0);
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        if (authLoading || !user?.admin) return;
        const nextQuery = searchParams.get("q") ?? "";
        const nextPage = Number(searchParams.get("page")) || 1;
        setQuery(nextQuery);
        void load(nextPage, nextQuery);
    }, [authLoading, user?.admin, searchParams.toString()]);

    function updateSearchParams(nextPage: number, nextQuery = query) {
        const params = new URLSearchParams();
        if (nextQuery) params.set("q", nextQuery);
        params.set("page", String(nextPage));
        setSearchParams(params);
    }

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        updateSearchParams(1);
    }

    async function handleRestore(paper: PaperMeta) {
        setRestoringId(paper.id);
        try {
            await restoreTakenDownPaper(paper.id);
            toast.success(`Restored "${paper.title}"`);
            await load(page, query);
        } catch {
            toast.error("Failed to restore paper");
        } finally {
            setRestoringId(null);
        }
    }

    if (authLoading) {
        return (
            <>
                <NavBar />
                <main className="flex items-center justify-center py-24">
                    <Spinner className="size-8" />
                </main>
            </>
        );
    }

    if (!user?.admin) {
        return (
            <GenericError
                code={403}
                title="Admin access required"
                message="This dashboard is only available while admin mode is active."
                showNav={true}
            />
        );
    }

    return (
        <>
            <NavBar />
            <main className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-6 py-8">
                <div className="flex flex-col gap-2">
                    <div className="flex items-center gap-2">
                        <ShieldAlert className="text-primary" />
                        <h1 className="text-2xl font-bold">
                            Takedown Dashboard
                        </h1>
                    </div>
                    <p className="text-sm text-muted-foreground">
                        {total} removed paper{total === 1 ? "" : "s"}
                    </p>
                </div>

                <Card>
                    <CardHeader>
                        <CardTitle>Removed Papers</CardTitle>
                        <CardDescription>
                            Search by title, subject, school, source, year,
                            paper ID, or author ID.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-4">
                        <form
                            onSubmit={handleSubmit}
                            className="flex flex-col gap-2 sm:flex-row"
                        >
                            <Input
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Search takedowns..."
                                className="sm:max-w-md"
                            />
                            <div className="flex gap-2">
                                <Button type="submit" disabled={loading}>
                                    <SearchIcon data-icon="inline-start" />
                                    Search
                                </Button>
                                <Button
                                    type="button"
                                    variant="outline"
                                    onClick={() => {
                                        setQuery("");
                                        updateSearchParams(1, "");
                                    }}
                                    disabled={loading && !query}
                                >
                                    Clear
                                </Button>
                            </div>
                        </form>

                        {loading
                            ? (
                                <div className="flex flex-col items-center gap-2 py-20 text-muted-foreground">
                                    <Spinner className="size-8" />
                                    <p>Loading takedowns...</p>
                                </div>
                            )
                            : papers.length === 0
                            ? (
                                <div className="py-20 text-center">
                                    <p className="font-medium">
                                        No takedowns found.
                                    </p>
                                    <p className="text-sm text-muted-foreground">
                                        Try a different search term.
                                    </p>
                                </div>
                            )
                            : (
                                <>
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>Paper</TableHead>
                                                <TableHead>Subject</TableHead>
                                                <TableHead>Author</TableHead>
                                                <TableHead>Stats</TableHead>
                                                <TableHead>
                                                    Last Updated
                                                </TableHead>
                                                <TableHead className="text-right">
                                                    Actions
                                                </TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {papers.map((paper) => (
                                                <TableRow key={paper.id}>
                                                    <TableCell>
                                                        <div className="flex max-w-md flex-col gap-1">
                                                            <Link
                                                                to={`/papers/${paper.id}`}
                                                                className="font-medium hover:underline"
                                                            >
                                                                {paper.title}
                                                            </Link>
                                                            <span className="truncate text-xs text-muted-foreground">
                                                                {paper.id}
                                                            </span>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        <div className="flex flex-col gap-1">
                                                            <span>
                                                                {paper.subject}
                                                            </span>
                                                            <div className="flex flex-wrap gap-1">
                                                                {paper.year && (
                                                                    <Badge variant="outline">
                                                                        {paper
                                                                            .year}
                                                                    </Badge>
                                                                )}
                                                                {paper.source && (
                                                                    <Badge
                                                                        variant="secondary"
                                                                        className="uppercase"
                                                                    >
                                                                        {paper
                                                                            .source}
                                                                    </Badge>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        {paper.author_id}
                                                    </TableCell>
                                                    <TableCell>
                                                        <div className="flex flex-wrap gap-1">
                                                            <Badge variant="destructive">
                                                                Removed
                                                            </Badge>
                                                            <Badge variant="outline">
                                                                {paper
                                                                    .question_count}
                                                                {" "}q
                                                            </Badge>
                                                            <Badge variant="outline">
                                                                {paper
                                                                    .total_marks}
                                                                {" "}marks
                                                            </Badge>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell>
                                                        {formatDate(
                                                            paper.updated_at,
                                                        )}
                                                    </TableCell>
                                                    <TableCell>
                                                        <div className="flex justify-end gap-2">
                                                            <Button
                                                                variant="ghost"
                                                                size="icon"
                                                                aria-label="Open paper"
                                                                onClick={() =>
                                                                    navigate(
                                                                        `/papers/${paper.id}`,
                                                                    )}
                                                            >
                                                                <ExternalLink />
                                                            </Button>
                                                            <Button
                                                                variant="outline"
                                                                size="sm"
                                                                disabled={restoringId ===
                                                                    paper.id}
                                                                onClick={() =>
                                                                    handleRestore(
                                                                        paper,
                                                                    )}
                                                            >
                                                                <RotateCcw data-icon="inline-start" />
                                                                {restoringId ===
                                                                        paper.id
                                                                    ? "Restoring..."
                                                                    : "Restore"}
                                                            </Button>
                                                        </div>
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>

                                    {totalPages > 1 && (
                                        <div className="flex items-center justify-end gap-2">
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                disabled={page <= 1}
                                                onClick={() =>
                                                    updateSearchParams(
                                                        page - 1,
                                                    )}
                                            >
                                                Previous
                                            </Button>
                                            <span className="text-sm text-muted-foreground">
                                                Page {page} of {totalPages}
                                            </span>
                                            <Button
                                                variant="outline"
                                                size="sm"
                                                disabled={page >= totalPages}
                                                onClick={() =>
                                                    updateSearchParams(
                                                        page + 1,
                                                    )}
                                            >
                                                Next
                                            </Button>
                                        </div>
                                    )}
                                </>
                            )}
                    </CardContent>
                </Card>
            </main>
        </>
    );
}
