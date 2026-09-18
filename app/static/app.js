/* 拓竹耗材管家 前端 —— 无构建步骤的原生实现，容器里直接静态托管。 */

const S = {
  status: null,
  printers: [],
  printers_full: [],
  spools: [],
  dashSpools: [],
  jobs: [],
  catalog: { brands: [], materials: [], colors: [], color_series: {}, material_color_series: {}, spool_weights: {} },
  bindings: [],
  view: "dashboard",
  socket: null,
  auth: { setupRequired: false, authenticated: false, user: null },
  socketRetry: null,
  // 列表状态：状态标签页与分页都放在这里，渲染时只读
  spoolTab: "all",
  spoolPage: 1,
  spoolPageSize: 10,
  // 表头排序：默认按 ID 升序。dir 只有 asc / desc 两个值。
  spoolSort: { key: "id", dir: "asc" },
  jobPage: 1,
  jobPageSize: 10,
  // 耗材汇总页：概览环形图上选中的材料（null = 看全部）
  summaryFilter: null,
};

/* ── 图标（内联 SVG，随文字颜色走） ───────────────────── */
const ICO = {
  spool: '<svg viewBox="0 0 24 24"><ellipse cx="12" cy="6.5" rx="7.5" ry="2.8"/><path d="M4.5 6.5V12c0 1.6 3.4 2.8 7.5 2.8s7.5-1.2 7.5-2.8V6.5"/><path d="M4.5 12v5.5c0 1.6 3.4 2.8 7.5 2.8s7.5-1.2 7.5-2.8V12"/></svg>',
  weight: '<svg viewBox="0 0 24 24"><circle cx="12" cy="13" r="6.5"/><path d="M12 9.6V13l2.6 1.8"/><path d="M8 4.5h8"/></svg>',
  coins: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M12 7.6v8.8M9.4 10.2h5.2M9.4 13.8h5.2"/></svg>',
  clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M12 7.8v4.7l3.1 1.9"/></svg>',
  alert: '<svg viewBox="0 0 24 24"><path d="M12 4.2 21 19.8H3z"/><path d="M12 10v4.2M12 17.2h.01"/></svg>',
  pencil: '<svg viewBox="0 0 24 24"><path d="M16.4 4.6l3 3L9.6 17.4 5 18.8l1.4-4.6z"/></svg>',
  scale: '<svg viewBox="0 0 24 24"><circle cx="12" cy="13.4" r="6"/><path d="M12 10.4v3.3l2.3 1.6"/><path d="M8.4 4.6h7.2l-1.4 3"/></svg>',
  trash: '<svg viewBox="0 0 24 24"><path d="M4 7h16"/><path d="M9.4 7V5.4c0-.8.6-1.4 1.4-1.4h2.4c.8 0 1.4.6 1.4 1.4V7"/><path d="M6.6 7l.9 12.1c.1 1 .9 1.7 1.9 1.7h5.2c1 0 1.8-.7 1.9-1.7L17.4 7"/><path d="M10.4 11v6M13.6 11v6"/></svg>',
  printer: '<svg viewBox="0 0 24 24"><rect x="6" y="3" width="12" height="5.5" rx="1.4"/><rect x="3.5" y="10.5" width="17" height="9" rx="2"/><path d="M7 19.5v2h10v-2"/><path d="M17 14.2h.01"/></svg>',
  tag: '<svg viewBox="0 0 24 24"><path d="M4.2 4.2h7.1l8.5 8.5-7.1 7.1-8.5-8.5z"/><circle cx="8.1" cy="8.1" r="1.35"/></svg>',
  thermo: '<svg viewBox="0 0 24 24"><path d="M10.4 13.4V5.6a1.6 1.6 0 0 1 3.2 0v7.8a4 4 0 1 1-3.2 0z"/><path d="M12 9.8v6"/></svg>',
  fan: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="1.9"/><path d="M10.2 10.2C8.2 7.6 8.6 5.2 10.7 4.6c1.9-.5 3.1 1.2 2.3 3.1"/><path d="M13.8 10.2c2.6-2 5-1.6 5.6.5.5 1.9-1.2 3.1-3.1 2.3"/><path d="M13.8 13.8c2 2.6 1.6 5-.5 5.6-1.9.5-3.1-1.2-2.3-3.1"/><path d="M10.2 13.8c-2.6 2-5 1.6-5.6-.5-.5-1.9 1.2-3.1 3.1-2.3"/></svg>',
  layer: '<svg viewBox="0 0 24 24"><path d="M12 3.6 20 7.9l-8 4.3-8-4.3z"/><path d="m4 12.4 8 4.3 8-4.3"/><path d="m4 16.4 8 4.3 8-4.3"/></svg>',
  drop: '<svg viewBox="0 0 24 24"><path d="M12 3.6c3 4 5.4 6.6 5.4 9.6a5.4 5.4 0 0 1-10.8 0c0-3 2.4-5.6 5.4-9.6z"/></svg>',
  scan: '<svg viewBox="0 0 24 24"><path d="M4 8.5V5.8c0-1 .8-1.8 1.8-1.8H8.5"/><path d="M15.5 4h2.7c1 0 1.8.8 1.8 1.8v2.7"/><path d="M20 15.5v2.7c0 1-.8 1.8-1.8 1.8h-2.7"/><path d="M8.5 20H5.8c-1 0-1.8-.8-1.8-1.8v-2.7"/><path d="M4 12h16"/></svg>',
  eye: '<svg viewBox="0 0 24 24"><path d="M2.6 12S6.2 6.6 12 6.6 21.4 12 21.4 12 17.8 17.4 12 17.4 2.6 12 2.6 12z"/><circle cx="12" cy="12" r="2.6"/></svg>',
  link: '<svg viewBox="0 0 24 24"><path d="M10.2 13.8a3.6 3.6 0 0 0 5.1 0l2.5-2.5a3.6 3.6 0 0 0-5.1-5.1l-1 1"/><path d="M13.8 10.2a3.6 3.6 0 0 0-5.1 0l-2.5 2.5a3.6 3.6 0 0 0 5.1 5.1l1-1"/></svg>',
  // 解绑用「断开的链」：左下 + 右上的两段链环中间留一道缺口，和 link 一眼能区分
  unlink: '<svg viewBox="0 0 24 24"><path d="M9.6 5.4 8.5 4.3a3.6 3.6 0 0 0-5.1 5.1l2.5 2.5a3.6 3.6 0 0 0 5.1 0"/><path d="M14.4 18.6l1.1 1.1a3.6 3.6 0 0 0 5.1-5.1l-2.5-2.5"/><path d="M4 4l16 16"/></svg>',
  copy: '<svg viewBox="0 0 24 24"><rect x="8.6" y="8.6" width="10.8" height="10.8" rx="2"/><path d="M15.4 5.6v-.1A1.5 1.5 0 0 0 13.9 4H5.6A1.5 1.5 0 0 0 4 5.5V14a1.5 1.5 0 0 0 1.5 1.5h.1"/></svg>',
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

function closeModal() {
  document.getElementById("modalHost").innerHTML = "";
  // 深链（#spool= / #bind=）开出来的弹窗关掉后，地址里还留着那段深链，
  // 不换成 #view= 的话随手一刷新又把它弹回来了。
  const hash = location.hash.slice(1);
  if (hash.startsWith("spool=") || hash.startsWith("bind=")) {
    syncHashView(S.view || "dashboard", true);
  }
}

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
/** 所有可切换的视图名。新增视图时这里要跟着加 —— 少了它，
 *  `#view=<新视图>` 的链接会被当成无效 hash 而掉回仪表盘。 */
const VIEW_NAMES = ["dashboard", "spools", "summary", "jobs", "settings"];

/** 上次所在视图的本地存储键。
 *
 *  为什么光有 hash 不够（用户报的「每次刷新都回到仪表盘」）：
 *  hash 只覆盖「地址栏里确实带着 #view=xxx」这一种情形。实际按 F5 时
 *  地址栏常常是**干净的** —— 从书签进的、手打网址进的、浏览器把 hash 吞了、
 *  或者用了会清掉 hash 的跳转。那时 applyHashRoute(initial) 落到 else 分支
 *  直接 switchView("dashboard")，界面就被拽回仪表盘了。
 *  所以除了 hash，再往 localStorage 里记一份兜底。 */
const VIEW_STORE_KEY = "bambu.lastView";

function rememberView(name) {
  try { localStorage.setItem(VIEW_STORE_KEY, name); } catch (e) { /* 隐私模式等，忽略 */ }
}

/** 读回上次所在视图；不在白名单里（老版本残留 / 手改过）就当没有。 */
function lastRememberedView() {
  try {
    const v = localStorage.getItem(VIEW_STORE_KEY);
    return VIEW_NAMES.includes(v) ? v : "";
  } catch (e) { return ""; }
}

/** 把当前视图记进地址栏，刷新后能回到原页面。
 *
 *  用 replaceState 而不是 location.hash =：后者会触发 hashchange，
 *  于是「改 hash → applyHashRoute → switchView → 再改 hash」自成死循环；
 *  replaceState 只换地址不派发事件，也不往前进/后退历史里塞记录，
 *  免得用户点一下后退在五个标签之间来回跳。
 *
 *  `#spool=` / `#bind=` 这类深链**不覆盖**：扫码进来的那次刷新还应该落在
 *  那盘料上（弹窗关掉时由 closeModal 换成 `#view=<当前视图>`）。
 */
function syncHashView(name, force) {
  // 记本地兜底要在「深链不覆盖」判断**之前**：扫码进来停在料盘详情时，
  // 用户按 F5 期望的是回到料盘库存页，而不是被深链判空后掉回仪表盘。
  rememberView(name);
  const hash = location.hash.slice(1);
  const isDeepLink = hash.startsWith("spool=") || hash.startsWith("bind=");
  if (isDeepLink && !force) return;
  if (hash === "view=" + name) return;
  try {
    history.replaceState(null, "", "#view=" + name);
  } catch (e) { /* 某些嵌入环境禁改地址，忽略即可 */ }
}

function switchView(name) {
  S.view = name;
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  const target = document.getElementById("view-" + name);
  if (target) target.classList.add("active");
  document.querySelectorAll(".nav button").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === name));
  syncHashView(name);
  if (name === "spools") loadSpools();
  if (name === "jobs") loadJobs();
  if (name === "summary") loadSummary();
  if (name === "settings") { loadStatus(); }
}

document.querySelectorAll(".nav button").forEach((button) => {
  button.addEventListener("click", () => switchView(button.dataset.view));
});

document.querySelectorAll("#spoolTabs .tab").forEach((button) => {
  button.addEventListener("click", () => switchSpoolTab(button.dataset.tab));
});

/* ── 目录候选：品牌 / 外观 ─────────────────────────────── */
/** 外观关键词 -> 规范名。必须与后端 catalog._FINISH_KEYWORDS 一致，
 *  否则「颜色名自动预填外观」在前后端会给出不同的结果。
 *  顺序敏感：丝绸在哑光前（「丝绸哑光」算丝绸）、半透在透明前（「半透明」算半透）。 */
const FINISH_KEYWORDS = [
  ["丝绸", "丝绸"], ["silk", "丝绸"], ["丝滑", "丝绸"], ["丝光", "丝绸"],
  ["哑光", "哑光"], ["磨砂", "磨砂"], ["matte", "哑光"], ["matt", "哑光"],
  ["珠光", "珠光"], ["金属", "金属"], ["metallic", "金属"],
  ["夜光", "夜光"], ["glow", "夜光"], ["luminous", "夜光"],
  ["半透", "半透"], ["translucent", "半透"],
  ["透明", "透明"], ["clear", "透明"],
  ["渐变", "渐变"], ["rainbow", "渐变"], ["gradient", "渐变"],
  ["双色", "双色"], ["twotone", "双色"],
  ["木纹", "木纹"], ["wood", "木纹"],
  ["碳纤", "碳纤"], ["carbon", "碳纤"],
  ["亮面", "亮面"], ["gloss", "亮面"],
];

/** 从颜色名里猜外观（「哑光黑」→ 哑光）。用于预填，不覆盖用户已填的值。 */
function inferFinish(text) {
  const s = String(text || "").toLowerCase();
  for (const [keyword, finish] of FINISH_KEYWORDS) {
    if (s.includes(keyword)) return finish;
  }
  return "普通";
}

/** 色卡系列名里带的外观信息（「PLA 哑光」→ 哑光、「PLA 丝绸」→ 丝绸）。
 *  系列名**没写**外观时返回空串，而不是「普通」——「猜不出」和「确定是普通」是两回事：
 *  点「PLA 哑光」色卡里的颜色应该把外观设成哑光；点普通「PLA」色卡里的颜色
 *  则**不该**把用户已经选好的丝绸/哑光改回普通（那会变成另一种「选了又被改掉」）。 */
function finishFromSeries(series) {
  const hit = inferFinish(series || "");
  return hit === "普通" ? "" : hit;
}

/** 品牌候选：目录预设 + 库里实际用过的品牌（历史品牌与自定义品牌也要能筛）。 */
function brandChoices(extra) {
  const preset = (S.catalog.brands || []).slice();
  const pool = S.spools.map((s) => s.brand).filter(Boolean);
  if (extra) pool.push(extra);
  const rest = [...new Set(pool)].filter((b) => !preset.includes(b))
    .sort((a, b) => String(a).localeCompare(String(b), "zh"));
  return preset.concat(rest);
}

/** 外观候选：目录预设 + 库里实际用过的（含用户自填的写法）。 */
function finishChoices(extra) {
  const preset = (S.catalog.finishes || []).slice();
  const pool = S.spools.map((s) => s.finish).filter(Boolean);
  if (extra) pool.push(extra);
  return preset.concat([...new Set(pool)].filter((f) => !preset.includes(f)));
}

/** 重填一个下拉：保留用户当前选中的值，且不重复追加（loadCatalog 可能被多次调用）。 */
function refillSelect(id, values, placeholder) {
  const sel = document.getElementById(id);
  if (!sel) return;
  const current = sel.value;
  sel.innerHTML = (placeholder ? `<option value="">${esc(placeholder)}</option>` : "")
    + values.map((v) => `<option value="${esc(v)}">${esc(v)}</option>`).join("");
  if (current && values.includes(current)) sel.value = current;
}

/* ── 数据加载 ──────────────────────────────────────────── */
async function loadCatalog() {
  try {
    S.catalog = await api("/api/catalog");
    refillSelect("spoolMaterial", S.catalog.materials, "全部材料");
    refillSelect("spoolBrand", S.catalog.brands, "全部品牌");
    refillSelect("spoolFinish", S.catalog.finishes, "全部外观");
  } catch (err) { /* 目录加载失败不阻塞主界面 */ }
}

/** 库存页筛选项跟着实际数据走：老数据里的品牌/外观不在预设里也要能筛出来。 */
function syncFilterOptions() {
  refillSelect("spoolBrand", brandChoices(), "全部品牌");
  refillSelect("spoolFinish", finishChoices(), "全部外观");
}

/** 客户端时区（UTC 以东的分钟数）。后端按它切「今天 / 本周」的边界。 */
function tzMinutes() {
  return -new Date().getTimezoneOffset();
}

async function loadStatus() {
  S.status = await api("/api/system/status");
  try { S.stats = await api(`/api/stats?tz_minutes=${tzMinutes()}`); } catch (err) { S.stats = null; }
  // 仪表盘的三栏活动面板要用到在用料盘，顺手取一份不带筛选的
  try { S.dashSpools = (await api("/api/spools?archived=false")).spools || []; }
  catch (err) { /* 非致命：面板会退化成空列表 */ }
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
  // 归档的与在用的都要拿到：状态标签页里有「已归档」，一次取回后在本地筛选，
  // 搜索框、价格区间这类交互就不用每次打服务器了。
  const [live, archived] = await Promise.all([
    api("/api/spools?archived=false"),
    api("/api/spools?archived=true"),
  ]);
  S.spools = [...(live.spools || []), ...(archived.spools || [])];
  renderSpools();
}

async function loadJobs() {
  const status = document.getElementById("jobFilter").value;
  const data = await api("/api/jobs?limit=120" + (status ? "&status=" + status : ""));
  S.jobs = data.jobs || [];
  renderJobs();
}

/* ── 仪表盘 ────────────────────────────────────────────── */
/** 本周三张卡。版式照官方 App：标题在左上、图标在右上、大号数值 + 单位、底部一行说明。 */
function renderWeekCards() {
  const host = document.getElementById("weekStats");
  if (!host) return;
  const st = S.stats || {};
  const week = st.week;
  if (!week) { host.innerHTML = ""; return; }
  const cost = sumRecentDays(st.by_day_cost, 7);
  host.innerHTML = `
    <div class="stat big"><span class="ico">${ICO.clock}</span>
      <div class="label">本周打印时长</div>
      <div class="value">${(Number(week.print_hours) || 0).toFixed(1)}<small> h</small></div>
      <div class="sub">七日内累计任务耗时${week.job_count ? ` · 共 ${week.job_count} 个任务` : ""}</div></div>
    <div class="stat big"><span class="ico">${ICO.printer}</span>
      <div class="label">本周成功打印</div>
      <div class="value">${week.success_count || 0}<small> 次</small></div>
      <div class="sub">七日内正常完成次数</div></div>
    <div class="stat big"><span class="ico">${ICO.weight}</span>
      <div class="label">本周耗材消耗</div>
      <div class="value">${(Number(week.used_g) || 0).toFixed(1)}<small> g</small></div>
      <div class="sub">七日内累计净重消耗${cost > 0 ? ` · 约 ¥${cost.toFixed(2)}` : ""}</div></div>`;
}

