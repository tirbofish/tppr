import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { NotepadTextDashed } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useAuth } from "@/api/auth"

export default function NavBar() {
  const { user, logout } = useAuth()

  return (
    <header className="w-full border-b">
      <div className="mx-auto flex h-16 w-full items-center px-6">
        {/* Left*/}
        <div className="flex items-center gap-2">
          <div className="flex size-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <NotepadTextDashed className="size-4" />
          </div>
          <span className="text-lg font-semibold">Thribhu's Past Paper Repository</span>
        </div>

        {/* Right*/}
        <div className="ml-auto flex items-center gap-2">
          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative size-8 rounded-full">
                  <Avatar className="size-8">
                    <AvatarImage src="force_to_not_work" />
                    <AvatarFallback>{user.username?.slice(0, 2).toUpperCase() ?? "U"}</AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={logout}>
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <>
              <Button asChild variant="outline">
                <Link to="/login">Login</Link>
              </Button>
              <Button asChild>
                <Link to="/signup">Signup</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  )
}