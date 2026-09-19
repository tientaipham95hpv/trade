import 'package:flutter_test/flutter_test.dart';
import 'package:binance_quant_pro/main.dart';
import 'package:binance_quant_pro/services/api_service.dart';

void main() {
  testWidgets('App smoke test', (WidgetTester tester) async {
    final apiService = ApiService();
    await tester.pumpWidget(BinanceQuantProApp(apiService: apiService));
    expect(find.text('BINANCE QUANT PRO'), findsOneWidget);
  });
}
