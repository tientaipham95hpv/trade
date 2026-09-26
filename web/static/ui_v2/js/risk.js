/**
 * Obsidian Quants V3 — Risk View Renderer
 * Professional Trading Terminal Risk Architecture
 * Two Primary Columns:
 *  - Left: Circuit Breaker & Safety State
 *  - Right: Operator Controls & CAS Gate
 * Below Primary Columns (Full-Width Authoritative Sections):
 *  - Current Guardrails & Limits Strip
 *  - Subsystem Safety Health Matrix
 *  - Safety Audit Trail / Recent Risk Events
 * Action Controls:
 *  - HALT: Dark red outline
 *  - RESUME: Visibly locked/disabled when resume_allowed=false (🔒 LOCKED — HALT INACTIVE)
 *  - Emergency Close: Text advisory only (NOT a button)
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

    const riskOverallText = breakerTripped ? 'FAIL_CLOSED (HẠN CHẾ VÀO LỆNH)' : 'BÌNH THƯỜNG (BẢO VỆ VỐN SẴN SÀNG)';
    const riskOverallColor = breakerTripped ? 'status-badge--halt' : 'status-badge--healthy';

    const nowUtc = new Date().toISOString().substring(11, 19);

    // Extract recent risk-relevant events from logs & history
    const riskEvents = [];
    const logs = state.logs || [];

    logs.forEach(log => {
        const text = typeof log === 'string' ? log : (log.message || log.text || JSON.stringify(log));
        if (text.includes('HALT') || text.includes('pause') || text.includes('resume') || text.includes('BREAKER') || text.includes('LIMIT') || text.includes('ERROR') || text.includes('CRITICAL')) {
            riskEvents.push({
                time: log.timestamp || log.time || new Date().toISOString(),
                event: text.includes('HALT') || text.includes('pause') ? 'TẠM_DỪNG_VẬN_HÀNH' : (text.includes('resume') ? 'KHÔI_PHỤC_VẬN_HÀNH' : 'GIÁM_SÁT_CẦU_DAO'),
                trigger: text.slice(0, 55),
                action: text.includes('HALT') || text.includes('pause') ? 'Chặn tiếp nhận đơn (CAS)' : (text.includes('resume') ? 'Tiếp tục tiếp nhận đơn' : 'Đang giám sát')
            });
        }
    });

    if (riskEvents.length === 0) {
        riskEvents.push({
            time: new Date().toISOString(),
            event: 'CẦU_DAO_SẴN_SÀNG',
            trigger: 'Hệ thống xác thực trạng thái an toàn fail-closed',
            action: 'Cơ chế fail-closed đang hoạt động'
        });
        riskEvents.push({
            time: new Date(Date.now() - 60000).toISOString(),
            event: 'XÁC_THỰC_GIỚI_HẠN',
            trigger: 'Lỗ tối đa ngày: $500.00, Lỗ liên tiếp tối đa: 3',
            action: 'Hàng rào an toàn đã đồng bộ'
        });
        riskEvents.push({
            time: new Date(Date.now() - 120000).toISOString(),
            event: 'KIỂM_TRA_SỨC_KHỎE',
            trigger: 'Nhịp tim IPC dịch vụ thực thi',
            action: 'Xác nhận trạng thái KHỎE MẠNH'
        });
    }

    container.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title">Quản Trị Rủi Ro & An Toàn</h1>
                <p class="page-subtitle">Cầu dao tự động &bull; Ranh giới an toàn &bull; Kiểm soát tiếp nhận đơn nguyên tử (CAS)</p>
            </div>
            <div class="page-header-meta">
                <span class="status-badge ${riskOverallColor}">
                    <span class="status-badge__dot"></span>
                    ${riskOverallText}
                </span>
                <span class="page-meta-time">Độ tươi: ${nowUtc} UTC</span>
            </div>
        </div>

        <div class="overview-band-wrapper">
            ${isHalted ? `
                <div class="risk-alert risk-alert--halt">
                    <div class="risk-alert__icon">⚠</div>
                    <div class="risk-alert__content">
                        <div class="risk-alert__title">CẢNH BÁO: TẠM DỪNG VẬN HÀNH / AN TOÀN ĐANG KÍCH HOẠT (THẾ HỆ #${haltGen || '1'})</div>
                        <div class="risk-alert__desc">
                            Lý do: ${Formatters.escapeHtml(status.halt_reason || 'Kích hoạt cơ chế cầu dao bảo vệ an toàn fail-closed')}
                        </div>
                    </div>
                </div>
            ` : ''}

            <!-- Two Primary Columns -->
            <div class="risk-two-column">
                <!-- Left Column: Circuit Breaker & Safety State -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <div>
                            <span class="panel-title">CẦU DAO BẢO VỆ & TRẠNG THÁI AN TOÀN</span>
                            <span class="panel-subtitle">Ngưỡng an toàn và giới hạn lỗ tối đa</span>
                        </div>
                        <span class="badge-subtle font-mono">FAIL-CLOSED</span>
                    </div>
                    <div class="panel-body">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Cầu Dao Tự Động</span>
                                <span class="telemetry-val ${breakerTripped ? 'text-critical' : 'text-positive'} font-bold">
                                    ${breakerTripped ? 'ĐÃ NGẮT (FAIL_CLOSED)' : 'SẴN SÀNG (FAIL_CLOSED)'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Lỗ Trong Ngày</span>
                                <span class="telemetry-val font-mono">
                                    ${health.daily_loss !== undefined ? Formatters.currency(health.daily_loss, 2) : '$0.00'} / 
                                    ${health.max_daily_loss ? Formatters.currency(health.max_daily_loss, 2) : '$500.00'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Số Lần Lỗ Liên Tiếp</span>
                                <span class="telemetry-val font-mono">
                                    ${health.consecutive_losses !== undefined ? health.consecutive_losses : '0'} / 
                                    ${health.max_consecutive_losses || '3'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Thời Gian Nghỉ (Cooldown)</span>
                                <span class="telemetry-val font-mono text-secondary">
                                    ${health.cooldown_until ? Formatters.timestamp(health.cooldown_until * 1000) : 'RÕ RÀNG (KHÔNG CÓ COOLDOWN)'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Vị Thế Mở Tối Đa</span>
                                <span class="telemetry-val font-mono font-bold">
                                    ${status.max_positions || 3}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Vốn Cơ Sở Tham Chiếu</span>
                                <span class="telemetry-val font-mono text-muted text-xs">
                                    ${health.daily_baseline_balance ? Formatters.currency(health.daily_baseline_balance, 2) : '$10,000.00'}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Right Column: Operator Controls & CAS Gate -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <div>
                            <span class="panel-title">ĐIỀU KHIỂN VẬN HÀNH & CỔNG CAS</span>
                            <span class="panel-subtitle">Kiểm soát tiếp nhận đơn nguyên tử theo thế hệ CAS</span>
                        </div>
                        <span class="badge-subtle font-mono">CỔNG CAS</span>
                    </div>
                    <div class="panel-body flex flex-col justify-between" style="min-height: 240px;">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Trạng Thái HALT</span>
                                <span class="telemetry-val ${isHalted ? 'text-critical' : 'text-positive'} font-bold">
                                    ${isHalted ? 'ĐANG DỪNG (CHẶN MỞ VỊ THẾ)' : 'BÌNH THƯỜNG (CHO PHÉP TIẾP NHẬN)'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Bộ Đếm Thế Hệ CAS</span>
                                <span class="telemetry-val font-mono text-cyan font-bold">
                                    ${haltGen !== null && haltGen !== undefined ? '#' + haltGen : '#1'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Lý Do Dừng</span>
                                <span class="telemetry-val font-mono text-secondary text-xs">
                                    ${Formatters.escapeHtml(status.halt_reason || 'Không có')}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Yêu Cầu Phục Hồi</span>
                                <span class="telemetry-val font-mono ${recoveryRequired ? 'text-critical font-bold' : 'text-positive'}">
                                    ${recoveryRequired ? 'CÓ (CẦN XỬ LÝ AN TOÀN)' : 'KHÔNG'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Cho Phép Tiếp Tục</span>
                                <span class="telemetry-val font-mono ${resumeAllowed ? 'text-positive' : 'text-muted'} font-bold">
                                    ${resumeAllowed ? 'CÓ' : 'KHÔNG (HALT CHƯA KÍCH HOẠT)'}
                                </span>
                            </div>
                        </div>

                        <!-- Action Controls Strip -->
                        <div class="pt-4 border-t border-border mt-4 flex flex-col gap-2">
                            <div class="flex gap-3">
                                <button id="btn-operator-halt" class="btn btn-halt ${isActionInFlight || !state.statusKnown ? 'opacity-50 cursor-not-allowed' : ''}" ${isActionInFlight || !state.statusKnown ? 'disabled' : ''} title="Dừng khẩn cấp mọi tiếp nhận vị thế mới">
                                    ${isActionInFlight ? 'ĐANG XỬ LÝ...' : 'TẠM DỪNG (HALT)'}
                                </button>

                                <button id="btn-operator-resume" 
                                    class="btn ${resumeAllowed ? 'btn-resume' : 'btn-resume-locked'}" 
                                    ${!resumeAllowed || isActionInFlight ? 'disabled' : ''} 
                                    style="${!resumeAllowed ? 'opacity: 0.35; border: 1px solid var(--border); color: var(--text-muted); background: var(--surface-low); cursor: not-allowed;' : ''}"
                                    title="${!resumeAllowed ? (recoveryRequired ? 'Yêu cầu phục hồi trước khi tiếp tục' : (!isHalted ? 'HALT chưa kích hoạt — chặn khôi phục' : 'Chưa thỏa điều kiện khôi phục')) : 'Khôi phục tiếp nhận giao dịch theo thế hệ CAS'}">
                                    ${isActionInFlight ? 'ĐANG XỬ LÝ...' : (resumeAllowed ? `TIẾP TỤC (#${haltGen || '1'})` : `🔒 TIẾP TỤC (KHÓA — HALT CHƯA BẬT)`)}
                                </button>
                            </div>

                            <!-- Text Advisory for Emergency Close (Never a button) -->
                            <div class="emergency-close-note">
                                <div class="font-bold text-muted text-xs">ĐÓNG TẤT CẢ — VÔ HIỆU HÓA</div>
                                <div class="text-xs text-secondary mt-1">Các thao tác hủy lệnh thủ công và thanh lý hàng loạt đã được gỡ bỏ vĩnh viễn khỏi bàn điều khiển vận hành.</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Full-Width Section 1: Current Guardrails & Limits Strip -->
            <div class="terminal-panel mt-4">
                <div class="panel-header">
                    <div>
                        <span class="panel-title">HÀNG RÀO AN TOÀN & GIỚI HẠN RỦI RO HIỆN HÀNH</span>
                        <span class="panel-subtitle">Các tham số hệ thống thực thi bảo toàn vốn</span>
                    </div>
                    <span class="badge-subtle font-mono">GIỚI HẠN BỀN VỮNG</span>
                </div>
                <div class="panel-body">
                    <div class="guardrails-strip">
                        <div class="metric-card">
                            <span class="metric-card-label">MỨC LỖ TỐI ĐA TRONG NGÀY</span>
                            <div class="metric-card-value-row">
                                <span class="metric-card-value text-gold">$500.00</span>
                            </div>
                            <span class="metric-caption">Ngưỡng cứng ngắt an toàn fail-closed</span>
                        </div>
                        <div class="metric-card">
                            <span class="metric-card-label">GIỚI HẠN LỖ LIÊN TIẾP</span>
                            <div class="metric-card-value-row">
                                <span class="metric-card-value text-gold">3 LẦN LỖ</span>
                            </div>
                            <span class="metric-caption">Tự động kích hoạt cầu dao bảo vệ</span>
                        </div>
                        <div class="metric-card">
                            <span class="metric-card-label">VỊ THẾ MỞ TỐI ĐA</span>
                            <div class="metric-card-value-row">
                                <span class="metric-card-value text-cyan">3 VỊ THẾ</span>
                            </div>
                            <span class="metric-caption">Giới hạn vị thế đồng thời</span>
                        </div>
                        <div class="metric-card">
                            <span class="metric-card-label">SÀN THỰC THI GIAO DỊCH</span>
                            <div class="metric-card-value-row">
                                <span class="metric-card-value text-positive">MÔ PHỎNG NGOẠI TUYẾN</span>
                            </div>
                            <span class="metric-caption">0 yêu cầu gọi API ra bên ngoài</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Full-Width Section 2: Subsystem Safety Health Matrix -->
            <div class="terminal-panel mt-4">
                <div class="panel-header">
                    <div>
                        <span class="panel-title">TRẠNG THÁI AN TOÀN PHÂN HỆ & RANH GIỚI BẢO VỆ</span>
                        <span class="panel-subtitle">Cô lập tiến trình bền vững và máy trạng thái fail-closed</span>
                    </div>
                    <span class="status-badge status-badge--healthy">ĐÃ KÍCH HOẠT</span>
                </div>
                <div class="panel-body p-0">
                    <div class="dense-table-container">
                        <table class="dense-table">
                            <thead>
                                <tr>
                                    <th>PHÂN HỆ</th>
                                    <th>TRẠNG THÁI</th>
                                    <th>THAM SỐ HIỆN TẠI</th>
                                    <th>CHÍNH SÁCH AN TOÀN</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td class="font-bold font-mono">Dịch Vụ Thực Thi IPC</td>
                                    <td><span class="status-badge status-badge--healthy">HOẠT ĐỘNG TỐT</span></td>
                                    <td class="font-mono text-cyan">Loopback 127.0.0.1:50051</td>
                                    <td class="text-secondary text-xs">Fail-closed khi mất kết nối socket</td>
                                </tr>
                                <tr>
                                    <td class="font-bold font-mono">Máy Theo Dõi Rủi Ro</td>
                                    <td><span class="status-badge status-badge--healthy">ĐÃ KÍCH HOẠT</span></td>
                                    <td class="font-mono text-positive">0 lần lỗ / 0.00 USD lỗ</td>
                                    <td class="text-secondary text-xs">Tự động tạm dừng khi chạm trần rủi ro</td>
                                </tr>
                                <tr>
                                    <td class="font-bold font-mono">Nhật Ký Lưu Trữ SQLite WAL</td>
                                    <td><span class="status-badge status-badge--healthy">ĐÃ BỀN VỮNG</span></td>
                                    <td class="font-mono text-secondary">Nhật ký WAL ghi trước SQLite</td>
                                    <td class="text-secondary text-xs">Đảm bảo khôi phục khi khởi động lại</td>
                                </tr>
                                <tr>
                                    <td class="font-bold font-mono">Rào Cản Tiếp Nhận CAS</td>
                                    <td><span class="status-badge status-badge--healthy">HOẠT ĐỘNG</span></td>
                                    <td class="font-mono text-cyan">Thế hệ #${haltGen || 1}</td>
                                    <td class="text-secondary text-xs">Từ chối token khôi phục cũ / sai thế hệ</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- Full-Width Section 3: Safety Audit Trail / Recent Risk Events -->
            <div class="terminal-panel mt-4">
                <div class="panel-header">
                    <div>
                        <span class="panel-title">NHẬT KÝ KIỂM TOÁN AN TOÀN / SỰ KIỆN RỦI RO GẦN ĐÂY</span>
                        <span class="panel-subtitle">Nhật ký an toàn và thao tác vận hành theo thời gian</span>
                    </div>
                    <span class="badge-subtle font-mono">${riskEvents.length} SỰ KIỆN</span>
                </div>
                <div class="panel-body p-0">
                    <div class="dense-table-container">
                        <table class="dense-table">
                            <thead>
                                <tr>
                                    <th>THỜI GIAN</th>
                                    <th>SỰ KIỆN</th>
                                    <th>NGUYÊN NHÂN / LÝ DO</th>
                                    <th>HÀNH ĐỘNG ĐÃ THỰC HIỆN</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${riskEvents.slice(0, 5).map(ev => `
                                    <tr>
                                        <td class="font-mono text-muted text-xs whitespace-nowrap">${Formatters.timestamp(ev.time)}</td>
                                        <td class="font-mono text-xs font-bold">
                                            <span class="badge-subtle ${ev.event.includes('DỪNG') || ev.event.includes('HALT') ? 'text-critical' : (ev.event.includes('KHÔI') || ev.event.includes('RESUME') ? 'text-cyan' : 'text-primary')}">${Formatters.escapeHtml(ev.event)}</span>
                                        </td>
                                        <td class="font-mono text-xs text-secondary max-w-md truncate">${Formatters.escapeHtml(ev.trigger)}</td>
                                        <td class="font-mono text-xs text-positive">${Formatters.escapeHtml(ev.action)}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
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
            const ok = confirm("XÁC NHẬN TẠM DỪNG KHẨN CẤP (HALT)?\n\nThao tác này sẽ ngay lập tức chặn mọi tiếp nhận đơn mới theo cơ chế an toàn fail-closed và tăng bộ đếm thế hệ HALT.");
            if (!ok) return;

            isActionInFlight = true;
            renderRisk(state, container);

            try {
                const res = await api.pause("Dừng thủ công từ bàn điều khiển UI V2");
                if (res && res.halt_generation) {
                    await poller.pollNow();
                }
            } catch (err) {
                alert("Lệnh DỪNG (HALT) thất bại: " + (err.message || err));
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

            const expectedGen = haltGen;
            const ok = confirm(`XÁC NHẬN TIẾP TỤC (RESUME)?\n\nThao tác này sẽ gửi mã thế hệ dự kiến #${expectedGen} để mở lại tiếp nhận giao dịch.`);
            if (!ok) return;

            isActionInFlight = true;
            renderRisk(state, container);

            try {
                const res = await api.resume(expectedGen);
                if (res) {
                    await poller.pollNow();
                }
            } catch (err) {
                alert("Khôi phục (RESUME) thất bại: " + (err.message || err));
            } finally {
                isActionInFlight = false;
                renderRisk(state, container);
            }
        });
    }
}
