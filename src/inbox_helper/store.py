"""SQLite store for messages, triage, drafts, reviewer decisions and the audit trail.

The store never writes to the outbox. Only `dispatch.send` does.
"""

from __future__ import annotations

import hashlib
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Literal

from inbox_helper.models import (
    Action,
    AuditEvent,
    Decision,
    Draft,
    Message,
    OutboxEntry,
    Triage,
)

SYSTEM_ACTOR = "system"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS triage (
    message_id TEXT PRIMARY KEY REFERENCES messages(id),
    payload TEXT NOT NULL,
    action TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
    message_id TEXT PRIMARY KEY REFERENCES messages(id),
    text TEXT NOT NULL,
    origin TEXT NOT NULL CHECK (origin IN ('agent', 'reviewer')),
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id TEXT NOT NULL REFERENCES messages(id),
    reviewer TEXT NOT NULL,
    approved INTEGER NOT NULL CHECK (approved IN (0, 1)),
    text_sha256 TEXT NOT NULL,
    decided_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS outbox (
    message_id TEXT PRIMARY KEY REFERENCES messages(id),
    to_email TEXT NOT NULL,
    text TEXT NOT NULL,
    text_sha256 TEXT NOT NULL,
    decision_id INTEGER NOT NULL REFERENCES decisions(id),
    sent_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT NOT NULL,
    actor TEXT NOT NULL,
    event TEXT NOT NULL,
    message_id TEXT,
    detail TEXT NOT NULL
);
"""


class UnknownMessageError(LookupError):
    """The message id is not in the store."""


class DraftNotAllowedError(PermissionError):
    """The message is not routed to drafting, so it may not hold a draft."""


def text_hash(text: str) -> str:
    """Hash that ties a reviewer's decision to one exact text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc_now() -> datetime:
    return datetime.now(UTC)


class Store:
    def __init__(self, path: str) -> None:
        self._db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(_SCHEMA)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Run several statements atomically. Rolls back on any error."""
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield self._db
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        else:
            self._db.execute("COMMIT")

    # -- writes ---------------------------------------------------------------

    def add_message(self, message: Message) -> None:
        with self.transaction() as db:
            db.execute(
                "INSERT INTO messages (id, payload) VALUES (?, ?)",
                (message.id, message.model_dump_json()),
            )
            self.log(db, SYSTEM_ACTOR, "message_added", message.id)

    def save_triage(self, triage: Triage) -> None:
        with self.transaction() as db:
            self._require_message(db, triage.message_id)
            db.execute(
                "INSERT OR REPLACE INTO triage (message_id, payload, action) VALUES (?, ?, ?)",
                (triage.message_id, triage.model_dump_json(), triage.action.value),
            )
            self.log(
                db,
                SYSTEM_ACTOR,
                "triaged",
                triage.message_id,
                f"{triage.intent.value} -> {triage.action.value}",
            )

    def save_draft(
        self,
        message_id: str,
        text: str,
        *,
        origin: Literal["agent", "reviewer"] = "agent",
        actor: str = SYSTEM_ACTOR,
    ) -> Draft:
        """Store the current draft. Refused unless the message is routed to drafting."""
        draft = Draft(message_id=message_id, text=text, origin=origin, updated_at=utc_now())
        with self.transaction() as db:
            self._require_message(db, message_id)
            row = db.execute(
                "SELECT action FROM triage WHERE message_id = ?", (message_id,)
            ).fetchone()
            if row is None or row["action"] != Action.DRAFT.value:
                routed = "not triaged" if row is None else f"routed to {row['action']}"
                raise DraftNotAllowedError(f"{message_id} may not hold a draft: {routed}")
            db.execute(
                "INSERT OR REPLACE INTO drafts (message_id, text, origin, updated_at) "
                "VALUES (?, ?, ?, ?)",
                (message_id, draft.text, draft.origin, draft.updated_at.isoformat()),
            )
            self.log(db, actor, "draft_saved", message_id, f"{origin} {text_hash(text)[:12]}")
        return draft

    def record_decision(self, message_id: str, *, reviewer: str, approved: bool) -> Decision:
        """Record a reviewer's verdict on the draft text as it stands right now."""
        reviewer = reviewer.strip()
        if not reviewer:
            raise ValueError("a decision needs a named reviewer")
        decided_at = utc_now()
        with self.transaction() as db:
            self._require_message(db, message_id)
            row = db.execute(
                "SELECT text FROM drafts WHERE message_id = ?", (message_id,)
            ).fetchone()
            if row is None:
                raise UnknownMessageError(f"{message_id} has no draft to decide on")
            digest = text_hash(row["text"])
            cursor = db.execute(
                "INSERT INTO decisions (message_id, reviewer, approved, text_sha256, decided_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (message_id, reviewer, int(approved), digest, decided_at.isoformat()),
            )
            decision_id = cursor.lastrowid
            if decision_id is None:  # pragma: no cover - sqlite always sets it on INSERT
                raise RuntimeError("decision was not stored")
            self.log(db, reviewer, "approved" if approved else "rejected", message_id, digest[:12])
        return Decision(
            id=decision_id,
            message_id=message_id,
            reviewer=reviewer,
            approved=approved,
            text_sha256=digest,
            decided_at=decided_at,
        )

    def log(
        self,
        db: sqlite3.Connection,
        actor: str,
        event: str,
        message_id: str | None,
        detail: str = "",
    ) -> None:
        """Append to the audit trail inside the caller's transaction."""
        db.execute(
            "INSERT INTO audit (at, actor, event, message_id, detail) VALUES (?, ?, ?, ?, ?)",
            (utc_now().isoformat(), actor, event, message_id, detail),
        )

    # -- reads ----------------------------------------------------------------

    def messages(self) -> list[Message]:
        rows = self._db.execute("SELECT payload FROM messages ORDER BY id").fetchall()
        return [Message.model_validate_json(row["payload"]) for row in rows]

    def message(self, message_id: str) -> Message:
        row = self._db.execute(
            "SELECT payload FROM messages WHERE id = ?", (message_id,)
        ).fetchone()
        if row is None:
            raise UnknownMessageError(message_id)
        return Message.model_validate_json(row["payload"])

    def triage(self, message_id: str) -> Triage | None:
        row = self._db.execute(
            "SELECT payload FROM triage WHERE message_id = ?", (message_id,)
        ).fetchone()
        return None if row is None else Triage.model_validate_json(row["payload"])

    def draft(self, message_id: str) -> Draft | None:
        row = self._db.execute(
            "SELECT message_id, text, origin, updated_at FROM drafts WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        return None if row is None else Draft.model_validate(dict(row))

    def latest_decision(self, message_id: str) -> Decision | None:
        row = self._db.execute(
            "SELECT id, message_id, reviewer, approved, text_sha256, decided_at FROM decisions "
            "WHERE message_id = ? ORDER BY id DESC LIMIT 1",
            (message_id,),
        ).fetchone()
        return None if row is None else Decision.model_validate(dict(row))

    def outbox(self) -> list[OutboxEntry]:
        rows = self._db.execute(
            "SELECT message_id, to_email, text, text_sha256, decision_id, sent_at "
            "FROM outbox ORDER BY sent_at, message_id"
        ).fetchall()
        return [OutboxEntry.model_validate(dict(row)) for row in rows]

    def audit_trail(self) -> list[AuditEvent]:
        rows = self._db.execute(
            "SELECT id, at, actor, event, message_id, detail FROM audit ORDER BY id"
        ).fetchall()
        return [AuditEvent.model_validate(dict(row)) for row in rows]

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _require_message(db: sqlite3.Connection, message_id: str) -> None:
        if db.execute("SELECT 1 FROM messages WHERE id = ?", (message_id,)).fetchone() is None:
            raise UnknownMessageError(message_id)