function renderDashboard() {
  if (!S.status) return;
  const stats = S.status.stats || {};
  const st = S.stats || {};
  const priceTotal = st.price_total != null ? st.price_total : (stats.price_total || 0);
  const stockValue = st.stock_value != null ? st.stock_value : (stats.stock_value || 0);
  const printCost = st.print_cost_total != null ? st.print_cost_total : 0;
  // 本周口径优先用后端的 week 块（它按客户端时区切自然日）；
  // 老版本接口没有 week 时退回本地按日求和。
  const week = st.week || null;
  const weekUsed = week ? Number(week.used_g) || 0 : sumRecentDays(st.by_day, 7);
  const weekCost = sumRecentDays(st.by_day_cost, 7);

  renderWeekCards();

  document.getElementById("dashStats").innerHTML = `
    <div class="stat"><span class="ico">${ICO.spool}</span>
      <div class="label">在用料盘</div>
      <div class="value">${stats.spool_count || 0}<small> 盘</small></div>
      <div class="sub">已归档 ${stats.archived_count || 0} 盘</div></div>
    <div class="stat"><span class="ico">${ICO.weight}</span>
      <div class="label">库存余量</div>
      <div class="value">${(stats.remaining_total || 0).toFixed(0)}<small> g</small></div>
      <div class="sub">近 7 天消耗 ${weekUsed.toFixed(0)} g</div></div>
    <div class="stat"><span class="ico">${ICO.alert}</span>
      <div class="label">余量不足</div>
      <div class="value">${stats.low_count || 0}<small> 盘</small></div>
      <div class="sub">低于 100 g 自动标红</div></div>
    <div class="stat accent"><span class="ico">${ICO.coins}</span>
      <div class="label">耗材总价值</div>
      <div class="value">¥${priceTotal.toFixed(2)}</div>
      <div class="sub">库存余值 ¥${stockValue.toFixed(2)}</div></div>
    <div class="stat accent"><span class="ico">${ICO.coins}</span>
      <div class="label">累计打印耗材费</div>
      <div class="value">¥${printCost.toFixed(2)}</div>
      <div class="sub">近 7 天 ¥${weekCost.toFixed(2)}</div></div>
    <div class="stat"><span class="ico">${ICO.clock}</span>
      <div class="label">待结算任务</div>
      <div class="value">${(S.status.pending_jobs || []).length}<small> 个</small></div>
      <div class="sub">打印结束后自动扣重</div></div>`;

  const printers = S.status.printers || [];
  const host = document.getElementById("printerCards");
  const printerCount = document.getElementById("printerCount");
  if (printerCount) printerCount.textContent = printers.length ? `共 ${printers.length} 台` : "";
  if (!printers.length) {
    host.innerHTML = `<div class="card"><div class="empty-state">
      还没有打印机。到「设置」页绑定拓竹账号后同步设备即可。<br />
      <span class="small">想先看看效果？用 BAMBU_MOCK=1 启动可以跑模拟数据。</span></div></div>`;
  } else {
    host.innerHTML = printers.map(renderPrinterCard).join("");
  }

  renderDashPanels();

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

/** 统计接口的 by_day / by_day_cost 是 {日期: 数值}，求最近 N 天之和。 */
function sumRecentDays(byDay, days) {
  if (!byDay) return 0;
  const cutoff = new Date();
  cutoff.setHours(0, 0, 0, 0);
  cutoff.setDate(cutoff.getDate() - (days - 1));
  let sum = 0;
  Object.keys(byDay).forEach((key) => {
    const day = new Date(key + "T00:00:00");
    if (!isNaN(day) && day >= cutoff) sum += Number(byDay[key]) || 0;
  });
  return sum;
}

/** 最近使用 / 最近添加 / 库存不足 三栏。数据全部来自在用料盘清单。 */
function renderDashPanels() {
  const host = document.getElementById("dashPanels");
  if (!host) return;
  const spools = (S.dashSpools && S.dashSpools.length) ? S.dashSpools : S.spools;

  const recent = spools.filter((s) => s.last_used_at)
    .sort((a, b) => (a.last_used_at < b.last_used_at ? 1 : -1)).slice(0, 6);
  const added = spools.slice()
    .sort((a, b) => (a.created_at < b.created_at ? 1 : -1)).slice(0, 6);
  const low = spools.filter((s) => s.is_low)
    .sort((a, b) => a.remaining_weight - b.remaining_weight).slice(0, 6);

  host.innerHTML = [
    panelCard("最近使用", ICO.clock, recent,
      (s) => [ `最后 ${fmtTime(s.last_used_at)}`, s.location || "未指定位置" ],
      (s) => `${s.remaining_weight.toFixed(0)} g`),
    panelCard("最近添加", ICO.spool, added,
      (s) => [ fmtTime(s.created_at), `${s.material || "—"} · 皮重 ${(s.spool_weight || 0).toFixed(0)} g` ],
      (s) => `${s.remaining_weight.toFixed(0)} g`),
    panelCard("库存不足", ICO.alert, low,
      (s) => [ `${s.material || "—"} · ${s.location || "未指定位置"}`, "建议补货或换盘" ],
      (s) => `<b style="color:var(--red)">${s.remaining_weight.toFixed(1)} g</b>`),
  ].join("");
}

function panelCard(title, icon, spools, metaOf, valueOf) {
  const body = spools.length
    ? spools.map((s) => {
        const [line1, line2] = metaOf(s);
        return `<div class="panel-item" style="cursor:pointer" onclick="openSpoolDetail(${s.id})">
          <span class="panel-ico"><span class="mat-dot" style="width:12px;height:12px;background:${esc(s.color_hex)}"></span></span>
          <div class="panel-main">
            <div class="panel-name">${esc(s.name)}</div>
            <div class="panel-meta">${esc(line1)}${line2 ? " · " + esc(line2) : ""}</div>
          </div>
          <div class="panel-val">${valueOf(s)}</div>
        </div>`;
      }).join("")
    : '<div class="panel-meta" style="padding:14px 0">暂无数据</div>';
  return `<div class="panel">
    <div class="panel-head">${icon}<span>${esc(title)}</span><span class="spacer"></span>
      <span class="count">${spools.length}</span></div>
    ${body}
  </div>`;
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

/* ── 打印机面板（Mars Printer Hub 风格） ─────────────────
   左列：机器示意图 + 打印状态 / 温度属性 / 风扇状态
   右列：AMS / AMS HT / 外挂料盘的槽位卡片（竖直料条）
   ─────────────────────────────────────────────────────── */

/** 风扇通道：[state.fans 的键, 中文名, 是否必须显示]。
 *
 *  P2S / X2 直接照抄拓竹官方 App（Bambu Handy / Studio）与打印机屏幕
 *  「空调系统」页的四行与用词：部件 / 右(辅助) / 左(辅助) / 外排。
 *  取值来源（详见 app/core/status.py 的注释）：
 *   - 部件     cooling_fan_speed（工具头前盖组件里那台，M106 P1）
 *   - 右(辅助) 自适应风道切换组件自带风扇，装在腔室右侧（device.airduct
 *              parts[id=16]，M106 P2）。P2S 真机的 big_fan1_speed 恒为 0，
 *              所以后端把 airduct 那一路并进 aux，兜底才用 big_fan1。
 *   - 左(辅助) 选配的 12W 左侧辅助风扇（device.airduct parts[id=160]，M106 P10）
 *   - 外排     选配的外排风扇套件（自带控制板并入空调系统；认不出部件就退回
 *              big_fan2 档位）
 *  左(辅助) / 外排 是选配件，没装就是 null → 界面写「未安装」，不假装成 0%。
 *  热端风扇官方不列在这一页（自动控制），所以这里不显示。
 *
 *  X1 / P1 / A1 / H2 等机型没有自适应风道组件，沿用「腔体风扇」那套命名。 */
function fanChannels(printer) {
  const model = String((printer && printer.model) || "").toUpperCase();
  const airduct = model.startsWith("P2") || model.startsWith("X2");
  if (airduct) {
    // 对齐拓竹官方 App / 打印机屏幕「空调系统」页的 4 行，顺序也照抄：
    //   部件 → 右(辅助) → 左(辅助) → 外排
    // 左(辅助) 与 外排 是选配件，没装时值为 null，界面显示「未安装」而不是 0%。
    // 热端风扇官方不列在这一页（自动控制），所以这里不显示。
    return [
      ["cooling", "部件", true],
      ["aux", "右(辅助)", true],
      ["secondary", "左(辅助)", true],
      ["exhaust", "外排", true],
    ];
  }
  return [
    ["cooling", "部件冷却风扇", true],
    ["aux", "辅助部件冷却风扇", true],
    ["chamber", "腔体风扇", true],
    ["heatbreak", "热端风扇", true],
  ];
}

/** #rrggbb → rgba(r,g,b,alpha)。解析失败退回中性灰。 */
function tint(hex, alpha) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
  if (!m) return `rgba(15, 23, 42, ${alpha})`;
  const n = parseInt(m[1], 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}

/** 料条该画多高（百分比），以及这个高度是否可信。
 *
 *  优先级：本系统台账的实测余重 > 机器上报的余重（克） > 机器上报的余量百分比。
 *  都没有就返回 null，界面把料条压暗表示「量未知」——
 *  以前不论剩多少都按满格画，用户明确反馈「不要耗材一直是满的」。
 *
 *  满盘容量取料盘的 initial_weight（默认 1000g），外挂/未绑定槽位退回机器的
 *  tray_weight 标称值。返回值夹到 [MIN_FILL, 100]：快用完的盘也要留一条能看见的边，
 *  否则用户会以为是空槽。 */
const MIN_FILL_PCT = 7;
function filFill(spool, tray) {
  const clampPct = (v) => Math.max(MIN_FILL_PCT, Math.min(100, v));
  // ⚠️ 不能用 Number(x)：Number(null) 是 0、Number("") 也是 0，会把「机器没上报
  // 这个字段」误判成「余重就是 0 克」，于是料条被画成一小条（known 还是 true），
  // 「未知」状态就永远不会出现。所以这里必须区分「没有值」和「值就是 0」。
  const num = (v) => {
    if (v === null || v === undefined || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };
  if (spool) {
    const cap = num(spool.initial_weight) || 1000;
    const rem = num(spool.remaining_weight);
    if (rem !== null && cap > 0) return { pct: clampPct((rem / cap) * 100), known: true };
  }
  const trayCap = num(tray && tray.tray_weight) || 1000;
  const grams = num(tray && tray.remain_weight_g);
  if (grams !== null && trayCap > 0) return { pct: clampPct((grams / trayCap) * 100), known: true };
  const remain = num(tray && tray.remain);
  if (remain !== null && remain >= 0) return { pct: clampPct(remain), known: true };
  return { pct: 100, known: false };
}

/** 把耗材色压暗，用作色条上克重标签的底色。 */
function shade(hex, factor) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
  if (!m) return "#334155";
  const n = parseInt(m[1], 16);
  const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255]
    .map((v) => Math.max(0, Math.min(255, Math.round(v * factor))));
  return `rgb(${ch[0]}, ${ch[1]}, ${ch[2]})`;
}

/** 按相对亮度挑一个能看清的字色。 */
function inkOn(hex) {
  const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
  if (!m) return "#ffffff";
  const n = parseInt(m[1], 16);
  const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  return (r * 299 + g * 587 + b * 114) / 1000 > 160 ? "#111827" : "#ffffff";
}

/** 拓竹湿度有两种口径：普通 AMS 上报 0-5 档位，AMS HT 上报百分比。 */
function humidityText(value) {
  if (value === undefined || value === null || value === "") return "湿度 —";
  const num = Number(value);
  if (Number.isNaN(num)) return `湿度 ${esc(value)}`;
  if (num <= 5) {
    const desc = num <= 2 ? "干燥" : num <= 3 ? "正常" : "偏潮";
    return `湿度 ${num} 级 · ${desc}`;
  }
  return `湿度 ${Math.round(num)}%`;
}

/** 槽位编号：单元字母 + 槽位序号，例如 A1、B3。 */
function slotCode(unit, tray) {
  const letter = String((unit && unit.name) || "AMS").split(" ").pop();
  return `${letter}${tray.tray_id + 1}`;
}

/** ams_id → 展示名。别直接用 ams_id + 1，AMS HT 的 128 会变成「129」。 */
function amsSlotLabel(amsId, trayId) {
  if (amsId < 0) return "外挂料盘";
  let name;
  if (amsId >= 128 && amsId <= 131) name = `HT ${"ABCD"[amsId - 128]}`;
  else if (amsId >= 0 && amsId < 4) name = `AMS ${"ABCD"[amsId]}`;
  else name = `AMS ${amsId}`;
  return `${name} 槽位 ${trayId + 1}`;
}

/** 槽位右上角的状态标记。 */
function trayFlag(occupied, bound, active) {
  if (active) return '<span class="tray-flag live" title="当前使用中"></span>';
  if (!occupied) return '<span class="tray-flag off" title="空槽位"></span>';
  if (bound) return '<span class="tray-flag ok" title="已绑定本系统料盘"></span>';
  return '<span class="tray-flag warn" title="机器有料，但还没绑定本系统料盘"></span>';
}

/** 机型 -> 真机照片 URL。
 *
 *  表由后端扫 app/static/printer/ 目录得到（/api/system/status 的 printer_images），
 *  所以加一台机器只要放一张 <机型>.jpg，不用改代码。没配照片的机型不在表里。
 */
function printerPhoto(model, map) {
  const table = map || (S.status && S.status.printer_images) || {};
  const key = String(model || "").trim().toUpperCase();
  return table[key] || "";
}

/** P2S 外形示意图：纯内联 SVG，不依赖外部图片，离线也能显示。
 *  现在它退居兜底 —— 有真机照片时用照片（见 printerArt）。 */
function printerArtSVG(model, uid) {
  const b = `pab-${uid}`, g = `pag-${uid}`;
  return `<svg class="printer-art" viewBox="0 0 230 300" preserveAspectRatio="xMidYMid meet" aria-hidden="true">
    <defs>
      <linearGradient id="${b}" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="#f5f7fa"/><stop offset=".42" stop-color="#e3e8ef"/>
        <stop offset="1" stop-color="#c6cdd7"/>
      </linearGradient>
      <linearGradient id="${g}" x1="0" y1="0" x2=".7" y2="1">
        <stop offset="0" stop-color="#343c47"/><stop offset=".45" stop-color="#1b2129"/>
        <stop offset="1" stop-color="#27303a"/>
      </linearGradient>
    </defs>
    <rect x="10" y="8" width="210" height="284" rx="15" fill="url(#${b})" stroke="#b7c0cb" stroke-width="1.2"/>
    <rect x="10" y="8" width="210" height="36" rx="15" fill="#eaeef3"/>
    <rect x="10" y="32" width="210" height="12" fill="#eaeef3"/>
    <line x1="12" y1="44" x2="218" y2="44" stroke="#d3dae3" stroke-width="1"/>
    <rect x="22" y="15" width="58" height="27" rx="5" fill="#1a1e24"/>
    <rect x="26" y="19" width="50" height="19" rx="3" fill="#2c3844"/>
    <rect x="30" y="24" width="26" height="3" rx="1.5" fill="#5c6b7a"/>
    <circle cx="69" cy="28.5" r="3" fill="#4a90d9" opacity=".9"/>
    <text x="205" y="32" text-anchor="end" font-size="14" font-weight="600"
          fill="#7d8794" font-family="system-ui">${model}</text>
    <rect x="20" y="54" width="190" height="228" rx="10" fill="url(#${g})"/>
    <rect x="32" y="104" width="166" height="10" rx="3" fill="#4e5762"/>
    <rect x="120" y="92" width="32" height="34" rx="6" fill="#3b434e"/>
    <rect x="126" y="100" width="20" height="8" rx="2" fill="#5a636f"/>
    <rect x="36" y="202" width="158" height="11" rx="3" fill="#616b77"/>
    <rect x="36" y="213" width="158" height="32" fill="#3d454f"/>
    <rect x="36" y="245" width="158" height="6" fill="#333a43"/>
    <rect x="13" y="150" width="8" height="50" rx="4" fill="#aab3bf"/>
    <rect x="14.5" y="158" width="5" height="34" rx="2.5" fill="#c4ccd6"/>
    <rect x="34" y="284" width="26" height="8" rx="3" fill="#9aa4b0"/>
    <rect x="170" y="284" width="26" height="8" rx="3" fill="#9aa4b0"/>
  </svg>`;
}

/** 机器示意图：有该机型的真机照片就用照片，否则退回内联 SVG。
 *
 *  照片和 SVG 一起渲染，靠 .art-broken 切换 —— onerror 里的兜底不能省：
 *  机型拼错、照片被删、文件损坏时，界面不能给用户留一块空白，
 *  这一点在「用户自己往 printer/ 里塞图」的用法下尤其容易踩到。
 */
function printerArt(model, uid) {
  const svg = printerArtSVG(model, uid);
  const photo = printerPhoto(model);
  if (!photo) return svg;
  return `<span class="printer-art-wrap">
    <img class="printer-art printer-photo" src="${esc(photo)}"
         alt="${esc(model)} 真机照片" decoding="async"
         onerror="this.parentNode.classList.add('art-broken')" />
    ${svg}
  </span>`;
}

function fmtTemp(value, target) {
  const current = `${(Number(value) || 0).toFixed(0)}°C`;
  return target ? `${current} / ${Number(target).toFixed(0)}°C` : current;
}

/** 机器示意图上的浮标温度（喷嘴 / 仓温 / 热床），排布对齐官方 App。
 *  读数为 0 的通道（没通电或没这个传感器）直接不画，免得挂一串 0°C。 */
function renderArtChips(state) {
  const rows = [
    ["nozzle", "喷嘴", Number(state.nozzle_temper) || 0, fmtTemp(state.nozzle_temper, state.nozzle_target)],
    ["chamber", "仓温", Number(state.chamber_temper) || 0, fmtTemp(state.chamber_temper, state.chamber_target)],
    ["bed", "热床", Number(state.bed_temper) || 0, fmtTemp(state.bed_temper, state.bed_target)],
  ].filter(([, , value]) => value > 0);
  if (!rows.length) return "";
  return `<div class="art-chips">${rows.map(([cls, label, , text]) =>
    `<span class="art-chip ${cls}">${ICO.thermo}<b>${esc(text)}</b><i>${esc(label)}</i></span>`).join("")}</div>`;
}

/** 打印状态 + 层数 + 进度条。 */
function renderRunCard(state) {
  const progCls = state.gcode_state === "FAILED" ? "failed"
    : state.gcode_state === "FINISH" ? "done"
    : state.gcode_state === "PAUSE" ? "paused" : "";
  const layers = state.total_layer_num
    ? `${state.layer_num || 0} / ${state.total_layer_num}`
    : "—";
  const stage = [state.stage_label, state.remaining_minutes ? `剩余 ${state.remaining_minutes} 分钟` : ""]
    .filter(Boolean).join(" · ");
  const hms = (state.hms && state.hms.length)
    ? `<div class="row" style="margin-top:10px;gap:6px">
         ${state.hms.map((h) => `<span class="tag red">${esc(h.module)} · ${esc(h.severity)}</span>`).join("")}
       </div>`
    : "";

  return `<div class="pcard">
    <div class="pcard-head">${ICO.printer}<span>打印状态</span>
      <span class="spacer"></span><span class="pcard-k">打印层数</span></div>
    <div class="dual">
      <div>
        <div class="kv-value xl">${esc(state.state_label || "—")}</div>
        <div class="kv-label">${esc(stage || "—")}</div>
      </div>
      <div class="right">
        <div class="kv-value xl">${esc(layers)}</div>
        <div class="kv-label">${esc(state.subtask_name || "无任务")}</div>
      </div>
    </div>
    <div class="pcard-head tight">${ICO.layer}<span>打印进度</span>
      <span class="spacer"></span><b class="kv-value">${state.progress || 0}%</b></div>
    <div class="progress ${progCls}"><div style="width:${Math.max(0, Math.min(100, state.progress || 0))}%"></div></div>
    ${hms}
  </div>`;
}

/** 温度属性：热床 / 仓温 / 喷嘴 / 信号。 */
function renderTempCard(state) {
  const chamber = Number(state.chamber_temper) || 0;
  const items = [
    ["热床", fmtTemp(state.bed_temper, state.bed_target)],
    ["仓温", chamber ? fmtTemp(chamber, state.chamber_target) : "—"],
    ["喷嘴", fmtTemp(state.nozzle_temper, state.nozzle_target)],
    ["信号", state.wifi_signal || "—"],
  ];
  return `<div class="pcard">
    <div class="pcard-head">${ICO.thermo}<span>温度属性</span></div>
    <div class="kv-grid">${items.map(([label, value]) => `
      <div class="kv"><div class="kv-label">${esc(label)}</div>
        <div class="kv-value">${esc(value)}</div></div>`).join("")}
    </div>
  </div>`;
}

/** 风扇状态：每条通道一根细进度条。值是后端换算好的百分比（原始 0-15 档位在解析层已经换算）。
 *
 *  值为 null 表示机器没装这一件（左侧辅助风扇 / 外排风扇都是选配件），
 *  这时不画进度条，直接写「未安装」—— 画成 0% 会让人以为是风扇停了。
 *
 *  这张卡排在右列最后，并且会撑满剩余高度（.pcard.grow）：右列（AMS）通常比
 *  左列（照片 + 打印状态 + 温度）矮，不撑满的话右下角会空出一大块。 */
function renderFanCard(state, printer) {
  const fans = state.fans || {};
  const rows = fanChannels(printer).filter(([key, , required]) => required || fans[key] != null);
  if (!rows.length) return "";
  return `<div class="pcard grow fan-card">
    <div class="pcard-head">${ICO.fan}<span>风扇状态</span></div>
    <div class="fan-rows">${rows.map(([key, label]) => {
      if (fans[key] == null) {
        return `<div class="fan-row missing">
          <span class="fan-name">${esc(label)}</span>
          <span class="fan-bar"></span>
          <span class="fan-val">未安装</span>
        </div>`;
      }
      const value = Math.max(0, Math.min(100, Number(fans[key]) || 0));
      return `<div class="fan-row">
        <span class="fan-name">${esc(label)}</span>
        <span class="fan-bar"><span style="width:${value}%"></span></span>
        <span class="fan-val">${value}%</span>
      </div>`;
    }).join("")}</div>
  </div>`;
}

/** 右列内容：所有 AMS / AMS HT 单元 + 外挂料盘。外层 .printer-col 由调用方给。 */
function renderUnits(state, printer) {
  const cards = (state.ams || []).map((unit) => renderUnitCard(unit, printer)).join("");
  const ext = renderExternalCard(state.external_spool, printer);
  const body = cards + ext;
  return body || `<div class="pcard">
      <div class="empty-state">这台机器没有上报 AMS 单元。</div></div>`;
}

function renderUnitCard(unit, printer) {
  const isHt = unit.kind === "ht";
  const trays = (unit.trays || []);
  const active = trays.find((t) => t.is_active);
  const letter = String(unit.name || "AMS").split(" ").pop();
  const usage = active ? `${letter}${active.tray_id + 1}` : "无";
  const temp = Number(unit.temp) ? `${Number(unit.temp).toFixed(0)}°C` : "—";

  return `<div class="pcard unit-card">
    <div class="pcard-head">
      <b>${esc(unit.name || "AMS")}</b>
      ${unit.model ? `<span class="tag ${isHt ? "teal" : ""}">${esc(unit.model)}</span>` : ""}
      <span class="spacer"></span>
      <span class="metric">${ICO.thermo}${esc(temp)}</span>
      <span class="metric">${ICO.drop}${humidityText(unit.humidity)}</span>
      <span class="metric">使用 ${esc(usage)}</span>
    </div>
    <div class="tray-grid ${isHt ? "single" : ""}">${trays.map((tray) => renderTrayCard(unit, tray, printer)).join("")}</div>
  </div>`;
}

/** 单个槽位：竖直料条 + 克重 + 材料名。 */
function renderTrayCard(unit, tray, printer) {
  const code = slotCode(unit, tray);
  const click = `onclick="openSlotDialog(${printer.id}, ${tray.ams_id}, ${tray.tray_id})"`;
  const binding = (S.bindingMap || {})[`${printer.id}:${tray.ams_id}:${tray.tray_id}`];
  const spool = binding && binding.spool;

  if (!tray.occupied) {
    return `<div class="tray-card empty" ${click}>
      <div class="tray-top"><span class="tray-code">${esc(code)}</span>${trayFlag(false, false, false)}</div>
      <div class="tray-fil empty"><span>空</span></div>
      <div class="fil-name">空</div>
    </div>`;
  }

  const color = (spool && spool.color_hex) || tray.color || "#64748b";
  const grams = spool && spool.remaining_weight != null
    ? `${Number(spool.remaining_weight).toFixed(0)}g`
    : (tray.remain_weight_g != null ? `${Math.round(tray.remain_weight_g)}g` : "");
  const material = spool
    ? (spool.material || spool.name || "未知")
    : (tray.tray_type || tray.label || "未知");
  // 余量不足的料盘，克重标签直接标红，扫一眼就能发现
  const low = !!(spool && spool.is_low);
  const labelBg = low ? "#b42318" : shade(color, 0.78);
  const labelInk = low ? "#ffffff" : inkOn(labelBg);
  const fill = filFill(spool, tray);

  return `<div class="tray-card ${tray.is_active ? "active" : ""} ${spool ? "" : "unbound"}" ${click}>
    <div class="tray-top"><span class="tray-code">${esc(code)}</span>${trayFlag(true, !!spool, !!tray.is_active)}</div>
    <div class="tray-fil">
      <div class="fil-body ${fill.known ? "" : "unknown"}"
           style="background:${esc(color)};height:${fill.pct.toFixed(1)}%"></div>
      ${grams ? `<div class="fil-weight" style="background:${labelBg};color:${labelInk}">${esc(grams)}</div>` : ""}
    </div>
    <div class="fil-name" style="background:${tint(color, 0.16)}">${esc(material)}</div>
  </div>`;
}

/** 外挂料盘（没有 AMS 时挂在机器外面的那一路）。 */
function renderExternalCard(ext, printer) {
  if (!ext) return "";
  const occupied = !!ext.occupied;
  const color = ext.color || "#64748b";
  const grams = ext.remain_weight_g != null ? `${Math.round(ext.remain_weight_g)}g` : "";
  const material = occupied ? (ext.tray_type || ext.label || "未知") : "空";
  const label = shade(color, 0.78);
  // 外挂那一路的绑定键就是 ams_id=-1（与 openSlotDialog 用的口径一致）
  const boundSpool = ((S.bindingMap || {})[`${printer.id}:-1:0`] || {}).spool;
  const fill = filFill(boundSpool, ext);

  return `<div class="pcard unit-card">
    <div class="pcard-head"><b>外挂料盘</b>
      <span class="spacer"></span>
      <span class="metric">使用 ${ext.is_active ? "中" : "无"}</span></div>
    <div class="tray-grid single">
      <div class="tray-card ${ext.is_active ? "active" : ""}" onclick="openSlotDialog(${printer.id}, -1, 0)">
        <div class="tray-top"><span class="tray-code">外挂</span>
          ${trayFlag(occupied, occupied, !!ext.is_active)}</div>
        <div class="tray-fil ${occupied ? "" : "empty"}">
          ${occupied
            ? `<div class="fil-body ${fill.known ? "" : "unknown"}"
                 style="background:${esc(color)};height:${fill.pct.toFixed(1)}%"></div>`
            : "<span>空</span>"}
          ${occupied && grams ? `<div class="fil-weight" style="background:${label};color:${inkOn(label)}">${esc(grams)}</div>` : ""}
        </div>
        <div class="fil-name" style="background:${tint(color, 0.16)}">${esc(material)}</div>
      </div>
    </div>
  </div>`;
}

function renderPrinterCard(entry) {
  const p = entry.printer;
  const state = entry.state;
  const online = (p.online || state) ? "ok" : "bad";

  const bar = `<div class="printer-bar">
    <span class="dot ${online}"></span>
    <b>${esc(p.name || p.serial)}</b>
    <span class="tag">${esc(p.model || "未知机型")}</span>
    <span class="small muted">编号 ${esc((p.serial || "").slice(-6))}</span>
    ${state ? stateTag(state) : ""}
    <span class="spacer"></span>
    ${state ? `<span class="small muted">更新于 ${esc(fmtTime(state.updated_at))}</span>` : ""}
    <button class="sm" onclick="requestPushall(${p.id})">请求全量状态</button>
  </div>`;

  if (!state) {
    return `<div class="printer-block">${bar}
      <div class="pcard"><div class="empty-state">
        尚未收到状态。若刚登录，稍等十几秒；也可以点右上角「请求全量状态」重新拉取。
      </div></div>
    </div>`;
  }

  return `<div class="printer-block">${bar}
    <div class="printer-layout">
      <div class="printer-col">
        <div class="pcard photo-card">
          <div class="art-wrap">${printerArt(esc(p.model || "P2S"), p.id)}${renderArtChips(state)}</div>
        </div>
        ${renderRunCard(state)}
        ${renderTempCard(state)}
      </div>
      <div class="printer-col">
        ${renderUnits(state, p)}
        ${renderFanCard(state, p)}
      </div>
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

/* ── 料盘状态分类（库存页标签页 与 汇总页概览图 共用同一套口径）─────
 * 两个地方各写一套判定，就会再次出现「概览说 5 盘用完、点进去只剩 2 盘」
 * 这种对不上的现象，所以判定与统计都只留这一个实现。 */

/** 一盘料处于哪种状态。
 *
 *  empty  —— 已经用光（余量 ≤ 0）
 *  unused —— 全新未拆封：没有任何用量、也没装到机器上
 *  in_use —— 其余（用掉一部分，或正装在机器上）
 *
 *  余量必须显式判空：`Number(null) === 0`，字段缺失会被当成「0 克」而误判成
 *  消耗完 —— 老数据或接口漏字段时就会凭空多出一堆「用完的盘」。
 */
function spoolUseState(spool) {
  const remaining = spool.remaining_weight;
  const hasRemaining = remaining !== null && remaining !== undefined && remaining !== "";
  if (hasRemaining && Number(remaining) <= 0) return "empty";
  const used = Number(spool.used_weight) || 0;
  const count = Number(spool.usage_count) || 0;
  const mounted = (spool.slots || []).length > 0;
  if (used <= 0 && count <= 0 && !mounted) return "unused";
  return "in_use";
}

const USE_STATE_META = {
  unused: { label: "未使用", color: "#16a34a", tab: "idle" },
  in_use: { label: "使用中", color: "#2563eb", tab: "inuse" },
  empty: { label: "消耗完", color: "#dc2626", tab: "empty" },
};

/** 按状态点数（只数在库料盘；归档的不参与）。 */
function useStateTally(spools) {
  const out = { unused: 0, in_use: 0, empty: 0, total: 0 };
  (spools || []).forEach((s) => {
    out[spoolUseState(s)] += 1;
    out.total += 1;
  });
  return out;
}

/* ── 价格区间分布 ──────────────────────────────────────── */
/** 固定六档（按反馈定死）：0-10 / 10-20 / 20-30 / 30-40 / 40-50 / 50 以上。
 *  之前按最高价自适应步长，档位名称每次都不一样，看着费劲；
 *  最早最后一档是「40 以上」上不封顶，但 40+ 那一档把 42 元和 200 元的盘混在一起，
 *  看不出「贵的到底多贵」。现在拆成 40-50 与 50 以上，最后一档仍上不封顶。 */
const PRICE_BANDS = [
  { from: 0, to: 10, label: "¥0 - 10" },
  { from: 10, to: 20, label: "¥10 - 20" },
  { from: 20, to: 30, label: "¥20 - 30" },
  { from: 30, to: 40, label: "¥30 - 40" },
  { from: 40, to: 50, label: "¥40 - 50" },
  { from: 50, to: null, label: "¥50 以上" },
];

/** 把料盘按整盘价分进固定六档。
 *
 *  @returns {{buckets: Array, unpriced: number, priced: number}}
 */
function priceBuckets(spools) {
  const priced = (spools || []).filter((s) => (Number(s.price) || 0) > 0);
  const unpriced = (spools || []).length - priced.length;
  if (!priced.length) return { buckets: [], unpriced, priced: 0 };

  const buckets = PRICE_BANDS.map((band) => {
    // 全部档位统一「左开右闭」(from, to]：价格正好等于档位边界时落在**低**的一档。
    // 这样 20 元归「¥10 - 20」、50 元归「¥40 - 50」，相邻两档不会重复计数。
    //
    // 最后一档（to == null）也必须左开：写成 `p >= from` 的话，
    // 50 元会同时落进「¥40 - 50」和「¥50 以上」（实测就是这么漏的，占比之和变成 133%）。
    // 上不封顶只管「没有上界」，不代表「下界闭合」——
    // 所以 50 元算 40-50 档，50.01 元才算「¥50 以上」。
    const hit = priced.filter((s) => {
      const p = Number(s.price) || 0;
      return band.to == null ? p > band.from : (p > band.from && p <= band.to);
    });
    return {
      from: band.from,
      to: band.to,
      label: band.label,
      count: hit.length,
      percent: priced.length ? (hit.length / priced.length) * 100 : 0,
      value: hit.reduce((sum, s) => sum + (Number(s.price) || 0), 0),
    };
  });
  return { buckets, unpriced, priced: priced.length };
}

/* ── 表头排序 ──────────────────────────────────────────── */
function sortSpools(list) {
  const sort = S.spoolSort || { key: "id", dir: "asc" };
  const factor = sort.dir === "desc" ? -1 : 1;
  return list.slice().sort((a, b) => {
    let va = a[sort.key];
    let vb = b[sort.key];
    if (sort.key === "last_used_at") { va = va || ""; vb = vb || ""; }
    else { va = Number(va) || 0; vb = Number(vb) || 0; }
    if (va < vb) return -1 * factor;
    if (va > vb) return 1 * factor;
    return (a.id || 0) - (b.id || 0);   // 同值时按 ID 兜底，顺序稳定
  });
}

/** 点表头切换排序：同一列反方向，换列时「越大越关心」的列默认降序。 */
function toggleSpoolSort(key) {
  const cur = S.spoolSort || { key: "id", dir: "asc" };
  const bigFirst = key === "remaining_weight" || key === "price" || key === "last_used_at";
  S.spoolSort = cur.key === key
    ? { key, dir: cur.dir === "asc" ? "desc" : "asc" }
    : { key, dir: bigFirst ? "desc" : "asc" };
  S.spoolPage = 1;
  renderSpools();
}

/** 可排序表头。箭头是文字而不是图标 —— 表格里用 SVG 会跟表头基线对不齐。 */
function sortHead(key, label, width, align) {
  const cur = S.spoolSort || {};
  const on = cur.key === key;
  const arrow = on ? (cur.dir === "desc" ? "↓" : "↑") : "⇅";
  const style = `width:${width}${align ? `;text-align:${align}` : ""}`;
  return `<th class="sortable${on ? " on" : ""}" style="${style}"
     onclick="toggleSpoolSort('${key}')" title="按${esc(label)}排序">${esc(label)}<span class="sort-arrow">${arrow}</span></th>`;
}

function switchSpoolTab(tab) {
  S.spoolTab = tab;
  S.spoolPage = 1;
  document.querySelectorAll("#spoolTabs .tab").forEach((btn) =>
    btn.classList.toggle("active", btn.dataset.tab === tab));
  renderSpools();
}

function resetSpoolFilters() {
  ["spoolSearch", "spoolPriceMin", "spoolPriceMax", "spoolBrand", "spoolMaterial", "spoolFinish"]
    .forEach((id) => { const el = document.getElementById(id); if (el) el.value = ""; });
  S.spoolPage = 1;
  switchSpoolTab("all");
}

/** 状态标签页 + 筛选条件 → 可见料盘列表（全部在本地算，输入即时响应）。 */
function filteredSpools() {
  const read = (id) => { const el = document.getElementById(id); return el ? el.value : ""; };
  const kw = read("spoolSearch").trim().toLowerCase();
  const brand = read("spoolBrand");
  const material = read("spoolMaterial");
  const finish = read("spoolFinish");
  const minPrice = parseFloat(read("spoolPriceMin"));
  const maxPrice = parseFloat(read("spoolPriceMax"));
  const tab = S.spoolTab || "all";

  const list = S.spools.filter((s) => {
    if (tab === "archived") { if (!s.archived) return false; }
    else if (s.archived) return false;

    // 状态标签页一律走 spoolUseState —— 与耗材汇总页的「库存使用状态」同一个口径，
    // 否则会出现「概览说消耗完 53 盘、点进来只剩 3 盘」这种两边对不上的现象。
    const use = spoolUseState(s);
    if (tab === "inuse" && use !== "in_use") return false;
    if (tab === "idle" && use !== "unused") return false;
    if (tab === "empty" && use !== "empty") return false;
    if (tab === "low" && !s.is_low) return false;

    // 分组口径统一走 SUMMARY_DRILL_FIELDS.norm：汇总页点名字钻过来时，
    // 「未填写 / 普通」这类空值归组也要能筛得到，否则跳过去是空列表。
    if (brand && SUMMARY_DRILL_FIELDS.brand.norm(s) !== brand) return false;
    if (material && SUMMARY_DRILL_FIELDS.material.norm(s) !== material) return false;
    if (finish && SUMMARY_DRILL_FIELDS.finish.norm(s) !== finish) return false;
    if (!isNaN(minPrice) && (s.price || 0) < minPrice) return false;
    if (!isNaN(maxPrice) && (s.price || 0) > maxPrice) return false;
    if (kw) {
      const hay = [s.name, s.brand, s.material, s.color_name, s.location, s.note]
        .join(" ").toLowerCase();
      if (!hay.includes(kw)) return false;
    }
    return true;
  });
  return sortSpools(list);
}

function spoolRowHtml(spool) {
  const hasPrice = (spool.price || 0) > 0;
  const slots = (spool.slots || []).length
    ? spool.slots.map((x) => esc(x.label)).join("、")
    : "";
  const first = spool.first_used_at ? fmtTime(spool.first_used_at) : "";
  const last = spool.last_used_at ? fmtTime(spool.last_used_at) : "";
  const usage = first
    ? `首次 ${first}${last ? `<br>最后 ${last}` : ""}`
    : '<span class="tag">未使用</span>';

  // data-label 给窄屏卡片式布局用（CSS 里 td::before 取 attr(data-label)）：
  // 手机上一行 9 列横向塞不下，会把表格拉出屏幕，所以窄屏改成竖排卡片。
  return `<tr class="clickable" onclick="openSpoolDetail(${spool.id})">
    <td class="small muted" data-label="ID">${spool.id}</td>
    <td class="cell-main">
      <div class="cell-name">
        <span class="swatch" style="background:${esc(spool.color_hex)}"></span>
        <div class="nm">
          <div>${esc(spool.name)}</div>
          <div class="tiny muted">${esc(spool.location || slots || "未装到机器上")}</div>
        </div>
      </div>
    </td>
    <td data-label="类型"><span class="tag">${esc(spool.material)}</span></td>
    <td data-label="颜色"><span class="hex-pill"><i style="background:${esc(spool.color_hex)}"></i>${esc((spool.color_hex || "").toUpperCase())}</span></td>
    <td class="small muted" data-label="外观">${esc(spool.finish || "普通")}</td>
    <td class="num" data-label="价格">${hasPrice ? "¥" + spool.price.toFixed(2) : '<span class="tiny muted">未登记</span>'}</td>
    <td data-label="剩余">
      <div class="bar-cell">
        <div style="display:flex;justify-content:space-between;align-items:baseline;gap:8px">
          <span class="small">${spool.remaining_weight.toFixed(0)} g</span>
          ${spool.is_low ? '<span class="tag amber">偏低</span>'
            : `<span class="tiny muted">${spool.remaining_percent}%</span>`}
        </div>
        <div class="bar" style="margin-top:5px">
          <div class="${spool.is_low ? "low" : ""}" style="width:${Math.max(0, Math.min(100, spool.remaining_percent))}%"></div>
        </div>
      </div>
    </td>
    <td class="tiny muted" data-label="使用时间">${usage}</td>
    <td class="cell-actions" onclick="event.stopPropagation()">
      <div class="row-actions main">
        <button title="查看这盘料的详情与使用记录" onclick="openSpoolDetail(${spool.id})">${ICO.eye}详情</button>
        <button title="绑到 AMS 槽位 / 从槽位上解绑" onclick="openBindSpoolDialog(${spool.id})">${ICO.link}绑定</button>
        <button title="复制这盘料的规格，新增一盘同款" onclick="openCloneSpoolDialog(${spool.id})">${ICO.copy}克隆</button>
      </div>
      <div class="row-actions sub">
        <button title="打印或导出这盘料的标签" onclick="openLabelDialog(${spool.id})">${ICO.tag}标签</button>
        <button title="手动补录消耗" onclick="openUseDialog(${spool.id})">${ICO.pencil}补录</button>
        <button title="按称重校准余量" onclick="openMeasureDialog(${spool.id})">${ICO.scale}校准</button>
        <button class="del" title="删除这盘料" onclick="openDeleteSpoolDialog(${spool.id})">${ICO.trash}删除</button>
      </div>
    </td>
  </tr>`;
}

function renderSpools() {
  const host = document.getElementById("spoolTable");
  syncFilterOptions();
  const list = filteredSpools();
  const size = S.spoolPageSize || 10;
  const pages = Math.max(1, Math.ceil(list.length / size));
  if (S.spoolPage > pages) S.spoolPage = pages;
  const page = S.spoolPage || 1;

  const counter = document.getElementById("spoolCount");
  if (counter) counter.textContent = `${S.spools.filter((s) => !s.archived).length} 盘`;

  if (!list.length) {
    host.innerHTML = `<div class="empty-state">
      没有符合条件的料盘。换个筛选条件，或点右上角「新增料盘」开始记录。</div>`;
    renderTableFoot("spoolFooter", "", 0, 1, size, "spool");
    return;
  }

  const slice = list.slice((page - 1) * size, page * size);
  host.innerHTML = `<table>
    <thead><tr>
      ${sortHead("id", "ID", "66px")}
      <th>料盘</th>
      <th style="width:92px">类型</th>
      <th style="width:140px">颜色</th>
      <th style="width:70px">外观</th>
      ${sortHead("price", "价格", "104px", "right")}
      ${sortHead("remaining_weight", "剩余", "148px")}
      ${sortHead("last_used_at", "使用时间", "168px")}
      <th style="width:214px"></th>
    </tr></thead>
    <tbody>${slice.map(spoolRowHtml).join("")}</tbody></table>`;
  renderTableFoot("spoolFooter", "", list.length, page, size, "spool");
}

function spoolGoPage(page) {
  const size = S.spoolPageSize || 10;
  const pages = Math.max(1, Math.ceil(filteredSpools().length / size));
  S.spoolPage = Math.max(1, Math.min(pages, page));
  renderSpools();
}

function spoolSetSize(value) {
  S.spoolPageSize = parseInt(value, 10) || 10;
  S.spoolPage = 1;
  renderSpools();
}

/* ── 删除料盘 ──────────────────────────────────────────── */
async function openDeleteSpoolDialog(spoolId) {
  // 列表里就有完整对象；直接从详情/深链进来时再补一次请求
  let spool = spoolById(spoolId);
  if (!spool) {
    try { spool = await api(`/api/spools/${spoolId}`); }
    catch (err) { toast(err.message, "err"); return; }
  }
  const count = spool.usage_count != null ? spool.usage_count : (spool.usages || []).length;
  const slots = (spool.slots || []).length || (spool.bindings || []).length;

  openModal("删除料盘", `
    <div class="info-box">
      <div style="font-weight:600;margin-bottom:3px">${esc(spool.name)}</div>
      <div class="muted small">
        余量 ${spool.remaining_weight.toFixed(0)} / ${spool.initial_weight.toFixed(0)} g
        ${(spool.price || 0) > 0 ? ` · 整盘价 ¥${spool.price.toFixed(2)}` : ""}
      </div>
      <div class="muted small">
        使用记录 ${count} 条${slots ? ` · 已装在 ${slots} 个槽位` : ""}
      </div>
    </div>
    ${count ? `<div class="warn-box">
      这盘料有 <b>${count}</b> 条使用流水，删除后这些记录会一起消失，且无法恢复。
      如果只是余量记错了，请改用「校准」；如果是重复录入或参数录错，删除是安全的。
    </div>` : `<p class="hint">这盘料还没有使用记录，删除不会影响任何打印账目。</p>`}
    ${slots ? `<p class="hint">对应的 AMS 槽位会自动解绑，不会留下悬空绑定。</p>` : ""}
  `, `<button onclick="closeModal()">取消</button>
      <button class="danger" onclick="doDeleteSpool(${spoolId}, ${count ? "true" : "false"})">
        ${count ? "确认删除（连带记录）" : "确认删除"}
      </button>`);
}

async function doDeleteSpool(spoolId, force) {
  try {
    const result = await api(
      `/api/spools/${spoolId}?force=${force ? "true" : "false"}`,
      { method: "DELETE" }
    );
    closeModal();
    const extra = result.deleted_usages ? `，清理 ${result.deleted_usages} 条记录` : "";
    toast(`已删除「${result.name || ""}」${extra}`, "ok");
    await loadSpools();
    if (S.status) { await loadStatus(); await loadBindings(); }
  } catch (err) { toast(err.message, "err"); }
}

/* ── 分页脚注（料盘与打印记录共用） ────────────────────── */
function pageNumbers(page, pages) {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1);
  const out = [1];
  const from = Math.max(2, page - 1);
  const to = Math.min(pages - 1, page + 1);
  if (from > 2) out.push("...");
  for (let i = from; i <= to; i++) out.push(i);
  if (to < pages - 1) out.push("...");
  out.push(pages);
  return out;
}

function renderTableFoot(hostId, label, total, page, size, prefix) {
  const host = document.getElementById(hostId);
  if (!host) return;
  const pages = Math.max(1, Math.ceil(total / size) || 1);
  const nav = pageNumbers(page, pages).map((n) => (n === "..."
    ? '<span class="muted" style="padding:0 3px">…</span>'
    : `<button class="${n === page ? "active" : ""}" onclick="${prefix}GoPage(${n})">${n}</button>`)).join("");
  host.innerHTML = `
    <span>${label}</span>
    <span class="row" style="gap:10px">
      <span class="muted">共 ${total} 条记录</span>
      <select onchange="${prefix}SetSize(this.value)" style="width:auto;padding:4px 8px">
        ${[10, 20, 50, 100].map((n) =>
          `<option value="${n}" ${n === size ? "selected" : ""}>${n} / 页</option>`).join("")}
      </select>
      <span class="pager">
        <button onclick="${prefix}GoPage(${page - 1})" ${page <= 1 ? "disabled" : ""}>‹</button>
        ${nav}
        <button onclick="${prefix}GoPage(${page + 1})" ${page >= pages ? "disabled" : ""}>›</button>
      </span>
    </span>`;
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

  const groups = presetGroupsFor(currentBrandValue() || brandEl.value, matEl.value);
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
        // 系列名里的外观（「PLA 哑光」）顺带写进提示：点这里的颜色会把外观设成哑光。
        const seriesFinish = finishFromSeries(g.series);
        const tip = `${c.name}${c.en ? " / " + c.en : ""} ${c.hex}${c.official ? "" : "（色值为近似）"}`
          + (seriesFinish ? ` · 外观：${seriesFinish}` : "");
        return `<button type="button" class="preset-chip${c.official ? "" : " approx"}"
          data-hex="${esc(c.hex)}" data-series="${esc(g.series)}" style="background:${esc(c.hex)}" title="${esc(tip)}"
          onclick="pickPresetColor('${esc(c.hex)}', '${esc(c.name)}', '${esc(g.series)}')"></button>`;
      }).join("")}</div>
    </div>`).join("");

  list.innerHTML = groups.flatMap((g) => g.colors)
    .map((c) => `<option value="${esc(c.name)}" label="${esc(c.en || "")}"></option>`).join("");

  S._presetIndex = index;
  markActivePreset();
}

