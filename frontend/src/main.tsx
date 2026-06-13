import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { paperStore } from "@/lib/paper";

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

/**
 * Allows for exporting a published paper.
 * 
 * Use `exportPaper("uuid")` in the console
 */
(window as any).exportPaper = async (id: string) => {
    const paper = await paperStore.getPaper(id);
    if (!paper) {
        console.error(`Paper "${id}" not found in local store.`);
        return;
    }
    const json = JSON.stringify(paper, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${paper.title.replace(/[^a-z0-9]/gi, "_")}.json`;
    a.click();
    URL.revokeObjectURL(url);
    console.log(`Exported "${paper.title}" (${paper.questions.length} questions)`);
};