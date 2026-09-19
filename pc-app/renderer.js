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

// Các phần tử DOM chung
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
const aiAuditFeed = document.getElementById('aiAuditFeed');
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

// Các phần tử Navigation 6 Tabs
const tabBtns = {
  overview: document.getElementById('tabBtnOverview'),
  radar: document.getElementById('tabBtnRadar'),
  history: document.getElementById('tabBtnHistory'),
  strategy: document.getElementById('tabBtnStrategy'),
  logs: document.getElementById('tabBtnLogs'),
  ai: document.getElementById('tabBtnAi')
};

const viewPanels = {
  overview: document.getElementById('viewOverview'),
  radar: document.getElementById('viewRadar'),
  history: document.getElementById('viewHistory'),
  strategy: document.getElementById('viewStrategy'),
  logs: document.getElementById('viewLogs'),
  ai: document.getElementById('viewAi')
};

// Phần tử Tab 2: Scanner Radar
const inputRadarSearch = document.getElementById('inputRadarSearch');
const btnFilterAll = document.getElementById('btnFilterAll');
const btnFilterLong = document.getElementById('btnFilterLong');
const btnFilterShort = document.getElementById('btnFilterShort');
const btnFilterTrend = document.getElementById('btnFilterTrend');
const radarCardsGrid = document.getElementById('radarCardsGrid');

// Phần tử Tab 3: History & Analytics
const histTotalTrades = document.getElementById('histTotalTrades');
const histWinRate = document.getElementById('histWinRate');
const histWinLoss = document.getElementById('histWinLoss');
const histNetPnl = document.getElementById('histNetPnl');
const histProfitFactor = document.getElementById('histProfitFactor');
const btnExportCsv = document.getElementById('btnExportCsv');
const equityChartContainer = document.getElementById('equityChartContainer');
const historyTableBody = document.getElementById('historyTableBody');

// Phần tử Tab 4: Strategy Settings
const stratBtnBluechip = document.getElementById('stratBtnBluechip');
const stratBtnMarket = document.getElementById('stratBtnMarket');
const stratTradeDirection = document.getElementById('stratTradeDirection');
const stratLeverage = document.getElementById('stratLeverage');
const stratLeverageVal = document.getElementById('stratLeverageVal');
const stratRisk = document.getElementById('stratRisk');
const stratRiskVal = document.getElementById('stratRiskVal');
const stratAdx = document.getElementById('stratAdx');
const stratAdxVal = document.getElementById('stratAdxVal');
const stratHardCap = document.getElementById('stratHardCap');
const stratTrailingStop = document.getElementById('stratTrailingStop');
const stratBtcFilter = document.getElementById('stratBtcFilter');
const stratDynamicLev = document.getElementById('stratDynamicLev');
const btnSaveLiveStrategy = document.getElementById('btnSaveLiveStrategy');
const stratStatusMsg = document.getElementById('stratStatusMsg');

// Phần tử Tab 5: Logs Live
const logTerminalBox = document.getElementById('logTerminalBox');
const logAutoScroll = document.getElementById('logAutoScroll');
const btnRefreshLogs = document.getElementById('btnRefreshLogs');
const btnClearLogs = document.getElementById('btnClearLogs');
const logSourceBadge = document.getElementById('logSourceBadge');

// Phần tử Tab 6: AI Copilot
const aiChatMessages = document.getElementById('aiChatMessages');
const aiChatForm = document.getElementById('aiChatForm');
const aiChatInput = document.getElementById('aiChatInput');

