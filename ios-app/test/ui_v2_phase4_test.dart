import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:binance_quant_pro/ui_v2/models/system_status.dart';
import 'package:binance_quant_pro/ui_v2/screens/risk_tab.dart';
import 'package:binance_quant_pro/ui_v2/services/auth_store.dart';
import 'package:binance_quant_pro/ui_v2/services/quant_api_client.dart';
import 'package:binance_quant_pro/ui_v2/widgets/environment_badge.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Phase 4 Model Tests (SystemStatus Environment & Resume Authority)', () {
    test('SystemStatus parses environment, recovery_required, and resume_allowed', () {
      final json = {
        'status': 'HALTED',
        'is_paused': true,
        'halt_generation': 4,
        'environment': 'OFFLINE',
        'recovery_required': false,
        'resume_allowed': true,
      };

      final status = SystemStatus.fromJson(json);
      expect(status.environment, equals('OFFLINE'));
      expect(status.recoveryRequired, isFalse);
      expect(status.resumeAllowed, isTrue);
      expect(status.isHalted, isTrue);
      expect(status.haltGeneration, equals(4));
    });

    test('SystemStatus derives resumeAllowed == false when recovery_required is true', () {
      final json = {
        'status': 'HALTED',
        'is_paused': true,
        'halt_generation': 4,
        'environment': 'TESTNET',
        'recovery_required': true,
      };

      final status = SystemStatus.fromJson(json);
      expect(status.environment, equals('TESTNET'));
      expect(status.recoveryRequired, isTrue);
      expect(status.resumeAllowed, isFalse);
    });

    test('SystemStatus.unknown defaults environment to null and resumeAllowed to false', () {
      final status = SystemStatus.unknown();
      expect(status.environment, isNull);
      expect(status.recoveryRequired, isFalse);
      expect(status.resumeAllowed, isFalse);
      expect(status.isUnknown, isTrue);
    });
  });

  group('Phase 4 QuantApiClient Operator Mutation Tests', () {
    test('sendHalt sends POST /api/pause with admin token and returns result', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/api/pause') {
          final body = jsonDecode(request.body);
          expect(body['reason'], equals('Testing Halt'));
          expect(body['source'], equals('flutter'));
          expect(request.headers['Authorization'], contains('test_admin_token'));
          return http.Response(
            jsonEncode({
              'success': true,
              'is_paused': true,
              'halt_generation': 5,
              'authoritative_state': 'HALTED',
            }),
            200,
          );
        }
        return http.Response('Not Found', 404);
      });

      final authStore = AuthStore(useMemoryOnly: true);
      await authStore.saveToken('test_admin_token');
      final apiClient = QuantApiClient(authStore: authStore, client: mockClient);

      final result = await apiClient.sendHalt(reason: 'Testing Halt');
      expect(result['success'], isTrue);
      expect(result['halt_generation'], equals(5));
      expect(result['authoritative_state'], equals('HALTED'));
    });

    test('sendHalt throws UNKNOWN_OUTCOME on transport timeout', () async {
      final mockClient = MockClient((request) async {
        await Future.delayed(const Duration(milliseconds: 100));
        return http.Response('timeout', 408);
      });

      final authStore = AuthStore(useMemoryOnly: true);
      final apiClient = QuantApiClient(
        authStore: authStore,
        client: mockClient,
        timeout: const Duration(milliseconds: 20),
      );

      try {
        await apiClient.sendHalt();
        fail('Should have thrown QuantApiException');
      } on QuantApiException catch (e) {
        expect(e.code, equals('UNKNOWN_OUTCOME'));
      }
    });

    test('sendHalt handles 403 Forbidden with permission denied message', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({'detail': 'Bạn không có quyền thực hiện thao tác này.'}),
          403,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      final authStore = AuthStore(useMemoryOnly: true);
      await authStore.saveToken('client_token');
      final apiClient = QuantApiClient(authStore: authStore, client: mockClient);

      try {
        await apiClient.sendHalt();
        fail('Should have thrown QuantApiException');
      } on QuantApiException catch (e) {
        expect(e.statusCode, equals(403));
        expect(e.message, contains('không có quyền'));
      }
    });

    test('sendResume validates expectedHaltGeneration > 0 before sending request', () async {
      final authStore = AuthStore(useMemoryOnly: true);
      final apiClient = QuantApiClient(authStore: authStore);

      try {
        await apiClient.sendResume(expectedHaltGeneration: 0);
        fail('Should have thrown QuantApiException');
      } on QuantApiException catch (e) {
        expect(e.code, equals('INVALID_HALT_GENERATION'));
      }

      try {
        await apiClient.sendResume(expectedHaltGeneration: -1);
        fail('Should have thrown QuantApiException');
      } on QuantApiException catch (e) {
        expect(e.code, equals('INVALID_HALT_GENERATION'));
      }
    });

    test('sendResume sends POST /api/resume with CAS generation and returns result', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/api/resume') {
          final body = jsonDecode(request.body);
          expect(body['expected_halt_generation'], equals(3));
          return http.Response(
            jsonEncode({
              'success': true,
              'is_paused': false,
              'authoritative_state': 'RESUMED',
            }),
            200,
          );
        }
        return http.Response('Not Found', 404);
      });

      final authStore = AuthStore(useMemoryOnly: true);
      await authStore.saveToken('test_admin_token');
      final apiClient = QuantApiClient(authStore: authStore, client: mockClient);

      final result = await apiClient.sendResume(expectedHaltGeneration: 3);
      expect(result['success'], isTrue);
      expect(result['authoritative_state'], equals('RESUMED'));
    });

    test('sendResume handles 409 STALE_HALT_GENERATION cleanly', () async {
      final mockClient = MockClient((request) async {
        return http.Response(
          jsonEncode({
            'success': false,
            'code': 'STALE_HALT_GENERATION',
            'current_generation': 4,
            'expected_generation': 3,
            'message': 'Thế hệ HALT đã thay đổi',
          }),
          409,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      final authStore = AuthStore(useMemoryOnly: true);
      final apiClient = QuantApiClient(authStore: authStore, client: mockClient);

      try {
        await apiClient.sendResume(expectedHaltGeneration: 3);
        fail('Should have thrown QuantApiException');
      } on QuantApiException catch (e) {
        expect(e.statusCode, equals(409));
        expect(e.code, equals('STALE_HALT_GENERATION'));
      }
    });
  });

  group('Phase 4 EnvironmentBadge Truth Tests', () {
    testWidgets('EnvironmentBadge renders UNKNOWN for null or empty input', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EnvironmentBadge.fromString(null),
          ),
        ),
      );
      expect(find.text('UNKNOWN'), findsOneWidget);
    });

    testWidgets('EnvironmentBadge renders TESTNET in gold', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EnvironmentBadge.fromString('TESTNET'),
          ),
        ),
      );
      expect(find.text('TESTNET'), findsOneWidget);
    });

    testWidgets('EnvironmentBadge renders LIVE in red', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: EnvironmentBadge.fromString('LIVE'),
          ),
        ),
      );
      expect(find.text('LIVE'), findsOneWidget);
    });
  });

  group('Phase 4 RiskTab Operator Action Widgets Tests', () {
    testWidgets('RiskTab disables RESUME when resumeAllowed is false', (tester) async {
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

      expect(find.text('HALT'), findsOneWidget);
      expect(find.text('RESUME'), findsOneWidget);
      expect(find.text('CLOSE ALL (KHÔNG KHẢ DỤNG)'), findsOneWidget);

      final closeAllButton = tester.widget<OutlinedButton>(
        find.ancestor(of: find.text('CLOSE ALL (KHÔNG KHẢ DỤNG)'), matching: find.byType(OutlinedButton)),
      );
      expect(closeAllButton.onPressed, isNull);

      final resumeButton = tester.widget<OutlinedButton>(
        find.ancestor(of: find.text('RESUME'), matching: find.byType(OutlinedButton)),
      );
      expect(resumeButton.onPressed, isNull);
    });

    testWidgets('RiskTab enables RESUME when status.resumeAllowed is true', (tester) async {
      final status = SystemStatus(
        status: 'HALTED',
        isPaused: true,
        haltGeneration: 2,
        resumeAllowed: true,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RiskTab(status: status),
          ),
        ),
      );

      final resumeButton = tester.widget<OutlinedButton>(
        find.ancestor(of: find.text('RESUME'), matching: find.byType(OutlinedButton)),
      );
      expect(resumeButton.onPressed, isNotNull);
    });

    testWidgets('RiskTab tapping HALT opens QuantConfirmSheet', (tester) async {
      final status = SystemStatus(
        status: 'HEALTHY',
        isPaused: false,
        haltGeneration: 1,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RiskTab(status: status),
          ),
        ),
      );

      await tester.tap(find.text('HALT'));
      await tester.pumpAndSettle();

      expect(find.text('XÁC NHẬN DỪNG KHẨN CẤP (HALT)'), findsOneWidget);
      expect(find.textContaining('GLOBAL'), findsOneWidget);
    });

    testWidgets('RiskTab tapping RESUME opens QuantConfirmSheet showing CAS generation', (tester) async {
      final status = SystemStatus(
        status: 'HALTED',
        isPaused: true,
        haltGeneration: 5,
        resumeAllowed: true,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: RiskTab(status: status),
          ),
        ),
      );

      await tester.tap(find.text('RESUME'));
      await tester.pumpAndSettle();

      expect(find.text('XÁC NHẬN KHÔI PHỤC (RESUME)'), findsOneWidget);
      expect(find.textContaining('EXECUTION_CORE'), findsOneWidget);
      expect(find.text('HALT GENERATION: 5'), findsOneWidget);
    });
  });
}
