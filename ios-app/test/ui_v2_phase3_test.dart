import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:binance_quant_pro/ui_v2/models/position_view.dart';
import 'package:binance_quant_pro/ui_v2/models/risk_view.dart';
import 'package:binance_quant_pro/ui_v2/models/system_status.dart';
import 'package:binance_quant_pro/ui_v2/services/auth_store.dart';
import 'package:binance_quant_pro/ui_v2/services/polling_controller.dart';
import 'package:binance_quant_pro/ui_v2/services/quant_api_client.dart';
import 'package:binance_quant_pro/ui_v2/utils/quant_formatters.dart';
import 'package:binance_quant_pro/ui_v2/screens/home_screen.dart';
import 'package:binance_quant_pro/ui_v2/screens/login_screen.dart';
import 'package:binance_quant_pro/ui_v2/screens/overview_tab.dart';
import 'package:binance_quant_pro/ui_v2/screens/positions_tab.dart';
import 'package:binance_quant_pro/ui_v2/screens/risk_tab.dart';
import 'package:binance_quant_pro/ui_v2/screens/system_tab.dart';

void main() {
  group('AuthStore Tests', () {
    test('Token management in memory fallback', () async {
      final store = AuthStore(useMemoryOnly: true);

      expect(await store.hasToken(), isFalse);
      expect(await store.getToken(), isNull);

      await store.saveToken('test_session_token_123');
      expect(await store.hasToken(), isTrue);
      expect(await store.getToken(), equals('test_session_token_123'));

      await store.clearToken();
      expect(await store.hasToken(), isFalse);
      expect(await store.getToken(), isNull);
    });

    test('Server URL persistence and default', () async {
      final store = AuthStore(useMemoryOnly: true);

      expect(await store.getServerUrl(), equals(AuthStore.defaultServerUrl));

      await store.saveServerUrl('https://custom.trader.site/');
      expect(await store.getServerUrl(), equals('https://custom.trader.site'));
    });
  });

  group('QuantFormatters Tests (Zero Fake Defaults)', () {
    test('Currency formatting handles null with em-dash and values cleanly', () {
      expect(QuantFormatters.formatCurrency(null), equals('—'));
      expect(QuantFormatters.formatCurrency(1234.5), equals('\$1,234.50'));
      expect(QuantFormatters.formatCurrency(-50.25), equals('-\$50.25'));
    });

    test('PnL formatting includes explicit plus/minus signs', () {
      expect(QuantFormatters.formatPnl(null), equals('—'));
      expect(QuantFormatters.formatPnl(12.5), equals('+\$12.50'));
      expect(QuantFormatters.formatPnl(-8.2), equals('-\$8.20'));
      expect(QuantFormatters.formatPnl(0.0), equals('\$0.00'));
    });

    test('Percent formatting handles signs and nulls', () {
      expect(QuantFormatters.formatPercent(null), equals('—'));
      expect(QuantFormatters.formatPercent(2.45), equals('+2.45%'));
      expect(QuantFormatters.formatPercent(-1.2), equals('-1.20%'));
    });

    test('Generic number formatting trims zeros properly', () {
      expect(QuantFormatters.formatNumber(null), equals('—'));
      expect(QuantFormatters.formatNumber(0.025), equals('0.025'));
      expect(QuantFormatters.formatNumber(1250.0), equals('1,250'));
    });

    test('Latency formatting adds ms suffix', () {
      expect(QuantFormatters.formatLatency(null), equals('—'));
      expect(QuantFormatters.formatLatency(24), equals('24ms'));
    });
  });

  group('Model Strong Parsing Tests', () {
    test('SystemStatus parses null balance without fabricating \$1000', () {
      final json = {
        'status': 'HEALTHY',
        'projection_source': 'EXECUTION_SERVICE',
        'is_paused': false,
        'halt_generation': 4,
        'halt_reason': 'None',
        'balance': null,
        'realized_pnl': 125.5,
        'pnl_state': 'KNOWN_VALUE',
        'open_positions_count': 1,
        'positions': [
          {
            'symbol': 'BTCUSDT',
            'side': 'LONG',
            'qty': 0.05,
            'entry_price': 60000.0,
            'current_price': 61000.0,
            'unrealized_pnl': 50.0,
            'pnl_percent': 1.67,
            'leverage': 5,
            'stop_loss': 59000.0,
            'take_profit': 63000.0,
          }
        ],
        'max_positions': 3,
      };

      final status = SystemStatus.fromJson(json);

      expect(status.status, equals('HEALTHY'));
      expect(status.isHealthy, isTrue);
      expect(status.isHalted, isFalse);
      expect(status.balance, isNull);
      expect(status.realizedPnl, equals(125.5));
      expect(status.haltGeneration, equals(4));
      expect(status.positions.length, equals(1));

      final pos = status.positions.first;
      expect(pos.symbol, equals('BTCUSDT'));
      expect(pos.side, equals('LONG'));
      expect(pos.isLong, isTrue);
      expect(pos.entryPrice, equals(60000.0));
      expect(pos.markPrice, equals(61000.0));
      expect(pos.unrealizedPnl, equals(50.0));
    });

    test('SystemStatus parses dictionary positions map safely', () {
      final json = {
        'status': 'HALTED',
        'is_paused': true,
        'halt_generation': 7,
        'halt_reason': 'Risk Breaker Limit Exceeded',
        'positions': {
          'ETHUSDT': {
            'side': 'SHORT',
            'qty': 1.5,
            'entry_price': 3000.0,
            'current_price': 2950.0,
            'unrealized_pnl': 75.0,
            'leverage': 3,
          }
        },
      };

      final status = SystemStatus.fromJson(json);
      expect(status.isHalted, isTrue);
      expect(status.haltGeneration, equals(7));
      expect(status.haltReason, equals('Risk Breaker Limit Exceeded'));
      expect(status.positions.length, equals(1));
      expect(status.positions.first.symbol, equals('ETHUSDT'));
      expect(status.positions.first.isShort, isTrue);
    });

    test('RiskView correctly projects circuit breaker and governance from status', () {
      final status = SystemStatus(
        status: 'HEALTHY',
        isPaused: false,
        haltGeneration: 2,
        haltReason: 'None',
        openPositionsCount: 0,
        maxPositions: 3,
      );

      final risk = RiskView.fromStatus(status);
      expect(risk.circuitBreakerStatus, equals('ARMED'));
      expect(risk.isHalted, isFalse);
      expect(risk.haltGeneration, equals(2));
      expect(risk.certificationText, equals('OFFLINE EXECUTION CORE ACCEPTED'));
      expect(risk.hashVerification, equals('15/15 PRESERVED (0 MISMATCH)'));
    });
  });

  group('QuantApiClient & PollingController Tests', () {
    test('checkAuth returns true on 200 {authenticated: true}', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/api/check_auth') {
          return http.Response(jsonEncode({'authenticated': true, 'username': 'admin'}), 200);
        }
        return http.Response('Not Found', 404);
      });

      final authStore = AuthStore(useMemoryOnly: true);
      final apiClient = QuantApiClient(authStore: authStore, client: mockClient);

      final isAuth = await apiClient.checkAuth();
      expect(isAuth, isTrue);
    });

    test('401 response on fetchStatus triggers clearToken and onUnauthorized', () async {
      bool unauthorizedCalled = false;
      final mockClient = MockClient((request) async {
        return http.Response(jsonEncode({'message': 'Session expired'}), 401);
      });

      final authStore = AuthStore(useMemoryOnly: true);
      await authStore.saveToken('expired_token');

      final apiClient = QuantApiClient(
        authStore: authStore,
        client: mockClient,
        onUnauthorized: () => unauthorizedCalled = true,
      );

      expect(() => apiClient.fetchStatus(), throwsA(isA<QuantApiException>()));
      await Future.delayed(const Duration(milliseconds: 20));
      expect(unauthorizedCalled, isTrue);
      expect(await authStore.hasToken(), isFalse);
    });

    test('PollingController single in-flight request lock prevents overlap', () async {
      int statusCallCount = 0;
      final mockClient = MockClient((request) async {
        if (request.url.path == '/api/status') {
          statusCallCount++;
          await Future.delayed(const Duration(milliseconds: 50));
          return http.Response(jsonEncode({'status': 'HEALTHY', 'positions': []}), 200);
        }
        return http.Response(jsonEncode({}), 200);
      });

      final authStore = AuthStore(useMemoryOnly: true);
      final apiClient = QuantApiClient(authStore: authStore, client: mockClient);
      final controller = PollingController(apiClient: apiClient);

      // Trigger two concurrent refreshStatus calls simultaneously
      final future1 = controller.refreshStatus();
      final future2 = controller.refreshStatus();

      await Future.wait([future1, future2]);

      // Only 1 network request should execute due to in-flight lock
      expect(statusCallCount, equals(1));
      controller.dispose();
    });
  });

  group('UI V2 Screen Widget Tests', () {
    testWidgets('LoginScreen renders institutional branding and fields', (tester) async {
      final authStore = AuthStore(useMemoryOnly: true);
      final apiClient = QuantApiClient(authStore: authStore);
      bool loginSucceeded = false;

      await tester.pumpWidget(
        MaterialApp(
          home: LoginScreen(
            apiClient: apiClient,
            onLoginSuccess: () => loginSucceeded = true,
          ),
        ),
      );

      expect(find.text('BINANCE QUANT PRO'), findsOneWidget);
      expect(find.text('OBSIDIAN QUANTS'), findsOneWidget);
      expect(find.text('UNKNOWN'), findsOneWidget);
      expect(find.text('XÁC THỰC VẬN HÀNH BẢO MẬT'), findsOneWidget);
      expect(find.text('CỔNG DỊCH VỤ (GATEWAY URL)'), findsOneWidget);
      expect(find.text('TÊN QUẢN TRỊ VIÊN'), findsOneWidget);
      expect(find.text('MẬT KHẨU'), findsOneWidget);
      expect(find.text('ĐĂNG NHẬP VẬN HÀNH'), findsOneWidget);
      expect(loginSucceeded, isFalse);
    });

    testWidgets('QuantHomeScreen mounts with 4 tabs and verifies retirement of Scanner/Copilot', (tester) async {
      final authStore = AuthStore(useMemoryOnly: true);
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'status': 'HEALTHY',
            'projection_source': 'EXECUTION_SERVICE',
            'is_paused': false,
            'halt_generation': 1,
            'balance': null,
            'realized_pnl': null,
            'positions': [],
          }),
          200,
        );
      });

      final apiClient = QuantApiClient(authStore: authStore, client: mockClient);
      final controller = PollingController(apiClient: apiClient);

      await tester.pumpWidget(
        MaterialApp(
          home: QuantHomeScreen(
            pollingController: controller,
            onLogout: () {},
          ),
        ),
      );
      await tester.pump();

      // 4-Tab bottom navigation items
      expect(find.text('TỔNG QUAN'), findsOneWidget);
      expect(find.text('VỊ THẾ'), findsOneWidget);
      expect(find.text('RỦI RO'), findsOneWidget);
      expect(find.text('HỆ THỐNG'), findsOneWidget);

      // Strict Retirement Check: Scanner and AI Copilot MUST NOT be present
      expect(find.text('SCANNER'), findsNothing);
      expect(find.text('AI COPILOT'), findsNothing);
      expect(find.text('ScannerTab'), findsNothing);
      expect(find.text('AiCopilotTab'), findsNothing);

      // Verify Tab switching
      await tester.tap(find.text('VỊ THẾ'));
      await tester.pump();

      await tester.tap(find.text('RỦI RO'));
      await tester.pump();

      await tester.tap(find.text('HỆ THỐNG'));
      await tester.pump();

      controller.dispose();
    });

    testWidgets('OverviewTab renders null balance as em-dash without fake numbers', (tester) async {
      final status = SystemStatus(
        status: 'HEALTHY',
        projectionSource: 'EXECUTION_SERVICE',
        balance: null,
        realizedPnl: null,
        openPositionsCount: 0,
        positions: [],
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: OverviewTab(
              status: status,
              onNavigateToPositions: () {},
            ),
          ),
        ),
      );

      // Check balance is strictly '—'
      expect(find.text('SỐ DƯ (BALANCE)'), findsOneWidget);
      expect(find.text('—'), findsWidgets);
      // Hard rule: Zero $1000 fake numbers
      expect(find.text('\$1,000.00'), findsNothing);
      expect(find.text('1000.0'), findsNothing);

      // Check empty positions message
      expect(find.text('Không có vị thế mở'), findsOneWidget);
      expect(find.text('Lõi giao dịch đang ở trạng thái flat (0 vị thế đang hoạt động).'), findsOneWidget);
    });

    testWidgets('PositionsTab and PositionDetailSheet are strictly read-only', (tester) async {
      final testPos = PositionView(
        symbol: 'BTCUSDT',
        side: 'LONG',
        qty: 0.05,
        entryPrice: 62000.0,
        markPrice: 62500.0,
        unrealizedPnl: 25.0,
        pnlPercent: 0.81,
        leverage: 5,
        margin: 620.0,
        stopLoss: 61000.0,
        takeProfit: 64000.0,
      );

      final status = SystemStatus(
        status: 'HEALTHY',
        positions: [testPos],
        openPositionsCount: 1,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PositionsTab(
              status: status,
              onRefresh: () async {},
            ),
          ),
        ),
      );

      expect(find.text('BTCUSDT'), findsOneWidget);
      expect(find.text('LONG'), findsOneWidget);
      expect(find.text('5x'), findsOneWidget);
      expect(find.text('VÔ HIỆU HÓA (PROHIBITED)'), findsOneWidget);

      // Tap to open PositionDetailSheet
      await tester.tap(find.text('BTCUSDT'));
      await tester.pumpAndSettle();

      expect(find.text('CHẾ ĐỘ XEM CHỈ ĐỌC (READ-ONLY)'), findsOneWidget);
      expect(find.text('Giá vào lệnh (Entry)'), findsOneWidget);
      expect(find.text('\$62,000.00'), findsNWidgets(2));

      // Prohibited: No BUY, SELL, or manual close buttons
      expect(find.text('BUY'), findsNothing);
      expect(find.text('SELL'), findsNothing);
      expect(find.text('ĐÓNG VỊ THẾ NGAY'), findsNothing);
    });

    testWidgets('RiskTab renders circuit breaker telemetry and Phase 3 guard notice', (tester) async {
      final status = SystemStatus(
        status: 'HEALTHY',
        isPaused: false,
        haltGeneration: 3,
        haltReason: 'None',
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RiskTab(status: status),
          ),
        ),
      );

      expect(find.text('TELEMETRY CẦU DAO RỦI RO'), findsOneWidget);
      expect(find.text('CẦU DAO SẴN SÀNG (ARMED)'), findsOneWidget);
      expect(find.text('KIỂM SOÁT THẾ HỆ HALT (CAS PROTOCOL)'), findsOneWidget);
      expect(find.text('HALT'), findsOneWidget);
      expect(find.text('RESUME'), findsOneWidget);
    });

    testWidgets('SystemTab displays full governance matrix and certification', (tester) async {
      final status = SystemStatus(status: 'HEALTHY');

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SystemTab(
              status: status,
              logs: ['[INFO] System initialized in OFFLINE mode.'],
              onRefreshLogs: () async {},
              onLogout: () async {},
            ),
          ),
        ),
      );

      // Hard Governance Matrix verification
      expect(find.text('MA TRẬN QUẢN TRỊ KIẾN TRÚC (GOVERNANCE)'), findsOneWidget);
      expect(find.text('REMOVED (0 credentials)'), findsOneWidget);
      expect(find.text('REMOVED'), findsOneWidget);
      expect(find.text('DISABLED'), findsWidgets);
      expect(find.text('NOT ENABLED'), findsOneWidget);
      expect(find.text('PROHIBITED'), findsOneWidget);

      // Certification verification
      expect(find.text('OFFLINE EXECUTION CORE ACCEPTED'), findsWidgets);
      expect(find.text('15/15 PRESERVED (0 MISMATCH)'), findsOneWidget);

      // Log verification
      expect(find.text('[INFO] System initialized in OFFLINE mode.'), findsOneWidget);
    });
  });
}
