/* 标签光栅打包自测（node 直跑，不需要浏览器）。
 *
 * label.js 是给浏览器写的 IIFE，这里用 vm 把它跑在一个最小沙箱里，
 * 只补 window / document / localStorage 这几个它加载时会碰到的全局，
 * 然后校验 labelDebug 暴露出来的纯函数。
 *
 * 为什么要测这一层：
 *   01 位打包与 ESC/POS 报文是整条链路里唯一「错了就默默打出白纸」的部分，
 *   而它又最难靠肉眼发现 —— 浏览器里预览是对的，发出去可能是空的。
 *   所以把位序（MSB-first）、行宽（字节对齐）、浓度阈值的边界钉死。
 *
 * 运行： node tests/test_label_raster.mjs
 */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const SRC = path.join(ROOT, "app", "static", "label.js");

const PASSED = [];
const FAILED = [];

function check(label, condition, detail = "") {
  if (condition) {
    PASSED.push(label);
    console.log(`  [通过] ${label}`);
  } else {
    FAILED.push(label);
    console.log(`  [失败] ${label} ${detail}`);
  }
}

/* ── 载入 label.js ──────────────────────────────────────────── */
const store = new Map();
const sandbox = {
  console,
  setTimeout,
  clearTimeout,
  Uint8Array,
  Uint8ClampedArray,
  Array,
  Object,
  Math,
  JSON,
  Number,
  String,
  Boolean,
  Error,
  Date,
  Promise,
  parseInt,
  parseFloat,
  isNaN,
  document: { getElementById: () => null, createElement: () => ({ style: {}, getContext: () => null }) },
  localStorage: {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
  },
  navigator: {},
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(SRC, "utf8"), sandbox, { filename: "label.js" });

const { mm2dot, packRaster, buildEscPosJob, buildJobParts, rasterCommands, effHeightMm, rasterRowsFor } = sandbox.labelDebug || {};

/* ── 0.12.22 → 0.12.25：默认流必须 = 已验证形态 ───────────── */
function testDefaultCfgSafe() {
  console.log("== 默认配置安全（0.12.22 起，0.12.25 扩充） ==");
  const cfg = sandbox.labelDebug.loadCfg();
  check("默认 bandRows=0（不分带，回已验证形态）", cfg.bandRows === 0, JSON.stringify(cfg));
  check("默认 blankSkip=false（不发 ESC J，断链头号嫌疑）", cfg.blankSkip === false);
  check("默认 pipeline=false（并发 GATT 断链，0.12.21 定案）", cfg.pipeline === false);
  check("默认 resetFirst=true（不发复位实测打不出来）", cfg.resetFirst === true);
  // 0.12.25：多一次头部 = 多一次定位动作（会进纸）。用户实测「第二张没有头部，位置反而是对的」。
  check("默认 perCopyPos=false（每份不再补头部）", cfg.perCopyPos === false, String(cfg.perCopyPos));
  // 0.12.27：拆开发送被真机证伪（等待 1200ms → 卡在发送 24% + 掉线），拆分降级为实验。
  check("默认 headWaitMs=0（不拆不等 = 0.12.23 已验证形态）",
    cfg.headWaitMs === 0, String(cfg.headWaitMs));
  check("默认 copyDelayMs=1500（多份之间留打印时间，这份固件一份一份地打）",
    cfg.copyDelayMs === 1500, String(cfg.copyDelayMs));
  const src = fs.readFileSync(SRC, "utf8");
  check("旧存档迁移：cfgRev 不一致时强制重置实验开关与时间旋钮",
    /cfgRev !== CFG_REV/.test(src) && /const CFG_REV = 4;/.test(src) &&
      /cfg\.headWaitMs = 0;/.test(src) && /cfg\.perCopyPos = false;/.test(src));
}

