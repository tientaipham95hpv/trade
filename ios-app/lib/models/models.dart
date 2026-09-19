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
      entryPrice: (json['entry_price'] as num?)?.toDouble() ?? 0.0,
      currentPrice: (json['current_price'] as num?)?.toDouble() ?? (json['entry_price'] as num?)?.toDouble() ?? 0.0,
      stopLoss: (json['stop_loss'] as num?)?.toDouble() ?? 0.0,
      takeProfit: (json['take_profit'] as num?)?.toDouble() ?? 0.0,
      pnlUsdt: (json['pnl_usdt'] as num?)?.toDouble() ?? (json['unrealized_pnl'] as num?)?.toDouble() ?? 0.0,
      pnlPercent: (json['pnl_percent'] as num?)?.toDouble() ?? 0.0,
      margin: (json['margin'] as num?)?.toDouble() ?? 0.0,
      leverage: (json['leverage'] as num?)?.toInt() ?? 5,
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
      balance: (json['balance'] as num?)?.toDouble() ?? 1000.0,
      unrealizedPnl: (json['unrealized_pnl'] as num?)?.toDouble() ?? (json['total_unrealized_pnl'] as num?)?.toDouble() ?? 0.0,
      btcRegime: json['btc_regime'] ?? 'BULL',
      btcRegimeReason: json['btc_regime_reason'] ?? 'BTC Trend Shield',
      fearAndGreedValue: (fng['value'] as num?)?.toInt() ?? 50,
      fearAndGreedClass: fng['classification_vi'] ?? fng['value_classification'] ?? 'Trung Lập',
      circuitBreakerTriggered: cb['triggered'] == true,
      isPaused: json['is_paused'] == true,
      tradingMode: json['trading_mode'] ?? 'MARKET_ALL',
      positions: posList,
      maxPositions: (json['max_concurrent_positions'] as num?)?.toInt() ?? 3,
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
      price: (json['price'] as num?)?.toDouble() ?? 0.0,
      adx: (json['adx'] as num?)?.toDouble() ?? 25.0,
      rsi: (json['rsi'] as num?)?.toDouble() ?? 50.0,
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
