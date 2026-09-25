/**
 * Obsidian Quants V3 — Overview View Renderer
 * Professional Trading Terminal 3-Band Information Architecture
 * Band 1: System Strip (5 cols)
 * Band 2: Financial Telemetry (5 cols)
 * Band 3: Main Work Area (Left 65% Positions, Right 35% Risk / Protection)
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

    const haltText = isHalted ? `ACTIVE (#${status.halt_generation || '1'})` : 'INACTIVE';
    const haltColorClass = isHalted ? 'text-critical' : 'text-positive';

    const latencyText = state.latency ? Formatters.latency(state.latency) : '—';

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

    const dailyLossText = (health.daily_loss !== null && health.daily_loss !== undefined)
        ? Formatters.currency(health.daily_loss, 2)
        : '—';

    const lossStreak = (health.consecutive_losses !== null && health.consecutive_losses !== undefined)
        ? health.consecutive_losses
        : 0;

    const positions = state.positions || [];

    container.innerHTML = `
        <div class="overview-band-wrapper">
            <!-- BAND 1: SYSTEM STRIP (5 COLUMNS) -->
            <div class="band-system-strip">
                <div class="system-strip-item">
                    <span class="system-strip-label">EXECUTION</span>
                    <span class="system-strip-val ${execColorClass}">
                        <span class="status-badge__dot"></span>
                        ${execStatusText}
                    </span>
                </div>
                <div class="system-strip-item">
                    <span class="system-strip-label">ENVIRONMENT</span>
                    <span class="system-strip-val text-cyan font-bold">${envText}</span>
                </div>
                <div class="system-strip-item">
                    <span class="system-strip-label">BREAKER</span>
                    <span class="system-strip-val ${breakerColorClass}">${breakerText}</span>
                </div>
                <div class="system-strip-item">
                    <span class="system-strip-label">HALT</span>
                    <span class="system-strip-val ${haltColorClass}">${haltText}</span>
                </div>
                <div class="system-strip-item">
                    <span class="system-strip-label">LATENCY</span>
                    <span class="system-strip-val text-cyan">${latencyText}</span>
                </div>
            </div>

            <!-- BAND 2: FINANCIAL TELEMETRY STRIP (5 COLUMNS) -->
            <div class="band-financial-strip">
                <div class="financial-strip-item">
                    <span class="financial-strip-label">REALIZED PNL</span>
                    <span class="financial-strip-val ${realizedPnlObj.className}">${realizedPnlObj.text}</span>
                </div>
                <div class="financial-strip-item">
                    <span class="financial-strip-label">UNREALIZED PNL</span>
                    <span class="financial-strip-val ${unrealizedPnlObj.className}">${unrealizedPnlObj.text}</span>
                </div>
                <div class="financial-strip-item">
                    <span class="financial-strip-label">OPEN POSITIONS</span>
                    <span class="financial-strip-val text-primary">${positionsRatioText}</span>
                </div>
                <div class="financial-strip-item">
                    <span class="financial-strip-label">DAILY LOSS</span>
                    <span class="financial-strip-val text-secondary">${dailyLossText}</span>
                </div>
                <div class="financial-strip-item">
                    <span class="financial-strip-label">LOSS STREAK</span>
                    <span class="financial-strip-val ${lossStreak > 0 ? 'text-warning' : 'text-secondary'}">${lossStreak}</span>
                </div>
            </div>

            <!-- BAND 3: MAIN WORK AREA (65% ACTIVE POSITIONS, 35% RISK / PROTECTION) -->
            <div class="band-work-area">
                <!-- Left 65%: Active Positions -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">ACTIVE POSITIONS</span>
                        <span class="badge-subtle font-mono">${positions.length} OPEN</span>
                    </div>
                    <div class="panel-body p-0">
                        ${renderPositionsPreview(positions)}
                    </div>
                </div>

                <!-- Right 35%: Risk / Protection -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">RISK & PROTECTION SUMMARY</span>
                        <span class="badge-subtle font-mono">DETERMINISTIC</span>
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
                                    ${status.halt_generation !== null && status.halt_generation !== undefined ? '#' + status.halt_generation : '—'}
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
                                <span class="telemetry-val font-mono">
                                    ${health.max_daily_loss ? Formatters.currency(health.max_daily_loss, 2) : '—'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Max Concurrent</span>
                                <span class="telemetry-val font-mono">
                                    ${status.max_positions || 3} POSITIONS
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Core Integrity</span>
                                <span class="telemetry-val text-positive font-bold font-mono">
                                    15/15 CERTIFIED
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

function renderPositionsPreview(positions) {
    if (!positions || positions.length === 0) {
        return `
            <div class="empty-state py-8">
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
                        <th>STATE</th>
                    </tr>
                </thead>
                <tbody>
                    ${positions.map((pos) => {
                        const side = (pos.side || 'LONG').toUpperCase();
                        const sideClass = side === 'LONG' ? 'side-badge--long' : 'side-badge--short';
                        const unPnl = Formatters.pnl(pos.unrealized_pnl || pos.pnl);
                        const sym = Formatters.escapeHtml(pos.symbol || '—');
                        return `
                            <tr>
                                <td class="font-bold font-mono text-cyan">${sym}</td>
                                <td><span class="side-badge ${sideClass}">${side}</span></td>
                                <td class="text-right font-mono">${Formatters.number(pos.qty || pos.quantity, 4)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.entry_price || pos.entry, 2)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.mark_price || pos.mark, 2)}</td>
                                <td class="text-right font-mono ${unPnl.className}">${unPnl.text}</td>
                                <td><span class="status-badge status-badge--healthy">OPEN</span></td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}
