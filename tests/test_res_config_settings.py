from odoo.tests import TransactionCase


class TestResConfigSettings(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Settings = self.env["res.config.settings"]
        self.IrConfig = self.env["ir.config_parameter"].sudo()

    def test_default_model_name(self):
        current = self.IrConfig.get_param("ai_assistant.model_name", "openai/gpt-4o-mini")
        self.assertEqual(current, "openai/gpt-4o-mini")

    def test_get_values_popular_model(self):
        self.IrConfig.set_param("ai_assistant.model_name", "openai/gpt-4o-mini")
        settings = self.Settings.create({})
        values = settings.get_values()
        self.assertEqual(values.get("ai_assistant_model_name"), "openai/gpt-4o-mini")
        self.assertFalse(values.get("ai_assistant_custom_model"))

    def test_get_values_custom_model(self):
        self.IrConfig.set_param("ai_assistant.model_name", "custom-model/test")
        settings = self.Settings.create({})
        values = settings.get_values()
        self.assertEqual(values.get("ai_assistant_model_name"), "_custom_")
        self.assertEqual(values.get("ai_assistant_custom_model"), "custom-model/test")

    def test_set_values_popular(self):
        settings = self.Settings.create({
            "ai_assistant_model_name": "anthropic/claude-sonnet-4",
        })
        settings.set_values()
        saved = self.IrConfig.get_param("ai_assistant.model_name")
        self.assertEqual(saved, "anthropic/claude-sonnet-4")

    def test_set_values_custom(self):
        settings = self.Settings.create({
            "ai_assistant_model_name": "_custom_",
            "ai_assistant_custom_model": "deepseek/deepseek-v4-flash",
        })
        settings.set_values()
        saved = self.IrConfig.get_param("ai_assistant.model_name")
        self.assertEqual(saved, "deepseek/deepseek-v4-flash")

    def test_set_values_custom_empty_fallback(self):
        settings = self.Settings.create({
            "ai_assistant_model_name": "_custom_",
            "ai_assistant_custom_model": "",
        })
        settings.set_values()
        saved = self.IrConfig.get_param("ai_assistant.model_name")
        self.assertEqual(saved, "openai/gpt-4o-mini")

    def test_compute_custom_model_visible_true(self):
        settings = self.Settings.create({
            "ai_assistant_model_name": "_custom_",
        })
        self.assertTrue(settings.ai_assistant_custom_model_visible)

    def test_compute_custom_model_visible_false(self):
        settings = self.Settings.create({
            "ai_assistant_model_name": "openai/gpt-4o-mini",
        })
        self.assertFalse(settings.ai_assistant_custom_model_visible)

    def test_default_web_search_enabled(self):
        current = self.IrConfig.get_param("ai_assistant.web_search_enabled", "True")
        self.assertEqual(current, "True")

    def test_config_persistence(self):
        self.IrConfig.set_param("ai_assistant.welcome_message", "¡Bienvenido!")
        saved = self.IrConfig.get_param("ai_assistant.welcome_message")
        self.assertEqual(saved, "¡Bienvenido!")
