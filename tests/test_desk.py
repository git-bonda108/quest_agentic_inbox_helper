"""The review desk: a signed-in person approves, edits or rejects each draft."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from inbox_helper.checks import SIGN_OFF
from inbox_helper.desk import create_app
from inbox_helper.models import Action, Intent, Message, Triage
from inbox_helper.store import Store

DRAFT = f"Hi Aiko,\n\nWe review applications within 5 business days.\n\n{SIGN_OFF}"
HOSTILE = '<script>alert("x")</script>'


def _add(store: Store, message_id: str, intent: Intent, action: Action, body: str = "Hi") -> None:
    store.add_message(
        Message.model_validate(
            {
                "id": message_id,
                "received_at": "2026-11-09T08:12:00Z",
                "from_name": "Aiko Tanaka",
                "from_email": "aiko.tanaka@example.com",
                "subject": "Hello",
                "body": body,
            }
        )
    )
    store.save_triage(
        Triage(message_id=message_id, intent=intent, action=action, confidence=0.9, reason="r")
    )
    if action is Action.DRAFT:
        store.save_draft(message_id, DRAFT)


@pytest.fixture
def store() -> Store:
    store = Store(":memory:")
    _add(store, "m1", Intent.STATUS_CHECK, Action.DRAFT, body=HOSTILE)
    _add(store, "m2", Intent.ESCALATE, Action.ESCALATE)
    return store


@pytest.fixture
def client(store: Store) -> TestClient:
    app = create_app(store, passcode="open-sesame", session_secret="test-secret", source="test")
    return TestClient(app, base_url="https://testserver")


def _token(page: str) -> str:
    found = re.search(r'name="csrf" value="([^"]+)"', page)
    assert found is not None
    return found.group(1)


def _sign_in(client: TestClient, name: str = "Rita") -> str:
    page = client.get("/login").text
    response = client.post(
        "/login", data={"name": name, "passcode": "open-sesame", "csrf": _token(page)}
    )
    assert response.status_code == 200
    return _token(response.text)


def test_desk_requires_sign_in(client: TestClient) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert client.post("/messages/m1/approve", data={"text": DRAFT}).status_code in (401, 403)


def test_wrong_passcode_is_refused(client: TestClient) -> None:
    page = client.get("/login").text
    response = client.post(
        "/login", data={"name": "Rita", "passcode": "nope", "csrf": _token(page)}
    )
    assert response.status_code == 401


def test_approve_sends_the_text_the_reviewer_saw(client: TestClient, store: Store) -> None:
    csrf = _sign_in(client)
    response = client.post("/messages/m1/approve", data={"text": DRAFT, "csrf": csrf})
    assert response.status_code == 200
    [entry] = store.outbox()
    assert entry.text == DRAFT
    decision = store.latest_decision("m1")
    assert decision is not None
    assert decision.reviewer == "Rita"


def test_edited_text_is_what_gets_approved_and_sent(client: TestClient, store: Store) -> None:
    csrf = _sign_in(client)
    edited = f"Hi Aiko,\n\nA recruiter will follow up.\n\n{SIGN_OFF}"
    client.post("/messages/m1/approve", data={"text": edited, "csrf": csrf})
    [entry] = store.outbox()
    assert entry.text == edited
    draft = store.draft("m1")
    assert draft is not None
    assert draft.origin == "reviewer"


def test_reject_sends_nothing(client: TestClient, store: Store) -> None:
    csrf = _sign_in(client)
    assert client.post("/messages/m1/reject", data={"csrf": csrf}).status_code == 200
    assert store.outbox() == []
    decision = store.latest_decision("m1")
    assert decision is not None
    assert not decision.approved


def test_reviewer_name_comes_from_the_session_not_the_form(
    client: TestClient, store: Store
) -> None:
    csrf = _sign_in(client, name="Rita")
    client.post("/messages/m1/approve", data={"text": DRAFT, "csrf": csrf, "reviewer": "Mallory"})
    decision = store.latest_decision("m1")
    assert decision is not None
    assert decision.reviewer == "Rita"


def test_missing_or_wrong_csrf_token_is_refused(client: TestClient, store: Store) -> None:
    _sign_in(client)
    assert client.post("/messages/m1/approve", data={"text": DRAFT}).status_code == 403
    assert (
        client.post("/messages/m1/approve", data={"text": DRAFT, "csrf": "forged"}).status_code
        == 403
    )
    assert store.outbox() == []


def test_escalated_message_cannot_be_approved(client: TestClient, store: Store) -> None:
    csrf = _sign_in(client)
    response = client.post("/messages/m2/approve", data={"text": "Sorry.", "csrf": csrf})
    assert response.status_code == 409
    assert store.outbox() == []


def test_empty_reply_cannot_be_approved(client: TestClient, store: Store) -> None:
    csrf = _sign_in(client)
    assert client.post("/messages/m1/approve", data={"text": "  ", "csrf": csrf}).status_code == 422
    assert store.outbox() == []


def test_message_text_is_escaped_and_pages_carry_a_strict_policy(client: TestClient) -> None:
    _sign_in(client)
    response = client.get("/")
    assert HOSTILE not in response.text
    assert "&lt;script&gt;" in response.text
    policy = response.headers["content-security-policy"]
    assert "default-src 'none'" in policy
    assert "script-src" not in policy
    assert response.headers["x-frame-options"] == "DENY"


def test_desk_groups_by_intent_and_separates_escalations(client: TestClient) -> None:
    _sign_in(client)
    page = client.get("/").text
    assert "Status check" in page
    assert "Needs a person" in page
    assert "RECORDED" not in page  # the source label is shown as given
    assert "test" in page
