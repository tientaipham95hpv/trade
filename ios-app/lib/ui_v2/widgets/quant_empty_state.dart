import 'package:flutter/material.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';

/// Stoic Non-Decorative Empty State Placeholder
class QuantEmptyState extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? message;
  final Widget? action;

  const QuantEmptyState({
    super.key,
    this.icon = Icons.layers_clear_outlined,
    required this.title,
    this.message,
    this.action,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: QuantSpacing.spaceMd,
          vertical: QuantSpacing.spaceXl,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 28,
              color: QuantColors.textMuted.withValues(alpha: 0.6),
            ),
            const SizedBox(height: QuantSpacing.spaceXs),
            Text(
              title,
              style: QuantTypography.heading.copyWith(
                fontSize: 12.0,
                color: QuantColors.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            if (message != null) ...[
              const SizedBox(height: QuantSpacing.space2xs),
              Text(
                message!,
                style: QuantTypography.caption.copyWith(
                  fontFamily: 'monospace',
                ),
                textAlign: TextAlign.center,
              ),
            ],
            if (action != null) ...[
              const SizedBox(height: QuantSpacing.spaceSm),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}
