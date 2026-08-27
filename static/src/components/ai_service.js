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
     * Renderizar Markdown a HTML con formato amigable.
     *
     * Soporta:
     * - Encabezados (#, ##, ###)
     * - Negrita (**texto**) y cursiva (*texto*)
     * - Código inline (`código`) y bloques de código (```)
     * - Listas con viñetas (-, *) y numeradas (1.)
     * - Blockquotes (> texto)
     * - Enlaces [texto](url)
     * - Separadores (---)
     * - Párrafos y saltos de línea
     */
    renderMarkdown(text) {
        if (!text) return "";

        // Escapar HTML para seguridad, pero preservar markdown
        let html = text;

        // Bloques de código (```) - procesar primero para no interferir con otros
        html = html.replace(
            /```(\w*)\n([\s\S]*?)```/g,
            '<div class="ai_code_block"><div class="ai_code_header"><span class="ai_code_lang">$1</span></div><pre><code class="$1">$2</code></pre></div>'
        );

        // Código inline
        html = html.replace(/`([^`]+)`/g, '<code class="ai_inline_code">$1</code>');

        // Encabezados
        html = html.replace(/^#### (.+)$/gm, '<h5 class="ai_md_h5">$1</h5>');
        html = html.replace(/^### (.+)$/gm, '<h4 class="ai_md_h4">$1</h4>');
        html = html.replace(/^## (.+)$/gm, '<h3 class="ai_md_h3">$1</h3>');
        html = html.replace(/^# (.+)$/gm, '<h2 class="ai_md_h2">$1</h2>');

        // Negrita y cursiva
        html = html.replace(/\*\*\*([^*]+)\*\*\*/g, '<strong><em>$1</em></strong>');
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // Blockquotes (> texto)
        html = html.replace(/^> (.+)$/gm, '<blockquote class="ai_md_blockquote">$1</blockquote>');
        // Agrupar blockquotes consecutivos
        html = html.replace(
            /((?:<blockquote class="ai_md_blockquote">.*?<\/blockquote>\s*)+)/g,
            '<div class="ai_md_blockquote_group">$1</div>'
        );

        // Separadores horizontales (---, ***, ___)
        html = html.replace(/^[-*_]{3,}$/gm, '<hr class="ai_md_separator"/>');

        // Listas con viñetas (-, *)
        html = html.replace(/^[-*] (.+)$/gm, '<li class="ai_md_li">$1</li>');

        // Listas numeradas
        html = html.replace(/^\d+\. (.+)$/gm, '<li class="ai_md_oli">$1</li>');

        // Enlaces [texto](url)
        html = html.replace(
            /\[([^\]]+)\]\(([^)]+)\)/g,
            '<a href="$2" target="_blank" rel="noopener" class="ai_md_link">$1</a>'
        );

        // Imágenes (alternativa de texto para chat)
        html = html.replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<span class="ai_md_image">[Imagen: $1]</span>');

        // Párrafos: doble salto de línea
        html = html.replace(/\n\n/g, '</p><p class="ai_md_paragraph">');

        // Saltos de línea simples
        html = html.replace(/\n/g, '<br/>');

        // Envolver en párrafo inicial
        html = '<p class="ai_md_paragraph">' + html + '</p>';

        // Limpiar párrafos vacíos y etiquetas de bloque anidadas
        html = html.replace(/<p class="ai_md_paragraph">\s*<(h[2-5]|ul|ol|div|blockquote|hr)/g, '<$1');
        html = html.replace(/<\/?(h[2-5]|ul|ol|div|blockquote|hr)[^>]*>\s*<\/p>/g, '');
        html = html.replace(/<p class="ai_md_paragraph">\s*<\/p>/g, '');

        return html;
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
