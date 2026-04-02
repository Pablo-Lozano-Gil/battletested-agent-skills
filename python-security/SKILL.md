---
name: python-security
description: Use when creating Python projects with Docker, handling environment variables, managing secrets, or setting up secure deployments. Trigger: when writing Dockerfiles, docker-compose files, .env files, or configuring database connections and API keys.
license: MIT
metadata:
  author: Pablo Lozano
  version: "0.2"
  scope: [root]
  auto_invoke:
    - "when writing Dockerfiles, docker-compose files, .env files, or configuring database connections and API keys"
    - "Creating Python programs in general (security is a must always)"
allowed-tools: Read, Edit, Write, Glob, Grep
---

# Python Security Best Practices

## Overview

**Core Principle:** Secrets NEVER go into git. Not in Dockerfile, not in docker-compose.yml, not in any committed file. Environment variables are for runtime, not build time.

This skill covers: environment variables (python-dotenv), UV package manager, Docker security, .gitignore, logging security, input validation, secrets rotation, and production secrets management.

## Red Flags - STOP Immediately

- Hardcoding passwords, API keys, or tokens in ANY file that goes to git
- "It's just for development" excuses
- Putting secrets in Dockerfile `ENV` or `ARG`
- Passwords in docker-compose.yml under `environment:`
- Logging sensitive data "for debugging"
- "I'll fix it later" when it comes to secrets

**All of these mean: STOP. Delete the secrets. Start over with proper patterns.**

## Quick Reference

| Category | DO | DON'T |
|----------|-----|-------|
| Environment | `.env` in `.gitignore`, load with `python-dotenv` | Commit `.env`, hardcode in Python |
| Docker | Pass secrets at runtime via env vars | Put secrets in Dockerfile `ENV`/`ARG` |
| Compose | `${VAR:-default}` syntax, `.env` file | Hardcode passwords in `environment:` |
| Git | Comprehensive `.gitignore` | Assume "I won't accidentally commit" |
| Logging | Mask/omit secrets, use structured logging | Log raw `os.environ`, passwords, tokens |
| UV | Commit `uv.lock`, use `--frozen` in CI | Ignore lock file, floating versions |
| Production | Secrets manager (Vault, AWS, etc.) | Files on disk, environment in images |

---

## 1. Environment Variables with python-dotenv

### Basic Pattern

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    secret_key: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### .env Files

```bash
# .env.example (commit to git - TEMPLATE ONLY with <placeholders>)
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<database>
OPENAI_API_KEY=<your-openai-api-key>
SECRET_KEY=<your-secret-key-min-32-chars>

# .env (NEVER commit - actual secrets)
DATABASE_URL=postgresql://realuser:realpass@prod-db.example.com/proddb
OPENAI_API_KEY=sk-prod-abc123xyz789
SECRET_KEY=super-secret-production-key-42
```

**Critical:** `.env.example` shows STRUCTURE, not real values. Use obvious placeholders.

---

## 2. UV Best Practices

### Project Setup

```bash
# Initialize project
uv init
uv add fastapi uvicorn pydantic-settings

# Generate/update lock file - RUN THIS after adding dependencies
uv lock

# uv.lock MUST be committed to git for reproducible builds
git add uv.lock
```

### Docker with UV

```dockerfile
FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies FIRST (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy and install project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Non-root user
RUN useradd --create-home --shell /bin/bash app
USER app

ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

### CI/CD with UV

```bash
# In CI - fail if lock is outdated
uv sync --frozen

# Or with frozen flag
uv run --frozen python -m pytest
```

**Key:** `--locked` fails if `uv.lock` needs update. `--frozen` prevents network access. Use in CI.

---

## 3. Docker Without Secrets

### The Rules

1. **NO secrets in Dockerfile** - `ENV API_KEY=xxx` is forever in image layers
2. **NO secrets in build args** - `ARG PASSWORD` is visible in `docker history`
3. **NO secrets in docker-compose environment hardcoded** - That file goes to git

### Correct Pattern: Runtime Injection

```yaml
# docker-compose.yml
services:
  app:
    build: .
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    env_file:
      - .env  # Local dev only - .env should be in .gitignore

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # NO default for passwords!
      POSTGRES_DB: ${POSTGRES_DB:-appdb}
