{
    "name": "AI Assistant",
    "version": "17.0.1.1.0",
    "category": "Productivity",
    "icon": "odoo_ai_assistant/static/description/icon.png",
    "summary": "Asistente de IA flotante con FAB y atajo Ctrl+Shift+H",
    "description": """
        Asistente de IA para Odoo
        =========================

        Chat con IA, voz, TTS y contexto automático.
    """,
    "author": "AI Assistant Dev",
    "website": "https://github.com/odoo-ai-assistant",
    "license": "LGPL-3",
    "depends": ["base", "web"],
    "external_dependencies": {
        "python": [
            "duckduckgo-search",
            "edge-tts",
            "vosk",
        ],
    },
    "data": [
        "security/security.xml",
        "security/ir_rule.xml",
        "security/ir.model.access.csv",
        "data/cron_cleanup.xml",
        "views/ai_chat_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "post_init_hook": "set_default_config_parameters",
    "assets": {
        "web.assets_web": [
            "odoo_ai_assistant/static/src/css/ai_chat.css",
            "odoo_ai_assistant/static/src/js/fab.js",
            "odoo_ai_assistant/static/src/js/systray.js",
            "odoo_ai_assistant/static/src/xml/ai_chat.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
