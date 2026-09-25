import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/models.dart';

class ApiService {
  static const String defaultServerUrl = 'https://trader.noza.site';
  String serverUrl = defaultServerUrl;
  String authToken = '';

  Future<void> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    serverUrl = prefs.getString('server_url') ?? defaultServerUrl;
    authToken = '';
    await prefs.remove('auth_token');
  }

  Future<void> saveSettings(String url, String token) async {
    final prefs = await SharedPreferences.getInstance();
    serverUrl = url.trim().replaceAll(RegExp(r'/+$'), '');
    authToken = token.trim();
    await prefs.setString('server_url', serverUrl);
    await prefs.remove('auth_token');
  }

  Future<bool> login([String? username, String? password]) async {
    if (username == null || username.trim().isEmpty || password == null || password.isEmpty) {
      return false;
    }
    try {
      final uri = Uri.parse('$serverUrl/api/login');
      final response = await http.post(
        uri,
        headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
        body: jsonEncode({'username': username, 'password': password}),
      ).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data['success'] == true && data['token'] != null) {
          authToken = data['token'].toString();
          return true;
        }
      }
    } catch (_) {}
    return false;
  }

  Map<String, String> _buildHeaders() {
    final headers = {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
    if (authToken.isNotEmpty) {
      headers['X-Session-Token'] = authToken;
      headers['Authorization'] = 'Bearer $authToken';
    }
    return headers;
  }

  Future<BotStatus> fetchStatus() async {
    if (authToken.isEmpty) {
      throw Exception('Yêu cầu đăng nhập quản trị rõ ràng');
    }
    final uri = Uri.parse('$serverUrl/api/status');
    var response = await http.get(uri, headers: _buildHeaders()).timeout(const Duration(seconds: 10));

    if (response.statusCode == 401) {
      authToken = '';
      throw Exception('Phiên đăng nhập đã hết hạn');
    }

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return BotStatus.fromJson(data);
    } else {
      throw Exception('Lỗi nạp trạng thái: HTTP ${response.statusCode}');
    }
  }

  Future<List<RadarPair>> fetchRadar() async {
    final uri = Uri.parse('$serverUrl/api/radar');
    final response = await http.get(uri, headers: _buildHeaders()).timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      final pairs = data['pairs'] as List<dynamic>? ?? [];
      return pairs.map((p) => RadarPair.fromJson(p as Map<String, dynamic>)).toList();
    }
    return [];
  }

  Future<bool> closePosition(String symbol) async {
    final uri = Uri.parse('$serverUrl/api/close_position?symbol=$symbol');
    final response = await http.post(uri, headers: _buildHeaders()).timeout(const Duration(seconds: 10));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['success'] == true;
    }
    return false;
  }

  Future<bool> emergencyCloseAll() async {
    final uri = Uri.parse('$serverUrl/api/close_all_positions');
    final response = await http.post(uri, headers: _buildHeaders()).timeout(const Duration(seconds: 10));
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['success'] == true;
    }
    return false;
  }

  Future<bool> toggleBotPause(bool pause) async {
    final action = pause ? 'pause' : 'resume';
    final uri = Uri.parse('$serverUrl/api/$action');
    final response = await http.post(uri, headers: _buildHeaders()).timeout(const Duration(seconds: 10));
    return response.statusCode == 200;
  }

  Future<bool> setTradingMode(String mode) async {
    final uri = Uri.parse('$serverUrl/api/update_settings');
    final response = await http.post(
      uri,
      headers: _buildHeaders(),
      body: jsonEncode({'trading_mode': mode}),
    ).timeout(const Duration(seconds: 10));
    return response.statusCode == 200;
  }

  Future<HistoryData> fetchHistory() async {
    if (authToken.isEmpty) {
      throw Exception('Yêu cầu đăng nhập quản trị rõ ràng');
    }
    final uri = Uri.parse('$serverUrl/api/history');
    var response = await http.get(uri, headers: _buildHeaders()).timeout(const Duration(seconds: 10));

    if (response.statusCode == 401) {
      authToken = '';
      throw Exception('Phiên đăng nhập đã hết hạn');
    }

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      return HistoryData.fromJson(data);
    } else {
      throw Exception('Lỗi nạp lịch sử: HTTP ${response.statusCode}');
    }
  }

  Future<String> askAiCopilot(String query) async {
    final uri = Uri.parse('$serverUrl/api/ai_chat');
    final response = await http.post(
      uri,
      headers: _buildHeaders(),
      body: jsonEncode({'query': query}),
    ).timeout(const Duration(seconds: 25));

    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['reply'] ?? data['response'] ?? 'Không có phản hồi từ AI.';
    } else {
      throw Exception('Lỗi AI Copilot: HTTP ${response.statusCode}');
    }
  }
}

