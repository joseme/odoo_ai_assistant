/** @odoo-module **/

import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/*
 * AI Assistant - Chat flotante (portado a Odoo 17 / OWL2, DOM nativo).
 */
export class AIAssistant extends Component {
    static template = "odoo_ai_assistant.ChatWindow";
    static props = {};

    setup() {
        this.actionService = useService("action");
        this.rpc = useService("rpc");
        this.isOpen = false;
        this.isLoading = false;
        this.isRecording = false;
        this.conversationId = null;
        this.messages = [];
        this.config = { welcome_message: "", tts_enabled: true, voice_enabled: true };
        this.conversations = [];
        this.showHistory = false;
        this.currentContext = {};
        this._audioPlayer = null;
        this._mediaRecorder = null;
        this._audioChunks = [];
        this._stream = null;
        this._autoStopTimer = null;

        this._loadConfig();
        this._detectContext();

        onMounted(() => {
        this._bindShortcuts();
        this._bindDelegatedEvents();
        this.isOpen = true;
        const win = this._qs(".ai_assistant_window");
        const fab = this._qs(".ai_assistant_toggle");
        if (win) win.classList.add("active");
        if (fab) fab.classList.add("active");
        const input = this._qs(".ai_assistant_input");
        if (input) input.focus();
        this._loadConfig().then(() => {
            if (this.config && this.config.welcome_message) {
                const c = this._qs(".ai_assistant_messages");
                if (c && c.children.length === 0) this._addMessage("assistant", this.config.welcome_message);
            }
        });
        this._loadConversations();
        });
        onWillUnmount(() => {
        if (this._audioPlayer) {
            this._audioPlayer.pause();
            this._audioPlayer = null;
        }
        if (this._mediaRecorder && this._mediaRecorder.state === "recording") {
            this._mediaRecorder.stop();
        }
        if (this._autoStopTimer) {
            clearTimeout(this._autoStopTimer);
        }
        document.removeEventListener("keydown", this._keyHandler, true);
        this._qsAll("[data-aiassistant]").forEach((n) => n.remove());
        });
    }

    /** Busca un único elemento bajo la raíz del componente. */
    _qs(sel) {
        return (this.el || document).querySelector(sel);
    }
    _qsAll(sel) {
        return Array.from((this.el || document).querySelectorAll(sel));
    }
    /** Crea un elemento a partir de HTML. */
    _mk(html) {
        const tpl = document.createElement("template");
        tpl.innerHTML = html.trim();
        return tpl.content.firstElementChild;
    }

    _bindShortcuts() {
        this._keyHandler = (ev) => {
            if (ev.ctrlKey && ev.shiftKey && (ev.key === "A" || ev.key === "a")) {
                ev.preventDefault();
                this._onToggle();
            }
        };
        document.addEventListener("keydown", this._keyHandler, true);
    }

    _bindDelegatedEvents() {
        const root = this.el || document;
        root.addEventListener("click", (ev) => {
            const t = ev.target;
            const c = (t.closest ? t.closest.bind(t) : () => null);
            if (t.closest && t.closest(".ai_assistant_toggle")) { this._onToggle(ev); return; }
            if (t.closest && t.closest(".ai_assistant_close")) { this._onClose(ev); return; }
            if (t.closest && t.closest(".ai_assistant_send")) { this._onSend(); return; }
            if (t.closest && t.closest(".ai_assistant_voice_btn")) { this._onVoiceInput(ev); return; }
            if (t.closest && t.closest(".ai_assistant_new_chat")) { this._onNewChat(ev); return; }
            if (t.closest && t.closest(".ai_assistant_history_item")) { this._onSelectHistory(ev); return; }
            if (t.closest && t.closest(".ai_assistant_delete_chat")) { this._onDeleteChat(ev); return; }
            if (t.closest && t.closest(".ai_assistant_play_audio")) { this._onPlayAudio(ev); return; }
            if (t.closest && t.closest(".ai_assistant_source_link")) { this._onSourceLink(ev); return; }
            if (t.closest && t.closest(".ai_assistant_history_toggle")) { this._onHistoryToggle(ev); return; }
            if (t.closest && t.closest(".ai_assistant_settings")) { this._onSettings(ev); return; }
        });
        const input = this._qs(".ai_assistant_input");
        if (input) {
            input.addEventListener("keydown", (ev) => this._onKeyDown(ev));
            input.addEventListener("input", () => this._onInputChange());
        }
    }

