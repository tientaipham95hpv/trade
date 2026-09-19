// =======================================================
// TRẠM ĐIỀU HÀNH GIAO DỊCH ĐỊNH LƯỢNG BINANCE QUANT PRO
// BẢN MÁY TÍNH TIẾNG VIỆT 100%
// =======================================================

let serverUrl = 'https://trader.noza.site';
let authToken = '';
let soundEnabled = true;
let isPolling = true;
let pollTimer = null;
let lastPositionsCount = 0;
let lastUnrealizedPnl = 0;
let currentUser = '';

// Bộ tạo âm thanh sàn giao dịch Web Audio Synthesizer
class AudioSynthesizer {
  constructor() {
    this.ctx = null;
  }

  init() {
    if (!this.ctx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioContext();
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  playEntrySound() {
    if (!soundEnabled) return;
    this.init();
    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, now); // D5
      osc.frequency.exponentialRampToValueAtTime(880, now + 0.15); // A5
      gain.gain.setValueAtTime(0.15, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.25);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + 0.25);
    } catch (e) {
      console.error('Lỗi phát âm thanh:', e);
    }
  }

  playTakeProfitSound() {
    if (!soundEnabled) return;
    this.init();
    try {
      const now = this.ctx.currentTime;
      // Âm thanh chuông ngân tiếng vàng chốt lời
      [523.25, 659.25, 783.99, 1046.50].forEach((freq, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, now + idx * 0.06);
        gain.gain.setValueAtTime(0.12, now + idx * 0.06);
        gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.06 + 0.2);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(now + idx * 0.06);
        osc.stop(now + idx * 0.06 + 0.2);
      });
    } catch (e) {
      console.error('Lỗi phát âm thanh:', e);
    }
  }

  playWarningSound() {
    if (!soundEnabled) return;
    this.init();
    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(220, now);
      osc.frequency.linearRampToValueAtTime(160, now + 0.3);
      gain.gain.setValueAtTime(0.2, now);
      gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(now);
      osc.stop(now + 0.35);
    } catch (e) {
      console.error('Lỗi phát âm thanh:', e);
    }
  }
}

const audioSynth = new AudioSynthesizer();

// Phần tử DOM
const connIndicator = document.getElementById('connIndicator');
const connStatus = document.getElementById('connStatus');
const pingLatency = document.getElementById('pingLatency');
const statBalance = document.getElementById('statBalance');
const statUnrealized = document.getElementById('statUnrealized');
const statUnrealizedPct = document.getElementById('statUnrealizedPct');
const statBtcRegime = document.getElementById('statBtcRegime');
const statBtcDetails = document.getElementById('statBtcDetails');
const statFng = document.getElementById('statFng');
const statCircuit = document.getElementById('statCircuit');
const badgePosCount = document.getElementById('badgePosCount');
const positionsTableBody = document.getElementById('positionsTableBody');
const radarCardsGrid = document.getElementById('radarCardsGrid');
const aiAuditFeed = document.getElementById('aiAuditFeed');
const aiChatMessages = document.getElementById('aiChatMessages');
const aiChatForm = document.getElementById('aiChatForm');
const aiChatInput = document.getElementById('aiChatInput');
const btnEmergencyClose = document.getElementById('btnEmergencyClose');
const btnAudioToggle = document.getElementById('btnAudioToggle');
const btnLoginOpen = document.getElementById('btnLoginOpen');
const userBadge = document.getElementById('userBadge');
const loginModal = document.getElementById('loginModal');
const btnCloseLogin = document.getElementById('btnCloseLogin');
const btnLoginSubmit = document.getElementById('btnLoginSubmit');
const loginUsername = document.getElementById('loginUsername');
const loginPassword = document.getElementById('loginPassword');
const loginErrorMsg = document.getElementById('loginErrorMsg');
const btnSettings = document.getElementById('btnSettings');
const settingsModal = document.getElementById('settingsModal');
const btnCloseSettings = document.getElementById('btnCloseSettings');
const btnCancelSettings = document.getElementById('btnCancelSettings');
const btnSaveSettings = document.getElementById('btnSaveSettings');
const btnModeBluechip = document.getElementById('btnModeBluechip');
const btnModeMarket = document.getElementById('btnModeMarket');
const btnPauseResume = document.getElementById('btnPauseResume');
const pauseResumeText = document.getElementById('pauseResumeText');

