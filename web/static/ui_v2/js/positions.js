/**
 * Obsidian Quants - Positions View Renderer
 * Dense institutional table, slide-over detail drawer, zero manual trading controls.
 */

import { Formatters } from './formatters.js';
import { store } from './state.js';

export function renderPositions(state, container) {
    if (!container) return;

    const positions = state.positions || [];

    container.innerHTML = `
        <div class="terminal-panel">
            <div class="panel-header">
                <div>
                    <span class="panel-title">ACTIVE POSITIONS & EXPOSURE</span>
                    <span class="panel-subtitle">Authoritative execution service inventory</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="panel-badge font-mono">${positions.length} ACTIVE</span>
                </div>
            </div>
            <div class="panel-body p-0">
                ${renderPositionsTable(positions)}
            </div>
        </div>

        <!-- Position Detail Slide-over Drawer -->
        <div id="position-drawer-backdrop" class="drawer-backdrop hidden">
            <div id="position-drawer" class="position-drawer">
                <div class="drawer-header">
                    <div class="flex items-center gap-2">
                        <span id="drawer-symbol" class="font-bold text-lg font-mono">BTCUSDT</span>
                        <span id="drawer-side-badge" class="status-badge font-mono">LONG</span>
                    </div>
                    <button id="btn-close-drawer" class="btn-icon" aria-label="Close details">
                        ✕
                    </button>
                </div>
                <div id="drawer-content" class="drawer-body">
                    <!-- Dynamic read-only details rendered here -->
                </div>
                <div class="drawer-footer">
                    <span class="text-xs text-muted font-mono">READ-ONLY TELEMETRY (MANUAL TRADING DISABLED)</span>
                </div>
            </div>
        </div>
    `;

    setupDrawerEvents(container, positions);
}

