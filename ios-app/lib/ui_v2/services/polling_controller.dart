import 'dart:async';
import 'package:flutter/widgets.dart';
import '../models/activity_view.dart';
import '../models/system_status.dart';
import 'quant_api_client.dart';

/// Lifecycle-Aware Polling Coordinator for Obsidian Quants Operator Console.
///
/// Cadence:
/// - Status: 4 seconds
/// - History: 8 seconds
/// - Logs: 10 seconds
///
/// Features:
/// - Pauses all timers in background/inactive lifecycle state.
/// - Resumes and triggers immediate refresh on foreground resume.
/// - Single in-flight request lock preventing query stacking.
/// - Latency calculation for operator telemetry.
class PollingController extends ChangeNotifier with WidgetsBindingObserver {
  final QuantApiClient apiClient;

  SystemStatus? _status;
  ActivityData? _history;
  List<String> _logs = [];

  bool _isLoading = false;
  bool _isStatusUpdating = false;
  bool _isHistoryUpdating = false;
  bool _isLogsUpdating = false;

  int? _lastLatencyMs;
  String? _lastError;
  DateTime? _lastRefreshTime;
  bool _isPolling = false;
  bool _isAppInBackground = false;

  Timer? _statusTimer;
  Timer? _historyTimer;
  Timer? _logsTimer;

  PollingController({required this.apiClient}) {
    WidgetsBinding.instance.addObserver(this);
  }

  SystemStatus? get status => _status;
  ActivityData? get history => _history;
  List<String> get logs => List.unmodifiable(_logs);
  bool get isLoading => _isLoading;
  int? get lastLatencyMs => _lastLatencyMs;
  String? get lastError => _lastError;
  DateTime? get lastRefreshTime => _lastRefreshTime;
  bool get isPolling => _isPolling;
  bool get isAppInBackground => _isAppInBackground;

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused || state == AppLifecycleState.inactive) {
      _isAppInBackground = true;
      _pauseTimers();
    } else if (state == AppLifecycleState.resumed) {
      _isAppInBackground = false;
      if (_isPolling) {
        _resumeTimers();
        refreshAll();
      }
    }
  }

  /// Start polling lifecycle
  void start() {
    if (_isPolling) return;
    _isPolling = true;
    _resumeTimers();
    refreshAll();
  }

  /// Stop polling lifecycle
  void stop() {
    _isPolling = false;
    _pauseTimers();
  }

  void _resumeTimers() {
    _pauseTimers();

    _statusTimer = Timer.periodic(const Duration(seconds: 4), (_) {
      if (!_isAppInBackground) {
        refreshStatus();
      }
    });

    _historyTimer = Timer.periodic(const Duration(seconds: 8), (_) {
      if (!_isAppInBackground) {
        refreshHistory();
      }
    });

    _logsTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (!_isAppInBackground) {
        refreshLogs();
      }
    });
  }

  void _pauseTimers() {
    _statusTimer?.cancel();
    _statusTimer = null;
    _historyTimer?.cancel();
    _historyTimer = null;
    _logsTimer?.cancel();
    _logsTimer = null;
  }

  /// Trigger immediate refresh across all domains
  Future<void> refreshAll() async {
    _isLoading = true;
    notifyListeners();

    await Future.wait([
      refreshStatus(),
      refreshHistory(),
      refreshLogs(),
    ]);

    _isLoading = false;
    _lastRefreshTime = DateTime.now();
    notifyListeners();
  }

  /// Refresh system status (4s cadence)
  Future<void> refreshStatus() async {
    if (_isStatusUpdating) return;
    _isStatusUpdating = true;

    final stopwatch = Stopwatch()..start();
    try {
      final newStatus = await apiClient.fetchStatus();
      stopwatch.stop();
      _lastLatencyMs = stopwatch.elapsedMilliseconds;
      _status = newStatus;
      _lastError = null;
    } catch (e) {
      stopwatch.stop();
      _lastError = e.toString();
      // If we don't have status yet, provide fail-safe fallback
      _status ??= SystemStatus.unknown(reason: e.toString());
    } finally {
      _isStatusUpdating = false;
      notifyListeners();
    }
  }

  /// Refresh trade history (8s cadence)
  Future<void> refreshHistory() async {
    if (_isHistoryUpdating) return;
    _isHistoryUpdating = true;

    try {
      final newHistory = await apiClient.fetchHistory();
      _history = newHistory;
    } catch (_) {
      // Retain last known history
    } finally {
      _isHistoryUpdating = false;
      notifyListeners();
    }
  }

  /// Refresh system logs (10s cadence)
  Future<void> refreshLogs() async {
    if (_isLogsUpdating) return;
    _isLogsUpdating = true;

    try {
      final newLogs = await apiClient.fetchLogs();
      _logs = newLogs;
    } catch (_) {
      // Retain last known logs
    } finally {
      _isLogsUpdating = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    stop();
    super.dispose();
  }
}
