import 'package:flutter/material.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';

enum QuantStatusType {
  healthy,
  ready,
  warning,
  critical,
  halted,
  disabled,
  unknown,
  sideLong,
  sideShort,
}

/// Semantic Status Badge Pill
class QuantStatusBadge extends StatelessWidget {
  final String label;
  final QuantStatusType type;
  final bool showDot;

  const QuantStatusBadge({
    super.key,
    required this.label,
    this.type = QuantStatusType.unknown,
    this.showDot = true,
  });

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color border;
    Color text;

    switch (type) {
      case QuantStatusType.healthy:
      case QuantStatusType.ready:
      case QuantStatusType.sideLong:
        bg = QuantColors.tintHealthyBg;
        border = QuantColors.tintHealthyBorder;
        text = QuantColors.green;
        break;
      case QuantStatusType.warning:
        bg = QuantColors.tintWarningBg;
        border = QuantColors.tintWarningBorder;
        text = QuantColors.gold;
        break;
      case QuantStatusType.critical:
      case QuantStatusType.halted:
      case QuantStatusType.sideShort:
        bg = QuantColors.tintCriticalBg;
        border = QuantColors.tintCriticalBorder;
        text = QuantColors.red;
        break;
      case QuantStatusType.disabled:
      case QuantStatusType.unknown:
        bg = QuantColors.surfaceLow;
        border = QuantColors.border;
        text = QuantColors.textMuted;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: QuantSpacing.borderMicro,
        border: Border.all(color: border, width: 1.0),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          if (showDot) ...[
            Container(
              width: 5,
              height: 5,
              decoration: BoxDecoration(
                color: text,
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 4),
          ],
          Text(
            label.toUpperCase(),
            style: QuantTypography.label.copyWith(
              fontSize: 9.0,
              color: text,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}
