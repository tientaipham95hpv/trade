import json
from typing import Dict, Any, Optional

def _shared_portal_head(title: str) -> str:
    return f"""
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} | Astra Quant Non-Custodial SaaS</title>
    <link rel="icon" type="image/png" href="/logo.png">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script>
        tailwind.config = {{
            darkMode: 'class',
            theme: {{
                extend: {{
                    fontFamily: {{
                        sans: ['Inter', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace']
                    }},
                    colors: {{
                        binance: {{
                            DEFAULT: '#F0B90B',
                            hover: '#FCD535',
                            dark: '#1E2329'
                        }}
                    }}
                }}
            }}
        }};
    </script>
    <style>
        body {{
            font-family: 'Inter', sans-serif;
            background-color: #0B0E14;
            color: #E2E8F0;
        }}
        html.light body {{
            background-color: #F8FAFC;
            color: #0F172A;
        }}
        .glass-card {{
            background: rgba(18, 24, 38, 0.85);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }}
        html.light .glass-card {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(0, 0, 0, 0.08);
            box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
        }}
    </style>
    """

def _shared_portal_scripts() -> str:
    return """
    <div id="toast-container" class="fixed bottom-5 right-5 z-50 flex flex-col space-y-2 pointer-events-none"></div>

    <!-- Custom Modal Container -->
    <div id="custom-modal-backdrop" class="fixed inset-0 z-50 hidden bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
        <div id="custom-modal-box" class="glass-card rounded-2xl max-w-md w-full p-6 space-y-4 transform transition-all scale-95 opacity-0 border border-slate-700/80 shadow-2xl">
            <div class="flex items-center space-x-3 text-amber-400">
                <i id="custom-modal-icon" class="fa-solid fa-triangle-exclamation text-2xl"></i>
                <h3 id="custom-modal-title" class="text-lg font-bold text-slate-100">Xác nhận</h3>
            </div>
            <p id="custom-modal-message" class="text-sm text-slate-300 leading-relaxed"></p>
            <div class="flex items-center justify-end space-x-3 pt-2">
                <button id="custom-modal-cancel" class="px-4 py-2 rounded-xl text-sm font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors">
                    Hủy Bỏ
                </button>
                <button id="custom-modal-confirm" class="px-5 py-2 rounded-xl text-sm font-bold bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/30 transition-all">
                    Xác Nhận
                </button>
            </div>
        </div>
    </div>

    <script>
        // Theme Manager
        function initTheme() {
            const saved = localStorage.getItem('theme');
            if (saved === 'light') {
                document.documentElement.classList.remove('dark');
                document.documentElement.classList.add('light');
                const ic = document.getElementById('theme-icon');
                if (ic) ic.className = 'fa-solid fa-sun';
            } else {
                document.documentElement.classList.add('dark');
                document.documentElement.classList.remove('light');
                const ic = document.getElementById('theme-icon');
                if (ic) ic.className = 'fa-solid fa-moon';
            }
        }

        function toggleTheme() {
            const isDark = document.documentElement.classList.contains('dark');
            if (isDark) {
                document.documentElement.classList.remove('dark');
                document.documentElement.classList.add('light');
                localStorage.setItem('theme', 'light');
                const ic = document.getElementById('theme-icon');
                if (ic) ic.className = 'fa-solid fa-sun';
            } else {
                document.documentElement.classList.add('dark');
                document.documentElement.classList.remove('light');
                localStorage.setItem('theme', 'dark');
                const ic = document.getElementById('theme-icon');
                if (ic) ic.className = 'fa-solid fa-moon';
            }
            if (typeof drawGrowthChart === 'function') {
                drawGrowthChart();
            }
        }
        initTheme();

        // Toast Notification Function (Replaces alert)
        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            if (!container) return;
            const toast = document.createElement('div');
            toast.className = 'pointer-events-auto flex items-center space-x-3 px-4 py-3 rounded-xl border shadow-2xl backdrop-blur-md text-sm font-medium transition-all transform duration-300 translate-y-2 opacity-0 ';
            let icon = 'fa-info-circle text-cyan-400';
            if (type === 'success') {
                toast.className += 'bg-slate-900/95 border-emerald-500/60 text-emerald-200';
                icon = 'fa-circle-check text-emerald-400';
            } else if (type === 'error') {
                toast.className += 'bg-slate-900/95 border-rose-500/60 text-rose-200';
                icon = 'fa-triangle-exclamation text-rose-400';
            } else {
                toast.className += 'bg-slate-900/95 border-slate-700 text-slate-200';
            }
            toast.innerHTML = `<i class="fa-solid ${icon} text-lg"></i><span>${message}</span>`;
            container.appendChild(toast);
            setTimeout(() => {
                toast.classList.remove('translate-y-2', 'opacity-0');
            }, 20);
            setTimeout(() => {
                toast.classList.add('opacity-0', 'translate-y-2');
                setTimeout(() => toast.remove(), 300);
            }, 3500);
        }

        // Custom Confirmation Modal (Replaces confirm)
        function showConfirmModal(title, message, isDanger = true) {
            return new Promise((resolve) => {
                const backdrop = document.getElementById('custom-modal-backdrop');
                const box = document.getElementById('custom-modal-box');
                const titleEl = document.getElementById('custom-modal-title');
                const msgEl = document.getElementById('custom-modal-message');
                const confirmBtn = document.getElementById('custom-modal-confirm');
                const cancelBtn = document.getElementById('custom-modal-cancel');
                const iconEl = document.getElementById('custom-modal-icon');

                titleEl.textContent = title;
                msgEl.textContent = message;

                if (isDanger) {
                    confirmBtn.className = "px-5 py-2 rounded-xl text-sm font-bold bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/30 transition-all";
                    iconEl.className = "fa-solid fa-triangle-exclamation text-2xl text-rose-400";
                } else {
                    confirmBtn.className = "px-5 py-2 rounded-xl text-sm font-bold bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-lg shadow-amber-500/30 transition-all";
                    iconEl.className = "fa-solid fa-circle-question text-2xl text-amber-400";
                }

                backdrop.classList.remove('hidden');
                setTimeout(() => {
                    box.classList.remove('scale-95', 'opacity-0');
                }, 20);

                function close(result) {
                    box.classList.add('scale-95', 'opacity-0');
                    setTimeout(() => {
                        backdrop.classList.add('hidden');
                        resolve(result);
                    }, 200);
                }

                confirmBtn.onclick = () => close(true);
                cancelBtn.onclick = () => close(false);
                backdrop.onclick = (e) => {
                    if (e.target === backdrop) close(false);
                };
            });
        }
    </script>
    """

