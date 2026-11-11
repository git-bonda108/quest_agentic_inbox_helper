"""Evaluation gate: the recorded run on the labelled inbox must meet the targets in intent.md.

Runs offline against RECORDED model outputs, so CI needs no credentials. It proves the
pipeline still turns those outputs into the right decisions; it does not re-test the models.
"""

from __future__ import annotations

import asyncio

from inbox_helper.checks import MAX_WORDS
from inbox_helper.cli import DEFAULT_INBOX, DEFAULT_LABELS, DEFAULT_RECORDING
from inbox_helper.evaluate import Report, evaluate, load_labels, load_messages
from inbox_helper.pipeline import process_inbox
from inbox_helper.recording import RecordedTeam
from inbox_helper.store import Store

INTENT_ACCURACY_TARGET = 0.90


def _recorded_report() -> tuple[Report, Store]:
    store = Store(":memory:")
    team = RecordedTeam(DEFAULT_RECORDING)
    outcomes = asyncio.run(process_inbox(store, team, load_messages(DEFAULT_INBOX)))
    return evaluate(store, outcomes, load_labels(DEFAULT_LABELS)), store


def test_recorded_run_meets_the_targets() -> None:
    report, store = _recorded_report()
    assert report.failures == []
    assert report.escalations_drafted == []
    assert report.intent_accuracy >= INTENT_ACCURACY_TARGET
    assert report.longest_draft_words <= MAX_WORDS
    assert store.outbox() == []  # processing an inbox never sends anything


def test_labels_cover_every_message_exactly_once() -> None:
    messages = load_messages(DEFAULT_INBOX)
    labels = load_labels(DEFAULT_LABELS)
    assert sorted(m.id for m in messages) == sorted(labels)
