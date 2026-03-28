#!/usr/bin/env python3
"""
Analyze git changes to suggest Conventional Commits type and scope.
"""

import subprocess
import sys
import os
import re
from typing import Tuple, Optional, List


def run_git_command(args: List[str], cwd: Optional[str] = None) -> str:
    """Run git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args, cwd=cwd, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {e}", file=sys.stderr)
        return ""


def get_git_status(cwd: Optional[str] = None) -> List[str]:
    """Get list of changed files with status."""
    output = run_git_command(["status", "--porcelain"], cwd)
    if not output:
        return []
    return [line for line in output.split("\n") if line.strip()]


def get_git_diff(cwd: Optional[str] = None) -> str:
    """Get unified diff of changes."""
    return run_git_command(["diff", "--unified=0"], cwd)


def analyze_changes(cwd: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Analyze git changes and suggest commit type and scope.

    Returns:
        Tuple of (suggested_type, suggested_scope)
    """
    status_lines = get_git_status(cwd)
    diff_output = get_git_diff(cwd)

    if not status_lines and not diff_output:
        return ("chore", None)  # Default if no changes detected

    # Collect file patterns and keywords
    files = []
    for line in status_lines:
        # Format: XY filename (X=staged, Y=unstaged)
        if len(line) >= 3:
            files.append(line[3:].strip())

    # Analyze file types
    has_docs = any(
        f.endswith((".md", ".rst", ".txt")) or "README" in f or "docs/" in f
        for f in files
    )
    has_tests = any(
        re.search(r"\.(test|spec)\.[a-z]+$", f) or "__tests__" in f or "test/" in f
        for f in files
    )
    has_config = any(
        f.endswith((".json", ".yaml", ".yml", ".toml", ".config"))
        or f
        in (
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "webpack.config.js",
            "tsconfig.json",
        )
        for f in files
    )
    has_build = any(
        f.endswith((".js", ".ts", ".py"))
        and ("build" in f or "compile" in f or "webpack" in f)
        for f in files
    )
    has_ci = any(
        f.startswith((".github/", ".gitlab/", "jenkins/"))
        or "ci" in f.lower()
        or "workflow" in f.lower()
        for f in files
    )

    # Analyze diff content
    diff_lower = diff_output.lower()
    keywords = {
        "feat": ["add", "create", "implement", "new", "feature", "support"],
        "fix": ["fix", "bug", "error", "issue", "correct", "solve", "resolve", "patch"],
        "refactor": ["refactor", "rename", "restructure", "cleanup", "extract"],
        "perf": ["optimize", "performance", "speed", "fast", "slow"],
        "style": ["format", "whitespace", "indent", "style", "prettier", "eslint"],
    }

    # Determine type
    suggested_type = "chore"  # default

    # Priority order
    if has_tests:
        suggested_type = "test"
    elif has_docs:
        suggested_type = "docs"
    elif has_ci:
        suggested_type = "ci"
    elif has_build:
        suggested_type = "build"
    elif has_config:
        suggested_type = "chore"

    # Override with keyword detection
    for type_name, words in keywords.items():
        for word in words:
            if word in diff_lower:
                suggested_type = type_name
                break

    # Determine scope from directory structure
    suggested_scope = None
    if files:
        # Get most common directory prefix
        dirs = []
        for f in files:
            if "/" in f:
                dirs.append(f.split("/")[0])
            elif "\\" in f:  # Windows
                dirs.append(f.split("\\")[0])

        if dirs:
            # Find most common non-empty directory
            from collections import Counter

            dir_counts = Counter(dirs)
            common_dir = dir_counts.most_common(1)[0][0]
            if common_dir and common_dir not in (".", ".."):
                suggested_scope = common_dir

    return suggested_type, suggested_scope


def main():
    """Main entry point."""
    cwd = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    # Check if git repo
    if not os.path.exists(os.path.join(cwd, ".git")):
        print("Error: Not a git repository", file=sys.stderr)
        sys.exit(1)

    try:
        commit_type, scope = analyze_changes(cwd)
        print(f"Suggested type: {commit_type}")
        if scope:
            print(f"Suggested scope: {scope}")
        else:
            print("Suggested scope: (none)")
    except Exception as e:
        print(f"Analysis error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
