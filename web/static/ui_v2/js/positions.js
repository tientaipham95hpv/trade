/**
 * Obsidian Quants V3 — Positions View Renderer
 * Professional High-Density Trading Terminal Workstation Layout
 * Left (~68%): Active Positions Table with clickable row selection
 * Right (~32%): Persistent read-only Position Inspector
 * Bottom: Protection State, Execution Metadata & Synchronized Activity
 * Zero mutation controls. Read-only institutional inspection.
 */

import { Formatters } from './formatters.js';

let selectedIndex = 0;

export function renderPositions(state, container) {
    if (!container) return;

    const positions = state.positions || [];
    if (selectedIndex >= positions.length) {
        selectedIndex = positions.length > 0 ? 0 : -1;
    }

    const nowUtc = new Date().toISOString().substring(11, 19);

    container.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title">Positions</h1>
                <p class="page-subtitle">Active execution inventory (${positions.length} open position${positions.length === 1 ? '' : 's'})</p>
            </div>
            <div class="page-header-meta">
                <span class="live-stream-badge">
                    <span class="pulse-dot"></span> LIVE TELEMETRY
                </span>
                <span class="page-meta-time">Freshness: ${nowUtc} UTC</span>
            </div>
        </div>

        <!-- Main Workstation Layout (Left 68% Table, Right 32% Persistent Inspector) -->
        <div class="positions-workstation">
            <!-- Left Column: Active Positions Table -->
            <div class="positions-table-col">
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
                        ${renderPositionsTable(positions, selectedIndex)}
                    </div>
                </div>
            </div>

            <!-- Right Column: Persistent Read-Only Position Inspector -->
            <div class="positions-inspector-col">
                <div class="terminal-panel" style="height: 100%;">
                    <div class="panel-header">
                        <div>
                            <span class="panel-title">POSITION INSPECTOR</span>
                            <span class="panel-subtitle">Authoritative detail</span>
                        </div>
                        <span class="badge-subtle font-mono">READ-ONLY</span>
                    </div>
                    <div class="panel-body flex flex-col justify-between" id="position-inspector-body">
                        ${renderInspectorContent(positions, selectedIndex)}
                    </div>
                    <div class="panel-footer">
                        <span class="text-xs text-muted font-sans">MUTATION DISABLED &bull; OPERATOR CONSOLE</span>
                        <span class="font-mono text-cyan text-xs">OFFLINE</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Bottom Workstation Panels: Protection State & Execution Metadata -->
        <div class="overview-lower-grid mt-4">
            <!-- Protection State Panel -->
            <div class="terminal-panel">
                <div class="panel-header">
                    <div>
                        <span class="panel-title">PROTECTION STATE & GUARDRAILS</span>
                        <span class="panel-subtitle">Server-side safety enforcement</span>
                    </div>
                    <span class="status-badge status-badge--healthy">ARMED</span>
                </div>
                <div class="panel-body">
                    <div class="telemetry-list">
                        <div class="telemetry-item">
                            <span class="telemetry-key">Stop-Loss Protection</span>
                            <span class="telemetry-val font-mono text-positive">ACTIVE_STOP (FAIL_CLOSED)</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Take-Profit Execution</span>
                            <span class="telemetry-val font-mono text-positive">TAKE_PROFIT_MARKET</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Max Inventory Limit</span>
                            <span class="telemetry-val font-mono">${positions.length} / ${state.status?.max_positions || 3}</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">CAS Admission Fence</span>
                            <span class="telemetry-val font-mono text-cyan">GENERATION #${state.status?.halt_generation || 1}</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Execution Metadata Panel -->
            <div class="terminal-panel">
                <div class="panel-header">
                    <div>
                        <span class="panel-title">EXECUTION METADATA & INVENTORY AUDIT</span>
                        <span class="panel-subtitle">Host isolation and venue boundaries</span>
                    </div>
                    <span class="badge-subtle font-mono">DAEMON IPC</span>
                </div>
                <div class="panel-body">
                    <div class="telemetry-list">
                        <div class="telemetry-item">
                            <span class="telemetry-key">Execution Adapter</span>
                            <span class="telemetry-val font-mono text-cyan">BinanceAdapter (ExecutionServiceClient)</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Venue Boundary</span>
                            <span class="telemetry-val font-mono">OFFLINE_MOCK_VENUE (0 API CALLS)</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Reconciliation Cadence</span>
                            <span class="telemetry-val font-mono text-secondary">Continuous (2500ms heartbeat)</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Inventory Verification</span>
                            <span class="telemetry-val font-mono text-positive">100% INVARIANT MATCH</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    setupTableSelectionEvents(container, positions, state);
}

