/* Trae H5 Embedded Jupyter IDE —— 内置 JS agent
 *
 * 运行于浏览器侧，通过 HTTP 调用后端 /api/* 接口，组合 llama 引擎、
 * security、skills_pool、business_tools 等能力。
 */
(function () {
  "use strict";

  const API = (path) => "/api" + path;
  const $ = (id) => document.getElementById(id);

  // ------------------------------------------------------------ JS agent 内核
  /**
   * JS agent —— 封装对后端 API 的调用，提供 chat / audit / iterate / tool 等动作。
   * 这就是「内置 js agent」：H5 内嵌 IDE 中运行于浏览器侧的 agent 内核。
   */
  const JsAgent = {
    name: "trae-js-agent",
    tools: ["notebook", "llm", "security", "skills", "tools"],

    async health() {
      const r = await fetch(API("/health"));
      return r.json();
    },

    async chat(text) {
      const r = await fetch(API("/llm/chat"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: text }],
          temperature: 0.7,
          max_tokens: 512,
        }),
      });
      return r.json();
    },

    async audit(target, content) {
      const r = await fetch(API("/llm/audit"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target, content, context: {} }),
      });
      return r.json();
    },

    async iterate(baselineMs) {
      const r = await fetch(API("/llm/iterate"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ baseline_ms: baselineMs, baseline_payload: {} }),
      });
      return r.json();
    },

    async callTool(tool, payload) {
      const map = {
        "xor-encode": () =>
          fetch(API("/security/xor/encode"), json(payload)),
        "xor-decode": () =>
          fetch(API("/security/xor/decode"), json(payload)),
        "chain-mine": () =>
          fetch(API("/security/blockchain/mine"), json(payload)),
        "skill-add": () => fetch(API("/skills/skill"), json(payload)),
        "like": () => fetch(API("/skills/like"), json(payload)),
        "run-add": () => fetch(API("/tools/running"), json(payload)),
        "budget-add": () => fetch(API("/tools/budget"), json(payload)),
        "bio": () => fetch(API("/tools/bio-science"), json(payload)),
      };
      const fn = map[tool];
      if (!fn) throw new Error("未知工具: " + tool);
      const r = await fn();
      return r.json();
    },
  };

  function json(body) {
    return {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    };
  }

  function show(el, obj) {
    if (!el) return;
    el.textContent = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
  }

  function setStatus(ok, msg) {
    const dot = $("status-dot");
    dot.className = "dot " + (ok ? "dot-ok" : "dot-err");
    $("footer-status").textContent = msg || (ok ? "ready" : "error");
  }

  // ------------------------------------------------------------ notebook
  let cells = [];

  async function refreshNotebook() {
    const r = await fetch(API("/notebook"));
    const data = await r.json();
    cells = data.cells || [];
    renderCells();
    show($("nb-meta"), `单元格: ${data.cell_count}  notebook: ${data.name}`);
  }

  function renderCells() {
    const root = $("cells");
    root.innerHTML = "";
    cells.forEach((c, idx) => root.appendChild(renderCell(c, idx)));
  }

  function renderCell(c, idx) {
    const div = document.createElement("div");
    div.className = "cell cell-" + c.cell_type;
    div.dataset.id = c.cell_id;

    const head = document.createElement("div");
    head.className = "cell-head";
    head.innerHTML =
      `<span class="cell-type">[${idx + 1}] ${c.cell_type}</span>` +
      `<span class="cell-actions">` +
      `<button class="mini-btn run" data-act="run">Run</button>` +
      `<button class="mini-btn" data-act="up">▲</button>` +
      `<button class="mini-btn del" data-act="del">Del</button>` +
      `</span>`;

    const editor = document.createElement("textarea");
    editor.className = "cell-editor";
    editor.value = c.source || "";
    editor.placeholder = c.cell_type === "code" ? "# python code" : "# markdown";
    editor.addEventListener("input", () => {
      c.source = editor.value;
    });

    const out = document.createElement("div");
    out.className = "cell-output";
    if (c.result) renderOutput(out, c.result);

    head.querySelectorAll(".mini-btn").forEach((b) => {
      b.addEventListener("click", async () => {
        const act = b.dataset.act;
        if (act === "run") await runCell(c.cell_id, out);
        if (act === "del") await deleteCell(c.cell_id);
        if (act === "up") {
          c.source = editor.value;
          await updateCell(c.cell_id, c.source);
        }
      });
    });

    // Shift+Enter 运行
    editor.addEventListener("keydown", (e) => {
      if (e.shiftKey && e.key === "Enter") {
        e.preventDefault();
        c.source = editor.value;
        updateCell(c.cell_id, c.source).then(() => runCell(c.cell_id, out));
      }
    });

    div.appendChild(head);
    div.appendChild(editor);
    div.appendChild(out);
    return div;
  }

  function renderOutput(el, result) {
    el.className = "cell-output " + (result.ok ? "ok" : "err");
    let html = "";
    if (result.stdout) html += `<div class="stdout">${esc(result.stdout)}</div>`;
    if (result.value_repr) html += `<div class="val">${esc(result.value_repr)}</div>`;
    if (result.error) html += `<div class="err">${esc(result.error)}</div>`;
    html += `<div class="meta-line">${result.ok ? "ok" : "error"} · ${result.elapsed_ms} ms</div>`;
    el.innerHTML = html;
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (m) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    })[m]);
  }

  async function addCell(type) {
    const r = await fetch(API("/notebook/cell"), json({ cell_type: type, source: "" }));
    await r.json();
    await refreshNotebook();
  }

  async function updateCell(id, source) {
    await fetch(API("/notebook/cell/" + id), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source }),
    });
  }

  async function runCell(id, outEl) {
    outEl = outEl || document.querySelector(`.cell[data-id="${id}"] .cell-output`);
    outEl.className = "cell-output ok";
    outEl.textContent = "running...";
    const r = await fetch(API("/notebook/cell/" + id + "/run"), { method: "POST" });
    const result = await r.json();
    renderOutput(outEl, result);
    setStatus(result.ok, result.ok ? "ok" : "error");
  }

  async function deleteCell(id) {
    await fetch(API("/notebook/cell/" + id), { method: "DELETE" });
    await refreshNotebook();
  }

  async function runAll() {
    const r = await fetch(API("/notebook/run-all"), { method: "POST" });
    const data = await r.json();
    await refreshNotebook();
    show($("footer-info"), `执行 ${data.results.length} 个单元格`);
  }

  async function resetNb() {
    await fetch(API("/notebook/reset"), { method: "POST" });
    await refreshNotebook();
  }

  // ------------------------------------------------------------ tabs
  function bindTabs() {
    document.querySelectorAll(".tab").forEach((t) => {
      t.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((x) => x.classList.remove("active"));
        document.querySelectorAll(".tab-panel").forEach((x) => x.classList.remove("active"));
        t.classList.add("active");
        document.querySelector(`.tab-panel[data-panel="${t.dataset.tab}"]`).classList.add("active");
      });
    });
  }

  // ------------------------------------------------------------ LLM
  async function refreshLlmHealth() {
    const h = await JsAgent.health();
    show($("llm-health"), JSON.stringify(h, null, 2));
    setStatus(h.status === "ok", `llm: ${h.llm && h.llm.mode}`);
  }

  async function llmChat() {
    const text = $("llm-input").value.trim();
    if (!text) return;
    show($("llm-output"), "thinking...");
    const r = await JsAgent.chat(text);
    show($("llm-output"), r);
  }

  async function doAudit() {
    const target = $("audit-target").value || "target";
    const content = $("audit-content").value || "";
    show($("agent-output"), "auditing...");
    const r = await JsAgent.audit(target, content);
    show($("agent-output"), r);
  }

  async function doIterate() {
    const ms = parseFloat($("iter-baseline").value) || 100;
    show($("agent-output"), "iterating...");
    const r = await JsAgent.iterate(ms);
    show($("agent-output"), r);
  }

  // ------------------------------------------------------------ security
  async function xorEncode() {
    const payload = {
      plaintext: $("xor-plain").value,
      dimension: $("xor-dim").value,
      clock_seed: parseInt($("xor-seed").value, 10),
    };
    const r = await JsAgent.callTool("xor-encode", payload);
    show($("xor-output"), r);
    if (r.data_hex) $("xor-plain").dataset.encoded = r.data_hex;
  }

  async function xorDecode() {
    const hex = $("xor-plain").dataset.encoded || $("xor-plain").value;
    const r = await JsAgent.callTool("xor-decode", { data_hex: hex, verify: true });
    show($("xor-output"), r);
  }

  async function chainMine() {
    const r = await JsAgent.callTool("chain-mine", {
      dictionary_entry: $("mine-entry").value,
      ca_serial: $("mine-ca").value,
      dimension: $("xor-dim").value || "dim-1",
      clock_seed: parseInt($("xor-seed").value, 10) || 42,
      ciphertext_hex: $("mine-cipher").value,
      difficulty: 2,
    });
    show($("chain-output"), r);
  }

  async function chainView() {
    const r = await fetch(API("/security/blockchain"));
    show($("chain-output"), await r.json());
  }

  async function chainVerify() {
    const r = await fetch(API("/security/blockchain/verify"));
    show($("chain-output"), await r.json());
  }

  // ------------------------------------------------------------ skills
  async function skillAdd() {
    const r = await JsAgent.callTool("skill-add", {
      name: $("skill-name").value || "untitled",
      description: $("skill-desc").value,
      tags: ($("skill-tags").value || "").split(",").map((s) => s.trim()).filter(Boolean),
    });
    show($("skills-output"), r);
  }

  async function settle() {
    const r = await fetch(API("/skills/settle"));
    show($("skills-output"), await r.json());
  }

  async function skillsRefresh() {
    const r = await fetch(API("/skills"));
    show($("skills-output"), await r.json());
  }

  // ------------------------------------------------------------ tools
  async function runAdd() {
    const r = await JsAgent.callTool("run-add", {
      distance_km: parseFloat($("run-dist").value),
      duration_s: parseFloat($("run-dur").value),
      avg_heart_rate: parseInt($("run-hr").value, 10) || 0,
    });
    show($("tools-output"), r);
  }

  async function runGet() {
    const r = await fetch(API("/tools/running"));
    show($("tools-output"), await r.json());
  }

  async function budgetAdd() {
    const r = await JsAgent.callTool("budget-add", {
      amount: parseFloat($("bud-amount").value),
      category: $("bud-cat").value,
      kind: $("bud-kind").value,
    });
    show($("tools-output"), r);
  }

  async function budgetGet() {
    const r = await fetch(API("/tools/budget"));
    show($("tools-output"), await r.json());
  }

  async function bioGen() {
    const r = await JsAgent.callTool("bio", { n: parseInt($("bio-n").value, 10) || 10 });
    show($("tools-output"), r);
  }

  // ------------------------------------------------------------ bind
  function bind() {
    $("btn-add-code").onclick = () => addCell("code");
    $("btn-add-md").onclick = () => addCell("markdown");
    $("btn-run-all").onclick = runAll;
    $("btn-reset").onclick = resetNb;

    $("btn-llm-health").onclick = refreshLlmHealth;
    $("btn-llm-chat").onclick = llmChat;
    $("btn-audit").onclick = doAudit;
    $("btn-iterate").onclick = doIterate;

    $("btn-xor-encode").onclick = xorEncode;
    $("btn-xor-decode").onclick = xorDecode;
    $("btn-mine").onclick = chainMine;
    $("btn-chain").onclick = chainView;
    $("btn-verify").onclick = chainVerify;

    $("btn-skill-add").onclick = skillAdd;
    $("btn-settle").onclick = settle;
    $("btn-skills-refresh").onclick = skillsRefresh;

    $("btn-run-add").onclick = runAdd;
    $("btn-run-get").onclick = runGet;
    $("btn-bud-add").onclick = budgetAdd;
    $("btn-bud-get").onclick = budgetGet;
    $("btn-bio").onclick = bioGen;
  }

  // ------------------------------------------------------------ init
  async function init() {
    bindTabs();
    bind();
    try {
      await refreshNotebook();
      await refreshLlmHealth();
      // embed 标识
      if (document.documentElement.dataset.embed === "true") {
        $("embed-badge").textContent = "embedded";
      }
      setStatus(true, "ready");
    } catch (e) {
      setStatus(false, "连接失败: " + e.message);
    }
    // 暴露 JS agent 供 H5 宿主调用
    window.TraeJsAgent = JsAgent;
  }

  document.addEventListener("DOMContentLoaded", init);
})();
