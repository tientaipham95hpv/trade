import 'package:flutter/material.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';

/// Compact Terminal Section Header
class QuantSectionHeader extends StatelessWidget {
  final String title;
  final String? meta;
  final Widget? statusBadge;
  final Widget? action;

  const QuantSectionHeader({
    super.key,
    required this.title,
    this.meta,
    this.statusBadge,
    this.action,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.only(bottom: QuantSpacing.spaceXs),
      decoration: const BoxDecoration(
        border: Border(
          bottom: BorderSide(color: QuantColors.border, width: 1.0),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Expanded(
            child: Row(
              children: [
                Flexible(
                  child: Text(
                    title.toUpperCase(),
                    style: QuantTypography.sectionTitle,
                    softWrap: true,
                    maxLines: 2,
                  ),
                ),
                if (statusBadge != null) ...[
                  const SizedBox(width: QuantSpacing.spaceXs),
                  statusBadge!,
                ],
              ],
            ),
          ),
          if (meta != null || action != null) ...[
            const SizedBox(width: QuantSpacing.spaceXs),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (meta != null)
                  Text(
                    meta!,
                    style: QuantTypography.caption,
                  ),
                if (action != null) ...[
                  const SizedBox(width: QuantSpacing.spaceXs),
                  action!,
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }
}
