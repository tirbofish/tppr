"""tppr-paper-extractor: convert Mistral OCR output into tppr paper JSON.

Public API:
    extract_paper(mistral_doc) -> dict   # tppr paper document
    validate_paper(paper) -> list[str]   # schema errors (empty list = valid)
"""

from .extractor import extract_paper, extract_paper_from_text, validate_paper

__all__ = ["extract_paper", "extract_paper_from_text", "validate_paper"]