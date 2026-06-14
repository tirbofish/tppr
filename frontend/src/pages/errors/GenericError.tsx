import { useNavigate } from "react-router-dom";
import NavBar from "@/components/navbar";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface GenericErrorProps {
    title?: string;
    message?: string;
    code?: number | string;
    showNav: boolean;
}

export function GenericError({
    title = "Something went wrong",
    message = "An unexpected error occurred.",
    code,
    showNav = false,
}: GenericErrorProps) {
    const navigate = useNavigate();

    return (
        <>
            {showNav ? <NavBar /> : " "}

            <main className="flex flex-col items-center gap-4 py-24 text-center px-6">
                <AlertTriangle className="size-12 text-destructive" />
                {code && (
                    <span className="text-5xl font-bold text-muted-foreground">
                        {code}
                    </span>
                )}
                <h1 className="text-2xl font-bold">{title}</h1>
                <p className="text-muted-foreground max-w-md">{message}</p>
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
