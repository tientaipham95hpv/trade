import 'package:flutter/material.dart';

/// Obsidian Quants Spacing and Radius Scale
abstract class QuantSpacing {
  // Spacing Rhythm (High Density)
  static const double space2xs = 2.0;
  static const double spaceXs = 4.0;
  static const double spaceSm = 8.0;
  static const double spaceMd = 12.0;
  static const double spaceLg = 16.0;
  static const double spaceXl = 24.0;
  static const double space2xl = 32.0;

  // Insets Presets
  static const EdgeInsets paddingPanel = EdgeInsets.all(spaceSm);
  static const EdgeInsets paddingPanelHeader = EdgeInsets.symmetric(horizontal: spaceSm, vertical: spaceXs);
  static const EdgeInsets paddingScreen = EdgeInsets.all(spaceMd);
  static const EdgeInsets paddingCard = EdgeInsets.all(spaceSm);

  // Radius Scale
  static const double radiusMicro = 2.0;
  static const double radiusDefault = 4.0;
  static const double radiusContainer = 6.0;
  static const double radiusMax = 8.0;

  static const BorderRadius borderMicro = BorderRadius.all(Radius.circular(radiusMicro));
  static const BorderRadius borderDefault = BorderRadius.all(Radius.circular(radiusDefault));
  static const BorderRadius borderContainer = BorderRadius.all(Radius.circular(radiusContainer));
  static const BorderRadius borderMax = BorderRadius.all(Radius.circular(radiusMax));

  // Minimum Mobile Touch Target
  static const double minTouchTarget = 44.0;
}
