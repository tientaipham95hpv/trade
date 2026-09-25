import 'package:flutter/material.dart';
import '../models/risk_view.dart';
import '../models/system_status.dart';
import '../services/quant_api_client.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';
import '../widgets/quant_confirm_sheet.dart';
import '../widgets/quant_panel.dart';
import '../widgets/quant_risk_banner.dart';
import '../widgets/quant_status_badge.dart';

/// Tab 3: RỦI RO (Risk & Circuit Breaker)
/// Authoritative risk telemetry and safety surface.
/// Phase 4 Operator Actions: HALT and RESUME with CAS generation checks. CLOSEALL strictly unavailable.
class RiskTab extends StatefulWidget {
  final SystemStatus? status;
  final QuantApiClient? apiClient;
  final Future<void> Function()? onActionCompleted;

  const RiskTab({
    super.key,
    required this.status,
    this.apiClient,
    this.onActionCompleted,
  });

  @override
  State<RiskTab> createState() => _RiskTabState();
}

class _RiskTabState extends State<RiskTab> {
  bool _isExecuting = false;

  Future<void> _handleHalt(RiskView riskView) async {
    if (_isExecuting) return;

    final confirmed = await QuantConfirmSheet.show(
      context,
      title: 'XÁC NHẬN DỪNG KHẨN CẤP (HALT)',
      message: 'Lệnh này sẽ chặn tiếp nhận mọi vị thế mới và kích hoạt thế hệ HALT mới trong Execution Service.',
      isDanger: true,
      targetScope: 'GLOBAL',
      expectedHaltGeneration: (riskView.haltGeneration ?? 0) + 1,
    );

    if (confirmed != true) return;
    if (widget.apiClient == null) return;

    setState(() => _isExecuting = true);

    try {
      final res = await widget.apiClient!.sendHalt(
        reason: 'Flutter operator manual halt',
        source: 'flutter',
      );

      if (mounted) {
        final gen = res['halt_generation'];
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Đã kích hoạt HALT thành công (Thế hệ #${gen ?? '—'})'),
            backgroundColor: QuantColors.surfaceLow,
          ),
        );
      }
      await widget.onActionCompleted?.call();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(e is QuantApiException ? e.message : 'Lỗi dừng hệ thống: $e'),
            backgroundColor: QuantColors.tintCriticalBg,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isExecuting = false);
      }
    }
  }

  Future<void> _handleResume(RiskView riskView) async {
    if (_isExecuting) return;

    final haltGen = riskView.haltGeneration;
    if (haltGen == null || haltGen < 1) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Không thể khôi phục: Không xác định được thế hệ HALT hợp lệ.'),
          backgroundColor: QuantColors.tintCriticalBg,
        ),
      );
      return;
    }

    final confirmed = await QuantConfirmSheet.show(
      context,
      title: 'XÁC NHẬN KHÔI PHỤC (RESUME)',
      message: 'Khôi phục tiếp nhận giao dịch từ thế hệ #$haltGen. Thao tác yêu cầu CAS generation phải khớp chính xác thế hệ hiện tại.',
      isDanger: false,
      targetScope: 'EXECUTION_CORE',
      expectedHaltGeneration: haltGen,
    );

    if (confirmed != true) return;
    if (widget.apiClient == null) return;

    setState(() => _isExecuting = true);

    try {
      await widget.apiClient!.sendResume(
        expectedHaltGeneration: haltGen,
        source: 'flutter',
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Đã khôi phục hệ thống thành công (RESUMED)'),
            backgroundColor: QuantColors.surfaceLow,
          ),
        );
      }
      await widget.onActionCompleted?.call();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(e is QuantApiException ? e.message : 'Lỗi khôi phục hệ thống: $e'),
            backgroundColor: QuantColors.tintCriticalBg,
          ),
        );
      }
      if (e is QuantApiException && e.code == 'STALE_HALT_GENERATION') {
        await widget.onActionCompleted?.call();
      }
    } finally {
      if (mounted) {
        setState(() => _isExecuting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final st = widget.status ?? SystemStatus.unknown();
    final riskView = RiskView.fromStatus(st);
    final isHalted = riskView.isHalted;
    final resumeAllowed = st.resumeAllowed && !_isExecuting;
    final haltAllowed = !st.isUnknown && !_isExecuting;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(QuantSpacing.spaceMd),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Circuit Breaker State Banner
          if (isHalted)
            QuantRiskBanner(
              title: 'CẦU DAO ĐÃ KÍCH HOẠT (TRIPPED)',
              message: 'Lõi giao dịch đang ở trạng thái HALTED. Mọi đơn tiếp nhận mới bị chặn.',
              level: QuantRiskLevel.critical,
            )
          else
            const QuantRiskBanner(
              title: 'CẦU DAO SẴN SÀNG (ARMED)',
              message: 'Hệ thống giám sát rủi ro liên tục bảo vệ vốn và kiểm soát drawdown.',
              level: QuantRiskLevel.info,
            ),
          const SizedBox(height: QuantSpacing.spaceMd),

          // 1. Circuit Breaker Telemetry Panel
          QuantPanel(
            title: 'TELEMETRY CẦU DAO RỦI RO',
            subtitle: 'CIRCUIT BREAKER',
            trailing: QuantStatusBadge(
              label: riskView.circuitBreakerStatus,
              type: isHalted ? QuantStatusType.halted : QuantStatusType.healthy,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildRow('TRẠNG THÁI HALT', isHalted ? 'HALTED' : 'NORMAL', isHalted ? QuantColors.red : QuantColors.cyan),
                const SizedBox(height: 6),
                _buildRow('HALT GENERATION TOKEN', riskView.haltGeneration != null ? '#${riskView.haltGeneration}' : '—', QuantColors.cyan),
                const SizedBox(height: 6),
                _buildRow('LÝ DO DỪNG', riskView.haltReason ?? 'None', QuantColors.textPrimary),
                const SizedBox(height: 6),
                _buildRow('VỊ THẾ TỐI ĐA CHO PHÉP', '${riskView.maxPositions ?? 3} vị thế', QuantColors.textSecondary),
                const SizedBox(height: 6),
                _buildRow('VỊ THẾ ĐANG GIỮ', '${riskView.currentPositions} vị thế', QuantColors.textSecondary),
              ],
            ),
          ),
          const SizedBox(height: QuantSpacing.spaceMd),

          // 2. Health Dimensions Breakdown
          QuantPanel(
            title: 'CHIỀU KHÔNG GIAN BẢO MẬT (HEALTH DIMENSIONS)',
            subtitle: 'SUBSYSTEM HEALTH',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildHealthRow('Dịch vụ thực thi (Execution Service)', isHalted ? 'HALTED' : (st.isHealthy ? 'HEALTHY' : 'UNKNOWN')),
                const SizedBox(height: 6),
                _buildHealthRow('Cổng giao tiếp Web (Web Gateway)', 'READY'),
                const SizedBox(height: 6),
                _buildHealthRow('Bộ đệm tin nhắn Telegram', 'READY'),
                const SizedBox(height: 6),
                _buildHealthRow('Cơ sở dữ liệu SQLite', 'WAL_ACTIVE'),
              ],
            ),
          ),
          const SizedBox(height: QuantSpacing.spaceMd),

          // 3. Operator Actions Surface (Phase 4 Active Controls)
          QuantPanel(
            title: 'ĐIỀU KHIỂN TÁC ĐỘNG KHẨN CẤP (MUTATIONS)',
            subtitle: 'PHASE 4 CAS GUARDS',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                QuantRiskBanner(
                  title: 'KIỂM SOÁT THẾ HỆ HALT (CAS PROTOCOL)',
                  message: st.recoveryRequired
                      ? 'YÊU CẦU PHỤC HỒI: Hệ thống đang yêu cầu kiểm tra và xử lý an toàn khẩn cấp trước khi khôi phục.'
                      : (isHalted
                          ? 'Hệ thống đang HALT ở thế hệ #${riskView.haltGeneration ?? '—'}. Lệnh RESUME yêu cầu thế hệ phải khớp chính xác.'
                          : 'Hệ thống đang hoạt động bình thường. Có thể kích hoạt dừng khẩn cấp HALT khi cần.'),
                  level: st.recoveryRequired || isHalted ? QuantRiskLevel.warning : QuantRiskLevel.info,
                ),
                const SizedBox(height: QuantSpacing.spaceMd),

                // Active Action Buttons
                Row(
                  children: [
                    Expanded(
                      child: SizedBox(
                        height: QuantSpacing.minTouchTarget,
                        child: OutlinedButton.icon(
                          icon: _isExecuting
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: QuantColors.red),
                                )
                              : const Icon(Icons.pause_circle_outline, color: QuantColors.red, size: 18),
                          label: Text(
                            _isExecuting ? 'ĐANG XỬ LÝ...' : 'HALT',
                            style: QuantTypography.sectionTitle.copyWith(
                              color: haltAllowed ? QuantColors.red : QuantColors.textMuted,
                            ),
                          ),
                          style: OutlinedButton.styleFrom(
                            side: BorderSide(color: haltAllowed ? QuantColors.red : QuantColors.border),
                            shape: const RoundedRectangleBorder(borderRadius: QuantSpacing.borderDefault),
                          ),
                          onPressed: haltAllowed ? () => _handleHalt(riskView) : null,
                        ),
                      ),
                    ),
                    const SizedBox(width: QuantSpacing.spaceSm),
                    Expanded(
                      child: SizedBox(
                        height: QuantSpacing.minTouchTarget,
                        child: OutlinedButton.icon(
                          icon: _isExecuting
                              ? const SizedBox(
                                  width: 16,
                                  height: 16,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: QuantColors.cyan),
                                )
                              : Icon(
                                  Icons.play_circle_outline,
                                  color: resumeAllowed ? QuantColors.cyan : QuantColors.textMuted,
                                  size: 18,
                                ),
                          label: Text(
                            _isExecuting ? 'ĐANG XỬ LÝ...' : 'RESUME',
                            style: QuantTypography.sectionTitle.copyWith(
                              color: resumeAllowed ? QuantColors.cyan : QuantColors.textMuted,
                            ),
                          ),
                          style: OutlinedButton.styleFrom(
                            side: BorderSide(color: resumeAllowed ? QuantColors.cyan : QuantColors.border),
                            shape: const RoundedRectangleBorder(borderRadius: QuantSpacing.borderDefault),
                          ),
                          onPressed: resumeAllowed ? () => _handleResume(riskView) : null,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: QuantSpacing.spaceSm),
                SizedBox(
                  height: QuantSpacing.minTouchTarget,
                  child: OutlinedButton.icon(
                    icon: const Icon(Icons.block, color: QuantColors.textMuted, size: 16),
                    label: Text(
                      'CLOSE ALL (KHÔNG KHẢ DỤNG)',
                      style: QuantTypography.caption.copyWith(color: QuantColors.textMuted),
                    ),
                    style: OutlinedButton.styleFrom(
                      side: const BorderSide(color: QuantColors.border),
                      shape: const RoundedRectangleBorder(borderRadius: QuantSpacing.borderDefault),
                    ),
                    onPressed: null, // Strictly disabled in operator console
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRow(String label, String value, Color color) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Expanded(
          child: Text(
            label,
            style: QuantTypography.caption,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(width: QuantSpacing.spaceXs),
        Flexible(
          child: Text(
            value,
            style: QuantTypography.technical.copyWith(
              color: color,
              fontWeight: FontWeight.w700,
              fontSize: 11.5,
            ),
            textAlign: TextAlign.end,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  Widget _buildHealthRow(String label, String state) {
    final isGood = state == 'HEALTHY' || state == 'READY' || state == 'WAL_ACTIVE';
    final color = isGood ? QuantColors.green : (state == 'HALTED' ? QuantColors.red : QuantColors.textMuted);

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Expanded(
          child: Text(
            label,
            style: QuantTypography.caption,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(width: QuantSpacing.spaceXs),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            borderRadius: QuantSpacing.borderMicro,
            border: Border.all(color: color.withValues(alpha: 0.4)),
          ),
          child: Text(
            state,
            style: QuantTypography.technical.copyWith(
              color: color,
              fontSize: 10.0,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ],
    );
  }
}