def render_portal_login_html() -> str:
    """Giao diện Đăng nhập Client Portal"""
    tmpl = """<!DOCTYPE html>
<html lang="vi" class="dark">
<head>
    __HEAD__
</head>
<body class="min-h-screen flex items-center justify-center p-4">
    <div class="max-w-md w-full glass-card rounded-3xl p-8 space-y-6 shadow-2xl border border-slate-700/60">
        <div class="text-center space-y-2">
            <div class="inline-flex w-12 h-12 rounded-2xl bg-gradient-to-tr from-amber-500 to-yellow-300 items-center justify-center font-extrabold text-slate-950 text-2xl shadow-lg shadow-amber-500/30">
                AQ
            </div>
            <h1 class="text-2xl font-black text-slate-100 tracking-tight">Client Portal</h1>
            <p class="text-xs text-slate-400">Cổng giám sát OFFLINE Astra Quant</p>
        </div>

        <form id="loginForm" class="space-y-4" onsubmit="handleLogin(event)">
            <div class="space-y-1">
                <label class="text-xs font-semibold text-slate-300">Tên Đăng Nhập hoặc Email</label>
                <div class="relative">
                    <i class="fa-solid fa-user absolute left-3.5 top-3.5 text-slate-500 text-sm"></i>
                    <input type="text" id="username" required placeholder="Nhập username hoặc email" class="w-full bg-slate-900/80 border border-slate-700 focus:border-amber-500 rounded-xl py-2.5 pl-10 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500">
                </div>
            </div>

            <div class="space-y-1">
                <label class="text-xs font-semibold text-slate-300">Mật Khẩu</label>
                <div class="relative">
                    <i class="fa-solid fa-lock absolute left-3.5 top-3.5 text-slate-500 text-sm"></i>
                    <input type="password" id="password" required placeholder="••••••••" class="w-full bg-slate-900/80 border border-slate-700 focus:border-amber-500 rounded-xl py-2.5 pl-10 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500">
                </div>
            </div>

            <button type="submit" id="submitBtn" class="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-400 hover:from-amber-400 hover:to-yellow-300 text-slate-950 font-bold text-sm shadow-lg shadow-amber-500/25 transition-all flex items-center justify-center space-x-2">
                <i class="fa-solid fa-right-to-bracket"></i>
                <span>Đăng Nhập Vào Portal</span>
            </button>
        </form>

        <div class="text-center pt-2 space-y-3">
            <p class="text-xs text-slate-400">
                Chưa có tài khoản?
                <a href="/portal/register" class="text-amber-400 hover:underline font-semibold ml-1">Đăng ký thành viên</a>
            </p>
            <div class="border-t border-slate-800 pt-3 flex items-center justify-between text-[11px] text-slate-500">
                <a href="/track-record" class="hover:text-slate-400 flex items-center space-x-1">
                    <i class="fa-solid fa-chart-line"></i>
                    <span>Xem Track Record</span>
                </a>
                <button onclick="toggleTheme()" class="hover:text-slate-400 flex items-center space-x-1">
                    <i id="theme-icon" class="fa-solid fa-moon"></i>
                    <span>Giao diện</span>
                </button>
            </div>
        </div>
    </div>

    __SCRIPTS__
    <script>
        async function handleLogin(e) {
            e.preventDefault();
            const btn = document.getElementById('submitBtn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i><span>Đang xác thực...</span>';

            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value.trim();

            try {
                const res = await fetch('/api/portal/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Đăng nhập thành công!', 'success');
                    setTimeout(() => {
                        window.location.href = data.redirect || '/portal/dashboard';
                    }, 600);
                } else {
                    showToast(data.message || 'Sai thông tin đăng nhập', 'error');
                }
            } catch (err) {
                showToast('Lỗi kết nối máy chủ: ' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i><span>Đăng Nhập Vào Portal</span>';
            }
        }
    </script>
</body>
</html>"""
    return tmpl.replace("__HEAD__", _shared_portal_head("Đăng Nhập Khách Hàng")).replace("__SCRIPTS__", _shared_portal_scripts())


