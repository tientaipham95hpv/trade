import 'package:flutter/material.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';

/// Modal Bottom Sheet for Safety-Critical Operator Confirmations
class QuantConfirmSheet extends StatelessWidget {
  final String title;
  final String message;
  final bool isDanger;
  final String confirmLabel;
  final String cancelLabel;
  final String? targetScope;
  final int? expectedHaltGeneration;
  final VoidCallback onConfirm;
  final VoidCallback? onCancel;

  const QuantConfirmSheet({
    super.key,
    required this.title,
    required this.message,
    this.isDanger = true,
    this.confirmLabel = 'XÁC NHẬN',
    this.cancelLabel = 'HỦY BỎ',
    this.targetScope,
    this.expectedHaltGeneration,
    required this.onConfirm,
    this.onCancel,
  });

  static Future<bool?> show(
    BuildContext context, {
    required String title,
    required String message,
    bool isDanger = true,
    String confirmLabel = 'XÁC NHẬN',
    String cancelLabel = 'HỦY BỎ',
    String? targetScope,
    int? expectedHaltGeneration,
  }) {
    return showModalBottomSheet<bool>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) => QuantConfirmSheet(
        title: title,
        message: message,
        isDanger: isDanger,
        confirmLabel: confirmLabel,
        cancelLabel: cancelLabel,
        targetScope: targetScope,
        expectedHaltGeneration: expectedHaltGeneration,
        onConfirm: () => Navigator.of(ctx).pop(true),
        onCancel: () => Navigator.of(ctx).pop(false),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final accentColor = isDanger ? QuantColors.red : QuantColors.gold;

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

            // Header Row
            Row(
              children: [
                Icon(
                  isDanger ? Icons.warning_amber_rounded : Icons.info_outline,
                  color: accentColor,
                  size: 20,
                ),
                const SizedBox(width: QuantSpacing.spaceSm),
                Expanded(
                  child: Text(
                    title.toUpperCase(),
                    style: QuantTypography.heading.copyWith(color: accentColor),
                  ),
                ),
              ],
            ),
            const SizedBox(height: QuantSpacing.spaceSm),

            // Body Message
            Text(
              message,
              style: QuantTypography.body,
            ),
            const SizedBox(height: QuantSpacing.spaceSm),

            // Meta Info Container (Target Scope / HALT Generation)
            if (targetScope != null || expectedHaltGeneration != null) ...[
              Container(
                padding: QuantSpacing.paddingPanel,
                decoration: BoxDecoration(
                  color: QuantColors.surfaceLowest,
                  borderRadius: QuantSpacing.borderDefault,
                  border: Border.all(color: QuantColors.border, width: 1.0),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    if (targetScope != null) ...[
                      Text(
                        'PHẠM VI: $targetScope',
                        style: QuantTypography.technical.copyWith(fontSize: 10.5),
                      ),
                    ],
                    if (expectedHaltGeneration != null) ...[
                      const SizedBox(height: 2),
                      Text(
                        'HALT GENERATION: $expectedHaltGeneration',
                        style: QuantTypography.technical.copyWith(
                          fontSize: 10.5,
                          color: QuantColors.cyan,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: QuantSpacing.spaceMd),
            ],

            // Action Buttons (Minimum 44px Touch Targets)
            Row(
              children: [
                Expanded(
                  child: SizedBox(
                    height: QuantSpacing.minTouchTarget,
                    child: OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        foregroundColor: QuantColors.textSecondary,
                        side: const BorderSide(color: QuantColors.border),
                        shape: const RoundedRectangleBorder(
                          borderRadius: QuantSpacing.borderDefault,
                        ),
                      ),
                      onPressed: onCancel ?? () => Navigator.of(context).pop(false),
                      child: Text(
                        cancelLabel.toUpperCase(),
                        style: QuantTypography.sectionTitle.copyWith(color: QuantColors.textSecondary),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: QuantSpacing.spaceSm),
                Expanded(
                  child: SizedBox(
                    height: QuantSpacing.minTouchTarget,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: isDanger ? QuantColors.red : QuantColors.cyan,
                        foregroundColor: isDanger ? Colors.white : QuantColors.textInverse,
                        shape: const RoundedRectangleBorder(
                          borderRadius: QuantSpacing.borderDefault,
                        ),
                        elevation: 0,
                      ),
                      onPressed: onConfirm,
                      child: Text(
                        confirmLabel.toUpperCase(),
                        style: QuantTypography.sectionTitle.copyWith(
                          color: isDanger ? Colors.white : QuantColors.textInverse,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
