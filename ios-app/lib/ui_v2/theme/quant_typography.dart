import 'package:flutter/material.dart';
import 'quant_colors.dart';

/// Obsidian Quants Typography System
abstract class QuantTypography {
  static const List<FontFeature> tabularFeatures = [
    FontFeature.tabularFigures(),
    FontFeature.slashedZero(),
  ];

  // Display / Master Metric (Tabular Figures)
  static const TextStyle displayMetric = TextStyle(
    fontFamily: 'monospace',
    fontFeatures: tabularFeatures,
    fontSize: 22.0,
    fontWeight: FontWeight.w700,
    color: QuantColors.textPrimary,
    letterSpacing: -0.5,
    height: 1.15,
  );

  // Standard Metric (Tabular Figures)
  static const TextStyle metric = TextStyle(
    fontFamily: 'monospace',
    fontFeatures: tabularFeatures,
    fontSize: 15.0,
    fontWeight: FontWeight.w700,
    color: QuantColors.textPrimary,
    letterSpacing: -0.3,
    height: 1.2,
  );

  // Technical State / Timestamp / ID / Latency
  static const TextStyle technical = TextStyle(
    fontFamily: 'monospace',
    fontFeatures: tabularFeatures,
    fontSize: 11.5,
    fontWeight: FontWeight.w500,
    color: QuantColors.textSecondary,
    height: 1.3,
  );

  // Panel Heading
  static const TextStyle heading = TextStyle(
    fontSize: 13.5,
    fontWeight: FontWeight.w700,
    color: QuantColors.textPrimary,
    letterSpacing: -0.2,
  );

  // Section Title (Uppercase Tracked)
  static const TextStyle sectionTitle = TextStyle(
    fontSize: 11.0,
    fontWeight: FontWeight.w700,
    color: QuantColors.textPrimary,
    letterSpacing: 0.5,
  );

  // Standard Body
  static const TextStyle body = TextStyle(
    fontSize: 12.0,
    fontWeight: FontWeight.w400,
    color: QuantColors.textSecondary,
    height: 1.35,
  );

  // Micro Caption / Subtitle
  static const TextStyle caption = TextStyle(
    fontSize: 10.0,
    fontWeight: FontWeight.w400,
    color: QuantColors.textMuted,
  );

  // Uppercase Metric Label
  static const TextStyle label = TextStyle(
    fontSize: 9.5,
    fontWeight: FontWeight.w700,
    color: QuantColors.textMuted,
    letterSpacing: 0.6,
  );
}
