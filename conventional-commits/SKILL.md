---
name: conventional-commits
description: Automatically analyze git changes and create Conventional Commits compliant messages. Use when the user requests to commit changes, make a commit, git commit, or mentions conventional/semantic/structured commits. This skill guides through proper commit type selection (feat, fix, docs, etc.), scope determination, and body creation, ensuring consistent commit history for automated tooling.
license: MIT
compatibility: claude-code, opencode
metadata:
  author: Pablo Lozano
  version: 0.3
  scope: [root, git]
  auto_invoke: User asks to commit changes
---

# Conventional Commits Skill

## Purpose

This skill helps you create and execute git commits that follow the [Conventional Commits specification](https://www.conventionalcommits.org/en/v1.0.0/). It automatically analyzes git changes, suggests appropriate commit types, guides you through creating a properly formatted commit message, and executes the commit.

## When to Use

ALWAYS use this skill when:
- The user asks to "make a commit", "commit changes", "do a commit"
- The user mentions "conventional commits", "semantic commits", "structured commits"
- The user wants to follow git best practices for commit messages
- The user is working in a git repository and needs to commit changes

## Workflow

Follow this EXACT workflow every time:

### 1. Initial Checks
- Verify you're in a git repository: `git status`
- Check for uncommitted changes: `git diff --name-status`
- If no changes, inform the user and exit

### 2. Analyze Changes
- Run `git diff` to see what changed
- Run `git status --porcelain` for machine-readable status
- Analyze the changes to suggest commit type

### 3. Smart Information Extraction

Before prompting the user, extract information from their request to reduce unnecessary interactions:

1. **Look for explicit type mentions**: "feat", "fix", "docs", "style", "refactor", "perf", "test", "chore", "ci", "build"
2. **Look for scope in parentheses or after "scope"**: "auth", "ui", "api", "login", "user-profile", "button"
3. **Look for description clues**: After "description:", "message:", or in quotes
4. **Look for issue references**: "#123", "issue #45", "fixes #456", "closes #789"
5. **Look for breaking change indicators**: "breaking change", "BREAKING CHANGE", "breaking", "! (will be added automatically)"
6. **Look for partial commit requests**: "only", "just the", "specific files", "auth middleware only"

If you extract clear information, use it as defaults and confirm with the user instead of asking from scratch.

### 4. Determine Commit Type

Based on the Conventional Commits specification and Angular convention, use these guidelines:

| Type | When to Use | Examples |
|------|-------------|----------|
| **feat** | New feature or functionality | New component, API endpoint, user feature |
| **fix** | Bug fix | Correcting errors, fixing crashes |
| **docs** | Documentation changes | README, comments, API docs |
| **style** | Code style/formatting | Prettier, ESLint, whitespace |
| **refactor** | Code refactoring | Renaming, restructuring without behavior change |
| **perf** | Performance improvements | Optimizations, faster algorithms |
| **test** | Test-related changes | Adding/updating tests, test infrastructure |
| **chore** | Maintenance tasks | Build scripts, dependencies, config files |
| **ci** | CI/CD changes | GitHub Actions, Jenkins, deployment |
| **build** | Build system changes | Webpack, Babel, compilation |

**Analysis logic:**
- Look for keywords in diff: `add`, `create`, `implement` → `feat`
- Keywords: `fix`, `correct`, `solve`, `error` → `fix`
- File patterns: `*.md`, `README`, `docs/` → `docs`
- File patterns: `*.test.*`, `*.spec.*`, `__tests__/` → `test`
- Configuration files: `package.json`, `webpack.config.*` → `chore` or `build`
- Only whitespace/style changes → `style`
- No behavior changes but code restructuring → `refactor`

### 4. Commit Message Creation (Smart & Interactive)

**Goal:** Create the best possible commit message with minimal unnecessary interaction.

#### Step 1: Extract information from user request
- Scan the user's message for type keywords: "feat", "fix", "docs", "style", "refactor", "perf", "test", "chore", "ci", "build"
- Look for scope: words in parentheses, after "scope:", or module names like "auth", "ui", "api", "login", "button"
- Extract description: Look for quotes or descriptive phrases after "description:", "message:", or in the main request
- Identify issues: "#123", "issue #45", "fixes #456", "closes #789"
- Detect breaking changes: "breaking change", "BREAKING CHANGE", "breaking", "! (add automatically)"
- Note partial commits: "only", "just the", "specific files", mentions of specific file paths

#### Step 2: Determine missing information
Based on git diff analysis AND extracted information:
- If type is clearly extracted AND matches git analysis → use it without asking
- If type is unclear or conflicting → ask: "Based on changes and your request, this looks like [type]. Correct? (yes/no/other)"
- If scope is clearly extracted (from request or file paths) → use it
- If scope is unclear → ask: "What's the scope? (e.g., 'auth', 'ui', 'api'). Leave empty if none."
- Description is REQUIRED: If user provided a clear description, use it. Otherwise ask: "Please provide a short description (imperative mood):"

#### Step 3: Create descriptive commit body
**ALWAYS include a body when:**
- User provides detailed context about changes
- Multiple components/files are affected
- Security fixes, performance improvements, or breaking changes are involved
- The commit message alone doesn't capture the full context

**Body content should include:**
- What changed and why
- Key implementation details
- Any relevant technical decisions
- References to related components or systems

**Example body for a feature:**
```
- Added avatar upload with image cropping and validation
- Implemented bio fields with markdown support (500 char limit)
- Updated User model with new profile fields
- Created API endpoints at /api/user/profile
- Added frontend components in src/components/profile/
```

#### Step 4: Handle special cases
- **Breaking changes**: Always add '!' after type/scope AND include BREAKING CHANGE footer with details
- **Issue references**: Use "fixes #123" or "closes #456" in footer
- **Partial commits**: If user mentions specific files, use `git add path/to/file` instead of `git add .`
- **Evaluation mode**: When the request is clearly an evaluation (mentions "eval", "test case", or contains detailed predefined values), skip confirmations and use provided information

#### Step 5: Confirm before executing
Show the complete commit message and ask:
"Ready to commit? This will run 'git add [files]' and 'git commit -m \"message\"' (yes/no)"
If partial commit: specify which files will be added.

### 5. Commit Format & Examples

The commit message MUST follow this exact Conventional Commits format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Complete examples with bodies:**

```
feat(user-profile): add avatar upload and bio fields

- Added avatar upload with image cropping and validation
- Implemented bio fields with markdown support (500 character limit)
- Updated User model with new profile fields
- Created API endpoints at /api/user/profile
- Added frontend components in src/components/profile/
```

```
fix(auth): resolve race condition in JWT validation

- Fixed race condition in token validation that caused intermittent auth failures
- Added proper locking mechanism for concurrent requests
- Updated tests to cover edge cases
- Performance impact: minimal (< 2ms overhead)

Fixes #123
```

```
chore(deps)!: update React to v18.3 and Node.js to 20.x

- Updated React from v17 to v18.3 with concurrent features
- Upgraded Node.js from 16.x to 20.x for security and performance
- Fixed critical security vulnerability CVE-2024-12345 in auth middleware
- Removed deprecated API v1 endpoints

BREAKING CHANGE: API v1 endpoints removed, response format changed for /api/v2/users

fixes #45
```

**Simple examples:**
- `feat(auth): add JWT authentication`
- `fix(api): resolve null pointer in user endpoint`
- `docs: update installation instructions`
- `chore(deps): update dependencies`

### 6. Confirm and Execute

1. **Show complete commit message** to the user with highlighted sections
2. **Determine files to add**:
   - If user requested partial commit (specific files/directories): `git add path/to/file1 path/to/file2`
   - If user didn't specify: `git add .` (all changes)
3. **Ask for confirmation**: "Ready to commit? This will run 'git add [files]' and 'git commit -m \"message\"' (yes/no)"
   - For partial commits: specify exactly which files will be added
4. **If yes**:
   - Run the appropriate `git add` command
   - Run `git commit -m "message"` (properly escaped, use `-m` for each paragraph if needed)
   - Show the commit hash and summary
5. **If no**: Allow editing or cancel the commit

**Note for evaluation mode**: When running in an automated test/evaluation environment, you may skip confirmations if all required information is provided in the request.

### 7. Error Handling

- If not in git repo: "Not a git repository. Initialize first with 'git init'."
- If no changes: "No uncommitted changes found."
- If commit fails: Show error and suggest solutions

## Scripts and Utilities

This skill includes helper scripts in the `scripts/` directory:

- `analyze-changes.py`: Analyzes git diff to suggest commit type
- `format-message.py`: Formats commit message according to Conventional Commits

Read these scripts when you need to understand the analysis logic or formatting rules.

## Best Practices

1. **Always validate**: Ensure commit message follows Conventional Commits spec
2. **Keep it simple**: Don't overcomplicate - simple, clear messages are best
3. **Use imperative mood**: "add feature" not "added feature"
4. **Limit scope**: Scope should be a short noun, not a sentence
5. **Reference issues**: Use "fixes #123", "closes #456" in footer when appropriate

## Examples

**User:** "I fixed a bug in the login form"
**Skill:** Analyzes changes, suggests `fix(login): ...`, confirms scope, creates commit

**User:** "haz un commit de los cambios en el componente Button"
**Skill:** Analyzes Button component changes, suggests appropriate type, creates Spanish-friendly interaction

**User:** "commit using conventional commits"
**Skill:** Full workflow: analyze, suggest type, ask scope/description, execute

## Troubleshooting

- **Commit rejected by hooks**: Check for pre-commit hooks, offer to run with `--no-verify` (ask user first)
- **Large diff**: Consider breaking into multiple commits if changes are unrelated
- **Merge conflicts**: Advise user to resolve conflicts first

Remember: The goal is to create meaningful, standardized commit messages that improve project history and enable automated tools.