// Khởi chạy ứng dụng
async function initApp() {
  let cfg = {
    serverUrl: 'https://trader.noza.site',
    authToken: '',
    soundEnabled: true
  };

  // Đọc từ Electron / PyWebView / LocalStorage
  if (window.electronAPI) {
    try {
      const eCfg = await window.electronAPI.getConfig();
      cfg = { ...cfg, ...eCfg };
      window.electronAPI.onTriggerAction((action) => {
        if (action === 'emergency-close-all') {
          executeEmergencyClose();
        } else if (action === 'pause') {
          togglePauseResume(true);
        } else if (action === 'resume') {
          togglePauseResume(false);
        }
      });
    } catch (e) {}
  } else if (window.pywebview && window.pywebview.api) {
    try {
      const pCfg = await window.pywebview.api.get_config();
      cfg = { ...cfg, ...pCfg };
    } catch (e) {}
  } else {
    try {
      const local = localStorage.getItem('desktop_config');
      if (local) cfg = { ...cfg, ...JSON.parse(local) };
    } catch (e) {}
  }

  serverUrl = cfg.serverUrl || 'https://trader.noza.site';
  authToken = cfg.authToken || localStorage.getItem('auth_token') || '';
  soundEnabled = cfg.soundEnabled !== undefined ? cfg.soundEnabled : true;
  updateAudioIcon();

  document.getElementById('cfgServerUrl').value = serverUrl;
  document.getElementById('cfgAuthToken').value = authToken;
  document.getElementById('cfgSound').checked = soundEnabled;

  // Nếu chưa có token, thử tự động đăng nhập với tài khoản mặc định
  if (!authToken) {
    await tryAutoLogin('admin', 'admin123456');
  }

  // Bắt đầu quét dữ liệu định kỳ mỗi 3 giây
  pollDashboardData();
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollDashboardData, 3000);
}

