// AI Assistant FAB - Standalone (NO AMD)
(function() {
    'use strict';
    
    var isOpen = false;
    var conversationId = null;
    
    // Convierte Markdown a texto plano: **texto** -> «texto», `codigo` -> 'codigo', etc.
    function markdownToPlain(text) {
        if (!text) return "";
        text = text.replace(/```(?:\w+)?\n?[\s\S]*?\n?```/g, '');
        text = text.replace(/`([^`]+)`/g, "'$1'");
        text = text.replace(/\*\*(.+?)\*\*/g, '«$1»');
        text = text.replace(/__(.+?)__/g, '«$1»');
        text = text.replace(/(?<!\w)\*(.+?)\*(?!\w)/g, '_$1_');
        text = text.replace(/(?<!\w)_(.+?)_(?!\w)/g, '_$1_');
        text = text.replace(/^#{1,6}\s+(.+)$/gm, function(m, t) { return t.toUpperCase(); });
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '$1 ($2)');
        text = text.replace(/^\d+\.\s+/gm, '- ');
        return text.trim();
    }
    
    function createFab() {
        if (document.getElementById("ai_assistant_fab")) return;
        
        var fab = document.createElement("div");
        fab.id = "ai_assistant_fab";
        fab.innerHTML = "🤖";
        fab.style.cssText = "position:fixed;bottom:24px;right:24px;width:60px;height:60px;border-radius:50%;background:linear-gradient(135deg,#7c3aed,#6d28d9);color:white;display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 20px rgba(124,58,237,0.4);z-index:99999;font-size:28px;border:none;";
        
        document.body.appendChild(fab);
        
        fab.addEventListener("click", function(e) {
            e.preventDefault();
            toggleWindow();
        });
    }
    
    function createWindow() {
        if (document.getElementById("ai_assistant_window")) return;
        
        var w = document.createElement("div");
        w.id = "ai_assistant_window";
        w.innerHTML = 
            '<div class="aihdr" style="background:linear-gradient(135deg,#7c3aed,#6d28d9);color:white;padding:16px;display:flex;align-items:center;justify-content:space-between;">' +
                '<div style="display:flex;align-items:center;gap:12px;">' +
                    '<div style="font-size:24px;">🤖</div>' +
                    '<div><div style="font-weight:600;">Asistente de IA</div><div style="font-size:12px;opacity:0.8;">En línea</div></div>' +
                '</div>' +
                '<button class="aiclose" style="background:rgba(255,255,255,0.2);border:none;color:white;width:36px;height:36px;border-radius:8px;cursor:pointer;font-size:18px;">×</button>' +
            '</div>' +
            '<div class="aimsgs" style="flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;"></div>' +
            '<div class="aiinputc" style="padding:12px;border-top:1px solid #e2e8f0;display:flex;gap:8px;align-items:center;">' +
                '<textarea class="aiinp" placeholder="Escribe un mensaje..." rows="1" style="flex:1;padding:12px;border:1px solid #e2e8f0;border-radius:8px;resize:none;font-family:inherit;font-size:14px;"></textarea>' +
                '<button class="aisend" style="background:#7c3aed;color:white;border:none;width:48px;height:42px;border-radius:8px;cursor:pointer;font-size:18px;flex-shrink:0;">➤</button>' +
            '</div>';
        
        w.style.cssText = "position:fixed;bottom:24px;right:24px;width:420px;height:640px;max-height:calc(100vh - 48px);background:white;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,0.15);display:none;flex-direction:column;z-index:100000;overflow:hidden;";
        
        document.body.appendChild(w);
        
        w.querySelector(".aiclose").onclick = function() { w.style.display = "none"; isOpen = false; };
        w.querySelector(".aisend").onclick = sendMessage;
        w.querySelector(".aiinp").onkeydown = function(e) {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
        };
    }
    
    function toggleWindow() {
        var w = document.getElementById("ai_assistant_window");
        if (!w) createWindow();
        w = document.getElementById("ai_assistant_window");
        
        if (w.style.display === "none" || !w.style.display) {
            w.style.display = "flex";
            isOpen = true;
            w.querySelector(".aiinp").focus();
        } else {
            w.style.display = "none";
            isOpen = false;
        }
    }
    
    function addMessage(role, content) {
        var w = document.getElementById("ai_assistant_window");
        if (!w) return;
        
        var m = w.querySelector(".aimsgs");
        var d = document.createElement("div");
        d.style.cssText = "display:flex;gap:10px;max-width:100%;" + (role === "user" ? "flex-direction:row-reverse;" : "");
        
        var icon = role === "user" ? "👤" : "🤖";
        var bg = role === "user" ? "#7c3aed" : "#f8fafc";
        var color = role === "user" ? "white" : "#1e293b";
        
        d.innerHTML = '<div style="width:32px;height:32px;border-radius:8px;background:' + bg + ';color:' + color + ';display:flex;align-items:center;justify-content:center;flex-shrink:0;">' + icon + '</div>' +
                     '<div style="padding:12px 16px;border-radius:14px;background:' + bg + ';color:' + color + ';font-size:14px;line-height:1.6;">' + content + '</div>';
        m.appendChild(d);
        m.scrollTop = m.scrollHeight;
    }
    
    function getPageContext() {
        var ctx = {
            title: document.title || "",
            url: window.location.pathname + window.location.search,
            action_id: "",
            model: "",
            res_id: null
        };
        
        // Intentar extraer action_id de la URL
        var match = window.location.href.match(/action=(\d+)/);
        if (match) ctx.action_id = match[1];
        
        // Intentar extraer model y res_id de la URL
        match = window.location.href.match(/model=([\w.]+)/);
        if (match) ctx.model = match[1];
        
        match = window.location.href.match(/id=(\d+)/);
        if (match) ctx.res_id = match[1];
        
        // Intentar obtener del breadcrumb de Odoo
        var breadcrumb = document.querySelector(".o_breadcrumb");
        if (breadcrumb) ctx.breadcrumb = breadcrumb.textContent.trim();
        
        // Intentar obtener el nombre del menú activo
        var activeMenu = document.querySelector(".o_menu_section .active");
        if (activeMenu) ctx.menu = activeMenu.textContent.trim();
        
        return ctx;
    }
    
    function sendMessage() {
        var w = document.getElementById("ai_assistant_window");
        var inp = w.querySelector(".aiinp");
        var msg = inp.value.trim();
        if (!msg) return;
        
        inp.value = "";
        addMessage("user", msg);
        
        w.querySelector(".aisend").disabled = true;
        inp.disabled = true;
        
        var pageCtx = getPageContext();
        var enhancedMsg = msg;
        
        // Agregar contexto de página si es relevante
        var pageInfo = "";
        if (pageCtx.menu) pageInfo += "Menú: " + pageCtx.menu + ". ";
        if (pageCtx.breadcrumb) pageInfo += "Ruta: " + pageCtx.breadcrumb + ". ";
        if (pageCtx.model) pageInfo += "Modelo: " + pageCtx.model + ". ";
        if (pageCtx.res_id) pageInfo += "Registro ID: " + pageCtx.res_id + ". ";
        
        if (pageInfo) {
            enhancedMsg = msg + " [Contexto: " + pageInfo.trim() + "]";
        }
        
        fetch("/ai_assistant/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                message: enhancedMsg,
                conversation_id: conversationId,
                context_info: pageCtx
            })
        }).then(function(r) { return r.json(); })
        .then(function(data) {
            w.querySelector(".aisend").disabled = false;
            inp.disabled = false;
            conversationId = data.conversation_id;
            addMessage("assistant", markdownToPlain(data.response));
        })
        .catch(function(err) {
            w.querySelector(".aisend").disabled = false;
            inp.disabled = false;
            addMessage("system", "Error: " + err.message);
        });
    }

    // Init
    if (document.body) {
        createFab();
    } else {
        document.addEventListener("DOMContentLoaded", function() {
            createFab();
        });
    }
    setTimeout(function() {
        if (!document.getElementById("ai_assistant_fab")) {
            createFab();
        }
    }, 3000);
    
})();
