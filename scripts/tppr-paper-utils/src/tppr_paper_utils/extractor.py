from __future__ import annotations

import logging
import re
from io import BufferedReader, BytesIO
from pathlib import Path

import pdfplumber
import pymupdf as fitz

from .questions import QuestionExtractor
from .text import clean_text
from .visual import VisualExtractor

logger = logging.getLogger(__name__)


class TPPRExtractor:
    def __init__(self, stream: str | Path | BufferedReader | BytesIO):
        self.pdf = pdfplumber.open(stream)

        if isinstance(stream, (str, Path)):
            self._fitz_doc = fitz.open(str(stream))
            logger.debug("Opened PDF from path for text and image extraction")
        elif isinstance(stream, (BufferedReader, BytesIO)):
            stream.seek(0)
            self._fitz_doc = fitz.open(stream=stream.read(), filetype="pdf")
            logger.debug("Opened PDF from stream for text and image extraction")
        else:
            self._fitz_doc = None
            logger.debug("Opened PDF without image-rendering backend")

        self._visual = VisualExtractor(self._fitz_doc)

    def extract(self) -> dict:
        logger.info("Starting TPPR extraction")
        pages: list[dict[str, str | int]] = []
        for i, page in enumerate(self.pdf.pages):
            page_text = page.extract_text()
            if page_text:
                pages.append({"page": i + 1, "text": page_text})

        questions = QuestionExtractor(self.pdf, self._visual).extract()
        first_page_text = str(pages[0]["text"]) if pages else ""
        metadata = self._extract_metadata(first_page_text)
        logger.info("Finished TPPR extraction with %d questions", len(questions))

        return {
            "metadata": metadata,
            "questions": questions,
        }

    def render_page(self, page_num: int, zoom: float = 2.0) -> bytes:
        return self._visual.render_page(page_num, zoom)

    def render_region(
        self, page_num: int, clip: tuple[float, float, float, float], zoom: float = 2.0
    ) -> bytes:
        return self._visual.render_region(page_num, clip, zoom)

    def render_transparent_region(
        self, page_num: int, clip: tuple[float, float, float, float], zoom: float = 2.0
    ) -> bytes:
        return self._visual.render_transparent_region(page_num, clip, zoom)

    def render_page_base64(self, page_num: int, zoom: float = 2.0) -> str:
        return self._visual.render_page_base64(page_num, zoom)

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

        year_match = re.search(r"(20\d{2})", text)
        if year_match:
            meta["year"] = int(year_match.group(1))
        else:
            logger.debug("Could not find paper year in first page text")

        title_match = re.search(r"EXAMINATION\n(.+)", text)
        if title_match:
            meta["paper"] = title_match.group(1).strip()
        else:
            logger.debug("Could not find paper title in first page text")

        sections = []
        section_matches = re.finditer(
            r"Section\s+(I{1,3}|IV|V)\s*[–—-]\s*(\d+)\s*marks\s*\(pages?\s*([\d–\-]+)\)",
            text,
        )
        for match in section_matches:
            sections.append(
                {
                    "name": f"Section {match.group(1)}",
                    "marks": int(match.group(2)),
                    "pages": clean_text(match.group(3)),
                }
            )
        if sections:
            meta["sections"] = sections
        else:
            logger.debug("Could not find section metadata in first page text")

        return meta
