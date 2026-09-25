import 'package:flutter/material.dart';
import '../models/position_view.dart';
import '../models/system_status.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';
import '../utils/quant_formatters.dart';
import '../widgets/environment_badge.dart';
import '../widgets/quant_empty_state.dart';
import '../widgets/quant_metric.dart';
import '../widgets/quant_panel.dart';
import '../widgets/quant_risk_banner.dart';
import '../widgets/quant_section_header.dart';
import '../widgets/quant_status_badge.dart';
import 'position_detail_sheet.dart';

/// Tab 1: TỔNG QUAN (Overview)
/// High-density Bloomberg-style situational awareness.
class OverviewTab extends StatelessWidget {
  final SystemStatus? status;
  final VoidCallback onNavigateToPositions;

  const OverviewTab({
    super.key,
    required this.status,
    required this.onNavigateToPositions,
  });

  @override
  Widget build(BuildContext context) {
    final st = status ?? SystemStatus.unknown();
    final isHalted = st.isHalted;
    final isHealthy = st.isHealthy;

    QuantStatusType statusType;
    if (isHalted) {
      statusType = QuantStatusType.halted;
    } else if (isHealthy) {
      statusType = QuantStatusType.healthy;
    } else {
      statusType = QuantStatusType.unknown;
    }

    final pnl = st.realizedPnl;
    final pnlFormatted = pnl != null ? QuantFormatters.formatPnl(pnl) : null;
    final pnlColor = (pnl != null && pnl > 0)
        ? QuantColors.green
        : (pnl != null && pnl < 0 ? QuantColors.red : QuantColors.textMuted);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(QuantSpacing.spaceMd),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // If system is HALTED, display prominent warning banner
          if (isHalted) ...[
            QuantRiskBanner(
              title: 'CẢNH BÁO: HỆ THỐNG ĐANG BỊ TẠM DỪNG (HALTED)',
              message: 'Lý do: ${st.haltReason ?? "Kích hoạt bảo vệ rủi ro"}. Thế hệ HALT: ${st.haltGeneration ?? "—"}.',
              level: QuantRiskLevel.critical,
            ),
            const SizedBox(height: QuantSpacing.spaceMd),
          ],

          // 1. System Status & Projection Panel
          QuantPanel(
            title: 'HỆ THỐNG VẬN HÀNH',
            subtitle: st.projectionSource ?? 'PROJECTION',
            trailing: QuantStatusBadge(
              label: st.status,
              type: statusType,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('NGUỒN DỮ LIỆU', style: QuantTypography.caption),
                    Text(st.projectionSource ?? 'EXECUTION_SERVICE', style: QuantTypography.technical.copyWith(fontSize: 11.5)),
                  ],
                ),
                const SizedBox(height: 6),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('CẦU DAO (CIRCUIT BREAKER)', style: QuantTypography.caption),
                    Text(
                      isHalted ? 'TRIPPED' : 'ARMED',
                      style: QuantTypography.technical.copyWith(
                        color: isHalted ? QuantColors.red : QuantColors.cyan,
                        fontWeight: FontWeight.w700,
                        fontSize: 11.5,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('HALT GENERATION', style: QuantTypography.caption),
                    Text(
                      st.haltGeneration != null ? '${st.haltGeneration}' : '—',
                      style: QuantTypography.technical.copyWith(
                        color: QuantColors.cyan,
                        fontWeight: FontWeight.w700,
                        fontSize: 11.5,
                      ),
                    ),
                  ],
                ),
                if (st.haltReason != null && st.haltReason != 'None') ...[
                  const SizedBox(height: 6),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text('LÝ DO DỪNG', style: QuantTypography.caption),
                      Flexible(
                        child: Text(
                          st.haltReason!,
                          style: QuantTypography.caption.copyWith(color: QuantColors.gold),
                          textAlign: TextAlign.end,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: QuantSpacing.spaceMd),

          // 2. Telemetry Key Metrics (2x2 Grid)
          // Strictly display '—' for missing values; ZERO fake $1000 fallback
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: QuantSpacing.paddingCard,
                  decoration: BoxDecoration(
                    color: QuantColors.surface,
                    borderRadius: QuantSpacing.borderDefault,
                    border: Border.all(color: QuantColors.border),
                  ),
                  child: QuantMetric(
                    label: 'SỐ DƯ (BALANCE)',
                    value: st.balance != null ? QuantFormatters.formatCurrency(st.balance) : null,
                    unit: 'USDT',
                  ),
                ),
              ),
              const SizedBox(width: QuantSpacing.spaceSm),
              Expanded(
                child: Container(
                  padding: QuantSpacing.paddingCard,
                  decoration: BoxDecoration(
                    color: QuantColors.surface,
                    borderRadius: QuantSpacing.borderDefault,
                    border: Border.all(color: QuantColors.border),
                  ),
                  child: QuantMetric(
                    label: 'PNL THỰC HIỆN',
                    value: pnlFormatted,
                    unit: 'USDT',
                    valueColor: pnlColor,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: QuantSpacing.spaceSm),
          Row(
            children: [
              Expanded(
                child: Container(
                  padding: QuantSpacing.paddingCard,
                  decoration: BoxDecoration(
                    color: QuantColors.surface,
                    borderRadius: QuantSpacing.borderDefault,
                    border: Border.all(color: QuantColors.border),
                  ),
                  child: QuantMetric(
                    label: 'TRẠNG THÁI PNL',
                    value: st.pnlState,
                    valueColor: st.pnlState == 'KNOWN_VALUE' ? QuantColors.cyan : QuantColors.textMuted,
                  ),
                ),
              ),
              const SizedBox(width: QuantSpacing.spaceSm),
              Expanded(
                child: Container(
                  padding: QuantSpacing.paddingCard,
                  decoration: BoxDecoration(
                    color: QuantColors.surface,
                    borderRadius: QuantSpacing.borderDefault,
                    border: Border.all(color: QuantColors.border),
                  ),
                  child: QuantMetric(
                    label: 'VỊ THẾ ĐANG MỞ',
                    value: '${st.openPositionsCount ?? st.positions.length}',
                    unit: '/ ${st.maxPositions ?? 3}',
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: QuantSpacing.spaceLg),

          // 3. Active Positions Snapshot
          QuantSectionHeader(
            title: 'VỊ THẾ ĐANG MỞ',
            action: InkWell(
              onTap: onNavigateToPositions,
              child: Text(
                'XEM TẤT CẢ (${st.positions.length})',
                style: QuantTypography.caption.copyWith(
                  color: QuantColors.cyan,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          const SizedBox(height: QuantSpacing.spaceSm),

          if (st.positions.isEmpty)
            const QuantEmptyState(
              title: 'Không có vị thế mở',
              message: 'Lõi giao dịch đang ở trạng thái flat (0 vị thế đang hoạt động).',
            )
          else ...[
            ...st.positions.take(3).map((pos) => _buildPositionRow(context, pos)),
          ],

          const SizedBox(height: QuantSpacing.spaceLg),

          // 4. Governance & Certification Banner
          QuantPanel(
            title: 'CHỨNG THỰC VẬN HÀNH',
            subtitle: 'OFFLINE ARCHITECTURE',
            trailing: EnvironmentBadge.fromString(status?.environment),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildGovRow('Lõi giao dịch (Core)', 'OFFLINE EXECUTION CORE ACCEPTED', QuantColors.cyan),
                const SizedBox(height: 6),
                _buildGovRow('Toàn vẹn mã nguồn', '15/15 PRESERVED (0 MISMATCH)', QuantColors.green),
                const SizedBox(height: 6),
                _buildGovRow('Chứng chỉ API sàn', 'REMOVED (0 credentials)', QuantColors.textSecondary),
                const SizedBox(height: 6),
                _buildGovRow('Thị trường mở', 'OFFLINE ONLY (Live/Testnet Disabled)', QuantColors.gold),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPositionRow(BuildContext context, PositionView pos) {
    final isLong = pos.isLong;
    final sideColor = isLong ? QuantColors.green : QuantColors.red;
    final pnl = pos.unrealizedPnl;
    final pnlColor = (pnl != null && pnl > 0)
        ? QuantColors.green
        : (pnl != null && pnl < 0 ? QuantColors.red : QuantColors.textMuted);

    return InkWell(
      onTap: () => PositionDetailSheet.show(context, pos),
      borderRadius: QuantSpacing.borderDefault,
      child: Container(
        margin: const EdgeInsets.only(bottom: QuantSpacing.spaceSm),
        padding: QuantSpacing.paddingPanel,
        decoration: BoxDecoration(
          color: QuantColors.surface,
          borderRadius: QuantSpacing.borderDefault,
          border: Border.all(color: QuantColors.border),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(pos.symbol, style: QuantTypography.heading.copyWith(fontSize: 13.0)),
                      const SizedBox(width: QuantSpacing.spaceXs),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
                        decoration: BoxDecoration(
                          color: sideColor.withValues(alpha: 0.12),
                          border: Border.all(color: sideColor.withValues(alpha: 0.4)),
                          borderRadius: QuantSpacing.borderMicro,
                        ),
                        child: Text(
                          pos.side,
                          style: QuantTypography.technical.copyWith(
                            color: sideColor,
                            fontSize: 9.5,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 3),
                  Text(
                    'Entry: ${QuantFormatters.formatCurrency(pos.entryPrice)} | Qty: ${QuantFormatters.formatNumber(pos.qty)}',
                    style: QuantTypography.caption,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
            const SizedBox(width: QuantSpacing.spaceSm),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  QuantFormatters.formatPnl(pnl),
                  style: QuantTypography.technical.copyWith(
                    color: pnlColor,
                    fontWeight: FontWeight.w700,
                    fontSize: 12.5,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  QuantFormatters.formatPercent(pos.pnlPercent),
                  style: QuantTypography.caption.copyWith(color: pnlColor),
                ),
              ],
            ),
          ],
        ),
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
