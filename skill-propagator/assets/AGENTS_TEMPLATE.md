# Repository Guidelines

## How to Use This Guide

- Start here for cross-project norms. The project is a monorepo with several components.
- Each component has an `AGENTS.md` file with specific guidelines (e.g., `api/AGENTS.md`, `ui/AGENTS.md`).
- Component docs override this file when guidance conflicts.

## Available Skills

Use these skills for detailed patterns on-demand:

<!-- SKILLS_AVAILABLE:START -->
<!-- SKILLS_AVAILABLE:END -->

### Auto-invoke Skills

When performing these actions, ALWAYS invoke the corresponding skill FIRST:

<!-- SKILLS_AUTO_INVOKE:START -->
<!-- SKILLS_AUTO_INVOKE:END -->

---

## Project Overview

{Project-description}.

| Component | Location | Tech Stack |
| ----------- | ---------- | ------------ |
| API | `api/` | FastAPI, uv |
| UI | `ui/` | Astro.js, Tailwind 4 |

---

## Python Development

```bash
# Setup
uv init
uv sync --all-extras

# Code quality (using Ruff from Astral)
ruff check
ruff format
```

---

## Commit & Pull Request Guidelines

Follow conventional-commit style: `<type>[scope]: <description>`

**Types:** `feat`, `fix`, `docs`, `chore`, `perf`, `refactor`, `style`, `test`

Before creating a PR:

1. Complete checklist in `.github/pull_request_template.md`
2. Run all relevant tests and linters
3. Link screenshots for UI changes
