'use strict';

document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.key === '/') {
        e.preventDefault();
        const dmcInput = document.getElementById('dmc-input');
        if (dmcInput) { dmcInput.focus(); dmcInput.select(); }
    }
    if (e.ctrlKey && e.shiftKey && e.key === 'R') {
        e.preventDefault();
        if (typeof resetScanner === 'function') resetScanner();
    }
});
