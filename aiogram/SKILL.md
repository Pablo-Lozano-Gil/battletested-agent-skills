---
name: aiogram
description: Use when building Telegram bots with Python aiogram framework, especially for complex conversational flows with FSM, modular router architecture, middleware patterns, and security requirements. Trigger: when creating a Telegram bot or when the user asks to create a Telegram bot.
license: MIT
metadata:
  author: Pablo Lozano
  version: "0.3"
  scope: [root, telegram]
  auto_invoke:
    - "When creating a Telegram bot using Python"
    - "User asks to generate a bot for Telegram"
allowed-tools: Read, Edit, Write, Glob, Grep
---

# Aiogram - Modern Telegram Bot Framework

## Overview

Aiogram is a modern, fully asynchronous framework for Telegram Bot API written in Python using asyncio. Designed from the ground up for async/await with native support for Finite State Machines (FSM), router-based architecture, middleware patterns, and comprehensive type hints.

**Core advantages:**
- **Native FSM** with persistent storage (Redis, Memory, MongoDB)
- **Router-based architecture** for modular bot design
- **First-class middleware** for cross-cutting concerns
- **Dependency injection** integrated throughout the framework
- **Webhook support** designed from day one
- **100% type hinted** for better IDE support

## When to Use

**Use aiogram when:**
- Building complex conversational bots with multi-step flows
- Needing modular architecture with separate feature routers
- Requiring persistent conversation state across bot restarts
- Implementing custom middleware for auth, logging, or rate limiting
- Deploying with webhooks behind reverse proxies
- Prioritizing modern async patterns and type safety

**Consider alternatives when:**
- Building extremely simple bots with minimal logic
- Needing synchronous execution (use python-telegram-bot sync mode)
- Working with legacy Python versions (< 3.10)

## Core Patterns

### Finite State Machine (FSM)

Aiogram's FSM system provides structured conversation flows with state persistence:

```python
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

router = Router()

class OrderForm(StatesGroup):
    waiting_for_product = State()
    waiting_for_quantity = State()
    waiting_for_address = State()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.set_state(OrderForm.waiting_for_product)
    await message.answer("What product would you like to order?")

@router.message(OrderForm.waiting_for_product)
async def process_product(message: Message, state: FSMContext) -> None:
    await state.update_data(product=message.text)
    await state.set_state(OrderForm.waiting_for_quantity)
    await message.answer("How many units?")

@router.message(OrderForm.waiting_for_quantity, F.text.regexp(r"^\d+$"))
async def process_quantity(message: Message, state: FSMContext) -> None:
    await state.update_data(quantity=int(message.text))
    await state.set_state(OrderForm.waiting_for_address)
    await message.answer("Please provide delivery address:")
```

**Key concepts:**
- `StatesGroup` defines conversation states as class attributes
- `FSMContext` manages state transitions and data storage
- State-specific handlers trigger only when user is in that state
- Data persists in storage (Redis, Memory, SQLite, MongoDB)

**Storage backends:**
```python
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage

# Persistent storage (recommended for production)
storage = RedisStorage.from_url(
    "redis://localhost:6379/0",
    state_ttl=3600,  # State expires after 1 hour
    data_ttl=3600    # Data expires after 1 hour
)

# Memory storage (loses data on restart)
storage = MemoryStorage()

dp = Dispatcher(storage=storage)
```

### Router-Based Architecture

Routers enable modular bot design by grouping related handlers:

```python
from aiogram import Router, Dispatcher, Bot
from aiogram.filters import Command
from aiogram.types import Message

# Create separate routers for different features
user_router = Router(name="user")
admin_router = Router(name="admin")
telegram_adapter = Router(name="telegram_adapter")

@user_router.message(Command("profile"))
async def show_profile(message: Message) -> None:
    await message.answer(f"User ID: {message.from_user.id}")

@admin_router.message(Command("stats"))
async def show_stats(message: Message) -> None:
    await message.answer("Bot statistics: 100 users")

# Include routers in dispatcher hierarchically
dp = Dispatcher()
dp.include_router(user_router)
dp.include_router(admin_router)
```

