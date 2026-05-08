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

    # questions based on 2025-hsc-maths-advanced.pdf, expected to see 2025-hsc-maths-advanced.json

    questions = data["questions"]
    assert [question["number"] for question in questions] == list(range(1, 11))
    assert [question["page"] for question in questions] == [
        2,
        3,
        3,
        4,
        4,
        5,
        6,
        6,
        7,
        8,
    ]

    q1 = questions[0]
    # question 1 is available
    assert q1["text"] == (
        "The probability distribution table for a discrete random variable X is shown. "
        "What is the value of P (X = 3)?"
    )
    # badly formatted text
    assert "xP (X = x)" not in q1["text"]
    # (previous) regex cutoff issue
    assert "Section I" not in q1["text"]
    # options for question 1
    assert q1["options"] == [
        {"label": "A", "text": "$0.2$"},
        {"label": "B", "text": "$0.4$"},
        {"label": "C", "text": "$1.2$"},
        {"label": "D", "text": "$2.0$"},
    ]

    q2 = questions[1]
    assert q2["text"] == "Which graph could represent $y = 4^{x}$?"
    assert [option["label"] for option in q2["options"]] == ["A", "B", "C", "D"]
    assert all(option["text"] == "" for option in q2["options"])
    assert all(option.get("image") for option in q2["options"])

    q3 = questions[2]
    assert "$y = 6 - x^{2}$" in q3["text"]
    assert q3["options"][0]["text"] == "$(0, 6)$"
    assert q3["options"][2]["text"] == "$(-6, 6)$"

    q7 = questions[6]
    assert q7["options"] == [
        {"label": "A", "text": "$\\frac{1}{17}$"},
        {"label": "B", "text": "$\\frac{1}{11}$"},
        {"label": "C", "text": "$\\frac{1}{10}$"},
        {"label": "D", "text": "$\\frac{1}{9}$"},
    ]

    q10 = questions[9]
    assert "$y = f(e^{x})$" in q10["text"]

    assert all("latex" not in question for question in questions)
    assert all(
        "latex" not in option
        for question in questions
        for option in question["options"]
    )

    option_image_question_numbers = [
        question["number"]
        for question in questions
        if any(option.get("image") for option in question["options"])
    ]
    assert option_image_question_numbers == [2, 4, 6]

    image_question_numbers = [
        question["number"] for question in questions if question.get("image")
    ]
    assert image_question_numbers == [1, 6, 9, 10]

    for question in questions:
        if not question.get("image"):
            continue

        assert_transparent_png(question["image"])

    for question in questions:
        for option in question["options"]:
            if not option.get("image"):
                continue

            assert_transparent_png(option["image"])


def test_stimulus_text_detection():
    assert looks_like_stimulus_text("1 2 4 3")
    assert looks_like_stimulus_text("EID 35 6 47 5 6")
    assert looks_like_stimulus_text("fo rebmuN 8 am 9 am 10 am 11 am 12 pm Time")
    assert looks_like_stimulus_text("fo rebmuN Time")

    assert not looks_like_stimulus_text(
        "The sum of the two numbers obtained is the score."
    )
    assert not looks_like_stimulus_text(
        "The table of scores below is partially completed."
    )
    assert not looks_like_stimulus_text(
        "What is the probability of getting a score of 7 or more?"
    )


def test_section_i_question_limit():
    data = extract_test_paper()

    assert len(data["questions"]) == data["metadata"]["sections"][0]["marks"]
