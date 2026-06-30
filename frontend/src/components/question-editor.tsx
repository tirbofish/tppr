import { Input } from "@/components/ui/input";
import { Field, FieldLabel } from "@/components/ui/field";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import type { Question, QuestionType } from "@/types/tppr-paper";
import { defaultOptions } from "./editors/helpers";
import { MultipleChoiceEditor } from "./editors/multiple-choice";
import { StimulusSection } from "./editors/stimulus";
import { LongAnswerEditor } from "./editors/long-answer";
import { ShortAnswerEditor } from "./editors/short-answer";
import { sumQuestionMarks } from "@/lib/parts";

export function QuestionEditor({
    question,
    onChange,
}: {
    question: Question;
    onChange: (q: Question) => void;
}) {
    const marksEditable = question.type === "short_answer";

    return (
        <div className="space-y-4 px-4 pb-8">

            <div className="flex gap-4">
                <Field className="flex-1">
                    <FieldLabel htmlFor="q-type">Type</FieldLabel>
                    <Select
                        value={question.type}
                        onValueChange={(v) => {
                            const type = v as QuestionType;
                            onChange({
                                ...question,
                                type,
                                options: type === "multiple_choice"
                                    ? question.options ?? defaultOptions()
                                    : undefined,

                                // mcq is always 1 mark, long answer is a sum of its parts, short answer is editable
                                marks: type === "multiple_choice"
                                    ? 1
                                    : type === "long_answer"
                                    ? sumQuestionMarks({ ...question, type })
                                    : question.marks,
                            });
                        }}
                    >
                        <SelectTrigger id="q-type" className="w-full">
                            <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="multiple_choice">
                                Multiple choice
                            </SelectItem>
                            <SelectItem value="short_answer">
                                Short answer
                            </SelectItem>
                            <SelectItem value="long_answer">
                                Long answer
                            </SelectItem>
                        </SelectContent>
                    </Select>
                </Field>

                <Field className="w-24">
                    <FieldLabel htmlFor="q-marks">Marks</FieldLabel>
                    <Input
                        id="q-marks"
                        type="number"
                        min={1}
                        value={question.marks}
                        readOnly={!marksEditable}
                        disabled={!marksEditable}
                        onChange={(e) =>
                            marksEditable &&
                            onChange({
                                ...question,
                                marks: Number(e.target.value),
                            })}
                    />
                </Field>
            </div>

            <StimulusSection question={question} onChange={onChange} />

            {question.type === "multiple_choice" && (
                <MultipleChoiceEditor question={question} onChange={onChange} />
            )}

            {question.type === "long_answer" && (
                <LongAnswerEditor question={question} onChange={onChange} />
            )}

            {question.type === "short_answer" && (
                <ShortAnswerEditor question={question} onChange={onChange} />
            )}
        </div>
    );
}
