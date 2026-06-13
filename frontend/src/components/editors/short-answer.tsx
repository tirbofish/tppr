import {
    answerContentText,
    answerSummary,
    firstText,
    withAnswerContentText,
    withAnswerSummary,
    withFirstText,
} from "./helpers";
import type { Question } from "@/types/tppr-paper";
import { X } from "lucide-react";
import { Button } from "../ui/button";
import { Field, FieldLabel } from "../ui/field";
import { Textarea } from "../ui/textarea";
import { Separator } from "../ui/separator";

export function ShortAnswerEditor({ question, onChange }: {
    question: Question;
    onChange: (q: Question) => void;
}) {
    return (
        <div className="space-y-4">
            {/* Question text */}
            <Field>
                <FieldLabel htmlFor="q-content">Question text</FieldLabel>
                <Textarea
                    id="q-content"
                    value={firstText(question.content)}
                    onChange={(e) => onChange({
                        ...question,
                        content: withFirstText(
                            question.content,
                            e.target.value,
                        ),
                    })}
                />
            </Field>

            <Separator />

            <Field>
                <div className="flex items-center justify-between gap-2">
                    <FieldLabel htmlFor="q-answer-summary">
                        Sample answer
                    </FieldLabel>
                    <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        disabled={!question.answer}
                        onClick={() =>
                            onChange({ ...question, answer: undefined })}
                    >
                        <X /> Clear
                    </Button>
                </div>
                <Textarea
                    id="q-answer-summary"
                    value={answerSummary(question.answer)}
                    onChange={(e) =>
                        onChange({
                            ...question,
                            answer: withAnswerSummary(
                                question.answer,
                                e.target.value,
                            ),
                        })}
                />
            </Field>

            <Field>
                <FieldLabel htmlFor="q-answer-working">
                    Worked solution / marking notes
                </FieldLabel>
                <Textarea
                    id="q-answer-working"
                    value={answerContentText(question.answer)}
                    onChange={(e) =>
                        onChange({
                            ...question,
                            answer: withAnswerContentText(
                                question.answer,
                                e.target.value,
                            ),
                        })}
                />
            </Field>
        </div>
    );
}
