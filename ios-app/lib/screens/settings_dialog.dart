import 'package:flutter/material.dart';
import '../services/api_service.dart';

class SettingsDialog extends StatefulWidget {
  final ApiService apiService;
  final VoidCallback onSaved;

  const SettingsDialog({super.key, required this.apiService, required this.onSaved});

  @override
  State<SettingsDialog> createState() => _SettingsDialogState();
}

class _SettingsDialogState extends State<SettingsDialog> {
  late TextEditingController _urlCtrl;
  late TextEditingController _tokenCtrl;

  @override
  void initState() {
    super.initState();
    _urlCtrl = TextEditingController(text: widget.apiService.serverUrl);
    _tokenCtrl = TextEditingController(text: widget.apiService.authToken);
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: const Color(0xFF10141E),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16), side: const BorderSide(color: Color(0xFF1C2436))),
      title: const Row(
        children: [
          Icon(Icons.settings, color: Color(0xFFF0B90B), size: 20),
          SizedBox(width: 8),
          Text('Cấu Hình Kết Nối VPS', style: TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.bold)),
        ],
      ),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Địa chỉ máy chủ VPS (Server URL):', style: TextStyle(color: Colors.grey, fontSize: 11)),
            const SizedBox(height: 6),
            TextField(
              controller: _urlCtrl,
              style: const TextStyle(color: Colors.white, fontSize: 12, fontFamily: 'monospace'),
              decoration: InputDecoration(
                filled: true,
                fillColor: const Color(0xFF080A0F),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF1C2436))),
                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFFF0B90B))),
              ),
            ),
            const SizedBox(height: 14),
            const Text('Token phiên quản trị (chỉ giữ trong bộ nhớ):', style: TextStyle(color: Colors.grey, fontSize: 11)),
            const SizedBox(height: 6),
            TextField(
              controller: _tokenCtrl,
              obscureText: true,
              style: const TextStyle(color: Colors.white, fontSize: 12, fontFamily: 'monospace'),
              decoration: InputDecoration(
                hintText: 'Nhập token phiên; không lưu trên thiết bị',
                hintStyle: const TextStyle(color: Colors.grey, fontSize: 11),
                filled: true,
                fillColor: const Color(0xFF080A0F),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFF1C2436))),
                focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: Color(0xFFF0B90B))),
              ),
            ),
            const SizedBox(height: 16),
            const Text('Chế Độ Quét & Giao Dịch:', style: TextStyle(color: Colors.grey, fontSize: 11)),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF080A0F),
                      foregroundColor: const Color(0xFFF0B90B),
                      side: const BorderSide(color: Color(0xFF1C2436)),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                    onPressed: () async {
                      await widget.apiService.setTradingMode('BLUECHIP_ONLY');
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Đã chuyển sang chế độ BLUECHIP (BTC/ETH)')),
                        );
                        widget.onSaved();
                      }
                    },
                    child: const Text('BLUECHIP', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFFF0B90B).withValues(alpha: 0.15),
                      foregroundColor: const Color(0xFFF0B90B),
                      side: BorderSide(color: const Color(0xFFF0B90B).withValues(alpha: 0.4)),
                      padding: const EdgeInsets.symmetric(vertical: 10),
                    ),
                    onPressed: () async {
                      await widget.apiService.setTradingMode('MARKET_ALL');
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Đã chuyển sang chế độ QUÉT TOP 80 COIN')),
                        );
                        widget.onSaved();
                      }
                    },
                    child: const Text('TOP 80 COIN', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),

      actions: [
        TextButton(
          child: const Text('HỦY', style: TextStyle(color: Colors.grey)),
          onPressed: () => Navigator.pop(context),
        ),
        ElevatedButton(
          style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFF0B90B), foregroundColor: Colors.black),
          child: const Text('LƯU CẤU HÌNH', style: TextStyle(fontWeight: FontWeight.bold)),
          onPressed: () async {
            await widget.apiService.saveSettings(_urlCtrl.text, _tokenCtrl.text);
            if (context.mounted) {
              Navigator.pop(context);
              widget.onSaved();
            }
          },
        ),
      ],
    );
  }
}
