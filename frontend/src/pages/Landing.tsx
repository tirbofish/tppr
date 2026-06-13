import { Link } from "react-router-dom";
import NavBar from "@/components/navbar";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/api/auth";
import {
  BookOpen,
  Download,
  NotepadTextDashed,
  Search,
  Share2,
} from "lucide-react";

export default function Landing() {
  const { user } = useAuth();

  return (
    <>
      <NavBar />
      <main className="mx-auto w-full max-w-6xl px-6">
        {/* Hero */}
        <section className="flex min-h-[calc(100vh-12rem)] flex-col items-center justify-center gap-6 text-center">
          <div className="flex size-16 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <NotepadTextDashed className="size-10" />
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Thribhu's Past Paper Repository
          </h1>
          <p className="max-w-lg text-lg text-muted-foreground">
            Create, organise, and share HSC past paper questions. A modern
            alternative to{" "}
            <a
              href="https://thsconline.github.io/s/"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground transition-colors"
            >
              thsconline
            </a>
            , if you will.
          </p>
          <p className="text-sm text-muted-foreground">
            Built by a student, for students
          </p>
          <div className="flex gap-3">
            {user
              ? (
                <>
                  <Button asChild size="lg">
                    <Link to="/papers">My Papers</Link>
                  </Button>
                  <Button asChild variant="outline" size="lg">
                    <Link to="/search">Browse Questions</Link>
                  </Button>
                </>
              )
              : (
                <>
                  <Button asChild size="lg">
                    <Link to="/signup?redirect=%2Fpapers">Get Started</Link>
                  </Button>
                  <Button asChild variant="outline" size="lg">
                    <Link to="/login?redirect=%2Fpapers">Log In</Link>
                  </Button>
                </>
              )}
          </div>
        </section>

        {/* Features */}
        <section className="grid gap-8 pb-24 sm:grid-cols-2 lg:grid-cols-4">
          <Feature
            icon={<BookOpen className="size-5" />}
            title="Advanced Rendering"
            description="Full math support with KaTeX and advanced rendering with Markdown. Questions render exactly as they appear on paper."
          />
          <Feature
            icon={<Search className="size-5" />}
            title="Search & Filter"
            description="Find questions by subject, year, source, or topic across the public question pool."
          />
          <Feature
            icon={<Share2 className="size-5" />}
            title="Remix & Share"
            description="Copy any public paper, remix it with your own edits, and publish it back to the world."
          />
          <Feature
            icon={<Download className="size-5" />}
            title="Focused Study Mode"
            description="Tackle questions one at a time. Reveal answers and criteria only when you're ready."
          />
        </section>
      </main>
    </>
  );
}

function Feature({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border p-5">
      <div className="flex size-9 items-center justify-center rounded-md bg-primary/10 text-primary">
        {icon}
      </div>
      <h3 className="font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}
