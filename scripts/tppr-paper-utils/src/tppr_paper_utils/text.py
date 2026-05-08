from __future__ import annotations

import re


def clean_text(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = text.translate(
        str.maketrans({
            "–": "-",
            "—": "-",
            "−": "-",
            "ƒ": "f",
            "′": "'",
            "“": '"',
            "”": '"',
            "‘": "'",
            "’": "'",
        })
    )
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    return text.strip()


def clean_question_lines(lines: list[str]) -> str:
    text = clean_text(" ".join(lines))
    text = re.sub(r"\s+([),.?])", r"\1", text)
    text = re.sub(r"([([])\s+", r"\1", text)
    return text


def clean_option_value(value: str) -> str:
    value = re.sub(r"\(\s+", "(", value)
    value = re.sub(r"\s+\)", ")", value)
    value = re.sub(r"\(\s*-\s*", "(-", value)
    value = re.sub(r"^-\s+", "-", value)
    value = re.sub(r",\s*-\s*", ", -", value)
    return value


def question_latex(text: str) -> str:
    latex = text

    latex = re.sub(
        r"What is 1 dx\? x \+ 5",
        r"What is $\\int \\frac{1}{\\sqrt{x + 5}}\\,dx$?",
        latex,
    )
    latex = re.sub(r"y = 4x", r"$y = 4^{x}$", latex)
    latex = re.sub(r"y = 6 - x 2", r"$y = 6 - x^{2}$", latex)
    latex = re.sub(
        r"y = -5 x \(x - 2\) \(3 - x\)",
        r"$y = -5x(x - 2)(3 - x)$",
        latex,
    )
    latex = re.sub(r"y = f\(x\)", r"$y = f(x)$", latex)
    latex = re.sub(r"y = -f\(-x\)", r"$y = -f(-x)$", latex)
    latex = re.sub(r"y = f'\(x\)", r"$y = f'(x)$", latex)
    latex = re.sub(r"f\(1\) = 6", r"$f(1) = 6$", latex)
    latex = re.sub(r"f\(1\.1\)", r"$f(1.1)$", latex)
    latex = re.sub(r"y = f\(e x\)", r"$y = f(e^{x})$", latex)

    return latex


def option_latex(value: str) -> str:
    if not value:
        return ""

    fraction_match = re.fullmatch(r"(\d+)/(\d+)", value)
    if fraction_match:
        return fraction_latex(fraction_match.group(1), fraction_match.group(2))

    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        return f"${value}$"

    percent_match = re.fullmatch(r"(\d+(?:\.\d+)?)%", value)
    if percent_match:
        return f"${percent_match.group(1)}\\%$"

    interval_match = re.fullmatch(r"\(?\s*(-?\d+),\s*(-?\d+)\s*\)?", value)
    if interval_match:
        left, right = interval_match.groups()
        return f"$({left}, {right})$"

    sqrt_option = sqrt_option_latex(value)
    if sqrt_option:
        return sqrt_option

    return f"${value}$"


def fraction_latex(numerator: str, denominator: str) -> str:
    return f"$\\frac{{{numerator}}}{{{denominator}}}$"


def sqrt_option_latex(value: str) -> str:
    normalised = value.replace("−", "-")
    patterns = {
        "x + 5 + C 2": r"$\frac{1}{2}\sqrt{x + 5} + C$",
        "2 x + 5 + C": r"$2\sqrt{x + 5} + C$",
        "2 x + 5 + C 1": r"$2\sqrt{x + 5} + C$",
        "- x + 5 + C 2": r"$-\frac{1}{2}\sqrt{x + 5} + C$",
        "-x + 5 + C 2": r"$-\frac{1}{2}\sqrt{x + 5} + C$",
        "-2 x + 5 + C": r"$-2\sqrt{x + 5} + C$",
    }
    return patterns.get(normalised, "")


def is_axis_or_tick_label(text: str) -> bool:
    text = clean_text(text)
    return bool(re.fullmatch(r"(?:x|y|O|-?\d+(?:\.\d+)?)", text))


def looks_like_stimulus_text(text: str) -> bool:
    text = clean_text(text)
    tokens = text.split()
    if not tokens:
        return False

    if all(is_axis_or_tick_label(token) for token in tokens):
        return True

    if re.search(r"\b\d{1,2}\s*(?:am|pm)\b", text, re.IGNORECASE):
        return True

    lower_text = text.lower()
    if "time" in lower_text and (
        "number" in lower_text or "rebmun" in lower_text or " fo " in f" {lower_text} "
    ):
        return True

    digit_tokens = [
        token
        for token in tokens
        if re.search(r"\d", token) and not re.search(r"[A-Za-z]{3,}", token)
    ]
    long_word_tokens = [token for token in tokens if re.search(r"[A-Za-z]{4,}", token)]
    short_tokens = [token for token in tokens if len(token.strip(".,:;()")) <= 4]

    if len(digit_tokens) >= 2 and len(digit_tokens) >= len(tokens) / 2:
        return True

    return (
        len(tokens) >= 3
        and len(short_tokens) / len(tokens) >= 0.75
        and bool(digit_tokens)
        and len(long_word_tokens) <= 1
        and not text.endswith("?")
    )


def looks_like_graphical_options(text: str, matches: list[re.Match]) -> bool:
    if len(matches) > 1 and any(
        text[matches[i].end() : matches[i + 1].start()].strip() in {"y", "O", ""}
        for i in range(len(matches) - 1)
    ):
        return True
    label_lines = [line for line in text.splitlines() if re.search(r"\b[A-D]\.", line)]
    return any(len(re.findall(r"\b[A-D]\.", line)) > 1 for line in label_lines)


def is_axis_only_option(value: str) -> bool:
    stripped = value.strip()
    if not stripped:
        return True
    tokens = re.findall(r"[A-Za-z']+|-?\d+", stripped)
    return bool(tokens) and all(token in {"x", "y", "O"} for token in tokens)


def is_page_footer(line: str) -> bool:
    return bool(re.fullmatch(r"-\s*\d+\s*-", line))
