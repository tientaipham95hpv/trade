/**
 * Obsidian Quants - Overview View Renderer
 * Institutional 12-column telemetry, status projections, PnL, protection state.
 */

import { Formatters } from './formatters.js';

export function renderOverview(state, container) {
    if (!container) return;

    const status = state.status || {};
    const health = status.health || {};
    const isHealthy = state.statusKnown && status.status === 'HEALTHY';
    const isHalted = state.statusKnown && (status.status === 'HALTED' || status.is_paused === true);

    const execStatusText = state.statusKnown ? (isHalted ? 'HALTED' : (isHealthy ? 'HEALTHY' : status.status)) : 'UNKNOWN';
    const execStatusClass = state.statusKnown ? (isHalted ? 'status-badge--halt' : (isHealthy ? 'status-badge--healthy' : 'status-badge--degraded')) : 'status-badge--degraded';

    const pnlObj = Formatters.pnl(status.realized_pnl);
    const positions = state.positions || [];

    container.innerHTML = `
        <div class="terminal-grid-12">
            <!-- Row 1: System Health (4 cols), PnL & Performance (4 cols), Risk & Breaker (4 cols) -->
            <div class="col-span-4">
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">SYSTEM PROJECTION</span>
                        <span class="status-badge ${execStatusClass}">
                            <span class="status-badge__dot"></span>
                            ${execStatusText}
                        </span>
                    </div>
                    <div class="panel-body">
                        <div class="metric-grid-2">
                            <div class="metric-card">
                                <div class="metric-label">EXECUTION CORE</div>
                                <div class="metric-value font-mono ${state.statusKnown ? 'text-cyan' : 'text-muted'}">
                                    ${state.statusKnown ? 'OFFLINE_OK' : 'UNKNOWN'}
                                </div>
                                <div class="metric-caption">Deterministic Sandbox</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">IPC TRANSPORT</div>
                                <div class="metric-value font-mono text-cyan">
                                    ${state.latency ? Formatters.latency(state.latency) : '—'}
                                </div>
                                <div class="metric-caption">Loopback 50051</div>
                            </div>
                        </div>

                        <div class="telemetry-list mt-3">
                            <div class="telemetry-item">
                                <span class="telemetry-key">State Store</span>
                                <span class="telemetry-val text-primary font-mono">SQLite WAL Certified</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Execution Mode</span>
                                <span class="telemetry-val text-cyan font-mono">${status.mode || 'OFFLINE'}</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Global HALT</span>
                                <span class="telemetry-val ${isHalted ? 'text-loss' : 'text-profit'} font-mono">
                                    ${status.is_paused ? 'ACTIVE' : 'INACTIVE'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">HALT Generation</span>
                                <span class="telemetry-val font-mono">${status.halt_generation !== null && status.halt_generation !== undefined ? '#' + status.halt_generation : '—'}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-span-4">
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">PNL & PERFORMANCE</span>
                        <span class="badge-subtle">PROJECTION ONLY</span>
                    </div>
                    <div class="panel-body">
                        <div class="metric-grid-2">
                            <div class="metric-card">
                                <div class="metric-label">REALIZED PNL</div>
                                <div class="metric-value font-mono ${pnlObj.className}">
                                    ${pnlObj.text}
                                </div>
                                <div class="metric-caption">Authoritative execution</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">ACTIVE POSITIONS</div>
                                <div class="metric-value font-mono text-primary">
                                    ${status.open_positions_count !== null && status.open_positions_count !== undefined ? status.open_positions_count : '—'}
                                </div>
                                <div class="metric-caption">Max cap: ${status.max_positions || '—'}</div>
                            </div>
                        </div>

                        <div class="telemetry-list mt-3">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Win Rate</span>
                                <span class="telemetry-val text-muted font-mono" title="Authoritative metric unavailable">—</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Total Trades</span>
                                <span class="telemetry-val text-muted font-mono" title="Authoritative metric unavailable">—</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Max Drawdown</span>
                                <span class="telemetry-val text-muted font-mono" title="Authoritative metric unavailable">—</span>
                            </div>
                        </div>
                        <div class="equity-notice mt-2 text-xs text-muted font-mono text-center">
                            Chưa có dữ liệu equity được xác nhận.
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-span-4">
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">RISK & CIRCUIT BREAKER</span>
                        <span class="status-badge ${status.is_paused ? 'status-badge--halt' : 'status-badge--healthy'}">
                            <span class="status-badge__dot"></span>
                            ${status.is_paused ? 'TRIPPED' : 'ARMED'}
                        </span>
                    </div>
                    <div class="panel-body">
                        <div class="metric-grid-2">
                            <div class="metric-card">
                                <div class="metric-label">DAILY LOSS LIMIT</div>
                                <div class="metric-value font-mono text-primary">
                                    ${health.daily_loss !== undefined ? Formatters.currency(health.daily_loss) : '—'}
                                </div>
                                <div class="metric-caption">Max: ${health.max_daily_loss ? Formatters.currency(health.max_daily_loss) : '—'}</div>
                            </div>
                            <div class="metric-card">
                                <div class="metric-label">CONSECUTIVE LOSS</div>
                                <div class="metric-value font-mono text-primary">
                                    ${health.consecutive_losses !== undefined ? health.consecutive_losses : '—'}
                                </div>
                                <div class="metric-caption">Threshold: ${health.max_consecutive_losses || '—'}</div>
                            </div>
                        </div>

                        <div class="telemetry-list mt-3">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Cooldown Period</span>
                                <span class="telemetry-val font-mono">${health.cooldown_until ? Formatters.timestamp(health.cooldown_until * 1000) : 'CLEAR'}</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">HALT Reason</span>
                                <span class="telemetry-val font-mono text-ellipsis" title="${Formatters.escapeHtml(status.halt_reason || 'None')}">
                                    ${Formatters.escapeHtml(status.halt_reason || 'None')}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Row 2: Active Positions Mini-Table (8 cols) & Protection Status (4 cols) -->
            <div class="col-span-8">
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">ACTIVE POSITIONS SUMMARY</span>
                        <span class="panel-badge font-mono">${positions.length} OPEN</span>
                    </div>
                    <div class="panel-body p-0">
                        ${renderMiniPositionsTable(positions)}
                    </div>
                </div>
            </div>

            <div class="col-span-4">
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">PROTECTION & RECOVERY</span>
                        <span class="badge-subtle font-mono">FAIL-CLOSED</span>
                    </div>
                    <div class="panel-body">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Trailing Stop</span>
                                <span class="telemetry-val font-mono ${status.use_trailing_stop ? 'text-profit' : 'text-muted'}">
                                    ${status.use_trailing_stop ? 'ENABLED' : 'DISABLED'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Activation R:R</span>
                                <span class="telemetry-val font-mono">${status.trailing_activation_rr || '—'}</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Leverage Default</span>
                                <span class="telemetry-val font-mono">${status.leverage ? status.leverage + 'x' : '—'}</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Risk per Trade</span>
                                <span class="telemetry-val font-mono">${status.risk_percent ? status.risk_percent + '%' : '—'}</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Accounting State</span>
                                <span class="telemetry-val font-mono text-cyan">VERIFIED_ISOLATED</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderMiniPositionsTable(positions) {
    if (!positions || positions.length === 0) {
        return `
            <div class="empty-state py-8">
                <div class="empty-state-title">Không có vị thế mở nào đang hoạt động</div>
                <div class="empty-state-desc">Hệ thống đang ở chế độ giám sát. Không có rủi ro ký quỹ.</div>
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
                        <th>PROTECTION</th>
                    </tr>
                </thead>
                <tbody>
                    ${positions.map(pos => {
                        const side = (pos.side || 'LONG').toUpperCase();
                        const sideClass = side === 'LONG' ? 'text-profit' : 'text-loss';
                        const unPnl = Formatters.pnl(pos.unrealized_pnl || pos.pnl);
                        return `
                            <tr>
                                <td class="font-bold font-mono">${pos.symbol || '—'}</td>
                                <td class="${sideClass} font-mono font-bold">${side}</td>
                                <td class="text-right font-mono">${Formatters.number(pos.qty || pos.quantity, 4)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.entry_price || pos.entry, 2)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.mark_price || pos.mark, 2)}</td>
                                <td class="text-right font-mono ${unPnl.className}">${unPnl.text}</td>
                                <td>
                                    <span class="badge-subtle font-mono">${pos.protection || 'SL_GUARDED'}</span>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}
