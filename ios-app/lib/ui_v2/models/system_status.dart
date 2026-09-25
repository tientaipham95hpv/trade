import 'position_view.dart';

/// Read-only snapshot of Execution Service and System Status.
/// Zero fake defaults: fields default to null, formatting to '—'.
class SystemStatus {
  final String status;
  final String? environment;
  final String? projectionSource;
  final bool isPaused;
  final int? haltGeneration;
  final String? haltReason;
  final bool recoveryRequired;
  final bool resumeAllowed;
  final double? balance;
  final double? realizedPnl;
  final String pnlState;
  final int? openPositionsCount;
  final List<PositionView> positions;
  final String? mode;
  final String? tradingMode;
  final int? maxPositions;
  final Map<String, dynamic>? healthDimensions;
  final DateTime updatedAt;
  final Map<String, dynamic>? raw;

  SystemStatus({
    required this.status,
    this.environment,
    this.projectionSource,
    this.isPaused = false,
    this.haltGeneration,
    this.haltReason,
    this.recoveryRequired = false,
    this.resumeAllowed = false,
    this.balance,
    this.realizedPnl,
    this.pnlState = 'UNKNOWN',
    this.openPositionsCount,
    this.positions = const [],
    this.mode,
    this.tradingMode,
    this.maxPositions,
    this.healthDimensions,
    DateTime? updatedAt,
    this.raw,
  }) : updatedAt = updatedAt ?? DateTime.now();

  bool get isHalted => status.toUpperCase() == 'HALTED' || isPaused == true;
  bool get isHealthy => status.toUpperCase() == 'HEALTHY' && !isHalted;
  bool get isUnknown => !isHealthy && !isHalted;

  factory SystemStatus.fromJson(Map<String, dynamic> json) {
    final rawPositions = json['positions'] ?? json['open_positions'];
    final posList = <PositionView>[];

    if (rawPositions is List) {
      for (final item in rawPositions) {
        if (item is Map<String, dynamic>) {
          posList.add(PositionView.fromJson(item));
        }
      }
    } else if (rawPositions is Map) {
      rawPositions.forEach((key, val) {
        if (val is Map<String, dynamic>) {
          posList.add(PositionView.fromJson(val, key.toString()));
        }
      });
    }

    final posCount = safeNullableInt(json['open_positions_count']) ?? posList.length;

    Map<String, dynamic>? health;
    if (json['health'] is Map<String, dynamic>) {
      health = json['health'] as Map<String, dynamic>;
    }

    final statusStr = (json['status'] ?? 'UNKNOWN').toString().toUpperCase();
    final isPaused = json['is_paused'] == true;
    final isHalted = statusStr == 'HALTED' || isPaused;
    final haltGen = safeNullableInt(json['halt_generation']);
    final recReq = json['recovery_required'] == true;
    final resumeAllowed = json['resume_allowed'] is bool
        ? json['resume_allowed'] as bool
        : (isHalted && haltGen != null && haltGen > 0 && !recReq && statusStr != 'UNKNOWN');

    return SystemStatus(
      status: statusStr,
      environment: json['environment']?.toString(),
      projectionSource: json['projection_source']?.toString(),
      isPaused: isPaused,
      haltGeneration: haltGen,
      haltReason: json['halt_reason']?.toString(),
      recoveryRequired: recReq,
      resumeAllowed: resumeAllowed,
      balance: safeNullableDouble(json['balance']),
      realizedPnl: safeNullableDouble(json['realized_pnl']),
      pnlState: json['pnl_state']?.toString() ?? (json['realized_pnl'] != null ? 'KNOWN_VALUE' : 'UNKNOWN'),
      openPositionsCount: posCount,
      positions: posList,
      mode: json['mode']?.toString() ?? 'OFFLINE',
      tradingMode: json['trading_mode']?.toString(),
      maxPositions: safeNullableInt(json['max_positions']),
      healthDimensions: health,
      updatedAt: DateTime.now(),
      raw: json,
    );
  }

  factory SystemStatus.unknown({String? reason}) {
    return SystemStatus(
      status: 'UNKNOWN',
      environment: null,
      projectionSource: 'OFFLINE_FALLBACK',
      isPaused: false,
      haltReason: reason ?? 'Dịch vụ chưa kết nối',
      recoveryRequired: false,
      resumeAllowed: false,
      balance: null,
      realizedPnl: null,
      pnlState: 'UNKNOWN',
      openPositionsCount: 0,
      positions: const [],
      mode: 'OFFLINE',
      updatedAt: DateTime.now(),
    );
  }
}
