import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { PaperCard } from "../paper-card";
import { describe, expect, it, vi } from "vitest";

const mockPaper = {
    id: "paper-1",
    title: "2023 HSC Physics",
    subject: "Physics",
    visibility: "public" as const,
    question_count: 10,
    total_marks: 50,
    author_id: "user-1",
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
};

describe("PaperCard", () => {
    it("renders the paper title", () => {
        render(
            <MemoryRouter>
                <PaperCard
                    paper={mockPaper}
                    onOpen={vi.fn()}
                    onEdit={vi.fn()}
                    onDelete={vi.fn()}
                />
            </MemoryRouter>,
        );
        expect(screen.getByText("2023 HSC Physics")).toBeInTheDocument();
    });

    it("renders the subject", () => {
        render(
            <MemoryRouter>
                <PaperCard
                    paper={mockPaper}
                    onOpen={vi.fn()}
                    onEdit={vi.fn()}
                    onDelete={vi.fn()}
                />
            </MemoryRouter>,
        );
        expect(screen.getByText("Physics")).toBeInTheDocument();
    });
});
