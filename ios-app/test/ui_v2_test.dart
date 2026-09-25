import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:binance_quant_pro/ui_v2/theme/quant_colors.dart';
import 'package:binance_quant_pro/ui_v2/theme/quant_theme.dart';
import 'package:binance_quant_pro/ui_v2/widgets/environment_badge.dart';
import 'package:binance_quant_pro/ui_v2/widgets/quant_status_badge.dart';
import 'package:binance_quant_pro/ui_v2/widgets/quant_metric.dart';
import 'package:binance_quant_pro/ui_v2/widgets/quant_panel.dart';
import 'package:binance_quant_pro/ui_v2/widgets/quant_risk_banner.dart';
import 'package:binance_quant_pro/ui_v2/widgets/quant_empty_state.dart';
import 'package:binance_quant_pro/ui_v2/widgets/quant_confirm_sheet.dart';

void main() {
  group('QuantTheme Tests', () {
    test('Constructs dark theme matching Obsidian Quants tokens', () {
      final theme = QuantTheme.darkTheme;
      expect(theme.brightness, equals(Brightness.dark));
      expect(theme.scaffoldBackgroundColor, equals(QuantColors.background));
      expect(theme.colorScheme.primary, equals(QuantColors.cyan));
      expect(theme.colorScheme.secondary, equals(QuantColors.gold));
      expect(theme.colorScheme.surface, equals(QuantColors.surface));
    });
  });

  group('EnvironmentBadge Widget Tests', () {
    testWidgets('Renders OFFLINE badge in cyan', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EnvironmentBadge(environment: EnvironmentType.offline),
          ),
        ),
      );

      expect(find.text('OFFLINE'), findsOneWidget);
    });

    testWidgets('Parses environment strings correctly', (tester) async {
      final offline = EnvironmentBadge.fromString('OFFLINE');
      expect(offline.environment, equals(EnvironmentType.offline));

      final testnet = EnvironmentBadge.fromString('TESTNET');
      expect(testnet.environment, equals(EnvironmentType.testnet));

      final live = EnvironmentBadge.fromString('LIVE');
      expect(live.environment, equals(EnvironmentType.live));

      final unknown = EnvironmentBadge.fromString(null);
      expect(unknown.environment, equals(EnvironmentType.unknown));
    });
  });

  group('QuantStatusBadge Widget Tests', () {
    testWidgets('Renders healthy status badge', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: QuantStatusBadge(label: 'HEALTHY', type: QuantStatusType.healthy),
          ),
        ),
      );

      expect(find.text('HEALTHY'), findsOneWidget);
    });

    testWidgets('Renders halted status badge', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: QuantStatusBadge(label: 'HALTED', type: QuantStatusType.halted),
          ),
        ),
      );

      expect(find.text('HALTED'), findsOneWidget);
    });
  });

  group('QuantMetric Widget Tests', () {
    testWidgets('Renders explicit value and unit', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: QuantMetric(label: 'Realized PnL', value: '+\$12.50', unit: 'USDT'),
          ),
        ),
      );

      expect(find.text('REALIZED PNL'), findsOneWidget);
      expect(find.text('+\$12.50'), findsOneWidget);
      expect(find.text('USDT'), findsOneWidget);
    });

    testWidgets('Renders dash for null or empty value without fabricating fake numbers', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                QuantMetric(label: 'Balance', value: null),
                QuantMetric(label: 'Win Rate', value: ''),
              ],
            ),
          ),
        ),
      );

      expect(find.text('BALANCE'), findsOneWidget);
      expect(find.text('WIN RATE'), findsOneWidget);
      expect(find.text('—'), findsNWidgets(2));
      // Ensure fake $1000 fallback is NOT rendered
      expect(find.text('\$1,000.00'), findsNothing);
      expect(find.text('1000'), findsNothing);
    });
  });

  group('QuantPanel Widget Tests', () {
    testWidgets('Renders panel title and child content', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: QuantPanel(
              title: 'Telemetry',
              subtitle: 'v1.0',
              child: Text('Panel Content'),
            ),
          ),
        ),
      );

      expect(find.text('TELEMETRY'), findsOneWidget);
      expect(find.text('v1.0'), findsOneWidget);
      expect(find.text('Panel Content'), findsOneWidget);
    });
  });

  group('QuantRiskBanner Widget Tests', () {
    testWidgets('Renders warning risk banner', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: QuantRiskBanner(
              title: 'Circuit Breaker Cooldown',
              message: 'Trading paused until cooldown expires.',
              level: QuantRiskLevel.warning,
            ),
          ),
        ),
      );

      expect(find.text('CIRCUIT BREAKER COOLDOWN'), findsOneWidget);
      expect(find.text('Trading paused until cooldown expires.'), findsOneWidget);
    });
  });

  group('QuantEmptyState Widget Tests', () {
    testWidgets('Renders empty state stoically', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: QuantEmptyState(
              title: 'No Active Positions',
              message: 'Core is flat.',
            ),
          ),
        ),
      );

      expect(find.text('No Active Positions'), findsOneWidget);
      expect(find.text('Core is flat.'), findsOneWidget);
    });
  });

  group('QuantConfirmSheet Widget Tests', () {
    testWidgets('Renders operator confirmation sheet with actions', (tester) async {
      bool confirmed = false;
      bool cancelled = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: QuantConfirmSheet(
              title: 'Confirm Operator Halt',
              message: 'Immediate halt for all order admission.',
              targetScope: 'GLOBAL',
              expectedHaltGeneration: 4,
              onConfirm: () => confirmed = true,
              onCancel: () => cancelled = true,
            ),
          ),
        ),
      );

      expect(find.text('CONFIRM OPERATOR HALT'), findsOneWidget);
      expect(find.text('Immediate halt for all order admission.'), findsOneWidget);
      expect(find.text('PHẠM VI: GLOBAL'), findsOneWidget);
      expect(find.text('HALT GENERATION: 4'), findsOneWidget);
      expect(find.text('XÁC NHẬN'), findsOneWidget);
      expect(find.text('HỦY BỎ'), findsOneWidget);

      await tester.tap(find.text('XÁC NHẬN'));
      expect(confirmed, isTrue);

      await tester.tap(find.text('HỦY BỎ'));
      expect(cancelled, isTrue);
    });
  });
}
