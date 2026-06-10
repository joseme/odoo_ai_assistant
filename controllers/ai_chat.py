import json
import logging
import base64
import asyncio
import os
import tempfile
import struct

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

# Variable global para cachear el modelo Vosk
_vosk_model = None

# Intentar importar Vosk
try:
    import vosk
    VOSK_AVAILABLE = True
    _logger.info("Vosk disponible para reconocimiento de voz offline")
except ImportError:
    VOSK_AVAILABLE = False
    _logger.warning("vosk no está instalado. Instale con: pip install vosk")

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    _logger.warning("edge-tts no está instalado. Instale con: pip install edge-tts")


class AIChatController(http.Controller):
    """Controlador principal del Asistente de IA."""

    # ------------------------------------------------------------------ #
    #  Vista HTML del chat (standalone)
    # ------------------------------------------------------------------ #
    @http.route("/ai_assistant/ui", type="http", auth="user", methods=["GET"])
    def chat_ui(self):
        """Muestra una UI standalone del chat."""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>AI Assistant</title>
    <meta charset="utf-8">
    <style>
        body { font-family: sans-serif; padding: 20px; background: #f5f5f5; }
        .chat-container { max-width: 500px; margin: 0 auto; background: white; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { background: #7c3aed; color: white; padding: 20px; border-radius: 12px 12px 0 0; }
        .messages { height: 400px; overflow-y: auto; padding: 20px; }
        .input-area { display: flex; padding: 15px; border-top: 1px solid #eee; }
        input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 6px; }
        button { margin-left: 10px; padding: 12px 20px; background: #7c3aed; color: white; border: none; border-radius: 6px; cursor: pointer; }
        .message { margin-bottom: 15px; padding: 12px 16px; border-radius: 12px; max-width: 80%; }
        .message-user { background: #7c3aed; color: white; margin-left: auto; }
        .message-assistant { background: #f1f5f9; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="header">
            <h1>AI Assistant</h1>
        </div>
        <div class="messages" id="messages"></div>
        <div class="input-area">
            <input type="text" id="input" placeholder="Escribe tu mensaje..."/>
            <button id="send">Enviar</button>
        </div>
    </div>
    <script>
        var convId = null;
        var input = document.getElementById("input");
        var sendBtn = document.getElementById("send");
        var messagesDiv = document.getElementById("messages");
        
        function addMessage(content, role) {
            var div = document.createElement("div");
            div.className = "message message-" + role;
            div.textContent = content;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        async function sendMessage() {
            var msg = input.value.trim();
            if (!msg) return;
            addMessage(msg, "user");
            input.value = "";
            addMessage("...", "assistant");
            try {
                var response = await fetch("/ai_assistant/chat", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({message: msg, conversation_id: convId})
                });
                var result = await response.json();
                console.log(">>> Result:", result);
                messagesDiv.lastChild.remove();
                // Odoo json responses are wrapped in 'result'
                var text = result.result ? (result.result.response || result.error || JSON.stringify(result)) : JSON.stringify(result);
                addMessage(text, "assistant");
                convId = result.result ? result.result.conversation_id : convId;
            } catch(e) { addMessage("Error: " + e.message, "assistant"); }
        }
        sendBtn.onclick = sendMessage;
        input.onkeydown = function(e) { if (e.key === "Enter") sendMessage(); };
    </script>
</body>
</html>"""
        return request.make_response(html, headers=[("Content-Type", "text/html; charset=utf-8")])

    # ------------------------------------------------------------------ #
    #  Chat - Envío de mensajes
    # ------------------------------------------------------------------ #
    @http.route("/ai_assistant/chat", type="http", auth="user", methods=["POST"], csrf=False)
    def chat(self):
        """Procesa un mensaje del usuario y devuelve la respuesta de la IA."""
        raw = json.loads(request.httprequest.data)
        message = raw.get("message", "")
        conversation_id = raw.get("conversation_id")
        user = request.env.user
        AIAssistantService = request.env["ai.assistant.service"]

        # Obtener o crear conversación
        if conversation_id:
            conversation = request.env["ai.chat.conversation"].sudo().search(
                [("id", "=", conversation_id), ("user_id", "=", user.id)], limit=1
            )
            if not conversation:
                conversation = request.env["ai.chat.conversation"].sudo().create({
                    "user_id": user.id,
                })
        else:
            conversation = request.env["ai.chat.conversation"].sudo().create({
                "user_id": user.id,
            })

        # Crear mensaje del usuario
        request.env["ai.chat.message"].sudo().create({
            "conversation_id": conversation.id,
            "role": "user",
            "content": message,
        })

        # Obtener historial
        history_messages = request.env["ai.chat.message"].sudo().search_read(
            [("conversation_id", "=", conversation.id)],
            ["role", "content"],
            order="create_date asc",
        )
        history_messages = [{"role": m["role"], "content": m["content"]} for m in history_messages]

        # Enriquecer contexto
        enriched_context = raw.get("context_info", {})
        search_knowledge = request.env["ir.config_parameter"].sudo().get_param(
            "ai_assistant.knowledge_search_enabled", "True"
        ) == "True"
        search_web = request.env["ir.config_parameter"].sudo().get_param(
            "ai_assistant.web_search_enabled", "True"
        ) == "True"

        # Generar respuesta
        result = AIAssistantService.sudo().generate_response(
            messages=history_messages,
            context_info=enriched_context,
            search_knowledge=search_knowledge,
            search_web=search_web,
        )

        # Crear mensaje del asistente
        assistant_message = request.env["ai.chat.message"].sudo().create({
            "conversation_id": conversation.id,
            "role": "assistant",
            "content": result["response"],
            "sources": json.dumps(result["sources"]) if result["sources"] else False,
        })

        # Generar TTS si está habilitado
        tts_enabled = request.env["ir.config_parameter"].sudo().get_param(
            "ai_assistant.tts_enabled", "True"
        ) == "True"
        tts_attachment_id = False
        if tts_enabled and EDGE_TTS_AVAILABLE:
            tts_attachment_id = AIAssistantService.sudo().generate_tts(result["response"])
            if tts_attachment_id:
                assistant_message.sudo().write({"audio_attachment_id": tts_attachment_id})

        # Convertir Markdown de la respuesta a texto plano
        response_text = self._markdown_to_plain(result["response"])

        return request.make_response(
            json.dumps({
                "response": response_text,
                "sources": result["sources"],
                "conversation_id": conversation.id,
                "message_id": assistant_message.id,
                "tts_attachment_id": tts_attachment_id,
            }),
            headers=[("Content-Type", "application/json")],
        )

    @staticmethod
    def _markdown_to_plain(text):
        """Convierte Markdown a texto plano con atributos de formato."""
        import re
        
        # Bloques de código: ``` ... ```
        text = re.sub(r'```(?:\w+)?\n?(.*?)\n?```', r'\1', text, flags=re.DOTALL)
        
        # Código inline: `texto`
        text = re.sub(r'`([^`]+)`', r"'\1'", text)
        
        # Negrita: **texto** o __texto__
        text = re.sub(r'\*\*(.+?)\*\*', r'«\1»', text)
        text = re.sub(r'__(.+?)__', r'«\1»', text)
        
        # Cursiva: *texto* o _texto_
        text = re.sub(r'(?<!\w)\*(.+?)\*(?!\w)', r'_\1_', text)
        text = re.sub(r'(?<!\w)_(.+?)_(?!\w)', r'_\1_', text)
        
        # Títulos: ### texto -> TEXTO
        text = re.sub(r'^#{1,6}\s+(.+)$', lambda m: m.group(1).upper(), text, flags=re.MULTILINE)
        
        # Links: [texto](url) -> texto (url)
        text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1 (\2)', text)
        
        # Listas numeradas: 1. item -> - item
        text = re.sub(r'^\d+\.\s+', '- ', text, flags=re.MULTILINE)
        
        return text.strip()

    # ------------------------------------------------------------------ #
    #  Chat - Obtener historial de conversación
    # ------------------------------------------------------------------ #
    @http.route("/ai_assistant/conversations", type="json", auth="user", methods=["POST"])
    def get_conversations(self, limit=20):
        """Obtiene las conversaciones del usuario actual."""
        user = request.env.user
        conversations = request.env["ai.chat.conversation"].search(
            [("user_id", "=", user.id)],
            order="create_date desc",
            limit=limit,
        )
        return [{"id": c.id, "name": c.name, "date": c.create_date} for c in conversations]

    @http.route("/ai_assistant/conversation/<int:conversation_id>", type="json", auth="user")
    def get_conversation(self, conversation_id):
        """Obtiene los mensajes de una conversación."""
        user = request.env.user
        conversation = request.env["ai.chat.conversation"].search(
            [("id", "=", conversation_id), ("user_id", "=", user.id)], limit=1
        )
        if not conversation:
            return {"error": "Conversación no encontrada"}
        
        messages = request.env["ai.chat.message"].search_read(
            [("conversation_id", "=", conversation_id)],
            ["role", "content", "create_date"],
            order="create_date asc",
        )
        return {"conversation_id": conversation_id, "messages": messages}

    @http.route("/ai_assistant/config", type="json", auth="user")
    def get_config(self):
        """Devuelve configuración para el frontend."""
        params = request.env["ir.config_parameter"].sudo()
        return {
            "welcome_message": params.get_param("ai_assistant.welcome_message", ""),
            "tts_enabled": params.get_param("ai_assistant.tts_enabled", "True") == "True",
            "voice_enabled": params.get_param("ai_assistant.voice_enabled", "True") == "True",
            "web_search_enabled": params.get_param("ai_assistant.web_search_enabled", "True") == "True",
            "knowledge_search_enabled": params.get_param("ai_assistant.knowledge_search_enabled", "True") == "True",
        }

    @http.route("/ai_assistant/tts", type="json", auth="user", methods=["POST"], csrf=False)
    def generate_tts(self):
        """Genera audio TTS."""
        text = request.params.get("text", "")
        if not text:
            return {"error": "Texto vacío"}
        
        if not EDGE_TTS_AVAILABLE:
            return {"error": "edge-tts no está instalado"}
        
        AIAssistantService = request.env["ai.assistant.service"]
        attachment_id = AIAssistantService.sudo().generate_tts(text)
        
        return {
            "attachment_id": attachment_id,
            "audio_url": f"/ai_assistant/audio/{attachment_id}" if attachment_id else None,
        }

    @http.route("/ai_assistant/audio/<int:attachment_id>", type="http", auth="user")
    def stream_audio(self, attachment_id):
        """Serve audio TTS."""
        attachment = request.env["ir.attachment"].browse(attachment_id).exists()
        if not attachment:
            return request.not_found()
        
        return request.make_response(
            base64.b64decode(attachment.datas),
            headers=[("Content-Type", "audio/mpeg"), ("Content-Disposition", "inline")]
        )

    # ------------------------------------------------------------------ #
    #  Voz - Transcripción con Vosk (offline)
    # ------------------------------------------------------------------ #
    @http.route("/ai_assistant/transcribe", type="http", auth="user", methods=["POST"], csrf=False)
    def transcribe_audio(self):
        """Recibe audio WebM/WAV y lo transcribe con Vosk."""
        global _vosk_model
        
        if not VOSK_AVAILABLE:
            return request.make_response(
                json.dumps({"error": "Vosk no está instalado en el servidor"}),
                headers=[("Content-Type", "application/json")]
            )
        
        # Cargar modelo Vosk (cacheado)
        if _vosk_model is None:
            try:
                model_path = request.env["ir.config_parameter"].sudo().get_param(
                    "ai_assistant.vosk_model_path", "/opt/vosk-models"
                )
                model_name = request.env["ir.config_parameter"].sudo().get_param(
                    "ai_assistant.vosk_model", "vosk-model-small-es-0.42"
                )
                full_path = os.path.join(model_path, model_name)
                _logger.info("Cargando modelo Vosk desde: %s", full_path)
                _vosk_model = vosk.Model(full_path)
            except Exception as e:
                _logger.error("Error cargando modelo Vosk: %s", e)
                return request.make_response(
                    json.dumps({"error": f"Error cargando modelo Vosk: {str(e)}"}),
                    headers=[("Content-Type", "application/json")]
                )
        
        # Leer audio del body
        audio_data = request.httprequest.data
        if not audio_data:
            return request.make_response(
                json.dumps({"error": "No se recibió audio"}),
                headers=[("Content-Type", "application/json")]
            )
        
        try:
            # Vosk espera PCM 16kHz 16-bit mono
            # Si es WebM, necesitamos convertirlo - pero por ahora asumimos WAV/PCM
            rec = vosk.KaldiRecognizer(_vosk_model, 16000)
            
            # Si es un archivo WAV, saltar cabecera (44 bytes)
            if audio_data[:4] == b'RIFF':
                audio_pcm = audio_data[44:]
            else:
                audio_pcm = audio_data
            
            # Procesar en chunks para no saturar memoria
            chunk_size = 4000
            for i in range(0, len(audio_pcm), chunk_size):
                chunk = audio_pcm[i:i+chunk_size]
                rec.AcceptWaveform(chunk)
            
            result = json.loads(rec.FinalResult())
            text = result.get("text", "")
            
            _logger.info("Vosk transcripción: '%s'", text[:100])
            
            return request.make_response(
                json.dumps({"text": text, "success": bool(text)}),
                headers=[("Content-Type", "application/json")]
            )
        except Exception as e:
            _logger.error("Error en transcripción Vosk: %s", e)
            return request.make_response(
                json.dumps({"error": f"Error de transcripción: {str(e)}"}),
                headers=[("Content-Type", "application/json")]
            )