#!/usr/bin/env python3
"""
CLI Adapter - Abstraction layer for different AI coding agent CLIs.

Supports both Claude Code (`claude`) and OpenCode (`opencode`) CLIs,
providing a unified interface for running prompts and parsing JSON output.

Usage:
    from scripts.cli_adapter import detect_cli, get_cli_command, parse_tool_use

    cli = detect_cli()
    cmd = get_cli_command(cli, mode="json", model="claude-sonnet-4")
    # Run subprocess, then parse events...
"""

import os
import shutil
from typing import Literal


CLITypes = Literal["claude", "opencode"]


def detect_cli() -> CLITypes | None:
    """
    Detect which CLI is available in the system.

    Returns:
        "claude" if Claude Code CLI is found
        "opencode" if OpenCode CLI is found
        None if neither is found
    """
    if shutil.which("claude"):
        return "claude"
    elif shutil.which("opencode"):
        return "opencode"
    return None


def get_cli_command(
    cli: CLITypes,
    mode: Literal["json", "text"],
    model: str | None = None,
) -> list[str]:
    """
    Build the base CLI command for the given mode.

    Args:
        cli: The CLI type ("claude" or "opencode")
        mode: Output mode - "json" for structured events, "text" for plain text
        model: Optional model identifier

    Returns:
        List of command arguments ready for subprocess

    Example:
        >>> get_cli_command("claude", "json")
        ["claude", "-p", "--output-format", "stream-json", "--include-partial-messages"]

        >>> get_cli_command("opencode", "json", model="anthropic/claude-sonnet-4")
        ["opencode", "run", "--format", "json", "--model", "anthropic/claude-sonnet-4"]
    """
    if cli == "claude":
        cmd = ["claude", "-p"]
        if mode == "json":
            cmd.extend(["--output-format", "stream-json", "--include-partial-messages"])
        else:
            cmd.extend(["--output-format", "text"])
    elif cli == "opencode":
        cmd = ["opencode", "run"]
        if mode == "json":
            cmd.extend(["--format", "json"])
        # text is default for opencode, no flag needed
    else:
        raise ValueError(f"Unsupported CLI: {cli}")

    if model:
        cmd.extend(["--model", model])

    return cmd


def get_clean_env(cli: CLITypes) -> dict:
    """
    Return a clean environment dict for running the CLI subprocess.

    Removes CLI-specific variables that prevent nesting.

    Args:
        cli: The CLI type

    Returns:
        Copy of os.environ with nesting-prevention vars removed
    """
    env = dict(os.environ)

    if cli == "claude":
        # Claude Code uses CLAUDECODE to prevent nesting
        env.pop("CLAUDECODE", None)
    elif cli == "opencode":
        # OpenCode doesn't document a similar variable, but remove if exists
        env.pop("OPENCODE", None)

    return env


def parse_tool_use_event(cli: CLITypes, event: dict) -> dict | None:
    """
    Parse a JSON event and extract tool use information if present.

    This normalizes the different event formats between CLIs into a common structure.

    Args:
        cli: The CLI type
        event: Parsed JSON event dict

    Returns:
        dict with keys:
            - "tool_name": str - Name of the tool (e.g., "skill", "read", "bash")
            - "tool_input": dict - Input arguments to the tool
            - "partial_json": str | None - Accumulated JSON for streaming (OpenCode)
            - "status": str | None - "completed" or "error" (OpenCode only)
        Or None if the event is not a tool use event.

    Example:
        # Claude Code event
        >>> parse_tool_use_event("claude", {"type": "stream_event", "event": {
        ...     "type": "content_block_start",
        ...     "content_block": {"type": "tool_use", "name": "Skill", "input": {}}
        ... }})
        {"tool_name": "Skill", "tool_input": {}, "partial_json": None, "status": None}

        # OpenCode event
        >>> parse_tool_use_event("opencode", {"type": "tool_use", "part": {
        ...     "tool": "skill",
        ...     "state": {"input": {"name": "my-skill"}, "status": "completed"}
        ... }})
        {"tool_name": "skill", "tool_input": {"name": "my-skill"}, "partial_json": None, "status": "completed"}
    """
    if cli == "claude":
        return _parse_claude_tool_use(event)
    elif cli == "opencode":
        return _parse_opencode_tool_use(event)
    return None


