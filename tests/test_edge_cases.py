"""Edge cases with mock data: odd inputs, repeated actions and two reviewers at once."""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import pytest
from fastapi.testclient import TestClient

from inbox_helper.checks import SIGN_OFF
from inbox_helper.desk import MAX_REPLY_CHARS, create_app
from inbox_helper.models import Action, Intent, Message, Triage
from inbox_helper.pipeline import process_inbox
from inbox_helper.service import MAX_INPUT_CHARS, propose
from inbox_helper.store import Store
from scripted import GOOD, ScriptedTeam, message

DRAFT = f"Hi Aiko,\n\nWe review applications within 5 business days.\n\n{SIGN_OFF}"
EDITED = f"Hi Aiko,\n\nThank you for your patience.\n\n{SIGN_OFF}"


def _message(message_id: str, **changes: object) -> Message:
    return Message.model_validate(message(message_id).model_dump(mode="json") | changes)


def _process(team: ScriptedTeam, *messages: Message) -> tuple[Store, dict[str, Any]]:
    store = Store(":memory:")
    outcomes = asyncio.run(process_inbox(store, team, list(messages)))
    return store, {outcome.message_id: outcome for outcome in outcomes}


# -- odd messages ---------------------------------------------------------------


@pytest.mark.parametrize("body", ["", "   ", "\n\t \n"])
def test_a_message_with_nothing_in_it_goes_to_a_person_without_a_model_call(body: str) -> None:
    team = ScriptedTeam(fail_on="m1")  # would raise if the classifier were called
    store, outcomes = _process(team, _message("m1", subject=" ", body=body))
    triage = store.triage("m1")
    assert triage is not None
    assert triage.action is Action.ESCALATE
    assert "empty" in triage.reason
    assert outcomes["m1"].error is None


def test_an_empty_body_with_a_subject_is_still_read() -> None:
    store, _ = _process(ScriptedTeam(), _message("m1", subject="Any update?", body=""))
    assert store.draft("m1") is not None


@pytest.mark.parametrize(
    "body",
    [
        "지원 현황이 궁금합니다. 감사합니다.",
        "मेरे आवेदन की स्थिति क्या है?",
        "هل من جديد بخصوص طلبي؟",
        "Any news? 🙏🙏 I'm so nervous 😬",
        "Zöe here — any update​?",  # combining mark and a zero-width space
    ],
)
def test_other_scripts_and_emoji_pass_through_unchanged(body: str) -> None:
    store, _ = _process(ScriptedTeam(), _message("m1", body=body))
    assert store.message("m1").body == body
    assert store.draft("m1") is not None


def test_the_same_id_twice_is_reported_and_the_first_copy_is_kept() -> None:
    first, second = _message("m1", body="first"), _message("m1", body="second")
    store = Store(":memory:")
    outcomes = asyncio.run(process_inbox(store, ScriptedTeam(), [first, second, _message("m2")]))
    assert store.message("m1").body == "first"
    assert [o.error is not None for o in outcomes] == [False, True, False]
    assert "duplicate" in (outcomes[1].error or "")
    assert store.draft("m2") is not None


def test_an_empty_inbox_is_fine() -> None:
    store, outcomes = _process(ScriptedTeam())
    assert outcomes == {}
    assert store.messages() == []


# -- the hosted service's input ---------------------------------------------------


def _service(payload: str) -> dict[str, Any]:
    reply: dict[str, Any] = json.loads(asyncio.run(propose(payload, ScriptedTeam())))
    return reply


def _payload(**changes: object) -> str:
    return json.dumps(message("m1").model_dump(mode="json") | changes)


def test_the_service_accepts_input_just_under_the_limit_and_refuses_one_over() -> None:
    room = MAX_INPUT_CHARS - len(_payload(body=""))
    assert _service(_payload(body="x" * room))["proposal"] is not None
    assert _service(_payload(body="x" * (room + 1)))["proposal"] is None


@pytest.mark.parametrize(
    "payload",
    ["", "null", "42", '"just a string"', "{}", '{"id": ""}', "{not json", '[{"id": "m1"}]'],
)
def test_the_service_refuses_anything_that_is_not_one_message(payload: str) -> None:
    reply = _service(payload)
    assert reply["proposal"] is None
    assert reply["error"]


def test_the_service_refuses_a_message_with_a_bad_date_or_stage() -> None:
    assert _service(_payload(received_at="yesterday"))["proposal"] is None
    assert _service(_payload(stage="offer_signed"))["proposal"] is None


