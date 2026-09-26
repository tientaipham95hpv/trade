import 'package:flutter/material.dart';
import '../services/polling_controller.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';
import '../utils/quant_formatters.dart';
import '../widgets/environment_badge.dart';
import '../widgets/quant_status_badge.dart';
import 'overview_tab.dart';
import 'positions_tab.dart';
import 'risk_tab.dart';
import 'system_tab.dart';

/// Main Operator Console Container for Obsidian Quants UI V2.
/// Features persistent institutional header and 4-tab bottom navigation:
/// 1. TỔNG QUAN
/// 2. VỊ THẾ
/// 3. RỦI RO
/// 4. HỆ THỐNG
class QuantHomeScreen extends StatefulWidget {
  final PollingController pollingController;
  final VoidCallback onLogout;

  const QuantHomeScreen({
    super.key,
    required this.pollingController,
    required this.onLogout,
  });

  @override
  State<QuantHomeScreen> createState() => _QuantHomeScreenState();
}

class _QuantHomeScreenState extends State<QuantHomeScreen> {
  int _currentTabIndex = 0;

  @override
  void initState() {
    super.initState();
    widget.pollingController.addListener(_onControllerUpdate);
    widget.pollingController.start();
  }

  @override
  void dispose() {
    widget.pollingController.removeListener(_onControllerUpdate);
    super.dispose();
  }

  void _onControllerUpdate() {
    if (mounted) {
      setState(() {});
    }
  }

  void _switchTab(int index) {
    setState(() {
      _currentTabIndex = index;
    });
  }

