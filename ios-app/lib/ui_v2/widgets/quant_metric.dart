import 'package:flutter/material.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';

/// Compact Quantitative Metric Card
class QuantMetric extends StatelessWidget {
  final String label;
  final String? value;
  final String? unit;
  final String? delta;
  final bool? deltaIsPositive;
  final Color? valueColor;
  final bool isLoading;

  const QuantMetric({
    super.key,
    required this.label,
    this.value,
    this.unit,
    this.delta,
    this.deltaIsPositive,
    this.valueColor,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    final displayVal = (value != null && value!.trim().isNotEmpty) ? value! : '—';
    final isDash = displayVal == '—';

    Color resolvedColor;
    if (valueColor != null) {
      resolvedColor = valueColor!;
    } else if (isDash) {
      resolvedColor = QuantColors.textMuted;
    } else {
      resolvedColor = QuantColors.textPrimary;
    }

    return Container(
      padding: QuantSpacing.paddingCard,
      decoration: BoxDecoration(
        color: QuantColors.surfaceLow,
        borderRadius: QuantSpacing.borderDefault,
        border: Border.all(color: QuantColors.border, width: 1.0),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Label
          Text(
            label.toUpperCase(),
            style: QuantTypography.label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: QuantSpacing.space2xs),
          // Value & Unit Row
          if (isLoading)
            Container(
              height: 20,
              width: 60,
              margin: const EdgeInsets.symmetric(vertical: 2),
              decoration: BoxDecoration(
                color: QuantColors.surfaceHigh,
                borderRadius: QuantSpacing.borderMicro,
              ),
            )
          else
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Flexible(
                  child: Text(
                    displayVal,
                    style: QuantTypography.metric.copyWith(color: resolvedColor),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (unit != null && !isDash) ...[
                  const SizedBox(width: QuantSpacing.spaceXs),
                  Text(
                    unit!,
                    style: QuantTypography.caption.copyWith(color: QuantColors.textSecondary),
                  ),
                ],
              ],
            ),
          // Delta Row
          if (delta != null) ...[
            const SizedBox(height: QuantSpacing.space2xs),
            Row(
              children: [
                if (deltaIsPositive != null)
                  Icon(
                    deltaIsPositive! ? Icons.arrow_drop_up : Icons.arrow_drop_down,
                    size: 14,
                    color: deltaIsPositive! ? QuantColors.green : QuantColors.red,
                  ),
                Text(
                  delta!,
                  style: QuantTypography.technical.copyWith(
                    fontSize: 10.0,
                    color: deltaIsPositive == null
                        ? QuantColors.textMuted
                        : (deltaIsPositive! ? QuantColors.green : QuantColors.red),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}
