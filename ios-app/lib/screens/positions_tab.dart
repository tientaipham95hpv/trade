import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/models.dart';
import '../services/api_service.dart';

class PositionsTab extends StatelessWidget {
  final List<Position> positions;
  final ApiService apiService;
  final VoidCallback onRefresh;

  const PositionsTab({
    super.key,
    required this.positions,
    required this.apiService,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    if (positions.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.radar, size: 64, color: Colors.grey.shade700),
            const SizedBox(height: 12),
            const Text(
              'Không có vị thế nào đang mở',
              style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            const Text(
              'Hệ thống đang quét 80 cặp coin để tìm setup tối ưu...',
              style: TextStyle(color: Colors.grey, fontSize: 12),
            ),
          ],
        ),
      );
    }

    final currencyFmt = NumberFormat.currency(locale: 'en_US', symbol: '\$', decimalDigits: 4);

    return RefreshIndicator(
      color: const Color(0xFFF0B90B),
      onRefresh: () async => onRefresh(),
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: positions.length,
        separatorBuilder: (_, _) => const SizedBox(height: 12),
        itemBuilder: (context, index) {
          final pos = positions[index];
          final isLong = pos.side == 'BUY';
          final isPnlPositive = pos.pnlUsdt >= 0;
          final pnlColor = isPnlPositive ? const Color(0xFF0ECB81) : const Color(0xFFF6465D);

          return Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF10141E),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF1C2436), width: 1.2),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Header: Symbol & Side & Leverage
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Row(
                      children: [
                        Text(
                          pos.symbol,
                          style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold),
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
                            pos.side,
                            style: TextStyle(
                              color: isLong ? const Color(0xFF0ECB81) : const Color(0xFFF6465D),
                              fontSize: 10,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: Colors.grey.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            '${pos.leverage}x Isolated',
                            style: const TextStyle(color: Colors.grey, fontSize: 10, fontFamily: 'monospace'),
                          ),
                        ),
                      ],
                    ),
                    Text(
                      '${isPnlPositive ? '+' : ''}\$${pos.pnlUsdt.toStringAsFixed(2)} (${isPnlPositive ? '+' : ''}${pos.pnlPercent.toStringAsFixed(2)}%)',
                      style: TextStyle(color: pnlColor, fontSize: 14, fontWeight: FontWeight.bold, fontFamily: 'monospace'),
                    ),
                  ],
                ),

                const SizedBox(height: 12),
                const Divider(color: Color(0xFF1C2436), height: 1),
                const SizedBox(height: 12),

                // Prices Grid
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _priceColumn('GIÁ VÀO (ENTRY)', currencyFmt.format(pos.entryPrice), Colors.grey.shade300),
                    _priceColumn('GIÁ HIỆN TẠI', currencyFmt.format(pos.currentPrice), Colors.white),
                    _priceColumn('STOP LOSS', currencyFmt.format(pos.stopLoss), const Color(0xFFF6465D)),
                  ],
                ),

                const SizedBox(height: 10),

                // Multi-TP Info
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _priceColumn('TP1 (+1.0R / 33%)', currencyFmt.format(pos.takeProfit), const Color(0xFFF0B90B)),
                    _priceColumn('KÝ QUỸ', '\$${pos.margin.toStringAsFixed(2)} USDT', Colors.grey.shade400),
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFFF6465D).withValues(alpha: 0.2),
                        foregroundColor: const Color(0xFFF6465D),
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                          side: const BorderSide(color: Color(0xFFF6465D)),
                        ),
                      ),
                      onPressed: () => _confirmClose(context, pos.symbol),
                      child: const Text('ĐÓNG VỊ THẾ', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _priceColumn(String label, String value, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: Colors.grey, fontSize: 9, fontWeight: FontWeight.bold)),
        const SizedBox(height: 2),
        Text(value, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600, fontFamily: 'monospace')),
      ],
    );
  }

  void _confirmClose(BuildContext context, String symbol) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF10141E),
        title: Text('Đóng vị thế $symbol?', style: const TextStyle(color: Colors.white, fontSize: 16)),
        content: Text('Bạn có chắc chắn muốn đóng vị thế $symbol ngay lập tức theo giá thị trường?',
            style: const TextStyle(color: Colors.grey, fontSize: 13)),
        actions: [
          TextButton(
            child: const Text('HỦY BỎ', style: TextStyle(color: Colors.grey)),
            onPressed: () => Navigator.pop(ctx),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFF6465D)),
            child: const Text('XÁC NHẬN ĐÓNG', style: TextStyle(color: Colors.white)),
            onPressed: () async {
              Navigator.pop(ctx);
              await apiService.closePosition(symbol);
              onRefresh();
            },
          ),
        ],
      ),
    );
  }
}