/* ── 0.12.27：蓝牙动作互斥 + 重发阈值 ─────────────────────── */
function testBleGuards() {
  console.log("== 蓝牙动作互斥与重发阈值（0.12.27） ==");
  const src = fs.readFileSync(SRC, "utf8");
  check("存在统一的蓝牙动作互斥锁 bleBusyBlock", /function bleBusyBlock\(what\)/.test(src));
  // 每个会碰 GATT 的动作都必须过这把锁 —— 漏一个就等于留一条掐链路的路
  // （0.12.26 真实事故：「查询状态」当时没有锁，打印中一点就掉链路）
  const body = (name) => {
    const i = src.indexOf("function " + name + "(");
    return i < 0 ? "" : src.slice(i, src.indexOf("\n  }", i) + 4);
  };
  for (const fn of ["labelBleProbe", "labelBleConnect", "labelBleDisconnect",
                    "labelBleReset", "labelBleAlign", "labelBleFeedTest", "labelBleRaw"]) {
    const b = body(fn);
    check(`${fn} 有 busy 守卫`, b.length > 0 && /bleBusyBlock\(/.test(b),
      b ? b.slice(0, 60) : "找不到该函数");
  }
  check("打印入口 labelPrintBle 自己不套互斥锁（它就是持锁方）",
    !/bleBusyBlock\(/.test(body("labelPrintBle")));
  // 重发阈值：只在这份作业几乎没发出去时才自动重连重发；已发过大半就别再灌第二份
  // （0.12.25 丢了这条阈值 → 「卡在 24%」被自动重发 + 断开重连放大成「卡死 + 蓝牙掉了」）
  check("发送中断后按进度阈值决定是否自动重发（pct >= 0.05 就不再重发）",
    /pct >= 0\.05/.test(body("labelPrintBle")));
  check("不做自动重发时给出可执行处置（先点「复位打印机」清缓冲）",
    /先点「复位打印机」清掉缓冲/.test(src));
  check("单包写入超时 6s（缩短「看着像卡死」的窗口）",
    /withTimeout\(p, 6000,/.test(src) && !/withTimeout\(p, 10000,/.test(src));
}

/* ── 报文解析器 ──────────────────────────────────────────────
 * 把作业字节流按指令顺序解出来。它同时是「结构自检」：
 * 只要出现一个解析不了的字节，就说明报文被切错了（位图数据长度写错、段边界算错…）。
 * 光栅指令按 x*y 精确跳过数据，所以数据里含 1b/1d/0c 也不会被误认成指令。
 */
function parseJob(bytes) {
  const out = [];
  let i = 0;
  while (i < bytes.length) {
    const b = bytes[i];
    if (b === 0x1b && bytes[i + 1] === 0x40) { out.push({ op: "reset" }); i += 2; continue; }
    if (b === 0x1d && bytes[i + 1] === 0x73 && bytes[i + 2] === 0x65 && bytes[i + 3] === 0x74 && bytes[i + 4] === 0x70) {
      out.push({ op: "setp", mode: bytes[i + 5] });
      i += 6;
      continue;
    }
    if (b === 0x1d && bytes[i + 1] === 0x50) {          // GS P x y：走纸单位
      out.push({ op: "pitch", x: bytes[i + 2] | (bytes[i + 3] << 8), y: bytes[i + 4] | (bytes[i + 5] << 8) });
      i += 6;
      continue;
    }
    if (b === 0x1d && bytes[i + 1] === 0x76 && bytes[i + 2] === 0x30) {
      const m = bytes[i + 3];
      const x = bytes[i + 4] | (bytes[i + 5] << 8);
      const y = bytes[i + 6] | (bytes[i + 7] << 8);
      let sum = 0;
      for (let k = i + 8; k < i + 8 + x * y; k++) sum += bytes[k];
      out.push({ op: "raster", m, x, y, sum });
      i += 8 + x * y;
      continue;
    }
    if (b === 0x1b && bytes[i + 1] === 0x4a) { out.push({ op: "feed", n: bytes[i + 2] }); i += 3; continue; }
    if (b === 0x0c) { out.push({ op: "ff" }); i += 1; continue; }
    out.push({ op: "unknown", b });
    i += 1;
  }
  return out;
}

/** 造一个光栅：rowBytes(y) 返回该行的字节数组（长度 = bytesPerRow） */
function mkRaster(rows, bytesPerRow, rowBytes) {
  const bytes = new Uint8Array(rows * bytesPerRow);
  for (let y = 0; y < rows; y++) bytes.set(rowBytes(y), y * bytesPerRow);
  return { bytes, bytesPerRow, heightDots: rows, widthDots: bytesPerRow * 8 };
}
const BLANK_ROW_52 = () => new Uint8Array(52);

/* ── 1. 暴露面 ─────────────────────────────────────────────── */
// label.js 里所有 onclick/onchange 会碰到的函数，一个都不能少。
// 少一个的表现是「按钮点了没反应」，而 JS 控制台只报一个 ReferenceError，
// 很容易漏 —— 所以这里按名单逐个点名。
const REQUIRED_HANDLERS = [
  "openLabelDialog", "labelRefresh", "labelDownload", "labelExportJob", "labelPrintBle",
  "labelBleProbe", "labelBleCalibrate", "labelBleReset", "labelBleAlign", "labelBleFeedTest", "labelBleRaw", "labelBleDisconnect", "labelBleConnect",
  "labelA4", "labelPickSpool", "labelPickSize", "labelPickCustom", "labelPickDpi",
  "labelPickDensity", "labelPickCopies", "labelPickFootMargin", "labelPickResetFirst",
  "labelPickPerCopyPos", "labelPickHeadWait", "labelPickCopyDelay",
  "labelPickBandRows", "labelPickBlankSkip", "labelPickPipeline", "labelPickShowAll",
];

// 由 app.js 提供、label.js 直接引用的外部函数（不是 label.js 的职责）
const EXTERNAL_HANDLERS = new Set(["closeModal"]);

function testExports() {
  console.log("== 调试出口 ==");
  check("labelDebug 已挂到 window", !!sandbox.labelDebug);
  check("mm2dot 可调用", typeof mm2dot === "function");
  check("packRaster 可调用", typeof packRaster === "function");
  check("buildEscPosJob 可调用", typeof buildEscPosJob === "function");
  const missing = REQUIRED_HANDLERS.filter((n) => typeof sandbox[n] !== "function");
  check(`onclick 处理器全部导出（${REQUIRED_HANDLERS.length} 个）`, missing.length === 0,
    "缺失：" + missing.join(","));
}

/* ── 2. 毫米 → 点 ──────────────────────────────────────────── */
function testMm2dot() {
  console.log("== 毫米换算 ==");
  check("25.4mm @203dpi = 203 点", mm2dot(25.4, 203) === 203, String(mm2dot(25.4, 203)));
  check("25.4mm @300dpi = 300 点", mm2dot(25.4, 300) === 300, String(mm2dot(25.4, 300)));
  check("50mm @203dpi ≈ 400 点", Math.round(mm2dot(50, 203)) === 400, String(mm2dot(50, 203)));
  check("0mm = 0 点", mm2dot(0, 203) === 0);
}

/* ── 3. 位图打包 ───────────────────────────────────────────── */
// 造一个假 canvas：pixel(x,y) 返回 [r,g,b]
function mkCanvas(w, h, pixel) {
  const data = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const [r, g, b] = pixel(x, y);
      const i = (y * w + x) * 4;
      data[i] = r;
      data[i + 1] = g;
      data[i + 2] = b;
      data[i + 3] = 255;
    }
  }
  return {
    width: w,
    height: h,
    getContext: () => ({ getImageData: () => ({ data }) }),
  };
}

const WHITE = () => [255, 255, 255];
const BLACK = () => [0, 0, 0];

function testPackRaster() {
  console.log("== 1 位打包 ==");

  const full = packRaster(mkCanvas(16, 2, BLACK), 4);
  check("行宽 = ceil(宽/8)", full.bytesPerRow === 2, String(full.bytesPerRow));
  check("行数透传", full.heightDots === 2 && full.widthDots === 16);
  check("字节总数 = 行宽×行数", full.bytes.length === 4, String(full.bytes.length));
  check("全黑 → 每字节 0xff", Array.from(full.bytes).every((b) => b === 0xff), String(Array.from(full.bytes)));

  const blank = packRaster(mkCanvas(16, 2, WHITE), 4);
  check("全白 → 每字节 0x00", Array.from(blank.bytes).every((b) => b === 0x00), String(Array.from(blank.bytes)));

  // MSB-first：最左一列黑，应落在第 1 个字节的最高位
  const leftmost = packRaster(mkCanvas(10, 1, (x) => (x === 0 ? BLACK() : WHITE())), 4);
  check("最左像素打在最高位（MSB-first）", leftmost.bytes[0] === 0x80, "0x" + leftmost.bytes[0].toString(16));
  check("第 9 位落在第二字节最高位", leftmost.bytes[1] === 0x00, "0x" + leftmost.bytes[1].toString(16));

  const ninth = packRaster(mkCanvas(10, 1, (x) => (x === 8 ? BLACK() : WHITE())), 4);
  check("第 9 个像素（x=8）落在第二字节 0x80", ninth.bytes[1] === 0x80, "0x" + ninth.bytes[1].toString(16));

  const one = packRaster(mkCanvas(1, 1, BLACK), 4);
  check("宽 1 像素仍占 1 字节", one.bytesPerRow === 1 && one.bytes[0] === 0x80, "0x" + one.bytes[0].toString(16));

  // 非 8 倍数宽度：10 像素 → 16 位补齐，右侧补 0 而不是报错
  const odd = packRaster(mkCanvas(10, 1, BLACK), 4);
  check("非 8 倍数宽度右侧补 0", odd.bytes[1] === 0xc0, "0x" + odd.bytes[1].toString(16));

  // 浓度 → 阈值：中灰在低浓度下留白、高浓度下打成黑
  const gray = () => [150, 150, 150];
  const low = packRaster(mkCanvas(8, 1, gray), 1);
  const high = packRaster(mkCanvas(8, 1, gray), 8);
  check("中灰在浓度 1 下留白", low.bytes[0] === 0x00, "0x" + low.bytes[0].toString(16));
  check("中灰在浓度 8 下打成黑（浓度越高越浓）", high.bytes[0] === 0xff, "0x" + high.bytes[0].toString(16));

  // 越界的浓度值应被夹住而不是崩
  const over = packRaster(mkCanvas(8, 1, BLACK), 99);
  check("浓度超上限不崩", over.bytes[0] === 0xff);
  const under = packRaster(mkCanvas(8, 1, BLACK), 0);
  check("浓度 0 仍按 1 处理", under.bytes[0] === 0xff);
}

/* ── 4. ESC/POS 报文 ───────────────────────────────────────── */
function concatBytes(parts) {
  let total = 0;
  for (const p of parts) total += p.length;
  const out = new Uint8Array(total);
  let at = 0;
  for (const p of parts) { out.set(p, at); at += p.length; }
  return out;
}

function testEscPosJob() {
  console.log("== ESC/POS 报文 ==");
  const raster = {
    bytes: Uint8Array.from([0xaa, 0xbb, 0xcc, 0xdd]),
    bytesPerRow: 2,
    heightDots: 2,
    widthDots: 16,
  };

  const job = buildEscPosJob(raster, { copies: 1 });
  const ops = parseJob(job);
  check("报文能顺序解析完（无未知字节 → 段边界没算错）",
    ops.every((o) => o.op !== "unknown"), JSON.stringify(ops));
  // 2026-09-20 真机实测：不勾「打印前复位」时发送会中途停住、根本打不出来；勾上才出纸。
  // 与官方抓包（1b 40 出现 0 次）相反，原因是官方 App 打印前自带初始化，浏览器直连没有。
  check("默认发 ESC @ 复位（实测不发则发送停住、打不出来）",
    job[0] === 0x1b && job[1] === 0x40, Array.from(job.slice(0, 2)).join(","));
  check("复位后紧跟 GS \"setp\" 01（标签纸模式）",
    [0x1d, 0x73, 0x65, 0x74, 0x70, 0x01].every((b, i) => job[2 + i] === b),
    Array.from(job.slice(2, 8)).join(","));
  // 空白行跳过靠 ESC J 走纸，纵向单位各家常不一样（1/203、1/144、1/360），
  // 所以必须显式下发 GS P 203 203 把单位钉成 1 点，否则整张标签会被拉长/压扁。
  check("跟一条 GS P 203 203（钉住 ESC J 的走纸单位 = 1 点）",
    [0x1d, 0x50, 0xcb, 0x00, 0xcb, 0x00].every((b, i) => job[8 + i] === b),
    Array.from(job.slice(8, 14)).join(","));
  check("单份长度 = 2+6+6+8+4+1 = 27", job.length === 27, String(job.length));

  const r = ops.find((o) => o.op === "raster");
  check("含一条 GS v 0 光栅指令", !!r);
  check("GS v 0 m=0（未压缩位图）", r && r.m === 0x00, r && String(r.m));
  check("行宽小端（2 → 02 00）", r && r.x === 2, r && String(r.x));
  check("行数小端（2 → 02 00）", r && r.y === 2, r && String(r.y));
  check("位图数据不丢不改（aa+bb+cc+dd = 694）",
    r && r.sum === 0xaa + 0xbb + 0xcc + 0xdd, r && String(r.sum));
  check("以 FF 走纸收尾（多张不串位关键）", job[job.length - 1] === 0x0c, String(job[job.length - 1]));

  // 关掉复位 + 关掉空白跳过 = 对齐官方抓包的最小形态（不含 ESC @ / GS P）
  const noReset = buildEscPosJob(raster, { copies: 1, resetFirst: false, blankSkip: false });
  check("关掉复位与空白跳过 → 首字节就是 setp 01（对齐官方抓包）",
    [0x1d, 0x73, 0x65, 0x74, 0x70, 0x01].every((b, i) => noReset[i] === b),
    Array.from(noReset.slice(0, 6)).join(","));
  check("不发 GS P（不省空白就不需要走纸命令）",
    !(noReset[6] === 0x1d && noReset[7] === 0x50), Array.from(noReset.slice(6, 14)).join(","));
  check("该形态长度回到 19（= 6+8+4+1）", noReset.length === 19, String(noReset.length));

  const two = buildEscPosJob(raster, { copies: 2 });
  const twoOps = parseJob(two);
  check("两份 = 2 条光栅 + 2 个 FF",
    twoOps.filter((o) => o.op === "raster").length === 2 &&
      twoOps.filter((o) => o.op === "ff").length === 2, JSON.stringify(twoOps));
  // 0.12.25：默认**关**「每份重新定位」→ 全篇只有一个头部（与官方抓包同构：一份头 + 若干块）
  check("默认每份不补头部：两份长度 = 27 + 13 = 40", two.length === 40, String(two.length));
  check("默认第二份首字节就是 GS v 0（没有 ESC @、没有 setp）",
    two[27] === 0x1d && two[28] === 0x76, Array.from(two.slice(27, 30)).join(","));

  // 勾上「每份重新定位」：第二份补一条 setp 01，**不带 ESC @**
  //   （ESC @ 才是「打印前纸先进一下」的嫌疑，中途再发一次就再来一次进纸）
  const twoPos = buildEscPosJob(raster, { copies: 2, perCopyPos: true });
  check("勾上每份重新定位 → 两份长度 = 27 + 19 = 46", twoPos.length === 46, String(twoPos.length));
  check("每份重新定位补的是 setp 01，不是 ESC @",
    twoPos[27] === 0x1d && [0x1d, 0x73, 0x65, 0x74, 0x70, 0x01].every((b, i) => twoPos[27 + i] === b),
    Array.from(twoPos.slice(27, 33)).join(","));
  check("关掉每份重新定位与打开的默认形态逐字节相同",
    Array.from(buildEscPosJob(raster, { copies: 2, perCopyPos: false })).join(",") ===
      Array.from(two).join(","));

  check("份数 0 兜底成 1 份",
    parseJob(buildEscPosJob(raster, { copies: 0 })).filter((o) => o.op === "raster").length === 1);
  check("份数超上限夹到 50",
    parseJob(buildEscPosJob(raster, { copies: 999 })).filter((o) => o.op === "raster").length === 50,
    String(parseJob(buildEscPosJob(raster, { copies: 999 })).filter((o) => o.op === "raster").length));
  check("cfg 只有 copies 也不崩（其余走默认）",
    parseJob(buildEscPosJob(raster, {})).filter((o) => o.op === "ff").length === 1);
  check("feed 已废弃（结尾恒为 FF，不崩）",
    buildEscPosJob(raster, { copies: 1, feed: -5 }).slice(-1)[0] === 0x0c,
    String(buildEscPosJob(raster, { copies: 1, feed: -5 }).slice(-1)[0]));

  // ESC @ 只该在「断链重发」或「用户勾了复位」时出现
  const retry = buildEscPosJob(raster, { copies: 1, resetFirst: false }, { reset: true });
  check("重发时强制发 ESC @（清打印机里的半份残留）",
    retry[0] === 0x1b && retry[1] === 0x40 && retry.length === 27,
    Array.from(retry.slice(0, 2)).join(",") + " len=" + retry.length);
  check("{reset:false} 显式压过 cfg.resetFirst",
    buildEscPosJob(raster, { copies: 1, resetFirst: true }, { reset: false })[0] !== 0x1b);

  // 403 点宽（50mm @ 203dpi）时行宽高字节仍要为 0，不能溢出。
  // 注意位图必须非空：空白行会被「空白跳过」吃掉，那样测的就不是行宽字段了。
  const wide = parseJob(
    buildEscPosJob(
      { bytes: Uint8Array.from({ length: 51 * 2 }, () => 0xff), bytesPerRow: 51, heightDots: 2, widthDots: 403 },
      { copies: 1, blankSkip: false }
    )
  );
  check("403 点宽 → 行宽 51 字节（0x33 0x00）", wide.find((o) => o.op === "raster").x === 51,
    JSON.stringify(wide.find((o) => o.op === "raster")));
  check("行宽超过 255 也不截断（0x33 0x00 而非 0x33 0x01）",
    wide.find((o) => o.op === "raster").x === 51 && wide.find((o) => o.op === "raster").y === 2,
    JSON.stringify(wide.find((o) => o.op === "raster")));
}

/* ── 4a1b. 作业拆分（0.12.25：头 / 位图分两次发） ─────────────
 * 真机证据：打第一张时纸会往里进一下、位置就错；第二张不再进纸、位置反而是对的。
 * 两处唯一差别 = 整份开头那一次作业头（ESC @ + setp 01）。修法不是删掉头（0.12.19 试过，
 * 不发就「发送半天、打一点就没了」），而是把头与位图拆成两次写入，中间等 headWaitMs
 * 让固件的复位/定位动作走完 —— 位图于是从静止的纸位开始。
 * 这里钉的是「拆只是分包，不改内容」：拼回去必须与单块作业逐字节相同。
 */
function testJobParts() {
  console.log("== 作业拆分（头 / 位图分两次发） ==");
  const raster = {
    bytes: Uint8Array.from([0xaa, 0xbb, 0xcc, 0xdd]),
    bytesPerRow: 2,
    heightDots: 2,
    widthDots: 16,
  };
  const cat = (arrs) => {
    const n = arrs.reduce((s, a) => s + a.length, 0);
    const out = new Uint8Array(n);
    let o = 0;
    for (const a of arrs) { out.set(a, o); o += a.length; }
    return out;
  };

  const cfg = { copies: 3, resetFirst: true, blankSkip: false, bandRows: 0 };
  const p = buildJobParts(raster, cfg);
  check("head 只含 ESC @ + setp 01（3 份共用一个头）",
    p.head.length === 8 && p.head[0] === 0x1b && p.head[1] === 0x40 &&
      [0x1d, 0x73, 0x65, 0x74, 0x70, 0x01].every((b, i) => p.head[2 + i] === b),
    Array.from(p.head).join(","));
  check("copies 切出 3 份", p.copies.length === 3, String(p.copies.length));
  check("每份 13 字节（光栅 12 + FF 1），份尾都是 FF",
    p.copies.every((c) => c.length === 13 && c[12] === 0x0c),
    p.copies.map((c) => c.length).join(","));
  check("拼回去与单块作业逐字节相同（拆只是分包，不改内容）",
    Array.from(cat([p.head].concat(p.copies))).join(",") ===
      Array.from(buildEscPosJob(raster, cfg)).join(","));
  check("关闭复位：head 只剩 setp 01（6 字节）",
    buildJobParts(raster, { copies: 1, resetFirst: false, blankSkip: false }).head.length === 6);
  check("份数为 1 时 copies 只有 1 份",
    buildJobParts(raster, { copies: 1 }).copies.length === 1);
  check("份数 0 兜底成 1 份",
    buildJobParts(raster, { copies: 0 }).copies.length === 1);
  // 拆包行为钉在源码里：sendJobParts 必须「先发头 → 等待 → 再发位图」，且仍是串行不并发
  const src = fs.readFileSync(SRC, "utf8");
  check("sendJobParts 存在且先发头再等 headWaitMs",
    /async function sendJobParts\(parts, cfg\)/.test(src) && /await sleep\(wait\)/.test(src));
  check("打印路径改用 buildJobParts / sendJobParts（不再一口气发）",
    /const parts = buildJobParts\(raster, cfg\)/.test(src) && !/await sendJob\(/.test(src));
  check("多份之间等 copyDelayMs（这份固件一份一份地打）",
    /await sleep\(gap\)/.test(src));
}

/* ── 4a2. 分带 / 空白跳过 ──────────────────────────────────────
 * 这两条是「为什么汉印发得动、我们发不动」的直接对策：
 *   汉码官方每张只发 3475 字节（私有压缩位图），而且拆成 22 条 10 行的 GS v 0（每条 520 字节）；
 *   我们原来是 12000 字节一整坨未压缩位图 —— 50mm 宽、218 行满幅，纯白行占七成体积。
 *   空白行用 ESC J 走纸跳过（3 字节换 52 字节）。实测一份 50×30（二维码占右上约四成高）
 *   从 11351 字节降到 5082 字节 —— 逼近官方压缩流的 3473 字节/份。
 */
function testRasterCommands() {
  console.log("== 分带与空白跳过 ==");
  const ROWS = 218;
  const BPR = 52;
  const header = (c) => c[0] === 0x1d && c[1] === 0x76 && c[2] === 0x30;
  const isFeed = (c) => c[0] === 0x1b && c[1] === 0x4a;
  const size = (cmds) => cmds.reduce((a, c) => a + c.length, 0);

  // 1) 全空白：一行位图都不该发，全用 ESC J 跳过
  const blank = mkRaster(ROWS, BPR, BLANK_ROW_52);
  const c1 = rasterCommands(blank, { bandRows: 10, blankSkip: true });
  check("全空白标签 → 一条光栅指令都不发", c1.every((c) => !header(c)), size(c1) + " 字节");
  check("ESC J 合计走纸 218 点（= 218 行空白）",
    c1.filter(isFeed).reduce((a, c) => a + c[2], 0) === ROWS,
    String(c1.filter(isFeed).reduce((a, c) => a + c[2], 0)));
  check("全空白作业不到 20 字节（旧写法 218×52 = 11336 字节）", size(c1) < 20, String(size(c1)));

  // 2) 关掉空白跳过 → 回到一整块位图（旧行为）
  const c2 = rasterCommands(blank, { bandRows: 0, blankSkip: false });
  check("关掉空白跳过 → 只剩一条 GS v 0 + 一块数据",
    c2.length === 2 && header(c2[0]) && c2[1].length === ROWS * BPR,
    `${c2.length} 段 / ${c2[1] && c2[1].length} 字节`);
  check("关掉后行数字段 = 218（0xda 0x00）", c2[0][6] === 0xda && c2[0][7] === 0x00,
    `${c2[0][6]},${c2[0][7]}`);

  // 3) 分带：官方同款每 10 行一条（22 条 = 21×10 + 8）
  const c3 = rasterCommands(blank, { bandRows: 10, blankSkip: false });
  const heads = c3.filter(header);
  check("分带 10 行 → 22 条 GS v 0（对齐汉码抓包 22 块）", heads.length === 22, String(heads.length));
  check("每条行数 10，最后一条 8（合计仍 218 行）",
    heads.slice(0, 21).every((h) => h[6] === 10) && heads[21][6] === 8 &&
      heads.reduce((a, h) => a + h[6], 0) === ROWS,
    heads.map((h) => h[6]).join(","));
  check("每块载荷 520 字节（不再是 11KB 一整坨）",
    c3[1].length === 520 && c3[2 * 21 + 1].length === 416,
    `${c3[1].length} / ${c3[2 * 21 + 1].length}`);
  check("分带后行宽仍是 52 字节", heads.every((h) => h[4] === 52 && h[5] === 0), String(heads[0][4]));

  // 4) 首尾有内容、中间全空白 → 块 + 跳过 + 块
  const sparse = mkRaster(100, BPR, (y) => {
    const row = new Uint8Array(BPR);
    if (y === 0 || y === 99) row[0] = 0xff;
    return row;
  });
  const c4 = parseJob(concatBytes(rasterCommands(sparse, { bandRows: 0, blankSkip: true })));
  check("稀疏标签 → 位图 / ESC J 98 / 位图",
    c4.length === 3 && c4[0].op === "raster" && c4[0].y === 1 &&
      c4[1].op === "feed" && c4[1].n === 98 && c4[2].op === "raster" && c4[2].y === 1,
    JSON.stringify(c4));

  // 5) 空白段超过 255 点要拆多条（ESC J 单条上限 255）
  const longBlank = mkRaster(600, BPR, BLANK_ROW_52);
  const c5 = rasterCommands(longBlank, { bandRows: 0, blankSkip: true });
  check("空白段超 255 点自动拆成 255+255+90",
    c5.length === 3 && c5[0][2] === 255 && c5[1][2] === 255 && c5[2][2] === 90,
    c5.map((c) => c[2]).join(","));

  // 6) 真实尺寸的整份作业：要如实反映「标签上有二维码」这件事 ——
  //    二维码那几十行整行都有墨，跳过不了；能省的只有纯白行（上部、行间、底部）。
  //    按我们自己的版式（二维码占右上、纵向约四成高），省幅大概在三到五成。
  const rows218 = rasterRowsFor(30, 2.75, 203);
  const withQr = mkRaster(rows218, BPR, (y) => {
    const row = new Uint8Array(BPR);
    if (y < 90) {
      for (let i = 30; i < BPR - 2; i++) row[i] = (y + i) % 2 ? 0xb4 : 0xff; // 二维码带
    } else if (y % 30 === 0) {
      row[2] = 0xff;                                                        // 零散文字行
    }
    return row;
  });
  const cfgNew = { copies: 1, bandRows: 10, blankSkip: true, resetFirst: true };
  const jobNew = buildEscPosJob(withQr, cfgNew);
  const jobOld = buildEscPosJob(withQr, { copies: 1, bandRows: 0, blankSkip: false, resetFirst: true });
  check("新作业能解析完（结构自检）",
    parseJob(jobNew).every((o) => o.op !== "unknown"), JSON.stringify(parseJob(jobNew).slice(0, 6)));
  check("带二维码的真实作业仍能省下四分之一以上",
    jobNew.length * 4 < jobOld.length * 3, `${jobNew.length} vs ${jobOld.length}`);
  check("省幅有上限：二维码整行跳过不了（省不到 2/3）",
    jobNew.length * 3 > jobOld.length, `${jobNew.length} vs ${jobOld.length}`);
  check("省下来的都是纯白行（ESC J 段数 ≥ 3，不是只砍了底部留白）",
    parseJob(jobNew).filter((o) => o.op === "feed").length >= 3,
    String(parseJob(jobNew).filter((o) => o.op === "feed").length));
  check("多份时每份仍以 FF 收尾",
    parseJob(buildEscPosJob(withQr, { copies: 3, bandRows: 10, blankSkip: true }))
      .filter((o) => o.op === "ff").length === 3);
}

/* ── 4b. 底部留白 / 光栅高度 ───────────────────────────────── */
// 这一层钉的是「多张连打不串位」的物理前提：不能把整张标签打满。
// 依据：汉码官方「打印到文件」抓包（50×30mm ×3 份）每份恰好 22 个 GS v 0 块、
//       行数合计 218 行（21×10 + 1×8）= 27.28mm，底部留 22 行 ≈ 2.75mm。
//       打满 240 行的头会停在标签边缘/缝里，结尾 FF 的间隙定位就失准 → 逐张累积偏移。
function testFootMargin() {
  console.log("== 底部留白与光栅高度 ==");
  check("effHeightMm(30, 2.75) = 27.25", effHeightMm(30, 2.75) === 27.25, String(effHeightMm(30, 2.75)));
  check("50×30 留白 2.75mm @203dpi → 218 行（对齐汉码官方抓包）",
    rasterRowsFor(30, 2.75, 203) === 218, String(rasterRowsFor(30, 2.75, 203)));
  check("留白 0 → 满幅 240 行（旧行为，会串位）",
    rasterRowsFor(30, 0, 203) === 240, String(rasterRowsFor(30, 0, 203)));
  check("留白 0 与留白 2.75 相差正好 22 行",
    rasterRowsFor(30, 0, 203) - rasterRowsFor(30, 2.75, 203) === 22,
    String(rasterRowsFor(30, 0, 203) - rasterRowsFor(30, 2.75, 203)));
  check("300dpi 下同一留白同样成立（27.25mm → 322 行）",
    rasterRowsFor(30, 2.75, 300) === 322, String(rasterRowsFor(30, 2.75, 300)));

  // 兜底：脏配置不能让画布变成 0 高或负数（0 高的 canvas 会让整条打印链路静默失败）
  check("留白为 undefined 视作 0", effHeightMm(30, undefined) === 30, String(effHeightMm(30, undefined)));
  check("留白为 null 视作 0", effHeightMm(30, null) === 30, String(effHeightMm(30, null)));
  check("留白为 NaN 视作 0", effHeightMm(30, NaN) === 30, String(effHeightMm(30, NaN)));
  check("留白为负数夹成 0", effHeightMm(30, -5) === 30, String(effHeightMm(30, -5)));
  check("留白大于标签高 → 有效高度下限 6mm", effHeightMm(30, 999) === 6, String(effHeightMm(30, 999)));
  check("高度为 0 也不崩（下限 6mm）", effHeightMm(0, 0) === 6, String(effHeightMm(0, 0)));
  check("光栅行数恒 ≥ 8（脏配置下仍可打印）",
    rasterRowsFor(30, 999, 203) >= 8, String(rasterRowsFor(30, 999, 203)));
  check("光栅行数恒为整数", Number.isInteger(rasterRowsFor(30, 2.75, 203)));

  // 留白必须真的作用到报文里：同等份数下，留白越大报文越短。
  // 这里刻意把两个「省体积」开关关掉，单独量留白对报文体量的作用。
  const BPR = 52;
  const mkSolid = (rows) => mkRaster(rows, BPR, () => Uint8Array.from({ length: BPR }, () => 0xff));
  // 这里刻意把「省体积」开关与「每份重新定位」都关掉，单独量留白对报文体量的作用
  // （perCopyPos 会每份多发一次头部，会干扰这条长度公式）。
  const base = { copies: 2, bandRows: 0, blankSkip: false, resetFirst: true, perCopyPos: false };
  const rows218 = rasterRowsFor(30, 2.75, 203);
  const rows240 = rasterRowsFor(30, 0, 203);
  const jobSmall = buildEscPosJob(mkSolid(rows218), base);
  const jobBig = buildEscPosJob(mkSolid(rows240), base);
  check("留白后的两份报文确实更短（每份少 22 行×52 字节）",
    jobBig.length - jobSmall.length === 2 * 22 * BPR,
    `${jobBig.length} vs ${jobSmall.length}`);
  check("留白后每份仍以 FF 收尾",
    parseJob(jobSmall).filter((o) => o.op === "ff").length === 2);
  check("行数字段写进报文（218 = 0xda 0x00）",
    parseJob(jobSmall).find((o) => o.op === "raster").y === 218,
    String(parseJob(jobSmall).find((o) => o.op === "raster").y));
  check("报文长度 = 2+6+2×(8+52×218+1)（数据无隐藏裁剪）",
    jobSmall.length === 2 + 6 + 2 * (8 + BPR * rows218 + 1), String(jobSmall.length));
}

/* ── 5. 对话框装配 ─────────────────────────────────────────── */
// 把 openModal 换成一个「记下来就抛」的桩：这样 openLabelDialog 会在拼完
// body/footer 之后立刻停下，不用去桩 canvas / Image（那才是不必要的负担）。
async function testDialogHtml() {
  console.log("== 对话框装配 ==");
  const captured = {};
  sandbox.esc = (s) =>
    String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  sandbox.toast = () => {};
  sandbox.S = {
    spools: [
      {
        id: 1, name: "测试料盘 PLA 深空黑", brand: "拓竹", material: "PLA",
        color_name: "深空黑", color_hex: "#1A1A1A", location: "干燥箱 A",
        remaining_weight: 640, initial_weight: 1000, spool_weight: 250, archived: false,
      },
    ],
    dashSpools: [],
  };
  sandbox.openModal = (title, body, footer) => {
    captured.title = title;
    captured.body = body;
    captured.footer = footer;
    throw new Error("__stop__");
  };

  try {
    await sandbox.openLabelDialog(1);
  } catch (err) {
    if (!/__stop__/.test(err.message)) throw err;
  }

  check("对话框已打开", captured.title === "标签打印", String(captured.title));
  const html = (captured.body || "") + (captured.footer || "");
  check("带出料盘名（已转义）", html.includes("测试料盘 PLA 深空黑"));
  check("含料盘选择框", html.includes('id="labelSpool"'));
  check("含尺寸预设", html.includes("50×30 mm"));
  check("含 dpi 选项", html.includes('value="203"') && html.includes('value="300"'));
  check("含浓度与份数", html.includes('id="labelDensity"') && html.includes('id="labelCopies"'));
  check("含底部留白字段（多张连打不串位的关键参数）", html.includes('id="labelFootMargin"'));
  check("含「打印前复位」开关（真机实测不发则打不出来）", html.includes('id="labelResetFirst"'));
  check("含「官方同款分带」开关", html.includes('id="labelBandRows"'));
  check("含「空白行不传数据」开关（12KB → 5KB 上下）", html.includes('id="labelBlankSkip"'));
  check("含「流水线连发」开关且文案标注默认关（并发 GATT 会掐链路，0.12.20 教训）",
    html.includes('id="labelPipeline"') && /流水线连发（快，但本机实测/.test(html));
  check("流水线默认关闭钉在 defaultCfg 源码里",
    /pipeline: false/.test(fs.readFileSync(SRC, "utf8")));
  check("含导出作业与对齐标签两个诊断按钮",
    html.includes("labelExportJob") && html.includes("labelBleAlign"));
  check("含走纸测试按钮（串页时分离「走纸定位」与「位图打印」）",
    html.includes("labelBleFeedTest"));
  check("诊断动作先发 setp 01 进标签模式（只发裸 FF 真机按了没反应）",
    typeof (sandbox.labelDebug || {}).labelModeBytes === "function" &&
      (sandbox.labelDebug.labelModeBytes() || [])[0] === 0x1d);
  check("含「每份重新定位」开关（默认关，文案写上不带 ESC @）",
    html.includes('id="labelPerCopyPos"') && /每份重新定位（实验，默认关/.test(html));
  check("含「作业头后等待」时间旋钮（修第一张进纸导致的位置偏）",
    html.includes('id="labelHeadWait"') && /作业头后等待 ms/.test(html));
  check("含「多份间隔」时间旋钮（这份固件一份一份地打）",
    html.includes('id="labelCopyDelay"') && /多份间隔 ms/.test(html));
  check("含「复位打印机」独立按钮（卡住/发送中断时手动清缓冲）",
    html.includes("labelBleReset") && typeof sandbox.labelBleReset === "function");
  // 版本自证：面板上要打运行版本号。0.12.25 的两个旋钮曾因「镜像没拉 / 浏览器缓存旧 JS」
  // 在面板上根本看不到，白白排查一轮 —— 有版本号，一张截图就能定位是哪一版。
  const srcAll = fs.readFileSync(SRC, "utf8");
  check("预览信息行打出运行版本号（截图自证容器是哪一版）",
    /" · 版本 " \+ runningVersion\(\)/.test(srcAll));
  check("版本号取自后端 /api/system/status，不硬写第三份",
    /S\.status\.version/.test(srcAll) &&
      typeof ((sandbox.labelDebug || {}).runningVersion) === "function");
  check("取不到后端版本时写「未知」而不是 undefined",
    sandbox.labelDebug.runningVersion() === "未知", String(sandbox.labelDebug.runningVersion()));
  check("落运行时把版本读成整数语义（source 里没有第三个硬编码版本号）",
    !/["']0\.12\.\d+["']/.test(srcAll.replace(/\/\*[\s\S]*?\*\//g, "")));
  check("说明里写明「位置偏」的处置（等待值 / 取消复位）",
    html.includes("作业头后等待") && html.includes("取消勾选"));
  check("说明里写清「先连接→再间隙学习→再打印」的顺序",
    html.includes("连接打印机") && html.includes("间隙学习") && html.includes("蓝牙打印"));
  // 0.12.28：说明与实验开关都收进折叠区，默认收起 —— 面板上不再铺半屏长文。
  check("操作说明收进折叠区且默认收起",
    /<details class="label-diag label-help">/.test(html) && !/label-help"[^>]*\sopen/.test(html) &&
      html.includes("<summary>"));
  check("四个实验开关收进折叠区且默认收起",
    /<details class="label-diag label-adv">/.test(html) && !/label-adv"[^>]*\sopen/.test(html) &&
      html.indexOf('id="labelPerCopyPos"') > html.indexOf("label-adv") &&
      html.indexOf('id="labelPipeline"') < html.indexOf("</details>", html.indexOf("label-adv")));
  check("面板正文不再有直接铺开的 .hint 长文",
    !/class="hint"/.test(html), html.match(/class="hint"[^>]{0,40}/)?.[0] || "");
  check("含诊断折叠区挂点", html.includes('id="labelBlePanel"'));
  check("含预览挂点", html.includes('id="labelPreviewHost"'));
  check("提示语提到 T260LR 蓝牙方案", html.includes("T260LR"));
  check("没有渲染出 undefined", !html.includes("undefined"), html.match(/.{0,40}undefined.{0,40}/)?.[0] || "");
  check("没有渲染出 [object Object]", !html.includes("[object Object]"));

  // 最关键的一条：HTML 里 on* 属性调用的函数必须真的存在，否则按钮点了没反应
  const called = new Set();
  for (const m of html.matchAll(/on(?:click|change|input|submit)\s*=\s*"([^"]*)"/g)) {
    for (const f of m[1].matchAll(/([A-Za-z_$][\w$]*)\s*\(/g)) called.add(f[1]);
  }
  check("对话框里确实绑了事件", called.size >= 8, [...called].join(","));
  const missing = [...called].filter(
    (n) => typeof sandbox[n] !== "function" && !EXTERNAL_HANDLERS.has(n)
  );
  check("所有 on* 处理器都有定义（含 app.js 提供的外部函数）", missing.length === 0,
    "缺失：" + missing.join(","));
  check("只依赖白名单里的外部函数",
    [...called].every((n) => typeof sandbox[n] === "function" || EXTERNAL_HANDLERS.has(n)),
    [...called].join(","));

  for (const must of ["labelPrintBle", "labelDownload", "labelA4", "labelPickSpool", "labelPickSize"]) {
    check(`处理器 ${must} 被引用到`, called.has(must), [...called].join(","));
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) {
  testExports();
  testDefaultCfgSafe();
  testBleGuards();
  testMm2dot();
  testPackRaster();
  testEscPosJob();
  testJobParts();
  testRasterCommands();
  testFootMargin();
  await testDialogHtml();
  console.log(`\n通过 ${PASSED.length} 项，失败 ${FAILED.length} 项`);
  if (FAILED.length) {
    console.log("失败项：", FAILED);
    process.exit(1);
  }
  console.log("全部通过");
}
