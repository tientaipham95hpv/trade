// =======================================================
// TRẠM ĐIỀU HÀNH GIAO DỊCH ĐỊNH LƯỢNG BINANCE QUANT PRO
// BẢN MÁY TÍNH TIẾNG VIỆT 100% - FULL 6 TABS CHUYÊN NGHIỆP
// =======================================================

let serverUrl = 'https://trader.noza.site';
let authToken = '';
let soundEnabled = true;
let isPolling = true;
let pollTimer = null;
let lastPositionsCount = 0;
let lastUnrealizedPnl = 0;
let currentUser = '';
let cachedRadarPairs = [];
let activeRadarFilter = 'ALL';
let logPollInterval = null;
let currentActiveTab = 'overview';
let activeTradingMode = 'MARKET_ALL';

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

// Safe DOM Helper
const $ = (id) => document.getElementById(id);

// =======================================================
// KHỞI CHẠY ỨNG DỤNG
// =======================================================
async function initApp() {
  let cfg = {
    serverUrl: 'https://trader.noza.site',
    soundEnabled: true
  };

  if (window.electronAPI) {
    try {
      const eCfg = await window.electronAPI.getConfig();
      cfg = { ...cfg, ...eCfg };
      window.electronAPI.onTriggerAction((action) => {
        if (action === 'emergency-close-all') executeEmergencyClose();
        else if (action === 'pause') togglePauseResume(true);
        else if (action === 'resume') togglePauseResume(false);
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
      if (local) {
        const localCfg = JSON.parse(local);
        delete localCfg.authToken;
        cfg = { ...cfg, ...localCfg };
        localStorage.setItem('desktop_config', JSON.stringify(localCfg));
      }
    } catch (e) {}
  }

  localStorage.removeItem('auth_token');
  authToken = '';
  serverUrl = cfg.serverUrl || 'https://trader.noza.site';
  soundEnabled = cfg.soundEnabled !== undefined ? cfg.soundEnabled : true;
  updateAudioIcon();

  if ($('cfgServerUrl')) $('cfgServerUrl').value = serverUrl;
  if ($('cfgSound')) $('cfgSound').checked = soundEnabled;

  setupNavigationTabs();
  setupRadarFilters();
  setupStrategySliders();
  setupAiQuickButtons();
  setupHeaderButtons();

  if (!authToken) {
    showLoginModal('Đăng nhập quản trị để bắt đầu phiên làm việc. Token không được lưu trên thiết bị.');
  }

  // Bắt đầu chu kỳ quét dữ liệu
  pollDashboardData();
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(pollDashboardData, 3000);

  // Chu kỳ quét logs nền
  if (logPollInterval) clearInterval(logPollInterval);
  logPollInterval = setInterval(() => {
    if (currentActiveTab === 'logs') pollLiveLogs();
  }, 3500);
}

// =======================================================
// XỬ LÝ CHUYỂN TAB (NAVIGATION)
// =======================================================
function setupNavigationTabs() {
  const tabsConfig = [
    { key: 'overview', btn: $('tabBtnOverview'), view: $('viewOverview') },
    { key: 'radar', btn: $('tabBtnRadar'), view: $('viewRadar') },
    { key: 'history', btn: $('tabBtnHistory'), view: $('viewHistory') },
    { key: 'strategy', btn: $('tabBtnStrategy'), view: $('viewStrategy') },
    { key: 'logs', btn: $('tabBtnLogs'), view: $('viewLogs') },
    { key: 'ai', btn: $('tabBtnAi'), view: $('viewAi') },
  ];

  tabsConfig.forEach(({ key, btn }) => {
    if (!btn) return;
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      switchTab(key);
    });
  });
}

function switchTab(tabKey) {
  currentActiveTab = tabKey;
  const tabsConfig = [
    { key: 'overview', btn: $('tabBtnOverview'), view: $('viewOverview') },
    { key: 'radar', btn: $('tabBtnRadar'), view: $('viewRadar') },
    { key: 'history', btn: $('tabBtnHistory'), view: $('viewHistory') },
    { key: 'strategy', btn: $('tabBtnStrategy'), view: $('viewStrategy') },
    { key: 'logs', btn: $('tabBtnLogs'), view: $('viewLogs') },
    { key: 'ai', btn: $('tabBtnAi'), view: $('viewAi') },
  ];

  tabsConfig.forEach(({ key, btn, view }) => {
    if (!btn || !view) return;
    if (key === tabKey) {
      btn.classList.add('active', 'bg-darkCardHover', 'text-white');
      btn.classList.remove('text-gray-400');
      view.classList.remove('hidden');
      if (key === 'strategy') {
        view.classList.add('block');
      } else {
        view.classList.add('flex');
      }
    } else {
      btn.classList.remove('active', 'bg-darkCardHover', 'text-white');
      btn.classList.add('text-gray-400');
      view.classList.add('hidden');
      view.classList.remove('flex', 'block');
    }
  });

  if (tabKey === 'history') loadHistoryData();
  else if (tabKey === 'strategy') loadStrategySettings();
  else if (tabKey === 'logs') pollLiveLogs();
  else if (tabKey === 'radar') pollRadar();
}

// =======================================================
// GIAO TIẾP VỚI MÁY CHỦ & XÁC THỰC
// =======================================================
async function loginWithCredentials(user, pass) {
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
      if ($('userBadge')) $('userBadge').textContent = currentUser;
      return true;
    }
  } catch (e) {
    console.debug('Tự động đăng nhập thất bại:', e);
  }
  return false;
}

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
    if ($('pingLatency')) $('pingLatency').textContent = `${latency} ms`;

    if (res.status === 401) {
      authToken = '';
      currentUser = '';
      if ($('connIndicator')) $('connIndicator').className = 'inline-block w-2 h-2 rounded-full bg-yellow-400';
      if ($('connStatus')) $('connStatus').textContent = 'Yêu cầu đăng nhập quản trị';
      showLoginModal('Phiên làm việc hết hạn hoặc chưa đăng nhập. Vui lòng đăng nhập để tiếp tục.');
      return null;
    }

    if ($('connIndicator')) $('connIndicator').className = 'inline-block w-2 h-2 rounded-full bg-green-400';
    if ($('connStatus')) $('connStatus').textContent = 'Đã kết nối VPS trực tiếp';
    return await res.json();
  } catch (err) {
    if ($('pingLatency')) $('pingLatency').textContent = '-- ms';
    if ($('connIndicator')) $('connIndicator').className = 'inline-block w-2 h-2 rounded-full bg-red-500 animate-pulse';
    if ($('connStatus')) $('connStatus').textContent = 'Mất kết nối máy chủ VPS';
    throw err;
  }
}

