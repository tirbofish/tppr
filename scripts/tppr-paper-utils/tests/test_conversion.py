from pathlib import Path
import pytest
import tppr_paper_utils
import json

TEST_DIR = Path(__file__).parent
PDF_PATH = TEST_DIR / "2025-hsc-maths-advanced.pdf"


def test_extraction():
    with open(PDF_PATH, "rb") as pdf:
        with tppr_paper_utils.TPPRExtractor(pdf) as extractor:
            print(json.dumps(extractor.extract()))


test_extraction()
