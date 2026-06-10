def set_default_config_parameters(cr, registry):
    env = registry(cr)
    defaults = {
        "ai_assistant.openrouter_api_key": "",
        "ai_assistant.model_name": "openai/gpt-4o-mini",
        "ai_assistant.tts_voice": "es-MX-JorgeNeural",
        "ai_assistant.tts_language": "es",
        "ai_assistant.voice_enabled": "True",
        "ai_assistant.tts_enabled": "True",
        "ai_assistant.web_search_enabled": "True",
        "ai_assistant.knowledge_search_enabled": "True",
        "ai_assistant.welcome_message": "¡Hola! Soy tu asistente de IA en Odoo. ¿En qué puedo ayudarte?",
        "ai_assistant.max_history": "20",
        "ai_assistant.vosk_model": "vosk-model-small-es-0.42",
        "ai_assistant.vosk_model_path": "/opt/vosk-models",
    }
    ICP = env["ir.config_parameter"].sudo()
    for key, value in defaults.items():
        ICP.set_param(key, value)