// =======================================================
// TAB 1: TỔNG QUAN & VỊ THẾ LIVE
// =======================================================
async function pollDashboardData() {
  if (!authToken) return;
  try {
    const data = await fetchApi('/api/status');
    if (!data) return;

    // 1. Số dư vốn & PnL
    const bal = data.balance || 1000.0;
    const uPnl = data.total_unrealized_pnl !== undefined ? data.total_unrealized_pnl : (data.unrealized_pnl || 0.0);
    const uPnlPct = bal > 0 ? (uPnl / bal) * 100 : 0;

    if ($('statBalance')) {
      $('statBalance').textContent = `$${bal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USDT`;
    }
    
    const pnlPrefix = uPnl >= 0 ? '+' : '';
    if ($('statUnrealized')) {
      $('statUnrealized').textContent = `${pnlPrefix}$${uPnl.toFixed(2)} USDT`;
      $('statUnrealized').className = `text-lg font-bold font-mono mt-0.5 ${uPnl >= 0 ? 'text-profitGreen' : 'text-lossRed'}`;
    }
    if ($('statUnrealizedPct')) {
      $('statUnrealizedPct').textContent = `${pnlPrefix}${uPnlPct.toFixed(2)}%`;
      $('statUnrealizedPct').className = `text-[10px] font-mono mt-0.5 ${uPnl >= 0 ? 'text-profitGreen' : 'text-lossRed'}`;
    }

    // 2. Lá chắn BTC Regime
    const btcMatrix = (data.protection_matrix && data.protection_matrix.btc_regime) || {};
    const btcRegime = btcMatrix.regime || data.btc_regime || 'BULL';
    if ($('statBtcRegime')) {
      if (btcRegime.includes('BULL') || btcRegime === 'UPTREND') {
        $('statBtcRegime').innerHTML = '<i class="fa-solid fa-arrow-trend-up text-profitGreen"></i> <span class="text-profitGreen">XU HƯỚNG TĂNG (CẤM SHORT)</span>';
      } else if (btcRegime.includes('BEAR') || btcRegime === 'DOWNTREND') {
        $('statBtcRegime').innerHTML = '<i class="fa-solid fa-arrow-trend-down text-lossRed"></i> <span class="text-lossRed">XU HƯỚNG GIẢM (CẤM LONG)</span>';
      } else {
        $('statBtcRegime').innerHTML = '<i class="fa-solid fa-arrows-left-right text-yellow-400"></i> <span class="text-yellow-400">ĐI NGANG (CẢ 2 CHIỀU)</span>';
      }
    }
    if ($('statBtcDetails')) {
      $('statBtcDetails').textContent = btcMatrix.desc || data.btc_regime_reason || 'Đồng pha xu hướng khung 1H/4H';
    }

    // 3. Tâm lý Fear & Greed
    if ($('statFng') && data.fear_and_greed) {
      $('statFng').innerHTML = `<i class="fa-solid fa-fire text-amber-500"></i> <span>${data.fear_and_greed.value}/100 (${data.fear_and_greed.classification_vi || 'Tham Lam'})</span>`;
    }

    // 4. Circuit Breaker
    if ($('statCircuit')) {
      if (data.circuit_breaker && data.circuit_breaker.triggered) {
        $('statCircuit').innerHTML = '<i class="fa-solid fa-triangle-exclamation text-lossRed"></i> <span class="text-lossRed">ĐANG KHÓA COOLDOWN</span>';
      } else {
        $('statCircuit').innerHTML = '<i class="fa-solid fa-circle-check text-profitGreen"></i> <span class="text-profitGreen">BẢO VỆ AN TOÀN</span>';
      }
    }

    // 5. Danh sách vị thế đang mở
    const positions = data.positions || [];
    renderPositions(positions);
    if ($('badgePosCount')) {
      $('badgePosCount').textContent = `${positions.length}/${data.max_positions || data.max_concurrent_positions || 3}`;
    }

    // Phát âm thanh khi có lệnh mới
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

    // 6. Trạng thái tạm dừng
    if ($('pauseResumeText') && $('btnPauseResume')) {
      if (data.is_paused) {
        $('pauseResumeText').textContent = 'Đã tạm dừng';
        $('btnPauseResume').className = 'px-3 py-1 rounded bg-red-500/10 text-red-400 border border-red-500/30 flex items-center space-x-1 hover:bg-red-500/20 transition';
        $('btnPauseResume').innerHTML = '<i class="fa-solid fa-pause text-[10px]"></i> <span id="pauseResumeText">Đã tạm dừng</span>';
      } else {
        $('pauseResumeText').textContent = 'Đang chạy';
        $('btnPauseResume').className = 'px-3 py-1 rounded bg-green-500/10 text-green-400 border border-green-500/30 flex items-center space-x-1 hover:bg-green-500/20 transition';
        $('btnPauseResume').innerHTML = '<i class="fa-solid fa-play text-[10px]"></i> <span id="pauseResumeText">Đang chạy</span>';
      }
    }

    // 7. Chế độ giao dịch
    activeTradingMode = data.trading_mode || 'MARKET_ALL';
    updateTradingModeButtons();

    // 8. Cập nhật Gatekeeper Audit Feed Động
    renderGatekeeperFeed(data);

  } catch (e) {
    console.debug('Lỗi quét dữ liệu dashboard:', e);
  }

  // Đồng bộ Radar nếu đang ở tab radar
  if (currentActiveTab === 'radar') {
    pollRadar();
  }
}

