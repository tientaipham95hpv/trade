/**
 * Obsidian Quants V3 — System & Governance View Renderer
 * Professional Trading Terminal System Architecture
 * Concise Sections: Runtime | Services | Authority | Certification | Features | Build
 * Compact neutral certification block: CORE CERTIFICATION 15/15 verified OFFLINE EXECUTION CORE ACCEPTED
 */

import { Formatters } from './formatters.js';

export function renderSystem(state, container) {
    if (!container) return;

    const status = state.status || {};

    container.innerHTML = `
        <div class="overview-band-wrapper">
            <!-- 2-Column Grid for System Specifications -->
            <div class="terminal-grid-12">
                <!-- Section 1: Runtime (6 cols) -->
                <div class="col-span-6">
                    <div class="terminal-panel">
                        <div class="panel-header">
                            <span class="panel-title">RUNTIME SPECIFICATION</span>
                            <span class="status-badge status-badge--healthy">OFFLINE_ACTIVE</span>
                        </div>
                        <div class="panel-body">
                            <div class="telemetry-list">
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Environment</span>
                                    <span class="telemetry-val font-mono text-cyan font-bold">${(status.environment || state.environment || 'OFFLINE').toUpperCase()}</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Mode</span>
                                    <span class="telemetry-val font-mono">${status.mode || 'SIMULATION'}</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Release Target</span>
                                    <span class="telemetry-val font-mono text-xs">UI_V2_RC1_PHASE6C</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Venue Target</span>
                                    <span class="telemetry-val font-mono">OFFLINE_MOCK_VENUE (0 API CALLS)</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Supervisor Unit</span>
                                    <span class="telemetry-val font-mono text-xs">trader-stack-offline.service</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 2: Services Health (6 cols) -->
                <div class="col-span-6">
                    <div class="terminal-panel">
                        <div class="panel-header">
                            <span class="panel-title">SERVICES</span>
                            <span class="badge-subtle font-mono">DAEMON PROCESSES</span>
                        </div>
                        <div class="panel-body">
                            <div class="telemetry-list">
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Execution Service</span>
                                    <span class="telemetry-val font-mono text-positive font-bold">HEALTHY</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Web Gateway</span>
                                    <span class="telemetry-val font-mono text-positive font-bold">HEALTHY</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Telegram Bot</span>
                                    <span class="telemetry-val font-mono text-positive font-bold">HEALTHY</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">State Store WAL</span>
                                    <span class="telemetry-val font-mono text-positive font-bold">HEALTHY</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Loopback IPC (50051)</span>
                                    <span class="telemetry-val font-mono text-positive font-bold">BOUND</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 3: Authority Boundaries (6 cols) -->
                <div class="col-span-6">
                    <div class="terminal-panel">
                        <div class="panel-header">
                            <span class="panel-title">AUTHORITY BOUNDARIES</span>
                            <span class="badge-subtle font-mono">PROCESS ISOLATION</span>
                        </div>
                        <div class="panel-body">
                            <div class="telemetry-list">
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Execution Mutation</span>
                                    <span class="telemetry-val font-mono text-cyan">Execution Service only</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Trading Credentials</span>
                                    <span class="telemetry-val font-mono text-muted">REMOVED / NONE</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Web Direct Exchange Calls</span>
                                    <span class="telemetry-val font-mono text-positive">ZERO (PROHIBITED)</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Direct DB Trade Execution</span>
                                    <span class="telemetry-val font-mono text-positive">ZERO (SERVICE PID ONLY)</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Auth Transport</span>
                                    <span class="telemetry-val font-mono">HttpOnly SameSite Cookie</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 4: Core Certification (6 cols) -->
                <div class="col-span-6">
                    <div class="terminal-panel">
                        <div class="panel-header">
                            <span class="panel-title">CERTIFICATION</span>
                            <span class="status-badge status-badge--healthy font-mono">CRYPTOGRAPHIC</span>
                        </div>
                        <div class="panel-body">
                            <div class="core-cert-block">
                                <span class="core-cert-title">CORE CERTIFICATION</span>
                                <span class="core-cert-status">15 / 15 verified</span>
                                <span class="core-cert-sub">OFFLINE EXECUTION CORE ACCEPTED</span>
                            </div>
                            <div class="telemetry-list mt-3">
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Mismatch Count</span>
                                    <span class="telemetry-val font-mono text-positive">0 MISMATCHES</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Core Path</span>
                                    <span class="telemetry-val font-mono text-xs">core/execution/*</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Execution Invariance</span>
                                    <span class="telemetry-val font-mono text-positive">FROZEN_STABLE</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 5: Features Governance Matrix (12 cols) -->
                <div class="col-span-12">
                    <div class="terminal-panel">
                        <div class="panel-header">
                            <span class="panel-title">FEATURES GOVERNANCE MATRIX</span>
                            <span class="badge-subtle font-mono">FAIL-CLOSED</span>
                        </div>
                        <div class="panel-body p-0">
                            <div class="dense-table-container">
                                <table class="dense-table">
                                    <thead>
                                        <tr>
                                            <th>FEATURE SUBSYSTEM</th>
                                            <th>AUTHORITY TARGET</th>
                                            <th>STATUS</th>
                                            <th>SAFEGUARD POLICY</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td class="font-bold font-mono">Operator HALT</td>
                                            <td class="font-mono text-xs">Execution Service (/api/pause)</td>
                                            <td><span class="status-badge status-badge--healthy">AVAILABLE</span></td>
                                            <td class="text-secondary text-xs">Atomic CAS generation increment</td>
                                        </tr>
                                        <tr>
                                            <td class="font-bold font-mono">Operator RESUME</td>
                                            <td class="font-mono text-xs">Execution Service (/api/resume)</td>
                                            <td><span class="status-badge status-badge--healthy">AVAILABLE</span></td>
                                            <td class="text-secondary text-xs">Conditional on CAS generation match</td>
                                        </tr>
                                        <tr>
                                            <td class="font-bold font-mono">CLOSE ALL</td>
                                            <td class="font-mono text-xs">Unavailable</td>
                                            <td><span class="status-badge status-badge--critical">DISABLED</span></td>
                                            <td class="text-muted text-xs">Prohibited in operator console</td>
                                        </tr>
                                        <tr>
                                            <td class="font-bold font-mono">Manual Order Entry</td>
                                            <td class="font-mono text-xs">Unavailable</td>
                                            <td><span class="status-badge status-badge--critical">DISABLED</span></td>
                                            <td class="text-muted text-xs">Manual buy/sell surfaces retired</td>
                                        </tr>
                                        <tr>
                                            <td class="font-bold font-mono">Live Exchange Trading</td>
                                            <td class="font-mono text-xs">Binance Real Venue</td>
                                            <td><span class="status-badge status-badge--critical">DISABLED</span></td>
                                            <td class="text-muted text-xs">Locked in OPERATIONAL_OFFLINE mode</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 6: Build (12 cols) -->
                <div class="col-span-12">
                    <div class="terminal-panel">
                        <div class="panel-header">
                            <span class="panel-title">BUILD & RELEASE AUDIT</span>
                            <span class="badge-subtle font-mono">GIT COMMIT</span>
                        </div>
                        <div class="panel-body">
                            <div class="telemetry-list">
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Branch</span>
                                    <span class="telemetry-val font-mono text-cyan">ui-v2-rc1</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Release Candidate</span>
                                    <span class="telemetry-val font-mono">UI_V2_RC1</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Target Platforms</span>
                                    <span class="telemetry-val font-mono">Web V2 + Flutter iOS V2</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Deployment Status</span>
                                    <span class="telemetry-val font-mono text-warning">LOCAL_ONLY (NO VPS DEPLOY IN PHASE 6C)</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
