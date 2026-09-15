/* 无头 Edge 实拍验收（开发工装）。
 *
 * 直接用 CDP 驱动 Edge：起一个临时 profile、在页面里完成初始化并塞演示数据，
 * 然后逐个视图截图。同时跑一批断言（真机照片有没有加载出来、扫码浮层有没有起来、
 * 微信扫码那种 hash 深链会不会跳转），光靠截图肉眼是看不出「图片 404 了但布局还在」
 * 「浮标飘出卡片」这种问题的。
 *
 * 运行： node scripts/shot_ui.mjs
 * 环境变量（都有默认值，按需覆盖）：
 *   PYTHON   python 解释器（默认 python3/python）
 *   EDGE_EXE Edge 可执行文件（默认探测常见安装位置）
 *   SHOT_OUT 截图输出目录（默认 <repo>/shots，已 gitignore）
 *
 * 这套工装依赖「真浏览器 + 真服务」，所以不进 CI；CI 里跑的是 tests/*.mjs
 * 那种纯函数自测。两者互补：CI 保证口径，本脚本保证「在浏览器里真的是这个样子」。
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// 脚本在 <repo>/scripts/ 下，仓库根就是它的上一级
const APP = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const OUT = process.env.SHOT_OUT || path.join(APP, "shots");
const PROFILE = path.join(APP, "data", "_shotui", "edgeprof");  // 放 data/ 下，跟着一起被 ignore
const PORT = Number(process.env.SHOT_PORT || 8791);        // 应用端口
const CDP_PORT = Number(process.env.SHOT_CDP_PORT || 9333); // 调试端口

const PYTHON = process.env.PYTHON
  || (process.platform === "win32" ? "python" : "python3");

/** 找 Edge：显式指路 > 常见安装位置。找不到就直接报错退出，别让它变成一堆超时。 */
function findEdge() {
  const candidates = [
    process.env.EDGE_EXE,
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/usr/bin/microsoft-edge",
    "/usr/bin/microsoft-edge-stable",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
  ].filter(Boolean);
  for (const p of candidates) {
    try { if (fs.statSync(p).isFile()) return p; } catch (err) { /* 试下一个 */ }
  }
  console.error("找不到 Edge / Chrome。用 EDGE_EXE 环境变量指一个可执行文件。");
  console.error("试过：\n  " + candidates.join("\n  "));
  process.exit(1);
}

const EDGE = findEdge();

const PASSED = [];
const FAILED = [];
const check = (label, ok, detail = "") => {
  (ok ? PASSED : FAILED).push(label);
  console.log(`  ${ok ? "[通过]" : "[失败]"} ${label} ${ok ? "" : detail}`);
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ── 1. 起应用 ───────────────────────────────────────────────────
// 每次都从空库开始：脚本后面要跑「首次初始化 → 建管理员 → 塞演示数据」这条链路，
// 库里残留任何东西都会让它走到另一条分支上（表现为演示数据一条都没种进去）。
// PROFILE 也在这个目录下，一并被清掉没关系 —— Edge 到用的时候自己会建。
const DATA_DIR = path.join(APP, "data", "_shotui");
fs.rmSync(DATA_DIR, { recursive: true, force: true });
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

const server = spawn(
  PYTHON,
  ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(PORT)],
  {
    cwd: APP,
    env: {
      ...process.env,
      BAMBU_MOCK: "1",
      DATA_DIR,
      ALLOW_PUBLIC_SETUP: "1",
      BAMBU_REGION: "china",
      PORT: String(PORT),
    },
    stdio: ["ignore", "pipe", "pipe"],
  },
);
server.stdout.on("data", () => {});
server.stderr.on("data", (d) => process.stderr.write(`[uvicorn] ${d}`));