```

### .dockerignore

```
# .dockerignore - Prevent secrets from entering build context
.env
.env.*
*.pem
*.key
credentials.json
secrets.*
.git
.gitignore
__pycache__
.venv
*.pyc
.pytest_cache
.ruff_cache
```

---

## 4. Robust .gitignore

```gitignore
# Secrets - NEVER commit these
.env
.env.local
.env.*.local
*.pem
*.key
*.crt
credentials.json
secrets.*
secrets.yaml
secrets.yml
service-account.json
*.p12
*.pfx

# Python
__pycache__/
*.py[cod]
*$py.class
.venv/
venv/
*.so
.Python
build/
dist/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# UV - IMPORTANT: uv.lock SHOULD be committed!
# Only ignore the cache
.uv/

# OS
.DS_Store
Thumbs.db
```

**Note:** `uv.lock` MUST be committed. It ensures reproducible builds.

---

## 5. Secure Logging

### Wrong - Leaks Secrets

```python
# BAD - Logs entire config including secrets
import logging
logging.info(f"Config: {settings.dict()}")

# BAD - Logs environment variables
import os
logging.info(f"Environment: {dict(os.environ)}")

# BAD - Logs database URL with password
logging.info(f"Connecting to: {settings.database_url}")
```

### Correct - Masked Logging

```python
import logging
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    secret_key: str

    @field_validator('database_url')
    @classmethod
    def mask_password(cls, v: str) -> str:
        # For logging only - mask password
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', v)

    def safe_dict(self) -> dict:
        """Returns dict with secrets masked"""
        return {
            "database_url": self.mask_password(self.database_url),
            "openai_api_key": f"{self.openai_api_key[:8]}...",
            "secret_key": "***MASKED***"
        }

settings = Settings()
logging.info(f"Config loaded: {settings.safe_dict()}")
```

### Structured Logging Pattern

```python
import logging
import structlog

logger = structlog.get_logger()

# Good - explicit, intentional logging
logger.info("database_connected", host=db_host, port=db_port)
logger.info("api_request", endpoint="/users", method="GET")

# Never log: passwords, tokens, api keys, personal data
```

---

## 6. Input Validation

### Basic Validation with Pydantic

```python
from pydantic import BaseModel, field_validator, HttpUrl
import re

class UserInput(BaseModel):
    username: str
    email: str
    file_path: str | None = None

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', v):
            raise ValueError('Username must be 3-20 alphanumeric chars')
        return v

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v.lower()

    @field_validator('file_path')
    @classmethod
    def prevent_path_traversal(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if '..' in v or v.startswith('/'):
            raise ValueError('Path traversal detected')
        return v
```

### SQL Injection Prevention

```python
# BAD - SQL injection vulnerable
cursor.execute(f"SELECT * FROM users WHERE id = {user_input}")

# GOOD - Parameterized queries
cursor.execute("SELECT * FROM users WHERE id = %s", (user_input,))

# GOOD - With SQLAlchemy
from sqlalchemy import text
result = db.execute(text("SELECT * FROM users WHERE id = :id"), {"id": user_input})
```

### Command Injection Prevention

```python
import shlex
import subprocess

# BAD - Command injection vulnerable
subprocess.run(f"convert {filename} output.png", shell=True)

# GOOD - Use list args (no shell interpretation)
subprocess.run(["convert", filename, "output.png"], check=True)

# GOOD - If shell needed, use shlex.quote
subprocess.run(f"convert {shlex.quote(filename)} output.png", shell=True, check=True)
```

---

## 7. Secrets Rotation Strategy

### Design for Rotation

```python
class Settings(BaseSettings):
    # Support multiple API keys for rotation
    openai_api_key: str
    openai_api_key_backup: str | None = None

    def get_api_key(self) -> str:
        """Returns active key, supports rotation"""
        return self.openai_api_key

    def rotate_key(self, new_key: str) -> None:
        """Rotate API key without downtime"""
        self.openai_api_key_backup = self.openai_api_key
        self.openai_api_key = new_key

# In production, use a secrets manager that supports rotation
```

### Rotation Checklist

1. **Generate new secret** in secrets manager
2. **Deploy with new secret** (old still valid)
3. **Verify new secret works**
4. **Revoke old secret** after grace period
5. **Monitor for failures** - catch services still using old secret

### Database Password Rotation

```yaml
# Support read-only connection during rotation
database_url: postgresql://app:password@db/app
database_url_readonly: postgresql://app_ro:ro_password@db/app
```

---

## 8. Production Secrets Management

### Never Use .env in Production

```python
# BAD - .env files in production
from dotenv import load_dotenv
load_dotenv()  # Never do this in production

# GOOD - Load from environment (set by orchestrator)
import os
api_key = os.environ.get("OPENAI_API_KEY")

# BETTER - Use secrets manager SDK
```

### AWS Secrets Manager

```python
import boto3
import json

def get_secret(secret_name: str, region: str = "us-east-1") -> dict:
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])

