import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import {
    HoverCard,
    HoverCardContent,
    HoverCardTrigger,
} from "@/components/ui/hover-card";
import { Clock, Globe, Lock, Trash2 } from "lucide-react";
import { QuestionSample } from "@/components/question-sample";
import type { PaperMeta } from "@/types/tppr-paper";
import { PaperSettings } from "./paper-settings";
import { useState } from "react";
import { StarPaperButton } from "@/components/star-paper-button";
import { PaperVerifiedBadge } from "@/components/paper-verified-badge";

interface PaperCardProps {
    paper: PaperMeta;
    onOpen: () => void;
    onEdit: (updated: PaperMeta) => void;
    onDelete: () => void;
}

export function PaperCard({ paper, onOpen, onEdit, onDelete }: PaperCardProps) {
    const [hoverOpen, setHoverOpen] = useState(false);
    const [settingsOpen, setSettingsOpen] = useState(false);

    return (
        <HoverCard
            open={hoverOpen && !settingsOpen}
            onOpenChange={(open) => {
                if (!settingsOpen) setHoverOpen(open);
            }}
            openDelay={400}
        >
            <HoverCardTrigger asChild>
                <Card
                    className="cursor-pointer transition-shadow hover:shadow-md"
                    onClick={onOpen}
                >
                    <CardHeader>
                        <div className="flex items-start justify-between gap-2">
                            <CardTitle className="line-clamp-2">
                                {paper.title}
                            </CardTitle>
                            <div className="flex shrink-0 items-center gap-1">
                                <PaperVerifiedBadge paper={paper} />
                                {paper.visibility === "public"
                                    ? (
                                        <Globe className="size-4 text-muted-foreground" />
                                    )
                                    : (
                                        <Lock className="size-4 text-muted-foreground" />
                                    )}
                            </div>
                        </div>
                        <CardDescription>
                            {paper.subject}
                            {paper.year ? ` · ${paper.year}` : ""}
                            {paper.school ? ` · ${paper.school}` : ""}
                        </CardDescription>
                    </CardHeader>

                    <CardContent className="flex flex-wrap gap-1.5">
                        {paper.source && (
                            <Badge variant="secondary" className="uppercase">
                                {paper.source}
                            </Badge>
                        )}
                        {paper.course_level && (
                            <Badge variant="outline">
                                {paper.course_level.replace("_", " ")}
                            </Badge>
                        )}
                        <Badge variant="outline">
                            {paper.question_count} questions
                        </Badge>
                        <Badge variant="outline">
                            {paper.total_marks} marks
                        </Badge>
                        {paper.duration_minutes
                            ? (
                                <Badge variant="outline">
                                    <Clock data-icon="inline-start" />
                                    {paper.duration_minutes} min
                                </Badge>
                            )
                            : null}
                        {paper.topics?.slice(0, 3).map((topic) => (
                            <Badge key={`topic-${topic}`} variant="outline">
                                {topic}
                            </Badge>
                        ))}
                        {paper.topics && paper.topics.length > 3 && (
                            <Badge variant="outline">
                                +{paper.topics.length - 3} topics
                            </Badge>
                        )}
                        {paper.outcomes?.slice(0, 2).map((outcome) => (
                            <Badge
                                key={`outcome-${outcome}`}
                                variant="secondary"
                            >
                                {outcome}
                            </Badge>
                        ))}
                        {paper.outcomes && paper.outcomes.length > 2 && (
                            <Badge variant="secondary">
                                +{paper.outcomes.length - 2} outcomes
                            </Badge>
                        )}
                    </CardContent>

                    <CardFooter className="justify-end gap-1">
                        <StarPaperButton paperId={paper.id} />
                        <span onClick={(e) => e.stopPropagation()}>
                            <PaperSettings
                                paper={paper}
                                onSave={onEdit}
                                onOpenChange={setSettingsOpen}
                            />
                        </span>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="size-8 text-destructive hover:text-destructive"
                            onClick={(e) => {
                                e.stopPropagation();
                                onDelete();
                            }}
                        >
                            <Trash2 className="size-4" />
                        </Button>
                    </CardFooter>
                </Card>
            </HoverCardTrigger>

            <HoverCardContent side="right" className="w-80">
                <QuestionSample paperId={paper.id} />
            </HoverCardContent>
        </HoverCard>
    );
}
