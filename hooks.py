def set_default_config_parameters(cr, registry):
    env = registry(cr)
    defaults = {
        "ai_assistant.openrouter_api_key": "",
        "ai_assistant.model_name": "openai/gpt-4o-mini",
        "ai_assistant.web_search_enabled": "True",
        "ai_assistant.knowledge_search_enabled": "True",
        "ai_assistant.welcome_message": "¡Hola! Soy tu asistente de IA en Odoo. ¿En qué puedo ayudarte?",
        "ai_assistant.max_history": "20",
    }
    ICP = env["ir.config_parameter"].sudo()
    for key, value in defaults.items():
        ICP.set_param(key, value)