function updateTradingModeButtons() {
  const isBluechip = activeTradingMode === 'BLUECHIP_ONLY';

  if ($('btnModeBluechip') && $('btnModeMarket')) {
    if (isBluechip) {
      $('btnModeBluechip').className = 'px-2.5 py-1 rounded bg-binanceGold/20 text-binanceGold font-semibold transition';
      $('btnModeMarket').className = 'px-2.5 py-1 rounded text-gray-400 hover:text-white transition';
    } else {
      $('btnModeMarket').className = 'px-2.5 py-1 rounded bg-binanceGold/20 text-binanceGold font-semibold transition';
      $('btnModeBluechip').className = 'px-2.5 py-1 rounded text-gray-400 hover:text-white transition';
    }
  }

  if ($('stratBtnBluechip') && $('stratBtnMarket')) {
    if (isBluechip) {
      $('stratBtnBluechip').className = 'py-2 px-3 rounded-lg border border-binanceGold/40 bg-binanceGold/20 text-binanceGold font-bold transition text-center';
      $('stratBtnMarket').className = 'py-2 px-3 rounded-lg border border-darkBorder text-gray-400 hover:text-white transition text-center';
    } else {
      $('stratBtnMarket').className = 'py-2 px-3 rounded-lg border border-binanceGold/40 bg-binanceGold/20 text-binanceGold font-bold transition text-center';
      $('stratBtnBluechip').className = 'py-2 px-3 rounded-lg border border-darkBorder text-gray-400 hover:text-white transition text-center';
    }
  }
}

