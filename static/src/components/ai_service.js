odoo.define("odoo_ai_assistant.OwlComponents", ["web.core", "web.rpc"], function (require) {
    "use strict";

    /**
     * Componentes OWL para compatibilidad con Odoo 18 y 19.
     * Estos componentes usan el framework OWL nativo que viene
     * integrado en las versiones más recientes de Odoo.
     *
     * En Odoo 17, se usa el sistema de widgets legacy.
     * En Odoo 18/19, se puede usar el framework OWL directamente.
     *
     * Este archivo proporciona un adaptador de compatibilidad.
     */

    var core = require("web.core");
    var rpc = require("web.rpc");
    var _t = core._t;

    /**
     * Servicio de IA - Capa de abstracción para llamadas al backend.
     * Reutilizado por ambos sistemas (legacy y OWL).
     */
    var AIService = {
        /**
         * Enviar mensaje al chat
         */
        chat: function (message, conversationId, contextInfo) {
            return rpc.query({
                route: "/ai_assistant/chat",
                params: {
                    message: message,
                    conversation_id: conversationId,
                    context_info: contextInfo,
                },
            });
        },

        /**
         * Obtener conversaciones del usuario
         */
        getConversations: function (limit) {
            return rpc.query({
                route: "/ai_assistant/conversations",
                params: { limit: limit || 20 },
            });
        },

        /**
         * Obtener mensajes de una conversación
         */
        getConversation: function (conversationId) {
            return rpc.query({
                route: "/ai_assistant/conversation/" + conversationId,
                params: {},
            });
        },

        /**
         * Eliminar conversación
         */
        deleteConversation: function (conversationId) {
            return rpc.query({
                route: "/ai_assistant/conversation/" + conversationId + "/delete",
                params: {},
            });
        },

        /**
         * Obtener contexto actual
         */
        getContext: function (model, recordId, action, viewType) {
            return rpc.query({
                route: "/ai_assistant/context",
                params: {
                    model: model,
                    record_id: recordId,
                    action: action,
                    view_type: viewType,
                },
            });
        },

        /**
         * Detectar contexto desde la URL actual de Odoo
         */
        detectContextFromURL: function () {
            var hash = window.location.hash;
            var params = {};

            if (hash) {
                var hashStr = hash.substring(1);
                hashStr.split("&").forEach(function (pair) {
                    var kv = pair.split("=");
                    if (kv.length === 2) {
                        params[kv[0]] = decodeURIComponent(kv[1]);
                    }
                });
            }

            return {
                model: params.model || "",
                record_id: params.id || null,
                action: params.action || "",
                view_type: params.view_type || "",
            };
        },

        /**
         * Renderizar Markdown simple a HTML
         */
        renderMarkdown: function (text) {
            if (!text) return "";
            return text
                .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="$1">$2</code></pre>')
                .replace(/`([^`]+)`/g, "<code>$1</code>")
                .replace(/^### (.+)$/gm, "<h4>$1</h4>")
                .replace(/^## (.+)$/gm, "<h3>$1</h3>")
                .replace(/^# (.+)$/gm, "<h2>$1</h2>")
                .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
                .replace(/\*([^*]+)\*/g, "<em>$1</em>")
                .replace(/^[*-] (.+)$/gm, '<li class="ai_md_li">$1</li>')
                .replace(/^\d+\. (.+)$/gm, '<li class="ai_md_oli">$1</li>')
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
                .replace(/\n\n/g, "</p><p>")
                .replace(/\n/g, "<br>");
        },

        /**
         * Escapar HTML
         */
        escapeHtml: function (text) {
            if (!text) return "";
            var div = document.createElement("div");
            div.appendChild(document.createTextNode(text));
            return div.innerHTML;
        },
    };

    return AIService;
});
