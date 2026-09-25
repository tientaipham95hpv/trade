/// Safe nullable number parsers (Zero fake defaults)
double? safeNullableDouble(dynamic val) {
  if (val == null) return null;
  if (val is num) return val.toDouble();
  final str = val.toString().replaceAll('%', '').replaceAll('+', '').replaceAll('\$', '').trim();
  if (str.isEmpty || str == 'null' || str == '—') return null;
  return double.tryParse(str);
}

int? safeNullableInt(dynamic val) {
  if (val == null) return null;
  if (val is num) return val.toInt();
  final str = val.toString().replaceAll(RegExp(r'[^0-9\-]'), '').trim();
  if (str.isEmpty || str == 'null' || str == '—') return null;
  return int.tryParse(str);
}

/// Read-only presentation model for an active position.
class PositionView {
  final String symbol;
  final String side;
  final double? qty;
  final double? entryPrice;
  final double? markPrice;
  final double? unrealizedPnl;
  final double? pnlPercent;
  final int? leverage;
  final double? margin;
  final double? stopLoss;
  final double? takeProfit;
  final double? liquidationPrice;
  final String? protectionStatus;
  final String? state;
  final Map<String, dynamic>? raw;

  PositionView({
    required this.symbol,
    required this.side,
    this.qty,
    this.entryPrice,
    this.markPrice,
    this.unrealizedPnl,
    this.pnlPercent,
    this.leverage,
    this.margin,
    this.stopLoss,
    this.takeProfit,
    this.liquidationPrice,
    this.protectionStatus,
    this.state,
    this.raw,
  });

  bool get isLong => side.toUpperCase() == 'BUY' || side.toUpperCase() == 'LONG';
  bool get isShort => side.toUpperCase() == 'SELL' || side.toUpperCase() == 'SHORT';

  factory PositionView.fromJson(Map<String, dynamic> json, [String? explicitSymbol]) {
    final sym = explicitSymbol ?? json['symbol']?.toString() ?? 'UNKNOWN';
    final rawSide = (json['side'] ?? json['positionSide'] ?? 'LONG').toString().toUpperCase();
    final side = (rawSide == 'BUY' || rawSide == 'LONG') ? 'LONG' : 'SHORT';

    final entry = safeNullableDouble(json['entry_price'] ?? json['entryPrice']);
    final mark = safeNullableDouble(json['current_price'] ?? json['mark_price'] ?? json['markPrice']);
    final pnl = safeNullableDouble(json['unrealized_pnl'] ?? json['pnl_usdt'] ?? json['unRealizedProfit']);
    var pnlPct = safeNullableDouble(json['pnl_percent'] ?? json['percentage']);

    // Calculate percentage if missing but entry, mark and side are present
    if (pnlPct == null && entry != null && entry > 0 && mark != null) {
      if (side == 'LONG') {
        pnlPct = ((mark - entry) / entry) * 100.0;
      } else {
        pnlPct = ((entry - mark) / entry) * 100.0;
      }
    }

    String? protection;
    if (json['partial_tp_activated'] == true) {
      protection = 'BE Moved';
    } else if (json['trailing_active'] == true) {
      protection = 'Trailing';
    } else if (json['protection_status'] != null) {
      protection = json['protection_status'].toString();
    } else if (json['stop_loss'] != null || json['stopLoss'] != null) {
      protection = 'SL/TP Set';
    }

    return PositionView(
      symbol: sym,
      side: side,
      qty: safeNullableDouble(json['qty'] ?? json['amount'] ?? json['size'] ?? json['positionAmt']),
      entryPrice: entry,
      markPrice: mark,
      unrealizedPnl: pnl,
      pnlPercent: pnlPct,
      leverage: safeNullableInt(json['leverage']),
      margin: safeNullableDouble(json['margin'] ?? json['isolatedWallet']),
      stopLoss: safeNullableDouble(json['stop_loss'] ?? json['stopLoss']),
      takeProfit: safeNullableDouble(json['take_profit'] ?? json['takeProfit']),
      liquidationPrice: safeNullableDouble(json['liquidation_price'] ?? json['liquidationPrice']),
      protectionStatus: protection,
      state: json['state']?.toString() ?? json['status']?.toString() ?? 'OPEN',
      raw: json,
    );
  }
}