def test_markup_in_a_message_comes_back_as_plain_json_text() -> None:
    hostile = '<script>alert(1)</script><img src=x onerror="alert(2)">'
    raw = asyncio.run(propose(_payload(body=hostile, from_name=hostile), ScriptedTeam()))
    assert json.loads(raw)["proposal"]["message_id"] == "m1"


# -- the review desk --------------------------------------------------------------


def _store_with_draft(body: str = "Hi", name: str = "Aiko Tanaka", subject: str = "Hello") -> Store:
    store = Store(":memory:")
    store.add_message(_message("m1", body=body, from_name=name, subject=subject))
    store.save_triage(
        Triage(
            message_id="m1",
            intent=Intent.STATUS_CHECK,
            action=Action.DRAFT,
            confidence=0.9,
            reason="r",
        )
    )
    store.save_draft("m1", DRAFT)
    return store


def _client(store: Store) -> TestClient:
    app = create_app(store, passcode=None, session_secret="test-secret", source="test")
    return TestClient(app, base_url="https://testserver")


def _sign_in(client: TestClient, name: str) -> str:
    def token(page: str) -> str:
        found = re.search(r'name="csrf" value="([^"]+)"', page)
        assert found is not None
        return found.group(1)

    response = client.post("/login", data={"name": name, "csrf": token(client.get("/login").text)})
    assert response.status_code == 200
    return token(response.text)


def test_approving_twice_sends_once_and_changes_nothing() -> None:
    store = _store_with_draft()
    client = _client(store)
    csrf = _sign_in(client, "Rita")
    assert (
        client.post("/messages/m1/approve", data={"text": DRAFT, "csrf": csrf}).status_code == 200
    )
    again = client.post("/messages/m1/approve", data={"text": DRAFT, "csrf": csrf})
    assert again.status_code == 409
    assert len(store.outbox()) == 1
    assert [e.event for e in store.audit_trail()].count("approved") == 1


def test_a_second_reviewer_cannot_change_a_reply_that_was_already_sent() -> None:
    """Two reviewers have the same draft open. The first to approve wins; the second is told."""
    store = _store_with_draft()
    rita, omar = _client(store), _client(store)
    rita_csrf, omar_csrf = _sign_in(rita, "Rita"), _sign_in(omar, "Omar")
    assert (
        rita.post("/messages/m1/approve", data={"text": DRAFT, "csrf": rita_csrf}).status_code
        == 200
    )

    late = omar.post("/messages/m1/approve", data={"text": EDITED, "csrf": omar_csrf})
    assert late.status_code == 409
    [entry] = store.outbox()
    assert entry.text == DRAFT
    draft = store.draft("m1")
    assert draft is not None
    assert draft.text == DRAFT  # the record of what was sent is not overwritten
    assert "Omar" not in [e.actor for e in store.audit_trail()]


def test_a_sent_reply_cannot_be_rejected_afterwards() -> None:
    store = _store_with_draft()
    client = _client(store)
    csrf = _sign_in(client, "Rita")
    client.post("/messages/m1/approve", data={"text": DRAFT, "csrf": csrf})
    assert client.post("/messages/m1/reject", data={"csrf": csrf}).status_code == 409
    decision = store.latest_decision("m1")
    assert decision is not None
    assert decision.approved


def test_a_rejected_draft_can_be_edited_and_approved_later() -> None:
    store = _store_with_draft()
    client = _client(store)
    csrf = _sign_in(client, "Rita")
    assert client.post("/messages/m1/reject", data={"csrf": csrf}).status_code == 200
    assert store.outbox() == []
    assert (
        client.post("/messages/m1/approve", data={"text": EDITED, "csrf": csrf}).status_code == 200
    )
    [entry] = store.outbox()
    assert entry.text == EDITED


def test_an_absurdly_long_reply_is_refused() -> None:
    store = _store_with_draft()
    client = _client(store)
    csrf = _sign_in(client, "Rita")
    response = client.post(
        "/messages/m1/approve", data={"text": "x" * (MAX_REPLY_CHARS + 1), "csrf": csrf}
    )
    assert response.status_code == 422
    assert store.outbox() == []


