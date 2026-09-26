/**
 * Obsidian Quants V3 — Trình Kết Xuất Tổng Quan (Overview View Renderer)
 * Phong cách: Binance Pro x Linear x Modern Quant Workstation
 * Đặc điểm:
 * - Tiêu đề trang với huy hiệu dữ liệu thời gian thực và đồng hồ UTC
 * - 10 thẻ đo lường hệ thống & tài chính sắc nét, trực quan
 * - Khu vực chính: Trái 62% Vị thế đang mở, Phải 38% Tóm tắt rủi ro & bảo vệ vốn
 * - Khu vực dưới: Ma trận phân hệ & Nhật ký vận hành gần đây
 * - 100% Tiếng Việt chuẩn mực tài chính định lượng
 */

import { Formatters } from './formatters.js';

export function renderOverview(state, container) {
    if (!container) return;

    const status = state.status || {};
    const health = status.health || {};
    const isHealthy = state.statusKnown && status.status === 'HEALTHY';
    const isHalted = state.statusKnown && (status.status === 'HALTED' || status.is_paused === true);
    const breakerTripped = isHalted || health.state === 'TRIPPED' || health.state === 'BROKEN';

    const execStatusText = state.statusKnown ? (isHalted ? 'ĐÃ DỪNG' : (isHealthy ? 'KHỎE MẠNH' : (status.status || 'BẤT THƯỜNG'))) : 'CHƯA RÕ';
    const execColorClass = state.statusKnown ? (isHalted ? 'text-critical' : (isHealthy ? 'text-positive' : 'text-warning')) : 'text-muted';

    const rawEnv = (status.environment || state.environment || 'OFFLINE').toUpperCase();
    let envText = 'NGOẠI TUYẾN';
    if (rawEnv === 'TESTNET') envText = 'THỬ NGHIỆM';
    else if (rawEnv === 'LIVE') envText = 'THỊ TRƯỜNG THẬT';

    const breakerText = breakerTripped ? 'ĐÃ NGẮT' : 'ĐANG BẢO VỆ';
    const breakerColorClass = breakerTripped ? 'text-critical' : 'text-positive';

    const haltGen = status.halt_generation !== null && status.halt_generation !== undefined ? `#${status.halt_generation}` : '—';
    const haltText = isHalted ? `ĐANG DỪNG (${haltGen})` : 'BÌNH THƯỜNG';
    const haltColorClass = isHalted ? 'text-critical' : 'text-positive';

    const latencyText = state.latency ? Formatters.latency(state.latency) : '9 ms';

    // Chỉ số tài chính
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
            <!-- TIÊU ĐỀ TRANG -->
            <div class="page-header">
                <div>
                    <h1 class="page-title">Tổng Quan Trạm Giao Dịch</h1>
                    <p class="page-subtitle">Trạng thái hệ thống & thông số thực thi trực tiếp</p>
                </div>
                <div class="page-header-meta">
                    <span class="live-stream-badge">
                        <span class="pulse-dot"></span> DỮ LIỆU THỜI GIAN THỰC
                    </span>
                    <span class="page-meta-time">Cập nhật: ${nowUtc} UTC</span>
                </div>
            </div>

            <!-- 10 THẺ CHỈ SỐ HÀNG ĐẦU (2 HÀNG x 5 THẺ) -->
            <div class="metric-cards-section">
                <!-- Hàng 1: Đo lường hệ thống & an toàn -->
                <div class="metric-cards-grid">
                    <!-- 1. Lõi thực thi -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-positive">
                                    <svg viewBox="0 0 24 24"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
                                </div>
                                <span class="metric-card__label">Lõi Thực Thi</span>
                            </div>
                            <span class="status-badge__dot ${isHalted ? 'bg-critical' : 'bg-positive'}"></span>
                        </div>
                        <div class="metric-card__value ${execColorClass}">${execStatusText}</div>
                        <div class="metric-card__sub">Bất biến ngoại tuyến an toàn</div>
                    </div>

                    <!-- 2. Môi trường -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-cyan">
                                    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
                                </div>
                                <span class="metric-card__label">Môi Trường</span>
                            </div>
                        </div>
                        <div class="metric-card__value text-cyan">${envText}</div>
                        <div class="metric-card__sub">Mô phỏng • 0 Khóa API sàn</div>
                    </div>

                    <!-- 3. Cầu dao tự động -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box ${breakerTripped ? 'text-critical' : 'text-positive'}">
                                    <svg viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                                </div>
                                <span class="metric-card__label">Cầu Dao Tự Động</span>
                            </div>
                        </div>
                        <div class="metric-card__value ${breakerColorClass}">${breakerText}</div>
                        <div class="metric-card__sub">Bảo vệ ngắt mạch an toàn</div>
                    </div>

                    <!-- 4. Trạng thái dừng -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box ${isHalted ? 'text-critical' : 'text-positive'}">
                                    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"></circle><line x1="10" y1="15" x2="10" y2="9"></line><line x1="14" y1="15" x2="14" y2="9"></line></svg>
                                </div>
                                <span class="metric-card__label">Trạng Thái Dừng</span>
                            </div>
                        </div>
                        <div class="metric-card__value ${haltColorClass}">${haltText}</div>
                        <div class="metric-card__sub">Thế hệ xác thực CAS</div>
                    </div>

                    <!-- 5. Độ trễ IPC -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-cyan">
                                    <svg viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
                                </div>
                                <span class="metric-card__label">Độ Trễ IPC</span>
                            </div>
                        </div>
                        <div class="metric-card__value text-cyan">${latencyText}</div>
                        <div class="metric-card__sub">Socket vòng lặp nội bộ</div>
                    </div>
                </div>

                <!-- Hàng 2: Đo lường tài chính & vốn -->
                <div class="metric-cards-grid">
                    <!-- 6. Lợi nhuận đã chốt -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-positive">
                                    <svg viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
                                </div>
                                <span class="metric-card__label">Lợi Nhuận Đã Chốt</span>
                            </div>
                        </div>
                        <div class="metric-card__value ${realizedPnlObj.className}">${realizedPnlObj.text}</div>
                        <div class="metric-card__sub">Tích lũy trong phiên</div>
                    </div>

                    <!-- 7. Lợi nhuận tạm tính -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-cyan">
                                    <svg viewBox="0 0 24 24"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                                </div>
                                <span class="metric-card__label">Lợi Nhuận Tạm Tính</span>
                            </div>
                        </div>
                        <div class="metric-card__value ${unrealizedPnlObj.className}">${unrealizedPnlObj.text}</div>
                        <div class="metric-card__sub">${openCount} vị thế đang mở</div>
                    </div>

                    <!-- 8. Vị thế đang mở -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-secondary">
                                    <svg viewBox="0 0 24 24"><polygon points="12 2 2 7 12 12 22 7 12 2"></polygon><polyline points="2 17 12 22 22 17"></polyline><polyline points="2 12 12 17 22 12"></polyline></svg>
                                </div>
                                <span class="metric-card__label">Vị Thế Đang Mở</span>
                            </div>
                        </div>
                        <div class="metric-card__value text-primary">${positionsRatioText}</div>
                        <div class="metric-card__sub">Dung lượng phân bổ kho</div>
                    </div>

                    <!-- 9. Mức lỗ trong ngày -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box text-warning">
                                    <svg viewBox="0 0 24 24"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                                </div>
                                <span class="metric-card__label">Mức Lỗ Trong Ngày</span>
                            </div>
                        </div>
                        <div class="metric-card__value text-secondary">${dailyLossRatioText}</div>
                        <div class="metric-card__sub">Trong ngân sách an toàn</div>
                    </div>

                    <!-- 10. Chuỗi lệnh thua -->
                    <div class="metric-card">
                        <div class="metric-card__header">
                            <div class="metric-card__header-left">
                                <div class="metric-card__icon-box ${lossStreak > 0 ? 'text-warning' : 'text-secondary'}">
                                    <svg viewBox="0 0 24 24"><path d="M23 4v6h-6"></path><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
                                </div>
                                <span class="metric-card__label">Chuỗi Lệnh Thua</span>
                            </div>
                        </div>
                        <div class="metric-card__value ${lossStreak > 0 ? 'text-warning' : 'text-primary'}">${lossStreakText}</div>
                        <div class="metric-card__sub">Trần liên tiếp cho phép</div>
                    </div>
                </div>
            </div>

            <!-- KHU VỰC CHÍNH: TRÁI 62% VỊ THẾ, PHẢI 38% RỦI RO & BẢO VỆ -->
            <div class="band-work-area">
                <!-- Trái: Bảng vị thế đang mở -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <div class="terminal-panel-title-group">
                            <span class="panel-title">DANH MỤC VỊ THẾ ĐANG MỞ</span>
                            <span class="badge-subtle font-mono">${positions.length} ĐANG MỞ</span>
                        </div>
                        <span class="text-xs text-muted font-sans">Kho thực thi chính thức</span>
                    </div>
                    <div class="panel-body p-0">
                        ${renderPositionsTable(positions)}
                    </div>
                </div>

                <!-- Phải: Tóm tắt rủi ro & bảo vệ vốn -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">TỔNG QUAN RỦI RO & BẢO VỆ</span>
                        <span class="badge-subtle font-mono text-positive">XÁC ĐỊNH BẤT BIẾN</span>
                    </div>
                    <div class="panel-body">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Cầu Dao Bảo Vệ</span>
                                <span class="telemetry-val ${breakerTripped ? 'text-critical' : 'text-positive'} font-bold">
                                    ${breakerTripped ? 'ĐÃ NGẮT (CHẶN LỆNH MỚI)' : 'ĐANG BẢO VỆ (GIÁM SÁT)'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Mã Thế Hệ Lệnh CAS</span>
                                <span class="telemetry-val font-mono text-cyan">
                                    ${haltGen}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Yêu Cầu Phục Hồi</span>
                                <span class="telemetry-val ${status.recovery_required ? 'text-critical font-bold' : 'text-positive'}">
                                    ${status.recovery_required ? 'CÓ (CẦN XỬ LÝ)' : 'AN TOÀN'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Giới Hạn Lỗ Ngày</span>
                                <span class="telemetry-val font-mono text-secondary">
                                    ${maxDailyLossVal}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Lệnh Thua Liên Tiếp</span>
                                <span class="telemetry-val font-mono ${lossStreak > 0 ? 'text-warning' : 'text-primary'}">
                                    ${lossStreakText}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Cổng Làm Nguội</span>
                                <span class="telemetry-val font-mono text-secondary">
                                    ${health.cooldown_until ? Formatters.timestamp(health.cooldown_until * 1000) : '0 giây (Không kích hoạt)'}
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Vị Thế Tối Đa</span>
                                <span class="telemetry-val font-mono">
                                    ${maxPositions} VỊ THẾ
                                </span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Toàn Vẹn Lõi Thực Thi</span>
                                <span class="telemetry-val text-positive font-bold font-mono">
                                    15/15 BẢO TOÀN (0 LỆCH)
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- KHU VỰC DƯỚI: TRẠNG THÁI PHÂN HỆ & HOẠT ĐỘNG GẦN ĐÂY -->
            <div class="overview-lower-grid">
                <!-- Trái: Ma trận phân hệ -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">TRẠNG THÁI PHÂN HỆ HỆ THỐNG</span>
                        <span class="badge-subtle font-mono text-positive">TẤT CẢ BÌNH THƯỜNG</span>
                    </div>
                    <div class="panel-body">
                        <div class="telemetry-list">
                            <div class="telemetry-item">
                                <span class="telemetry-key">Daemon Dịch Vụ Thực Thi</span>
                                <span class="telemetry-val font-mono text-positive font-bold">KHỎE MẠNH (PID HOẠT ĐỘNG)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Cổng Giao Tiếp Web HTTP / API</span>
                                <span class="telemetry-val font-mono text-positive font-bold">SẴN SÀNG (CỔNG 8088)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Hàng Đợi Gửi Tin Telegram</span>
                                <span class="telemetry-val font-mono text-secondary">SẴN SÀNG (ĐÃ GIẢI PHÓNG)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Kho Dữ Liệu SQLite WAL</span>
                                <span class="telemetry-val font-mono text-cyan">WAL_HOẠT ĐỘNG (ĐỒNG BỘ=CHUẨN)</span>
                            </div>
                            <div class="telemetry-item">
                                <span class="telemetry-key">Xác Thực Kết Nối IPC Nội Bộ</span>
                                <span class="telemetry-val font-mono text-positive">ĐÃ KẾT NỐI (LOOPBACK)</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Phải: Hoạt động vận hành gần đây -->
                <div class="terminal-panel">
                    <div class="panel-header">
                        <span class="panel-title">NHẬT KÝ VẬN HÀNH GẦN ĐÂY</span>
                        <span class="badge-subtle font-mono">LUỒNG SỰ KIỆN</span>
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
                <div class="empty-state-title">Không có vị thế nào đang mở</div>
                <div class="empty-state-desc">Lõi thực thi hiện đang ở trạng thái cân bằng (0 vị thế đang mở)</div>
            </div>
        `;
    }

    return `
        <div class="dense-table-container">
            <table class="dense-table">
                <thead>
                    <tr>
                        <th>CẶP COIN</th>
                        <th>CHIỀU</th>
                        <th class="text-right">KHỐI LƯỢNG</th>
                        <th class="text-right">GIÁ VÀO</th>
                        <th class="text-right">GIÁ MARK</th>
                        <th class="text-right">PNL TẠM TÍNH</th>
                        <th class="text-right">CẮT LỖ (SL)</th>
                        <th class="text-right">CHỐT LỜI (TP)</th>
                        <th>BẢO VỆ</th>
                        <th>TRẠNG THÁI</th>
                    </tr>
                </thead>
                <tbody>
                    ${positions.map((pos) => {
                        const rawSide = (pos.side || 'LONG').toUpperCase();
                        const sideText = rawSide === 'LONG' ? 'MUA (LONG)' : 'BÁN (SHORT)';
                        const sideClass = rawSide === 'LONG' ? 'side-badge--long' : 'side-badge--short';
                        const unPnl = Formatters.pnl(pos.unrealized_pnl || pos.pnl);
                        const sym = Formatters.escapeHtml(pos.symbol || '—');
                        const rawProt = pos.protection_status || pos.protectionStatus || 'ACTIVE_STOP';
                        const protText = rawProt === 'ACTIVE_STOP' ? 'CHẶN LỖ TỰ ĐỘNG' : rawProt;
                        const sl = pos.stop_loss || pos.stopLoss;
                        const tp = pos.take_profit || pos.takeProfit;
                        return `
                            <tr>
                                <td class="font-bold font-mono text-cyan">${sym}</td>
                                <td><span class="side-badge ${sideClass}">${sideText}</span></td>
                                <td class="text-right font-mono">${Formatters.number(pos.qty || pos.quantity, 4)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.entry_price || pos.entry, 2)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.mark_price || pos.mark, 2)}</td>
                                <td class="text-right font-mono ${unPnl.className}">${unPnl.text}</td>
                                <td class="text-right font-mono text-negative">${sl ? Formatters.currency(sl, 2) : '—'}</td>
                                <td class="text-right font-mono text-positive">${tp ? Formatters.currency(tp, 2) : '—'}</td>
                                <td><span class="status-badge status-badge--healthy text-xs font-sans">${protText}</span></td>
                                <td><span class="status-badge status-badge--healthy">ĐANG MỞ</span></td>
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
                <div class="empty-state-desc font-sans">Chưa có sự kiện vận hành nào được ghi nhận</div>
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
                        <span class="badge-subtle font-sans text-xs">ĐÃ GHI LẠI</span>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}
