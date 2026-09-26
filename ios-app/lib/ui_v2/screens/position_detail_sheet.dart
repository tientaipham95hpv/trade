import 'package:flutter/material.dart';
import '../models/position_view.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';
import '../utils/quant_formatters.dart';
import '../widgets/quant_risk_banner.dart';

/// Read-Only Position Details Modal Sheet.
/// Displays exhaustive telemetry without offering manual trading triggers.
class PositionDetailSheet extends StatelessWidget {
  final PositionView position;

  const PositionDetailSheet({
    super.key,
    required this.position,
  });

  static Future<void> show(BuildContext context, PositionView position) {
    return showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) => PositionDetailSheet(position: position),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isLong = position.isLong;
    final sideColor = isLong ? QuantColors.green : QuantColors.red;
    final pnl = position.unrealizedPnl;
    final pnlColor = (pnl != null && pnl > 0)
        ? QuantColors.green
        : (pnl != null && pnl < 0 ? QuantColors.red : QuantColors.textMuted);

    return Container(
      decoration: BoxDecoration(
        color: QuantColors.surface,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(QuantSpacing.radiusMax),
          topRight: Radius.circular(QuantSpacing.radiusMax),
        ),
        border: Border.all(color: QuantColors.borderActive, width: 1.0),
      ),
      padding: const EdgeInsets.all(QuantSpacing.spaceMd),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Handle bar
            Center(
              child: Container(
                width: 32,
                height: 3,
                decoration: BoxDecoration(
                  color: QuantColors.borderActive,
                  borderRadius: QuantSpacing.borderMicro,
                ),
              ),
            ),
            const SizedBox(height: QuantSpacing.spaceMd),

            // Sheet Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Text(
                      position.symbol,
                      style: QuantTypography.heading.copyWith(fontSize: 16.0),
                    ),
                    const SizedBox(width: QuantSpacing.spaceSm),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: sideColor.withValues(alpha: 0.12),
                        border: Border.all(color: sideColor.withValues(alpha: 0.4)),
                        borderRadius: QuantSpacing.borderMicro,
                      ),
                      child: Text(
                        position.side,
                        style: QuantTypography.technical.copyWith(
                          color: sideColor,
                          fontWeight: FontWeight.w800,
                          fontSize: 11.0,
                        ),
                      ),
                    ),
                    if (position.leverage != null) ...[
                      const SizedBox(width: QuantSpacing.space2xs),
                      Text(
                        '${position.leverage}x',
                        style: QuantTypography.caption.copyWith(color: QuantColors.textSecondary),
                      ),
                    ],
                  ],
                ),
                IconButton(
                  icon: const Icon(Icons.close, color: QuantColors.textSecondary, size: 20),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const Divider(color: QuantColors.border, height: QuantSpacing.spaceMd),

            // Key PnL Banner Container
            Container(
              padding: QuantSpacing.paddingPanel,
              decoration: BoxDecoration(
                color: QuantColors.surfaceLowest,
                borderRadius: QuantSpacing.borderDefault,
                border: Border.all(color: QuantColors.border),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('LỢI NHUẬN CHƯA THỰC HIỆN', style: QuantTypography.caption),
                      const SizedBox(height: 2),
                      Text(
                        QuantFormatters.formatPnl(pnl),
                        style: QuantTypography.displayMetric.copyWith(
                          color: pnlColor,
                          fontSize: 18.0,
                        ),
                      ),
                    ],
                  ),
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: [
                      Text('TỶ SUẤT (%)', style: QuantTypography.caption),
                      const SizedBox(height: 2),
                      Text(
                        QuantFormatters.formatPercent(position.pnlPercent),
                        style: QuantTypography.displayMetric.copyWith(
                          color: pnlColor,
                          fontSize: 18.0,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: QuantSpacing.spaceMd),

            // Metadata Grid
            _buildDetailRow('Khối lượng vị thế (Qty)', QuantFormatters.formatNumber(position.qty)),
            _buildDetailRow('Giá vào lệnh (Entry)', QuantFormatters.formatCurrency(position.entryPrice)),
            _buildDetailRow('Giá đánh dấu (Mark)', QuantFormatters.formatCurrency(position.markPrice)),
            _buildDetailRow('Ký quỹ (Margin)', QuantFormatters.formatCurrency(position.margin)),
            _buildDetailRow('Giá thanh lý (Liq Price)', QuantFormatters.formatCurrency(position.liquidationPrice)),
            _buildDetailRow('Cắt lỗ (Stop Loss)', QuantFormatters.formatCurrency(position.stopLoss)),
            _buildDetailRow('Chốt lời (Take Profit)', QuantFormatters.formatCurrency(position.takeProfit)),
            _buildDetailRow('Trạng thái bảo vệ', position.protectionStatus ?? '—'),
            _buildDetailRow('Trạng thái lệnh', position.state == 'OPEN' ? 'ĐANG MỞ (OPEN)' : (position.state ?? 'ĐANG MỞ (OPEN)')),

            const SizedBox(height: QuantSpacing.spaceMd),

            // Read-Only Operator Notice
            const QuantRiskBanner(
              title: 'CHẾ ĐỘ XEM CHỈ ĐỌC (READ-ONLY)',
              message: 'Vị thế được quản lý hoàn toàn tự động bởi lõi giao dịch ngoại tuyến (Execution Service). Không mở quyền can thiệp thủ công từ thiết bị di động.',
              level: QuantRiskLevel.info,
            ),
            const SizedBox(height: QuantSpacing.spaceSm),
          ],
        ),
      ),
    );
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: QuantTypography.body.copyWith(color: QuantColors.textSecondary, fontSize: 12.0)),
          Text(
            value,
            style: QuantTypography.technical.copyWith(
              fontWeight: FontWeight.w600,
              fontSize: 12.0,
            ),
          ),
        ],
      ),
    );
  }
}
