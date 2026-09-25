import 'package:flutter/material.dart';

/// Obsidian Quants Canonical Color System Tokens
abstract class QuantColors {
  // Foundations & Surfaces
  static const Color background = Color(0xFF051424);
  static const Color surfaceLowest = Color(0xFF010F1F);
  static const Color surfaceLow = Color(0xFF0D1C2D);
  static const Color surface = Color(0xFF122131);
  static const Color surfaceHigh = Color(0xFF1C2B3C);
  static const Color surfaceHighest = Color(0xFF273647);

  // Borders & Dividers
  static const Color border = Color(0xFF1C2E42);
  static const Color borderActive = Color(0xFF334155);
  static const Color borderSubtle = Color(0x991C2E42);

  // Functional Accents
  static const Color gold = Color(0xFFF0B90B);
  static const Color cyan = Color(0xFF00F0FF);
  static const Color green = Color(0xFF0ECB81);
  static const Color red = Color(0xFFF6465D);
  static const Color purple = Color(0xFFA855F7);

  // Text & Labels
  static const Color textPrimary = Color(0xFFD4E4FA);
  static const Color textSecondary = Color(0xFFB9CACB);
  static const Color textMuted = Color(0xFF849495);
  static const Color textInverse = Color(0xFF051424);

  // Semantic Status Aliases
  static const Color statusHealthy = green;
  static const Color statusReady = green;
  static const Color statusWarning = gold;
  static const Color statusCritical = red;
  static const Color statusHalted = red;
  static const Color statusOffline = cyan;
  static const Color statusTestnet = gold;
  static const Color statusLive = gold;
  static const Color statusDisabled = textMuted;
  static const Color statusUnknown = textMuted;

  // Semantic Surface Tints
  static const Color tintHealthyBg = Color(0x1A0ECB81);
  static const Color tintHealthyBorder = Color(0x590ECB81);
  static const Color tintWarningBg = Color(0x1AF0B90B);
  static const Color tintWarningBorder = Color(0x59F0B90B);
  static const Color tintCriticalBg = Color(0x1AF6465D);
  static const Color tintCriticalBorder = Color(0x59F6465D);
  static const Color tintOfflineBg = Color(0x1A00F0FF);
  static const Color tintOfflineBorder = Color(0x5900F0FF);
}
