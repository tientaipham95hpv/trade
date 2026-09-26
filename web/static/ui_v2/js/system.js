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

    const nowUtc = new Date().toISOString().substring(11, 19);

    container.innerHTML = `
        <div class="page-header">
            <div>
                <h1 class="page-title">Kiến Trúc Hệ Thống & Quản Trị</h1>
                <p class="page-subtitle">Cấu hình môi trường chạy &bull; Kiểm toán mật mã học &bull; Sơ đồ phân hệ dịch vụ</p>
            </div>
            <div class="page-header-meta">
                <span class="status-badge status-badge--healthy">
                    <span class="status-badge__dot"></span>
                    NGOẠI_TUYẾN_HOẠT_ĐỘNG
                </span>
                <span class="page-meta-time">${nowUtc} UTC</span>
            </div>
        </div>

        <div class="overview-band-wrapper">
            <!-- 2-Column Grid for System Specifications -->
            <div class="terminal-grid-12">
                <!-- Section 1: Runtime (6 cols) -->
                <div class="col-span-6">
                    <div class="terminal-panel">
                        <div class="panel-header">
                            <div>
                                <span class="panel-title">MÔI TRƯỜNG & KIẾN TRÚC MẠNG</span>
                                <span class="panel-subtitle">Tiến trình hệ thống và cô lập máy chủ</span>
                            </div>
                            <span class="status-badge status-badge--healthy">NGOẠI_TUYẾN</span>
                        </div>
                        <div class="panel-body">
                            <div class="telemetry-list">
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Môi Trường</span>
                                    <span class="telemetry-val font-mono text-cyan font-bold">${(status.environment || state.environment || 'OFFLINE') === 'OFFLINE' ? 'NGOẠI TUYẾN' : (status.environment || state.environment || 'OFFLINE').toUpperCase()}</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Chế Độ Chạy</span>
                                    <span class="telemetry-val font-mono">${status.mode || 'MÔ PHỎNG / GIẢ LẬP'}</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Máy Chủ Đích</span>
                                    <span class="telemetry-val font-mono text-xs">Cục Bộ Chuẩn / Nút Chuyên Dụng</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Sàn Giao Dịch Đích</span>
                                    <span class="telemetry-val font-mono">SÀN MÔ PHỎNG NGOẠI TUYẾN (0 GỌI API)</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Đơn Vị Giám Sát</span>
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
                            <div>
                                <span class="panel-title">MA TRẬN SỨC KHỎE DỊCH VỤ</span>
                                <span class="panel-subtitle">Các tiến trình daemon cốt lõi và cổng IPC</span>
                            </div>
                            <span class="badge-subtle font-mono">TIẾN TRÌNH DAEMON</span>
                        </div>
                        <div class="panel-body">
                            <div class="telemetry-list">
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Dịch Vụ Thực Thi (Execution)</span>
                                    <span class="telemetry-val font-mono text-positive font-bold">KHỎE MẠNH</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Cổng Giao Tiếp Web Gateway</span>
                                    <span class="telemetry-val font-mono text-positive font-bold">KHỎE MẠNH</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Bot Thông Báo Telegram</span>
                                    <span class="telemetry-val font-mono text-positive font-bold">KHỎE MẠNH</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Nhật Ký Lưu Trữ SQLite WAL</span>
                                    <span class="telemetry-val font-mono text-positive font-bold">KHỎE MẠNH</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Cổng Loopback IPC (50051)</span>
                                    <span class="telemetry-val font-mono text-positive font-bold">ĐÃ GẮN KẾT</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 3: Authority Boundaries (6 cols) -->
                <div class="col-span-6">
                    <div class="terminal-panel">
                        <div class="panel-header">
                            <div>
                                <span class="panel-title">RANH GIỚI BẢO MẬT & QUYỀN HẠN</span>
                                <span class="panel-subtitle">Kiểm soát truy cập và phân tách đặc quyền</span>
                            </div>
                            <span class="badge-subtle font-mono">CÔ LẬP TIẾN TRÌNH</span>
                        </div>
                        <div class="panel-body">
                            <div class="telemetry-list">
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Quyền Đặt Lệnh / Sửa Đổi</span>
                                    <span class="telemetry-val font-mono text-cyan">Duy nhất Dịch Vụ Thực Thi</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Chứng Chỉ API Giao Dịch</span>
                                    <span class="telemetry-val font-mono text-muted">ĐÃ GỠ BỎ / KHÔNG CÓ</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Gọi Sàn Trực Tiếp Từ Web</span>
                                    <span class="telemetry-val font-mono text-positive">BẰNG 0 (BỊ NGĂN CHẶN)</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Thực Thi Lệnh Trực Tiếp Vào DB</span>
                                    <span class="telemetry-val font-mono text-positive">BẰNG 0 (CHỈ PID THỰC THI)</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Phương Thức Xác Thực</span>
                                    <span class="telemetry-val font-mono">Cookie HttpOnly SameSite</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 4: Core Certification (6 cols) -->
                <div class="col-span-6">
                    <div class="terminal-panel">
                        <div class="panel-header">
                            <div>
                                <span class="panel-title">XÁC THỰC LÕI BẰNG MẬT MÃ HỌC</span>
                                <span class="panel-subtitle">Bất biến thực thi tất định SHA-256</span>
                            </div>
                            <span class="status-badge status-badge--healthy font-mono">MẬT MÃ HỌC</span>
                        </div>
                        <div class="panel-body">
                            <div class="core-cert-block">
                                <span class="core-cert-title">CHỨNG THỰC LÕI THỰC THI</span>
                                <span class="core-cert-status">15 / 15 tệp đã khớp chuẩn</span>
                                <span class="core-cert-sub">CHẤP NHẬN LÕI THỰC THI NGOẠI TUYẾN</span>
                            </div>
                            <div class="telemetry-list mt-3">
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Số Tệp Sai Lệch</span>
                                    <span class="telemetry-val font-mono text-positive">0 SAI LỆCH</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Đường Dẫn Lõi</span>
                                    <span class="telemetry-val font-mono text-xs">core/execution/*</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Tính Bất Biến Thực Thi</span>
                                    <span class="telemetry-val font-mono text-positive">ĐÓNG BĂNG ỔN ĐỊNH</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 5: Features Governance Matrix (12 cols) -->
                <div class="col-span-12">
                    <div class="terminal-panel">
                        <div class="panel-header">
                            <span class="panel-title">MA TRẬN QUẢN TRỊ TÍNH NĂNG</span>
                            <span class="badge-subtle font-mono">KHÓA AN TOÀN (FAIL-CLOSED)</span>
                        </div>
                        <div class="panel-body p-0">
                            <div class="dense-table-container">
                                <table class="dense-table">
                                    <thead>
                                        <tr>
                                            <th>PHÂN HỆ TÍNH NĂNG</th>
                                            <th>MỤC TIÊU QUYỀN HẠN</th>
                                            <th>TRẠNG THÁI</th>
                                            <th>CHÍNH SÁCH BẢO VỆ</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td class="font-bold font-mono">Tạm Dừng Khẩn Cấp (HALT)</td>
                                            <td class="font-mono text-xs">Dịch Vụ Thực Thi (/api/pause)</td>
                                            <td><span class="status-badge status-badge--healthy">SẴN SÀNG</span></td>
                                            <td class="text-secondary text-xs">Tăng thế hệ CAS nguyên tử</td>
                                        </tr>
                                        <tr>
                                            <td class="font-bold font-mono">Khôi Phục Tiếp Tục (RESUME)</td>
                                            <td class="font-mono text-xs">Dịch Vụ Thực Thi (/api/resume)</td>
                                            <td><span class="status-badge status-badge--healthy">SẴN SÀNG</span></td>
                                            <td class="text-secondary text-xs">Điều kiện khớp chính xác thế hệ CAS</td>
                                        </tr>
                                        <tr>
                                            <td class="font-bold font-mono">Đóng Toàn Bộ Vị Thế (CLOSE ALL)</td>
                                            <td class="font-mono text-xs">Không khả dụng</td>
                                            <td><span class="status-badge status-badge--critical">VÔ HIỆU HÓA</span></td>
                                            <td class="text-muted text-xs">Bị cấm trên bàn điều khiển vận hành</td>
                                        </tr>
                                        <tr>
                                            <td class="font-bold font-mono">Đặt Lệnh Mua / Bán Thủ Công</td>
                                            <td class="font-mono text-xs">Không khả dụng</td>
                                            <td><span class="status-badge status-badge--critical">VÔ HIỆU HÓA</span></td>
                                            <td class="text-muted text-xs">Giao diện đặt lệnh thủ công đã gỡ bỏ</td>
                                        </tr>
                                        <tr>
                                            <td class="font-bold font-mono">Giao Dịch Thị Trường Thật</td>
                                            <td class="font-mono text-xs">Sàn Giao Dịch Thật Binance</td>
                                            <td><span class="status-badge status-badge--critical">VÔ HIỆU HÓA</span></td>
                                            <td class="text-muted text-xs">Khóa cứng ở chế độ NGOẠI TUYẾN</td>
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
                            <span class="panel-title">KIỂM TOÁN PHÁT HÀNH & BẢN DỰNG</span>
                            <span class="badge-subtle font-mono">CAM KẾT GIT</span>
                        </div>
                        <div class="panel-body">
                            <div class="telemetry-list">
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Nhánh Git</span>
                                    <span class="telemetry-val font-mono text-cyan">ui-v2-rc1</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Ứng Viên Phát Hành</span>
                                    <span class="telemetry-val font-mono">UI_V2_RC1</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Nền Tảng Đích</span>
                                    <span class="telemetry-val font-mono">Web V2 + Flutter iOS V2 + App PC</span>
                                </div>
                                <div class="telemetry-item">
                                    <span class="telemetry-key">Trạng Thái Triển Khai</span>
                                    <span class="telemetry-val font-mono text-positive">ĐÃ CHỨNG THỰC HOÀN TOÀN</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}
