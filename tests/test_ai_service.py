from unittest.mock import patch, MagicMock
from odoo.tests import TransactionCase
from odoo.exceptions import UserError


class TestAIAssistantServiceUtilities(TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env["ai.assistant.service"]

    def test_html_to_text_empty(self):
        self.assertEqual(self.service._html_to_text(""), "")
        self.assertEqual(self.service._html_to_text(None), "")

    def test_html_to_text_simple(self):
        self.assertEqual(self.service._html_to_text("<p>Hola mundo</p>"), "Hola mundo")

    def test_html_to_text_nested(self):
        html = "<div><h1>Título</h1><p>Texto con <b>negrita</b></p></div>"
        result = self.service._html_to_text(html)
        self.assertIn("Título", result)
        self.assertIn("Texto con", result)
        self.assertIn("negrita", result)

    def test_html_to_text_multiple_spaces(self):
        self.assertEqual(
            self.service._html_to_text("<p>  Hola   mundo  </p>"),
            "Hola mundo",
        )

    def test_html_to_text_no_html(self):
        self.assertEqual(self.service._html_to_text("Texto plano"), "Texto plano")

    def test_build_system_prompt_without_context(self):
        prompt = self.service._build_system_prompt()
        self.assertIn("asistente de IA experto en Odoo", prompt)
        self.assertIn("Responde SIEMPRE en el mismo idioma", prompt)
        self.assertNotIn("Contexto actual del usuario", prompt)

    def test_build_system_prompt_with_context(self):
        context = {
            "module": "Ventas",
            "model": "sale.order",
            "record_name": "Pedido #42",
            "record_id": "42",
            "action": "1",
            "view_type": "form",
        }
        prompt = self.service._build_system_prompt(context)
        self.assertIn("Contexto actual del usuario", prompt)
        self.assertIn("Ventas", prompt)
        self.assertIn("sale.order", prompt)
        self.assertIn("Pedido #42", prompt)

    def test_build_system_prompt_partial_context(self):
        context = {"module": "CRM"}
        prompt = self.service._build_system_prompt(context)
        self.assertIn("CRM", prompt)
        self.assertIn("Desconocido", prompt)

    def test_run_async_simple(self):
        async def dummy():
            return 42
        result = self.service._run_async(dummy())
        self.assertEqual(result, 42)

    def test_run_async_with_exception(self):
        async def failing():
            raise ValueError("test error")
        with self.assertRaises(ValueError):
            self.service._run_async(failing())


class TestAIAssistantServiceRecordContext(TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env["ai.assistant.service"]

    def test_get_record_context_record_not_found(self):
        result = self.service.get_record_context("res.users", -1)
        self.assertEqual(result.get("error"), "Registro no encontrado")

    def test_get_record_context_invalid_model(self):
        result = self.service.get_record_context("nonexistent.model", 1)
        self.assertIn("error", result)

    def test_get_record_context_valid_record(self):
        result = self.service.get_record_context("res.users", self.env.user.id)
        self.assertEqual(result["id"], self.env.user.id)
        self.assertEqual(result["model"], "res.users")
        self.assertTrue(result.get("display_name"))
        self.assertTrue(result.get("login"))
        self.assertTrue(result.get("name"))

    def test_get_record_context_limits_fields(self):
        result = self.service.get_record_context("res.users", self.env.user.id)
        keys = list(result.keys())
        fields_count = len(keys) - 3
        self.assertLessEqual(fields_count, 20)


class TestAIAssistantServiceKnowledge(TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env["ai.assistant.service"]

    def test_search_knowledge_local_no_module(self):
        ctx, sources = self.service._search_knowledge_local("test query")
        self.assertEqual(ctx, "")
        self.assertEqual(sources, [])

    def test_search_knowledge_local_no_registry(self):
        ctx, sources = self.service._search_knowledge_local("test")
        self.assertEqual(ctx, "")
        self.assertEqual(sources, [])

    def test_search_knowledge_dispatches_to_local_by_default(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.knowledge_search_mode", "local"
        )
        ctx, sources = self.service._search_knowledge("test")
        self.assertEqual(ctx, "")
        self.assertEqual(sources, [])

    def test_search_knowledge_dispatches_to_anythingllm(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.knowledge_search_mode", "anythingllm"
        )
        ctx, sources = self.service._search_knowledge("test")
        self.assertEqual(ctx, "")
        self.assertEqual(sources, [])

    def test_search_anythingllm_no_config(self):
        ctx, sources = self.service._search_anythingllm("test")
        self.assertEqual(ctx, "")
        self.assertEqual(sources, [])


class TestAIAssistantServiceWebSearch(TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env["ai.assistant.service"]

    def test_search_web_disabled(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.web_search_enabled", "False"
        )
        ctx, sources = self.service._search_web("test")
        self.assertEqual(ctx, "")
        self.assertEqual(sources, [])


class TestAIAssistantServiceGenerateResponse(TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env["ai.assistant.service"]
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.openrouter_api_key", ""
        )

    def test_generate_response_empty_messages(self):
        result = self.service.generate_response([], search_knowledge=False, search_web=False)
        self.assertIn("response", result)
        self.assertEqual(result["sources"], [])

    def test_generate_response_with_user_message(self):
        messages = [{"role": "user", "content": "¿Qué es Odoo?"}]
        result = self.service.generate_response(
            messages, context_info=None, search_knowledge=False, search_web=False
        )
        self.assertIn("response", result)
        self.assertIn("error", result["response"].lower())

    def test_generate_response_sources_empty_when_disabled(self):
        messages = [{"role": "user", "content": "test"}]
        result = self.service.generate_response(
            messages, context_info=None, search_knowledge=False, search_web=False
        )
        self.assertEqual(result["sources"], [])

    def test_generate_response_max_history(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.max_history", "3"
        )
        messages = [
            {"role": "user", "content": f"Mensaje {i}"}
            for i in range(10)
        ]
        with patch.object(type(self.service), "_call_openrouter") as mock:
            mock.side_effect = UserError("No API key")
            result = self.service.generate_response(
                messages, context_info=None, search_knowledge=False, search_web=False
            )
        self.assertIn("error", result["response"].lower())

    def test_generate_response_knowledge_error_does_not_break(self):
        messages = [{"role": "user", "content": "test"}]
        with patch.object(
            type(self.service), "_search_knowledge", side_effect=Exception("Knowledge fail")
        ):
            result = self.service.generate_response(
                messages, context_info=None, search_knowledge=True, search_web=False
            )
        self.assertIn("response", result)

    def test_generate_response_web_error_does_not_break(self):
        messages = [{"role": "user", "content": "test"}]
        with patch.object(
            type(self.service), "_search_web", side_effect=Exception("Web fail")
        ):
            result = self.service.generate_response(
                messages, context_info=None, search_knowledge=False, search_web=True
            )
        self.assertIn("response", result)

    def test_generate_response_with_context_info(self):
        messages = [{"role": "user", "content": "test"}]
        context = {
            "module": "CRM",
            "model": "crm.lead",
            "record_name": "Lead #1",
        }
        with patch.object(type(self.service), "_build_system_prompt") as mock_prompt:
            mock_prompt.return_value = "System prompt"
            with patch.object(type(self.service), "_call_openrouter") as mock_call:
                mock_call.side_effect = UserError("No API key")
                self.service.generate_response(
                    messages, context_info=context,
                    search_knowledge=False, search_web=False
                )
        mock_prompt.assert_called_once_with(context)


class TestAIAssistantServiceCallOpenRouter(TransactionCase):

    def setUp(self):
        super().setUp()
        self.service = self.env["ai.assistant.service"]
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.openrouter_api_key", ""
        )

    def test_call_openrouter_no_api_key(self):
        with self.assertRaises(UserError):
            self.service._call_openrouter(
                [{"role": "user", "content": "Hola"}]
            )

    def test_call_openrouter_with_api_key_no_custom_model(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.openrouter_api_key", "test-key-123"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.model_name", "openai/gpt-4o-mini"
        )
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Respuesta de prueba"}}]
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            result = self.service._call_openrouter(
                [{"role": "user", "content": "Hola"}]
            )
            self.assertEqual(result, "Respuesta de prueba")
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args[1]
            self.assertEqual(call_kwargs["json"]["model"], "openai/gpt-4o-mini")
            self.assertEqual(
                call_kwargs["headers"]["Authorization"], "Bearer test-key-123"
            )

    def test_call_openrouter_timeout(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.openrouter_api_key", "test-key"
        )
        with patch("requests.post") as mock_post:
            import requests
            mock_post.side_effect = requests.exceptions.Timeout("Timeout")
            with self.assertRaises(UserError):
                self.service._call_openrouter(
                    [{"role": "user", "content": "Hola"}]
                )

    def test_call_openrouter_http_error(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.openrouter_api_key", "test-key"
        )
        with patch("requests.post") as mock_post:
            import requests
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            http_error = requests.exceptions.HTTPError("401 Unauthorized")
            http_error.response = mock_response
            mock_post.side_effect = http_error
            with self.assertRaises(UserError):
                self.service._call_openrouter(
                    [{"role": "user", "content": "Hola"}]
                )

    def test_call_openrouter_custom_model(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.openrouter_api_key", "test-key"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.model_name", "_custom_"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.custom_model", "anthropic/claude-sonnet"
        )
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Ok"}}]
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            self.service._call_openrouter(
                [{"role": "user", "content": "Hola"}]
            )
            call_kwargs = mock_post.call_args[1]
            self.assertEqual(
                call_kwargs["json"]["model"], "anthropic/claude-sonnet"
            )

    def test_call_openrouter_custom_model_empty_fallback(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.openrouter_api_key", "test-key"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.model_name", "_custom_"
        )
        self.env["ir.config_parameter"].sudo().set_param(
            "ai_assistant.custom_model", ""
        )
        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Ok"}}]
            }
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            self.service._call_openrouter(
                [{"role": "user", "content": "Hola"}]
            )
            call_kwargs = mock_post.call_args[1]
            self.assertEqual(
                call_kwargs["json"]["model"], "openai/gpt-4o-mini"
            )
