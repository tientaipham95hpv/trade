import 'package:flutter/material.dart';
import 'quant_colors.dart';
import 'quant_spacing.dart';
import 'quant_typography.dart';

/// Obsidian Quants Master ThemeData
class QuantTheme {
  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: QuantColors.background,
      primaryColor: QuantColors.cyan,
      colorScheme: const ColorScheme.dark(
        primary: QuantColors.cyan,
        secondary: QuantColors.gold,
        surface: QuantColors.surface,
        error: QuantColors.red,
        onPrimary: QuantColors.textInverse,
        onSurface: QuantColors.textPrimary,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: QuantColors.surfaceLowest,
        elevation: 0,
        scrolledUnderElevation: 0,
        titleTextStyle: QuantTypography.heading,
        iconTheme: IconThemeData(color: QuantColors.textSecondary, size: 20),
        shape: Border(
          bottom: BorderSide(color: QuantColors.border, width: 1.0),
        ),
      ),
      cardTheme: const CardThemeData(
        color: QuantColors.surface,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: QuantSpacing.borderDefault,
          side: BorderSide(color: QuantColors.border, width: 1.0),
        ),
      ),
      dividerTheme: const DividerThemeData(
        color: QuantColors.border,
        thickness: 1.0,
        space: 1.0,
      ),
      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: QuantColors.surfaceLowest,
        selectedItemColor: QuantColors.gold,
        unselectedItemColor: QuantColors.textMuted,
        selectedLabelStyle: QuantTypography.label,
        unselectedLabelStyle: QuantTypography.label,
        type: BottomNavigationBarType.fixed,
        elevation: 0,
      ),
      dialogTheme: const DialogThemeData(
        backgroundColor: QuantColors.surface,
        elevation: 8,
        shape: RoundedRectangleBorder(
          borderRadius: QuantSpacing.borderContainer,
          side: BorderSide(color: QuantColors.borderActive, width: 1.0),
        ),
      ),
    );
  }
}