**Benefits:**
- Feature isolation and separation of concerns
- Reusable router modules across projects
- Hierarchical inclusion for complex bot structures
- Per-router middleware and filters

### Middleware Patterns

Middleware intercepts and processes updates before handlers:

```python
from typing import Any, Callable, Awaitable
from aiogram import BaseMiddleware, Dispatcher, Router
from aiogram.types import Message, TelegramObject
import time

class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        start_time = time.time()
        result = await handler(event, data)
        process_time = time.time() - start_time
        print(f"Handler took {process_time:.3f}s")
        return result

class AuthMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: list[int]):
        self.admin_ids = admin_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any]
    ) -> Any:
        # Inject is_admin into handler data
        data["is_admin"] = event.from_user.id in self.admin_ids
        return await handler(event, data)

# Register middlewares globally or per-router
dp = Dispatcher()
dp.message.middleware(LoggingMiddleware())
dp.message.middleware(AuthMiddleware(admin_ids=[123456789]))
```

**Dependency injection:**
```python
@router.message(Command("admin"))
async def admin_command(message: Message, is_admin: bool) -> None:
    # is_admin injected by AuthMiddleware
    if is_admin:
        await message.answer("Welcome, admin!")
    else:
        await message.answer("Access denied")
```

### Security Patterns

**1. Whitelist authentication:**
```python
class WhitelistMiddleware(BaseMiddleware):
    def __init__(self, allowed_user_ids: set[int]):
        self.allowed_user_ids = allowed_user_ids

    async def __call__(self, handler, event: Message, data):
        if event.from_user.id not in self.allowed_user_ids:
            # Silently ignore unauthorized users
            return
        return await handler(event, data)
```

**2. Rate limiting with flags:**
```python
from aiogram import flags

@router.message(Command("stats"))
@flags.rate_limit(rate=5, key="stats_command")  # 5 requests per key
async def stats_handler(message: Message) -> None:
    await message.answer("Bot stats: ...")
```

**3. Webhook security:**
```python
# Set secret token when configuring webhook
await bot.set_webhook(
    f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}",
    secret_token=WEBHOOK_SECRET,  # Validates incoming requests
)

# In webhook handler configuration
webhook_requests_handler = SimpleRequestHandler(
    dispatcher=dp,
    bot=bot,
    secret_token=WEBHOOK_SECRET,  # Validates each request
)
```

**4. IP filtering (behind reverse proxy):**
```python
# Configure reverse proxy (nginx/traefik) to:
# - Forward requests to http://127.0.0.1:8080/webhook
# - Set X-Forwarded-For header
# - Configure SSL/TLS termination
# - Set X-Telegram-Bot-Api-Secret-Token header

# Bind to localhost only
WEB_SERVER_HOST = "127.0.0.1"
WEB_SERVER_PORT = 8080
```

**5. NEVER hardcode the Telegram bot TOKEN**

Always use a library like python_dotenv for loading the Telegram bot token or any sensitive variable.
```python
import os
from dotenv import load_dotenv

# Load sensitive and set them in os.environ
load_dotenv() 

# Get the relevant token
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    raise ValueError("Telegram bot token not found. Cofigure the TELEGRAM_BOT_TOKEN variable.")

# Proceed with the rest of the implementation of the bot
```

### Magic Filter (F) DSL

Powerful filtering without custom filter classes:

```python
from aiogram import Router, F
from aiogram.types import Message, ContentType

router = Router()

# Filter by text content
@router.message(F.text == "hello")
async def exact_match(message: Message) -> None:
    await message.answer("You said hello!")

# Filter by regex pattern
@router.message(F.text.regexp(r"^/order_(\d+)$"))
async def order_pattern(message: Message) -> None:
    await message.answer("Order command received")

# Combine filters with AND/OR
@router.message(F.text.len() > 10, F.text.startswith("!"))
async def long_command(message: Message) -> None:
    await message.answer("Long command received")

# Filter by user attributes
@router.message(F.from_user.username.in_(["admin1", "admin2"]))
async def admin_only(message: Message) -> None:
    await message.answer("Hello, admin!")
```

