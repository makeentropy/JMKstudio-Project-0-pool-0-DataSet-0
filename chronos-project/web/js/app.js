/* ===== CHRONOS Main App ===== */
const App = (() => {
  const STATUS_TEXT = { todo:'待办', in_progress:'进行中', review:'评审', done:'完成', blocked:'阻塞' };
  const PRIORITY_TEXT = { urgent:'紧急', high:'高', medium:'中', low:'低' };
  const STATUS_COLOR = { todo:'var(--text-dim)', in_progress:'var(--accent)', review:'var(--purple)', done:'var(--success)', blocked:'var(--danger)' };
  const PROJECT_STATUS_TEXT = { planning:'规划中', active:'进行中', paused:'暂停', completed:'完成' };
  const PRESETS = {
    focus:    { freq: 40,   carrier: 200, purpose: 'focus',    mode: 'isochronic', label: '🧠 专注 40Hz' },
    relax:    { freq: 8,    carrier: 180, purpose: 'relax',    mode: 'isochronic', label: '🌊 放松 8Hz' },
    meditate: { freq: 6,    carrier: 150, purpose: 'meditate', mode: 'isochronic', label: '🧘 冥想 6Hz' },
    sleep:    { freq: 2.5,  carrier: 100, purpose: 'sleep',    mode: 'isochronic', label: '🌙 睡眠 2.5Hz' },
    energy:   { freq: 15,   carrier: 220, purpose: 'energy',   mode: 'isochronic', label: '⚡ 能量 15Hz' },
  };

  let currentActivePreset = null;
  let editingProjectId = null;
  let editingJobId = null;

  function init() {
    setupTabs();
    setupClock();
    setupBioClock();
    Attention.init();
    Sync.init();
    setupProjectModal();
    setupJobModal();
    setupFilters();
    setupKanbanDragDrop();
    refreshAll();
  }

  function refreshAll() {
    renderDashboard();
    renderProjects();
    renderJobs();
    renderSessions();
    renderAttention();
    Sync.render();
  }

  // ===== Tabs =====
  function setupTabs() {
    document.querySelectorAll('.tab').forEach(t => {
      t.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(x => x.classList.remove('active'));
        t.classList.add('active');
        document.getElementById('tab-' + t.dataset.tab).classList.add('active');
        if (t.dataset.tab === 'attention') setTimeout(Attention.drawChart, 50);
      });
    });
  }

  // ===== Live Clock =====
  function setupClock() {
    const el = document.getElementById('liveClock');
    const ed = document.getElementById('liveDate');
    const tick = () => {
      const n = new Date();
      el.textContent = `${pad(n.getHours())}:${pad(n.getMinutes())}:${pad(n.getSeconds())}`;
      ed.textContent = `${n.getFullYear()}/${pad(n.getMonth()+1)}/${pad(n.getDate())} ${'日一二三四五六'[n.getDay()]}`;
    };
    tick(); setInterval(tick, 1000);
  }
  function pad(n) { return String(n).padStart(2,'0'); }

  // ===== Dashboard =====
  function renderDashboard() {
    const projects = DataStore.listProjects();
    const jobs = DataStore.listJobs();
    document.getElementById('statActiveProjects').textContent = projects.filter(p => p.status === 'active').length;
    document.getElementById('statPendingJobs').textContent = jobs.filter(j => j.status !== 'done').length;
    document.getElementById('statFocusMinutes').textContent = DataStore.todayFocusMinutes();

    // recent jobs
    const ul = document.getElementById('recentJobs');
    ul.innerHTML = '';
    jobs.slice(0, 6).forEach(j => {
      const p = DataStore.getProject(j.projectId);
      const li = document.createElement('li');
      li.innerHTML = `
        <div class="j-info">
          <div class="t1">${escapeHtml(j.title)}</div>
          <div class="t2">${p?escapeHtml(p.name):'-'} · ${PRIORITY_TEXT[j.priority]||j.priority} · ${timeAgo(j.updatedAt)}</div>
        </div>
        <span class="badge" style="color:${STATUS_COLOR[j.status]};background:${STATUS_COLOR[j.status]}22;padding:0.2rem 0.5rem;border-radius:10px;font-size:0.7rem">${STATUS_TEXT[j.status]||j.status}</span>`;
      ul.appendChild(li);
    });
    if (!jobs.length) ul.innerHTML = '<li><div class="j-info"><div class="t2">暂无任务</div></div></li>';

    // circadian hints
    const circ = document.getElementById('circadianHints');
    const hour = new Date().getHours();
    const phases = [
      { range: [0,5],  name: '深度睡眠期', color: 'var(--purple)', tip: 'δ波 0.5-4Hz 主导 · 身体修复 · 生长激素分泌' },
      { range: [5,7],  name: '浅眠/皮质醇上升', color: 'var(--accent-2)', tip: 'θ波→α波过渡 · 体温开始回升 · 适合做轻柔冥想' },
      { range: [7,9],  name: '认知高峰期', color: 'var(--accent)', tip: 'β波活跃 · 适合做分析/决策/学习 · 推荐15-20Hz β波声频' },
      { range: [9,12], name: '持续专注期', color: 'var(--success)', tip: '警觉性最高 · 适合复杂任务 · 推荐40Hz γ波增强专注' },
      { range: [12,14],name: '午后低谷期', color: 'var(--warn)', tip: '警觉性下降 · 建议15min小憩 · 可听α波放松' },
      { range: [14,17],name: '创意产出期', color: 'var(--pink)', tip: 'α+β波混合 · 适合创作/讨论 · 推荐8-12Hz SMR' },
      { range: [17,20],name: '运动黄金期', color: 'var(--danger)', tip: '身体协调性/体温最高 · 适合运动' },
      { range: [20,22],name: '放松褪黑期', color: 'var(--purple)', tip: '蓝光抑制褪黑素 · 建议暖光 · 听8Hz以下放松' },
      { range: [22,24],name: '睡眠准备期', color: 'var(--accent-2)', tip: 'θ→δ波过渡 · 2-4Hz声频助眠 · 远离屏幕' }
    ];
    circ.innerHTML = phases.map(p => {
      const now = hour >= p.range[0] && hour < p.range[1];
      return `<div class="phase ${now?'now':''}" style="border-left-color:${p.color}">
        <b style="color:${now?'var(--warn)':p.color}">${pad(p.range[0])}:00 - ${pad(p.range[1])}:00 ${p.name}</b>${now?' <span style="float:right;color:var(--warn)">▼ 当前</span>':''}
        <div style="font-size:0.78rem;color:var(--text-dim);margin-top:0.2rem">${p.tip}</div>
      </div>`;
    }).join('');
  }

  function timeAgo(ts) {
    const diff = (Date.now() - new Date(ts).getTime()) / 1000;
    if (diff < 60) return '刚刚';
    if (diff < 3600) return Math.floor(diff/60) + '分钟前';
    if (diff < 86400) return Math.floor(diff/3600) + '小时前';
    return Math.floor(diff/86400) + '天前';
  }

  // ===== Projects =====
  function renderProjects() {
    const grid = document.getElementById('projectGrid');
    grid.innerHTML = '';
    document.getElementById('btnAddProject').onclick = () => openProjectModal();

    const projects = DataStore.listProjects().sort((a,b) => new Date(b.createdAt) - new Date(a.createdAt));
    projects.forEach(p => {
      const card = document.createElement('div');
      card.className = 'project-card';
      const jobsCount = DataStore.listJobs({ projectId: p.id }).length;
      const doneCount = DataStore.listJobs({ projectId: p.id, status: 'done' }).length;
      card.innerHTML = `
        <div class="p-head">
          <div class="p-name">${escapeHtml(p.name)}</div>
          <span class="p-status ${p.status}">${PROJECT_STATUS_TEXT[p.status]||p.status}</span>
        </div>
        <div class="p-desc">${escapeHtml(p.description||'暂无描述')}</div>
        <div class="p-progress">
          <div class="progress-bar"><div class="fill" style="width:${p.progress}%"></div></div>
          <div class="progress-label"><span>${p.progress}%</span><span>${doneCount}/${jobsCount} 任务</span></div>
        </div>
        <div class="p-meta">
          <span>📅 ${p.startDate||'-'} ~ ${p.endDate||'-'}</span>
          ${(p.members||[]).length?`<span>👥 ${p.members.length}人</span>`:''}
          ${(p.tags||[]).map(t=>`<span class="tag">#${escapeHtml(t)}</span>`).join('')}
        </div>
        <div class="p-actions">
          <button class="btn" data-act="edit" data-id="${p.id}">✏ 编辑</button>
          <button class="btn" data-act="jobs" data-id="${p.id}">📋 任务</button>
          <button class="btn danger" data-act="del" data-id="${p.id}">🗑</button>
        </div>`;
      grid.appendChild(card);
    });

    grid.querySelectorAll('button').forEach(b => {
      b.addEventListener('click', (e) => {
        e.stopPropagation();
        const act = b.dataset.act, id = b.dataset.id;
        if (act === 'edit') openProjectModal(id);
        else if (act === 'del') { if (confirm('删除此项目及所有任务？')) { DataStore.deleteProject(id); refreshAll(); showSnackbar('项目已删除'); } }
        else if (act === 'jobs') {
          document.querySelector('.tab[data-tab="jobs"]').click();
          document.getElementById('filterProject').value = id;
          renderJobs();
        }
      });
    });
  }

  function setupProjectModal() {
    document.getElementById('btnSaveProject').addEventListener('click', () => {
      const name = document.getElementById('pName').value.trim();
      if (!name) { showSnackbar('请填写项目名称', 'error'); return; }
      const obj = {
        id: editingProjectId || undefined,
        name,
        description: document.getElementById('pDesc').value.trim(),
        startDate: document.getElementById('pStart').value || null,
        endDate: document.getElementById('pEnd').value || null,
        status: document.getElementById('pStatus').value,
        members: document.getElementById('pMembers').value.split(',').map(s=>s.trim()).filter(Boolean),
        tags: document.getElementById('pTags').value.split(',').map(s=>s.trim()).filter(Boolean),
      };
      DataStore.upsertProject(obj);
      closeModal('modalProject');
      refreshAll();
      showSnackbar('✅ 项目已保存', 'success');
    });
  }

  function openProjectModal(id) {
    editingProjectId = id || null;
    document.getElementById('modalProjectTitle').textContent = id ? '编辑项目' : '新建项目';
    const p = id ? DataStore.getProject(id) : {};
    document.getElementById('pName').value = p.name || '';
    document.getElementById('pDesc').value = p.description || '';
    document.getElementById('pStart').value = p.startDate || '';
    document.getElementById('pEnd').value = p.endDate || '';
    document.getElementById('pStatus').value = p.status || 'planning';
    document.getElementById('pMembers').value = (p.members||[]).join(',');
    document.getElementById('pTags').value = (p.tags||[]).join(',');
    openModal('modalProject');
  }

  // ===== Jobs (Kanban) =====
  function setupFilters() {
    ['filterProject','filterStatus','filterPriority'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('change', renderJobs);
    });
    document.getElementById('btnAddJob').addEventListener('click', () => openJobModal());
  }

  function setupKanbanDragDrop() {
    // use native HTML5 drag
    const cols = ['todo','in_progress','review','done'];
    cols.forEach(status => {
      const col = document.getElementById('col-'+status);
      col.addEventListener('dragover', e => { e.preventDefault(); col.style.outline = '1px dashed var(--accent)'; });
      col.addEventListener('dragleave', () => { col.style.outline = ''; });
      col.addEventListener('drop', e => {
        e.preventDefault();
        col.style.outline = '';
        const id = e.dataTransfer.getData('text/plain');
        if (id && status) {
          DataStore.moveJob(id, status);
          showSnackbar(`→ ${STATUS_TEXT[status]}`, 'success');
          refreshAll();
        }
      });
    });
  }

  function renderJobs() {
    // refresh project filter select
    const fp = document.getElementById('filterProject');
    const cur = fp.value;
    fp.innerHTML = '<option value="">全部项目</option>' +
      DataStore.listProjects().sort((a,b)=>a.name.localeCompare(b.name))
        .map(p => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('');
    fp.value = cur;

    // refresh job modal project select
    const jp = document.getElementById('jProject');
    const cur2 = jp.value;
    jp.innerHTML = DataStore.listProjects().map(p => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('');
    if (cur2) jp.value = cur2;
    else if (fp.value) jp.value = fp.value;

    const filters = {
      projectId: fp.value || undefined,
      status: document.getElementById('filterStatus').value || undefined,
      priority: document.getElementById('filterPriority').value || undefined,
    };
    // render per column
    const cols = ['todo','in_progress','review','done'];
    let counts = {};
    cols.forEach(s => { document.getElementById('col-'+s).innerHTML = ''; counts[s] = 0; });
    const blocked = [];
    DataStore.listJobs(filters).forEach(j => {
      if (!cols.includes(j.status)) { blocked.push(j); return; }
      counts[j.status]++;
      const card = buildJobCard(j);
      document.getElementById('col-'+j.status).appendChild(card);
    });
    cols.forEach(s => { document.getElementById('cnt-'+s).textContent = counts[s]; });
  }

  function buildJobCard(j) {
    const p = DataStore.getProject(j.projectId);
    const el = document.createElement('div');
    el.className = `job-card priority-${j.priority}`;
    el.draggable = true;
    el.dataset.id = j.id;
    el.innerHTML = `
      <div class="j-title">${escapeHtml(j.title)}</div>
      ${j.description ? `<div class="j-desc">${escapeHtml(j.description)}</div>` : ''}
      <div class="j-meta">
        <span>👤 ${escapeHtml(j.assignee||'未分配')}</span>
        <span>⏱ ${j.actualHours||0}/${j.estimatedHours||0}h</span>
      </div>
      ${p ? `<div class="j-meta" style="margin-top:0.3rem;color:var(--accent)">📁 ${escapeHtml(p.name)}</div>` : ''}
      ${(j.tags||[]).length ? `<div class="j-tags">${j.tags.map(t=>`<span class="j-tag">#${escapeHtml(t)}</span>`).join('')}</div>` : ''}
      <div class="button-row" style="margin-top:0.5rem">
        <button class="btn" data-act="edit" style="font-size:0.72rem;padding:0.25rem 0.5rem">✏</button>
        <button class="btn danger" data-act="del" style="font-size:0.72rem;padding:0.25rem 0.5rem">🗑</button>
      </div>
    `;
    el.addEventListener('dragstart', e => {
      e.dataTransfer.setData('text/plain', j.id);
      el.classList.add('dragging');
    });
    el.addEventListener('dragend', () => el.classList.remove('dragging'));
    el.querySelector('[data-act=edit]').addEventListener('click', e => { e.stopPropagation(); openJobModal(j.id); });
    el.querySelector('[data-act=del]').addEventListener('click', e => {
      e.stopPropagation();
      if (confirm('删除任务？')) { DataStore.deleteJob(j.id); refreshAll(); showSnackbar('任务已删除'); }
    });
    return el;
  }

  function setupJobModal() {
    document.getElementById('btnSaveJob').addEventListener('click', () => {
      const title = document.getElementById('jTitle').value.trim();
      if (!title) { showSnackbar('请填写任务标题', 'error'); return; }
      const obj = {
        id: editingJobId || undefined,
        projectId: document.getElementById('jProject').value,
        title,
        description: document.getElementById('jDesc').value.trim(),
        assignee: document.getElementById('jAssignee').value.trim(),
        status: document.getElementById('jStatus').value,
        priority: document.getElementById('jPriority').value,
        dueDate: document.getElementById('jDue').value || null,
        estimatedHours: parseFloat(document.getElementById('jEst').value) || 0,
        actualHours: parseFloat(document.getElementById('jAct').value) || 0,
        tags: document.getElementById('jTags').value.split(',').map(s=>s.trim()).filter(Boolean),
        dependsOn: []
      };
      DataStore.upsertJob(obj);
      closeModal('modalJob');
      refreshAll();
      showSnackbar('✅ 任务已保存', 'success');
    });
  }

  function openJobModal(id) {
    editingJobId = id || null;
    document.getElementById('modalJobTitle').textContent = id ? '编辑任务' : '新建任务';
    const j = id ? DataStore.getJob(id) : {};
    if (j.projectId) document.getElementById('jProject').value = j.projectId;
    document.getElementById('jTitle').value = j.title || '';
    document.getElementById('jDesc').value = j.description || '';
    document.getElementById('jAssignee').value = j.assignee || '';
    document.getElementById('jStatus').value = j.status || 'todo';
    document.getElementById('jPriority').value = j.priority || 'medium';
    document.getElementById('jDue').value = j.dueDate || '';
    document.getElementById('jEst').value = j.estimatedHours ?? 1;
    document.getElementById('jAct').value = j.actualHours ?? 0;
    document.getElementById('jTags').value = (j.tags||[]).join(',');
    openModal('modalJob');
  }

  // ===== BioClock =====
  function setupBioClock() {
    const freq = document.getElementById('freqSlider');
    const freqVal = document.getElementById('freqVal');
    const carrier = document.getElementById('carrierSlider');
    const carrierVal = document.getElementById('carrierVal');
    const dur = document.getElementById('durSlider');
    const durVal = document.getElementById('durVal');
    const vol = document.getElementById('volSlider');
    const volVal = document.getElementById('volVal');

    freq.addEventListener('input', () => { freqVal.textContent = parseFloat(freq.value).toFixed(1); });
    carrier.addEventListener('input', () => { carrierVal.textContent = carrier.value; });
    dur.addEventListener('input', () => { durVal.textContent = dur.value; });
    vol.addEventListener('input', () => {
      volVal.textContent = vol.value;
      BioClock.setVolume(parseInt(vol.value, 10));
    });

    // presets
    document.querySelectorAll('.preset').forEach(btn => {
      btn.addEventListener('click', () => {
        const preset = PRESETS[btn.dataset.preset];
        if (!preset) return;
        document.querySelectorAll('.preset').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentActivePreset = btn.dataset.preset;
        freq.value = preset.freq; freqVal.textContent = parseFloat(preset.freq).toFixed(1);
        carrier.value = preset.carrier; carrierVal.textContent = preset.carrier;
        document.getElementById('beatType').value = preset.mode;
      });
    });

    document.getElementById('btnPlay').addEventListener('click', () => {
      const sessionId = BioClock.play({
        mode: document.getElementById('beatType').value,
        freq: parseFloat(freq.value),
        carrier: parseInt(carrier.value, 10),
        volume: parseInt(vol.value, 10),
        durationMin: parseInt(dur.value, 10),
        purpose: currentActivePreset ? PRESETS[currentActivePreset].purpose : 'custom'
      });
      document.getElementById('btnPlay').disabled = true;
      document.getElementById('btnStop').disabled = false;
    });

    document.getElementById('btnStop').addEventListener('click', () => {
      BioClock.stop();
      document.getElementById('btnPlay').disabled = false;
      document.getElementById('btnStop').disabled = true;
      renderSessions();
      renderDashboard();
    });
  }

  function renderSessions() {
    const ul = document.getElementById('sessionHistory');
    ul.innerHTML = '';
    const sessions = DataStore.listSessions(10);
    sessions.forEach(s => {
      const li = document.createElement('li');
      const purposeIcon = { focus:'🧠', relax:'🌊', meditate:'🧘', sleep:'🌙', energy:'⚡', custom:'🎵' }[s.purpose] || '🎵';
      const typeText = { isochronic:'等时', binaural:'双耳', monaural:'单耳' }[s.type] || s.type;
      li.innerHTML = `
        <div class="j-info">
          <div class="t1">${purposeIcon} ${s.frequencyHz}Hz · ${typeText} · ${s.durationMinutes}分钟</div>
          <div class="t2">载波${s.carrierFrequencyHz}Hz · ${new Date(s.startedAt).toLocaleString()} · ${s.completed?'✅':'⏹'}</div>
        </div>`;
      ul.appendChild(li);
    });
    if (!sessions.length) ul.innerHTML = '<li><div class="j-info"><div class="t2">暂无记录</div></div></li>';
  }

  // ===== Attention =====
  function renderAttention() {
    const ul = document.getElementById('attentionList');
    ul.innerHTML = '';
    const recs = DataStore.listAttention(8);
    recs.forEach(r => {
      const li = document.createElement('li');
      const faces = ['','😴','🥱','🙂','💪','🔥'];
      li.innerHTML = `
        <div class="j-info">
          <div class="t1">${faces[r.arousalLevel]||''} 专注${r.attentionScore}分 · ${escapeHtml(r.task||'')}</div>
          <div class="t2">${new Date(r.timestamp).toLocaleString()}${r.note?' · '+escapeHtml(r.note):''}</div>
        </div>`;
      ul.appendChild(li);
    });
    if (!recs.length) ul.innerHTML = '<li><div class="j-info"><div class="t2">暂无记录</div></div></li>';
    setTimeout(Attention.drawChart, 30);
  }

  // ===== Modal / Snackbar Helpers (global) =====
  window.openModal = id => document.getElementById(id).classList.remove('hidden');
  window.closeModal = id => document.getElementById(id).classList.add('hidden');
  document.querySelectorAll('.modal').forEach(m => {
    m.addEventListener('click', e => { if (e.target === m) m.classList.add('hidden'); });
  });

  window.showSnackbar = (msg, type = '') => {
    const sb = document.getElementById('snackbar');
    sb.textContent = msg;
    sb.className = 'show ' + type;
    clearTimeout(showSnackbar._t);
    showSnackbar._t = setTimeout(() => sb.className = '', 2200);
  };

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  return { init, refreshAll, renderDashboard, renderProjects, renderJobs, renderSessions, renderAttention };
})();

document.addEventListener('DOMContentLoaded', () => App.init());
