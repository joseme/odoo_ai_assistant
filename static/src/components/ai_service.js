/** @odoo-module **/

/**
 * AI Service - Capa de abstracción para llamadas al backend.
 *
 * Migrado a OWL/ES modules (Odoo 17+). Sustituye el antiguo módulo
 * `odoo.define` que dependía de `web.rpc` / `web.core` (eliminados en Odoo 17).
 *
 * Usa los servicios Odoo nativos del entorno:
 * - `env.services.rpc`  → rutas `type="json"` (JSON-RPC)
 * - `env.services.http` → rutas `type="http"` (fetch con CSRF)
 */
export class AIService {
    constructor(env) {
        this.env = env;
    }

    /**
     * Enviar mensaje al chat.
     * `/ai_assistant/chat` es `type="json"` (Odoo 17+): se usa `rpc` porque
     * el servicio `http` de Odoo envía FormData (null → "null", dict → "[object Object]").
     */
    chat(message, conversationId, contextInfo) {
        return this.env.services.rpc("/ai_assistant/chat", {
            message: message,
            conversation_id: conversationId,
            context_info: contextInfo,
        });
    }

    /**
     * Obtener conversaciones del usuario
     */
    getConversations(limit) {
        return this.env.services.rpc("/ai_assistant/conversations", {
            limit: limit || 20,
        });
    }

    /**
     * Obtener mensajes de una conversación
     */
    getConversation(conversationId) {
        return this.env.services.rpc("/ai_assistant/conversation/" + conversationId, {});
    }

    /**
     * Eliminar conversación
     */
    deleteConversation(conversationId) {
        return this.env.services.rpc("/ai_assistant/conversation/" + conversationId + "/delete", {});
    }

    /**
     * Obtener configuración para el frontend
     */
    getConfig() {
        return this.env.services.rpc("/ai_assistant/config", {});
    }

    /**
     * Obtener contexto actual de la página
     */
    getContext(model, recordId, action, viewType) {
        return this.env.services.rpc("/ai_assistant/context", {
            model: model,
            record_id: recordId,
            action: action,
            view_type: viewType,
        });
    }

    /**
     * Detectar contexto desde la URL actual de Odoo (hash: #model=..&id=..&action=..&view_type=..)
     */
    detectContextFromURL() {
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
    }

    /**
     * Renderizar Markdown simple a HTML
     */
    renderMarkdown(text) {
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
    }

    /**
     * Escapar HTML
     */
    escapeHtml(text) {
        if (!text) return "";
        var div = document.createElement("div");
        div.appendChild(document.createTextNode(text));
        return div.innerHTML;
    }
}