def render_portal_register_html() -> str:
    """Giao diện Đăng ký Client Portal"""
    tmpl = """<!DOCTYPE html>
<html lang="vi" class="dark">
<head>
    __HEAD__
</head>
<body class="min-h-screen flex items-center justify-center p-4">
    <div class="max-w-md w-full glass-card rounded-3xl p-8 space-y-6 shadow-2xl border border-slate-700/60">
        <div class="text-center space-y-2">
            <div class="inline-flex w-12 h-12 rounded-2xl bg-gradient-to-tr from-amber-500 to-yellow-300 items-center justify-center font-extrabold text-slate-950 text-2xl shadow-lg shadow-amber-500/30">
                AQ
            </div>
            <h1 class="text-2xl font-black text-slate-100 tracking-tight">Tạo Tài Khoản Khách Hàng</h1>
            <p class="text-xs text-slate-400">Tạo tài khoản giám sát OFFLINE</p>
        </div>

        <form id="registerForm" class="space-y-4" onsubmit="handleRegister(event)">
            <div class="space-y-1">
                <label class="text-xs font-semibold text-slate-300">Tên Đăng Nhập</label>
                <div class="relative">
                    <i class="fa-solid fa-user absolute left-3.5 top-3.5 text-slate-500 text-sm"></i>
                    <input type="text" id="username" required placeholder="ví dụ: investor_pro" class="w-full bg-slate-900/80 border border-slate-700 focus:border-amber-500 rounded-xl py-2.5 pl-10 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500">
                </div>
            </div>

            <div class="space-y-1">
                <label class="text-xs font-semibold text-slate-300">Email</label>
                <div class="relative">
                    <i class="fa-solid fa-envelope absolute left-3.5 top-3.5 text-slate-500 text-sm"></i>
                    <input type="email" id="email" required placeholder="investor@example.com" class="w-full bg-slate-900/80 border border-slate-700 focus:border-amber-500 rounded-xl py-2.5 pl-10 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500">
                </div>
            </div>

            <div class="space-y-1">
                <label class="text-xs font-semibold text-slate-300">Mật Khẩu</label>
                <div class="relative">
                    <i class="fa-solid fa-lock absolute left-3.5 top-3.5 text-slate-500 text-sm"></i>
                    <input type="password" id="password" required placeholder="Tối thiểu 6 ký tự" class="w-full bg-slate-900/80 border border-slate-700 focus:border-amber-500 rounded-xl py-2.5 pl-10 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500">
                </div>
            </div>

            <div class="space-y-1">
                <label class="text-xs font-semibold text-slate-300">Xác Nhận Mật Khẩu</label>
                <div class="relative">
                    <i class="fa-solid fa-check-double absolute left-3.5 top-3.5 text-slate-500 text-sm"></i>
                    <input type="password" id="confirm_password" required placeholder="Nhập lại mật khẩu" class="w-full bg-slate-900/80 border border-slate-700 focus:border-amber-500 rounded-xl py-2.5 pl-10 pr-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-amber-500">
                </div>
            </div>

            <button type="submit" id="submitBtn" class="w-full py-3 rounded-xl bg-gradient-to-r from-amber-500 to-yellow-400 hover:from-amber-400 hover:to-yellow-300 text-slate-950 font-bold text-sm shadow-lg shadow-amber-500/25 transition-all flex items-center justify-center space-x-2">
                <i class="fa-solid fa-user-plus"></i>
                <span>Tạo Tài Khoản & Bắt Đầu</span>
            </button>
        </form>

        <div class="text-center pt-2 space-y-3">
            <p class="text-xs text-slate-400">
                Đã có tài khoản?
                <a href="/portal/login" class="text-amber-400 hover:underline font-semibold ml-1">Đăng nhập ngay</a>
            </p>
            <div class="border-t border-slate-800 pt-3 flex items-center justify-between text-[11px] text-slate-500">
                <a href="/track-record" class="hover:text-slate-400 flex items-center space-x-1">
                    <i class="fa-solid fa-chart-line"></i>
                    <span>Xem Track Record</span>
                </a>
                <button onclick="toggleTheme()" class="hover:text-slate-400 flex items-center space-x-1">
                    <i id="theme-icon" class="fa-solid fa-moon"></i>
                    <span>Giao diện</span>
                </button>
            </div>
        </div>
    </div>

    __SCRIPTS__
    <script>
        async function handleRegister(e) {
            e.preventDefault();
            const username = document.getElementById('username').value.trim();
            const email = document.getElementById('email').value.trim();
            const password = document.getElementById('password').value.trim();
            const confirm = document.getElementById('confirm_password').value.trim();

            if (password !== confirm) {
                showToast('Mật khẩu xác nhận không khớp!', 'error');
                return;
            }
            if (password.length < 6) {
                showToast('Mật khẩu cần tối thiểu 6 ký tự!', 'error');
                return;
            }

            const btn = document.getElementById('submitBtn');
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i><span>Đang khởi tạo...</span>';

            try {
                const res = await fetch('/api/portal/register', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, email, password})
                });
                const data = await res.json();
                if (data.success) {
                    showToast('Đăng ký tài khoản thành công!', 'success');
                    setTimeout(() => {
                        window.location.href = '/portal/dashboard';
                    }, 800);
                } else {
                    showToast(data.message || 'Lỗi khi đăng ký', 'error');
                }
            } catch (err) {
                showToast('Lỗi kết nối máy chủ: ' + err.message, 'error');
            } finally {
                btn.disabled = false;
                btn.innerHTML = '<i class="fa-solid fa-user-plus"></i><span>Tạo Tài Khoản & Bắt Đầu</span>';
            }
        }
    </script>
</body>
</html>"""
    return tmpl.replace("__HEAD__", _shared_portal_head("Đăng Ký Khách Hàng")).replace("__SCRIPTS__", _shared_portal_scripts())


