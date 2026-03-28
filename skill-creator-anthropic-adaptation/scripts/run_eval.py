#!/usr/bin/env python3
"""Run trigger evaluation for a skill description.

Tests whether a skill's description causes the AI agent to trigger
(read the skill) for a set of queries. Outputs results as JSON.

Supports both Claude Code (`claude`) and OpenCode (`opencode`) CLIs.
"""

import argparse
import json
import os
import select
import subprocess
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from scripts.cli_adapter import (
    CLITypes,
    check_skill_triggered,
    detect_cli,
    get_clean_env,
    get_cli_command,
    get_text_content,
    parse_step_finish,
    parse_tool_use_event,
)
from scripts.utils import parse_skill_md


def find_project_root() -> Path:
    """Find the project root by walking up from cwd looking for .claude/
    or other sources like .agent/ or .opencode/.
    """
    current = Path.cwd()
    agent_possible_folders = [
        ".claude",
        ".opencode",
        ".agent",
        ".agents",
        ".gemini",
        ".codex",
        ".cursor",
        ".vscode",
    ]
    for parent in [current, *current.parents]:
        for folder in agent_possible_folders:
            if (parent / folder).is_dir():
                return parent
    return current


def get_commands_dir(cli: CLITypes, project_root: Path) -> Path:
    """Get the commands directory for the given CLI."""
    if cli == "claude":
        return project_root / ".claude" / "commands"
    elif cli == "opencode":
        # OpenCode uses .opencode/commands/ for command files
        return project_root / ".opencode" / "commands"
    return project_root / ".claude" / "commands"


def run_single_query(
    query: str,
    skill_name: str,
    skill_description: str,
    timeout: int,
    project_root: str,
    cli: CLITypes,
    model: str | None = None,
) -> bool:
    """Run a single query and return whether the skill was triggered.

    Creates a command file so it appears in the agent's available_skills
    list, then runs the CLI with the query. Parses JSON stream events to
    detect if the skill was triggered.
    """
    unique_id = uuid.uuid4().hex[:8]
    clean_name = f"{skill_name}-skill-{unique_id}"
    commands_dir = get_commands_dir(cli, Path(project_root))
    command_file = commands_dir / f"{clean_name}.md"

    try:
        commands_dir.mkdir(parents=True, exist_ok=True)
        # Use YAML block scalar to avoid breaking on quotes in description
        indented_desc = "\n  ".join(skill_description.split("\n"))
        command_content = (
            f"---\n"
            f"description: |\n"
            f"  {indented_desc}\n"
            f"---\n\n"
            f"# {skill_name}\n\n"
            f"This skill handles: {skill_description}\n"
        )
        command_file.write_text(command_content)

        cmd = get_cli_command(cli, mode="json", model=model)
        cmd.append(query)

        # Add --verbose for Claude Code (helps with partial messages)
        if cli == "claude":
            cmd.append("--verbose")

        env = get_clean_env(cli)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            cwd=project_root,
            env=env,
        )

        triggered = False
        start_time = time.time()
        buffer = ""
        # Track state for stream event detection
        pending_tool_name = None
        accumulated_json = ""

        try:
            while time.time() - start_time < timeout:
                if process.poll() is not None:
                    remaining = process.stdout.read()
                    if remaining:
                        buffer += remaining.decode("utf-8", errors="replace")
                    break

                ready, _, _ = select.select([process.stdout], [], [], 1.0)
                if not ready:
                    continue

                chunk = os.read(process.stdout.fileno(), 8192)
                if not chunk:
                    break
                buffer += chunk.decode("utf-8", errors="replace")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # Use the adapter to parse tool use events
                    tool_info = parse_tool_use_event(cli, event)

                    if tool_info:
                        tool_name = tool_info.get("tool_name")
                        tool_input = tool_info.get("tool_input", {})
                        partial_json = tool_info.get("partial_json")

                        # Check if skill was triggered
                        if check_skill_triggered(
                            cli, tool_name, tool_input, partial_json, clean_name
                        ):
                            return True

                        # For Claude Code streaming: track pending tool
                        if cli == "claude" and tool_name in ("Skill", "Read"):
                            pending_tool_name = tool_name
                            accumulated_json = partial_json or ""
                        elif cli == "claude" and partial_json:
                            accumulated_json += partial_json
                            if clean_name in accumulated_json:
                                return True

                        # For OpenCode: check directly
                        if cli == "opencode" and tool_name == "skill":
                            input_name = tool_input.get("name", "")
                            if input_name == clean_name:
                                return True

                        # For OpenCode: also check Read tool for skill files
                        if cli == "opencode" and tool_name == "read":
                            file_path = tool_input.get("filePath", "")
                            if clean_name in file_path:
                                return True

                    # Handle step_finish (end of turn)
                    finish_info = parse_step_finish(cli, event)
                    if finish_info:
                        # If we had a pending tool with accumulated JSON, check it
                        if pending_tool_name and clean_name in accumulated_json:
                            return True
                        # Otherwise, the turn ended without triggering
                        return triggered

                    # Claude Code specific: content_block_stop
                    if cli == "claude" and event.get("type") == "stream_event":
                        se = event.get("event", {})
                        if se.get("type") in ("content_block_stop", "message_stop"):
                            if pending_tool_name and clean_name in accumulated_json:
                                return True
                            if se.get("type") == "message_stop":
                                return False

        finally:
            # Clean up process on any exit path
            if process.poll() is None:
                process.kill()
                process.wait()

        return triggered
    finally:
        if command_file.exists():
            command_file.unlink()