  @override
  Widget build(BuildContext context) {
    final controller = widget.pollingController;
    final status = controller.status;
    final isHalted = status?.isHalted ?? false;
    final isHealthy = status?.isHealthy ?? false;

    QuantStatusType statusType;
    String statusLabel = 'CHƯA RÕ';
    if (isHalted) {
      statusType = QuantStatusType.halted;
      statusLabel = 'ĐÃ DỪNG';
    } else if (isHealthy) {
      statusType = QuantStatusType.healthy;
      statusLabel = 'KHỎE MẠNH';
    } else {
      statusType = QuantStatusType.unknown;
      statusLabel = status?.status ?? 'CHƯA RÕ';
    }

    final pages = [
      OverviewTab(
        status: status,
        onNavigateToPositions: () => _switchTab(1),
      ),
      PositionsTab(
        status: status,
        onRefresh: controller.refreshStatus,
      ),
      RiskTab(
        status: status,
        apiClient: controller.apiClient,
        onActionCompleted: controller.refreshStatus,
      ),
      SystemTab(
        status: status,
        logs: controller.logs,
        onRefreshLogs: controller.refreshLogs,
        onLogout: () async {
          await controller.apiClient.logout();
          controller.stop();
          widget.onLogout();
        },
      ),
    ];

    return Scaffold(
      backgroundColor: QuantColors.background,
      appBar: PreferredSize(
        preferredSize: const Size.fromHeight(60.0),
        child: Container(
          decoration: const BoxDecoration(
            color: QuantColors.surface,
            border: Border(bottom: BorderSide(color: QuantColors.border, width: 1.0)),
          ),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: QuantSpacing.spaceMd, vertical: QuantSpacing.space2xs),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // App Brand & Mode: TRẠM ĐỊNH LƯỢNG | NGOẠI TUYẾN | KHỎE MẠNH
                  Row(
                    children: [
                      Container(
                        width: 24,
                        height: 24,
                        decoration: BoxDecoration(
                          color: QuantColors.surfaceLow,
                          borderRadius: QuantSpacing.borderMicro,
                          border: Border.all(color: QuantColors.borderActive),
                        ),
                        child: const Center(
                          child: Icon(Icons.show_chart_rounded, color: QuantColors.cyan, size: 15),
                        ),
                      ),
                      const SizedBox(width: QuantSpacing.spaceXs),
                      Text(
                        'TRẠM ĐỊNH LƯỢNG',
                        style: QuantTypography.heading.copyWith(
                          fontSize: 12.5,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 0.5,
                        ),
                      ),
                      const SizedBox(width: QuantSpacing.spaceXs),
                      Text(
                        '|',
                        style: QuantTypography.caption.copyWith(
                          color: QuantColors.borderActive,
                          fontWeight: FontWeight.w300,
                        ),
                      ),
                      const SizedBox(width: QuantSpacing.spaceXs),
                      EnvironmentBadge.fromString(status?.environment ?? 'OFFLINE'),
                      const SizedBox(width: QuantSpacing.spaceXs),
                      Text(
                        '|',
                        style: QuantTypography.caption.copyWith(
                          color: QuantColors.borderActive,
                          fontWeight: FontWeight.w300,
                        ),
                      ),
                      const SizedBox(width: QuantSpacing.spaceXs),
                      QuantStatusBadge(
                        label: statusLabel,
                        type: statusType,
                      ),
                    ],
                  ),

                  // Latency & Refresh
                  Row(
                    children: [
                      if (controller.lastLatencyMs != null) ...[
                        Text(
                          QuantFormatters.formatLatency(controller.lastLatencyMs),
                          style: QuantTypography.caption.copyWith(
                            color: QuantColors.cyan,
                            fontSize: 10.0,
                          ),
                        ),
                        const SizedBox(width: QuantSpacing.space2xs),
                      ],
                      IconButton(
                        icon: controller.isLoading
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(strokeWidth: 1.8, color: QuantColors.cyan),
                              )
                            : const Icon(Icons.refresh, color: QuantColors.textSecondary, size: 18),
                        onPressed: controller.isLoading ? null : () => controller.refreshAll(),
                        tooltip: 'Làm mới dữ liệu',
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
      body: Column(
        children: [
          // Network / Offline Error Notification Banner
          if (controller.lastError != null) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: QuantSpacing.spaceMd, vertical: 4.0),
              color: QuantColors.tintWarningBg,
              child: Row(
                children: [
                  const Icon(Icons.cloud_off_outlined, color: QuantColors.gold, size: 14),
                  const SizedBox(width: QuantSpacing.spaceXs),
                  Expanded(
                    child: Text(
                      'Mất kết nối với Gateway. Đang thử lại tự động...',
                      style: QuantTypography.caption.copyWith(color: QuantColors.gold),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ],
          Expanded(
            child: IndexedStack(
              index: _currentTabIndex,
              children: pages,
            ),
          ),
        ],
      ),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: QuantColors.surface,
          border: Border(top: BorderSide(color: QuantColors.border, width: 1.0)),
        ),
        child: BottomNavigationBar(
          currentIndex: _currentTabIndex,
          onTap: _switchTab,
          backgroundColor: QuantColors.surface,
          selectedItemColor: QuantColors.cyan,
          unselectedItemColor: QuantColors.textMuted,
          selectedLabelStyle: QuantTypography.caption.copyWith(fontWeight: FontWeight.w700, fontSize: 10.0),
          unselectedLabelStyle: QuantTypography.caption.copyWith(fontSize: 10.0),
          type: BottomNavigationBarType.fixed,
          elevation: 0,
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.dashboard_outlined, size: 20),
              activeIcon: Icon(Icons.dashboard, size: 20),
              label: 'TỔNG QUAN',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.table_chart_outlined, size: 20),
              activeIcon: Icon(Icons.table_chart, size: 20),
              label: 'VỊ THẾ',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.shield_outlined, size: 20),
              activeIcon: Icon(Icons.shield, size: 20),
              label: 'RỦI RO',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.terminal_outlined, size: 20),
              activeIcon: Icon(Icons.terminal, size: 20),
              label: 'HỆ THỐNG',
            ),
          ],
        ),
      ),
    );
  }
}
