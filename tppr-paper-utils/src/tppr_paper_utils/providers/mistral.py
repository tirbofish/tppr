from __future__ import annotations

import os

from tppr_paper_utils.providers import (
    OCRInput,
    OCROptions,
    OCRProvider,
    OCRResult,
)


class MistralOCRError(RuntimeError):
    pass


class MistralOCRProvider(OCRProvider):
    name = "mistral"

    def __init__(
        self,
        api_key: str,
        model: str = "mistral-ocr-latest",
        ocr_url: str = "https://api.mistral.ai/v1/ocr",
    ):
        if not api_key:
            raise MistralOCRError("MISTRAL_API_KEY is not configured.")

        self.api_key = api_key
        self.model = model
        self.ocr_url = ocr_url

    @classmethod
    def from_env(cls) -> "MistralOCRProvider":
        return cls(
            api_key=os.getenv("MISTRAL_API_KEY", ""),
            model=os.getenv("MISTRAL_OCR_MODEL", "mistral-ocr-latest"),
            ocr_url=os.getenv("MISTRAL_OCR_URL", "https://api.mistral.ai/v1/ocr"),
        )

    def extract(
        self,
        source: OCRInput,
        options: OCROptions | None = None,
    ) -> OCRResult:
        return None  # todo for later
