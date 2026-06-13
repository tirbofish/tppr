import { Plus, X } from "lucide-react";
import { defaultOptions, firstText, relabelOptions, withFirstText } from "./helpers";
import type { ChoiceOption, Question } from "@/types/tppr-paper";
import { Button } from "../ui/button";
import { Field, FieldLabel } from "../ui/field";
import { Textarea } from "../ui/textarea";

const MIN_OPTIONS = 2;
const MAX_OPTIONS = 6;

export function MultipleChoiceEditor({ question, onChange }: {
    question: Question;
    onChange: (q: Question) => void;
}) {
    const options = question.options ?? defaultOptions();

    function setOptions(next: ChoiceOption[], answer = question.answer) {
        onChange({ ...question, options: next, answer });
    }

    function updateOption(label: string, text: string) {
        setOptions(options.map((opt) =>
            opt.label === label
                ? { ...opt, content: withFirstText(opt.content, text) }
                : opt
        ));
    }

    function addOption() {
        if (options.length >= MAX_OPTIONS) return;
        setOptions(relabelOptions([
            ...options,
            { label: "", content: [{ kind: "text", text: "" }] },
        ]));
    }

    function removeOption(label: string) {
        if (options.length <= MIN_OPTIONS) return;
        const next = relabelOptions(options.filter((o) => o.label !== label));

        const answer = next.some((o) => o.label === question.answer)
            ? question.answer
            : undefined;
        setOptions(next, answer);
    }

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

            {options.map((opt) => (
                <Field key={opt.label}>
                    <FieldLabel htmlFor={`q-opt-${opt.label}`}>
                        Option {opt.label}
                    </FieldLabel>
                    <div className="flex gap-2">
                        <Textarea
                            id={`q-opt-${opt.label}`}
                            value={firstText(opt.content)}
                            onChange={(e) => updateOption(opt.label, e.target.value)}
                        />
                        <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            disabled={options.length <= MIN_OPTIONS}
                            onClick={() => removeOption(opt.label)}
                        >
                            <X />
                        </Button>
                    </div>
                </Field>
            ))}

            <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={options.length >= MAX_OPTIONS}
                onClick={addOption}
            >
                <Plus /> Add option
            </Button>

            {/* correct-answer Select stays as before, mapped over `options`. if i bother tho */}
        </div>
    );
}