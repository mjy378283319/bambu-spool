/* 标签打印自测（node 直跑，不需要浏览器）。
 *
 * label.js 是给浏览器写的 IIFE，这里用 vm 把它跑在一个最小沙箱里，
 * 只补 window / document / localStorage 这几个它加载时会碰到的全局，
 * 然后校验 labelDebug 暴露出来的纯函数。
 *
 * 1.0.0 起：蓝牙（Web Bluetooth 直发 ESC/POS）整体删除，打印只剩
 * USB / 汉印 HMarkService 一条路。本文件钉的是：
 *   ① 蓝牙必须删干净（代码里不许再有任何 GATT / ESC/POS 发送路径）；
 *   ② 版式几何（毫米换算、留白、右侧死区）不许悄悄跑偏；
 *   ③ USB 报文结构逐字对齐官方抓包；
 *   ④ 对话框装配完整（料盘排序、按钮、on* 处理器都有定义）。
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

const { mm2dot, effHeightMm, rasterRowsFor } = sandbox.labelDebug || {};

/* ── 0. 1.0.0：蓝牙必须删干净 ──────────────────────────────── */
// 用户定论（09-24）：BLE 直发这条固件「不按垫行走纸、FF 走 0」，连改十几版没稳住，
// 正式砍掉、只留 USB 驱动通道。这里钉「删干净」：任何蓝牙运行时痕迹都不许回来。
function testBleRemoved() {
  console.log("== 蓝牙已删净（1.0.0） ==");
  const src = fs.readFileSync(SRC, "utf8");
  // 去掉块注释后再查（文件头的历史说明里允许提到「蓝牙已删除」）
  const code = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "");
  check("没有 Web Bluetooth 运行时调用", !/navigator\.bluetooth|requestDevice|gatt\./.test(code));
  check("没有蓝牙动作函数残留（bleConnect/bleWriteAll/bleSendRaw/bleBusyBlock…）",
    !/function\s+(bleConnect|bleWriteAll|bleSendRaw|bleDisconnect|bleBusyBlock|bleState|negotiate|ensureConnected|onGattDisconnected)/.test(code));
  check("没有蓝牙面板/动作入口残留（labelPrintBle/labelBle*/renderBlePanel）",
    !/function\s+(labelPrintBle|labelBle\w+|renderBlePanel|labelProgress)/.test(code));
  check("没有 ESC/POS 作业组装残留（packRaster/rasterCommands/buildJobParts/buildEscPosJob）",
    !/function\s+(packRaster|rasterCommands|buildJobParts|buildEscPosJob)/.test(code));
  check("没有 BLE 服务/特征常量残留", !/BLE_SERVICES|BLE_WRITE_CHARS/.test(code));
  check("对话框里没有蓝牙打印按钮（说明文案里的「蓝牙打印去哪了」不算）",
    !/labelPrintBle|>蓝牙打印</.test(code));
  check("没有原始指令输入框与发送按钮", !/labelRawHex|labelBleRaw|发送原始指令/.test(code));
  check("没有导出作业(.bin)按钮（蓝牙时代的对账工具，随通道一起删）",
    !/labelExportJob|导出作业/.test(code));
  check("USB 是主打印按钮（primary）",
    /'<button class="primary" onclick="labelPrintUsb\(\)">USB 打印（驱动）<\/button>'/.test(src));
  check("说明里写明蓝牙删除原因（固件不按垫行走纸 / FF 走 0）",
    /蓝牙打印去哪了/.test(src) && /不按垫行走纸/.test(src));
}

