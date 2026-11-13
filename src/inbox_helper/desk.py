"""The review desk: a small web app where a person approves, edits or rejects drafts.

The reviewer's identity comes from the signed session, never from a form field.
Message text is hostile input: templates escape it and pages allow no scripts.
"""

from __future__ import annotations

import hmac
import secrets
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from inbox_helper.dispatch import NotApprovedError, send
from inbox_helper.models import Action, Intent
from inbox_helper.store import DraftNotAllowedError, Store, UnknownMessageError

WEB = Path(__file__).parent / "web"
MAX_NAME = 40
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'self'; form-action 'self'; "
        "base-uri 'none'; frame-ancestors 'none'"
    ),
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}


# A reply is 90 words. This cap only stops a browser from posting megabytes.
MAX_REPLY_CHARS = 5_000


def _label(intent: Intent) -> str:
    return intent.value.replace("_", " ").capitalize()


def _desk_view(store: Store) -> dict[str, Any]:
    sent = {entry.message_id: entry for entry in store.outbox()}
    groups: dict[Intent, list[dict[str, Any]]] = {}
    escalated, ignored, rejected, done, failed = [], [], [], [], []
    for message in store.messages():
        triage = store.triage(message.id)
        row: dict[str, Any] = {"message": message, "triage": triage}
        if triage is None:
            failed.append(row)
        elif message.id in sent:
            done.append(row | {"entry": sent[message.id]})
        elif triage.action is Action.ESCALATE:
            escalated.append(row)
        elif triage.action is Action.IGNORE:
            ignored.append(row)
        else:
            decision = store.latest_decision(message.id)
            row |= {"draft": store.draft(message.id), "decision": decision}
            if decision is not None and not decision.approved:
                rejected.append(row)
            else:
                groups.setdefault(triage.intent, []).append(row)
    ordered = [(_label(intent), groups[intent]) for intent in Intent if intent in groups]
    return {
        "groups": ordered,
        "waiting": sum(len(rows) for _, rows in ordered),
        "escalated": escalated,
        "ignored": ignored,
        "rejected": rejected,
        "sent": done,
        "failed": failed,
    }


def create_app(
    store: Store,
    *,
    passcode: str | None,
    session_secret: str,
    source: str,
    https_only: bool = True,
) -> FastAPI:
    app = FastAPI(title="Inbox helper review desk", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        SessionMiddleware, secret_key=session_secret, https_only=https_only, same_site="lax"
    )
    app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")
    templates = Jinja2Templates(directory=WEB / "templates")

    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    def csrf_token(request: Request) -> str:
        token = request.session.get("csrf")
        if not isinstance(token, str):
            token = secrets.token_urlsafe(32)
            request.session["csrf"] = token
        return token

    def check_csrf(request: Request, submitted: str) -> None:
        expected = request.session.get("csrf")
        if not isinstance(expected, str) or not hmac.compare_digest(expected, submitted):
            raise HTTPException(403, "This form has expired. Reload the page and try again.")

    def reviewer_of(request: Request) -> str:
        reviewer = request.session.get("reviewer")
        if not isinstance(reviewer, str) or not reviewer:
            raise HTTPException(401, "Sign in to review drafts.")
        return reviewer

    def page(request: Request, name: str, status: int = 200, **context: Any) -> Response:
        context |= {
            "csrf": csrf_token(request),
            "reviewer": request.session.get("reviewer"),
            "source": source,
            "passcode_required": passcode is not None,
        }
        return templates.TemplateResponse(request, name, context, status_code=status)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/login")
    async def login_form(request: Request) -> Response:
        return page(request, "login.html", error=None)

    @app.post("/login")
    async def login(
        request: Request,
        name: Annotated[str, Form()] = "",
        passcode_given: Annotated[str, Form(alias="passcode")] = "",
        csrf: Annotated[str, Form()] = "",
    ) -> Response:
        check_csrf(request, csrf)
        name = " ".join(name.split())[:MAX_NAME]
        if passcode is not None and not hmac.compare_digest(
            passcode.encode(), passcode_given.encode()
        ):
            return page(request, "login.html", status=401, error="That passcode is not right.")
        if not name:
            return page(request, "login.html", status=422, error="Enter your name.")
        request.session.clear()
        request.session["reviewer"] = name
        return RedirectResponse("/", status_code=303)

    @app.post("/logout")
    async def logout(request: Request, csrf: Annotated[str, Form()] = "") -> Response:
        check_csrf(request, csrf)
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    @app.get("/")
    async def desk(request: Request) -> Response:
        if not request.session.get("reviewer"):
            return RedirectResponse("/login", status_code=303)
        return page(request, "desk.html", **_desk_view(store))

    @app.get("/audit")
    async def audit(request: Request) -> Response:
        reviewer_of(request)
        return page(request, "audit.html", events=store.audit_trail())

    @app.post("/messages/{message_id}/approve")
    async def approve(
        request: Request,
        message_id: str,
        text: Annotated[str, Form()] = "",
        csrf: Annotated[str, Form()] = "",
    ) -> Response:
        reviewer = reviewer_of(request)
        check_csrf(request, csrf)
        text = text.replace("\r\n", "\n").strip()
        try:
            store.message(message_id)  # raises if the id is unknown
            triage = store.triage(message_id)
            if triage is None or triage.action is not Action.DRAFT:
                raise HTTPException(409, "This message is handled by a person, not by a draft.")
            if store.sent(message_id) is not None:
                raise HTTPException(409, "This reply was already sent. Nothing was changed.")
            if not text:
                raise HTTPException(422, "A reply cannot be empty.")
            if len(text) > MAX_REPLY_CHARS:
                raise HTTPException(
                    422, f"A reply cannot be longer than {MAX_REPLY_CHARS} characters."
                )
            current = store.draft(message_id)
            if current is None or current.text != text:
                store.save_draft(message_id, text, origin="reviewer", actor=reviewer)
            store.record_decision(message_id, reviewer=reviewer, approved=True)
            send(store, message_id)
        except UnknownMessageError as error:
            raise HTTPException(404, "No such message.") from error
        except (DraftNotAllowedError, NotApprovedError) as error:
            raise HTTPException(409, str(error)) from error
        return RedirectResponse("/", status_code=303)

    @app.post("/messages/{message_id}/reject")
    async def reject(
        request: Request, message_id: str, csrf: Annotated[str, Form()] = ""
    ) -> Response:
        reviewer = reviewer_of(request)
        check_csrf(request, csrf)
        try:
            store.message(message_id)  # raises if the id is unknown
            if store.sent(message_id) is not None:
                raise HTTPException(409, "This reply was already sent. It cannot be rejected now.")
            store.record_decision(message_id, reviewer=reviewer, approved=False)
        except UnknownMessageError as error:
            raise HTTPException(404, "No such message or draft.") from error
        return RedirectResponse("/", status_code=303)

    return app
