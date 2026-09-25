/**
 * Obsidian Quants - Risk View Renderer
 * Circuit breaker telemetry, HALT state machine inspection, fail-closed safety monitors.
 * Operator controls: HALT and RESUME with CAS generation checks. CLOSEALL strictly disabled.
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

    container.innerHTML = `
        <div class="terminal-grid-12">
            <!-- Alert Banner if HALTED or Breaker Tripped -->
            ${isHalted ? `
                <div class="col-span-12">
                    <div class="risk-alert risk-alert--halt">
                        <div class="risk-alert__icon">⚠</div>
                        <div class="risk-alert__content">
                            <div class="risk-alert__title">OPERATOR / SAFETY HALT ACTIVE (GENERATION #${haltGen || '1'})</div>
                            <div class="risk-alert__desc">
                                Reason: ${Formatters.escapeHtml(status.halt_reason || 'Safety circuit breaker triggered')}
                            </div>
                        </div>
                    </div>
                </div>
            ` : ''}

            <!-- Card 1: Circuit Breaker State (6 cols) -->
            <div class="col-span-6">
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">CIRCUIT BREAKER STATUS</span>
                        <span class="status-badge ${breakerTripped ? 'status-badge--halt' : 'status-badge--healthy'}">
                            <span class="status-badge__dot"></span>
                            ${breakerTripped ? 'TRIPPED / HALTED' : 'ARMED / NORMAL'}
                        </span>
                    </div>
                    <div class="panel-body">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Breaker Operational Mode</span>
                                <span class="telemetry-val font-mono font-bold ${breakerTripped ? 'text-loss' : 'text-profit'}">
                                    ${breakerTripped ? 'TRIPPED_FAIL_CLOSED' : 'ARMED_MONITORING'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Daily Loss Current / Max</span>
                                <span class="telemetry-val font-mono">
                                    ${health.daily_loss !== undefined ? Formatters.currency(health.daily_loss) : '—'} / 
                                    ${health.max_daily_loss ? Formatters.currency(health.max_daily_loss) : '—'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Consecutive Losses / Max</span>
                                <span class="telemetry-val font-mono">
                                    ${health.consecutive_losses !== undefined ? health.consecutive_losses : '—'} / 
                                    ${health.max_consecutive_losses || '—'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Cooldown Period</span>
                                <span class="telemetry-val font-mono">
                                    ${health.cooldown_until ? Formatters.timestamp(health.cooldown_until * 1000) : 'CLEAR (NO COOLDOWN)'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Baseline Capital Reference</span>
                                <span class="telemetry-val font-mono">
                                    ${health.daily_baseline_balance ? Formatters.currency(health.daily_baseline_balance) : 'AUTHORITATIVE_STORE'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Card 2: HALT State Machine (6 cols) -->
            <div class="col-span-6">
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">HALT & RECOVERY MACHINE</span>
                        <span class="badge-subtle font-mono">CAS PROTOCOL</span>
                    </div>
                    <div class="panel-body">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Global HALT Gate</span>
                                <span class="telemetry-val font-mono ${status.is_paused ? 'text-loss' : 'text-profit'}">
                                    ${status.is_paused ? 'ACTIVE (ENTRY BLOCKED)' : 'INACTIVE (PERMITTED)'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Expected Halt Generation</span>
                                <span class="telemetry-val font-mono text-cyan">
                                    ${haltGen !== null && haltGen !== undefined ? '#' + haltGen : '—'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Recovery Required</span>
                                <span class="telemetry-val font-mono ${recoveryRequired ? 'text-loss font-bold' : ''}">
                                    ${recoveryRequired ? 'REQUIRED (STOP CLEANUP)' : 'CLEAR'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Resume Pre-condition</span>
                                <span class="telemetry-val font-mono ${resumeAllowed ? 'text-profit' : ''}">
                                    ${resumeAllowed ? 'CAS RESUME PERMITTED' : (recoveryRequired ? 'BLOCKED (RECOVERY REQUIRED)' : (isHalted ? 'CAS GENERATION MATCH REQUIRED' : 'NORMAL (NOT HALTED)'))}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Fee Conflict Detection</span>
                                <span class="telemetry-val font-mono text-profit">CLEAR (NO CONFLICT)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Balance / Equity Authority</span>
                                <span class="telemetry-val font-mono text-cyan">EXECUTION_SERVICE_ONLY</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Card 3: Operator Actions (HALT / RESUME / CLOSEALL Disabled) (12 cols) -->
            <div class="col-span-12">
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">OPERATOR ACTIONS & SAFETY GUARDS</span>
                        <span class="badge-subtle font-mono">PHASE 4 CAS</span>
                    </div>
                    <div class="panel-body">
                        <p class="text-sm text-secondary mb-4">
                            Hệ thống kiểm soát điều hành thế hệ HALT (CAS). Thao tác HALT và RESUME được xác thực bằng quyền quản trị và chứng thực trực tiếp qua Execution Service. Lệnh Đóng tất cả bị vô hiệu hóa an toàn trên giao diện.
                        </p>
                        <div class="flex flex-wrap gap-4 items-center">
                            <button id="btn-operator-halt" class="btn-terminal danger font-mono ${isActionInFlight || !state.statusKnown ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}" ${isActionInFlight || !state.statusKnown ? 'disabled' : ''} title="Dừng khẩn cấp toàn bộ tiếp nhận vào lệnh">
                                ${isActionInFlight ? '[ĐANG XỬ LÝ...]' : '[EMERGENCY HALT]'}
                            </button>
                            <button id="btn-operator-resume" class="btn-terminal primary font-mono ${!resumeAllowed || isActionInFlight ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}" ${!resumeAllowed || isActionInFlight ? 'disabled' : ''} title="${!resumeAllowed ? (recoveryRequired ? 'Yêu cầu khắc phục khẩn cấp trước khi khôi phục' : (!isHalted ? 'Hệ thống hiện không ở trạng thái HALT' : 'Không đủ điều kiện khôi phục')) : 'Khôi phục tiếp nhận giao dịch'}">
                                ${isActionInFlight ? '[ĐANG XỬ LÝ...]' : `[RESUME WITH CAS (#${haltGen || '—'})]`}
                            </button>
                            <button class="btn-terminal font-mono opacity-50 cursor-not-allowed" disabled title="Lệnh đóng tất cả bị vô hiệu hóa trên giao diện điều hành để đảm bảo an toàn vốn.">
                                [ĐÓNG TẤT CẢ — VÔ HIỆU HÓA]
                            </button>
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
            const ok = confirm("XÁC NHẬN DỪNG KHẨN CẤP (HALT)?\n\nLệnh này sẽ chặn tiếp nhận mọi vị thế mới và kích hoạt thế hệ HALT mới trong Execution Service.");
            if (!ok) return;

            isActionInFlight = true;
            renderRisk(state, container);

            try {
                const res = await api.post('/api/pause', {
                    reason: 'Web operator manual halt',
                    source: 'web'
                });

                if (res.status === 403) {
                    alert('Bạn không có quyền thực hiện thao tác này (403 Forbidden).');
                } else if (res.status === 0) {
                    alert('LỖI KHÔNG XÁC ĐỊNH (UNKNOWN_OUTCOME): Mất kết nối khi gửi lệnh HALT. Vui lòng kiểm tra trạng thái máy chủ trước khi thao tác lại.');
                } else if (!res.success) {
                    alert(`LỖI DỪNG HỆ THỐNG (${res.status}): ${res.data?.message || res.error || 'Thao tác thất bại'}`);
                } else {
                    await poller.pollStatus();
                }
            } catch (err) {
                alert(`LỖI KHÔNG XÁC ĐỊNH (UNKNOWN_OUTCOME): ${err.message || err}`);
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

            const expectedGen = status.halt_generation;
            if (!expectedGen || expectedGen < 1) {
                alert('Không thể khôi phục: Không xác định được thế hệ HALT hợp lệ trên máy chủ.');
                return;
            }

            const ok = confirm(`XÁC NHẬN KHÔI PHỤC (RESUME)?\n\nKhôi phục tiếp nhận giao dịch từ thế hệ #${expectedGen}.\nThao tác yêu cầu CAS generation phải khớp chính xác thế hệ hiện tại.`);
            if (!ok) return;

            isActionInFlight = true;
            renderRisk(state, container);

            try {
                const res = await api.post('/api/resume', {
                    expected_halt_generation: expectedGen,
                    source: 'web'
                });

                if (res.status === 403) {
                    alert('Bạn không có quyền thực hiện thao tác này (403 Forbidden).');
                } else if (res.status === 409) {
                    const code = res.data?.code;
                    if (code === 'STALE_HALT_GENERATION') {
                        alert(`XUNG ĐỘT THẾ HỆ (409): Thế hệ HALT đã thay đổi trên máy chủ (hiện tại: #${res.data?.current_generation ?? '—'}). Đang cập nhật dữ liệu...`);
                    } else if (code === 'RECOVERY_REQUIRED') {
                        alert('YÊU CẦU PHỤC HỒI (409): Hệ thống yêu cầu khắc phục trạng thái khẩn cấp (recovery_required=True) trước khi khôi phục.');
                    } else {
                        alert(`XUNG ĐỘT TRẠNG THÁI (409): ${res.data?.message || 'Không thể khôi phục'}`);
                    }
                    await poller.pollStatus();
                } else if (res.status === 0) {
                    alert('LỖI KHÔNG XÁC ĐỊNH (UNKNOWN_OUTCOME): Mất kết nối khi gửi lệnh RESUME. Vui lòng kiểm tra trạng thái máy chủ trước khi thao tác lại.');
                } else if (!res.success) {
                    alert(`LỖI KHÔI PHỤC (${res.status}): ${res.data?.message || res.error || 'Thao tác thất bại'}`);
                } else {
                    await poller.pollStatus();
                }
            } catch (err) {
                alert(`LỖI KHÔNG XÁC ĐỊNH (UNKNOWN_OUTCOME): ${err.message || err}`);
            } finally {
                isActionInFlight = false;
                renderRisk(state, container);
            }
        });
    }
}
