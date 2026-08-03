/** @odoo-module **/

import { Component, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

/*
 * Input de voz (portado a Odoo 17 / OWL2).
 * Vosk (local vía servidor) + fallback Web Speech API.
 */
export class VoiceInput extends Component {
    static template = "odoo_ai_assistant.VoiceInput";
    static props = {
        onResult: { type: Function, optional: true },
        onError: { type: Function, optional: true },
        language: { type: String, optional: true },
        useVosk: { type: Boolean, optional: true },
    };

    setup() {
        this.rpc = useService("rpc");
        this.options = {
            onResult: this.props.onResult || (() => {}),
            onError: this.props.onError || (() => {}),
            language: this.props.language || "es-ES",
            useVosk: this.props.useVosk !== undefined ? this.props.useVosk : true,
        };
        this.isRecording = false;
        this._mediaRecorder = null;
        this._audioChunks = [];
        this._recognition = null;
        this._stream = null;
        this._autoStopTimer = null;
        this._voskAvailable = false;

        this.rpc("/ai_assistant/config", {})
            .then((config) => {
                this._voskAvailable = !!config.vosk_available;
                this.options.useVosk = config.voice_enabled && this._voskAvailable;
            })
            .catch(() => {
                this._voskAvailable = false;
                this.options.useVosk = false;
            });

        onWillUnmount(() => {
            this.stopRecording();
            if (this._autoStopTimer) clearTimeout(this._autoStopTimer);
        });
    }

    onToggleRecording(ev) {
        ev.preventDefault();
        if (this.isRecording) this.stopRecording();
        else this.startRecording();
    }

    startRecording() {
        if (this.isRecording) return;
        if (this.options.useVosk && this._voskAvailable) this._startVoskRecording();
        else this._startWebSpeechRecording();
    }

    stopRecording() {
        if (!this.isRecording) return;
        this.isRecording = false;
        if (this.el) this.el.classList.remove("recording");
        const ind = this.el ? this.el.querySelector(".ai_voice_indicator") : null;
        if (ind) ind.classList.remove("active");
        if (this._mediaRecorder && this._mediaRecorder.state === "recording") this._mediaRecorder.stop();
        if (this._recognition) this._recognition.stop();
        if (this._stream) { this._stream.getTracks().forEach((t) => t.stop()); this._stream = null; }
    }

    _setRecordingUI(on) {
        if (!this.el) return;
        this.el.classList.toggle("recording", on);
        const ind = this.el.querySelector(".ai_voice_indicator");
        if (ind) ind.classList.toggle("active", on);
    }

    _startVoskRecording() {
        navigator.mediaDevices
            .getUserMedia({
                audio: { channelCount: 1, sampleRate: 16000, echoCancellation: true, noiseSuppression: true },
            })
            .then((stream) => {
                this._stream = stream;
                this.isRecording = true;
                this._setRecordingUI(true);
                this._audioChunks = [];
                this._mediaRecorder = new MediaRecorder(stream, {
                    mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
                        ? "audio/webm;codecs=opus"
                        : "audio/webm",
                });
                this._mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) this._audioChunks.push(event.data);
                };
                this._mediaRecorder.onstop = () => {
                    const audioBlob = new Blob(this._audioChunks, { type: this._mediaRecorder.mimeType });
                    const reader = new FileReader();
                    reader.onloadend = () => this._transcribeWithVosk(reader.result.split(",")[1]);
                    reader.readAsDataURL(audioBlob);
                };
                this._mediaRecorder.start(1000);
                this._autoStopTimer = setTimeout(() => { if (this.isRecording) this.stopRecording(); }, 60000);
            })
            .catch((err) => {
                console.error("Error accediendo al micrófono:", err);
                this.options.onError(_t("No se pudo acceder al micrófono. Verifica los permisos del navegador."));
            });
    }

    _transcribeWithVosk(base64Audio) {
        this.rpc("/ai_assistant/transcribe", { audio_base64: base64Audio, sample_rate: 16000 })
            .then((result) => {
                if (result.error) { this.options.onError(result.error); return; }
                if (result.text) this.options.onResult(result.text);
            })
            .catch((error) => {
                console.error("Error en transcripción Vosk:", error);
                this.options.onError(_t("Error en la transcripción de voz."));
            });
    }

    _startWebSpeechRecording() {
        const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SR) {
            this.options.onError(_t("Tu navegador no soporta reconocimiento de voz. Usa Chrome o Edge."));
            return;
        }
        this._recognition = new SR();
        this._recognition.lang = this.options.language;
        this._recognition.continuous = false;
        this._recognition.interimResults = true;
        this._recognition.maxAlternatives = 1;
        this.isRecording = true;
        this._setRecordingUI(true);
        this._recognition.onresult = (event) => {
            const last = event.results.length - 1;
            if (event.results[last].isFinal) this.options.onResult(event.results[last][0].transcript);
        };
        this._recognition.onerror = (event) => {
            console.warn("Speech recognition error:", event.error);
            if (event.error === "no-speech") return;
            this.options.onError(_t("Error en reconocimiento de voz: ") + event.error);
        };
        this._recognition.onend = () => {
            this.isRecording = false;
            this._setRecordingUI(false);
        };
        this._recognition.start();
    }
}
