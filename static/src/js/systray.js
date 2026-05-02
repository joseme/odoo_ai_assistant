odoo.define("odoo_ai_assistant.Systray", function (require) {
    "use strict";

    var SystrayMenu = require("web.SystrayMenu");
    var Widget = require("web.Widget");
    var AIAssistant = require("odoo_ai_assistant.AIAssistant");
    var core = require("web.core");

    var AISystrayItem = Widget.extend({
        template: "odoo_ai_assistant.SystrayItem",
        events: {
            "click": "_onClick",
        },

        init: function () {
            this._super.apply(this, arguments);
            this._assistant = null;
            this._chatInitialized = false;
            this._bindShortcuts();
        },

        _bindShortcuts: function () {
            // Listen for Ctrl+Shift+A to toggle the AI assistant
            $(document).on("keydown.odoo_ai_assistant", function(ev) {
                // Check for Ctrl+Shift+A (Ctrl=17, Shift=16, A=65)
                if (ev.ctrlKey && ev.shiftKey && ev.keyCode === 65) {
                    ev.preventDefault();
                    this._triggerAssistant();
                }
            }.bind(this));
        },

        _triggerAssistant: function () {
            var self = this;

            if (!this._assistant) {
                this._assistant = new AIAssistant(this);
                this._assistant.attachTo(document.body).then(function() {
                    self._chatInitialized = true;
                    self._assistant._onToggle();
                });
            } else {
                this._assistant._onToggle();
            }
        },

        _onClick: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            this._triggerAssistant();
        },

        destroy: function () {
            $(document).off(".odoo_ai_assistant");
            if (this._assistant) {
                this._assistant.destroy();
                this._assistant = null;
            }
            this._super.apply(this, arguments);
        },
    });

    SystrayMenu.Items.push(AISystrayItem);

    return AISystrayItem;
});