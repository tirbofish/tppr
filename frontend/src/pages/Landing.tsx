import NavBar from "@/components/navbar"
import { NotepadTextDashed } from "lucide-react"

export default function Landing() {
  return (
    <>
      <NavBar />
      <main className="mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-6xl items-center justify-center px-6">
        <div className="flex flex-col items-center gap-4 text-center">
          <div className="flex size-16 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <NotepadTextDashed className="size-10" />
          </div>
          <h1 className="text-3xl font-bold">Thribhu's Past Paper Repository</h1>
        </div>
      </main>
    </>
  )
}