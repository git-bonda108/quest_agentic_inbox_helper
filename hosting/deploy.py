"""Deploy the tool to Microsoft Foundry as a hosted agent, from source.

    uv run --group deploy python hosting/deploy.py

Builds a zip (entry point, the inbox_helper package, the policy, pinned
requirements), uploads it as a new agent version, waits until it is active and
routes the agent's endpoint to it. Signs in by identity; reads no secrets from
the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import sys
import time
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AgentEndpointConfig,
    CodeConfiguration,
    FixedRatioVersionSelectionRule,
    HostedAgentDefinition,
    ProtocolConfiguration,
    ProtocolVersionRecord,
    RaiConfig,
    ResponsesProtocolConfiguration,
    SessionConfiguration,
    VersionSelector,
)
from azure.identity import DefaultAzureCredential

from package import build_zip


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-name", default="inbox-helper")
    parser.add_argument(
        "--idle-seconds", type=int, default=120, help="shortest the platform allows"
    )
    parser.add_argument("--rai-policy", default=os.environ.get("INBOX_HELPER_RAI_POLICY_ID"))
    parser.add_argument("--zip-only", type=Path, help="write the zip here and stop")
    args = parser.parse_args()

    code = build_zip()
    digest = hashlib.sha256(code).hexdigest()
    print(f"zip: {len(code)} bytes, sha256 {digest}")
    if args.zip_only:
        args.zip_only.write_bytes(code)
        return 0

    endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
    environment = {
        "PYTHONNOUSERSITE": "1",
        "FOUNDRY_PROJECT_ENDPOINT": endpoint,
        "INBOX_HELPER_WORKER_MODEL": os.environ.get("INBOX_HELPER_WORKER_MODEL", "gpt-5.6-luna"),
        "INBOX_HELPER_CRITIC_MODEL": os.environ.get("INBOX_HELPER_CRITIC_MODEL", "gpt-5.5"),
    }
    definition = HostedAgentDefinition(
        cpu="0.5",
        memory="1Gi",
        code_configuration=CodeConfiguration(
            runtime="python_3_13",
            entry_point=["python", "main.py"],
            dependency_resolution="remote_build",
        ),
        protocol_versions=[ProtocolVersionRecord(protocol="responses", version="2.0.0")],
        environment_variables=environment,
        session_configuration=SessionConfiguration(idle_timeout_seconds=args.idle_seconds),
        rai_config=RaiConfig(rai_policy_name=args.rai_policy) if args.rai_policy else None,
    )
    print(f"guardrail policy: {args.rai_policy or 'none attached'}")

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project,
    ):
        archive = io.BytesIO(code)
        archive.name = "inbox-helper.zip"  # the SDK requires a stream named *.zip
        created = project.agents.create_version_from_code(
            agent_name=args.agent_name,
            description="Groups candidate messages and drafts replies. Cannot send.",
            definition=definition,
            code=archive,
            code_zip_sha256=digest,
        )
        print(f"created version {created.version}")
        for _ in range(90):
            details = project.agents.get_version(
                agent_name=args.agent_name, agent_version=created.version
            )
            status = details["status"]
            print(f"  status: {status}")
            if status == "active":
                break
            if status == "failed":
                print(f"provisioning failed: {details.get('error')}", file=sys.stderr)
                return 1
            time.sleep(10)
        else:
            print("timed out waiting for the version to become active", file=sys.stderr)
            return 1
        project.agents.update_details(
            agent_name=args.agent_name,
            agent_endpoint=AgentEndpointConfig(
                version_selector=VersionSelector(
                    version_selection_rules=[
                        FixedRatioVersionSelectionRule(
                            agent_version=created.version, traffic_percentage=100
                        )
                    ]
                ),
                protocol_configuration=ProtocolConfiguration(
                    responses=ResponsesProtocolConfiguration()
                ),
            ),
        )
        print(f"endpoint routed to version {created.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
