import 'package:flutter/material.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';

enum QuantRiskLevel {
  info,
  warning,
  critical,
  halted,
  recovery,
}

/// Prominent Safety & Risk Warning Banner
class QuantRiskBanner extends StatelessWidget {
  final String title;
  final String message;
  final QuantRiskLevel level;
  final Widget? action;

  const QuantRiskBanner({
    super.key,
    required this.title,
    required this.message,
    this.level = QuantRiskLevel.info,
    this.action,
  });

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color border;
    Color iconColor;
    IconData iconData;

    switch (level) {
      case QuantRiskLevel.info:
        bg = QuantColors.tintOfflineBg;
        border = QuantColors.tintOfflineBorder;
        iconColor = QuantColors.cyan;
        iconData = Icons.info_outline;
        break;
      case QuantRiskLevel.warning:
      case QuantRiskLevel.recovery:
        bg = QuantColors.tintWarningBg;
        border = QuantColors.tintWarningBorder;
        iconColor = QuantColors.gold;
        iconData = Icons.warning_amber_rounded;
        break;
      case QuantRiskLevel.critical:
      case QuantRiskLevel.halted:
        bg = QuantColors.tintCriticalBg;
        border = QuantColors.tintCriticalBorder;
        iconColor = QuantColors.red;
        iconData = Icons.gpp_bad_outlined;
        break;
    }

    return Container(
      padding: QuantSpacing.paddingPanel,
      decoration: BoxDecoration(
        color: bg,
        borderRadius: QuantSpacing.borderDefault,
        border: Border.all(color: border, width: 1.0),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(iconData, size: 18, color: iconColor),
          const SizedBox(width: QuantSpacing.spaceSm),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title.toUpperCase(),
                  style: QuantTypography.heading.copyWith(
                    fontSize: 11.5,
                    color: iconColor,
                    letterSpacing: 0.3,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  message,
                  style: QuantTypography.body.copyWith(
                    fontSize: 11.0,
                    color: QuantColors.textPrimary,
                  ),
                ),
                if (action != null) ...[
                  const SizedBox(height: QuantSpacing.spaceXs),
                  action!,
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