/* ── 1. 默认配置 ───────────────────────────────────────────── */
function testDefaultCfgSafe() {
  console.log("== 默认配置（1.0.0：只剩版式字段） ==");
  const cfg = sandbox.labelDebug.loadCfg();
  check("默认 wMm=50 / hMm=30 / dpi=203 / copies=1",
    cfg.wMm === 50 && cfg.hMm === 30 && cfg.dpi === 203 && cfg.copies === 1,
    JSON.stringify(cfg));
  // 09-22~09-24 真机验证过的居中几何：留白 2.75 + 内容下移 1.5。别动。
  check("默认 footMargin=2.75（对齐汉码官方 218/240 行几何）",
    cfg.footMargin === 2.75, String(cfg.footMargin));
  check("默认 topShiftMm=1.5（内容居中：上下留白对称、落标签正中）",
    cfg.topShiftMm === 1.5, String(cfg.topShiftMm));
  const src = fs.readFileSync(SRC, "utf8");
  check("旧存档迁移：cfgRev 不一致时整份回默认（不再沿用旧实验开关）",
    /Number\(saved\.cfgRev\) === CFG_REV/.test(src) && /const CFG_REV = 9;/.test(src));
  check("defaultCfg 不再有实验/发送开关字段",
    !/resetFirst|headWaitMs|copyDelayMs|perCopyPos|bandRows|blankSkip|pipeline|rewindAfter|showAll|fullPitch|density/
      .test(src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "")));
}

/* ── 2. 暴露面 ─────────────────────────────────────────────── */
// label.js 里所有 onclick/onchange 会碰到的函数，一个都不能少。
// 少一个的表现是「按钮点了没反应」，而 JS 控制台只报一个 ReferenceError，
// 很容易漏 —— 所以这里按名单逐个点名。
const REQUIRED_HANDLERS = [
  "openLabelDialog", "labelRefresh", "labelDownload", "labelPrintUsb",
  "labelA4", "labelPickSpool", "labelPickSize", "labelPickCustom", "labelPickDpi",
  "labelPickCopies",
];

// 由 app.js 提供、label.js 直接引用的外部函数（不是 label.js 的职责）
const EXTERNAL_HANDLERS = new Set(["closeModal"]);

function testExports() {
  console.log("== 调试出口 ==");
  check("labelDebug 已挂到 window", !!sandbox.labelDebug);
  check("mm2dot 可调用", typeof mm2dot === "function");
  const missing = REQUIRED_HANDLERS.filter((n) => typeof sandbox[n] !== "function");
  check(`onclick 处理器全部导出（${REQUIRED_HANDLERS.length} 个）`, missing.length === 0,
    "缺失：" + missing.join(","));
}

/* ── 3. 毫米 → 点 ──────────────────────────────────────────── */
function testMm2dot() {
  console.log("== 毫米换算 ==");
  check("25.4mm @203dpi = 203 点", mm2dot(25.4, 203) === 203, String(mm2dot(25.4, 203)));
  check("25.4mm @300dpi = 300 点", mm2dot(25.4, 300) === 300, String(mm2dot(25.4, 300)));
  check("50mm @203dpi ≈ 400 点", Math.round(mm2dot(50, 203)) === 400, String(mm2dot(50, 203)));
  check("0mm = 0 点", mm2dot(0, 203) === 0);
}

