/* ===== CHRONOS Isochronic Biological Clock Engine =====
 * Web Audio API realtime generator for isochronic tones, binaural beats, monaural beats
 */
const BioClock = (() => {
  let ctx = null;
  let leftOsc = null, rightOsc = null;
  let leftGain = null, rightGain = null;
  let masterGain = null;
  let modOsc = null, modGain = null;    // isochronic / monaural modulator
  let analyser = null;
  let currentMode = 'isochronic';
  let currentFreq = 10;
  let currentCarrier = 200;
  let currentVol = 0.6;
  let playing = false;
  let startTime = 0;
  let durationMs = 15 * 60 * 1000;
  let timerId = null;
  let sessionId = null;
  let sessionPurpose = 'custom';

  function ensureCtx() {
    if (!ctx) {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      masterGain = ctx.createGain();
      masterGain.gain.value = currentVol;
      masterGain.connect(ctx.destination);

      analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      masterGain.connect(analyser);
    }
    if (ctx.state === 'suspended') ctx.resume();
  }

  function stopAll() {
    if (leftOsc) try { leftOsc.stop(); } catch(e){} leftOsc = null;
    if (rightOsc) try { rightOsc.stop(); } catch(e){} rightOsc = null;
    if (modOsc) try { modOsc.stop(); } catch(e){} modOsc = null;
    leftGain = rightGain = modGain = null;
    playing = false;
  }

  function play({ mode, freq, carrier, volume, durationMin, purpose }) {
    ensureCtx();
    stopAll();
    currentMode = mode || 'isochronic';
    currentFreq = freq;
    currentCarrier = carrier;
    currentVol = volume / 100;
    durationMs = durationMin * 60 * 1000;
    sessionPurpose = purpose || 'custom';
    masterGain.gain.value = currentVol;

    const now = ctx.currentTime;

    if (mode === 'binaural') {
      // Binaural: L = carrier, R = carrier + freq (detune in Hz -> cents = 1200*log2((c+f)/c))
      const leftC = carrier;
      const rightC = carrier + freq;
      leftOsc = ctx.createOscillator();
      leftOsc.type = 'sine';
      leftOsc.frequency.value = leftC;
      leftGain = ctx.createGain();
      leftGain.gain.value = 0.5;
      // Pan left
      const pannerL = ctx.createStereoPanner();
      pannerL.pan.value = -1;
      leftOsc.connect(leftGain).connect(pannerL).connect(masterGain);

      rightOsc = ctx.createOscillator();
      rightOsc.type = 'sine';
      rightOsc.frequency.value = rightC;
      rightGain = ctx.createGain();
      rightGain.gain.value = 0.5;
      const pannerR = ctx.createStereoPanner();
      pannerR.pan.value = 1;
      rightOsc.connect(rightGain).connect(pannerR).connect(masterGain);

      leftOsc.start(now);
      rightOsc.start(now);
    }
    else if (mode === 'monaural') {
      // Monaural: single oscillator amplitude-modulated at beat freq via LFO (sine modulation)
      leftOsc = ctx.createOscillator();
      leftOsc.type = 'sine';
      leftOsc.frequency.value = carrier;
      leftGain = ctx.createGain();
      leftGain.gain.value = 0.5;

      modOsc = ctx.createOscillator();
      modOsc.type = 'sine';
      modOsc.frequency.value = freq;
      modGain = ctx.createGain();
      modGain.gain.value = 0.45; // modulation depth
      // modGain output goes into leftGain.gain so gain = 0.5 + 0.45*sin(2πft)
      modOsc.connect(modGain).connect(leftGain.gain);

      leftOsc.connect(leftGain).connect(masterGain);
      leftOsc.start(now);
      modOsc.start(now);
    }
    else { // isochronic - default & most effective
      // Isochronic: square-wave amplitude modulation -> distinct pulses
      // Implementation: carrier oscillator + gain node rapidly switched by square LFO
      leftOsc = ctx.createOscillator();
      leftOsc.type = 'sine';
      leftOsc.frequency.value = carrier;

      leftGain = ctx.createGain();
      leftGain.gain.value = 0.5;

      modOsc = ctx.createOscillator();
      modOsc.type = 'square';
      modOsc.frequency.value = freq;
      modGain = ctx.createGain();
      modGain.gain.value = 0.48; // sharp pulses, 0.02 to ~0.98
      modOsc.connect(modGain).connect(leftGain.gain);

      // smooth in to avoid clicks
      leftGain.gain.setValueAtTime(0, now);
      leftGain.gain.linearRampToValueAtTime(0.5, now + 0.3);

      leftOsc.connect(leftGain).connect(masterGain);
      leftOsc.start(now);
      modOsc.start(now);
    }

    playing = true;
    startTime = Date.now();
    sessionId = DataStore.addSession({
      type: mode,
      frequencyHz: freq,
      carrierFrequencyHz: carrier,
      durationMinutes: durationMin,
      purpose: purpose,
      volume: volume,
      completed: false
    }).id;

    if (timerId) clearInterval(timerId);
    timerId = setInterval(tick, 250);
    updateTimerDisplay();
    return sessionId;
  }

  function stop() {
    if (!playing) return;
    const elapsed = (Date.now() - startTime) / 60000;
    stopAll();
    if (timerId) { clearInterval(timerId); timerId = null; }
    if (sessionId) {
      DataStore.updateSession(sessionId, {
        endedAt: DataStore.ts(),
        completed: elapsed >= (durationMs / 60000) * 0.9
      });
    }
    updateTimerDisplay();
  }

  function tick() {
    if (!playing) return;
    const elapsed = Date.now() - startTime;
    if (elapsed >= durationMs) {
      stop();
      showSnackbar('✅ 声频疗程完成', 'success');
      if (typeof App !== 'undefined' && App.renderSessions) App.renderSessions();
      return;
    }
    updateTimerDisplay();
    drawWave();
  }

  function updateTimerDisplay() {
    const el = document.getElementById('timerDisplay');
    if (!el) return;
    if (!playing) {
      const d = Math.floor(durationMs / 60000);
      el.textContent = `00:00 / ${pad(d)}:00`;
      return;
    }
    const elapsed = Date.now() - startTime;
    const rem = Math.max(0, durationMs - elapsed);
    const em = Math.floor(elapsed / 60000);
    const es = Math.floor((elapsed % 60000) / 1000);
    const rm = Math.floor(rem / 60000);
    const rs = Math.floor((rem % 60000) / 1000);
    el.textContent = `${pad(em)}:${pad(es)} / ${pad(rm)}:${pad(rs)}`;
  }

  function pad(n) { return String(n).padStart(2,'0'); }

  function setVolume(v) {
    currentVol = v / 100;
    if (masterGain) masterGain.gain.value = currentVol;
  }

  let waveRaf = null;
  function drawWave() {
    const canvas = document.getElementById('waveCanvas');
    if (!canvas || !analyser) return;
    const ctx2 = canvas.getContext('2d');
    const W = canvas.width, H = canvas.height;
    const buf = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteTimeDomainData(buf);
    ctx2.clearRect(0, 0, W, H);
    // grid
    ctx2.strokeStyle = 'rgba(56,189,248,0.1)';
    ctx2.lineWidth = 1;
    for (let i=0;i<5;i++) { ctx2.beginPath(); ctx2.moveTo(0,i*H/4); ctx2.lineTo(W,i*H/4); ctx2.stroke(); }
    // wave
    ctx2.lineWidth = 2;
    const grad = ctx2.createLinearGradient(0,0,W,0);
    grad.addColorStop(0,'#38bdf8'); grad.addColorStop(0.5,'#818cf8'); grad.addColorStop(1,'#f472b6');
    ctx2.strokeStyle = grad;
    ctx2.beginPath();
    const step = W / buf.length;
    for (let i=0; i<buf.length; i++) {
      const v = buf[i] / 128.0;
      const y = (v * H) / 2;
      if (i === 0) ctx2.moveTo(i*step, y);
      else ctx2.lineTo(i*step, y);
    }
    ctx2.stroke();
  }

  return {
    play, stop, setVolume,
    get playing() { return playing; },
    get currentFreq() { return currentFreq; },
    get currentCarrier() { return currentCarrier; }
  };
})();
