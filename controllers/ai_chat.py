# -*- coding: utf-8 -*-
import json
import logging
import base64
import asyncio
import os
import tempfile

from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError, AccessError

_logger = logging.getLogger(__name__)

# Intentar importar Vosk
try:
    import vosk
    VOSK_AVAILABLE = True
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
    #  Chat - Envío de mensajes
    # ------------------------------------------------------------------ #
    @http.route("/ai_assistant/chat", type="json", auth="user", methods=["POST"], csrf=False)
    def chat(self, message, conversation_id=None, context_info=None):
        """Procesa un mensaje del usuario y devuelve la respuesta de la IA.

        Args:
            message: Texto del mensaje del usuario
            conversation_id: ID de la conversación (opcional, crea una nueva si no se proporciona)
            context_info: Diccionario con información del contexto actual de Odoo

        Returns:
            Diccionario con la respuesta, sources y conversation_id
        """
        user = request.env.user
        AIAssistantService = request.env["ai.assistant.service"]

        # Obtener o crear conversación
        if conversation_id:
            conversation = request.env["ai.chat.conversation"].search(
                [("id", "=", conversation_id), ("user_id", "=", user.id)], limit=1
            )
            if not conversation:
                conversation = request.env["ai.chat.conversation"].create({
                    "user_id": user.id,
                    "context_module": context_info.get("module", "") if context_info else "",
                    "context_model": context_info.get("model", "") if context_info else "",
                    "context_record_id": context_info.get("record_id", 0) if context_info else 0,
                })
        else:
            conversation = request.env["ai.chat.conversation"].create({
                "user_id": user.id,
                "context_module": context_info.get("module", "") if context_info else "",
                "context_model": context_info.get("model", "") if context_info else "",
                "context_record_id": context_info.get("record_id", 0) if context_info else 0,
            })

        # Crear mensaje del usuario
        request.env["ai.chat.message"].create({
            "conversation_id": conversation.id,
            "role": "user",
            "content": message,
        })

        # Enriquecer contexto con información del registro si está disponible
        enriched_context = dict(context_info) if context_info else {}
        if enriched_context.get("model") and enriched_context.get("record_id"):
            record_context = AIAssistantService.get_record_context(
                enriched_context["model"], int(enriched_context["record_id"])
            )
            enriched_context["record_data"] = record_context

        # Obtener historial de conversación
        history_messages = []
        for msg in conversation.message_ids:
            history_messages.append({
                "role": msg.role,
                "content": msg.content,
            })

        # Configurar búsqueda
        search_knowledge = request.env["ir.config_parameter"].sudo().get_param(
            "ai_assistant.knowledge_search_enabled", "True"
        ) == "True"
        search_web = request.env["ir.config_parameter"].sudo().get_param(
            "ai_assistant.web_search_enabled", "True"
        ) == "True"

        # Generar respuesta
        result = AIAssistantService.generate_response(
            messages=history_messages,
            context_info=enriched_context,
            search_knowledge=search_knowledge,
            search_web=search_web,
        )

        # Crear mensaje del asistente
        assistant_message = request.env["ai.chat.message"].create({
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
            tts_attachment_id = AIAssistantService.generate_tts(result["response"])
            if tts_attachment_id:
                assistant_message.write({"audio_attachment_id": tts_attachment_id})

        return {
            "response": result["response"],
            "sources": result["sources"],
            "conversation_id": conversation.id,
            "message_id": assistant_message.id,
            "tts_attachment_id": tts_attachment_id,
        }

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
        return [
            {
                "id": conv.id,
                "title": conv.title or "Sin título",
                "message_count": conv.message_count,
                "create_date": conv.create_date.isoformat() if conv.create_date else False,
                "context_module": conv.context_module,
                "context_model": conv.context_model,
            }
            for conv in conversations
        ]

    @http.route("/ai_assistant/conversation/<int:conversation_id>", type="json", auth="user")
    def get_conversation(self, conversation_id):
        """Obtiene los mensajes de una conversación específica."""
        user = request.env.user
        conversation = request.env["ai.chat.conversation"].search(
            [("id", "=", conversation_id), ("user_id", "=", user.id)], limit=1
        )
        if not conversation:
            return {"error": "Conversación no encontrada"}

        return {
            "id": conversation.id,
            "title": conversation.title or "Sin título",
            "messages": [
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "has_audio": msg.has_audio,
                    "audio_url": f"/ai_assistant/audio/{msg.audio_attachment_id.id}" if msg.audio_attachment_id else False,
                    "sources": json.loads(msg.sources) if msg.sources else [],
                    "create_date": msg.create_date.isoformat() if msg.create_date else False,
                }
                for msg in conversation.message_ids
            ],
        }

    # ------------------------------------------------------------------ #
    #  Chat - Eliminar conversación
    # ------------------------------------------------------------------ #
    @http.route("/ai_assistant/conversation/<int:conversation_id>/delete", type="json", auth="user", methods=["POST"])
    def delete_conversation(self, conversation_id):
        """Elimina una conversación del usuario."""
        user = request.env.user
        conversation = request.env["ai.chat.conversation"].search(
            [("id", "=", conversation_id), ("user_id", "=", user.id)], limit=1
        )
        if conversation:
            conversation.unlink()
            return {"success": True}
        return {"error": "Conversación no encontrada"}

    # ------------------------------------------------------------------ #
    #  Audio - Obtener audio TTS
    # ------------------------------------------------------------------ #
    @http.route("/ai_assistant/audio/<int:attachment_id>", type="http", auth="user")
    def get_audio(self, attachment_id):
        """Devuelve el archivo de audio TTS generado."""
        # sudo() se mantiene porque ir.attachment tiene reglas de registro
        # restrictivas; el audio fue generado por el sistema y debe ser
        # servido al usuario que puede leer el mensaje relacionado.
        attachment = request.env["ir.attachment"].sudo().browse(attachment_id)
        if not attachment.exists():
            return Response(status=404)

        audio_data = base64.b64decode(attachment.datas)
        return Response(
            audio_data,
            content_type="audio/mpeg",
            headers={
                "Content-Disposition": f"inline; filename={attachment.name}",
                "Content-Length": len(audio_data),
            },
        )

    # ------------------------------------------------------------------ #
    #  Voz - Transcripción con Vosk (local)
    # ------------------------------------------------------------------ #
    @http.route("/ai_assistant/transcribe", type="json", auth="user", methods=["POST"])
    def transcribe_audio(self, audio_base64, sample_rate=16000):
        """Transcribe audio usando Vosk (reconocimiento de voz local).

        Args:
            audio_base64: Audio codificado en base64 (WAV format)
            sample_rate: Tasa de muestreo del audio

        Returns:
            Diccionario con el texto transcrito
        """
        if not VOSK_AVAILABLE:
            return {"error": "Vosk no está instalado. Instale con: pip install vosk"}

        voice_enabled = request.env["ir.config_parameter"].sudo().get_param(
            "ai_assistant.voice_enabled", "True"
        )
        if voice_enabled != "True":
            return {"error": "El reconocimiento de voz está deshabilitado"}

        try:
            # Decodificar audio
            audio_data = base64.b64decode(audio_base64)

            # Obtener modelo Vosk
            model_name = request.env["ir.config_parameter"].sudo().get_param(
                "ai_assistant.vosk_model", "vosk-model-small-es-0.42"
            )
            vosk_base_path = request.env["ir.config_parameter"].sudo().get_param(
                "ai_assistant.vosk_model_path", "/opt/vosk-models"
            )
            model_path = os.path.join(vosk_base_path, model_name)

            if not os.path.exists(model_path):
                return {
                    "error": f"Modelo Vosk no encontrado en {model_path}. "
                    "Descargue el modelo desde https://alphacephei.com/vosk/models "
                    f"y colóquelo en {vosk_base_path}/",
                }

            # Cargar modelo y transcribir
            model = vosk.Model(model_path)
            rec = vosk.KaldiRecognizer(model, sample_rate)

            # Procesar audio
            rec.AcceptWaveform(audio_data)
            result = json.loads(rec.FinalResult())

            text = result.get("text", "")
            if not text:
                return {"error": "No se pudo transcribir el audio. Intente hablar más claro."}

            return {"text": text, "confidence": result.get("confidence", 0.0)}

        except Exception as e:
            _logger.error("Error al transcribir audio con Vosk: %s", str(e))
            return {"error": f"Error en la transcripción: {str(e)}"}

    # ------------------------------------------------------------------ #
    #  Configuración - Obtener ajustes del asistente
    # ------------------------------------------------------------------ #
    @http.route("/ai_assistant/config", type="json", auth="user")
    def get_config(self):
        """Obtiene la configuración del asistente para el frontend."""
        sudo_params = request.env["ir.config_parameter"].sudo()
        return {
            "voice_enabled": sudo_params.get_param("ai_assistant.voice_enabled", "True") == "True",
            "tts_enabled": sudo_params.get_param("ai_assistant.tts_enabled", "True") == "True",
            "web_search_enabled": sudo_params.get_param("ai_assistant.web_search_enabled", "True") == "True",
            "knowledge_search_enabled": sudo_params.get_param("ai_assistant.knowledge_search_enabled", "True") == "True",
            "welcome_message": sudo_params.get_param(
                "ai_assistant.welcome_message",
                "¡Hola! Soy tu asistente de IA en Odoo. ¿En qué puedo ayudarte?",
            ),
            "tts_voice": sudo_params.get_param("ai_assistant.tts_voice", "es-MX-JorgeNeural"),
            "vosk_available": VOSK_AVAILABLE,
            "edge_tts_available": EDGE_TTS_AVAILABLE,
            "knowledge_installed": bool(
                request.env["ir.module.module"].sudo().search(
                    [("name", "=", "knowledge"), ("state", "=", "installed")], limit=1
                )
            ),
        }

    # ------------------------------------------------------------------ #
    #  Contexto - Obtener información de la página actual
    # ------------------------------------------------------------------ #
    @http.route("/ai_assistant/context", type="json", auth="user")
    def get_context(self, model=None, record_id=None, action=None, view_type=None):
        """Obtiene información contextual del entorno actual de Odoo.

        Args:
            model: Nombre técnico del modelo actual
            record_id: ID del registro actual
            action: Acción actual
            view_type: Tipo de vista actual

        Returns:
            Diccionario con información contextual enriquecida
        """
        context = {
            "model": model,
            "record_id": record_id,
            "action": action,
            "view_type": view_type,
            "module": "",
            "record_name": "",
            "record_data": {},
        }

        # Detectar módulo basado en el modelo
        if model:
            module_name = self._get_module_from_model(model)
            context["module"] = module_name

            # Obtener información del registro si hay ID
            if record_id:
                try:
                    record_info = request.env["ai.assistant.service"].get_record_context(
                        model, int(record_id)
                    )
                    context["record_name"] = record_info.get("display_name", "")
                    context["record_data"] = record_info
                except Exception as e:
                    _logger.warning("Error al obtener contexto: %s", str(e))

        return context

    def _get_module_from_model(self, model_name):
        """Obtiene el nombre del módulo de Odoo basado en el nombre del modelo."""
        model_to_module = {
            "crm.lead": "CRM",
            "sale.order": "Ventas",
            "purchase.order": "Compras",
            "account.move": "Contabilidad",
            "stock.picking": "Inventario",
            "stock.quant": "Inventario",
            "project.project": "Proyectos",
            "project.task": "Proyectos",
            "hr.employee": "Empleados",
            "hr.leave": "Recursos Humanos",
            "res.partner": "Contactos",
            "product.product": "Productos",
            "product.template": "Productos",
            "mrp.production": "Fabricación",
            "mrp.bom": "Fabricación",
            "pos.order": "Punto de Venta",
            "website.page": "Sitio Web",
            "mail.channel": "Mensajería",
            "knowledge.article": "Conocimiento",
            "survey.survey": "Encuestas",
            "fleet.vehicle": "Flota",
            "helpdesk.ticket": "Helpdesk",
            "quality.alert": "Calidad",
            "maintenance.equipment": "Mantenimiento",
            "maintenance.request": "Mantenimiento",
            "hr.recruitment": "Reclutamiento",
            "hr.applicant": "Reclutamiento",
            "lunch.order": "Almuerzos",
            "hr.expense": "Gastos",
            "hr.contract": "Contratos",
            "hr.payroll": "Nómina",
            "event.event": "Eventos",
            "event.registration": "Eventos",
            "utm.campaign": "Marketing",
            "utm.source": "Marketing",
            "mail.mass_mailing": "Marketing por Email",
            "snailmail.letter": "Correo Postal",
            "sign.request": "Firma",
            "approval.request": "Aprobaciones",
        }
        return model_to_module.get(model_name, model_name.split(".")[0].capitalize() if model_name else "")

    # ------------------------------------------------------------------ #
    #  TTS - Generar audio desde frontend
    # ------------------------------------------------------------------ #
    @http.route("/ai_assistant/tts", type="json", auth="user", methods=["POST"])
    def generate_tts(self, text, voice=None):
        """Genera audio TTS y devuelve el ID del attachment."""
        if not EDGE_TTS_AVAILABLE:
            return {"error": "edge-tts no está instalado"}

        tts_enabled = request.env["ir.config_parameter"].sudo().get_param(
            "ai_assistant.tts_enabled", "True"
        )
        if tts_enabled != "True":
            return {"error": "TTS está deshabilitado"}

        attachment_id = request.env["ai.assistant.service"].generate_tts(text, voice)
        if attachment_id:
            return {
                "attachment_id": attachment_id,
                "audio_url": f"/ai_assistant/audio/{attachment_id}",
            }
        return {"error": "No se pudo generar el audio"}

    # ------------------------------------------------------------------ #
    #  Voces TTS - Listar voces disponibles
    # ------------------------------------------------------------------ #
    @http.route("/ai_assistant/tts_voices", type="json", auth="user")
    def get_tts_voices(self):
        """Obtiene las voces TTS disponibles."""
        voices = request.env["ai.assistant.service"].get_available_tts_voices()
        return {"voices": voices}
