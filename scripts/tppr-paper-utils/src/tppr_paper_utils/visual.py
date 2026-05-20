from __future__ import annotations

import base64
import io
import logging
import re

import pdfplumber
import pymupdf as fitz
from PIL import Image

from .geometry import (
    Rect,
    expand_rect,
    group_words_by_line,
    rect_intersection,
    rect_intersects,
    union_rects,
    words_on_line,
)
from .text import clean_text, is_axis_or_tick_label

logger = logging.getLogger(__name__)


class VisualExtractor:
    def __init__(self, fitz_doc: fitz.Document | None):
        self._fitz_doc = fitz_doc

    def stimulus_clip(
        self,
        page_idx: int,
        page: pdfplumber.page.Page,
        question_clip: Rect,
    ) -> Rect | None:
        if not self._fitz_doc:
            logger.debug(
                "Skipping stimulus detection because no image backend is available"
            )
            return None

        _, q_top, _, q_bottom = question_clip
        words = page.extract_words()
        prompt_bottom = self._prompt_line_bottom(words, q_top)
        option_top = min(
            (
                word["top"]
                for word in words
                if word["text"] == "A." and q_top <= word["top"] <= q_bottom
            ),
            default=q_bottom,
        )

        candidates = [
            rect
            for rect in self._drawing_rects(page_idx)
            if rect_intersects(rect, question_clip)
            and q_top <= rect[1] <= q_bottom
            and rect[1] > prompt_bottom
            and rect[3] < option_top - 2
            and not self._is_page_rule(rect, page)
            and not self._is_glyph_like_drawing(rect)
        ]
        if not candidates:
            logger.debug(
                "No stimulus drawing candidates found on page %d", page_idx + 1
            )
            return None

        candidates = self._largest_visual_cluster(candidates)
        visual_rect = union_rects(candidates)
        visual_width = visual_rect[2] - visual_rect[0]
        visual_height = visual_rect[3] - visual_rect[1]
        if len(candidates) < 3 and (visual_width < 80 or visual_height < 50):
            logger.debug(
                "Rejected small stimulus candidate on page %d: %.1fx%.1f",
                page_idx + 1,
                visual_width,
                visual_height,
            )
            return None

        nearby_word_rects = [
            (word["x0"], word["top"], word["x1"], word["bottom"])
            for word in words
            if q_top <= word["top"] <= min(option_top, q_bottom)
            and word["top"] > prompt_bottom + 2
            and word["top"] <= visual_rect[3] + 12
            and self._is_visual_label(word, visual_rect, page)
        ]
        if nearby_word_rects:
            visual_rect = union_rects([visual_rect, *nearby_word_rects])

        visual_rect = self._sandwich_visual_rect(
            visual_rect, words, q_top, prompt_bottom, option_top, page
        )
        clip = expand_rect(visual_rect, 6, 6, page)
        logger.debug("Found stimulus clip on page %d: %s", page_idx + 1, clip)
        return clip

    def attach_option_images(
        self,
        page_idx: int,
        page: pdfplumber.page.Page,
        question_clip: Rect,
        options: list[dict],
    ) -> None:
        if (
            not self._fitz_doc
            or not options
            or any(option["text"] for option in options)
        ):
            return

        option_clips = self._option_image_clips(page_idx, page, question_clip)
        attached = 0
        for option in options:
            clip = option_clips.get(option["label"])
            if not clip:
                continue

            option["image"] = self.transparent_region_base64(page_idx, clip)
            attached += 1

        if attached:
            logger.debug("Attached %d option images on page %d", attached, page_idx + 1)

    def render_page(self, page_num: int, zoom: float = 2.0) -> bytes:
        """Render a full page as PNG bytes (0-indexed)."""
        page = self._fitz_doc[page_num]
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        return pix.tobytes("png")

    def render_region(self, page_num: int, clip: Rect, zoom: float = 2.0) -> bytes:
        """Render a cropped region as PNG bytes. clip = (x0, y0, x1, y1)."""
        page = self._fitz_doc[page_num]
        rect = fitz.Rect(*clip)
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=rect)
        return pix.tobytes("png")

    def render_transparent_region(
        self, page_num: int, clip: Rect, zoom: float = 2.0
    ) -> bytes:
        """Render a cropped region and make white paper background transparent."""
        png_bytes = self.render_region(page_num, clip, zoom)
        image = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        pixels = image.load()
        width, height = image.size
        for x in range(width):
            for y in range(height):
                red, green, blue = pixels[x, y][:3]
                if red > 245 and green > 245 and blue > 245:
                    pixels[x, y] = (red, green, blue, 0)

        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue()

    def transparent_region_base64(
        self, page_num: int, clip: Rect, zoom: float = 2.0
    ) -> str:
        png_bytes = self.render_transparent_region(page_num, clip, zoom)
        return base64.b64encode(png_bytes).decode("utf-8")

    def render_page_base64(self, page_num: int, zoom: float = 2.0) -> str:
        """Render a page as a base64-encoded PNG string (for embedding in JSON/HTML)."""
        png_bytes = self.render_page(page_num, zoom)
        return base64.b64encode(png_bytes).decode("utf-8")

    def _option_image_clips(
        self,
        page_idx: int,
        page: pdfplumber.page.Page,
        question_clip: Rect,
    ) -> dict[str, Rect]:
        _, q_top, q_x1, q_bottom = question_clip
        words = page.extract_words()
        labels = {
            word["text"][0]: word
            for word in words
            if word["text"] in {"A.", "B.", "C.", "D."}
            and q_top <= word["top"] <= q_bottom
        }
        if set(labels) != {"A", "B", "C", "D"}:
            logger.debug("Option image labels were incomplete on page %d", page_idx + 1)
            return {}

        x_split = page.width / 2
        y_split = min(labels["C"]["top"], labels["D"]["top"]) - 4
        cells = {
            "A": (labels["A"]["x0"] - 2, labels["A"]["top"] - 10, x_split, y_split),
            "B": (labels["B"]["x0"] - 2, labels["B"]["top"] - 10, q_x1, y_split),
            "C": (labels["C"]["x0"] - 2, labels["C"]["top"] - 10, x_split, q_bottom),
            "D": (labels["D"]["x0"] - 2, labels["D"]["top"] - 10, q_x1, q_bottom),
        }

        drawing_rects = self._drawing_rects(page_idx)
        clips = {}
        for label, cell in cells.items():
            candidates = [
                rect_intersection(rect, cell)
                for rect in drawing_rects
                if rect_intersects(rect, cell)
                and not self._is_page_rule(rect, page)
                and not self._is_glyph_like_drawing(rect)
            ]
            if not candidates:
                continue

            candidates = self._largest_visual_cluster(candidates)
            visual_rect = union_rects(candidates)
            nearby_word_rects = [
                (word["x0"], word["top"], word["x1"], word["bottom"])
                for word in words
                if rect_intersects(
                    (word["x0"], word["top"], word["x1"], word["bottom"]),
                    cell,
                )
                and self._is_visual_label(word, visual_rect, page)
            ]
            if nearby_word_rects:
                visual_rect = union_rects([visual_rect, *nearby_word_rects])

            clips[label] = expand_rect(visual_rect, 6, 6, page)

        return clips

    def _trim_before_followup_text(
        self, visual_rect: Rect, words: list[dict], option_top: float
    ) -> Rect:
        for line_words in group_words_by_line(words):
            line_top = min(word["top"] for word in line_words)
            if not visual_rect[1] + 40 < line_top < min(visual_rect[3], option_top):
                continue

            line_text = " ".join(clean_text(word["text"]) for word in line_words)
            if len(line_words) >= 3 and not all(
                is_axis_or_tick_label(word) for word in line_text.split()
            ):
                return (visual_rect[0], visual_rect[1], visual_rect[2], line_top - 4)

        return visual_rect

    def _sandwich_visual_rect(
        self,
        visual_rect: Rect,
        words: list[dict],
        question_top: float,
        prompt_bottom: float,
        option_top: float,
        page: pdfplumber.page.Page,
    ) -> Rect:
        top = (
            self._prompt_block_bottom(
                words, question_top, visual_rect[1], prompt_bottom
            )
            + 1
        )
        bottom = self._followup_text_top(visual_rect, words, option_top) - 2
        bottom = max(bottom, top + 26)

        band_rect = (0, top, page.width, min(option_top, bottom))
        band_word_rects = [
            (word["x0"], word["top"], word["x1"], word["bottom"])
            for word in words
            if rect_intersects(
                (word["x0"], word["top"], word["x1"], word["bottom"]),
                band_rect,
            )
        ]
        rect = (
            union_rects([visual_rect, *band_word_rects])
            if band_word_rects
            else visual_rect
        )
        return (rect[0], top, rect[2], min(option_top - 2, bottom))

    def _prompt_block_bottom(
        self,
        words: list[dict],
        question_top: float,
        visual_top: float,
        fallback: float,
    ) -> float:
        prompt_line_bottoms = []
        for line_words in group_words_by_line(words):
            line_top = min(word["top"] for word in line_words)
            if question_top <= line_top < visual_top - 4:
                prompt_line_bottoms.append(max(word["bottom"] for word in line_words))
        return max(prompt_line_bottoms, default=fallback)

    def _followup_text_top(
        self, visual_rect: Rect, words: list[dict], option_top: float
    ) -> float:
        for line_words in group_words_by_line(words):
            line_top = min(word["top"] for word in line_words)
            if not visual_rect[3] + 2 < line_top < option_top:
                continue

            line_text = " ".join(clean_text(word["text"]) for word in line_words)
            line_rect = union_rects(
                [
                    (word["x0"], word["top"], word["x1"], word["bottom"])
                    for word in line_words
                ]
            )
            if self._is_visual_annotation_line(line_text, line_rect, visual_rect):
                continue

            return line_top

        return option_top

    def _is_visual_annotation_line(
        self, line_text: str, line_rect: Rect, visual_rect: Rect
    ) -> bool:
        lower_text = clean_text(line_text).lower()
        tokens = lower_text.split()
        expanded_visual_rect = (
            visual_rect[0] - 40,
            visual_rect[1] - 20,
            visual_rect[2] + 40,
            visual_rect[3] + 60,
        )
        if not rect_intersects(line_rect, expanded_visual_rect):
            return False

        if any(re.fullmatch(r"\d{1,2}\s*(?:am|pm)", token) for token in tokens):
            return True
        if all(is_axis_or_tick_label(token) for token in tokens):
            return True
        return lower_text in {"time", "number of bees", "fo rebmun", "fo rebmun time"}

    def _largest_visual_cluster(self, rects: list[Rect]) -> list[Rect]:
        clusters = []
        for rect in sorted(rects, key=lambda item: item[1]):
            if not clusters:
                clusters.append([rect])
                continue

            current_cluster = clusters[-1]
            current_bottom = max(item[3] for item in current_cluster)
            if rect[1] <= current_bottom + 20:
                current_cluster.append(rect)
            else:
                clusters.append([rect])

        return max(clusters, key=self._cluster_area)

    def _cluster_area(self, rects: list[Rect]) -> float:
        rect = union_rects(rects)
        return (rect[2] - rect[0]) * (rect[3] - rect[1])

    def _prompt_line_bottom(self, words: list[dict], question_top: float) -> float:
        line_words = words_on_line(words, question_top)
        if not line_words:
            return question_top
        return max(word["bottom"] for word in line_words)

    def _is_page_rule(self, rect: Rect, page: pdfplumber.page.Page) -> bool:
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        return width > page.width * 0.65 and height < 2

    def _is_glyph_like_drawing(self, rect: Rect) -> bool:
        width = rect[2] - rect[0]
        height = rect[3] - rect[1]
        return 2 < width < 25 and 2 < height < 25

    def _is_visual_label(
        self, word: dict, visual_rect: Rect, page: pdfplumber.page.Page
    ) -> bool:
        word_rect = (word["x0"], word["top"], word["x1"], word["bottom"])
        if rect_intersects(word_rect, visual_rect):
            return True

        if not is_axis_or_tick_label(word["text"]):
            return False

        label_search_rect = expand_rect(visual_rect, 24, 28, page)
        return rect_intersects(word_rect, label_search_rect)

    def _drawing_rects(self, page_idx: int) -> list[Rect]:
        page = self._fitz_doc[page_idx]
        rects = []
        for drawing in page.get_drawings():
            rect = drawing.get("rect")
            if rect and rect.is_valid:
                rects.append((rect.x0, rect.y0, rect.x1, rect.y1))

        for image_info in page.get_images(full=True):
            xref = image_info[0]
            for rect in page.get_image_rects(xref):
                if rect and rect.is_valid:
                    rects.append((rect.x0, rect.y0, rect.x1, rect.y1))

        return rects