def run_eval(
    eval_set: list[dict],
    skill_name: str,
    description: str,
    num_workers: int,
    timeout: int,
    project_root: Path,
    cli: CLITypes,
    runs_per_query: int = 1,
    trigger_threshold: float = 0.5,
    model: str | None = None,
) -> dict:
    """Run the full eval set and return results."""
    results = []

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_info = {}
        for item in eval_set:
            for run_idx in range(runs_per_query):
                future = executor.submit(
                    run_single_query,
                    item["query"],
                    skill_name,
                    description,
                    timeout,
                    str(project_root),
                    cli,
                    model,
                )
                future_to_info[future] = (item, run_idx)

        query_triggers: dict[str, list[bool]] = {}
        query_items: dict[str, dict] = {}
        for future in as_completed(future_to_info):
            item, _ = future_to_info[future]
            query = item["query"]
            query_items[query] = item
            if query not in query_triggers:
                query_triggers[query] = []
            try:
                query_triggers[query].append(future.result())
            except Exception as e:
                print(f"Warning: query failed: {e}", file=sys.stderr)
                query_triggers[query].append(False)

    for query, triggers in query_triggers.items():
        item = query_items[query]
        trigger_rate = sum(triggers) / len(triggers)
        should_trigger = item["should_trigger"]
        if should_trigger:
            did_pass = trigger_rate >= trigger_threshold
        else:
            did_pass = trigger_rate < trigger_threshold
        results.append(
            {
                "query": query,
                "should_trigger": should_trigger,
                "trigger_rate": trigger_rate,
                "triggers": sum(triggers),
                "runs": len(triggers),
                "pass": did_pass,
            }
        )

    passed = sum(1 for r in results if r["pass"])
    total = len(results)

    return {
        "skill_name": skill_name,
        "description": description,
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run trigger evaluation for a skill description"
    )
    parser.add_argument("--eval-set", required=True, help="Path to eval set JSON file")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument(
        "--description", default=None, help="Override description to test"
    )
    parser.add_argument(
        "--num-workers", type=int, default=10, help="Number of parallel workers"
    )
    parser.add_argument(
        "--timeout", type=int, default=30, help="Timeout per query in seconds"
    )
    parser.add_argument(
        "--runs-per-query", type=int, default=3, help="Number of runs per query"
    )
    parser.add_argument(
        "--trigger-threshold", type=float, default=0.5, help="Trigger rate threshold"
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model to use (default: user's configured model)",
    )
    parser.add_argument(
        "--cli",
        choices=["claude", "opencode", "auto"],
        default="auto",
        help="CLI to use (default: auto-detect)",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print progress to stderr"
    )
    args = parser.parse_args()

    # Detect or use specified CLI
    if args.cli == "auto":
        cli = detect_cli()
        if cli is None:
            print("Error: No supported CLI found (claude or opencode)", file=sys.stderr)
            sys.exit(1)
    else:
        cli = args.cli

    eval_set = json.loads(Path(args.eval_set).read_text())
    skill_path = Path(args.skill_path)

    if not (skill_path / "SKILL.md").exists():
        print(f"Error: No SKILL.md found at {skill_path}", file=sys.stderr)
        sys.exit(1)

    name, original_description, content = parse_skill_md(skill_path)
    description = args.description or original_description
    project_root = find_project_root()

    if args.verbose:
        print(f"Using CLI: {cli}", file=sys.stderr)
        print(f"Evaluating: {description}", file=sys.stderr)

    output = run_eval(
        eval_set=eval_set,
        skill_name=name,
        description=description,
        num_workers=args.num_workers,
        timeout=args.timeout,
        project_root=project_root,
        cli=cli,
        runs_per_query=args.runs_per_query,
        trigger_threshold=args.trigger_threshold,
        model=args.model,
    )

    if args.verbose:
        summary = output["summary"]
        print(
            f"Results: {summary['passed']}/{summary['total']} passed", file=sys.stderr
        )
        for r in output["results"]:
            status = "PASS" if r["pass"] else "FAIL"
            rate_str = f"{r['triggers']}/{r['runs']}"
            print(
                f"  [{status}] rate={rate_str} expected={r['should_trigger']}: {r['query'][:70]}",
                file=sys.stderr,
            )

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
