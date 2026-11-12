"""What is shipped to the hosted agent, and what is deliberately left out."""

from __future__ import annotations

import ast
import hashlib
import io
import stat
import zipfile

from package import NOT_IN_AGENT, agent_files, build_zip


def test_the_agent_ships_without_any_code_that_can_send() -> None:
    files = agent_files()
    assert "inbox_helper/dispatch.py" not in files
    assert "inbox_helper/desk.py" not in files
    for name, content in files.items():
        if name.endswith(".py"):
            assert b"INSERT INTO outbox" not in content, name


def test_nothing_shipped_imports_something_left_behind() -> None:
    left_behind = {f"inbox_helper.{name.removesuffix('.py')}" for name in NOT_IN_AGENT}
    for name, content in agent_files().items():
        if not name.endswith(".py"):
            continue
        for node in ast.walk(ast.parse(content)):
            if isinstance(node, ast.ImportFrom):
                assert node.module not in left_behind, f"{name} imports {node.module}"
            if isinstance(node, ast.Import):
                assert not {alias.name for alias in node.names} & left_behind, name


def test_dependencies_are_pinned_and_include_the_agent_server() -> None:
    lines = agent_files()["requirements.txt"].decode().splitlines()
    assert all("==" in line for line in lines)
    assert any(line.startswith("azure-ai-agentserver-responses==") for line in lines)
    assert any(line.startswith("openai-agents==") for line in lines)


def test_the_zip_is_reproducible() -> None:
    assert hashlib.sha256(build_zip()).digest() == hashlib.sha256(build_zip()).digest()


def test_every_zip_entry_is_marked_as_a_regular_readable_file() -> None:
    """Foundry's builder ignores entries without file-type bits: two deployments failed on it."""
    with zipfile.ZipFile(io.BytesIO(build_zip())) as archive:
        assert {"main.py", "requirements.txt"} <= set(archive.namelist())
        for entry in archive.infolist():
            mode = entry.external_attr >> 16
            assert stat.S_ISREG(mode), entry.filename
            assert mode & 0o444 == 0o444, entry.filename
