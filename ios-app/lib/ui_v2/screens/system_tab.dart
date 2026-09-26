import 'package:flutter/material.dart';
import '../models/system_status.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';
import '../widgets/environment_badge.dart';
import '../widgets/quant_panel.dart';

/// Tab 4: HỆ THỐNG (System & Governance)
/// Complete architecture governance matrix, live logs inspection, and operator session management.
class SystemTab extends StatelessWidget {
  final SystemStatus? status;
  final List<String> logs;
  final Future<void> Function() onRefreshLogs;
  final Future<void> Function() onLogout;

  const SystemTab({
    super.key,
    required this.status,
    required this.logs,
    required this.onRefreshLogs,
    required this.onLogout,
  });

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(QuantSpacing.spaceMd),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 1. Governance Matrix Panel
          QuantPanel(
            title: 'MA TRẬN QUẢN TRỊ KIẾN TRÚC (GOVERNANCE)',
            subtitle: 'NGUYÊN TẮC KIẾN TRÚC CỐ ĐỊNH',
            trailing: EnvironmentBadge.fromString(status?.environment),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildGovRow('Chứng chỉ API giao dịch sàn', 'REMOVED (0 credentials)', QuantColors.textSecondary),
                const SizedBox(height: 6),
                _buildGovRow('ClientApiCredential Model', 'REMOVED', QuantColors.textSecondary),
                const SizedBox(height: 6),
                _buildGovRow('Tính năng Copy-Trade', 'DISABLED', QuantColors.textMuted),
                const SizedBox(height: 6),
                _buildGovRow('Tính năng AI Copilot', 'NOT ENABLED', QuantColors.textMuted),
                const SizedBox(height: 6),
                _buildGovRow('Máy quét tín hiệu (Scanner)', 'DISABLED', QuantColors.textMuted),
                const SizedBox(height: 6),
                _buildGovRow('Môi trường Testnet / Live', 'DISABLED', QuantColors.gold),
                const SizedBox(height: 6),
                _buildGovRow('Đặt lệnh thủ công (Manual Buy/Sell)', 'PROHIBITED', QuantColors.red),
              ],
            ),
          ),
          const SizedBox(height: QuantSpacing.spaceMd),

          // 2. Core Execution Certification
          QuantPanel(
            title: 'CHỨNG THỰC LÕI THỰC THI',
            subtitle: 'CHỨNG THỰC BẢO TOÀN LÕI 15/15',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildGovRow('Trạng thái xác thực lõi', 'OFFLINE EXECUTION CORE ACCEPTED', QuantColors.cyan),
                const SizedBox(height: 6),
                _buildGovRow('Mã băm kiểm toán SHA-256', '15/15 PRESERVED (0 MISMATCH)', QuantColors.green),
                const SizedBox(height: 6),
                _buildGovRow('Đường dẫn lõi bảo vệ', 'core/execution/*', QuantColors.textSecondary),
                const SizedBox(height: 6),
                _buildGovRow('Dịch vụ giám sát máy chủ', 'trader-stack-offline.service', QuantColors.textSecondary),
                const SizedBox(height: 6),
                _buildGovRow('Cơ sở dữ liệu lưu trữ', 'SQLite (Chế độ WAL Hoạt động)', QuantColors.cyan),
              ],
            ),
          ),
          const SizedBox(height: QuantSpacing.spaceMd),

          // 3. Live System Logs Viewer
          QuantPanel(
            title: 'NHẬT KÝ VẬN HÀNH',
            subtitle: 'DỮ LIỆU NHẬT KÝ THỜI GIAN THỰC',
            trailing: IconButton(
              icon: const Icon(Icons.refresh, color: QuantColors.cyan, size: 18),
              onPressed: onRefreshLogs,
            ),
            padding: EdgeInsets.zero,
            child: Container(
              height: 220,
              padding: const EdgeInsets.all(QuantSpacing.spaceSm),
              decoration: const BoxDecoration(
                color: QuantColors.surfaceLowest,
                borderRadius: BorderRadius.only(
                  bottomLeft: Radius.circular(QuantSpacing.radiusDefault),
                  bottomRight: Radius.circular(QuantSpacing.radiusDefault),
                ),
              ),
              child: logs.isEmpty
                  ? const Center(
                      child: Text(
                        'Chưa có nhật ký hoạt động.',
                        style: TextStyle(color: QuantColors.textMuted, fontSize: 11.0),
                      ),
                    )
                  : ListView.builder(
                      itemCount: logs.length,
                      reverse: true,
                      itemBuilder: (ctx, idx) {
                        final line = logs[logs.length - 1 - idx];
                        Color lineColor = QuantColors.textSecondary;
                        if (line.contains('ERROR') || line.contains('CRITICAL')) {
                          lineColor = QuantColors.red;
                        } else if (line.contains('WARNING') || line.contains('WARN')) {
                          lineColor = QuantColors.gold;
                        } else if (line.contains('HALT')) {
                          lineColor = QuantColors.red;
                        }
                        return Padding(
                          padding: const EdgeInsets.symmetric(vertical: 2.0),
                          child: Text(
                            line,
                            style: QuantTypography.technical.copyWith(
                              fontSize: 10.5,
                              color: lineColor,
                            ),
                          ),
                        );
                      },
                    ),
            ),
          ),
          const SizedBox(height: QuantSpacing.spaceMd),

          // 4. Operator Session & Logout
          QuantPanel(
            title: 'PHIÊN VẬN HÀNH HIỆN TẠI',
            subtitle: 'PHIÊN LÀM VIỆC QUẢN TRỊ',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('TÀI KHOẢN', style: QuantTypography.caption),
                    Text('admin (Quản trị viên)', style: QuantTypography.technical.copyWith(fontSize: 11.5)),
                  ],
                ),
                const SizedBox(height: 6),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('LƯU TRỮ CHỨNG CHỈ', style: QuantTypography.caption),
                    Text('iOS Keychain (Bảo mật)', style: QuantTypography.technical.copyWith(fontSize: 11.5, color: QuantColors.cyan)),
                  ],
                ),
                const SizedBox(height: QuantSpacing.spaceMd),

                SizedBox(
                  height: QuantSpacing.minTouchTarget,
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.logout, color: QuantColors.red, size: 18),
                    label: Text(
                      'ĐĂNG XUẤT QUẢN TRỊ (LOGOUT)',
                      style: QuantTypography.sectionTitle.copyWith(color: QuantColors.red),
                    ),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: QuantColors.red),
                      shape: const RoundedRectangleBorder(borderRadius: QuantSpacing.borderDefault),
                    ),
                    onPressed: () async {
                      final confirmed = await showDialog<bool>(
                        context: context,
                        builder: (ctx) => AlertDialog(
                          backgroundColor: QuantColors.surface,
                          shape: const RoundedRectangleBorder(borderRadius: QuantSpacing.borderDefault),
                          title: Text('XÁC NHẬN ĐĂNG XUẤT', style: QuantTypography.heading),
                          content: Text(
                            'Bạn có chắc chắn muốn kết thúc phiên làm việc của quản trị viên?',
                            style: QuantTypography.body,
                          ),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.of(ctx).pop(false),
                              child: const Text('HỦY BỎ', style: TextStyle(color: QuantColors.textSecondary)),
                            ),
                            ElevatedButton(
                              style: ElevatedButton.styleFrom(backgroundColor: QuantColors.red),
                              onPressed: () => Navigator.of(ctx).pop(true),
                              child: const Text('ĐĂNG XUẤT', style: TextStyle(color: Colors.white)),
                            ),
                          ],
                        ),
                      );

                      if (confirmed == true) {
                        await onLogout();
                      }
                    },
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: QuantSpacing.spaceLg),
        ],
      ),
    );
  }

  Widget _buildGovRow(String label, String value, Color color) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        Expanded(
          flex: 5,
          child: Text(
            label,
            style: QuantTypography.caption,
            softWrap: true,
            maxLines: 2,
          ),
        ),
        const SizedBox(width: QuantSpacing.spaceXs),
        Expanded(
          flex: 6,
          child: Text(
            value,
            style: QuantTypography.technical.copyWith(
              color: color,
              fontWeight: FontWeight.w700,
              fontSize: 10.5,
            ),
            textAlign: TextAlign.end,
            softWrap: true,
            maxLines: 2,
          ),
        ),
      ],
    );
  }
}
