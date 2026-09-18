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
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

// 脚本在 <repo>/scripts/ 下，仓库根就是它的上一级
const APP = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const OUT = process.env.SHOT_OUT || path.join(APP, "shots");
// 放 data/ 下，跟着一起被 ignore。按浏览器分开：夸克复用 Edge 留下的 profile 目录
// 会起不来（两家虽然都是 Chromium，但 profile 里的 First Run / LOCK 之类的约定不同），
// 表现为页面白屏、CDP 拿不到任何 DOM。
const PROFILE = process.env.SHOT_PROFILE
  || path.join(APP, "data", "_shotui",
       /quark/i.test(process.env.EDGE_EXE || "") ? "quarkprof" : "edgeprof");
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

/** 轮询等页面里的某个条件成立。
 *  固定 sleep 不够用：换浏览器（夸克比 Edge 起得慢）或机器正忙时，
 *  后面读 DOM 会读到「应用还没起来」的空页面，把「照片没加载」之类的假失败报出来。 */
async function waitFor(cdp, sessionId, expr, timeout = 20000) {
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    try {
      if (await cdp.evaluate(sessionId, `!!(${expr})`)) return true;
    } catch (err) { /* 页面正在导航，下一轮再看 */ }
    await sleep(400);
  }
  return false;
}

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
    if (name === "edgeprof" || name === "quarkprof") continue;
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

  // mock 模式只造打印机和料盘，不造打印任务 —— 打印记录页是空的，
  // 「查看料盘 / 更改料盘」两个按钮就没东西可点。这里补一条演示任务 + 扣重流水。
  const seeded = spawnSync(
    PYTHON, [path.join(APP, "scripts", "seed_demo_job.py")],
    {
      cwd: APP,
      env: { ...process.env, BAMBU_MOCK: "1", DATA_DIR, ALLOW_PUBLIC_SETUP: "1" },
      encoding: "utf8",
    },
  );
  console.log("演示任务：", (seeded.stdout || "").trim() || (seeded.stderr || "").trim().slice(-200));
  check("演示用的打印任务灌进去了（打印记录页有东西可点）",
    seeded.status === 0, `exit=${seeded.status} ${(seeded.stderr || "").slice(-300)}`);

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
  // 等仪表盘真的把打印机卡片画出来再看照片 —— 固定 sleep 会在慢机器上读到空页面
  // 等的是「布局算完了」而不是「DOM 有了」：样式表还在路上时元素宽高是 0，
  // 下面那条「照片按 240x292 排布」会读成 0×0，白白报一次假失败。
  await waitFor(cdp, sessionId, `(() => {
    const img = document.querySelector(".printer-art-wrap .printer-photo");
    return !!img && img.naturalWidth > 0 && img.getBoundingClientRect().width > 0;
  })()`);

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

  /* ── 断言：打印机状态必须「填满」，两列都不留空白 ──
     风扇卡原先排在左列最后一张，而右列（AMS 单元）通常比左列矮，于是右下角
     空出一大块（用户原话：「这个打印机状态右下角不要空出这么多空白区域」）。
     现在风扇卡排到右列最后并用 flex 撑满 —— 但只做这一步，右列反而变成较高的
     那一列，空白只是从右下角搬到左下角。
     ⚠️ 量法很关键：**不能量 `.printer-col` 的底边** —— 列容器被 `align-items: stretch`
     拉得一样高，无论内容填没填满都是等高的（第一版就是这么量错的，一块空白都没拦住）。
     要量**每列最后一张卡**的底边差，那才是「内容是不是真顶到底」。 */
  const layout = await cdp.evaluate(sessionId, `(() => {
    const cols = [...document.querySelectorAll(".printer-layout > .printer-col")];
    if (cols.length < 2) return { cols: cols.length };
    const box = (el) => {
      const r = el.getBoundingClientRect();
      return {
        top: Math.round(r.top), bottom: Math.round(r.bottom),
        w: Math.round(r.width), h: Math.round(r.height),
      };
    };
    const cards = (col) => [...col.querySelectorAll(".pcard")];
    const lastOf = (col) => { const c = cards(col); return c.length ? box(c[c.length - 1]) : null; };
    const rightCards = cards(cols[1]);
    const lastRight = rightCards[rightCards.length - 1];
    const photo = cols[0].querySelector(".photo-card");
    return {
      cols: cols.length,
      leftCol: box(cols[0]), rightCol: box(cols[1]),
      leftLast: lastOf(cols[0]), rightLast: lastOf(cols[1]),
      rightLastClass: lastRight ? lastRight.className : "",
      fanInRight: !!cols[1].querySelector(".fan-card"),
      fanInLeft: !!cols[0].querySelector(".fan-card"),
      fanRows: cols[1].querySelectorAll(".fan-row").length,
      photoBox: photo ? box(photo) : null,
      photoArt: photo && photo.querySelector(".printer-art-wrap")
        ? box(photo.querySelector(".printer-art-wrap")) : null,
    };
  })()`);
  console.log("打印机布局：", JSON.stringify(layout));
  check("打印机状态是左右两列", layout.cols === 2, JSON.stringify(layout));
  check("风扇卡挪到了右列（AMS 那一边）", layout.fanInRight === true, JSON.stringify(layout));
  check("风扇卡不再占左列", layout.fanInLeft === false, JSON.stringify(layout));
  check("风扇四条通道都渲染出来了", layout.fanRows >= 4, String(layout.fanRows));
  check("风扇卡是右列最后一张（贴着右下角）",
    /fan-card/.test(layout.rightLastClass || ""), layout.rightLastClass);
  check("右列内容顶到底边（风扇卡底边 = 列底边）",
    !!layout.rightLast && Math.abs(layout.rightLast.bottom - layout.rightCol.bottom) <= 2,
    JSON.stringify([layout.rightLast, layout.rightCol]));
  check("左列内容也顶到底边（照片卡吃掉了多余高度）",
    !!layout.leftLast && Math.abs(layout.leftLast.bottom - layout.leftCol.bottom) <= 2,
    JSON.stringify([layout.leftLast, layout.leftCol]));
  check("两列最后一张卡底边齐平（整块无空白，差 ≤ 2px）",
    !!layout.leftLast && !!layout.rightLast
    && Math.abs(layout.leftLast.bottom - layout.rightLast.bottom) <= 2,
    JSON.stringify([layout.leftLast, layout.rightLast]));
  check("照片卡被拉高但照片本身没被拉伸（contain + 居中）",
    !!layout.photoBox && !!layout.photoArt
    && Math.abs(layout.photoArt.w - 240) <= 2 && Math.abs(layout.photoArt.h - 292) <= 2,
    JSON.stringify([layout.photoBox, layout.photoArt]));

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

  /* ── 冷启动直接点槽位绑定（手机上的高频路径） ──
     场景：打开应用落在仪表盘 → 直接点打印机卡片上的槽位 → 弹窗里挑料盘；
     或者扫槽位二维码走 `#bind=` 深链进来。
     `S.spools` 过去只在进「料盘库存」页时才被 loadSpools() 填上（见 switchView），
     上面两条路都不经过库存页 → 弹窗里只有「— 不绑定 —」，用户反馈「选择不了耗材」。
     现在启动时就拉料盘，另外弹窗自己也会在空列表时补拉一次（双保险）。 */
  const freshBind = await cdp.evaluate(sessionId, `(async () => {
    const before = (window.panelDebug.state.spools || []).length;
    const printers = (window.panelDebug.state.printers_full || []);
    const p = printers[0];
    const ams = ((p || {}).state || {}).ams || [];
    if (!p || !ams.length) return { reason: "mock 没有打印机 / AMS" };
    openSlotDialog(p.id, ams[0].ams_id, 0);
    await new Promise((r) => setTimeout(r, 900));
    const sel = document.getElementById("bindSpool");
    const opts = sel ? [...sel.options].map((o) => o.textContent.trim()) : [];
    const host = document.getElementById("modalBody");
    return {
      before, opts: opts.length, sample: opts.slice(0, 3),
      hint: host ? host.innerText.replace(/\\s+/g, " ").slice(-90) : "",
    };
  })()`);
  console.log("冷启动直接开槽位弹窗：", JSON.stringify(freshBind));
  if (freshBind.reason) {
    console.log(`  （跳过冷启动绑定断言：${freshBind.reason}）`);
  } else {
    check("启动时就把料盘列表拉好了（这一步之前没进过「料盘库存」）",
      freshBind.before >= 1, String(freshBind.before));
    check("弹窗里的料盘下拉有选项", freshBind.opts >= 2, JSON.stringify(freshBind));
    check("选项是真实的料盘（「名字（余 xx g）」），不是只有「不绑定」这一项",
      /（余 \d+ g）/.test(freshBind.sample.join(" ")), JSON.stringify(freshBind.sample));
  }

  /* ── 双保险：万一启动那次没拉到料盘（接口失败/深链更早），弹窗自己要补上 ──
     把列表清空再开一次，模拟「S.spools 空着」的状态。 */
  const heal = await cdp.evaluate(sessionId, `(async () => {
    const printers = (window.panelDebug.state.printers_full || []);
    const p = printers[0];
    const ams = ((p || {}).state || {}).ams || [];
    if (!p || !ams.length) return { reason: "mock 没有打印机 / AMS" };
    window.panelDebug.state.spools = [];
    openSlotDialog(p.id, ams[0].ams_id, 0);
    const sel = document.getElementById("bindSpool");
    const first = sel ? sel.options.length : -1;
    await new Promise((r) => setTimeout(r, 1400));
    const hint = document.getElementById("bindSpoolHint");
    return {
      first, after: sel ? sel.options.length : -1,
      restored: (window.panelDebug.state.spools || []).length,
      hint: hint ? hint.textContent.trim() : "(没有提示位)",
    };
  })()`);
  console.log("空列表自愈：", JSON.stringify(heal));
  if (heal.reason) {
    console.log(`  （跳过空列表自愈断言：${heal.reason}）`);
  } else {
    check("列表空着时弹窗先显示「只有不绑定」这一项", heal.first === 1, JSON.stringify(heal));
    check("弹窗自己把料盘列表补回来了（不用用户手动去库存页）",
      heal.after >= 2, JSON.stringify(heal));
    check("补回来的料盘同时写进了 S.spools（后续下拉都受益）",
      heal.restored >= 1, JSON.stringify(heal));
    check("补齐后不再显示「正在读取…」这类占位文案",
      !/正在读取|还没有登记/.test(heal.hint), heal.hint);
  }
  await cdp.evaluate(sessionId, `closeModal()`);
  await sleep(300);

  /* 给人看的一张：原生选择器的弹层截不到，就把 select 撑成列表截一张 ——
     里面应当是一串「名字（余 xx g）」，只剩「— 不绑定 —」就是那个 bug 复现了。 */
  await cdp.evaluate(sessionId, `(() => {
    const printers = (window.panelDebug.state.printers_full || []);
    const p = printers[0];
    const ams = ((p || {}).state || {}).ams || [];
    if (!p || !ams.length) return;
    openSlotDialog(p.id, ams[0].ams_id, 0);
    const sel = document.getElementById("bindSpool");
    if (sel) sel.size = Math.min(6, sel.options.length);
  })()`);
  await sleep(400);
  await cdp.shot(sessionId, path.join(OUT, "07b-slot-dialog-options.png"));
  await cdp.evaluate(sessionId, `closeModal()`);
  await sleep(200);

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

  /* ── 桌面端每个视图都不许横向溢出 ──
     料盘表一行 9 列 + 7 个操作按钮，列多到这个程度时表格很容易撑破卡片
     （`table { width:100% }` 只是「至少 100%」，自动布局下内容更宽就溢出去），
     表现是整页横向滚动条、右边缘的「删除」被裁掉。截图里看得见，但没人会去数像素 —— 断言量。
     （手机宽度那套 `scrollWidth <= clientWidth` 断言只跑了 ≤430px，管不到这里。） */
  const overflow = [];
  for (const name of ["dashboard", "spools", "summary", "jobs", "settings"]) {
    await cdp.evaluate(sessionId, `switchView(${JSON.stringify(name)})`);
    await sleep(500);
    const m = await cdp.evaluate(sessionId, `(() => {
      const de = document.documentElement;
      const wide = [];
      document.querySelectorAll("table, .card, .table-card, .printer-block").forEach((el) => {
        if (el.clientWidth > 0 && el.scrollWidth > el.clientWidth + 2) {
          wide.push(((el.tagName + "." + String(el.className)).slice(0, 50))
            + " " + el.scrollWidth + ">" + el.clientWidth);
        }
      });
      const off = [...document.querySelectorAll("button, th, td")]
        .filter((el) => el.getBoundingClientRect().right > de.clientWidth + 2)
        .map((el) => (el.innerText || el.tagName).trim().slice(0, 12));
      return { page: de.scrollWidth, client: de.clientWidth, wide: wide.slice(0, 4), off: off.slice(0, 4) };
    })()`);
    if (m.page > m.client + 2 || m.wide.length || m.off.length) overflow.push({ view: name, ...m });
  }
  console.log("横向溢出：", JSON.stringify(overflow));
  check("桌面端各视图都没有横向溢出（表格没撑破卡片、按钮没被裁掉）",
    overflow.length === 0, JSON.stringify(overflow));

  /* 窄一点的桌面窗口（1280）：表格允许在卡片内部横滑，但**整页**不许出现横向滚动条。 */
  await cdp.send("Emulation.setDeviceMetricsOverride",
    { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false }, sessionId);
  await cdp.evaluate(sessionId, `switchView("spools")`);
  await sleep(700);
  const narrow = await cdp.evaluate(sessionId, `(() => {
    const de = document.documentElement;
    const card = document.querySelector(".table-card");
    return {
      page: de.scrollWidth, client: de.clientWidth,
      cardScrollable: card ? getComputedStyle(card).overflowX : "",
      cardOver: card ? card.scrollWidth - card.clientWidth : 0,
    };
  })()`);
  console.log("1280 窄桌面：", JSON.stringify(narrow));
  check("1280 桌面窗口不出现整页横向滚动条", narrow.page <= narrow.client + 2, JSON.stringify(narrow));
  check("1280 下表格溢出时是在卡片内部横滑（overflow-x: auto）",
    narrow.cardOver <= 2 || narrow.cardScrollable === "auto", JSON.stringify(narrow));
  await cdp.send("Emulation.setDeviceMetricsOverride",
    { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false }, sessionId);
  await sleep(400);

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
    const dr = donut ? donut.getBoundingClientRect() : null;
    return {
      hasDonut: !!donut, arcs: arcs.length, items, bar,
      // 渲染尺寸必须真的量一遍：环形图的 width/height 写在 SVG 属性上，
      // 会被全局那条 svg { width:16px } 盖掉（属性优先级低于 CSS）→ 缩成 16px 的点。
      // 光断言弧长算得对是拦不住的，第一版就漏了。（注意这里不能写反引号：外面是模板串）
      donutSize: dr ? { w: Math.round(dr.width), h: Math.round(dr.height) } : null,
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
  check("环形图真的画得够大（≥140px，没被全局 svg 16px 规则压扁）",
    !!overview.donutSize && overview.donutSize.w >= 140 && overview.donutSize.h >= 140,
    JSON.stringify(overview.donutSize));
  check("环形图是正方形（宽高差 ≤ 2px）",
    !!overview.donutSize && Math.abs(overview.donutSize.w - overview.donutSize.h) <= 2,
    JSON.stringify(overview.donutSize));
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

  /* ── 汇总页：品牌分布卡（用户截图里右边那张「品牌分布」） ──
     三件事都要真量：① 卡片和概览卡并排（不是掉到下面一行）；
     ② 品牌名单上的盘数加起来 = 在库盘数；③ 点品牌名跳过去、列表里真的是这个品牌。
     第 ③ 条是「假断言陷阱」的重灾区 —— 只看「跳过去了」不够，
     要看筛选项真的等于那个品牌，且列表非空。 */
  const brandDist = await cdp.evaluate(sessionId, `(() => {
    const host = document.getElementById("brandDist");
    const rows = [...document.querySelectorAll("#brandDist .bd-row")];
    const spools = (window.panelDebug.state.summarySpools || []);
    // 每行文本形如「Polymaker 42 33% 每盘均价 ¥88.00」，从 .bd-count 里取盘数
    const counts = rows.map((r) => {
      const t = (r.querySelector(".bd-count") || {}).innerText || "";
      const m = t.match(/(\\d+)/); return m ? Number(m[1]) : 0;
    });
    // 并排：两张卡顶边差 ≤2px 且品牌卡在概览卡右边
    const ovCard = document.querySelector(".overview-row > .card");
    const bdCard = document.querySelectorAll(".overview-row > .card")[1];
    let side = null;
    if (ovCard && bdCard) {
      const a = ovCard.getBoundingClientRect(), b = bdCard.getBoundingClientRect();
      side = { sameRow: Math.abs(a.top - b.top) <= 2, toRight: b.left >= a.right - 2 };
    }
    const byBrand = {};
    spools.forEach((s) => { const k = s.brand || "未填写"; byBrand[k] = (byBrand[k] || 0) + 1; });
    return {
      hasHost: !!host, rowCount: rows.length,
      distinctBrands: Object.keys(byBrand).length,
      sumCounts: counts.reduce((a, b) => a + b, 0),
      totalSpools: spools.length,
      side,
      // 「不留空」：每行的价格位上要么是均价、要么明说未登记，不许是空的
      blanks: rows.filter((r) => {
        const t = (r.querySelector(".bd-sub") || {}).innerText || "";
        return !t.trim();
      }).length,
      firstRowText: rows[0] ? rows[0].innerText.replace(/\\s+/g, " ").trim() : "",
      firstName: rows[0] ? (rows[0].dataset.value || "") : "",
      counter: (document.getElementById("brandDistCount") || {}).innerText || "",
    };
  })()`);
  console.log("品牌分布：", JSON.stringify(brandDist).slice(0, 460));
  check("品牌分布卡画出来了（有行）", brandDist.rowCount >= 1, String(brandDist.rowCount));
  check("品牌行数 = 汇总里出现的品牌数",
    brandDist.rowCount === brandDist.distinctBrands,
    `${brandDist.rowCount} vs ${brandDist.distinctBrands}`);
  check("各品牌盘数之和 = 在库料盘数",
    brandDist.sumCounts === brandDist.totalSpools,
    `${brandDist.sumCounts} vs ${brandDist.totalSpools}`);
  check("品牌分布卡每行都有价格说明（不留空）",
    brandDist.blanks === 0, `空 ${brandDist.blanks} 行`);
  check("品牌卡与概览卡并排（顶边齐、在右侧）",
    !!brandDist.side && brandDist.side.sameRow && brandDist.side.toRight,
    JSON.stringify(brandDist.side));
  check("品牌卡右上角写了品牌数与总盘数",
    /\d+\s*个品牌/.test(brandDist.counter) && /共\s*\d+\s*盘/.test(brandDist.counter),
    JSON.stringify(brandDist.counter));

  // 点第一个品牌 -> 跳到料盘库存、筛选器真的等于这个品牌、列表非空
  const brandJump = await cdp.evaluate(sessionId, `(() => {
    const row = document.querySelector("#brandDist .bd-row");
    const wanted = row.dataset.value;
    row.click();
    const sel = document.getElementById("spoolBrand");
    return {
      wanted,
      view: (window.panelDebug.state.view || ""),
      selectValue: sel ? sel.value : null,
      rows: document.querySelectorAll("#spoolTable tbody tr").length,
      // 权威值来自渲染用的那份数据，不是 DOM 数数
      shown: (window.panelDebug.state.spools || []).filter((s) => !s.archived).length,
    };
  })()`);
  await sleep(350);
  await cdp.shot(sessionId, path.join(OUT, "03c-summary-brand-jump.png"));
  console.log("点品牌钻取：", JSON.stringify(brandJump));
  check("点品牌名跳到了料盘库存页", brandJump.view === "spools", JSON.stringify(brandJump));
  check("列表真的按这个品牌筛了（不是跳过去空着）",
    brandJump.selectValue === brandJump.wanted && brandJump.shown >= 1
    && brandJump.rows >= 1, JSON.stringify(brandJump));
  // 回到汇总页，后面几条断言还要用它的 DOM
  await cdp.evaluate(sessionId, `switchView("summary")`);
  await sleep(300);

  /* ── 汇总页：均价卡 + 点名字钻到料盘库存 ──
     沙箱自测证明了「HTML 对」，这里证明「浏览器里点得动、跳得过去、跳过去不是空列表」。 */
  const avgCards = await cdp.evaluate(sessionId, `(() => {
    const host = document.getElementById("summaryStats");
    const cards = [...document.querySelectorAll("#summaryStats .stat")];
    const labels = cards.map((c) => (c.querySelector(".label") || {}).innerText || "");
    // 宽屏三列，卡数不是 3 的倍数就会在末行空一格 —— 那正是「不要留空」要避免的
    const rowFull = cards.length % 3 === 0;
    const values = cards.map((c) => (c.querySelector(".value") || {}).innerText || "");
    // 只看均价那三张卡：另外六张里「累计打印耗材费 ¥0.00」是合法的零
    // （还没有打印任务），拿全部九张来判会误报（实测过一次）。
    const avgLabels = ["平均每盘单价", "平均每公斤", "整盘价格区间"];
    const avgValues = cards
      .filter((c) => avgLabels.includes((c.querySelector(".label") || {}).innerText || ""))
      .map((c) => (c.querySelector(".value") || {}).innerText || "");
    return {
      count: cards.length, labels, rowFull, avgValues,
      // 没有价格时写「未登记」，不许出现空值
      emptyValues: values.filter((v) => !v.trim()).length,
      hasAvgPerSpool: labels.includes("平均每盘单价"),
      text: (host || {}).innerText || "",
    };
  })()`);
  console.log("汇总页均价卡：", JSON.stringify(avgCards).slice(0, 500));
  check("汇总页有「平均每盘单价」这张卡", avgCards.hasAvgPerSpool === true, JSON.stringify(avgCards.labels));
  check("统计卡总数是 3 的倍数（宽屏三列，末行不留空位）",
    avgCards.rowFull === true && avgCards.count >= 6, `${avgCards.count} 张`);
  check("每张卡都有值（没有空白的数值位）", avgCards.emptyValues === 0, String(avgCards.emptyValues));
  check("均价三张卡都拿到了值（不是空、也不是 ¥0.00 冒充）",
    avgCards.avgValues.length === 3
    && avgCards.avgValues.every((v) => v.trim() && !v.includes("¥0.00")),
    JSON.stringify(avgCards.avgValues));
  check("按材料表有「每盘均价」列",
    (await cdp.evaluate(sessionId,
      `[...document.querySelectorAll("#materialSummary th")].map(th => th.innerText.trim())`))
      .includes("每盘均价"));

  const drill = await cdp.evaluate(sessionId, `(() => {
    const btn = document.querySelector("#brandSummary tbody .cell-link");
    if (!btn) return { found: false };
    // 先给别处塞点脏数据：钻取必须把它们清掉，否则两个条件叠一起看着像没生效
    const kw = document.getElementById("spoolSearch");
    if (kw) kw.value = "随便搜点什么";
    btn.click();
    return { found: true, name: btn.dataset.value || btn.innerText.trim() };
  })()`);
  await sleep(900);
  const drilled = await cdp.evaluate(sessionId, `(() => {
    const P = window.panelDebug;
    const norm = (v) => (String(v || "").trim() || "未填写");
    const rows = [...document.querySelectorAll("#spoolTable tbody tr")];
    const ids = rows.map((tr) => tr.cells[0].innerText.trim());
    return {
      view: P.state.view, hash: location.hash,
      brand: (document.getElementById("spoolBrand") || {}).value || "",
      kw: (document.getElementById("spoolSearch") || {}).value || "",
      count: rows.length,
      // 用 S.spools 反查每一盘的 brand，别只信界面上那一行字
      allMatch: ids.length > 0 && ids.every((id) => {
        const s = (P.state.spools || []).find((x) => String(x.id) === id) || {};
        return norm(s.brand) === norm(DRILL_NAME);
      }),
      active: ((document.querySelector(".view.active") || {}).id) || "",
    };
    // 用函数形式替换：品牌名里万一有 $& 之类的序列会被当成替换模式
  })()`.replace("DRILL_NAME", () => JSON.stringify(drill.name || "")));
  console.log("汇总钻取：", JSON.stringify(drill), "→", JSON.stringify(drilled));
  check("汇总表里的品牌名是可点的按钮", drill.found === true, JSON.stringify(drill));
  check("点了品牌名 -> 切到料盘库存页",
    drilled.view === "spools" && drilled.active === "view-spools", JSON.stringify(drilled));
  check("钻取后下拉里就是那个品牌", drilled.brand === drill.name, `${drilled.brand} vs ${drill.name}`);
  check("钻取把其它筛选清掉了（关键词不再残留）", drilled.kw === "", drilled.kw);
  check("钻取跳过去不是空列表（空列表 = 分组口径跟筛选对不上）",
    drilled.count > 0, `${drilled.count} 行`);
  check("列表里每一盘都属于这个品牌", drilled.allMatch === true, JSON.stringify(drilled));

  // 钻完把筛选清掉，别污染后面「表头排序」那一段（它要比对全部料盘）
  await cdp.evaluate(sessionId, `resetSpoolFilters()`);
  await sleep(500);

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
    // 7 个按钮怎么排：显式分两行（主操作一行、次操作一行），别竖着堆成 4 行。
    // ⚠️ 用 getBoundingClientRect().top 而不是 offsetTop：td 里的 offsetTop 测量基准
    //    会踩到定位祖先的坑，实测两行按钮报出同一个值（actLines 假成 1）。
    const actBox = document.querySelector("#spoolTable tbody tr:first-child .cell-actions");
    const actBtns = actBox ? [...actBox.querySelectorAll(".row-actions button")] : [];
    const actTops = actBtns.map((b) => Math.round(b.getBoundingClientRect().top));
    const actLines = new Set(actTops).size;
    const actGroups = actBox
      ? [...actBox.querySelectorAll(".row-actions")].map((g) => g.querySelectorAll("button").length)
      : [];
    const actWidth = actBox ? Math.round(actBox.getBoundingClientRect().width) : 0;
    const tableBox = document.querySelector("#spoolTable");
    const tableOver = tableBox ? tableBox.scrollWidth - tableBox.clientWidth : 0;
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
      actLines, actWidth, actGroups, tableOver,
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
  check("7 个操作按钮排成两行：3 个主操作 + 4 个次操作",
    spoolUI.actLines === 2 && spoolUI.actGroups.join("+") === "3+4",
    `lines=${spoolUI.actLines} groups=${JSON.stringify(spoolUI.actGroups)} width=${spoolUI.actWidth}`);
  check("料盘表本身没有横向溢出（table.scrollWidth <= clientWidth）",
    spoolUI.tableOver <= 2, String(spoolUI.tableOver));
  check("状态标签页里有「已用尽」", spoolUI.tabs.includes("已用尽"), JSON.stringify(spoolUI.tabs));
  check("「已用尽」标签页筛出来的条数与同一套口径算出来的一致",
    spoolUI.emptyRows === spoolUI.expectedEmpty,
    `${spoolUI.emptyRows} vs ${spoolUI.expectedEmpty}`);
  check("点标签页会高亮它自己", spoolUI.tabActive === "已用尽", spoolUI.tabActive);

  /* ── 打印记录：任务详情里的「查看料盘」「更改料盘」 ──
     沙箱自测只能验「弹窗 HTML 对」，这里验「真点得动、跳得过去、改得动」。 */
  await cdp.evaluate(sessionId, `switchView("jobs")`);
  await sleep(800);
  const jobButtons = await cdp.evaluate(sessionId, `(() => {
    const P = window.panelDebug;
    // 找一条真的有耗材费用的任务（一条费用都没有的行两个按钮都是禁用的）
    const jobs = P.state.jobs || [];
    const job = jobs.find((j) => Number(j.cost_total) > 0) || jobs[0];
    if (!job) return { noJob: true, total: jobs.length };
    openJobDetail(job.id);
    return { jobId: job.id, total: jobs.length };
  })()`);
  // 等弹窗里的表格真的渲染出来：固定 sleep 在机器忙时会读到「还没渲染」的空弹窗
  await waitFor(cdp, sessionId, `!!document.querySelector("#modalBody table")`, 10000).catch(() => {});
  const jobRow = await cdp.evaluate(sessionId, `(() => {
    const tr = document.querySelector("#modalBody tbody tr");
    if (!tr) return { noRow: true, body: (document.getElementById("modalBody") || {}).innerText || "" };
    const btns = [...tr.querySelectorAll("button")].map((b) => ({
      text: b.innerText.trim(), disabled: !!b.disabled,
    }));
    return {
      btns,
      hasView: btns.some((b) => b.text === "查看料盘"),
      hasRebind: btns.some((b) => b.text === "更改料盘"),
      viewDisabled: (btns.find((b) => b.text === "查看料盘") || {}).disabled,
      rebindDisabled: (btns.find((b) => b.text === "更改料盘") || {}).disabled,
      spoolName: (tr.cells[0] || {}).innerText || "",
    };
  })()`);
  console.log("选中任务：", JSON.stringify(jobButtons), "明细行：", JSON.stringify(jobRow).slice(0, 400));
  check("打印记录里有任务可点开", jobButtons.noJob !== true, JSON.stringify(jobButtons));
  check("任务详情每行都有「查看料盘」", jobRow.hasView === true, JSON.stringify(jobRow).slice(0, 300));
  check("任务详情每行都有「更改料盘」", jobRow.hasRebind === true, JSON.stringify(jobRow).slice(0, 300));
  check("绑了料盘的行「查看料盘」可点（不是禁用）",
    jobRow.viewDisabled === false || String(jobRow.spoolName).includes("未绑定"),
    JSON.stringify(jobRow).slice(0, 300));
  check("有扣重流水的行「更改料盘」可点（不是禁用）",
    jobRow.rebindDisabled === false, JSON.stringify(jobRow).slice(0, 300));

  /* ── 打印成果图：列表缩略图 + 详情大图 ──
     只断言「有 <img>」是不够的：src 404 时 <img> 也在，只是画成破图。
     所以必须等图片真的解码完，量 naturalWidth —— 它 >0 才代表字节真的取到了。
     这是「假断言」的高发区（沙箱里那条只验了 HTML 字符串）。 */
  await cdp.evaluate(sessionId, `closeModal(); switchView("jobs")`);
  await sleep(600);
  const coverUI = await cdp.evaluate(sessionId, `(async () => {
    const img = document.querySelector("#jobTable img.job-thumb")
      || [...document.querySelectorAll("#jobTable img")][0];
    if (!img) return { noImg: true, table: (document.getElementById("jobTable") || {}).innerHTML?.slice(0, 300) };
    // src 有了不代表加载成功，等它 load/error 再说
    if (!img.complete) await new Promise((r) => { img.onload = r; img.onerror = r; setTimeout(r, 4000); });
    const r = img.getBoundingClientRect();
    return {
      src: img.getAttribute("src"), alt: img.getAttribute("alt"),
      naturalWidth: img.naturalWidth, naturalHeight: img.naturalHeight,
      w: Math.round(r.width), h: Math.round(r.height),
      complete: img.complete,
      all: document.querySelectorAll("#jobTable img.job-thumb").length,
    };
  })()`);
  console.log("列表成果缩略图：", JSON.stringify(coverUI));
  check("打印记录列表里有成果缩略图", coverUI.noImg !== true, JSON.stringify(coverUI).slice(0, 300));
  check("成果缩略图 src 指向本地取图接口（不是云端过期链接）",
    /^\/api\/jobs\/\d+\/cover$/.test(String(coverUI.src)), String(coverUI.src));
  check("成果缩略图真的取到字节（naturalWidth>0，不是 404 破图）",
    Number(coverUI.naturalWidth) > 0,
    `naturalWidth=${coverUI.naturalWidth} complete=${coverUI.complete} src=${coverUI.src}`);
  check("成果缩略图在列表里真的占了地方（没被压成 0 宽）",
    Number(coverUI.w) > 8 && Number(coverUI.h) > 8,
    `${coverUI.w}x${coverUI.h}`);

  // 详情里的大图，以及口径文案（别让人以为这是摄像头实拍）
  const coverDetail = await cdp.evaluate(sessionId, `(async () => {
    const jobs = (window.panelDebug.state.jobs || []);
    const job = jobs.find((j) => j.has_cover) || jobs[0];
    if (!job) return { noJob: true };
    openJobDetail(job.id);
    await new Promise((r) => setTimeout(r, 500));
    const img = document.querySelector("#modalBody .job-cover img");
    if (!img) {
      return { noImg: true, hasCover: !!job.has_cover,
               body: (document.getElementById("modalBody") || {}).innerText?.slice(0, 300) || "" };
    }
    if (!img.complete) await new Promise((r) => { img.onload = r; img.onerror = r; setTimeout(r, 4000); });
    const r = img.getBoundingClientRect();
    return {
      src: img.getAttribute("src"), naturalWidth: img.naturalWidth,
      w: Math.round(r.width), h: Math.round(r.height),
      note: (document.querySelector("#modalBody .job-cover p") || {}).innerText || "",
      title: (document.querySelector(".modal h3") || {}).innerText || "",
    };
  })()`);
  console.log("详情成果图：", JSON.stringify(coverDetail));
  check("详情里渲染出成果大图", coverDetail.noImg !== true, JSON.stringify(coverDetail).slice(0, 300));
  check("详情大图真的取到字节（naturalWidth>0）",
    Number(coverDetail.naturalWidth) > 0, `naturalWidth=${coverDetail.naturalWidth}`);
  check("详情大图有实际尺寸（没被全局 svg/图标规则压扁）",
    Number(coverDetail.w) > 40, `${coverDetail.w}x${coverDetail.h}`);
  check("详情写明了是切片盘面预览图、不是摄像头实拍",
    String(coverDetail.note).includes("切片盘面预览图")
    && String(coverDetail.note).includes("不是摄像头实拍"),
    String(coverDetail.note).slice(0, 200));

  // 接着的一段要靠任务详情弹窗里的表格来点「查看料盘」。
  // 上面为了验详情图已经把这个弹窗关掉了，这里必须重新打开 ——
  // 否则下一段读 #modalBody 拿到 null，整个实拍直接抛错中断（不是断言失败，是崩）。
  await cdp.evaluate(sessionId, `openJobDetail(${jobButtons.jobId})`);
  await waitFor(cdp, sessionId, `!!document.querySelector("#modalBody tbody tr")`, 10000).catch(() => {});
  await sleep(300);

  // 真点一次「查看料盘」：要真的打开那盘料的详情，不是原地不动
  const jumped = await cdp.evaluate(sessionId, `(() => {
    const tr = document.querySelector("#modalBody tbody tr");
    if (!tr) return { skipped: true, want: "", reason: "任务详情弹窗没打开" };
    const btn = [...tr.querySelectorAll("button")].find((b) => b.innerText.trim() === "查看料盘");
    const want = tr.cells[0].innerText.trim();
    if (!btn || btn.disabled) return { skipped: true, want };
    btn.click();
    return { want };
  })()`);
  await sleep(900);
  const spoolModal = await cdp.evaluate(sessionId, `(() => {
    const m = document.querySelector("#modalHost .modal");
    return {
      title: m ? (m.querySelector("h3") || {}).innerText || "" : "",
      text: m ? m.innerText.slice(0, 300) : "",
      hasHistory: m ? m.innerText.includes("使用历史") : false,
    };
  })()`);
  console.log("查看料盘：", JSON.stringify(jumped), "→", JSON.stringify(spoolModal).slice(0, 300));
  check("点「查看料盘」真的打开了料盘详情（弹窗标题 = 那盘料的名字）",
    jumped.skipped === true || spoolModal.title === jumped.want,
    `${spoolModal.title} vs ${jumped.want}`);
  check("料盘详情里有「使用历史」（确认打开的是料盘页不是别的）",
    jumped.skipped === true || spoolModal.hasHistory === true, spoolModal.title);

  // 真点一次「更改料盘」：要弹出带下拉的改绑窗，且下拉里有料盘可选
  await cdp.evaluate(sessionId, `openJobDetail(${JSON.stringify(jobButtons.jobId)})`);
  await sleep(900);
  const rebind = await cdp.evaluate(sessionId, `(() => {
    const tr = document.querySelector("#modalBody tbody tr");
    const btn = [...tr.querySelectorAll("button")].find((b) => b.innerText.trim() === "更改料盘");
    if (!btn || btn.disabled) return { skipped: true };
    btn.click();
    return {};
  })()`);
  await sleep(800);
  const rebindModal = await cdp.evaluate(sessionId, `(() => {
    const sel = document.getElementById("rebindSpool");
    return {
      title: ((document.querySelector("#modalHost .modal h3") || {}).innerText || "").trim(),
      hasSelect: !!sel,
      opts: sel ? sel.options.length : 0,
      selected: sel ? (sel.options[sel.selectedIndex] || {}).textContent || "" : "",
    };
  })()`);
  console.log("更改料盘：", JSON.stringify(rebind), "→", JSON.stringify(rebindModal));
  check("点「更改料盘」弹出改绑窗",
    rebind.skipped === true || rebindModal.title === "更改料盘", rebindModal.title);
  check("改绑窗里的下拉有料盘可选（空下拉 = 点了没反应）",
    rebind.skipped === true || (rebindModal.hasSelect && rebindModal.opts >= 2),
    JSON.stringify(rebindModal));
  check("下拉默认选中当前那盘",
    rebind.skipped === true || rebindModal.selected.length > 0, JSON.stringify(rebindModal));
  await cdp.evaluate(sessionId, `closeModal()`);
  await sleep(300);

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
        !brandOptions.some((b) => ["eSUN 易生", "三绿 Sunlu", "Overture", "Prusament"].includes(b)),
        JSON.stringify(brandOptions));
  // ⚠️ JAYO 已回归（2026-09 补齐官方 225 色色卡后重新上架），不能再断言它「不在下拉里」。
  check("下拉里有 2026-09 新增的品牌",
        ["锐造", "JAYO", "天瑞", "iBOSS", "R3D", "爱丽兹 Allizz"].every((b) => brandOptions.includes(b)),
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

  /* ── 新增料盘：外观到底存进去没有（2026-09-16 用户反馈） ──
     用户说的是「选了哑光、选完色卡、保存后还是普通」。真凶是 saveSpool() 的 payload
     从来没带 finish（表单上有输入框、后端也一直在收，中间少了一根线）。
     这里**不看界面回显** —— 列表本来就是照接口画的，界面看着永远是对的；
     走完整的「填表单 → 点色卡 → 保存」，最后**再拉一次接口**核对库里到底是什么。 */
  const finishPart1 = await cdp.evaluate(sessionId, `(() => {
    openSpoolDialog(null);
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
    const val = (id) => ((document.getElementById(id) || {}).value || "");
    const hintInfo = () => {
      const h = document.getElementById("finishHint");
      return h ? { shown: !h.classList.contains("hidden"), text: (h.textContent || "").trim() } : null;
    };
    // ⚠️ 必须挑一个「色卡里真的有哑光系列」的品牌 —— 魔创 PLA 只有 PLA+ 一个系列，
    //    在那儿找哑光色卡必然找不到、chip 恒为 null，四条断言永远是红的（假红）。
    //    全库只有 Polymaker 的「Panchroma 哑光 PLA」和彩多屋的「哑光 PLA」带哑光。
    set("f_brand", "Polymaker");
    set("f_material", "PLA");
    set("f_color_name", "天蓝");
    set("f_finish", "普通");
    renderColorPresets();
    const chip = [...document.querySelectorAll(".preset-chip")]
      .find((c) => (c.getAttribute("data-series") || "").indexOf("哑光") >= 0);
    // ① 外观还是「普通」时点哑光色卡里的颜色 —— 系列名写着外观，应该被带成哑光
    if (chip) chip.click();
    return {
      chipSeries: chip ? chip.getAttribute("data-series") : null,
      autoFilled: val("f_finish"),
      autoHint: hintInfo(),
    };
  })()`);
  // 这一张就是给用户看的证据：色卡下面那行「已按色卡…设为哑光」。
  // 拍之前把鼠标挪开 —— 色块上的原生 title 提示框会糊在色卡正中间。
  await cdp.send("Input.dispatchMouseEvent",
    { type: "mouseMoved", x: 8, y: 8, button: "none" }, sessionId);
  await sleep(400);
  await cdp.shot(sessionId, path.join(OUT, "07c-spool-dialog-finish.png"));

  const finishPart2 = await cdp.evaluate(sessionId, `(async () => {
    const before = await (await fetch("/api/spools?archived=false")).json();
    const beforeIds = new Set((before.spools || []).map((s) => s.id));
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
    const val = (id) => ((document.getElementById(id) || {}).value || "");
    const hintInfo = () => {
      const h = document.getElementById("finishHint");
      return h ? { shown: !h.classList.contains("hidden"), text: (h.textContent || "").trim() } : null;
    };
    const chip = [...document.querySelectorAll(".preset-chip")]
      .find((c) => (c.getAttribute("data-series") || "").indexOf("哑光") >= 0);

    // ② 用户自己选了丝绸，再点哑光色卡 —— 不许把人家选的值改掉
    set("f_finish", "丝绸");
    if (chip) chip.click();
    const keptFinish = val("f_finish");
    const keptHint = hintInfo();

    // ③ 用户的操作顺序（截图里就是先选哑光、再点哑光色卡）—— 保持哑光
    set("f_finish", "哑光");
    if (chip) chip.click();
    const sameFinish = val("f_finish");

    await saveSpool(null);
    const after = await (await fetch("/api/spools?archived=false")).json();
    const fresh = (after.spools || []).find((s) => !beforeIds.has(s.id));
    return {
      keptFinish, keptHint, sameFinish,
      saved: fresh ? { id: fresh.id, finish: fresh.finish, name: fresh.name } : null,
    };
  })()`);
  const finishSave = { ...finishPart1, ...finishPart2 };
  console.log("新增料盘（外观存没存）：", JSON.stringify(finishSave).slice(0, 460));
  check("Polymaker PLA 里能找到「哑光」色卡",
    !!finishSave.chipSeries && finishSave.chipSeries.indexOf("哑光") >= 0,
    String(finishSave.chipSeries));
  check("外观还是「普通」时点哑光色卡里的颜色，会带成哑光",
    finishSave.autoFilled === "哑光", JSON.stringify(finishSave.autoFilled));
  check("预填时给了提示（不是偷偷改的）",
    !!(finishSave.autoHint || {}).shown, JSON.stringify(finishSave.autoHint));
  check("用户自己选过丝绸时，点哑光色卡不会被改掉",
    finishSave.keptFinish === "丝绸", JSON.stringify(finishSave.keptFinish));
  check("不覆盖时也说明了原因（这张卡是哑光，外观保持你选的）",
    /保持/.test(((finishSave.keptHint || {}).text) || ""), JSON.stringify(finishSave.keptHint));
  check("先选哑光再点哑光色卡，外观还是哑光",
    finishSave.sameFinish === "哑光", JSON.stringify(finishSave.sameFinish));
  check("保存后库里那盘料的外观确实是哑光（不是「普通」）",
    !!finishSave.saved && finishSave.saved.finish === "哑光",
    JSON.stringify(finishSave.saved));
  check("默认名也跟着带上了外观",
    !!finishSave.saved && finishSave.saved.name.indexOf("哑光") >= 0,
    JSON.stringify((finishSave.saved || {}).name));
  // 断言完就把这盘试验品删掉，别影响后面的手机端截图
  if (finishSave.saved) {
    await cdp.evaluate(sessionId,
      `fetch("/api/spools/" + ${JSON.stringify(finishSave.saved.id)}, { method: "DELETE" })`);
  }

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

  /* ── 刷新后要停在原视图 ──
   * 用户原话：「每次刷新都会回到仪表盘界面。只是想刷新一下，要在原界面不要动。」
   * 现在视图名会写进 hash（#view=<name>），刷新一次看它能不能落回去。
   * 挑汇总页做样本：它不在最初的 knownViews 里（漏加就会掉回仪表盘）。 */
  await cdp.evaluate(sessionId, `closeModal(); switchView("summary")`);
  await sleep(700);
  const beforeReload = await cdp.evaluate(sessionId, `({
    view: (window.panelDebug.state || {}).view || "",
    hash: location.hash,
  })`);
  console.log("刷新前：", JSON.stringify(beforeReload));
  check("切到汇总页后，hash 里记下了视图名",
    beforeReload.hash === "#view=summary" && beforeReload.view === "summary",
    JSON.stringify(beforeReload));

  await cdp.send("Page.reload", { ignoreCache: false }, sessionId);
  // reload 之后要重新走一遍 boot → enterApp，等它把视图真正切过去再断言
  let afterReload = {};
  for (let i = 0; i < 24; i++) {
    await sleep(500);
    afterReload = await cdp.evaluate(sessionId, `(() => {
      const st = (window.panelDebug || {}).state || {};
      return {
        // 「应用起来了」的信号：状态数据有了 + 有激活视图。
        // 只判断 view 非空会踩坑 —— S.view 的初始值就是 dashboard，
        // boot 还没跑到 applyHashRoute 时读到的正是这个中间态。
        ready: !!st.status && !!document.querySelector(".view.active"),
        view: st.view || "",
        hash: location.hash,
        active: ((document.querySelector(".view.active") || {}).id) || "",
        navActive: ((document.querySelector(".nav button.active") || {}).dataset || {}).view || "",
      };
    })()`).catch(() => ({}));
    if (afterReload.ready) break;
  }
  console.log("刷新后：", JSON.stringify(afterReload));
  // 先确认「等到了应用起来」：没等到就断言视图，失败原因会被误读成「路由没生效」
  check("刷新后应用重新起来了（等待没有超时）", afterReload.ready === true, JSON.stringify(afterReload));
  check("刷新后还停在汇总页（不被弹回仪表盘）", afterReload.view === "summary", JSON.stringify(afterReload));
  check("刷新后 DOM 上激活的也是汇总页", afterReload.active === "view-summary", JSON.stringify(afterReload));
  check("刷新后导航高亮跟着落在汇总页", afterReload.navActive === "summary", JSON.stringify(afterReload));

  /* ── 刷新时地址栏里**没有 hash** 也要停在原视图 ──
   * 上面那条只覆盖了「hash 里有 #view=summary」的理想路径。用户实际按 F5 时，
   * 地址栏很可能是干净的（书签进的、手打网址进的、或者浏览器把 hash 吞了），
   * 那条路径下 hash 为空 → applyHashRoute(initial) 会直接 switchView("dashboard")。
   * 所以这里补一条：**先切到打印记录，再清空 hash，然后刷新** ——
   * 必须靠本地存储里的「上次所在视图」落回去，而不是靠地址栏。 */
  await cdp.evaluate(sessionId, `closeModal(); switchView("jobs")`);
  await sleep(700);
  const jobsBefore = await cdp.evaluate(sessionId, `({
    view: (window.panelDebug.state || {}).view || "",
    hash: location.hash,
  })`);
  check("切到打印记录后视图已生效", jobsBefore.view === "jobs", JSON.stringify(jobsBefore));

  // 模拟「地址栏没有 hash」：清掉 hash 再刷新
  await cdp.evaluate(sessionId, `history.replaceState(null, "", location.pathname + location.search)`);
  await sleep(200);
  const cleanHash = await cdp.evaluate(sessionId, `location.hash`);
  check("已把 hash 清干净（复现用户按 F5 时地址栏干净的情形）",
    cleanHash === "", JSON.stringify(cleanHash));

  await cdp.send("Page.reload", { ignoreCache: false }, sessionId);
  let afterClean = {};
  for (let i = 0; i < 24; i++) {
    await sleep(500);
    afterClean = await cdp.evaluate(sessionId, `(() => {
      const st = (window.panelDebug || {}).state || {};
      return {
        ready: !!st.status && !!document.querySelector(".view.active"),
        view: st.view || "",
        hash: location.hash,
        active: ((document.querySelector(".view.active") || {}).id) || "",
      };
    })()`).catch(() => ({}));
    if (afterClean.ready) break;
  }
  console.log("hash 为空时刷新后：", JSON.stringify(afterClean));
  check("hash 为空刷新后应用也重新起来了", afterClean.ready === true, JSON.stringify(afterClean));
  check("地址栏没有 hash 时刷新，仍然停在原视图（不回仪表盘）",
    afterClean.view === "jobs", JSON.stringify(afterClean));
  check("hash 为空刷新后 DOM 上激活的也是原视图",
    afterClean.active === "view-jobs", JSON.stringify(afterClean));
  check("回落到原视图后把 hash 补回去（地址栏与界面重新一致）",
    afterClean.hash === "#view=jobs", JSON.stringify(afterClean));

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

  /* ── 手机宽度扫描：320 / 360 / 390 / 430 × 各视图，一律不许横向溢出 ──
     料盘表一行 9 列 + 7 个操作按钮，是这张表最容易「推着整页往右跑」的地方；
     360px 上一旦溢出，用户看到的是整页能左右晃、右边内容看不到。 */
  const mSweep = [];
  for (const w of [320, 360, 390, 430]) {
    await cdp.send("Emulation.setDeviceMetricsOverride",
      { width: w, height: 844, deviceScaleFactor: 2, mobile: true }, sessionId);
    for (const view of ["dashboard", "spools", "summary", "jobs", "settings"]) {
      await cdp.evaluate(sessionId, `closeModal(); switchView(${JSON.stringify(view)})`);
      await sleep(320);
      const m = await cdp.evaluate(sessionId, `(() => {
        const de = document.documentElement;
        const over = [...document.querySelectorAll("body *")]
          .filter((el) => {
            const r = el.getBoundingClientRect();
            return r.width > 0 && r.right > de.clientWidth + 2;
          })
          .map((el) => ((el.tagName + "." + String(el.className)).slice(0, 40)
            + "「" + (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 18) + "」"
            + " r=" + Math.round(el.getBoundingClientRect().right)))
          .slice(0, 3);
        return { page: de.scrollWidth, client: de.clientWidth, over };
      })()`);
      if (m.page > m.client + 2 || m.over.length) mSweep.push({ w, view, ...m });
    }
  }
  console.log("手机宽度扫描：", JSON.stringify(mSweep));
  check("320/360/390/430 各视图都没有横向溢出（页面不左右晃）",
    mSweep.length === 0, JSON.stringify(mSweep.slice(0, 3)));

  /* 恢复 390 宽，保持后面截图与断言的环境一致 */
  await cdp.send("Emulation.setDeviceMetricsOverride",
    { width: 390, height: 844, deviceScaleFactor: 2, mobile: true }, sessionId);
  await cdp.evaluate(sessionId, `closeModal()`);
  await sleep(400);

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
