// ============================================
//  AI SIGNAL PRO — CLIENT APPLICATION
// ============================================

let ws = null;
let isAnalyzing = false;
let signalHistory = [];
let simulatorInterval = null;

// ---- Market Simulator (fallback when browser extraction isn't ready) ----
class MarketSimulator {
  constructor() {
    this.prices = {
      'EUR/USD': 1.0852, 'GBP/USD': 1.2648, 'USD/JPY': 149.52,
      'USD/CHF': 0.8782, 'AUD/USD': 0.6538, 'NZD/USD': 0.6118,
      'USD/CAD': 1.3582, 'EUR/GBP': 0.8572, 'EUR/JPY': 162.18,
      'GBP/JPY': 189.08, 'AUD/JPY': 97.82, 'EUR/AUD': 1.6588,
      'CHF/JPY': 170.30, 'BTC/USD': 67500, 'ETH/USD': 3450,
      'LTC/USD': 72.50,
      'EUR/USD (OTC)': 1.0855, 'GBP/USD (OTC)': 1.2645,
      'USD/JPY (OTC)': 149.55, 'AUD/CAD (OTC)': 0.8920,
      'EUR/GBP (OTC)': 0.8565, 'NZD/USD (OTC)': 0.6115
    };
    this.trends = {};
    this.candles = {};
    Object.keys(this.prices).forEach(p => {
      this.trends[p] = (Math.random() - 0.5) * 0.0015;
    });
  }

  getVolatility(pair) {
    const p = this.prices[pair] || 1;
    if (p > 10000) return p * 0.0004;
    if (p > 100) return p * 0.00025;
    return p * 0.00035;
  }

  generateCandles(pair, tfSec, count = 120) {
    const candles = [];
    let price = this.prices[pair] || 1;
    const vol = this.getVolatility(pair);
    let trend = this.trends[pair] || 0;
    const phase = Math.random() * Math.PI * 2;
    const period = 15 + Math.random() * 25;

    for (let i = 0; i < count; i++) {
      if (Math.random() < 0.04) trend = (Math.random() - 0.5) * 0.002;
      const cycle = Math.sin(phase + (i / period) * Math.PI * 2) * vol * 0.8;
      const noise = (Math.random() - 0.5) * vol * 2;
      const change = trend * price + noise + cycle * 0.02;
      const open = price;
      price += change;
      const close = price;
      const wU = Math.random() * vol * 1.2;
      const wD = Math.random() * vol * 1.2;
      candles.push({
        time: Date.now() - (count - i) * tfSec * 1000,
        open: +open.toFixed(5), high: +(Math.max(open, close) + wU).toFixed(5),
        low: +(Math.min(open, close) - wD).toFixed(5), close: +close.toFixed(5),
        volume: Math.floor(50 + Math.random() * 500)
      });
    }
    this.prices[pair] = price;
    this.trends[pair] = trend;
    this.candles[pair] = candles;
    return candles;
  }

  tick(pair, tfSec) {
    if (!this.candles[pair]) return this.generateCandles(pair, tfSec);
    const candles = this.candles[pair];
    const vol = this.getVolatility(pair);
    const price = this.prices[pair];
    const change = (Math.random() - 0.5) * vol * 2 + (this.trends[pair] || 0) * price;
    const np = price + change;
    this.prices[pair] = np;
    const last = candles[candles.length - 1];
    if (Date.now() - last.time >= tfSec * 1000) {
      candles.push({
        time: Date.now(), open: +np.toFixed(5), high: +np.toFixed(5),
        low: +np.toFixed(5), close: +np.toFixed(5), volume: 1
      });
      if (candles.length > 250) candles.shift();
    } else {
      last.close = +np.toFixed(5);
      last.high = +Math.max(last.high, np).toFixed(5);
      last.low = +Math.min(last.low, np).toFixed(5);
      last.volume++;
    }
    return candles;
  }
}

const sim = new MarketSimulator();

