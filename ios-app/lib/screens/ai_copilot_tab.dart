import 'package:flutter/material.dart';
import '../models/models.dart';
import '../services/api_service.dart';

class AiCopilotTab extends StatefulWidget {
  final ApiService apiService;

  const AiCopilotTab({super.key, required this.apiService});

  @override
  State<AiCopilotTab> createState() => _AiCopilotTabState();
}

class _AiCopilotTabState extends State<AiCopilotTab> {
  final List<ChatMessage> _messages = [
    ChatMessage(
      sender: 'AI Quant Copilot',
      text: 'Xin chào! Tôi là Trợ Lý Quant Định Lượng DeepSeek V4.1 Flash. Tôi đang trực tiếp theo dõi danh mục Binance Futures, bộ lọc xu hướng BTC Regime và các điểm chốt lời đa tầng. Bạn có thắc mắc gì về thị trường không?',
      isUser: false,
      timestamp: DateTime.now(),
    ),
  ];
  final TextEditingController _textCtrl = TextEditingController();
  bool _isSending = false;

  void _sendMessage(String query) async {
    if (query.trim().isEmpty || _isSending) return;

    final userText = query.trim();
    _textCtrl.clear();

    setState(() {
      _messages.add(ChatMessage(
        sender: 'Bạn',
        text: userText,
        isUser: true,
        timestamp: DateTime.now(),
      ));
      _isSending = true;
    });

    try {
      final reply = await widget.apiService.askAiCopilot(userText);
      setState(() {
        _messages.add(ChatMessage(
          sender: 'DeepSeek V4.1 Flash',
          text: reply,
          isUser: false,
          timestamp: DateTime.now(),
        ));
      });
    } catch (e) {
      setState(() {
        _messages.add(ChatMessage(
          sender: 'Hệ thống',
          text: 'Lỗi kết nối AI: $e',
          isUser: false,
          timestamp: DateTime.now(),
        ));
      });
    } finally {
      setState(() => _isSending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Quick Prompts Chips
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Row(
            children: [
              _promptChip('📊 Phân tích BTC hôm nay'),
              const SizedBox(width: 8),
              _promptChip('🛡️ Kiểm tra rủi ro danh mục'),
              const SizedBox(width: 8),
              _promptChip('🚀 Coin nào có dòng tiền mạnh?'),
              const SizedBox(width: 8),
              _promptChip('📈 Chiến lược Multi-TP là gì?'),
            ],
          ),
        ),

        // Messages List
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            itemCount: _messages.length,
            itemBuilder: (context, index) {
              final msg = _messages[index];
              return Align(
                alignment: msg.isUser ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(14),
                  constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.8),
                  decoration: BoxDecoration(
                    color: msg.isUser ? const Color(0xFFF0B90B).withValues(alpha: 0.15) : const Color(0xFF10141E),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: msg.isUser ? const Color(0xFFF0B90B).withValues(alpha: 0.3) : const Color(0xFF1C2436),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            msg.isUser ? Icons.person : Icons.psychology,
                            size: 14,
                            color: msg.isUser ? const Color(0xFFF0B90B) : Colors.purpleAccent,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            msg.sender,
                            style: TextStyle(
                              color: msg.isUser ? const Color(0xFFF0B90B) : Colors.purpleAccent,
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        msg.text,
                        style: const TextStyle(color: Colors.white, fontSize: 13, height: 1.4),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),

        // Thinking Indicator
        if (_isSending)
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            child: Row(
              children: [
                SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.purpleAccent),
                ),
                SizedBox(width: 8),
                Text('DeepSeek V4.1 Flash đang phân tích...', style: TextStyle(color: Colors.grey, fontSize: 11)),
              ],
            ),
          ),

        // Input Field
        Container(
          padding: const EdgeInsets.all(12),
          decoration: const BoxDecoration(
            color: Color(0xFF10141E),
            border: Border(top: BorderSide(color: Color(0xFF1C2436))),
          ),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _textCtrl,
                  style: const TextStyle(color: Colors.white, fontSize: 13),
                  decoration: InputDecoration(
                    hintText: 'Hỏi AI Copilot...',
                    hintStyle: const TextStyle(color: Colors.grey, fontSize: 13),
                    filled: true,
                    fillColor: const Color(0xFF080A0F),
                    contentPadding: const EdgeInsets.symmetric(vertical: 10, horizontal: 14),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1C2436))),
                    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFF1C2436))),
                    focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: Color(0xFFF0B90B))),
                  ),
                  onSubmitted: _sendMessage,
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                style: IconButton.styleFrom(
                  backgroundColor: const Color(0xFFF0B90B),
                  foregroundColor: Colors.black,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                ),
                icon: const Icon(Icons.send, size: 18),
                onPressed: () => _sendMessage(_textCtrl.text),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _promptChip(String text) {
    return ActionChip(
      label: Text(text, style: const TextStyle(color: Colors.grey, fontSize: 11)),
      backgroundColor: const Color(0xFF10141E),
      side: const BorderSide(color: Color(0xFF1C2436)),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      onPressed: () => _sendMessage(text),
    );
  }
}
