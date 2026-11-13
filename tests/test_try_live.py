"""The "try a message" form: one live message at a time, with a daily cap."""

from __future__ import annotations

import re

from fastapi.testclient import TestClient

from inbox_helper.desk import MAX_TRY_CHARS, create_app
from inbox_helper.models import Action, Intent, Message, Triage
from inbox_helper.store import Store
from scripted import GOOD


def _app(store: Store, *, live: bool = True, cap: int = 3) -> tuple[TestClient, list[Message]]:
    seen: list[Message] = []

    async def process(message: Message) -> None:
        seen.append(message)
        store.add_message(message)
        store.save_triage(
            Triage(
                message_id=message.id,
                intent=Intent.STATUS_CHECK,
                action=Action.DRAFT,
                confidence=0.9,
                reason="r",
            )
        )
        store.save_draft(message.id, GOOD)

    app = create_app(
        store,
        passcode=None,
        session_secret="test-secret",
        source="test",
        live=process if live else None,
        live_cap_per_day=cap,
        live_seconds_between=0,
    )
    return TestClient(app, base_url="https://testserver"), seen


def _sign_in(client: TestClient) -> str:
    def token(page: str) -> str:
        found = re.search(r'name="csrf" value="([^"]+)"', page)
        assert found is not None
        return found.group(1)

    return token(
        client.post("/login", data={"name": "Rita", "csrf": token(client.get("/login").text)}).text
    )


FORM = {"from_name": "Test Person", "subject": "Hello", "body": "Any update on my application?"}


def test_without_a_live_agent_there_is_no_form() -> None:
    client, _ = _app(Store(":memory:"), live=False)
    csrf = _sign_in(client)
    assert client.get("/try").status_code == 404
    assert client.post("/try", data=FORM | {"csrf": csrf}).status_code == 404
    assert "/try" not in client.get("/").text


def test_a_submitted_message_is_processed_once_and_appears_on_the_desk() -> None:
    store = Store(":memory:")
    client, seen = _app(store)
    csrf = _sign_in(client)
    response = client.post("/try", data=FORM | {"csrf": csrf})
    assert response.status_code == 200
    [message] = seen
    assert message.body == FORM["body"]
    assert message.from_email.endswith("@example.com")  # never a real address
    assert FORM["body"] in response.text
    assert store.outbox() == []  # processing never sends


def test_the_form_needs_sign_in_and_a_valid_token() -> None:
    client, seen = _app(Store(":memory:"))
    assert client.post("/try", data=FORM).status_code in (401, 403)
    _sign_in(client)
    assert client.post("/try", data=FORM | {"csrf": "wrong"}).status_code == 403
    assert seen == []


def test_the_daily_cap_stops_further_live_calls() -> None:
    client, seen = _app(Store(":memory:"), cap=2)
    csrf = _sign_in(client)
    assert client.post("/try", data=FORM | {"csrf": csrf}).status_code == 200
    assert client.post("/try", data=FORM | {"csrf": csrf}).status_code == 200
    capped = client.post("/try", data=FORM | {"csrf": csrf})
    assert capped.status_code == 429
    assert "limit" in capped.text
    assert len(seen) == 2


def test_an_empty_or_oversized_message_is_refused_before_any_live_call() -> None:
    client, seen = _app(Store(":memory:"))
    csrf = _sign_in(client)
    assert client.post("/try", data=FORM | {"body": "  ", "csrf": csrf}).status_code == 422
    too_long = "x" * (MAX_TRY_CHARS + 1)
    assert client.post("/try", data=FORM | {"body": too_long, "csrf": csrf}).status_code == 422
    assert seen == []


def test_a_failure_in_the_live_agent_is_explained_and_not_counted_as_sent() -> None:
    store = Store(":memory:")

    async def broken(_message: Message) -> None:
        raise RuntimeError("agent unavailable")

    app = create_app(store, passcode=None, session_secret="s", source="test", live=broken)
    client = TestClient(app, base_url="https://testserver")
    csrf = _sign_in(client)
    response = client.post("/try", data=FORM | {"csrf": csrf})
    assert response.status_code == 502
    assert store.outbox() == []
