"""Package the agent's source as a zip for Foundry's remote build. Standard library only."""

from __future__ import annotations

import io
import stat
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "inbox_helper"
# Sending, the review desk, the command line and the scoring code stay with the
# reviewer. The agent is shipped without them, so it has no code that can send.
NOT_IN_AGENT = frozenset(
    {"cli.py", "desk.py", "dispatch.py", "evaluate.py", "hosted.py", "planted.py"}
)


def requirements() -> str:
    """Pinned dependencies, exported from the lock file so the agent matches the tests."""
    command = ["uv", "export", "--no-dev", "--group", "hosted", "--no-hashes", "--no-emit-project"]
    exported = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)  # noqa: S603
    pins = [line for line in exported.stdout.splitlines() if "==" in line and line[0].isalnum()]
    return "\n".join(pins) + "\n"


def agent_files() -> dict[str, bytes]:
    files = {
        "main.py": (ROOT / "hosting" / "main.py").read_bytes(),
        "hiring_policy.md": (ROOT / "data" / "policy" / "hiring_policy.md").read_bytes(),
        "requirements.txt": requirements().encode(),
    }
    for path in sorted(PACKAGE.glob("*.py")):
        if path.name not in NOT_IN_AGENT:
            files[f"inbox_helper/{path.name}"] = path.read_bytes()
    return files


def build_zip() -> bytes:
    """A flat, reproducible zip: the same sources always give the same SHA-256."""
    files = agent_files()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            # Mark each entry as a regular, readable file. Foundry's builder skips
            # entries without the file-type bits and then reports no requirements.txt.
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(entry, files[name])
    return buffer.getvalue()
