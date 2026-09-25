import 'package:flutter/material.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';

/// Compact Technical Panel Container
class QuantPanel extends StatelessWidget {
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final Widget child;
  final Widget? footer;
  final bool isCritical;
  final bool isLoading;
  final EdgeInsetsGeometry padding;

  const QuantPanel({
    super.key,
    required this.title,
    this.subtitle,
    this.trailing,
    required this.child,
    this.footer,
    this.isCritical = false,
    this.isLoading = false,
    this.padding = QuantSpacing.paddingPanel,
  });

  @override
  Widget build(BuildContext context) {
    final borderColor = isCritical ? QuantColors.red : QuantColors.border;
    final headerBg = isCritical ? QuantColors.tintCriticalBg : QuantColors.surfaceLow;

    return Container(
      decoration: BoxDecoration(
        color: QuantColors.surface,
        borderRadius: QuantSpacing.borderDefault,
        border: Border.all(color: borderColor, width: 1.0),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Header Bar
          Container(
            padding: QuantSpacing.paddingPanelHeader,
            decoration: BoxDecoration(
              color: headerBg,
              border: Border(
                bottom: BorderSide(
                  color: isCritical ? QuantColors.tintCriticalBorder : QuantColors.border,
                  width: 1.0,
                ),
              ),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Row(
                    children: [
                      Flexible(
                        child: Text(
                          title.toUpperCase(),
                          style: QuantTypography.heading.copyWith(fontSize: 12.0),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (subtitle != null) ...[
                        const SizedBox(width: QuantSpacing.spaceXs),
                        Flexible(
                          child: Text(
                            subtitle!,
                            style: QuantTypography.caption,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                ?trailing,
              ],
            ),
          ),
          // Body
          Padding(
            padding: padding,
            child: isLoading
                ? const Center(
                    child: Padding(
                      padding: EdgeInsets.all(QuantSpacing.spaceMd),
                      child: SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2.0, color: QuantColors.cyan),
                      ),
                    ),
                  )
                : child,
          ),
          // Optional Footer
          if (footer != null) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: QuantSpacing.spaceSm, vertical: QuantSpacing.space2xs),
              decoration: const BoxDecoration(
                color: QuantColors.surfaceLowest,
                border: Border(top: BorderSide(color: QuantColors.border, width: 1.0)),
              ),
              child: footer!,
            ),
          ],
        ],
      ),
    );
  }
}