# Usage
secrets = get_secret("prod/myapp/database")
database_url = secrets["database_url"]
```

### HashiCorp Vault

```python
import hvac

client = hvac.Client(url="https://vault.example.com")
client.auth.approle.login(
    role_id=os.environ["VAULT_ROLE_ID"],
    secret_id=os.environ["VAULT_SECRET_ID"]
)

secret = client.secrets.kv.v2.read_secret_version(path="myapp/database")
database_url = secret["data"]["data"]["database_url"]
```

### Environment Variable Pattern (Kubernetes/GitLab CI/etc.)

```yaml
# Kubernetes Secret
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  DATABASE_URL: "postgresql://..."
  OPENAI_API_KEY: "sk-..."
---
# Deployment
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: app
          envFrom:
            - secretRef:
                name: app-secrets
```

---

## Common Rationalizations (And Why They're Wrong)

| Excuse | Reality |
|--------|---------|
| "It's just a demo" | Demos become prototypes become production. Start right. |
| "I'll fix it later" | Later never comes. The commit with the password is forever. |
| "It's only in docker-compose" | docker-compose.yml goes to git. Password is in history forever. |
| "The repo is private" | Private repos get cloned, leaked, sold. Treat all repos as public. |
| "It's for local dev only" | Dev environments have real data. Local databases get production dumps. |
| "The password is in .env" | Great! But you also put it in docker-compose environment section. |
| "I'll use .env.example" | .env.example with real password patterns teaches bad habits. |
| "It's just a test API key" | Test keys become prod keys. Habits compound. |

---

## Checklist Before Any Commit

```bash
# 1. Check for secrets accidentally staged
git diff --cached | grep -i -E "(password|secret|api_key|token)"

# 2. Verify .gitignore is working
git status --porcelain | grep -E "\.env|\.pem|\.key|credentials"

# 3. Check docker-compose for hardcoded secrets
grep -E "POSTGRES_PASSWORD|MYSQL_ROOT_PASSWORD|API_KEY" docker-compose.yml

# 4. Verify no secrets in Dockerfile
grep -E "ENV.*=.*[" dockerfile | grep -v "ENV PATH\|ENV PYTHON"

# 5. If any match found, STOP and fix before commit
```

---

## TL;DR

1. **Never commit secrets** - `.env` in `.gitignore`, templates in `.env.example`
2. **Runtime injection only** - Docker gets secrets from env vars, not from files
3. **UV lock file** - Commit `uv.lock`, use `--frozen` in CI
4. **Mask in logs** - Never log raw secrets, passwords, tokens
5. **Validate all inputs** - Pydantic, parameterized queries, no shell=True
6. **Design for rotation** - Support multiple keys, grace periods
7. **Production: secrets manager** - AWS, Vault, Kubernetes secrets - not files