def render_portal_api_settings_html(
    client_info: Dict[str, Any], cred_info: Optional[Dict[str, Any]] = None
) -> str:
    """Render a product-safe retired feature page without credential fields."""
    del client_info, cred_info
    return """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Feature disabled</title></head>
<body><main><h1>Feature disabled</h1>
<p>Client-account trading is not supported in the current architecture.</p>
<p>No Binance credentials are required or accepted by this application.</p>
<a href="/portal/dashboard">Return to monitoring dashboard</a></main></body></html>"""


def render_portal_dashboard_html(client_info: Dict[str, Any], data: Dict[str, Any]) -> str:
    """Minimal read-only fallback used only when the dashboard template is unavailable."""
    del client_info
    positions = data.get("positions", [])
    position_count = len(positions) if isinstance(positions, (list, dict)) else 0
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>OFFLINE Monitoring Dashboard</title></head>
<body><main>
<h1>OFFLINE Monitoring Dashboard</h1>
<p>Execution Service projection is read-only. Scanner, strategy, AI, copy-trade, Testnet and LIVE are disabled.</p>
<dl><dt>Open positions</dt><dd>{position_count}</dd>
<dt>Client-account trading</dt><dd>Unavailable / disabled</dd></dl>
<nav><a href="/track-record">Audit history</a> | <a href="/portal/logout">Sign out</a></nav>
</main></body></html>"""
