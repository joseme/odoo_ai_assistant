/** @odoo-module **/
// Systray button for the AI Assistant — opens standalone UI

import { registry } from "@web/core/registry";
import { Component, onWillDestroy } from "@odoo/owl";

class AISystrayItem extends Component {
    static template = "odoo_ai_assistant.SystrayIcon";
    static props = {};

    setup() {
        // Keyboard shortcut: Ctrl+Shift+H
        this._onKeyDown = this._onKeyDown.bind(this);
        document.addEventListener("keydown", this._onKeyDown);
        onWillDestroy(() => {
            document.removeEventListener("keydown", this._onKeyDown);
        });
    }

    onClick(ev) {
        ev.preventDefault();
        this._openUI();
    }

    _onKeyDown(ev) {
        if (ev.ctrlKey && ev.shiftKey && ev.key === "H") {
            ev.preventDefault();
            this._openUI();
        }
    }

    _openUI() {
        window.open("/ai_assistant/ui", "_blank", "width=500,height=700");
    }
}

// Register in the systray registry
registry.category("systray").add("ai_assistant", {
    Component: AISystrayItem,
}, { sequence: 10 });
