/* 拓竹耗材管家 前端 —— 无构建步骤的原生实现，容器里直接静态托管。 */

const S = {
  status: null,
  printers: [],
  printers_full: [],
  spools: [],
  jobs: [],
  catalog: { brands: [], materials: [], colors: [], color_series: {}, material_color_series: {}, spool_weights: {} },
  bindings: [],
  view: "dashboard",
  socket: null,
  auth: { setupRequired: false, authenticated: false, user: null },
  socketRetry: null,
};

/* ── 基础设施 ──────────────────────────────────────────── */
function esc(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

async function api(path, options = {}) {
  const headers = Object.assign({ "Content-Type": "application/json" }, options.headers || {});
  // 登录态走 HttpOnly Cookie，浏览器自动携带，前端不接触令牌
  const resp = await fetch(path, Object.assign({}, options, { headers, credentials: "same-origin" }));
  if (resp.status === 401) {
    showAuthPage();
    throw new Error("需要登录");
  }
  if (!resp.ok) {
    let detail = `请求失败（${resp.status}）`;
    try { detail = (await resp.json()).detail || detail; } catch (e) { /* 忽略 */ }
    throw new Error(detail);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

function toast(message, kind = "") {
  const host = document.getElementById("toasts");
  const node = document.createElement("div");
  node.className = "toast " + kind;
  node.textContent = message;
  host.appendChild(node);
  setTimeout(() => node.remove(), 4200);
}

/* ── 登录页 ────────────────────────────────────────────── */
function showAuthPage() {
  document.getElementById("app").classList.add("hidden");
  document.getElementById("authPage").classList.remove("hidden");
  if (S.socket) { try { S.socket.close(); } catch (e) { /* 忽略 */ } S.socket = null; }
  if (S.socketRetry) { clearTimeout(S.socketRetry); S.socketRetry = null; }
}

function hideAuthPage() {
  document.getElementById("authPage").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
}

function authError(message) {
  const box = document.getElementById("authError");
  if (!message) { box.classList.add("hidden"); box.textContent = ""; return; }
  box.textContent = message;
  box.classList.remove("hidden");
}

function renderAuthPage(status) {
  const setup = !!status.setup_required;
  S.auth = { setupRequired: setup, authenticated: !!status.authenticated, user: status.user || null };

  document.getElementById("authTitle").textContent = setup ? "初始化管理员" : "登录";
  document.getElementById("authSub").textContent = setup
    ? "第一次使用，请创建管理员账号"
    : "请输入账号和密码";

  document.getElementById("authConfirmWrap").classList.toggle("hidden", !setup);
  document.getElementById("authRememberWrap").classList.toggle("hidden", setup);
  document.getElementById("authSubmit").textContent = setup ? "创建并进入" : "登录";

  const userInput = document.getElementById("authUser");
  userInput.value = setup ? "admin" : "";
  document.getElementById("authPass").value = "";
  document.getElementById("authPass2").value = "";
  document.getElementById("authPass").setAttribute("autocomplete", setup ? "new-password" : "current-password");
  authError("");

  // 初始化引导文案：明确告知安全前提
  let foot = "";
  if (setup) {
    foot = status.setup_allowed
      ? "口令至少 8 位，不要只用纯数字。创建后此初始化入口会自动关闭。"
      : "⚠️ 当前不是内网直连，初始化已被拒绝。请先在内网打开本页面完成初始化。";
  }
  document.getElementById("authFoot").innerHTML = foot;
  setTimeout(() => (setup ? document.getElementById("authPass") : userInput).focus(), 60);
}

async function submitAuth(event) {
  event.preventDefault();
  const setup = S.auth.setupRequired;
  const username = document.getElementById("authUser").value.trim();
  const password = document.getElementById("authPass").value;
  const confirm = document.getElementById("authPass2").value;
  const remember = document.getElementById("authRemember").checked;
  const button = document.getElementById("authSubmit");

  authError("");
  if (!username) { authError("请填写账号"); return false; }
  if (!password) { authError("请填写密码"); return false; }
  if (setup && password !== confirm) { authError("两次输入的密码不一致"); return false; }

  button.disabled = true;
  const original = button.textContent;
  button.textContent = setup ? "创建中…" : "登录中…";
  try {
    if (setup) {
      await api("/api/auth/setup", { method: "POST", body: JSON.stringify({ username, password }) });
    } else {
      await api("/api/auth/login", { method: "POST", body: JSON.stringify({ username, password, remember }) });
    }
    await enterApp();
  } catch (err) {
    authError(err.message || "登录失败");
    button.disabled = false;
    button.textContent = original;
    document.getElementById("authPass").value = "";
    document.getElementById("authPass").focus();
  }
  return false;
}

async function doLogout() {
  try { await api("/api/auth/logout", { method: "POST" }); } catch (err) { /* 忽略 */ }
  S.status = null;
  S.auth = { setupRequired: false, authenticated: false, user: null };
  const check = await fetch("/api/auth/status", { credentials: "same-origin" }).then((r) => r.json()).catch(() => null);
  if (check) renderAuthPage(check);
  showAuthPage();
}

function openAccountMenu() {
  const user = S.auth.user || {};
  openModal("账号", `
    <div class="row" style="margin-bottom:14px">
      <span class="avatar" style="width:32px;height:32px;background:var(--accent-soft);color:var(--accent);display:flex;align-items:center;justify-content:center;border-radius:50%;font-weight:600">${esc((user.display_name || "U").slice(0, 1))}</span>
      <div>
        <div><b>${esc(user.display_name || user.username || "—")}</b></div>
        <div class="small muted">账号 ${esc(user.username || "—")}</div>
      </div>
    </div>
    <div class="small muted" style="margin-bottom:14px">
      上次登录：${esc(fmtTime(user.last_login_at))}
    </div>
    <h2 style="font-size:13.5px">修改密码</h2>
    <label class="field"><span>当前密码</span><input type="password" id="pwOld" autocomplete="current-password" /></label>
    <label class="field"><span>新密码</span><input type="password" id="pwNew" autocomplete="new-password" /></label>
    <label class="field"><span>确认新密码</span><input type="password" id="pwNew2" autocomplete="new-password" /></label>
    <div class="row" style="margin-top:16px">
      <button class="primary" onclick="submitPasswordChange()">保存新密码</button>
      <span class="spacer"></span>
      <button class="sm" onclick="logoutAllDevices()">退出所有设备</button>
    </div>
    <p class="small muted" style="margin:14px 0 0">改完密码后，除当前浏览器外的其它登录都会失效。</p>
  `);
}

async function submitPasswordChange() {
  const oldPw = document.getElementById("pwOld").value;
  const newPw = document.getElementById("pwNew").value;
  const newPw2 = document.getElementById("pwNew2").value;
  if (!oldPw || !newPw) { toast("请填写当前密码和新密码", "err"); return; }
  if (newPw !== newPw2) { toast("两次输入的新密码不一致", "err"); return; }
  try {
    await api("/api/auth/password", { method: "POST", body: JSON.stringify({ old_password: oldPw, new_password: newPw }) });
    closeModal();
    toast("密码已更新", "ok");
    const me = await api("/api/auth/me").catch(() => null);
    if (me) { S.auth.user = me.user; renderUserChip(); }
  } catch (err) { toast(err.message, "err"); }
}

async function logoutAllDevices() {
  try {
    await api("/api/auth/logout-all", { method: "POST" });
    closeModal();
    toast("已退出所有设备", "ok");
    doLogout();
  } catch (err) { toast(err.message, "err"); }
}

function renderUserChip() {
  const user = S.auth.user || {};
  const name = user.display_name || user.username || "—";
  document.getElementById("userName").textContent = name;
  document.getElementById("userAvatar").textContent = (name || "U").slice(0, 1);
}

function fmtTime(iso) {
  if (!iso) return "—";
  const date = new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z");
  if (isNaN(date)) return "—";
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  const hhmm = date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  if (sameDay) return "今天 " + hhmm;
  return date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" }) + " " + hhmm;
}

function fmtDuration(seconds) {
  if (!seconds || seconds < 0) return "—";
  const h = Math.floor(seconds / 3600);
  const m = Math.round((seconds % 3600) / 60);
  if (h > 0) return `${h} 小时 ${m} 分`;
  return `${m} 分钟`;
}

function closeModal() { document.getElementById("modalHost").innerHTML = ""; }

function openModal(title, bodyHtml, actionsHtml, wide = false) {
  const host = document.getElementById("modalHost");
  host.innerHTML = `
    <div class="overlay" onclick="if(event.target===this)closeModal()">
      <div class="modal ${wide ? "wide" : ""}">
        <h3>${esc(title)}</h3>
        <div id="modalBody">${bodyHtml}</div>
        <div class="actions">${actionsHtml || '<button onclick="closeModal()">关闭</button>'}</div>
      </div>
    </div>`;
}

/* ── 路由 ─────────────────────────────────────────────── */
function switchView(name) {
  S.view = name;
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  const target = document.getElementById("view-" + name);
  if (target) target.classList.add("active");
  document.querySelectorAll(".nav button").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === name));
  if (name === "spools") loadSpools();
  if (name === "jobs") loadJobs();
  if (name === "settings") { loadStatus(); }
}

document.querySelectorAll(".nav button").forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

/* ── 数据加载 ──────────────────────────────────────────── */
async function loadCatalog() {
  try {
    S.catalog = await api("/api/catalog");
    const materialSel = document.getElementById("spoolMaterial");
    S.catalog.materials.forEach((m) => {
      const option = document.createElement("option");
      option.value = m; option.textContent = m;
      materialSel.appendChild(option);
    });
    const brandSel = document.getElementById("spoolBrand");
    S.catalog.brands.forEach((b) => {
      const option = document.createElement("option");
      option.value = b; option.textContent = b;
      brandSel.appendChild(option);
    });
  } catch (err) { /* 目录加载失败不阻塞主界面 */ }
}

async function loadStatus() {
  S.status = await api("/api/system/status");
  renderDashboard();
  renderSettings();
}

async function loadPrinters() {
  const data = await api("/api/printers");
  S.printers_full = data.printers || [];
}

async function loadBindings() {
  const data = await api("/api/bindings");
  S.bindings = data.bindings || [];
  S.bindingMap = {};
  S.bindings.forEach((b) => { S.bindingMap[`${b.printer_id}:${b.ams_id}:${b.tray_id}`] = b; });
}

async function loadSpools() {
  const params = new URLSearchParams({
    q: document.getElementById("spoolSearch").value || "",
    material: document.getElementById("spoolMaterial").value || "",
    brand: document.getElementById("spoolBrand").value || "",
    archived: document.getElementById("spoolArchived").checked ? "true" : "false",
    low_only: document.getElementById("spoolLowOnly").checked ? "true" : "false",
  });
  const data = await api("/api/spools?" + params.toString());
  S.spools = data.spools || [];
  renderSpools();
}

async function loadJobs() {
  const status = document.getElementById("jobFilter").value;
  const data = await api("/api/jobs?limit=120" + (status ? "&status=" + status : ""));
  S.jobs = data.jobs || [];
  renderJobs();
}

/* ── 仪表盘 ────────────────────────────────────────────── */
function renderDashboard() {
  if (!S.status) return;
  const stats = S.status.stats || {};
  document.getElementById("dashStats").innerHTML = `
    <div class="stat"><div class="label">在用料盘</div><div class="value">${stats.spool_count || 0}<small> 盘</small></div></div>
    <div class="stat"><div class="label">库存余量</div><div class="value">${(stats.remaining_total || 0).toFixed(0)}<small> g</small></div></div>
    <div class="stat"><div class="label">余量不足</div><div class="value">${stats.low_count || 0}<small> 盘</small></div></div>
    <div class="stat"><div class="label">待结算任务</div><div class="value">${(S.status.pending_jobs || []).length}<small> 个</small></div></div>`;

  const printers = S.status.printers || [];
  const host = document.getElementById("printerCards");
  if (!printers.length) {
    host.innerHTML = `<div class="card"><div class="empty-state">
      还没有打印机。到「设置」页绑定拓竹账号后同步设备即可。<br />
      <span class="small">想先看看效果？用 BAMBU_MOCK=1 启动可以跑模拟数据。</span></div></div>`;
  } else {
    host.innerHTML = printers.map(renderPrinterCard).join("");
  }

  const events = S.status.events || [];
  document.getElementById("eventCount").textContent = events.length ? `${events.length} 条` : "";
  document.getElementById("eventList").innerHTML = events.length
    ? events.map((e) => `
        <div class="event">
          <span class="at">${esc(fmtTime(e.at))}</span>
          <div class="body">
            <div class="title">${esc(e.title)}</div>
            ${e.detail ? `<div class="detail">${esc(e.detail)}</div>` : ""}
          </div>
        </div>`).join("")
    : '<div class="empty-state">暂无事件</div>';

  renderConn();
}

function renderConn() {
  const node = document.getElementById("conn");
  const dot = node.querySelector(".dot");
  const text = document.getElementById("connText");
  if (!S.status) { dot.className = "dot"; text.textContent = "连接中"; return; }
  if (S.status.mock) { dot.className = "dot warn"; text.textContent = "模拟模式"; return; }
  const loggedIn = S.status.account && S.status.account.logged_in;
  const mqtt = S.status.mqtt && S.status.mqtt.connected;
  if (mqtt) { dot.className = "dot ok"; text.textContent = "云已连接"; }
  else if (loggedIn) { dot.className = "dot warn"; text.textContent = "云连接中断"; }
  else { dot.className = "dot bad"; text.textContent = "未登录"; }
}

function stateTag(state) {
  if (!state) return '<span class="tag">无数据</span>';
  const map = {
    RUNNING: "green", PREPARE: "blue", PAUSE: "amber",
    FINISH: "teal", FAILED: "red", IDLE: "", OFFLINE: "",
  };
  const cls = map[state.gcode_state] || "";
  return `<span class="tag ${cls}">${esc(state.state_label)}</span>`;
}

function renderPrinterCard(entry) {
  const p = entry.printer;
  const state = entry.state;
  const onlineDot = (p.online || state) ? "ok" : "bad";

  let body = `
    <div class="row small muted" style="gap:14px">
      <span><span class="dot ${onlineDot}"></span> ${esc(p.name || p.serial)}</span>
      <span>${esc(p.model || "未知机型")}</span>
      <span>编号 ${esc((p.serial || "").slice(-6))}</span>
    </div>`;

  if (!state) {
    body += `<div class="empty-state">尚未收到状态。若刚登录，稍等十几秒；也可以点右上角「请求全量状态」。</div>`;
  } else {
    const running = state.gcode_state === "RUNNING" || state.gcode_state === "PAUSE";
    const progressCls = state.gcode_state === "FAILED" ? "failed"
      : state.gcode_state === "FINISH" ? "done"
      : state.gcode_state === "PAUSE" ? "paused" : "";
    body += `
      <div class="row" style="margin-top:10px">
        ${stateTag(state)}
        <span class="small muted">${esc(state.stage_label)}</span>
        <span class="spacer"></span>
        <span class="small muted">${esc(state.subtask_name || "无任务")}</span>
      </div>
      <div class="progress ${progressCls}"><div style="width:${state.progress || 0}%"></div></div>
      <div class="row small muted">
        <span>${state.progress || 0}%</span>
        ${state.total_layer_num ? `<span>第 ${state.layer_num} / ${state.total_layer_num} 层</span>` : ""}
        ${state.remaining_minutes ? `<span>剩余约 ${state.remaining_minutes} 分钟</span>` : ""}
      </div>`;

    if (state.hms && state.hms.length) {
      body += `<div class="row" style="margin-top:8px;gap:6px">
        ${state.hms.map((h) => `<span class="tag red">${esc(h.module)} · ${esc(h.severity)}</span>`).join("")}
      </div>`;
    }

    (state.ams || []).forEach((unit) => {
      body += renderAmsUnit(p, unit, state);
    });

    body += `
      <div class="temps">
        <div class="item">喷嘴 <b>${fmtTemp(state.nozzle_temper, state.nozzle_target)}</b></div>
        <div class="item">热床 <b>${fmtTemp(state.bed_temper, state.bed_target)}</b></div>
        ${state.chamber_temper ? `<div class="item">腔温 <b>${state.chamber_temper.toFixed(0)}°C</b></div>` : ""}
        <div class="item">信号 <b>${esc(state.wifi_signal || "—")}</b></div>
      </div>`;
  }

  return `<div class="card">
    <h2>${esc(p.name || p.serial)} <span class="count">${esc(p.model || "")}</span>
      <span class="spacer"></span>
      <button class="sm" onclick="requestPushall(${p.id})">请求全量状态</button>
    </h2>
    ${body}
  </div>`;
}

function fmtTemp(value, target) {
  const current = (value || 0).toFixed(0);
  return target ? `${current} / ${target.toFixed(0)}°C` : `${current}°C`;
}

function renderAmsUnit(printer, unit, state) {
  const slots = (unit.trays || []).map((tray) => renderSlot(printer, unit, tray)).join("");
  return `<div class="ams-group">
    <div class="ams-title">
      <b>${esc(unit.model || "AMS")} ${unit.ams_id + 1}</b>
      ${unit.temp ? `<span class="tag">${unit.temp.toFixed(0)}°C</span>` : ""}
      ${unit.humidity !== undefined && unit.humidity !== "" ? `<span class="tag">湿度 ${esc(unit.humidity)}</span>` : ""}
    </div>
    <div class="slots">${slots}</div>
  </div>`;
}

function renderSlot(printer, unit, tray) {
  const binding = (S.bindingMap || {})[`${printer.id}:${tray.ams_id}:${tray.tray_id}`];
  const spool = binding && binding.spool;
  const classes = ["slot"];
  if (!tray.occupied) classes.push("empty");
  if (tray.is_active) classes.push("active");
  if (tray.occupied && !spool) classes.push("unbound");

  let barCls = "";
  let barWidth = 0;
  if (spool) {
    barWidth = spool.remaining_percent;
    if (spool.is_low) barCls = "low";
  } else if (tray.remain >= 0) {
    barWidth = tray.remain;
    if (tray.remain <= 15) barCls = "low";
  } else {
    barCls = "unknown";
  }

  const label = tray.occupied ? esc(tray.label) : "空";
  const sub = spool
    ? esc(spool.name)
    : (tray.occupied ? '<span style="color:#b45309">未绑定料盘</span>' : "&nbsp;");

  const remainText = spool
    ? `${spool.remaining_weight.toFixed(0)} g`
    : (tray.remain >= 0 ? `${tray.remain}%` : "");

  return `<div class="${classes.join(" ")}" onclick='openSlotDialog(${printer.id}, ${tray.ams_id}, ${tray.tray_id})'>
    <div class="top">
      <span class="swatch" style="background:${esc(spool ? spool.color_hex : tray.color)}"></span>
      <span class="mat">${label}</span>
      <span class="spacer"></span>
      <span class="idx">${tray.tray_id + 1}</span>
    </div>
    <div class="spool">${sub}</div>
    <div class="bar"><div class="${barCls}" style="width:${Math.max(0, Math.min(100, barWidth))}%"></div></div>
    <div class="row tiny muted" style="justify-content:space-between;margin-top:4px">
      <span>${remainText}</span>
      ${tray.has_rfid ? '<span class="tag teal" style="padding:0 5px">RFID</span>' : ""}
    </div>
  </div>`;
}

async function requestPushall(printerId) {
  try {
    const result = await api(`/api/printers/${printerId}/pushall`, { method: "POST" });
    toast(result.message || "已发送", result.ok ? "ok" : "err");
  } catch (err) { toast(err.message, "err"); }
}

/* ── 料盘 ──────────────────────────────────────────────── */
function renderSpools() {
  const host = document.getElementById("spoolTable");
  document.getElementById("spoolCount").textContent = S.spools.length ? `${S.spools.length} 盘` : "";
  if (!S.spools.length) {
    host.innerHTML = '<div class="empty-state">还没有料盘。点右上角「新增料盘」开始记录。</div>';
    return;
  }
  host.innerHTML = `<table>
    <thead><tr>
      <th>料盘</th><th>材料</th><th>位置 / 槽位</th>
      <th style="text-align:right">余量</th><th style="width:130px">使用进度</th><th></th>
    </tr></thead>
    <tbody>${S.spools.map((spool) => {
      const slots = (spool.slots || []).length
        ? spool.slots.map((x) => esc(x.label)).join("、")
        : "未装到机器上";
      return `<tr class="clickable" onclick="openSpoolDetail(${spool.id})">
        <td>
          <div class="row" style="gap:8px">
            <span class="swatch" style="background:${esc(spool.color_hex)}"></span>
            <div style="min-width:0">
              <div>${esc(spool.name)}</div>
              ${spool.location ? `<div class="tiny muted">${esc(spool.location)}</div>` : ""}
            </div>
          </div>
        </td>
        <td>${esc(spool.material)}</td>
        <td class="small muted">${slots}</td>
        <td class="num">
          ${spool.remaining_weight.toFixed(0)} g
          ${spool.is_low ? '<span class="tag amber">偏低</span>' : ""}
        </td>
        <td>
          <div class="bar" style="height:5px;background:var(--surface-2);border-radius:999px;overflow:hidden">
            <div style="height:100%;width:${spool.remaining_percent}%;
              background:${spool.is_low ? "#d97706" : "var(--accent)"}"></div>
          </div>
          <div class="tiny muted" style="margin-top:3px">${spool.remaining_percent}% · 已用 ${spool.used_weight.toFixed(0)} g</div>
        </td>
        <td onclick="event.stopPropagation()">
          <button class="sm ghost" onclick="openUseDialog(${spool.id})">补录</button>
          <button class="sm ghost" onclick="openMeasureDialog(${spool.id})">校准</button>
        </td>
      </tr>`;
    }).join("")}</tbody></table>`;
}

function spoolById(id) { return S.spools.find((s) => s.id === id); }

/* 从详情弹窗进入编辑：优先用详情接口拿到的完整对象 */
async function editCurrentSpool(id) {
  let spool = S.spools.find((s) => s.id === id);
  if (!spool) {
    try { spool = await api(`/api/spools/${id}`); } catch (err) { /* 退回空表单 */ }
  }
  closeModal();
  openSpoolDialog(spool);
}

/* ── 品牌官方色卡（如 Polymaker Panchroma / PETG） ─────── */
function presetGroupsFor(brand, material) {
  const all = S.catalog.color_series || {};
  const seriesMap = all[brand];
  if (!seriesMap) return [];
  const map = S.catalog.material_color_series || {};
  const mat = (material || "").toUpperCase();
  const groups = [];
  Object.keys(map).forEach((key) => {
    if (!mat.startsWith(key)) return;
    (map[key] || []).forEach((name) => {
      const colors = seriesMap[name];
      if (colors && colors.length) groups.push({ series: name, colors });
    });
  });
  return groups;
}

function renderColorPresets() {
  const brandEl = document.getElementById("f_brand");
  const matEl = document.getElementById("f_material");
  const box = document.getElementById("colorPresets");
  const list = document.getElementById("colorList");
  if (!brandEl || !matEl || !box || !list) return;

  const groups = presetGroupsFor(brandEl.value, matEl.value);
  if (!groups.length) {
    box.innerHTML = "";
    list.innerHTML = (S.catalog.colors || [])
      .map((c) => `<option value="${esc(c.name)}">`).join("");
    S._presetIndex = {};
    return;
  }

  const index = {};
  box.innerHTML = groups.map((g) => `
    <div class="preset-color-box">
      <div class="preset-head">
        <span class="preset-title">${esc(g.series)} 色卡</span>
        <span class="preset-count">${g.colors.length} 色 · 点色块直接选用</span>
      </div>
      <div class="preset-grid">${g.colors.map((c) => {
        index[c.name] = c.hex;
        if (c.en) index[c.en] = c.hex;
        const tip = `${c.name}${c.en ? " / " + c.en : ""} ${c.hex}${c.official ? "" : "（色值为近似）"}`;
        return `<button type="button" class="preset-chip${c.official ? "" : " approx"}"
          data-hex="${esc(c.hex)}" style="background:${esc(c.hex)}" title="${esc(tip)}"
          onclick="pickPresetColor('${esc(c.hex)}', '${esc(c.name)}')"></button>`;
      }).join("")}</div>
    </div>`).join("");

  list.innerHTML = groups.flatMap((g) => g.colors)
    .map((c) => `<option value="${esc(c.name)}" label="${esc(c.en || "")}"></option>`).join("");

  S._presetIndex = index;
  markActivePreset();
}

function pickPresetColor(hex, name) {
  const nameEl = document.getElementById("f_color_name");
  const hexEl = document.getElementById("f_color_hex");
  if (nameEl) nameEl.value = name;
  if (hexEl) hexEl.value = hex;
  markActivePreset();
}

function onColorNameInput() {
  const nameEl = document.getElementById("f_color_name");
  const hexEl = document.getElementById("f_color_hex");
  if (!nameEl || !hexEl) return;
  const hit = (S._presetIndex || {})[nameEl.value.trim()];
  if (hit) hexEl.value = hit;
  markActivePreset();
}

function markActivePreset() {
  const hexEl = document.getElementById("f_color_hex");
  if (!hexEl) return;
  const cur = (hexEl.value || "").toUpperCase();
  document.querySelectorAll(".preset-chip").forEach((el) => {
    const hex = (el.getAttribute("data-hex") || "").toUpperCase();
    el.classList.toggle("active", hex === cur);
  });
}

function openSpoolDialog(spool, forceNew) {
  S.dialogSpool = spool || null;
  // forceNew：表单预填了某盘料的参数，但目的是新增（例如图片识色匹配到的色卡）
  const isEdit = !!spool && !forceNew;
  const value = spool || {
    brand: "", material: "", color_name: "黑色", color_hex: "#1A1A1A",
    spool_weight: 250, initial_weight: 1000, location: "", note: "", name: "",
  };
  const brandOptions = S.catalog.brands.map((b) =>
    `<option value="${esc(b)}" ${b === value.brand ? "selected" : ""}>${esc(b)}</option>`).join("");
  const materialOptions = S.catalog.materials.map((m) =>
    `<option value="${esc(m)}" ${m === value.material ? "selected" : ""}>${esc(m)}</option>`).join("");

  openModal(isEdit ? "编辑料盘" : "新增料盘", `
    <label class="field"><span>品牌</span>
      <select id="f_brand" onchange="renderColorPresets()">${brandOptions}</select></label>
    <div class="field-row">
      <label class="field"><span>材料</span><select id="f_material" onchange="renderColorPresets()">${materialOptions}</select></label>
      <label class="field"><span>颜色名称</span>
        <input id="f_color_name" list="colorList" value="${esc(value.color_name)}" oninput="onColorNameInput()" />
        <datalist id="colorList">${S.catalog.colors.map((c) => `<option value="${esc(c.name)}">`).join("")}</datalist>
      </label>
    </div>
    <div id="colorPresets"></div>
    <div class="field-row">
      <label class="field"><span>颜色</span>
        <input type="color" id="f_color_hex" value="${esc(value.color_hex)}" style="height:34px;padding:2px" oninput="markActivePreset()" /></label>
      <label class="field"><span>空盘皮重（g）</span>
        <input type="number" id="f_spool_weight" value="${value.spool_weight}" step="1" /></label>
    </div>
    <div class="field-row">
      <label class="field"><span>满盘净重（g）</span>
        <input type="number" id="f_initial_weight" value="${value.initial_weight}" step="10" /></label>
      <label class="field"><span>当前余量（g）</span>
        <input type="number" id="f_remaining_weight" value="${isEdit ? value.remaining_weight : value.initial_weight}" step="1" /></label>
    </div>
    <label class="field"><span>存放位置（可选）</span>
      <input id="f_location" value="${esc(value.location || "")}" placeholder="如：干燥箱 A / 货架第二层" /></label>
    <label class="field"><span>备注（可选）</span><input id="f_note" value="${esc(value.note || "")}" /></label>
    <p class="hint">不确定皮重？多数塑料盘在 190~250 g 之间。皮重只影响「称重校准」的换算，不影响自动扣重。</p>
  `, `<button onclick="closeModal()">取消</button>
      <button class="primary" onclick="saveSpool(${isEdit ? spool.id : "null"})">保存</button>`);
  renderColorPresets();
}

async function saveSpool(id) {
  const payload = {
    brand: document.getElementById("f_brand").value.trim(),
    material: document.getElementById("f_material").value.trim(),
    color_name: document.getElementById("f_color_name").value.trim() || "黑色",
    color_hex: document.getElementById("f_color_hex").value,
    spool_weight: parseFloat(document.getElementById("f_spool_weight").value) || 0,
    initial_weight: parseFloat(document.getElementById("f_initial_weight").value) || 1000,
    remaining_weight: parseFloat(document.getElementById("f_remaining_weight").value),
    location: document.getElementById("f_location").value.trim(),
    note: document.getElementById("f_note").value.trim(),
  };
  if (!payload.brand) { toast("请填写品牌", "err"); return; }
  if (!payload.material) { toast("请选择材料", "err"); return; }
  try {
    if (id) {
      await api(`/api/spools/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
      toast("已保存", "ok");
    } else {
      await api("/api/spools", { method: "POST", body: JSON.stringify(payload) });
      toast("已新增料盘", "ok");
    }
    closeModal();
    await loadSpools();
    if (S.status) { await loadStatus(); await loadBindings(); }
  } catch (err) { toast(err.message, "err"); }
}

async function openSpoolDetail(id) {
  try {
    const spool = await api(`/api/spools/${id}`);
    const usages = (spool.usages || []).filter((u) => u.weight_g !== 0);
    const usageRows = usages.length ? usages.map((u) => `
      <tr>
        <td class="small">${esc(fmtTime(u.created_at))}</td>
        <td class="small muted">${esc(u.job_title || u.note || "—")}</td>
        <td class="small muted">${esc(u.slot_label || "")}</td>
        <td class="num">${u.weight_g > 0 ? "-" : "+"}${Math.abs(u.weight_g).toFixed(1)} g</td>
        <td class="small muted">${usageSourceLabel(u.source)}</td>
        <td><button class="sm ghost" onclick="openMoveDialog(${u.id}, ${id}, ${u.weight_g})">转移</button></td>
      </tr>`).join("") : '<tr><td colspan="6"><div class="empty-state">还没有使用记录</div></td></tr>';

    openModal(spool.name, `
      <div class="row" style="margin-bottom:14px;gap:16px">
        <span class="swatch" style="background:${esc(spool.color_hex)};width:26px;height:26px"></span>
        <div>
          <div><b>${spool.remaining_weight.toFixed(0)} g</b>
            <span class="muted small">剩余 / 满盘 ${spool.initial_weight.toFixed(0)} g</span></div>
          <div class="small muted">已用 ${spool.used_weight.toFixed(0)} g ·
            皮重 ${spool.spool_weight.toFixed(0)} g · 含盘 ${spool.total_weight.toFixed(0)} g</div>
        </div>
        <span class="spacer"></span>
        <div class="small muted" style="text-align:right">
          ${(spool.bindings || []).map((b) => `AMS ${b.ams_id + 1} 槽位 ${b.tray_id + 1}`).join("<br>") || "未装载"}
        </div>
      </div>
      <div class="row" style="margin-bottom:14px">
        <button class="sm" onclick="closeModal();openUseDialog(${spool.id})">手动补录消耗</button>
        <button class="sm" onclick="closeModal();openMeasureDialog(${spool.id})">称重校准</button>
        <button class="sm" onclick="editCurrentSpool(${spool.id})">编辑</button>
        <span class="spacer"></span>
        <img src="/api/labels/spool/${spool.id}.png" alt="二维码" style="width:62px;height:62px;border:1px solid var(--border);border-radius:6px" />
      </div>
      <h3 style="font-size:13px;margin-bottom:8px">使用历史</h3>
      <table><thead><tr>
        <th>时间</th><th>来源任务</th><th>槽位</th><th style="text-align:right">增减</th><th>类型</th><th></th>
      </tr></thead><tbody>${usageRows}</tbody></table>
    `, `<button class="primary" onclick="closeModal()">关闭</button>`, true);
  } catch (err) { toast(err.message, "err"); }
}

function usageSourceLabel(source) {  const map = { auto: "自动扣重", manual: "手动补录", calibrate: "称重校准",
                correction: "纠错调整", adjust: "手动调整" };
  return map[source] || source;
}

function openMoveDialog(usageId, spoolId, weight) {
  const options = S.spools.map((s) =>
    `<option value="${s.id}">${esc(s.name)}（余 ${s.remaining_weight.toFixed(0)} g）</option>`).join("");
  const current = spoolById(spoolId);
  openModal("把这条消耗转到另一盘料", `
    <p class="hint">将从「${esc(current ? current.name : "")}」返还 ${Math.abs(weight).toFixed(1)} g，
       并从下面选中的料盘扣减同样的重量。</p>
    <label class="field"><span>目标料盘</span><select id="moveTarget">${options}</select></label>
  `, `<button onclick="closeModal()">取消</button>
      <button class="primary" onclick="doMoveUsage(${usageId})">确认转移</button>`);
}

async function doMoveUsage(usageId) {
  const spoolId = parseInt(document.getElementById("moveTarget").value, 10);
  try {
    await api(`/api/usages/${usageId}/move`, { method: "POST", body: JSON.stringify({ spool_id: spoolId }) });
    toast("已转移并同步余量", "ok");
    closeModal();
    await loadSpools();
    if (S.status) await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

function openUseDialog(spoolId) {
  const spool = spoolById(spoolId) || {};
  openModal("手动补录消耗", `
    <p class="hint">${esc(spool.name || "")}　当前余量 ${(spool.remaining_weight || 0).toFixed(0)} g</p>
    <label class="field"><span>消耗重量（g）</span><input type="number" id="useWeight" step="0.1" value="10" autofocus /></label>
    <label class="field"><span>备注</span><input id="useNote" value="手动补录" /></label>
  `, `<button onclick="closeModal()">取消</button>
      <button class="primary" onclick="doUse(${spoolId})">确认扣减</button>`);
}

async function doUse(spoolId) {
  const weight = parseFloat(document.getElementById("useWeight").value);
  const note = document.getElementById("useNote").value;
  if (!(weight > 0)) { toast("消耗量必须大于 0", "err"); return; }
  try {
    await api(`/api/spools/${spoolId}/use`, { method: "POST", body: JSON.stringify({ weight_g: weight, note }) });
    toast(`已扣减 ${weight} g`, "ok");
    closeModal();
    await loadSpools();
    if (S.status) await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

function openMeasureDialog(spoolId) {
  const spool = spoolById(spoolId) || {};
  openModal("称重校准", `
    <p class="hint">把料盘整个放到秤上称，输入读数即可。<br />
       程序会自动减去皮重（${(spool.spool_weight || 0).toFixed(0)} g），不需要你手动换算。</p>
    <label class="field"><span>含盘总重（g）</span>
      <input type="number" id="measureWeight" step="0.1"
        value="${((spool.spool_weight || 0) + (spool.remaining_weight || 0)).toFixed(1)}" autofocus /></label>
    <p class="hint">当前换算净重：${(spool.remaining_weight || 0).toFixed(1)} g</p>
  `, `<button onclick="closeModal()">取消</button>
      <button class="primary" onclick="doMeasure(${spoolId})">按此校准</button>`);
}

async function doMeasure(spoolId) {
  const total = parseFloat(document.getElementById("measureWeight").value);
  if (!(total > 0)) { toast("称重值必须大于 0", "err"); return; }
  try {
    const result = await api(`/api/spools/${spoolId}/measure`, {
      method: "POST", body: JSON.stringify({ total_weight: total }),
    });
    toast(`已校准为 ${result.remaining_weight.toFixed(1)} g`, "ok");
    closeModal();
    await loadSpools();
    if (S.status) await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

function openLabelSheet() {
  const ids = S.spools.map((s) => s.id).join(",");
  window.open(`/api/labels/sheet?ids=${ids}`, "_blank");
}

/* ── 槽位绑定 ──────────────────────────────────────────── */
function openSlotDialog(printerId, amsId, trayId) {
  const printer = (S.printers_full || []).find((p) => p.id === printerId) || {};
  const binding = (S.bindingMap || {})[`${printerId}:${amsId}:${trayId}`];
  const tray = findTray(printer, amsId, trayId);
  const boundId = binding ? binding.spool_id : 0;

  const options = S.spools.map((s) =>
    `<option value="${s.id}" ${s.id === boundId ? "selected" : ""}>
       ${esc(s.name)}（余 ${s.remaining_weight.toFixed(0)} g）</option>`).join("");

  openModal(`AMS ${amsId + 1} · 槽位 ${trayId + 1}`, `
    <div class="row" style="margin-bottom:12px;gap:14px">
      <span class="swatch" style="background:${esc(tray ? tray.color : "#000")};width:24px;height:24px"></span>
      <div>
        <div>${esc(tray ? tray.label : "未知")}</div>
        <div class="small muted">
          ${tray && tray.remain >= 0 ? `机器报告余量 ${tray.remain}%` : "机器未报告余量"}
          ${tray && tray.has_rfid ? " · 官方 RFID 料盘" : ""}
        </div>
      </div>
    </div>
    <label class="field"><span>绑定到哪盘料</span>
      <select id="bindSpool"><option value="">— 不绑定 —</option>${options}</select></label>
    <div class="row">
      <input id="bindScan" placeholder="或扫码：把光标放这里扫料盘二维码" onkeydown="if(event.key==='Enter')handleScan(this.value,'bindSpool')" />
      <button class="sm" onclick="quickCreateSpoolFromSlot(${printerId},${amsId},${trayId})">按槽位信息建料盘</button>
    </div>
    <div class="row" style="margin-top:14px">
      <img src="/api/labels/slot/${printerId}/${amsId}/${trayId}.png" alt="槽位二维码"
           style="width:72px;height:72px;border:1px solid var(--border);border-radius:6px" />
      <div class="small muted">这是该槽位的二维码，打印出来贴在槽位上，
        以后拿扫码枪扫料盘码就能直接进绑定页。</div>
    </div>
  `, `<button onclick="closeModal()">取消</button>
      <button class="primary" onclick="saveBinding(${printerId},${amsId},${trayId})">保存绑定</button>`);
}

function findTray(printer, amsId, trayId) {
  const state = printer.state;
  if (!state || !state.ams) return null;
  const unit = state.ams.find((u) => u.ams_id === amsId);
  if (!unit) return null;
  return (unit.trays || []).find((t) => t.tray_id === trayId) || null;
}

function handleScan(value, targetSelectId) {
  const text = (value || "").trim();
  if (!text) return;
  let spoolId = 0;
  const match = text.match(/spool=(\d+)/);
  if (match) spoolId = parseInt(match[1], 10);
  else if (/^\d+$/.test(text)) spoolId = parseInt(text, 10);
  if (!spoolId) { toast("没识别出料盘编号", "err"); return; }
  document.getElementById(targetSelectId).value = spoolId;
  toast("已选中料盘 #" + spoolId, "ok");
}

async function quickCreateSpoolFromSlot(printerId, amsId, trayId) {
  const printer = (S.printers_full || []).find((p) => p.id === printerId) || {};
  const tray = findTray(printer, amsId, trayId);
  if (!tray || !tray.occupied) { toast("这个槽位没有识别到耗材", "err"); return; }
  try {
    const created = await api("/api/spools", {
      method: "POST",
      body: JSON.stringify({
        brand: "Bambu Lab",
        material: tray.tray_type || "PLA",
        color_name: "按机器识别",
        color_hex: tray.color,
        spool_weight: 250,
        initial_weight: tray.tray_weight || 1000,
        tray_info_idx: tray.info_idx || "",
      }),
    });
    await loadSpools();
    await api("/api/bindings", {
      method: "PUT",
      body: JSON.stringify({ printer_id: printerId, ams_id: amsId, tray_id: trayId, spool_id: created.id }),
    });
    await loadBindings();
    toast(`已按槽位信息创建并绑定「${created.name}」`, "ok");
    closeModal();
    if (S.status) await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

async function saveBinding(printerId, amsId, trayId) {
  const raw = document.getElementById("bindSpool").value;
  const spoolId = raw ? parseInt(raw, 10) : null;
  try {
    await api("/api/bindings", {
      method: "PUT",
      body: JSON.stringify({ printer_id: printerId, ams_id: amsId, tray_id: trayId, spool_id: spoolId }),
    });
    toast(spoolId ? "已绑定" : "已解绑", "ok");
    closeModal();
    await loadBindings();
    if (S.status) await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

/* ── 打印记录 ──────────────────────────────────────────── */
function jobStatusTag(status, pending) {
  if (pending) return '<span class="tag blue">结算中</span>';
  const map = {
    finished: ["teal", "已完成"], failed: ["red", "失败"],
    cancelled: ["", "已取消"], running: ["green", "进行中"],
  };
  const [cls, label] = map[status] || ["", status];
  return `<span class="tag ${cls}">${label}</span>`;
}

function renderJobs() {
  const host = document.getElementById("jobTable");
  document.getElementById("jobCount").textContent = S.jobs.length ? `${S.jobs.length} 条` : "";
  if (!S.jobs.length) {
    host.innerHTML = '<div class="empty-state">还没有打印记录。任务会在打印机开始打印时自动创建。</div>';
    return;
  }
  host.innerHTML = `<table>
    <thead><tr>
      <th>任务</th><th>打印机</th><th>时间</th>
      <th style="text-align:right">耗材</th><th>状态</th><th>数据来源</th>
    </tr></thead>
    <tbody>${S.jobs.map((job) => `
      <tr class="clickable" onclick="openJobDetail(${job.id})">
        <td><div>${esc(job.title)}</div>
            <div class="tiny muted">${esc(fmtDuration(job.duration_seconds))} · 结束于 ${esc(job.progress_at_end)}%</div></td>
        <td class="small">${esc(job.printer_name || "")}</td>
        <td class="small muted">${esc(fmtTime(job.started_at))}</td>
        <td class="num">${job.total_weight_g ? job.total_weight_g.toFixed(1) + " g" : "—"}</td>
        <td>${jobStatusTag(job.status, job.pending)}</td>
        <td class="small muted">${job.source === "cloud_task" ? "云端任务记录"
          : job.source === "manual" ? "手动录入" : "无数据"}</td>
      </tr>`).join("")}</tbody></table>`;
}

async function openJobDetail(jobId) {
  try {
    const job = await api(`/api/jobs/${jobId}`);
    const filaments = job.filaments || [];
    const rows = filaments.length ? filaments.map((f) => `
      <tr>
        <td><div class="row" style="gap:8px">
          <span class="swatch" style="background:${esc(f.color)}"></span>
          <span>${esc(f.spool_name || "未绑定料盘")}</span></div></td>
        <td class="small muted">${esc(f.slot_label || "—")}</td>
        <td class="small muted">${esc(f.material || "")} ${f.filament_id ? "· " + esc(f.filament_id) : ""}</td>
        <td class="num">${f.weight_g.toFixed(2)} g</td>
        <td class="small muted">${esc(f.match_strategy || "")}</td>
      </tr>`).join("") : '<tr><td colspan="5"><div class="empty-state">这次任务没有解析到耗材明细</div></td></tr>';

    const actions = job.deduction_applied
      ? ""
      : `<button class="sm" onclick="retryJob(${job.id})">重新匹配云端记录</button>
         <button class="sm" onclick="closeModal();openManualDialog(${job.id}, ${job.printer_id})">手动录入用量</button>`;

    openModal(job.title, `
      <div class="row small muted" style="gap:16px;margin-bottom:12px">
        <span>${esc(job.printer_name || "")}</span>
        <span>${esc(fmtTime(job.started_at))} 起</span>
        <span>${esc(fmtDuration(job.duration_seconds))}</span>
        ${jobStatusTag(job.status, job.pending)}
      </div>
      ${job.note ? `<p class="hint">${esc(job.note)}</p>` : ""}
      <div class="row small" style="margin-bottom:12px">
        <span>总耗材 <b>${job.total_weight_g ? job.total_weight_g.toFixed(2) + " g" : "—"}</b></span>
        <span class="muted">数据来源：${job.source === "cloud_task" ? "拓竹云端任务记录"
          : job.source === "manual" ? "手动录入" : "暂无"}</span>
      </div>
      ${actions ? `<div class="row" style="margin-bottom:12px">${actions}</div>` : ""}
      <table><thead><tr><th>料盘</th><th>槽位</th><th>耗材</th>
        <th style="text-align:right">用量</th><th>匹配依据</th></tr></thead>
        <tbody>${rows}</tbody></table>
    `, `<button class="primary" onclick="closeModal()">关闭</button>`, true);
  } catch (err) { toast(err.message, "err"); }
}

async function retryJob(jobId) {
  try {
    const result = await api(`/api/jobs/${jobId}/retry`, { method: "POST" });
    if (result.settled) toast("已匹配到云端记录并完成扣重", "ok");
    else if (result.error) toast(result.error, "err");
    else toast("云端暂时还没有这条任务的记录，稍后会自动重试");
    closeModal();
    await loadJobs();
    await loadSpools();
    if (S.status) await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

function openManualDialog(jobId, printerId) {
  const printer = (S.printers_full || []).find((p) => p.id === printerId) || {};
  const spoolOptions = S.spools.map((s) =>
    `<option value="${s.id}">${esc(s.name)}（余 ${s.remaining_weight.toFixed(0)} g）</option>`).join("");

  let slotRows = "";
  (printer.state && printer.state.ams ? printer.state.ams : []).forEach((unit) => {
    (unit.trays || []).forEach((tray) => {
      if (!tray.occupied) return;
      slotRows += `<tr>
        <td class="small">AMS ${tray.ams_id + 1} 槽位 ${tray.tray_id + 1}
          <div class="tiny muted">${esc(tray.label)}</div></td>
        <td><select id="mn_spool_${tray.ams_id}_${tray.tray_id}">
            <option value="">— 不扣减 —</option>${spoolOptions}</select></td>
        <td><input type="number" id="mn_w_${tray.ams_id}_${tray.tray_id}" step="0.01" value="0" style="width:90px" /></td>
      </tr>`;
    });
  });

  openModal("手动录入本次用量", `
    <p class="hint">云端没有这次打印的记录时用这个。填入各槽位实际消耗的克数，
       并选择从哪盘料扣减。填 0 的行会被忽略。</p>
    ${slotRows ? `<table><thead><tr><th>槽位</th><th>扣减料盘</th>
        <th>消耗（g）</th></tr></thead><tbody>${slotRows}</tbody></table>`
      : '<div class="empty-state">这台机器目前没有在机料盘，请先绑定槽位</div>'}
  `, `<button onclick="closeModal()">取消</button>
      <button class="primary" onclick="submitManual(${jobId},${printerId})">确认并扣减</button>`);
}

async function submitManual(jobId, printerId) {
  const printer = (S.printers_full || []).find((p) => p.id === printerId) || {};
  const items = [];
  (printer.state && printer.state.ams ? printer.state.ams : []).forEach((unit) => {
    (unit.trays || []).forEach((tray) => {
      if (!tray.occupied) return;
      const spoolSel = document.getElementById(`mn_spool_${tray.ams_id}_${tray.tray_id}`);
      const weightInput = document.getElementById(`mn_w_${tray.ams_id}_${tray.tray_id}`);
      if (!spoolSel || !weightInput) return;
      const weight = parseFloat(weightInput.value) || 0;
      const spoolId = spoolSel.value ? parseInt(spoolSel.value, 10) : null;
      if (weight <= 0 || !spoolId) return;
      items.push({ ams_id: tray.ams_id, tray_id: tray.tray_id, spool_id: spoolId, weight_g: weight });
    });
  });
  if (!items.length) { toast("没有填写任何有效用量", "err"); return; }
  try {
    const result = await api(`/api/jobs/${jobId}/manual`, {
      method: "POST", body: JSON.stringify({ items, mark_applied: true }),
    });
    toast(`已扣减 ${result.total_weight_g.toFixed(1)} g`, "ok");
    closeModal();
    await loadJobs();
    await loadSpools();
    if (S.status) await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

/* ── 设置 ──────────────────────────────────────────────── */
function renderSettings() {
  if (!S.status) return;
  const account = S.status.account || {};
  const box = document.getElementById("accountBox");

  if (S.status.mock) {
    box.innerHTML = `<p class="hint">当前是模拟模式，不需要拓竹账号。
      去掉环境变量 BAMBU_MOCK 重启即可接入真实账号。</p>`;
  } else if (account.logged_in) {
    box.innerHTML = `
      <div class="row" style="gap:14px;margin-bottom:12px">
        <span class="tag teal">已登录</span>
        <div>
          <div>${esc(account.account)}</div>
          <div class="small muted">用户 ID ${esc(account.uid)} ·
            区域 ${account.region === "china" ? "中国大陆" : "海外"}</div>
        </div>
      </div>
      <div class="small muted" style="margin-bottom:14px">
        令牌有效期至 ${esc(fmtTime(account.token_expires_at))}
        ${account.has_password_saved ? " · 已保存密码，过期会自动续期"
          : " · 未保存密码，过期后需要重新登录"}
      </div>
      ${account.status !== "ok" ? `<p class="hint">${esc(account.status_message || "")}</p>` : ""}
      <div class="row">
        <button class="sm" onclick="syncDevices()">同步设备</button>
        <button class="sm danger" onclick="logoutAccount()">退出登录</button>
      </div>`;
  } else {
    box.innerHTML = `
      <label class="field"><span>账号（邮箱或手机号）</span>
        <input id="loginAccount" placeholder="you@example.com" /></label>
      <label class="field"><span>密码</span><input type="password" id="loginPassword" /></label>
      <label class="field"><span>区域</span>
        <select id="loginRegion">
          <option value="china">中国大陆</option>
          <option value="global">海外</option>
        </select></label>
      <label class="small muted" style="display:flex;gap:6px;align-items:center;margin-bottom:12px">
        <input type="checkbox" id="loginRemember" checked style="width:auto" />
        保存密码以便令牌过期后自动续期（密码会加密存放在本地数据库里）
      </label>
      <div class="row">
        <button class="primary" onclick="doLogin()">登录</button>
        <button onclick="sendCode()">改用验证码登录</button>
      </div>
      ${account.status === "verifyCode" || account.status === "tfa" ? `
        <div style="margin-top:14px">
          <label class="field"><span>验证码</span><input id="loginCode" /></label>
          <button class="primary" onclick="doCodeLogin()">提交验证码</button>
        </div>` : ""}`;
  }

  const system = S.status;
  const mqtt = system.mqtt || {};
  const cloud = system.cloud || {};
  document.getElementById("systemBox").innerHTML = `
    <table><tbody>
      <tr><td class="muted small">版本</td><td>${esc(system.version)}</td></tr>
      <tr><td class="muted small">运行模式</td><td>${system.mock ? "模拟打印机" : "接入拓竹云"}</td></tr>
      <tr><td class="muted small">云连接</td><td>
        <span class="dot ${mqtt.connected ? "ok" : "bad"}"></span>
        ${mqtt.connected ? "已连接" : esc(mqtt.message || "未连接")}</td></tr>
      <tr><td class="muted small">最近轮询</td><td>${esc(fmtTime(cloud.last_poll))}</td></tr>
      <tr><td class="muted small">云端任务数</td><td>${cloud.tasks_seen || 0}</td></tr>
      ${cloud.last_error ? `<tr><td class="muted small">轮询错误</td><td class="small">${esc(cloud.last_error)}</td></tr>` : ""}
      <tr><td class="muted small">待结算</td><td>${(system.pending_jobs || []).length} 个任务</td></tr>
    </tbody></table>`;

  const printers = system.printers || [];
  document.getElementById("deviceBox").innerHTML = printers.length
    ? `<table><thead><tr><th>名称</th><th>机型</th><th>序列号</th><th>状态</th><th></th></tr></thead>
        <tbody>${printers.map((entry) => `
          <tr>
            <td><input value="${esc(entry.printer.name)}" style="max-width:180px"
                 onchange="renameDevice(${entry.printer.id}, this.value)" /></td>
            <td class="small">${esc(entry.printer.model || "未知")}</td>
            <td class="small muted">${esc(entry.printer.serial)}</td>
            <td><span class="tag ${entry.printer.enabled ? "green" : ""}">
              ${entry.printer.enabled ? "已启用" : "已停用"}</span></td>
            <td>
              <button class="sm ghost" onclick="toggleDevice(${entry.printer.id}, ${!entry.printer.enabled})">
                ${entry.printer.enabled ? "停用" : "启用"}</button>
            </td>
          </tr>`).join("")}</tbody></table>
       <p class="hint" style="margin-top:10px">名称改完按回车生效。停用只是不再订阅它的状态，历史记录会保留。</p>`
    : '<div class="empty-state">还没有设备。先登录拓竹账号，再点「同步设备」。</div>';
}

async function doLogin() {
  const payload = {
    account: document.getElementById("loginAccount").value.trim(),
    password: document.getElementById("loginPassword").value,
    region: document.getElementById("loginRegion").value,
    remember: document.getElementById("loginRemember").checked,
  };
  if (!payload.account || !payload.password) { toast("请填写账号和密码", "err"); return; }
  try {
    await api("/api/account/login", { method: "POST", body: JSON.stringify(payload) });
    toast("登录成功，正在同步设备", "ok");
    await loadPrinters();
    await loadStatus();
  } catch (err) {
    const message = err.message || "";
    if (message.includes("验证码") || message.includes("双重验证")) {
      toast("该账号需要验证码，请在下方输入", "err");
      await loadStatus();
    } else { toast(message, "err"); }
  }
}

async function sendCode() {
  const account = document.getElementById("loginAccount").value.trim();
  const region = document.getElementById("loginRegion").value;
  if (!account) { toast("请先填写邮箱或手机号", "err"); return; }
  try {
    const result = await api("/api/account/code", {
      method: "POST", body: JSON.stringify({ account, region }),
    });
    toast(result.message || "验证码已发送", "ok");
  } catch (err) { toast(err.message, "err"); }
}

async function doCodeLogin() {
  const account = document.getElementById("loginAccount").value.trim();
  const code = document.getElementById("loginCode").value.trim();
  const region = document.getElementById("loginRegion").value;
  try {
    await api("/api/account/login-code", {
      method: "POST", body: JSON.stringify({ account, code, region }),
    });
    toast("登录成功", "ok");
    await loadPrinters();
    await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

async function syncDevices() {
  try {
    const result = await api("/api/devices/sync", { method: "POST" });
    toast(`已同步 ${(result.devices || []).length} 台设备`, "ok");
    await loadPrinters();
    await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

async function logoutAccount() {
  if (!confirm("确定退出登录？本地保存的令牌和密码会被清除。")) return;
  try {
    await api("/api/account/logout", { method: "POST" });
    toast("已退出登录", "ok");
    await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

async function renameDevice(printerId, name) {
  try {
    await api(`/api/printers/${printerId}`, { method: "PATCH", body: JSON.stringify({ name }) });
    toast("已保存", "ok");
    await loadPrinters();
    await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

async function toggleDevice(printerId, enabled) {
  try {
    await api(`/api/printers/${printerId}`, { method: "PATCH", body: JSON.stringify({ enabled }) });
    toast(enabled ? "已启用" : "已停用", "ok");
    await loadPrinters();
    await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

/* ── WebSocket ─────────────────────────────────────────── */
/* ── 图片识色 ───────────────────────────────────────────
   图像本身在浏览器里处理（Canvas 主色聚类 + 吸管），只把最终几个 HEX
   发给后端做配色匹配。好处：容器不用图像库、上传流量小、可以交互式调色。
   色差统一用 CIEDE2000，比 RGB 欧氏距离更贴近人眼判断。         */

const CF = {
  img: null,        // 已解码的原图
  palette: [],      // [{hex, weight}]
  result: null,     // 上一次匹配结果，渲染时按索引取用（避免把中文塞进 onclick）
  catalogTotal: 0,
  busy: false,
};

function cfRgb(hex) {
  const v = String(hex || "").replace("#", "");
  if (v.length !== 6) return [0, 0, 0];
  return [parseInt(v.slice(0, 2), 16), parseInt(v.slice(2, 4), 16), parseInt(v.slice(4, 6), 16)];
}

function cfHexOf(rgb, alpha) {
  const body = rgb.map((v) => Math.max(0, Math.min(255, Math.round(v)))
    .toString(16).padStart(2, "0")).join("");
  return "#" + (alpha === undefined ? body : body + alpha).toUpperCase();
}

function cfDist2(a, b) {
  const dr = a[0] - b[0], dg = a[1] - b[1], db = a[2] - b[2];
  return dr * dr + dg * dg + db * db;
}

function cfLevelClass(level) {
  if (level === "几乎一致" || level === "同色") return "lv-ok";
  if (level === "非常接近" || level === "接近") return "lv-info";
  if (level === "略有差异") return "lv-warn";
  return "lv-far";
}

function openColorFinder() {
  CF.img = null;
  CF.palette = [];
  CF.result = null;
  CF.busy = false;

  const materials = (S.catalog.materials || []).map((m) => `<option value="${esc(m)}">${esc(m)}</option>`).join("");
  const brands = (S.catalog.brands || []).map((b) => `<option value="${esc(b)}">${esc(b)}</option>`).join("");

  openModal("图片识色 · 找同色耗材", `
    <div class="cf-grid">
      <div>
        <div class="cf-drop" id="cfDrop">
          <input type="file" id="cfFile" accept="image/*" hidden />
          <div class="cf-drop-inner" id="cfDropInner">
            <div class="cf-drop-icon"></div>
            <div><b>把图片拖到这里</b></div>
            <div class="small muted">或 <a href="#" onclick="cfBrowse();return false">选择文件</a>，也可以直接 Ctrl+V 粘贴</div>
            <div class="small muted">手机端支持直接拍照</div>
          </div>
          <canvas id="cfCanvas" class="hidden" onclick="cfPick(event)"></canvas>
        </div>
        <div class="cf-tools">
          <button class="sm" onclick="cfBrowse()">选择图片</button>
          <button class="sm" id="cfAgain" onclick="cfExtract()" disabled>重新识别主色</button>
          <button class="sm hidden" id="cfReset" onclick="cfResetImage()">换一张</button>
        </div>
        <div class="small muted" id="cfHint">点击图片上任意位置，可以精确吸取那一块的颜色。</div>
      </div>

      <div>
        <div class="cf-title">识别到的颜色 <span class="count" id="cfPaletteCount"></span>
          <span class="spacer"></span>
          <button class="sm" onclick="cfAddManual()">手动加色</button>
        </div>
        <div class="cf-palette" id="cfPalette"></div>

        <div class="field-row">
          <label class="field"><span>材料</span>
            <select id="cfMaterial"><option value="">全部材料</option>${materials}</select></label>
          <label class="field"><span>品牌</span>
            <select id="cfBrand"><option value="">全部品牌</option>${brands}</select></label>
        </div>
        <label class="field"><span>匹配范围</span>
          <select id="cfScope">
            <option value="both">库里的料 + 品牌色卡</option>
            <option value="inventory">只看库里已有的料</option>
            <option value="catalog">只看品牌色卡</option>
          </select></label>
        <label class="field"><span>色差上限 <b id="cfThresholdLabel">ΔE ≤ 12</b></span>
          <input type="range" id="cfThreshold" min="2" max="30" step="1" value="12"
                 oninput="cfThresholdLabel()" /></label>

        <button class="primary" id="cfRun" onclick="cfRunMatch()" style="width:100%">开始匹配</button>
      </div>
    </div>
    <div id="cfResult" class="cf-result"></div>
  `, '<button onclick="closeModal()">关闭</button>', true);

  const drop = document.getElementById("cfDrop");
  drop.addEventListener("dragover", (ev) => { ev.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (ev) => {
    ev.preventDefault();
    drop.classList.remove("over");
    const file = ev.dataTransfer && ev.dataTransfer.files && ev.dataTransfer.files[0];
    if (file) cfLoadFile(file);
  });
  document.getElementById("cfFile").addEventListener("change", (ev) => {
    const file = ev.target.files && ev.target.files[0];
    if (file) cfLoadFile(file);
  });
  cfRenderPalette();
}

function cfBrowse() {
  const input = document.getElementById("cfFile");
  if (input) input.click();
}

function cfThresholdLabel() {
  const el = document.getElementById("cfThreshold");
  const label = document.getElementById("cfThresholdLabel");
  if (el && label) label.textContent = "ΔE ≤ " + el.value;
}

function cfResetImage() {
  CF.img = null;
  CF.palette = [];
  CF.result = null;
  const canvas = document.getElementById("cfCanvas");
  const inner = document.getElementById("cfDropInner");
  if (canvas) { canvas.classList.add("hidden"); canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height); }
  if (inner) inner.classList.remove("hidden");
  document.getElementById("cfAgain").disabled = true;
  document.getElementById("cfReset").classList.add("hidden");
  document.getElementById("cfResult").innerHTML = "";
  cfRenderPalette();
}

function cfLoadFile(file) {
  if (!file || !/^image\//.test(file.type || "")) { toast("请选择图片文件", "err"); return; }
  if (file.size > 16 * 1024 * 1024) { toast("图片超过 16MB，请先压缩一下", "err"); return; }
  const reader = new FileReader();
  reader.onerror = () => toast("读取图片失败", "err");
  reader.onload = () => {
    const image = new Image();
    image.onerror = () => toast("这个图片格式浏览器打不开", "err");
    image.onload = () => {
      CF.img = image;
      cfDrawImage();
      cfExtract();
    };
    // 用 dataURL 而不是 createObjectURL：现代浏览器会按 EXIF 自动摆正手机照片
    image.src = reader.result;
  };
  reader.readAsDataURL(file);
}

function cfDrawImage() {
  const canvas = document.getElementById("cfCanvas");
  const inner = document.getElementById("cfDropInner");
  if (!canvas || !CF.img) return;
  // 预览按比例缩放到框内，坐标换算时用 canvas 的像素尺寸做基准
  const scale = Math.min(1, 560 / CF.img.width, 380 / CF.img.height);
  canvas.width = Math.max(1, Math.round(CF.img.width * scale));
  canvas.height = Math.max(1, Math.round(CF.img.height * scale));
  canvas.getContext("2d").drawImage(CF.img, 0, 0, canvas.width, canvas.height);
  canvas.classList.remove("hidden");
  if (inner) inner.classList.add("hidden");
  document.getElementById("cfAgain").disabled = false;
  document.getElementById("cfReset").classList.remove("hidden");
}

/* 主色提取：先用边框像素估背景色并剔除，再在最远点初始化的 k-means 上聚类。
   纯 RGB 距离够用了——这一步只决定「哪些像素算一块」，精确色差交给后端。 */
function cfExtract() {
  if (!CF.img) return;
  const MAX = 140;
  const scale = Math.min(1, MAX / CF.img.width, MAX / CF.img.height);
  const w = Math.max(1, Math.round(CF.img.width * scale));
  const h = Math.max(1, Math.round(CF.img.height * scale));

  const work = document.createElement("canvas");
  work.width = w;
  work.height = h;
  const ctx = work.getContext("2d", { willReadFrequently: true });
  ctx.drawImage(CF.img, 0, 0, w, h);
  let data;
  try {
    data = ctx.getImageData(0, 0, w, h).data;
  } catch (err) {
    toast("无法读取图片像素", "err");
    return;
  }

  const pixels = [];
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] < 200) continue;                          // 透明像素
    pixels.push([data[i], data[i + 1], data[i + 2]]);
  }
  if (!pixels.length) { toast("这张图没有可用像素", "err"); return; }

  // 背景色 = 最外两圈像素的中位数
  const border = [];
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (x > 1 && x < w - 2 && y > 1 && y < h - 2) continue;
      const i = (y * w + x) * 4;
      if (data[i + 3] < 200) continue;
      border.push([data[i], data[i + 1], data[i + 2]]);
    }
  }
  let bg = null;
  if (border.length >= 20) {
    const mid = (arr) => { const s = arr.slice().sort((a, b) => a - b); return s[Math.floor(s.length / 2)]; };
    bg = [mid(border.map((p) => p[0])), mid(border.map((p) => p[1])), mid(border.map((p) => p[2]))];
  }

  let subject = bg ? pixels.filter((p) => cfDist2(p, bg) > 34 * 34) : pixels;
  // 主体几乎占满画面时背景估计会失灵，那就别剔了
  if (subject.length < pixels.length * 0.12) subject = pixels;
  // 采样上限，保证手机上也够快
  if (subject.length > 12000) {
    const stride = Math.ceil(subject.length / 12000);
    subject = subject.filter((_, i) => i % stride === 0);
  }

  const clusters = cfKmeans(subject, 6, 12);
  CF.palette = clusters.map((c) => ({ hex: cfHexOf(c.rgb), weight: c.weight }));
  CF.result = null;
  document.getElementById("cfResult").innerHTML = "";
  cfRenderPalette();
}

function cfKmeans(pixels, k, rounds) {
  if (!pixels.length) return [];
  const mean = [0, 0, 0];
  pixels.forEach((p) => { mean[0] += p[0]; mean[1] += p[1]; mean[2] += p[2]; });
  mean[0] /= pixels.length; mean[1] /= pixels.length; mean[2] /= pixels.length;

  // 最远点采样初始化：结果是确定的，同一张图不会每次跳色
  let far = -1, farD = -1;
  pixels.forEach((p, i) => { const d = cfDist2(p, mean); if (d > farD) { farD = d; far = i; } });
  const centroids = [pixels[far].slice()];
  while (centroids.length < k) {
    let best = 0, bestD = -1;
    pixels.forEach((p, i) => {
      let d = Infinity;
      centroids.forEach((c) => { const dd = cfDist2(p, c); if (dd < d) d = dd; });
      if (d > bestD) { bestD = d; best = i; }
    });
    if (bestD <= 0) break;
    centroids.push(pixels[best].slice());
  }

  const assign = new Array(pixels.length).fill(0);
  for (let round = 0; round < rounds; round++) {
    let moved = false;
    for (let i = 0; i < pixels.length; i++) {
      let best = 0, bestD = Infinity;
      for (let c = 0; c < centroids.length; c++) {
        const d = cfDist2(pixels[i], centroids[c]);
        if (d < bestD) { bestD = d; best = c; }
      }
      if (assign[i] !== best) { assign[i] = best; moved = true; }
    }
    const sums = centroids.map(() => [0, 0, 0, 0]);
    for (let i = 0; i < pixels.length; i++) {
      const s = sums[assign[i]];
      s[0] += pixels[i][0]; s[1] += pixels[i][1]; s[2] += pixels[i][2]; s[3] += 1;
    }
    for (let c = 0; c < centroids.length; c++) {
      if (sums[c][3]) centroids[c] = [sums[c][0] / sums[c][3], sums[c][1] / sums[c][3], sums[c][2] / sums[c][3]];
    }
    if (!moved && round > 0) break;
  }

  const counts = centroids.map(() => 0);
  pixels.forEach((p, i) => { counts[assign[i]] += 1; });
  return centroids
    .map((c, i) => ({ rgb: c, count: counts[i] }))
    .filter((c) => c.count > 0)
    .sort((a, b) => b.count - a.count)
    .map((c) => ({ rgb: c.rgb, weight: c.count / pixels.length }));
}

/* 吸管：取点击处 5×5 的平均色 */
function cfPick(ev) {
  if (!CF.img) return;
  const canvas = document.getElementById("cfCanvas");
  const rect = canvas.getBoundingClientRect();
  const x = Math.round((ev.clientX - rect.left) / rect.width * canvas.width);
  const y = Math.round((ev.clientY - rect.top) / rect.height * canvas.height);
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  const r = 2;
  const x0 = Math.max(0, x - r), y0 = Math.max(0, y - r);
  const w = Math.min(canvas.width - x0, r * 2 + 1);
  const h = Math.min(canvas.height - y0, r * 2 + 1);
  if (w <= 0 || h <= 0) return;
  const data = ctx.getImageData(x0, y0, w, h).data;
  let sum = [0, 0, 0], n = 0;
  for (let i = 0; i < data.length; i += 4) {
    if (data[i + 3] < 200) continue;
    sum[0] += data[i]; sum[1] += data[i + 1]; sum[2] += data[i + 2]; n++;
  }
  if (!n) return;
  const hex = cfHexOf(sum.map((v) => v / n));
  cfAddHex(hex, "吸管取色");
}

function cfAddHex(hex, label) {
  const norm = String(hex || "").toUpperCase();
  if (!/^#[0-9A-F]{6}$/.test(norm)) return;
  const hit = CF.palette.find((c) => c.hex === norm);
  if (hit) {
    hit.weight = Math.min(1, hit.weight + 0.12);
    toast(`${norm} 权重已调高`, "ok");
  } else {
    CF.palette.push({ hex: norm, weight: 0.2, manual: true });
    if (label) toast(`${label}：${norm}`, "ok");
  }
  cfRenderPalette();
}

function cfAddManual() {
  const input = document.createElement("input");
  input.type = "color";
  input.value = "#888888";
  input.style.position = "fixed";
  input.style.left = "-9999px";
  document.body.appendChild(input);
  input.addEventListener("input", () => cfAddHex(input.value));
  input.addEventListener("change", () => input.remove());
  input.click();
}

function cfRemoveColor(index) {
  CF.palette.splice(index, 1);
  cfRenderPalette();
}

function cfRenderPalette() {
  const box = document.getElementById("cfPalette");
  const count = document.getElementById("cfPaletteCount");
  if (!box) return;
  if (!CF.palette.length) {
    box.innerHTML = '<div class="cf-empty small">还没有颜色。拖一张图片进来，或点「手动加色」。</div>';
    if (count) count.textContent = "";
    return;
  }
  const total = CF.palette.reduce((sum, c) => sum + c.weight, 0) || 1;
  box.innerHTML = CF.palette.map((c, i) => `
    <div class="cf-chip">
      <span class="cf-swatch" style="background:${esc(c.hex)}"></span>
      <span class="cf-chip-hex">${esc(c.hex)}</span>
      <span class="cf-chip-weight">${Math.round((c.weight / total) * 100)}%</span>
      <button class="cf-chip-x" title="移除" onclick="cfRemoveColor(${i})">×</button>
    </div>`).join("");
  if (count) count.textContent = CF.palette.length + " 色";
}

async function cfRunMatch() {
  if (CF.busy) return;
  if (!CF.palette.length) { toast("先取一个颜色吧", "err"); return; }
  const button = document.getElementById("cfRun");
  CF.busy = true;
  if (button) { button.disabled = true; button.textContent = "匹配中…"; }
  try {
    const data = await api("/api/color/match", {
      method: "POST",
      body: JSON.stringify({
        colors: CF.palette.map((c) => ({ hex: c.hex, weight: c.weight })),
        material: document.getElementById("cfMaterial").value,
        brands: document.getElementById("cfBrand").value ? [document.getElementById("cfBrand").value] : [],
        scope: document.getElementById("cfScope").value,
        max_delta_e: parseFloat(document.getElementById("cfThreshold").value),
        limit: 5,
      }),
    });
    CF.result = data;
    CF.catalogTotal = (data.catalog || {}).total || 0;
    cfRenderResult();
  } catch (err) {
    toast(err.message, "err");
  } finally {
    CF.busy = false;
    if (button) { button.disabled = false; button.textContent = "开始匹配"; }
  }
}

function cfRenderResult() {
  const box = document.getElementById("cfResult");
  if (!box || !CF.result) return;
  const colors = CF.result.colors || [];
  const scope = CF.result.filters.scope;
  const total = CF.catalogTotal;

  if (!colors.length) {
    box.innerHTML = '<div class="cf-empty">没有可匹配的颜色。</div>';
    return;
  }

  box.innerHTML = colors.map((color, ci) => {
    const head = `
      <div class="cf-result-head">
        <span class="cf-swatch lg" style="background:${esc(color.hex)}"></span>
        <div>
          <div class="cf-hit-name">${esc(color.hex)}</div>
          <div class="cf-hit-sub">占画面 ${Math.round(color.weight * 100)}%${
            (color.brands || []).length ? " · 最接近 " + esc(color.brands[0].brand) : ""}</div>
        </div>
      </div>`;

    const inv = color.inventory;
    const cat = color.catalog;

    const invCol = scope === "catalog" ? "" : `
      <div class="cf-col">
        <div class="cf-col-title">库里的料 <span class="count">${
          inv ? (inv.length || "0") : "—"}</span></div>
        ${cfRenderInventory(color, ci)}
      </div>`;

    const catCol = scope === "inventory" ? "" : `
      <div class="cf-col">
        <div class="cf-col-title">品牌色卡 <span class="count">${
          cat ? cat.length : 0}</span><span class="cf-col-note">${total} 色参与比对</span></div>
        ${cfRenderCatalog(color, ci)}
      </div>`;

    return `
      <div class="cf-result-block">
        ${head}
        <div class="cf-cols">${invCol}${catCol}</div>
        ${cfRenderBrands(color, ci)}
      </div>`;
  }).join("");
}

function cfRenderInventory(color, ci) {
  const list = color.inventory;
  if (!list) return "";
  if (!list.length) {
    const near = color.nearest_inventory;
    return `<div class="cf-empty small">库里没有色差在阈值内的料。${
      near ? `最接近的是「${esc(near.name)}」ΔE ${near.delta_e}（差异明显）。` : ""}</div>`;
  }
  return list.map((hit) => `
    <div class="cf-hit">
      <span class="cf-swatch" style="background:${esc(hit.hex)}"></span>
      <div class="cf-hit-main">
        <div class="cf-hit-name">${esc(hit.name || hit.color_name)}${hit.is_low
          ? ' <span class="tag red">余量不足</span>' : ""}</div>
        <div class="cf-hit-sub">${esc(hit.brand)} · ${esc(hit.material)} · ${esc(hit.hex)}
          · 余 ${hit.remaining_weight} g（${hit.remaining_percent}%）${
          hit.location ? " · " + esc(hit.location) : ""}</div>
      </div>
      <div class="cf-hit-de">
        <span class="cf-de">ΔE ${hit.delta_e}</span>
        <span class="cf-level ${cfLevelClass(hit.level)}">${esc(hit.level)}</span>
      </div>
      <button class="sm" onclick="cfOpenSpool(${hit.spool_id})">查看</button>
    </div>`).join("");
}

function cfRenderCatalog(color, ci) {
  const list = color.catalog;
  if (!list) return "";
  if (!list.length) {
    const near = color.nearest_catalog;
    return `<div class="cf-empty small">没有色差在阈值内的官方色。${
      near ? `最接近的是 ${esc(near.brand)}「${esc(near.name)}」ΔE ${near.delta_e}，可以把阈值放宽再试。` : ""}</div>`;
  }
  return list.map((hit, hi) => `
    <div class="cf-hit">
      <span class="cf-swatch" style="background:${esc(hit.hex)}"></span>
      <div class="cf-hit-main">
        <div class="cf-hit-name">${esc(hit.name)}${hit.en ? ` <span class="muted small">${esc(hit.en)}</span>` : ""}${
          hit.official ? "" : ' <span class="tag amber">色值近似</span>'}</div>
        <div class="cf-hit-sub">${esc(hit.brand)} · ${esc(hit.series)} · ${esc(hit.hex)}</div>
      </div>
      <div class="cf-hit-de">
        <span class="cf-de">ΔE ${hit.delta_e}</span>
        <span class="cf-level ${cfLevelClass(hit.level)}">${esc(hit.level)}</span>
      </div>
      <button class="sm" onclick="cfNewSpool(${ci}, ${hi})">建料盘</button>
    </div>`).join("");
}

function cfRenderBrands(color, ci) {
  const brands = color.brands || [];
  if (brands.length < 2) return "";
  return `
    <div class="cf-brands">
      <span class="small muted">换个品牌的等价色：</span>
      ${brands.map((b) => `<span class="cf-brand-chip lv-${cfLevelClass(b.level).slice(3)}">
        <i style="background:${esc(b.hex)}"></i>${esc(b.brand)} · ${esc(b.name)}
        <b>ΔE ${b.delta_e}</b></span>`).join("")}
    </div>`;
}

function cfOpenSpool(spoolId) {
  closeModal();
  openSpoolDetail(spoolId);
}

function cfNewSpool(colorIndex, hitIndex) {
  const color = (CF.result && CF.result.colors || [])[colorIndex];
  const hit = color && (color.catalog || [])[hitIndex];
  if (!hit) return;
  const material = materialForSeries(hit.series);
  const weights = (S.catalog.spool_weights || {})[hit.brand] || [];
  closeModal();
  openSpoolDialog({
    brand: hit.brand,
    material: material,
    color_name: hit.name,
    color_hex: hit.hex,
    spool_weight: weights[0] || 200,
    initial_weight: 1000,
    location: "",
    note: "由图片识色添加（" + hit.hex + "）",
    name: "",
  }, true);
}

/* 色卡系列名反推材料：优先精确命中，再退回前缀匹配 */
function materialForSeries(series) {
  const map = S.catalog.material_color_series || {};
  for (const material of Object.keys(map)) {
    if ((map[material] || []).includes(series)) return material;
  }
  return "";
}

/* 粘贴图片：全局只挂一次，模态不在时直接忽略 */
document.addEventListener("paste", (ev) => {
  if (!document.getElementById("cfDrop")) return;
  const items = (ev.clipboardData && ev.clipboardData.items) || [];
  for (const item of items) {
    if (item.kind === "file" && /^image\//.test(item.type)) {
      const file = item.getAsFile();
      if (file) { ev.preventDefault(); cfLoadFile(file); }
      return;
    }
  }
});

function connectSocket() {
  if (S.socket) { try { S.socket.close(); } catch (e) { /* 忽略 */ } }
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${proto}://${location.host}/ws`);
  S.socket = socket;

  socket.onmessage = (event) => {
    let payload = null;
    try { payload = JSON.parse(event.data); } catch (e) { return; }
    if (payload.type === "hello") {
      // 握手包只带设备快照，不含统计与事件，重新拉一次完整状态
      loadStatus();
      return;
    }
    if (payload.type === "event") {
      addEvent(payload);
      if (payload.title && (payload.title.includes("扣重") || payload.title.includes("打印"))) {
        loadStatus();
      }
      return;
    }
    if (payload.type === "state") {
      const entry = (S.status && S.status.printers || []).find(
        (x) => x.printer.id === payload.printer_id);
      if (entry) {
        entry.state = payload.data;
      } else {
        loadStatus();
        return;
      }
      renderDashboard();
      return;
    }
    if (payload.type === "job_created" || payload.type === "job_settled") {
      loadStatus();
    }
    if (payload.type === "mqtt") {
      if (S.status) {
        S.status.mqtt = { connected: payload.connected, message: payload.message };
        renderConn();
      }
    }
  };

  socket.onclose = (event) => {
    S.socket = null;
    // 4401 是服务端因未登录主动关闭：不要重连，直接回登录页
    if (event && event.code === 4401) {
      showAuthPage();
      return;
    }
    if (S.socketRetry) clearTimeout(S.socketRetry);
    S.socketRetry = setTimeout(connectSocket, 4000);
  };
  socket.onerror = () => { /* onclose 会接手重连 */ };
}

function addEvent(event) {
  if (!S.status) return;
  const list = document.getElementById("eventList");
  if (list.querySelector(".empty-state")) list.innerHTML = "";
  const node = document.createElement("div");
  node.className = "event";
  node.innerHTML = `<span class="at">${esc(fmtTime(event.at))}</span>
    <div class="body">
      <div class="title">${esc(event.title)}</div>
      ${event.detail ? `<div class="detail">${esc(event.detail)}</div>` : ""}
    </div>`;
  list.prepend(node);
  while (list.children.length > 60) list.lastChild.remove();
  document.getElementById("eventCount").textContent = `${list.children.length} 条`;
}

/* ── 启动 ──────────────────────────────────────────────── */
function applyHashRoute() {
  const knownViews = ["dashboard", "spools", "jobs", "settings"];
  const hash = location.hash.slice(1);
  if (knownViews.includes(hash)) {
    switchView(hash);
  } else if (hash.startsWith("spool=")) {
    const id = parseInt(hash.slice(6), 10);
    if (id) { switchView("spools"); openSpoolDetail(id); }
  } else if (hash.startsWith("bind=")) {
    const parts = hash.slice(5).split(":").map(Number);
    if (parts.length === 3 && parts.every((n) => !isNaN(n))) {
      switchView("dashboard");
      openSlotDialog(parts[0], parts[1], parts[2]);
    }
  } else {
    switchView("dashboard");
  }
}

/** 登录成功后进入应用：拉取数据并建立实时连接。 */
async function enterApp() {
  S.auth.authenticated = true;
  S.auth.setupRequired = false;
  renderUserChip();
  hideAuthPage();
  await loadCatalog();
  try {
    await loadBindings();
    await loadPrinters();
    await loadStatus();
    const me = await api("/api/auth/me").catch(() => null);
    if (me) { S.auth.user = me.user; renderUserChip(); }
  } catch (err) {
    if ((err.message || "").includes("登录")) return false;
    toast(err.message, "err");
  }
  connectSocket();
  applyHashRoute();
  return true;
}

async function boot() {
  let status = null;
  try {
    const resp = await fetch("/api/auth/status", { credentials: "same-origin" });
    status = await resp.json();
  } catch (err) {
    document.body.innerHTML = '<div style="padding:40px;font-family:system-ui">无法连接服务，请刷新重试。</div>';
    return;
  }

  if (!status.authenticated) {
    renderAuthPage(status);
    showAuthPage();
    return;
  }

  S.auth = { setupRequired: false, authenticated: true, user: status.user || null };
  await enterApp();
}

// 定时兜底刷新（WebSocket 断线时也能保持数据新鲜）
setInterval(() => { if (S.status && !S.status.mock) loadStatus().catch(() => {}); }, 45000);

boot();
