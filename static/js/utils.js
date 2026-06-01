'use strict';

function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function pasteToField(fieldId) {
    navigator.clipboard.readText().then(text => {
        const el = document.getElementById(fieldId);
        if (el) { el.value = text; el.dispatchEvent(new Event('input', {bubbles:true})); }
    }).catch(() => {});
}

function debounce(fn, ms) {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}
