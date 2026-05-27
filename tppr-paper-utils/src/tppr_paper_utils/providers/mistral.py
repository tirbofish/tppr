from __future__ import annotations

import base64
import mimetypes
import os
from pathlib import Path
from typing import Any

from mistralai.client import Mistral

from tppr_paper_utils.providers import (
    OCRInput,
    OCROptions,
    OCRPage,
    OCRProvider,
    OCRResult,
)


class MistralOCRError(RuntimeError):
    """
    Exception thrown when the Mistral OCR provider throws an error in its requests.
    """

    pass


class MistralOCRProvider(OCRProvider):
    name = "mistral"

    def __init__(self, mistral: Mistral):
        self.mistral = mistral

    @classmethod
    def from_env(cls) -> "MistralOCRProvider":
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise MistralOCRError("MISTRAL_API_KEY is not set")

        return cls(mistral=Mistral(api_key=api_key))

    def extract(
        self,
        source: OCRInput,
        options: OCROptions | None = None,
    ) -> OCRResult:
        options = options or OCROptions()
        document = self._build_document(source)
        table_format = options.table_format
        if table_format is None and options.include_tables:
            table_format = "html"

        if table_format not in {None, "html", "markdown"}:
            raise MistralOCRError(
                "Mistral OCR table_format must be None, 'html', or 'markdown'"
            )

        pages = None
        if options.max_pages is not None:
            if options.max_pages < 1:
                raise MistralOCRError("max_pages must be greater than zero")
            pages = list(range(options.max_pages))

        try:
            response = self.mistral.ocr.process(
                model="mistral-ocr-latest",
                document=document,
                pages=pages,
                table_format=table_format,
                extract_header=options.extract_header,
                extract_footer=options.extract_footer,
                include_image_base64=options.include_images,
                timeout_ms=options.timeout_seconds * 1000,
            )
        except Exception as exc:
            raise MistralOCRError(f"Mistral OCR failed: {exc}") from exc

        raw = self._dump(response)
        ocr_pages = [self._to_ocr_page(page) for page in response.pages]
        text = "\n\n".join(page.text for page in ocr_pages if page.text)

        return OCRResult(
            provider=self.name,
            text=text,
            pages=ocr_pages,
            raw=raw,
        )

    def _build_document(self, source: OCRInput) -> dict[str, str]:
        mime_type = self._infer_mime_type(source)

        match source.type:
            case "url":
                if not isinstance(source.value, str):
                    raise MistralOCRError("url OCRInput value must be a string")
                url = source.value

            case "file_path":
                path = Path(source.value)
                if not path.is_file():
                    raise MistralOCRError(f"File does not exist: {path}")
                url = self._data_uri(path.read_bytes(), mime_type)

            case "bytes":
                if not isinstance(source.value, bytes):
                    raise MistralOCRError("bytes OCRInput value must be bytes")
                url = self._data_uri(source.value, mime_type)

            case "base64":
                if not isinstance(source.value, str):
                    raise MistralOCRError("base64 OCRInput value must be a string")
                url = source.value
                if not url.startswith("data:"):
                    url = f"data:{mime_type};base64,{url}"

            case _:
                raise MistralOCRError(f"Unsupported OCR input type: {source.type}")

        if mime_type.startswith("image/") or url.startswith("data:image/"):
            return {"type": "image_url", "image_url": url}

        return {"type": "document_url", "document_url": url}

    def _infer_mime_type(self, source: OCRInput) -> str:
        if source.mime_type:
            return source.mime_type

        guess_source: str | None = None
        if source.filename:
            guess_source = source.filename
        elif source.type == "file_path":
            guess_source = str(source.value)
        elif source.type == "url" and isinstance(source.value, str):
            guess_source = source.value
        elif (
            source.type == "base64"
            and isinstance(source.value, str)
            and source.value.startswith("data:")
        ):
            return source.value.split(";", 1)[0].removeprefix("data:")

        if guess_source:
            guessed, _ = mimetypes.guess_type(guess_source)
            if guessed:
                return guessed

        return "application/pdf"

    def _data_uri(self, content: bytes, mime_type: str) -> str:
        encoded = base64.b64encode(content).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def _to_ocr_page(self, page: Any) -> OCRPage:
        raw = self._dump(page)
        dimensions = getattr(page, "dimensions", None)
        confidence_scores = getattr(page, "confidence_scores", None)
        page_index = getattr(page, "index", 0)
        markdown = getattr(page, "markdown", "") or ""

        return OCRPage(
            page_number=page_index + 1,
            text=markdown,
            markdown=markdown,
            confidence=getattr(
                confidence_scores,
                "average_page_confidence_score",
                None,
            ),
            width=getattr(dimensions, "width", None),
            height=getattr(dimensions, "height", None),
            raw=raw,
        )

    def _dump(self, value: Any) -> dict[str, Any]:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")

        if isinstance(value, dict):
            return value

        return dict(value)
