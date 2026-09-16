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
//
// 数据库文件和 Edge profile 分开清：本机安全策略对「一轮里删几百个文件」有上限，
// Edge 的 profile 有三百多个文件，一删就被拦。所以：
//   数据库（几个文件，必须清干净）—— 逐个删，被拦就直接报错，绝不带着旧库往下跑；
//   profile（几百个文件，可留可删）—— 删不掉就复用旧目录，Edge 起得来就行。
const DATA_DIR = path.join(APP, "data", "_shotui");
if (fs.existsSync(DATA_DIR)) {
  for (const name of fs.readdirSync(DATA_DIR)) {
    if (name === "edgeprof") continue;
    fs.rmSync(path.join(DATA_DIR, name), { recursive: true, force: true });
  }
}
try {
  fs.rmSync(PROFILE, { recursive: true, force: true });
} catch (err) {
  console.warn("  [提示] 上次的 Edge profile 没清掉（本机删除配额），直接复用");
}
fs.mkdirSync(DATA_DIR, { recursive: true });
try {
  fs.rmSync(OUT, { recursive: true, force: true });   // 旧截图留着也不影响，删不掉就算了
} catch (err) {
  console.warn("  [提示] 旧截图目录没清掉，直接覆盖同名文件");
}
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

  /** 按页面坐标截一块（可以超出视口，靠 captureBeyondViewport 补画）。
   *  整页很高的区域（比如打印机状态那一大块）用这个，普通截图只有首屏。 */
  async shotClip(sessionId, file, clip) {
    const res = await this.send("Page.captureScreenshot", {
      format: "png", clip, captureBeyondViewport: true,
    }, sessionId);
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
      // 这两种是「库存使用状态」里另外两档的样子：全新未拆封 / 已用尽。
      // 没有它们，概览图上的「未使用 / 消耗完」永远显示 0，看图看不出问题。
      ["兰博", "PLA", "普通", "素白", "#F1F5F9", 1000, 1000, 88],
      ["魔创", "ABS", "普通", "用尽黑", "#1F2937", 1000, 0, 76],
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

  /* ── 断言：打印机状态必须「填满」，右下角不留空白 ──
     风扇卡原先排在左列最后一张，而右列（AMS 单元）通常比左列矮，于是右下角
     空出一大块（用户原话：「这个打印机状态右下角不要空出这么多空白区域」）。
     现在风扇卡排到右列最后并用 flex 撑满，所以这里量两列的底边差 —— 截图看得出
     「有点空」，量不出「差 80px」，还是得断言。 */
  const layout = await cdp.evaluate(sessionId, `(() => {
    const cols = [...document.querySelectorAll(".printer-layout > .printer-col")];
    if (cols.length < 2) return { cols: cols.length };
    const box = (el) => {
      const r = el.getBoundingClientRect();
      return { top: Math.round(r.top), bottom: Math.round(r.bottom) };
    };
    const rightCards = cols[1].querySelectorAll(".pcard");
    const lastRight = rightCards[rightCards.length - 1];
    return {
      cols: cols.length,
      left: box(cols[0]), right: box(cols[1]),
      rightLast: lastRight ? lastRight.className : "",
      fanInRight: !!cols[1].querySelector(".fan-card"),
      fanInLeft: !!cols[0].querySelector(".fan-card"),
      fanRows: cols[1].querySelectorAll(".fan-row").length,
    };
  })()`);
  console.log("打印机布局：", JSON.stringify(layout));
  check("打印机状态是左右两列", layout.cols === 2, JSON.stringify(layout));
  check("风扇卡挪到了右列（AMS 那一边）", layout.fanInRight === true, JSON.stringify(layout));
  check("风扇卡不再占左列", layout.fanInLeft === false, JSON.stringify(layout));
  check("风扇四条通道都渲染出来了", layout.fanRows >= 4, String(layout.fanRows));
  check("风扇卡是右列最后一张（贴着右下角）",
    /fan-card/.test(layout.rightLast || ""), layout.rightLast);
  check("左右两列等高、右下角不留空白（底边差 ≤ 2px）",
    Math.abs(layout.left.bottom - layout.right.bottom) <= 2,
    JSON.stringify([layout.left, layout.right]));

  // 整块特写：这块比视口高，得用 captureBeyondViewport 才拍得全
  const blockClip = await cdp.evaluate(sessionId, `(() => {
    const b = document.querySelector(".printer-block").getBoundingClientRect();
    return { x: Math.max(0, Math.round(b.x + window.scrollX) - 6),
             y: Math.max(0, Math.round(b.y + window.scrollY) - 6),
             width: Math.round(b.width) + 12, height: Math.round(b.height) + 12 };
  })()`);
  await cdp.shotClip(sessionId, path.join(OUT, "01c-printer-block.png"),
    { ...blockClip, scale: 1 });

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

  /* ── 汇总页的库存概览图与价格分布（真 DOM 里量一遍） ──
     沙箱自测只能证明「函数返回的 HTML 对」，这里证明「浏览器真的画出来了、
     点得动、跳得过去」，两边互补。 */
  const overview = await cdp.evaluate(sessionId, `(() => {
    const donut = document.querySelector("#summaryOverview .donut");
    const arcs = document.querySelectorAll("#summaryOverview .donut-arc");
    const items = [...document.querySelectorAll("#summaryOverview .use-item")]
      .map((el) => el.innerText.replace(/\\s+/g, " ").trim());
    const bar = [...document.querySelectorAll("#summaryOverview .use-bar > span")]
      .map((el) => Math.round(el.getBoundingClientRect().width));
    const cards = [...document.querySelectorAll("#priceDist .price-card")];
    const priced = (window.panelDebug.state.summarySpools || [])
      .filter((s) => Number(s.price) > 0).length;
    return {
      hasDonut: !!donut, arcs: arcs.length, items, bar,
      hidden: !!(document.getElementById("overviewClear") || {}).classList.contains("hidden"),
      cards: cards.length,
      cardsSum: cards.reduce((n, c) => {
        const m = c.innerText.match(/数量\\s*(\\d+)/); return n + (m ? Number(m[1]) : 0);
      }, 0),
      priced,
      firstCard: cards[0] ? cards[0].innerText.replace(/\\s+/g, " ").trim() : "",
    };
  })()`);
  console.log("库存概览：", JSON.stringify(overview));
  check("环形图画出来了", overview.hasDonut === true);
  check("环形图每份材料一段弧", overview.arcs >= 2, String(overview.arcs));
  check("使用状态三行都在（未使用 / 使用中 / 消耗完）",
    overview.items.length === 3 && overview.items.join(" ").includes("消耗完"),
    JSON.stringify(overview.items));
  check("使用状态分段条铺满（三段宽度之和 > 0）",
    overview.bar.reduce((a, b) => a + b, 0) > 0, JSON.stringify(overview.bar));
  check("没筛选时不显示「看全部」按钮", overview.hidden === true);
  check("价格分布卡片数量 = 有价格的档数", overview.cards >= 1, String(overview.cards));
  check("各档盘数之和 = 已登记价格的料盘数",
    overview.cardsSum === overview.priced, `${overview.cardsSum} vs ${overview.priced}`);
  check("价格卡片有「数量 / 占比 / 查看明细」",
    overview.firstCard.includes("数量") && overview.firstCard.includes("查看明细"),
    overview.firstCard);

  // 点一个材料图例 -> 只统计那种材料；再点回全部
  const filtered = await cdp.evaluate(sessionId, `(() => {
    const first = document.querySelector("#summaryOverview .legend-item");
    const name = first.innerText.trim();
    first.click();
    const label = (document.getElementById("overviewFilter") || {}).innerText || "";
    const clear = document.getElementById("overviewClear");
    const cards = document.querySelectorAll("#priceDist .price-card").length;
    return { name, label, clearHidden: clear.classList.contains("hidden"), cards };
  })()`);
  await sleep(300);
  await cdp.shot(sessionId, path.join(OUT, "03b-summary-filtered.png"));
  const restored = await cdp.evaluate(sessionId, `(() => {
    document.getElementById("overviewClear").click();
    return { label: (document.getElementById("overviewFilter") || {}).innerText || "" };
  })()`);
  console.log("材料筛选：", JSON.stringify(filtered), "→", JSON.stringify(restored));
  check("点材料图例后显示「已筛选：X」",
    filtered.label.includes("已筛选") && filtered.label.includes(filtered.name), JSON.stringify(filtered));
  check("筛选后出现「看全部」按钮", filtered.clearHidden === false);
  check("点「看全部」能还原", restored.label === "", JSON.stringify(restored));

  /* ── 料盘库存：表头排序、行内快捷操作、已用尽标签页 ── */
  await cdp.evaluate(sessionId, `switchView("spools")`);
  await sleep(700);
  const spoolUI = await cdp.evaluate(sessionId, `(() => {
    const P = window.panelDebug;
    const bodies = () => [...document.querySelectorAll("#spoolTable tbody tr")];
    const ids = () => bodies().map((tr) => tr.cells[0].innerText.trim());
    const remOf = (list) => list.map((id) => {
      const s = (P.state.spools || []).find((x) => String(x.id) === id) || {};
      return Number(s.remaining_weight) || 0;
    });
    const heads = [...document.querySelectorAll("#spoolTable th.sortable")]
      .map((th) => th.innerText.replace(/\\s+/g, " ").trim());
    const remHead = [...document.querySelectorAll("#spoolTable th.sortable")]
      .find((th) => th.innerText.includes("剩余"));

    const before = ids();
    remHead.click();
    const descIds = ids(); const desc = remOf(descIds);
    const descArrow = [...document.querySelectorAll("#spoolTable th.sortable")]
      .find((th) => th.innerText.includes("剩余")).innerText.replace(/\\s+/g, " ").trim();
    remHead.click();
    const ascIds = ids(); const asc = remOf(ascIds);

    const actions = [...document.querySelectorAll("#spoolTable tbody tr:first-child .row-actions button")]
      .map((b) => b.innerText.trim());
    const tabs = [...document.querySelectorAll("#spoolTabs .tab")].map((b) => b.innerText.trim());

    // 已用尽标签页：条数必须跟同一套口径算出来的一致
    const emptyTab = [...document.querySelectorAll("#spoolTabs .tab")]
      .find((b) => b.innerText.includes("已用尽"));
    const expectedEmpty = (P.state.spools || [])
      .filter((x) => !x.archived && P.spoolUseState(x) === "empty").length;
    emptyTab.click();
    const emptyRows = bodies().length;
    const tabActive = [...document.querySelectorAll("#spoolTabs .tab.active")]
      .map((b) => b.innerText.trim()).join(",");
    // 收敛到「所有」以免影响后面的截图
    [...document.querySelectorAll("#spoolTabs .tab")]
      .find((b) => b.innerText.includes("所有")).click();
    return {
      heads, before, descIds, ascIds, descArrow, actions, tabs,
      descOk: desc.every((v, i) => i === 0 || desc[i - 1] >= v),
      ascOk: asc.every((v, i) => i === 0 || asc[i - 1] <= v),
      expectedEmpty, emptyRows, tabActive,
    };
  })()`);
  console.log("料盘表：", JSON.stringify(spoolUI).slice(0, 500));
  check("表头有 4 个可排序的列（ID / 价格 / 剩余 / 使用时间）",
    spoolUI.heads.length === 4 && spoolUI.heads.join(" ").includes("剩余")
    && spoolUI.heads.join(" ").includes("价格"), JSON.stringify(spoolUI.heads));
  check("点「剩余」表头后按余量降序", spoolUI.descOk === true, spoolUI.descIds.join(","));
  check("再点一次切成升序", spoolUI.ascOk === true, spoolUI.ascIds.join(","));
  check("排序箭头跟着方向变（↓ / ↑）", /↓|↑/.test(spoolUI.descArrow), spoolUI.descArrow);
  check("每行有「详情 / 绑定 / 克隆」三个快捷入口",
    ["详情", "绑定", "克隆"].every((k) => spoolUI.actions.includes(k)),
    JSON.stringify(spoolUI.actions));
  check("状态标签页里有「已用尽」", spoolUI.tabs.includes("已用尽"), JSON.stringify(spoolUI.tabs));
  check("「已用尽」标签页筛出来的条数与同一套口径算出来的一致",
    spoolUI.emptyRows === spoolUI.expectedEmpty,
    `${spoolUI.emptyRows} vs ${spoolUI.expectedEmpty}`);
  check("点标签页会高亮它自己", spoolUI.tabActive === "已用尽", spoolUI.tabActive);

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
  await cdp.evaluate(sessionId, `closeModal()`);

  /* ── 从料盘这一侧管槽位绑定（料盘行里的「绑定」按钮） ──
     反向路径：手里拿着这盘料，直接选槽位绑上去 / 从槽位上解绑。 */
  const bindDlg = await cdp.evaluate(sessionId, `(() => {
    const spools = (window.panelDebug.state.spools || []).filter((s) => !s.archived);
    if (!spools.length) return { opened: false, reason: "没有料盘" };
    const target = spools[0];
    openBindSpoolDialog(target.id);
    const rows = [...document.querySelectorAll("#modalHost .bind-row")];
    return {
      opened: true, name: target.name, rows: rows.length,
      labels: rows.map((r) => (r.querySelector(".bind-slot") || {}).innerText || ""),
      buttons: rows.map((r) => (r.querySelector("button") || {}).innerText || ""),
      title: (document.querySelector("#modalHost h3") || {}).innerText || "",
    };
  })()`);
  console.log("料盘侧绑定弹窗：", JSON.stringify(bindDlg).slice(0, 400));
  check("料盘行能打开绑定弹窗", bindDlg.opened === true, JSON.stringify(bindDlg));
  check("弹窗标题带上料盘名",
    bindDlg.title && bindDlg.title.includes(bindDlg.name || ""), bindDlg.title);
  check("列出了 mock 的全部槽位（AMS 4 + HT 1 + 外挂 1）",
    bindDlg.rows === 6, JSON.stringify(bindDlg.labels));
  check("槽位名带单元前缀（AMS A 槽位 1 / HT A 槽位 1），不是两个 A1 撞在一起",
    bindDlg.labels.some((x) => x.includes("AMS A 槽位 1"))
    && bindDlg.labels.some((x) => x.includes("HT A 槽位 1"))
    && !bindDlg.labels.some((x) => /129/.test(x)),
    JSON.stringify(bindDlg.labels));
  check("未绑定的槽位给出「绑到这盘」按钮",
    bindDlg.buttons.filter((b) => b === "绑到这盘").length === bindDlg.rows,
    JSON.stringify(bindDlg.buttons));
  await cdp.shot(sessionId, path.join(OUT, "08-bind-spool.png"));

  // 真的绑一个，看那一行会不会翻成「解绑」
  await cdp.evaluate(sessionId, `document.querySelector("#modalHost .bind-row button").click()`);
  await sleep(1500);
  const bound = await cdp.evaluate(sessionId, `(() => {
    const rows = [...document.querySelectorAll("#modalHost .bind-row")];
    return {
      mine: rows.filter((r) => r.className.includes("mine")).length,
      firstBtn: rows[0] ? (rows[0].querySelector("button") || {}).innerText || "" : "",
    };
  })()`);
  console.log("绑定后：", JSON.stringify(bound));
  check("绑定成功后那一行翻成已绑定（按钮变成解绑）",
    bound.mine === 1 && bound.firstBtn === "解绑", JSON.stringify(bound));

  // 解绑回去，别给后面的截图留状态
  await cdp.evaluate(sessionId, `document.querySelector("#modalHost .bind-row button").click()`);
  await sleep(1500);
  const unbound = await cdp.evaluate(sessionId, `(() => {
    const rows = [...document.querySelectorAll("#modalHost .bind-row")];
    return { mine: rows.filter((r) => r.className.includes("mine")).length };
  })()`);
  check("解绑后没有已绑定的行了", unbound.mine === 0, JSON.stringify(unbound));
  await cdp.evaluate(sessionId, `closeModal()`);

  /* ── 克隆料盘（料盘行里的「克隆」按钮） ── */
  const clone = await cdp.evaluate(sessionId, `(() => {
    const s = (window.panelDebug.state.spools || []).filter((x) => !x.archived)[0];
    const val = (id) => (document.getElementById(id) || {}).value || "";
    openCloneSpoolDialog(s.id);
    return {
      title: (document.querySelector("#modalHost h3") || {}).innerText || "",
      brand: val("f_brand"), material: val("f_material"),
      color: val("f_color_name"), hex: val("f_color_hex"),
      remaining: val("f_remaining_weight"), price: val("f_price"),
      src: { brand: s.brand, material: s.material, color: s.color_name,
             hex: s.color_hex, initial: s.initial_weight, price: s.price,
             remaining: s.remaining_weight },
    };
  })()`);
  console.log("克隆：", JSON.stringify(clone).slice(0, 300));
  check("克隆弹窗标题是「克隆料盘」", clone.title === "克隆料盘", clone.title);
  check("品牌 / 材料 / 颜色都带过来了",
    clone.brand === clone.src.brand && clone.material === clone.src.material
    && clone.color === clone.src.color, JSON.stringify(clone));
  check("颜色值与价格也带过来了",
    String(clone.hex).toUpperCase() === String(clone.src.hex).toUpperCase()
    && Number(clone.price) === Number(clone.src.price), JSON.stringify(clone));
  check("余量按满盘算（不是照抄原料盘的余量）",
    Number(clone.remaining) === Number(clone.src.initial),
    `克隆 ${clone.remaining} vs 满盘 ${clone.src.initial}`);
  await cdp.evaluate(sessionId, `closeModal()`);

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
    // 「这个 id 到底是哪盘料」以接口为准 —— 列表可能正按别的键排序，
    // 拿 spools[0] 当答案会把「跳错料盘」放过去。
    const want = await (await fetch("/api/spools/" + id)).json();
    location.hash = "#spool=" + id;
    await new Promise((r) => setTimeout(r, 900));
    // 弹窗标题就是料盘名（openModal 的第一个参数），body 里只有数字，
    // 之前用 body.includes(id) 是碰运气（重量里正好有个 "11" 就过）。
    const title = ((document.querySelector(".modal h3") || {}).textContent || "").trim();
    return {
      id,
      before,
      opened: !!document.querySelector(".modal"),
      want: want.name,
      title,
      showsSpool: title === want.name,
      view: (window.panelDebug.state || {}).view || "",
    };
  })()`);
  console.log("扫码深链：", JSON.stringify(deepLink).slice(0, 400));
  if (deepLink.skipped) {
    console.log(`  （跳过深链断言：${deepLink.skipped}）`);
  } else {
    check("改 hash 之前没有弹窗（确认是 hash 触发的）", deepLink.before === false, JSON.stringify(deepLink));
    check("应用接住了 hashchange 并打开料盘详情", deepLink.opened === true, JSON.stringify(deepLink));
    check("打开的是 hash 里那个料盘（弹窗标题 = 该 id 的料盘名）", deepLink.showsSpool === true, JSON.stringify(deepLink));
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