function renderPositions(positions) {
  if (!$('positionsTableBody')) return;

  if (!positions || positions.length === 0) {
    $('positionsTableBody').innerHTML = `
      <tr>
        <td colspan="8" class="text-center py-10 text-gray-500 font-mono">
          <i class="fa-solid fa-radar text-2xl mb-2 text-gray-600 block"></i>
          Chưa có vị thế nào đang mở. Hệ thống đang quét các cặp coin để tìm setup tối ưu...
        </td>
      </tr>
    `;
    return;
  }

  $('positionsTableBody').innerHTML = positions.map(pos => {
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
      <tr class="hover:bg-darkCardHover/50 transition font-mono">
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

function renderGatekeeperFeed(data) {
  if (!$('aiAuditFeed')) return;
  const timeStr = data.last_updated || new Date().toLocaleTimeString('vi-VN');
  const btcMatrix = (data.protection_matrix && data.protection_matrix.btc_regime) || {};
  const regime = btcMatrix.regime || data.btc_regime || 'BULL';
  const regimeDesc = btcMatrix.desc || data.btc_regime_reason || 'Đồng pha xu hướng khung 1H/4H';
  const posCount = (data.positions || []).length;
  const maxPos = data.max_positions || 3;
  const lev = data.leverage || 5;
  const risk = data.risk_percent || 1.5;
  const adxMin = (data.protection_matrix && data.protection_matrix.adx_filter && data.protection_matrix.adx_filter.min_adx) || 20;
  const newsSafe = (data.protection_matrix && data.protection_matrix.news_filter && !data.protection_matrix.news_filter.is_blackout);
  const circuitSafe = !(data.circuit_breaker && data.circuit_breaker.triggered);

  $('aiAuditFeed').innerHTML = `
    <!-- Card 1: BTC Regime Safety Shield -->
    <div class="bg-darkBase border border-darkBorder rounded-lg p-2.5 hover:border-profitGreen/40 transition">
      <div class="flex items-center justify-between text-[11px] font-bold text-profitGreen mb-1">
        <span class="flex items-center space-x-1.5">
          <i class="fa-solid fa-shield-halved"></i>
          <span>Lá Chắn Xu Hướng BTC 1H/4H</span>
        </span>
        <span class="text-[10px] text-gray-500">${timeStr}</span>
      </div>
      <div class="text-[11px] text-gray-200">
        Trạng thái: <b class="text-binanceGold font-mono">${regime}</b>. ${regimeDesc}.
      </div>
      <div class="text-[10px] text-gray-400 mt-1 flex items-center space-x-2">
        <span>Chiều đánh: <b class="text-cyan-400">${btcMatrix.direction || 'AUTO'}</b></span>
        <span>•</span>
        <span>Phán quyết: <b class="text-profitGreen">AN TOÀN</b></span>
      </div>
    </div>

    <!-- Card 2: AI Gatekeeper Matrix Verdict -->
    <div class="bg-darkBase border border-darkBorder rounded-lg p-2.5 hover:border-purple-500/40 transition">
      <div class="flex items-center justify-between text-[11px] font-bold text-purple-400 mb-1">
        <span class="flex items-center space-x-1.5">
          <i class="fa-solid fa-microchip"></i>
          <span>Kiểm Toán Phân Bổ Vốn AI</span>
        </span>
        <span class="text-[10px] text-gray-500">DeepSeek V4.1</span>
      </div>
      <div class="text-[11px] text-gray-200">
        Giữ <b class="text-binanceGold font-mono">${posCount}/${maxPos}</b> vị thế. Đòn bẩy tối đa <b class="text-white font-mono">${lev}x</b>, rủi ro <b class="text-white font-mono">${risk}%</b>/lệnh.
      </div>
      <div class="text-[10px] text-gray-400 mt-1 flex items-center space-x-2">
        <span>Lọc ADX: <b class="text-cyan-400">≥ ${adxMin}</b></span>
        <span>•</span>
        <span>Tin tức: <b class="${newsSafe ? 'text-profitGreen' : 'text-lossRed'}">${newsSafe ? 'Bình thường' : 'Tin bão'}</b></span>
      </div>
    </div>

    <!-- Card 3: Live Scanner & Execution -->
    <div class="bg-darkBase border border-darkBorder rounded-lg p-2.5 hover:border-cyan-500/40 transition">
      <div class="flex items-center justify-between text-[11px] font-bold text-cyan-400 mb-1">
        <span class="flex items-center space-x-1.5">
          <i class="fa-solid fa-satellite-dish"></i>
          <span>Radar Quét Thị Trường Live</span>
        </span>
        <span class="text-[10px] text-gray-500">${data.active_strategy || 'AUTO_DYNAMIC'}</span>
      </div>
      <div class="text-[11px] text-gray-200">
        Chế độ: <b class="text-binanceGold font-mono">${data.trading_mode === 'BLUECHIP_ONLY' ? 'Chỉ BTC/ETH' : 'Top 80 Coin'}</b>. Cầu dao bảo vệ: <b class="${circuitSafe ? 'text-profitGreen' : 'text-lossRed'}">${circuitSafe ? 'Hoạt động an toàn' : 'Tạm khóa'}</b>.
      </div>
      <div class="text-[10px] text-gray-400 mt-1">
        Chốt lời đa tầng: 33% @ 1R | 33% @ 2R | 34% Trailing Runner.
      </div>
    </div>
  `;
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
    if ($('btnEmergencyClose')) $('btnEmergencyClose').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ĐANG ĐÓNG...';
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
    if ($('btnEmergencyClose')) $('btnEmergencyClose').innerHTML = '<i class="fa-solid fa-radiation"></i> <span>CẮT KHẨN CẤP [KILL-SWITCH]</span>';
  }
}

// =======================================================
// TAB 2: SCANNER 80 COIN RADAR
// =======================================================
function setupRadarFilters() {
  if ($('btnFilterAll')) $('btnFilterAll').addEventListener('click', () => setRadarFilter('ALL'));
  if ($('btnFilterLong')) $('btnFilterLong').addEventListener('click', () => setRadarFilter('LONG'));
  if ($('btnFilterShort')) $('btnFilterShort').addEventListener('click', () => setRadarFilter('SHORT'));
  if ($('btnFilterTrend')) $('btnFilterTrend').addEventListener('click', () => setRadarFilter('TREND'));
  if ($('inputRadarSearch')) $('inputRadarSearch').addEventListener('input', () => renderFilteredRadar());
}

function setRadarFilter(filter) {
  activeRadarFilter = filter;
  const filterBtns = [
    { btn: $('btnFilterAll'), name: 'ALL' },
    { btn: $('btnFilterLong'), name: 'LONG' },
    { btn: $('btnFilterShort'), name: 'SHORT' },
    { btn: $('btnFilterTrend'), name: 'TREND' }
  ];

  filterBtns.forEach(({ btn, name }) => {
    if (!btn) return;
    if (name === filter) {
      btn.className = 'px-2.5 py-1 rounded bg-binanceGold/20 text-binanceGold font-semibold border border-binanceGold/30';
    } else {
      btn.className = 'px-2.5 py-1 rounded bg-darkBase border border-darkBorder text-gray-400 hover:text-white';
    }
  });

  renderFilteredRadar();
}

async function pollRadar() {
  try {
    const data = await fetchApi('/api/radar');
    if (data && data.pairs) {
      cachedRadarPairs = data.pairs;
      renderFilteredRadar();
    }
  } catch (e) {
    console.debug('Lỗi nạp Radar:', e);
  }
}

function renderFilteredRadar() {
  if (!$('radarCardsGrid')) return;
  const search = ($('inputRadarSearch') ? $('inputRadarSearch').value : '').trim().toUpperCase();

  let filtered = cachedRadarPairs.filter(p => {
    if (search && !p.symbol.toUpperCase().includes(search)) return false;
    if (activeRadarFilter === 'LONG') return p.signal === 'BUY' || p.trend === 'UP';
    if (activeRadarFilter === 'SHORT') return p.signal === 'SELL' || p.trend === 'DOWN';
    if (activeRadarFilter === 'TREND') return (p.adx || 0) >= 25;
    return true;
  });

  if (filtered.length === 0) {
    $('radarCardsGrid').innerHTML = `
      <div class="col-span-4 text-center py-12 text-gray-500 font-mono">
        <i class="fa-solid fa-satellite-dish text-2xl mb-2 text-gray-600 block"></i>
        Không tìm thấy cặp coin nào thỏa mãn tiêu chí lọc (${activeRadarFilter}).
      </div>
    `;
    return;
  }

  $('radarCardsGrid').innerHTML = filtered.map(pair => {
    const isUp = pair.trend === 'UP' || pair.signal === 'BUY';
    const isDown = pair.trend === 'DOWN' || pair.signal === 'SELL';
    const badge = isUp 
      ? '<span class="px-2 py-0.5 rounded bg-profitGreen/20 text-profitGreen text-[10px] font-bold border border-profitGreen/30">MUA (Long) ▲</span>'
      : (isDown 
        ? '<span class="px-2 py-0.5 rounded bg-lossRed/20 text-lossRed text-[10px] font-bold border border-lossRed/30">BÁN (Short) ▼</span>'
        : '<span class="px-2 py-0.5 rounded bg-gray-500/20 text-gray-400 text-[10px] font-bold">CHỜ •</span>');

    const price = Number(pair.price || 0);
    const priceStr = price >= 1 ? price.toFixed(2) : price.toFixed(4);
    const adx = Number(pair.adx || 25).toFixed(1);
    const rsi = Number(pair.rsi || 50).toFixed(1);

    return `
      <div class="bg-darkCard border border-darkBorder rounded-xl p-3 hover:border-binanceGold/50 transition shadow-sm font-mono">
        <div class="flex items-center justify-between">
          <span class="font-bold text-white text-xs">${pair.symbol}</span>
          ${badge}
        </div>
        <div class="flex items-baseline justify-between mt-2">
          <span class="text-sm font-bold text-white">$${priceStr}</span>
          <span class="text-[10px] text-gray-400">RSI ${rsi}</span>
        </div>
        <div class="flex items-center justify-between text-[10px] text-gray-500 mt-1 border-t border-darkBorder/50 pt-1.5">
          <span>Xu hướng: <b class="${isUp ? 'text-profitGreen' : (isDown ? 'text-lossRed' : 'text-gray-400')}">${pair.trend || 'N/A'}</b></span>
          <span class="text-cyan-400 font-semibold">ADX ${adx}</span>
        </div>
      </div>
    `;
  }).join('');
}

// =======================================================
// TAB 3: LỊCH SỬ & PHÂN TÍCH (HISTORY & ANALYTICS)
// =======================================================
async function loadHistoryData() {
  try {
    const res = await fetchApi('/api/history');
    if (!res) return;

    const summary = res.summary || {};
    const trades = res.trades || [];
    const chartData = res.chart_data || [];

    // Cập nhật thẻ KPI
    if ($('histTotalTrades')) $('histTotalTrades').textContent = summary.total || 0;
    const wr = summary.win_rate !== undefined ? Number(summary.win_rate).toFixed(1) : '0.0';
    if ($('histWinRate')) $('histWinRate').textContent = `${wr}%`;
    if ($('histWinLoss')) $('histWinLoss').textContent = `${summary.wins || 0} Thắng / ${summary.losses || 0} Thua`;

    const netPnl = summary.net_pnl !== undefined ? Number(summary.net_pnl) : 0.0;
    const netPrefix = netPnl >= 0 ? '+' : '';
    if ($('histNetPnl')) {
      $('histNetPnl').textContent = `${netPrefix}$${netPnl.toFixed(2)} USDT`;
      $('histNetPnl').className = `text-lg font-bold mt-0.5 ${netPnl >= 0 ? 'text-profitGreen' : 'text-lossRed'}`;
    }

    // Tính Profit Factor
    let grossWin = 0, grossLoss = 0;
    trades.forEach(t => {
      const p = parseFloat(t.pnl_usdt || 0);
      if (p > 0) grossWin += p;
      else if (p < 0) grossLoss += Math.abs(p);
    });
    const pf = grossLoss > 0 ? (grossWin / grossLoss).toFixed(2) : (grossWin > 0 ? '99.9' : '0.00');
    if ($('histProfitFactor')) $('histProfitFactor').textContent = pf;

    // Vẽ biểu đồ Equity Curve SVG
    renderEquityCurve(chartData);

    // Vẽ bảng lịch sử giao dịch
    renderHistoryTable(trades);

  } catch (e) {
    console.debug('Lỗi nạp lịch sử:', e);
  }
}

function renderEquityCurve(chartData) {
  if (!$('equityChartContainer')) return;
  if (!chartData || chartData.length === 0) {
    $('equityChartContainer').innerHTML = '<div class="text-gray-500">Chưa có giao dịch hoàn tất nào trong chu kỳ này để vẽ đường cong vốn.</div>';
    return;
  }

  const w = $('equityChartContainer').clientWidth || 750;
  const h = 100;
  const pad = 24;

  const cumValues = chartData.map(d => d.cum_pnl || 0);
  const minVal = Math.min(0, ...cumValues);
  const maxVal = Math.max(1, ...cumValues);
  const range = (maxVal - minVal) || 1;

  const getX = (idx) => pad + (idx / Math.max(1, chartData.length - 1)) * (w - pad * 2);
  const getY = (val) => h - pad - ((val - minVal) / range) * (h - pad * 2);

  const points = chartData.map((d, i) => `${getX(i).toFixed(1)},${getY(d.cum_pnl || 0).toFixed(1)}`).join(' ');
  const zeroY = getY(0).toFixed(1);
  const finalVal = cumValues[cumValues.length - 1];
  const strokeColor = finalVal >= 0 ? '#0ECB81' : '#F6465D';

  $('equityChartContainer').innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" class="w-full h-full">
      <defs>
        <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${strokeColor}" stop-opacity="0.25" />
          <stop offset="100%" stop-color="${strokeColor}" stop-opacity="0.0" />
        </linearGradient>
      </defs>
      <line x1="${pad}" y1="${zeroY}" x2="${w - pad}" y2="${zeroY}" stroke="#2B313A" stroke-dasharray="3,3" stroke-width="1" />
      <text x="${pad}" y="${Math.max(12, zeroY - 4)}" fill="#6B7280" font-size="9" font-family="monospace">$0</text>
      <polygon points="${getX(0)},${h - pad} ${points} ${getX(chartData.length - 1)},${h - pad}" fill="url(#equityGrad)" />
      <polyline fill="none" stroke="${strokeColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="${points}" />
      <circle cx="${getX(chartData.length - 1)}" cy="${getY(finalVal)}" r="3.5" fill="${strokeColor}" />
      <text x="${w - pad - 60}" y="${Math.min(h - 8, getY(finalVal) - 6)}" fill="${strokeColor}" font-size="10" font-weight="bold" font-family="monospace">
        ${finalVal >= 0 ? '+' : ''}$${finalVal.toFixed(2)}
      </text>
    </svg>
  `;
}

function renderHistoryTable(trades) {
  if (!$('historyTableBody')) return;
  if (!trades || trades.length === 0) {
    $('historyTableBody').innerHTML = `
      <tr>
        <td colspan="8" class="text-center py-10 text-gray-500 font-mono">
          Chưa có lệnh nào được ghi nhận vào trade_history.csv
        </td>
      </tr>
    `;
    return;
  }

  $('historyTableBody').innerHTML = trades.map((t, idx) => {
    const isLong = (t.side || 'BUY').toUpperCase().includes('BUY') || (t.side || '').toUpperCase().includes('LONG');
    const sideBadge = isLong 
      ? '<span class="text-profitGreen font-bold">LONG</span>' 
      : '<span class="text-lossRed font-bold">SHORT</span>';

    const pnl = parseFloat(t.pnl_usdt || 0);
    const pnlColor = pnl >= 0 ? 'text-profitGreen' : 'text-lossRed';
    const pnlPrefix = pnl >= 0 ? '+' : '';

    return `
      <tr class="hover:bg-darkCardHover/40 transition font-mono">
        <td class="py-2.5 text-gray-500">${idx + 1}</td>
        <td class="py-2.5 text-gray-300">${t.timestamp || '--'}</td>
        <td class="py-2.5 font-bold text-white">${t.symbol || '--'}</td>
        <td class="py-2.5">${sideBadge}</td>
        <td class="py-2.5 text-gray-300">$${Number(t.entry_price || 0).toFixed(4)}</td>
        <td class="py-2.5 text-gray-300">$${Number(t.exit_price || 0).toFixed(4)}</td>
        <td class="py-2.5 font-bold ${pnlColor}">${pnlPrefix}$${pnl.toFixed(2)}</td>
        <td class="py-2.5 text-gray-400 text-[11px]">${escapeHtml(t.exit_reason || t.reason || 'Đóng chuẩn')}</td>
      </tr>
    `;
  }).join('');
}

// =======================================================
// TAB 4: CẤU HÌNH THAM SỐ CHIẾN LƯỢC LIVE
// =======================================================
function setupStrategySliders() {
  if ($('stratLeverage') && $('stratLeverageVal')) {
    $('stratLeverage').addEventListener('input', () => {
      $('stratLeverageVal').textContent = `${$('stratLeverage').value}x`;
    });
  }
  if ($('stratRisk') && $('stratRiskVal')) {
    $('stratRisk').addEventListener('input', () => {
      $('stratRiskVal').textContent = `${parseFloat($('stratRisk').value).toFixed(1)}%`;
    });
  }
  if ($('stratAdx') && $('stratAdxVal')) {
    $('stratAdx').addEventListener('input', () => {
      $('stratAdxVal').textContent = $('stratAdx').value;
    });
  }

  if ($('stratBtnBluechip')) {
    $('stratBtnBluechip').addEventListener('click', () => {
      activeTradingMode = 'BLUECHIP_ONLY';
      updateTradingModeButtons();
    });
  }
  if ($('stratBtnMarket')) {
    $('stratBtnMarket').addEventListener('click', () => {
      activeTradingMode = 'MARKET_ALL';
      updateTradingModeButtons();
    });
  }

  if ($('btnSaveLiveStrategy')) {
    $('btnSaveLiveStrategy').addEventListener('click', saveLiveStrategySettings);
  }
}

async function loadStrategySettings() {
  try {
    const data = await fetchApi('/api/status');
    if (!data) return;

    activeTradingMode = data.trading_mode || 'MARKET_ALL';
    updateTradingModeButtons();

    if ($('stratLeverage') && data.leverage) {
      $('stratLeverage').value = data.leverage;
      if ($('stratLeverageVal')) $('stratLeverageVal').textContent = `${data.leverage}x`;
    }
    if ($('stratRisk') && data.risk_percent) {
      $('stratRisk').value = data.risk_percent;
      if ($('stratRiskVal')) $('stratRiskVal').textContent = `${parseFloat(data.risk_percent).toFixed(1)}%`;
    }
    if ($('stratAdx') && data.protection_matrix && data.protection_matrix.adx_filter) {
      const adx = data.protection_matrix.adx_filter.min_adx || 20;
      $('stratAdx').value = adx;
      if ($('stratAdxVal')) $('stratAdxVal').textContent = adx;
    }
    if ($('stratHardCap') && data.real_trading_hard_cap) {
      $('stratHardCap').value = data.real_trading_hard_cap;
    }
    if ($('stratTrailingStop') && data.use_trailing_stop !== undefined) {
      $('stratTrailingStop').checked = !!data.use_trailing_stop;
    }
    if ($('stratBtcFilter') && data.protection_matrix && data.protection_matrix.btc_regime) {
      $('stratBtcFilter').checked = data.protection_matrix.btc_regime.enabled !== false;
      const dir = data.protection_matrix.btc_regime.direction || 'AUTO';
      if ($('stratTradeDirection')) $('stratTradeDirection').value = dir;
    }
    if ($('stratDynamicLev') && data.protection_matrix && data.protection_matrix.dynamic_leverage) {
      $('stratDynamicLev').checked = data.protection_matrix.dynamic_leverage.enabled !== false;
    }
  } catch (e) {
    console.debug('Lỗi đọc cấu hình chiến lược:', e);
  }
}

async function saveLiveStrategySettings() {
  if (!$('btnSaveLiveStrategy')) return;
  $('btnSaveLiveStrategy').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ĐANG LƯU...';
  if ($('stratStatusMsg')) $('stratStatusMsg').className = 'hidden';

  const payload = {
    trading_mode: activeTradingMode,
    trade_direction: $('stratTradeDirection') ? $('stratTradeDirection').value : 'AUTO',
    leverage: $('stratLeverage') ? parseInt($('stratLeverage').value, 10) : 5,
    risk_percent: $('stratRisk') ? parseFloat($('stratRisk').value) : 1.5,
    adx_min: $('stratAdx') ? parseFloat($('stratAdx').value) : 20,
    real_trading_hard_cap: $('stratHardCap') ? parseFloat($('stratHardCap').value) : 100,
    use_trailing_stop: $('stratTrailingStop') ? $('stratTrailingStop').checked : false,
    enable_btc_regime_filter: $('stratBtcFilter') ? $('stratBtcFilter').checked : true,
    enable_dynamic_leverage: $('stratDynamicLev') ? $('stratDynamicLev').checked : true
  };

  try {
    await fetchApi('/api/update_settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if ($('stratStatusMsg')) {
      $('stratStatusMsg').className = 'p-3 rounded-lg text-xs font-mono text-center bg-profitGreen/20 text-profitGreen border border-profitGreen/40';
      $('stratStatusMsg').innerHTML = '<i class="fa-solid fa-circle-check"></i> Đã lưu cấu hình thời gian thực thành công lên máy chủ VPS!';
    }
    audioSynth.playTakeProfitSound();
    pollDashboardData();
  } catch (err) {
    if ($('stratStatusMsg')) {
      $('stratStatusMsg').className = 'p-3 rounded-lg text-xs font-mono text-center bg-lossRed/20 text-lossRed border border-lossRed/40';
      $('stratStatusMsg').innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Không thể lưu cấu hình: ${err.message}`;
    }
  } finally {
    if ($('btnSaveLiveStrategy')) $('btnSaveLiveStrategy').innerHTML = '<i class="fa-solid fa-floppy-disk"></i> <span>LƯU CẤU HÌNH LIVE</span>';
  }
}

