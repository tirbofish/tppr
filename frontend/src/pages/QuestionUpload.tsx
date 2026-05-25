/// WARNING
//
// This page is made with AI and is only used for testing. Later on, I will replace this with my own UI design

import * as React from "react"
import {
  AlertCircle,
  CheckCircle2,
  FileJson,
  Grid2X2,
  ImageIcon,
  Loader2,
  UploadCloud,
} from "lucide-react"

import NavBar from "@/components/navbar"
import { useAuth } from "@/api/auth"
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
  FileUploadItemProgress,
  FileUploadItemPreview,
  FileUploadList,
  FileUploadTrigger,
} from "@/components/ui/file-upload"
import { RelativeTimeCard } from "@/components/ui/relative-time-card"

const maxJsonSize = 12 * 1024 * 1024
const maxUploadSize = 80 * 1024 * 1024
const nullCharacter = String.fromCharCode(0)
const terminalUploadStatuses = new Set(["complete", "failed"])

type UploadPhase = "idle" | "uploading" | "processing" | "complete" | "failed"

type UploadStatus = {
  upload_id?: string
  paper_id?: string
  status?: string
  stage?: string
  progress?: number
  message?: string
  progress_url?: string
  result_url?: string
  error?: string
  details?: string
  msg?: string
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null
  }

  return value as Record<string, unknown>
}

function cleanText(value: unknown): string {
  if (value == null) {
    return ""
  }

  if (Array.isArray(value)) {
    return value.map(cleanText).filter(Boolean).join("\n")
  }

  const record = asRecord(value)
  if (record) {
    for (const key of ["text", "question", "prompt", "answer"]) {
      const cleaned = cleanText(record[key])

      if (cleaned) {
        return cleaned
      }
    }

    return ""
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

function isJsonFile(file: File) {
  return (
    file.type === "application/json" ||
    file.name.toLowerCase().endsWith(".json")
  )
}

function isPdfFile(file: File) {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
}

function getUploadMessage(status: UploadStatus | null, phase: UploadPhase) {
  if (status?.message) {
    return status.message
  }

  if (phase === "uploading") {
    return "Uploading file..."
  }

  if (phase === "processing") {
    return "Processing upload..."
  }

  if (phase === "complete") {
    return "Upload complete."
  }

  if (phase === "failed") {
    return "Upload failed."
  }

  return "Ready to upload."
}

function clampProgress(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)))
}

function parseUploadResponse(text: string): UploadStatus {
  if (!text) {
    return {}
  }

  const parsed = JSON.parse(text) as UploadStatus
  return parsed
}

