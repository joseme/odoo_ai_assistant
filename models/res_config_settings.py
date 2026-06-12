# -*- coding: utf-8 -*-
from odoo import api, fields, models

# Modelos populares de OpenRouter para el selector
POPULAR_MODELS = [
    ("openai/gpt-4o-mini", "OpenAI GPT-4o Mini"),
    ("openai/gpt-4o", "OpenAI GPT-4o"),
    ("openai/o1", "OpenAI o1"),
    ("anthropic/claude-sonnet-4", "Claude Sonnet 4"),
    ("anthropic/claude-haiku-4", "Claude Haiku 4"),
    ("google/gemini-2.0-flash", "Gemini 2.0 Flash"),
    ("google/gemini-2.0-flash-lite", "Gemini 2.0 Flash Lite"),
    ("meta-llama/llama-4-scout", "Llama 4 Scout"),
    ("meta-llama/llama-4-maverick", "Llama 4 Maverick"),
    ("deepseek/deepseek-v4-flash", "DeepSeek V4 Flash"),
    ("mistral/mistral-large", "Mistral Large"),
    ("cohere/command-r", "Command R+"),
    ("qwen/qwen-2.5-72b", "Qwen 2.5 72B"),
    ("_custom_", "Otro (escribe el modelo manualmente)"),
]


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # --- API Configuration ---
    ai_assistant_openrouter_api_key = fields.Char(
        string="OpenRouter API Key",
        config_parameter="ai_assistant.openrouter_api_key",
        help="Clave API de OpenRouter para el asistente de IA. Obtén una en https://openrouter.ai/keys",
    )
    ai_assistant_model_name = fields.Selection(
        POPULAR_MODELS,
        string="Modelo de IA",
        config_parameter="ai_assistant.model_name",
        default="openai/gpt-4o-mini",
        help="Modelo de IA a utilizar. OpenRouter soporta cientos de modelos: proveedor/modelo",
    )
    ai_assistant_custom_model = fields.Char(
        string="Modelo personalizado",
        config_parameter="ai_assistant.custom_model",
        help="Nombre del modelo personalizado si seleccionaste 'Otro' arriba. "
             "Ej: openai/gpt-4o, anthropic/claude-sonnet, deepseek/deepseek-v4-flash",
    )

    @api.depends("ai_assistant_model_name")
    def _compute_custom_model_visibility(self):
        for rec in self:
            rec.ai_assistant_custom_model_visible = rec.ai_assistant_model_name == "_custom_"

    ai_assistant_custom_model_visible = fields.Boolean(
        compute="_compute_custom_model_visibility",
    )

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        # Leer el modelo actual de ir.config_parameter
        current_model = self.env["ir.config_parameter"].sudo().get_param(
            "ai_assistant.model_name", "openai/gpt-4o-mini"
        )
        # Si el modelo actual no está en la lista de populares, seleccionar "_custom_"
        popular_ids = [m[0] for m in POPULAR_MODELS]
        if current_model in popular_ids:
            res["ai_assistant_model_name"] = current_model
            res["ai_assistant_custom_model"] = False
        else:
            res["ai_assistant_model_name"] = "_custom_"
            res["ai_assistant_custom_model"] = current_model
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        selected = self.ai_assistant_model_name
        if selected == "_custom_":
            actual_model = self.ai_assistant_custom_model or "openai/gpt-4o-mini"
        else:
            actual_model = selected
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.model_name", actual_model
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
