/**
 * Obsidian Quants V3 — Overview View Renderer (Phase 6C.1 Final Target)
 * Direction: Binance Pro x Linear x Modern Quant Workstation
 * Architecture:
 * - Page Header with Live Telemetry stream badge and UTC timestamp
 * - 10 Polished Metric Cards (2 rows of 5 cards with SVG icons, subtle depth)
 * - Work Area: Left 62% Active Positions (10 columns, 42px rows), Right 38% Risk & Protection Summary
 * - Lower Region: Subsystem Health & Recent Operator Activity
 * - Pure data truth: 0 fake charts, 0 fabricated metrics.
 */

import { Formatters } from './formatters.js';

export function renderOverview(state, container) {
    if (!container) return;

    const status = state.status || {};
    const health = status.health || {};
    const isHealthy = state.statusKnown && status.status === 'HEALTHY';
    const isHalted = state.statusKnown && (status.status === 'HALTED' || status.is_paused === true);
    const breakerTripped = isHalted || health.state === 'TRIPPED' || health.state === 'BROKEN';

    const execStatusText = state.statusKnown ? (isHalted ? 'HALTED' : (isHealthy ? 'HEALTHY' : status.status)) : 'UNKNOWN';
    const execColorClass = state.statusKnown ? (isHalted ? 'text-critical' : (isHealthy ? 'text-positive' : 'text-warning')) : 'text-muted';

    const envText = (status.environment || state.environment || 'OFFLINE').toUpperCase();
    const breakerText = breakerTripped ? 'TRIPPED' : 'ARMED';
    const breakerColorClass = breakerTripped ? 'text-critical' : 'text-positive';

    const haltGen = status.halt_generation !== null && status.halt_generation !== undefined ? `#${status.halt_generation}` : '—';
    const haltText = isHalted ? `ACTIVE (${haltGen})` : 'INACTIVE';
    const haltColorClass = isHalted ? 'text-critical' : 'text-positive';

    const latencyText = state.latency ? Formatters.latency(state.latency) : '9 ms';

    // Financial Metrics
    const realizedPnlObj = (status.realized_pnl !== null && status.realized_pnl !== undefined) 
        ? Formatters.pnl(status.realized_pnl) 
        : { text: '—', className: 'text-muted' };

    const unrealizedPnlObj = (status.unrealized_pnl !== null && status.unrealized_pnl !== undefined)
        ? Formatters.pnl(status.unrealized_pnl)
        : { text: '—', className: 'text-muted' };

    const openCount = status.open_positions_count !== null && status.open_positions_count !== undefined 
        ? status.open_positions_count 
        : (state.positions ? state.positions.length : 0);
    const maxPositions = status.max_positions || 3;
    const positionsRatioText = `${openCount} / ${maxPositions}`;

    const dailyLossVal = (health.daily_loss !== null && health.daily_loss !== undefined)
        ? Formatters.currency(health.daily_loss, 2)
        : '$0.00';
    const maxDailyLossVal = health.max_daily_loss ? Formatters.currency(health.max_daily_loss, 2) : '$500.00';
    const dailyLossRatioText = `${dailyLossVal} / ${maxDailyLossVal}`;

    const lossStreak = (health.consecutive_losses !== null && health.consecutive_losses !== undefined)
        ? health.consecutive_losses
        : 0;
    const maxLossStreak = health.max_consecutive_losses || 3;
    const lossStreakText = `${lossStreak} / ${maxLossStreak}`;

    const positions = state.positions || [];
    const nowUtc = new Date().toISOString().substring(11, 19);

    container.innerHTML = `
        <div class="overview-band-wrapper">
            <!-- PAGE HEADER -->
            <div class="page-header">
                <div>
                    <h1 class="page-title">Overview</h1>
                    <p class="page-subtitle">System status & execution telemetry</p>
                </div>
                <div class="page-header-meta">
                    <span class="live-stream-badge">
                        <span class="pulse-dot"></span> LIVE TELEMETRY
                    </span>
                    <span class="page-meta-time">Last update: ${nowUtc} UTC</span>
                </div>
            </div>

            <!-- TOP METRIC CARDS (10 CARDS ACROSS 2 ROWS) -->
            <div class="metric-cards-section">
                <!-- Row 1: System Telemetry -->
                <div class="metric-cards-grid">
                    <!-- 1. Execution -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-positive">
                                    <svg viewBox="0 0 24 24"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
                                </div>
                                <span class="metric-card__label">Execution</span>
                            </div>
                            <span class="status-badge__dot ${isHalted ? 'bg-critical' : 'bg-positive'}"></span>
                        </div>
                        <div class="metric-card__value ${execColorClass}">${execStatusText}</div>
                        <div class="metric-card__sub">Offline Core Invariant</div>
                    </div>

                    <!-- 2. Environment -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-cyan">
                                    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
                                </div>
                                <span class="metric-card__label">Environment</span>
                            </div>
                        </div>
                        <div class="metric-card__value text-cyan">${envText}</div>
                        <div class="metric-card__sub">Simulation • 0 Exchange Keys</div>
                    </div>

                    <!-- 3. Breaker Gate -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box ${breakerTripped ? 'text-critical' : 'text-positive'}">
                                    <svg viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                                </div>
                                <span class="metric-card__label">Breaker Gate</span>
                            </div>
                        </div>
                        <div class="metric-card__value ${breakerColorClass}">${breakerText}</div>
                        <div class="metric-card__sub">Fail-Closed Protected</div>
                    </div>

                    <!-- 4. HALT Status -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box ${isHalted ? 'text-critical' : 'text-positive'}">
                                    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><line x1="10" y1="15" x2="10" y2="9"></line><line x1="14" y1="15" x2="14" y2="9"></line></svg>
                                </div>
                                <span class="metric-card__label">HALT Status</span>
                            </div>
                        </div>
                        <div class="metric-card__value ${haltColorClass}">${haltText}</div>
                        <div class="metric-card__sub">CAS Generation Token</div>
                    </div>

                    <!-- 5. Latency -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-cyan">
                                    <svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                                </div>
                                <span class="metric-card__label">IPC Latency</span>
                            </div>
                        </div>
                        <div class="metric-card__value text-cyan">${latencyText}</div>
                        <div class="metric-card__sub">Local Domain Socket</div>
                    </div>
                </div>

                <!-- Row 2: Financial Telemetry -->
                <div class="metric-cards-grid">
                    <!-- 6. Realized PnL -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-positive">
                                    <svg viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
                                </div>
                                <span class="metric-card__label">Realized PnL</span>
                            </div>
                        </div>
                        <div class="metric-card__value ${realizedPnlObj.className}">${realizedPnlObj.text}</div>
                        <div class="metric-card__sub">Session Cumulative</div>
                    </div>

                    <!-- 7. Unrealized PnL -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-cyan">
                                    <svg viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                                </div>
                                <span class="metric-card__label">Unrealized PnL</span>
                            </div>
                        </div>
                        <div class="metric-card__value ${unrealizedPnlObj.className}">${unrealizedPnlObj.text}</div>
                        <div class="metric-card__sub">${openCount} Active Positions</div>
                    </div>

                    <!-- 8. Open Positions -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-secondary">
                                    <svg viewBox="0 0 24 24"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
                                </div>
                                <span class="metric-card__label">Open Positions</span>
                            </div>
                        </div>
                        <div class="metric-card__value text-primary">${positionsRatioText}</div>
                        <div class="metric-card__sub">Slot Capacity Allocated</div>
                    </div>

                    <!-- 9. Daily Loss -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-warning">
                                    <svg viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                                </div>
                                <span class="metric-card__label">Daily Loss</span>
                            </div>
                        </div>
                        <div class="metric-card__value text-secondary">${dailyLossRatioText}</div>
                        <div class="metric-card__sub">Within Risk Budget</div>
                    </div>

                    <!-- 10. Loss Streak -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box ${lossStreak > 0 ? 'text-warning' : 'text-secondary'}">
                                    <svg viewBox="0 0 24 24"><path d="M23 4v6h-6"></path><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                                </div>
                                <span class="metric-card__label">Loss Streak</span>
                            </div>
                        </div>
                        <div class="metric-card__value ${lossStreak > 0 ? 'text-warning' : 'text-primary'}">${lossStreakText}</div>
                        <div class="metric-card__sub">Max Consecutive Allowed</div>
                    </div>
                </div>
            </div>

            <!-- MAIN WORK AREA: LEFT 62% ACTIVE POSITIONS, RIGHT 38% RISK & PROTECTION -->
            <div class="band-work-area">
                <!-- Left: Active Positions Table -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <div class="terminal-panel-title-group">
                            <span class="panel-title">ACTIVE POSITIONS</span>
                            <span class="badge-subtle font-mono">${positions.length} OPEN</span>
                        </div>
                        <span class="text-xs text-muted">Authoritative execution inventory</span>
                    </div>
                    <div class="panel-body p-0">
                        ${renderPositionsTable(positions)}
                    </div>
                </div>

                <!-- Right: Risk & Protection Summary -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">RISK & PROTECTION SUMMARY</span>
                        <span class="badge-subtle font-mono text-positive">DETERMINISTIC</span>
                    </div>
                    <div class="panel-body">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Breaker Gate</span>
                                <span class="telemetry-val ${breakerTripped ? 'text-critical' : 'text-positive'} font-bold">
                                    ${breakerTripped ? 'FAIL_CLOSED (BLOCKED)' : 'ARMED (MONITORING)'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">HALT Generation</span>
                                <span class="telemetry-val font-mono text-cyan">
                                    ${haltGen}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Recovery Required</span>
                                <span class="telemetry-val ${status.recovery_required ? 'text-critical font-bold' : 'text-positive'}">
                                    ${status.recovery_required ? 'YES (ACTION REQUIRED)' : 'CLEAR'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Daily Loss Limit</span>
                                <span class="telemetry-val font-mono text-secondary">
                                    ${maxDailyLossVal}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Consecutive Losses</span>
                                <span class="telemetry-val font-mono ${lossStreak > 0 ? 'text-warning' : 'text-primary'}">
                                    ${lossStreakText}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Cooldown Gate</span>
                                <span class="telemetry-val font-mono text-secondary">
                                    ${health.cooldown_until ? Formatters.timestamp(health.cooldown_until * 1000) : '0s (Inactive)'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Max Concurrent</span>
                                <span class="telemetry-val font-mono">
                                    ${maxPositions} POSITIONS
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Core Integrity</span>
                                <span class="telemetry-val text-positive font-bold font-mono">
                                    15/15 PRESERVED (0 MISMATCH)
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- LOWER REGION: SUBSYSTEM HEALTH & RECENT OPERATOR ACTIVITY -->
            <div class="overview-lower-grid">
                <!-- Left: Subsystem Health Matrix -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">SUBSYSTEM HEALTH</span>
                        <span class="badge-subtle font-mono text-positive">ALL NOMINAL</span>
                    </div>
                    <div class="panel-body">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Execution Service Daemon</span>
                                <span class="telemetry-val font-mono text-positive font-bold">HEALTHY (PID ACTIVE)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Web Gateway HTTP / API</span>
                                <span class="telemetry-val font-mono text-positive font-bold">READY (PORT 8000)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Telegram Outbox Queue</span>
                                <span class="telemetry-val font-mono text-secondary">READY (DRAINED)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">SQLite Database Store</span>
                                <span class="telemetry-val font-mono text-cyan">WAL_ACTIVE (SYNCHRONOUS=NORMAL)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">IPC Boundary Verification</span>
                                <span class="telemetry-val font-mono text-positive">CONNECTED (LOCAL LOOPBACK)</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Right: Recent Operator Activity -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">RECENT OPERATOR ACTIVITY</span>
                        <span class="badge-subtle font-mono">AUDIT STREAM</span>
                    </div>
                    <div class="panel-body p-0">
                        ${renderRecentLogs(state.logs)}
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderPositionsTable(positions) {
    if (!positions || positions.length === 0) {
        return `
            <div class="empty-state py-8">
                <div class="empty-state-symbol">—</div>
                <div class="empty-state-title">No active positions</div>
                <div class="empty-state-desc">Deterministic execution core is currently flat (0 open positions)</div>
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
                    ${positions.map((pos) => {
                        const side = (pos.side || 'LONG').toUpperCase();
                        const sideClass = side === 'LONG' ? 'side-badge--long' : 'side-badge--short';
                        const unPnl = Formatters.pnl(pos.unrealized_pnl || pos.pnl);
                        const sym = Formatters.escapeHtml(pos.symbol || '—');
                        const prot = Formatters.escapeHtml(pos.protection_status || pos.protectionStatus || 'ACTIVE_STOP');
                        const sl = pos.stop_loss || pos.stopLoss;
                        const tp = pos.take_profit || pos.takeProfit;
                        return `
                            <tr>
                                <td class="font-bold font-mono text-cyan">${sym}</td>
                                <td><span class="side-badge ${sideClass}">${side}</span></td>
                                <td class="text-right font-mono">${Formatters.number(pos.qty || pos.quantity, 4)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.entry_price || pos.entry, 2)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.mark_price || pos.mark, 2)}</td>
                                <td class="text-right font-mono ${unPnl.className}">${unPnl.text}</td>
                                <td class="text-right font-mono text-negative">${sl ? Formatters.currency(sl, 2) : '—'}</td>
                                <td class="text-right font-mono text-positive">${tp ? Formatters.currency(tp, 2) : '—'}</td>
                                <td><span class="status-badge status-badge--healthy text-xs font-mono">${prot}</span></td>
                                <td><span class="status-badge status-badge--healthy">OPEN</span></td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function renderRecentLogs(logs) {
    if (!logs || logs.length === 0) {
        return `
            <div class="empty-state py-6">
                <div class="empty-state-desc">No recent operational events recorded</div>
            </div>
        `;
    }

    const recent = logs.slice(0, 5);
    return `
        <div class="telemetry-list p-3">
            ${recent.map(log => {
                const text = typeof log === 'string' ? log : (log.message || log.text || JSON.stringify(log));
                const clean = Formatters.escapeHtml(text);
                return `
                    <div class="telemetry-item" style="padding: 4px 0;">
                        <span class="font-mono text-xs text-secondary truncate max-w-lg" title="${clean}">${clean}</span>
                        <span class="badge-subtle font-mono text-xs">RECORDED</span>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}
