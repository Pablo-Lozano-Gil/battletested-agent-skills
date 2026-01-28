# 🛡️ Battletested Agent Skills

**A centralized arsenal of production-grade Agent Skills for autonomous AI agents.**

This repository contains **Agent Skills** following the [Agent Skills open standard](https://agentskills.io). Skills provide domain-specific patterns, conventions, and guardrails that help AI coding assistants (Claude Code, OpenCode, Cursor, Antigravity, etc.) understand project-specific requirements.

It serves as a shared library of Agent Skills. It is designed to be included as a **Git Submodule** in your agent projects, ensuring that all your agents share the same "muscle memory" and reliable tooling.

## What Are Skills?

[Agent Skills](https://agentskills.io) is an open standard format for extending AI agent capabilities with specialized knowledge. Originally developed by Anthropic and released as an open standard, it is now adopted by multiple agent products.

Skills teach AI assistants how to perform specific tasks. When an AI loads a skill, it gains context about:

- Critical rules (what to always/never do)
- Code patterns and conventions
- Project-specific workflows
- References to detailed documentation

---

## Setup

This repository is not meant to be run standalone. It is a library meant to be consumed by other projects.

## How to Use Skills

Skills are automatically discovered by the AI agent. To manually load a skill during a session:

```text
Read skills/{skill-name}/SKILL.md
```

## Available Skills

### Generic Skills (Any Project)

| Skill | Description | URL |
| ------- | ----------- | ----- |

### Project-Specific Skills

| Skill | Description | URL |
| ------- | ------------- | ----- |

### Meta Skills

| Skill | Description |
| ------- | ------------- |

## Directory Structure

```text
battletested-agent-skills/
├── {skill-name}/
│   ├── SKILL.md              # Required - main instrunsction and metadata
│   ├── scripts/              # Optional - executable code
│   ├── assets/               # Optional - templates, schemas, resources
│   └── references/           # Optional - links to local docs
└── README.md                 # This file
```

## Why Auto-invoke Sections?

**Problem**: AI assistants (Claude, Gemini, etc.) don't reliably auto-invoke skills even when the `Trigger:` in the skill description matches the user's request. They treat skill suggestions as "background noise" and barrel ahead with their default approach.

**Solution**: The `AGENTS.md` files in each directory contain an **Auto-invoke Skills** section that explicitly commands the AI: "When performing X action, ALWAYS invoke Y skill FIRST." This is a [known workaround](https://scottspence.com/posts/claude-code-skills-dont-auto-activate) that forces the AI to load skills.

**Automation**: Instead of manually maintaining these sections, run `skill-sync` after creating or modifying a skill:

```bash
skill-sync/assets/sync.sh
```

This reads `metadata.scope` and `metadata.auto_invoke` from each `SKILL.md` and generates the Auto-invoke tables in the corresponding `AGENTS.md` files.

## Creating New Skills

Use the `skill-creator` skill for guidance:

```text
Read skill-creator/SKILL.md
```

### Quick Checklist

1. Create directory: `{skill-name}/`
2. Add `SKILL.md` with required frontmatter
3. Add `metadata.scope` and `metadata.auto_invoke` fields
4. Keep content concise (under 500 lines)
5. Reference existing docs instead of duplicating
6. Run `skill-sync/assets/sync.sh` to update AGENTS.md
7. Add to `AGENTS.md` skills table (if not auto-generated)

## Design Principles

- **Concise**: Only include what AI doesn't already know
- **Progressive disclosure**: Point to detailed docs, don't duplicate
- **Critical rules first**: Lead with ALWAYS/NEVER patterns
- **Minimal examples**: Show patterns, not tutorials

## Resources

- [Agent Skills Standard](https://agentskills.io) - Open standard specification
- [Agent Skills GitHub](https://github.com/anthropics/skills) - Example skills
- [Claude Code Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) - Skill authoring guide
- [SKILLS](https://skills.sh) - Skills repository from Vercel