// =======================================================
// TAB 5: NHẬT KÝ LOGS LIVE STREAM TERMINAL
// =======================================================
async function pollLiveLogs() {
  if (!$('logTerminalBox')) return;
  try {
    const res = await fetchApi('/api/logs?lines=120');
    if (!res || !res.lines) return;

    if (res.source && $('logSourceBadge')) {
      $('logSourceBadge').textContent = `Nguồn: ${res.source}`;
    }

    $('logTerminalBox').innerHTML = res.lines.map(line => {
      let colorClass = 'text-gray-300';
      if (line.includes('ERROR') || line.includes('CRITICAL') || line.includes('Exception')) {
        colorClass = 'text-lossRed font-bold';
      } else if (line.includes('WARNING') || line.includes('CẢNH BÁO')) {
        colorClass = 'text-yellow-400';
      } else if (line.includes('KHỚP LỆNH') || line.includes('BUY') || line.includes('LONG') || line.includes('THẮNG')) {
        colorClass = 'text-profitGreen font-bold';
      } else if (line.includes('SELL') || line.includes('SHORT')) {
        colorClass = 'text-red-400 font-bold';
      } else if (line.includes('DeepSeek') || line.includes('AI') || line.includes('Gatekeeper')) {
        colorClass = 'text-purple-300';
      }

      return `<div class="${colorClass} hover:bg-white/5 px-1 py-0.5 rounded transition">${escapeHtml(line)}</div>`;
    }).join('');

    if ($('logAutoScroll') && $('logAutoScroll').checked) {
      $('logTerminalBox').scrollTop = $('logTerminalBox').scrollHeight;
    }
  } catch (e) {
    console.debug('Lỗi nạp logs:', e);
  }
}

