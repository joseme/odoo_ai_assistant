{
    "name": "AI Assistant",
    "version": "17.0.1.1.0",
    "category": "Productivity",
    "icon": "odoo_ai_assistant/static/description/icon.png",
    "summary": "Asistente de IA flotante con FAB y atajo Ctrl+Shift+H",
    "description": """
        Asistente de IA para Odoo
        =========================

        Chat con IA y contexto automático.
    """,
    "author": "AI Assistant Dev",
    "website": "https://github.com/odoo-ai-assistant",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "external_dependencies": {
        "python": [
            "duckduckgo-search",
        ],
    },
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_asset.xml",
        "views/ai_chat_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "post_init_hook": "set_default_config_parameters",
    "assets": {
        "web.assets_backend": [
            "odoo_ai_assistant/static/src/css/ai_chat.css",
            "odoo_ai_assistant/static/src/components/ai_service.js",
            "odoo_ai_assistant/static/src/js/ai_assistant.js",
            "odoo_ai_assistant/static/src/js/systray.js",
            "odoo_ai_assistant/static/src/xml/ai_chat.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
