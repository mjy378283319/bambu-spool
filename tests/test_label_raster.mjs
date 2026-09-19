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

const { mm2dot, packRaster, buildEscPosJob } = sandbox.labelDebug || {};

/* ── 1. 暴露面 ─────────────────────────────────────────────── */
// label.js 里所有 onclick/onchange 会碰到的函数，一个都不能少。
// 少一个的表现是「按钮点了没反应」，而 JS 控制台只报一个 ReferenceError，
// 很容易漏 —— 所以这里按名单逐个点名。
const REQUIRED_HANDLERS = [
  "openLabelDialog", "labelRefresh", "labelDownload", "labelPrintBle",
  "labelBleProbe", "labelBleCalibrate", "labelBleRaw", "labelBleDisconnect", "labelBleConnect",
  "labelA4", "labelPickSpool", "labelPickSize", "labelPickCustom", "labelPickDpi",
  "labelPickDensity", "labelPickCopies", "labelPickShowAll",
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
function testEscPosJob() {
  console.log("== ESC/POS 报文 ==");
  const raster = {
    bytes: Uint8Array.from([0xaa, 0xbb, 0xcc, 0xdd]),
    bytesPerRow: 2,
    heightDots: 2,
    widthDots: 16,
  };

  const job = buildEscPosJob(raster, { copies: 1, feed: 3 });
  const head = Array.from(job.slice(0, 8));
  check("以 ESC @ 复位开头", head[0] === 0x1b && head[1] === 0x40, head.join(","));
  check("接 GS \"setp\" 01（标签纸模式）",
    [0x1d, 0x73, 0x65, 0x74, 0x70, 0x01].every((b, i) => job[2 + i] === b),
    Array.from(job.slice(2, 8)).join(","));
  check("接 GS v 0 m=0 光栅指令",
    [0x1d, 0x76, 0x30, 0x00].every((b, i) => job[8 + i] === b),
    Array.from(job.slice(8, 12)).join(","));
  check("行宽小端（2 → 02 00）", job[12] === 0x02 && job[13] === 0x00, `${job[12]},${job[13]}`);
  check("行数小端（2 → 02 00）", job[14] === 0x02 && job[15] === 0x00, `${job[14]},${job[15]}`);
  check("位图数据紧随其后（不丢不改）",
    Array.from(job.slice(16, 20)).join(",") === "170,187,204,221",
    Array.from(job.slice(16, 20)).join(","));
  check("以 ESC d 3 走纸收尾",
    job[20] === 0x1b && job[21] === 0x64 && job[22] === 3,
    `${job[20]},${job[21]},${job[22]}`);
  check("单份长度 = 2+6+8+4+3 = 23", job.length === 23, String(job.length));

  const two = buildEscPosJob(raster, { copies: 2, feed: 3 });
  check("两份 = 2+6+2×(8+4+3) = 38", two.length === 38, String(two.length));
  // 第 2 份从第 23 字节开始（2 复位 + 6 标签模式 + 15 第一份）
  check("两份的第二份仍是完整报文",
    two[23] === 0x1d && two[24] === 0x76 && two[25] === 0x30 && two[26] === 0x00 &&
      two[27] === 0x02 && two[29] === 0x02 && two[37] === 3,
    Array.from(two.slice(23)).join(","));
  check("两份逐字节相同（除长度翻倍）",
    Array.from(two.slice(8, 23)).join(",") === Array.from(two.slice(23, 38)).join(","),
    Array.from(two.slice(23, 38)).join(","));

  check("份数 0 兜底成 1 份", buildEscPosJob(raster, { copies: 0 }).length === 23,
    String(buildEscPosJob(raster, { copies: 0 }).length));
  check("份数超上限夹到 50",
    buildEscPosJob(raster, { copies: 999 }).length === 2 + 6 + 50 * 15,
    String(buildEscPosJob(raster, { copies: 999 }).length));
  check("feed 缺省按 0（不崩）", buildEscPosJob(raster, {}).length === 23);
  check("feed 负数夹成 0",
    buildEscPosJob(raster, { copies: 1, feed: -5 })[22] === 0,
    String(buildEscPosJob(raster, { copies: 1, feed: -5 })[22]));

  // 403 点宽（50mm @ 203dpi）时行宽高字节仍要为 0，不能溢出成 0x00 0x00 之外的值
  const wide = buildEscPosJob(
    { bytes: new Uint8Array(51 * 2), bytesPerRow: 51, heightDots: 2, widthDots: 403 },
    { copies: 1, feed: 2 }
  );
  check("403 点宽 → 行宽 51 字节（0x33 0x00）", wide[12] === 51 && wide[13] === 0, `${wide[12]},${wide[13]}`);
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
  testMm2dot();
  testPackRaster();
  testEscPosJob();
  await testDialogHtml();
  console.log(`\n通过 ${PASSED.length} 项，失败 ${FAILED.length} 项`);
  if (FAILED.length) {
    console.log("失败项：", FAILED);
    process.exit(1);
  }
  console.log("全部通过");
}