// ---- WebSocket Connection ----
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}`);

  ws.onopen = () => {
    console.log('Dashboard WebSocket connected');
    updateFooterStatus('Dashboard connected');
  };

  ws.onmessage = (evt) => {
    try {
      const { type, data } = JSON.parse(evt.data);
      switch (type) {
        case 'status': handleStatus(data); break;
        case 'signal': handleSignal(data); break;
        case 'account': handleAccount(data); break;
        case 'candles_update': handleCandlesUpdate(data); break;
        case 'error': console.error('Server error:', data.message); break;
      }
    } catch (e) {}
  };

  ws.onclose = () => {
    console.log('WS disconnected, reconnecting...');
    setTimeout(connectWS, 3000);
  };

  ws.onerror = () => {};
}

function sendWS(data) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(data));
  }
}

// ---- Handlers ----
function handleStatus(data) {
  const dot = document.getElementById('status-dot');
  const text = document.getElementById('status-text');

  if (data.status === 'launching' || data.status === 'navigating' || data.status === 'connecting') {
    dot.className = 'status-dot connecting';
    text.textContent = data.message || 'Connecting...';
  } else if (data.status === 'connected' || data.status === 'logged_in' || data.status === 'analyzing') {
    dot.className = 'status-dot online';
    text.textContent = data.message || 'Connected';
    if (data.status === 'logged_in') {
      document.getElementById('btn-connect').textContent = '✓ CONNECTED';
      document.getElementById('btn-connect').disabled = true;
    }
  } else if (data.status === 'error') {
    dot.className = 'status-dot offline';
    text.textContent = data.message || 'Error';
  } else if (data.status === 'stopped') {
    text.textContent = 'Analysis stopped';
  }

  updateFooterStatus(data.message || data.status);
}

function handleAccount(data) {
  const section = document.getElementById('account-section');
  section.style.display = 'block';
  document.getElementById('account-balance').textContent = data.balance || '$0.00';
  const typeEl = document.getElementById('account-type');
  typeEl.textContent = data.accountType || 'DEMO';
  typeEl.className = 'account-type' + (data.accountType === 'REAL' ? ' real' : '');
}

function handleCandlesUpdate(data) {
  document.getElementById('candle-count').textContent = data.count || 0;
  const ds = document.getElementById('data-source');
  if (data.source === 'live') {
    ds.className = 'data-source live';
    ds.innerHTML = '<span class="material-icons-round">cloud_done</span><span>Live Feed from Pocket Option</span>';
  } else if (data.source === 'tick-built') {
    ds.className = 'data-source live';
    ds.innerHTML = '<span class="material-icons-round">stream</span><span>Building from live ticks</span>';
  }
  if (data.currentPrice) {
    document.getElementById('signal-price').textContent = parseFloat(data.currentPrice).toFixed(5);
  }
  if (data.pair) {
    document.getElementById('signal-pair').textContent = data.pair;
  }
  updateFooterSource(data.source || 'unknown');
}

function handleSignal(data) {
  if (!data || !data.signal) return;

  // -- Signal Header --
  const arrowWrap = document.getElementById('signal-arrow-wrap');
  const arrowIcon = document.getElementById('signal-arrow-icon');
  const label = document.getElementById('signal-label');
  const confText = document.getElementById('signal-confidence-text');
  const confFill = document.getElementById('confidence-fill');

  arrowWrap.className = 'signal-arrow-wrap';
  label.className = 'signal-label';

  if (data.signal === 'BUY') {
    arrowWrap.classList.add('buy');
    arrowIcon.textContent = 'north';
    label.textContent = '▲ BUY';
    label.classList.add('buy');
    playSound('buy');
  } else if (data.signal === 'SELL') {
    arrowWrap.classList.add('sell');
    arrowIcon.textContent = 'south';
    label.textContent = '▼ SELL';
    label.classList.add('sell');
    playSound('sell');
  } else {
    arrowIcon.textContent = 'schedule';
    label.textContent = 'WAIT';
  }

  confText.textContent = `Confidence: ${data.confidence}%`;
  confFill.style.width = data.confidence + '%';
  document.getElementById('buy-score-num').textContent = data.buyScore || '0.00';
  document.getElementById('sell-score-num').textContent = data.sellScore || '0.00';

  if (data.currentPrice) {
    document.getElementById('signal-price').textContent = parseFloat(data.currentPrice).toFixed(5);
  } else if (data.indicators && data.indicators.price) {
    document.getElementById('signal-price').textContent = data.indicators.price;
  }

  if (data.pair) document.getElementById('signal-pair').textContent = data.pair;
  document.getElementById('signal-time').textContent = new Date().toLocaleTimeString();

  // -- Indicators --
  if (data.indicators) updateIndicators(data.indicators);

  // -- Reasons --
  if (data.reasons) updateReasons(data.reasons);

  // -- History --
  addHistory(data);

  // Footer time
  document.getElementById('footer-time').textContent = new Date().toLocaleTimeString();
}

function updateIndicators(ind) {
  setInd('ind-rsi', 'RSI (14)', ind.rsi, classifyRSI(ind.rsi));
  setInd('ind-macd', 'MACD', ind.macdHist, classifyMACD(ind.macdHist));

  const stVal = `K:${ind.stochK || '--'} D:${ind.stochD || '--'}`;
  setInd('ind-stoch', 'Stochastic', stVal, classifyStoch(ind.stochK));

  setInd('ind-bb', 'Bollinger', `Pos: ${ind.bbPosition || '--'}`, classifyBB(ind.bbPosition));
  setInd('ind-adx', 'ADX', `${ind.adx || '--'} +DI:${ind.plusDI || '--'} -DI:${ind.minusDI || '--'}`, classifyADX(ind.adx, ind.plusDI, ind.minusDI));

  const emaDir = parseFloat(ind.ema9) > parseFloat(ind.ema21) ? '▲ Bullish' : '▼ Bearish';
  const emaCls = parseFloat(ind.ema9) > parseFloat(ind.ema21) ? 'bullish' : 'bearish';
  setInd('ind-ema', 'EMA 9/21', emaDir, emaCls);

  setInd('ind-cci', 'CCI (20)', ind.cci, classifyCCI(ind.cci));
  setInd('ind-williams', 'Williams %R', ind.williams, classifyWilliams(ind.williams));
  setInd('ind-mfi', 'MFI (14)', ind.mfi, classifyMFI(ind.mfi));

  const vwapDir = parseFloat(ind.price) > parseFloat(ind.vwap) ? 'Above' : 'Below';
  const vwapCls = vwapDir === 'Above' ? 'bullish' : 'bearish';
  setInd('ind-vwap', 'VWAP', `${vwapDir} (${ind.vwap || '--'})`, vwapCls);

  setInd('ind-ichimoku', 'Ichimoku', `T:${ind.ichimokuTenkan || '--'}`, classifyIchimoku(ind));
  setInd('ind-atr', 'ATR (14)', ind.atr, 'neutral');

  // Patterns
  const pList = document.getElementById('patterns-list');
  if (ind.patterns && ind.patterns.length > 0) {
    pList.innerHTML = ind.patterns.map(p => {
      const cls = p.toLowerCase().includes('bull') || p.toLowerCase().includes('hammer') ||
                  p.toLowerCase().includes('morning') || p.toLowerCase().includes('piercing') ||
                  p.toLowerCase().includes('soldiers') || p.toLowerCase().includes('inverted') ||
                  p.toLowerCase().includes('dragonfly')
                  ? 'buy' : p.toLowerCase().includes('bear') || p.toLowerCase().includes('shooting') ||
                    p.toLowerCase().includes('evening') || p.toLowerCase().includes('dark') ||
                    p.toLowerCase().includes('crows') || p.toLowerCase().includes('hanging') ||
                    p.toLowerCase().includes('gravestone')
                    ? 'sell' : '';
      return `<span class="pattern-tag ${cls}">🕯 ${p}</span>`;
    }).join('');
  } else {
    pList.innerHTML = '<div class="empty-state">No patterns detected</div>';
  }

  // Support/Resistance
  const sLevels = document.getElementById('support-levels');
  const rLevels = document.getElementById('resistance-levels');
  sLevels.innerHTML = (ind.supportLevels && ind.supportLevels.length > 0)
    ? ind.supportLevels.map(l => `<span class="level-tag support">${l}</span>`).join('')
    : '<div class="empty-state">--</div>';
  rLevels.innerHTML = (ind.resistanceLevels && ind.resistanceLevels.length > 0)
    ? ind.resistanceLevels.map(l => `<span class="level-tag resistance">${l}</span>`).join('')
    : '<div class="empty-state">--</div>';

  // Trend
  const trendEl = document.getElementById('trend-display');
  const trend = ind.trend || 'NEUTRAL';
  trendEl.className = 'trend-display';
  if (trend === 'BULLISH') {
    trendEl.classList.add('bullish');
    trendEl.innerHTML = '<span class="material-icons-round">trending_up</span> BULLISH';
  } else if (trend === 'BEARISH') {
    trendEl.classList.add('bearish');
    trendEl.innerHTML = '<span class="material-icons-round">trending_down</span> BEARISH';
  } else {
    trendEl.innerHTML = '<span class="material-icons-round">trending_flat</span> NEUTRAL';
  }
}

function setInd(id, name, value, cls) {
  const card = document.getElementById(id);
  if (!card) return;
  card.querySelector('.ind-val').textContent = value || '--';
  const badge = card.querySelector('.ind-badge');
  badge.className = `ind-badge ${cls}`;
  badge.textContent = cls === 'bullish' ? 'BUY' : cls === 'bearish' ? 'SELL' : 'HOLD';
  card.className = `ind-card ${cls === 'bullish' ? 'bullish' : cls === 'bearish' ? 'bearish' : ''}`;
}

function classifyRSI(v) { const n = parseFloat(v); if (isNaN(n)) return 'neutral'; return n < 35 ? 'bullish' : n > 65 ? 'bearish' : 'neutral'; }
function classifyMACD(v) { const n = parseFloat(v); if (isNaN(n)) return 'neutral'; return n > 0 ? 'bullish' : n < 0 ? 'bearish' : 'neutral'; }
function classifyStoch(v) { const n = parseFloat(v); if (isNaN(n)) return 'neutral'; return n < 25 ? 'bullish' : n > 75 ? 'bearish' : 'neutral'; }
function classifyBB(v) { const n = parseInt(v); if (isNaN(n)) return 'neutral'; return n < 25 ? 'bullish' : n > 75 ? 'bearish' : 'neutral'; }
function classifyCCI(v) { const n = parseFloat(v); if (isNaN(n)) return 'neutral'; return n < -100 ? 'bullish' : n > 100 ? 'bearish' : 'neutral'; }
function classifyWilliams(v) { const n = parseFloat(v); if (isNaN(n)) return 'neutral'; return n < -80 ? 'bullish' : n > -20 ? 'bearish' : 'neutral'; }
function classifyMFI(v) { const n = parseFloat(v); if (isNaN(n)) return 'neutral'; return n < 20 ? 'bullish' : n > 80 ? 'bearish' : 'neutral'; }
function classifyADX(adx, pdi, mdi) { const a = parseFloat(adx); if (isNaN(a) || a < 20) return 'neutral'; return parseFloat(pdi) > parseFloat(mdi) ? 'bullish' : 'bearish'; }
function classifyIchimoku(ind) {
  const p = parseFloat(ind.price);
  const a = parseFloat(ind.ichimokuTenkan);
  const k = parseFloat(ind.ichimokuKijun);
  if (isNaN(p) || isNaN(a) || isNaN(k)) return 'neutral';
  return a > k ? 'bullish' : a < k ? 'bearish' : 'neutral';
}

function updateReasons(reasons) {
  const list = document.getElementById('reasons-list');
  list.innerHTML = reasons.map(r => {
    const type = r.type || (
      r.text && (r.text.toLowerCase().includes('bull') || r.text.toLowerCase().includes('buy') ||
      r.text.toLowerCase().includes('oversold') || r.text.toLowerCase().includes('support') ||
      r.text.toLowerCase().includes('above') || r.text.toLowerCase().includes('uptrend') ||
      r.text.toLowerCase().includes('positive') || r.text.toLowerCase().includes('rising') ||
      r.text.toLowerCase().includes('hammer') || r.text.toLowerCase().includes('morning'))
      ? 'buy' : 'sell'
    );
    const text = r.text || r;
    return `<div class="reason-item ${type}">
      <span class="reason-dot"></span>
      <span>${text}</span>
    </div>`;
  }).join('');
}

function addHistory(data) {
  const pair = document.getElementById('currency-pair').value;
  const duration = document.getElementById('duration');
  const durText = duration.options[duration.selectedIndex].text;
  const entry = {
    time: new Date().toLocaleTimeString(),
    pair: data.pair || pair,
    signal: data.signal,
    confidence: data.confidence,
    buyScore: data.buyScore,
    sellScore: data.sellScore
  };
  signalHistory.unshift(entry);
  if (signalHistory.length > 100) signalHistory.pop();

  const tbody = document.getElementById('history-body');
  const row = document.createElement('tr');
  row.className = data.signal === 'BUY' ? 'buy-row' : data.signal === 'SELL' ? 'sell-row' : 'wait-row';
  row.innerHTML = `
    <td>${entry.time}</td>
    <td>${entry.pair}</td>
    <td>${data.signal === 'BUY' ? '▲ BUY' : data.signal === 'SELL' ? '▼ SELL' : '— WAIT'}</td>
    <td>${entry.confidence}%</td>
    <td style="color:var(--green)">${entry.buyScore}</td>
  `;

  if (tbody.firstChild) tbody.insertBefore(row, tbody.firstChild);
  else tbody.appendChild(row);

  while (tbody.children.length > 100) tbody.removeChild(tbody.lastChild);
  document.getElementById('history-count').textContent = signalHistory.length;
}

// ---- Sound ----
function playSound(type) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    if (type === 'buy') {
      osc.frequency.setValueAtTime(700, ctx.currentTime);
      osc.frequency.linearRampToValueAtTime(1400, ctx.currentTime + 0.15);
    } else {
      osc.frequency.setValueAtTime(800, ctx.currentTime);
      osc.frequency.linearRampToValueAtTime(400, ctx.currentTime + 0.15);
    }
    gain.gain.setValueAtTime(0.2, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.3);
  } catch (e) {}
}

// ---- Actions ----
async function connectBroker() {
  const btn = document.getElementById('btn-connect');
  btn.innerHTML = '<span class="material-icons-round">hourglass_top</span> LAUNCHING BROWSER...';
  btn.disabled = true;

  const dot = document.getElementById('status-dot');
  dot.className = 'status-dot connecting';
  document.getElementById('status-text').textContent = 'Launching...';

  sendWS({ action: 'launch' });

  // Also start simulator as fallback
  setTimeout(() => {
    if (!isAnalyzing) {
      dot.className = 'status-dot online';
      document.getElementById('status-text').textContent = 'Browser launched — login to your account';
      btn.innerHTML = '<span class="material-icons-round">check_circle</span> BROWSER OPENED';
    }
  }, 5000);
}

function startAnalysis() {
  if (isAnalyzing) return;
  isAnalyzing = true;

  document.getElementById('btn-start').style.display = 'none';
  document.getElementById('btn-stop').style.display = 'flex';
  document.querySelectorAll('.panel').forEach(p => p.classList.add('analyzing'));

  // Tell server to start analysis loop
  sendWS({ action: 'start_analysis', interval: 2000 });

  // Also run local simulator as fallback / supplement
  const pair = document.getElementById('currency-pair').value;
  const tf = parseInt(document.getElementById('timeframe').value);
  sim.generateCandles(pair, tf, 120);

  simulatorInterval = setInterval(() => {
    const pair = document.getElementById('currency-pair').value;
    const tf = parseInt(document.getElementById('timeframe').value);
    const candles = sim.tick(pair, tf);

    // Send to server for analysis
    sendWS({
      action: 'analyze_now',
      candles: candles,
      strategy: document.getElementById('strategy').value
    });

    // Update data source display
    document.getElementById('candle-count').textContent = candles.length;
    const price = candles[candles.length - 1].close;
    document.getElementById('signal-price').textContent = price.toFixed(5);
    document.getElementById('signal-pair').textContent = pair;
  }, 2000);

  updateFooterStatus('Analysis running');
}

function stopAnalysis() {
  isAnalyzing = false;

  document.getElementById('btn-start').style.display = 'flex';
  document.getElementById('btn-stop').style.display = 'none';
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('analyzing'));

  sendWS({ action: 'stop_analysis' });

  if (simulatorInterval) {
    clearInterval(simulatorInterval);
    simulatorInterval = null;
  }

  updateFooterStatus('Analysis stopped');
}

// ---- Helpers ----
function updateFooterStatus(text) {
  document.getElementById('footer-status').textContent = text;
}

function updateFooterSource(source) {
  document.getElementById('footer-source').textContent =
    source === 'live' ? 'Live Feed' :
    source === 'tick-built' ? 'Tick Data' : 'Simulator';
}

// ---- Currency pair change ----
document.getElementById('currency-pair').addEventListener('change', () => {
  const pair = document.getElementById('currency-pair').value;
  document.getElementById('signal-pair').textContent = pair;
  sendWS({ action: 'select_pair', pair });

  if (isAnalyzing) {
    const tf = parseInt(document.getElementById('timeframe').value);
    sim.generateCandles(pair, tf, 120);
  }
});

document.getElementById('timeframe').addEventListener('change', () => {
  const tf = parseInt(document.getElementById('timeframe').value);
  sendWS({ action: 'set_timeframe', timeframe: tf });

  if (isAnalyzing) {
    const pair = document.getElementById('currency-pair').value;
    sim.generateCandles(pair, tf, 120);
  }
});

// ---- Init ----
document.addEventListener('DOMContentLoaded', () => {
  connectWS();
  document.getElementById('footer-time').textContent = new Date().toLocaleTimeString();
  setInterval(() => {
    document.getElementById('footer-time').textContent = new Date().toLocaleTimeString();
  }, 1000);
});