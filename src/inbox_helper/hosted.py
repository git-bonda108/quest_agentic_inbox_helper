"""Use the tool as deployed on Microsoft Foundry: send messages to the hosted agent.

The hosted agent proposes. This side still decides: it re-runs the code checks on
every draft it receives, hands blocked messages to a person, and keeps the store
that the review desk and the send gate work from.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Protocol

from inbox_helper.checks import draft_problems
from inbox_helper.models import Action, Message, Triage
from inbox_helper.pipeline import DEFAULT_CONCURRENCY, Outcome, hand_to_a_person
from inbox_helper.service import Reply
from inbox_helper.store import Store
from inbox_helper.team import InputBlockedError


class Agent(Protocol):
    async def propose(self, message: Message) -> Reply: ...


@dataclass
class FoundryAgent:
    """The hosted agent's Responses endpoint, signed in by identity."""

    endpoint: str
    name: str
    seconds: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
        from openai import AsyncOpenAI

        self._credential = DefaultAzureCredential()
        self._client = AsyncOpenAI(
            base_url=f"{self.endpoint.rstrip('/')}/agents/{self.name}/endpoint/protocols/openai",
            api_key=get_bearer_token_provider(self._credential, "https://ai.azure.com/.default"),
            default_query={"api-version": "v1"},
            max_retries=4,
            timeout=180,
        )
        self._session: str | None = None
        self._opening = asyncio.Lock()

    async def aclose(self) -> None:
        await self._client.close()
        await self._credential.close()

    async def propose(self, message: Message) -> Reply:
        """Send one message. Every call after the first reuses the first call's session.

        Without a session id the platform starts a new sandbox for each request. The
        service keeps nothing between messages, so one sandbox can serve a whole inbox.
        """
        if self._session is None:
            async with self._opening:
                if self._session is None:
                    return await self._call(message)
        return await self._call(message)

    async def _call(self, message: Message) -> Reply:
        from openai import BadRequestError

        body = {"agent_session_id": self._session} if self._session else None
        started = time.perf_counter()
        try:
            raw = await self._client.responses.with_raw_response.create(
                input=message.model_dump_json(), extra_body=body
            )
        except BadRequestError as error:
            if error.code == "content_filter":
                raise InputBlockedError(["content safety policy, at the agent's input"]) from error
            raise
        finally:
            self.seconds.append(round(time.perf_counter() - started, 3))
        self._session = self._session or raw.headers.get("x-agent-session-id")
        return Reply.model_validate_json(raw.parse().output_text)


async def _one(store: Store, agent: Agent, message: Message) -> Outcome:
    try:
        reply = await agent.propose(message)
    except InputBlockedError as blocked:
        return hand_to_a_person(store, message, None, blocked)
    proposal = reply.proposal
    if proposal is None:
        raise RuntimeError(reply.error or "the agent returned neither a proposal nor an error")
    if proposal.message_id != message.id:
        raise RuntimeError(f"the agent answered about {proposal.message_id!r}, not {message.id!r}")

    action, reason, draft = proposal.action, proposal.reason, proposal.draft
    problems = draft_problems(draft) if draft is not None else []
    if action is Action.DRAFT and (draft is None or problems):
        action = Action.ESCALATE
        found = " ".join(problems) or "The agent proposed a draft but sent none."
        reason = f"The agent's draft failed a check on arrival: {found}"
    store.save_triage(
        Triage(
            message_id=message.id,
            intent=proposal.intent,
            action=action,
            confidence=proposal.confidence,
            reason=reason,
        )
    )
    if action is Action.DRAFT and draft is not None:
        store.save_draft(message.id, draft)
    return Outcome(
        message.id,
        proposal.intent,
        action,
        drafted=action is Action.DRAFT,
        blocked=proposal.blocked,
    )


async def process_inbox_hosted(
    store: Store,
    agent: Agent,
    messages: list[Message],
    *,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> list[Outcome]:
    """Process a pile of messages through the hosted agent. One failure never stops the rest."""
    for message in messages:
        store.add_message(message)
    gate = asyncio.Semaphore(concurrency)

    async def guarded(message: Message) -> Outcome:
        async with gate:
            try:
                return await _one(store, agent, message)
            except Exception as error:
                detail = f"{type(error).__name__}: {error}"
                store.record_failure(message.id, detail)
                return Outcome(message.id, None, None, drafted=False, error=detail)

    return list(await asyncio.gather(*(guarded(message) for message in messages)))
