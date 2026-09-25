import 'package:flutter/material.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';

/// Compact Skeleton Placeholder for Loading States
class QuantLoadingSkeleton extends StatelessWidget {
  final double width;
  final double height;
  final BorderRadius? borderRadius;

  const QuantLoadingSkeleton({
    super.key,
    required this.width,
    required this.height,
    this.borderRadius,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: QuantColors.surfaceHigh,
        borderRadius: borderRadius ?? QuantSpacing.borderMicro,
      ),
    );
  }
}

/// Compact Monospace Progress Indicator
class QuantLoadingIndicator extends StatelessWidget {
  final double size;
  final Color color;

  const QuantLoadingIndicator({
    super.key,
    this.size = 18.0,
    this.color = QuantColors.cyan,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CircularProgressIndicator(
        strokeWidth: 2.0,
        color: color,
        backgroundColor: QuantColors.surfaceLow,
      ),
    );
  }
}