// =======================================================
// TAB 6: TRỢ LÝ AI QUANT COPILOT
// =======================================================
function setupAiQuickButtons() {
  document.querySelectorAll('.ai-quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const prompt = btn.textContent.replace(/^[^\s]+\s+/, '');
      if ($('aiChatInput')) $('aiChatInput').value = prompt;
      if ($('aiChatForm')) $('aiChatForm').dispatchEvent(new Event('submit'));
    });
  });

  if ($('aiChatForm')) {
    $('aiChatForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const query = $('aiChatInput') ? $('aiChatInput').value.trim() : '';
      if (!query || !$('aiChatMessages')) return;

      const userMsgDiv = document.createElement('div');
      userMsgDiv.className = 'bg-binanceGold/10 border border-binanceGold/30 text-white rounded-lg p-2.5 ml-8 text-xs font-mono';
      userMsgDiv.innerHTML = `<b>Bạn:</b> ${escapeHtml(query)}`;
      $('aiChatMessages').appendChild(userMsgDiv);
      if ($('aiChatInput')) $('aiChatInput').value = '';
      $('aiChatMessages').scrollTop = $('aiChatMessages').scrollHeight;

      const botThinking = document.createElement('div');
      botThinking.className = 'bg-darkBase/70 border border-darkBorder text-gray-400 rounded-lg p-2.5 mr-8 text-xs font-mono flex items-center space-x-2';
      botThinking.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-purple-400"></i> <span>DeepSeek V4.1 Flash đang phân tích định lượng...</span>';
      $('aiChatMessages').appendChild(botThinking);
      $('aiChatMessages').scrollTop = $('aiChatMessages').scrollHeight;

      try {
        const res = await fetchApi('/api/ai_chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: query, query: query })
        });
        botThinking.remove();

        const botMsgDiv = document.createElement('div');
        botMsgDiv.className = 'bg-darkBase border border-purple-500/30 text-gray-200 rounded-lg p-2.5 mr-8 text-xs leading-relaxed font-mono';
        botMsgDiv.innerHTML = `<div class="flex items-center space-x-1.5 text-purple-400 font-bold mb-1"><i class="fa-solid fa-brain text-[10px]"></i><span>Trợ Lý Quant (${(res && res.provider) || 'DeepSeek V4.1'}):</span></div>${escapeHtml((res && (res.reply || res.response)) || 'Không có phản hồi từ mô hình AI.')}`;
        $('aiChatMessages').appendChild(botMsgDiv);
        $('aiChatMessages').scrollTop = $('aiChatMessages').scrollHeight;
      } catch (err) {
        botThinking.remove();
        const errorDiv = document.createElement('div');
        errorDiv.className = 'bg-lossRed/10 border border-lossRed/30 text-lossRed rounded-lg p-2 text-xs font-mono';
        errorDiv.textContent = `Lỗi kết nối AI: ${err.message}`;
        $('aiChatMessages').appendChild(errorDiv);
      }
    });
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

