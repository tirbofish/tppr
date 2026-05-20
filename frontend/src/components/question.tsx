import { ArrowLeft, FileText } from "lucide-react"
import Latex from "react-latex-next"
import "katex/dist/katex.min.css"

import NavBar from "@/components/navbar"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/ui/hover-card"
import { cn } from "@/lib/utils"

export type PaperMetadata = {
  year?: string | number
  paper?: string
  sections?: Array<{
    name?: string
    marks?: string | number
    pages?: string
  }>
}

export type QuestionOption = {
  label?: string
  text?: unknown
  image?: string
  images?: string[]
}

export type PaperQuestion = {
  number?: string | number
  type?: string
  text?: unknown
  prompt?: unknown
  question?: unknown
  question_to_answer?: unknown
  questionToAnswer?: unknown
  stimulus?: unknown
  stimulus_question?: unknown
  stimulusQuestion?: unknown
  context?: unknown
  image?: string
  images?: string[]
  stimulus_image?: string
  stimulusImage?: string
  answer?: unknown
  answer_text?: unknown
  answerText?: unknown
  answer_image?: string
  answerImage?: string
  answer_images?: string[]
  answerImages?: string[]
  prompt_image?: string
  promptImage?: string
  prompt_images?: string[]
  promptImages?: string[]
  options?: QuestionOption[]
  marks?: string | number
  page?: string | number
}

export type PaperOutput = {
  metadata?: PaperMetadata
  questions?: PaperQuestion[]
}

export type PdfRequest = {
  metadata: PaperMetadata
  question: PaperQuestion
  page?: string | number
}

type LatexTextProps = {
  text: unknown
  className?: string
}

type QuestionProps = {
  data?: PaperOutput
  metadata?: PaperMetadata
  question?: PaperQuestion
  questionIndex?: number
  showNav?: boolean
  className?: string
  onOpenPdf?: (request: PdfRequest) => void
  onBack?: () => void
  backLabel?: string
}

const defaultQuestion: PaperQuestion = {
  number: 3,
  type: "multiple_choice",
  text: "What is the value of P (X = 3)?",
  marks: 1,
}

const defaultMetadata: PaperMetadata = {
  paper: "Mathematics Advanced",
  year: 2025,
}

const nullCharacter = String.fromCharCode(0)

function cleanQuestionText(value: unknown): string {
  if (value == null) {
    return ""
  }

  if (Array.isArray(value)) {
    return value.map(cleanQuestionText).filter(Boolean).join("\n")
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
    const cleaned = cleanQuestionText(value)

    if (cleaned) {
      return cleaned
    }
  }

  return ""
}

function asImageSource(image?: string): string {
  const source = String(image ?? "").replace(/\s/g, "")

  if (!source) {
    return ""
  }

  if (/^(https?:|blob:|data:image\/)/i.test(source)) {
    return source
  }

  return `data:image/png;base64,${source}`
}

function getImageSources(...images: Array<string | string[] | undefined>) {
  return images
    .flatMap((image) => (Array.isArray(image) ? image : [image]))
    .map(asImageSource)
    .filter(Boolean)
}

function getStimulusImages(question: PaperQuestion) {
  return getImageSources(
    question.image,
    question.stimulusImage,
    question.stimulus_image,
    question.images
  )
}

function getAnswerPromptImages(question: PaperQuestion) {
  return getImageSources(
    question.answerImage,
    question.answer_image,
    question.answerImages,
    question.answer_images,
    question.promptImage,
    question.prompt_image,
    question.promptImages,
    question.prompt_images
  )
}

function getQuestionLabel(question: PaperQuestion): string {
  const number = cleanQuestionText(question.number)
  return number ? `Question ${number}` : "Question"
}

function getMarks(question: PaperQuestion): string {
  const explicitMarks = cleanQuestionText(question.marks)

  if (explicitMarks) {
    return explicitMarks
  }

  return question.type === "multiple_choice" ? "1" : "Not listed"
}

function formatMarks(question: PaperQuestion): string {
  const marks = getMarks(question)

  if (marks === "Not listed") {
    return marks
  }

  return Number(marks) === 1 ? "1 mark" : `${marks} marks`
}