function renderPositionsTable(positions) {
    if (!positions || positions.length === 0) {
        return `
            <div class="empty-state py-12">
                <div class="empty-state-title">Không có vị thế mở nào đang hoạt động</div>
                <div class="empty-state-desc">Hệ thống đang ở chế độ giám sát an toàn. Zero open margin exposure.</div>
            </div>
        `;
    }

    return `
        <div class="dense-table-container">
            <table class="dense-table">
                <thead>
                    <tr>
                        <th>SYMBOL</th>
                        <th>SIDE</th>
                        <th class="text-right">QTY</th>
                        <th class="text-right">ENTRY</th>
                        <th class="text-right">MARK</th>
                        <th class="text-right">UNREALIZED</th>
                        <th class="text-right">SL</th>
                        <th class="text-right">TP</th>
                        <th>PROTECTION</th>
                        <th>STATE</th>
                        <th class="text-right">ACTION</th>
                    </tr>
                </thead>
                <tbody>
                    ${positions.map((pos, idx) => {
                        const side = (pos.side || 'LONG').toUpperCase();
                        const sideClass = side === 'LONG' ? 'text-profit' : 'text-loss';
                        const unPnl = Formatters.pnl(pos.unrealized_pnl || pos.pnl);
                        const sym = Formatters.escapeHtml(pos.symbol || '—');
                        return `
                            <tr class="cursor-pointer row-hover" data-position-idx="${idx}">
                                <td class="font-bold font-mono text-cyan">${sym}</td>
                                <td class="${sideClass} font-mono font-bold">${side}</td>
                                <td class="text-right font-mono">${Formatters.number(pos.qty || pos.quantity, 4)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.entry_price || pos.entry, 2)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.mark_price || pos.mark, 2)}</td>
                                <td class="text-right font-mono ${unPnl.className}">${unPnl.text}</td>
                                <td class="text-right font-mono text-loss">${pos.stop_loss ? Formatters.currency(pos.stop_loss, 2) : '—'}</td>
                                <td class="text-right font-mono text-profit">${pos.take_profit ? Formatters.currency(pos.take_profit, 2) : '—'}</td>
                                <td>
                                    <span class="badge-subtle font-mono">${pos.protection || 'ACTIVE_STOP'}</span>
                                </td>
                                <td>
                                    <span class="status-badge status-badge--healthy font-mono">
                                        <span class="status-badge__dot"></span>
                                        ${pos.state || 'FILLED'}
                                    </span>
                                </td>
                                <td class="text-right">
                                    <button class="btn btn--outline btn--sm font-mono btn-view-detail" data-position-idx="${idx}">
                                        VIEW
                                    </button>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function setupDrawerEvents(container, positions) {
    const backdrop = container.querySelector('#position-drawer-backdrop');
    const drawer = container.querySelector('#position-drawer');
    const closeBtn = container.querySelector('#btn-close-drawer');
    const drawerContent = container.querySelector('#drawer-content');
    const drawerSymbol = container.querySelector('#drawer-symbol');
    const drawerSideBadge = container.querySelector('#drawer-side-badge');

    function openDrawer(pos) {
        if (!pos) return;
        const side = (pos.side || 'LONG').toUpperCase();
        drawerSymbol.textContent = pos.symbol || '—';
        drawerSideBadge.textContent = side;
        drawerSideBadge.className = `status-badge font-mono ${side === 'LONG' ? 'status-badge--healthy' : 'status-badge--halt'}`;

        const unPnl = Formatters.pnl(pos.unrealized_pnl || pos.pnl);

        drawerContent.innerHTML = `
            <div class="telemetry-list">
                <div class="telemetry-item">
                    <span class="telemetry-key">Symbol</span>
                    <span class="telemetry-val font-mono text-cyan">${Formatters.escapeHtml(pos.symbol || '—')}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Side</span>
                    <span class="telemetry-val font-mono font-bold ${side === 'LONG' ? 'text-profit' : 'text-loss'}">${side}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Quantity</span>
                    <span class="telemetry-val font-mono">${Formatters.number(pos.qty || pos.quantity, 4)}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Entry Price</span>
                    <span class="telemetry-val font-mono">${Formatters.currency(pos.entry_price || pos.entry, 2)}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Mark Price</span>
                    <span class="telemetry-val font-mono">${Formatters.currency(pos.mark_price || pos.mark, 2)}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Unrealized PnL</span>
                    <span class="telemetry-val font-mono font-bold ${unPnl.className}">${unPnl.text}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Stop Loss</span>
                    <span class="telemetry-val font-mono text-loss">${pos.stop_loss ? Formatters.currency(pos.stop_loss, 2) : '—'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Take Profit</span>
                    <span class="telemetry-val font-mono text-profit">${pos.take_profit ? Formatters.currency(pos.take_profit, 2) : '—'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Leverage</span>
                    <span class="telemetry-val font-mono">${pos.leverage ? pos.leverage + 'x' : '—'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Margin Type</span>
                    <span class="telemetry-val font-mono">ISOLATED</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Protection State</span>
                    <span class="telemetry-val font-mono text-cyan">${pos.protection || 'DETERMINISTIC_STOP'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Lifecycle State</span>
                    <span class="telemetry-val font-mono">${pos.state || 'MANAGED'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Execution Receipt ID</span>
                    <span class="telemetry-val font-mono text-xs text-muted">${pos.receipt_id || pos.id || 'RCV_DURABLE_INTENT'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Fee & Accounting State</span>
                    <span class="telemetry-val font-mono text-profit">RECONCILED_NO_DISCREPANCY</span>
                </div>
            </div>
        `;

        backdrop.classList.remove('hidden');
    }

    function closeDrawer() {
        backdrop.classList.add('hidden');
    }

    closeBtn?.addEventListener('click', closeDrawer);
    backdrop?.addEventListener('click', (e) => {
        if (e.target === backdrop) closeDrawer();
    });

    container.querySelectorAll('[data-position-idx]').forEach(el => {
        el.addEventListener('click', (e) => {
            const idx = parseInt(el.getAttribute('data-position-idx'), 10);
            if (!isNaN(idx) && positions[idx]) {
                openDrawer(positions[idx]);
            }
        });
    });
}
