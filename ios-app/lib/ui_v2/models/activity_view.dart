import 'position_view.dart';

/// Read-only trade history item.
class ActivityTradeItem {
  final String timestamp;
  final String symbol;
  final String side;
  final double? entryPrice;
  final double? exitPrice;
  final double? pnlUsdt;
  final double? pnlPercent;
  final String reason;
  final int? leverage;

  ActivityTradeItem({
    required this.timestamp,
    required this.symbol,
    required this.side,
    this.entryPrice,
    this.exitPrice,
    this.pnlUsdt,
    this.pnlPercent,
    this.reason = 'Đóng vị thế',
    this.leverage,
  });

  bool get isWin => pnlUsdt != null && pnlUsdt! > 0;
  bool get isLoss => pnlUsdt != null && pnlUsdt! < 0;

  factory ActivityTradeItem.fromJson(Map<String, dynamic> json) {
    return ActivityTradeItem(
      timestamp: json['timestamp']?.toString() ?? json['closed_at']?.toString() ?? '',
      symbol: json['symbol']?.toString() ?? 'UNKNOWN',
      side: (json['side'] ?? 'BUY').toString().toUpperCase(),
      entryPrice: safeNullableDouble(json['entry_price'] ?? json['entryPrice']),
      exitPrice: safeNullableDouble(json['exit_price'] ?? json['exitPrice']),
      pnlUsdt: safeNullableDouble(json['pnl_usdt'] ?? json['pnl']),
      pnlPercent: safeNullableDouble(json['pnl_percent']),
      reason: json['exit_reason']?.toString() ?? json['reason']?.toString() ?? 'Đóng vị thế',
      leverage: safeNullableInt(json['leverage']),
    );
  }
}

/// Aggregated history performance metrics.
class ActivitySummary {
  final int? totalTrades;
  final int? wins;
  final int? losses;
  final double? winRate;
  final double? netPnl;

  ActivitySummary({
    this.totalTrades,
    this.wins,
    this.losses,
    this.winRate,
    this.netPnl,
  });

  factory ActivitySummary.fromJson(Map<String, dynamic> json) {
    return ActivitySummary(
      totalTrades: safeNullableInt(json['total'] ?? json['total_trades']),
      wins: safeNullableInt(json['wins']),
      losses: safeNullableInt(json['losses']),
      winRate: safeNullableDouble(json['win_rate']),
      netPnl: safeNullableDouble(json['net_pnl']),
    );
  }
}

/// Composite history payload.
class ActivityData {
  final ActivitySummary summary;
  final List<ActivityTradeItem> trades;

  ActivityData({required this.summary, required this.trades});

  factory ActivityData.fromJson(Map<String, dynamic> json) {
    final sumJson = json['summary'] as Map<String, dynamic>? ?? {};
    final rawTrades = json['trades'] as List<dynamic>? ?? [];

    return ActivityData(
      summary: ActivitySummary.fromJson(sumJson),
      trades: rawTrades
          .whereType<Map<String, dynamic>>()
          .map((t) => ActivityTradeItem.fromJson(t))
          .toList(),
    );
  }

  factory ActivityData.empty() {
    return ActivityData(
      summary: ActivitySummary(),
      trades: const [],
    );
  }
}