// =======================================================
// NÚT HEADER & CÀI ĐẶT CHUNG
// =======================================================
function setupHeaderButtons() {
  if ($('btnExportCsv')) {
    $('btnExportCsv').addEventListener('click', () => {
      const url = `${serverUrl.replace(/\/+$/, '')}/api/download_csv`;
      window.open(url, '_blank');
    });
  }

  if ($('btnRefreshLogs')) $('btnRefreshLogs').addEventListener('click', pollLiveLogs);
  if ($('btnClearLogs')) {
    $('btnClearLogs').addEventListener('click', () => {
      if ($('logTerminalBox')) $('logTerminalBox').innerHTML = '<div class="text-gray-600">Đã xóa khung nhìn logs tạm thời. Nhấn Làm Mới để tải lại.</div>';
    });
  }

  if ($('btnAudioToggle')) {
    $('btnAudioToggle').addEventListener('click', () => {
      soundEnabled = !soundEnabled;
      updateAudioIcon();
      saveDesktopConfig({ soundEnabled });
      if (soundEnabled) audioSynth.playEntrySound();
    });
  }

  if ($('btnEmergencyClose')) $('btnEmergencyClose').addEventListener('click', executeEmergencyClose);
  if ($('btnLoginOpen')) $('btnLoginOpen').addEventListener('click', () => showLoginModal());
  if ($('btnCloseLogin')) $('btnCloseLogin').addEventListener('click', hideLoginModal);

  if ($('btnLoginSubmit')) {
    $('btnLoginSubmit').addEventListener('click', async () => {
      const user = $('loginUsername') ? $('loginUsername').value.trim() : '';
      const pass = $('loginPassword') ? $('loginPassword').value.trim() : '';
      if (!user || !pass) {
        if ($('loginErrorMsg')) {
          $('loginErrorMsg').textContent = 'Vui lòng nhập đầy đủ tài khoản và mật khẩu!';
          $('loginErrorMsg').classList.remove('hidden');
        }
        return;
      }

      $('btnLoginSubmit').innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ĐANG XÁC THỰC...';
      try {
        const success = await loginWithCredentials(user, pass);
        if (success) {
          if ($('loginPassword')) $('loginPassword').value = '';
          hideLoginModal();
          pollDashboardData();
        } else {
          if ($('loginErrorMsg')) {
            $('loginErrorMsg').textContent = 'Sai tên đăng nhập hoặc mật khẩu quản trị!';
            $('loginErrorMsg').classList.remove('hidden');
          }
        }
      } catch (e) {
        if ($('loginErrorMsg')) {
          $('loginErrorMsg').textContent = `Lỗi kết nối: ${e.message}`;
          $('loginErrorMsg').classList.remove('hidden');
        }
      } finally {
        $('btnLoginSubmit').innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> <span>XÁC NHẬN ĐĂNG NHẬP</span>';
      }
    });
  }

  if ($('btnSettings')) $('btnSettings').addEventListener('click', () => $('settingsModal') && $('settingsModal').classList.remove('hidden'));
  if ($('btnCloseSettings')) $('btnCloseSettings').addEventListener('click', () => $('settingsModal') && $('settingsModal').classList.add('hidden'));
  if ($('btnCancelSettings')) $('btnCancelSettings').addEventListener('click', () => $('settingsModal') && $('settingsModal').classList.add('hidden'));

  if ($('btnSaveSettings')) {
    $('btnSaveSettings').addEventListener('click', async () => {
      serverUrl = $('cfgServerUrl') ? $('cfgServerUrl').value.trim() : serverUrl;
      soundEnabled = $('cfgSound') ? $('cfgSound').checked : soundEnabled;
      const minimizeTray = $('cfgMinimizeTray') ? $('cfgMinimizeTray').checked : false;
      const hotkey = $('cfgHotkey') ? $('cfgHotkey').value.trim() : 'Ctrl+Shift+K';

      saveDesktopConfig({
        serverUrl,
        soundEnabled,
        minimizeToTray: minimizeTray,
        hotkeyEmergency: hotkey
      });

      updateAudioIcon();
      if ($('settingsModal')) $('settingsModal').classList.add('hidden');
      pollDashboardData();
    });
  }

  if ($('btnModeBluechip')) {
    $('btnModeBluechip').addEventListener('click', async () => {
      activeTradingMode = 'BLUECHIP_ONLY';
      await fetchApi('/api/update_settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trading_mode: 'BLUECHIP_ONLY' })
      });
      updateTradingModeButtons();
      pollDashboardData();
    });
  }

  if ($('btnModeMarket')) {
    $('btnModeMarket').addEventListener('click', async () => {
      activeTradingMode = 'MARKET_ALL';
      await fetchApi('/api/update_settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ trading_mode: 'MARKET_ALL' })
      });
      updateTradingModeButtons();
      pollDashboardData();
    });
  }

  if ($('btnPauseResume')) $('btnPauseResume').addEventListener('click', () => togglePauseResume());
}

