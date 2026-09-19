import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';

class HistoryTab extends StatefulWidget {
  final ApiService apiService;

  const HistoryTab({super.key, required this.apiService});

  @override
  State<HistoryTab> createState() => _HistoryTabState();
}

class _HistoryTabState extends State<HistoryTab> {
  HistoryData? _data;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final res = await widget.apiService.fetchHistory();
      if (mounted) {
        setState(() {
          _data = res;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading && _data == null) {
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFFF0B90B)),
      );
    }

    if (_error != null && _data == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: Color(0xFFF6465D), size: 40),
              const SizedBox(height: 12),
              Text(
                'Lỗi kết nối lịch sử:\n$_error',
                textAlign: TextAlign.center,
                style: const TextStyle(color: Colors.white, fontSize: 13, fontFamily: 'monospace'),
              ),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFF0B90B), foregroundColor: Colors.black),
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text('Thử Lại'),
                onPressed: _loadHistory,
              ),
            ],
          ),
        ),
      );
    }

    final summary = _data?.summary;
    final trades = _data?.trades ?? [];

    return RefreshIndicator(
      color: const Color(0xFFF0B90B),
      backgroundColor: const Color(0xFF10141E),
      onRefresh: _loadHistory,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          // KPI Performance Summary Cards
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFF10141E),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF1C2436)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Row(
                  children: [
                    Icon(Icons.query_stats, color: Color(0xFFF0B90B), size: 18),
                    SizedBox(width: 8),
                    Text(
                      'HIỆU SUẤT GIAO DỊCH',
                      style: TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.bold, letterSpacing: 0.5),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Row(
                  children: [
                    // Total trades
                    Expanded(
                      child: _buildKpiBox(
                        label: 'LỆNH ĐÃ ĐÓNG',
                        value: '${summary?.total ?? 0}',
                        subtext: '${summary?.wins ?? 0} Thắng / ${summary?.losses ?? 0} Thua',
                        valColor: Colors.white,
                      ),
                    ),
                    const SizedBox(width: 10),
                    // Win Rate
                    Expanded(
                      child: _buildKpiBox(
                        label: 'TỶ LỆ THẮNG',
                        value: '${(summary?.winRate ?? 0).toStringAsFixed(1)}%',
                        subtext: 'Target ≥ 65%',
                        valColor: (summary?.winRate ?? 0) >= 50 ? const Color(0xFF0ECB81) : const Color(0xFFF6465D),
                      ),
                    ),
                    const SizedBox(width: 10),
                    // Net PnL
                    Expanded(
                      child: _buildKpiBox(
                        label: 'LÃI RÒNG',
                        value: '${(summary?.netPnl ?? 0) >= 0 ? '+' : ''}\$${(summary?.netPnl ?? 0).toStringAsFixed(2)}',
                        subtext: 'Lũy kế USDT',
                        valColor: (summary?.netPnl ?? 0) >= 0 ? const Color(0xFF0ECB81) : const Color(0xFFF6465D),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),

          // Header Lịch sử lệnh
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'LỊCH SỬ LỆNH GẦN ĐÂY (${trades.length})',
                style: const TextStyle(color: Colors.grey, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 0.5),
              ),
              IconButton(
                icon: const Icon(Icons.refresh, color: Colors.grey, size: 18),
                onPressed: _loadHistory,
                tooltip: 'Làm mới',
              ),
            ],
          ),
          const SizedBox(height: 6),

          // Danh sách lệnh
          if (trades.isEmpty)
            Container(
              padding: const EdgeInsets.symmetric(vertical: 40),
              alignment: Alignment.center,
              child: Column(
                children: [
                  Icon(Icons.history_toggle_off, color: Colors.grey.shade700, size: 48),
                  const SizedBox(height: 8),
                  const Text('Chưa có lệnh nào trong lịch sử', style: TextStyle(color: Colors.grey, fontSize: 12)),
                ],
              ),
            )
          else
            ...trades.map((t) => _buildTradeCard(t)),
        ],
      ),
    );
  }

  Widget _buildKpiBox({
    required String label,
    required String value,
    required String subtext,
    required Color valColor,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF080A0F),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF1C2436)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: Colors.grey, fontSize: 9, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              value,
              style: TextStyle(color: valColor, fontSize: 15, fontWeight: FontWeight.bold, fontFamily: 'monospace'),
            ),
          ),
          const SizedBox(height: 2),
          Text(subtext, style: const TextStyle(color: Colors.grey, fontSize: 9, fontFamily: 'monospace')),
        ],
      ),
    );
  }

  Widget _buildTradeCard(ClosedTrade t) {
    final isLong = t.side.contains('BUY') || t.side.contains('LONG');
    final isWin = t.pnlUsdt >= 0;
    final pnlColor = isWin ? const Color(0xFF0ECB81) : const Color(0xFFF6465D);
    final prefix = isWin ? '+' : '';

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF10141E),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF1C2436)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Symbol, Side, PnL
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Text(
                    t.symbol,
                    style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: isLong ? const Color(0xFF0ECB81).withValues(alpha: 0.15) : const Color(0xFFF6465D).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(
                        color: isLong ? const Color(0xFF0ECB81).withValues(alpha: 0.4) : const Color(0xFFF6465D).withValues(alpha: 0.4),
                      ),
                    ),
                    child: Text(
                      isLong ? 'LONG' : 'SHORT',
                      style: TextStyle(
                        color: isLong ? const Color(0xFF0ECB81) : const Color(0xFFF6465D),
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    '${t.leverage}x',
                    style: const TextStyle(color: Colors.grey, fontSize: 10, fontFamily: 'monospace'),
                  ),
                ],
              ),
              Text(
                '$prefix\$${t.pnlUsdt.toStringAsFixed(2)} ($prefix${t.pnlPercent.toStringAsFixed(2)}%)',
                style: TextStyle(color: pnlColor, fontSize: 13, fontWeight: FontWeight.bold, fontFamily: 'monospace'),
              ),
            ],
          ),
          const SizedBox(height: 8),

          // Price details
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Vào: \$${t.entryPrice.toStringAsFixed(4)} → Đóng: \$${t.exitPrice.toStringAsFixed(4)}',
                style: const TextStyle(color: Colors.grey, fontSize: 11, fontFamily: 'monospace'),
              ),
              if (t.timestamp.isNotEmpty)
                Text(
                  t.timestamp.split(' ').length > 1 ? t.timestamp.split(' ')[1] : t.timestamp,
                  style: const TextStyle(color: Colors.grey, fontSize: 10, fontFamily: 'monospace'),
                ),
            ],
          ),
          if (t.exitReason.isNotEmpty) ...[
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFF080A0F),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                'Lý do: ${t.exitReason}',
                style: const TextStyle(color: Colors.grey, fontSize: 10, fontStyle: FontStyle.italic),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
