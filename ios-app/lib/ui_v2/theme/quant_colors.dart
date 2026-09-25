import 'package:flutter/material.dart';

/// Obsidian Quants V3 Restrained Dark Palette Tokens (Phase 6C)
/// Direction: Binance Pro + Linear + Bloomberg Terminal Density
abstract class QuantColors {
  // Foundations & Surfaces (Restrained Dark Palette)
  static const Color background = Color(0xFF070B12);
  static const Color surfaceLowest = Color(0xFF070B12);
  static const Color surfaceLow = Color(0xFF0D111A);
  static const Color surface = Color(0xFF0D111A);
  static const Color surfaceHigh = Color(0xFF121824);
  static const Color surfaceHighest = Color(0xFF171E2B);
  static const Color surfaceElevated = Color(0xFF171E2B);

  // Borders & Dividers
  static const Color border = Color(0xFF202938);
  static const Color borderActive = Color(0xFF334155);
  static const Color borderSubtle = Color(0x0FFFFFFF); // rgba(255, 255, 255, 0.06)

  // Functional Accents (Strictly restrained, Cyan max 10%)
  static const Color accentCyan = Color(0xFF3DD9EB);
  static const Color cyan = Color(0xFF3DD9EB);
  static const Color positive = Color(0xFF18C784);
  static const Color green = Color(0xFF18C784);
  static const Color negative = Color(0xFFF0445E);
  static const Color red = Color(0xFFF0445E);
  static const Color warning = Color(0xFFF3BA2F);
  static const Color gold = Color(0xFFF3BA2F);
  static const Color critical = Color(0xFFFF5C68);
  static const Color purple = Color(0xFFA855F7);

  // Text & Labels
  static const Color textPrimary = Color(0xFFE8EDF5);
  static const Color textSecondary = Color(0xFF95A1B2);
  static const Color textMuted = Color(0xFF5E6A7D);
  static const Color textInverse = Color(0xFF070B12);

  // Semantic Status Aliases
  static const Color statusHealthy = green;
  static const Color statusReady = green;
  static const Color statusWarning = gold;
  static const Color statusCritical = critical;
  static const Color statusHalted = critical;
  static const Color statusOffline = cyan;
  static const Color statusTestnet = gold;
  static const Color statusLive = gold;
  static const Color statusDisabled = textMuted;
  static const Color statusUnknown = textMuted;

  // Semantic Surface Tints (Subtle, Non-Neon)
  static const Color tintHealthyBg = Color(0x1418C784);
  static const Color tintHealthyBorder = Color(0x4018C784);
  static const Color tintWarningBg = Color(0x14F3BA2F);
  static const Color tintWarningBorder = Color(0x40F3BA2F);
  static const Color tintCriticalBg = Color(0x14FF5C68);
  static const Color tintCriticalBorder = Color(0x40FF5C68);
  static const Color tintOfflineBg = Color(0x143DD9EB);
  static const Color tintOfflineBorder = Color(0x403DD9EB);
}