function updateAudioIcon() {
  if (!$('btnAudioToggle')) return;
  if (soundEnabled) {
    $('btnAudioToggle').innerHTML = '<i class="fa-solid fa-volume-high text-xs text-binanceGold"></i>';
    $('btnAudioToggle').title = 'Âm thanh: BẬT';
  } else {
    $('btnAudioToggle').innerHTML = '<i class="fa-solid fa-volume-xmark text-xs text-gray-500"></i>';
    $('btnAudioToggle').title = 'Âm thanh: TẮT';
  }
}

function showLoginModal(msg = '') {
  if (!$('loginModal')) return;
  $('loginModal').classList.remove('hidden');
  if ($('loginErrorMsg')) {
    if (msg) {
      $('loginErrorMsg').textContent = msg;
      $('loginErrorMsg').classList.remove('hidden');
    } else {
      $('loginErrorMsg').classList.add('hidden');
    }
  }
}

function hideLoginModal() {
  if ($('loginModal')) $('loginModal').classList.add('hidden');
}

async function saveDesktopConfig(patch) {
  try {
    const safePatch = { ...(patch || {}) };
    delete safePatch.authToken;
    const local = localStorage.getItem('desktop_config');
    const stored = local ? JSON.parse(local) : {};
    delete stored.authToken;
    const merged = { ...stored, ...safePatch };
    localStorage.removeItem('auth_token');
    localStorage.setItem('desktop_config', JSON.stringify(merged));
    if (window.electronAPI) {
      await window.electronAPI.saveConfig(merged);
    } else if (window.pywebview && window.pywebview.api) {
      await window.pywebview.api.save_config(merged);
    }
  } catch (e) {}
}

async function togglePauseResume() {
  await fetchApi('/api/toggle_pause', { method: 'POST' });
  pollDashboardData();
}

// Bắt đầu khởi tạo
initApp();
