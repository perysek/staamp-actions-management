'use strict';

const _sortState = {};

function sortTable(colIdx, tableId = 'resultsTable') {
    const table = document.getElementById(tableId);
    if (!table) return;
    const key = `${tableId}:${colIdx}`;
    _sortState[key] = !_sortState[key];
    const asc = _sortState[key];

    const rows = Array.from(table.tBodies[0].rows);
    rows.sort((a, b) => {
        const av = a.cells[colIdx]?.textContent.trim() || '';
        const bv = b.cells[colIdx]?.textContent.trim() || '';
        const an = parseFloat(av.replace(/[^\d.-]/g, ''));
        const bn = parseFloat(bv.replace(/[^\d.-]/g, ''));
        if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
        return asc ? av.localeCompare(bv, 'pl') : bv.localeCompare(av, 'pl');
    });
    rows.forEach(r => table.tBodies[0].appendChild(r));
}

function applyAllFilters(tableId = 'resultsTable') {
    const table = document.getElementById(tableId);
    if (!table) return;
    const inputs = Array.from(table.tHead.querySelectorAll('.column-search'));
    const filterVals = inputs.map(i => i.value.trim().toLowerCase());
    const isAllEmpty = filterVals.every(v => !v);

    Array.from(table.tBodies[0].rows).forEach(row => {
        if (row.classList.contains('detail-row') || row.id?.startsWith('detail-')) {
            row.classList.add('hidden'); return;
        }
        const visible = isAllEmpty || filterVals.every((val, ci) => {
            if (!val) return true;
            const cellText = (row.cells[ci]?.textContent || '').trim().toLowerCase();
            // SELECT filters use word-boundary match so 'ok' does not match inside 'nok'
            if (inputs[ci]?.tagName === 'SELECT') {
                return cellText.split(/\s+/).includes(val);
            }
            return cellText.includes(val);
        });
        row.style.display = visible ? '' : 'none';
    });
}

function clearFilters(tableId = 'resultsTable') {
    const table = document.getElementById(tableId);
    if (!table) return;
    table.tHead.querySelectorAll('.column-search').forEach(i => { i.value = ''; });
    applyAllFilters(tableId);
}

function exportToCSV(tableId = 'resultsTable', filename = 'export') {
    const table = document.getElementById(tableId);
    if (!table) return;
    const rows = [];
    const hRow = Array.from(table.tHead.rows[0].cells).map(c => `"${c.textContent.trim()}"`);
    rows.push(hRow.join(','));
    Array.from(table.tBodies[0].rows).forEach(row => {
        if (row.style.display === 'none') return;
        if (row.id?.startsWith('detail-')) return;
        const cols = Array.from(row.cells).map(c => `"${c.textContent.trim().replace(/"/g, '""')}"`);
        rows.push(cols.join(','));
    });
    const blob = new Blob(['﻿' + rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${filename}_${new Date().toISOString().slice(0,10)}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.sortable-table').forEach(t => {
        if (t.id) {
            t.querySelectorAll('.column-search').forEach(i => {
                i.addEventListener('input', () => applyAllFilters(t.id));
                i.addEventListener('change', () => applyAllFilters(t.id));
            });
        }
    });
});
