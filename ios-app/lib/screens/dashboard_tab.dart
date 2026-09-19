import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../models/models.dart';
import '../services/api_service.dart';

class DashboardTab extends StatelessWidget {
  final BotStatus? status;
  final ApiService apiService;
  final VoidCallback onRefresh;

  const DashboardTab({
    super.key,
    required this.status,
    required this.apiService,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    if (status == null) {
      return const Center(
        child: CircularProgressIndicator(color: Color(0xFFF0B90B)),
      );
    }

    final currencyFmt = NumberFormat.currency(locale: 'en_US', symbol: '\$', decimalDigits: 2);
    final pnl = status!.unrealizedPnl;
    final isPnlPositive = pnl >= 0;
    final pnlColor = isPnlPositive ? const Color(0xFF0ECB81) : const Color(0xFFF6465D);

    return RefreshIndicator(
      color: const Color(0xFFF0B90B),
      onRefresh: () async => onRefresh(),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // 1. Balance & Unrealized PnL Hero Card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF141A27), Color(0xFF0E121A)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFF1C2436), width: 1.5),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    const Text(
                      'TỔNG VỐN KHẢ DỤNG',
                      style: TextStyle(color: Colors.grey, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF0B90B).withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: const Color(0xFFF0B90B).withValues(alpha: 0.3)),
                      ),
                      child: const Text(
                        'Binance Futures',
                        style: TextStyle(color: Color(0xFFF0B90B), fontSize: 10, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  currencyFmt.format(status!.balance),
                  style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.bold, fontFamily: 'monospace'),
                ),
                const SizedBox(height: 12),
                const Divider(color: Color(0xFF1C2436)),
                const SizedBox(height: 8),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('PnL Tạm Tính (Active)', style: TextStyle(color: Colors.grey, fontSize: 11)),
                        const SizedBox(height: 2),
                        Text(
                          '${isPnlPositive ? '+' : ''}${currencyFmt.format(pnl)} USDT',
                          style: TextStyle(color: pnlColor, fontSize: 15, fontWeight: FontWeight.bold, fontFamily: 'monospace'),
                        ),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        const Text('Vị Thế Đang Mở', style: TextStyle(color: Colors.grey, fontSize: 11)),
                        const SizedBox(height: 2),
                        Text(
                          '${status!.positions.length}/${status!.maxPositions}',
                          style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.bold, fontFamily: 'monospace'),
                        ),
                      ],
                    ),
                  ],
                ),
              ],
            ),
          ),

          const SizedBox(height: 14),

          // 2. BTC Trend Shield Banner
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(
              color: const Color(0xFF10141E),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: status!.btcRegime.contains('BULL')
                    ? const Color(0xFF0ECB81).withValues(alpha: 0.4)
                    : (status!.btcRegime.contains('BEAR')
                        ? const Color(0xFFF6465D).withValues(alpha: 0.4)
                        : const Color(0xFFF0B90B).withValues(alpha: 0.4)),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  status!.btcRegime.contains('BULL')
                      ? Icons.trending_up
                      : (status!.btcRegime.contains('BEAR') ? Icons.trending_down : Icons.compare_arrows),
                  color: status!.btcRegime.contains('BULL')
                      ? const Color(0xFF0ECB81)
                      : (status!.btcRegime.contains('BEAR') ? const Color(0xFFF6465D) : const Color(0xFFF0B90B)),
                  size: 28,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'BTC REGIME: ${status!.btcRegime}',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        status!.btcRegimeReason,
                        style: const TextStyle(color: Colors.grey, fontSize: 11),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 14),

          // 3. Mini Indicators Row (Fear & Greed + Circuit Breaker)
          Row(
            children: [
              Expanded(
                child: Container(
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
                          Icon(Icons.local_fire_department, color: Colors.orange, size: 16),
                          SizedBox(width: 4),
                          Text('FEAR & GREED', style: TextStyle(color: Colors.grey, fontSize: 10, fontWeight: FontWeight.bold)),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${status!.fearAndGreedValue}/100',
                        style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold, fontFamily: 'monospace'),
                      ),
                      Text(
                        status!.fearAndGreedClass,
                        style: const TextStyle(color: Colors.orange, fontSize: 11),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Container(
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
                          Icon(Icons.security, color: Color(0xFF0ECB81), size: 16),
                          SizedBox(width: 4),
                          Text('CẦU DAO VỐN', style: TextStyle(color: Colors.grey, fontSize: 10, fontWeight: FontWeight.bold)),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        status!.circuitBreakerTriggered ? 'COOLDOWN' : 'AN TOÀN',
                        style: TextStyle(
                          color: status!.circuitBreakerTriggered ? const Color(0xFFF6465D) : const Color(0xFF0ECB81),
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const Text(
                        'Ngưỡng ngắt: \$30/ngày',
                        style: TextStyle(color: Colors.grey, fontSize: 11),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 20),

          // 4. Quick Emergency Controls
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF10141E),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: const Color(0xFF1C2436)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'ĐIỀU KHIỂN CHIẾN LƯỢC NHANH',
                  style: TextStyle(color: Colors.grey, fontSize: 11, fontWeight: FontWeight.bold, letterSpacing: 1),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton.icon(
                        icon: Icon(status!.isPaused ? Icons.play_arrow : Icons.pause, size: 18),
                        label: Text(status!.isPaused ? 'BẬT LẠI BOT' : 'TẠM DỪNG BOT', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: status!.isPaused ? const Color(0xFF0ECB81) : Colors.amber.shade700,
                          foregroundColor: Colors.black,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        onPressed: () async {
                          await apiService.toggleBotPause(!status!.isPaused);
                          onRefresh();
                        },
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        icon: const Icon(Icons.warning, size: 18),
                        label: const Text('KILL-SWITCH', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFFF6465D),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        onPressed: () => _confirmEmergencyClose(context),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void _confirmEmergencyClose(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF10141E),
        title: const Row(
          children: [
            Icon(Icons.report_problem, color: Color(0xFFF6465D)),
            SizedBox(width: 8),
            Text('CẢNH BÁO KHẨN CẤP', style: TextStyle(color: Colors.white, fontSize: 16)),
          ],
        ),
        content: const Text(
          'Bạn có chắc chắn muốn kích hoạt KILL-SWITCH để đóng SẠCH TOÀN BỘ vị thế Binance ngay bây giờ?',
          style: TextStyle(color: Colors.grey, fontSize: 13),
        ),
        actions: [
          TextButton(
            child: const Text('HỦY BỎ', style: TextStyle(color: Colors.grey)),
            onPressed: () => Navigator.pop(ctx),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFF6465D)),
            child: const Text('XÁC NHẬN ĐÓNG SẠCH', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
            onPressed: () async {
              Navigator.pop(ctx);
              await apiService.emergencyCloseAll();
              onRefresh();
            },
          ),
        ],
      ),
    );
  }
}