    // ------------------------------------------------------------------ //
    //  Configuración
    // ------------------------------------------------------------------ //
    _loadConfig() {
        return this.rpc("/ai_assistant/config", {})
            .then((config) => {
                if (config && typeof config === "object") this.config = Object.assign(this.config, config);
            })
            .catch(() => {});
    }

    _detectContext() {
        try {
            const hash = window.location.hash || "";
            const params = {};
            const qIdx = hash.indexOf("?");
            const hashStr = qIdx === -1 ? hash.substring(1) : hash.substring(1, qIdx);
            hashStr.split("&").forEach((pair) => {
                const kv = pair.split("=");
                if (kv.length === 2) params[kv[0]] = decodeURIComponent(kv[1]);
            });
            this.currentContext = {
                model: params.model || "",
                record_id: params.id || null,
                action: params.action || "",
                view_type: params.view_type || "",
                module: "",
            };
            if (this.currentContext.model) {
                return this.rpc("/ai_assistant/context", {
                    model: this.currentContext.model,
                    record_id: this.currentContext.record_id,
                    action: this.currentContext.action,
                    view_type: this.currentContext.view_type,
                })
                    .then((ctx) => {
                        if (ctx && typeof ctx === "object") this.currentContext = ctx;
                        this._renderContextBar();
                    })
                    .catch(() => {});
            }
        } catch (e) {
            console.warn("Error detectando contexto:", e);
        }
        this._renderContextBar();
        return Promise.resolve();
    }

    _renderContextBar() {
        const bar = this._qs(".ai_assistant_context_bar");
        if (!bar) return;
        const ctx = this.currentContext || {};
        if (ctx.model) {
            const label = ctx.module || ctx.model;
            const title = (ctx.record_name || ctx.model) + (ctx.record_id ? " #" + ctx.record_id : "");
            bar.setAttribute("title", title);
            const badge = bar.querySelector(".ai_assistant_context_badge span");
            if (badge) badge.textContent = label;
            bar.style.display = "";
        } else {
            bar.style.display = "none";
        }
    }

    // ------------------------------------------------------------------ //
    //  Chat - envío de mensajes
    // ------------------------------------------------------------------ //
    _onSend() {
        const input = this._qs(".ai_assistant_input");
        if (!input) return;
        const message = input.value.trim();
        if (!message || this.isLoading) return;
        input.value = "";
        this._addMessage("user", message);
        this._setLoading(true);

        this.rpc("/ai_assistant/chat", {
            message,
            conversation_id: this.conversationId,
            context_info: this.currentContext,
        })
            .then((result) => {
                this._setLoading(false);
                if (result.error) {
                    this._addMessage("system", "Error: " + result.error);
                    return;
                }
                this.conversationId = result.conversation_id;
                this._addMessage("assistant", result.response, result.sources, result.tts_attachment_id);
            })
            .catch((error) => {
                this._setLoading(false);
                this._addMessage("system", _t("Error de conexión. Verifica tu internet y la configuración del asistente."));
                console.error("AI Assistant error:", error);
            });
    }