// =======================================================
// KHỞI CHẠY ỨNG DỤNG
// =======================================================
async function initApp() {
  let cfg = {
    serverUrl: 'https://trader.noza.site',
    authToken: '',
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

  setupNavigationTabs();
  setupRadarFilters();
  setupStrategySliders();
  setupAiQuickButtons();

  if (!authToken) {
    await tryAutoLogin('admin', 'admin123456');
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
  Object.keys(tabBtns).forEach((tabKey) => {
    const btn = tabBtns[tabKey];
    if (!btn) return;
    btn.addEventListener('click', () => switchTab(tabKey));
  });
}

function switchTab(tabKey) {
  currentActiveTab = tabKey;
  Object.keys(tabBtns).forEach((key) => {
    const btn = tabBtns[key];
    const view = viewPanels[key];
    if (!btn || !view) return;

    if (key === tabKey) {
      btn.classList.add('bg-darkCardHover', 'text-white');
      btn.classList.remove('text-gray-400');
      view.classList.remove('hidden');
      if (key === 'strategy') {
        view.classList.add('block');
      } else {
        view.classList.add('flex');
      }
    } else {
      btn.classList.remove('bg-darkCardHover', 'text-white');
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

// =======================================================
// TAB 1: TỔNG QUAN & VỊ THẾ LIVE
// =======================================================
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

    // 2. Lá chắn BTC Regime
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

    // 3. Tâm lý Fear & Greed
    if (data.fear_and_greed) {
      statFng.innerHTML = `<i class="fa-solid fa-fire text-amber-500"></i> <span>${data.fear_and_greed.value}/100 (${data.fear_and_greed.classification_vi || 'Tham Lam'})</span>`;
    }

    // 4. Circuit Breaker
    if (data.circuit_breaker && data.circuit_breaker.triggered) {
      statCircuit.innerHTML = '<i class="fa-solid fa-triangle-exclamation text-lossRed"></i> <span class="text-lossRed">ĐANG KHÓA COOLDOWN</span>';
    } else {
      statCircuit.innerHTML = '<i class="fa-solid fa-circle-check text-profitGreen"></i> <span class="text-profitGreen">BẢO VỆ AN TOÀN</span>';
    }

    // 5. Danh sách vị thế đang mở
    const positions = data.positions || [];
    renderPositions(positions);
    badgePosCount.textContent = `${positions.length}/${data.max_positions || data.max_concurrent_positions || 3}`;

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
    activeTradingMode = data.trading_mode || 'MARKET_ALL';
    updateTradingModeButtons();

    // 8. Gatekeeper Audit Feed
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
  if (activeTradingMode === 'BLUECHIP_ONLY') {
    btnModeBluechip.className = 'px-2.5 py-1 rounded bg-binanceGold/20 text-binanceGold font-semibold transition';
    btnModeMarket.className = 'px-2.5 py-1 rounded text-gray-400 hover:text-white transition';
    stratBtnBluechip.className = 'py-2 px-3 rounded-lg border border-binanceGold/40 bg-binanceGold/20 text-binanceGold font-bold transition text-center';
    stratBtnMarket.className = 'py-2 px-3 rounded-lg border border-darkBorder text-gray-400 hover:text-white transition text-center';
  } else {
    btnModeMarket.className = 'px-2.5 py-1 rounded bg-binanceGold/20 text-binanceGold font-semibold transition';
    btnModeBluechip.className = 'px-2.5 py-1 rounded text-gray-400 hover:text-white transition';
    stratBtnMarket.className = 'py-2 px-3 rounded-lg border border-binanceGold/40 bg-binanceGold/20 text-binanceGold font-bold transition text-center';
    stratBtnBluechip.className = 'py-2 px-3 rounded-lg border border-darkBorder text-gray-400 hover:text-white transition text-center';
  }
}

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
  if (!aiAuditFeed) return;
  const timeStr = new Date().toLocaleTimeString('vi-VN');
  const btcMatrix = (data.protection_matrix && data.protection_matrix.btc_regime) || {};
  const regime = btcMatrix.regime || 'BULL';
  const posCount = (data.positions || []).length;

  aiAuditFeed.innerHTML = `
    <div class="bg-darkBase border border-darkBorder rounded-lg p-2.5">
      <div class="flex items-center justify-between text-[11px] font-bold text-profitGreen mb-1">
        <span><i class="fa-solid fa-shield-check"></i> BTC Trend Filter</span>
        <span class="text-[10px] text-gray-500">${timeStr}</span>
      </div>
      <div class="text-[11px] text-gray-300">Bộ lọc trạng thái: <b class="text-binanceGold">${regime}</b>. ${btcMatrix.desc || 'Đang bảo vệ vốn an toàn'}.</div>
    </div>
    <div class="bg-darkBase border border-darkBorder rounded-lg p-2.5">
      <div class="flex items-center justify-between text-[11px] font-bold text-cyan-400 mb-1">
        <span><i class="fa-solid fa-chart-pie"></i> Giám Sát Danh Mục</span>
        <span class="text-[10px] text-gray-500">${timeStr}</span>
      </div>
      <div class="text-[11px] text-gray-300">Đang giữ ${posCount} vị thế. Đòn bẩy ${data.leverage || 5}x với rủi ro ${data.risk_percent || 1.5}%/vị thế.</div>
    </div>
    <div class="bg-darkBase border border-darkBorder rounded-lg p-2.5">
      <div class="flex items-center justify-between text-[11px] font-bold text-purple-400 mb-1">
        <span><i class="fa-solid fa-microchip"></i> AI Gatekeeper Validator</span>
        <span class="text-[10px] text-gray-500">${timeStr}</span>
      </div>
      <div class="text-[11px] text-gray-300">Bộ não DeepSeek V4.1 kết nối thời gian thực, sẵn sàng phân tích tín hiệu quét.</div>
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

// =======================================================
// TAB 2: SCANNER 80 COIN RADAR
// =======================================================
function setupRadarFilters() {
  btnFilterAll.addEventListener('click', () => setRadarFilter('ALL'));
  btnFilterLong.addEventListener('click', () => setRadarFilter('LONG'));
  btnFilterShort.addEventListener('click', () => setRadarFilter('SHORT'));
  btnFilterTrend.addEventListener('click', () => setRadarFilter('TREND'));

  inputRadarSearch.addEventListener('input', () => renderFilteredRadar());
}

function setRadarFilter(filter) {
  activeRadarFilter = filter;
  const filterBtns = [
    { btn: btnFilterAll, name: 'ALL' },
    { btn: btnFilterLong, name: 'LONG' },
    { btn: btnFilterShort, name: 'SHORT' },
    { btn: btnFilterTrend, name: 'TREND' }
  ];

  filterBtns.forEach(({ btn, name }) => {
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
  if (!radarCardsGrid) return;
  const search = (inputRadarSearch.value || '').trim().toUpperCase();

  let filtered = cachedRadarPairs.filter(p => {
    if (search && !p.symbol.toUpperCase().includes(search)) return false;
    if (activeRadarFilter === 'LONG') return p.signal === 'BUY' || p.trend === 'UP';
    if (activeRadarFilter === 'SHORT') return p.signal === 'SELL' || p.trend === 'DOWN';
    if (activeRadarFilter === 'TREND') return (p.adx || 0) >= 25;
    return true;
  });

  if (filtered.length === 0) {
    radarCardsGrid.innerHTML = `
      <div class="col-span-4 text-center py-12 text-gray-500 font-mono">
        <i class="fa-solid fa-satellite-dish text-2xl mb-2 text-gray-600 block"></i>
        Không tìm thấy cặp coin nào thỏa mãn tiêu chí lọc (${activeRadarFilter}).
      </div>
    `;
    return;
  }

  radarCardsGrid.innerHTML = filtered.map(pair => {
    const isUp = pair.trend === 'UP' || pair.signal === 'BUY';
    const isDown = pair.trend === 'DOWN' || pair.signal === 'SELL';
    const badge = isUp 
      ? '<span class="px-2 py-0.5 rounded bg-profitGreen/20 text-profitGreen text-[10px] font-bold border border-profitGreen/30">LONG ▲</span>'
      : (isDown 
        ? '<span class="px-2 py-0.5 rounded bg-lossRed/20 text-lossRed text-[10px] font-bold border border-lossRed/30">SHORT ▼</span>'
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
    histTotalTrades.textContent = summary.total || 0;
    const wr = summary.win_rate !== undefined ? Number(summary.win_rate).toFixed(1) : '0.0';
    histWinRate.textContent = `${wr}%`;
    histWinLoss.textContent = `${summary.wins || 0} Thắng / ${summary.losses || 0} Thua`;

    const netPnl = summary.net_pnl !== undefined ? Number(summary.net_pnl) : 0.0;
    const netPrefix = netPnl >= 0 ? '+' : '';
    histNetPnl.textContent = `${netPrefix}$${netPnl.toFixed(2)} USDT`;
    histNetPnl.className = `text-lg font-bold mt-0.5 ${netPnl >= 0 ? 'text-profitGreen' : 'text-lossRed'}`;

    // Tính Profit Factor
    let grossWin = 0, grossLoss = 0;
    trades.forEach(t => {
      const p = parseFloat(t.pnl_usdt || 0);
      if (p > 0) grossWin += p;
      else if (p < 0) grossLoss += Math.abs(p);
    });
    const pf = grossLoss > 0 ? (grossWin / grossLoss).toFixed(2) : (grossWin > 0 ? '99.9' : '0.00');
    histProfitFactor.textContent = pf;

    // Vẽ biểu đồ Equity Curve SVG
    renderEquityCurve(chartData);

    // Vẽ bảng lịch sử giao dịch
    renderHistoryTable(trades);

  } catch (e) {
    console.debug('Lỗi nạp lịch sử:', e);
  }
}

function renderEquityCurve(chartData) {
  if (!equityChartContainer) return;
  if (!chartData || chartData.length === 0) {
    equityChartContainer.innerHTML = '<div class="text-gray-500">Chưa có giao dịch hoàn tất nào trong chu kỳ này để vẽ đường cong vốn.</div>';
    return;
  }

  const w = equityChartContainer.clientWidth || 750;
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

  equityChartContainer.innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" class="w-full h-full">
      <defs>
        <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="${strokeColor}" stop-opacity="0.25" />
          <stop offset="100%" stop-color="${strokeColor}" stop-opacity="0.0" />
        </linearGradient>
      </defs>
      <!-- Đường cơ sở mốc 0 -->
      <line x1="${pad}" y1="${zeroY}" x2="${w - pad}" y2="${zeroY}" stroke="#2B313A" stroke-dasharray="3,3" stroke-width="1" />
      <text x="${pad}" y="${Math.max(12, zeroY - 4)}" fill="#6B7280" font-size="9" font-family="monospace">$0</text>
      <!-- Vùng diện tích mờ -->
      <polygon points="${getX(0)},${h - pad} ${points} ${getX(chartData.length - 1)},${h - pad}" fill="url(#equityGrad)" />
      <!-- Đường cong vốn chính -->
      <polyline fill="none" stroke="${strokeColor}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="${points}" />
      <!-- Điểm cuối cùng -->
      <circle cx="${getX(chartData.length - 1)}" cy="${getY(finalVal)}" r="3.5" fill="${strokeColor}" />
      <text x="${w - pad - 60}" y="${Math.min(h - 8, getY(finalVal) - 6)}" fill="${strokeColor}" font-size="10" font-weight="bold" font-family="monospace">
        ${finalVal >= 0 ? '+' : ''}$${finalVal.toFixed(2)}
      </text>
    </svg>
  `;
}

function renderHistoryTable(trades) {
  if (!historyTableBody) return;
  if (!trades || trades.length === 0) {
    historyTableBody.innerHTML = `
      <tr>
        <td colspan="8" class="text-center py-10 text-gray-500 font-mono">
          Chưa có lệnh nào được ghi nhận vào trade_history.csv
        </td>
      </tr>
    `;
    return;
  }

  historyTableBody.innerHTML = trades.map((t, idx) => {
    const isLong = (t.side || 'BUY').toUpperCase().includes('BUY') || (t.side || '').toUpperCase().includes('LONG');
    const sideBadge = isLong 
      ? '<span class="text-profitGreen font-bold">LONG</span>' 
      : '<span class="text-lossRed font-bold">SHORT</span>';

    const pnl = parseFloat(t.pnl_usdt || 0);
    const pnlColor = pnl >= 0 ? 'text-profitGreen' : 'text-lossRed';
    const pnlPrefix = pnl >= 0 ? '+' : '';

    return `
      <tr class="hover:bg-darkCardHover/40 transition">
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

// Xuất file CSV
btnExportCsv.addEventListener('click', () => {
  const url = `${serverUrl.replace(/\/+$/, '')}/api/download_csv`;
  window.open(url, '_blank');
});

// =======================================================
// TAB 4: CẤU HÌNH THAM SỐ CHIẾN LƯỢC LIVE
// =======================================================
function setupStrategySliders() {
  stratLeverage.addEventListener('input', () => {
    stratLeverageVal.textContent = `${stratLeverage.value}x`;
  });
  stratRisk.addEventListener('input', () => {
    stratRiskVal.textContent = `${parseFloat(stratRisk.value).toFixed(1)}%`;
  });
  stratAdx.addEventListener('input', () => {
    stratAdxVal.textContent = stratAdx.value;
  });

  stratBtnBluechip.addEventListener('click', () => {
    activeTradingMode = 'BLUECHIP_ONLY';
    updateTradingModeButtons();
  });
  stratBtnMarket.addEventListener('click', () => {
    activeTradingMode = 'MARKET_ALL';
    updateTradingModeButtons();
  });

  btnSaveLiveStrategy.addEventListener('click', saveLiveStrategySettings);
}

async function loadStrategySettings() {
  try {
    const data = await fetchApi('/api/status');
    if (!data) return;

    activeTradingMode = data.trading_mode || 'MARKET_ALL';
    updateTradingModeButtons();

    if (data.leverage) {
      stratLeverage.value = data.leverage;
      stratLeverageVal.textContent = `${data.leverage}x`;
    }
    if (data.risk_percent) {
      stratRisk.value = data.risk_percent;
      stratRiskVal.textContent = `${parseFloat(data.risk_percent).toFixed(1)}%`;
    }
    if (data.protection_matrix && data.protection_matrix.adx_filter) {
      const adx = data.protection_matrix.adx_filter.min_adx || 20;
      stratAdx.value = adx;
      stratAdxVal.textContent = adx;
    }
    if (data.real_trading_hard_cap) {
      stratHardCap.value = data.real_trading_hard_cap;
    }
    if (data.use_trailing_stop !== undefined) {
      stratTrailingStop.checked = !!data.use_trailing_stop;
    }
    if (data.protection_matrix && data.protection_matrix.btc_regime) {
      stratBtcFilter.checked = data.protection_matrix.btc_regime.enabled !== false;
      const dir = data.protection_matrix.btc_regime.direction || 'AUTO';
      stratTradeDirection.value = dir;
    }
    if (data.protection_matrix && data.protection_matrix.dynamic_leverage) {
      stratDynamicLev.checked = data.protection_matrix.dynamic_leverage.enabled !== false;
    }
  } catch (e) {
    console.debug('Lỗi đọc cấu hình chiến lược:', e);
  }
}

async function saveLiveStrategySettings() {
  btnSaveLiveStrategy.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ĐANG LƯU...';
  stratStatusMsg.className = 'hidden';

  const payload = {
    trading_mode: activeTradingMode,
    trade_direction: stratTradeDirection.value,
    leverage: parseInt(stratLeverage.value, 10),
    risk_percent: parseFloat(stratRisk.value),
    adx_min: parseFloat(stratAdx.value),
    real_trading_hard_cap: parseFloat(stratHardCap.value),
    use_trailing_stop: stratTrailingStop.checked,
    enable_btc_regime_filter: stratBtcFilter.checked,
    enable_dynamic_leverage: stratDynamicLev.checked
  };

  try {
    const res = await fetchApi('/api/update_settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    stratStatusMsg.className = 'p-3 rounded-lg text-xs font-mono text-center bg-profitGreen/20 text-profitGreen border border-profitGreen/40';
    stratStatusMsg.innerHTML = '<i class="fa-solid fa-circle-check"></i> Đã lưu cấu hình thời gian thực thành công lên máy chủ VPS!';
    audioSynth.playTakeProfitSound();
    pollDashboardData();
  } catch (err) {
    stratStatusMsg.className = 'p-3 rounded-lg text-xs font-mono text-center bg-lossRed/20 text-lossRed border border-lossRed/40';
    stratStatusMsg.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Không thể lưu cấu hình: ${err.message}`;
  } finally {
    btnSaveLiveStrategy.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> <span>LƯU CẤU HÌNH LIVE</span>';
  }
}

// =======================================================
// TAB 5: NHẬT KÝ LOGS LIVE STREAM TERMINAL
// =======================================================
async function pollLiveLogs() {
  if (!logTerminalBox) return;
  try {
    const res = await fetchApi('/api/logs?lines=120');
    if (!res || !res.lines) return;

    if (res.source && logSourceBadge) {
      logSourceBadge.textContent = `Nguồn: ${res.source}`;
    }

    logTerminalBox.innerHTML = res.lines.map(line => {
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

    if (logAutoScroll && logAutoScroll.checked) {
      logTerminalBox.scrollTop = logTerminalBox.scrollHeight;
    }
  } catch (e) {
    console.debug('Lỗi nạp logs:', e);
  }
}

btnRefreshLogs.addEventListener('click', pollLiveLogs);
btnClearLogs.addEventListener('click', () => {
  if (logTerminalBox) logTerminalBox.innerHTML = '<div class="text-gray-600">Đã xóa khung nhìn logs tạm thời. Nhấn Làm Mới để tải lại.</div>';
});

// =======================================================
// TAB 6: TRỢ LÝ AI QUANT COPILOT
// =======================================================
function setupAiQuickButtons() {
  document.querySelectorAll('.ai-quick-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const prompt = btn.textContent.replace(/^[^\s]+\s+/, '');
      aiChatInput.value = prompt;
      aiChatForm.dispatchEvent(new Event('submit'));
    });
  });
}

aiChatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const query = aiChatInput.value.trim();
  if (!query) return;

  const userMsgDiv = document.createElement('div');
  userMsgDiv.className = 'bg-binanceGold/10 border border-binanceGold/30 text-white rounded-lg p-2.5 ml-8 text-xs font-mono';
  userMsgDiv.innerHTML = `<b>Bạn:</b> ${escapeHtml(query)}`;
  aiChatMessages.appendChild(userMsgDiv);
  aiChatInput.value = '';
  aiChatMessages.scrollTop = aiChatMessages.scrollHeight;

  const botThinking = document.createElement('div');
  botThinking.className = 'bg-darkBase/70 border border-darkBorder text-gray-400 rounded-lg p-2.5 mr-8 text-xs font-mono flex items-center space-x-2';
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
    botMsgDiv.className = 'bg-darkBase border border-purple-500/30 text-gray-200 rounded-lg p-2.5 mr-8 text-xs leading-relaxed font-mono';
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
  div.textContent = text || '';
  return div.innerHTML;
}

// =======================================================
// ÂM THANH & CÀI ĐẶT
// =======================================================
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

// Modal Cài Đặt Kết Nối
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

// Chuyển đổi nhanh chế độ Bluechip / Market Top 80 ở Header
btnModeBluechip.addEventListener('click', async () => {
  activeTradingMode = 'BLUECHIP_ONLY';
  await fetchApi('/api/update_settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ trading_mode: 'BLUECHIP_ONLY' })
  });
  updateTradingModeButtons();
  pollDashboardData();
});

btnModeMarket.addEventListener('click', async () => {
  activeTradingMode = 'MARKET_ALL';
  await fetchApi('/api/update_settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ trading_mode: 'MARKET_ALL' })
  });
  updateTradingModeButtons();
  pollDashboardData();
});

// Tạm dừng / Tiếp tục bot
async function togglePauseResume(forcePause = null) {
  await fetchApi('/api/toggle_pause', { method: 'POST' });
  pollDashboardData();
}
btnPauseResume.addEventListener('click', () => togglePauseResume());

// Bắt đầu khởi tạo
initApp();
