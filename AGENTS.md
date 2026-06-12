# AGENTS.md - Odoo AI Assistant

## Repository Type
Odoo 17/18/19 module (Python). Not a standalone app — requires an Odoo instance.

## Setup & Installation

```bash
# Option 1: Automated install script
sudo bash install.sh

# Option 2: Manual — Python dependencies
pip install duckduckgo-search>=4.0.0 nest-asyncio>=1.5.0

# Install module in Odoo
cp -r odoo_ai_assistant /path/to/odoo/addons/
# Restart Odoo and install from Apps menu
```

## Configuration
- Path: **Settings > Ajustes > AI Assistant**
- Required: `ai_assistant.openrouter_api_key` (get at https://openrouter.ai/keys)

### Config Parameters (ir.config_parameter)
| Key | Default | Notes |
|-----|---------|-------|
| `ai_assistant.openrouter_api_key` | (empty) | Required for LLM |
| `ai_assistant.model_name` | openai/gpt-4o-mini | Any OpenRouter model: openai/gpt-4o, anthropic/claude-sonnet, etc. |
| `ai_assistant.web_search_enabled` | True | DuckDuckGo search |
| `ai_assistant.knowledge_search_enabled` | True | Knowledge search (any mode) |
| `ai_assistant.knowledge_search_mode` | local | `local` (Odoo Knowledge) or `anythingllm` |
| `ai_assistant.anythingllm_url` | (empty) | AnythingLLM API URL |
| `ai_assistant.anythingllm_key` | (empty) | AnythingLLM API key |
| `ai_assistant.anythingllm_workspace` | (empty) | Workspace slug |
| `ai_assistant.welcome_message` | "¡Hola! Soy tu asistente..." | Chat welcome message |
| `ai_assistant.max_history` | 20 | Messages sent to LLM context |

## Module Structure
```
controllers/ai_chat.py              → API endpoints (JSON-RPC + HTTP routes)
models/ai_chat.py                   → Core service: LLM (OpenRouter via OpenAI-compatible API), Knowledge, DuckDuckGo
models/res_config_settings.py       → Settings backend (fields linked to ir.config_parameter)
static/src/js/ai_assistant.js       → Main chat widget (legacy Odoo 17 widget system)
static/src/js/systray.js            → Systray icon button

static/src/components/ai_service.js → RPC abstraction layer (shared by legacy/OWL)
static/src/xml/ai_chat.xml          → OWL/QWeb templates
```

**Frontend architecture quirk:** The module uses Odoo 17's legacy widget system (`odoo.define`, `web.AbstractAction`) but includes `static/src/components/ai_service.js` as a shared RPC service layer. The manifest only registers `static/src/js/*.js` and `static/src/css/*.css` in `web.assets_backend`; `ai_service.js` is imported by the legacy JS files, not declared in the manifest assets.

## API Endpoints
All routes are under `/ai_assistant/` and require authenticated user (`auth="user"`).

| Endpoint | Type | Method | Description |
|----------|------|--------|-------------|
| `/ai_assistant/chat` | json | POST | Send message, returns `{response, sources, conversation_id, message_id}` |
| `/ai_assistant/conversations` | json | POST | List user's conversations |
| `/ai_assistant/conversation/<id>` | json | GET | Get messages of a conversation |
| `/ai_assistant/conversation/<id>/delete` | json | POST | Delete a conversation |
| `/ai_assistant/config` | json | GET | Get frontend config (flags, welcome message) |
| `/ai_assistant/context` | json | POST | Get contextual info about current Odoo page |

## Key Conventions & Quirks
- **Settings storage:** Uses `ir.config_parameter` exclusively. `res.config.settings` fields have `config_parameter=` attribute.
- **Async handling:** Uses `nest_asyncio` inside `ai_chat.py` because Odoo's threaded request handlers may already have a running asyncio event loop. Centralized in `AIAssistantService._run_async(coro)`; do not duplicate the `try/except RuntimeError` + `nest_asyncio.apply()` pattern elsewhere.
- **Knowledge search dual mode:** `models/ai_chat.py` checks `knowledge_search_mode` parameter. If `local`, searches `knowledge.article` (only if `knowledge` module installed). If `anythingllm`, calls external REST API.
- **External deps are optional at import:** All external Python libs (`duckduckgo-search`) are wrapped in `try/except ImportError` blocks. The module installs and loads without them, but features fail gracefully at runtime.
- **Security:** Two groups — `group_ai_assistant_user` (implied `base.group_user`) and `group_ai_assistant_manager`. Users have full CRUD on `ai.chat.conversation` and `ai.chat.message`.
- **Controller security:** CRUD operations on `ai.chat.conversation` and `ai.chat.message` rely on ACLs (`group_ai_assistant_user`). `.sudo()` is reserved for `ir.config_parameter` reads and `ir.attachment` audio streaming.

## Testing
No unit tests are present. Testing is manual:
1. Install module in Odoo
2. Configure OpenRouter API key in Settings
3. Test chat via UI (systray icon or FAB)
4. Check Odoo logs: `tail -f /var/log/odoo/odoo-server.log`

## Update / Upgrade
```bash
# After code changes, restart Odoo with update flag:
python3 /opt/odoo/odoo-bin -u odoo_ai_assistant -d YOUR_DATABASE
```