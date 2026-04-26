/* @odoo-module alias=odoo_ai_assistant.Systray */
odoo.define("odoo_ai_assistant.Systray", function (require) {
    "use strict";

    var SystrayMenu = require("web.SystrayMenu");
    var Widget = require("web.Widget");
    var AIAssistant = require("odoo_ai_assistant.AIAssistant");
    var rpc = require("web.rpc");

    /**
     * Botón del asistente de IA en la barra de systray de Odoo.
     * Compatible con Odoo 17, 18 y 19.
     */
    var AISystrayItem = Widget.extend({
        template: "odoo_ai_assistant.SystrayItem",
        events: {
            click: "_onClick",
        },

        init: function () {
            this._super.apply(this, arguments);
            this._assistant = null;
        },

        _onClick: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();

            if (!this._assistant) {
                this._assistant = new AIAssistant(this);
                this._assistant.appendTo("body");
            }

            this._assistant._onToggle();
        },

        destroy: function () {
            if (this._assistant) {
                this._assistant.destroy();
                this._assistant = null;
            }
            this._super.apply(this, arguments);
        },
    });

    // Añadir al systray menu
    SystrayMenu.Items.push(AISystrayItem);

    return AISystrayItem;
});
