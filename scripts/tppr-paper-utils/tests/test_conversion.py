import base64
import io
from pathlib import Path

from PIL import Image

import tppr_paper_utils
from tppr_paper_utils.text import looks_like_stimulus_text

TEST_DIR = Path(__file__).parent
PDF_PATH = TEST_DIR / "2025-hsc-maths-advanced.pdf"
OUTPUT_PATH = TEST_DIR / f"{PDF_PATH.stem}.json"

extracted: dict | None = None


def extract_test_paper():
    global extracted

    if extracted is not None:
        return extracted

    with open(PDF_PATH, "rb") as pdf:
        with tppr_paper_utils.TPPRExtractor(pdf) as extractor:
            extracted = extractor.extract()
            return extracted


def assert_transparent_png(encoded: str):
    # ensures that the images found in the stimulus/question are transparent.
    image = Image.open(io.BytesIO(base64.b64decode(encoded)))
    assert image.mode == "RGBA"

    alpha = image.getchannel("A")
    assert alpha.getextrema() == (0, 255)


def test_extraction():
    data = extract_test_paper()

    questions = data["questions"]
    assert [question["number"] for question in questions] == list(range(1, 11))

    # question 1
    q1 = questions[0]
    assert q1["type"] == 'multiple_choice'
    assert q1['stimulus']['text'] == 'The probability distribution table for a discrete random variable X is shown.'
    assert q1['stimulus']['image'] != None
    assert q1['question'] == 'What is the value of $P(X=3)$?'
    assert q1['options'][0] == {
        "label": "A",
        "text": "$0.2$",
    }
    assert q1['options'][1] == {
        "label": "B",
        "text": "$0.4$",
    }
    assert q1['options'][2] == {
        "label": "C",
        "text": "$1.2$",
    }
    assert q1['options'][3] == {
        "label": "D",
        "text": "$2.0$",
    }

    # question 2
    q2 = questions[1]
    assert q2["type"] == 'multiple_choice'
    assert q2['stimulus']['text'] == None
    assert q2['stimulus']['image'] == None
    assert q2['question'] == 'Which graph could represent $y=4^x$?'
    assert q2['options'][0]["label"] == "A" and ['options'][0]["image"] != None
    assert q2['options'][1]["label"] == "B" and ['options'][1]["image"] != None
    assert q2['options'][2]["label"] == "C" and ['options'][2]["image"] != None
    assert q2['options'][3]["label"] == "D" and ['options'][3]["image"] != None

    # question 3
    q3 = questions[2]
    assert q3["type"] == 'multiple_choice'
    assert q3['stimulus']['text'] == None
    assert q3['stimulus']['image'] == None
    assert q3['question'] == 'What is the domain of the function $y = \sqrt{6 - x^2}$?'
    assert q3['options'][0]["label"] == "A" and [
        'options'][0]["image"] == None and ['options'][0]["text"] == "$(0, \sqrt{6})"
    assert q3['options'][1]["label"] == "B" and [
        'options'][1]["image"] == None and ['options'][0]["text"] == "$[0, \sqrt{6}]"
    assert q3['options'][2]["label"] == "C" and [
        'options'][2]["image"] == None and ['options'][0]["text"] == "$(-\sqrt{6}, \sqrt{6})"
    assert q3['options'][3]["label"] == "D" and [
        'options'][3]["image"] == None and ['options'][0]["text"] == "$[-\sqrt{6}, \sqrt{6}]"