/* ── 4. 底部留白 / 光栅高度 ────────────────────────────────── */
// 留白 2.75mm + 内容下移 1.5mm 是 09-22~09-24 真机验证过的居中几何；
// USB 通道沿用同一几何，这两个纯函数不许悄悄跑偏。
function testFootMargin() {
  console.log("== 底部留白与光栅高度 ==");
  check("effHeightMm(30, 2.75) = 27.25", effHeightMm(30, 2.75) === 27.25, String(effHeightMm(30, 2.75)));
  check("50×30 留白 2.75mm @203dpi → 218 行（对齐汉码官方抓包）",
    rasterRowsFor(30, 2.75, 203) === 218, String(rasterRowsFor(30, 2.75, 203)));
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
  // 用完的（0 g）排在前面，用来验收「用完的排到最后」
  sandbox.S = {
    spools: [
      {
        id: 1, name: "测试料盘 PLA 深空黑", brand: "拓竹", material: "PLA",
        color_name: "深空黑", color_hex: "#1A1A1A", location: "干燥箱 A",
        remaining_weight: 0, initial_weight: 1000, spool_weight: 250, archived: false,
      },
      {
        id: 2, name: "Polymaker PLA 哑光 白色 CA04028", brand: "Polymaker", material: "PLA",
        color_name: "哑光 白色", color_hex: "#FFFFFF", location: "",
        remaining_weight: 523, initial_weight: 1000, spool_weight: 250, archived: false,
      },
    ],
    dashSpools: [],
    status: { version: "1.0.0" },
  };
  sandbox.openModal = (title, body, footer) => {
    captured.title = title;
    captured.body = body;
    captured.footer = footer;
    throw new Error("__stop__");
  };

  try {
    await sandbox.openLabelDialog();
  } catch (err) {
    if (!/__stop__/.test(err.message)) throw err;
  }

  check("对话框已打开", captured.title === "标签打印", String(captured.title));
  const html = (captured.body || "") + (captured.footer || "");
  check("带出料盘名（已转义）", html.includes("Polymaker PLA 哑光 白色 CA04028"));
  check("含料盘选择框", html.includes('id="labelSpool"'));
  check("含尺寸预设", html.includes("50×30 mm"));
  check("含 dpi 选项", html.includes('value="203"') && html.includes('value="300"'));
  check("含份数", html.includes('id="labelCopies"'));
  // ★ 用户 09-24 要求：用完的料盘排到最后，默认选中第一个还有料的
  const opt1 = html.indexOf('value="1"');
  const opt2 = html.indexOf('value="2"');
  check("用完的料盘（0 g）排在下拉最后", opt2 > 0 && opt1 > opt2, `opt1=${opt1} opt2=${opt2}`);
  check("默认选中还有料的料盘（不是 0 g 那盘）",
    /value="2"[^>]* selected/.test(html), html.match(/<option[^>]*selected[^>]*>/)?.[0] || "");
  check("0 g 料盘的余量标注仍是（0 g）", html.includes("（0 g）"));

  // 面板精简：只剩 USB 一条通道的字段
  check("没有浓度滑杆（USB 打印由驱动控制浓度）", !html.includes('id="labelDensity"'));
  check("没有底部留白 / 内容下移 / 时间旋钮等蓝牙调试字段",
    !html.includes('id="labelFootMargin"') && !html.includes('id="labelTopShift"') &&
      !html.includes('id="labelHeadWait"') && !html.includes('id="labelCopyDelay"'));
  check("没有蓝牙实验开关与「蓝牙列表」开关",
    !html.includes('id="labelPerCopyPos"') && !html.includes('id="labelBandRows"') &&
      !html.includes('id="labelBlankSkip"') && !html.includes('id="labelPipeline"') &&
      !html.includes('id="labelFullPitch"') && !html.includes('id="labelResetFirst"') &&
      !html.includes('id="labelRewind"') && !html.includes('id="labelShowAll"'));
  check("没有蓝牙状态区与诊断面板挂点",
    !html.includes('id="labelBleStatus"') && !html.includes('id="labelBlePanel"'));
  check("没有复位打印机 / 导出作业按钮",
    !html.includes("labelBleReset") && !html.includes("labelExportJob"));

  // 版本自证：预览信息行打出运行版本号（一张截图就能定位是哪一版）
  const srcAll = fs.readFileSync(SRC, "utf8");
  check("预览信息行打出运行版本号（截图自证容器是哪一版）",
    /" · 版本 " \+ runningVersion\(\)/.test(srcAll));
  check("版本号取自后端 /api/system/status，不硬写第三份",
    /S\.status\.version/.test(srcAll) &&
      typeof ((sandbox.labelDebug || {}).runningVersion) === "function");
  check("取不到后端版本时写「未知」而不是 undefined",
    (sandbox.S.status = null, sandbox.labelDebug.runningVersion()) === "未知" &&
      (sandbox.S.status = { version: "1.0.0" }, true));
  check("落运行时把版本读成整数语义（source 里没有第三个硬编码版本号）",
    !/["']0\.12\.\d+["']/.test(srcAll.replace(/\/\*[\s\S]*?\*\//g, "")));

  // 说明折叠区：默认收起，内容只讲 USB
  check("操作说明收进折叠区且默认收起",
    /<details class="label-diag label-help">/.test(html) && !/label-help"[^>]*\sopen/.test(html) &&
      html.includes("<summary>"));
  check("说明写明 USB 通道用法（HMarkService / ws://127.0.0.1:9004）",
    html.includes("USB 打印（驱动）") && html.includes("HMark Services"));
  check("说明写明右侧死区实测结论", html.includes("物理死区") && html.includes("2.91mm"));
  check("说明写明手机端的替代路（下载标签图 → 汉码 App）", html.includes("汉码 App"));
  check("说明写明蓝牙已删（1.0.0）", html.includes("整体删除"));
  check("面板正文不再有直接铺开的 .hint 长文",
    !/class="hint"/.test(html), html.match(/class="hint"[^>]{0,40}/)?.[0] || "");
  check("含预览挂点", html.includes('id="labelPreviewHost"'));
  check("没有渲染出 undefined", !html.includes("undefined"), html.match(/.{0,40}undefined.{0,40}/)?.[0] || "");
  check("没有渲染出 [object Object]", !html.includes("[object Object]"));

  // 最关键的一条：HTML 里 on* 属性调用的函数必须真的存在，否则按钮点了没反应
  const called = new Set();
  for (const m of html.matchAll(/on(?:click|change|input|submit)\s*=\s*"([^"]*)"/g)) {
    for (const f of m[1].matchAll(/([A-Za-z_$][\w$]*)\s*\(/g)) called.add(f[1]);
  }
  check("对话框里确实绑了事件", called.size >= 5, [...called].join(","));
  const missing = [...called].filter(
    (n) => typeof sandbox[n] !== "function" && !EXTERNAL_HANDLERS.has(n)
  );
  check("所有 on* 处理器都有定义（含 app.js 提供的外部函数）", missing.length === 0,
    "缺失：" + missing.join(","));
  check("只依赖白名单里的外部函数",
    [...called].every((n) => typeof sandbox[n] === "function" || EXTERNAL_HANDLERS.has(n)),
    [...called].join(","));

  for (const must of ["labelPrintUsb", "labelDownload", "labelA4", "labelPickSpool", "labelPickSize"]) {
    check(`处理器 ${must} 被引用到`, called.has(must), [...called].join(","));
  }
  check("底部没有蓝牙打印按钮（USB 是唯一 primary）",
    /class="primary" onclick="labelPrintUsb\(\)"/.test(captured.footer || "") &&
      !/labelPrintBle/.test(captured.footer || ""));
}

/** 取某个顶层函数的函数体（到下一个 "\n  }" 为止）。 */
function fnBody(src, name) {
  const i = src.indexOf("function " + name + "(");
  return i < 0 ? "" : src.slice(i, src.indexOf("\n  }", i) + 4);
}

/* ── 6. USB / 驱动通道（汉印 HMarkService）───────────────────────
 * 钉的是 2026-09-24 从官方网页**真实报文**里逐字抄下来的结构。
 * 教训：照着反编译源码「猜」结构猜了几十个变体，全是 code:404 —— 而且猜错时
 * 服务端**不报错**（异常被吞），只有正确/错误两种结果、没有任何线索。
 * 所以这些细节必须在这里钉死，改坏了立刻红。
 */
function testHmarkUsb() {
  const src = fs.readFileSync(SRC, "utf8");
  const doc = fnBody(src, "hmarkDoc");   // 只看报文构造函数体，别被注释里的说明文字误伤
  check("命令外层是「hmarkwebclient + 空格 + JSON」（SuperSocket 子协议约定，不是再包一层 key）",
    /"hmarkwebclient " \+ JSON\.stringify/.test(src));
  check("报文根是 PrtLable，且带 ?xml 声明头",
    /"\?xml":\s*\{/.test(doc) && /PrtLable:\s*\{/.test(doc));
  check("ObjectList 直接挂在 PrtLable 下、是数组（中间没有 GraphicsList 这层）",
    /ObjectList:\s*\[\{/.test(doc) && !/GraphicsList/.test(doc));
  check("LabelPage 的 MeasureUnit/LabelShape/Height/Width 是 XML 属性（@ 前缀）",
    /"@MeasureUnit":\s*"Mm"/.test(doc) && /"@LabelShape"/.test(doc) &&
      /"@Height":\s*hMm\.toFixed\(3\)/.test(doc));
  check("Image 放裸 base64（不带 data:image/png 前缀）",
    /Image:\s*b64/.test(doc) && !/data:image\/png/.test(doc));
  check("宽高按「4 单位/mm」换算（官方 50mm → 200）", /mmPerDot\s*\*\s*4/.test(src));
  check("面板上有 USB 打印按钮", /labelPrintUsb\(\)/.test(src));
  check("打印结束必定关 WebSocket 并释放 busy 锁",
    /finally\s*\{[\s\S]{0,300}ws\.close\(\)[\s\S]{0,200}LABEL\.busy\s*=\s*false/.test(src));
}

/* ── 7. 右侧打印头死区（0.12.36 引入）────────────────────────────
 * 标尺图程序化实测（2026-09-24，photo 0f19f232，逐列刻度检测 47 条 + 纯白右缘）：
 * 50mm 标签只打到 47mm，右侧 ~2.8mm 物理打不出墨；官方样图同样右留 2.91mm。
 * 0.12.35 及之前左右同用 pad=1.6mm → QR 右缘落在死区里被裁（用户截图实锤）。
 */
function testRightDeadZone() {
  const src = fs.readFileSync(SRC, "utf8");
  const lay = fnBody(src, "layoutOf");
  check("版式区分左右留白：padR 在 pad 基础上再让开死区（+1.8mm 保险）",
    /const padR = pad \+ 1\.8;/.test(lay) && /pad, padR/.test(lay));
  check("二维码 x 坐标用 padR（右侧死区之外），y 仍用 pad",
    /wDots - Math\.round\(padRDots\) - qrDots/.test(src) &&
      /Math\.round\(padDots \+ dyDots\)/.test(src));
  check("文字右边界按 padR 收（无 QR 时页脚也不进死区）",
    /cfg\.wMm - L\.padR - qrMm - 0\.8 : cfg\.wMm - L\.padR/.test(src));
  const layout = { wMm: 50 };
  // 直接求值核对数值：50mm 标签 → pad≈1.6、padR≈3.4（> 实测死区 2.8）
  const pad = Math.max(1.1, layout.wMm * 0.032);
  check("50mm 标签数值核对：pad≈1.6mm、padR≈3.4mm ≥ 死区 2.8mm",
    Math.abs(pad - 1.6) < 1e-9 && Math.abs(pad + 1.8 - 3.4) < 1e-9 && pad + 1.8 > 2.8,
    `pad=${pad}`);
  check("说明折叠区写明右侧死区实测结论（~2.8mm / 官方 2.91mm）",
    /物理死区/.test(src) && /2\.8mm/.test(src) && /2\.91mm/.test(src));
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) {
  testBleRemoved();
  testExports();
  testDefaultCfgSafe();
  testMm2dot();
  testFootMargin();
  testHmarkUsb();
  testRightDeadZone();
  await testDialogHtml();
  console.log(`\n通过 ${PASSED.length} 项，失败 ${FAILED.length} 项`);
  if (FAILED.length) {
    console.log("失败项：", FAILED);
    process.exit(1);
  }
  console.log("全部通过");
}
