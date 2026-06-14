import { Link, useLocation, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  FileText,
  Filter,
  NotepadTextDashed,
  Plus,
  SearchIcon,
  ShieldCheck,
} from "lucide-react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/api/auth";
import { Dialog, DialogTrigger } from "@/components/ui/dialog";
import { CreatePaperDialog } from "./create-paper-dialog";
import { useEffect, useRef, useState } from "react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import { AllNESASubjectsList } from "@/lib/subjects";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useOnline } from "@/lib/hooks";
import { Popover, PopoverContent, PopoverTrigger } from "./ui/popover";

export default function NavBar() {
  const online = useOnline();

  const { user, logout } = useAuth();
  const [newPaperOpen, setNewPaperOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [focused, setFocused] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [subject, setSubject] = useState("");
  const [source, setSource] = useState("");
  const [year, setYear] = useState("");
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  const [showSearchGuide, setShowSearchGuide] = useState(false);
  const location = useLocation();
  const isSearchPage = location.pathname === "/search";

  useEffect(() => {
    if (!localStorage.getItem("hasSeenSearchGuide")) {
      setShowSearchGuide(true);
    }
  }, []);

  function dismissGuide() {
    localStorage.setItem("hasSeenSearchGuide", "true");
    setShowSearchGuide(false);
  }

  function handleSearch(e: React.SubmitEvent) {
    e.preventDefault();
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (subject && subject !== "all") params.set("subject", subject);
    if (source) params.set("source", source);
    if (year) params.set("year", year);
    params.set("page", "1");
    params.set("per_page", "20");
    navigate(`/search?${params.toString()}`);
    setFocused(false);
    setShowFilters(false);
    inputRef.current?.blur();
  }

  <Tooltip>
    <TooltipTrigger>
      <span className="relative flex size-2">
        <span className="absolute inline-flex size-full animate-ping rounded-full bg-orange-400 opacity-75" />
        <span className="inline-flex size-2 rounded-full bg-orange-500" />
      </span>
    </TooltipTrigger>
    <TooltipContent>You're offline — changes saved locally</TooltipContent>
  </Tooltip>;

  return (
    <header className="w-full border-b">
      <div className="mx-auto flex h-16 w-full items-center px-6">
        {/* Brand — takes up left space */}
        <Link to="/" className="flex flex-1 shrink-0 items-center gap-2">
          <div className="flex size-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <NotepadTextDashed className="size-4" />
          </div>
          <span className="hidden text-lg font-semibold sm:inline">
            Thribhu's Past Paper Repository
          </span>
        </Link>

        {/* Search bar — centered */}
        {!isSearchPage && (
          <form
            onSubmit={handleSearch}
            className="mx-auto flex max-w-md flex-1 items-center gap-2"
          >
            <Popover
              open={showSearchGuide}
              onOpenChange={(open) => !open && dismissGuide()}
            >
              <PopoverTrigger asChild>
                <div className="relative flex-1">
                  <SearchIcon className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    ref={inputRef}
                    placeholder="Search papers…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => {
                      setFocused(true);
                      dismissGuide();
                    }}
                    onBlur={(e) => {
                      if (e.relatedTarget?.closest("[data-filter-toggle]")) {
                        return;
                      }
                      setFocused(false);
                    }}
                    className={`pl-8 ${
                      showSearchGuide ? "ring-2 ring-primary" : ""
                    }`}
                  />
                </div>
              </PopoverTrigger>
              <PopoverContent side="bottom" align="center" className="w-72">
                <p className="font-medium text-sm">Start by searching</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Search for past papers by subject, year, or topic here.
                </p>
                <Button
                  size="sm"
                  className="mt-3 w-full"
                  onClick={dismissGuide}
                >
                  Got it!
                </Button>
              </PopoverContent>
            </Popover>
            {focused && (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="size-8 shrink-0"
                data-filter-toggle
                onClick={() => setShowFilters((v) => !v)}
                aria-label="Toggle filters"
              >
                <Filter className="size-4" />
              </Button>
            )}
          </form>
        )}

        {/* Right */}
        <div className="flex flex-1 shrink-0 items-center justify-end gap-2">
          {user
            ? (
              <>
                <Button asChild variant="ghost" size="icon" className="size-8">
                  <Link to="/papers">
                    <FileText className="size-4" />
                  </Link>
                </Button>

                <Dialog open={newPaperOpen} onOpenChange={setNewPaperOpen}>
                  <DialogTrigger asChild>
                    <Button variant="outline" size="sm">
                      <Plus data-icon="inline-start" />
                      New Paper
                    </Button>
                  </DialogTrigger>
                  <CreatePaperDialog onCreated={() => setNewPaperOpen(true)} />
                </Dialog>

                <DropdownMenu>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            className="relative size-8 rounded-full"
                          >
                            {user.admin
                              ? <ShieldCheck className="size-5 text-primary" />
                              : (
                                <Avatar className="size-8">
                                  <AvatarImage src="dont_worry_about_it_just_need_to_ensure_the_avatar_fetching_fails" />
                                  <AvatarFallback>
                                    {user.username?.slice(0, 2).toUpperCase() ??
                                      "U"}
                                  </AvatarFallback>
                                </Avatar>
                              )}
                            <span
                              className={`absolute bottom-0 right-0 size-2.5 rounded-full border-2 border-background ${
                                online ? "bg-green-500" : "bg-yellow-500"
                              }`}
                            />
                          </Button>
                        </DropdownMenuTrigger>
                      </TooltipTrigger>
                      <TooltipContent side="bottom">
                        {online
                          ? "Online; syncing to cloud"
                          : "Offline; changes saved locally"}
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                  <DropdownMenuContent align="end">
                    <DropdownMenuGroup>
                      {user.admin && (
                        <>
                          <DropdownMenuItem
                            disabled
                            className="gap-2 text-primary"
                          >
                            <ShieldCheck />
                            Admin mode
                          </DropdownMenuItem>
                          <DropdownMenuItem asChild>
                            <Link to="/admin/takedowns">
                              <ShieldCheck />
                              Takedowns
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                        </>
                      )}
                      <DropdownMenuItem onClick={logout}>
                        Sign out
                      </DropdownMenuItem>
                    </DropdownMenuGroup>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            )
            : (
              <>
                <Button asChild variant="outline">
                  <Link
                    to={`/login?redirect=${
                      encodeURIComponent(location.pathname + location.search)
                    }`}
                  >
                    Login
                  </Link>
                </Button>
                <Button asChild>
                  <Link
                    to={`/signup?redirect=${
                      encodeURIComponent(location.pathname + location.search)
                    }`}
                  >
                    Signup
                  </Link>
                </Button>
              </>
            )}
        </div>
      </div>

      {/* Filter row — only visible when search is focused and toggled */}
      {focused && showFilters && (
        <div className="border-t bg-muted/50 px-6 py-3">
          <form
            onSubmit={handleSearch}
            className="mx-auto flex max-w-2xl items-center justify-center gap-3"
          >
            <Select value={subject} onValueChange={setSubject}>
              <SelectTrigger className="w-44" onFocus={() => setFocused(true)}>
                <SelectValue placeholder="Subject" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Any subject</SelectItem>
                <AllNESASubjectsList />
              </SelectContent>
            </Select>
            <Input
              placeholder="Source"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              onFocus={() => setFocused(true)}
              className="w-28"
            />
            <Input
              type="number"
              placeholder="Year"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              onFocus={() => setFocused(true)}
              min={2000}
              className="w-24"
            />
            <Button type="submit" size="sm">
              Search
            </Button>
          </form>
        </div>
      )}
    </header>
  );
}
