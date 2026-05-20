from __future__ import annotations

import logging
import re

import pdfplumber

from .geometry import (
    Rect,
    group_words_by_line,
    rect_intersects,
    union_rects,
    word_center_inside,
    words_on_line,
)
from .text import (
    clean_option_value,
    clean_question_lines,
    clean_text,
    fraction_latex,
    is_axis_only_option,
    is_page_footer,
    looks_like_graphical_options,
    option_latex,
    question_latex,
    split_stimulus_and_prompt,
)
from .visual import VisualExtractor

logger = logging.getLogger(__name__)


class QuestionExtractor:
    def __init__(self, pdf: pdfplumber.PDF, visual: VisualExtractor):
        self.pdf = pdf
        self.visual = visual

    def extract(self) -> list[dict]:
        return self.extract_section_i()

    def extract_section_i(self) -> list[dict]:
        """Extract Section I questions using page coordinates."""
        section_pages = self._section_i_page_range()
        question_limit = self._section_i_question_limit()
        logger.debug("Extracting Section I questions from pages: %s", sorted(section_pages))
        page_starts = []
        for page_idx, page in enumerate(self.pdf.pages):
            if section_pages and page_idx + 1 not in section_pages:
                continue
            starts = self._question_starts(page.extract_words(), question_limit)
            if starts:
                logger.debug(
                    "Found %d question starts on page %d", len(starts), page_idx + 1
                )
                page_starts.append((page_idx, starts))

        questions = []
        for page_idx, starts in page_starts:
            page = self.pdf.pages[page_idx]
            for start_idx, start in enumerate(starts):
                bottom = (
                    starts[start_idx + 1]["top"]
                    if start_idx + 1 < len(starts)
                    else self._page_content_bottom(page)
                )
                clip = self._question_clip(page, start["top"], bottom)
                stimulus_clip = self.visual.stimulus_clip(page_idx, page, clip)
                (
                    question_text,
                    options,
                    stimulus_text,
                    question_to_answer,
                ) = self._parse_question_text(page, clip, stimulus_clip)

                question = {
                    "number": start["number"],
                    "type": "multiple_choice",
                    "text": question_text,
                    "options": options,
                    "page": page_idx + 1,
                }

                if stimulus_text:
                    question["stimulus_question"] = stimulus_text

                if question_to_answer:
                    question["question_to_answer"] = question_to_answer

                if stimulus_clip:
                    question["image"] = self.visual.transparent_region_base64(
                        page_idx, stimulus_clip
                    )
                    logger.debug(
                        "Attached stimulus image for question %d on page %d",
                        start["number"],
                        page_idx + 1,
                    )

                self.visual.attach_option_images(page_idx, page, clip, options)
                questions.append(question)

        logger.info("Extracted %d Section I questions", len(questions))
        return sorted(questions, key=lambda q: q["number"])

    def _question_starts(self, words: list[dict], question_limit: int) -> list[dict]:
        starts = []
        seen = set()
        for word in words:
            text = word["text"]
            if not re.fullmatch(r"\d{1,2}", text):
                continue
            number = int(text)
            if not 1 <= number <= question_limit:
                continue
            if not 55 <= word["x0"] <= 85:
                continue
            if word["top"] > 760:
                continue
            line_words = words_on_line(words, word["top"])
            has_question_body = any(w["x0"] > 90 for w in line_words)
            if not has_question_body:
                continue
            key = (number, round(word["top"], 1))
            if key in seen:
                continue
            seen.add(key)
            starts.append({"number": number, "top": word["top"]})
        return sorted(starts, key=lambda item: item["top"])

    def _section_i_page_range(self) -> set[int]:
        first_page_text = self.pdf.pages[0].extract_text() if self.pdf.pages else ""
        match = re.search(
            r"Section\s+I\s*[–—-]\s*\d+\s*marks\s*\(pages?\s*(\d+)\s*[–—-]\s*(\d+)\)",
            first_page_text or "",
        )
        if not match:
            logger.warning("Section I page range was not found; scanning all pages")
            return set()
        start, end = (int(match.group(1)), int(match.group(2)))
        return set(range(start, end + 1))

    def _section_i_question_limit(self) -> int:
        first_page_text = self.pdf.pages[0].extract_text() if self.pdf.pages else ""
        match = re.search(
            r"Section\s+I\s*[–—-]\s*(\d+)\s*marks",
            first_page_text or "",
        )
        if not match:
            logger.warning("Section I mark count was not found; allowing questions 1-30")
            return 30
        return int(match.group(1))

    def _page_content_bottom(self, page: pdfplumber.page.Page) -> float:
        words = page.extract_words()
        footer_top = min(
            (w["top"] for w in words if w["text"] == "–" and w["top"] > 730),
            default=page.height - 40,
        )
        return footer_top

    def _question_clip(self, page: pdfplumber.page.Page, top: float, bottom: float) -> Rect:
        padding = 2
        return (
            0,
            max(0, top - padding),
            page.width,
            min(page.height, bottom - 2),
        )

    def _parse_question_text(
        self,
        page: pdfplumber.page.Page,
        clip: Rect,
        stimulus_clip: Rect | None = None,
    ) -> tuple[str, list[dict], str, str]:
        lines = self._extract_text_lines(page, clip, stimulus_clip)
        lines = [line for line in lines if line and not is_page_footer(line)]

        if not lines:
            return "", [], "", ""

        lines[0] = re.sub(r"^\d{1,2}\s+", "", lines[0]).strip()
        option_start = next(
            (i for i, line in enumerate(lines) if re.search(r"\bA\.\s*", line)),
            len(lines),
        )
        if (
            option_start > 0
            and re.fullmatch(r"(?:y|x|O)(?:\s+(?:y|x|O))*", lines[option_start - 1])
            and len(re.findall(r"\b[A-D]\.", lines[option_start])) > 1
        ):
            option_start -= 1

        question_lines = lines[:option_start]
        option_lines = lines[option_start:]
        if question_lines and option_lines and re.fullmatch(r"\d+", question_lines[-1]):
            if re.fullmatch(r"A\.", option_lines[0]):
                option_lines.insert(0, question_lines.pop())
            elif re.match(r"A\.", option_lines[0]):
                question_lines.pop()

        question_text = question_latex(clean_question_lines(question_lines))
        stimulus_text, question_to_answer = split_stimulus_and_prompt(question_text)

        return (
            question_text,
            self._extract_options(option_lines),
            stimulus_text,
            question_to_answer,
        )

    def _extract_text_lines(
        self,
        page: pdfplumber.page.Page,
        clip: Rect,
        excluded_clip: Rect | None,
    ) -> list[str]:
        cropped = page.crop(clip)
        words = cropped.extract_words(x_tolerance=2, y_tolerance=4)
        lines = []
        previous_bottom = None
        for line_words in group_words_by_line(words):
            if self._line_belongs_to_stimulus(line_words, excluded_clip):
                continue

            line_top = min(word["top"] for word in line_words)
            if previous_bottom is not None and line_top - previous_bottom > 10:
                lines.append("")

            line = " ".join(word["text"] for word in line_words)
            lines.append(clean_text(line))
            previous_bottom = max(word["bottom"] for word in line_words)
        return lines

    def _line_belongs_to_stimulus(
        self,
        line_words: list[dict],
        stimulus_clip: Rect | None,
    ) -> bool:
        if not line_words or not stimulus_clip:
            return False

        inside_count = sum(1 for word in line_words if word_center_inside(word, stimulus_clip))
        if inside_count / len(line_words) >= 0.5:
            return True

        line_rect = union_rects([
            (word["x0"], word["top"], word["x1"], word["bottom"])
            for word in line_words
        ])
        stimulus_text_clip = self._stimulus_text_clip(stimulus_clip)
        line_mid_y = (line_rect[1] + line_rect[3]) / 2
        return (
            rect_intersects(line_rect, stimulus_text_clip)
            and stimulus_text_clip[1] <= line_mid_y <= stimulus_text_clip[3]
        )

    def _stimulus_text_clip(self, stimulus_clip: Rect) -> Rect:
        x0, top, x1, bottom = stimulus_clip
        return (x0 - 24, top, x1 + 24, bottom)

    def _extract_options(self, lines: list[str]) -> list[dict]:
        if not lines:
            return []

        fraction_options = self._extract_stacked_fraction_options(lines)
        if fraction_options:
            return fraction_options

        option_text = "\n".join(lines)
        matches = list(re.finditer(r"\b([A-D])\.\s*", option_text))
        if not matches:
            return []

        graphical = looks_like_graphical_options(option_text, matches)
        options = []
        for idx, match in enumerate(matches):
            label = match.group(1)
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(option_text)
            value = clean_text(option_text[start:end])
            value = clean_text(value.replace("\n", " "))
            value = clean_option_value(value)
            if graphical or is_axis_only_option(value):
                value = ""
            options.append({
                "label": label,
                "text": option_latex(value),
            })

        return options

    def _extract_stacked_fraction_options(self, lines: list[str]) -> list[dict]:
        options = []
        idx = 0
        numerator = None
        while idx < len(lines):
            line = lines[idx]
            if re.fullmatch(r"\d+", line) and idx + 1 < len(lines):
                numerator = line
                idx += 1
                continue

            label_match = re.fullmatch(r"([A-D])\.", line)
            if (
                label_match
                and numerator
                and idx + 1 < len(lines)
                and re.fullmatch(r"\d+", lines[idx + 1])
            ):
                options.append({
                    "label": label_match.group(1),
                    "text": fraction_latex(numerator, lines[idx + 1]),
                })
                numerator = None
                idx += 2
                continue

            return []

        labels = [option["label"] for option in options]
        if labels == ["A", "B", "C", "D"]:
            return options
        return []
