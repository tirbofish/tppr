"""
helpers for parsing through multiple choice questions
"""

import re


def extract_mc_questions(text: str) -> list[dict]:
    """
    In a multiple choice paper, there is always a combination of `A.`, `B.`, `C.`, `D.`. 
    From there, you can split off each section for each pattern
    """

    mc_pattern = re.compile(
        r'A\.\s+.+?\s+B\.\s+.+?\s+C\.\s+.+?\s+D\.\s+.+?(?=\n\d+\s|\Z|– \d+ –)',
        re.DOTALL
    )

    questions = []
    prev_end = 0
    for match in mc_pattern.finditer(text):
        option_block = match.group()

        options = re.findall(
            r'([A-D])\.\s+(.+?)(?=\s+[A-D]\.\s|\Z)', option_block, re.DOTALL)
        options = [{"label": label, "text": value.strip()}
                   for label, value in options]

        start = match.start()
        preceding = text[prev_end:start]

        # Find ALL line-starting 1-2 digit numbers, take the LAST one
        # This skips headers/instructions and finds the actual question number
        all_q_matches = list(re.finditer(
            r'(?:^|\n)(\d{1,2})\s+', preceding))

        prev_end = match.end()

        if all_q_matches:
            last_q = all_q_matches[-1]
            q_number = int(last_q.group(1))
            # Text starts after the question number, ends at option block
            q_text = preceding[last_q.end():].strip()

            questions.append({
                "number": q_number,
                "type": "multiple_choice",
                "text": q_text,
                "options": options,
                "char_offset": start,
                # Store where question text begins for image cropping
                "q_text_offset": prev_end - len(option_block) - len(preceding) + last_q.start(),
            })

    return questions
