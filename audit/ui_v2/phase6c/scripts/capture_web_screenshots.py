import os
import sys
import json
import time
import threading
import traceback
from http.server import HTTPServer, SimpleHTTPRequestHandler
import asyncio
from playwright.async_api import async_playwright
import jinja2

ROOT = os.getcwd()
SCREENSHOT_DIR = os.path.join(ROOT, 'audit', 'ui_v2', 'phase6c', 'screenshots')
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

class MockHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        if path.startswith('/static/'):
            return os.path.join(ROOT, 'web', path[1:].replace('/', os.sep))
        return super().translate_path(path)

    def do_GET(self):
        try:
            if self.path in ['/portal/dashboard', '/portal/dashboard-v2', '/']:
                env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(ROOT, 'web', 'templates')))
                template = env.get_template('ui_v2/dashboard.html')
                html = template.render()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                self.wfile.write(html.encode('utf-8'))
            elif self.path == '/api/status':
                data = {
                    'status': 'HEALTHY',
                    'environment': 'OFFLINE',
                    'mode': 'SIMULATION',
                    'is_paused': False,
                    'halt_generation': 1,
                    'halt_reason': None,
                    'recovery_required': False,
                    'resume_allowed': False,
                    'realized_pnl': 124.50,
                    'unrealized_pnl': 42.50,
                    'open_positions_count': 2,
                    'max_positions': 3,
                    'positions': [
                        {
                            'symbol': 'BTCUSDT',
                            'side': 'LONG',
                            'qty': 0.05,
                            'entry_price': 65000.0,
                            'mark_price': 65850.0,
                            'unrealized_pnl': 42.50,
                            'pnl': 42.50,
                            'stop_loss': 63500.0,
                            'take_profit': 67000.0,
                            'protection': 'ACTIVE_STOP',
                            'state': 'OPEN',
                            'created_at': '2026-09-25T14:30:00Z'
                        },
                        {
                            'symbol': 'ETHUSDT',
                            'side': 'SHORT',
                            'qty': 1.25,
                            'entry_price': 3450.0,
                            'mark_price': 3420.0,
                            'unrealized_pnl': 37.50,
                            'pnl': 37.50,
                            'stop_loss': 3550.0,
                            'take_profit': 3300.0,
                            'protection': 'ACTIVE_STOP',
                            'state': 'OPEN',
                            'created_at': '2026-09-25T15:10:00Z'
                        }
                    ],
                    'health': {
                        'state': 'ARMED',
                        'daily_loss': 0.0,
                        'max_daily_loss': 500.0,
                        'consecutive_losses': 0,
                        'max_consecutive_losses': 3,
                        'cooldown_until': None,
                        'daily_baseline_balance': 10000.0
                    }
                }
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))
            elif self.path == '/api/history':
                data = [
                    {'time': '2026-09-25T15:10:00Z', 'symbol': 'ETHUSDT', 'side': 'SELL', 'order_type': 'MARKET', 'qty': 1.25, 'price': 3450.0, 'status': 'FILLED'},
                    {'time': '2026-09-25T14:30:00Z', 'symbol': 'BTCUSDT', 'side': 'BUY', 'order_type': 'LIMIT', 'qty': 0.05, 'price': 65000.0, 'status': 'FILLED'}
                ]
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))
            elif self.path == '/api/logs':
                data = [
                    {'timestamp': '2026-09-25T15:10:02Z', 'component': 'EXECUTION', 'level': 'INFO', 'message': 'Position opened: ETHUSDT SHORT 1.25'},
                    {'timestamp': '2026-09-25T14:30:05Z', 'component': 'EXECUTION', 'level': 'INFO', 'message': 'Order matched: BTCUSDT BUY 0.05 @ 65000.0'}
                ]
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))
            else:
                super().do_GET()
        except Exception as e:
            print('Handler error:', e)

server = HTTPServer(('127.0.0.1', 8899), MockHandler)
t = threading.Thread(target=server.serve_forever, daemon=True)
t.start()
print('Local screenshot server running on http://127.0.0.1:8899')

async def capture_web():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                headless=True
            )
            # 1. 1920x1080 Overview
            page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
            await page.goto('http://127.0.0.1:8899/portal/dashboard', wait_until='networkidle')
            await page.wait_for_timeout(1000)
            p1 = os.path.join(SCREENSHOT_DIR, 'web_1920x1080_overview.png')
            await page.screenshot(path=p1)
            print('Captured:', p1)

            # 2. 1920x1080 Positions
            await page.click('a[data-tab="positions"]')
            await page.wait_for_timeout(500)
            p2 = os.path.join(SCREENSHOT_DIR, 'web_1920x1080_positions.png')
            await page.screenshot(path=p2)
            print('Captured:', p2)

            # 3. 1920x1080 Risk
            await page.click('a[data-tab="risk"]')
            await page.wait_for_timeout(500)
            p3 = os.path.join(SCREENSHOT_DIR, 'web_1920x1080_risk.png')
            await page.screenshot(path=p3)
            print('Captured:', p3)

            # 4. 1440x900 System
            await page.set_viewport_size({'width': 1440, 'height': 900})
            await page.click('a[data-tab="system"]')
            await page.wait_for_timeout(500)
            p4 = os.path.join(SCREENSHOT_DIR, 'web_1440x900_system.png')
            await page.screenshot(path=p4)
            print('Captured:', p4)

            # 5. 390x844 Overview
            await page.set_viewport_size({'width': 390, 'height': 844})
            await page.click('a[data-tab="overview"]')
            await page.wait_for_timeout(500)
            p5 = os.path.join(SCREENSHOT_DIR, 'web_390x844_overview.png')
            await page.screenshot(path=p5)
            print('Captured:', p5)

            # 6. 390x844 Risk
            await page.click('a[data-tab="risk"]')
            await page.wait_for_timeout(500)
            p6 = os.path.join(SCREENSHOT_DIR, 'web_390x844_risk.png')
            await page.screenshot(path=p6)
            print('Captured:', p6)

            await browser.close()
            print('All 6 Web screenshots captured successfully!')
    except Exception as e:
        traceback.print_exc()

asyncio.run(capture_web())
server.shutdown()
