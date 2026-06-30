import { CheckCircle2 } from "lucide-react";

import type { PaperMeta } from "@/types/tppr-paper";
import { Button } from "@/components/ui/button";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";

interface PaperVerifiedBadgeProps {
    paper: Pick<
        PaperMeta,
        | "verified"
        | "verified_source_name"
        | "verified_source_url"
        | "verified_at"
    >;
}

export function PaperVerifiedBadge({ paper }: PaperVerifiedBadgeProps) {
    if (!paper.verified) return null;

    return (
        <Popover>
            <PopoverTrigger asChild>
                <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label="Verified paper"
                    className="text-primary"
                    onClick={(event) => event.stopPropagation()}
                >
                    <CheckCircle2 />
                </Button>
            </PopoverTrigger>
            <PopoverContent
                align="end"
                className="w-72"
                onClick={(event) => event.stopPropagation()}
            >
                <div className="flex flex-col gap-2">
                    <p className="text-sm font-medium">Verified paper</p>
                    <p className="text-sm text-muted-foreground">
                        This paper has been manually checked against{" "}
                        {paper.verified_source_url
                            ? (
                                <a
                                    href={paper.verified_source_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="font-medium text-foreground underline"
                                >
                                    {paper.verified_source_name ??
                                        "the original source"}
                                </a>
                            )
                            : (
                                <span className="font-medium text-foreground">
                                    {paper.verified_source_name ??
                                        "the original source"}
                                </span>
                            )}
                        .
                    </p>
                    {paper.verified_at && (
                        <p className="text-xs text-muted-foreground">
                            Verified{" "}
                            {new Date(paper.verified_at).toLocaleDateString()}
                        </p>
                    )}
                </div>
            </PopoverContent>
        </Popover>
    );
}
