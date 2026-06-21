import { Link } from "react-router-dom";
import { Monitor, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/lib/theme";
import { useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

const BACKEND_URL_KEY = "tppr-custom-backend-url";

export function Footer() {
    const { theme, setTheme } = useTheme();
    const [url, setUrl] = useState(() => localStorage.getItem(BACKEND_URL_KEY) ?? "");

    function cycleTheme() {
        const next = theme === "light" ? "dark" : theme === "dark" ? "system" : "light";
        setTheme(next);
    }

    function saveBackend() {
        const trimmed = url.trim().replace(/\/+$/, "");
        if (trimmed) {
            localStorage.setItem(BACKEND_URL_KEY, trimmed);
        } else {
            localStorage.removeItem(BACKEND_URL_KEY);
        }
        window.location.reload();
    }

    function clearBackend() {
        localStorage.removeItem(BACKEND_URL_KEY);
        setUrl("");
        window.location.reload();
    }

    return (
        <footer className="border-t mt-auto">
            <div className="mx-auto flex w-full max-w-6xl flex-col items-center gap-4 px-6 py-6 sm:flex-row sm:justify-between">
                <Dialog>
                    <DialogTrigger asChild>
                        <button className="text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer">
                            © 2026 Thribhu K (It's literally his past paper repository). Licensed under MIT.
                        </button>
                    </DialogTrigger>
                    <DialogContent>
                        <DialogHeader>
                            <DialogTitle>Custom Backend</DialogTitle>
                            <DialogDescription>
                                Point the frontend at your own backend instance. Leave empty to use the default.
                            </DialogDescription>
                        </DialogHeader>
                        <div className="flex flex-col gap-3">
                            <Input
                                placeholder="https://your-backend.example.com"
                                value={url}
                                onChange={(e) => setUrl(e.target.value)}
                            />
                            <div className="flex gap-2 justify-end">
                                <Button variant="outline" size="sm" onClick={clearBackend}>
                                    Reset
                                </Button>
                                <Button size="sm" onClick={saveBackend}>
                                    Save & Reload
                                </Button>
                            </div>
                            {localStorage.getItem(BACKEND_URL_KEY) && (
                                <p className="text-xs text-muted-foreground">
                                    Currently using: <code className="text-foreground">{localStorage.getItem(BACKEND_URL_KEY)}</code>
                                </p>
                            )}
                        </div>
                    </DialogContent>
                </Dialog>
                <nav className="flex items-center gap-4 text-xs text-muted-foreground">
                    <Link to="/legal/privacy" className="hover:text-foreground transition-colors">
                        Privacy
                    </Link>
                    <Link to="/legal/copyright" className="hover:text-foreground transition-colors">
                        Copyright
                    </Link>
                    <a
                        href="https://github.com/TempeHS/2026SE_MajorProject_Thribhu.K"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:text-foreground transition-colors"
                    >
                        GitHub
                    </a>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="size-7"
                        onClick={cycleTheme}
                        title={`Theme: ${theme}`}
                    >
                        {theme === "light" && <Sun className="size-3.5" />}
                        {theme === "dark" && <Moon className="size-3.5" />}
                        {theme === "system" && <Monitor className="size-3.5" />}
                    </Button>
                </nav>
            </div>
        </footer>
    );
}