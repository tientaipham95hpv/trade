import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'services/api_service.dart';
import 'screens/home_screen.dart';
import 'ui_v2/screens/home_screen.dart' as v2;
import 'ui_v2/screens/login_screen.dart';
import 'ui_v2/services/auth_store.dart';
import 'ui_v2/services/polling_controller.dart';
import 'ui_v2/services/quant_api_client.dart';
import 'ui_v2/theme/quant_theme.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Set iOS Status Bar theme to light text (for dark background)
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
      statusBarBrightness: Brightness.dark,
    ),
  );

  final apiService = ApiService();
  await apiService.loadSettings();

  runApp(BinanceQuantProApp(apiService: apiService));
}

class BinanceQuantProApp extends StatefulWidget {
  final ApiService? apiService;
  final AuthStore? authStore;
  final QuantApiClient? apiClient;
  final PollingController? pollingController;
  final bool? initialIsAuthenticated;
  final bool useV2;

  const BinanceQuantProApp({
    super.key,
    this.apiService,
    this.authStore,
    this.apiClient,
    this.pollingController,
    this.initialIsAuthenticated,
    this.useV2 = false,
  });

  @override
  State<BinanceQuantProApp> createState() => _BinanceQuantProAppState();
}

class _BinanceQuantProAppState extends State<BinanceQuantProApp> {
  late final ApiService _apiService;
  AuthStore? _authStore;
  QuantApiClient? _apiClient;
  PollingController? _pollingController;
  bool _isAuthenticated = false;

  @override
  void initState() {
    super.initState();
    _apiService = widget.apiService ?? ApiService();

    if (widget.useV2) {
      _authStore = widget.authStore ?? AuthStore(useMemoryOnly: true);
      _apiClient = widget.apiClient ?? QuantApiClient(authStore: _authStore!);
      _pollingController = widget.pollingController ?? PollingController(apiClient: _apiClient!);

      _apiClient!.onUnauthorized = () {
        if (mounted) {
          setState(() {
            _isAuthenticated = false;
          });
        }
      };

      if (widget.initialIsAuthenticated != null) {
        _isAuthenticated = widget.initialIsAuthenticated!;
      }
    }
  }

  @override
  void dispose() {
    _pollingController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.useV2) {
      return MaterialApp(
        title: 'Binance Quant Pro',
        debugShowCheckedModeBanner: false,
        theme: QuantTheme.darkTheme,
        home: _isAuthenticated
            ? v2.QuantHomeScreen(
                pollingController: _pollingController!,
                onLogout: () => setState(() => _isAuthenticated = false),
              )
            : LoginScreen(
                apiClient: _apiClient!,
                onLoginSuccess: () => setState(() => _isAuthenticated = true),
              ),
      );
    }

    // Giao diện gốc (Classic 5-tab iOS Terminal)
    return MaterialApp(
      title: 'Binance Quant Pro',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF080A0F),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFFF0B90B),
          surface: Color(0xFF10141E),
        ),
        fontFamily: 'SF Pro Display',
        useMaterial3: true,
      ),
      home: HomeScreen(apiService: _apiService),
    );
  }
}
