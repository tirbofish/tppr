import { useEffect, useState } from "react";
import { Trophy } from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/api/auth";
import {
    type LeaderboardEntry,
    getLeaderboard,
} from "@/api/social";
import NavBar from "@/components/navbar";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";

type Scope = "global" | "friends";

function formatDuration(totalSeconds: number): string {
    const s = Math.max(0, Math.floor(totalSeconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${sec}s`;
    return `${sec}s`;
}

export default function Leaderboard() {
    const { user } = useAuth();
    const [scope, setScope] = useState<Scope>("global");
    const [entries, setEntries] = useState<LeaderboardEntry[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Friends scope requires a signed-in user; fall back to global.
        const effective: Scope = scope === "friends" && !user ? "global" : scope;
        let cancelled = false;
        setLoading(true);
        getLeaderboard(effective === "friends" ? "friends" : undefined)
            .then((data) => {
                if (!cancelled) setEntries(data.entries);
            })
            .catch((e) => {
                if (!cancelled) {
                    toast.error(
                        e instanceof Error ? e.message : "Failed to load leaderboard",
                    );
                    setEntries([]);
                }
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => {
            cancelled = true;
        };
    }, [scope, user]);

    return (
        <>
            <NavBar />
            <main className="mx-auto w-full max-w-4xl px-6 py-10 space-y-6">
                <div className="flex items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl font-bold flex items-center gap-2">
                            <Trophy className="size-6" />
                            Leaderboard
                        </h1>
                        <p className="text-sm text-muted-foreground">
                            Ranked by papers completed, then study time.
                        </p>
                    </div>
                    {user && (
                        <div className="flex gap-2">
                            <Button
                                size="sm"
                                variant={scope === "global" ? "default" : "outline"}
                                onClick={() => setScope("global")}
                            >
                                Global
                            </Button>
                            <Button
                                size="sm"
                                variant={scope === "friends" ? "default" : "outline"}
                                onClick={() => setScope("friends")}
                            >
                                Friends
                            </Button>
                        </div>
                    )}
                </div>

                <Card>
                    <CardHeader>
                        <CardTitle>
                            {scope === "friends" && user
                                ? "Friends ranking"
                                : "Global ranking"}
                        </CardTitle>
                        <CardDescription>
                            Top {entries.length || 0} students.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loading
                            ? (
                                <div className="flex justify-center py-8">
                                    <Spinner />
                                </div>
                            )
                            : entries.length === 0
                            ? (
                                <p className="text-sm text-muted-foreground py-8 text-center">
                                    No one to rank yet. Be the first!
                                </p>
                            )
                            : (
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            <TableHead className="w-16">#</TableHead>
                                            <TableHead>User</TableHead>
                                            <TableHead className="text-right">
                                                Completed
                                            </TableHead>
                                            <TableHead className="text-right">
                                                Practised
                                            </TableHead>
                                            <TableHead className="text-right">
                                                Answered
                                            </TableHead>
                                            <TableHead className="text-right">
                                                Study time
                                            </TableHead>
                                            <TableHead className="text-right">
                                                Streak
                                            </TableHead>
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {entries.map((e) => (
                                            <TableRow key={e.user_id}>
                                                <TableCell className="font-medium">
                                                    {e.rank}
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex items-center gap-2">
                                                        <Avatar className="size-7">
                                                            <AvatarImage
                                                                src={e.avatar_url ?? undefined}
                                                                alt={e.username}
                                                            />
                                                            <AvatarFallback className="text-xs">
                                                                {e.username?.slice(0, 2).toUpperCase()}
                                                            </AvatarFallback>
                                                        </Avatar>
                                                        <span className="font-medium">
                                                            {e.username}
                                                        </span>
                                                    </div>
                                                </TableCell>
                                                <TableCell className="text-right font-medium tabular-nums">
                                                    {e.papers_completed}
                                                </TableCell>
                                                <TableCell className="text-right tabular-nums">
                                                    {e.papers_attempted}
                                                </TableCell>
                                                <TableCell className="text-right tabular-nums">
                                                    {e.questions_answered}
                                                </TableCell>
                                                <TableCell className="text-right tabular-nums">
                                                    {formatDuration(e.total_study_seconds)}
                                                </TableCell>
                                                <TableCell className="text-right tabular-nums">
                                                    {e.current_streak}d
                                                </TableCell>
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            )}
                    </CardContent>
                </Card>
            </main>
        </>
    );
}