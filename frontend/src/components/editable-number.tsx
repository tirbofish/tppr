import { useEffect, useRef, useState } from "react";

export function EditableNumber({ value, onCommit }: {
    value: number;
    onCommit: (n: number) => void;
}) {
    const [editing, setEditing] = useState(false);
    const [draft, setDraft] = useState(String(value));
    const inputRef = useRef<HTMLInputElement>(null);

    useEffect(() => {
        if (editing) {
            inputRef.current?.focus();
            inputRef.current?.select();
        }
    }, [editing]);

    if (!editing) {
        return (
            <span
                title="Double-click to change"
                className="cursor-text underline decoration-dotted underline-offset-4"
                onDoubleClick={() => {
                    setDraft(String(value));
                    setEditing(true);
                }}
            >
                {value}
            </span>
        );
    }

    function commit() {
        setEditing(false);
        const n = Number(draft);
        if (Number.isInteger(n) && n >= 1) onCommit(n);
    }

    return (
        <form
            className="inline"
            onSubmit={(e) => {
                e.preventDefault();
                commit();
            }}
        >
            <input
                ref={inputRef}
                type="number"
                min={1}
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onBlur={() => setEditing(false)}
                onKeyDown={(e) => {
                    if (e.key === "Escape") {
                        e.preventDefault();
                        e.stopPropagation();
                        setEditing(false);
                    }
                }}
                className="w-14 rounded-md border bg-transparent px-1 text-center"
            />
        </form>
    );
}