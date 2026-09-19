import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'services/api_service.dart';
import 'screens/home_screen.dart';

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

class BinanceQuantProApp extends StatelessWidget {
  final ApiService apiService;

  const BinanceQuantProApp({super.key, required this.apiService});

  @override
  Widget build(BuildContext context) {
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
      home: HomeScreen(apiService: apiService),
    );
  }
}
