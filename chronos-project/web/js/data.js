/* ===== CHRONOS Data Layer =====
 * LocalStorage based data store with entity management
 */
const DataStore = (() => {
  const KEY = 'chronos_data_v1';
  const DEFAULT_DATA = () => ({
    version: 1,
    projects: [],
    jobs: [],
    clockSessions: [],
    attentionRecords: [],
    sync: { lastWebSync: null, lastCliSync: null, conflicts: [] },
    meta: { createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() }
  });

  let data = null;

  function load() {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) {
        data = JSON.parse(raw);
        // backward compat: fill missing keys
        const def = DEFAULT_DATA();
        for (const k of Object.keys(def)) if (data[k] === undefined) data[k] = def[k];
      } else {
        data = DEFAULT_DATA();
        // seed demo data
        seedDemoData();
        save();
      }
    } catch (e) {
      console.error('Data load failed:', e);
      data = DEFAULT_DATA();
      seedDemoData();
      save();
    }
    return data;
  }

  function save() {
    data.meta.updatedAt = new Date().toISOString();
    localStorage.setItem(KEY, JSON.stringify(data));
  }

  function seedDemoData() {
    const p1 = uuid();
    data.projects.push({
      id: p1, name: 'Chronos 时空工作站', description: '生物钟+项目管理双端项目',
      createdAt: new Date().toISOString(),
      startDate: new Date().toISOString().slice(0,10),
      endDate: addDays(30).slice(0,10),
      status: 'active', progress: 35, members: ['你','AI助理'], tags: ['核心','MVP']
    });
    const p2 = uuid();
    data.projects.push({
      id: p2, name: '神经科学研究', description: '脑波频率与注意力相关性研究',
      createdAt: new Date().toISOString(),
      startDate: addDays(-7).slice(0,10),
      endDate: addDays(60).slice(0,10),
      status: 'planning', progress: 10, members: ['你'], tags: ['R&D','生物']
    });

    data.jobs.push({
      id: uuid(), projectId: p1, title: '设计H5主界面', description: '深色科幻风格，6大tab',
      assignee: '你', status: 'done', priority: 'high',
      estimatedHours: 4, actualHours: 3.5,
      dueDate: addDays(2).slice(0,10),
      createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
      dependsOn: [], tags: ['前端','UI']
    });
    data.jobs.push({
      id: uuid(), projectId: p1, title: '实现Web Audio等时声频引擎', description: '支持isochronic/binaural',
      assignee: '你', status: 'in_progress', priority: 'urgent',
      estimatedHours: 6, actualHours: 2,
      dueDate: addDays(1).slice(0,10),
      createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
      dependsOn: [], tags: ['音频','核心']
    });
    data.jobs.push({
      id: uuid(), projectId: p1, title: 'Termux CLI TUI开发', description: 'Python curses实现终端UI',
      assignee: '你', status: 'todo', priority: 'medium',
      estimatedHours: 8, actualHours: 0,
      dueDate: addDays(7).slice(0,10),
      createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
      dependsOn: [], tags: ['后端','CLI']
    });
    data.jobs.push({
      id: uuid(), projectId: p2, title: '文献综述：40Hz Gamma与认知', description: '整理10篇论文',
      assignee: '你', status: 'todo', priority: 'high',
      estimatedHours: 10, actualHours: 0,
      dueDate: addDays(14).slice(0,10),
      createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
      dependsOn: [], tags: ['研究']
    });

    data.attentionRecords.push({
      id: uuid(), timestamp: new Date().toISOString(),
      sessionId: null, attentionScore: 72, arousalLevel: 3,
      task: '项目初始化', note: '启动项目，状态良好'
    });
  }

  // ===== Utils =====
  function uuid() { return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = Math.random()*16|0; return (c==='x'?r:(r&0x3|0x8)).toString(16); });
  }
  function addDays(n) { const d = new Date(); d.setDate(d.getDate()+n); return d.toISOString(); }
  function ts() { return new Date().toISOString(); }

  // ===== Projects =====
  function listProjects() { return [...data.projects]; }
  function getProject(id) { return data.projects.find(p => p.id === id); }
  function upsertProject(p) {
    const idx = data.projects.findIndex(x => x.id === p.id);
    if (idx >= 0) {
      data.projects[idx] = { ...data.projects[idx], ...p, updatedAt: ts() };
    } else {
      p.id = p.id || uuid();
      p.createdAt = p.createdAt || ts();
      data.projects.push(p);
    }
    save();
    return p;
  }
  function deleteProject(id) {
    data.projects = data.projects.filter(p => p.id !== id);
    // also delete its jobs
    data.jobs = data.jobs.filter(j => j.projectId !== id);
    save();
  }
  function computeProjectProgress(projectId) {
    const jobs = data.jobs.filter(j => j.projectId === projectId);
    if (!jobs.length) return 0;
    const done = jobs.filter(j => j.status === 'done').length;
    const review = jobs.filter(j => j.status === 'review').length;
    return Math.round(((done + review * 0.5) / jobs.length) * 100);
  }

  // ===== Jobs =====
  function listJobs(filters = {}) {
    let r = [...data.jobs];
    if (filters.projectId) r = r.filter(j => j.projectId === filters.projectId);
    if (filters.status) r = r.filter(j => j.status === filters.status);
    if (filters.priority) r = r.filter(j => j.priority === filters.priority);
    return r.sort((a,b) => new Date(b.updatedAt) - new Date(a.updatedAt));
  }
  function getJob(id) { return data.jobs.find(j => j.id === id); }
  function upsertJob(j) {
    const idx = data.jobs.findIndex(x => x.id === j.id);
    if (idx >= 0) {
      data.jobs[idx] = { ...data.jobs[idx], ...j, updatedAt: ts() };
      j = data.jobs[idx];
    } else {
      j.id = j.id || uuid();
      j.createdAt = j.createdAt || ts();
      j.updatedAt = ts();
      data.jobs.push(j);
    }
    // update parent project progress
    if (j.projectId) {
      const p = getProject(j.projectId);
      if (p) { p.progress = computeProjectProgress(p.id); }
    }
    save();
    return j;
  }
  function deleteJob(id) {
    const j = getJob(id);
    data.jobs = data.jobs.filter(x => x.id !== id);
    if (j && j.projectId) {
      const p = getProject(j.projectId);
      if (p) { p.progress = computeProjectProgress(p.id); }
    }
    save();
  }
  function moveJob(id, newStatus) {
    const j = getJob(id);
    if (!j) return null;
    j.status = newStatus;
    j.updatedAt = ts();
    if (j.projectId) {
      const p = getProject(j.projectId);
      if (p) { p.progress = computeProjectProgress(p.id); }
    }
    save();
    return j;
  }

  // ===== Clock Sessions =====
  function listSessions(limit = 20) {
    return [...data.clockSessions].sort((a,b) => new Date(b.startedAt) - new Date(a.startedAt)).slice(0, limit);
  }
  function addSession(s) {
    s.id = s.id || uuid();
    s.startedAt = s.startedAt || ts();
    data.clockSessions.push(s);
    save();
    return s;
  }
  function updateSession(id, patch) {
    const s = data.clockSessions.find(x => x.id === id);
    if (!s) return null;
    Object.assign(s, patch);
    save();
    return s;
  }
  function todayFocusMinutes() {
    const today = new Date().toISOString().slice(0,10);
    return data.clockSessions
      .filter(s => s.completed && s.startedAt.slice(0,10) === today && (s.purpose === 'focus' || s.purpose === 'energy'))
      .reduce((sum, s) => sum + (s.durationMinutes || 0), 0);
  }

  // ===== Attention Records =====
  function listAttention(limit = 50) {
    return [...data.attentionRecords].sort((a,b) => new Date(b.timestamp) - new Date(a.timestamp)).slice(0, limit);
  }
  function todayAttention() {
    const today = new Date().toISOString().slice(0,10);
    return data.attentionRecords.filter(r => r.timestamp.slice(0,10) === today);
  }
  function addAttention(r) {
    r.id = r.id || uuid();
    r.timestamp = r.timestamp || ts();
    data.attentionRecords.push(r);
    save();
    return r;
  }

  // ===== Export / Import =====
  function exportAll() { return JSON.parse(JSON.stringify(data)); }
  function importAll(newData, merge = true) {
    if (merge && data) {
      // merge arrays by id, prefer newer updatedAt
      const mergeArr = (key, timeKey = 'updatedAt') => {
        const existing = data[key] || [];
        const incoming = newData[key] || [];
        const map = new Map();
        for (const item of existing) map.set(item.id, item);
        for (const item of incoming) {
          const curr = map.get(item.id);
          if (!curr || new Date(item[timeKey] || item.createdAt || 0) > new Date(curr[timeKey] || curr.createdAt || 0)) {
            map.set(item.id, item);
          }
        }
        return [...map.values()];
      };
      data.projects = mergeArr('projects');
      data.jobs = mergeArr('jobs', 'updatedAt');
      data.clockSessions = mergeArr('clockSessions', 'endedAt');
      data.attentionRecords = mergeArr('attentionRecords', 'timestamp');
      data.sync = { ...(data.sync || {}), ...(newData.sync || {}), lastWebSync: ts() };
      data.version = Math.max(data.version || 1, (newData.version || 1) + 1);
    } else {
      data = { ...DEFAULT_DATA(), ...newData };
    }
    save();
  }
  function clearAll() { data = DEFAULT_DATA(); save(); }

  function touchWebSync() { data.sync.lastWebSync = ts(); save(); }

  // init
  load();

  return {
    load, save,
    // projects
    listProjects, getProject, upsertProject, deleteProject, computeProjectProgress,
    // jobs
    listJobs, getJob, upsertJob, deleteJob, moveJob,
    // sessions
    listSessions, addSession, updateSession, todayFocusMinutes,
    // attention
    listAttention, todayAttention, addAttention,
    // export
    exportAll, importAll, clearAll, touchWebSync,
    // getter
    get data() { return data; },
    uuid, ts
  };
})();
