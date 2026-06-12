import asyncio
import json
import logging
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None
    _logger.warning("duckduckgo-search no está instalado. Instale con: pip install duckduckgo-search")

try:
    import nest_asyncio
    _NEST_ASYNCIO_AVAILABLE = True
except ImportError:
    nest_asyncio = None
    _NEST_ASYNCIO_AVAILABLE = False


class AIChatConversation(models.Model):
    _name = "ai.chat.conversation"
    _description = "Conversación del Asistente de IA"
    _order = "create_date desc, id desc"
    _rec_name = "title"

    title = fields.Char(
        string="Título",
        compute="_compute_title",
        store=True,
        readonly=False,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Usuario",
        required=True,
        default=lambda self: self.env.user,
        ondelete="cascade",
    )
    message_ids = fields.One2many(
        "ai.chat.message",
        "conversation_id",
        string="Mensajes",
    )
    message_count = fields.Integer(
        string="Número de mensajes",
        compute="_compute_message_count",
    )
    is_active = fields.Boolean(
        string="Activa",
        default=True,
    )
    context_module = fields.Char(
        string="Módulo contextual",
        help="Módulo de Odoo que el usuario estaba viendo al crear la conversación",
    )
    context_model = fields.Char(
        string="Modelo contextual",
        help="Modelo de Odoo que el usuario estaba viendo al crear la conversación",
    )
    context_record_id = fields.Integer(
        string="ID de registro contextual",
        help="ID del registro que el usuario estaba viendo al crear la conversación",
    )
    create_date = fields.Datetime(
        string="Fecha de creación",
        readonly=True,
    )

    @api.depends("message_ids")
    def _compute_title(self):
        for conv in self:
            if not conv.title and conv.message_ids:
                first_msg = conv.message_ids[0]
                conv.title = first_msg.content[:60] + ("..." if len(first_msg.content) > 60 else "")

    def _compute_message_count(self):
        for conv in self:
            conv.message_count = len(conv.message_ids)

    def action_open_conversation(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Conversación con IA"),
            "res_model": "ai.chat.conversation",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }


class AIChatMessage(models.Model):
    _name = "ai.chat.message"
    _description = "Mensaje del Asistente de IA"
    _order = "create_date asc"

    conversation_id = fields.Many2one(
        "ai.chat.conversation",
        string="Conversación",
        required=True,
        ondelete="cascade",
    )
    role = fields.Selection(
        [
            ("user", "Usuario"),
            ("assistant", "Asistente"),
            ("system", "Sistema"),
        ],
        string="Rol",
        required=True,
    )
    content = fields.Text(
        string="Contenido",
        required=True,
    )
    sources = fields.Text(
        string="Fuentes",
        help="Fuentes utilizadas para generar la respuesta (Knowledge, DuckDuckGo, etc.)",
    )
    create_date = fields.Datetime(
        string="Fecha",
        readonly=True,
    )


