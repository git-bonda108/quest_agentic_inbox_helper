"""Deterministic checks on a drafted reply. These run in code before the critic sees it."""

from __future__ import annotations

import re

MAX_WORDS = 90
SIGN_OFF = "Larkfield Labs Hiring Team"

_MONEY = re.compile(
    r"[$€£₹¥]|\b\d[\d,.]*\s?(?:k|usd|eur|gbp|inr|dollars?|euros?|pounds?|rupees?)\b",
    re.IGNORECASE,
)


def draft_problems(text: str) -> list[str]:
    """Return every rule the draft breaks. An empty list means it may go to the critic."""
    text = text.strip()
    if not text:
        return ["The reply is empty."]
    problems: list[str] = []
    words = len(text.split())
    if words > MAX_WORDS:
        problems.append(f"The reply has {words} words; the limit is {MAX_WORDS}.")
    if "!" in text:
        problems.append("The reply uses an exclamation mark.")
    if _MONEY.search(text):
        problems.append("The reply mentions an amount of money.")
    if not text.endswith(SIGN_OFF):
        problems.append(f"The reply must end with the sign-off '{SIGN_OFF}'.")
    return problems
