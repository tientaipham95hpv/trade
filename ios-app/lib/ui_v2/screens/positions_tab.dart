import 'package:flutter/material.dart';
import '../models/position_view.dart';
import '../models/system_status.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';
import '../utils/quant_formatters.dart';
import '../widgets/quant_empty_state.dart';
import '../widgets/quant_panel.dart';
import '../widgets/quant_risk_banner.dart';
import '../widgets/quant_section_header.dart';
import 'position_detail_sheet.dart';

/// Tab 2: VỊ THẾ (Positions)
/// Dense inspection table for active positions.
/// Read-only: Zero manual trade controls or close buttons.
class PositionsTab extends StatelessWidget {
  final SystemStatus? status;
  final Future<void> Function() onRefresh;

  const PositionsTab({
    super.key,
    required this.status,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    final positions = status?.positions ?? [];
    final maxPositions = status?.maxPositions ?? 3;

    return RefreshIndicator(
      onRefresh: onRefresh,
      color: QuantColors.cyan,
      backgroundColor: QuantColors.surface,
      child: SingleChildScrollView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.all(QuantSpacing.spaceMd),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header summary panel
            QuantPanel(
            title: 'QUẢN LÝ VỊ THẾ THỰC THI',
            subtitle: '${positions.length}/$maxPositions HOẠT ĐỘNG',
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('SỐ LƯỢNG VỊ THẾ', style: QuantTypography.caption),
                    Text(
                      '${positions.length} / $maxPositions',
                      style: QuantTypography.technical.copyWith(
                        color: QuantColors.cyan,
                        fontWeight: FontWeight.w700,
                        fontSize: 12.0,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Expanded(
                      child: Text(
                        'QUYỀN ĐẶT LỆNH THỦ CÔNG',
                        style: QuantTypography.caption,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: QuantSpacing.spaceXs),
                    Flexible(
                      child: Text(
                        'VÔ HIỆU HÓA (PROHIBITED)',
                        style: QuantTypography.technical.copyWith(
                          color: QuantColors.textSecondary,
                          fontWeight: FontWeight.w700,
                          fontSize: 11.0,
                        ),
                        textAlign: TextAlign.end,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: QuantSpacing.spaceMd),

          QuantSectionHeader(
            title: 'DANH SÁCH VỊ THẾ HIỆN HÀNH (${positions.length})',
          ),
          const SizedBox(height: QuantSpacing.spaceSm),

          if (positions.isEmpty)
            const QuantEmptyState(
              title: 'Không có vị thế mở',
              message: 'Lõi giao dịch đang ở trạng thái flat (0 vị thế). Tất cả nguồn lực an toàn trong trạng thái chờ.',
            )
          else
            ...positions.map((pos) => _buildPositionCard(context, pos)),

          const SizedBox(height: QuantSpacing.spaceMd),

          const QuantRiskBanner(
            title: 'CHẾ ĐỘ GIÁM SÁT TOÀN DIỆN',
            message: 'Nhấn vào từng vị thế để kiểm tra chi tiết tham số SL/TP và mức giá thanh lý bảo vệ.',
            level: QuantRiskLevel.info,
          ),
        ],
      ),
    ),
  );
  }

  Widget _buildPositionCard(BuildContext context, PositionView pos) {
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
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Row 1: Symbol, Side, Leverage, Chevron
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Text(pos.symbol, style: QuantTypography.heading.copyWith(fontSize: 14.0)),
                    const SizedBox(width: QuantSpacing.spaceSm),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: sideColor.withValues(alpha: 0.12),
                        border: Border.all(color: sideColor.withValues(alpha: 0.4)),
                        borderRadius: QuantSpacing.borderMicro,
                      ),
                      child: Text(
                        pos.side,
                        style: QuantTypography.technical.copyWith(
                          color: sideColor,
                          fontWeight: FontWeight.w800,
                          fontSize: 10.0,
                        ),
                      ),
                    ),
                    if (pos.leverage != null) ...[
                      const SizedBox(width: QuantSpacing.space2xs),
                      Text(
                        '${pos.leverage}x',
                        style: QuantTypography.caption.copyWith(color: QuantColors.textSecondary),
                      ),
                    ],
                  ],
                ),
                const Icon(Icons.chevron_right, color: QuantColors.textSecondary, size: 18),
              ],
            ),
            const Divider(color: QuantColors.border, height: QuantSpacing.spaceMd),

            // Row 2: Price Metrics
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('GIÁ VÀO (ENTRY)', style: QuantTypography.caption, overflow: TextOverflow.ellipsis),
                      const SizedBox(height: 2),
                      Text(
                        QuantFormatters.formatCurrency(pos.entryPrice),
                        style: QuantTypography.technical.copyWith(fontSize: 12.0),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      Text('GIÁ MARK', style: QuantTypography.caption, overflow: TextOverflow.ellipsis),
                      const SizedBox(height: 2),
                      Text(
                        QuantFormatters.formatCurrency(pos.markPrice),
                        style: QuantTypography.technical.copyWith(fontSize: 12.0),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text('PNL TẠM TÍNH', style: QuantTypography.caption, overflow: TextOverflow.ellipsis),
                      const SizedBox(height: 2),
                      Text(
                        QuantFormatters.formatPnl(pnl),
                        style: QuantTypography.technical.copyWith(
                          color: pnlColor,
                          fontWeight: FontWeight.w700,
                          fontSize: 12.0,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: QuantSpacing.spaceSm),

            // Row 3: Protection & Size
            Container(
              padding: const EdgeInsets.symmetric(horizontal: QuantSpacing.spaceSm, vertical: 4),
              decoration: BoxDecoration(
                color: QuantColors.surfaceLowest,
                borderRadius: QuantSpacing.borderMicro,
                border: Border.all(color: QuantColors.border),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text(
                      'Qty: ${QuantFormatters.formatNumber(pos.qty)}',
                      style: QuantTypography.caption,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Expanded(
                    child: Text(
                      'Bảo vệ: ${pos.protectionStatus ?? "—"}',
                      textAlign: TextAlign.center,
                      style: QuantTypography.caption.copyWith(
                        color: pos.protectionStatus != null ? QuantColors.cyan : QuantColors.textMuted,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Expanded(
                    child: Text(
                      'Tỷ suất: ${QuantFormatters.formatPercent(pos.pnlPercent)}',
                      textAlign: TextAlign.end,
                      style: QuantTypography.caption.copyWith(color: pnlColor),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
