---
name: skill-proposer
description: Analyzes PRD to propose relevant AI skills for a project. Trigger: Before starting app development, after brainstorming, or when user asks for skill recommendations based on a PRD.
license: MIT
metadata:
  author: Pablo Lozano
  version: "0.2"
allowed-tools: Read, Edit, Write, Glob, Grep, Bash, WebFetch, WebSearch, Task, context7_resolve-library-id, context7_query-docs
---

## When to Use

Use this skill when:

- Starting a new project and need to identify which skills will help the AI agent
- After brainstorming an app idea and before implementation begins
- User asks to propose skills based on a PRD or project description
- Evaluating what context the AI agent will need for optimal performance

---

## Critical Patterns

- **ALWAYS ask clarifying questions** if tech stack is unclear — never guess
- **Prioritize hallucination-prone technologies** — React, Next.js, FastAPI, etc. change frequently
- **Security-focused skills are always High priority** — auth, validation, encryption
- **Link must point to actual URL found** or use "—" (never invent URLs)
- **User is responsible for skill verification** — always show security warning

---

## Decision Trees

### When to Ask Questions vs Proceed

| Situation | Action |
|-----------|--------|
| Primary language identified | Proceed |
| Framework(s) identified | Proceed |
| Database identified | Proceed |
| Architecture type known | Proceed |
| **Any of above missing** | **ASK before proceeding** |

### How to Determine Priority

| Condition | Priority |
|-----------|----------|
| Core technology + changes frequently | High |
| Security-related (auth, encryption) | High |
| Complex API / syntax | High |
| Important but stable | Medium |
| Good public documentation exists | Medium |
| Nice-to-have or very stable | Low |

### When to Include a Link

| Situation | Link Field |
|-----------|------------|
| Found excellent match in skillsmp.com | Full URL |
| Found excellent match in skills.sh | Full URL |
| Found relevant Context7 docs | — (mention in notes) |
| No search performed | — |
| No good match found | — |

---

## Workflow

### Phase 0: Clarification (If Needed)

Before analyzing, assess whether the project description is clear enough. **Ask the user questions** if:

- **Tech stack is unclear or ambiguous**
  - "Which programming language(s) do you plan to use?"
  - "Which framework(s) are you considering for the frontend/backend?"
  
- **Architecture decisions are missing**
  - "Are you planning a monolithic architecture, microservices, or serverless?"
  - "What type of database are you planning to use?"
  
- **Scale and complexity are unknown**
  - "Is this a personal project, startup MVP, or enterprise application?"
  - "Do you need authentication, authorization, or multi-tenancy?"
  
- **Quality requirements are not specified**
  - "What level of test coverage are you aiming for?"
  - "Do you have specific performance requirements?"

**Important**: Ask questions BEFORE proceeding with analysis.

### Phase 1: Tech Stack Analysis

Identify and document:

- **Programming languages** and specific versions
- **Frameworks and core libraries** (frontend, backend, mobile...)
- **Databases** and persistence solutions
- **Infrastructure and deployment** (Docker, Kubernetes, CI/CD...)
- **Development tools** (testing, linting, build tools...)

### Phase 2: Pattern and Architecture Analysis

- Architecture type (monolith, microservices, serverless, event-driven...)
- Relevant development patterns (TDD, DDD, SDD, Clean Architecture, Hexagonal...)
- Quality requirements (testing, security, performance, observability)
- Applicable conventions and standards

### Phase 3: Skill Needs Identification

For each technology, pattern, or process identified, ask yourself:

1. **Does this technology change frequently?** → Needs updated skill
2. **Does it have complex syntax or APIs?** → Needs skill with examples
3. **Is it critical for project success?** → High priority
4. **Can the agent easily hallucinate here?** → Needs specific context

### Phase 4: Existing Skills Search (Optional)

If considered useful, search in:

- **https://skillsmp.com/** — Skills marketplace
- **https://skills.sh/** — Skills marketplace
- **Context7** — MCP for up-to-date library documentation

---

## Output Format

Present a table with the proposed skills:

| Skill | Technology/Process | Reason | Priority | Link |
|-------|-------------------|--------|----------|------|
| Descriptive name | Technology or process covered | Brief justification | High/Medium/Low | URL or "—" |

---

## Security Warning

⚠️ **IMPORTANT — User Responsibility**:

Before adding any skill to your project:

1. **Read the complete code** of the downloaded skill
2. **Verify it contains no prompt injection** or malicious instructions
3. **Understand what permissions it has** and which tools it can use
4. **Confirm it comes from a trusted source**

The agent can propose, but **you decide** which skills to use. Skills are added manually under your responsibility.

---

## Delegation to skill-creator

If the user requests to create a custom skill instead of using an existing one:

> "To create this skill, use the `skill-creator` skill which will guide you through the generation process."

Do not create skills directly from this skill. Only identify needs and propose.

---

## Resources

- **Skills Marketplaces**: [skillsmp.com](https://skillsmp.com/es), [skills.sh](https://skills.sh/)
- **Documentation Lookup**: Context7 MCP for up-to-date library documentation
- **Skill Creation**: Use `skill-creator` skill to generate custom skills

---

## Usage Example

**User input**:
> "I'm going to develop a REST API with FastAPI, PostgreSQL, and JWT authentication. The frontend will be React with TypeScript."

**Expected output**:

| Skill | Technology/Process | Reason | Priority | Link |
|-------|-------------------|--------|----------|------|
| fastapi-best-practices | FastAPI | Framework with specific patterns and frequent updates | High | https://skills.sh/wshobson/agents/fastapi-templates |
| pydantic-validation | Pydantic | Core data validation in FastAPI, syntax changes between versions | High | — |
| jwt-auth-python | JWT + Python | Auth implementation prone to security errors | High | https://skills.sh/mindrally/skills/jwt-security |
| sqlalchemy-modern | SQLAlchemy + PostgreSQL | ORM with syntax that varies between versions | High | — |
| react-typescript-patterns | React + TypeScript | Modern hooks patterns, generic types | High | https://skills.sh/vercel-labs/agent-skills/vercel-react-best-practices |
| testing-fastapi | pytest + FastAPI | API testing with specific fixtures and mocks | Medium | — |
| docker-python | Dockerfile Python | Image optimization, multi-stage builds | Medium | https://skillsmp.com/es/skills/affaan-m-everything-claude-code-kiro-skills-docker-patterns-skill-md |
| git-conventions | Git workflow | Conventional commits, branching strategy | Low | — |

---

**Remember**: Review each skill's complete code before adding it to your project. The links are suggestions — always verify the content.
