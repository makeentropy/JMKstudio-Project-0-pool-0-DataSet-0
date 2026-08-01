/* ===== CHRONOS Sync Module ===== */
const Sync = (() => {
  function init() {
    document.getElementById('btnExport').addEventListener('click', exportJson);
    document.getElementById('btnImportBtn').addEventListener('click', () => document.getElementById('fileImport').click());
    document.getElementById('fileImport').addEventListener('change', importJsonFile);
    document.getElementById('btnClearData').addEventListener('click', clearAll);
    document.getElementById('btnMergeText').addEventListener('click', mergeTextarea);
    document.getElementById('btnCopyJson').addEventListener('click', copyJson);
    render();
  }

  function render() {
    const d = DataStore.data.sync || {};
    document.getElementById('lastWebSync').textContent = d.lastWebSync ? new Date(d.lastWebSync).toLocaleString() : '-';
    document.getElementById('lastCliSync').textContent = d.lastCliSync ? new Date(d.lastCliSync).toLocaleString() : '-';
    document.getElementById('dataVersion').textContent = DataStore.data.version || 1;
    document.getElementById('conflictCount').textContent = (d.conflicts || []).length;
  }

  function exportJson() {
    const data = DataStore.exportAll();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `chronos_export_${new Date().toISOString().slice(0,10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    DataStore.touchWebSync();
    render();
    showSnackbar('✅ 已导出 JSON 文件', 'success');
  }

  function importJsonFile(e) {
    const f = e.target.files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = evt => {
      try {
        const d = JSON.parse(evt.target.result);
        DataStore.importAll(d, true);
        DataStore.touchWebSync();
        showSnackbar('✅ 数据已合并导入', 'success');
        render();
        if (typeof App !== 'undefined') App.refreshAll();
      } catch (err) {
        showSnackbar('导入失败: ' + err.message, 'error');
      }
    };
    reader.readAsText(f);
    e.target.value = '';
  }

  function mergeTextarea() {
    const ta = document.getElementById('syncTextarea');
    const raw = ta.value.trim();
    if (!raw) { showSnackbar('JSON 内容为空', 'error'); return; }
    try {
      const d = JSON.parse(raw);
      DataStore.importAll(d, true);
      DataStore.touchWebSync();
      render();
      if (typeof App !== 'undefined') App.refreshAll();
      showSnackbar('✅ 合并成功', 'success');
    } catch (err) {
      showSnackbar('合并失败: ' + err.message, 'error');
    }
  }

  function copyJson() {
    const data = JSON.stringify(DataStore.exportAll(), null, 2);
    navigator.clipboard.writeText(data).then(() => {
      showSnackbar('✅ 已复制到剪贴板', 'success');
    }).catch(() => {
      document.getElementById('syncTextarea').value = data;
      showSnackbar('⚠ 剪贴板不可用，已填入文本框', 'error');
    });
  }

  function clearAll() {
    if (!confirm('确定要清空所有数据吗？此操作不可撤销！')) return;
    DataStore.clearAll();
    showSnackbar('已清空，正在刷新...', 'success');
    setTimeout(() => location.reload(), 600);
  }

  return { init, render };
})();