function getDisplayType(type?: string): string {
  return cleanQuestionText(type)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function getSectionForPage(metadata: PaperMetadata, page: string | number | undefined) {
  const pageNumber = Number(page)

  if (!Number.isFinite(pageNumber)) {
    return null
  }

  return (
    metadata.sections?.find((section) => {
      const pages = cleanQuestionText(section.pages)
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

function openPdfStub(request: PdfRequest) {
  console.info("PDF retrieval stub", request)
}

export function LatexText({ text, className }: LatexTextProps) {
  const cleaned = cleanQuestionText(text)

  if (!cleaned) {
    return null
  }

  return (
    <span className={cn("whitespace-pre-line leading-7", className)}>
      <Latex>{cleaned}</Latex>
    </span>
  )
}

type ImageStripProps = {
  images: string[]
  alt: string
  className?: string
  imageClassName?: string
}

function ImageStrip({ images, alt, className, imageClassName }: ImageStripProps) {
  if (images.length === 0) {
    return null
  }

  return (
    <div className={cn("grid justify-items-center gap-3", className)}>
      {images.map((src, index) => (
        <img
          key={`${src.slice(0, 32)}-${index}`}
          src={src}
          alt={images.length === 1 ? alt : `${alt} ${index + 1}`}
          className={cn(
            "max-h-[32vh] w-auto max-w-full rounded-md object-contain",
            imageClassName
          )}
          loading="lazy"
        />
      ))}
    </div>
  )
}

export default function Question({
  data,
  metadata,
  question,
  questionIndex = 0,
  showNav = true,
  className,
  onOpenPdf = openPdfStub,
  onBack,
  backLabel = "Back",
}: QuestionProps) {
  const resolvedMetadata = metadata ?? data?.metadata ?? defaultMetadata
  const resolvedQuestion =
    question ?? data?.questions?.[questionIndex] ?? defaultQuestion
  const questionLabel = getQuestionLabel(resolvedQuestion)
  const stimulusText = firstText(
    resolvedQuestion.stimulusQuestion,
    resolvedQuestion.stimulus_question,
    resolvedQuestion.stimulus,
    resolvedQuestion.context
  )
  const answerText = firstText(
    resolvedQuestion.questionToAnswer,
    resolvedQuestion.question_to_answer,
    resolvedQuestion.question,
    resolvedQuestion.prompt,
    resolvedQuestion.answerText,
    resolvedQuestion.answer_text,
    resolvedQuestion.answer
  )
  const fallbackText = cleanQuestionText(resolvedQuestion.text)
  const topText = stimulusText || (!answerText ? fallbackText : "")
  const bottomText = answerText || (topText ? "" : fallbackText)
  const stimulusImages = getStimulusImages(resolvedQuestion)
  const answerPromptImages = getAnswerPromptImages(resolvedQuestion)
  const paper = cleanQuestionText(resolvedMetadata.paper) || "Unknown paper"
  const year = cleanQuestionText(resolvedMetadata.year) || "Unknown year"
  const page = cleanQuestionText(resolvedQuestion.page)
  const type = getDisplayType(resolvedQuestion.type)
  const section = getSectionForPage(resolvedMetadata, resolvedQuestion.page)

  return (
    <div className="min-h-screen bg-background text-foreground">
      {showNav ? <NavBar /> : null}
      <main
        className={cn(
          "mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-6xl items-center justify-center px-4 py-8 sm:px-6",
          !showNav && "min-h-screen",
          className
        )}
      >
        <Card className="w-full max-w-3xl shadow-sm">
          <CardHeader className="border-b">
            <CardTitle className="flex min-w-0 flex-wrap items-start gap-2">
              {onBack ? (
                <Button type="button" variant="ghost" onClick={onBack}>
                  <ArrowLeft />
                  {backLabel}
                </Button>
              ) : null}
              <HoverCard openDelay={150} closeDelay={100}>
                <HoverCardTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() =>
                      onOpenPdf({
                        metadata: resolvedMetadata,
                        question: resolvedQuestion,
                        page: resolvedQuestion.page,
                      })
                    }
                  >
                    <FileText />
                    {questionLabel}
                  </Button>
                </HoverCardTrigger>
                <HoverCardContent>
                  <div className="space-y-2">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground">
                        Paper
                      </p>
                      <p className="font-medium">{paper}</p>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <div>
                        <p className="font-medium text-muted-foreground">
                          Year
                        </p>
                        <p>{year}</p>
                      </div>
                      {page ? (
                        <div>
                          <p className="font-medium text-muted-foreground">
                            Page
                          </p>
                          <p>{page}</p>
                        </div>
                      ) : null}
                      {section ? (
                        <div className="col-span-2">
                          <p className="font-medium text-muted-foreground">
                            Section
                          </p>
                          <p>
                            {section.name ?? "Unnamed section"}
                            {section.pages ? ` · pages ${section.pages}` : ""}
                          </p>
                        </div>
                      ) : null}
                    </div>
                    {type ? (
                      <p className="text-xs text-muted-foreground">{type}</p>
                    ) : null}
                  </div>
                </HoverCardContent>
              </HoverCard>
            </CardTitle>
            <CardAction>
              <div className="rounded-lg border bg-muted/60 px-3 py-2 text-right">
                <p className="text-xs font-medium text-muted-foreground">
                  Marks
                </p>
                <p className="text-sm font-semibold">
                  {formatMarks(resolvedQuestion)}
                </p>
              </div>
            </CardAction>
          </CardHeader>

          <CardContent className="space-y-6">
            {topText ? (
              <section className="text-base">
                <LatexText text={topText} />
              </section>
            ) : null}

            <ImageStrip
              images={stimulusImages}
              alt={`${questionLabel} stimulus`}
              imageClassName="max-h-[28vh]"
            />

            {(bottomText || answerPromptImages.length > 0) ? (
              <section className="space-y-4 text-base font-medium">
                {bottomText ? <LatexText text={bottomText} /> : null}
                <ImageStrip
                  images={answerPromptImages}
                  alt={`${questionLabel} answer prompt`}
                />
              </section>
            ) : null}

            {resolvedQuestion.options?.length ? (
              <ol className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {resolvedQuestion.options.map((option, index) => {
                  const label = cleanQuestionText(option.label) || String(index + 1)
                  const optionImages = getImageSources(option.image, option.images)

                  return (
                    <li
                      key={`${label}-${index}`}
                      className="grid gap-3 rounded-lg border bg-background p-3"
                    >
                      <div className="flex items-center gap-2">
                        <span className="flex size-8 items-center justify-center rounded-md bg-muted text-sm font-semibold">
                          {label}
                        </span>
                        <LatexText text={option.text} className="text-sm" />
                      </div>
                      <div className="grid gap-2 self-center">
                        <ImageStrip
                          images={optionImages}
                          alt={`${questionLabel} option ${label}`}
                          className="justify-items-start"
                          imageClassName="max-h-[20vh]"
                        />
                      </div>
                    </li>
                  )
                })}
              </ol>
            ) : null}
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
