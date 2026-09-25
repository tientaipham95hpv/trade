/**
 * Obsidian Quants - Activity & Audit View Renderer
 * Chronological execution receipts, audit logs, strict credential sanitization.
 */

import { Formatters } from './formatters.js';

export function renderActivity(state, container) {
    if (!container) return;

    const history = state.history || [];
    const logs = state.logs || [];

    container.innerHTML = `
        <div class="terminal-panel">
            <div class="panel-header">
                <div>
                    <span class="panel-title">AUDIT TRAIL & EXECUTION ACTIVITY</span>
                    <span class="panel-subtitle">Authoritative chronological execution events</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="panel-badge font-mono">${history.length + logs.length} EVENTS</span>
                </div>
            </div>
            <div class="panel-body p-0">
                ${renderActivityTable(history, logs)}
            </div>
        </div>
    `;
}

function renderActivityTable(history, logs) {
    // Combine history and logs into normalized events
    const events = [];

    history.forEach(item => {
        events.push({
            time: item.created_at || item.timestamp || item.time,
            component: 'ORDER_LIFECYCLE',
            severity: item.status === 'FILLED' ? 'INFO' : (item.status === 'REJECTED' ? 'WARN' : 'INFO'),
            symbol: item.symbol || '—',
            action: `${item.side || 'ORDER'} ${item.order_type || ''}`,
            result: item.status || 'PROCESSED',
            details: `qty=${item.quantity || item.qty || '—'}, price=${item.price || item.entry_price || '—'}`
        });
    });

    logs.forEach(logItem => {
        const text = typeof logItem === 'string' ? logItem : (logItem.message || logItem.text || JSON.stringify(logItem));
        const cleanText = Formatters.sanitize(text);
        events.push({
            time: logItem.timestamp || logItem.time || new Date().toISOString(),
            component: logItem.component || 'SYSTEM_LOG',
            severity: logItem.level || (text.includes('ERROR') ? 'ERROR' : (text.includes('WARN') ? 'WARN' : 'INFO')),
            symbol: logItem.symbol || 'SYSTEM',
            action: 'DISPATCH',
            result: cleanText.length > 80 ? cleanText.substring(0, 80) + '...' : cleanText,
            details: cleanText
        });
    });

    if (events.length === 0) {
        return `
            <div class="empty-state py-12">
                <div class="empty-state-title">Chưa có bản ghi hoạt động nào</div>
                <div class="empty-state-desc">Các sự kiện thực thi và cảnh báo hệ thống sẽ được ghi nhận tại đây theo thời gian thực.</div>
            </div>
        `;
    }

    // Sort descending by time
    events.sort((a, b) => {
        const ta = new Date(a.time).getTime() || 0;
        const tb = new Date(b.time).getTime() || 0;
        return tb - ta;
    });

    return `
        <div class="dense-table-container">
            <table class="dense-table">
                <thead>
                    <tr>
                        <th>TIME (UTC)</th>
                        <th>COMPONENT</th>
                        <th>SEVERITY</th>
                        <th>SYMBOL</th>
                        <th>ACTION</th>
                        <th>RESULT / DETAILS</th>
                    </tr>
                </thead>
                <tbody>
                    ${events.slice(0, 50).map(ev => {
                        const sevClass = ev.severity === 'ERROR' ? 'text-loss font-bold' : (ev.severity === 'WARN' ? 'text-gold' : 'text-primary');
                        return `
                            <tr>
                                <td class="font-mono text-muted text-xs whitespace-nowrap">${Formatters.timestamp(ev.time)}</td>
                                <td class="font-mono text-xs"><span class="badge-subtle">${Formatters.escapeHtml(ev.component)}</span></td>
                                <td class="font-mono text-xs ${sevClass}">${Formatters.escapeHtml(ev.severity)}</td>
                                <td class="font-mono text-xs font-bold text-cyan">${Formatters.escapeHtml(ev.symbol)}</td>
                                <td class="font-mono text-xs">${Formatters.escapeHtml(ev.action)}</td>
                                <td class="font-mono text-xs text-secondary" title="${Formatters.escapeHtml(ev.details)}">
                                    ${Formatters.escapeHtml(ev.result)}
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}
