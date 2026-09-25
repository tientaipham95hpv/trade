import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/activity_view.dart';
import '../models/system_status.dart';
import 'auth_store.dart';

/// Structured API Exception
class QuantApiException implements Exception {
  final String message;
  final int? statusCode;
  final String? code;
  final bool isUnauthorized;

  QuantApiException({
    required this.message,
    this.statusCode,
    this.code,
    this.isUnauthorized = false,
  });

  @override
  String toString() => 'QuantApiException: $message (status: $statusCode, code: $code)';
}

/// Centralized HTTP Client for Obsidian Quants Operator Console.
/// Sourced exclusively via Application Gateway (https://trader.noza.site).
/// Zero direct connections to Binance, Execution Service (port 50051), or SQLite.
class QuantApiClient {
  final AuthStore authStore;
  final http.Client _client;
  final Duration timeout;
  void Function()? onUnauthorized;

  QuantApiClient({
    required this.authStore,
    http.Client? client,
    this.timeout = const Duration(seconds: 8),
    this.onUnauthorized,
  }) : _client = client ?? http.Client();

  Future<Map<String, String>> _buildHeaders() async {
    final headers = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
    final token = await authStore.getToken();
    if (token != null && token.isNotEmpty) {
      headers['X-Session-Token'] = token;
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  /// Verify session token against /api/check_auth.
  Future<bool> checkAuth() async {
    try {
      final baseUrl = await authStore.getServerUrl();
      final uri = Uri.parse('$baseUrl/api/check_auth');
      final headers = await _buildHeaders();
      final response = await _client.get(uri, headers: headers).timeout(timeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['authenticated'] == true;
      }
    } catch (_) {}
    return false;
  }

  /// Authenticate operator via /api/login.
  Future<bool> login(String username, String password) async {
    final cleanUser = username.trim();
    final cleanPass = password.trim();
    if (cleanUser.isEmpty || cleanPass.isEmpty) {
      throw QuantApiException(message: 'Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu');
    }

    final baseUrl = await authStore.getServerUrl();
    final uri = Uri.parse('$baseUrl/api/login');

    try {
      final response = await _client
          .post(
            uri,
            headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
            body: jsonEncode({'username': cleanUser, 'password': cleanPass}),
          )
          .timeout(timeout);

      final data = jsonDecode(response.body);

      if (response.statusCode == 200 && data['success'] == true) {
        final token = data['token']?.toString();
        if (token != null && token.isNotEmpty) {
          await authStore.saveToken(token);
          return true;
        }
      } else if (response.statusCode == 429) {
        throw QuantApiException(
          message: data['message']?.toString() ?? 'Quá nhiều lần đăng nhập thất bại. Thử lại sau.',
          statusCode: 429,
          code: 'LOGIN_RATE_LIMITED',
        );
      } else if (response.statusCode == 401) {
        throw QuantApiException(
          message: data['message']?.toString() ?? 'Sai tên đăng nhập hoặc mật khẩu quản trị',
          statusCode: 401,
          code: 'INVALID_CREDENTIALS',
        );
      } else {
        throw QuantApiException(
          message: data['message']?.toString() ?? 'Đăng nhập không thành công (HTTP ${response.statusCode})',
          statusCode: response.statusCode,
        );
      }
    } on QuantApiException {
      rethrow;
    } catch (e) {
      throw QuantApiException(message: 'Không thể kết nối đến máy chủ quản trị: $e');
    }

    return false;
  }

  /// Revoke session via /api/logout and clear secure storage.
  Future<void> logout() async {
    try {
      final baseUrl = await authStore.getServerUrl();
      final uri = Uri.parse('$baseUrl/api/logout');
      final headers = await _buildHeaders();
      await _client.post(uri, headers: headers).timeout(const Duration(seconds: 4));
    } catch (_) {}
    await authStore.clearToken();
  }

  /// Fetch authoritative telemetry snapshot via /api/status.
  Future<SystemStatus> fetchStatus() async {
    final baseUrl = await authStore.getServerUrl();
    final uri = Uri.parse('$baseUrl/api/status');
    final headers = await _buildHeaders();

    http.Response response;
    try {
      response = await _client.get(uri, headers: headers).timeout(timeout);
    } catch (e) {
      throw QuantApiException(message: 'Lỗi mạng khi tải trạng thái hệ thống: $e');
    }

    if (response.statusCode == 401) {
      await authStore.clearToken();
      onUnauthorized?.call();
      throw QuantApiException(
        message: 'Phiên đăng nhập quản trị đã hết hạn (401)',
        statusCode: 401,
        isUnauthorized: true,
      );
    }

    if (response.statusCode == 200 || response.statusCode == 503) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return SystemStatus.fromJson(data);
      } catch (e) {
        throw QuantApiException(message: 'Phản hồi trạng thái không hợp lệ: $e');
      }
    }

    throw QuantApiException(
      message: 'Không thể tải trạng thái: HTTP ${response.statusCode}',
      statusCode: response.statusCode,
    );
  }

  /// Fetch closed trades and performance metrics via /api/history.
  Future<ActivityData> fetchHistory() async {
    final baseUrl = await authStore.getServerUrl();
    final uri = Uri.parse('$baseUrl/api/history');
    final headers = await _buildHeaders();

    http.Response response;
    try {
      response = await _client.get(uri, headers: headers).timeout(timeout);
    } catch (e) {
      throw QuantApiException(message: 'Lỗi mạng khi tải lịch sử giao dịch: $e');
    }

    if (response.statusCode == 401) {
      await authStore.clearToken();
      onUnauthorized?.call();
      throw QuantApiException(
        message: 'Phiên đăng nhập quản trị đã hết hạn (401)',
        statusCode: 401,
        isUnauthorized: true,
      );
    }

    if (response.statusCode == 200) {
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return ActivityData.fromJson(data);
      } catch (e) {
        throw QuantApiException(message: 'Phản hồi lịch sử không hợp lệ: $e');
      }
    }

