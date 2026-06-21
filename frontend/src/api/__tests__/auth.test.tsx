import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider, useAuth } from "../auth";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/supabase", () => ({
    supabase: {
        auth: {
            getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
            onAuthStateChange: vi.fn(() => ({
                data: { subscription: { unsubscribe: vi.fn() } },
            })),
            signInWithPassword: vi.fn(),
            signUp: vi.fn(),
            signOut: vi.fn().mockResolvedValue({}),
        },
    },
}));

function TestConsumer() {
    const { user, loading } = useAuth();
    if (loading) return <div>Loading...</div>;
    return <div>{user ? user.username : "No user"}</div>;
}

describe("AuthProvider", () => {
    it("shows no user when session is null", async () => {
        render(
            <MemoryRouter>
                <AuthProvider>
                    <TestConsumer />
                </AuthProvider>
            </MemoryRouter>,
        );
        await waitFor(() => {
            expect(screen.getByText("No user")).toBeInTheDocument();
        });
    });
});
