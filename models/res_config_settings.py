# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # --- API Configuration ---
    ai_assistant_openrouter_api_key = fields.Char(
        string="OpenRouter API Key",
        config_parameter="ai_assistant.openrouter_api_key",
        help="Clave API de OpenRouter para el asistente de IA.",
    )
    ai_assistant_model_name = fields.Char(
        string="Modelo de IA",
        config_parameter="ai_assistant.model_name",
        default="openai/gpt-4o-mini",
        help="Modelo de IA a utilizar (formato OpenRouter: proveedor/modelo). Ej: openai/gpt-4o, anthropic/claude-sonnet",
    )

    # --- Voice Configuration ---
    ai_assistant_tts_voice = fields.Char(
        string="Voz TTS",
        config_parameter="ai_assistant.tts_voice",
        default="es-MX-JorgeNeural",
        help="Nombre de la voz para text-to-speech (edge-tts). Ej: es-MX-JorgeNeural, es-ES-AlvaroNeural",
    )
    ai_assistant_tts_language = fields.Char(
        string="Idioma TTS",
        config_parameter="ai_assistant.tts_language",
        default="es",
        help="Código de idioma para filtrar voces TTS disponibles. Ej: es, en, fr, pt",
    )
    ai_assistant_voice_enabled = fields.Boolean(
        string="Reconocimiento de voz habilitado",
        config_parameter="ai_assistant.voice_enabled",
        default=True,
        help="Habilita el reconocimiento de voz con Vosk (local).",
    )
    ai_assistant_tts_enabled = fields.Boolean(
        string="Respuesta hablada habilitada",
        config_parameter="ai_assistant.tts_enabled",
        default=True,
        help="Habilita la respuesta hablada con edge-tts.",
    )

    # --- Search Configuration ---
    ai_assistant_knowledge_search_mode = fields.Selection(
        [
            ("local", "Odoo Knowledge (Local)"),
            ("anythingllm", "AnythingLLM API"),
        ],
        string="Modo de Búsqueda de Conocimiento",
        config_parameter="ai_assistant.knowledge_search_mode",
        default="local",
        help="Selecciona la fuente de conocimiento para el asistente.",
    )
    ai_assistant_anythingllm_url = fields.Char(
        string="AnythingLLM API URL",
        config_parameter="ai_assistant.anythingllm_url",
        help="URL de la API de AnythingLLM. Ej: http://localhost:3001",
    )
    ai_assistant_anythingllm_key = fields.Char(
        string="AnythingLLM API Key",
        config_parameter="ai_assistant.anythingllm_key",
        help="Clave de API para autenticación con AnythingLLM.",
    )
    ai_assistant_anythingllm_workspace = fields.Char(
        string="AnythingLLM Workspace ID",
        config_parameter="ai_assistant.anythingllm_workspace",
        help="ID/Slug del Workspace de AnythingLLM.",
    )
    ai_assistant_web_search_enabled = fields.Boolean(
        string="Búsqueda web habilitada",
        config_parameter="ai_assistant.web_search_enabled",
        default=True,
        help="Habilita la búsqueda en DuckDuckGo para enriquecer las respuestas.",
    )
    ai_assistant_knowledge_search_enabled = fields.Boolean(
        string="Búsqueda en Knowledge habilitada",
        config_parameter="ai_assistant.knowledge_search_enabled",
        default=True,
        help="Habilita la búsqueda de conocimiento (Local o AnythingLLM).",
    )

    # --- Chat Configuration ---
    ai_assistant_welcome_message = fields.Char(
        string="Mensaje de bienvenida",
        config_parameter="ai_assistant.welcome_message",
        default="¡Hola! Soy tu asistente de IA en Odoo. ¿En qué puedo ayudarte?",
        help="Mensaje que se muestra al abrir el chat por primera vez.",
    )
    ai_assistant_max_history = fields.Integer(
        string="Mensajes de historial",
        config_parameter="ai_assistant.max_history",
        default=20,
        help="Número máximo de mensajes de historial enviados al LLM.",
    )

    # --- Vosk Configuration ---
    ai_assistant_vosk_model_path = fields.Char(
        string="Ruta modelos Vosk",
        config_parameter="ai_assistant.vosk_model_path",
        default="/opt/vosk-models",
        help="Ruta base donde se encuentran los modelos de Vosk. Ej: /opt/vosk-models",
    )
    ai_assistant_vosk_model = fields.Char(
        string="Modelo Vosk",
        config_parameter="ai_assistant.vosk_model",
        default="vosk-model-small-es-0.42",
        help="Nombre del modelo de Vosk para reconocimiento de voz. Ej: vosk-model-small-es-0.42",
    )
