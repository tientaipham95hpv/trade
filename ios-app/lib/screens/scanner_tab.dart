import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';

class ScannerTab extends StatefulWidget {
  final ApiService apiService;

  const ScannerTab({super.key, required this.apiService});

  @override
  State<ScannerTab> createState() => _ScannerTabState();
}

class _ScannerTabState extends State<ScannerTab> {
  List<RadarPair> _pairs = [];
  bool _loading = true;
  String _searchQuery = '';

  @override
  void initState() {
    super.initState();
    _loadRadar();
  }

  Future<void> _loadRadar() async {
    setState(() => _loading = true);
    try {
      final res = await widget.apiService.fetchRadar();
      setState(() {
        _pairs = res;
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _pairs.where((p) => p.symbol.toLowerCase().contains(_searchQuery.toLowerCase())).toList();

    return Column(
      children: [
        // Search Bar
        Padding(
          padding: const EdgeInsets.all(16),
          child: TextField(
            style: const TextStyle(color: Colors.white, fontSize: 13),
            decoration: InputDecoration(
              hintText: 'Tìm kiếm coin (vd: BTC, ETH, SOL)...',
              hintStyle: const TextStyle(color: Colors.grey, fontSize: 13),
              prefixIcon: const Icon(Icons.search, color: Color(0xFFF0B90B), size: 20),
              filled: true,
              fillColor: const Color(0xFF10141E),
              contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: 16),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFF1C2436))),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFF1C2436))),
              focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFFF0B90B))),
            ),
            onChanged: (val) => setState(() => _searchQuery = val),
          ),
        ),

        // Pairs List
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator(color: Color(0xFFF0B90B)))
              : RefreshIndicator(
                  color: const Color(0xFFF0B90B),
                  onRefresh: _loadRadar,
                  child: ListView.separated(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    itemCount: filtered.length,
                    separatorBuilder: (_, _) => const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final pair = filtered[index];
                      final isLong = pair.signal == 'BUY' || pair.trend == 'UP';

                      return Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        decoration: BoxDecoration(
                          color: const Color(0xFF10141E),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFF1C2436)),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(pair.symbol, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                                const SizedBox(height: 2),
                                Text('\$${pair.price.toStringAsFixed(4)}', style: const TextStyle(color: Colors.grey, fontSize: 12, fontFamily: 'monospace')),
                              ],
                            ),
                            Row(
                              children: [
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.end,
                                  children: [
                                    Text('ADX ${pair.adx.toStringAsFixed(1)}', style: const TextStyle(color: Color(0xFF00F0FF), fontSize: 11, fontFamily: 'monospace')),
                                    Text('RSI ${pair.rsi.toStringAsFixed(1)}', style: const TextStyle(color: Colors.grey, fontSize: 10, fontFamily: 'monospace')),
                                  ],
                                ),
                                const SizedBox(width: 12),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                  decoration: BoxDecoration(
                                    color: isLong ? const Color(0xFF0ECB81).withValues(alpha: 0.15) : const Color(0xFFF6465D).withValues(alpha: 0.15),
                                    borderRadius: BorderRadius.circular(6),
                                    border: Border.all(
                                      color: isLong ? const Color(0xFF0ECB81).withValues(alpha: 0.4) : const Color(0xFFF6465D).withValues(alpha: 0.4),
                                    ),
                                  ),
                                  child: Text(
                                    isLong ? 'LONG ▲' : 'SHORT ▼',
                                    style: TextStyle(
                                      color: isLong ? const Color(0xFF0ECB81) : const Color(0xFFF6465D),
                                      fontSize: 11,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
        ),
      ],
    );
  }
}
