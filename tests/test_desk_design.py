"""The desk's look: self-hosted fonts, group anchors, and an explicit choice to go public."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from inbox_helper.cli import require_passcode_or_public
from inbox_helper.desk import create_app
from inbox_helper.models import Action, Intent, Message, Triage
from inbox_helper.store import Store


def _client() -> TestClient:
    store = Store(":memory:")
    for message_id, intent, action in [
        ("m1", Intent.STATUS_CHECK, Action.DRAFT),
        ("m2", Intent.RESCHEDULE, Action.DRAFT),
        ("m3", Intent.ESCALATE, Action.ESCALATE),
    ]:
        store.add_message(
            Message.model_validate(
                {
                    "id": message_id,
                    "received_at": "2026-11-09T08:12:00Z",
                    "from_name": "Aiko Tanaka",
                    "from_email": "aiko.tanaka@example.com",
                    "subject": "Hello",
                    "body": "Any update?",
                }
            )
        )
        store.save_triage(
            Triage(message_id=message_id, intent=intent, action=action, confidence=0.9, reason="r")
        )
        if action is Action.DRAFT:
            store.save_draft(message_id, "Hi Aiko,\n\nThanks.\n\nLarkfield Labs Hiring Team")
    app = create_app(store, passcode=None, session_secret="s", source="test")
    client = TestClient(app, base_url="https://testserver")
    page = client.get("/login").text
    token = re.search(r'name="csrf" value="([^"]+)"', page)
    assert token is not None
    client.post("/login", data={"name": "Rita", "csrf": token.group(1)})
    return client


@pytest.mark.parametrize(
    "font", ["dm-sans-latin-wght-normal.woff2", "montserrat-latin-wght-normal.woff2"]
)
def test_fonts_are_served_from_the_app_itself(font: str) -> None:
    response = _client().get(f"/static/fonts/{font}")
    assert response.status_code == 200
    assert response.content[:4] == b"wOF2"
    assert response.headers["content-type"] == "font/woff2"


def test_the_content_policy_allows_only_local_fonts() -> None:
    policy = _client().get("/login").headers["content-security-policy"]
    assert "font-src 'self'" in policy
    assert policy.startswith("default-src 'none'")


def test_each_group_has_an_anchor_and_a_link_to_it() -> None:
    page = _client().get("/").text
    for key in ("status_check", "reschedule"):
        assert f'id="group-{key}"' in page
        assert f'href="#group-{key}"' in page
    assert 'id="group-needs-a-person"' in page


def test_the_login_page_asks_for_a_name_only_when_there_is_no_passcode() -> None:
    page = (
        TestClient(
            create_app(Store(":memory:"), passcode=None, session_secret="s", source="test"),
            base_url="https://testserver",
        )
        .get("/login")
        .text
    )
    assert 'name="name"' in page
    assert 'name="passcode"' not in page


def test_a_public_address_needs_a_passcode_or_an_explicit_choice() -> None:
    with pytest.raises(SystemExit):
        require_passcode_or_public(local=False, passcode=None, public=False)
    require_passcode_or_public(local=False, passcode=None, public=True)
    require_passcode_or_public(local=False, passcode="x", public=False)
    require_passcode_or_public(local=True, passcode=None, public=False)
