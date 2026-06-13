import { useMemo } from "react";
import katex from "katex";
import "katex/dist/katex.min.css";

/** regex that splits on $$block$$ first, then $inline$. 
 * 
 * refer to https://xkcd.com/1171/ 
 * 
 * */
const SPLIT = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;

function renderSegment(seg: string, i: number) {
    const isBlock = seg.startsWith("$$") && seg.endsWith("$$");
    const isInline = !isBlock && seg.startsWith("$") && seg.endsWith("$") && seg.length > 2;

    if (!isBlock && !isInline) {
        return <span key={i}>{seg}</span>;
    }

    const tex = seg.slice(isBlock ? 2 : 1, isBlock ? -2 : -1);
    let html: string;
    try {
        html = katex.renderToString(tex, {
            displayMode: isBlock,
            throwOnError: true,
        });
    } catch {
        // invalid latex, make it evil
        return <span key={i} className="text-destructive">{seg}</span>;
    }
    return <span key={i} dangerouslySetInnerHTML={{ __html: html }} />;
}

export function MathText({ text, className }: { text: string; className?: string }) {
    const parts = useMemo(() => text.split(SPLIT), [text]);
    return (
        <span className={className}>
            {parts.map(renderSegment)}
        </span>
    );
}