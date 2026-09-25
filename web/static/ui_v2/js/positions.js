/**
 * Obsidian Quants V3 — Positions View Renderer
 * Professional High-Density Trading Terminal Table & Slide-Over Drawer
 * Columns: SYMBOL | SIDE | QTY | ENTRY | MARK | PNL | SL | TP | PROTECTION | STATE
 * Zero mutation controls. Read-only inspection drawer.
 */

import { Formatters } from './formatters.js';

export function renderPositions(state, container) {
    if (!container) return;

    const positions = state.positions || [];

    container.innerHTML = `
        <div class="terminal-panel">
            <div class="panel-header">
                <div>
                    <span class="panel-title">ACTIVE POSITIONS</span>
                    <span class="panel-subtitle">Authoritative execution service inventory</span>
                </div>
                <div class="flex items-center gap-2">
                    <span class="badge-subtle font-mono">${positions.length} ACTIVE</span>
                </div>
            </div>
            <div class="panel-body p-0">
                ${renderPositionsTable(positions)}
            </div>
        </div>

        <!-- Position Detail Slide-Over Drawer (380-440px) -->
        <div id="position-drawer-backdrop" class="drawer-backdrop hidden">
            <div id="position-drawer" class="position-drawer">
                <div class="drawer-header">
                    <div class="flex items-center gap-2">
                        <span id="drawer-symbol" class="font-bold text-base font-mono text-cyan">BTCUSDT</span>
                        <span id="drawer-side-badge" class="side-badge">LONG</span>
                    </div>
                    <button id="btn-close-drawer" class="btn-icon" aria-label="Close details">
                        ✕
                    </button>
                </div>
                <div id="drawer-content" class="drawer-body">
                    <!-- Dynamic read-only details rendered here -->
                </div>
                <div class="drawer-footer">
                    <span class="text-xs text-muted font-mono">READ-ONLY TELEMETRY (MUTATION DISABLED)</span>
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
                <div class="empty-state-symbol">—</div>
                <div class="empty-state-title">No active positions</div>
                <div class="empty-state-desc">Execution remains in OFFLINE mode</div>
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
                        <th class="text-right">PNL</th>
                        <th class="text-right">SL</th>
                        <th class="text-right">TP</th>
                        <th>PROTECTION</th>
                        <th>STATE</th>
                    </tr>
                </thead>
                <tbody>
                    ${positions.map((pos, idx) => {
                        const side = (pos.side || 'LONG').toUpperCase();
                        const sideClass = side === 'LONG' ? 'side-badge--long' : 'side-badge--short';
                        const unPnl = Formatters.pnl(pos.unrealized_pnl || pos.pnl);
                        const sym = Formatters.escapeHtml(pos.symbol || '—');
                        return `
                            <tr class="cursor-pointer row-hover" data-position-idx="${idx}">
                                <td class="font-bold font-mono text-cyan">${sym}</td>
                                <td><span class="side-badge ${sideClass}">${side}</span></td>
                                <td class="text-right font-mono">${Formatters.number(pos.qty || pos.quantity, 4)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.entry_price || pos.entry, 2)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.mark_price || pos.mark, 2)}</td>
                                <td class="text-right font-mono ${unPnl.className}">${unPnl.text}</td>
                                <td class="text-right font-mono text-negative">${pos.stop_loss ? Formatters.currency(pos.stop_loss, 2) : '—'}</td>
                                <td class="text-right font-mono text-positive">${pos.take_profit ? Formatters.currency(pos.take_profit, 2) : '—'}</td>
                                <td>
                                    <span class="badge-subtle font-mono">${pos.protection || 'ACTIVE_STOP'}</span>
                                </td>
                                <td>
                                    <span class="status-badge status-badge--healthy">
                                        <span class="status-badge__dot"></span>
                                        ${pos.state || 'OPEN'}
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

