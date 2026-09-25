/**
 * Obsidian Quants V3 — Risk View Renderer
 * Professional Trading Terminal Risk Architecture
 * Layout: RISK STATUS Header + 2-Column Grid (Left: Circuit Breaker & Loss Limits, Right: HALT Machine & Controls)
 * Action styling: Dark red outline HALT button, neutral/cyan outline RESUME button, muted note for CLOSE ALL.
 */

import { Formatters } from './formatters.js';
import { api } from './api.js';
import { poller } from './polling.js';

let isActionInFlight = false;

export function renderRisk(state, container) {
    if (!container) return;

    const status = state.status || {};
    const health = status.health || {};
    const isHalted = state.statusKnown && (status.status === 'HALTED' || status.is_paused === true);
    const breakerTripped = isHalted || health.state === 'TRIPPED' || health.state === 'BROKEN';
    const haltGen = status.halt_generation;
    const recoveryRequired = Boolean(status.recovery_required);
    const resumeAllowed = Boolean(status.resume_allowed !== undefined
        ? status.resume_allowed
        : (isHalted && haltGen && haltGen > 0 && !recoveryRequired && status.status !== 'UNKNOWN'));

    const riskOverallText = breakerTripped ? 'FAIL_CLOSED (RESTRICTED)' : 'NORMAL (FAIL_CLOSED ARMED)';
    const riskOverallColor = breakerTripped ? 'status-badge--halt' : 'status-badge--healthy';

    container.innerHTML = `
        <div class="overview-band-wrapper">
            <!-- Header: RISK STATUS -->
            <div class="terminal-panel">
                <div class="panel-header">
                    <span class="panel-title">RISK STATUS</span>
                    <span class="status-badge ${riskOverallColor}">
                        <span class="status-badge__dot"></span>
                        ${riskOverallText}
                    </span>
                </div>
            </div>

            ${isHalted ? `
                <div class="risk-alert risk-alert--halt">
                    <div class="risk-alert__icon">⚠</div>
                    <div class="risk-alert__content">
                        <div class="risk-alert__title">OPERATOR / SAFETY HALT ACTIVE (GENERATION #${haltGen || '1'})</div>
                        <div class="risk-alert__desc">
                            Reason: ${Formatters.escapeHtml(status.halt_reason || 'Circuit breaker fail-closed triggered')}
                        </div>
                    </div>
                </div>
            ` : ''}

            <!-- Two-Column Layout -->
            <div class="risk-two-column">
                <!-- Left Pane: Circuit Breaker & Limits -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">CIRCUIT BREAKER & THRESHOLDS</span>
                        <span class="badge-subtle font-mono">FAIL-CLOSED</span>
                    </div>
                    <div class="panel-body">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Circuit Breaker</span>
                                <span class="telemetry-val ${breakerTripped ? 'text-critical' : 'text-positive'} font-bold">
                                    ${breakerTripped ? 'TRIPPED (FAIL_CLOSED)' : 'ARMED (MONITORING)'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Daily Loss</span>
                                <span class="telemetry-val font-mono">
                                    ${health.daily_loss !== undefined ? Formatters.currency(health.daily_loss, 2) : '—'} / 
                                    ${health.max_daily_loss ? Formatters.currency(health.max_daily_loss, 2) : '—'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Consecutive Losses</span>
                                <span class="telemetry-val font-mono">
                                    ${health.consecutive_losses !== undefined ? health.consecutive_losses : '0'} / 
                                    ${health.max_consecutive_losses || '3'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Cooldown</span>
                                <span class="telemetry-val font-mono text-secondary">
                                    ${health.cooldown_until ? Formatters.timestamp(health.cooldown_until * 1000) : 'CLEAR (NO COOLDOWN)'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Max Concurrent Positions</span>
                                <span class="telemetry-val font-mono">
                                    ${status.max_positions || 3}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Baseline Capital Ref</span>
                                <span class="telemetry-val font-mono text-muted text-xs">
                                    ${health.daily_baseline_balance ? Formatters.currency(health.daily_baseline_balance, 2) : 'EXECUTION_SERVICE_STORE'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Right Pane: HALT State & Operator Controls -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">HALT & OPERATOR CONTROLS</span>
                        <span class="badge-subtle font-mono">CAS GATE</span>
                    </div>
                    <div class="panel-body flex flex-col justify-between" style="min-height: 240px;">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">HALT</span>
                                <span class="telemetry-val ${isHalted ? 'text-critical' : 'text-positive'} font-bold">
                                    ${isHalted ? 'ACTIVE (ENTRY BLOCKED)' : 'INACTIVE (PERMITTED)'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Generation</span>
                                <span class="telemetry-val font-mono text-cyan">
                                    ${haltGen !== null && haltGen !== undefined ? '#' + haltGen : '—'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Reason</span>
                                <span class="telemetry-val font-mono text-secondary text-xs">
                                    ${Formatters.escapeHtml(status.halt_reason || '—')}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Recovery Required</span>
                                <span class="telemetry-val font-mono ${recoveryRequired ? 'text-critical font-bold' : 'text-positive'}">
                                    ${recoveryRequired ? 'YES (ACTION REQUIRED)' : 'CLEAR'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Resume Allowed</span>
                                <span class="telemetry-val font-mono ${resumeAllowed ? 'text-positive' : 'text-muted'}">
                                    ${resumeAllowed ? 'CAS RESUME PERMITTED' : (recoveryRequired ? 'BLOCKED (RECOVERY REQUIRED)' : (isHalted ? 'CAS GENERATION MATCH REQUIRED' : 'NORMAL (NOT HALTED)'))}
                                </span>
                            </div>
                        </div>

                        <!-- Operator Action Controls at Bottom of Right Pane -->
                        <div class="pt-4 border-t border-border mt-4 flex flex-col gap-2">
                            <div class="flex gap-3">
                                <button id="btn-operator-halt" class="btn btn-halt ${isActionInFlight || !state.statusKnown ? 'opacity-50 cursor-not-allowed' : ''}" ${isActionInFlight || !state.statusKnown ? 'disabled' : ''} title="Emergency stop all new order admission">
                                    ${isActionInFlight ? 'PROCESSING...' : 'HALT'}
                                </button>
                                <button id="btn-operator-resume" class="btn btn-resume ${!resumeAllowed || isActionInFlight ? 'opacity-50 cursor-not-allowed' : ''}" ${!resumeAllowed || isActionInFlight ? 'disabled' : ''} title="${!resumeAllowed ? (recoveryRequired ? 'Recovery required before resume' : (!isHalted ? 'System is not halted' : 'Resume criteria not met')) : 'Resume execution admission with CAS'}">
                                    ${isActionInFlight ? 'PROCESSING...' : `RESUME (#${haltGen || '—'})`}
                                </button>
                            </div>
                            <!-- Small muted line for Emergency Close (Disabled in operator console) -->
                            <div class="emergency-close-note" disabled>
                                Emergency close: Unavailable in this console (ĐÓNG TẤT CẢ — VÔ HIỆU HÓA)
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Attach Event Listeners
    const haltBtn = container.querySelector('#btn-operator-halt');
    if (haltBtn && !haltBtn.disabled) {
        haltBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (isActionInFlight) return;
            const ok = confirm("CONFIRM EMERGENCY HALT?\n\nThis will trigger an immediate fail-closed block on all new order admissions and increment the HALT generation counter.");
            if (!ok) return;

            isActionInFlight = true;
            renderRisk(state, container);

            try {
                const res = await api.post('/api/pause', {
                    reason: 'Web operator manual halt',
                    source: 'web'
                });

                if (res.status === 403) {
                    alert('Permission denied (403 Forbidden).');
                } else if (res.status === 0) {
                    alert('UNKNOWN_OUTCOME: Network timeout communicating with Execution Service. Check server status before re-attempting.');
                } else if (!res.success) {
                    alert(`HALT ERROR (${res.status}): ${res.data?.message || res.error || 'Operation failed'}`);
                } else {
                    await poller.pollStatus();
                }
            } catch (err) {
                alert(`UNKNOWN_OUTCOME: ${err.message || err}`);
            } finally {
                isActionInFlight = false;
                renderRisk(state, container);
            }
        });
    }

    const resumeBtn = container.querySelector('#btn-operator-resume');
    if (resumeBtn && !resumeBtn.disabled) {
        resumeBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            if (isActionInFlight) return;
            if (!resumeAllowed) return;

            const ok = confirm(`CONFIRM RESUME WITH CAS (#${haltGen})?\n\nResume will be submitted with expected_halt_generation=${haltGen}. If generation has mutated, Execution Service will reject with STALE_HALT_GENERATION.`);
            if (!ok) return;

            isActionInFlight = true;
            renderRisk(state, container);

            try {
                const res = await api.post('/api/resume', {
                    expected_halt_generation: haltGen,
                    source: 'web'
                });

                if (res.status === 403) {
                    alert('Permission denied (403 Forbidden).');
                } else if (res.status === 409 || res.data?.code === 'STALE_HALT_GENERATION') {
                    alert(`STALE CAS CONFLICT: Expected generation #${haltGen} does not match authoritative generation #${res.data?.current_halt_generation || 'unknown'}. Refreshing state.`);
                    await poller.pollStatus();
                } else if (res.status === 0) {
                    alert('UNKNOWN_OUTCOME: Network timeout during resume. Check server status before re-attempting.');
                } else if (!res.success) {
                    alert(`RESUME ERROR (${res.status}): ${res.data?.message || res.error || 'Operation failed'}`);
                } else {
                    await poller.pollStatus();
                }
            } catch (err) {
                alert(`UNKNOWN_OUTCOME: ${err.message || err}`);
            } finally {
                isActionInFlight = false;
                renderRisk(state, container);
            }
        });
    }
}