    _onKeyDown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this._onSend();
        }
    }

    _onInputChange() {
        const input = this._qs(".ai_assistant_input");
        if (input) {
            input.style.height = "auto";
            input.style.height = Math.min(input.scrollHeight, 120) + "px";
        }
    }

    // ------------------------------------------------------------------ //
    //  Mensajes
    // ------------------------------------------------------------------ //
    _addMessage(role, content, sources, ttsAttachmentId) {
        const msg = {
            role,
            content,
            sources: sources || [],
            tts_attachment_id: ttsAttachmentId || false,
            timestamp: new Date(),
        };
        this.messages.push(msg);
        this._renderMessage(msg);
        this._scrollToBottom();
    }

    _renderMessage(msg) {
        const container = this._qs(".ai_assistant_messages");
        if (!container) return;

        const $msg = this._mk('<div class="ai_assistant_msg ai_assistant_msg_' + msg.role + '"></div>');
        const avatar = this._mk('<div class="ai_assistant_msg_avatar"></div>');
        if (msg.role === "user") avatar.innerHTML = '<i class="fa fa-user"></i>';
        else if (msg.role === "assistant") avatar.innerHTML = '<i class="fa fa-comments"></i>';
        else avatar.innerHTML = '<i class="fa fa-info-circle"></i>';

        const content = this._mk('<div class="ai_assistant_msg_content"></div>');
        if (msg.role === "assistant") content.innerHTML = this._renderMarkdown(msg.content);
        else content.textContent = msg.content;

        const meta = this._mk('<div class="ai_assistant_msg_meta"></div>');
        const time = msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        meta.textContent = time;

        if (msg.role === "assistant" && msg.tts_attachment_id && this.config.tts_enabled) {
            const audioBtn = this._mk('<button class="ai_assistant_play_audio" title="Escuchar respuesta"><i class="fa fa-volume-up"></i></button>');
            audioBtn.dataset.attachmentId = msg.tts_attachment_id;
            meta.appendChild(audioBtn);
        }

        if (msg.sources && msg.sources.length > 0) {
            const sources = this._mk('<div class="ai_assistant_sources"></div>');
            const toggle = this._mk('<button class="ai_assistant_sources_toggle"><i class="fa fa-link"></i> Fuentes</button>');
            const list = this._mk('<div class="ai_assistant_sources_list" style="display:none;"></div>');
            msg.sources.forEach((source) => {
                if (source.type === "knowledge") {
                    (source.items || []).forEach((item) => {
                        const el = this._mk('<div class="ai_assistant_source_item"><i class="fa fa-book"></i> <span class="ai_assistant_source_link"></span></div>');
                        const span = el.querySelector(".ai_assistant_source_link");
                        span.dataset.model = item.model;
                        span.dataset.id = item.id;
                        span.textContent = item.title;
                        list.appendChild(el);
                    });
                } else if (source.type === "web") {
                    (source.items || []).forEach((item) => {
                        const el = this._mk('<div class="ai_assistant_source_item"><i class="fa fa-globe"></i> <a target="_blank" rel="noopener"></a></div>');
                        const a = el.querySelector("a");
                        a.href = item.url;
                        a.textContent = item.title;
                        list.appendChild(el);
                    });
                }
            });
            toggle.addEventListener("click", () => {
                list.style.display = list.style.display === "none" ? "" : "none";
                const ic = toggle.querySelector("i");
                if (ic) ic.classList.toggle("fa-chevron-down");
            });
            sources.appendChild(toggle);
            sources.appendChild(list);
            content.appendChild(sources);
        }

        const body = this._mk('<div class="ai_assistant_msg_body"></div>');
        body.appendChild(content);
        body.appendChild(meta);
        $msg.appendChild(avatar);
        $msg.appendChild(body);
        container.appendChild($msg);
    }

    _renderMarkdown(text) {
        if (!text) return "";
        let html = text
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
        if (!html.startsWith("<")) html = "<p>" + html + "</p>";
        html = html.replace(/((?:<li class="ai_md_li">.*?<\/li>\s*)+)/g, "<ul>$1</ul>");
        html = html.replace(/((?:<li class="ai_md_oli">.*?<\/li>\s*)+)/g, "<ol>$1</ol>");
        return html;
    }

    _setLoading(loading) {
        this.isLoading = loading;
        const sendBtn = this._qs(".ai_assistant_send");
        if (sendBtn) sendBtn.disabled = loading;
        const removeLoading = () => {
            this._qsAll(".ai_assistant_loading_msg").forEach((n) => n.remove());
        };
        if (loading) {
            removeLoading();
            const container = this._qs(".ai_assistant_messages");
            if (container) {
                const el = this._mk(
                    '<div class="ai_assistant_msg ai_assistant_msg_assistant ai_assistant_loading_msg">' +
                        '<div class="ai_assistant_msg_avatar"><i class="fa fa-comments"></i></div>' +
                        '<div class="ai_assistant_msg_body"><div class="ai_assistant_typing"><span></span><span></span><span></span></div></div></div>'
                );
                container.appendChild(el);
                this._scrollToBottom();
            }
        } else {
            removeLoading();
        }
    }

    _scrollToBottom() {
        const container = this._qs(".ai_assistant_messages");
        if (container) container.scrollTop = container.scrollHeight;
    }

    // ------------------------------------------------------------------ //
    //  Audio TTS
    // ------------------------------------------------------------------ //
    _onPlayAudio(ev) {
        ev.preventDefault();
        const btn = ev.currentTarget;
        const attachmentId = btn && btn.dataset ? btn.dataset.attachmentId : null;
        if (!attachmentId) return;
        const icon = btn.querySelector("i");
        if (this._audioPlayer) {
            this._audioPlayer.pause();
            this._audioPlayer = null;
            if (icon) { icon.classList.remove("fa-stop"); icon.classList.add("fa-volume-up"); }
            return;
        }
        this._audioPlayer = new Audio("/ai_assistant/audio/" + attachmentId);
        if (icon) { icon.classList.remove("fa-volume-up"); icon.classList.add("fa-stop"); }
        this._audioPlayer.onended = () => {
            if (icon) { icon.classList.remove("fa-stop"); icon.classList.add("fa-volume-up"); }
            this._audioPlayer = null;
        };
        this._audioPlayer.onerror = () => {
            if (icon) { icon.classList.remove("fa-stop"); icon.classList.add("fa-volume-up"); }
            this._audioPlayer = null;
        };
        this._audioPlayer.play().catch((e) => {
            console.warn("Error reproduciendo audio:", e);
            if (icon) { icon.classList.remove("fa-stop"); icon.classList.add("fa-volume-up"); }
        });
    }

    // ------------------------------------------------------------------ //
    //  Voz
    // ------------------------------------------------------------------ //
    _onVoiceInput(ev) {
        ev.preventDefault();
        if (this.isRecording) {
            this._stopRecording();
            return;
        }
        if (!this.config.voice_enabled) {
            this._addMessage("system", _t("El reconocimiento de voz no está habilitado."));
            return;
        }
        if (this.config.vosk_available === false && (window.SpeechRecognition || window.webkitSpeechRecognition)) {
            this._useWebSpeechAPI();
            return;
        }
        this._startVoskRecording();
    }

    _startVoskRecording() {
        this.isRecording = true;
        const btn = this._qs(".ai_assistant_voice_btn");
        if (btn) { btn.classList.add("recording"); const ic = btn.querySelector("i"); if (ic) { ic.classList.remove("fa-microphone"); ic.classList.add("fa-stop"); } }
        navigator.mediaDevices
            .getUserMedia({ audio: true })
            .then((stream) => {
                this._stream = stream;
                this._mediaRecorder = new MediaRecorder(stream);
                this._audioChunks = [];
                this._mediaRecorder.ondataavailable = (event) => this._audioChunks.push(event.data);
                this._mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(this._audioChunks, { type: "audio/wav" });
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        const base64Audio = reader.result.split(",")[1];
                        this._transcribeAudio(base64Audio);
                    };
                    reader.readAsDataURL(audioBlob);
                    if (this._stream) { this._stream.getTracks().forEach((t) => t.stop()); this._stream = null; }
                };
                this._mediaRecorder.start();
            })
            .catch((err) => {
                this.isRecording = false;
                const b2 = this._qs(".ai_assistant_voice_btn");
                if (b2) { b2.classList.remove("recording"); const ic = b2.querySelector("i"); if (ic) { ic.classList.remove("fa-stop"); ic.classList.add("fa-microphone"); } }
                this._addMessage("system", _t("No se pudo acceder al micrófono. Verifica los permisos."));
                console.error("Error accediendo al micrófono:", err);
            });
    }

    _stopRecording() {
        this.isRecording = false;
        const btn = this._qs(".ai_assistant_voice_btn");
        if (btn) { btn.classList.remove("recording"); const ic = btn.querySelector("i"); if (ic) { ic.classList.remove("fa-stop"); ic.classList.add("fa-microphone"); } }
        if (this._mediaRecorder && this._mediaRecorder.state === "recording") this._mediaRecorder.stop();
    }

    _transcribeAudio(base64Audio) {
        this._setLoading(true);
        this.rpc("/ai_assistant/transcribe", { audio_base64: base64Audio, sample_rate: 16000 })
            .then((result) => {
                this._setLoading(false);
                if (result.error) { this._addMessage("system", result.error); return; }
                if (result.text) {
                    const input = this._qs(".ai_assistant_input");
                    if (input) { input.value = result.text; input.focus(); this._onInputChange(); }
                }
            })
            .catch((error) => {
                this._setLoading(false);
                this._addMessage("system", _t("Error en la transcripción de voz."));
                console.error("Transcription error:", error);
            });
    }

    _useWebSpeechAPI() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) { this._addMessage("system", _t("Tu navegador no soporta reconocimiento de voz.")); return; }
        const recognition = new SR();
        recognition.lang = "es-ES";
        recognition.continuous = false;
        recognition.interimResults = false;
        this.isRecording = true;
        const btn = this._qs(".ai_assistant_voice_btn");
        if (btn) { btn.classList.add("recording"); const ic = btn.querySelector("i"); if (ic) { ic.classList.remove("fa-microphone"); ic.classList.add("fa-stop"); } }
        recognition.onresult = (event) => {
            const text = event.results[0][0].transcript;
            const input = this._qs(".ai_assistant_input");
            if (input) { input.value = text; input.focus(); this._onInputChange(); }
        };
        recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            if (event.error !== "no-speech") this._addMessage("system", _t("Error en el reconocimiento de voz: ") + event.error);
        };
        recognition.onend = () => {
            this.isRecording = false;
            const b2 = this._qs(".ai_assistant_voice_btn");
            if (b2) { b2.classList.remove("recording"); const ic = b2.querySelector("i"); if (ic) { ic.classList.remove("fa-stop"); ic.classList.add("fa-microphone"); } }
        };
        recognition.start();
    }

    // ------------------------------------------------------------------ //
    //  Historial
    // ------------------------------------------------------------------ //
    _loadConversations() {
        this.rpc("/ai_assistant/conversations", { limit: 20 })
            .then((conversations) => {
                this.conversations = conversations || [];
                this._renderHistory();
            })
            .catch(() => {});
    }

    _renderHistory() {
        const list = this._qs(".ai_assistant_history_list");
        if (!list) return;
        list.innerHTML = "";
        if (this.conversations.length === 0) {
            list.appendChild(this._mk('<div class="ai_assistant_no_history">No hay conversaciones previas</div>'));
            return;
        }
        this.conversations.forEach((conv) => {
            const item = this._mk(
                '<div class="ai_assistant_history_item" data-id="' + conv.id + '">' +
                    '<div class="ai_assistant_history_item_title"></div>' +
                    '<div class="ai_assistant_history_item_meta"></div>' +
                    '<button class="ai_assistant_delete_chat" data-id="' + conv.id + '" title="Eliminar"><i class="fa fa-trash"></i></button>' +
                    "</div>"
            );
            item.querySelector(".ai_assistant_history_item_title").textContent = this._escapeHtml(conv.title);
            item.querySelector(".ai_assistant_history_item_meta").textContent =
                (conv.context_module || "") + " · " + (conv.message_count || 0) + " mensajes";
            list.appendChild(item);
        });
    }

    _onHistoryToggle(ev) {
        ev.preventDefault();
        this.showHistory = !this.showHistory;
        const hp = this._qs(".ai_assistant_history_panel");
        const cp = this._qs(".ai_assistant_chat_panel");
        if (hp) hp.classList.toggle("active", this.showHistory);
        if (cp) cp.classList.toggle("hidden", this.showHistory);
    }

    _onSelectHistory(ev) {
        ev.preventDefault();
        const item = ev.currentTarget;
        const conversationId = item.dataset.id;
        this.rpc("/ai_assistant/conversation/" + conversationId, {})
            .then((data) => {
                if (data.error) return;
                this.conversationId = data.id;
                this.messages = [];
                const container = this._qs(".ai_assistant_messages");
                if (container) container.innerHTML = "";
                (data.messages || []).forEach((msg) => {
                    let sources = [];
                    try { sources = msg.sources || []; } catch (e) {}
                    this._addMessage(msg.role, msg.content, sources, msg.audio_url ? msg.id : false);
                });
                this.showHistory = false;
                const hp = this._qs(".ai_assistant_history_panel");
                const cp = this._qs(".ai_assistant_chat_panel");
                if (hp) hp.classList.remove("active");
                if (cp) cp.classList.remove("hidden");
            })
            .catch(() => {});
    }

    _onDeleteChat(ev) {
        ev.stopPropagation();
        const btn = ev.currentTarget;
        const conversationId = btn.dataset.id;
        this.rpc("/ai_assistant/conversation/" + conversationId + "/delete", {})
            .then(() => {
                this._loadConversations();
                if (this.conversationId === conversationId) this._onNewChat();
            })
            .catch(() => {});
    }

    _onNewChat(ev) {
        if (ev && ev.preventDefault) ev.preventDefault();
        this.conversationId = null;
        this.messages = [];
        const container = this._qs(".ai_assistant_messages");
        if (container) container.innerHTML = "";
        if (this.config && this.config.welcome_message) this._addMessage("assistant", this.config.welcome_message);
        this._detectContext();
        this.showHistory = false;
        const hp = this._qs(".ai_assistant_history_panel");
        const cp = this._qs(".ai_assistant_chat_panel");
        if (hp) hp.classList.remove("active");
        if (cp) cp.classList.remove("hidden");
    }

    // ------------------------------------------------------------------ //
    //  Toggle / cierre
    // ------------------------------------------------------------------ //
    _onToggle(ev) {
        if (ev && ev.preventDefault) ev.preventDefault();
        this.isOpen = !this.isOpen;
        const win = this._qs(".ai_assistant_window");
        const fab = this._qs(".ai_assistant_toggle");
        if (win) win.classList.toggle("active", this.isOpen);
        if (fab) fab.classList.toggle("active", this.isOpen);
        if (this.isOpen) {
            this._detectContext();
            const input = this._qs(".ai_assistant_input");
            if (input) input.focus();
        }
    }

    _onClose(ev) {
        ev.preventDefault();
        this.isOpen = false;
        const win = this._qs(".ai_assistant_window");
        const fab = this._qs(".ai_assistant_toggle");
        if (win) win.classList.remove("active");
        if (fab) fab.classList.remove("active");
    }

    // ------------------------------------------------------------------ //
    //  Fuentes / configuración
    // ------------------------------------------------------------------ //
    _onSourceLink(ev) {
        ev.preventDefault();
        const el = ev.currentTarget;
        const model = el.dataset.model;
        const id = el.dataset.id;
        if (model && id) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: model,
                res_id: id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    _onSettings(ev) {
        ev.preventDefault();
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "res.config.settings",
            views: [[false, "form"]],
            target: "current",
            context: { module: "odoo_ai_assistant" },
        });
    }

    _escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.appendChild(document.createTextNode(String(text)));
        return div.innerHTML;
    }
}
