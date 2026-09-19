import 'dart:async';
import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';
import 'dashboard_tab.dart';
import 'positions_tab.dart';
import 'scanner_tab.dart';
import 'ai_copilot_tab.dart';
import 'settings_dialog.dart';

class HomeScreen extends StatefulWidget {
  final ApiService apiService;

  const HomeScreen({super.key, required this.apiService});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentIndex = 0;
  BotStatus? _status;
  Timer? _pollingTimer;

  @override
  void initState() {
    super.initState();
    _fetchData();
    _pollingTimer = Timer.periodic(const Duration(seconds: 4), (_) => _fetchData());
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchData() async {
    try {
      final res = await widget.apiService.fetchStatus();
      if (mounted) {
        setState(() => _status = res);
      }
    } catch (e) {
      debugPrint('Error polling status: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final tabs = [
      DashboardTab(status: _status, apiService: widget.apiService, onRefresh: _fetchData),
      PositionsTab(positions: _status?.positions ?? [], apiService: widget.apiService, onRefresh: _fetchData),
      ScannerTab(apiService: widget.apiService),
      AiCopilotTab(apiService: widget.apiService),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFF080A0F),
      appBar: AppBar(
        backgroundColor: const Color(0xFF10141E),
        elevation: 0,
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFFF0B90B).withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.bolt, color: Color(0xFFF0B90B), size: 18),
            ),
            const SizedBox(width: 8),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('BINANCE QUANT PRO', style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 0.5)),
                Text('iOS Terminal v1.0', style: TextStyle(color: Colors.grey, fontSize: 10, fontFamily: 'monospace')),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.tune, color: Colors.grey, size: 20),
            onPressed: () {
              showDialog(
                context: context,
                builder: (_) => SettingsDialog(apiService: widget.apiService, onSaved: _fetchData),
              );
            },
          ),
        ],
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(1),
          child: Container(color: const Color(0xFF1C2436), height: 1),
        ),
      ),
      body: IndexedStack(index: _currentIndex, children: tabs),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: Color(0xFF10141E),
          border: Border(top: BorderSide(color: Color(0xFF1C2436), width: 1)),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: (index) => setState(() => _currentIndex = index),
          backgroundColor: Colors.transparent,
          elevation: 0,
          type: BottomNavigationBarType.fixed,
          selectedItemColor: const Color(0xFFF0B90B),
          unselectedItemColor: Colors.grey.shade600,
          selectedFontSize: 10,
          unselectedFontSize: 10,
          selectedLabelStyle: const TextStyle(fontWeight: FontWeight.bold),
          items: [
            const BottomNavigationBarItem(icon: Icon(Icons.space_dashboard_outlined), activeIcon: Icon(Icons.space_dashboard), label: 'Tổng Quan'),
            BottomNavigationBarItem(
              icon: Badge(
                label: Text('${_status?.positions.length ?? 0}'),
                isLabelVisible: (_status?.positions.length ?? 0) > 0,
                backgroundColor: const Color(0xFF0ECB81),
                child: const Icon(Icons.candlestick_chart_outlined),
              ),
              activeIcon: const Icon(Icons.candlestick_chart),
              label: 'Vị Thế',
            ),
            const BottomNavigationBarItem(icon: Icon(Icons.radar_outlined), activeIcon: Icon(Icons.radar), label: 'Scanner 80'),
            const BottomNavigationBarItem(icon: Icon(Icons.psychology_outlined), activeIcon: Icon(Icons.psychology), label: 'AI Copilot'),
          ],
        ),
      ),
    );
  }
}
