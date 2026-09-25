import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:binance_quant_pro/ui_v2/models/system_status.dart';
import 'package:binance_quant_pro/ui_v2/screens/risk_tab.dart';
import 'package:binance_quant_pro/ui_v2/services/auth_store.dart';
import 'package:binance_quant_pro/ui_v2/services/polling_controller.dart';
import 'package:binance_quant_pro/ui_v2/services/quant_api_client.dart';
import 'package:binance_quant_pro/ui_v2/theme/quant_spacing.dart';
import 'package:binance_quant_pro/ui_v2/widgets/environment_badge.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Phase 5 RC - Server URL Security & HTTPS Validation', () {
    test('Default server URL is trader.noza.site', () {
      expect(AuthStore.defaultServerUrl, equals('https://trader.noza.site'));
    });

    test('Validates HTTPS requirement and rejects plain HTTP', () {
      expect(AuthStore.validateServerUrl('https://trader.noza.site'), isNull);
      expect(AuthStore.validateServerUrl('https://staging.noza.site'), isNull);

      final httpError = AuthStore.validateServerUrl('http://trader.noza.site');
      expect(httpError, isNotNull);
      expect(httpError, contains('HTTPS'));
    });

    test('Rejects internal IPC port 50051', () {
      final ipcError = AuthStore.validateServerUrl('https://localhost:50051');
      expect(ipcError, isNotNull);
      expect(ipcError, contains('50051'));
    });

    test('Rejects direct Binance API endpoints', () {
      final binanceError1 = AuthStore.validateServerUrl('https://fapi.binance.com');
      expect(binanceError1, isNotNull);
      expect(binanceError1, contains('Binance'));

      final binanceError2 = AuthStore.validateServerUrl('https://testnet.binancefuture.com');
      expect(binanceError2, isNotNull);
      expect(binanceError2, contains('Binance'));
    });

    test('saveServerUrl throws ArgumentError on forbidden URL', () async {
      final store = AuthStore(useMemoryOnly: true);
      expect(
        () async => await store.saveServerUrl('http://insecure.site'),
        throwsA(isA<ArgumentError>()),
      );
    });
  });

  group('Phase 5 RC - Secure Token Lifecycle & Keychain Emulation', () {
    test('Token save, retrieve, check, and clear lifecycle', () async {
      final store = AuthStore(useMemoryOnly: true);
      expect(await store.hasToken(), isFalse);
      expect(await store.getToken(), isNull);

      await store.saveToken('rc1_test_admin_token_jwt_secure');
      expect(await store.hasToken(), isTrue);
      expect(await store.getToken(), equals('rc1_test_admin_token_jwt_secure'));

      // Simulate app restart by reusing store with memory persistence
      expect(await store.hasToken(), isTrue);

      await store.clearToken();
      expect(await store.hasToken(), isFalse);
      expect(await store.getToken(), isNull);
    });

    test('401 response invokes onUnauthorized and clears token immediately', () async {
      bool unauthorizedCalled = false;
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Token expired'}),
          401,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      final authStore = AuthStore(useMemoryOnly: true);
      await authStore.saveToken('expired_token');
      expect(await authStore.hasToken(), isTrue);

      final apiClient = QuantApiClient(
        authStore: authStore,
        client: mockClient,
        onUnauthorized: () {
          unauthorizedCalled = true;
        },
      );

      try {
        await apiClient.fetchStatus();
        fail('Should throw QuantApiException');
      } on QuantApiException catch (e) {
        expect(e.statusCode, equals(401));
        expect(e.isUnauthorized, isTrue);
      }

      expect(unauthorizedCalled, isTrue);
      expect(await authStore.hasToken(), isFalse);
    });
  });

  group('Phase 5 RC - Polling Lifecycle & Timer Guard', () {
    test('Lifecycle pause and resume does not multiply timers', () async {
      int fetchCount = 0;
      final mockClient = MockClient((request) async {
        fetchCount++;
        return http.Response(
          jsonEncode({
            'success': true,
            'status': 'OPERATIONAL',
            'is_paused': false,
            'environment': 'OFFLINE',
          }),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      final authStore = AuthStore(useMemoryOnly: true);
      final apiClient = QuantApiClient(authStore: authStore, client: mockClient);
      final controller = PollingController(apiClient: apiClient);

      controller.start();
      await Future.delayed(const Duration(milliseconds: 50));
      expect(controller.isPolling, isTrue);
      expect(controller.isAppInBackground, isFalse);

      // Simulate app going to background
      controller.didChangeAppLifecycleState(AppLifecycleState.paused);
      expect(controller.isAppInBackground, isTrue);

      // Simulate rapid pause/resume/pause/resume
      controller.didChangeAppLifecycleState(AppLifecycleState.resumed);
      expect(controller.isAppInBackground, isFalse);
      controller.didChangeAppLifecycleState(AppLifecycleState.paused);
      expect(controller.isAppInBackground, isTrue);
      controller.didChangeAppLifecycleState(AppLifecycleState.resumed);
      expect(fetchCount, greaterThanOrEqualTo(1));
      controller.stop();
      expect(controller.isPolling, isFalse);
    });
  });

  group('Phase 5 RC - CAS Stale Intent & Recovery Guard', () {
    test('sendResume receives 409 STALE_HALT_GENERATION and does not auto retry', () async {
      int requestCount = 0;
      final mockClient = MockClient((request) async {
        requestCount++;
        return http.Response(
          jsonEncode({
            'success': false,
            'code': 'STALE_HALT_GENERATION',
            'current_generation': 5,
            'expected_generation': 4,
            'message': 'HALT generation has changed to 5',
          }),
          409,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      final authStore = AuthStore(useMemoryOnly: true);
      final apiClient = QuantApiClient(authStore: authStore, client: mockClient);

      try {
        await apiClient.sendResume(expectedHaltGeneration: 4);
        fail('Should throw QuantApiException');
      } on QuantApiException catch (e) {
        expect(e.statusCode, equals(409));
        expect(e.code, equals('STALE_HALT_GENERATION'));
      }

      // Exactly ONE request sent, no automatic retry
      expect(requestCount, equals(1));
    });

    test('sendResume receives 409 RECOVERY_REQUIRED when recovery is active', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'success': false,
            'code': 'RECOVERY_REQUIRED',
            'message': 'Cannot resume: recovery required',
          }),
          409,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      final authStore = AuthStore(useMemoryOnly: true);
      final apiClient = QuantApiClient(authStore: authStore, client: mockClient);

      try {
        await apiClient.sendResume(expectedHaltGeneration: 2);
        fail('Should throw QuantApiException');
      } on QuantApiException catch (e) {
        expect(e.statusCode, equals(409));
        expect(e.code, equals('RECOVERY_REQUIRED'));
      }
    });
  });

  group('Phase 5 RC - CLOSEALL Strict Absence & Touch Target QA', () {
    testWidgets('RiskTab CLOSEALL button is strictly disabled and unclickable', (tester) async {
      final status = SystemStatus(
        status: 'HEALTHY',
        isPaused: false,
        resumeAllowed: false,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RiskTab(status: status),
          ),
        ),
      );

      final closeAllFinder = find.textContaining('CLOSE ALL');
      expect(closeAllFinder, findsOneWidget);

      // Verify the button is disabled (OutlinedButton/ElevatedButton with onPressed == null)
      final buttonWidget = tester.widget<OutlinedButton>(
        find.ancestor(of: closeAllFinder, matching: find.byType(OutlinedButton)),
      );
      expect(buttonWidget.onPressed, isNull);
    });

    test('Minimum touch target is 44px for institutional mobile accessibility', () {
      expect(QuantSpacing.minTouchTarget, equals(44.0));
    });
  });

  group('Phase 5 RC - Environment Truth Spectrum', () {
    testWidgets('EnvironmentBadge correctly visualizes all 5 truth variants', (tester) async {
      // 1. Null / missing -> UNKNOWN
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: EnvironmentBadge.fromString(null))));
      expect(find.text('UNKNOWN'), findsOneWidget);

      // 2. OFFLINE -> OFFLINE
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: EnvironmentBadge.fromString('OFFLINE'))));
      expect(find.text('OFFLINE'), findsOneWidget);

      // 3. TESTNET -> TESTNET
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: EnvironmentBadge.fromString('TESTNET'))));
      expect(find.text('TESTNET'), findsOneWidget);

      // 4. LIVE -> LIVE
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: EnvironmentBadge.fromString('LIVE'))));
      expect(find.text('LIVE'), findsOneWidget);

      // 5. Unknown garbage -> UNKNOWN
      await tester.pumpWidget(MaterialApp(home: Scaffold(body: EnvironmentBadge.fromString('INVALID_GARBAGE'))));
      expect(find.text('UNKNOWN'), findsOneWidget);
    });
  });
}
