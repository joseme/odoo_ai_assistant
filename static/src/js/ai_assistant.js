odoo.define("odoo_ai_assistant.AIAssistant", ["web.core", "web.Widget", "web.rpc"], function (require) {
    "use strict";

    var core = require("web.core");
    var Widget = require("web.Widget");
    var rpc = require("web.rpc");
    var _t = core._t;
    var QWeb = core.qweb;

    // Crear FAB automáticamente si no existe
    function _createFab() {
        if (document.querySelector(".ai_assistant_fab")) {
            console.log(">>> FAB ya existe");
            return;
        }
        console.log(">>> Creando FAB");
        var fab = document.createElement("div");
        fab.className = "ai_assistant_fab ai_assistant_toggle";
        fab.title = "Asistente de IA (Ctrl+Alt+A)";
        fab.innerHTML = '<i class="bi bi-apps"></i>';
        fab.style.display = "none";
        
        // Agregar event listener directamente
        fab.addEventListener("click", function(e) {
            console.log(">>> Click en FAB manual");
            // Buscar si el widget ya está inicializado
            var widgetInstance = window._aiAssistantInstance;
            if (widgetInstance) {
                console.log(">>> Usando widget existente");
                widgetInstance._onToggle();
            } else {
                console.log(">>> Widget no inicializado, creando nuevo");
            }
        });
        
        document.body.appendChild(fab);
        // Mostrar después de un delay para asegurar que el DOM está listo
        setTimeout(function() { fab.style.display = "flex"; }, 1000);
    }

    // Keyboard shortcut global
    document.addEventListener("keydown", function(ev) {
        if (ev.ctrlKey && ev.altKey && ev.key === "A") {
            ev.preventDefault();
            _toggleOrCreate();
        }
    });

    function _toggleOrCreate() {
        var existing = document.querySelector(".ai_assistant_fab");
        if (!existing) {
            _createFab();
        }
        // Trigger click en el FAB
        if (existing) {
            existing.click();
        }
    }

    var AIAssistant = Widget.extend({
        template: "odoo_ai_assistant.ChatWindow",
        events: {
            "click .ai_assistant_toggle": "_onToggle",
            "click .ai_assistant_close": "_onClose",
            "click .ai_assistant_send": "_onSend",
            "keydown .ai_assistant_input": "_onKeyDown",
            "click .ai_assistant_voice_btn": "_onVoiceInput",
            "click .ai_assistant_new_chat": "_onNewChat",
            "click .ai_assistant_history_item": "_onSelectHistory",
            "click .ai_assistant_delete_chat": "_onDeleteChat",
            "click .ai_assistant_play_audio": "_onPlayAudio",
            "click .ai_assistant_source_link": "_onSourceLink",
            "click .ai_assistant_history_toggle": "_onHistoryToggle",
            "click .ai_assistant_settings": "_onSettings",
            "input .ai_assistant_input": "_onInputChange",
        },

        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.isOpen = false;
            this.isLoading = false;
            this.isRecording = false;
            this.conversationId = null;
            this.messages = [];
            this.config = {};
            this.conversations = [];
            this.showHistory = false;
            this.currentContext = {};
            this._audioPlayer = null;
        },

        willStart: function () {
            return Promise.all([
                this._loadConfig(),
                this._detectContext(),
            ]);
        },

        start: function () {
            this._super.apply(this, arguments);
            this.$input = this.$(".ai_assistant_input");
            this.$messages = this.$(".ai_assistant_messages");
            this.$sendBtn = this.$(".ai_assistant_send");

            // Guardar instancia global para el click del FAB
            window._aiAssistantInstance = this;
            console.log(">>> Widget iniciado, instancia guardada en window");

            // Mostrar mensaje de bienvenida
            if (this.config.welcome_message) {
                this._addMessage("assistant", this.config.welcome_message);
            }

            // Cargar conversaciones previas
            this._loadConversations();

            return Promise.resolve();
        },

        // ------------------------------------------------------------------ //
        //  Configuración
        // ------------------------------------------------------------------ //
        _loadConfig: function () {
            var self = this;
            return rpc
                .query({
                    route: "/ai_assistant/config",
                    params: {},
                })
                .then(function (config) {
                    self.config = config;
                })
                .catch(function () {
                    self.config = {
                        voice_enabled: true,
                        tts_enabled: true,
                        web_search_enabled: true,
                        welcome_message: "¡Hola! Soy tu asistente de IA en Odoo. ¿En qué puedo ayudarte?",
                    };
                });
        },

        // ------------------------------------------------------------------ //
        //  Detección de Contexto
        // ------------------------------------------------------------------ //
        _detectContext: function () {
            var self = this;
            try {
                // Detectar contexto desde la URL actual de Odoo
                var url = window.location.href;
                var hash = window.location.hash;

                // Parsear el hash de Odoo (formato: #id=XX&view_type=form&model=XX&action=XX)
                var params = {};
                if (hash) {
                    var hashStr = hash.substring(1); // Remover #
                    hashStr.split("&").forEach(function (pair) {
                        var kv = pair.split("=");
                        if (kv.length === 2) {
                            params[kv[0]] = decodeURIComponent(kv[1]);
                        }
                    });
                }

                self.currentContext = {
                    model: params.model || "",
                    record_id: params.id || null,
                    action: params.action || "",
                    view_type: params.view_type || "",
                    module: "",
                };

                // Obtener contexto enriquecido del servidor
                if (self.currentContext.model) {
                    return rpc
                        .query({
                            route: "/ai_assistant/context",
                            params: {
                                model: self.currentContext.model,
                                record_id: self.currentContext.record_id,
                                action: self.currentContext.action,
                                view_type: self.currentContext.view_type,
                            },
                        })
                        .then(function (ctx) {
                            self.currentContext = ctx;
                        })
                        .catch(function () {
                            // Usar contexto local si falla la petición
                        });
                }
            } catch (e) {
                console.warn("Error detectando contexto:", e);
            }
            return Promise.resolve();
        },

        // ------------------------------------------------------------------ //
        //  Chat - Envío de mensajes
        // ------------------------------------------------------------------ //
        _onSend: function () {
            var message = this.$input.val().trim();
            if (!message || this.isLoading) return;

            console.log(">>> Enviando mensaje:", message);
            
            this.$input.val("");
            this._addMessage("user", message);
            this._setLoading(true);

            var self = this;
            rpc.query({
                route: "/ai_assistant/chat",
                params: {
                    message: message,
                    conversation_id: self.conversationId,
                    context_info: self.currentContext,
                },
            })
            .then(function (result) {
                console.log(">>> Respuesta recibida:", result);
                self._setLoading(false);
                if (result.error) {
                    self._addMessage("system", "Error: " + result.error);
                    return;
                }
                self.conversationId = result.conversation_id;
                self._addMessage("assistant", result.response, result.sources, result.tts_attachment_id);
            })
            .catch(function (error) {
                self._setLoading(false);
                self._addMessage(
                    "system",
                    "Error de conexión. Por favor, verifica tu conexión a internet y la configuración del asistente."
                );
                console.error("AI Assistant error:", error);
            });
        },

        _onKeyDown: function (ev) {
            if (ev.key === "Enter" && !ev.shiftKey) {
                ev.preventDefault();
                this._onSend();
            }
        },

        _onInputChange: function () {
            // Auto-resize del textarea
            var input = this.$input[0];
            input.style.height = "auto";
            input.style.height = Math.min(input.scrollHeight, 120) + "px";
        },

        // ------------------------------------------------------------------ //
        //  Mensajes
        // ------------------------------------------------------------------ //
        _addMessage: function (role, content, sources, ttsAttachmentId) {
            var msg = {
                role: role,
                content: content,
                sources: sources || [],
                tts_attachment_id: ttsAttachmentId || false,
                timestamp: new Date(),
            };
            this.messages.push(msg);
            this._renderMessage(msg);
            this._scrollToBottom();
        },

        _renderMessage: function (msg) {
            var $msg = $('<div class="ai_assistant_msg ai_assistant_msg_' + msg.role + '"></div>');

            // Avatar
            var $avatar = $('<div class="ai_assistant_msg_avatar"></div>');
            if (msg.role === "user") {
                $avatar.html('<i class="bi bi-person"></i>');
            } else if (msg.role === "assistant") {
                $avatar.html('<i class="bi bi-apps"></i>');
            } else {
                $avatar.html('<i class="bi bi-info-circle"></i>');
            }

            // Contenido
            var $content = $('<div class="ai_assistant_msg_content"></div>');
            if (msg.role === "assistant") {
                // Renderizar Markdown de forma simple
                $content.html(this._renderMarkdown(msg.content));
            } else {
                $content.text(msg.content);
            }

            // Metadata
            var $meta = $('<div class="ai_assistant_msg_meta"></div>');
            var time = msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
            $meta.text(time);

            // Botón de audio TTS
            if (msg.role === "assistant" && msg.tts_attachment_id && this.config.tts_enabled) {
                var $audioBtn = $(
                    '<button class="ai_assistant_play_audio" title="Escuchar respuesta">' +
                    '<i class="bi bi-volume-up"></i></button>'
                );
                $audioBtn.data("attachment-id", msg.tts_attachment_id);
                $meta.append($audioBtn);
            }

            // Fuentes
            if (msg.sources && msg.sources.length > 0) {
                var $sources = $('<div class="ai_assistant_sources"></div>');
                var $sourcesToggle = $(
                    '<button class="ai_assistant_sources_toggle">' +
                    '<i class="bi bi-link-45deg"></i> Fuentes</button>'
                );
                var $sourcesList = $('<div class="ai_assistant_sources_list" style="display:none;"></div>');

                msg.sources.forEach(function (source) {
                    if (source.type === "knowledge") {
                        source.items.forEach(function (item) {
                            $sourcesList.append(
                                '<div class="ai_assistant_source_item">' +
                                '<i class="bi bi-book"></i> ' +
                                '<span class="ai_assistant_source_link" data-model="' +
                                item.model + '" data-id="' + item.id + '">' +
                                item.title + "</span></div>"
                            );
                        });
                    } else if (source.type === "web") {
                        source.items.forEach(function (item) {
                            $sourcesList.append(
                                '<div class="ai_assistant_source_item">' +
                                '<i class="bi bi-globe"></i> ' +
                                '<a href="' + item.url + '" target="_blank" rel="noopener">' +
                                item.title + "</a></div>"
                            );
                        });
                    }
                });

                $sourcesToggle.on("click", function () {
                    $sourcesList.toggle();
                    $(this).find("i").toggleClass("bi bi-link-45deg bi bi-chevron-down");
                });

                $sources.append($sourcesToggle).append($sourcesList);
                $content.append($sources);
            }

            $msg.append($avatar).append(
                $('<div class="ai_assistant_msg_body"></div>').append($content).append($meta)
            );

            this.$messages.append($msg);
        },

        _renderMarkdown: function (text) {
            if (!text) return "";
            // Conversión simple de Markdown a HTML
            var html = text
                // Bloques de código
                .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code class="$1">$2</code></pre>')
                // Código inline
                .replace(/`([^`]+)`/g, "<code>$1</code>")
                // Encabezados
                .replace(/^### (.+)$/gm, "<h4>$1</h4>")
                .replace(/^## (.+)$/gm, "<h3>$1</h3>")
                .replace(/^# (.+)$/gm, "<h2>$1</h2>")
                // Negrita
                .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
                // Cursiva
                .replace(/\*([^*]+)\*/g, "<em>$1</em>")
                // Listas no ordenadas
                .replace(/^[*-] (.+)$/gm, '<li class="ai_md_li">$1</li>')
                // Listas ordenadas
                .replace(/^\d+\. (.+)$/gm, '<li class="ai_md_oli">$1</li>')
                // Links
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
                // Saltos de línea
                .replace(/\n\n/g, "</p><p>")
                .replace(/\n/g, "<br>");

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
        },

        _setLoading: function (loading) {
            this.isLoading = loading;
            if (loading) {
                this.$sendBtn.prop("disabled", true);
                var $loadingMsg = $(
                    '<div class="ai_assistant_msg ai_assistant_msg_assistant ai_assistant_loading_msg">' +
                    '<div class="ai_assistant_msg_avatar"><i class="bi bi-apps"></i></div>' +
                    '<div class="ai_assistant_msg_body">' +
                    '<div class="ai_assistant_typing">' +
                    '<span></span><span></span><span></span>' +
                    "</div></div></div>"
                );
                this.$messages.append($loadingMsg);
                this._scrollToBottom();
            } else {
                this.$sendBtn.prop("disabled", false);
                this.$(".ai_assistant_loading_msg").remove();
            }
        },

        _scrollToBottom: function () {
            var container = this.$messages[0];
            if (container) {
                container.scrollTop = container.scrollHeight;
            }
        },

        // ------------------------------------------------------------------ //
        //  Audio - TTS playback
        // ------------------------------------------------------------------ //
        _onPlayAudio: function (ev) {
            var $btn = $(ev.currentTarget);
            var attachmentId = $btn.data("attachment-id");

            if (!attachmentId) return;

            // Detener audio actual si está reproduciéndose
            if (this._audioPlayer) {
                this._audioPlayer.pause();
                this._audioPlayer = null;
                $btn.find("i").removeClass("bi bi-stop-fill").addClass("bi bi-volume-up");
                return;
            }

            // Reproducir nuevo audio
            var audioUrl = "/ai_assistant/audio/" + attachmentId;
            this._audioPlayer = new Audio(audioUrl);
            $btn.find("i").removeClass("bi bi-volume-up").addClass("bi bi-stop-fill");

            this._audioPlayer.onended = function () {
                $btn.find("i").removeClass("bi bi-stop-fill").addClass("bi bi-volume-up");
                this._audioPlayer = null;
            }.bind(this);

            this._audioPlayer.onerror = function () {
                $btn.find("i").removeClass("bi bi-stop-fill").addClass("bi bi-volume-up");
                this._audioPlayer = null;
            }.bind(this);

            this._audioPlayer.play().catch(function (e) {
                console.warn("Error reproduciendo audio:", e);
                $btn.find("i").removeClass("bi bi-stop-fill").addClass("bi bi-volume-up");
            });
        },

        // ------------------------------------------------------------------ //
        //  Voz - Input con Vosk
        // ------------------------------------------------------------------ //
        _onVoiceInput: function () {
            if (this.isRecording) {
                this._stopRecording();
                return;
            }

            if (!this.config.voice_enabled) {
                this._addMessage("system", "El reconocimiento de voz no está habilitado.");
                return;
            }

            // Intentar usar Web Speech API como fallback si Vosk no está disponible
            if (this.config.vosk_available === false && "webkitSpeechRecognition" in window) {
                this._useWebSpeechAPI();
                return;
            }

            // Usar Vosk vía MediaRecorder + envío al servidor
            this._startVoskRecording();
        },

        _startVoskRecording: function () {
            var self = this;
            this.isRecording = true;
            this.$(".ai_assistant_voice_btn").addClass("recording");
            this.$(".ai_assistant_voice_btn i").removeClass("bi bi-mic").addClass("bi bi-stop-fill");

            navigator.mediaDevices
                .getUserMedia({ audio: true })
                .then(function (stream) {
                    self._mediaRecorder = new MediaRecorder(stream);
                    self._audioChunks = [];

                    self._mediaRecorder.ondataavailable = function (event) {
                        self._audioChunks.push(event.data);
                    };

                    self._mediaRecorder.onstop = function () {
                        var audioBlob = new Blob(self._audioChunks, { type: "audio/wav" });
                        var reader = new FileReader();
                        reader.onloadend = function () {
                            var base64Audio = reader.result.split(",")[1];
                            self._transcribeAudio(base64Audio);
                        };
                        reader.readAsDataURL(audioBlob);

                        // Detener stream
                        stream.getTracks().forEach(function (track) {
                            track.stop();
                        });
                    };

                    self._mediaRecorder.start();
                })
                .catch(function (err) {
                    self.isRecording = false;
                    self.$(".ai_assistant_voice_btn").removeClass("recording");
                    self.$(".ai_assistant_voice_btn i").removeClass("bi bi-stop-fill").addClass("bi bi-mic");
                    self._addMessage("system", "No se pudo acceder al micrófono. Verifica los permisos.");
                    console.error("Error accediendo al micrófono:", err);
                });
        },

        _stopRecording: function () {
            this.isRecording = false;
            this.$(".ai_assistant_voice_btn").removeClass("recording");
            this.$(".ai_assistant_voice_btn i").removeClass("bi bi-stop-fill").addClass("bi bi-mic");

            if (this._mediaRecorder && this._mediaRecorder.state === "recording") {
                this._mediaRecorder.stop();
            }
        },

        _transcribeAudio: function (base64Audio) {
            var self = this;
            this._setLoading(true);

            rpc.query({
                route: "/ai_assistant/transcribe",
                params: {
                    audio_base64: base64Audio,
                    sample_rate: 16000,
                },
            })
            .then(function (result) {
                self._setLoading(false);
                if (result.error) {
                    self._addMessage("system", result.error);
                    return;
                }
                if (result.text) {
                    self.$input.val(result.text);
                    self.$input.focus();
                    self._onInputChange();
                }
            })
            .catch(function (error) {
                self._setLoading(false);
                self._addMessage("system", "Error en la transcripción de voz.");
                console.error("Transcription error:", error);
            });
        },

        _useWebSpeechAPI: function () {
            // Fallback: Web Speech API del navegador
            var self = this;
            var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

            if (!SpeechRecognition) {
                this._addMessage("system", "Tu navegador no soporta reconocimiento de voz.");
                return;
            }

            var recognition = new SpeechRecognition();
            recognition.lang = "es-ES";
            recognition.continuous = false;
            recognition.interimResults = false;

            this.isRecording = true;
            this.$(".ai_assistant_voice_btn").addClass("recording");
            this.$(".ai_assistant_voice_btn i").removeClass("bi bi-mic").addClass("bi bi-stop-fill");

            recognition.onresult = function (event) {
                var text = event.results[0][0].transcript;
                self.$input.val(text);
                self.$input.focus();
                self._onInputChange();
            };

            recognition.onerror = function (event) {
                console.warn("Speech recognition error:", event.error);
                if (event.error !== "no-speech") {
                    self._addMessage("system", "Error en el reconocimiento de voz: " + event.error);
                }
            };

            recognition.onend = function () {
                self.isRecording = false;
                self.$(".ai_assistant_voice_btn").removeClass("recording");
                self.$(".ai_assistant_voice_btn i").removeClass("bi bi-stop-fill").addClass("bi bi-mic");
            };

            recognition.start();
        },

        // ------------------------------------------------------------------ //
        //  Historial de conversaciones
        // ------------------------------------------------------------------ //
        _loadConversations: function () {
            var self = this;
            rpc.query({
                route: "/ai_assistant/conversations",
                params: { limit: 20 },
            })
            .then(function (conversations) {
                self.conversations = conversations;
                self._renderHistory();
            })
            .catch(function () {
                // Silenciar error, no es crítico
            });
        },

        _renderHistory: function () {
            var $historyList = this.$(".ai_assistant_history_list");
            $historyList.empty();

            if (this.conversations.length === 0) {
                $historyList.append('<div class="ai_assistant_no_history">No hay conversaciones previas</div>');
                return;
            }

            var self = this;
            this.conversations.forEach(function (conv) {
                var $item = $(
                    '<div class="ai_assistant_history_item" data-id="' + conv.id + '">' +
                    '<div class="ai_assistant_history_item_title">' + self._escapeHtml(conv.title) + "</div>" +
                    '<div class="ai_assistant_history_item_meta">' +
                    (conv.context_module || "") + " · " +
                    (conv.message_count || 0) + " mensajes" +
                    "</div>" +
                    '<button class="ai_assistant_delete_chat" data-id="' + conv.id + '" title="Eliminar">' +
                    '<i class="bi bi-trash"></i></button>' +
                    "</div>"
                );
                $historyList.append($item);
            });
        },

        _onHistoryToggle: function () {
            this.showHistory = !this.showHistory;
            this.$(".ai_assistant_history_panel").toggleClass("active", this.showHistory);
            this.$(".ai_assistant_chat_panel").toggleClass("hidden", this.showHistory);
        },

        _onSelectHistory: function (ev) {
            var $item = $(ev.currentTarget);
            var conversationId = $item.data("id");

            var self = this;
            rpc.query({
                route: "/ai_assistant/conversation/" + conversationId,
                params: {},
            })
            .then(function (data) {
                if (data.error) return;

                self.conversationId = data.id;
                self.messages = [];
                self.$messages.empty();

                data.messages.forEach(function (msg) {
                    var sources = [];
                    try {
                        sources = msg.sources || [];
                    } catch (e) {
                        // Ignorar error de parseo
                    }
                    self._addMessage(msg.role, msg.content, sources, msg.audio_url ? msg.id : false);
                });

                self.showHistory = false;
                self.$(".ai_assistant_history_panel").removeClass("active");
                self.$(".ai_assistant_chat_panel").removeClass("hidden");
            });
        },

        _onDeleteChat: function (ev) {
            ev.stopPropagation();
            var $btn = $(ev.currentTarget);
            var conversationId = $btn.data("id");

            var self = this;
            rpc.query({
                route: "/ai_assistant/conversation/" + conversationId + "/delete",
                params: {},
            })
            .then(function () {
                self._loadConversations();
                if (self.conversationId === conversationId) {
                    self._onNewChat();
                }
            });
        },

        _onNewChat: function () {
            this.conversationId = null;
            this.messages = [];
            this.$messages.empty();
            if (this.config.welcome_message) {
                this._addMessage("assistant", this.config.welcome_message);
            }
            this._detectContext();
            this.showHistory = false;
            this.$(".ai_assistant_history_panel").removeClass("active");
            this.$(".ai_assistant_chat_panel").removeClass("hidden");
        },

        // ------------------------------------------------------------------ //
        //  Toggle del chat
        // ------------------------------------------------------------------ //
        _onToggle: function () {
            this.isOpen = !this.isOpen;
            this.$(".ai_assistant_window").toggleClass("active", this.isOpen);
            this.$(".ai_assistant_toggle").toggleClass("active", this.isOpen);

            if (this.isOpen) {
                this._detectContext();
                this.$input.focus();
            }
        },

        _onClose: function () {
            this.isOpen = false;
            this.$(".ai_assistant_window").removeClass("active");
            this.$(".ai_assistant_toggle").removeClass("active");
        },

        // ------------------------------------------------------------------ //
        //  Navegación a fuentes
        // ------------------------------------------------------------------ //
        _onSourceLink: function (ev) {
            var $el = $(ev.currentTarget);
            var model = $el.data("model");
            var id = $el.data("id");

            if (model && id) {
                // Navegar al registro en Odoo
                this.trigger_up("do_action", {
                    action: {
                        type: "ir.actions.act_window",
                        res_model: model,
                        res_id: id,
                        views: [[false, "form"]],
                        target: "current",
                    },
                });
            }
        },

        // ------------------------------------------------------------------ //
        //  Configuración
        // ------------------------------------------------------------------ //
        _onSettings: function () {
            this.trigger_up("do_action", {
                action: {
                    type: "ir.actions.act_window",
                    res_model: "res.config.settings",
                    views: [[false, "form"]],
                    target: "current",
                    context: { module: "odoo_ai_assistant" },
                },
            });
        },

        // ------------------------------------------------------------------ //
        //  Utilidades
        // ------------------------------------------------------------------ //
        _escapeHtml: function (text) {
            if (!text) return "";
            var div = document.createElement("div");
            div.appendChild(document.createTextNode(text));
            return div.innerHTML;
        },

        destroy: function () {
            if (this._audioPlayer) {
                this._audioPlayer.pause();
                this._audioPlayer = null;
            }
            if (this._mediaRecorder && this._mediaRecorder.state === "recording") {
                this._mediaRecorder.stop();
            }
            this._super.apply(this, arguments);
        },
    });

    return AIAssistant;
});
