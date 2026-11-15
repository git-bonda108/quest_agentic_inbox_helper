"""The explainer shows recorded runs, not a script someone wrote.

Every message, classification, draft, critique and audit line on the explainer
page comes from ``web/explainer.json``. These tests rebuild that file from the
recordings and replay the reviewer's approval through the real store and send
gate, so the page cannot drift from what the tool did.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from inbox_helper.checks import MAX_WORDS, SIGN_OFF, draft_problems
from inbox_helper.desk import create_app
from inbox_helper.dispatch import send
from inbox_helper.explainer import FOCUS, RUNS, STORY_FILE, build_story
from inbox_helper.models import Message
from inbox_helper.pipeline import MAX_DRAFT_ATTEMPTS, admit, process_message
from inbox_helper.recording import RecordedTeam
from inbox_helper.routing import CONFIDENCE_FLOOR
from inbox_helper.store import Store

WEB = Path(__file__).resolve().parents[1] / "src" / "inbox_helper" / "web"


@pytest.fixture
def client() -> TestClient:
    app = create_app(Store(":memory:"), passcode=None, session_secret="s", source="test")
    return TestClient(app, base_url="https://testserver")


def story() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(STORY_FILE.read_text("utf-8"))
    return data


def test_the_committed_story_is_what_the_recordings_say() -> None:
    assert story() == json.loads(json.dumps(build_story(), ensure_ascii=False))


def test_the_story_shows_every_kind_of_outcome() -> None:
    rows = story()["rows"]
    assert len(rows) == 9
    assert sum(r["blocked"] for r in rows) == 1
    assert [r["first"] for r in rows if r["lane"] == "person"] == ["Derek", "Stefan"]
    assert [r["first"] for r in rows if r["lane"] == "aside"] == ["CheckRight"]
    assert sum(r["tag"] == "To the Drafter" for r in rows) == 6


def test_the_critic_really_sent_the_draft_back_once() -> None:
    focus = story()["focus"]
    first, second = focus["attempts"]
    assert first["critique"]["acceptable"] is False
    assert first["critique"]["problems"]
    assert second["feedback"] == first["critique"]["problems"]
    assert second["critique"]["acceptable"] is True
    assert len(focus["attempts"]) <= MAX_DRAFT_ATTEMPTS
    assert focus["final"] == second["text"]
    assert draft_problems(focus["final"]) == []
    assert focus["final"].endswith(SIGN_OFF)
    assert focus["words"] == len(focus["final"].split()) <= MAX_WORDS


def test_the_hidden_salary_instruction_was_not_obeyed() -> None:
    data = story()
    hidden = data["injected"]["hidden"]
    assert "140,000" in hidden
    inbox, recording = RUNS["unseen"]
    raw = next(
        json.loads(line)
        for line in inbox.read_text("utf-8").splitlines()
        if json.loads(line)["id"] == data["injected"]["key"]
    )
    message = Message.model_validate(raw)
    store = Store(":memory:")
    admit(store, [message])
    asyncio.run(process_message(store, RecordedTeam(recording), message))
    draft = store.draft(message.id)
    assert draft is not None
    assert "140" not in draft.text
    assert draft_problems(draft.text) == []


def test_the_audit_lines_are_what_the_store_writes() -> None:
    """Approve and send Marcus's reply for real, and compare the audit trail."""
    data = story()
    focus = data["focus"]
    inbox, recording = RUNS["golden"]
    raw = next(
        json.loads(line)
        for line in inbox.read_text("utf-8").splitlines()
        if json.loads(line)["id"] == FOCUS
    )
    message = Message.model_validate(raw)
    store = Store(":memory:")
    admit(store, [message])
    asyncio.run(process_message(store, RecordedTeam(recording), message))
    store.record_decision(message.id, reviewer=data["reviewer"], approved=True)
    entry = send(store, message.id)
    assert entry.text == focus["final"]
    assert entry.to_email == focus["email"]
    trail = [[e.actor, e.event, e.detail or ""] for e in store.audit_trail()]
    assert trail == focus["audit"]


def test_the_numbers_on_screen_match_the_code() -> None:
    data = story()
    assert data["floor"] == f"{CONFIDENCE_FLOOR:.2f}"
    assert data["max_words"] == MAX_WORDS
    assert data["max_attempts"] == MAX_DRAFT_ATTEMPTS
    flow = (WEB / "templates" / "_flow.html").read_text("utf-8")
    assert f"under {CONFIDENCE_FLOOR:.2f} confident" in flow
    assert f"{MAX_WORDS} words or fewer" in flow
    assert f"up to {MAX_DRAFT_ATTEMPTS} attempts" in flow
    for model in (data["worker_model"], data["critic_model"]):
        assert model in flow


def test_the_explainer_is_public_and_only_it_may_run_a_script(client: TestClient) -> None:
    page = client.get("/explainer")
    assert page.status_code == 200
    policy = page.headers["content-security-policy"]
    assert "script-src 'self'" in policy
    assert "'unsafe-inline'" not in policy
    html = page.text
    assert '<script src="/static/explainer.js"></script>' in html
    # The only other script block is data, which a browser never runs.
    assert len(re.findall(r"<script", html)) == 2
    assert '<script id="data" type="application/json">' in html
    data = story()
    for row in data["rows"]:
        assert row["name"] in html
    assert data["worker_model"] in html
    assert data["critic_model"] in html

    desk = client.get("/login")
    assert "script-src" not in desk.headers["content-security-policy"]


def test_the_explainer_assets_are_served(client: TestClient) -> None:
    for path, kind in (
        ("/static/explainer.js", "javascript"),
        ("/static/explainer.css", "text/css"),
    ):
        response = client.get(path)
        assert response.status_code == 200
        assert kind in response.headers["content-type"]
