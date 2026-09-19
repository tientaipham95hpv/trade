double safeParseDouble(dynamic val, [double fallback = 0.0]) {
  if (val == null) return fallback;
  if (val is num) return val.toDouble();
  final str = val.toString().replaceAll('%', '').replaceAll('+', '').replaceAll('\$', '').trim();
  return double.tryParse(str) ?? fallback;
}

int safeParseInt(dynamic val, [int fallback = 0]) {
  if (val == null) return fallback;
  if (val is num) return val.toInt();
  final str = val.toString().replaceAll(RegExp(r'[^0-9\-]'), '').trim();
  return int.tryParse(str) ?? fallback;
}

class Position {
  final String symbol;
  final String side;
  final double entryPrice;
  final double currentPrice;
  final double stopLoss;
  final double takeProfit;
  final double pnlUsdt;
  final double pnlPercent;
  final double margin;
  final int leverage;

  Position({
    required this.symbol,
    required this.side,
    required this.entryPrice,
    required this.currentPrice,
    required this.stopLoss,
    required this.takeProfit,
    required this.pnlUsdt,
    required this.pnlPercent,
    required this.margin,
    required this.leverage,
  });

  factory Position.fromJson(Map<String, dynamic> json) {
    return Position(
      symbol: json['symbol'] ?? 'UNKNOWN',
      side: (json['side'] ?? 'BUY').toString().toUpperCase(),
      entryPrice: safeParseDouble(json['entry_price']),
      currentPrice: safeParseDouble(json['current_price'], safeParseDouble(json['entry_price'])),
      stopLoss: safeParseDouble(json['stop_loss']),
      takeProfit: safeParseDouble(json['take_profit']),
      pnlUsdt: safeParseDouble(json['pnl_usdt'], safeParseDouble(json['unrealized_pnl'])),
      pnlPercent: safeParseDouble(json['pnl_percent']),
      margin: safeParseDouble(json['margin']),
      leverage: safeParseInt(json['leverage'], 5),
    );
  }
}

class BotStatus {
  final double balance;
  final double unrealizedPnl;
  final String btcRegime;
  final String btcRegimeReason;
  final int fearAndGreedValue;
  final String fearAndGreedClass;
  final bool circuitBreakerTriggered;
  final bool isPaused;
  final String tradingMode;
  final List<Position> positions;
  final int maxPositions;

  BotStatus({
    required this.balance,
    required this.unrealizedPnl,
    required this.btcRegime,
    required this.btcRegimeReason,
    required this.fearAndGreedValue,
    required this.fearAndGreedClass,
    required this.circuitBreakerTriggered,
    required this.isPaused,
    required this.tradingMode,
    required this.positions,
    required this.maxPositions,
  });

  factory BotStatus.fromJson(Map<String, dynamic> json) {
    var rawPositions = json['positions'] as List<dynamic>? ?? [];
    List<Position> posList = rawPositions.map((p) => Position.fromJson(p as Map<String, dynamic>)).toList();

    var fng = json['fear_and_greed'] as Map<String, dynamic>? ?? {};
    var cb = json['circuit_breaker'] as Map<String, dynamic>? ?? {};

    return BotStatus(
      balance: safeParseDouble(json['balance'], 1000.0),
      unrealizedPnl: safeParseDouble(json['unrealized_pnl'], safeParseDouble(json['total_unrealized_pnl'], 0.0)),
      btcRegime: json['btc_regime'] ?? 'BULL',
      btcRegimeReason: json['btc_regime_reason'] ?? 'BTC Trend Shield',
      fearAndGreedValue: safeParseInt(fng['value'], 50),
      fearAndGreedClass: fng['classification_vi'] ?? fng['value_classification'] ?? 'Trung Lập',
      circuitBreakerTriggered: cb['triggered'] == true,
      isPaused: json['is_paused'] == true,
      tradingMode: json['trading_mode'] ?? 'MARKET_ALL',
      positions: posList,
      maxPositions: safeParseInt(json['max_concurrent_positions'], 3),
    );
  }
}

class RadarPair {
  final String symbol;
  final String trend;
  final String signal;
  final double price;
  final double adx;
  final double rsi;

  RadarPair({
    required this.symbol,
    required this.trend,
    required this.signal,
    required this.price,
    required this.adx,
    required this.rsi,
  });

  factory RadarPair.fromJson(Map<String, dynamic> json) {
    return RadarPair(
      symbol: json['symbol'] ?? '',
      trend: json['trend'] ?? 'NEUTRAL',
      signal: json['signal'] ?? 'HOLD',
      price: safeParseDouble(json['price']),
      adx: safeParseDouble(json['adx'], 25.0),
      rsi: safeParseDouble(json['rsi'], 50.0),
    );
  }
}

class ChatMessage {
  final String sender;
  final String text;
  final bool isUser;
  final DateTime timestamp;

  ChatMessage({
    required this.sender,
    required this.text,
    required this.isUser,
    required this.timestamp,
  });
}

class ClosedTrade {
  final String timestamp;
  final String symbol;
  final String side;
  final double entryPrice;
  final double exitPrice;
  final double pnlUsdt;
  final double pnlPercent;
  final String exitReason;
  final int leverage;

  ClosedTrade({
    required this.timestamp,
    required this.symbol,
    required this.side,
    required this.entryPrice,
    required this.exitPrice,
    required this.pnlUsdt,
    required this.pnlPercent,
    required this.exitReason,
    required this.leverage,
  });

  factory ClosedTrade.fromJson(Map<String, dynamic> json) {
    return ClosedTrade(
      timestamp: json['timestamp'] ?? json['closed_at'] ?? '',
      symbol: json['symbol'] ?? 'UNKNOWN',
      side: (json['side'] ?? 'BUY').toString().toUpperCase(),
      entryPrice: safeParseDouble(json['entry_price']),
      exitPrice: safeParseDouble(json['exit_price']),
      pnlUsdt: safeParseDouble(json['pnl_usdt']),
      pnlPercent: safeParseDouble(json['pnl_percent']),
      exitReason: json['exit_reason'] ?? json['reason'] ?? 'Đóng vị thế',
      leverage: safeParseInt(json['leverage'], 5),
    );
  }
}

class HistorySummary {
  final int total;
  final int wins;
  final int losses;
  final double winRate;
  final double netPnl;

  HistorySummary({
    required this.total,
    required this.wins,
    required this.losses,
    required this.winRate,
    required this.netPnl,
  });

  factory HistorySummary.fromJson(Map<String, dynamic> json) {
    return HistorySummary(
      total: safeParseInt(json['total']),
      wins: safeParseInt(json['wins']),
      losses: safeParseInt(json['losses']),
      winRate: safeParseDouble(json['win_rate']),
      netPnl: safeParseDouble(json['net_pnl']),
    );
  }
}

class HistoryData {
  final HistorySummary summary;
  final List<ClosedTrade> trades;

  HistoryData({required this.summary, required this.trades});

  factory HistoryData.fromJson(Map<String, dynamic> json) {
    final sumJson = json['summary'] as Map<String, dynamic>? ?? {};
    final tradesList = json['trades'] as List<dynamic>? ?? [];
    return HistoryData(
      summary: HistorySummary.fromJson(sumJson),
      trades: tradesList.map((t) => ClosedTrade.fromJson(t as Map<String, dynamic>)).toList(),
    );
  }
}
