import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Secure Storage for Operator Session Tokens.
/// Backed by iOS Keychain with graceful test/memory fallback.
class AuthStore {
  static const String defaultServerUrl = 'https://trader.noza.site';
  static const String _tokenKey = 'quant_session_token';
  static const String _urlKey = 'quant_server_url';

  final FlutterSecureStorage _storage;
  final Map<String, String> _memoryStore = {};
  bool _useMemoryStore;

  AuthStore({
    FlutterSecureStorage? storage,
    bool useMemoryOnly = false,
  })  : _storage = storage ??
            const FlutterSecureStorage(
              iOptions: IOSOptions(accessibility: KeychainAccessibility.first_unlock),
            ),
        _useMemoryStore = useMemoryOnly;

  /// Retrieve the stored session token.
  Future<String?> getToken() async {
    if (_useMemoryStore) {
      return _memoryStore[_tokenKey];
    }
    try {
      return await _storage.read(key: _tokenKey);
    } catch (_) {
      _useMemoryStore = true;
      return _memoryStore[_tokenKey];
    }
  }

  /// Securely persist session token.
  Future<void> saveToken(String token) async {
    final cleanToken = token.trim();
    if (_useMemoryStore) {
      _memoryStore[_tokenKey] = cleanToken;
      return;
    }
    try {
      await _storage.write(key: _tokenKey, value: cleanToken);
    } catch (_) {
      _useMemoryStore = true;
      _memoryStore[_tokenKey] = cleanToken;
    }
  }

  /// Delete session token upon logout or 401 unauthenticated response.
  Future<void> clearToken() async {
    if (_useMemoryStore) {
      _memoryStore.remove(_tokenKey);
      return;
    }
    try {
      await _storage.delete(key: _tokenKey);
    } catch (_) {
      _useMemoryStore = true;
      _memoryStore.remove(_tokenKey);
    }
  }

  /// Retrieve configured server URL.
  Future<String> getServerUrl() async {
    if (_useMemoryStore) {
      return _memoryStore[_urlKey] ?? defaultServerUrl;
    }
    try {
      final url = await _storage.read(key: _urlKey);
      return (url != null && url.trim().isNotEmpty) ? url.trim() : defaultServerUrl;
    } catch (_) {
      _useMemoryStore = true;
      return _memoryStore[_urlKey] ?? defaultServerUrl;
    }
  }

  /// Validate that the server URL is HTTPS and does not point to internal IPC or direct Binance.
  static String? validateServerUrl(String? url) {
    if (url == null || url.trim().isEmpty) {
      return 'Vui lòng nhập Gateway URL';
    }
    final trimmed = url.trim().toLowerCase();
    if (!trimmed.startsWith('https://')) {
      return 'URL phải sử dụng giao thức bảo mật HTTPS (https://)';
    }
    if (trimmed.contains('50051')) {
      return 'Không được phép trỏ trực tiếp vào cổng nội bộ IPC (50051)';
    }
    if (trimmed.contains('binance.com') || trimmed.contains('binancefuture') || trimmed.contains('binance.vision')) {
      return 'Không được phép trỏ trực tiếp vào máy chủ sàn Binance';
    }
    return null;
  }

  /// Persist configured server URL.
  Future<void> saveServerUrl(String url) async {
    final validationError = validateServerUrl(url);
    if (validationError != null) {
      throw ArgumentError(validationError);
    }
    final clean = url.trim().replaceAll(RegExp(r'/+$'), '');
    if (_useMemoryStore) {
      _memoryStore[_urlKey] = clean;
      return;
    }
    try {
      await _storage.write(key: _urlKey, value: clean);
    } catch (_) {
      _useMemoryStore = true;
      _memoryStore[_urlKey] = clean;
    }
  }

  /// Check whether an operator token is currently held.
  Future<bool> hasToken() async {
    final token = await getToken();
    return token != null && token.isNotEmpty;
  }
}
