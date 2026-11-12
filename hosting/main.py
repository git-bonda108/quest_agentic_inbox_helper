"""Entry point of the Foundry hosted agent (Responses protocol).

The request input is one candidate message as JSON. The response text is a
proposal as JSON: the group, the reason and, when allowed, a draft. The agent
cannot send anything; a person approves drafts in the review desk.

The agent server exports traces to Application Insights when the platform or
the agent version supplies APPLICATIONINSIGHTS_CONNECTION_STRING.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from azure.ai.agentserver.responses import (
    ResponseContext,
    ResponsesAgentServerHost,
    TextResponse,
)

from inbox_helper.foundry_team import FoundryTeam
from inbox_helper.service import propose

POLICY = (Path(__file__).parent / "hiring_policy.md").read_text(encoding="utf-8")

app = ResponsesAgentServerHost()
_team: FoundryTeam | None = None


def team() -> FoundryTeam:
    """One team per process, created on first use so start-up needs no network."""
    global _team
    if _team is None:
        _team = FoundryTeam(
            os.environ["FOUNDRY_PROJECT_ENDPOINT"],
            os.environ.get("INBOX_HELPER_WORKER_MODEL", "gpt-5.6-luna"),
            os.environ.get("INBOX_HELPER_CRITIC_MODEL", "gpt-5.5"),
            POLICY,
        )
    return _team


@app.response_handler
async def handler(
    request: Any,  # a CreateResponse; the library exposes that name as a runtime alias
    context: ResponseContext,
    _cancellation_signal: asyncio.Event,
) -> TextResponse:
    text = await context.get_input_text() or ""
    return TextResponse(context, request, text=await propose(text, team()))


if __name__ == "__main__":
    app.run()
