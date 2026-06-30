import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
    Award,
    FileText,
    Globe,
    ListChecks,
    Repeat,
    ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";

import { useAuth } from "@/api/auth";
import { getAllUserStats, getMyStats, type MyStats } from "@/api/stats";
import type { AllUserStats } from "@/api/stats";
import NavBar from "@/components/navbar";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
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

const ZERO: MyStats = {
    user_id: "",
    username: "",
    paper_count: 0,
    public_paper_count: 0,
    question_count: 0,
    total_marks: 0,
    remixes_received: 0,
};

function StatCard({
    icon,
    label,
    value,
}: {
    icon: React.ReactNode;
    label: string;
    value: number;
}) {
    return (
        <Card>
            <CardContent className="flex items-center gap-4 p-5">
                <div className="flex size-10 items-center justify-center rounded-md bg-primary/10 text-primary">
                    {icon}
                </div>
                <div>
                    <p className="text-2xl font-bold leading-none">{value}</p>
                    <p className="text-sm text-muted-foreground mt-1">{label}</p>
                </div>
            </CardContent>
        </Card>
    );
}

function Bars({ stats }: { stats: MyStats }) {
    const items = [
        { label: "Papers", value: stats.paper_count },
        { label: "Public", value: stats.public_paper_count },
        { label: "Questions", value: stats.question_count },
        { label: "Total marks", value: stats.total_marks },
        { label: "Remixes received", value: stats.remixes_received },
    ];
    const max = Math.max(1, ...items.map((i) => i.value));

    return (
        <div className="space-y-3">
            {items.map((i) => (
                <div key={i.label}>
                    <div className="flex justify-between text-sm mb-1">
                        <span className="text-muted-foreground">{i.label}</span>
                        <span className="font-medium">{i.value}</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                        <div
                            className="h-full rounded-full bg-primary"
                            style={{ width: `${(i.value / max) * 100}%` }}
                        />
                    </div>
                </div>
            ))}
        </div>
    );
}

export default function Dashboard() {
    const { user, loading: authLoading } = useAuth();
    const navigate = useNavigate();

    const [stats, setStats] = useState<MyStats | null>(null);
    const [loadingStats, setLoadingStats] = useState(true);
    const [allUsers, setAllUsers] = useState<AllUserStats[]>([]);
    const [loadingAll, setLoadingAll] = useState(false);

    useEffect(() => {
        if (!authLoading && !user) {
            navigate("/login?redirect=/dashboard", { replace: true });
        }
    }, [user, authLoading, navigate]);

    useEffect(() => {
        if (!user) return;
        let cancelled = false;
        setLoadingStats(true);
        getMyStats()
            .then((data) => {
                if (!cancelled) setStats(data);
            })
            .catch((e) => {
                if (!cancelled) {
                    toast.error(e instanceof Error ? e.message : "Failed to load stats");
                    setStats({ ...ZERO, user_id: user.user_id, username: user.username });
                }
            })
            .finally(() => {
                if (!cancelled) setLoadingStats(false);
            });
        return () => {
            cancelled = true;
        };
    }, [user]);

    useEffect(() => {
        if (!user?.admin) {
            setAllUsers([]);
            return;
        }
        let cancelled = false;
        setLoadingAll(true);
        getAllUserStats()
            .then((data) => {
                if (!cancelled) setAllUsers(data.users);
            })
            .catch((e) => {
                if (!cancelled) {
                    toast.error(e instanceof Error ? e.message : "Failed to load user stats");
                }
            })
            .finally(() => {
                if (!cancelled) setLoadingAll(false);
            });
        return () => {
            cancelled = true;
        };
    }, [user]);

    if (authLoading) return null;
    if (!user) return null;

    return (
        <>
            <NavBar />
            <main className="mx-auto w-full max-w-4xl px-6 py-10 space-y-6">
                <h1 className="text-2xl font-bold">Dashboard</h1>

                {/* My stats */}
                <Card>
                    <CardHeader>
                        <CardTitle>My stats</CardTitle>
                        <CardDescription>
                            Your authoring activity across the repository.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {loadingStats || !stats
                            ? (
                                <div className="flex justify-center py-8">
                                    <Spinner />
                                </div>
                            )
                            : (
                                <>
                                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                                        <StatCard
                                            icon={<FileText className="size-5" />}
                                            label="Papers"
                                            value={stats.paper_count}
                                        />
                                        <StatCard
                                            icon={<Globe className="size-5" />}
                                            label="Public papers"
                                            value={stats.public_paper_count}
                                        />
                                        <StatCard
                                            icon={<ListChecks className="size-5" />}
                                            label="Questions"
                                            value={stats.question_count}
                                        />
                                        <StatCard
                                            icon={<Award className="size-5" />}
                                            label="Total marks"
                                            value={stats.total_marks}
                                        />
                                        <StatCard
                                            icon={<Repeat className="size-5" />}
                                            label="Remixes received"
                                            value={stats.remixes_received}
                                        />
                                    </div>
                                    <Bars stats={stats} />
                                </>
                            )}
                    </CardContent>
                </Card>

                {/* Admin: all users */}
                {user.admin && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-primary">
                                <ShieldCheck className="size-5" />
                                All users
                            </CardTitle>
                            <CardDescription>
                                Aggregated stats for every user, sorted by total
                                marks.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {loadingAll
                                ? (
                                    <div className="flex justify-center py-8">
                                        <Spinner />
                                    </div>
                                )
                                : (
                                    <Table>
                                        <TableHeader>
                                            <TableRow>
                                                <TableHead>User</TableHead>
                                                <TableHead className="text-right">
                                                    Papers
                                                </TableHead>
                                                <TableHead className="text-right">
                                                    Questions
                                                </TableHead>
                                                <TableHead className="text-right">
                                                    Marks
                                                </TableHead>
                                                <TableHead className="text-right">
                                                    Remixes
                                                </TableHead>
                                            </TableRow>
                                        </TableHeader>
                                        <TableBody>
                                            {allUsers.map((u) => (
                                                <TableRow key={u.user_id}>
                                                    <TableCell>
                                                        <div className="flex items-center gap-2">
                                                            <Avatar className="size-6">
                                                                <AvatarImage
                                                                    src={u.avatar_url ?? undefined}
                                                                    alt={u.username}
                                                                />
                                                                <AvatarFallback className="text-xs">
                                                                    {u.username?.slice(0, 2).toUpperCase()}
                                                                </AvatarFallback>
                                                            </Avatar>
                                                            <span className="font-medium">
                                                                {u.username}
                                                            </span>
                                                        </div>
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        {u.paper_count}
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        {u.question_count}
                                                    </TableCell>
                                                    <TableCell className="text-right font-medium">
                                                        {u.total_marks}
                                                    </TableCell>
                                                    <TableCell className="text-right">
                                                        {u.remixes_received}
                                                    </TableCell>
                                                </TableRow>
                                            ))}
                                        </TableBody>
                                    </Table>
                                )}
                        </CardContent>
                    </Card>
                )}
            </main>
        </>
    );
}