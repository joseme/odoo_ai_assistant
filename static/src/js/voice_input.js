odoo.define("odoo_ai_assistant.VoiceInput", ["web.core", "web.Widget", "web.rpc"], function (require) {
    "use strict";

    var core = require("web.core");
    var Widget = require("web.Widget");
    var rpc = require("web.rpc");
    var _t = core._t;

    /**
     * Componente de reconocimiento de voz para el Asistente de IA.
     * Soporta dos modos:
     * 1. Vosk (local): Envía audio al servidor para transcripción con Vosk
     * 2. Web Speech API (fallback): Usa el reconocimiento nativo del navegador
     *
     * Compatible con Odoo 17, 18 y 19.
     */
    var VoiceInput = Widget.extend({
        template: "odoo_ai_assistant.VoiceInput",
        events: {
            "click .ai_voice_btn": "_onToggleRecording",
        },

        /**
         * @param {Object} options
         * @param {Function} options.onResult - Callback con el texto transcrito
         * @param {Function} options.onError - Callback con el error
         * @param {String} options.language - Idioma para reconocimiento (default: 'es-ES')
         * @param {Boolean} options.useVosk - Forzar uso de Vosk (default: true si está disponible)
         */
        init: function (parent, options) {
            this._super.apply(this, arguments);
            this.options = _.defaults(options || {}, {
                onResult: function () {},
                onError: function () {},
                language: "es-ES",
                useVosk: true,
            });
            this.isRecording = false;
            this._mediaRecorder = null;
            this._audioChunks = [];
            this._recognition = null;
            this._stream = null;
            this._voskAvailable = false;
        },

        willStart: function () {
            var self = this;
            // Verificar disponibilidad de Vosk en el servidor
            return rpc
                .query({
                    route: "/ai_assistant/config",
                    params: {},
                })
                .then(function (config) {
                    self._voskAvailable = config.vosk_available;
                    self.options.useVosk = config.voice_enabled && self._voskAvailable;
                })
                .catch(function () {
                    self._voskAvailable = false;
                    self.options.useVosk = false;
                });
        },

        start: function () {
            this._super.apply(this, arguments);
            this.$btn = this.$(".ai_voice_btn");
            this.$indicator = this.$(".ai_voice_indicator");
            return Promise.resolve();
        },

        // ------------------------------------------------------------------ //
        //  Grabación de voz
        // ------------------------------------------------------------------ //
        _onToggleRecording: function () {
            if (this.isRecording) {
                this.stopRecording();
            } else {
                this.startRecording();
            }
        },

        startRecording: function () {
            if (this.isRecording) return;

            // Decidir método de reconocimiento
            if (this.options.useVosk && this._voskAvailable) {
                this._startVoskRecording();
            } else {
                this._startWebSpeechRecording();
            }
        },

        stopRecording: function () {
            if (!this.isRecording) return;

            this.isRecording = false;
            this.$btn.removeClass("recording");
            this.$indicator.removeClass("active");

            if (this._mediaRecorder && this._mediaRecorder.state === "recording") {
                this._mediaRecorder.stop();
            }

            if (this._recognition) {
                this._recognition.stop();
            }

            if (this._stream) {
                this._stream.getTracks().forEach(function (track) {
                    track.stop();
                });
                this._stream = null;
            }
        },

        // ------------------------------------------------------------------ //
        //  Vosk - Grabación y envío al servidor
        // ------------------------------------------------------------------ //
        _startVoskRecording: function () {
            var self = this;

            navigator.mediaDevices
                .getUserMedia({
                    audio: {
                        channelCount: 1,
                        sampleRate: 16000,
                        echoCancellation: true,
                        noiseSuppression: true,
                    },
                })
                .then(function (stream) {
                    self._stream = stream;
                    self.isRecording = true;
                    self.$btn.addClass("recording");
                    self.$indicator.addClass("active");
                    self._audioChunks = [];

                    self._mediaRecorder = new MediaRecorder(stream, {
                        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                            ? "audio/webm;codecs=opus"
                            : "audio/webm",
                    });

                    self._mediaRecorder.ondataavailable = function (event) {
                        if (event.data.size > 0) {
                            self._audioChunks.push(event.data);
                        }
                    };

                    self._mediaRecorder.onstop = function () {
                        var audioBlob = new Blob(self._audioChunks, {
                            type: self._mediaRecorder.mimeType,
                        });

                        // Convertir a base64 y enviar al servidor
                        var reader = new FileReader();
                        reader.onloadend = function () {
                            var base64Audio = reader.result.split(",")[1];
                            self._transcribeWithVosk(base64Audio);
                        };
                        reader.readAsDataURL(audioBlob);
                    };

                    // Grabar en intervalos de 1 segundo para mejor UX
                    self._mediaRecorder.start(1000);

                    // Auto-detener después de 60 segundos
                    self._autoStopTimer = setTimeout(function () {
                        if (self.isRecording) {
                            self.stopRecording();
                        }
                    }, 60000);
                })
                .catch(function (err) {
                    console.error("Error accediendo al micrófono:", err);
                    self.options.onError(
                        _t("No se pudo acceder al micrófono. Verifica los permisos del navegador.")
                    );
                });
        },

        _transcribeWithVosk: function (base64Audio) {
            var self = this;

            rpc.query({
                route: "/ai_assistant/transcribe",
                params: {
                    audio_base64: base64Audio,
                    sample_rate: 16000,
                },
            })
            .then(function (result) {
                if (result.error) {
                    self.options.onError(result.error);
                    return;
                }
                if (result.text) {
                    self.options.onResult(result.text);
                }
            })
            .catch(function (error) {
                console.error("Error en transcripción Vosk:", error);
                self.options.onError(_t("Error en la transcripción de voz."));
            });
        },

        // ------------------------------------------------------------------ //
        //  Web Speech API - Fallback del navegador
        // ------------------------------------------------------------------ //
        _startWebSpeechRecording: function () {
            var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

            if (!SpeechRecognition) {
                this.options.onError(
                    _t("Tu navegador no soporta reconocimiento de voz. Usa Chrome o Edge.")
                );
                return;
            }

            var self = this;
            this._recognition = new SpeechRecognition();
            this._recognition.lang = this.options.language;
            this._recognition.continuous = false;
            this._recognition.interimResults = true;
            this._recognition.maxAlternatives = 1;

            this.isRecording = true;
            this.$btn.addClass("recording");
            this.$indicator.addClass("active");

            this._recognition.onresult = function (event) {
                var last = event.results.length - 1;
                var text = event.results[last][0].transcript;
                var isFinal = event.results[last].isFinal;

                if (isFinal) {
                    self.options.onResult(text);
                }
            };

            this._recognition.onerror = function (event) {
                console.warn("Speech recognition error:", event.error);
                if (event.error === "no-speech") {
                    // No se detectó voz, no mostrar error
                    return;
                }
                self.options.onError(
                    _t("Error en reconocimiento de voz: ") + event.error
                );
            };

            this._recognition.onend = function () {
                self.isRecording = false;
                self.$btn.removeClass("recording");
                self.$indicator.removeClass("active");
            };

            this._recognition.start();
        },

        // ------------------------------------------------------------------ //
        //  Limpieza
        // ------------------------------------------------------------------ //
        destroy: function () {
            this.stopRecording();
            if (this._autoStopTimer) {
                clearTimeout(this._autoStopTimer);
            }
            this._super.apply(this, arguments);
        },
    });

    return VoiceInput;
});