## Quick Reference

| Component | Import | Purpose |
|-----------|--------|---------|
| **Bot** | `from aiogram import Bot` | Main bot instance, sends API calls |
| **Dispatcher** | `from aiogram import Dispatcher` | Root router, manages updates |
| **Router** | `from aiogram import Router` | Modular handler container |
| **FSMContext** | `from aiogram.fsm.context import FSMContext` | State management in handlers |
| **StatesGroup** | `from aiogram.fsm.state import State, StatesGroup` | Define conversation states |
| **BaseMiddleware** | `from aiogram import BaseMiddleware` | Create custom middleware |
| **Magic Filter** | `from aiogram import F` | DSL for filter conditions |
| **Storage** | `from aiogram.fsm.storage.redis import RedisStorage` | Persistent FSM storage |

**Common storage backends:**
- `MemoryStorage` - In-memory (not persistent)
- `RedisStorage` - Redis-backed (production)
- `MongoStorage` - MongoDB-backed
- Custom storage - Implement `BaseStorage` interface

## Implementation Examples

### Basic Bot Setup (Polling)

```python
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from dotenv import load_dotenv

# Loads sensitive and sets them in os.environ
load_dotenv() 

# Gets the relevant token
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    raise ValueError("Telegram token not found. Cofigure the TELEGRAM_BOT_TOKEN variable.")

# Proceed with the rest of the implementation of the bot
router = Router()

@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer("Hello!")

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
```

### Webhook Setup with Reverse Proxy

```python
import logging
from os import getenv
from aiohttp import web
from aiogram import Bot, Dispatcher, Router
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

TOKEN = getenv("BOT_TOKEN")
WEB_SERVER_HOST = "127.0.0.1"
WEB_SERVER_PORT = 8080
WEBHOOK_PATH = "/webhook"
WEBHOOK_SECRET = "my-secret"
BASE_WEBHOOK_URL = "https://your-domain.com"

router = Router()

async def on_startup(bot: Bot) -> None:
    await bot.set_webhook(
        f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET
    )

def main():
    dp = Dispatcher()
    dp.include_router(router)
    dp.startup.register(on_startup)

    bot = Bot(token=TOKEN)
    app = web.Application()
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=WEBHOOK_SECRET
    )
    webhook_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    
    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
```

## Common Mistakes

### ❌ Using MemoryStorage in Production
**Problem:** `MemoryStorage` loses all state on bot restart.
**Solution:** Use `RedisStorage` or another persistent backend.

### ❌ Missing Error Handling in Middleware
**Problem:** Exceptions in middleware break the entire update chain.
**Solution:** Wrap middleware logic in try-except blocks.

### ❌ Circular Router Dependencies
**Problem:** Router A includes Router B, which includes Router A.
**Solution:** Design hierarchical router structure without cycles.

### ❌ Ignoring Webhook Secret Validation
**Problem:** Anyone can send POST requests to your webhook endpoint.
**Solution:** Always set and validate `secret_token` in webhook configuration.

### ❌ Blocking Handlers
**Problem:** CPU-bound operations block the event loop.
**Solution:** Use `asyncio.to_thread()` for blocking operations.

### ❌ Not Using Type Hints
**Problem:** Missed IDE support and runtime type validation.
**Solution:** Always add type hints to handlers and middleware.

### ❌ Hardcoding Configuration
**Problem:** Tokens and settings in source code.
**Solution:** Use environment variables and configuration classes.

## Resources

- **Official documentation:** https://docs.aiogram.dev/
- **GitHub repository:** https://github.com/aiogram/aiogram
- **Telegram API:** https://core.telegram.org/bots/api

---

*Skill created with information from Context7 MCP documentation. Always verify with official aiogram documentation for the latest patterns and best practices.*