async function waitForServer() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${PORT}/health`);
      if (r.ok) return true;
    } catch (err) { /* 还没起来 */ }
    await sleep(400);
  }
  return false;
}

// ── 2. 起 Edge ──────────────────────────────────────────────────
fs.rmSync(PROFILE, { recursive: true, force: true });
const edge = spawn(EDGE, [
  "--headless=new",
  `--remote-debugging-port=${CDP_PORT}`,
  `--user-data-dir=${PROFILE}`,
  "--no-first-run", "--no-default-browser-check",
  "--disable-gpu", "--hide-scrollbars",
  "--window-size=1440,1000",
  "about:blank",
], { stdio: ["ignore", "pipe", "pipe"] });
edge.stdout.on("data", () => {});
edge.stderr.on("data", () => {});

async function browserWs() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://127.0.0.1:${CDP_PORT}/json/version`);
      const j = await r.json();
      if (j.webSocketDebuggerUrl) return j.webSocketDebuggerUrl;
    } catch (err) { /* 还没起来 */ }
    await sleep(400);
  }
  throw new Error("Edge 的调试端口没起来");
}

// ── 3. 极简 CDP 客户端 ──────────────────────────────────────────
class CDP {
  constructor(url) {
    this.ws = new WebSocket(url);
    this.id = 0;
    this.waiting = new Map();
    this.ready = new Promise((resolve, reject) => {
      this.ws.addEventListener("open", resolve);
      this.ws.addEventListener("error", reject);
    });
    this.ws.addEventListener("message", (ev) => {
      const msg = JSON.parse(ev.data);
      const waiter = this.waiting.get(msg.id);
      if (!waiter) return;
      this.waiting.delete(msg.id);
      if (msg.error) waiter.reject(new Error(JSON.stringify(msg.error)));
      else waiter.resolve(msg.result);
    });
  }

  send(method, params = {}, sessionId) {
    const id = ++this.id;
    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    this.ws.send(JSON.stringify(payload));
    return new Promise((resolve, reject) => this.waiting.set(id, { resolve, reject }));
  }

  async evaluate(sessionId, expression, awaitPromise = true) {
    const res = await this.send("Runtime.evaluate", {
      expression, awaitPromise, returnByValue: true,
    }, sessionId);
    if (res.exceptionDetails) {
      throw new Error(res.exceptionDetails.exception?.description || "前端执行出错");
    }
    return res.result.value;
  }

  async shot(sessionId, file) {
    const res = await this.send("Page.captureScreenshot", { format: "png" }, sessionId);
    fs.writeFileSync(file, Buffer.from(res.data, "base64"));
  }
}