function getUploadErrorMessage(status: UploadStatus, fallback: string) {
  return status.message || status.details || status.error || status.msg || fallback
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

function hasBlockImage(value: unknown) {
  const record = asRecord(value)

  return Boolean(record?.image || (record?.images as unknown[] | undefined)?.[0])
}

function hasQuestionImage(question: PaperQuestion) {
  return Boolean(
    hasBlockImage(question.stimulus) ||
      hasBlockImage(question.question) ||
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
  const { user } = useAuth()
  const [files, setFiles] = React.useState<File[]>([])
  const [paperData, setPaperData] = React.useState<PaperOutput | null>(null)
  const [uploadedAt, setUploadedAt] = React.useState<Date | null>(null)
  const [selectedIndex, setSelectedIndex] = React.useState<number | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const [uploadPhase, setUploadPhase] = React.useState<UploadPhase>("idle")
  const [uploadProgress, setUploadProgress] = React.useState(0)
  const [uploadStatus, setUploadStatus] = React.useState<UploadStatus | null>(null)
  const xhrRef = React.useRef<XMLHttpRequest | null>(null)
  const pollTimeoutRef = React.useRef<number | null>(null)
  const uploadRunRef = React.useRef(0)

  const selectedQuestion =
    selectedIndex == null ? null : paperData?.questions?.[selectedIndex]

  const stopPolling = React.useCallback(() => {
    if (pollTimeoutRef.current != null) {
      window.clearTimeout(pollTimeoutRef.current)
      pollTimeoutRef.current = null
    }
  }, [])

  const abortUpload = React.useCallback(() => {
    xhrRef.current?.abort()
    xhrRef.current = null
    stopPolling()
  }, [stopPolling])

  React.useEffect(() => {
    return () => {
      abortUpload()
      uploadRunRef.current += 1
    }
  }, [abortUpload])

  const pollUploadStatus = React.useCallback(
    (progressUrl: string, runId: number) => {
      stopPolling()

      const poll = async () => {
        try {
          const response = await fetch(progressUrl, { credentials: "include" })
          const status = (await response.json()) as UploadStatus

          if (runId !== uploadRunRef.current) {
            return
          }

          if (!response.ok) {
            throw new Error(getUploadErrorMessage(status, "Could not load upload status."))
          }

          setUploadStatus(status)
          setUploadProgress(clampProgress(status.progress ?? 35))

          const nextStatus = status.status ?? "processing"

          if (terminalUploadStatuses.has(nextStatus)) {
            setUploadPhase(nextStatus === "complete" ? "complete" : "failed")

            if (nextStatus === "complete") {
              setUploadedAt(new Date())
            } else {
              setError(getUploadErrorMessage(status, "Upload failed."))
            }

            return
          }

          setUploadPhase("processing")
          pollTimeoutRef.current = window.setTimeout(poll, 1200)
        } catch (caughtError) {
          if (runId !== uploadRunRef.current) {
            return
          }

          setUploadPhase("failed")
          setError(
            caughtError instanceof Error
              ? caughtError.message
              : "Could not load upload status."
          )
        }
      }

      pollTimeoutRef.current = window.setTimeout(poll, 600)
    },
    [stopPolling]
  )

  const uploadFile = React.useCallback(
    (file: File, runId: number) =>
      new Promise<UploadStatus>((resolve, reject) => {
        const formData = new FormData()
        const xhr = new XMLHttpRequest()

        formData.append("file", file)
        xhrRef.current = xhr

        xhr.open("POST", "/api/upload")
        xhr.withCredentials = true

        xhr.upload.onprogress = (event) => {
          if (runId !== uploadRunRef.current || !event.lengthComputable) {
            return
          }

          setUploadPhase("uploading")
          setUploadProgress(clampProgress((event.loaded / event.total) * 25))
        }

        xhr.onload = () => {
          xhrRef.current = null

          let status: UploadStatus = {}

          try {
            status = parseUploadResponse(xhr.responseText)
          } catch {
            reject(new Error("Upload response was not valid JSON."))
            return
          }

          if (xhr.status < 200 || xhr.status >= 300) {
            reject(new Error(getUploadErrorMessage(status, "Upload failed.")))
            return
          }

          resolve(status)
        }

        xhr.onerror = () => {
          xhrRef.current = null
          reject(new Error("Could not upload the file."))
        }

        xhr.onabort = () => {
          xhrRef.current = null
          reject(new Error("Upload cancelled."))
        }

        xhr.send(formData)
      }),
    []
  )

  const handleFiles = React.useCallback(async (nextFiles: File[]) => {
    uploadRunRef.current += 1
    const runId = uploadRunRef.current

    abortUpload()
    setFiles(nextFiles)
    setSelectedIndex(null)
    setError(null)
    setUploadStatus(null)
    setUploadProgress(0)

    const file = nextFiles[0]

    if (!file) {
      setPaperData(null)
      setUploadedAt(null)
      setUploadPhase("idle")
      return
    }

    if (!user) {
      setPaperData(null)
      setUploadedAt(null)
      setUploadPhase("failed")
      setUploadProgress(0)
      setError("Please log in before uploading files.")
      return
    }

    if (!isJsonFile(file) && !isPdfFile(file)) {
      setPaperData(null)
      setUploadedAt(null)
      setUploadPhase("failed")
      setError("Only JSON and PDF files are supported.")
      return
    }

    try {
      setUploadPhase("uploading")

      if (isJsonFile(file)) {
        const text = await file.text()
        const parsed = normalizePaperOutput(JSON.parse(text))

        if (runId !== uploadRunRef.current) {
          return
        }

        setPaperData(parsed)
      } else {
        setPaperData(null)
      }

      const status = await uploadFile(file, runId)

      if (runId !== uploadRunRef.current) {
        return
      }

      setUploadStatus(status)
      setUploadProgress(clampProgress(status.progress ?? (status.progress_url ? 35 : 100)))

      if (status.progress_url && status.status !== "complete") {
        setUploadPhase("processing")
        pollUploadStatus(status.progress_url, runId)
      } else {
        setUploadPhase(status.status === "failed" ? "failed" : "complete")
        setUploadedAt(new Date())
      }
    } catch (caughtError) {
      if (runId !== uploadRunRef.current) {
        return
      }

      setPaperData(null)
      setUploadedAt(null)
      setUploadPhase("failed")
      setUploadProgress(100)
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : "Could not upload this file."
      )
    }
  }, [abortUpload, pollUploadStatus, uploadFile, user])

  const fileName = files[0]?.name
  const questions = paperData?.questions ?? []
  const isBusy = uploadPhase === "uploading" || uploadPhase === "processing"
  const uploadMessage = getUploadMessage(uploadStatus, uploadPhase)

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
              Question upload
            </CardTitle>
            <CardDescription>
              Upload an extracted JSON file for preview, or a PDF for backend processing.
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
              accept="application/json,application/pdf,.json,.pdf"
              maxFiles={1}
              maxSize={maxUploadSize}
              disabled={!user}
              onFileValidate={(file) => {
                if (!isJsonFile(file) && !isPdfFile(file)) {
                  return "Only JSON and PDF files are supported."
                }

                if (isJsonFile(file) && file.size > maxJsonSize) {
                  return "JSON files must be 12 MB or smaller."
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
                  <p className="text-sm font-medium">Drop JSON or PDF here</p>
                  <p className="text-xs text-muted-foreground">
                    JSON up to 12 MB, or PDF up to 80 MB
                  </p>
                </div>
                <FileUploadTrigger asChild>
                  <Button type="button" variant="outline">
                    <FileJson />
                    Browse files
                  </Button>
                </FileUploadTrigger>
              </FileUploadDropzone>

              <FileUploadList>
                {files.map((file) => (
                  <FileUploadItem
                    key={`${file.name}-${file.lastModified}`}
                    value={file}
                    className="items-start"
                  >
                    <FileUploadItemPreview />
                    <div className="grid min-w-0 flex-1 gap-2">
                      <FileUploadItemMetadata />
                      {uploadPhase !== "idle" ? (
                        <FileUploadItemProgress
                          forceMount
                          aria-label="Upload progress"
                          aria-valuemax={100}
                          aria-valuemin={0}
                          aria-valuenow={uploadProgress}
                          role="progressbar"
                        >
                          <div
                            className="h-full rounded-full bg-primary transition-all"
                            style={{ width: `${uploadProgress}%` }}
                          />
                        </FileUploadItemProgress>
                      ) : null}
                    </div>
                    <FileUploadItemDelete
                      disabled={isBusy}
                      onClick={() => {
                        setPaperData(null)
                        setUploadedAt(null)
                        setSelectedIndex(null)
                        setError(null)
                        setUploadPhase("idle")
                        setUploadProgress(0)
                        setUploadStatus(null)
                      }}
                    />
                  </FileUploadItem>
                ))}
              </FileUploadList>
              <FileUploadClear
                onClick={() => {
                  abortUpload()
                  setPaperData(null)
                  setUploadedAt(null)
                  setSelectedIndex(null)
                  setError(null)
                  setUploadPhase("idle")
                  setUploadProgress(0)
                  setUploadStatus(null)
                }}
              />
            </FileUpload>

            {!user ? (
              <div className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                <AlertCircle className="mt-0.5 size-4 shrink-0" />
                <div>
                  <p className="font-medium">Login required</p>
                  <p>
                    Uploads are protected by the backend. Sign in before choosing a
                    file.
                  </p>
                </div>
              </div>
            ) : null}

            {uploadPhase !== "idle" ? (
              <div className="flex items-start gap-3 rounded-lg border bg-muted/20 px-3 py-2 text-sm">
                {uploadPhase === "complete" ? (
                  <CheckCircle2 className="mt-0.5 size-4 text-muted-foreground" />
                ) : uploadPhase === "failed" ? (
                  <AlertCircle className="mt-0.5 size-4 text-destructive" />
                ) : (
                  <Loader2 className="mt-0.5 size-4 animate-spin text-muted-foreground" />
                )}
                <div className="min-w-0 flex-1">
                  <p className="font-medium capitalize">
                    {uploadStatus?.stage?.replace(/_/g, " ") ?? uploadPhase}
                  </p>
                  <p className="text-muted-foreground">{uploadMessage}</p>
                  {uploadStatus?.upload_id ? (
                    <p className="truncate text-xs text-muted-foreground">
                      Upload ID: {uploadStatus.upload_id}
                    </p>
                  ) : null}
                </div>
                <span className="text-xs font-medium text-muted-foreground">
                  {uploadProgress}%
                </span>
              </div>
            ) : null}

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
