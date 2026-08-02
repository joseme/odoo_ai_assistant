/** @odoo-module **/

/**
 * AI Assistant - Chat flotante (OWL Component, Odoo 17+).
 *
 * Migrado del sistema legacy (`odoo.define` + `web.Widget` + `web.rpc`,
 * eliminados en Odoo 17) a un Componente OWL. Reemplaza también al antiguo
 * FAB vanilla (`fab.js`) para evitar duplicación.
 *
 * Se monta como servicio OWL sobre `document.body`; el FAB y la ventana
 * de chat usan `position: fixed`, por lo que no dependen del DOM del webclient.
 */
import { Component, useState, useRef, useEffect, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { AIService } from "../components/ai_service";

export class AIAssistant extends Component {
    static template = "odoo_ai_assistant.ChatWindow";
    static props = {};

    setup() {
        this.state = useState({
            isOpen: false,
            loading: false,
            conversationId: null,
            messages: [],
            conversations: [],
            showHistory: false,
            currentContext: {},
            config: {},
        });

        this.inputRef = useRef("input");
        this.messagesRef = useRef("messages");
        this.aiService = new AIService(this.env);
        this._msgSeq = 0;

        // Scroll al fondo tras cada render que cambie mensajes/estado de carga.
        // (Este build de OWL no exporta nextTick; useEffect es el patrón OWL).
        useEffect(
            () => {
                const container = this.messagesRef.el;
                if (container) {
                    container.scrollTop = container.scrollHeight;
                }
            },
            () => [this.state.messages.length, this.state.loading]
        );

        // Atajo global Ctrl+Alt+A (paridad con el widget legacy)
        this._onKeyDown = this._onKeyDown.bind(this);
        document.addEventListener("keydown", this._onKeyDown);
        onWillUnmount(() => {
            document.removeEventListener("keydown", this._onKeyDown);
        });

        this._init();
    }

    async _init() {
        const [config, ctx] = await Promise.all([
            this._loadConfig(),
            this._detectContext(),
        ]);
        if (config.welcome_message) {
            this.addMessage("assistant", config.welcome_message);
        }
        this._loadConversations();
    }

    // ------------------------------------------------------------------ //
    //  Configuración
    // ------------------------------------------------------------------ //
    async _loadConfig() {
        try {
            this.state.config = await this.aiService.getConfig();
        } catch (e) {
            this.state.config = {
                web_search_enabled: true,
                welcome_message: "¡Hola! Soy tu asistente de IA en Odoo. ¿En qué puedo ayudarte?",
            };
        }
        return this.state.config;
    }

    // ------------------------------------------------------------------ //
    //  Detección de Contexto
    // ------------------------------------------------------------------ //
    async _detectContext() {
        const urlCtx = this.aiService.detectContextFromURL();
        this.state.currentContext = Object.assign({}, urlCtx, { module: "" });

        if (urlCtx.model) {
            try {
                this.state.currentContext = await this.aiService.getContext(
                    urlCtx.model,
                    urlCtx.record_id,
                    urlCtx.action,
                    urlCtx.view_type
                );
            } catch (e) {
                // Usar contexto local si falla la petición
            }
        }
        return this.state.currentContext;
    }

    // ------------------------------------------------------------------ //
    //  Chat - Envío de mensajes
    // ------------------------------------------------------------------ //
    async send() {
        const el = this.inputRef.el;
        const message = el.value.trim();
        if (!message || this.state.loading) return;

        el.value = "";
        el.style.height = "auto";
        this.addMessage("user", message);
        this.setLoading(true);

        try {
            const result = await this.aiService.chat(
                message,
                this.state.conversationId,
                this.state.currentContext
            );
            this.setLoading(false);
            if (result.error) {
                this.addMessage("system", "Error: " + result.error);
                return;
            }
            this.state.conversationId = result.conversation_id;
            this.addMessage("assistant", result.response, result.sources);
        } catch (error) {
            this.setLoading(false);
            this.addMessage(
                "system",
                "Error de conexión. Por favor, verifica tu conexión a internet y la configuración del asistente."
            );
            console.error("AI Assistant error:", error);
        }
    }

    onKeyDown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.send();
        }
    }

    onInput() {
        // Auto-resize del textarea
        const el = this.inputRef.el;
        el.style.height = "auto";
        el.style.height = Math.min(el.scrollHeight, 120) + "px";
    }

    _onKeyDown(ev) {
        if (ev.ctrlKey && ev.altKey && ev.key === "A") {
            ev.preventDefault();
            this.toggle();
        }
    }

    // ------------------------------------------------------------------ //
    //  Mensajes
    // ------------------------------------------------------------------ //
    addMessage(role, content, sources) {
        const msg = {
            key: ++this._msgSeq,
            role: role,
            content: content,
            html: role === "assistant" ? this._renderMarkdown(content) : "",
            sources: sources || [],
            showSources: false,
            time: new Date().toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
            }),
        };
        this.state.messages.push(msg);
    }

    setLoading(loading) {
        this.state.loading = loading;
    }

    toggleSources(msg) {
        msg.showSources = !msg.showSources;
    }

    _renderMarkdown(text) {
        if (!text) return "";
        let html = this.aiService.renderMarkdown(text);

        // Envolver en párrafos si no tiene tags de bloque
        if (!html.startsWith("<")) {
            html = "<p>" + html + "</p>";
        }

        // Agrupar <li> en <ul>/<ol>
        html = html.replace(
            /((?:<li class="ai_md_li">.*?<\/li>\s*)+)/g,
            "<ul>$1</ul>"
        );
        html = html.replace(
            /((?:<li class="ai_md_oli">.*?<\/li>\s*)+)/g,
            "<ol>$1</ol>"
        );

        return html;
    }

    // ------------------------------------------------------------------ //
    //  Historial de conversaciones
    // ------------------------------------------------------------------ //
    // Handlers de eventos: identificadores sin argumentos + data-attributes.
    // Este build de OWL ejecuta `t-on-click.stop="method(arg)"` (call con
    // argumentos + modificador) de forma eager durante el render, lo que
    // producía bucles de eliminación. Los identificadores simples con
    // modificador (como systray) compilan correctamente.
    onSelectHistory(ev) {
        this.selectHistory(Number(ev.currentTarget.dataset.id));
    }

    onDeleteChat(ev) {
        this.deleteChat(Number(ev.currentTarget.dataset.id));
    }

    onToggleSources(ev) {
        const msg = this.state.messages.find(
            (m) => m.key === Number(ev.currentTarget.dataset.key)
        );
        if (msg) {
            msg.showSources = !msg.showSources;
        }
    }

    onOpenRecord(ev) {
        this.openRecord(ev.currentTarget.dataset.model, Number(ev.currentTarget.dataset.id));
    }

    async _loadConversations() {
        try {
            this.state.conversations = await this.aiService.getConversations(20);
        } catch (e) {
            // Silenciar error, no es crítico
        }
    }

    async selectHistory(conversationId) {
        try {
            const data = await this.aiService.getConversation(conversationId);
            if (data.error) return;

            this.state.conversationId = data.conversation_id;
            this.state.messages = [];

            data.messages.forEach((msg) => {
                this.addMessage(msg.role, msg.content, msg.sources || []);
            });

            this.state.showHistory = false;
        } catch (e) {
            console.error("AI Assistant - error cargando conversación:", e);
        }
    }

    async deleteChat(conversationId) {
        try {
            await this.aiService.deleteConversation(conversationId);
            await this._loadConversations();
            if (this.state.conversationId === conversationId) {
                this.newChat();
            }
        } catch (e) {
            console.error("AI Assistant - error eliminando conversación:", e);
        }
    }

    newChat() {
        this.state.conversationId = null;
        this.state.messages = [];
        if (this.state.config.welcome_message) {
            this.addMessage("assistant", this.state.config.welcome_message);
        }
        this._detectContext();
        this.state.showHistory = false;
    }

    // ------------------------------------------------------------------ //
    //  Toggle del chat
    // ------------------------------------------------------------------ //
    toggle() {
        this.state.isOpen = !this.state.isOpen;
        if (this.state.isOpen) {
            this._detectContext();
            if (this.inputRef.el) {
                this.inputRef.el.focus();
            }
        }
    }

    close() {
        this.state.isOpen = false;
    }

    toggleHistory() {
        this.state.showHistory = !this.state.showHistory;
        if (this.state.showHistory) {
            this._loadConversations();
        }
    }

    // ------------------------------------------------------------------ //
    //  Navegación a fuentes y configuración
    // ------------------------------------------------------------------ //
    openRecord(model, id) {
        if (model && id) {
            this.env.services.action.doAction({
                type: "ir.actions.act_window",
                res_model: model,
                res_id: id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    openSettings() {
        this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.config.settings",
            views: [[false, "form"]],
            target: "current",
            context: { module: "odoo_ai_assistant" },
        });
    }
}

// Montar el chat flotante dentro del App del webclient (Odoo 17+).
// Se usa el registry `main_components` en vez de `mount()` porque el App
// del webclient ya tiene registrados los templates OWL; `mount()` crearía
// un App nuevo sin ellos (Missing template).
registry.category("main_components").add("ai_assistant", {
    Component: AIAssistant,
});
