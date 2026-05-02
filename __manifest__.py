# -*- coding: utf-8 -*-
{
    "name": "AI Assistant",
    "version": "17.0.1.0.0",
    "category": "Productivity",
    "summary": "Asistente de IA integrado en Odoo con chat flotante, voz y contexto automático",
    "description": """
        Asistente de IA para Odoo
        =========================

        Características principales:
        - Chat con IA: Respuestas inteligentes sobre el uso de Odoo (OpenRouter / LLM configurable)
        - Input de voz (Vosk): Reconocimiento de voz local, sin enviar audio a servicios externos
        - Respuesta hablada (edge-tts): Voces neuronales de Microsoft Edge, gratis y de alta calidad
        - Contexto automático: Detecta el módulo, modelo y registro que el usuario está viendo
        - Integración con Knowledge: Busca artículos relevantes del módulo Knowledge de Odoo
        - Búsqueda inteligente con DuckDuckGo: Busca información relevante en la web

        Compatible con Odoo 17, 18 y 19.
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
        "security/ir.model.access.csv",
        "data/default_data.xml",
        "data/cron_cleanup.xml",
        "views/ai_chat_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "odoo_ai_assistant/static/src/css/ai_chat.css",
            "odoo_ai_assistant/static/src/js/ai_assistant.js",
            "odoo_ai_assistant/static/src/js/systray.js",
            "odoo_ai_assistant/static/src/js/voice_input.js",
        ],
        "web.assets_qweb": [
            "odoo_ai_assistant/static/src/xml/ai_chat.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}