def test_windows_line_endings_in_an_edit_do_not_count_as_a_change() -> None:
    store = _store_with_draft()
    client = _client(store)
    csrf = _sign_in(client, "Rita")
    client.post("/messages/m1/approve", data={"text": DRAFT.replace("\n", "\r\n"), "csrf": csrf})
    draft = store.draft("m1")
    assert draft is not None
    assert draft.origin == "agent"  # unchanged text stays the agent's draft
    assert store.outbox()[0].text == DRAFT


@pytest.mark.parametrize("path", ["/messages/nope/approve", "/messages/nope/reject"])
def test_an_unknown_message_id_is_a_404(path: str) -> None:
    client = _client(_store_with_draft())
    csrf = _sign_in(client, "Rita")
    assert client.post(path, data={"text": DRAFT, "csrf": csrf}).status_code == 404


def test_markup_in_every_candidate_field_is_shown_as_text() -> None:
    hostile = '"><script>alert(1)</script><img src=x onerror=alert(2)>'
    client = _client(_store_with_draft(body=hostile, name=hostile, subject=hostile))
    _sign_in(client, "Rita")
    page = client.get("/").text
    assert "<script>alert(1)" not in page
    assert "<img src=x" not in page
    assert "&lt;script&gt;" in page
    assert "<script>alert(1)" not in client.get("/audit").text


def test_a_reviewer_name_with_markup_is_shown_as_text() -> None:
    store = _store_with_draft()
    client = _client(store)
    csrf = _sign_in(client, "<b>Rita</b>")
    client.post("/messages/m1/approve", data={"text": DRAFT, "csrf": csrf})
    assert "<b>Rita</b>" not in client.get("/audit").text


def test_a_blank_reviewer_name_cannot_sign_in() -> None:
    client = _client(_store_with_draft())
    page = client.get("/login").text
    found = re.search(r'name="csrf" value="([^"]+)"', page)
    assert found is not None
    response = client.post("/login", data={"name": "   ", "csrf": found.group(1)})
    assert response.status_code in {400, 401, 422}
    assert client.get("/", follow_redirects=False).status_code in {303, 307, 401}


def test_good_is_a_draft_the_checks_accept() -> None:
    assert GOOD.endswith(SIGN_OFF)


def test_a_refused_action_is_explained_on_a_page_not_in_raw_json() -> None:
    """A reviewer on a stale page sees what happened and a way back, with the right status."""
    store = _store_with_draft()
    rita, omar = _client(store), _client(store)
    rita_csrf, omar_csrf = _sign_in(rita, "Rita"), _sign_in(omar, "Omar")
    rita.post("/messages/m1/approve", data={"text": DRAFT, "csrf": rita_csrf})
    late = omar.post("/messages/m1/approve", data={"text": EDITED, "csrf": omar_csrf})
    assert late.status_code == 409
    assert late.headers["content-type"].startswith("text/html")
    assert "already sent" in late.text
    assert 'href="/"' in late.text
    assert late.headers["content-security-policy"].startswith("default-src 'none'")


# -- messages too long to handle automatically ---------------------------------------


def test_a_message_at_the_length_limit_is_processed_and_one_over_goes_to_a_person() -> None:
    from inbox_helper.pipeline import MAX_MESSAGE_CHARS

    subject = "Hello"
    at_limit = _message("m1", subject=subject, body="x" * (MAX_MESSAGE_CHARS - len(subject)))
    over = _message("m2", subject=subject, body="x" * (MAX_MESSAGE_CHARS - len(subject) + 1))
    store, _ = _process(ScriptedTeam(fail_on="m2"), at_limit, over)
    assert store.draft("m1") is not None
    triage = store.triage("m2")
    assert triage is not None
    assert triage.action is Action.ESCALATE
    assert "too long" in triage.reason


def test_the_hosted_client_applies_the_same_two_checks_before_calling_the_agent() -> None:
    from inbox_helper.hosted import process_inbox_hosted
    from inbox_helper.pipeline import MAX_MESSAGE_CHARS
    from inbox_helper.service import Reply

    class NeverCalled:
        async def propose(self, _message: Message) -> Reply:
            raise AssertionError("the agent must not be called for these messages")

    store = Store(":memory:")
    messages = [
        _message("m1", subject="", body="  "),
        _message("m2", body="x" * (MAX_MESSAGE_CHARS + 1)),
    ]
    outcomes = asyncio.run(process_inbox_hosted(store, NeverCalled(), messages))
    assert [o.error for o in outcomes] == [None, None]
    for message_id in ("m1", "m2"):
        triage = store.triage(message_id)
        assert triage is not None
        assert triage.action is Action.ESCALATE
