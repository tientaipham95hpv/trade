
        let equityChartInstance = null;
        let rawHistoryTrades = [];
        let currentFilterType = 'all';
        let isAudioEnabled = true;
        let audioCtx = null;
        let lastKnownPositionsCount = 0;
        let lastKnownRealizedPnl = 0;

        // Current Config State for Settings Modal
        let currentConfig = {
            trading_mode: 'MARKET_ALL',
            leverage: 5,
            risk_percent: 1.0,
            use_trailing_stop: true
        };

        // Web Audio Synthesizer
        function getAudioContext() {
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
            return audioCtx;
        }

        function playChime(type = 'fill') {
            if (!isAudioEnabled) return;
            try {
                const ctx = getAudioContext();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.connect(gain);
                gain.connect(ctx.destination);

                const now = ctx.currentTime;
                if (type === 'fill') {
                    // Gentle high-tech ting
                    osc.frequency.setValueAtTime(587.33, now); // D5
                    osc.frequency.exponentialRampToValueAtTime(880.0, now + 0.15); // A5
                    gain.gain.setValueAtTime(0.12, now);
                    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
                    osc.start(now);
                    osc.stop(now + 0.35);
                } else if (type === 'tp') {
                    // Triumphant double chime
                    osc.frequency.setValueAtTime(523.25, now); // C5
                    osc.frequency.setValueAtTime(659.25, now + 0.1); // E5
                    osc.frequency.setValueAtTime(1046.50, now + 0.2); // C6
                    gain.gain.setValueAtTime(0.15, now);
                    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.5);
                    osc.start(now);
                    osc.stop(now + 0.5);
                } else if (type === 'alert') {
                    // Warning low beep
                    osc.frequency.setValueAtTime(330.0, now);
                    gain.gain.setValueAtTime(0.15, now);
                    gain.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
                    osc.start(now);
                    osc.stop(now + 0.3);
                }
            } catch (e) {
                console.debug("Audio error:", e);
            }
        }

        function toggleAudio() {
            isAudioEnabled = !isAudioEnabled;
            const icon = document.getElementById('icon-audio');
            if (isAudioEnabled) {
                icon.className = 'fa-solid fa-volume-high text-sm text-profitGreen';
                showToast("Đã BẬT âm thanh thông báo web 🔔", "success");
                playChime('fill');
            } else {
                icon.className = 'fa-solid fa-volume-xmark text-sm text-gray-500';
                showToast("Đã TẮT âm thanh thông báo web", "info");
            }
        }

        // Play cute robotic chirp synthesizer
        function playRoboticChirp() {
            if (!isAudioEnabled) return;
            try {
                const ctx = getAudioCtx();
                const now = ctx.currentTime;
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();

                osc.type = 'triangle';
                osc.frequency.setValueAtTime(580, now);
                osc.frequency.exponentialRampToValueAtTime(1180, now + 0.08);
                osc.frequency.exponentialRampToValueAtTime(880, now + 0.16);

                gain.gain.setValueAtTime(0.08, now);
                gain.gain.linearRampToValueAtTime(0.12, now + 0.05);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start(now);
                osc.stop(now + 0.22);
            } catch (e) {}
        }

        // Mascot Interaction Trigger
        function triggerMascotClick() {
            playRoboticChirp();
            const box = document.getElementById('robot-avatar-box');
            if (box) {
                box.classList.remove('robot-jumping');
                void box.offsetWidth;
                box.classList.add('robot-jumping');
            }
            updateMascotCommentary(true);
        }

        // Update Mascot Speech, Mood, and Eyes from backend
        async function updateMascotCommentary(isManual = false) {
            try {
                const res = await fetch('/api/ai_mascot');
                const data = await res.json();

                const speechElem = document.getElementById('robot-speech');
                if (speechElem && data.speech) {
                    speechElem.style.opacity = '0';
                    setTimeout(() => {
                        speechElem.innerText = `"${data.speech}"`;
                        speechElem.style.opacity = '1';
                    }, 150);
                }

                // Update Mood Badge
                const moodText = document.getElementById('robot-mood-text');
                const moodChip = document.getElementById('robot-mood-chip');
                if (moodText && data.mood_title) {
                    moodText.innerText = data.mood_title;
                }

                // Toggle Digital Eye Expression
                const happyEyes = document.getElementById('robot-eyes-happy');
                const normalEyes = document.getElementById('robot-eyes-normal');
                const alertEyes = document.getElementById('robot-eyes-alert');

                if (data.mood === 'happy') {
                    if (happyEyes) happyEyes.classList.remove('hidden');
                    if (normalEyes) normalEyes.classList.add('hidden');
                    if (alertEyes) alertEyes.classList.add('hidden');
                    if (moodChip) moodChip.className = "px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-emerald-950/60 text-profitGreen border border-emerald-500/50 flex items-center gap-1";
                } else if (data.mood === 'alert') {
                    if (happyEyes) happyEyes.classList.add('hidden');
                    if (normalEyes) normalEyes.classList.add('hidden');
                    if (alertEyes) alertEyes.classList.remove('hidden');
                    if (moodChip) moodChip.className = "px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-red-950/60 text-lossRed border border-red-500/50 flex items-center gap-1";
                } else {
                    if (happyEyes) happyEyes.classList.add('hidden');
                    if (normalEyes) normalEyes.classList.remove('hidden');
                    if (alertEyes) alertEyes.classList.add('hidden');
                    if (moodChip) moodChip.className = "px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-cyan-950/60 text-cyberCyan border border-cyan-500/50 flex items-center gap-1";
                }

                // AI Neural Link tag
                const aiTag = document.getElementById('badge-ai-model-tag');
                if (aiTag) {
                    aiTag.innerText = data.ai_connected ? 'GEMINI 2.5 FLASH ACTIVE' : 'QUANT NEURAL LINK';
                    aiTag.className = data.ai_connected 
                        ? 'text-[10px] px-2 py-0.5 rounded font-mono bg-green-950/60 text-profitGreen border border-green-600/50 hidden sm:inline'
                        : 'text-[10px] px-2 py-0.5 rounded font-mono bg-cyan-900/30 text-cyan-300 border border-cyan-700/40 hidden sm:inline';
                }

                if (isManual) {
                    showToast("Cyber-Nova vừa cập nhật bình luận thị trường!", "info");
                }
            } catch (err) {
                console.error("Lỗi cập nhật mascot:", err);
            }
        }

        function triggerRobotDialogue() {
            triggerMascotClick();
        }

        // AI Copilot Modal & Chat Handlers
        function openAiModal() {
            document.getElementById('ai-chat-modal').classList.remove('hidden');
            document.getElementById('ai-chat-input').focus();
        }

        function closeAiModal() {
            document.getElementById('ai-chat-modal').classList.add('hidden');
        }

        function sendQuickPrompt(promptText) {
            document.getElementById('ai-chat-input').value = promptText;
            sendAiMessage();
        }

        async function sendAiMessage() {
            const input = document.getElementById('ai-chat-input');
            const userMsg = input.value.trim();
            if (!userMsg) return;

            const chatBody = document.getElementById('ai-chat-body');
            input.value = '';

            // User Message Bubble
            const userBubble = document.createElement('div');
            userBubble.className = "flex gap-2.5 items-start justify-end";
            userBubble.innerHTML = `
                <div class="p-3 rounded-2xl bg-cyan-950/60 border border-cyan-700/40 text-cyan-100 max-w-[85%] leading-relaxed shadow-sm">
                    ${userMsg}
                </div>
                <div class="w-7 h-7 rounded-lg bg-gray-800 border border-gray-600 flex items-center justify-center text-gray-300 text-xs flex-shrink-0 mt-0.5">
                    <i class="fa-solid fa-user"></i>
                </div>
            `;
            chatBody.appendChild(userBubble);
            chatBody.scrollTop = chatBody.scrollHeight;

            // Loading Robot Bubble
            const loadingBubble = document.createElement('div');
            loadingBubble.className = "flex gap-2.5 items-start";
            loadingBubble.innerHTML = `
                <div class="w-7 h-7 rounded-lg bg-cyan-950 border border-cyberCyan/50 flex items-center justify-center text-cyberCyan text-xs flex-shrink-0 mt-0.5">
                    <i class="fa-solid fa-robot fa-spin"></i>
                </div>
                <div class="p-3 rounded-2xl bg-darkCard border border-cyan-900/30 text-gray-400 max-w-[85%] leading-relaxed shadow-sm flex items-center gap-2">
                    <span class="inline-block w-2 h-2 rounded-full bg-cyberCyan animate-ping"></span>
                    <span>Cyber-Nova đang phân tích thị trường...</span>
                </div>
            `;
            chatBody.appendChild(loadingBubble);
            chatBody.scrollTop = chatBody.scrollHeight;

            try {
                const res = await fetch('/api/ai_chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: userMsg})
                });
                const data = await res.json();
                loadingBubble.remove();

                let formattedReply = (data.reply || "Em chưa nhận được phản hồi.")
                    .replace(/
/g, '<br>')
                    .replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');

                const botBubble = document.createElement('div');
                botBubble.className = "flex gap-2.5 items-start";
                botBubble.innerHTML = `
                    <div class="w-7 h-7 rounded-lg bg-cyan-950 border border-cyberCyan/50 flex items-center justify-center text-cyberCyan text-xs flex-shrink-0 mt-0.5">
                        <i class="fa-solid fa-robot"></i>
                    </div>
                    <div class="p-3.5 rounded-2xl bg-darkCard border border-cyan-900/40 text-gray-100 max-w-[85%] leading-relaxed shadow-md">
                        ${formattedReply}
                    </div>
                `;
                chatBody.appendChild(botBubble);
                chatBody.scrollTop = chatBody.scrollHeight;

                const badge = document.getElementById('ai-connected-badge');
                if (badge) {
                    badge.innerText = data.ai_connected ? 'GEMINI 2.5 FLASH' : 'LOCAL QUANT BRAIN';
                    badge.className = data.ai_connected 
                        ? 'px-2 py-0.5 rounded text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700/50'
                        : 'px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyberCyan border border-cyan-700/50';
                }
            } catch (err) {
                loadingBubble.remove();
                const errBubble = document.createElement('div');
                errBubble.className = "flex gap-2.5 items-start";
                errBubble.innerHTML = `
                    <div class="w-7 h-7 rounded-lg bg-red-950 border border-lossRed/50 flex items-center justify-center text-lossRed text-xs flex-shrink-0 mt-0.5">
                        <i class="fa-solid fa-triangle-exclamation"></i>
                    </div>
                    <div class="p-3 rounded-2xl bg-darkCard border border-red-900/30 text-lossRed max-w-[85%] leading-relaxed">
                        Lỗi kết nối AI: ${err}
                    </div>
                `;
                chatBody.appendChild(errBubble);
                chatBody.scrollTop = chatBody.scrollHeight;
            }
        }

        // Toast System
        function showToast(message, type = 'info') {
            const container = document.getElementById('toast-container');
            const toast = document.createElement('div');
            let bgClass = 'bg-gray-800 border-gray-700 text-white';
            let icon = '<i class="fa-solid fa-circle-info text-blue-400 mr-2"></i>';
            if (type === 'success') {
                bgClass = 'bg-darkCard border-profitGreen/50 text-white glow-green';
                icon = '<i class="fa-solid fa-circle-check text-profitGreen mr-2"></i>';
            } else if (type === 'error') {
                bgClass = 'bg-darkCard border-lossRed/50 text-white glow-red';
                icon = '<i class="fa-solid fa-circle-xmark text-lossRed mr-2"></i>';
            } else if (type === 'warning') {
                bgClass = 'bg-darkCard border-binanceGold/50 text-white glow-gold';
                icon = '<i class="fa-solid fa-triangle-exclamation text-binanceGold mr-2"></i>';
            }

            toast.className = `p-3 rounded-xl text-xs font-semibold border shadow-xl flex items-center transition-all duration-300 transform translate-y-2 opacity-0 pointer-events-auto ${bgClass}`;
            toast.innerHTML = `${icon}<span>${message}</span>`;
            container.appendChild(toast);

            setTimeout(() => toast.classList.remove('translate-y-2', 'opacity-0'), 10);
            setTimeout(() => {
                toast.classList.add('opacity-0', '-translate-y-2');
                setTimeout(() => toast.remove(), 300);
            }, 4000);
        }

        // Chart.js Setup
        function initChart(chartData) {
            const ctx = document.getElementById('equityChart').getContext('2d');
            if (equityChartInstance) equityChartInstance.destroy();

            const labels = chartData.map(d => `#${d.trade_num} (${d.symbol || ''})`);
            const dataPoints = chartData.map(d => d.cum_pnl);

            const gradient = ctx.createLinearGradient(0, 0, 0, 260);
            gradient.addColorStop(0, 'rgba(14, 203, 129, 0.35)');
            gradient.addColorStop(1, 'rgba(14, 203, 129, 0.0)');

            equityChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels.length > 0 ? labels : ['Chưa có lệnh'],
                    datasets: [{
                        label: 'PnL Tích Lũy ($)',
                        data: dataPoints.length > 0 ? dataPoints : [0],
                        borderColor: '#0ECB81',
                        borderWidth: 2.5,
                        fill: true,
                        backgroundColor: gradient,
                        tension: 0.3,
                        pointBackgroundColor: '#0ECB81',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 1.5,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            backgroundColor: '#10141e',
                            titleColor: '#fff',
                            bodyColor: '#0ECB81',
                            borderColor: '#1c2436',
                            borderWidth: 1,
                            padding: 10,
                            displayColors: false,
                            callbacks: {
                                label: function(context) {
                                    const sign = context.parsed.y >= 0 ? '+' : '';
                                    return ` Lợi nhuận tích lũy: ${sign}$${context.parsed.y.toFixed(2)} USDT`;
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: 'rgba(255, 255, 255, 0.04)' },
                            ticks: { color: '#6c757d', font: { family: 'JetBrains Mono', size: 10 } }
                        },
                        y: {
                            grid: { color: 'rgba(255, 255, 255, 0.04)' },
                            ticks: {
                                color: '#6c757d',
                                font: { family: 'JetBrains Mono', size: 10 },
                                callback: function(value) { return '$' + value; }
                            }
                        }
                    }
                }
            });
        }

        // Live Status Fetch
        async function fetchStatus(isManual = false) {
            const refreshIcon = document.getElementById('btn-refresh-icon');
            if (isManual && refreshIcon) refreshIcon.classList.add('fa-spin');

            try {
                const res = await fetch('/api/status');
                const data = await res.json();

                // Check for new position sound
                if (data.open_positions_count > lastKnownPositionsCount) {
                    playChime('fill');
                    showToast(`Đã khớp thêm vị thế mới! (${data.open_positions_count}/${data.max_positions})`, "success");
                }
                lastKnownPositionsCount = data.open_positions_count;

                // Sync current settings
                currentConfig.trading_mode = data.trading_mode || 'MARKET_ALL';
                currentConfig.leverage = data.leverage || 5;
                currentConfig.risk_percent = data.risk_percent || 1.0;
                currentConfig.use_trailing_stop = data.use_trailing_stop !== false;

                // Update Badges & Clock
                document.getElementById('clock').innerText = data.last_updated || '';
                document.getElementById('trading-mode-text').innerText = data.trading_mode === 'BLUECHIP_ONLY' ? 'CHỈ BTC/ETH' : 'ALL MARKET';
                
                const statusBadge = document.getElementById('badge-status');
                const btnPauseText = document.getElementById('btn-pause-text');
                const btnPauseIcon = document.getElementById('btn-pause-icon');

                // Robot Eye Color & Pulse
                const eyeL = document.getElementById('robot-eye-left');
                const eyeR = document.getElementById('robot-eye-right');

                if (data.is_paused) {
                    statusBadge.className = "px-2.5 py-1 rounded-full text-xs font-bold bg-yellow-900/30 text-binanceGold border border-yellow-700/50 flex items-center gap-1.5";
                    statusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-binanceGold"></span> TẠM DỪNG';
                    btnPauseText.innerText = "Tiếp Tục Quét";
                    btnPauseIcon.className = "fa-solid fa-play";
                    if (eyeL) eyeL.setAttribute('fill', '#F0B90B');
                    if (eyeR) eyeR.setAttribute('fill', '#F0B90B');
                } else {
                    statusBadge.className = "px-2.5 py-1 rounded-full text-xs font-bold bg-green-900/30 text-profitGreen border border-green-700/50 flex items-center gap-1.5";
                    statusBadge.innerHTML = '<span class="w-2 h-2 rounded-full bg-profitGreen animate-pulse"></span> ĐANG CHẠY';
                    btnPauseText.innerText = "Tạm Dừng Bot";
                    btnPauseIcon.className = "fa-solid fa-pause";
                    if (eyeL) eyeL.setAttribute('fill', data.total_unrealized_pnl >= 0 ? '#0ECB81' : '#F6465D');
                    if (eyeR) eyeR.setAttribute('fill', data.total_unrealized_pnl >= 0 ? '#0ECB81' : '#F6465D');
                }

                // Metrics
                document.getElementById('metric-balance').innerHTML = `$${data.balance.toLocaleString('en-US', {minimumFractionDigits: 2})} <span class="text-xs font-normal text-gray-400">USDT</span>`;
                const roiElem = document.getElementById('metric-roi');
                const roiSign = data.roi_percent >= 0 ? '+' : '';
                roiElem.innerText = `${roiSign}${data.roi_percent.toFixed(2)}%`;
                roiElem.className = `font-bold font-mono ${data.roi_percent >= 0 ? 'text-profitGreen' : 'text-lossRed'}`;
                document.getElementById('metric-leverage').innerText = `${data.leverage}x (${data.margin_type})`;

                // PnL
                const uPnlElem = document.getElementById('metric-unrealized-pnl');
                const uSign = data.total_unrealized_pnl >= 0 ? '+' : '';
                uPnlElem.innerText = `${uSign}$${data.total_unrealized_pnl.toFixed(2)}`;
                uPnlElem.className = `text-2xl lg:text-3xl font-extrabold font-mono ${data.total_unrealized_pnl >= 0 ? 'text-profitGreen' : 'text-lossRed'}`;
                document.getElementById('metric-open-count').innerText = `${data.open_positions_count} / ${data.max_positions} vị thế`;
                document.getElementById('badge-open-slots').innerText = `${data.open_positions_count} / ${data.max_positions} vị thế`;
                const slotPercent = (data.open_positions_count / data.max_positions) * 100.0;
                document.getElementById('metric-slot-bar').style.width = `${slotPercent}%`;

                // Watchdog
                if (data.health && Object.keys(data.health).length > 0) {
                    const h = data.health;
                    document.getElementById('metric-uptime').innerText = h.uptime || '--';
                    document.getElementById('metric-cpu').innerText = `${h.cpu_percent}%`;
                    document.getElementById('metric-ram').innerText = `${h.ram_percent}%`;
                    document.getElementById('metric-disk').innerText = `Trống ${h.disk_free_gb} GB`;
                    document.getElementById('ram-progress-bar').style.width = `${h.ram_percent}%`;
                    if (h.binance_latency_ms) {
                        document.getElementById('ping-latency').innerText = `${h.binance_latency_ms} ms`;
                    }
                }

                // Render Table
                renderPositionsTable(data.positions);

                if (isManual) showToast("Đã cập nhật dữ liệu mới nhất!", "success");

            } catch (err) {
                console.error("Lỗi cập nhật status:", err);
            } finally {
                if (refreshIcon) refreshIcon.classList.remove('fa-spin');
            }
        }

        function renderPositionsTable(positions) {
            const tbody = document.getElementById('positions-table-body');
            if (!positions || positions.length === 0) {
                tbody.innerHTML = '<tr><td colspan="11" class="px-6 py-10 text-center text-gray-400 font-sans"><i class="fa-solid fa-magnifying-glass text-binanceGold mr-2"></i> Không có vị thế nào đang mở. Bot đang liên tục quét cơ hội...</td></tr>';
                return;
            }

            tbody.innerHTML = positions.map(p => {
                const isLong = p.side === 'BUY';
                const sideBadge = isLong 
                    ? '<span class="px-2.5 py-1 rounded text-xs font-bold bg-green-950/60 text-profitGreen border border-green-700/50">LONG</span>' 
                    : '<span class="px-2.5 py-1 rounded text-xs font-bold bg-red-950/60 text-lossRed border border-red-700/50">SHORT</span>';
                
                const pnlClass = p.pnl_usdt >= 0 ? 'text-profitGreen font-bold' : 'text-lossRed font-bold';
                const sign = p.pnl_usdt >= 0 ? '+' : '';

                let statusBadge = '<span class="px-2 py-0.5 rounded text-[11px] bg-darkBase text-gray-400 border border-darkBorder">Đang chạy</span>';
                if (p.trailing_active) {
                    statusBadge = '<span class="px-2 py-0.5 rounded text-[11px] bg-purple-900/40 text-purple-400 border border-purple-700/40 animate-pulse">🚀 Trailing Stop</span>';
                } else if (p.partial_tp) {
                    statusBadge = '<span class="px-2 py-0.5 rounded text-[11px] bg-green-900/40 text-profitGreen border border-green-700/40">🎯 Chốt 50%</span>';
                } else if (p.breakeven) {
                    statusBadge = '<span class="px-2 py-0.5 rounded text-[11px] bg-yellow-900/40 text-binanceGold border border-yellow-700/40">🛡️ SL Hòa Vốn</span>';
                }

                const sliderVal = p.slider_pct || 50;
                const sliderColor = p.pnl_usdt >= 0 ? 'bg-profitGreen' : 'bg-lossRed';

                return `
                    <tr class="hover:bg-darkBase/40 transition">
                        <td class="px-5 py-4 font-bold text-white font-sans">${p.symbol}</td>
                        <td class="px-5 py-4 font-sans">${sideBadge}</td>
                        <td class="px-5 py-4">$${p.entry_price.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                        <td class="px-5 py-4 font-bold text-white">$${p.current_price.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                        <td class="px-5 py-4 text-lossRed font-semibold">$${p.stop_loss.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                        <td class="px-5 py-4 text-profitGreen font-semibold">$${p.take_profit.toLocaleString('en-US', {minimumFractionDigits: 2})}</td>
                        <td class="px-5 py-4 w-36">
                            <div class="w-full bg-darkBase h-2 rounded-full overflow-hidden border border-darkBorder relative">
                                <div class="${sliderColor} h-full transition-all duration-300" style="width: ${sliderVal}%"></div>
                            </div>
                            <div class="flex justify-between text-[9px] text-gray-500 mt-1">
                                <span>SL</span>
                                <span class="text-gray-300 font-semibold">${sliderVal}%</span>
                                <span>TP</span>
                            </div>
                        </td>
                        <td class="px-5 py-4">$${p.margin.toFixed(2)}</td>
                        <td class="px-5 py-4 ${pnlClass}">${sign}$${p.pnl_usdt.toFixed(2)} (${sign}${p.pnl_percent.toFixed(2)}%)</td>
                        <td class="px-5 py-4 text-center font-sans">${statusBadge}</td>
                        <td class="px-5 py-4 text-center font-sans">
                            <button onclick="closeSinglePosition('${p.symbol}')" class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-gray-800 hover:bg-lossRed text-gray-300 hover:text-white transition">
                                Đóng
                            </button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        // Live Scanner Radar Fetch
        async function fetchRadar() {
            try {
                const res = await fetch('/api/scanner_radar');
                const data = await res.json();

                const tbody = document.getElementById('radar-table-body');
                document.getElementById('radar-updated-at').innerText = data.updated_at || '';
                document.getElementById('radar-count-badge').innerText = `${data.scanned_count} CẶP COIN`;

                if (!data.radar || data.radar.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" class="px-6 py-6 text-center text-gray-400 font-sans">Đang chờ chu kỳ quét kế tiếp...</td></tr>';
                    return;
                }

                tbody.innerHTML = data.radar.map(r => {
                    const trendColor = r.trend.includes('Up') ? 'text-profitGreen' : (r.trend.includes('Down') ? 'text-lossRed' : 'text-gray-400');
                    const adxColor = r.adx >= 20 ? 'text-profitGreen font-bold' : 'text-lossRed';
                    const rsiColor = r.rsi <= 35 ? 'text-profitGreen font-bold' : (r.rsi >= 65 ? 'text-lossRed font-bold' : 'text-gray-300');

                    let statusBadge = '<span class="text-gray-400">Đang chờ Pullback</span>';
                    if (r.status.includes('Tín hiệu')) {
                        statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-green-950 text-profitGreen border border-green-700 animate-pulse">' + r.status + '</span>';
                    } else if (r.status.includes('ADX yếu')) {
                        statusBadge = '<span class="text-yellow-600 italic">' + r.status + '</span>';
                    }

                    return `
                        <tr class="hover:bg-darkBase/40 transition">
                            <td class="px-5 py-2.5 font-bold text-white font-sans">${r.symbol}</td>
                            <td class="px-5 py-2.5">$${r.price.toFixed(4)}</td>
                            <td class="px-5 py-2.5 font-semibold ${trendColor}">${r.trend}</td>
                            <td class="px-5 py-2.5 ${rsiColor}">${r.rsi}</td>
                            <td class="px-5 py-2.5 ${adxColor}">${r.adx}</td>
                            <td class="px-5 py-2.5 text-gray-400">${r.funding_rate}%</td>
                            <td class="px-5 py-2.5 font-sans">${statusBadge}</td>
                        </tr>
                    `;
                }).join('');
            } catch (err) {
                console.error("Lỗi nạp radar:", err);
            }
        }

        // Fetch History
        async function fetchHistory() {
            try {
                const res = await fetch('/api/history');
                const data = await res.json();

                if (data.summary) {
                    const s = data.summary;
                    document.getElementById('metric-total-closed').innerText = s.total;
                    document.getElementById('metric-wins').innerText = s.wins;
                    document.getElementById('metric-losses').innerText = s.losses;
                    document.getElementById('metric-winrate').innerText = `${s.win_rate}%`;

                    const rPnl = document.getElementById('metric-realized-pnl');
                    const sign = s.net_pnl >= 0 ? '+' : '';
                    rPnl.innerText = `${sign}$${s.net_pnl.toFixed(2)}`;
                    rPnl.className = `text-2xl lg:text-3xl font-extrabold font-mono ${s.net_pnl >= 0 ? 'text-profitGreen' : 'text-lossRed'}`;

                    // Check if new profit trade closed -> Play celebration sound
                    if (s.net_pnl > lastKnownRealizedPnl && lastKnownRealizedPnl !== 0) {
                        playChime('tp');
                        showToast(`Chúc mừng! Vừa chốt lời thành công! Lãi ròng hiện tại: $${s.net_pnl.toFixed(2)}`, "success");
                    }
                    lastKnownRealizedPnl = s.net_pnl;
                }

                if (data.chart_data && data.chart_data.length > 0) {
                    initChart(data.chart_data);
                }

                rawHistoryTrades = data.trades || [];
                applyHistoryFilter();

            } catch (err) {
                console.error("Lỗi nạp history:", err);
            }
        }

        function setFilterType(type) {
            currentFilterType = type;
            ['all', 'win', 'loss'].forEach(t => {
                const btn = document.getElementById(`btn-filter-${t}`);
                if (t === type) {
                    btn.className = "px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-binanceGold text-black";
                } else {
                    btn.className = "px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-darkBase text-gray-300 border border-darkBorder hover:text-white";
                }
            });
            applyHistoryFilter();
        }

        function applyHistoryFilter() {
            const searchKeyword = document.getElementById('history-search').value.toUpperCase().trim();
            const tbody = document.getElementById('history-table-body');

            let filtered = rawHistoryTrades.filter(t => {
                const symMatch = !searchKeyword || (t.symbol && t.symbol.toUpperCase().includes(searchKeyword));
                const pnl = parseFloat(t.pnl_usdt || 0);
                if (currentFilterType === 'win') return symMatch && pnl > 0;
                if (currentFilterType === 'loss') return symMatch && pnl < 0;
                return symMatch;
            });

            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="9" class="px-6 py-6 text-center text-gray-400 font-sans">Không tìm thấy giao dịch nào phù hợp bộ lọc.</td></tr>';
                return;
            }

            tbody.innerHTML = filtered.map(t => {
                const isWin = parseFloat(t.pnl_usdt || 0) >= 0;
                const pnlColor = isWin ? 'text-profitGreen' : 'text-lossRed';
                const sideColor = t.side === 'BUY' ? 'text-profitGreen' : 'text-lossRed';

                return `
                    <tr class="hover:bg-darkBase/30 transition">
                        <td class="px-5 py-3 text-gray-400">${t.timestamp}</td>
                        <td class="px-5 py-3 font-bold text-white font-sans">${t.symbol}</td>
                        <td class="px-5 py-3 font-semibold ${sideColor} font-sans">${t.side}</td>
                        <td class="px-5 py-3">$${parseFloat(t.entry_price).toFixed(2)}</td>
                        <td class="px-5 py-3 font-semibold text-white">$${parseFloat(t.exit_price).toFixed(2)}</td>
                        <td class="px-5 py-3">${t.qty}</td>
                        <td class="px-5 py-3 font-bold ${pnlColor}">${t.pnl_usdt}</td>
                        <td class="px-5 py-3 font-bold ${pnlColor}">${t.pnl_percent}</td>
                        <td class="px-5 py-3 text-gray-300 italic font-sans">${t.exit_reason}</td>
                    </tr>
                `;
            }).join('');
        }

        // Settings Modal Handlers
        function openSettingsModal() {
            document.getElementById('settings-modal').classList.remove('hidden');
            selectTradingMode(currentConfig.trading_mode);
            selectLeverage(currentConfig.leverage);
            selectRisk(currentConfig.risk_percent);
            document.getElementById('chk-trailing-stop').checked = currentConfig.use_trailing_stop;
            if (currentConfig.ai_api_key) {
                document.getElementById('input-ai-key').value = currentConfig.ai_api_key;
            }
        }

        function closeSettingsModal() {
            document.getElementById('settings-modal').classList.add('hidden');
        }

        function selectTradingMode(mode) {
            currentConfig.trading_mode = mode;
            const bB = document.getElementById('opt-mode-bluechip');
            const bA = document.getElementById('opt-mode-all');
            if (mode === 'BLUECHIP_ONLY') {
                bB.className = "p-3 rounded-xl border text-left flex flex-col justify-between transition border-cyan-500 bg-cyan-950/30 text-cyberCyan";
                bA.className = "p-3 rounded-xl border text-left flex flex-col justify-between transition border-darkBorder bg-darkBase text-gray-300";
            } else {
                bA.className = "p-3 rounded-xl border text-left flex flex-col justify-between transition border-binanceGold bg-yellow-950/20 text-binanceGold";
                bB.className = "p-3 rounded-xl border text-left flex flex-col justify-between transition border-darkBorder bg-darkBase text-gray-300";
            }
        }

        function selectLeverage(lev) {
            currentConfig.leverage = lev;
            [3, 5, 10, 15].forEach(l => {
                const btn = document.getElementById(`opt-lev-${l}`);
                if (l === lev) {
                    btn.className = "py-2 rounded-lg font-mono font-bold border border-binanceGold bg-yellow-950/30 text-binanceGold";
                } else {
                    btn.className = "py-2 rounded-lg font-mono font-bold border border-darkBorder bg-darkBase text-gray-300";
                }
            });
        }

        function selectRisk(risk) {
            currentConfig.risk_percent = risk;
            [0.5, 1.0, 1.5, 2.0].forEach(r => {
                const id = 'opt-risk-' + (r === 0.5 ? '05' : (r === 1.0 ? '10' : (r === 1.5 ? '15' : '20')));
                const btn = document.getElementById(id);
                if (r === risk) {
                    btn.className = "py-2 rounded-lg font-mono font-bold border border-profitGreen bg-green-950/30 text-profitGreen";
                } else {
                    btn.className = "py-2 rounded-lg font-mono font-bold border border-darkBorder bg-darkBase text-gray-300";
                }
            });
        }

        async function saveLiveSettings() {
            currentConfig.use_trailing_stop = document.getElementById('chk-trailing-stop').checked;
            const aiKeyInput = document.getElementById('input-ai-key');
            if (aiKeyInput) {
                currentConfig.ai_api_key = aiKeyInput.value.trim();
            }
            try {
                const res = await fetch('/api/update_settings', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(currentConfig)
                });
                const data = await res.json();
                closeSettingsModal();
                if (data.success) {
                    playChime('tp');
                    showToast(data.message, "success");
                    fetchStatus();
                    fetchRadar();
                    updateMascotCommentary();
                } else {
                    showToast(data.message, "error");
                }
            } catch (err) {
                showToast("Lỗi cập nhật cấu hình: " + err, "error");
            }
        }

        // Pause & Panic Close
        async function togglePause() {
            try {
                const res = await fetch('/api/toggle_pause', {method: 'POST'});
                const data = await res.json();
                playChime('alert');
                showToast(data.message, "info");
                fetchStatus();
            } catch (err) {
                showToast("Lỗi khi pause bot: " + err, "error");
            }
        }

        function confirmPanicClose() {
            document.getElementById('confirm-modal').classList.remove('hidden');
            document.getElementById('modal-confirm-btn').onclick = executePanicClose;
        }

        function closeConfirmModal() {
            document.getElementById('confirm-modal').classList.add('hidden');
        }

        async function executePanicClose() {
            closeConfirmModal();
            try {
                playChime('alert');
                showToast("Đang gửi lệnh đóng toàn bộ vị thế...", "warning");
                const res = await fetch('/api/panic_close', {method: 'POST'});
                const data = await res.json();
                showToast(data.message, "success");
                fetchStatus();
                fetchHistory();
            } catch (err) {
                showToast("Lỗi khi đóng khẩn cấp: " + err, "error");
            }
        }

        async function closeSinglePosition(symbol) {
            if (!confirm(`Bạn có chắc muốn đóng vị thế ${symbol} ngay lập tức?`)) return;
            try {
                const res = await fetch('/api/close_single', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({symbol: symbol})
                });
                const data = await res.json();
                if (data.success) {
                    showToast(data.message, "success");
                } else {
                    showToast(data.message, "error");
                }
                fetchStatus();
                fetchHistory();
            } catch (err) {
                showToast("Lỗi đóng vị thế: " + err, "error");
            }
        }

        // Auto Refresh
        fetchStatus();
        fetchHistory();
        fetchRadar();
        updateMascotCommentary();
        setInterval(fetchStatus, 3000);
        setInterval(fetchRadar, 10000);
        setInterval(fetchHistory, 15000);
        setInterval(updateMascotCommentary, 12000);
    