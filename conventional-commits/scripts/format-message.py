#!/usr/bin/env python3
"""
Format a commit message according to Conventional Commits specification.
"""

import sys


def format_commit_message(
    commit_type: str,
    scope: str = "",
    description: str = "",
    body: str = "",
    is_breaking: bool = False,
    issues: list = None,
) -> str:
    """
    Format a Conventional Commits message.

    Args:
        commit_type: Type (feat, fix, docs, style, refactor, perf, test, chore, ci, build)
        scope: Optional scope in parentheses
        description: Short description in imperative mood
        body: Optional detailed body
        is_breaking: Whether this is a breaking change
        issues: List of issue references (e.g., ["fixes #123", "closes #456"])

    Returns:
        Formatted commit message string
    """
    # Validate type
    valid_types = {
        "feat",
        "fix",
        "docs",
        "style",
        "refactor",
        "perf",
        "test",
        "chore",
        "ci",
        "build",
    }
    if commit_type not in valid_types:
        raise ValueError(
            f"Invalid commit type: {commit_type}. Must be one of: {valid_types}"
        )

    # Build header
    header_parts = [commit_type]

    if scope:
        header_parts[0] = f"{commit_type}({scope})"

    if is_breaking:
        header_parts[0] = f"{header_parts[0]}!"

    if not description:
        raise ValueError("Description is required")

    header = f"{header_parts[0]}: {description}"

    # Build message
    message_lines = [header]

    if body:
        message_lines.append("")  # Empty line before body
        message_lines.append(body)

    if issues:
        if body:
            message_lines.append("")  # Empty line before footer
        for issue in issues:
            message_lines.append(issue)

    return "\n".join(message_lines)


def main():
    """Command-line interface."""
    if len(sys.argv) < 4:
        print(
            "Usage: format-message.py <type> <description> [scope] [--breaking] [--issue ISSUE]..."
        )
        print(
            "Example: format-message.py feat 'add login' auth --breaking --issue 'fixes #123'"
        )
        sys.exit(1)

    commit_type = sys.argv[1]
    description = sys.argv[2]
    scope = ""
    is_breaking = False
    issues = []

    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--scope" and i + 1 < len(sys.argv):
            scope = sys.argv[i + 1]
            i += 2
        elif arg == "--breaking":
            is_breaking = True
            i += 1
        elif arg == "--issue" and i + 1 < len(sys.argv):
            issues.append(sys.argv[i + 1])
            i += 2
        else:
            # Assume scope without flag (backward compatibility)
            if not scope and not arg.startswith("--"):
                scope = arg
            i += 1

    try:
        message = format_commit_message(
            commit_type=commit_type,
            scope=scope,
            description=description,
            is_breaking=is_breaking,
            issues=issues,
        )
        print(message)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
