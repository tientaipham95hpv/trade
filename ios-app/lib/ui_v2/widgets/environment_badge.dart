import 'package:flutter/material.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';

enum EnvironmentType {
  offline,
  testnet,
  live,
  unknown,
}

/// System Environment Pill Badge (Cyan = OFFLINE, Gold = TESTNET, Red = LIVE)
class EnvironmentBadge extends StatelessWidget {
  final EnvironmentType environment;

  const EnvironmentBadge({
    super.key,
    required this.environment,
  });

  factory EnvironmentBadge.fromString(String? envStr) {
    final clean = (envStr ?? '').toUpperCase().trim();
    if (clean.contains('OFFLINE')) {
      return const EnvironmentBadge(environment: EnvironmentType.offline);
    } else if (clean.contains('TESTNET')) {
      return const EnvironmentBadge(environment: EnvironmentType.testnet);
    } else if (clean.contains('LIVE')) {
      return const EnvironmentBadge(environment: EnvironmentType.live);
    }
    return const EnvironmentBadge(environment: EnvironmentType.unknown);
  }

  @override
  Widget build(BuildContext context) {
    Color bg;
    Color border;
    Color text;
    String label;

    switch (environment) {
      case EnvironmentType.offline:
        bg = QuantColors.tintOfflineBg;
        border = QuantColors.tintOfflineBorder;
        text = QuantColors.cyan;
        label = 'OFFLINE';
        break;
      case EnvironmentType.testnet:
        bg = QuantColors.tintWarningBg;
        border = QuantColors.tintWarningBorder;
        text = QuantColors.gold;
        label = 'TESTNET';
        break;
      case EnvironmentType.live:
        bg = QuantColors.tintCriticalBg;
        border = QuantColors.tintCriticalBorder;
        text = QuantColors.red;
        label = 'LIVE';
        break;
      case EnvironmentType.unknown:
        bg = QuantColors.surfaceLow;
        border = QuantColors.border;
        text = QuantColors.textMuted;
        label = 'UNKNOWN';
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2.5),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: QuantSpacing.borderMicro,
        border: Border.all(color: border, width: 1.0),
      ),
      child: Text(
        label,
        style: QuantTypography.label.copyWith(
          fontSize: 9.0,
          color: text,
          fontWeight: FontWeight.w800,
          letterSpacing: 0.6,
        ),
      ),
    );
  }
}
