/* ===== CHRONOS Attention Tracking Module ===== */
const Attention = (() => {
  let arousalVal = 3;

  function init() {
    // Arousal buttons
    document.querySelectorAll('.arousal').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.arousal').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        arousalVal = parseInt(btn.dataset.v, 10);
      });
    });

    // Score slider
    const score = document.getElementById('attScore');
    const scoreVal = document.getElementById('attScoreVal');
    if (score && scoreVal) {
      score.addEventListener('input', () => { scoreVal.textContent = score.value; });
    }

    // Save
    const saveBtn = document.getElementById('btnSaveAttention');
    if (saveBtn) saveBtn.addEventListener('click', save);
  }

  function save() {
    const task = document.getElementById('attTask').value.trim();
    const score = parseInt(document.getElementById('attScore').value, 10);
    const note = document.getElementById('attNote').value.trim();
    if (!task) { showSnackbar('请填写当前任务', 'error'); return; }
    DataStore.addAttention({
      sessionId: null, attentionScore: score,
      arousalLevel: arousalVal, task, note
    });
    showSnackbar('✅ 状态已记录', 'success');
    document.getElementById('attTask').value = '';
    document.getElementById('attNote').value = '';
    if (typeof App !== 'undefined') { App.renderAttention(); App.renderDashboard(); }
  }

  function drawChart() {
    const canvas = document.getElementById('attentionChart');
    if (!canvas) return;
    const records = DataStore.todayAttention().sort((a,b) => new Date(a.timestamp) - new Date(b.timestamp));
    const ctx2 = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    ctx2.clearRect(0,0,W,H);

    // bg
    ctx2.fillStyle = '#0a0e1a';
    ctx2.fillRect(0,0,W,H);

    // grid
    ctx2.strokeStyle = 'rgba(56,189,248,0.08)';
    for (let i=0;i<=5;i++) {
      const y = (H-20) * i / 5 + 10;
      ctx2.beginPath(); ctx2.moveTo(40, y); ctx2.lineTo(W-10, y); ctx2.stroke();
      ctx2.fillStyle = 'rgba(148,163,184,0.6)';
      ctx2.font = '10px sans-serif';
      ctx2.fillText((100 - i*20), 5, y+3);
    }

    if (!records.length) {
      ctx2.fillStyle = 'rgba(148,163,184,0.5)';
      ctx2.font = '13px sans-serif';
      ctx2.fillText('暂无数据 — 记录当前状态开始追踪', W/2 - 110, H/2);
      return;
    }

    const padL = 40, padR = 10, padT = 10, padB = 25;
    const chartW = W - padL - padR;
    const chartH = H - padT - padB;
    const n = records.length;

    // points
    const getX = i => padL + (n <= 1 ? chartW/2 : (i / (n-1)) * chartW);
    const getY = v => padT + (1 - v/100) * chartH;

    // line gradient
    const grad = ctx2.createLinearGradient(padL, 0, W-padR, 0);
    grad.addColorStop(0, '#f87171'); grad.addColorStop(0.5,'#fbbf24'); grad.addColorStop(1,'#4ade80');

    // area fill
    ctx2.beginPath();
    ctx2.moveTo(getX(0), padT + chartH);
    records.forEach((r,i) => ctx2.lineTo(getX(i), getY(r.attentionScore)));
    ctx2.lineTo(getX(n-1), padT + chartH);
    ctx2.closePath();
    const areaGrad = ctx2.createLinearGradient(0, padT, 0, padT+chartH);
    areaGrad.addColorStop(0, 'rgba(56,189,248,0.3)');
    areaGrad.addColorStop(1, 'rgba(56,189,248,0.02)');
    ctx2.fillStyle = areaGrad;
    ctx2.fill();

    // line
    ctx2.beginPath();
    ctx2.strokeStyle = grad;
    ctx2.lineWidth = 2.5;
    records.forEach((r,i) => {
      const x = getX(i), y = getY(r.attentionScore);
      if (i === 0) ctx2.moveTo(x,y); else ctx2.lineTo(x,y);
    });
    ctx2.stroke();

    // dots
    records.forEach((r,i) => {
      const x = getX(i), y = getY(r.attentionScore);
      ctx2.beginPath();
      ctx2.arc(x, y, 4, 0, Math.PI*2);
      ctx2.fillStyle = '#818cf8';
      ctx2.fill();
      ctx2.strokeStyle = '#fff';
      ctx2.lineWidth = 1;
      ctx2.stroke();
      // label
      if (n <= 8 || i % Math.ceil(n/6) === 0) {
        ctx2.fillStyle = 'rgba(148,163,184,0.8)';
        ctx2.font = '9px sans-serif';
        const t = new Date(r.timestamp);
        const time = `${String(t.getHours()).padStart(2,'0')}:${String(t.getMinutes()).padStart(2,'0')}`;
        ctx2.fillText(time, x-13, H-6);
      }
    });
  }

  return { init, drawChart };
})();
