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
static/src/js/ai_assistant.js       → Main chat widget (OWL component, mounted as a service)
static/src/js/systray.js            → Systray icon button

static/src/components/ai_service.js → RPC abstraction layer (OWL service wrapper)
static/src/xml/ai_chat.xml          → OWL templates
```

**Frontend architecture:** Pure OWL (Odoo 17+). `ai_assistant.js` exports an OWL `Component` registered in the `main_components` registry (mounted inside the webclient App, so OWL templates resolve; a standalone `mount()` would create a fresh App without them). It replaces the old FAB + legacy widget. `ai_service.js` wraps the backend endpoints using Odoo's native services (`env.services.rpc` for all routes — including the chat route, which is `type="json"`; the `http` service would send FormData and destroy nested types). All JS is registered in `web.assets_backend`.

**Upstream Odoo 17 fix (login sin estilo):** builds recientes de Odoo 17 fallan la compilación de `web.assets_frontend` con `Undefined variable: "$gray-200"/"$black"` en instalaciones mínimas (base+web SIN `web_editor`, que es quien define esas variables vía `$grays`). `data/ir_asset.xml` inyecta `static/src/scss/frontend_fix.scss` al inicio del bundle (`prepend`, sequence < 16 → antes de los manifests de módulos). No tocar ese archivo sin verificar en instalación mínima.

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
- **Security:** Two groups — `group_ai_assistant_user` (implied `base.group_user`) and `group_ai_assistant_manager`. Users have full CRUD on `ai.chat.conversation` and `ai.chat.message`. A third ACL row grants `base.group_system` (Technical Features) full access — required since Odoo 17 removed the implicit admin superuser, so admins respect ACLs and would otherwise be locked out until a group is assigned.
- **Controller security:** CRUD operations on `ai.chat.conversation` and `ai.chat.message` rely on ACLs (`group_ai_assistant_user`). `.sudo()` is reserved for `ir.config_parameter` reads and `ir.attachment` audio streaming. `/ai_assistant/chat` is `type="json"` (JSON-RPC) — the Odoo `http` service would send FormData and destroy nested types (`null` → `"null"`, dict → `"[object Object]"`).

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