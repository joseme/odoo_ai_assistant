from odoo.tests import TransactionCase
from odoo.exceptions import UserError


class TestAIChatConversation(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Conversation = self.env["ai.chat.conversation"]
        self.Message = self.env["ai.chat.message"]
        self.user = self.env.user

    def test_create_conversation(self):
        conv = self.Conversation.create({"user_id": self.user.id})
        self.assertTrue(conv)
        self.assertEqual(conv.user_id, self.user)
        self.assertEqual(conv.is_active, True)
        self.assertEqual(conv.message_count, 0)

    def test_conversation_default_user(self):
        conv = self.Conversation.create({})
        self.assertEqual(conv.user_id, self.user)

    def test_conversation_title_from_first_message(self):
        conv = self.Conversation.create({"user_id": self.user.id})
        self.Message.create({
            "conversation_id": conv.id,
            "role": "user",
            "content": "¿Cómo configurar un CRM en Odoo?",
        })
        self.assertEqual(conv.title, "¿Cómo configurar un CRM en Odoo?")

    def test_conversation_title_truncated(self):
        long_text = "Hola " * 30
        conv = self.Conversation.create({"user_id": self.user.id})
        self.Message.create({
            "conversation_id": conv.id,
            "role": "user",
            "content": long_text,
        })
        self.assertEqual(len(conv.title), 63)
        self.assertTrue(conv.title.endswith("..."))

    def test_conversation_title_not_overwritten(self):
        conv = self.Conversation.create({
            "user_id": self.user.id,
            "title": "Título personalizado",
        })
        self.Message.create({
            "conversation_id": conv.id,
            "role": "user",
            "content": "Mensaje de prueba",
        })
        self.assertEqual(conv.title, "Título personalizado")

    def test_message_count_zero(self):
        conv = self.Conversation.create({"user_id": self.user.id})
        self.assertEqual(conv.message_count, 0)

    def test_message_count_with_messages(self):
        conv = self.Conversation.create({"user_id": self.user.id})
        self.Message.create({
            "conversation_id": conv.id,
            "role": "user",
            "content": "Mensaje 1",
        })
        self.Message.create({
            "conversation_id": conv.id,
            "role": "assistant",
            "content": "Respuesta 1",
        })
        self.assertEqual(conv.message_count, 2)

    def test_conversation_order(self):
        conv1 = self.Conversation.create({"user_id": self.user.id})
        conv2 = self.Conversation.create({"user_id": self.user.id})
        all_convs = self.Conversation.search([("user_id", "=", self.user.id)])
        self.assertEqual(all_convs[0], conv2)
        self.assertEqual(all_convs[1], conv1)

    def test_context_fields(self):
        conv = self.Conversation.create({
            "user_id": self.user.id,
            "context_module": "sale",
            "context_model": "sale.order",
            "context_record_id": 42,
        })
        self.assertEqual(conv.context_module, "sale")
        self.assertEqual(conv.context_model, "sale.order")
        self.assertEqual(conv.context_record_id, 42)

    def test_action_open_conversation(self):
        conv = self.Conversation.create({"user_id": self.user.id})
        action = conv.action_open_conversation()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "ai.chat.conversation")
        self.assertEqual(action["res_id"], conv.id)
        self.assertEqual(action["view_mode"], "form")

    def test_action_open_conversation_ensure_one(self):
        with self.assertRaises(ValueError):
            self.Conversation.action_open_conversation(self.Conversation)


class TestAIChatMessage(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Conversation = self.env["ai.chat.conversation"]
        self.Message = self.env["ai.chat.message"]
        self.user = self.env.user
        self.conv = self.Conversation.create({"user_id": self.user.id})

    def test_create_user_message(self):
        msg = self.Message.create({
            "conversation_id": self.conv.id,
            "role": "user",
            "content": "Hola, ¿qué puedes hacer?",
        })
        self.assertTrue(msg)
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Hola, ¿qué puedes hacer?")
        self.assertEqual(msg.conversation_id, self.conv)

    def test_create_assistant_message(self):
        msg = self.Message.create({
            "conversation_id": self.conv.id,
            "role": "assistant",
            "content": "Puedo ayudarte con Odoo.",
        })
        self.assertEqual(msg.role, "assistant")
        self.assertFalse(msg.has_audio)
        self.assertFalse(msg.sources)

    def test_create_system_message(self):
        msg = self.Message.create({
            "conversation_id": self.conv.id,
            "role": "system",
            "content": "Mensaje del sistema",
        })
        self.assertEqual(msg.role, "system")

    def test_role_selection(self):
        with self.assertRaises(Exception):
            self.Message.create({
                "conversation_id": self.conv.id,
                "role": "invalid_role",
                "content": "Prueba",
            })

    def test_message_order(self):
        self.Message.create({
            "conversation_id": self.conv.id,
            "role": "user",
            "content": "Primero",
        })
        self.Message.create({
            "conversation_id": self.conv.id,
            "role": "assistant",
            "content": "Segundo",
        })
        messages = self.conv.message_ids
        self.assertEqual(messages[0].content, "Primero")
        self.assertEqual(messages[1].content, "Segundo")

    def test_has_audio_false_by_default(self):
        msg = self.Message.create({
            "conversation_id": self.conv.id,
            "role": "assistant",
            "content": "Sin audio",
        })
        self.assertFalse(msg.has_audio)

    def test_has_audio_with_attachment(self):
        attachment = self.env["ir.attachment"].create({
            "name": "test.mp3",
            "type": "binary",
            "datas": b"fakeaudiodata",
            "res_model": "ai.chat.message",
            "mimetype": "audio/mpeg",
        })
        msg = self.Message.create({
            "conversation_id": self.conv.id,
            "role": "assistant",
            "content": "Con audio",
            "audio_attachment_id": attachment.id,
        })
        self.assertTrue(msg.has_audio)

    def test_sources_field(self):
        msg = self.Message.create({
            "conversation_id": self.conv.id,
            "role": "assistant",
            "content": "Con fuentes",
            "sources": '[{"type": "web", "items": [{"title": "Odoo Docs"}]}]',
        })
        self.assertTrue(msg.sources)

    def test_cascade_delete(self):
        msg = self.Message.create({
            "conversation_id": self.conv.id,
            "role": "user",
            "content": "Será eliminado",
        })
        msg_id = msg.id
        self.conv.unlink()
        self.assertFalse(self.Message.browse(msg_id).exists())

    def test_content_required(self):
        with self.assertRaises(Exception):
            self.Message.create({
                "conversation_id": self.conv.id,
                "role": "user",
            })

    def test_conversation_id_required(self):
        with self.assertRaises(Exception):
            self.Message.create({
                "role": "user",
                "content": "Sin conversación",
            })
