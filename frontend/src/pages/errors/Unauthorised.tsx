import { useLocation, useNavigate } from "react-router-dom";
import NavBar from "@/components/navbar";
import { ShieldX } from "lucide-react";
import { Button } from "@/components/ui/button";
import { loginPath } from "@/lib/routes";

export default function Unauthorized() {
    const navigate = useNavigate();
    const location = useLocation();
    const currentPath = `${location.pathname}${location.search}${location.hash}`;

    return (
        <>
            <NavBar />
            <main className="flex flex-col items-center gap-4 py-24 text-center">
                <ShieldX className="size-12 text-destructive" />
                <h1 className="text-2xl font-bold">Access Denied</h1>
                <p className="text-muted-foreground">
                    This paper is private. Please log in to view it.
                </p>
                <Button
                    onClick={() => navigate(loginPath(currentPath))}
                >
                    Go to Login
                </Button>
            </main>
        </>
    );
}
