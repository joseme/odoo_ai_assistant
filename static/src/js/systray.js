/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { AIAssistant } from "./ai_assistant";

/*
 * Ítem de Systray para abrir el AI Assistant (Odoo 17 / OWL2).
 */
export class AISystrayItem extends Component {
    static template = "odoo_ai_assistant.SystrayItem";
    static components = { AIAssistant };
    static props = {};

    setup() {
        this.state = useState({ open: false });
    }

    onToggle(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.state.open = !this.state.open;
    }
}

registry.category("systray").add(
    "odoo_ai_assistant.systray",
    { Component: AISystrayItem },
    { sequence: 50 }
);
