'use strict';

const SearchableSelect = (() => {
    function enhance(selector) {
        const el = typeof selector === 'string' ? document.querySelector(selector) : selector;
        if (!el || el.dataset.ssEnhanced) return;
        el.dataset.ssEnhanced = '1';
        el.style.display = 'none';

        const wrap = document.createElement('div');
        wrap.className = 'ss-wrap';
        wrap.style.cssText = 'position:relative;display:inline-block;width:100%;';
        el.parentNode.insertBefore(wrap, el);
        wrap.appendChild(el);

        const trigger = document.createElement('button');
        trigger.type = 'button';
        trigger.className = 'ss-trigger';
        trigger.style.cssText = 'width:100%;text-align:left;padding:.5rem .75rem;font-size:.8125rem;font-weight:300;border:1px solid var(--color-border);border-radius:2px;background:#fff;cursor:pointer;display:flex;align-items:center;justify-content:space-between;';
        trigger.innerHTML = `<span class="ss-label">${escapeHtml(el.options[el.selectedIndex]?.text || '')}</span><span class="material-icons ss-chevron" style="font-size:16px;color:#94a3b8;transition:transform .2s;">expand_more</span>`;

        const panel = document.createElement('div');
        panel.className = 'ss-panel';
        panel.style.cssText = 'display:none;position:absolute;z-index:200;width:100%;background:#fff;border:1px solid var(--color-border);border-radius:2px;box-shadow:0 4px 16px rgba(0,0,0,.1);top:calc(100% + 2px);';

        const search = document.createElement('input');
        search.type = 'text';
        search.className = 'ss-search';
        search.placeholder = 'Szukaj...';
        search.style.cssText = 'width:100%;padding:.4rem .625rem;font-size:.8125rem;font-weight:300;border:none;border-bottom:1px solid var(--color-border);outline:none;';

        const list = document.createElement('div');
        list.className = 'ss-list';
        list.style.cssText = 'max-height:200px;overflow-y:auto;';
        list.style.cssText += 'scrollbar-width:thin;';

        panel.appendChild(search);
        panel.appendChild(list);
        wrap.appendChild(trigger);
        wrap.appendChild(panel);

        function buildList(filter = '') {
            list.innerHTML = '';
            const fLow = filter.toLowerCase();
            let any = false;
            Array.from(el.options).forEach(opt => {
                if (fLow && !opt.text.toLowerCase().includes(fLow)) return;
                any = true;
                const item = document.createElement('div');
                item.className = 'ss-item' + (opt.selected ? ' ss-item--selected' : '');
                item.style.cssText = 'padding:.4rem .625rem;font-size:.8125rem;font-weight:300;cursor:pointer;transition:background .1s;';
                item.textContent = opt.text;
                item.dataset.value = opt.value;
                item.addEventListener('mouseenter', () => item.style.background='rgba(201,162,39,.25)');
                item.addEventListener('mouseleave', () => item.style.background='');
                item.addEventListener('click', () => {
                    el.value = opt.value;
                    el.dispatchEvent(new Event('change', {bubbles:true}));
                    trigger.querySelector('.ss-label').textContent = opt.text;
                    closePanel();
                });
                list.appendChild(item);
            });
            if (!any) {
                const ni = document.createElement('div');
                ni.className = 'ss-no-results';
                ni.style.cssText = 'padding:.5rem .625rem;font-size:.8125rem;color:#94a3b8;text-align:center;';
                ni.textContent = 'Brak wyników';
                list.appendChild(ni);
            }
        }

        function openPanel() {
            panel.style.display = 'block';
            trigger.querySelector('.ss-chevron').style.transform = 'rotate(180deg)';
            buildList();
            search.value = '';
            search.focus();
        }
        function closePanel() {
            panel.style.display = 'none';
            trigger.querySelector('.ss-chevron').style.transform = '';
        }

        trigger.addEventListener('click', e => { e.stopPropagation(); panel.style.display === 'none' ? openPanel() : closePanel(); });
        search.addEventListener('input', () => buildList(search.value));
        document.addEventListener('click', e => { if (!wrap.contains(e.target)) closePanel(); });
    }

    function sync(selector) {
        const el = typeof selector === 'string' ? document.querySelector(selector) : selector;
        if (!el) return;
        const label = el.parentNode?.querySelector('.ss-label');
        if (label) label.textContent = el.options[el.selectedIndex]?.text || '';
    }

    function setValue(selector, val) {
        const el = typeof selector === 'string' ? document.querySelector(selector) : selector;
        if (!el) return;
        el.value = val;
        sync(el);
    }

    return { enhance, sync, setValue };
})();
