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
  String _activeFilter = 'ALL'; // ALL, LONG, SHORT, ADX25
  bool _isSwitchingMode = false;

  @override
  void initState() {
    super.initState();
    _loadRadar();
  }

  Future<void> _loadRadar() async {
    setState(() => _loading = true);
    try {
      final res = await widget.apiService.fetchRadar();
      if (mounted) {
        setState(() {
          _pairs = res;
          _loading = false;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _switchTradingMode(String mode) async {
    setState(() => _isSwitchingMode = true);
    try {
      await widget.apiService.setTradingMode(mode);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(mode == 'BLUECHIP_ONLY' ? 'Đã đổi sang chế độ BLUECHIP (BTC/ETH)' : 'Đã đổi sang chế độ QUÉT TOP 80 COIN'),
            duration: const Duration(seconds: 2),
            backgroundColor: const Color(0xFF10141E),
          ),
        );
      }
      await _loadRadar();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Lỗi đổi chế độ: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isSwitchingMode = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isBluechip = _pairs.length <= 6 && _pairs.any((p) => p.symbol.contains('BTC'));

    final filtered = _pairs.where((p) {
      final matchesSearch = p.symbol.toLowerCase().contains(_searchQuery.toLowerCase());
      if (!matchesSearch) return false;

      if (_activeFilter == 'LONG') {
        return p.signal == 'BUY' || p.trend == 'UP';
      } else if (_activeFilter == 'SHORT') {
        return p.signal == 'SELL' || p.trend == 'DOWN';
      } else if (_activeFilter == 'ADX25') {
        return p.adx >= 25.0;
      }
      return true;
    }).toList();

    return Column(
      children: [
        // Mode Switcher Header
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: const BoxDecoration(
            color: Color(0xFF10141E),
            border: Border(bottom: BorderSide(color: Color(0xFF1C2436))),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'CHẾ ĐỘ QUÉT THỊ TRƯỜNG',
                    style: TextStyle(color: Colors.grey, fontSize: 10, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                  ),
                  if (_isSwitchingMode)
                    const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFFF0B90B)),
                    )
                  else
                    Text(
                      'Đang hiển thị ${_pairs.length} coin',
                      style: const TextStyle(color: Color(0xFFF0B90B), fontSize: 10, fontFamily: 'monospace', fontWeight: FontWeight.bold),
                    ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: GestureDetector(
                      onTap: () => _switchTradingMode('MARKET_ALL'),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        decoration: BoxDecoration(
                          color: !isBluechip ? const Color(0xFFF0B90B).withValues(alpha: 0.15) : const Color(0xFF080A0F),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: !isBluechip ? const Color(0xFFF0B90B).withValues(alpha: 0.5) : const Color(0xFF1C2436),
                          ),
                        ),
                        alignment: Alignment.center,
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.radar, size: 14, color: !isBluechip ? const Color(0xFFF0B90B) : Colors.grey),
                            const SizedBox(width: 6),
                            Text(
                              'TOP 80 COIN',
                              style: TextStyle(
                                color: !isBluechip ? const Color(0xFFF0B90B) : Colors.grey,
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: GestureDetector(
                      onTap: () => _switchTradingMode('BLUECHIP_ONLY'),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 8),
                        decoration: BoxDecoration(
                          color: isBluechip ? const Color(0xFFF0B90B).withValues(alpha: 0.15) : const Color(0xFF080A0F),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: isBluechip ? const Color(0xFFF0B90B).withValues(alpha: 0.5) : const Color(0xFF1C2436),
                          ),
                        ),
                        alignment: Alignment.center,
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.shield_outlined, size: 14, color: isBluechip ? const Color(0xFFF0B90B) : Colors.grey),
                            const SizedBox(width: 6),
                            Text(
                              'BLUECHIP (BTC/ETH)',
                              style: TextStyle(
                                color: isBluechip ? const Color(0xFFF0B90B) : Colors.grey,
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),

        // Search Bar
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
          child: TextField(
            style: const TextStyle(color: Colors.white, fontSize: 13, fontFamily: 'monospace'),
            decoration: InputDecoration(
              hintText: 'Tìm kiếm coin (vd: BTC, SOL, DOGE)...',
              hintStyle: const TextStyle(color: Colors.grey, fontSize: 12),
              prefixIcon: const Icon(Icons.search, color: Color(0xFFF0B90B), size: 18),
              suffixIcon: _searchQuery.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear, color: Colors.grey, size: 16),
                      onPressed: () => setState(() => _searchQuery = ''),
                    )
                  : null,
              filled: true,
              fillColor: const Color(0xFF10141E),
              contentPadding: const EdgeInsets.symmetric(vertical: 0, horizontal: 16),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1C2436))),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1C2436))),
              focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFFF0B90B))),
            ),
            onChanged: (val) => setState(() => _searchQuery = val),
          ),
        ),

        // Filter Chips
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: [
              _buildFilterChip('TẤT CẢ', 'ALL'),
              const SizedBox(width: 6),
              _buildFilterChip('CHỈ LONG ▲', 'LONG'),
              const SizedBox(width: 6),
              _buildFilterChip('CHỈ SHORT ▼', 'SHORT'),
              const SizedBox(width: 6),
              _buildFilterChip('ADX ≥ 25', 'ADX25'),
            ],
          ),
        ),
        const SizedBox(height: 6),

        // Pairs List
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator(color: Color(0xFFF0B90B)))
              : RefreshIndicator(
                  color: const Color(0xFFF0B90B),
                  backgroundColor: const Color(0xFF10141E),
                  onRefresh: _loadRadar,
                  child: filtered.isEmpty
                      ? ListView(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(vertical: 60),
                              alignment: Alignment.center,
                              child: Column(
                                children: [
                                  Icon(Icons.satellite_alt_outlined, color: Colors.grey.shade700, size: 48),
                                  const SizedBox(height: 10),
                                  Text(
                                    isBluechip
                                        ? 'Đang ở chế độ BLUECHIP (Chỉ 4 cặp chính).\nNhấn "TOP 80 COIN" ở trên để quét toàn thị trường!'
                                        : 'Không tìm thấy coin nào phù hợp bộ lọc.',
                                    textAlign: TextAlign.center,
                                    style: const TextStyle(color: Colors.grey, fontSize: 12),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          itemCount: filtered.length,
                          separatorBuilder: (_, _) => const SizedBox(height: 8),
                          itemBuilder: (context, index) {
                            final pair = filtered[index];
                            final isLong = pair.signal == 'BUY' || pair.trend == 'UP';
                            final isShort = pair.signal == 'SELL' || pair.trend == 'DOWN';

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
                                      Text(
                                        '\$${pair.price >= 1 ? pair.price.toStringAsFixed(2) : pair.price.toStringAsFixed(4)}',
                                        style: const TextStyle(color: Colors.grey, fontSize: 12, fontFamily: 'monospace'),
                                      ),
                                    ],
                                  ),
                                  Row(
                                    children: [
                                      Column(
                                        crossAxisAlignment: CrossAxisAlignment.end,
                                        children: [
                                          Text(
                                            'ADX ${pair.adx.toStringAsFixed(1)}',
                                            style: const TextStyle(color: Color(0xFF00F0FF), fontSize: 11, fontFamily: 'monospace', fontWeight: FontWeight.bold),
                                          ),
                                          Text(
                                            'RSI ${pair.rsi.toStringAsFixed(1)}',
                                            style: const TextStyle(color: Colors.grey, fontSize: 10, fontFamily: 'monospace'),
                                          ),
                                        ],
                                      ),
                                      const SizedBox(width: 12),
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                        decoration: BoxDecoration(
                                          color: isLong
                                              ? const Color(0xFF0ECB81).withValues(alpha: 0.15)
                                              : (isShort ? const Color(0xFFF6465D).withValues(alpha: 0.15) : Colors.grey.withValues(alpha: 0.15)),
                                          borderRadius: BorderRadius.circular(6),
                                          border: Border.all(
                                            color: isLong
                                                ? const Color(0xFF0ECB81).withValues(alpha: 0.4)
                                                : (isShort ? const Color(0xFFF6465D).withValues(alpha: 0.4) : Colors.grey.withValues(alpha: 0.4)),
                                          ),
                                        ),
                                        child: Text(
                                          isLong ? 'LONG ▲' : (isShort ? 'SHORT ▼' : 'CHỜ •'),
                                          style: TextStyle(
                                            color: isLong
                                                ? const Color(0xFF0ECB81)
                                                : (isShort ? const Color(0xFFF6465D) : Colors.grey),
                                            fontSize: 10,
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

  Widget _buildFilterChip(String label, String value) {
    final isSelected = _activeFilter == value;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() => _activeFilter = value),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 6),
          decoration: BoxDecoration(
            color: isSelected ? const Color(0xFFF0B90B).withValues(alpha: 0.2) : const Color(0xFF080A0F),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: isSelected ? const Color(0xFFF0B90B).withValues(alpha: 0.5) : const Color(0xFF1C2436),
            ),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: TextStyle(
              color: isSelected ? const Color(0xFFF0B90B) : Colors.grey,
              fontSize: 9,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      ),
    );
  }
}