/** 把推断出来的外观写进表单，**只在当前是空或「普通」时**才写。
 *  用户明确选过丝绸/磨砂就绝不覆盖 —— 出了问题的那一轮，毛病正是「选了又被改掉」。 */
function applyInferredFinish(message, guess) {
  const el = document.getElementById("f_finish");
  if (!el || !guess) return;
  const cur = (el.value || "").trim();
  if (cur && cur !== "普通") return;   // 已有明确选择，保持不动
  if (cur === guess) return;
  el.value = guess;
  setFinishHint(message);
}

/** 点色卡里的颜色。系列名写着外观时（「PLA 哑光」）把外观一起带过去 ——
 *  用户的心智就是「我在哑光色卡里挑的颜色」。自己选过别的外观则保持不动，只提示一声。 */
function applySeriesFinish(series) {
  const guess = finishFromSeries(series);
  if (!guess) return;
  const el = document.getElementById("f_finish");
  const cur = el ? (el.value || "").trim() : "";
  if (cur && cur !== "普通" && cur !== guess) {
    setFinishHint(`这张色卡是「${series}」，外观保持你选的「${cur}」`);
    return;
  }
  applyInferredFinish(`已按色卡「${series}」把外观设为${guess}，可改`, guess);
}

function setFinishHint(text) {
  const el = document.getElementById("finishHint");
  if (!el) return;
  if (text) {
    el.textContent = text;
    el.classList.remove("hidden");
  } else {
    el.textContent = "";
    el.classList.add("hidden");
  }
}

