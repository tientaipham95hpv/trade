import 'package:flutter/material.dart';
import '../services/auth_store.dart';
import '../services/quant_api_client.dart';
import '../theme/quant_colors.dart';
import '../theme/quant_spacing.dart';
import '../theme/quant_typography.dart';
import '../widgets/environment_badge.dart';
import '../widgets/quant_risk_banner.dart';

/// Institutional Login Screen for Obsidian Quants Operator Console.
class LoginScreen extends StatefulWidget {
  final QuantApiClient apiClient;
  final VoidCallback onLoginSuccess;

  const LoginScreen({
    super.key,
    required this.apiClient,
    required this.onLoginSuccess,
  });

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _serverController = TextEditingController();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();

  bool _obscurePassword = true;
  bool _isLoading = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadSavedUrl();
  }

  Future<void> _loadSavedUrl() async {
    final url = await widget.apiClient.authStore.getServerUrl();
    if (mounted) {
      _serverController.text = url;
    }
  }

  @override
  void dispose() {
    _serverController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _handleLogin() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final serverUrl = _serverController.text.trim();
      if (serverUrl.isNotEmpty) {
        await widget.apiClient.authStore.saveServerUrl(serverUrl);
      }

      final success = await widget.apiClient.login(
        _usernameController.text,
        _passwordController.text,
      );

      if (success && mounted) {
        widget.onLoginSuccess();
      }
    } on QuantApiException catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.message;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = 'Lỗi không xác định: $e';
        });
      }
    } finally {
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: QuantColors.background,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: QuantSpacing.spaceLg),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Brand Header
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        width: 38,
                        height: 38,
                        decoration: BoxDecoration(
                          color: QuantColors.surfaceLow,
                          borderRadius: QuantSpacing.borderDefault,
                          border: Border.all(color: QuantColors.borderActive),
                        ),
                        child: const Center(
                          child: Icon(Icons.show_chart_rounded, color: QuantColors.cyan, size: 22),
                        ),
                      ),
                      const SizedBox(width: QuantSpacing.spaceSm),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'BINANCE QUANT PRO',
                            style: QuantTypography.heading.copyWith(
                              fontSize: 16.0,
                              fontWeight: FontWeight.w800,
                              letterSpacing: 0.5,
                            ),
                          ),
                          Row(
                            children: [
                              Text(
                                'OBSIDIAN QUANTS',
                                style: QuantTypography.caption.copyWith(color: QuantColors.cyan, letterSpacing: 1.0),
                              ),
                              const SizedBox(width: QuantSpacing.space2xs),
                              EnvironmentBadge.fromString(null),
                            ],
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: QuantSpacing.spaceXl),

                  // Institutional Notice
                  const QuantRiskBanner(
                    title: 'XÁC THỰC VẬN HÀNH BẢO MẬT',
                    message: 'Bảng điều khiển yêu cầu tài khoản quản trị hệ thống. Mọi hoạt động được ghi nhận kiểm toán.',
                    level: QuantRiskLevel.info,
                  ),
                  const SizedBox(height: QuantSpacing.spaceMd),

                  // Error Banner
                  if (_errorMessage != null) ...[
                    QuantRiskBanner(
                      title: 'ĐĂNG NHẬP THẤT BẠI',
                      message: _errorMessage!,
                      level: QuantRiskLevel.critical,
                    ),
                    const SizedBox(height: QuantSpacing.spaceMd),
                  ],

                  // Form Container
                  Container(
                    padding: QuantSpacing.paddingPanel,
                    decoration: BoxDecoration(
                      color: QuantColors.surface,
                      borderRadius: QuantSpacing.borderDefault,
                      border: Border.all(color: QuantColors.border, width: 1.0),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        // Server URL
                        Text(
                          'CỔNG DỊCH VỤ (GATEWAY URL)',
                          style: QuantTypography.caption.copyWith(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: QuantSpacing.space2xs),
                        TextFormField(
                          controller: _serverController,
                          style: QuantTypography.body,
                          keyboardType: TextInputType.url,
                          decoration: const InputDecoration(
                            hintText: AuthStore.defaultServerUrl,
                            prefixIcon: Icon(Icons.dns_outlined, color: QuantColors.textMuted, size: 18),
                          ),
                          validator: (val) => AuthStore.validateServerUrl(val),
                        ),
                        const SizedBox(height: QuantSpacing.spaceSm),

                        // Username
                        Text(
                          'TÊN QUẢN TRỊ VIÊN',
                          style: QuantTypography.caption.copyWith(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: QuantSpacing.space2xs),
                        TextFormField(
                          controller: _usernameController,
                          style: QuantTypography.body,
                          keyboardType: TextInputType.name,
                          autocorrect: false,
                          decoration: const InputDecoration(
                            hintText: 'admin',
                            prefixIcon: Icon(Icons.person_outline, color: QuantColors.textMuted, size: 18),
                          ),
                          validator: (val) {
                            if (val == null || val.trim().isEmpty) {
                              return 'Vui lòng nhập tên đăng nhập';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: QuantSpacing.spaceSm),

                        // Password
                        Text(
                          'MẬT KHẨU',
                          style: QuantTypography.caption.copyWith(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: QuantSpacing.space2xs),
                        TextFormField(
                          controller: _passwordController,
                          obscureText: _obscurePassword,
                          style: QuantTypography.body,
                          decoration: InputDecoration(
                            hintText: '••••••••',
                            prefixIcon: const Icon(Icons.lock_outline, color: QuantColors.textMuted, size: 18),
                            suffixIcon: IconButton(
                              icon: Icon(
                                _obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                                color: QuantColors.textMuted,
                                size: 18,
                              ),
                              onPressed: () {
                                setState(() {
                                  _obscurePassword = !_obscurePassword;
                                });
                              },
                            ),
                          ),
                          validator: (val) {
                            if (val == null || val.isEmpty) {
                              return 'Vui lòng nhập mật khẩu';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: QuantSpacing.spaceLg),

                        // Submit Button
                        SizedBox(
                          height: QuantSpacing.minTouchTarget,
                          width: double.infinity,
                          child: ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              backgroundColor: QuantColors.cyan,
                              foregroundColor: QuantColors.textInverse,
                              shape: const RoundedRectangleBorder(
                                borderRadius: QuantSpacing.borderDefault,
                              ),
                              elevation: 0,
                            ),
                            onPressed: _isLoading ? null : _handleLogin,
                            child: _isLoading
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2.0,
                                      color: QuantColors.textInverse,
                                    ),
                                  )
                                : Text(
                                    'ĐĂNG NHẬP VẬN HÀNH',
                                    style: QuantTypography.sectionTitle.copyWith(
                                      color: QuantColors.textInverse,
                                      fontWeight: FontWeight.w800,
                                      letterSpacing: 0.8,
                                    ),
                                  ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: QuantSpacing.spaceLg),

                  // Governance Footer Notice
                  Center(
                    child: Text(
                      'Kiến trúc V2: 0 chứng chỉ API khách hàng | Lõi Offline đóng băng',
                      style: QuantTypography.technical.copyWith(
                        color: QuantColors.textMuted,
                        fontSize: 10.0,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
