/**
 * Obsidian Quants - System & Governance View Renderer
 * Read-only architecture specification, feature availability, core certification status.
 */

import { Formatters } from './formatters.js';

export function renderSystem(state, container) {
    if (!container) return;

    const status = state.status || {};

    container.innerHTML = `
        <div class="terminal-grid-12">
            <!-- Section 1: Core Certification & Environment (6 cols) -->
            <div class="col-span-6">
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">CORE CERTIFICATION & RUNTIME</span>
                        <span class="status-badge status-badge--healthy">
                            <span class="status-badge__dot"></span>
                            OFFLINE ACCEPTED
                        </span>
                    </div>
                    <div class="panel-body">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Execution Core Status</span>
                                <span class="telemetry-val font-mono text-cyan font-bold">
                                    OFFLINE EXECUTION CORE ACCEPTED
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Core Integrity Hash</span>
                                <span class="telemetry-val font-mono text-xs text-primary">
                                    15/15 PRESERVED (0 MISMATCH)
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Runtime Environment</span>
                                <span class="telemetry-val font-mono text-cyan font-bold">
                                    OPERATIONAL_OFFLINE
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Venue Mutation Target</span>
                                <span class="telemetry-val font-mono">OFFLINE_MOCK_VENUE (ZERO EXCHANGE CALLS)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Supervisor Process</span>
                                <span class="telemetry-val font-mono">trader-stack-offline.service</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section 2: Security & Authority Architecture (6 cols) -->
            <div class="col-span-6">
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">AUTHORITY BOUNDARIES</span>
                        <span class="badge-subtle font-mono">PROCESS ISOLATION</span>
                    </div>
                    <div class="panel-body">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Web IPC Authority</span>
                                <span class="telemetry-val font-mono text-cyan">Bearer Loopback (127.0.0.1:50051)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Web Direct Exchange Calls</span>
                                <span class="telemetry-val font-mono text-profit">ZERO (PROHIBITED)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Direct DB Trade Execution</span>
                                <span class="telemetry-val font-mono text-profit">ZERO (SERVICE PID ONLY)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Client Credentials</span>
                                <span class="telemetry-val font-mono text-muted">REMOVED / NON-EXTRACTABLE</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Browser Auth Transport</span>
                                <span class="telemetry-val font-mono">HttpOnly SameSite Cookie</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Section 3: Feature Availability Grid (12 cols) -->
            <div class="col-span-12">
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">FEATURE GOVERNANCE & AVAILABILITY MATRIX</span>
                        <span class="panel-badge font-mono">FAIL-CLOSED</span>
                    </div>
                    <div class="panel-body p-0">
                        <div class="dense-table-container">
                            <table class="dense-table">
                                <thead>
                                    <tr>
                                        <th>FEATURE SUBSYSTEM</th>
                                        <th>STATUS</th>
                                        <th>GOVERNANCE RULE</th>
                                        <th>AUTHORITY SCOPE</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td class="font-mono font-bold">Client Credential Authority</td>
                                        <td><span class="status-badge status-badge--degraded font-mono">REMOVED</span></td>
                                        <td class="text-secondary">Binance API keys permanently purged; no storage or UI forms</td>
                                        <td class="font-mono text-xs">NONE</td>
                                    </tr>
                                    <tr>
                                        <td class="font-mono font-bold">Copy-Trade Engine</td>
                                        <td><span class="status-badge status-badge--degraded font-mono">DISABLED</span></td>
                                        <td class="text-secondary">Copy trading disabled in OFFLINE mode; endpoints return FEATURE_DISABLED</td>
                                        <td class="font-mono text-xs">NONE</td>
                                    </tr>
                                    <tr>
                                        <td class="font-mono font-bold">AI Copilot / Autonomous Trader</td>
                                        <td><span class="status-badge status-badge--degraded font-mono">NOT ENABLED</span></td>
                                        <td class="text-secondary">AI possesses zero autonomous order placement authority</td>
                                        <td class="font-mono text-xs">ADVISORY ONLY</td>
                                    </tr>
                                    <tr>
                                        <td class="font-mono font-bold">Market Scanner Control</td>
                                        <td><span class="status-badge status-badge--degraded font-mono">DISABLED</span></td>
                                        <td class="text-secondary">External market scanners inactive during OFFLINE operation</td>
                                        <td class="font-mono text-xs">OFFLINE</td>
                                    </tr>
                                    <tr>
                                        <td class="font-mono font-bold">Binance Testnet Routing</td>
                                        <td><span class="status-badge status-badge--degraded font-mono">DISABLED</span></td>
                                        <td class="text-secondary">Testnet exchange mutations disabled in OFFLINE mode</td>
                                        <td class="font-mono text-xs">ISOLATED</td>
                                    </tr>
                                    <tr>
                                        <td class="font-mono font-bold">Binance Live Production</td>
                                        <td><span class="status-badge status-badge--degraded font-mono">DISABLED</span></td>
                                        <td class="text-secondary">Live exchange mutations strictly disabled</td>
                                        <td class="font-mono text-xs">PROHIBITED</td>
                                    </tr>
                                    <tr>
                                        <td class="font-mono font-bold">Manual Trade (BUY/SELL) Entry</td>
                                        <td><span class="status-badge status-badge--degraded font-mono">PROHIBITED</span></td>
                                        <td class="text-secondary">Web/Mobile UI has zero manual order entry controls</td>
                                        <td class="font-mono text-xs">REMOVED</td>
                                    </tr>
                                    <tr>
                                        <td class="font-mono font-bold">Emergency Circuit Breaker</td>
                                        <td><span class="status-badge status-badge--healthy font-mono">ACTIVE</span></td>
                                        <td class="text-secondary">Loss threshold, consecutive failure, and cooldown triggers active</td>
                                        <td class="font-mono text-xs">EXECUTION_CORE</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