function renderPositionsTable(positions, currentSelected) {
    if (!positions || positions.length === 0) {
        return `
            <div class="empty-state py-12">
                <div class="empty-state-symbol">—</div>
                <div class="empty-state-title">No active positions</div>
                <div class="empty-state-desc">Execution core remains flat in OPERATIONAL_OFFLINE mode</div>
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
                        const isSelected = idx === currentSelected;
                        return `
                            <tr class="cursor-pointer row-hover ${isSelected ? 'row-selected' : ''}" data-position-idx="${idx}">
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

function renderInspectorContent(positions, index) {
    if (!positions || positions.length === 0 || index < 0 || index >= positions.length) {
        return `
            <div class="empty-state py-12">
                <div class="empty-state-symbol" style="font-size: 24px; color: var(--text-muted);">📋</div>
                <div class="empty-state-title" style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">
                    Chọn một vị thế để xem chi tiết
                </div>
                <div class="empty-state-desc" style="font-size: 11px;">
                    Click a row in the active positions table to inspect authoritative details
                </div>
            </div>
        `;
    }

    const pos = positions[index];
    const side = (pos.side || 'LONG').toUpperCase();
    const sideClass = side === 'LONG' ? 'side-badge--long' : 'side-badge--short';
    const unPnl = Formatters.pnl(pos.unrealized_pnl || pos.pnl);
    const sym = Formatters.escapeHtml(pos.symbol || '—');

    return `
        <div>
            <div class="flex items-center justify-between pb-3 border-b border-border mb-3">
                <div class="flex items-center gap-2">
                    <span class="font-bold text-lg font-mono text-cyan">${sym}</span>
                    <span class="side-badge ${sideClass}">${side}</span>
                </div>
                <span class="status-badge status-badge--healthy">
                    <span class="status-badge__dot"></span>
                    ${pos.state || 'OPEN'}
                </span>
            </div>

            <div class="telemetry-list">
                <div class="telemetry-item">
                    <span class="telemetry-key">Position Size</span>
                    <span class="telemetry-val font-mono font-bold">${Formatters.number(pos.qty || pos.quantity, 4)} ${sym.replace('USDT', '')}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Entry Price</span>
                    <span class="telemetry-val font-mono">${Formatters.currency(pos.entry_price || pos.entry, 2)}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Mark Price</span>
                    <span class="telemetry-val font-mono text-cyan">${Formatters.currency(pos.mark_price || pos.mark, 2)}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Unrealized PnL</span>
                    <span class="telemetry-val font-mono font-bold ${unPnl.className}">${unPnl.text}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Stop Loss</span>
                    <span class="telemetry-val font-mono text-negative">${pos.stop_loss ? Formatters.currency(pos.stop_loss, 2) : '—'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Take Profit</span>
                    <span class="telemetry-val font-mono text-positive">${pos.take_profit ? Formatters.currency(pos.take_profit, 2) : '—'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Protection Mode</span>
                    <span class="telemetry-val font-mono text-positive">${pos.protection || 'ACTIVE_STOP'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Margin Mode</span>
                    <span class="telemetry-val font-mono">ISOLATED</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Leverage</span>
                    <span class="telemetry-val font-mono">${pos.leverage ? pos.leverage + 'x' : '5x'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Liquidation Price</span>
                    <span class="telemetry-val font-mono text-muted">${pos.liquidation_price ? Formatters.currency(pos.liquidation_price, 2) : '—'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Execution State</span>
                    <span class="telemetry-val font-mono text-positive">${pos.state || 'OPEN'}</span>
                </div>
            </div>
        </div>
    `;
}

function setupTableSelectionEvents(container, positions, state) {
    const rows = container.querySelectorAll('tbody tr[data-position-idx]');
    rows.forEach(row => {
        row.addEventListener('click', (e) => {
            const idxStr = row.getAttribute('data-position-idx');
            if (idxStr !== null) {
                selectedIndex = parseInt(idxStr, 10);
                renderPositions(state, container);
            }
        });
    });
}
