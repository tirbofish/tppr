from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

OCRInputType = Literal["file_path", "url", "bytes", "base64"]


@dataclass(frozen=True)
class OCRInput:
    type: OCRInputType
    value: str | bytes | Path
    mime_type: Optional[str] = None
    filename: Optional[str] = None


@dataclass(frozen=True)
class OCRPage:
    page_number: int
    text: str
    markdown: Optional[str] = None
    confidence: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OCRResult:
    provider: str
    text: str
    pages: list[OCRPage]
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OCROptions:
    include_images: bool = False
    include_tables: bool = True
    output_format: Literal["text", "markdown", "json"] = "markdown"
    timeout_seconds: int = 60
    max_pages: Optional[int] = None
    table_format: Optional[str] = None
    extract_header: bool = False
    extract_footer: bool = False


class OCRProvider(ABC):
    name: str

    @abstractmethod
    def extract(
        self,
        source: OCRInput,
        options: OCROptions | None = None,
    ) -> OCRResult:
        raise NotImplementedError
