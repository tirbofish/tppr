import * as React from "react"
import {
  CheckCircle2,
  FileJson,
  Grid2X2,
  ImageIcon,
  UploadCloud,
} from "lucide-react"

import NavBar from "@/components/navbar"
import Question, { type PaperOutput, type PaperQuestion } from "@/components/question"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  FileUpload,
  FileUploadClear,
  FileUploadDropzone,
  FileUploadItem,
  FileUploadItemDelete,
  FileUploadItemMetadata,
  FileUploadItemPreview,
  FileUploadList,
  FileUploadTrigger,
} from "@/components/ui/file-upload"
import { RelativeTimeCard } from "@/components/ui/relative-time-card"

const maxJsonSize = 12 * 1024 * 1024
const nullCharacter = String.fromCharCode(0)

function cleanText(value: unknown): string {
  if (value == null) {
    return ""
  }

  if (Array.isArray(value)) {
    return value.map(cleanText).filter(Boolean).join("\n")
  }

  if (typeof value === "object") {
    return JSON.stringify(value)
  }

  return String(value)
    .split(nullCharacter)
    .join("")
    .replace(/[\u200B-\u200D\uFEFF]/g, "")
    .replace(/\r\n?/g, "\n")
    .replace(/[^\S\n]+/g, " ")
    .replace(/ *\n */g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim()
}

function firstText(...values: unknown[]): string {
  for (const value of values) {
    const cleaned = cleanText(value)

    if (cleaned) {
      return cleaned
    }
  }

  return ""
}

function normalizePaperOutput(value: unknown): PaperOutput {
  if (Array.isArray(value)) {
    return { questions: value as PaperQuestion[] }
  }

  if (value && typeof value === "object") {
    const candidate = value as PaperOutput

    if (Array.isArray(candidate.questions)) {
      return candidate
    }
  }

  throw new Error("JSON must contain a questions array, or be an array of questions.")
}

function getQuestionLabel(question: PaperQuestion, index: number) {
  const number = cleanText(question.number)
  return number ? `Question ${number}` : `Question ${index + 1}`
}

function getQuestionType(question: PaperQuestion) {
  return cleanText(question.type).replace(/_/g, " ") || "Unknown"
}

function getQuestionMarks(question: PaperQuestion) {
  const marks = cleanText(question.marks)

  if (marks) {
    return Number(marks) === 1 ? "1 mark" : `${marks} marks`
  }

  return question.type === "multiple_choice" ? "1 mark" : "Not listed"
}

function getQuestionText(question: PaperQuestion) {
  return firstText(
    question.stimulusQuestion,
    question.stimulus_question,
    question.stimulus,
    question.context,
    question.questionToAnswer,
    question.question_to_answer,
    question.question,
    question.prompt,
    question.answerText,
    question.answer_text,
    question.answer,
    question.text
  )
}

function hasQuestionImage(question: PaperQuestion) {
  return Boolean(
    question.image ||
      question.stimulusImage ||
      question.stimulus_image ||
      question.images?.[0] ||
      question.answerImage ||
      question.answer_image ||
      question.answerImages?.[0] ||
      question.answer_images?.[0] ||
      question.promptImage ||
      question.prompt_image ||
      question.promptImages?.[0] ||
      question.prompt_images?.[0] ||
      question.options?.some((option) => option.image || option.images?.[0])
  )
}

function getSectionForPage(paperData: PaperOutput, page: string | number | undefined) {
  const pageNumber = Number(page)

  if (!Number.isFinite(pageNumber)) {
    return null
  }

  return (
    paperData.metadata?.sections?.find((section) => {
      const pages = cleanText(section.pages)
      const match = pages.match(/(\d+)\s*[–-]\s*(\d+)/) ?? pages.match(/(\d+)/)

      if (!match) {
        return false
      }

      const start = Number(match[1])
      const end = Number(match[2] ?? match[1])

      return pageNumber >= start && pageNumber <= end
    }) ?? null
  )
}

type QuestionHoverDetailsProps = {
  paperData: PaperOutput
  question: PaperQuestion
  index: number
  fileName?: string
}

function QuestionHoverDetails({
  paperData,
  question,
  index,
  fileName,
}: QuestionHoverDetailsProps) {
  const paper = cleanText(paperData.metadata?.paper) || "Unknown paper"
  const year = cleanText(paperData.metadata?.year) || "Unknown year"
  const page = cleanText(question.page) || "Not listed"
  const section = getSectionForPage(paperData, question.page)

  return (
    <div className="grid gap-2 text-sm">
      <div>
        <p className="text-xs font-medium text-muted-foreground">Question</p>
        <p className="font-medium">{getQuestionLabel(question, index)}</p>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div>
          <p className="font-medium text-muted-foreground">Paper</p>
          <p>{paper}</p>
        </div>
        <div>
          <p className="font-medium text-muted-foreground">Year</p>
          <p>{year}</p>
        </div>
        <div>
          <p className="font-medium text-muted-foreground">Page</p>
          <p>{page}</p>
        </div>
        <div>
          <p className="font-medium text-muted-foreground">Marks</p>
          <p>{getQuestionMarks(question)}</p>
        </div>
        {section ? (
          <div className="col-span-2">
            <p className="font-medium text-muted-foreground">Section</p>
            <p>
              {section.name ?? "Unnamed section"}
              {section.pages ? ` · pages ${section.pages}` : ""}
            </p>
          </div>
        ) : null}
      </div>
      {fileName ? (
        <p className="truncate text-xs text-muted-foreground">{fileName}</p>
      ) : null}
    </div>
  )
}

export default function QuestionUpload() {
  const [files, setFiles] = React.useState<File[]>([])
  const [paperData, setPaperData] = React.useState<PaperOutput | null>(null)
  const [uploadedAt, setUploadedAt] = React.useState<Date | null>(null)
  const [selectedIndex, setSelectedIndex] = React.useState<number | null>(null)
  const [error, setError] = React.useState<string | null>(null)

  const selectedQuestion =
    selectedIndex == null ? null : paperData?.questions?.[selectedIndex]

  const handleFiles = React.useCallback(async (nextFiles: File[]) => {
    setFiles(nextFiles)
    setSelectedIndex(null)
    setError(null)

    const file = nextFiles[0]

    if (!file) {
      setPaperData(null)
      setUploadedAt(null)
      return
    }

    try {
      const text = await file.text()
      const parsed = normalizePaperOutput(JSON.parse(text))

      setPaperData(parsed)
      setUploadedAt(new Date())
    } catch (caughtError) {
      setPaperData(null)
      setUploadedAt(null)
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Could not read this JSON file."
      )
    }
  }, [])

  const fileName = files[0]?.name
  const questions = paperData?.questions ?? []

  if (paperData && selectedIndex != null && selectedQuestion) {
    return (
      <Question
        data={paperData}
        questionIndex={selectedIndex}
        onBack={() => setSelectedIndex(null)}
        backLabel="All questions"
      />
    )
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <NavBar />
      <main className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-6xl gap-6 px-4 py-8 sm:px-6">
        <Card>
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <FileJson className="size-5" />
              JSON question viewer
            </CardTitle>
            <CardDescription>
              Upload an extracted paper JSON file and choose any question to view.
            </CardDescription>
            {uploadedAt ? (
              <CardAction>
                <RelativeTimeCard date={uploadedAt} variant="muted" />
              </CardAction>
            ) : null}
          </CardHeader>
          <CardContent className="space-y-4">
            <FileUpload
              value={files}
              onValueChange={handleFiles}
              accept="application/json,.json"
              maxFiles={1}
              maxSize={maxJsonSize}
              onFileValidate={(file) => {
                if (!file.name.toLowerCase().endsWith(".json")) {
                  return "Only JSON files are supported."
                }

                return null
              }}
              onFileReject={(_, message) => setError(message)}
              invalid={Boolean(error)}
            >
              <FileUploadDropzone>
                <div className="flex size-12 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <UploadCloud className="size-6" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium">Drop output JSON here</p>
                  <p className="text-xs text-muted-foreground">
                    One file, up to 12MB
                  </p>
                </div>
                <FileUploadTrigger asChild>
                  <Button type="button" variant="outline">
                    <FileJson />
                    Browse JSON
                  </Button>
                </FileUploadTrigger>
              </FileUploadDropzone>

              <FileUploadList>
                {files.map((file) => (
                  <FileUploadItem key={`${file.name}-${file.lastModified}`} value={file}>
                    <FileUploadItemPreview />
                    <FileUploadItemMetadata />
                    <FileUploadItemDelete />
                  </FileUploadItem>
                ))}
              </FileUploadList>
              <FileUploadClear
                onClick={() => {
                  setPaperData(null)
                  setUploadedAt(null)
                  setSelectedIndex(null)
                  setError(null)
                }}
              />
            </FileUpload>

            {error ? (
              <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                {error}
              </div>
            ) : null}

            {paperData ? (
              <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-muted/20 px-3 py-2 text-sm">
                <CheckCircle2 className="size-4 text-muted-foreground" />
                <span className="font-medium">{questions.length} questions loaded</span>
                <span className="text-muted-foreground">
                  {cleanText(paperData.metadata?.paper) || "Unknown paper"}
                </span>
                <span className="text-muted-foreground">
                  {cleanText(paperData.metadata?.year) || "Unknown year"}
                </span>
              </div>
            ) : null}
          </CardContent>
        </Card>

        {paperData ? (
          <Card>
            <CardHeader className="border-b">
              <CardTitle className="flex items-center gap-2">
                <Grid2X2 className="size-5" />
                Question tiles
              </CardTitle>
              <CardDescription>
                Hover a tile for paper metadata. Press it to open the full question.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {questions.map((question, index) => {
                  const text = getQuestionText(question)

                  return (
                    <RelativeTimeCard
                      key={`${getQuestionLabel(question, index)}-${index}`}
                      date={uploadedAt ?? new Date()}
                      asChild
                      align="start"
                      side="top"
                      className="block w-full text-left"
                      details={
                        <QuestionHoverDetails
                          paperData={paperData}
                          question={question}
                          index={index}
                          fileName={fileName}
                        />
                      }
                    >
                      <button
                        type="button"
                        className="grid min-h-36 w-full gap-3 rounded-lg border bg-background p-4 text-left transition-colors hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        onClick={() => setSelectedIndex(index)}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium">
                              {getQuestionLabel(question, index)}
                            </p>
                            <p className="text-xs capitalize text-muted-foreground">
                              {getQuestionType(question)}
                            </p>
                          </div>
                          <span className="rounded-md border bg-muted/60 px-2 py-1 text-xs font-medium">
                            {getQuestionMarks(question)}
                          </span>
                        </div>
                        <p className="line-clamp-3 text-sm leading-6 text-muted-foreground">
                          {text || "No extracted text. Image stimulus may contain the question."}
                        </p>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          {hasQuestionImage(question) ? (
                            <>
                              <ImageIcon className="size-3.5" />
                              Image
                            </>
                          ) : (
                            "Text only"
                          )}
                        </div>
                      </button>
                    </RelativeTimeCard>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        ) : null}
      </main>
    </div>
  )
}
