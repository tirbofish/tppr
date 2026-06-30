import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { UserPlus } from "lucide-react";

import { useAuth } from "@/api/auth";
import {
    type Friend,
    type FriendRequest,
    acceptFriendRequest,
    cancelFriendRequest,
    declineFriendRequest,
    listFriends,
    listIncomingRequests,
    listOutgoingRequests,
    removeFriend,
    sendFriendRequest,
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
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";

function UserAvatar({ username, avatarUrl }: { username: string; avatarUrl?: string | null }) {
    return (
        <Avatar className="size-9">
            <AvatarImage src={avatarUrl ?? undefined} alt={username} />
            <AvatarFallback>
                {username?.slice(0, 2).toUpperCase() ?? "U"}
            </AvatarFallback>
        </Avatar>
    );
}

export default function Friends() {
    const { user, loading: authLoading } = useAuth();
    const navigate = useNavigate();

    const [addUsername, setAddUsername] = useState("");
    const [incoming, setIncoming] = useState<FriendRequest[]>([]);
    const [outgoing, setOutgoing] = useState<FriendRequest[]>([]);
    const [friends, setFriends] = useState<Friend[]>([]);
    const [loading, setLoading] = useState(true);
    const [sending, setSending] = useState(false);
    const [busyId, setBusyId] = useState<number | string | null>(null);

    const refresh = useCallback(async () => {
        try {
            const [inc, out, fr] = await Promise.all([
                listIncomingRequests(),
                listOutgoingRequests(),
                listFriends(),
            ]);
            setIncoming(inc.requests);
            setOutgoing(out.requests);
            setFriends(fr.friends);
        } catch (e) {
            toast.error(e instanceof Error ? e.message : "Failed to load friends");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!authLoading && !user) {
            navigate("/login?redirect=/friends", { replace: true });
        }
    }, [user, authLoading, navigate]);

    useEffect(() => {
        if (user) refresh();
    }, [user, refresh]);

    if (authLoading) return null;
    if (!user) return null;

    async function handleSend() {
        const username = addUsername.trim();
        if (!username) return;
        setSending(true);
        try {
            const { message } = await sendFriendRequest(username);
            toast.success(message);
            setAddUsername("");
            await refresh();
        } catch (e) {
            toast.error(e instanceof Error ? e.message : "Failed to send request");
        } finally {
            setSending(false);
        }
    }

    async function handleAccept(id: number) {
        setBusyId(id);
        try {
            await acceptFriendRequest(id);
            toast.success("Friend added");
            await refresh();
        } catch (e) {
            toast.error(e instanceof Error ? e.message : "Failed to accept");
        } finally {
            setBusyId(null);
        }
    }

    async function handleDecline(id: number) {
        setBusyId(id);
        try {
            await declineFriendRequest(id);
            toast.success("Request declined");
            await refresh();
        } catch (e) {
            toast.error(e instanceof Error ? e.message : "Failed to decline");
        } finally {
            setBusyId(null);
        }
    }

    async function handleCancel(id: number) {
        setBusyId(id);
        try {
            await cancelFriendRequest(id);
            toast.success("Request cancelled");
            await refresh();
        } catch (e) {
            toast.error(e instanceof Error ? e.message : "Failed to cancel");
        } finally {
            setBusyId(null);
        }
    }

    async function handleRemove(userId: string) {
        setBusyId(userId);
        try {
            await removeFriend(userId);
            toast.success("Friend removed");
            await refresh();
        } catch (e) {
            toast.error(e instanceof Error ? e.message : "Failed to remove friend");
        } finally {
            setBusyId(null);
        }
    }

    return (
        <>
            <NavBar />
            <main className="mx-auto w-full max-w-2xl px-6 py-10 space-y-6">
                <h1 className="text-2xl font-bold">Friends</h1>

                {/* Add a friend */}
                <Card>
                    <CardHeader>
                        <CardTitle>Add a friend</CardTitle>
                        <CardDescription>
                            Send a request by their username.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form
                            className="flex gap-2"
                            onSubmit={(e) => {
                                e.preventDefault();
                                handleSend();
                            }}
                        >
                            <Input
                                placeholder="Username"
                                value={addUsername}
                                onChange={(e) => setAddUsername(e.target.value)}
                            />
                            <Button type="submit" disabled={sending}>
                                <UserPlus data-icon="inline-start" />
                                Send
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                {loading ? (
                    <div className="flex justify-center py-8">
                        <Spinner />
                    </div>
                ) : (
                    <>
                        {/* Pending requests */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Pending requests</CardTitle>
                                <CardDescription>
                                    Friend requests waiting on you, and ones
                                    you've sent.
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-2">
                                    {incoming.length === 0
                                        ? (
                                            <p className="text-sm text-muted-foreground">
                                                No incoming requests.
                                            </p>
                                        )
                                        : incoming.map((r) => (
                                            <div
                                                key={r.id}
                                                className="flex items-center justify-between gap-3"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <UserAvatar
                                                        username={r.username}
                                                        avatarUrl={r.avatar_url}
                                                    />
                                                    <span className="text-sm font-medium">
                                                        {r.username}
                                                    </span>
                                                </div>
                                                <div className="flex gap-2">
                                                    <Button
                                                        size="sm"
                                                        disabled={busyId === r.id}
                                                        onClick={() =>
                                                            handleAccept(r.id)}
                                                    >
                                                        Accept
                                                    </Button>
                                                    <Button
                                                        size="sm"
                                                        variant="outline"
                                                        disabled={busyId === r.id}
                                                        onClick={() =>
                                                            handleDecline(r.id)}
                                                    >
                                                        Decline
                                                    </Button>
                                                </div>
                                            </div>
                                        ))}
                                </div>

                                <div className="space-y-2 border-t pt-4">
                                    <p className="text-xs font-medium text-muted-foreground uppercase">
                                        Sent
                                    </p>
                                    {outgoing.length === 0
                                        ? (
                                            <p className="text-sm text-muted-foreground">
                                                No outgoing requests.
                                            </p>
                                        )
                                        : outgoing.map((r) => (
                                            <div
                                                key={r.id}
                                                className="flex items-center justify-between gap-3"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <UserAvatar
                                                        username={r.username}
                                                        avatarUrl={r.avatar_url}
                                                    />
                                                    <span className="text-sm font-medium">
                                                        {r.username}
                                                    </span>
                                                </div>
                                                <Button
                                                    size="sm"
                                                    variant="outline"
                                                    disabled={busyId === r.id}
                                                    onClick={() =>
                                                        handleCancel(r.id)}
                                                >
                                                    Cancel
                                                </Button>
                                            </div>
                                        ))}
                                </div>
                            </CardContent>
                        </Card>

                        {/* Your friends */}
                        <Card>
                            <CardHeader>
                                <CardTitle>Your friends</CardTitle>
                                <CardDescription>
                                    {friends.length === 0
                                        ? "You haven't added any friends yet."
                                        : `${friends.length} friend${friends.length === 1 ? "" : "s"}`}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-2">
                                {friends.length === 0
                                    ? (
                                        <p className="text-sm text-muted-foreground">
                                            Once someone accepts your request,
                                            they'll appear here.
                                        </p>
                                    )
                                    : friends.map((f) => (
                                        <div
                                            key={f.user_id}
                                            className="flex items-center justify-between gap-3"
                                        >
                                            <div className="flex items-center gap-3">
                                                <UserAvatar
                                                    username={f.username}
                                                    avatarUrl={f.avatar_url}
                                                />
                                                <div>
                                                    <p className="text-sm font-medium">
                                                        {f.username}
                                                    </p>
                                                    {f.since && (
                                                        <p className="text-xs text-muted-foreground">
                                                            Friends since{" "}
                                                            {new Date(f.since).toLocaleDateString()}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                disabled={busyId === f.user_id}
                                                onClick={() =>
                                                    handleRemove(f.user_id)}
                                            >
                                                Remove
                                            </Button>
                                        </div>
                                    ))}
                            </CardContent>
                        </Card>
                    </>
                )}
            </main>
        </>
    );
}