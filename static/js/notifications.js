'use strict';

const Notifications = (() => {
    const container = () => document.getElementById('toast-container');
    let count = 0;

    function show(message, type = 'info', duration = 5000) {
        const c = container();
        if (!c) return;
        if (c.children.length >= 3) c.firstElementChild?.remove();

        const id = 'toast-' + (++count);
        const icons = { success:'check_circle', error:'error', warning:'warning', info:'info' };
        const div = document.createElement('div');
        div.id = id;
        div.className = `toast toast-${type}`;
        div.setAttribute('role', 'status');
        div.innerHTML = `
            <span class="material-icons" style="font-size:18px;flex-shrink:0;">${icons[type]||'info'}</span>
            <span style="flex:1;line-height:1.4;">${escapeHtml(message)}</span>
            <button class="toast-close" onclick="document.getElementById('${id}').remove()" aria-label="Zamknij">×</button>
        `;
        c.appendChild(div);
        if (duration > 0) setTimeout(() => div.remove(), duration);
    }

    return {
        show,
        success: (msg, dur)  => show(msg, 'success', dur),
        error:   (msg, dur)  => show(msg, 'error',   dur),
        warning: (msg, dur)  => show(msg, 'warning',  dur),
        info:    (msg, dur)  => show(msg, 'info',     dur),
        clear:   ()          => { const c=container(); if(c) c.innerHTML=''; },
    };
})();