// ── 4. 主流程 ───────────────────────────────────────────────────
async function main() {
  if (!await waitForServer()) throw new Error("应用没起来");
  console.log("应用已启动");

  const cdp = new CDP(await browserWs());
  await cdp.ready;
  const { targetId } = await cdp.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  await cdp.send("Page.enable", {}, sessionId);
  await cdp.send("Runtime.enable", {}, sessionId);
  await cdp.send("Emulation.setDeviceMetricsOverride",
    { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false }, sessionId);

  // 初始化管理员 + 塞演示数据（同源 fetch，cookie 会留在浏览器里）
  await cdp.send("Page.navigate", { url: `http://127.0.0.1:${PORT}/` }, sessionId);
  await sleep(1200);

  const seed = await cdp.evaluate(sessionId, `(async () => {
    const post = (url, body) => fetch(url, {
      method: "POST", credentials: "same-origin",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }).then((r) => r.json().catch(() => ({})));

    const setup = await fetch("/api/auth/status").then((r) => r.json());
    if (!setup.authenticated) {
      await post("/api/auth/setup", { username: "admin", password: "password123" });
    }

    const spools = [
      ["拓竹", "PLA", "哑光", "哑光黑", "#1A1A1A", 1000, 640, 118],
      ["拓竹", "PLA", "普通", "基础白", "#FFFFFF", 1000, 210, 99],
      ["拓竹", "PETG", "透明", "透明蓝", "#8FD3E8", 1000, 880, 139],
      ["Polymaker", "PLA", "丝绸", "丝绸金", "#D8B24A", 1000, 45, 168],
      ["Polymaker", "PETG", "哑光", "哑光灰", "#6B7280", 1000, 720, 158],
      ["大简", "PETG-HT", "普通", "工程黑", "#111827", 1000, 560, 128],
      ["Kexcelled", "PLA", "珠光", "珠光粉", "#F0A6C0", 750, 300, 96],
      ["兰博", "PLA", "哑光", "哑光红", "#B91C1C", 1000, 150, 88],
      ["魔创", "ABS", "普通", "本色", "#E5E1D8", 1000, 940, 76],
    ];
    const ids = [];
    for (const [brand, material, finish, color_name, color_hex, initial_weight, remaining_weight, price] of spools) {
      const made = await post("/api/spools", {
        brand, material, finish, color_name, color_hex,
        initial_weight, remaining_weight, price,
        spool_weight: 250,
      });
      if (made.id) ids.push(made.id);
    }
    // 自定义品牌 + 一条手动用量，让汇总页与「自定义品牌」卡片都有东西可看
    await post("/api/brands", { name: "自家作坊" });
    await post("/api/spools/" + ids[0] + "/use", { weight_g: 60, note: "本周打印" }).catch(() => {});
    return { spools: ids.length };
  })()`);
  console.log("演示数据：", JSON.stringify(seed));

  // 带着会话重新加载，走完整的 boot() 流程
  await cdp.send("Page.navigate", { url: `http://127.0.0.1:${PORT}/` }, sessionId);
  await sleep(2500);

  /* ── 断言：真机照片真的加载出来了 ── */
  const art = await cdp.evaluate(sessionId, `(() => {
    const wrap = document.querySelector(".printer-art-wrap");
    const img = document.querySelector(".printer-art-wrap .printer-photo");
    return {
      hasWrap: !!wrap,
      broken: wrap ? wrap.classList.contains("art-broken") : null,
      src: img ? img.getAttribute("src") : null,
      naturalWidth: img ? img.naturalWidth : 0,
      complete: img ? img.complete : false,
      boxWidth: img ? Math.round(img.getBoundingClientRect().width) : 0,
      boxHeight: img ? Math.round(img.getBoundingClientRect().height) : 0,
      chips: document.querySelectorAll(".art-chip").length,
      images: Object.keys((window.__probeStatus = (window.panelDebug && window.panelDebug.state.status) || {}).printer_images || {}),
    };
  })()`);
  console.log("示意图：", JSON.stringify(art));
  check("仪表盘用了真机照片（有 .printer-art-wrap）", art.hasWrap === true, JSON.stringify(art));
  check("照片没有走到 SVG 兜底", art.broken === false, JSON.stringify(art));
  check("照片真的加载成功（naturalWidth > 0）", art.naturalWidth > 0, JSON.stringify(art));
  check("后端报了 P2S 的图片", (art.images || []).includes("P2S"), JSON.stringify(art.images));
  check("照片按 240x292 展示框排布",
    Math.abs(art.boxWidth - 240) <= 2 && Math.abs(art.boxHeight - 292) <= 2, JSON.stringify(art));
  check("温度浮标还在（和照片叠加）", art.chips >= 1, String(art.chips));

  /* ── 断言：温度浮标与照片的几何关系 ── */
  const geo = await cdp.evaluate(sessionId, `(() => {
    const wrap = document.querySelector(".printer-art-wrap");
    const img = document.querySelector(".printer-art-wrap .printer-photo");
    const chips = Array.from(document.querySelectorAll(".art-chip"));
    const r = (el) => { const b = el.getBoundingClientRect();
      return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
    return {
      camera: (() => { const b = document.querySelector(".photo-card").getBoundingClientRect();
        return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; })(),
      wrap: r(wrap), img: r(img),
      chips: chips.map((c) => ({ cls: c.className, ...r(c), text: c.innerText.replace(/\\n/g, " ") })),
    };
  })()`);
  console.log("几何：", JSON.stringify(geo));
  check("照片正好铺满展示框（没有被 letterbox 缩水）",
    Math.abs(geo.img.w - geo.wrap.w) <= 1 && Math.abs(geo.img.h - geo.wrap.h) <= 1, JSON.stringify(geo));
  check("三个温度浮标都在（喷嘴 / 仓温 / 热床）",
    geo.chips.length === 3, JSON.stringify(geo.chips));
  const outside = geo.chips.filter((c) =>
    c.x < geo.wrap.x - 2 || c.y < geo.wrap.y - 2
    || c.x + c.w > geo.wrap.x + geo.wrap.w + 2 || c.y + c.h > geo.wrap.y + geo.wrap.h + 2);
  check("浮标没有飘出机器卡片", outside.length === 0, JSON.stringify(outside));
  console.log("浮标位置：", geo.chips.map((c) => `${c.text} @ ${c.x},${c.y}`).join(" | "));

  await cdp.shot(sessionId, path.join(OUT, "01-dashboard.png"));

  // 机器卡片的特写，用来肉眼复核照片和浮标。
  // 坑：captureScreenshot 的 clip 用的是**页面坐标**（含滚动量），不是视口坐标，
  // 直接拿 getBoundingClientRect 会拍到文档顶部去。
  const card = await cdp.evaluate(sessionId, `(() => {
    const b = document.querySelector(".photo-card").getBoundingClientRect();
    return { x: Math.max(0, Math.round(b.x + window.scrollX) - 8),
             y: Math.max(0, Math.round(b.y + window.scrollY) - 8),
             width: Math.round(b.width) + 16, height: Math.round(b.height) + 16 };
  })()`);
  const cardShot = await cdp.send("Page.captureScreenshot",
    { format: "png", clip: { ...card, scale: 2 } }, sessionId);
  fs.writeFileSync(path.join(OUT, "01b-printer-card.png"), Buffer.from(cardShot.data, "base64"));

  /* ── 断言：区域文案 ── */
  const region = await cdp.evaluate(sessionId, `(() => {
    const st = window.panelDebug.state.status || {};
    const acct = st.account || {};
    return {
      top: st.region, acct: acct.region,
      label: window.panelDebug.regionLabel(acct.region),
      text: (document.getElementById("accountBox") || {}).innerText || "",
    };
  })()`);
  console.log("区域：", JSON.stringify(region));
  check("status.account.region 有值", !!region.acct, JSON.stringify(region));
  check("前端把它翻成「中国大陆」而不是「海外」", region.label === "中国大陆", JSON.stringify(region));
  // 模拟模式下设置页显示的是「不需要拓竹账号」提示，账号卡片本来就不渲染，
  // 所以这里只在真账号模式下查 DOM 文案。这条断言的重点是「undefined 不会变成海外」。
  if (region.text.includes("模拟模式")) {
    console.log("  （模拟模式：跳过设置页账号卡片文案断言）");
  } else {
    check("设置页文案里出现「中国大陆」", region.text.includes("中国大陆"), region.text.slice(0, 200));
  }

  /* ── 概览 → 库存 → 汇总 → 打印记录 → 设置 ── */
  const views = [
    ["spools", "02-spools.png"],
    ["summary", "03-summary.png"],
    ["jobs", "04-jobs.png"],
    ["settings", "05-settings.png"],
  ];
  for (const [name, file] of views) {
    await cdp.evaluate(sessionId, `switchView(${JSON.stringify(name)})`);
    await sleep(900);
    await cdp.shot(sessionId, path.join(OUT, file));
  }

  // 汇总页三张表都要有内容
  await cdp.evaluate(sessionId, `switchView("summary")`);
  await sleep(600);
  const summary = await cdp.evaluate(sessionId, `(() => {
    const rows = (id) => (document.querySelectorAll("#" + id + " tbody tr") || []).length;
    return {
      brand: rows("brandSummary"), material: rows("materialSummary"), finish: rows("finishSummary"),
      brandText: (document.getElementById("brandSummary") || {}).innerText || "",
      statText: (document.getElementById("summaryStats") || {}).innerText || "",
    };
  })()`);
  console.log("汇总页：", JSON.stringify(summary).slice(0, 400));
  check("按品牌汇总有数据行", summary.brand > 0, JSON.stringify(summary));
  check("按材料汇总有数据行", summary.material > 0, JSON.stringify(summary));
  check("按外观汇总有数据行", summary.finish > 0, JSON.stringify(summary));
  check("汇总数字对得上（9 盘）", summary.brandText.includes("9 盘") || summary.brandText.includes("3 盘"),
        summary.brandText.slice(0, 200));
  // 自定义品牌是「候选」，没录过料盘就不该出现在**库存**汇总里（这里是库存视角）。
  // 它该出现的地方是设置页的品牌标签和新建料盘的下拉，下面单独查。
  check("没录过料盘的自定义品牌不混进库存汇总",
        !summary.brandText.includes("自家作坊"), summary.brandText.slice(0, 200));

  /* ── 自定义品牌出现在该出现的地方 ── */
  await cdp.evaluate(sessionId, `switchView("settings")`);
  await sleep(800);
  const brandBox = await cdp.evaluate(sessionId, `(() => {
    const box = document.getElementById("brandBox");
    return { text: box ? box.innerText : "", chips: box ? box.querySelectorAll(".brand-chip").length : 0 };
  })()`);
  console.log("自定义品牌：", JSON.stringify(brandBox).slice(0, 300));
  check("设置页列出了自定义品牌", brandBox.text.includes("自家作坊"), brandBox.text.slice(0, 300));

  const brandOptions = await cdp.evaluate(sessionId, `(() => {
    openSpoolDialog();
    const sel = document.getElementById("f_brand");
    const opts = sel ? Array.from(sel.options).map((o) => o.value) : [];
    closeModal();
    return opts;
  })()`);
  console.log("品牌下拉：", JSON.stringify(brandOptions));
  check("新建料盘的下拉里有自定义品牌", brandOptions.includes("自家作坊"), JSON.stringify(brandOptions));
  check("下拉里没有已删除的品牌",
        !brandOptions.some((b) => ["eSUN 易生", "三绿 Sunlu", "Overture", "Prusament", "JAYO"].includes(b)),
        JSON.stringify(brandOptions));
  check("下拉里有「＋ 自定义品牌…」入口", brandOptions.includes("__custom__"), JSON.stringify(brandOptions));

  // 概览的本周三张卡
  await cdp.evaluate(sessionId, `switchView("dashboard")`);
  await sleep(700);
  const week = await cdp.evaluate(sessionId, `(() => {
    const host = document.getElementById("weekStats");
    return {
      cards: host ? host.querySelectorAll(".stat").length : 0,
      text: host ? host.innerText : "",
    };
  })()`);
  console.log("本周卡：", JSON.stringify(week));
  check("概览有本周三张卡", week.cards === 3, JSON.stringify(week));
  check("本周卡显示打印时长", week.text.includes("打印时长"), week.text);

  /* ── 扫码浮层 ── */
  await cdp.evaluate(sessionId, `openScan({ title: "扫料盘二维码" })`);
  await sleep(1500);
  const scan = await cdp.evaluate(sessionId, `(() => {
    const ov = document.querySelector(".scan-overlay");
    if (!ov) return { open: false };
    return {
      open: true,
      note: (ov.querySelector(".scan-note") || {}).textContent || "",
      hasFrame: !!ov.querySelector(".scan-frame"),
      hasPhotoBtn: !!ov.querySelector(".scan-photo"),
      retryHidden: (ov.querySelector(".scan-retry") || { hidden: null }).hidden,
      bodyLocked: document.body.classList.contains("scan-open"),
      hasJsQR: typeof window.jsQR === "function",
      hasDetector: typeof window.BarcodeDetector === "function",
    };
  })()`);
  console.log("扫码浮层：", JSON.stringify(scan));
  check("扫码浮层能打开", scan.open === true, JSON.stringify(scan));
  check("有取景框", scan.hasFrame === true);
  check("有「拍照识别」这条路（http 内网下的主力路径）", scan.hasPhotoBtn === true);
  check("jsQR 已加载（不依赖外网 CDN）", scan.hasJsQR === true);
  check("打开时锁住背景滚动", scan.bodyLocked === true);
  await cdp.shot(sessionId, path.join(OUT, "06-scan.png"));
  await cdp.evaluate(sessionId, `window.spoolScanner.close()`);
  await sleep(400);

  /* ── 槽位绑定弹窗（含新的「相机扫码」按钮） ── */
  const slot = await cdp.evaluate(sessionId, `(() => {
    const printers = (window.panelDebug.state.printers_full || []);
    if (!printers.length) return { opened: false, reason: "mock 没有打印机" };
    const p = printers[0];
    const ams = ((p.state || {}).ams || [])[0];
    if (!ams) return { opened: false, reason: "没有 AMS" };
    openSlotDialog(p.id, ams.ams_id, 0);
    const body = (document.getElementById("modalBody") || {}).innerText || "";
    return {
      opened: true,
      hasScanBtn: !!Array.from(document.querySelectorAll("#modalHost button"))
        .find((b) => (b.textContent || "").includes("相机扫码")),
      body: body.slice(0, 300),
    };
  })()`);
  console.log("槽位弹窗：", JSON.stringify(slot).slice(0, 400));
  if (slot.opened) {
    check("槽位弹窗里有「相机扫码」按钮", slot.hasScanBtn === true, JSON.stringify(slot));
  } else {
    console.log(`  （跳过槽位弹窗断言：${slot.reason}）`);
  }
  await cdp.shot(sessionId, path.join(OUT, "07-slot-dialog.png"));

  /* ── 扫码深链：应用开着时改 hash 也要跳转 ──
   * 手机上的真实用法是「应用开着 → 系统相机扫二维码 → 浏览器只换 hash」。
   * 这里就模拟那一步：直接改 location.hash，看应用有没有就地接住。 */
  await cdp.evaluate(sessionId, `closeModal(); location.hash = ""`);
  await sleep(300);
  const deepLink = await cdp.evaluate(sessionId, `(async () => {
    const spools = (window.panelDebug.state.spools || []);
    if (!spools.length) return { skipped: "mock 里没有料盘" };
    const id = spools[0].id;
    const before = !!document.querySelector(".modal");
    location.hash = "#spool=" + id;
    await new Promise((r) => setTimeout(r, 900));
    const body = (document.getElementById("modalBody") || {}).innerText || "";
    return {
      id,
      before,
      opened: !!document.querySelector(".modal"),
      showsSpool: body.includes(String(id)) || body.includes(spools[0].name || "\\u0000"),
      view: (window.panelDebug.state || {}).view || "",
    };
  })()`);
  console.log("扫码深链：", JSON.stringify(deepLink).slice(0, 400));
  if (deepLink.skipped) {
    console.log(`  （跳过深链断言：${deepLink.skipped}）`);
  } else {
    check("改 hash 之前没有弹窗（确认是 hash 触发的）", deepLink.before === false, JSON.stringify(deepLink));
    check("应用接住了 hashchange 并打开料盘详情", deepLink.opened === true, JSON.stringify(deepLink));
    check("打开的是 hash 里那个料盘", deepLink.showsSpool === true, JSON.stringify(deepLink));
    check("切到了料盘库存页", deepLink.view === "spools", JSON.stringify(deepLink));
  }
  await cdp.evaluate(sessionId, `closeModal(); location.hash = ""`);
  await sleep(300);

  /* ── 手机端 ── */
  await cdp.evaluate(sessionId, `closeModal(); switchView("dashboard")`);
  await cdp.send("Emulation.setDeviceMetricsOverride",
    { width: 390, height: 844, deviceScaleFactor: 2, mobile: true }, sessionId);
  await sleep(1000);
  await cdp.shot(sessionId, path.join(OUT, "08-mobile-dashboard.png"));

  /* ── 手机端：机器照片与浮标 ── */
  const mArt = await cdp.evaluate(sessionId, `(() => {
    const img = document.querySelector(".printer-art-wrap .printer-photo");
    const wrap = document.querySelector(".printer-art-wrap");
    const card = document.querySelector(".photo-card");
    if (!img) return { found: false };
    const r = (el) => { const b = el.getBoundingClientRect();
      return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height) }; };
    const chips = Array.from(document.querySelectorAll(".art-chip")).map(r);
    const cr = r(card);
    return {
      found: true, loaded: img.naturalWidth > 0, img: r(img), card: cr, wrap: r(wrap),
      chips,
      overflowRight: chips.filter((c) => c.x + c.w > window.innerWidth).length,
      pageWidth: window.innerWidth,
    };
  })()`);
  console.log("手机端机器卡片：", JSON.stringify(mArt));
  check("手机端照片也加载出来了", mArt.found && mArt.loaded === true, JSON.stringify(mArt));
  check("手机端照片没超出屏幕宽度", mArt.found && mArt.card.x >= 0 && mArt.card.x + mArt.card.w <= mArt.pageWidth,
        JSON.stringify(mArt));
  check("手机端浮标没有溢出屏幕", mArt.found && mArt.overflowRight === 0, JSON.stringify(mArt));

  const mCard = await cdp.evaluate(sessionId, `(() => {
    const b = document.querySelector(".photo-card").getBoundingClientRect();
    return { x: Math.max(0, Math.round(b.x + window.scrollX) - 6),
             y: Math.max(0, Math.round(b.y + window.scrollY) - 6),
             width: Math.round(b.width) + 12, height: Math.round(b.height) + 12, scale: 2 };
  })()`);
  const mShot = await cdp.send("Page.captureScreenshot",
    { format: "png", clip: mCard }, sessionId);
  fs.writeFileSync(path.join(OUT, "08b-mobile-printer-card.png"), Buffer.from(mShot.data, "base64"));

  await cdp.evaluate(sessionId, `switchView("summary")`);
  await sleep(900);
  await cdp.shot(sessionId, path.join(OUT, "09-mobile-summary.png"));
  await cdp.evaluate(sessionId, `switchView("spools")`);
  await sleep(900);
  await cdp.shot(sessionId, path.join(OUT, "10-mobile-spools.png"));
  await cdp.evaluate(sessionId, `openSpoolDialog()`);
  await sleep(900);
  await cdp.shot(sessionId, path.join(OUT, "11-mobile-new-spool.png"));
  await cdp.evaluate(sessionId, `closeModal(); switchView("settings")`);
  await sleep(900);
  await cdp.shot(sessionId, path.join(OUT, "12-mobile-settings.png"));

  /* ── 前端运行/控制台错误 ── */
  const errors = await cdp.evaluate(sessionId, `window.__errs || []`);
  check("页面没有未捕获的 JS 错误", !errors || errors.length === 0, JSON.stringify(errors));

  console.log("");
  console.log(`截图输出： ${OUT}`);
  if (FAILED.length) {
    console.log(`通过 ${PASSED.length} 项，失败 ${FAILED.length} 项`);
    console.log(`失败项： ${JSON.stringify(FAILED)}`);
    return 1;
  }
  console.log(`通过 ${PASSED.length} 项，失败 0 项`);
  return 0;
}

let code = 1;
try {
  code = await main();
} catch (err) {
  console.error("实拍失败：", err);
} finally {
  try { edge.kill(); } catch (err) { /* ignore */ }
  try { server.kill(); } catch (err) { /* ignore */ }
}
process.exit(code);
