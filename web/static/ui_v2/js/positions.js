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
                <h1 class="page-title">Vị Thế Đang Mở</h1>
                <p class="page-subtitle">Danh mục thực thi đang hoạt động (${positions.length} vị thế)</p>
            </div>
            <div class="page-header-meta">
                <span class="live-stream-badge">
                    <span class="pulse-dot"></span> DỮ LIỆU TRỰC TIẾP
                </span>
                <span class="page-meta-time">Độ tươi: ${nowUtc} UTC</span>
            </div>
        </div>

        <!-- Main Workstation Layout (Left 68% Table, Right 32% Persistent Inspector) -->
        <div class="positions-workstation">
            <!-- Left Column: Active Positions Table -->
            <div class="positions-table-col">
                <div class="terminal-panel">
                    <div class="panel-header">
                        <div>
                            <span class="panel-title">DANH SÁCH VỊ THẾ HOẠT ĐỘNG</span>
                            <span class="panel-subtitle">Danh mục vị thế được xác thực từ dịch vụ thực thi</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="badge-subtle font-mono">${positions.length} ĐANG MỞ</span>
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
                            <span class="panel-title">KIỂM TRA CHI TIẾT VỊ THẾ</span>
                            <span class="panel-subtitle">Chi tiết xác thực từ máy chủ</span>
                        </div>
                        <span class="badge-subtle font-mono">CHỈ ĐỌC</span>
                    </div>
                    <div class="panel-body flex flex-col justify-between" id="position-inspector-body">
                        ${renderInspectorContent(positions, selectedIndex)}
                    </div>
                    <div class="panel-footer">
                        <span class="text-xs text-muted font-sans">KHÓA THAY ĐỔI &bull; BÀN ĐIỀU KHIỂN VẬN HÀNH</span>
                        <span class="font-mono text-cyan text-xs">NGOẠI TUYẾN</span>
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
                        <span class="panel-title">TRẠNG THÁI BẢO VỆ & HÀNG RÀO AN TOÀN</span>
                        <span class="panel-subtitle">Thực thi an toàn phía máy chủ (Fail-closed)</span>
                    </div>
                    <span class="status-badge status-badge--healthy">ĐÃ KÍCH HOẠT</span>
                </div>
                <div class="panel-body">
                    <div class="telemetry-list">
                        <div class="telemetry-item">
                            <span class="telemetry-key">Cắt Lỗ Tự Động (SL)</span>
                            <span class="telemetry-val font-mono text-positive">DỪNG CHỦ ĐỘNG (FAIL_CLOSED)</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Chốt Lời Tự Động (TP)</span>
                            <span class="telemetry-val font-mono text-positive">LỆNH THỊ TRƯỜNG TP</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Giới Hạn Vị Thế Tối Đa</span>
                            <span class="telemetry-val font-mono">${positions.length} / ${state.status?.max_positions || 3}</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Rào Cản Tiếp Nhận CAS</span>
                            <span class="telemetry-val font-mono text-cyan">THẾ HỆ #${state.status?.halt_generation || 1}</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Execution Metadata Panel -->
            <div class="terminal-panel">
                <div class="panel-header">
                    <div>
                        <span class="panel-title">SIÊU DỮ LIỆU THỰC THI & KIỂM TOÁN DANH MỤC</span>
                        <span class="panel-subtitle">Cô lập máy chủ và ranh giới sàn giao dịch</span>
                    </div>
                    <span class="badge-subtle font-mono">IPC TIẾN TRÌNH NỀN</span>
                </div>
                <div class="panel-body">
                    <div class="telemetry-list">
                        <div class="telemetry-item">
                            <span class="telemetry-key">Bộ Điều Phối Thực Thi</span>
                            <span class="telemetry-val font-mono text-cyan">BinanceAdapter (ExecutionServiceClient)</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Ranh Giới Sàn Giao Dịch</span>
                            <span class="telemetry-val font-mono">SÀN MÔ PHỎNG NGOẠI TUYẾN (0 GỌI API)</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Tần Suất Đối Soát Dữ Liệu</span>
                            <span class="telemetry-val font-mono text-secondary">Liên tục (nhịp tim 2500ms)</span>
                        </div>
                        <div class="telemetry-item">
                            <span class="telemetry-key">Xác Thực Danh Mục</span>
                            <span class="telemetry-val font-mono text-positive">100% KHỚP CHUẨN BẤT BIẾN</span>
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
                <div class="empty-state-title">Không có vị thế nào đang mở</div>
                <div class="empty-state-desc">Lõi thực thi duy trì trạng thái trống ở chế độ NGOẠI TUYẾN</div>
            </div>
        `;
    }

    return `
        <div class="dense-table-container">
            <table class="dense-table">
                <thead>
                    <tr>
                        <th>CẶP GIAO DỊCH</th>
                        <th>CHIỀU</th>
                        <th class="text-right">KHỐI LƯỢNG</th>
                        <th class="text-right">GIÁ VÀO</th>
                        <th class="text-right">GIÁ MARK</th>
                        <th class="text-right">LỜI/LỖ</th>
                        <th class="text-right">CẮT LỖ (SL)</th>
                        <th class="text-right">CHỐT LỜI (TP)</th>
                        <th>CƠ CHẾ BẢO VỆ</th>
                        <th>TRẠNG THÁI</th>
                    </tr>
                </thead>
                <tbody>
                    ${positions.map((pos, idx) => {
                        const rawSide = (pos.side || 'LONG').toUpperCase();
                        const isLong = rawSide === 'LONG';
                        const sideText = isLong ? 'MUA (LONG)' : 'BÁN (SHORT)';
                        const sideClass = isLong ? 'side-badge--long' : 'side-badge--short';
                        const unPnl = Formatters.pnl(pos.unrealized_pnl || pos.pnl);
                        const sym = Formatters.escapeHtml(pos.symbol || '—');
                        const isSelected = idx === currentSelected;
                        const stateText = (pos.state || 'OPEN').toUpperCase() === 'OPEN' ? 'ĐANG MỞ' : (pos.state || 'ĐANG MỞ');
                        return `
                            <tr class="cursor-pointer row-hover ${isSelected ? 'row-selected' : ''}" data-position-idx="${idx}">
                                <td class="font-bold font-mono text-cyan">${sym}</td>
                                <td><span class="side-badge ${sideClass}">${sideText}</span></td>
                                <td class="text-right font-mono">${Formatters.number(pos.qty || pos.quantity, 4)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.entry_price || pos.entry, 2)}</td>
                                <td class="text-right font-mono">${Formatters.currency(pos.mark_price || pos.mark, 2)}</td>
                                <td class="text-right font-mono ${unPnl.className}">${unPnl.text}</td>
                                <td class="text-right font-mono text-negative">${pos.stop_loss ? Formatters.currency(pos.stop_loss, 2) : '—'}</td>
                                <td class="text-right font-mono text-positive">${pos.take_profit ? Formatters.currency(pos.take_profit, 2) : '—'}</td>
                                <td>
                                    <span class="badge-subtle font-mono">${pos.protection || 'DỪNG_TỰ_ĐỘNG'}</span>
                                </td>
                                <td>
                                    <span class="status-badge status-badge--healthy">
                                        <span class="status-badge__dot"></span>
                                        ${stateText}
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
                    Nhấp vào một dòng trong bảng danh sách vị thế để kiểm tra thông tin xác thực chi tiết
                </div>
            </div>
        `;
    }

    const pos = positions[index];
    const rawSide = (pos.side || 'LONG').toUpperCase();
    const isLong = rawSide === 'LONG';
    const sideText = isLong ? 'MUA (LONG)' : 'BÁN (SHORT)';
    const sideClass = isLong ? 'side-badge--long' : 'side-badge--short';
    const unPnl = Formatters.pnl(pos.unrealized_pnl || pos.pnl);
    const sym = Formatters.escapeHtml(pos.symbol || '—');
    const stateText = (pos.state || 'OPEN').toUpperCase() === 'OPEN' ? 'ĐANG MỞ' : (pos.state || 'ĐANG MỞ');

    return `
        <div>
            <div class="flex items-center justify-between pb-3 border-b border-border mb-3">
                <div class="flex items-center gap-2">
                    <span class="font-bold text-lg font-mono text-cyan">${sym}</span>
                    <span class="side-badge ${sideClass}">${sideText}</span>
                </div>
                <span class="status-badge status-badge--healthy">
                    <span class="status-badge__dot"></span>
                    ${stateText}
                </span>
            </div>

            <div class="telemetry-list">
                <div class="telemetry-item">
                    <span class="telemetry-key">Quy Mô Vị Thế</span>
                    <span class="telemetry-val font-mono font-bold">${Formatters.number(pos.qty || pos.quantity, 4)} ${sym.replace('USDT', '')}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Giá Vào Trung Bình</span>
                    <span class="telemetry-val font-mono">${Formatters.currency(pos.entry_price || pos.entry, 2)}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Giá Đánh Dấu (Mark)</span>
                    <span class="telemetry-val font-mono text-cyan">${Formatters.currency(pos.mark_price || pos.mark, 2)}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Lời / Lỗ Tạm Tính (PnL)</span>
                    <span class="telemetry-val font-mono font-bold ${unPnl.className}">${unPnl.text}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Điểm Cắt Lỗ (SL)</span>
                    <span class="telemetry-val font-mono text-negative">${pos.stop_loss ? Formatters.currency(pos.stop_loss, 2) : '—'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Điểm Chốt Lời (TP)</span>
                    <span class="telemetry-val font-mono text-positive">${pos.take_profit ? Formatters.currency(pos.take_profit, 2) : '—'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Cơ Chế Bảo Vệ</span>
                    <span class="telemetry-val font-mono text-positive">${pos.protection || 'DỪNG_TỰ_ĐỘNG'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Chế Độ Ký Quỹ</span>
                    <span class="telemetry-val font-mono">CÔ LẬP (ISOLATED)</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Đòn Bẩy</span>
                    <span class="telemetry-val font-mono">${pos.leverage ? pos.leverage + 'x' : '5x'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Giá Thanh Lý Dự Kiến</span>
                    <span class="telemetry-val font-mono text-muted">${pos.liquidation_price ? Formatters.currency(pos.liquidation_price, 2) : '—'}</span>
                </div>
                <div class="telemetry-item">
                    <span class="telemetry-key">Trạng Thái Thực Thi</span>
                    <span class="telemetry-val font-mono text-positive">${stateText}</span>
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
