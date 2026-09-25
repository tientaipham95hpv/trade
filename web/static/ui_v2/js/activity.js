/**
 * Obsidian Quants V3 — Activity & Audit View Renderer
 * Professional Trading Terminal Audit Console
 * Filter Strip: ALL | INFO | WARNING | ERROR | OPERATOR | EXECUTION
 * Table: TIME | SOURCE | EVENT | DETAIL | STATE
 */

import { Formatters } from './formatters.js';

let activeFilter = 'ALL';

export function renderActivity(state, container) {
    if (!container) return;

    const history = state.history || [];
    const logs = state.logs || [];

    // Combine history and logs into normalized events
    const allEvents = [];

    history.forEach(item => {
        allEvents.push({
            time: item.created_at || item.timestamp || item.time || new Date().toISOString(),
            source: 'EXECUTION',
            severity: item.status === 'FILLED' ? 'INFO' : (item.status === 'REJECTED' ? 'WARNING' : 'INFO'),
            event: `${item.side || 'ORDER'} ${item.order_type || ''}`.trim(),
            detail: `symbol=${item.symbol || '—'}, qty=${item.quantity || item.qty || '—'}, price=${item.price || item.entry_price || '—'}`,
            state: item.status || 'PROCESSED'
        });
    });

    logs.forEach(logItem => {
        const text = typeof logItem === 'string' ? logItem : (logItem.message || logItem.text || JSON.stringify(logItem));
        const cleanText = Formatters.sanitize(text);
        let sev = 'INFO';
        if (text.includes('ERROR') || text.includes('CRITICAL')) sev = 'ERROR';
        else if (text.includes('WARN')) sev = 'WARNING';

        let src = 'SYSTEM';
        if (text.includes('OPERATOR') || text.includes('web') || text.includes('pause') || text.includes('resume')) {
            src = 'OPERATOR';
        } else if (text.includes('core') || text.includes('order') || text.includes('engine')) {
            src = 'EXECUTION';
        }

        allEvents.push({
            time: logItem.timestamp || logItem.time || new Date().toISOString(),
            source: src,
            severity: sev,
            event: 'LOG_DISPATCH',
            detail: cleanText,
            state: sev === 'ERROR' ? 'FAIL' : 'OK'
        });
    });

    // Sort descending by time
    allEvents.sort((a, b) => {
        const ta = new Date(a.time).getTime() || 0;
        const tb = new Date(b.time).getTime() || 0;
        return tb - ta;
    });

    // Filter events
    const filteredEvents = allEvents.filter(ev => {
        if (activeFilter === 'ALL') return true;
        if (activeFilter === 'INFO') return ev.severity === 'INFO';
        if (activeFilter === 'WARNING') return ev.severity === 'WARNING';
        if (activeFilter === 'ERROR') return ev.severity === 'ERROR';
        if (activeFilter === 'OPERATOR') return ev.source === 'OPERATOR';
        if (activeFilter === 'EXECUTION') return ev.source === 'EXECUTION';
        return true;
    });

    container.innerHTML = `
        <div class="terminal-panel">
            <div class="panel-header">
                <div>
                    <span class="panel-title">AUDIT CONSOLE</span>
                    <span class="panel-subtitle">Authoritative chronological execution log</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="badge-subtle font-mono">${filteredEvents.length} / ${allEvents.length} EVENTS</span>
                </div>
            </div>

            <!-- Filter Strip -->
            <div class="activity-filter-strip">
                ${['ALL', 'INFO', 'WARNING', 'ERROR', 'OPERATOR', 'EXECUTION'].map(f => `
                    <button class="filter-btn ${activeFilter === f ? 'active' : ''}" data-filter="${f}">
                        ${f}
                    </button>
                `).join('')}
            </div>

            <div class="panel-body p-0">
                ${renderEventsTable(filteredEvents)}
            </div>
        </div>
    `;

    // Filter Click Handlers
    const filterBtns = container.querySelectorAll('.filter-btn');
    filterBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            activeFilter = btn.getAttribute('data-filter') || 'ALL';
            renderActivity(state, container);
        });
    });
}

function renderEventsTable(events) {
    if (!events || events.length === 0) {
        return `
            <div class="empty-state py-12">
                <div class="empty-state-symbol">—</div>
                <div class="empty-state-title">No audit records found</div>
                <div class="empty-state-desc">Authoritative execution receipts and operator events will stream here</div>
            </div>
        `;
    }

    return `
        <div class="dense-table-container">
            <table class="dense-table">
                <thead>
                    <tr>
                        <th>TIME</th>
                        <th>SOURCE</th>
                        <th>EVENT</th>
                        <th>DETAIL</th>
                        <th>STATE</th>
                    </tr>
                </thead>
                <tbody>
                    ${events.slice(0, 60).map(ev => {
                        const sevClass = ev.severity === 'ERROR' ? 'text-critical font-bold' : (ev.severity === 'WARNING' ? 'text-warning' : 'text-primary');
                        return `
                            <tr>
                                <td class="font-mono text-muted text-xs whitespace-nowrap">${Formatters.timestamp(ev.time)}</td>
                                <td class="font-mono text-xs"><span class="badge-subtle">${Formatters.escapeHtml(ev.source)}</span></td>
                                <td class="font-mono text-xs font-bold ${sevClass}">${Formatters.escapeHtml(ev.event)}</td>
                                <td class="font-mono text-xs text-secondary max-w-md truncate" title="${Formatters.escapeHtml(ev.detail)}">
                                    ${Formatters.escapeHtml(ev.detail)}
                                </td>
                                <td>
                                    <span class="status-badge ${ev.state === 'FAIL' || ev.state === 'REJECTED' ? 'status-badge--halt' : 'status-badge--healthy'}">
                                        ${Formatters.escapeHtml(ev.state)}
                                    </span>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}
