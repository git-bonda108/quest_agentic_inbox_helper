"""Every routing row in evals/README.md must match the result file it names.

A number in a document is a claim. This keeps the claims tied to the files the
runs produced, so the results page cannot drift from the evidence.
"""

from __future__ import annotations

import json
import re

from inbox_helper.cli import ROOT

README = (ROOT / "evals" / "README.md").read_text(encoding="utf-8")
RESULTS = ROOT / "evals" / "results"
FRACTION = re.compile(r"\b(\d+)/(\d+)\b")


def _rows() -> list[tuple[str, str]]:
    rows = []
    for line in README.splitlines():
        found = re.match(r"\| `([a-z0-9-]+)` \|", line)
        if found and (RESULTS / f"{found.group(1)}.json").exists():
            rows.append((found.group(1), line))
    return rows


def _load(name: str) -> dict[str, object]:
    data: dict[str, object] = json.loads((RESULTS / f"{name}.json").read_text(encoding="utf-8"))
    return data


def test_the_results_page_names_every_result_file() -> None:
    named = {name for name, _ in _rows()}
    on_disk = {path.stem for path in RESULTS.glob("*.json")}
    assert on_disk - named == set()


def test_every_routing_row_matches_its_result_file() -> None:
    checked = 0
    for name, line in _rows():
        data = _load(name)
        if "action_correct" not in data:
            continue
        fractions = [f"{a}/{b}" for a, b in FRACTION.findall(line)]
        action = f"{data['action_correct']}/{data['total']}"
        intent = f"{data['intent_correct']}/{data.get('intent_scored', data['total'])}"
        assert action in fractions, f"{name}: the page does not show {action} routed as labelled"
        if len(fractions) >= 2:
            assert fractions[0] == intent, (
                f"{name}: the page shows {fractions[0]}, the file {intent}"
            )
        checked += 1
    assert checked >= 25


def test_every_reviewer_row_matches_its_result_file() -> None:
    checked = 0
    for name, line in _rows():
        data = _load(name)
        if "planted" in data:  # a local planted-draft run
            assert f"{data['caught']}/{data['planted']}" in line, name
            assert f"{data['controls_passed']}/{data['controls']}" in line, name
            checked += 1
        elif "drafts_judged" in data:  # the judge on real drafts
            cells = [cell.strip() for cell in line.split("|")]
            assert str(data["drafts_judged"]) in cells, name
            assert str(data["drafts_flagged"]) in cells, name
            checked += 1
        elif "blocked_by_guardrail" in data and "planted_flaws_caught" not in data:
            cells = [cell.strip() for cell in line.split("|")]
            assert str(data["passed"]) in cells, name
            assert str(len(data["failed"])) in cells, name  # type: ignore[arg-type]
            assert str(len(data["blocked_by_guardrail"])) in cells, name  # type: ignore[arg-type]
            checked += 1
    assert checked >= 10
