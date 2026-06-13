import type { PaperMeta } from "@/types/tppr-paper";

export interface PapersListResponse {
    papers: PaperMeta[];
    total: number;
    page: number;
    per_page: number;
}