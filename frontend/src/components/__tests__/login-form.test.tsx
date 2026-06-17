import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LoginForm } from "../login-form";
import { describe, expect, it, vi } from "vitest";

// Mock supabase
vi.mock("@/lib/supabase", () => ({
    supabase: {
        auth: {
            signInWithPassword: vi.fn(),
            signInWithOAuth: vi.fn(),
            mfa: { listFactors: vi.fn().mockResolvedValue({ data: {} }) },
        },
    },
}));

describe("LoginForm", () => {
    it("renders email and password fields", () => {
        render(
            <MemoryRouter>
                <LoginForm />
            </MemoryRouter>,
        );
        expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    });

    it("renders a sign-in button", () => {
        render(
            <MemoryRouter>
                <LoginForm />
            </MemoryRouter>,
        );
        expect(screen.getByRole("button", { name: /^login$/i }))
            .toBeInTheDocument();
    });
});
