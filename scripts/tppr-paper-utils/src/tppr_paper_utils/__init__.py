from pathlib import Path

import pymupdf as fitz
import pdfplumber
from io import BufferedReader, BytesIO
import re
import base64

from tppr_paper_utils.mc import extract_mc_questions


class TPPRExtractor():
    def __init__(self, stream: str | Path | BufferedReader | BytesIO):
        # pdfplumber for text extraction
        self.pdf = pdfplumber.open(stream)

        # pymupdf for image rendering — needs bytes or path
        if isinstance(stream, (str, Path)):
            self._fitz_doc = fitz.open(str(stream))
        elif isinstance(stream, (BufferedReader, BytesIO)):
            stream.seek(0)
            self._fitz_doc = fitz.open(stream=stream.read(), filetype="pdf")
        else:
            self._fitz_doc = None

    def extract(self) -> dict:
        # Build page-indexed text
        pages = []
        for i, page in enumerate(self.pdf.pages):
            extracted = page.extract_text()
            if extracted:
                pages.append({"page": i + 1, "text": extracted})

        # Metadata from first page
        metadata = self._extract_metadata(pages[0]["text"] if pages else "")

        # Full text with page markers for question extraction
        full_text = ""
        page_boundaries = []  # (char_offset, page_number)
        for p in pages:
            page_boundaries.append((len(full_text), p["page"]))
            full_text += p["text"] + "\n"

        # Extract MC questions with page info
        raw_questions = extract_mc_questions(full_text)

        # Attach page numbers and screenshots
        for q in raw_questions:
            if "char_offset" in q:
                q["page"] = self._resolve_page(
                    q["char_offset"], page_boundaries)
                del q["char_offset"]
            if "q_text_offset" in q:
                del q["q_text_offset"]
            if self._fitz_doc and "page" in q:
                q["image"] = self._render_question_region(q)

        return {
            "metadata": metadata,
            "questions": raw_questions,
        }

    def _render_question_region(self, question: dict) -> str:
        """Render just the region of the page containing the question stimulus (between question number and options)."""
        page_idx = question["page"] - 1  # 0-indexed
        pdf_page = self.pdf.pages[page_idx]

        # Search for the question number at line start and option labels
        q_num = question["number"]
        words = pdf_page.extract_words()

        if not words:
            return self.render_page_base64(page_idx)

        # Find the top of the question (question number)
        q_top = None
        for w in words:
            if w["text"] == str(q_num):
                q_top = w["top"]
                break

        # Find the bottom — where options A. starts
        q_bottom = None
        for w in words:
            if w["text"] == "A." and (q_top is None or w["top"] > q_top):
                q_bottom = w["bottom"]
                break

        if q_top is None or q_bottom is None:
            return self.render_page_base64(page_idx)

        # Use full page width, crop vertically
        page_width = pdf_page.width
        clip = (0, q_top, page_width, q_bottom)

        png_bytes = self.render_region(page_idx, clip)
        return base64.b64encode(png_bytes).decode("utf-8")

    def render_page(self, page_num: int, zoom: float = 2.0) -> bytes:
        """Render a full page as PNG bytes (0-indexed)."""
        page = self._fitz_doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        return pix.tobytes("png")

    def render_region(self, page_num: int, clip: tuple[float, float, float, float], zoom: float = 2.0) -> bytes:
        """Render a cropped region as PNG bytes. clip = (x0, y0, x1, y1)."""
        page = self._fitz_doc[page_num]
        rect = fitz.Rect(*clip)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect)
        return pix.tobytes("png")

    def render_page_base64(self, page_num: int, zoom: float = 2.0) -> str:
        """Render a page as a base64-encoded PNG string (for embedding in JSON/HTML)."""
        png_bytes = self.render_page(page_num, zoom)
        return base64.b64encode(png_bytes).decode("utf-8")

    def close(self):
        self.pdf.close()
        if self._fitz_doc:
            self._fitz_doc.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _extract_metadata(self, text: str) -> dict:
        """Extract paper metadata from the first page."""
        meta = {}

        # Year (2025)
        year_match = re.search(r'(20\d{2})', text)
        if year_match:
            meta["year"] = int(year_match.group(1))

        # paper title ("Mathematics Advanced")
        title_match = re.search(r'EXAMINATION\n(.+)', text)
        if title_match:
            meta["paper"] = title_match.group(1).strip()

        # sections
        sections = []
        section_matches = re.finditer(
            r'Section\s+(I{1,3}|IV|V)\s*[–—-]\s*(\d+)\s*marks\s*\(pages?\s*([\d–\-]+)\)',
            text
        )
        for m in section_matches:
            sections.append({
                "name": f"Section {m.group(1)}",
                "marks": int(m.group(2)),
                "pages": m.group(3),
            })
        if sections:
            meta["sections"] = sections

        return meta

    def _resolve_page(self, offset: int, boundaries: list[tuple[int, int]]) -> int:
        """Find which page a character offset belongs to."""
        page = 1
        for boundary_offset, page_num in boundaries:
            if offset >= boundary_offset:
                page = page_num
            else:
                break
        return page
