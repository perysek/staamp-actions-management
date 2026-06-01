'use strict';

const Modals = (() => {
    const btnCls = {
        primary:   'px-4 py-2 text-sm font-medium text-white rounded-xl bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 transition-all btn-press',
        secondary: 'px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors btn-press',
        danger:    'px-4 py-2 text-sm font-medium text-white rounded-xl transition-all btn-press',
        success:   'px-4 py-2 text-sm font-medium text-white rounded-xl bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 transition-all btn-press',
    };
    const dangerStyle = 'background:linear-gradient(135deg,#ef4444 0%,#dc2626 100%);box-shadow:0 1px 3px rgba(220,38,38,.3);border-radius:.625rem;';

    function show({ title='', content='', size='medium', buttons=[], onClose, closeOnOverlay=true }) {
        const overlay = document.createElement('div');
        overlay.className = 'modal-overlay animate-fade-in';
        overlay.setAttribute('role', 'dialog');
        overlay.setAttribute('aria-modal', 'true');
        overlay.setAttribute('aria-labelledby', 'modal-title-' + Date.now());

        const widths = { small:'max-width:360px', medium:'max-width:480px', large:'max-width:640px' };
        const btnsHtml = buttons.map((b, i) => {
            const cls = btnCls[b.type] || btnCls.secondary;
            const style = b.type === 'danger' ? dangerStyle : '';
            return `<button class="${cls}" style="${style}" data-btn="${i}">${escapeHtml(b.text)}</button>`;
        }).join('');

        overlay.innerHTML = `
            <div class="modal-content animate-scale-in" style="${widths[size]||widths.medium}">
                <div class="modal-header">
                    <h3 class="modal-title">${escapeHtml(title)}</h3>
                    <button class="inline-flex items-center justify-center w-8 h-8 rounded-lg hover:bg-slate-100 transition-colors modal-close-btn" aria-label="Zamknij">
                        <span class="material-icons" style="font-size:18px;color:#64748b;">close</span>
                    </button>
                </div>
                <div class="modal-body">${content}</div>
                ${btnsHtml ? `<div class="modal-footer">${btnsHtml}</div>` : ''}
            </div>
        `;

        document.body.appendChild(overlay);

        const closeModal = () => { overlay.remove(); onClose?.(); };
        overlay.querySelector('.modal-close-btn')?.addEventListener('click', closeModal);
        if (closeOnOverlay) overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });
        document.addEventListener('keydown', function esc(e) { if (e.key === 'Escape') { closeModal(); document.removeEventListener('keydown', esc); } });

        buttons.forEach((b, i) => {
            overlay.querySelector(`[data-btn="${i}"]`)?.addEventListener('click', e => b.onClick?.(e, overlay));
        });

        const firstFocusable = overlay.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
        firstFocusable?.focus();
        return overlay;
    }

    function confirm({ title='Potwierdź', message='', confirmText='OK', cancelText='Anuluj', type='info', onConfirm, onCancel }) {
        const icons = { danger:'🔴', warning:'🟡', info:'🔵' };
        return show({
            title,
            content: `<div class="flex gap-3"><span style="font-size:1.5rem;">${icons[type]||icons.info}</span><p>${escapeHtml(message)}</p></div>`,
            buttons: [
                { text: cancelText,  type: 'secondary', onClick: (e, o) => { o.remove(); onCancel?.(); } },
                { text: confirmText, type: type === 'danger' ? 'danger' : 'primary',
                  onClick: (e, o) => { o.remove(); onConfirm?.(); } },
            ],
        });
    }

    function alert({ title='', message='', type='info' }) {
        return show({ title, content: `<p>${escapeHtml(message)}</p>`, buttons: [{ text:'OK', type:'primary', onClick:(e,o)=>o.remove() }] });
    }

    function loading(msg = 'Przetwarzanie...') {
        return show({
            title: msg,
            content: '<div style="text-align:center;padding:1rem;"><div style="width:32px;height:32px;border:3px solid #e2e8f0;border-top-color:#3b82f6;border-radius:50%;animation:spin 1s linear infinite;margin:0 auto;"></div></div>',
            closeOnOverlay: false,
        });
    }

    function closeAll() { document.querySelectorAll('.modal-overlay').forEach(m => m.remove()); }
    function close(overlay) { overlay?.remove(); }

    return { show, confirm, alert, loading, closeAll, close };
})();
