import { useEffect, useState } from "react";
import { useAuth } from "@/api/auth";
import { supabase } from "@/lib/supabase";
import NavBar from "@/components/navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "@/api/client";
import {
    Dialog,
    DialogClose,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";

export default function Settings() {
    const { user, loading: authLoading, logout } = useAuth();
    const navigate = useNavigate();

    const [username, setUsername] = useState(user?.username ?? "");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");

    const [mfaFactors, setMfaFactors] = useState<
        { id: string; friendlyName?: string }[]
    >([]);
    const [enrolling, setEnrolling] = useState(false);
    const [enrollData, setEnrollData] = useState<
        { id: string; qr: string; secret: string } | null
    >(null);
    const [verifyCode, setVerifyCode] = useState("");

    useEffect(() => {
        supabase.auth.mfa.listFactors().then(({ data }) => {
            if (data?.totp) setMfaFactors(data.totp);
        });
    }, []);

    useEffect(() => {
        if (!authLoading && !user) {
            navigate("/login?redirect=/settings", { replace: true });
        }
    }, [user, authLoading, navigate]);

    if (authLoading) return null;
    if (!user) return null;

    async function handleEnroll2FA() {
        setEnrolling(true);
        const { data, error } = await supabase.auth.mfa.enroll({
            factorType: "totp",
            friendlyName: "Authenticator App",
        });
        if (error) {
            toast.error(error.message);
            setEnrolling(false);
            return;
        }
        setEnrollData({
            id: data.id,
            qr: data.totp.qr_code,
            secret: data.totp.secret,
        });
    }

    async function handleVerifyEnrollment() {
        if (!enrollData) return;
        const { data: challenge, error: challengeErr } = await supabase.auth.mfa
            .challenge({
                factorId: enrollData.id,
            });
        if (challengeErr) {
            toast.error(challengeErr.message);
            return;
        }

        const { error: verifyErr } = await supabase.auth.mfa.verify({
            factorId: enrollData.id,
            challengeId: challenge.id,
            code: verifyCode,
        });
        if (verifyErr) {
            toast.error(verifyErr.message);
            return;
        }

        toast.success("2FA enabled successfully");
        setEnrolling(false);
        setEnrollData(null);
        setVerifyCode("");

        const { data } = await supabase.auth.mfa.listFactors();
        if (data?.totp) setMfaFactors(data.totp);
    }

    async function handleUnenroll(factorId: string) {
        if (!confirm("Disable two-factor authentication?")) return;
        const { error } = await supabase.auth.mfa.unenroll({ factorId });
        if (error) {
            toast.error(error.message);
            return;
        }
        toast.success("2FA disabled");
        setMfaFactors((prev) => prev.filter((f) => f.id !== factorId));
    }

    async function handleUpdateUsername() {
        const { error } = await supabase.auth.updateUser({
            data: { username },
        });
        if (error) {
            toast.error(error.message);
        } else {
            toast.success("Username updated");
        }
    }

    async function handleChangePassword() {
        if (newPassword !== confirmPassword) {
            toast.error("Passwords do not match");
            return;
        }
        if (newPassword.length < 6) {
            toast.error("Password must be at least 6 characters");
            return;
        }
        const { error } = await supabase.auth.updateUser({
            password: newPassword,
        });
        if (error) {
            toast.error(error.message);
        } else {
            toast.success("Password updated");
            setNewPassword("");
            setConfirmPassword("");
        }
    }

    async function handleDeleteAccount() {
        const res = await apiFetch("/api/account", { method: "DELETE" });
        if (!res.ok) {
            const body = await res.json().catch(() => null);
            toast.error(body?.message ?? "Failed to delete account");
            return;
        }
        await supabase.auth.signOut();
        toast("Well, to each their own. Have a good one!");
        navigate("/", { replace: true });
    }

    return (
        <>
            <NavBar />
            <main className="mx-auto w-full max-w-2xl px-6 py-10 space-y-6">
                <h1 className="text-2xl font-bold">Settings</h1>

                {/* Profile */}
                <Card>
                    <CardHeader>
                        <CardTitle>Profile</CardTitle>
                        <CardDescription>
                            Your public account information.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <FieldGroup>
                            <Field>
                                <FieldLabel>Email</FieldLabel>
                                <Input value={user.email} disabled />
                            </Field>
                            <Field>
                                <FieldLabel>Username</FieldLabel>
                                <Input
                                    value={username}
                                    onChange={(e) =>
                                        setUsername(e.target.value)}
                                />
                            </Field>
                            <Button onClick={handleUpdateUsername} size="sm">
                                Save Username
                            </Button>
                        </FieldGroup>
                    </CardContent>
                </Card>

                {/* Password */}
                <Card>
                    <CardHeader>
                        <CardTitle>Change Password</CardTitle>
                        <CardDescription>
                            Update your account password.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <FieldGroup>
                            <Field>
                                <FieldLabel>New Password</FieldLabel>
                                <Input
                                    type="password"
                                    value={newPassword}
                                    onChange={(e) =>
                                        setNewPassword(e.target.value)}
                                />
                            </Field>
                            <Field>
                                <FieldLabel>Confirm Password</FieldLabel>
                                <Input
                                    type="password"
                                    value={confirmPassword}
                                    onChange={(e) =>
                                        setConfirmPassword(e.target.value)}
                                />
                            </Field>
                            <Button onClick={handleChangePassword} size="sm">
                                Update Password
                            </Button>
                        </FieldGroup>
                    </CardContent>
                </Card>

                {/* Two-Factor Authentication */}
                <Card>
                    <CardHeader>
                        <CardTitle>Two-Factor Authentication</CardTitle>
                        <CardDescription>
                            Add an extra layer of security with an authenticator
                            app.
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {mfaFactors.length > 0 && !enrolling
                            ? (
                                <div className="space-y-3">
                                    <p className="text-sm text-green-600 font-medium">
                                        2FA is enabled
                                    </p>
                                    {mfaFactors.map((f) => (
                                        <div
                                            key={f.id}
                                            className="flex items-center justify-between"
                                        >
                                            <span className="text-sm">
                                                {f.friendlyName ||
                                                    "Authenticator"}
                                            </span>
                                            <Button
                                                variant="destructive"
                                                size="sm"
                                                onClick={() =>
                                                    handleUnenroll(f.id)}
                                            >
                                                Remove
                                            </Button>
                                        </div>
                                    ))}
                                </div>
                            )
                            : enrollData
                            ? (
                                <FieldGroup>
                                    <Field>
                                        <FieldLabel>
                                            Scan this QR code with your
                                            authenticator app
                                        </FieldLabel>
                                        <img
                                            src={enrollData.qr}
                                            alt="TOTP QR Code"
                                            className="w-48 min-w-48 h-48 min-h-48 aspect-square object-contain"
                                        />
                                    </Field>
                                    <Field>
                                        <FieldLabel>
                                            Or enter this secret manually
                                        </FieldLabel>
                                        <code className="text-xs bg-muted p-2 rounded block break-all select-all">
                                            {enrollData.secret}
                                        </code>
                                    </Field>
                                    <Field>
                                        <FieldLabel>
                                            Enter the 6-digit code from your app
                                        </FieldLabel>
                                        <Input
                                            value={verifyCode}
                                            onChange={(e) =>
                                                setVerifyCode(e.target.value)}
                                            placeholder="000000"
                                            maxLength={6}
                                        />
                                    </Field>
                                    <div className="flex gap-2">
                                        <Button
                                            size="sm"
                                            onClick={handleVerifyEnrollment}
                                        >
                                            Verify & Enable
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={() => {
                                                setEnrolling(false);
                                                setEnrollData(null);
                                            }}
                                        >
                                            Cancel
                                        </Button>
                                    </div>
                                </FieldGroup>
                            )
                            : (
                                <Button size="sm" onClick={handleEnroll2FA}>
                                    Enable 2FA
                                </Button>
                            )}
                    </CardContent>
                </Card>

                {/* Danger Zone */}
                <Card className="border-destructive/50">
                    <CardHeader>
                        <CardTitle className="text-destructive">
                            Danger Zone
                        </CardTitle>
                        <CardDescription>
                            Irreversible actions on your account.
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <Separator />
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium">
                                    Sign out everywhere
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    Invalidates all active sessions.
                                </p>
                            </div>
                            <Button
                                variant="outline"
                                size="sm"
                                onClick={logout}
                            >
                                Sign out
                            </Button>
                        </div>
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="text-sm font-medium">
                                    Delete account
                                </p>
                                <p className="text-xs text-muted-foreground">
                                    Permanently delete your account and all
                                    data.
                                </p>
                            </div>
                            <Dialog>
                                <DialogTrigger asChild>
                                    <Button variant="destructive" size="sm">
                                        Delete
                                    </Button>
                                </DialogTrigger>
                                <DialogContent>
                                    <DialogHeader>
                                        <DialogTitle>Are you sure?</DialogTitle>
                                        <DialogDescription>
                                            This action cannot be undone, and we
                                            would hate to see you go.
                                        </DialogDescription>
                                    </DialogHeader>
                                    <DialogFooter>
                                        <DialogClose asChild>
                                            <Button variant="outline">
                                                Cancel
                                            </Button>
                                        </DialogClose>
                                        <Button
                                            variant="destructive"
                                            onClick={handleDeleteAccount}
                                        >
                                            Delete my account
                                        </Button>
                                    </DialogFooter>
                                </DialogContent>
                            </Dialog>
                        </div>
                    </CardContent>
                </Card>
            </main>
        </>
    );
}