class AIAssistantService(models.AbstractModel):
    _name = "ai.assistant.service"
    _description = "Servicio del Asistente de IA"

    # ------------------------------------------------------------------ #
    #  LLM - OpenRouter (API compatible con OpenAI)
    # ------------------------------------------------------------------ #
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    @api.model
    def _call_openrouter(self, messages, temperature=0.7, max_tokens=4096):
        """Llama a la API de OpenRouter (compatible con OpenAI) para generar una respuesta.

        Args:
            messages: Lista de mensajes en formato OpenAI (role, content)
            temperature: Temperatura de generación
            max_tokens: Máximo de tokens a generar

        Returns:
            Texto de la respuesta generada
        """
        import requests as req

        api_key = self.env["ir.config_parameter"].sudo().get_param(
            "ai_assistant.openrouter_api_key", ""
        )
        if not api_key:
            raise UserError(
                _(
                    "No se ha configurado la API Key de OpenRouter. "
                    "Vaya a Configuración > Ajustes > AI Assistant y configure la clave."
                )
            )

        params = self.env["ir.config_parameter"].sudo()
        model_name = params.get_param("ai_assistant.model_name", "openai/gpt-4o-mini")
        # Si el modelo seleccionado es "_custom_", usar el modelo personalizado
        if model_name == "_custom_":
            model_name = params.get_param("ai_assistant.custom_model", "openai/gpt-4o-mini")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        _logger.warning(">>> Payload OpenRouter: %s", json.dumps(payload, indent=2))
        _logger.warning(">>> Headers OpenRouter: %s", headers)
        
        try:
            response = req.post(
                f"{self.OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60,
            )
            _logger.warning(">>> Response status: %s", response.status_code)
            if response.status_code != 200:
                _logger.warning(">>> Response body: %s", response.text[:500])
            response.raise_for_status()
            data = response.json()
            _logger.warning(">>> Response JSON: %s", json.dumps(data)[:500])
            return data["choices"][0]["message"]["content"]
        except req.exceptions.Timeout:
            raise UserError(
                _("La solicitud a OpenRouter excedió el tiempo de espera. Intente de nuevo.")
            )
        except req.exceptions.HTTPError as e:
            _logger.error("Error HTTP en OpenRouter: %s - %s", e, e.response.text if e.response else "")
            raise UserError(
                _("Error al comunicarse con OpenRouter (HTTP %(code)s). Revise su API Key y modelo.") %
                {"code": e.response.status_code if e.response else "desconocido"}
            )
        except Exception as e:
            _logger.error("Error al llamar a OpenRouter: %s", str(e))
            raise UserError(_("Error al conectar con OpenRouter: %(error)s") % {"error": str(e)})

    @api.model
    def _build_system_prompt(self, context_info=None):
        """Construye el prompt del sistema con contexto de Odoo."""
        base_prompt = """Eres un asistente de IA experto en Odoo integrado directamente en la plataforma. Tu objetivo es ayudar a los usuarios a utilizar Odoo de manera más eficiente.

Capacidades:
- Responder preguntas sobre funcionalidades de Odoo (CRM, Ventas, Contabilidad, Inventario, etc.)
- Guiar al usuario paso a paso en procesos dentro de Odoo
- Explicar conceptos y configuraciones de Odoo
- Sugerir mejores prácticas y flujos de trabajo
- Buscar información en la base de conocimiento de la empresa (Knowledge)
- Buscar información actualizada en la web cuando sea necesario

Reglas importantes:
- Responde SIEMPRE en el mismo idioma que el usuario
- Sé conciso pero completo en tus respuestas
- Cuando expliques procesos, indica los pasos de forma clara: ir a X > hacer clic en Y > etc.
- Si no estás seguro de algo, indícalo claramente
- Si la pregunta no está relacionada con Odoo, responde brevemente y redirige al usuario hacia temas de Odoo
- NO uses formato Markdown. Usa texto plano con estos atributos:
  * Negrita: encierra entre « » (comillas latinas)
  * Código o nombres técnicos: entre comillas simples ''
  * Listas: usa guiones (-) al inicio de línea
  * Separación: líneas en blanco entre párrafos
Ejemplo: «Ventas» es el módulo que buscas. Allí encuentras 'product.template' para gestionar productos.
"""
        if context_info:
            base_prompt += f"""

Contexto actual del usuario en Odoo:
- Menú activo: {context_info.get('menu', 'Desconocido')}
- Breadcrumb: {context_info.get('breadcrumb', 'N/A')}
- Modelo: {context_info.get('model', 'Desconocido')}
- ID de registro: {context_info.get('res_id', 'N/A')}
- Action ID: {context_info.get('action_id', 'N/A')}
- URL: {context_info.get('url', 'N/A')}
- Título de página: {context_info.get('title', 'N/A')}

El usuario está viendo esta página de Odoo. Usa este contexto para dar respuestas más relevantes y específicas sobre lo que el usuario está viendo.
"""
        return base_prompt

    @api.model
    def generate_response(self, messages, context_info=None, search_knowledge=True, search_web=True):
        """Genera una respuesta del LLM con contexto enriquecido.

        Args:
            messages: Lista de diccionarios con 'role' y 'content'
            context_info: Diccionario con información del contexto actual de Odoo
            search_knowledge: Si debe buscar en el módulo Knowledge
            search_web: Si debe buscar en DuckDuckGo

        Returns:
            Diccionario con la respuesta y las fuentes utilizadas
        """
        sources = []
        last_message = messages[-1].get("content", "") if messages else ""

        # 1. Buscar en Knowledge si está instalado y solicitado
        knowledge_context = ""
        if search_knowledge:
            try:
                knowledge_context, knowledge_sources = self._search_knowledge(
                    last_message, context_info
                )
                if knowledge_context:
                    sources.append({
                        "type": "knowledge",
                        "items": knowledge_sources,
                    })
            except Exception as e:
                _logger.warning("Error al buscar en Knowledge: %s", str(e))

        # 2. Buscar en la web si está solicitado
        web_context = ""
        if search_web:
            try:
                web_context, web_sources = self._search_web(last_message)
                if web_context:
                    sources.append({
                        "type": "web",
                        "items": web_sources,
                    })
            except Exception as e:
                _logger.warning("Error al buscar en web: %s", str(e))

        # 3. Construir mensajes para el LLM
        system_prompt = self._build_system_prompt(context_info)

        enriched_messages = [{"role": "system", "content": system_prompt}]

        if knowledge_context:
            enriched_messages.append({
                "role": "system",
                "content": f"Información relevante de la base de conocimiento de la empresa:\n{knowledge_context}",
            })

        if web_context:
            enriched_messages.append({
                "role": "system",
                "content": f"Información relevante de búsqueda web:\n{web_context}",
            })

        # Añadir historial de conversación (últimos N mensajes para no exceder tokens)
        max_history = int(self.env["ir.config_parameter"].sudo().get_param(
            "ai_assistant.max_history", "20"
        ))
        for msg in messages[-max_history:]:
            role = "user" if msg["role"] == "user" else "assistant"
            enriched_messages.append({"role": role, "content": msg["content"]})

        # 4. Llamar al LLM via OpenRouter
        try:
            # Preparar mensajes en formato OpenAI
            openai_messages = []
            for msg in enriched_messages:
                openai_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

            assistant_response = self._call_openrouter(
                messages=openai_messages,
                temperature=0.7,
                max_tokens=4096,
            )
        except Exception as e:
            _logger.error("Error al generar respuesta con OpenRouter: %s", str(e))
            # Fallback: intentar respuesta simple
            assistant_response = _(
                "Lo siento, hubo un error al generar la respuesta. "
                "Por favor, verifica la configuración de la API Key de OpenRouter. "
                "Error: %(error)s"
            ) % {"error": str(e)}

        return {
            "response": self._markdown_to_plain(assistant_response),
            "sources": sources,
        }

    @api.model
    def _markdown_to_plain(self, text):
        """Convierte Markdown a texto plano con atributos de formato.
        
        - **texto** o __texto__ -> «texto»
        - `codigo` -> 'codigo'
        - ### Título -> TÍTULO (en mayúscula)
        - links [texto](url) -> texto (url)
        - ``` ... ``` -> se mantiene pero sin los backticks triples
        """
        import re
        
        # Bloques de código triple: ``` ... ```
        text = re.sub(r'```(?:\w+)?\n?(.*?)\n?```', r'[código]\1[/código]', text, flags=re.DOTALL)
        
        # Código inline: `codigo`
        text = re.sub(r'`([^`]+)`', r"'\1'", text)
        
        # Negrita: **texto** o __texto__
        text = re.sub(r'\*\*(.+?)\*\*', r'«\1»', text)
        text = re.sub(r'__(.+?)__', r'«\1»', text)
        
        # Cursiva: *texto* o _texto_ (pero no si ya está dentro de « »)
        text = re.sub(r'(?<!«)\*(.+?)\*(?!»)', r'_\1_', text)
        text = re.sub(r'(?<!«)_(.+?)_(?!»)', r'_\1_', text)
        
        # Títulos: ### texto -> TEXTO
        text = re.sub(r'^#{1,6}\s+(.+)$', lambda m: m.group(1).upper(), text, flags=re.MULTILINE)
        
        # Links: [texto](url) -> texto (url)
        text = re.sub(r'\[(.+?)\]\((.+?)\)', r'\1 (\2)', text)
        
        # Listas: - item -> - item (ya está bien)
        # Listas numeradas: 1. item -> - item (unificar)
        text = re.sub(r'^\d+\.\s+', '- ', text, flags=re.MULTILINE)
        
        # Cerrar [código] -> eliminar marcadores (el contenido ya está con '')
        text = text.replace('[código]', '').replace('[/código]', '')
        
        return text.strip()

    # ------------------------------------------------------------------ #
    #  Knowledge - Búsqueda en módulo Knowledge de Odoo
    # ------------------------------------------------------------------ #
    @api.model
    def _search_knowledge(self, query, context_info=None):
        """Busca información relevante en la base de conocimiento.

        Decide si usa la búsqueda local de Odoo o la API de AnythingLLM según la configuración.
        """
        search_mode = self.env["ir.config_parameter"].sudo().get_param(
            "ai_assistant.knowledge_search_mode", "local"
        )

        if search_mode == "anythingllm":
            return self._search_anythingllm(query)

        return self._search_knowledge_local(query, context_info)

    @api.model
    def _search_knowledge_local(self, query, context_info=None):
        """Busca artículos relevantes en el módulo Knowledge de Odoo.

        Returns:
            Tupla (context_string, list_of_sources)
        """
        if "knowledge.article" not in self.env.registry:
            return "", []

        try:
            # Buscar en documentos del módulo Knowledge
            Article = self.env["knowledge.article"].sudo()
            domain = [
                "|",
                ("name", "ilike", query),
                ("content", "ilike", query),
            ]

            # Filtrar por artículos internos (no compartidos externamente)
            articles = Article.search(domain, limit=5)

            if not articles:
                return "", []

            context_parts = []
            sources = []
            for article in articles:
                # Limpiar HTML del contenido para extraer texto
                content = self._html_to_text(article.content or "")
                if content:
                    # Truncar contenido largo
                    if len(content) > 1000:
                        content = content[:1000] + "..."
                    context_parts.append(f"Artículo: {article.name}\n{content}")
                    sources.append({
                        "title": article.name,
                        "id": article.id,
                        "model": "knowledge.article",
                    })

            return "\n\n---\n\n".join(context_parts), sources

        except Exception as e:
            _logger.warning("Error al buscar en Knowledge local: %s", str(e))
            return "", []

    @api.model
    def _search_anythingllm(self, query):
        """Busca información relevante usando la API de AnythingLLM.

        Returns:
            Tupla (context_string, list_of_sources)
        """
        import requests

        url = self.env["ir.config_parameter"].sudo().get_param("ai_assistant.anythingllm_url")
        api_key = self.env["ir.config_parameter"].sudo().get_param("ai_assistant.anythingllm_key")
        workspace_slug = self.env["ir.config_parameter"].sudo().get_param("ai_assistant.anythingllm_workspace")

        if not url or not api_key or not workspace_slug:
            _logger.warning("Configuración de AnythingLLM incompleta (URL, Key o Workspace faltantes).")
            return "", []

        try:
            # Endpoint de chat/query de AnythingLLM
            endpoint = f"{url.rstrip('/')}/api/v1/workspace/{workspace_slug}/chat"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            payload = {
                "message": query,
                "mode": "query" # Modo query para obtener solo fragmentos relevantes
            }

            response = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()

            # Extraer respuesta y citas
            content = data.get("text", "")
            citations = data.get("citations", [])

            sources = []
            if citations:
                for cit in citations:
                    sources.append({
                        "title": cit.get("title", "Documento de AnythingLLM"),
                        "url": cit.get("url", ""),
                        "id": cit.get("id", "ext"),
                        "model": "anythingllm.document",
                    })

            return content, sources

        except Exception as e:
            _logger.error("Error al buscar en AnythingLLM: %s", str(e))
            return "", []

    # ------------------------------------------------------------------ #
    #  DuckDuckGo - Búsqueda web
    # ------------------------------------------------------------------ #
    @api.model
    def _search_web(self, query, max_results=5):
        """Busca información relevante en DuckDuckGo.

        Returns:
            Tupla (context_string, list_of_sources)
        """
        if DDGS is None:
            return "", []

        web_search_enabled = self.env["ir.config_parameter"].sudo().get_param(
            "ai_assistant.web_search_enabled", "True"
        )
        if web_search_enabled != "True":
            return "", []

        try:
            # Enriquecer la consulta con contexto de Odoo
            enriched_query = f"Odoo {query}"

            with DDGS() as ddgs:
                results = list(ddgs.text(enriched_query, max_results=max_results))

            if not results:
                return "", []

            context_parts = []
            sources = []
            for result in results:
                body = result.get("body", "")
                title = result.get("title", "")
                href = result.get("href", "")
                if body:
                    context_parts.append(f"Fuente: {title}\n{body}")
                    sources.append({
                        "title": title,
                        "url": href,
                    })

            return "\n\n---\n\n".join(context_parts), sources

        except Exception as e:
            _logger.warning("Error al buscar en DuckDuckGo: %s", str(e))
            return "", []

    # ------------------------------------------------------------------ #
    #  Contexto - Obtener información contextual de Odoo
    # ------------------------------------------------------------------ #
    @api.model
    def get_record_context(self, model_name, record_id):
        """Obtiene información contextual de un registro específico de Odoo.

        Args:
            model_name: Nombre técnico del modelo (ej: 'sale.order')
            record_id: ID del registro

        Returns:
            Diccionario con información del registro
        """
        try:
            Model = self.env[model_name].sudo().browse(record_id)
            if not Model.exists():
                return {"error": "Registro no encontrado"}

            record_info = {
                "id": record_id,
                "model": model_name,
                "display_name": Model.display_name if hasattr(Model, "display_name") else str(Model),
            }

            # Obtener campos importantes del modelo
            fields_to_include = []
            for field_name, field_info in Model.fields_get().items():
                if field_info.get("type") in ("char", "text", "selection", "integer", "float", "monetary", "date", "datetime", "boolean"):
                    if field_name not in ("id", "create_date", "write_date", "create_uid", "write_uid", "__last_update"):
                        fields_to_include.append(field_name)

            # Obtener valores de los campos (limitado a los más importantes)
            for field_name in fields_to_include[:20]:  # Limitar a 20 campos para no exceder tokens
                try:
                    value = Model[field_name]
                    if isinstance(value, models.BaseModel):
                        record_info[field_name] = value.display_name if hasattr(value, "display_name") else str(value)
                    else:
                        record_info[field_name] = value
                except Exception:
                    pass

            return record_info

        except Exception as e:
            _logger.warning("Error al obtener contexto del registro %s/%s: %s", model_name, record_id, str(e))
            return {"error": str(e)}

    # ------------------------------------------------------------------ #
    #  Utilidades
    # ------------------------------------------------------------------ #
    @api.model
    def _run_async(self, coro):
        """Ejecuta una coroutine de forma segura en el thread actual.

        Odoo corre en threads con un event loop potencialmente activo.
        Usa nest_asyncio cuando sea necesario para evitar RuntimeError.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                if not _NEST_ASYNCIO_AVAILABLE:
                    raise RuntimeError(
                        "nest-asyncio es requerido para ejecutar código async "
                        "dentro de un event loop activo. Instale con: pip install nest-asyncio"
                    )
                nest_asyncio.apply()
                return loop.run_until_complete(coro)
            return loop.run_until_complete(coro)
        except RuntimeError:
            return asyncio.run(coro)

    @api.model
    def _html_to_text(self, html):
        """Convierte HTML a texto plano de forma simple."""
        if not html:
            return ""
        # Eliminar tags HTML
        text = re.sub(r"<[^>]+>", " ", html)
        # Normalizar espacios
        text = re.sub(r"\s+", " ", text).strip()
        return text