function pickPresetColor(hex, name, series) {
  const nameEl = document.getElementById("f_color_name");
  const hexEl = document.getElementById("f_color_hex");
  if (nameEl) nameEl.value = name;
  if (hexEl) hexEl.value = hex;
  applySeriesFinish(series);
  markActivePreset();
}

function onColorNameInput() {
  const nameEl = document.getElementById("f_color_name");
  const hexEl = document.getElementById("f_color_hex");
  if (!nameEl || !hexEl) return;
  const hit = (S._presetIndex || {})[nameEl.value.trim()];
  if (hit) hexEl.value = hit;
  // 对话框底下的说明写着「颜色名里带哑光/丝绸会自动预填」——以前这句是空头支票
  // （inferFinish 只在单测里被调用过），现在真的接上了。
  const guess = inferFinish(nameEl.value);
  if (guess !== "普通") {
    applyInferredFinish(`颜色名里带了「${guess}」，已预填外观，可改`, guess);
  }
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

function openSpoolDialog(spool, forceNew, clonedFrom) {
  S.dialogSpool = spool || null;
  // forceNew：表单预填了某盘料的参数，但目的是新增（克隆、或图片识色匹配到的色卡）
  const isEdit = !!spool && !forceNew;
  const title = isEdit ? "编辑料盘" : (clonedFrom ? "克隆料盘" : "新增料盘");
  const value = spool || {
    brand: "", material: "", finish: "普通", color_name: "黑色", color_hex: "#1A1A1A",
    spool_weight: 250, initial_weight: 1000, location: "", note: "", name: "",
  };
  const brands = brandChoices(value.brand);
  const presetBrands = S.catalog.preset_brands || [];
  const brandOptions = brands.map((b) =>
    `<option value="${esc(b)}" ${b === value.brand ? "selected" : ""}>${esc(b)}${presetBrands.includes(b) ? "" : "（自定义）"}</option>`).join("");
  const materialOptions = S.catalog.materials.map((m) =>
    `<option value="${esc(m)}" ${m === value.material ? "selected" : ""}>${esc(m)}</option>`).join("");
  // 料盘不在候选里（历史自定义品牌）时默认落到「自定义」那一项
  const customSelected = value.brand && !brands.includes(value.brand) ? " selected" : "";
  const finish = value.finish || "普通";

  openModal(title, `
    ${clonedFrom ? `<div class="info-box">
      <div class="small">克隆自「${esc(clonedFrom)}」—— 规格已带过来，余量按满盘算。
        同一款买了好几盘时，改下位置/余量直接保存就行。</div>
    </div>` : ""}
    <label class="field"><span>品牌</span>
      <select id="f_brand" onchange="onBrandChoice()">${brandOptions}
        <option value="__custom__"${customSelected}>＋ 自定义品牌…</option></select></label>
    <div class="field-row${customSelected ? "" : " hidden"}" id="brandCustomRow">
      <label class="field"><span>自定义品牌名</span>
        <input id="f_brand_custom" value="${customSelected ? esc(value.brand) : ""}"
               placeholder="例如：某某耗材（保存后会自动进品牌下拉）" /></label>
    </div>
    <div class="field-row">
      <label class="field"><span>材料</span><select id="f_material" onchange="renderColorPresets()">${materialOptions}</select></label>
      <label class="field"><span>外观</span>
        <input id="f_finish" list="finishList" value="${esc(finish)}" placeholder="如：丝绸 / 哑光 / 亮面" />
        <datalist id="finishList">${finishChoices(finish).map((f) => `<option value="${esc(f)}">`).join("")}</datalist>
      </label>
    </div>
    <div class="field-row">
      <label class="field"><span>颜色名称</span>
        <input id="f_color_name" list="colorList" value="${esc(value.color_name)}" oninput="onColorNameInput()" />
        <datalist id="colorList">${S.catalog.colors.map((c) => `<option value="${esc(c.name)}">`).join("")}</datalist>
      </label>
      <label class="field"><span>颜色</span>
        <input type="color" id="f_color_hex" value="${esc(value.color_hex)}" style="height:34px;padding:2px" oninput="markActivePreset()" /></label>
    </div>
    <div id="colorPresets"></div>
    <p class="hint hidden" id="finishHint"></p>
    <div class="field-row">
      <label class="field"><span>空盘皮重（g）</span>
        <input type="number" id="f_spool_weight" value="${value.spool_weight}" step="1" /></label>
      <label class="field"><span>满盘净重（g）</span>
        <input type="number" id="f_initial_weight" value="${value.initial_weight}" step="10" /></label>
    </div>
    <div class="field-row">
      <label class="field"><span>当前余量（g）</span>
        <input type="number" id="f_remaining_weight" value="${isEdit ? value.remaining_weight : value.initial_weight}" step="1" /></label>
      <label class="field"><span>整盘价格（¥）</span>
        <input type="number" id="f_price" value="${value.price != null ? value.price : 0}" step="0.01" min="0" placeholder="如 99.9" /></label>
    </div>
    <label class="field"><span>存放位置（可选）</span>
      <input id="f_location" value="${esc(value.location || "")}" placeholder="如：干燥箱 A / 货架第二层" /></label>
    <label class="field"><span>备注（可选）</span><input id="f_note" value="${esc(value.note || "")}" /></label>
    <p class="hint">外观是表面工艺：同一材料同一颜色也可能有普通 / 哑光 / 丝绸几种货，价格不一样，
      所以单独记一列。颜色名里带「哑光」「丝绸」这类词、或从写着外观的色卡（如「PLA 哑光」）
      里点颜色时，会帮你把外观预填上；你自己填过的值不会被覆盖。保存时会原样存下来。</p>
    <p class="hint">不确定皮重？多数塑料盘在 190~250 g 之间。皮重只影响「称重校准」的换算，不影响自动扣重。</p>
    <p class="hint">价格用于统计「耗材总价值」和「每次打印耗费的料材费」：打印费 = 整盘价 ÷ 满盘净重 × 本次用量。留空表示未登记，不计入费用汇总。</p>
  `, `<button onclick="closeModal()">取消</button>
      <button class="primary" onclick="saveSpool(${isEdit ? spool.id : "null"})">保存</button>`);
  renderColorPresets();
}

/** 品牌下拉切到「＋ 自定义品牌…」时露出输入框。 */
function onBrandChoice() {
  const sel = document.getElementById("f_brand");
  const row = document.getElementById("brandCustomRow");
  if (!sel || !row) return;
  const isCustom = sel.value === "__custom__";
  row.classList.toggle("hidden", !isCustom);
  if (isCustom) {
    const input = document.getElementById("f_brand_custom");
    if (input && !input.value) input.focus();
  }
  renderColorPresets();
}

/** 读当前表单里的品牌：选「自定义」时取输入框的值。 */
function currentBrandValue() {
  const sel = document.getElementById("f_brand");
  if (!sel) return "";
  if (sel.value !== "__custom__") return sel.value.trim();
  const input = document.getElementById("f_brand_custom");
  return (input ? input.value : "").trim();
}

async function saveSpool(id) {
  const payload = {
    brand: document.getElementById("f_brand").value.trim(),
    material: document.getElementById("f_material").value.trim(),
    // 外观**必须**在 payload 里。它在 e32a12b 那次「加外观字段」时就漏了：
    // 表单上有输入框、后端也一直在收，中间少了一根线 →
    // 用户选了哑光、存下来还是普通（2026-09-16 反馈）。
    finish: document.getElementById("f_finish").value.trim(),
    color_name: document.getElementById("f_color_name").value.trim() || "黑色",
    color_hex: document.getElementById("f_color_hex").value,
    spool_weight: parseFloat(document.getElementById("f_spool_weight").value) || 0,
    initial_weight: parseFloat(document.getElementById("f_initial_weight").value) || 1000,
    remaining_weight: parseFloat(document.getElementById("f_remaining_weight").value),
    location: document.getElementById("f_location").value.trim(),
    note: document.getElementById("f_note").value.trim(),
    price: parseFloat(document.getElementById("f_price").value) || 0,
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
          <div class="small muted">整盘价 ${(spool.price > 0) ? "¥" + spool.price.toFixed(2) : "—"} ·
            单价 ${(spool.price_per_g > 0) ? "¥" + spool.price_per_g.toFixed(3) + "/g" : "—"} ·
            余值 ${(spool.stock_value > 0) ? "¥" + spool.stock_value.toFixed(2) : "—"}</div>
        </div>
        <span class="spacer"></span>
        <div class="small muted" style="text-align:right">
          ${(spool.bindings || []).map((b) => esc(amsSlotLabel(b.ams_id, b.tray_id))).join("<br>") || "未装载"}
        </div>
      </div>
      <div class="row" style="margin-bottom:14px">
        <button class="sm" onclick="openLabelDialog(${spool.id})">${ICO.tag}打印标签</button>
        <button class="sm" onclick="closeModal();openUseDialog(${spool.id})">手动补录消耗</button>
        <button class="sm" onclick="closeModal();openMeasureDialog(${spool.id})">称重校准</button>
        <button class="sm" onclick="editCurrentSpool(${spool.id})">编辑</button>
        <button class="sm danger" onclick="openDeleteSpoolDialog(${spool.id})">${ICO.trash}删除这盘料</button>
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

/** 克隆一盘料：把「这款耗材」的规格复制出来新增一盘。
 *
 *  带走的：品牌 / 材料 / 外观 / 颜色 / 皮重 / 满盘重 / 单价 / 位置。
 *  不带的：余量（新拆的那盘是满的）、使用记录、RFID、槽位绑定 ——
 *  后三样都是「这一盘」的属性，复制过来就是错的。
 */
function openCloneSpoolDialog(spoolId) {
  const src = spoolById(spoolId);
  if (!src) { toast("找不到这盘料，刷新一下列表", "err"); return; }
  openSpoolDialog({
    brand: src.brand,
    material: src.material,
    finish: src.finish || "普通",
    color_name: src.color_name,
    color_hex: src.color_hex,
    spool_weight: src.spool_weight,
    initial_weight: src.initial_weight,
    price: src.price,
    location: src.location,
    note: src.note,
  }, true, src.name);
}

/* ── 从料盘这一侧管槽位绑定 ──────────────────────────────
 *  原来只有「在仪表盘点槽位 → 从下拉里选料盘」这条单向路径。手里拿着刚拆的
 *  一盘料、想放到某个槽位时，得先在机器面板的一堆小格子里找到那个槽位，
 *  很别扭。这里给反向路径：在这盘料上直接选槽位，能绑、能换、能解绑。 */

function slotKey(entry) {
  return `${entry.printerId}:${entry.amsId}:${entry.trayId}`;
}

/** 把所有打印机上报的槽位摊平成一维（含外挂料盘），供「选槽位」用。
 *
 *  标签用 amsSlotLabel 而不是卡片里的短码（A1）：这里是扁平列表，普通 AMS 的 A1
 *  和 AMS HT 的 A1 会撞在一起，只写「A1」根本分不出是哪一个。
 */
function allSlotEntries() {
  const out = [];
  (S.printers_full || []).forEach((printer) => {
    const state = printer.state || {};
    const printerName = printer.name || printer.serial || `#${printer.id}`;
    (state.ams || []).forEach((unit) => {
      (unit.trays || []).forEach((tray) => {
        const amsId = tray.ams_id != null ? tray.ams_id : unit.ams_id;
        out.push({
          printerId: printer.id,
          printerName,
          amsId,
          trayId: tray.tray_id,
          occupied: !!tray.occupied,
          label: `${printerName} · ${amsSlotLabel(amsId, tray.tray_id)}`,
          material: tray.tray_type || tray.label || "",
          color: tray.color || "",
        });
      });
    });
    const ext = state.external_spool;
    if (ext) {
      out.push({
        printerId: printer.id,
        printerName,
        amsId: -1,
        trayId: 0,
        occupied: !!ext.occupied,
        label: `${printerName} · 外挂料盘`,
        material: ext.tray_type || ext.label || "",
        color: ext.color || "",
      });
    }
  });
  return out;
}

function bindSlotRowHtml(slot, spoolId) {
  const binding = (S.bindingMap || {})[slotKey(slot)];
  const boundId = binding ? binding.spool_id : null;
  const isMine = boundId === spoolId;
  const other = boundId && !isMine ? binding.spool : null;
  const dot = `<span class="mat-dot" style="width:12px;height:12px;background:${esc(slot.color || "#cbd5e1")}"></span>`;
  const tag = isMine ? '<span class="tag teal">本盘</span>'
    : other ? `<span class="tag amber">已装 ${esc(other.name)}</span>`
    : slot.occupied ? '<span class="tag">未绑定</span>'
    : '<span class="tag">空槽位</span>';
  const action = isMine
    ? `<button class="sm danger" onclick="toggleSpoolBinding(${spoolId},${slot.printerId},${slot.amsId},${slot.trayId},true)">解绑</button>`
    : `<button class="sm primary" onclick="toggleSpoolBinding(${spoolId},${slot.printerId},${slot.amsId},${slot.trayId},false)">${other ? "改为这盘" : "绑到这盘"}</button>`;
  return `<div class="bind-row${isMine ? " mine" : ""}">
    <span class="bind-slot">${esc(slot.label)}</span>
    <span class="bind-fil">${dot}${esc(slot.material || "—")}</span>
    <span class="spacer"></span>
    ${tag}${action}
  </div>`;
}

function openBindSpoolDialog(spoolId) {
  const spool = spoolById(spoolId);
  if (!spool) { toast("找不到这盘料，刷新一下列表", "err"); return; }
  const slots = allSlotEntries();
  if (!slots.length) {
    openModal(`绑定槽位 · ${spool.name}`, `<div class="empty-state">
      还没有同步到打印机槽位。<br />
      <span class="small">到「设置」页登录拓竹账号并同步设备后，这里就能看到 AMS 槽位。</span>
    </div>`, `<button class="primary" onclick="closeModal()">知道了</button>`);
    return;
  }
  const mineCount = slots.filter((s) => {
    const b = (S.bindingMap || {})[slotKey(s)];
    return b && b.spool_id === spoolId;
  }).length;

  openModal(`绑定槽位 · ${spool.name}`, `
    <p class="hint">这盘料现在装在 <b>${mineCount}</b> 个槽位上。
      点「绑到这盘」把一个槽位改成这盘料；原来装着的料盘会自动解绑（不会丢数据）。</p>
    <div class="bind-list">${slots.map((s) => bindSlotRowHtml(s, spoolId)).join("")}</div>
    <p class="hint">槽位里显示的材料名是<b>机器上报的</b>，不是你登记的 —— 官方 RFID 料盘
      换料后机器会自己更新，第三方料盘换料后要等它重新识别。</p>
  `, `<button class="primary" onclick="closeModal()">完成</button>`, true);
}

/** 绑定 / 解绑一个槽位。解绑传 spool_id = null。 */
async function toggleSpoolBinding(spoolId, printerId, amsId, trayId, unbind) {
  try {
    await api("/api/bindings", {
      method: "PUT",
      body: JSON.stringify({
        printer_id: printerId,
        ams_id: amsId,
        tray_id: trayId,
        spool_id: unbind ? null : spoolId,
      }),
    });
    await loadBindings();
    if (S.status) await loadStatus();   // 仪表盘上的槽位标记也要跟着变
    toast(unbind ? "已解绑" : "已绑定这盘料", "ok");
    openBindSpoolDialog(spoolId);       // 重开一次，让弹窗里的状态跟着刷新
  } catch (err) { toast(err.message, "err"); }
}

/** 槽位弹窗里的「解绑耗材」。
 *
 *  复用同一个 PUT /api/bindings（spool_id = null），但**不能**用 toggleSpoolBinding ——
 *  它解绑后会重开「料盘绑定槽位」那个弹窗（openBindSpoolDialog）。
 *  从槽位弹窗点解绑，人还在槽位页等着看结果，弹窗却被换成另一盘料的绑定页，
 *  等于点一下就被弹到别处去了。这里解绑完重开的是**同一个槽位**的弹窗。
 *
 *  expectedSpoolId 是从弹窗渲染那一刻就定下来的：解绑前再核一次当前绑定是否还是它，
 *  避免「弹窗开着的时候别处改了这个槽位」→ 把后来绑上去的那盘料误删。 */
async function unbindSlotSpool(printerId, amsId, trayId, expectedSpoolId) {
  const binding = (S.bindingMap || {})[`${printerId}:${amsId}:${trayId}`];
  const nowId = binding ? binding.spool_id : null;
  if (nowId == null) {
    toast("这个槽位已经没绑料盘了", "ok");
    openSlotDialog(printerId, amsId, trayId);
    return;
  }
  if (expectedSpoolId != null && nowId !== expectedSpoolId) {
    toast("这个槽位的绑定刚被改过，请重新确认", "err");
    openSlotDialog(printerId, amsId, trayId);
    return;
  }
  try {
    await api("/api/bindings", {
      method: "PUT",
      body: JSON.stringify({ printer_id: printerId, ams_id: amsId, tray_id: trayId, spool_id: null }),
    });
    await loadBindings();
    if (S.status) await loadStatus();
    const spool = spoolById(expectedSpoolId);
    toast(`已解绑${spool ? `「${spool.name}」` : ""}，料盘数据不受影响`, "ok");
    openSlotDialog(printerId, amsId, trayId);   // 刷新同一个槽位的弹窗
  } catch (err) { toast(err.message, "err"); }
}

function usageSourceLabel(source) {
  const map = { auto: "自动扣重", manual: "手动补录", calibrate: "称重校准",
                correction: "纠错调整", adjust: "手动调整" };
  return map[source] || source;
}

function openMoveDialog(usageId, spoolId, weight) {
  const options = (S.spools || []).filter((s) => !s.archived)
    .map((s) => spoolOptionHtml(s)).join("");
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

/* 标签打印的实现在 label.js（渲染 + ESC/POS 打包 + Web Bluetooth），
   入口是 openLabelDialog(spoolId)；这里保留 A4 拼版的兼容入口。 */
function openLabelSheet() {
  window.open(`/api/labels/sheet?ids=${S.spools.map((s) => s.id).join(",")}`, "_blank");
}

/* ── 槽位绑定 ──────────────────────────────────────────── */

/** 下拉里的一项料盘。
 *
 *  余量拿不到时写「余量未知」而不是 0 g —— `Number(null) === 0`，直接
 *  `(x || 0).toFixed(0)` 会把「字段缺失」显示成「0 克」，看着像一盘空料。
 *  归档的照旧列出来（不然「怎么找不到那盘料」更难查），但标注一下。 */
function spoolOptionHtml(s, selected) {
  const raw = s.remaining_weight;
  const missing = raw === null || raw === undefined || raw === "";
  const rest = missing ? "余量未知" : `余 ${Number(raw).toFixed(0)} g`;
  return `<option value="${s.id}"${selected ? " selected" : ""}>${
    esc(s.name)}（${rest}）${s.archived ? " · 已归档" : ""}</option>`;
}

/** 能出现在「绑定到哪盘料」里的料盘：归档的不进候选（绑上去没意义），
 *  但当前正绑着的那一盘例外 —— 否则打开弹窗看到「不绑定」，用户会以为绑定丢了。 */
function bindCandidates(boundId) {
  return (S.spools || []).filter((s) => !s.archived || s.id === boundId);
}

/** 槽位弹窗里那份料盘下拉。
 *
 *  取值优先级：下拉里当前选着的（扫码填进来的）> 这个槽位上原有的绑定。
 *  两者都不在候选里（比如那盘料已归档被过滤掉）才退回「不绑定」。
 *  @returns {boolean} 是否拿到了真实料盘（false = 候选是空的） */
function fillBindSpoolSelect(boundId) {
  const sel = document.getElementById("bindSpool");
  if (!sel) return false;
  const keep = sel.value;
  const list = bindCandidates(boundId);
  sel.innerHTML = `<option value="">— 不绑定 —</option>`
    + list.map((s) => spoolOptionHtml(s, s.id === boundId)).join("");
  const want = list.some((s) => String(s.id) === keep)
    ? keep
    : (list.some((s) => s.id === boundId) ? String(boundId || "") : "");
  sel.value = want;
  return list.length > 0;
}

/** 料盘列表还没拉到（应用刚起来、还没进过「料盘库存」页）时补一次再重建下拉。
 *
 *  这个坑的来历：`S.spools` 只在 switchView("spools") 里 loadSpools()，
 *  而仪表盘打印机卡片一点槽位就开这个弹窗、扫槽位二维码走的是 `#bind=` 深链 ——
 *  两条路都不经过库存页，于是弹窗里只有「— 不绑定 —」，选不了任何耗材。
 *  这里补拉一次；真的一个料盘都没登记时给一句人话，而不是让人对着空单选发呆。 */
async function ensureSpoolOptions(boundId) {
  const hint = document.getElementById("bindSpoolHint");
  if (hint) hint.textContent = "正在读取料盘列表…";
  await loadSpools().catch(() => {});
  const ok = fillBindSpoolSelect(boundId);
  if (!hint) return;
  hint.textContent = ok ? ""
    : "系统里还没有登记任何料盘 —— 可以点下面的「按槽位信息建料盘」，或先去「料盘库存」新增一盘。";
}

function openSlotDialog(printerId, amsId, trayId) {
  const printer = (S.printers_full || []).find((p) => p.id === printerId) || {};
  const binding = (S.bindingMap || {})[`${printerId}:${amsId}:${trayId}`];
  const tray = findTray(printer, amsId, trayId);
  const boundId = binding ? binding.spool_id : 0;
  // 外挂料盘用 ams_id = -1 表示，标题别写成「AMS 0」
  const isExt = amsId < 0;
  const unit = (((printer.state || {}).ams) || []).find((u) => u.ams_id === amsId);
  const letter = unit ? String(unit.name || "AMS").split(" ").pop() : "";
  const title = isExt ? "外挂料盘" : `${unit ? unit.name : "AMS"} · 槽位 ${letter}${trayId + 1}`;

  const options = bindCandidates(boundId)
    .map((s) => spoolOptionHtml(s, s.id === boundId)).join("");

  // 解绑按钮只在「这个槽位确实绑着料盘」时出现。没绑定却摆一个「解绑耗材」，
  // 点了什么也不会发生，只会让人怀疑是不是坏了。
  const boundSpool = boundId ? spoolById(boundId) : null;
  const unbindRow = boundId
    ? `<div class="slot-unbind">
        <button class="sm danger" onclick="unbindSlotSpool(${printerId},${amsId},${trayId},${boundId})">${
          ICO.unlink}解绑耗材</button>
        <span class="small muted">当前绑定：<b>${esc(boundSpool ? boundSpool.name : `#${boundId}`)}</b></span>
      </div>`
    : "";

  openModal(title, `
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
    <p class="hint" id="bindSpoolHint"></p>
    ${unbindRow}
    <div class="slot-actions">
      <button class="sm primary" onclick="scanForSlotBind(${printerId},${amsId},${trayId})">
        ${ICO.scan}相机扫码
      </button>
    </div>
    <div class="slot-actions">
      <button class="sm" onclick="quickCreateSpoolFromSlot(${printerId},${amsId},${trayId})">按槽位信息建料盘</button>
    </div>
    <div class="slot-qr">
      <img src="/api/labels/slot/${printerId}/${amsId}/${trayId}.png" alt="槽位二维码"
           style="width:72px;height:72px;border:1px solid var(--border);border-radius:6px" />
      <div class="small muted">这是该槽位的二维码，打印出来贴在槽位上。
        以后用上面的「相机扫码」扫这张码，就能直接进这个槽位的绑定页。</div>
    </div>
  `, `<button onclick="closeModal()">取消</button>
      <button class="primary" onclick="saveBinding(${printerId},${amsId},${trayId})">保存绑定</button>`);

  // 弹窗先弹出来（不卡手），下拉是空的就异步补一次料盘列表再重建。
  // 空列表只说明「这次会话还没进过料盘库存」，不代表系统里没有料盘。
  if (!(S.spools || []).length) ensureSpoolOptions(boundId);
}

/** 槽位绑定弹窗里的「相机扫码」：扫到料盘码就填进上面的下拉，
 *  扫到别的槽位码就直接跳到那个槽位（current 传进去是为了识别「扫的是自己」）。 */
function scanForSlotBind(printerId, amsId, trayId) {
  openScan({
    title: "扫料盘二维码",
    hint: "对准料盘上贴的二维码。扫到槽位码也可以 —— 会直接跳到那个槽位。",
    selectId: "bindSpool",
    current: { printer: printerId, ams: amsId, tray: trayId },
  });
}

function findTray(printer, amsId, trayId) {
  const state = printer.state;
  if (!state) return null;
  if (amsId < 0) return state.external_spool || null;   // 外挂料盘是单独一路
  if (!state.ams) return null;
  const unit = state.ams.find((u) => u.ams_id === amsId);
  if (!unit) return null;
  return (unit.trays || []).find((t) => t.tray_id === trayId) || null;
}

/* ── 扫码：认码 → 落地 ────────────────────────────────
 * 认码在 scan.js（相机扫码那套也放那儿），这里管「认出来之后干嘛」。
 * 入口只有相机（openScan）—— 原来那个「扫码枪：光标放这里」的输入框用户用不到，已删。 */

/** 认码。scan.js 没加载时用同规则的兜底实现，免得整条路直接断掉。 */
function parseScanText(text) {
  if (window.spoolScanner && window.spoolScanner.parseScan) {
    return window.spoolScanner.parseScan(text);
  }
  const s = String(text || "").trim();
  let m = s.match(/[#&?]bind=(-?\d+):(-?\d+):(-?\d+)/);
  if (m) return { kind: "bind", printer: +m[1], ams: +m[2], tray: +m[3] };
  m = s.match(/[#&?]spool=(\d+)/);
  if (m) return { kind: "spool", id: +m[1] };
  return /^\d{1,9}$/.test(s) ? { kind: "spool", id: +s } : null;
}

/** 把料盘填进某个下拉。
 *
 *  下拉里没有这盘时不能直接赋值了事 —— 赋值给一个不存在的 option 等于没赋，
 *  用户看到的是「扫了但没反应」。所以这里去后端单独取一次补进选项，
 *  取不到（编号不存在）才报错。
 */
async function pickSpoolInSelect(id, selectId) {
  const sel = document.getElementById(selectId);
  if (!sel) return false;
  if (![...sel.options].some((o) => o.value === String(id))) {
    let spool = null;
    try { spool = await api(`/api/spools/${id}`); } catch (err) { spool = null; }
    if (!spool || !spool.id) { toast(`系统里没有 #${id} 这盘料`, "err"); return false; }
    const option = document.createElement("option");
    option.value = String(spool.id);
    option.textContent = `${spool.name}（余 ${Number(spool.remaining_weight || 0).toFixed(0)} g）`;
    sel.appendChild(option);
    if (!S.spools) S.spools = [];
    if (!S.spools.some((s) => s.id === spool.id)) S.spools.push(spool);
  }
  sel.value = String(id);
  toast(`已选中 #${id}`, "ok");
  return true;
}

/** 扫到的码怎么落地。
 *
 *  - 料盘码：给了 selectId 就填进那个下拉（槽位绑定弹窗用），否则打开料盘详情；
 *  - 槽位码：跳到那个槽位的绑定弹窗 —— 这张贴纸就贴在槽位上，扫它多半是想绑/换料。
 *
 *  @param {string} text 扫到的原始文本
 *  @param {{selectId?:string, current?:{printer:number,ams:number,tray:number}}} opts
 */
async function applyScan(text, opts) {
  const options = opts || {};
  const hit = parseScanText(text);
  if (!hit) { toast("没认出这个码，扫料盘或槽位上那张二维码", "err"); return false; }

  if (hit.kind === "bind") {
    const cur = options.current;
    if (cur && cur.printer === hit.printer && cur.ams === hit.ams && cur.tray === hit.tray) {
      toast("这就是当前这个槽位", "ok");
      return true;
    }
    closeModal();
    switchView("dashboard");
    // 打印机状态还没拉过时先把列表取回来，否则弹窗里找不到这台机器
    if (!(S.printers_full || []).length) await loadPrinters().catch(() => {});
    openSlotDialog(hit.printer, hit.ams, hit.tray);
    return true;
  }

  if (options.selectId) return pickSpoolInSelect(hit.id, options.selectId);
  if (!(S.spools || []).length) await loadSpools().catch(() => {});
  switchView("spools");
  await openSpoolDetail(hit.id);
  return true;
}

/** 相机扫码入口。
 *
 *  手机浏览器没有键盘，原来那个「把光标放这里扫」的输入框在手机上完全没法用，
 *  所以凡是能扫码的地方都配一个按钮走这里。
 */
function openScan(options) {
  const opts = options || {};
  if (!window.spoolScanner) { toast("扫码模块没加载，刷新页面再试", "err"); return; }
  window.spoolScanner.open({
    title: opts.title || "扫二维码",
    hint: opts.hint,
    onResult: (text) => { applyScan(text, { selectId: opts.selectId, current: opts.current }); },
  });
}

/** 库存页工具栏的「扫码」：扫料盘码直接打开那盘料的详情。 */
function scanSpoolCode() {
  openScan({
    title: "扫料盘二维码",
    hint: "对准料盘上贴的二维码，扫到后直接打开这盘料的详情。",
  });
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

/** 打印成果图的地址。
 *  云端任务给的 cover 是 OSS 预签名链接，**30 分钟就过期**，存着过一会儿就是 403，
 *  所以界面只认结算时抓下来存本地的那一份；没抓到就是空，画占位而不是破图。
 *
 *  判定以服务端 `has_cover` 为准（= 有文件名 **且** 文件真在），不要自己看 `cover_file`：
 *  文件被清理掉时 `cover_file` 仍有值，前端会渲染出一个 404 破图。 */
function jobCoverUrl(job) {
  return job && job.has_cover ? `/api/jobs/${job.id}/cover` : "";
}

/** 列表里的成果缩略图。行本身有 onclick 打开详情，点图要 stopPropagation，
 *  否则会一边开大图一边把详情弹窗也顶上来。 */
function jobThumbHtml(job) {
  const url = jobCoverUrl(job);
  return url
    ? `<img class="job-thumb" src="${esc(url)}" alt="打印成果"
         onclick="event.stopPropagation();openJobCover(${job.id})" title="点开看大图">`
    : `<span class="tiny muted">—</span>`;
}

function openJobCover(jobId) {
  window.open(`/api/jobs/${Number(jobId) || 0}/cover`, "_blank");
}

/** 详情里的成果图。口径必须写清楚：这是切片盘面预览图，不是摄像头实拍。 */
function jobCoverBlock(job) {
  const url = jobCoverUrl(job);
  if (!url) {
    return `<div class="job-cover-empty">这次打印云端没有给成果图
      <span class="muted">（校准类任务本来就没有；也可能是抓图时签名链接已过期）</span></div>`;
  }
  return `<div class="job-cover">
      <img src="${esc(url)}" alt="打印成果" onclick="openJobCover(${job.id})" title="点开看大图">
      <p class="tiny muted">云端任务附带的是<b>切片盘面预览图</b>，不是摄像头实拍
        —— 摄像头画面云端不提供，要拿只能走局域网模式的摄像头流。</p>
    </div>`;
}

function renderJobs() {
  const host = document.getElementById("jobTable");
  const totalCost = S.jobs.reduce((sum, j) => sum + (j.cost_total || 0), 0);
  document.getElementById("jobCount").textContent = S.jobs.length
    ? `${S.jobs.length} 条 · 耗材费合计 ¥${totalCost.toFixed(2)}` : "";

  const size = S.jobPageSize || 10;
  if (!S.jobs.length) {
    host.innerHTML = '<div class="empty-state">还没有打印记录。任务会在打印机开始打印时自动创建。</div>';
    renderTableFoot("jobFooter", "", 0, 1, size, "job");
    return;
  }

  const pages = Math.max(1, Math.ceil(S.jobs.length / size));
  if (S.jobPage > pages) S.jobPage = pages;
  const page = S.jobPage || 1;
  const slice = S.jobs.slice((page - 1) * size, page * size);

  host.innerHTML = `<table>
    <thead><tr>
      <th style="width:60px">成果</th>
      <th style="width:96px">任务 ID</th>
      <th>任务标题</th>
      <th style="width:118px">打印机</th>
      <th style="width:150px">时间</th>
      <th style="width:92px;text-align:right">耗材</th>
      <th style="width:96px;text-align:right">耗材费</th>
      <th style="width:84px">状态</th>
      <th style="width:104px">数据来源</th>
      <th style="width:168px">操作</th>
    </tr></thead>
    <tbody>${slice.map((job) => `
      <tr class="clickable" onclick="openJobDetail(${job.id})">
        <td data-label="成果">${jobThumbHtml(job)}</td>
        <td class="small muted" data-label="任务 ID">${esc(job.task_id || job.cloud_task_id || job.id)}</td>
        <td class="cell-main"><div>${esc(job.title)}</div>
            <div class="tiny muted">${esc(fmtDuration(job.duration_seconds))} · 结束于 ${esc(job.progress_at_end)}%</div></td>
        <td class="small" data-label="打印机">${esc(job.printer_name || "")}</td>
        <td class="small muted" data-label="时间">${esc(fmtTime(job.started_at))}</td>
        <td class="num" data-label="耗材">${job.total_weight_g ? job.total_weight_g.toFixed(2) + " g" : "—"}</td>
        <td class="num" data-label="耗材费">${job.cost_total ? "¥" + job.cost_total.toFixed(2) : "—"}</td>
        <td data-label="状态">${jobStatusTag(job.status, job.pending)}</td>
        <td class="small muted" data-label="数据来源">${job.source === "cloud_task" ? "云端任务记录"
          : job.source === "manual" ? "手动录入" : "无数据"}</td>
        <td class="cell-actions" data-label="操作">
          <div class="row-actions main">${jobRowActions(job)}</div>
        </td>
      </tr>`).join("")}</tbody></table>`;
  renderTableFoot("jobFooter", "", S.jobs.length, page, size, "job");
}

/** 列表行内的「跳转耗材 / 更改料盘」。
 *
 *  以前这两个动作只在任务详情弹窗里，想纠正绑错的料盘得先点开任务、
 *  再在弹窗里找那一行 —— 列表上直接给一份，少一层点击。
 *
 *  一份任务可能占多个槽位（多色打印），所以「查看料盘」在多个料盘时
 *  先进详情让用户挑，只有一个时才直接跳 —— 不这么分的话，点了之后
 *  跳到哪一盘是随机的，用户会觉得「点错了」。
 *  两个按钮都要 stopPropagation：行本身有 onclick 打开详情，
 *  不拦的话会一边跳转一边把详情弹窗顶上来。 */
function jobRowActions(job) {
  const list = (job.filaments || []).filter((f) => Number(f.spool_id) > 0);
  const usageList = (job.filaments || []).filter((f) => Number(f.usage_id) > 0);
  const n = list.length;
  if (!n && !usageList.length) {
    return `<span class="tiny muted" title="这次任务没有绑定料盘，也没有扣重流水">—</span>`;
  }
  const single = n === 1 ? Number(list[0].spool_id) : 0;
  const spoolBtn = n
    ? `<button class="sm" onclick="event.stopPropagation();${single
        ? `jumpToSpoolFromJob(${single})`
        : `openJobDetail(${job.id})`}"
         title="${single ? "打开这盘料的详情" : `这次任务绑了 ${n} 盘料，点开详情挑一盘`}">
         ${ICO.spool} 耗材${n > 1 ? ` (${n})` : ""}</button>`
    : `<button class="sm" disabled title="这次任务没有绑定料盘">${ICO.spool} 耗材</button>`;
  // 改扣需要扣重流水；多盘时同样先进详情挑（那里每行一个「更改料盘」）
  const rebindBtn = usageList.length === 1
    ? `<button class="sm" onclick="event.stopPropagation();openRebindUsage(${Number(usageList[0].usage_id)}, ${Number(usageList[0].spool_id) || 0})"
         title="把这次用量改扣到另一盘料">${ICO.link} 绑定</button>`
    : usageList.length > 1
      ? `<button class="sm" onclick="event.stopPropagation();openJobDetail(${job.id})"
           title="这次任务有 ${usageList.length} 条扣重流水，点开详情逐条改">${ICO.link} 绑定 (${usageList.length})</button>`
      : `<button class="sm" disabled title="这次用量没有扣重流水，改不了">${ICO.link} 绑定</button>`;
  return spoolBtn + rebindBtn;
}

function jobGoPage(page) {
  const size = S.jobPageSize || 10;
  const pages = Math.max(1, Math.ceil(S.jobs.length / size));
  S.jobPage = Math.max(1, Math.min(pages, page));
  renderJobs();
}

function jobSetSize(value) {
  S.jobPageSize = parseInt(value, 10) || 10;
  S.jobPage = 1;
  renderJobs();
}

async function openJobDetail(jobId) {
  try {
    const job = await api(`/api/jobs/${jobId}`);
    // 改完料盘要能回到这个弹窗，记一下当前任务
    S.lastJobId = jobId;
    const filaments = job.filaments || [];
    const rows = filaments.length ? filaments.map((f) => {
      const spoolId = Number(f.spool_id) || 0;
      const usageId = Number(f.usage_id) || 0;
      return `
      <tr>
        <td><div class="row" style="gap:8px">
          <span class="swatch" style="background:${esc(f.color)}"></span>
          <span>${esc(f.spool_name || "未绑定料盘")}</span></div></td>
        <td class="small muted">${esc(f.slot_label || "—")}</td>
        <td class="small muted">${esc(f.material || "")} ${f.filament_id ? "· " + esc(f.filament_id) : ""}</td>
        <td class="num">${f.weight_g.toFixed(2)} g</td>
        <td class="num">${f.cost ? "¥" + f.cost.toFixed(2) : "—"}</td>
        <td class="small muted">${esc(f.match_strategy || "")}</td>
        <td class="cell-actions" data-label="操作">
          <div class="row-actions main">
            <button class="sm"${spoolId ? ` onclick="jumpToSpoolFromJob(${spoolId})"` : " disabled"}
              title="${spoolId ? "打开这盘料的详情" : "这行用量还没绑到料盘"}">查看料盘</button>
            <button class="sm"${usageId ? ` onclick="openRebindUsage(${usageId}, ${spoolId})"` : " disabled"}
              title="${usageId ? "把这次用量改扣到另一盘料" : "这次用量没有扣重流水，改不了"}">更改料盘</button>
          </div>
        </td>
      </tr>`;
    }).join("") : '<tr><td colspan="7"><div class="empty-state">这次任务没有解析到耗材明细</div></td></tr>';

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
        <span>本次耗材费 <b>¥${(job.cost_total || 0).toFixed(2)}</b></span>
        <span class="muted">数据来源：${job.source === "cloud_task" ? "拓竹云端任务记录"
          : job.source === "manual" ? "手动录入" : "暂无"}</span>
      </div>
      ${actions ? `<div class="row" style="margin-bottom:12px">${actions}</div>` : ""}
      ${jobCoverBlock(job)}
      <table><thead><tr><th>料盘</th><th>槽位</th><th>耗材</th>
        <th style="text-align:right">用量</th><th style="text-align:right">耗材费</th><th>匹配依据</th>
        <th style="width:170px">操作</th></tr></thead>
        <tbody>${rows}</tbody></table>
      <p class="hint" style="margin-top:10px">扣错盘了就点「更改料盘」：这次用量会先从原来那盘退回，再扣到新选的那盘。</p>
    `, `<button class="primary" onclick="closeModal()">关闭</button>`, true);
  } catch (err) { toast(err.message, "err"); }
}

/** 打印记录里的「查看料盘」：先关掉任务弹窗，再开料盘详情。
 *  这里是「一层弹窗」的模型（跟手动录入那条路一致），不关的话 openSpoolDetail
 *  会把 modalHost 整块换掉，看完料盘就回不到任务了。 */
async function jumpToSpoolFromJob(spoolId) {
  const id = Number(spoolId);
  if (!id) { toast("这行用量还没绑到料盘", "err"); return; }
  closeModal();
  // 从打印记录直接进来时可能压根没拉过料盘列表（列表只在库存页加载过），
  // 不补这一下，料盘弹窗会因为找不到这盘料而报错。
  if (!(S.spools || []).length) {
    try { await loadSpools(); } catch (err) { /* 接口失败就让 openSpoolDetail 自己提示 */ }
  }
  await openSpoolDetail(id);
}

/** 打印记录里的「更改料盘」：把这条扣重流水从一盘料转到另一盘。 */
async function openRebindUsage(usageId, currentSpoolId) {
  const id = Number(usageId);
  if (!id) { toast("这次用量没有扣重流水，改不了", "err"); return; }
  const cur = Number(currentSpoolId) || 0;
  if (!(S.spools || []).length) {
    try { await loadSpools(); } catch (err) { toast(err.message, "err"); return; }
  }
  const list = bindCandidates(cur);
  if (!list.length) { toast("还没有料盘可改扣，先到「料盘库存」录一盘", "err"); return; }
  S.rebindUsage = { id, spoolId: cur };
  openModal("更改料盘", `
    <p class="hint">这次用量会先从原来那盘料退回去，再扣到下面选的这盘上。
      用来纠正绑错料盘、扣错盘的情况。</p>
    <label class="fld"><span>改成这盘料</span>
      <select id="rebindSpool">
        ${list.map((s) => spoolOptionHtml(s, s.id === cur)).join("")}
      </select></label>
  `, `<button onclick="closeModal()">取消</button>
      <button class="primary" onclick="submitRebindUsage()">确认更改</button>`);
}

async function submitRebindUsage() {
  const ctx = S.rebindUsage;
  if (!ctx) { toast("页面已刷新过，请重新打开任务详情再试", "err"); return; }
  const sel = document.getElementById("rebindSpool");
  const target = Number(sel && sel.value) || 0;
  if (!target) { toast("先选一盘料", "err"); return; }
  if (target === ctx.spoolId) { toast("还是原来那盘，没变化", "err"); return; }
  try {
    await api(`/api/usages/${ctx.id}/move`, {
      method: "POST", body: JSON.stringify({ spool_id: target }),
    });
    toast("已改扣到新的料盘", "ok");
    const jobId = S.lastJobId;
    S.rebindUsage = null;
    closeModal();
    await loadJobs();
    await loadSpools();
    // 改完回到任务详情，让用户立刻看到新的料盘名和费用
    if (jobId) await openJobDetail(jobId);
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
  // 同一个下拉口径（余量缺失写「余量未知」而不是 0 g），别再各写一份手拼字符串
  const spoolOptions = (S.spools || []).map((s) => spoolOptionHtml(s)).join("");

  let slotRows = "";
  (printer.state && printer.state.ams ? printer.state.ams : []).forEach((unit) => {
    (unit.trays || []).forEach((tray) => {
      if (!tray.occupied) return;
      slotRows += `<tr>
        <td class="small">${esc(slotCode(unit, tray))} 槽位
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

/* ── 耗材汇总 ──────────────────────────────────────────── */
async function loadSummary() {
  try {
    S.stats = await api(`/api/stats?tz_minutes=${tzMinutes()}`);
    // 概览环形图与价格分布都在本地算（料盘也就几百条），这样点材料筛选是即时的，
    // 不用每点一次就打一趟服务器；口径也跟库存页的标签页共用同一套函数。
    try {
      S.summarySpools = (await api("/api/spools?archived=false")).spools || [];
    } catch (err) { S.summarySpools = S.summarySpools || []; }
    renderSummary();
    renderDashboard();
  } catch (err) { toast(err.message, "err"); }
}

/** 材料配色。固定顺序取色，同一材料每屏颜色一致，不会点一次换一个色。 */
const MATERIAL_COLORS = [
  "#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed",
  "#0891b2", "#db2777", "#65a30d", "#ea580c", "#475569",
];

/** 按材料聚合（盘数 + 余量），用于概览环形图。 */
function summaryMaterials(spools) {
  const map = new Map();
  (spools || []).forEach((s) => {
    const key = s.material || "未填写";
    const item = map.get(key) || { label: key, count: 0, remaining: 0 };
    item.count += 1;
    item.remaining += Number(s.remaining_weight) || 0;
    map.set(key, item);
  });
  return [...map.values()].sort((a, b) => b.count - a.count || b.remaining - a.remaining);
}

/** 手绘环形图。不引图表库 —— 这个应用常跑在没外网的内网里，多一个离线依赖不值当。
 *  segments: [{label, value, color}]，按 value 占比分配弧长（总和为 0 时只画底环）。 */
function donutChart(segments, size, thickness) {
  const box = size || 176;
  const w = thickness || 28;
  const r = (box - w) / 2;
  const c = 2 * Math.PI * r;
  const total = segments.reduce((sum, x) => sum + x.value, 0);
  let acc = 0;
  const arcs = segments.map((seg) => {
    const frac = total > 0 ? seg.value / total : 0;
    const on = frac * c;
    const arc = `<circle class="donut-arc" cx="${box / 2}" cy="${box / 2}" r="${r}"
      fill="none" stroke="${esc(seg.color)}" stroke-width="${w}"
      stroke-dasharray="${on.toFixed(2)} ${(c - on).toFixed(2)}"
      stroke-dashoffset="${(-acc * c).toFixed(2)}"
      transform="rotate(-90 ${box / 2} ${box / 2})"></circle>`;
    acc += frac;
    return arc;
  }).join("");
  return `<svg class="donut" viewBox="0 0 ${box} ${box}" width="${box}" height="${box}" role="img">
    <circle cx="${box / 2}" cy="${box / 2}" r="${r}" fill="none"
      stroke="var(--surface-3)" stroke-width="${w}"></circle>
    ${arcs}
    <text class="donut-total" x="${box / 2}" y="${box / 2 + 2}">${total}</text>
    <text class="donut-unit" x="${box / 2}" y="${box / 2 + 20}">盘</text>
  </svg>`;
}

/** 点环形图上的材料 -> 只统计这块。再点一次取消。 */
function pickSummaryMaterial(name) {
  S.summaryFilter = S.summaryFilter === name ? null : name;
  renderSummary();
}

function clearSummaryFilter() {
  S.summaryFilter = null;
  renderSummary();
}

/** 点「未使用 / 使用中 / 消耗完」-> 跳到料盘库存并切到对应的标签页。 */
function jumpToSpoolsByState(stateKey) {
  const meta = USE_STATE_META[stateKey];
  switchView("spools");
  const tab = (meta && meta.tab) || "all";
  // 标签页高亮是 switchSpoolTab 管的（它同时会重置页码并重绘）
  switchSpoolTab(tab);
}

/** 点价格档「查看明细」-> 跳到料盘库存并按这个价格区间筛。
 *  「¥40 以上」档没有上限，to 传空串 = 不填最大价。 */
function jumpToSpoolsByPrice(from, to) {
  switchView("spools");
  const min = document.getElementById("spoolPriceMin");
  const max = document.getElementById("spoolPriceMax");
  if (min) min.value = String(from);
  if (max) max.value = to == null || to === "" ? "" : String(to);
  S.spoolPage = 1;
  renderSpools();
}

/* ── 汇总表 → 料盘库存 的钻取 ──────────────────────────── */
/** 汇总页那三张分组表各自对应库存页的哪个筛选项，以及「分组名怎么从料盘上取」。
 *
 *  norm 必须跟后端 `_group_summary` 的口径一致，否则点了汇总表里的名字跳过去是空列表：
 *  后端把空品牌/空材料归到「未填写」，而外观的空值归到「普通」（外观有默认值）。
 *  这份表是两边的唯一约定，改后端分组规则时这里要跟着改。 */
const SUMMARY_DRILL_FIELDS = {
  brand: { select: "spoolBrand", label: "品牌", norm: (s) => (s.brand || "").trim() || "未填写" },
  material: { select: "spoolMaterial", label: "材料", norm: (s) => (s.material || "").trim() || "未填写" },
  finish: { select: "spoolFinish", label: "外观", norm: (s) => s.finish || "普通" },
};

/** 给下拉赋值；值不在选项里就先补一个 option 再选。
 *  直接 `sel.value = x` 在没有这个 option 时会静默变回空字符串 ——
 *  「未填写」和不在预设目录里的老品牌都走这条路，一静默就成了「点了没反应」。 */
function setSelectValue(id, value) {
  const sel = document.getElementById(id);
  if (!sel) return;
  if (!value) { sel.value = ""; return; }
  let has = false;
  for (const opt of sel.options) { if (opt.value === value) { has = true; break; } }
  if (!has) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = value;
    sel.appendChild(opt);
  }
  sel.value = value;
}

/** 点汇总表里的品牌 / 材料 / 外观名 -> 跳到料盘库存，只留这一个筛选条件。
 *  其余筛选先清空：不然「先点品牌再点材料」两个条件叠在一起，筛出的比任何一个都少，
 *  看起来就像点了没生效。 */
function jumpToSpoolsByField(field, value) {
  const cfg = SUMMARY_DRILL_FIELDS[field];
  if (!cfg) return;
  switchView("spools");
  resetSpoolFilters();
  setSelectValue(cfg.select, value);
  S.spoolPage = 1;
  renderSpools();
  toast(`已按${cfg.label}「${value}」筛选`, "ok");
}

/* ── 库存数据概览（环形图 + 使用状态） ─────────────────── */
function renderSummaryOverview() {
  const host = document.getElementById("summaryOverview");
  if (!host) return;
  const all = S.summarySpools || [];
  const filter = S.summaryFilter;
  const spools = filter ? all.filter((s) => (s.material || "未填写") === filter) : all;

  const filterLabel = document.getElementById("overviewFilter");
  const clearBtn = document.getElementById("overviewClear");
  if (filterLabel) filterLabel.textContent = filter ? `已筛选：${filter}` : "";
  if (clearBtn) clearBtn.classList.toggle("hidden", !filter);

  if (!spools.length) {
    host.innerHTML = `<div class="empty-state">还没有在库料盘。先到「料盘库存」里录一盘。</div>`;
    return;
  }

  const materials = summaryMaterials(spools);
  const segments = materials.map((m, i) => ({
    label: m.label, value: m.count,
    color: MATERIAL_COLORS[i % MATERIAL_COLORS.length],
  }));
  const tally = useStateTally(spools);
  const order = ["unused", "in_use", "empty"];

  host.innerHTML = `
    <div class="overview-grid">
      <div class="overview-chart">
        ${donutChart(segments)}
        <div class="donut-legend">
          ${segments.map((seg) => `<button class="legend-item${filter === seg.label ? " on" : ""}"
              onclick="pickSummaryMaterial('${esc(seg.label)}')"
              title="${filter === seg.label ? "取消筛选" : "只看 " + esc(seg.label)}">
            <span class="dot" style="background:${esc(seg.color)}"></span>${esc(seg.label)}
          </button>`).join("")}
        </div>
      </div>
      <div class="overview-uses">
        <div class="overview-title">库存使用状态
          <span class="muted small">共 ${tally.total} 盘</span></div>
        <div class="use-bar">
          ${order.map((k) => `<span style="width:${tally.total ? (tally[k] / tally.total) * 100 : 0}%;
            background:${USE_STATE_META[k].color}"></span>`).join("")}
        </div>
        <div class="use-legend">
          ${order.map((k) => {
            const pct = tally.total ? (tally[k] / tally.total) * 100 : 0;
            return `<button class="use-item" onclick="jumpToSpoolsByState('${k}')"
                title="到料盘库存里看这 ${tally[k]} 盘">
              <span class="dot" style="background:${USE_STATE_META[k].color}"></span>
              <span class="use-name">${USE_STATE_META[k].label}</span>
              <span class="spacer"></span>
              <b>${tally[k]}</b>
              <span class="use-pct">${pct.toFixed(0)}%</span>
            </button>`;
          }).join("")}
        </div>
        <p class="hint" style="margin:10px 0 0">
          点材料只统计那种材料，点状态行可直接跳到料盘库存的对应标签页。
        </p>
      </div>
    </div>`;
}

/* ── 品牌分布（按盘数排序，点品牌名钻取） ─────────────────
 *  和「库存数据概览」并排站，一起构成汇总页的第一屏。
 *  每行给三件事：盘数、占比条、这些盘的平均单价 —— 均价拿不到就明说「未登记价格」，
 *  不留空白（用户明确要求：不要留空）。 */
const BRAND_BAR_COLORS = ["#7c5cf0", "#e8479a", "#00b4c8", "#f0883e", "#12b886"];

function renderBrandDist() {
  const host = document.getElementById("brandDist");
  if (!host) return;
  const all = S.summarySpools || [];
  const filter = S.summaryFilter;
  const spools = filter ? all.filter((s) => (s.material || "未填写") === filter) : all;
  const counter = document.getElementById("brandDistCount");

  if (!spools.length) {
    if (counter) counter.textContent = "";
    host.innerHTML = `<div class="empty-state">还没有在库料盘。</div>`;
    return;
  }

  const byBrand = new Map();
  spools.forEach((s) => {
    const name = s.brand || "未填写";
    if (!byBrand.has(name)) byBrand.set(name, []);
    byBrand.get(name).push(s);
  });
  const rows = [...byBrand.entries()]
    .map(([name, list]) => {
      const prices = list.map((s) => s.price).filter((p) => p != null && p !== "" && Number(p) > 0);
      const avg = prices.length ? prices.reduce((a, b) => a + Number(b), 0) / prices.length : null;
      return { name, count: list.length, avg, priced: prices.length };
    })
    .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, "zh"));

  const total = spools.length;
  const max = rows[0] ? rows[0].count : 1;
  if (counter) counter.textContent = `${rows.length} 个品牌 · 共 ${total} 盘`;

  host.innerHTML = rows.map((r, i) => {
    const pct = (r.count / total) * 100;
    const color = i < BRAND_BAR_COLORS.length ? BRAND_BAR_COLORS[i] : "#98a2b3";
    const priceText = r.avg == null
      ? `<span class="bd-noprice">${r.count} 盘均未登记价格</span>`
      : `每盘均价 <b>¥${r.avg.toFixed(2)}</b>${
          r.priced < r.count ? `<span class="bd-tiny">（${r.priced}/${r.count} 盘有价）</span>` : ""}`;
    return `<button class="bd-row" data-value="${esc(r.name)}"
        onclick="jumpToSpoolsByField('brand', this.dataset.value)"
        title="到料盘库存里看「${esc(r.name)}」这 ${r.count} 盘">
      <span class="bd-name">${esc(r.name)}</span>
      <span class="bd-count"><b>${r.count}</b><span class="bd-tiny">${pct.toFixed(0)}%</span></span>
      <span class="bd-track"><span class="bd-fill"
        style="width:${Math.max(2, (r.count / max) * 100)}%;background:${color}"></span></span>
      <span class="bd-sub">${priceText}</span>
    </button>`;
  }).join("");
}

/* ── 价格区间分布 ──────────────────────────────────────── */
function renderPriceDist() {
  const host = document.getElementById("priceDist");
  if (!host) return;
  const all = S.summarySpools || [];
  const filter = S.summaryFilter;
  const spools = filter ? all.filter((s) => (s.material || "未填写") === filter) : all;
  const { buckets, unpriced } = priceBuckets(spools);

  const counter = document.getElementById("priceDistCount");
  if (counter) {
    counter.textContent = unpriced
      ? `另有 ${unpriced} 盘未登记价格（不计入）`
      : (buckets.length ? `共 ${buckets.length} 档` : "");
  }

  if (!buckets.length) {
    host.innerHTML = `<div class="card"><div class="empty-state">
      还没有登记价格的料盘。<br />
      <span class="small">在「料盘库存」里编辑料盘时填上「整盘价格」，这里就能看出价格分布。</span>
    </div></div>`;
    return;
  }

  host.innerHTML = buckets.map((b, i) => `
    <button class="price-card" onclick="jumpToSpoolsByPrice(${b.from}, ${b.to == null ? '""' : b.to})"
            title="到料盘库存里看这 ${b.count} 盘">
      <div class="price-head">
        <span class="dot" style="background:${MATERIAL_COLORS[i % MATERIAL_COLORS.length]}"></span>
        <span>整盘价格</span>
      </div>
      <div class="price-range">${esc(b.label)}</div>
      <div class="price-nums">
        <span>数量 <b>${b.count}</b> 盘</span>
        <span>占比 <b>${b.percent.toFixed(0)}%</b></span>
      </div>
      <div class="bar"><div style="width:${Math.max(0, Math.min(100, b.percent))}%;
        background:${MATERIAL_COLORS[i % MATERIAL_COLORS.length]}"></div></div>
      <div class="price-foot">
        <span class="muted tiny">合计 ¥${b.value.toFixed(2)}</span>
        <span class="price-more">查看明细 →</span>
      </div>
    </button>`).join("");
}

/** 分组汇总表：名称 | 盘数 | 每盘均价 | 满盘净重 | 已用 | 剩余 | 余量条 | 采购金额 | 余值。
 *  窄屏会走 .table-card 的卡片式布局，所以每格都要 data-label。
 *
 *  field 是钻取用的维度（brand / material / finish）：名称列会变成一个按钮，
 *  点了带着这个名字跳到料盘库存并预填筛选。传空字符串就不带钻取。 */
function summaryTable(rows, emptyText, field) {
  if (!rows || !rows.length) return `<div class="empty-state">${esc(emptyText)}</div>`;
  return `<table><thead><tr>
      <th>名称</th>
      <th style="text-align:right">盘数</th>
      <th style="text-align:right">每盘均价</th>
      <th style="text-align:right">满盘净重</th>
      <th style="text-align:right">已用</th>
      <th style="text-align:right">剩余</th>
      <th>余量</th>
      <th style="text-align:right">采购金额</th>
      <th style="text-align:right">余值</th>
    </tr></thead><tbody>${rows.map((r) => {
    // 分母只算登记过价的盘：混进没填价的盘会把均价拉低，看着像算错了
    const priced = Number(r.priced_count) || 0;
    const avg = priced > 0 ? r.price / priced : null;
    return `
      <tr>
        <td class="cell-main">${
          field
            ? `<button class="cell-link" data-value="${esc(r.name)}"
                 onclick="jumpToSpoolsByField('${field}', this.dataset.value)"
                 title="到料盘库存里看这 ${r.count} 盘">${esc(r.name)}</button>`
            : `<b>${esc(r.name)}</b>`}</td>
        <td class="num" data-label="盘数">${r.count} 盘</td>
        <td class="num" data-label="每盘均价">${
          avg == null ? '<span class="tiny muted">未登记</span>' : "¥" + avg.toFixed(2)}</td>
        <td class="num" data-label="满盘净重">${r.initial_g.toFixed(0)} g</td>
        <td class="num" data-label="已用">${r.used_g.toFixed(0)} g</td>
        <td class="num" data-label="剩余">${r.remaining_g.toFixed(0)} g</td>
        <td data-label="余量">
          <div class="bar"><div class="${r.remaining_percent <= 10 ? "low" : ""}"
            style="width:${Math.max(0, Math.min(100, r.remaining_percent))}%"></div></div>
          <div class="tiny muted" style="margin-top:4px">${r.remaining_percent}%</div>
        </td>
        <td class="num" data-label="采购金额">${r.price > 0 ? "¥" + r.price.toFixed(2) : '<span class="tiny muted">未登记</span>'}</td>
        <td class="num" data-label="余值">${r.stock_value > 0 ? "¥" + r.stock_value.toFixed(2) : "—"}</td>
      </tr>`;
  }).join("")}</tbody></table>`;
}

/** 在库料盘的均价口径。分母一律只算「登记过整盘价」的盘 ——
 *  把没填价的盘算进来会把均价拉低，看着像算错了。
 *  一条价格都没有时数值全是 null，由调用方决定怎么把这块地方填满，别留个空格。 */
function summaryPriceStats(spools) {
  const all = spools || [];
  const priced = all.filter((s) => (Number(s.price) || 0) > 0);
  const n = priced.length;
  if (!n) return { priced: 0, unpriced: all.length, perSpool: null, perKg: null, min: null, max: null };
  const total = priced.reduce((sum, s) => sum + (Number(s.price) || 0), 0);
  // 满盘净重缺省 1000 g，跟后端 Spool.initial_weight 的默认值保持一致
  const grams = priced.reduce((sum, s) => sum + (Number(s.initial_weight) || 1000), 0);
  const prices = priced.map((s) => Number(s.price) || 0);
  return {
    priced: n,
    unpriced: all.length - n,
    perSpool: total / n,
    perKg: grams > 0 ? (total / grams) * 1000 : null,
    min: Math.min(...prices),
    max: Math.max(...prices),
  };
}

/** 均价两张卡。加上前面 6 张固定卡凑成 8 张（宽屏 4×2，刚好两行整）——
 *  数量是刻意的：grid-stats 在 ≥980px 是四列，末行不留空位。
 *  （原先「平均每公斤」那张按用户反馈删了：不同规格的盘按满盘净重折算，
 *  口径虽然可比，但日常看盘单价已经够用，多一张反而要多解释一句。）
 *  一条价格都没有时不画数字，改写成「去哪儿登记」，卡里照样有内容。 */
function priceStatCards() {
  const ps = summaryPriceStats(S.summarySpools);
  const word = (text) => `<span class="value-word">${esc(text)}</span>`;
  const pricedSub = ps.priced
    ? `${ps.priced} 盘已登记价格${ps.unpriced ? `，另有 ${ps.unpriced} 盘未登记` : ""}`
    : "到「料盘库存」给料盘填上整盘价格";
  const card = (label, valueHtml, subText) => `<div class="stat accent"><span class="ico">${ICO.coins}</span>
      <div class="label">${esc(label)}</div>
      <div class="value">${valueHtml}</div>
      <div class="sub">${esc(subText)}</div></div>`;
  return [
    card("平均每盘单价",
      ps.perSpool == null ? word("未登记") : `¥${ps.perSpool.toFixed(2)}`,
      pricedSub),
    card("整盘价格区间",
      ps.min == null ? word("未登记") : `¥${ps.min.toFixed(0)} - ${ps.max.toFixed(0)}`,
      `${ps.priced ? `${ps.priced} 盘已登记，` : ""}最便宜 / 最贵的一盘`),
  ].join("");
}

function renderSummary() {
  const st = S.stats;
  const host = document.getElementById("summaryStats");
  if (!host) return;
  if (!st) { host.innerHTML = ""; return; }

  const remaining = Number(st.remaining_total) || 0;
  const used = Number(st.used_total) || 0;
  const initial = remaining + used;
  const pct = initial > 0 ? (remaining / initial) * 100 : 0;
  host.innerHTML = `
    <div class="stat"><span class="ico">${ICO.spool}</span>
      <div class="label">在库料盘</div>
      <div class="value">${st.spool_count || 0}<small> 盘</small></div>
      <div class="sub">已归档 ${st.archived_count || 0} 盘（不计入下方汇总）</div></div>
    <div class="stat accent"><span class="ico">${ICO.coins}</span>
      <div class="label">采购总额</div>
      <div class="value">¥${(Number(st.price_total) || 0).toFixed(2)}</div>
      <div class="sub">按在库料盘的整盘价累加</div></div>
    <div class="stat"><span class="ico">${ICO.weight}</span>
      <div class="label">已消耗</div>
      <div class="value">${used.toFixed(0)}<small> g</small></div>
      <div class="sub">折算约 ¥${(Number(st.used_value) || 0).toFixed(2)}（按当前单价）</div></div>
    <div class="stat"><span class="ico">${ICO.weight}</span>
      <div class="label">剩余</div>
      <div class="value">${remaining.toFixed(0)}<small> g</small></div>
      <div class="sub">占采购总量 ${pct.toFixed(1)}%</div></div>
    <div class="stat accent"><span class="ico">${ICO.coins}</span>
      <div class="label">库存余值</div>
      <div class="value">¥${(Number(st.stock_value) || 0).toFixed(2)}</div>
      <div class="sub">剩余克重 × 各自单价</div></div>
    <div class="stat accent"><span class="ico">${ICO.coins}</span>
      <div class="label">累计打印耗材费</div>
      <div class="value">¥${(Number(st.print_cost_total) || 0).toFixed(2)}</div>
      <div class="sub">按每次任务的实际用量逐笔累计</div></div>
    ${priceStatCards()}`;

  const brands = st.by_brand || [];
  const materials = st.by_material_detail || [];
  const finishes = st.by_finish || [];
  document.getElementById("brandSummary").innerHTML =
    summaryTable(brands, "还没有料盘。先到「料盘库存」里录一盘。", "brand");
  document.getElementById("materialSummary").innerHTML =
    summaryTable(materials, "还没有料盘。", "material");
  document.getElementById("finishSummary").innerHTML =
    summaryTable(finishes, "还没有料盘。", "finish");
  const setCount = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
  setCount("brandSummaryCount", brands.length ? `共 ${brands.length} 个品牌` : "");
  setCount("materialSummaryCount", materials.length ? `共 ${materials.length} 种材料` : "");
  setCount("finishSummaryCount", finishes.length ? `共 ${finishes.length} 种外观` : "");

  // 概览图与价格分布：数据来自在库料盘清单（本地算），点筛选是即时的
  renderSummaryOverview();
  renderBrandDist();
  renderPriceDist();
}

/* ── 自定义品牌 ────────────────────────────────────────── */
function renderBrandBox() {
  const host = document.getElementById("brandBox");
  if (!host) return;
  const catalog = S.catalog || {};
  const custom = catalog.custom_brands || [];
  const presets = catalog.preset_brands || [];
  host.innerHTML = `
    <p class="hint">预设品牌 ${presets.length} 个：
      ${presets.map((b) => esc(b)).join("、")}</p>
    <div class="row" style="margin:12px 0">
      <input id="newBrand" placeholder="自定义品牌名，如：某某耗材"
             onkeydown="if(event.key==='Enter')addBrand()" />
      <button class="sm primary" onclick="addBrand()">添加</button>
    </div>
    ${custom.length
      ? `<div class="chip-row">${custom.map((b, i) => `
          <span class="brand-chip">${esc(b)}
            <button class="chip-x" title="删除这个自定义品牌"
                    onclick="removeBrand(${i})">×</button></span>`).join("")}</div>`
      : '<p class="hint">还没有自定义品牌。新增料盘时品牌选「＋ 自定义品牌…」填的名字会自动记到这里。</p>'}
    <p class="hint">删除只影响下拉候选：已经用这个品牌录好的料盘照旧保留，需要时可以再加回来。</p>`;
}

async function addBrand() {
  const input = document.getElementById("newBrand");
  const name = (input ? input.value : "").trim();
  if (!name) { toast("请填写品牌名", "err"); return; }
  try {
    const data = await api("/api/brands", { method: "POST", body: JSON.stringify({ name }) });
    S.catalog = { ...(S.catalog || {}), brands: data.brands, custom_brands: data.custom_brands };
    renderBrandBox();
    toast(`已添加品牌「${name}」`, "ok");
  } catch (err) { toast(err.message, "err"); }
}

async function removeBrand(index) {
  const custom = (S.catalog && S.catalog.custom_brands) || [];
  const name = custom[index];
  if (!name) return;
  try {
    const data = await api(`/api/brands/${encodeURIComponent(name)}`, { method: "DELETE" });
    S.catalog = { ...(S.catalog || {}), brands: data.brands, custom_brands: data.custom_brands };
    renderBrandBox();
    toast(`已移除「${name}」`, "ok");
  } catch (err) { toast(err.message, "err"); }
}

/* ── 设置 ──────────────────────────────────────────────── */
/** 区域标签。只认两个已知值，其余原样显示。
 *
 *  以前写成 `region === "china" ? "中国大陆" : "海外"`，导致任何非 china 的值
 *  （包括 undefined）都会被说成「海外」—— 设置页因此永远显示海外，与账号真实
 *  区域无关。现在未知值会被显式标出来，不会再冒充某个区域。 */
function regionLabel(region) {
  const key = String(region || "").trim().toLowerCase();
  if (key === "china") return "中国大陆";
  if (key === "global") return "海外";
  return key ? `未知（${region}）` : "未设置";
}

function toggleRegionSwitch() {
  const box = document.getElementById("regionSwitchBox");
  if (box) box.classList.toggle("hidden");
}

async function switchRegion() {
  const region = document.getElementById("regionSwitch").value;
  try {
    const result = await api("/api/account/region", {
      method: "POST", body: JSON.stringify({ region }),
    });
    toast(result.message || "区域已切换", "ok");
    await loadStatus();
  } catch (err) { toast(err.message, "err"); }
}

function renderSettings() {
  renderBrandBox();
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
            区域 ${esc(regionLabel(account.region))}</div>
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
        <button class="sm ghost" onclick="toggleRegionSwitch()">区域不对？</button>
      </div>
      <div class="hidden" id="regionSwitchBox" style="margin-top:12px">
        <label class="field"><span>切换到哪个区域</span>
          <select id="regionSwitch">
            <option value="china" ${account.region === "china" ? "" : "selected"}>中国大陆</option>
            <option value="global" ${account.region === "global" ? "selected" : ""}>海外</option>
          </select></label>
        <p class="hint">拓竹账号只属于一个区域：选错区域时能登录成功，但设备列表永远是空的
          （接口打到了另一个域名）。切换后若之前保存过密码，会自动在新区域重新登录并同步设备；
          没保存密码就切到登录表单重新登一次。</p>
        <button class="sm" onclick="switchRegion()">切换并重新同步</button>
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
  // data-label 给窄屏卡片式布局用（CSS 里 #deviceBox td::before 取 attr(data-label)）：
  // 这张表 5 列，在 360px 手机上会把整页推出屏幕，所以窄屏改成竖排卡片。
  document.getElementById("deviceBox").innerHTML = printers.length
    ? `<table><thead><tr><th>名称</th><th>机型</th><th>序列号</th><th>状态</th><th></th></tr></thead>
        <tbody>${printers.map((entry) => `
          <tr>
            <td class="cell-main"><input value="${esc(entry.printer.name)}" style="max-width:180px"
                 onchange="renameDevice(${entry.printer.id}, this.value)" /></td>
            <td class="small" data-label="机型">${esc(entry.printer.model || "未知")}</td>
            <td class="small muted" data-label="序列号">${esc(entry.printer.serial)}</td>
            <td data-label="状态"><span class="tag ${entry.printer.enabled ? "green" : ""}">
              ${entry.printer.enabled ? "已启用" : "已停用"}</span></td>
            <td class="cell-actions">
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
    await loadStatus();  // 拉回 verifyCode 状态，让验证码输入框显示出来
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

/* 运行中 hash 变化：手机上用系统相机扫料盘/槽位二维码就会走到这里。
 *
 * 浏览器换 hash 不会重新加载页面，没有这个监听的话，「应用已经开着 + 扫码」
 * 就完全没有反应（用户以为扫码坏了）。放在应用外层，登录态都没进也无妨：
 * 那时页面还是登录页，switchView 找不到容器自然什么都不做。
 */
window.addEventListener("hashchange", () => { applyHashRoute(); });

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
/** 按 location.hash 落到对应页面 / 弹窗。
 *
 *  这个函数不只服务「首次打开带 hash 的链接」，也服务**运行中改 hash**：
 *  手机上最常见的用法是用系统相机（或微信）扫料盘/槽位上那张二维码，
 *  扫出来就是 `http://nas:8000/#spool=12`。如果应用此刻正开着，浏览器只会
 *  换一段 hash 而不会重新加载页面 —— 没人监听 hashchange 的话，用户看到的是
 *  「扫了，什么都没发生」。所以下面在启动时挂了 hashchange（见 bindGlobalEvents）。
 *
 *  弹窗依赖的数据（打印机列表 / 料盘列表）在这里按需补齐：直接开链接时
 *  enterApp 已经拉过一遍，但运行中改 hash 时不能假设一定有。
 *
 *  @param {{initial?:boolean}} [options] initial=true 表示这是启动时那次调用：
 *    此时 hash 为空要落到仪表盘（首次打开的默认页）；运行中改 hash 时
 *    hash 变空（比如用户按了浏览器回退）则什么都不做，免得把人从当前页拽走。
 */
async function applyHashRoute(options) {
  const opts = options || {};
  const hash = location.hash.slice(1);
  // 两种写法都认：`#view=summary`（当前形式）和老的裸名 `#spools`。
  if (hash.startsWith("view=")) {
    const name = hash.slice(5);
    if (VIEW_NAMES.includes(name)) { switchView(name); return; }
  }
  if (VIEW_NAMES.includes(hash)) {
    switchView(hash);
    return;
  }
  if (hash.startsWith("spool=")) {
    const id = parseInt(hash.slice(6), 10);
    if (!id) return;
    if (!(S.spools || []).length) await loadSpools().catch(() => {});
    switchView("spools");
    await openSpoolDetail(id);
    return;
  }
  if (hash.startsWith("bind=")) {
    const parts = hash.slice(5).split(":").map(Number);
    if (parts.length === 3 && parts.every((n) => !isNaN(n))) {
      // 打印机状态还没拉过时先取回来，否则弹窗里找不到这台机器
      if (!(S.printers_full || []).length) await loadPrinters().catch(() => {});
      // 弹窗里的「绑定到哪盘料」同样要有料盘可选（与上面 spool= 分支同一个道理）
      if (!(S.spools || []).length) await loadSpools().catch(() => {});
      switchView("dashboard");
      openSlotDialog(parts[0], parts[1], parts[2]);
      return;
    }
  }
  if (opts.initial) {
    // 地址栏没有 hash（按 F5、从书签进、手打网址进都长这样）时，
    // 落到上次所在的视图，而不是无脑回仪表盘 —— 这就是用户报的那个
    // 「每次刷新都回到仪表盘」。没记录过才用仪表盘（首次安装的默认页）。
    switchView(lastRememberedView() || "dashboard");
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
    // 料盘列表以前只在进「料盘库存」页时才拉（见 switchView）——
    // 于是「仪表盘点槽位 → 绑定到哪盘料」「打印记录 → 手动补录」这类
    // 不经过库存页的入口，下拉里可能一个料盘都没有。启动时一并取回。
    await loadSpools().catch(() => {});
    const me = await api("/api/auth/me").catch(() => null);
    if (me) { S.auth.user = me.user; renderUserChip(); }
  } catch (err) {
    if ((err.message || "").includes("登录")) return false;
    toast(err.message, "err");
  }
  connectSocket();
  await applyHashRoute({ initial: true });
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

// 无头自测钩子（tests/test_panel_fill.mjs、tests/test_ui_polish.mjs 直跑 node 校验用，
// 浏览器里没有副作用）。这几组纯函数要么是照着用户反馈改的、要么决定界面显示什么，
// 肉眼很难盯住，钉在这里。
window.panelDebug = {
  fanChannels, filFill, MIN_FILL_PCT,
  // 外观预填、区域文案、机型照片、扫码认码 —— 错了都是「界面看着正常但不对」
  inferFinish, finishFromSeries, finishChoices, regionLabel, printerPhoto, parseScanText,
  // 料盘状态口径 / 排序 / 价格分档 / 概览图：库存页与汇总页共用，必须一致
  spoolUseState, useStateTally, USE_STATE_META, priceBuckets, sortSpools,
  summaryMaterials, donutChart, allSlotEntries, slotKey,
  // 下拉里的料盘候选：余量缺失别显示成 0 g、归档的除非正绑着否则不进候选
  spoolOptionHtml, bindCandidates,
  // 视图路由：刷新要能回到原页面，靠的就是把视图名写进 hash + localStorage 兜底
  // （地址栏没 hash 时，只有 localStorage 那份能救回来）
  VIEW_NAMES, syncHashView, VIEW_STORE_KEY, lastRememberedView, rememberView,
  applyHashRoute,
  // 汇总页钻取与均价：分组口径（norm）必须与后端 _group_summary 一致，
  // 均价的分母必须是「登记过价的盘数」，错了就是跳过去空列表 / 均价被拉低
  SUMMARY_DRILL_FIELDS, summaryPriceStats, priceStatCards, summaryTable,
  // 品牌分布卡与打印记录行内操作（跳转料盘 / 更改料盘）
  renderBrandDist, BRAND_BAR_COLORS, jobRowActions,
  // 槽位绑定：下拉候选、槽位弹窗的解绑入口（解绑要重开同一个槽位弹窗，别跳到料盘页）
  fillBindSpoolSelect, unbindSlotSpool,
  // 全局状态也放出来：候选列表这类函数读 S，自测要能塞数据进去
  state: S,
};

boot();
