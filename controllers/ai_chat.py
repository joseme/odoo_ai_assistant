import json
import logging
import base64

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)


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
                    body: JSON.stringify({jsonrpc: "2.0", method: "call", params: {message: msg, conversation_id: convId}})
                });
                var result = await response.json();
                console.log(">>> Result:", result);
                messagesDiv.lastChild.remove();
                // Rutas type="json" de Odoo envuelven la respuesta en 'result'
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
    @http.route("/ai_assistant/chat", type="json", auth="user", methods=["POST"], csrf=False)
    def chat(self, message="", conversation_id=None, context_info=None, **kwargs):
        """Procesa un mensaje del usuario y devuelve la respuesta de la IA.

        type="json" para que el frontend use el servicio `rpc` de Odoo:
        el servicio `http` envía FormData (null → "null", dict → "[object Object]"),
        mientras que JSON-RPC preserva tipos (None, dict, int).
        """
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
        enriched_context = context_info or {}
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

        # Convertir Markdown de la respuesta a texto plano
        response_text = self._markdown_to_plain(result["response"])

        return {
            "response": response_text,
            "sources": result["sources"],
            "conversation_id": conversation.id,
            "message_id": assistant_message.id,
        }

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
        return [{"id": c.id, "title": c.title, "date": c.create_date} for c in conversations]

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

    @http.route("/ai_assistant/conversation/<int:conversation_id>/delete", type="json", auth="user")
    def delete_conversation(self, conversation_id):
        """Elimina una conversación del usuario actual.

        Ruta documentada en AGENTS.md pero nunca implementada; el frontend
        la llamaba y recibía 404 (error silencioso).
        """
        user = request.env.user
        conversation = request.env["ai.chat.conversation"].search(
            [("id", "=", conversation_id), ("user_id", "=", user.id)], limit=1
        )
        if conversation:
            conversation.unlink()
        return {"success": True}

    @http.route("/ai_assistant/config", type="json", auth="user")
    def get_config(self):
        """Devuelve configuración para el frontend."""
        params = request.env["ir.config_parameter"].sudo()
        return {
            "welcome_message": params.get_param("ai_assistant.welcome_message", ""),
            "web_search_enabled": params.get_param("ai_assistant.web_search_enabled", "True") == "True",
            "knowledge_search_enabled": params.get_param("ai_assistant.knowledge_search_enabled", "True") == "True",
        }

    @http.route("/ai_assistant/context", type="json", auth="user")
    def get_context(self, model="", record_id=None, action=None, view_type=None):
        """Devuelve contexto enriquecido de la página actual.

        La ruta estaba documentada en AGENTS.md pero nunca implementada;
        el frontend la llamaba y recibía 404 (usaba el contexto local como fallback).
        """
        ctx = {
            "model": model or "",
            "record_id": record_id,
            "action": action or "",
            "view_type": view_type or "",
            "module": "",
        }
        if model and model in request.env:
            try:
                ctx["module"] = request.env[model]._module
                if record_id:
                    rec = request.env[model].browse(int(record_id))
                    if rec.exists():
                        ctx["name"] = rec.display_name
            except (ValueError, TypeError):
                pass
        return ctx