def _parse_claude_tool_use(event: dict) -> dict | None:
    """Parse Claude Code stream event for tool use."""
    event_type = event.get("type")

    # Stream event with content_block_start
    if event_type == "stream_event":
        se = event.get("event", {})
        se_type = se.get("type")

        if se_type == "content_block_start":
            cb = se.get("content_block", {})
            if cb.get("type") == "tool_use":
                return {
                    "tool_name": cb.get("name", ""),
                    "tool_input": cb.get("input", {}),
                    "partial_json": "",
                    "status": None,
                }

        elif se_type == "content_block_delta":
            delta = se.get("delta", {})
            if delta.get("type") == "input_json_delta":
                return {
                    "tool_name": None,  # Already known from content_block_start
                    "tool_input": {},
                    "partial_json": delta.get("partial_json", ""),
                    "status": None,
                }

    # Full assistant message (fallback)
    elif event_type == "assistant":
        message = event.get("message", {})
        for content_item in message.get("content", []):
            if content_item.get("type") == "tool_use":
                return {
                    "tool_name": content_item.get("name", ""),
                    "tool_input": content_item.get("input", {}),
                    "partial_json": None,
                    "status": None,
                }

    return None


def _parse_opencode_tool_use(event: dict) -> dict | None:
    """Parse OpenCode stream event for tool use."""
    event_type = event.get("type")

    if event_type == "tool_use":
        part = event.get("part", {})
        tool_name = part.get("tool", "")
        state = part.get("state", {})

        return {
            "tool_name": tool_name,
            "tool_input": state.get("input", {}),
            "partial_json": None,
            "status": state.get("status"),
        }

    return None


def parse_step_finish(cli: CLITypes, event: dict) -> dict | None:
    """
    Parse a step_finish event and extract token/usage information.

    Args:
        cli: The CLI type
        event: Parsed JSON event dict

    Returns:
        dict with keys:
            - "total_tokens": int | None
            - "input_tokens": int | None
            - "output_tokens": int | None
            - "reason": str | None - "stop", "tool-calls", etc.
        Or None if not a step_finish event.
    """
    if cli == "claude":
        # Claude Code uses "result" type
        if event.get("type") == "result":
            result = event.get("result", {})
            usage = result.get("usage", {})
            return {
                "total_tokens": usage.get("total_tokens"),
                "input_tokens": usage.get("input_tokens"),
                "output_tokens": usage.get("output_tokens"),
                "reason": "stop",
            }
        return None

    elif cli == "opencode":
        # OpenCode uses "step_finish" type
        if event.get("type") == "step_finish":
            part = event.get("part", {})
            tokens = part.get("tokens", {})
            return {
                "total_tokens": tokens.get("total"),
                "input_tokens": tokens.get("input"),
                "output_tokens": tokens.get("output"),
                "reason": part.get("reason"),
            }
        return None

    return None


def check_skill_triggered(
    cli: CLITypes,
    tool_name: str | None,
    tool_input: dict,
    partial_json: str | None,
    skill_name: str,
) -> bool:
    """
    Check if a skill with the given name was triggered.

    Args:
        cli: The CLI type
        tool_name: Name of the tool being used
        tool_input: Input arguments to the tool
        partial_json: Accumulated JSON string (for streaming detection)
        skill_name: Name of the skill to check for

    Returns:
        True if the skill was triggered, False otherwise
    """
    if cli == "claude":
        # Claude Code: tool_name is "Skill" or "Read", skill name in input
        if tool_name in ("Skill", "Read"):
            if tool_input:
                skill_value = tool_input.get("skill", "") or tool_input.get(
                    "file_path", ""
                )
                if skill_name in skill_value:
                    return True
            # Check partial JSON during streaming
            if partial_json and skill_name in partial_json:
                return True

    elif cli == "opencode":
        # OpenCode: tool_name is "skill", skill name in input.name
        if tool_name == "skill":
            input_name = tool_input.get("name", "")
            if input_name == skill_name:
                return True

    return False


def get_text_content(cli: CLITypes, event: dict) -> str | None:
    """
    Extract text content from an event.

    Args:
        cli: The CLI type
        event: Parsed JSON event dict

    Returns:
        Text string if this is a text event, None otherwise.
    """
    if cli == "claude":
        # Claude Code streams text via content_block_delta
        if event.get("type") == "stream_event":
            se = event.get("event", {})
            if se.get("type") == "content_block_delta":
                delta = se.get("delta", {})
                if delta.get("type") == "text_delta":
                    return delta.get("text", "")
        return None

    elif cli == "opencode":
        # OpenCode uses "text" type
        if event.get("type") == "text":
            part = event.get("part", {})
            return part.get("text", "")
        return None

    return None