function setupDrawerEvents(container, positions) {
    const backdrop = container.querySelector('#position-drawer-backdrop');
    const closeBtn = container.querySelector('#btn-close-drawer');
    const drawerSymbol = container.querySelector('#drawer-symbol');
    const drawerSideBadge = container.querySelector('#drawer-side-badge');
    const drawerContent = container.querySelector('#drawer-content');

    if (!backdrop || !closeBtn || !drawerContent) return;

    const closeDrawer = () => {
        backdrop.classList.add('hidden');
    };

    closeBtn.addEventListener('click', closeDrawer);
    backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) closeDrawer();
    });

    const rows = container.querySelectorAll('tr[data-position-idx]');
    rows.forEach(row => {
        row.addEventListener('click', () => {
            const idx = parseInt(row.getAttribute('data-position-idx'), 10);
            const pos = positions[idx];
            if (!pos) return;

            const side = (pos.side || 'LONG').toUpperCase();
            drawerSymbol.textContent = pos.symbol || '—';
            drawerSideBadge.textContent = side;
            drawerSideBadge.className = `side-badge ${side === 'LONG' ? 'side-badge--long' : 'side-badge--short'}`;

            const unPnl = Formatters.pnl(pos.unrealized_pnl || pos.pnl);

            drawerContent.innerHTML = `
                <!-- 1. Position Section -->
                <div class="drawer-section">
                    <div class="drawer-section-title">Position</div>
                    <div class="telemetry-list">
                        <div class="telemetry-item">
                            <span class="telemetry-key">Symbol</span>
                            <span class="telemetry-val font-mono text-cyan">${Formatters.escapeHtml(pos.symbol || '—')}</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Direction</span>
                            <span class="telemetry-val font-mono">${side}</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Quantity</span>
                            <span class="telemetry-val font-mono">${Formatters.number(pos.qty || pos.quantity, 4)}</span>
                        </div>
                    </div>
                </div>

                <!-- 2. Pricing Section -->
                <div class="drawer-section">
                    <div class="drawer-section-title">Pricing</div>
                    <div class="telemetry-list">
                        <div class="telemetry-item">
                            <span class="telemetry-key">Entry Price</span>
                            <span class="telemetry-val font-mono">${Formatters.currency(pos.entry_price || pos.entry, 2)}</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Mark Price</span>
                            <span class="telemetry-val font-mono">${Formatters.currency(pos.mark_price || pos.mark, 2)}</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Liquidation Est</span>
                            <span class="telemetry-val font-mono text-muted">${pos.liquidation_price ? Formatters.currency(pos.liquidation_price, 2) : '—'}</span>
                        </div>
                    </div>
                </div>

                <!-- 3. PnL Section -->
                <div class="drawer-section">
                    <div class="drawer-section-title">PnL</div>
                    <div class="telemetry-list">
                        <div class="telemetry-item">
                            <span class="telemetry-key">Unrealized PnL</span>
                            <span class="telemetry-val font-mono ${unPnl.className}">${unPnl.text}</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Realized PnL</span>
                            <span class="telemetry-val font-mono">${pos.realized_pnl ? Formatters.pnl(pos.realized_pnl).text : '—'}</span>
                        </div>
                    </div>
                </div>

                <!-- 4. Protection Section -->
                <div class="drawer-section">
                    <div class="drawer-section-title">Protection</div>
                    <div class="telemetry-list">
                        <div class="telemetry-item">
                            <span class="telemetry-key">Stop Loss</span>
                            <span class="telemetry-val font-mono text-negative">${pos.stop_loss ? Formatters.currency(pos.stop_loss, 2) : '—'}</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Take Profit</span>
                            <span class="telemetry-val font-mono text-positive">${pos.take_profit ? Formatters.currency(pos.take_profit, 2) : '—'}</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Protection Guard</span>
                            <span class="telemetry-val font-mono">${pos.protection || 'ACTIVE_STOP'}</span>
                        </div>
                    </div>
                </div>

                <!-- 5. Execution Metadata Section -->
                <div class="drawer-section">
                    <div class="drawer-section-title">Execution Metadata</div>
                    <div class="telemetry-list">
                        <div class="telemetry-item">
                            <span class="telemetry-key">Order ID</span>
                            <span class="telemetry-val font-mono text-xs">${Formatters.escapeHtml(pos.order_id || 'OFFLINE_MOCK')}</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Position ID</span>
                            <span class="telemetry-val font-mono text-xs">${Formatters.escapeHtml(pos.id || 'pos_' + idx)}</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Opened Time</span>
                            <span class="telemetry-val font-mono text-xs text-muted">${pos.created_at ? Formatters.timestamp(pos.created_at) : '—'}</span>
                        </div>
                    </div>
                </div>
            `;

            backdrop.classList.remove('hidden');
        });
    });
}