// Tự động đăng nhập
async function tryAutoLogin(user, pass) {
  try {
    const res = await fetch(`${serverUrl.replace(/\/+$/, '')}/api/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ username: user, password: pass })
    });
    const data = await res.json();
    if (data && data.success && data.token) {
      authToken = data.token;
      currentUser = data.username || user;
      userBadge.textContent = currentUser;
      localStorage.setItem('auth_token', authToken);
      saveDesktopConfig({ authToken });
      return true;
    }
  } catch (e) {
    console.debug('Tự động đăng nhập thất bại:', e);
  }
  return false;
}

// Gọi API có kèm xác thực
async function fetchApi(endpoint, options = {}) {
  const url = `${serverUrl.replace(/\/+$/, '')}${endpoint}`;
  const headers = {
    'Accept': 'application/json',
    ...(options.headers || {})
  };
  if (authToken) {
    headers['X-Session-Token'] = authToken;
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const startTime = Date.now();
  try {
    const res = await fetch(url, { ...options, headers });
    const latency = Date.now() - startTime;
    pingLatency.textContent = `${latency} ms`;

    // Nếu bị 401 Unauthorized (Chưa đăng nhập / Token hết hạn)
    if (res.status === 401) {
      connIndicator.className = 'inline-block w-2 h-2 rounded-full bg-yellow-400';
      connStatus.textContent = 'Yêu cầu đăng nhập quản trị';
      showLoginModal('Phiên làm việc hết hạn hoặc chưa đăng nhập. Vui lòng đăng nhập để tiếp tục.');
      return null;
    }

    connIndicator.className = 'inline-block w-2 h-2 rounded-full bg-green-400';
    connStatus.textContent = 'Đã kết nối VPS trực tiếp';
    return await res.json();
  } catch (err) {
    pingLatency.textContent = '-- ms';
    connIndicator.className = 'inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse';
    connStatus.textContent = 'Mất kết nối máy chủ VPS';
    throw err;
  }
}

// Nạp dữ liệu Bảng điều khiển chính
async function pollDashboardData() {
  try {
    const data = await fetchApi('/api/status');
    if (!data) return;

    // 1. Số dư vốn & PnL
    const bal = data.balance || 1000.0;
    const uPnl = data.total_unrealized_pnl !== undefined ? data.total_unrealized_pnl : (data.unrealized_pnl || 0.0);
    const uPnlPct = bal > 0 ? (uPnl / bal) * 100 : 0;

    statBalance.textContent = `$${bal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USDT`;
    
    const pnlPrefix = uPnl >= 0 ? '+' : '';
    statUnrealized.textContent = `${pnlPrefix}$${uPnl.toFixed(2)} USDT`;
    statUnrealizedPct.textContent = `${pnlPrefix}${uPnlPct.toFixed(2)}%`;

    if (uPnl > 0) {
      statUnrealized.className = 'text-lg font-bold font-mono text-profitGreen mt-0.5';
      statUnrealizedPct.className = 'text-[10px] text-profitGreen font-mono mt-0.5';
    } else if (uPnl < 0) {
      statUnrealized.className = 'text-lg font-bold font-mono text-lossRed mt-0.5';
      statUnrealizedPct.className = 'text-[10px] text-lossRed font-mono mt-0.5';
    }

    // 2. Xu hướng BTC Regime
    const btcMatrix = (data.protection_matrix && data.protection_matrix.btc_regime) || {};
    const btcRegime = btcMatrix.regime || data.btc_regime || 'BULL';
    if (btcRegime.includes('BULL') || btcRegime === 'UPTREND') {
      statBtcRegime.innerHTML = '<i class="fa-solid fa-arrow-trend-up text-profitGreen"></i> <span class="text-profitGreen">BULL (CẤM SHORT 100%)</span>';
    } else if (btcRegime.includes('BEAR') || btcRegime === 'DOWNTREND') {
      statBtcRegime.innerHTML = '<i class="fa-solid fa-arrow-trend-down text-lossRed"></i> <span class="text-lossRed">BEAR (CẤM LONG 100%)</span>';
    } else {
      statBtcRegime.innerHTML = '<i class="fa-solid fa-arrows-left-right text-yellow-400"></i> <span class="text-yellow-400">SIDEWAY (ĐÁNH 2 CHIỀU)</span>';
    }
    statBtcDetails.textContent = btcMatrix.desc || data.btc_regime_reason || 'Đồng pha xu hướng khung 1H/4H';

    // 3. Chỉ số Tâm lý Fear & Greed
    if (data.fear_and_greed) {
      statFng.innerHTML = `<i class="fa-solid fa-fire text-amber-500"></i> <span>${data.fear_and_greed.value}/100 (${data.fear_and_greed.classification_vi || 'Tham Lam'})</span>`;
    }

    // 4. Cầu dao an toàn Circuit Breaker
    if (data.circuit_breaker && data.circuit_breaker.triggered) {
      statCircuit.innerHTML = '<i class="fa-solid fa-triangle-exclamation text-lossRed"></i> <span class="text-lossRed">ĐANG KHÓA COOLDOWN</span>';
    } else {
      statCircuit.innerHTML = '<i class="fa-solid fa-circle-check text-profitGreen"></i> <span class="text-profitGreen">BẢO VỆ AN TOÀN</span>';
    }

    // 5. Danh sách vị thế đang mở
    const positions = data.positions || [];
    renderPositions(positions);
    badgePosCount.textContent = `${positions.length}/${data.max_positions || data.max_concurrent_positions || 3}`;

    // Phát âm thanh và gửi thông báo khi có lệnh mới khớp
    if (positions.length > lastPositionsCount) {
      audioSynth.playEntrySound();
      if (window.electronAPI) {
        window.electronAPI.notify({
          title: '⚡ LỆNH MỚI ĐÃ KHỚP THÀNH CÔNG',
          body: 'Hệ thống Quant Pro vừa mở vị thế mới theo tín hiệu chuẩn!'
        });
      }
    }
    lastPositionsCount = positions.length;

    // Cập nhật System Tray trên PC
    if (window.electronAPI) {
      window.electronAPI.updateTray({
        pnl: `${pnlPrefix}$${uPnl.toFixed(2)}`,
        positions: positions.length,
        status: data.is_paused ? 'Tạm dừng' : 'Đang chạy'
      });
    }

    // 6. Trạng thái Tạm dừng / Bật lại
    if (data.is_paused) {
      pauseResumeText.textContent = 'Đã tạm dừng';
      btnPauseResume.className = 'px-3 py-1 rounded bg-red-500/10 text-red-400 border border-red-500/30 flex items-center space-x-1 hover:bg-red-500/20 transition';
      btnPauseResume.innerHTML = '<i class="fa-solid fa-pause text-[10px]"></i> <span id="pauseResumeText">Đã tạm dừng</span>';
    } else {
      pauseResumeText.textContent = 'Đang chạy';
      btnPauseResume.className = 'px-3 py-1 rounded bg-green-500/10 text-green-400 border border-green-500/30 flex items-center space-x-1 hover:bg-green-500/20 transition';
      btnPauseResume.innerHTML = '<i class="fa-solid fa-play text-[10px]"></i> <span id="pauseResumeText">Đang chạy</span>';
    }

    // 7. Chế độ giao dịch
    const mode = data.trading_mode || 'MARKET_ALL';
    if (mode === 'BLUECHIP_ONLY') {
      btnModeBluechip.className = 'px-2.5 py-1 rounded bg-binanceGold/20 text-binanceGold font-semibold transition';
      btnModeMarket.className = 'px-2.5 py-1 rounded text-gray-400 hover:text-white transition';
    } else {
      btnModeMarket.className = 'px-2.5 py-1 rounded bg-binanceGold/20 text-binanceGold font-semibold transition';
      btnModeBluechip.className = 'px-2.5 py-1 rounded text-gray-400 hover:text-white transition';
    }

  } catch (e) {
    console.debug('Lỗi quét dữ liệu:', e);
  }

  // Quét Radar thị trường
  pollRadar();
}

// Vẽ bảng danh sách vị thế
function renderPositions(positions) {
  if (!positions || positions.length === 0) {
    positionsTableBody.innerHTML = `
      <tr>
        <td colspan="8" class="text-center py-10 text-gray-500 font-mono">
          <i class="fa-solid fa-radar text-2xl mb-2 text-gray-600 block"></i>
          Chưa có vị thế nào đang mở. Hệ thống đang quét 80 cặp coin để tìm setup tối ưu...
        </td>
      </tr>
    `;
    return;
  }

  positionsTableBody.innerHTML = positions.map(pos => {
    const isLong = pos.side === 'BUY' || pos.side === 'LONG';
    const sideBadge = isLong 
      ? '<span class="px-1.5 py-0.5 rounded bg-profitGreen/20 text-profitGreen font-bold border border-profitGreen/30">MUA (LONG)</span>'
      : '<span class="px-1.5 py-0.5 rounded bg-lossRed/20 text-lossRed font-bold border border-lossRed/30">BÁN (SHORT)</span>';

    const pnl = pos.pnl_usdt !== undefined ? pos.pnl_usdt : (pos.unrealized_pnl || 0.0);
    const pnlPct = pos.pnl_percent !== undefined ? pos.pnl_percent : 0.0;
    const pnlColor = pnl >= 0 ? 'text-profitGreen' : 'text-lossRed';
    const pnlPrefix = pnl >= 0 ? '+' : '';

    const entry = pos.entry_price ? Number(pos.entry_price).toFixed(4) : '--';
    const curPrice = pos.current_price ? Number(pos.current_price).toFixed(4) : entry;
    const sl = pos.stop_loss ? Number(pos.stop_loss).toFixed(4) : '--';
    const tp = pos.take_profit ? Number(pos.take_profit).toFixed(4) : '--';

    return `
      <tr class="hover:bg-darkCardHover/50 transition">
        <td class="py-2.5 font-bold text-white">${pos.symbol} <span class="text-[10px] text-gray-500 font-normal">(${pos.leverage || 5}x)</span></td>
        <td class="py-2.5">${sideBadge}</td>
        <td class="py-2.5 text-gray-300">$${entry}</td>
        <td class="py-2.5 font-semibold text-white">$${curPrice}</td>
        <td class="py-2.5 text-lossRed font-semibold">$${sl}</td>
        <td class="py-2.5 text-binanceGold font-semibold">$${tp}</td>
        <td class="py-2.5 font-bold ${pnlColor}">${pnlPrefix}$${pnl.toFixed(2)} (${pnlPrefix}${pnlPct.toFixed(2)}%)</td>
        <td class="py-2.5 text-right">
          <button onclick="closeSinglePosition('${pos.symbol}')" class="px-2.5 py-1 rounded bg-lossRed/20 hover:bg-lossRed text-lossRed hover:text-white border border-lossRed/40 text-[10px] font-bold transition">
            ĐÓNG LỆNH
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

// Đóng vị thế cụ thể
window.closeSinglePosition = async function(symbol) {
  if (!confirm(`Bạn có chắc chắn muốn đóng vị thế ${symbol} ngay lập tức theo giá thị trường?`)) return;
  try {
    const res = await fetchApi(`/api/close_position?symbol=${symbol}`, { method: 'POST' });
    if (res && (res.success || res.status === 'success')) {
      audioSynth.playTakeProfitSound();
      pollDashboardData();
    } else {
      alert(`Không thể đóng vị thế: ${(res && res.message) || 'Lỗi xử lý'}`);
    }
  } catch (e) {
    alert(`Lỗi kết nối: ${e.message}`);
  }
};

// Cắt lệnh khẩn cấp (Kill-Switch)
async function executeEmergencyClose() {
  audioSynth.playWarningSound();
  const confirmed = confirm('🚨 CẢNH BÁO CẮT LỆNH KHẨN CẤP (KILL-SWITCH):\nBạn có chắc chắn muốn đóng SẠCH TOÀN BỘ vị thế đang chạy trên sàn Binance ngay bây giờ?');
  if (!confirmed) return;

  try {
    btnEmergencyClose.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ĐANG ĐÓNG...';
    const res = await fetchApi('/api/close_all_positions', { method: 'POST' });
    if (res && (res.success || res.status === 'success')) {
      if (window.electronAPI) {
        window.electronAPI.notify({
          title: '🚨 ĐÃ KÍCH HOẠT CẮT LỆNH KHẨN CẤP',
          body: 'Toàn bộ vị thế Binance đã được gửi lệnh đóng an toàn!'
        });
      }
      setTimeout(pollDashboardData, 1000);
    }
  } catch (e) {
    alert(`Lỗi khi kích hoạt Kill-switch: ${e.message}`);
  } finally {
    btnEmergencyClose.innerHTML = '<i class="fa-solid fa-radiation"></i> <span>CẮT KHẨN CẤP [KILL-SWITCH]</span>';
  }
}

btnEmergencyClose.addEventListener('click', executeEmergencyClose);

// Nạp dữ liệu Radar quét Top 80 coin
async function pollRadar() {
  try {
    const data = await fetchApi('/api/radar');
    if (!data || !data.pairs) return;

    radarCardsGrid.innerHTML = data.pairs.slice(0, 8).map(pair => {
      const isUp = pair.trend === 'UP' || pair.signal === 'BUY';
      const badge = isUp 
        ? '<span class="text-profitGreen font-bold">MUA ▲</span>' 
        : '<span class="text-lossRed font-bold">BÁN ▼</span>';
      return `
        <div class="bg-darkBase border border-darkBorder rounded-lg p-2 hover:border-binanceGold/40 transition">
          <div class="flex items-center justify-between text-xs font-bold text-white">
            <span>${pair.symbol}</span>
            <span class="text-[10px]">${badge}</span>
          </div>
          <div class="flex items-center justify-between text-[10px] text-gray-400 mt-1 font-mono">
            <span>$${Number(pair.price || 0).toFixed(4)}</span>
            <span class="text-cyan-400 font-semibold">ADX ${pair.adx ? Number(pair.adx).toFixed(1) : '25.0'}</span>
          </div>
        </div>
      `;
    }).join('');
  } catch (e) {
    // Bỏ qua lỗi polling radar
  }
}

// Khung Chat AI Copilot
aiChatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const query = aiChatInput.value.trim();
  if (!query) return;

  const userMsgDiv = document.createElement('div');
  userMsgDiv.className = 'bg-binanceGold/10 border border-binanceGold/30 text-white rounded-lg p-2.5 ml-4 text-xs font-mono';
  userMsgDiv.innerHTML = `<b>Bạn:</b> ${escapeHtml(query)}`;
  aiChatMessages.appendChild(userMsgDiv);
  aiChatInput.value = '';
  aiChatMessages.scrollTop = aiChatMessages.scrollHeight;

  const botThinking = document.createElement('div');
  botThinking.className = 'bg-darkBase/70 border border-darkBorder text-gray-400 rounded-lg p-2.5 mr-4 text-xs font-mono flex items-center space-x-2';
  botThinking.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-purple-400"></i> <span>DeepSeek V4.1 Flash đang phân tích định lượng...</span>';
  aiChatMessages.appendChild(botThinking);
  aiChatMessages.scrollTop = aiChatMessages.scrollHeight;

  try {
    const res = await fetchApi('/api/ai_chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: query, query: query })
    });
    botThinking.remove();

    const botMsgDiv = document.createElement('div');
    botMsgDiv.className = 'bg-darkBase border border-purple-500/30 text-gray-200 rounded-lg p-2.5 mr-4 text-xs leading-relaxed';
    botMsgDiv.innerHTML = `<div class="flex items-center space-x-1.5 text-purple-400 font-bold mb-1"><i class="fa-solid fa-brain text-[10px]"></i><span>Trợ Lý Quant (${(res && res.provider) || 'DeepSeek V4.1'}):</span></div>${escapeHtml((res && (res.reply || res.response)) || 'Không có phản hồi từ mô hình AI.')}`;
    aiChatMessages.appendChild(botMsgDiv);
    aiChatMessages.scrollTop = aiChatMessages.scrollHeight;
  } catch (err) {
    botThinking.remove();
    const errorDiv = document.createElement('div');
    errorDiv.className = 'bg-lossRed/10 border border-lossRed/30 text-lossRed rounded-lg p-2 text-xs font-mono';
    errorDiv.textContent = `Lỗi kết nối AI: ${err.message}`;
    aiChatMessages.appendChild(errorDiv);
  }
});

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Bật tắt âm thanh
btnAudioToggle.addEventListener('click', () => {
  soundEnabled = !soundEnabled;
  updateAudioIcon();
  saveDesktopConfig({ soundEnabled });
  if (soundEnabled) audioSynth.playEntrySound();
});

function updateAudioIcon() {
  if (soundEnabled) {
    btnAudioToggle.innerHTML = '<i class="fa-solid fa-volume-high text-xs text-binanceGold"></i>';
    btnAudioToggle.title = 'Âm thanh: BẬT';
  } else {
    btnAudioToggle.innerHTML = '<i class="fa-solid fa-volume-xmark text-xs text-gray-500"></i>';
    btnAudioToggle.title = 'Âm thanh: TẮT';
  }
}

// Quản lý Modal Đăng Nhập
function showLoginModal(msg = '') {
  loginModal.classList.remove('hidden');
  if (msg) {
    loginErrorMsg.textContent = msg;
    loginErrorMsg.classList.remove('hidden');
  } else {
    loginErrorMsg.classList.add('hidden');
  }
}

function hideLoginModal() {
  loginModal.classList.add('hidden');
}

btnLoginOpen.addEventListener('click', () => showLoginModal());
btnCloseLogin.addEventListener('click', hideLoginModal);

btnLoginSubmit.addEventListener('click', async () => {
  const user = loginUsername.value.trim();
  const pass = loginPassword.value.trim();
  if (!user || !pass) {
    loginErrorMsg.textContent = 'Vui lòng nhập đầy đủ tài khoản và mật khẩu!';
    loginErrorMsg.classList.remove('hidden');
    return;
  }

  btnLoginSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ĐANG XÁC THỰC...';
  try {
    const success = await tryAutoLogin(user, pass);
    if (success) {
      hideLoginModal();
      pollDashboardData();
    } else {
      loginErrorMsg.textContent = 'Sai tên đăng nhập hoặc mật khẩu quản trị!';
      loginErrorMsg.classList.remove('hidden');
    }
  } catch (e) {
    loginErrorMsg.textContent = `Lỗi kết nối: ${e.message}`;
    loginErrorMsg.classList.remove('hidden');
  } finally {
    btnLoginSubmit.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> <span>XÁC NHẬN ĐĂNG NHẬP</span>';
  }
});

// Modal Cài Đặt
btnSettings.addEventListener('click', () => settingsModal.classList.remove('hidden'));
btnCloseSettings.addEventListener('click', () => settingsModal.classList.add('hidden'));
btnCancelSettings.addEventListener('click', () => settingsModal.classList.add('hidden'));

btnSaveSettings.addEventListener('click', async () => {
  serverUrl = document.getElementById('cfgServerUrl').value.trim();
  authToken = document.getElementById('cfgAuthToken').value.trim();
  soundEnabled = document.getElementById('cfgSound').checked;
  const minimizeTray = document.getElementById('cfgMinimizeTray').checked;
  const hotkey = document.getElementById('cfgHotkey').value.trim();

  saveDesktopConfig({
    serverUrl,
    authToken,
    soundEnabled,
    minimizeToTray: minimizeTray,
    hotkeyEmergency: hotkey
  });

  updateAudioIcon();
  settingsModal.classList.add('hidden');
  pollDashboardData();
});

async function saveDesktopConfig(patch) {
  try {
    const local = localStorage.getItem('desktop_config');
    const merged = { ...(local ? JSON.parse(local) : {}), ...patch };
    localStorage.setItem('desktop_config', JSON.stringify(merged));
    if (window.electronAPI) {
      await window.electronAPI.saveConfig(merged);
    } else if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.save_config(merged);
    }
  } catch (e) {}
}

// Chuyển chế độ Bluechip / Market Top 80
btnModeBluechip.addEventListener('click', async () => {
  await fetchApi('/api/update_settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ trading_mode: 'BLUECHIP_ONLY' }) });
  pollDashboardData();
});
btnModeMarket.addEventListener('click', async () => {
  await fetchApi('/api/update_settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ trading_mode: 'MARKET_ALL' }) });
  pollDashboardData();
});

// Tạm dừng / Bật lại bot
async function togglePauseResume(forcePause = null) {
  await fetchApi('/api/toggle_pause', { method: 'POST' });
  pollDashboardData();
}
btnPauseResume.addEventListener('click', () => togglePauseResume());

// Bắt đầu
initApp();
