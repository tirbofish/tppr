import { firstText, withFirstText } from "./helpers";
import type { Question } from "@/types/tppr-paper";
import { Field, FieldLabel } from "../ui/field";
import { Textarea } from "../ui/textarea";

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
        </div>
    );
}