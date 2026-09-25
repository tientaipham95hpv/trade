/// Obsidian Quants Institutional Number and Text Formatters
/// Strict adherence to zero fake values: null or unverified values strictly format as '—'.
class QuantFormatters {
  static const String emDash = '—';

  /// Format currency with thousands separators. Returns '—' for null.
  static String formatCurrency(num? value, {int decimals = 2, String symbol = '\$'}) {
    if (value == null) return emDash;
    final isNegative = value < 0;
    final absVal = value.abs();
    final parts = absVal.toStringAsFixed(decimals).split('.');
    final integerPart = _addCommas(parts[0]);
    final decimalPart = parts.length > 1 ? '.${parts[1]}' : '';
    return '${isNegative ? '-' : ''}$symbol$integerPart$decimalPart';
  }

  /// Format PnL with explicit '+' or '-' sign. Returns '—' for null.
  static String formatPnl(num? value, {int decimals = 2, String symbol = '\$'}) {
    if (value == null) return emDash;
    if (value > 0) {
      final formatted = formatCurrency(value, decimals: decimals, symbol: symbol);
      return '+$formatted';
    } else if (value < 0) {
      return formatCurrency(value, decimals: decimals, symbol: symbol);
    } else {
      return '${symbol}0.${'0' * decimals}';
    }
  }

  /// Format percentage with optional sign. Returns '—' for null.
  static String formatPercent(num? value, {int decimals = 2, bool showPlusSign = true}) {
    if (value == null) return emDash;
    final sign = (showPlusSign && value > 0) ? '+' : '';
    return '$sign${value.toStringAsFixed(decimals)}%';
  }

  /// Format quantity or generic number with max decimals. Returns '—' for null.
  static String formatNumber(num? value, {int maxDecimals = 6, bool trimTrailingZeros = true}) {
    if (value == null) return emDash;
    var str = value.toStringAsFixed(maxDecimals);
    if (trimTrailingZeros && str.contains('.')) {
      str = str.replaceAll(RegExp(r'0*$'), '').replaceAll(RegExp(r'\.$'), '');
    }
    final parts = str.split('.');
    final intPart = _addCommas(parts[0]);
    return parts.length > 1 ? '$intPart.${parts[1]}' : intPart;
  }

  /// Format latency in milliseconds.
  static String formatLatency(int? ms) {
    if (ms == null) return emDash;
    return '${ms}ms';
  }

  /// Format timestamp cleanly for display.
  static String formatTime(String? timestamp) {
    if (timestamp == null || timestamp.trim().isEmpty) return emDash;
    final clean = timestamp.replaceAll('(VN)', '').trim();
    if (clean.length > 19) {
      return clean.substring(0, 19);
    }
    return clean;
  }

  static String _addCommas(String intStr) {
    final isNeg = intStr.startsWith('-');
    final digits = isNeg ? intStr.substring(1) : intStr;
    final chars = digits.split('').reversed.toList();
    final out = <String>[];
    for (int i = 0; i < chars.length; i++) {
      if (i > 0 && i % 3 == 0) {
        out.add(',');
      }
      out.add(chars[i]);
    }
    return (isNeg ? '-' : '') + out.reversed.join('');
  }
}
