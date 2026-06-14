import { useNavigate } from "react-router-dom";
import NavBar from "@/components/navbar";
import { ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Takendown() {
    const navigate = useNavigate();

    return (
        <>
            <NavBar />
            <main className="flex flex-col items-center gap-4 py-24 text-center px-6">
                <ShieldAlert className="size-12 text-destructive" />
                <span className="text-5xl font-bold text-muted-foreground">
                    410
                </span>
                <h1 className="text-2xl font-bold">
                    This paper has been removed
                </h1>
                <p className="text-muted-foreground max-w-md">
                    This content has been taken down due to a copyright or
                    policy violation and is no longer available.
                </p>
                <p className="text-sm text-muted-foreground max-w-md">
                    If you believe this was done in error, you should contact{" "}
                    <a
                        href="mailto:4tkbytes@pm.me"
                        className="underline text-foreground"
                    >
                        the site administrators
                    </a>{" "}
                    for further assistance.
                </p>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={() => navigate(-1)}>
                        Go Back
                    </Button>
                    <Button onClick={() => navigate("/")}>
                        Home
                    </Button>
                </div>
            </main>
        </>
    );
}
