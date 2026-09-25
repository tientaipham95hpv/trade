import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'ui_v2/screens/home_screen.dart';
import 'ui_v2/screens/login_screen.dart';
import 'ui_v2/services/auth_store.dart';
import 'ui_v2/services/polling_controller.dart';
import 'ui_v2/services/quant_api_client.dart';
import 'ui_v2/theme/quant_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Dark Institutional Status Bar theme
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      statusBarBrightness: Brightness.dark,
    ),
  );

  final authStore = AuthStore();
  final apiClient = QuantApiClient(authStore: authStore);
  final isAuthenticated = await authStore.hasToken() && await apiClient.checkAuth();

  runApp(BinanceQuantProApp(
    authStore: authStore,
    apiClient: apiClient,
    initialIsAuthenticated: isAuthenticated,
  ));
}

class BinanceQuantProApp extends StatefulWidget {
  final AuthStore? authStore;
  final QuantApiClient? apiClient;
  final PollingController? pollingController;
  final bool? initialIsAuthenticated;

  const BinanceQuantProApp({
    super.key,
    this.authStore,
    this.apiClient,
    this.pollingController,
    this.initialIsAuthenticated,
    dynamic apiService, // Compatibility parameter for legacy test invocation
  });

  @override
  State<BinanceQuantProApp> createState() => _BinanceQuantProAppState();
}

class _BinanceQuantProAppState extends State<BinanceQuantProApp> {
  late final AuthStore _authStore;
  late final QuantApiClient _apiClient;
  late final PollingController _pollingController;
  bool _isAuthenticated = false;

  @override
  void initState() {
    super.initState();
    _authStore = widget.authStore ?? AuthStore(useMemoryOnly: true);
    _apiClient = widget.apiClient ?? QuantApiClient(authStore: _authStore);
    _pollingController = widget.pollingController ?? PollingController(apiClient: _apiClient);

    _apiClient.onUnauthorized = () {
      if (mounted) {
        setState(() {
          _isAuthenticated = false;
        });
      }
    };

    if (widget.initialIsAuthenticated != null) {
      _isAuthenticated = widget.initialIsAuthenticated!;
    } else {
      _checkAuthStatus();
    }
  }

  Future<void> _checkAuthStatus() async {
    final hasToken = await _authStore.hasToken();
    if (!hasToken) {
      if (mounted && _isAuthenticated) {
        setState(() {
          _isAuthenticated = false;
        });
      }
      return;
    }

    final isValid = await _apiClient.checkAuth();
    if (mounted && _isAuthenticated != isValid) {
      setState(() {
        _isAuthenticated = isValid;
      });
    }
  }

  void _onLoginSuccess() {
    setState(() {
      _isAuthenticated = true;
    });
  }

  void _onLogout() {
    setState(() {
      _isAuthenticated = false;
    });
  }

  @override
  void dispose() {
    _pollingController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Binance Quant Pro',
      debugShowCheckedModeBanner: false,
      theme: QuantTheme.darkTheme,
      home: _isAuthenticated
          ? QuantHomeScreen(
              pollingController: _pollingController,
              onLogout: _onLogout,
            )
          : LoginScreen(
              apiClient: _apiClient,
              onLoginSuccess: _onLoginSuccess,
            ),
    );
  }
}