    return ActivityData.empty();
  }

  /// Fetch operator audit logs via /api/logs.
  Future<List<String>> fetchLogs({int lines = 80}) async {
    final baseUrl = await authStore.getServerUrl();
    final uri = Uri.parse('$baseUrl/api/logs?lines=$lines');
    final headers = await _buildHeaders();

    http.Response response;
    try {
      response = await _client.get(uri, headers: headers).timeout(timeout);
    } catch (e) {
      return ['[NETWORK_ERROR] Không thể kết nối để lấy logs: $e'];
    }

    if (response.statusCode == 401) {
      await authStore.clearToken();
      onUnauthorized?.call();
      return ['[UNAUTHORIZED] Phiên đăng nhập hết hạn'];
    }

    if (response.statusCode == 200) {
      try {
        final data = jsonDecode(response.body);
        if (data is Map && data['lines'] is List) {
          return (data['lines'] as List).map((l) => l.toString()).toList();
        }
      } catch (_) {}
    }

    return [];
  }

  /// Durably halt entries via /api/pause with admin authentication.
  Future<Map<String, dynamic>> sendHalt({String? reason, String source = 'flutter'}) async {
    final baseUrl = await authStore.getServerUrl();
    final uri = Uri.parse('$baseUrl/api/pause');
    final headers = await _buildHeaders();

    http.Response response;
    try {
      response = await _client
          .post(
            uri,
            headers: headers,
            body: jsonEncode({
              'reason': reason ?? 'Flutter operator manual halt',
              'source': source,
            }),
          )
          .timeout(timeout);
    } on TimeoutException {
      throw QuantApiException(
        message: 'Lỗi Timeout (UNKNOWN_OUTCOME): Mất kết nối khi gửi lệnh HALT. Vui lòng kiểm tra trạng thái trước khi thao tác lại.',
        code: 'UNKNOWN_OUTCOME',
      );
    } catch (e) {
      throw QuantApiException(
        message: 'Lỗi mạng khi gửi lệnh HALT (UNKNOWN_OUTCOME): $e',
        code: 'UNKNOWN_OUTCOME',
      );
    }

    if (response.statusCode == 401) {
      await authStore.clearToken();
      onUnauthorized?.call();
      throw QuantApiException(
        message: 'Yêu cầu đăng nhập tài khoản quản trị hệ thống bot (401)',
        statusCode: 401,
        isUnauthorized: true,
      );
    }

    if (response.statusCode == 403) {
      throw QuantApiException(
        message: 'Bạn không có quyền thực hiện thao tác này.',
        statusCode: 403,
        code: 'FORBIDDEN',
      );
    }

    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200 && data['success'] == true) {
        return data;
      }
      throw QuantApiException(
        message: data['message']?.toString() ?? 'Lỗi khi kích hoạt HALT',
        statusCode: response.statusCode,
        code: data['code']?.toString(),
      );
    } catch (e) {
      if (e is QuantApiException) rethrow;
      throw QuantApiException(
        message: 'Phản hồi không hợp lệ từ máy chủ: ${response.body}',
        statusCode: response.statusCode,
      );
    }
  }

  /// Durably resume entries via /api/resume requiring expected_halt_generation CAS match.
  Future<Map<String, dynamic>> sendResume({
    required int expectedHaltGeneration,
    String source = 'flutter',
  }) async {
    if (expectedHaltGeneration <= 0) {
      throw QuantApiException(
        message: 'Thế hệ HALT không hợp lệ (phải > 0)',
        statusCode: 400,
        code: 'INVALID_HALT_GENERATION',
      );
    }

    final baseUrl = await authStore.getServerUrl();
    final uri = Uri.parse('$baseUrl/api/resume');
    final headers = await _buildHeaders();

    http.Response response;
    try {
      response = await _client
          .post(
            uri,
            headers: headers,
            body: jsonEncode({
              'expected_halt_generation': expectedHaltGeneration,
              'source': source,
            }),
          )
          .timeout(timeout);
    } on TimeoutException {
      throw QuantApiException(
        message: 'Lỗi Timeout (UNKNOWN_OUTCOME): Mất kết nối khi gửi lệnh RESUME. Vui lòng kiểm tra trạng thái trước khi thao tác lại.',
        code: 'UNKNOWN_OUTCOME',
      );
    } catch (e) {
      throw QuantApiException(
        message: 'Lỗi mạng khi gửi lệnh RESUME (UNKNOWN_OUTCOME): $e',
        code: 'UNKNOWN_OUTCOME',
      );
    }

    if (response.statusCode == 401) {
      await authStore.clearToken();
      onUnauthorized?.call();
      throw QuantApiException(
        message: 'Yêu cầu đăng nhập tài khoản quản trị hệ thống bot (401)',
        statusCode: 401,
        isUnauthorized: true,
      );
    }

    if (response.statusCode == 403) {
      throw QuantApiException(
        message: 'Bạn không có quyền thực hiện thao tác này.',
        statusCode: 403,
        code: 'FORBIDDEN',
      );
    }

    try {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200 && data['success'] == true) {
        return data;
      }
      throw QuantApiException(
        message: data['message']?.toString() ?? 'Lỗi khi kích hoạt RESUME',
        statusCode: response.statusCode,
        code: data['code']?.toString(),
      );
    } catch (e) {
      if (e is QuantApiException) rethrow;
      throw QuantApiException(
        message: 'Phản hồi không hợp lệ từ máy chủ: ${response.body}',
        statusCode: response.statusCode,
      );
    }
  }
}
