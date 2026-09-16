/* 前端口径自测（node 直跑，不需要浏览器、不需要相机）。
 *
 * 这一批函数都是「看着正常但其实不对」的高危区，全是照着用户反馈改出来的：
 *   1. inferFinish   —— 颜色名自动预填外观（用户说「无法设置丝绸、哑光等外观」）
 *   2. finishChoices —— 外观候选去重合并（预设 + 库里实际用过的写法）
 *   3. regionLabel   —— 区域文案。就是它写成 `=== "china" ? 中国大陆 : 海外`，
 *                       才让设置页无论账号在哪都显示「海外」，用户直接来问过
 *   4. printerPhoto  —— 机型 -> 真机照片（用户说「改成真实的机器图片」）
 *   5. parseScanText —— 扫码认码（料盘码 / 槽位码 / 纯数字）
 *
 * app.js 与 scan.js 都是给浏览器写的普通脚本，这里用 vm 把它们跑在一个最小沙箱里
 * （补 document / window / navigator），并把 app.js 末尾的 boot() 摘掉（它会发真实请求）。
 *
 * 运行： node tests/test_ui_polish.mjs
 */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const APP_JS = path.join(ROOT, "app", "static", "app.js");
const SCAN_JS = path.join(ROOT, "app", "static", "scan.js");

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

// ── 最小 DOM 沙箱 ───────────────────────────────────────────────
function stubEl() {
  const el = {
    style: {}, dataset: {}, innerHTML: "", outerHTML: "", textContent: "",
    value: "", checked: false, hidden: false, disabled: false,
    files: [], children: [], options: [], selectedIndex: 0,
    classList: { add() {}, remove() {}, toggle() {}, contains() { return false; } },
    appendChild(node) { return node; },
    removeChild() {}, remove() {},
    setAttribute() {}, getAttribute() { return null; },
    hasAttribute() { return false; }, removeAttribute() {},
    addEventListener() {}, removeEventListener() {},
    querySelector() { return stubEl(); }, querySelectorAll() { return []; },
    closest() { return stubEl(); }, contains() { return false; },
    focus() {}, blur() {}, click() {}, scrollIntoView() {},
    insertAdjacentHTML() {}, replaceChildren() {},
    getBoundingClientRect() { return { top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 }; },
    getContext() { return null; }, toDataURL() { return ""; },
  };
  return el;
}

const store = new Map();
const localStorageStub = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => store.set(k, String(v)),
  removeItem: (k) => store.delete(k),
  clear: () => store.clear(),
};

const sandbox = {
  console,
  setTimeout: () => 0,
  clearTimeout: () => {},
  setInterval: () => 0,
  clearInterval: () => {},
  requestAnimationFrame: () => 0,
  localStorage: localStorageStub,
  fetch: () => new Promise(() => {}),
  WebSocket: class { constructor() { this.readyState = 0; } send() {} close() {} addEventListener() {} },
  alert() {}, confirm: () => false, prompt: () => null,
  btoa: (s) => Buffer.from(s, "binary").toString("base64"),
  atob: (s) => Buffer.from(s, "base64").toString("binary"),
  Blob: class {}, Image: class { set src(_v) {} },
  Event: class { constructor(type) { this.type = type; } },
  URL: { createObjectURL: () => "", revokeObjectURL() {} },
  // 浏览器只在 HTTPS / localhost 下才给 mediaDevices，沙箱里默认当成「有相机」
  isSecureContext: true,
  navigator: {
    clipboard: { writeText: async () => {} },
    mediaDevices: { getUserMedia: async () => { throw new Error("no camera in test"); } },
  },
  location: { hash: "", href: "http://localhost/", pathname: "/", search: "", reload() {} },
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
sandbox.document = {
  getElementById: () => stubEl(),
  querySelector: () => stubEl(),
  querySelectorAll: () => [],
  createElement: () => stubEl(),
  createDocumentFragment: () => stubEl(),
  addEventListener() {}, removeEventListener() {},
  body: stubEl(), head: stubEl(), documentElement: stubEl(), cookie: "",
};
// 记下 window 上挂了哪些监听：hashchange 是「应用开着时扫码」能否生效的关键
const windowListeners = new Map();
sandbox.window.addEventListener = (type, fn) => {
  if (!windowListeners.has(type)) windowListeners.set(type, []);
  windowListeners.get(type).push(fn);
};
sandbox.window.removeEventListener = () => {};
sandbox.window.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
sandbox.window.localStorage = localStorageStub;

const ctx = vm.createContext(sandbox);
let appSrc = fs.readFileSync(APP_JS, "utf8");
appSrc = appSrc.replace(/^boot\(\);\s*$/m, "");
vm.runInContext(appSrc, ctx, { filename: "app.js" });
vm.runInContext(fs.readFileSync(SCAN_JS, "utf8"), ctx, { filename: "scan.js" });

const dbg = sandbox.window.panelDebug;
if (!dbg) {
  console.error("app.js 没有导出 window.panelDebug，无法自测（是不是被改掉了？）");
  process.exit(1);
}
const { inferFinish, finishChoices, regionLabel, printerPhoto, parseScanText, state } = dbg;
const scanner = sandbox.window.spoolScanner;
if (!scanner) {
  console.error("scan.js 没有导出 window.spoolScanner，无法自测。");
  process.exit(1);
}

// ── 1. 颜色名 -> 外观预填 ───────────────────────────────────────
console.log("== 外观预填（颜色名里带工艺词就自动填上） ==");

const finishCases = [
  ["丝绸白", "丝绸"],
  ["丝滑白", "丝绸"],          // 牌子上印「丝滑」的比「丝绸」多
  ["PLA Silk 金色", "丝绸"],   // 英文也是牌子上常见的写法
  ["哑光黑", "哑光"],
  ["Matte 黑", "哑光"],
  ["磨砂红", "磨砂"],
  ["金属银", "金属"],
  ["珠光白", "珠光"],
  ["碳纤黑", "碳纤"],
  ["夜光绿", "夜光"],
  ["木纹棕", "木纹"],
  ["亮面黑", "亮面"],
  ["双色红蓝", "双色"],
  ["彩虹渐变", "渐变"],
  ["普通黑", "普通"],
  ["黑色", "普通"],            // 没线索就是普通
  ["", "普通"],
];
for (const [text, want] of finishCases) {
  const got = inferFinish(text);
  check(`inferFinish(${JSON.stringify(text)}) -> ${want}`, got === want, `实际 ${JSON.stringify(got)}`);
}

// 这一条是写测试时抓出来的真 bug：关键词表里「透明」排在「半透」前面，
// 于是「半透明黑」含「透明」先命中，半透料盘被判成透明。
check("「半透明黑」判成半透而不是透明（关键词顺序敏感）",
  inferFinish("半透明黑") === "半透", inferFinish("半透明黑"));
check("「translucent」判成半透", inferFinish("translucent 灰") === "半透", inferFinish("translucent 灰"));
// 同理：丝绸要压过哑光
check("「丝绸哑光」判成丝绸", inferFinish("丝绸哑光白") === "丝绸", inferFinish("丝绸哑光白"));

// ── 2. 外观候选列表 ─────────────────────────────────────────────
console.log("== 外观候选（预设 + 库里实际用过的写法，不重复） ==");

state.catalog = { finishes: ["普通", "哑光", "丝绸", "其他"] };
state.spools = [
  { finish: "哑光" }, { finish: "丝绸" }, { finish: "定制电镀" }, { finish: "" }, {},
];
const fChoices = finishChoices();
check("候选里没有重复项", fChoices.length === new Set(fChoices).size, JSON.stringify(fChoices));
check("预设排在前、库里的自定义写法补在后",
  fChoices.slice(0, 4).join(",") === "普通,哑光,丝绸,其他"
  && fChoices.includes("定制电镀"), JSON.stringify(fChoices));
check("空外观不会塞进候选", !fChoices.includes(""), JSON.stringify(fChoices));
check("额外值会去重合并", finishChoices("哑光").filter((x) => x === "哑光").length === 1);

// ── 3. 区域文案 ─────────────────────────────────────────────────
console.log("== 区域文案（未知值不许冒充某个区域） ==");

check('china -> 中国大陆', regionLabel("china") === "中国大陆", regionLabel("china"));
check('CHINA 大小写不敏感', regionLabel("CHINA") === "中国大陆", regionLabel("CHINA"));
check('global -> 海外', regionLabel("global") === "海外", regionLabel("global"));
// 关键回归：修复前 undefined 会被显示成「海外」，用户看到的就是这个 bug
check("undefined 不再显示成「海外」", regionLabel(undefined) !== "海外", regionLabel(undefined));
check("undefined -> 未设置", regionLabel(undefined) === "未设置", regionLabel(undefined));
check("空串 -> 未设置", regionLabel("") === "未设置", regionLabel(""));
check("未知值显式标出来（不冒充区域）",
  regionLabel("eu") === "未知（eu）", regionLabel("eu"));

// ── 4. 机型 -> 真机照片 ─────────────────────────────────────────
console.log("== 真机照片（有图用图，没图退回内联 SVG） ==");

const images = { P2S: "/static/printer/p2s.jpg", X1C: "/static/printer/x1c.png" };
check("P2S 命中", printerPhoto("P2S", images) === "/static/printer/p2s.jpg", printerPhoto("P2S", images));
check("机型大小写与空格不敏感",
  printerPhoto(" p2s ", images) === "/static/printer/p2s.jpg", printerPhoto(" p2s ", images));
check("没配照片的机型返回空（前端会退回 SVG）",
  printerPhoto("A1MINI", images) === "", `实际 ${printerPhoto("A1MINI", images)}`);
check("机型为空不炸", printerPhoto(null, images) === "" && printerPhoto(undefined, images) === "");
check("后端没给表也不炸", printerPhoto("P2S", {}) === "" && printerPhoto("P2S", undefined) === "");

// ── 5. 扫码认码 ─────────────────────────────────────────────────
console.log("== 扫码认码（料盘码 / 槽位码 / 纯数字） ==");

const scanCases = [
  ["http://nas:8000/#spool=12", { kind: "spool", id: 12 }],
  ["https://cd.example.com/#spool=7", { kind: "spool", id: 7 }],
  ["12", { kind: "spool", id: 12 }],
  [" http://nas:8000/#bind=1:0:2 ", { kind: "bind", printer: 1, ams: 0, tray: 2 }],
  // 外挂料盘的 ams_id 是 -1，写成 (\d+) 会漏掉这种码
  ["http://nas:8000/#bind=1:-1:0", { kind: "bind", printer: 1, ams: -1, tray: 0 }],
  ["http://nas:8000/?spool=5", { kind: "spool", id: 5 }],
  ["", null],
  ["   ", null],
  ["这不是二维码内容", null],
  ["http://nas:8000/#", null],
];
for (const [text, want] of scanCases) {
  const got = parseScanText(text);
  const ok = JSON.stringify(got) === JSON.stringify(want);
  check(`parseScanText(${JSON.stringify(text)})`, ok, `实际 ${JSON.stringify(got)} 期望 ${JSON.stringify(want)}`);
}

// 同一套规则必须同时存在于 app.js 和 scan.js，两边不一致就会出现
// 「相机扫码认得、手输号码不认得」这种极难排查的现象
// （2026-09-16：扫码枪输入框已按用户要求从界面移除，这条一致性约束仍然成立 ——
//  app.js 的兜底 parseScanText 在 scan.js 没加载时要用）
for (const [text] of scanCases) {
  const a = JSON.stringify(parseScanText(text));
  const b = JSON.stringify(scanner.parseScan(text));
  check(`app.js 与 scan.js 认码一致：${JSON.stringify(text)}`, a === b, `app=${a} scan=${b}`);
}

// ── 6. 相机可用性判定 ───────────────────────────────────────────
console.log("== 相机可用性（不能只说「不支持」，要说清原因） ==");

check("HTTPS 且有相机接口 -> 不拦截", scanner.cameraBlockReason() === "", scanner.cameraBlockReason());
sandbox.isSecureContext = false;
const insecure = scanner.cameraBlockReason();
check("http 下说明原因并指向「拍照识别」",
  insecure.includes("HTTPS") && insecure.includes("拍照识别"), insecure);
sandbox.isSecureContext = true;
const savedMd = sandbox.navigator.mediaDevices;
sandbox.navigator.mediaDevices = undefined;
check("没有相机接口时给的是换浏览器的建议",
  scanner.cameraBlockReason().includes("Chrome"), scanner.cameraBlockReason());
sandbox.navigator.mediaDevices = savedMd;

check("扫码取样宽度留了余量（逐帧解码别用原图）",
  scanner._internals.LIVE_MAX_WIDTH <= 720 && scanner._internals.LIVE_MAX_WIDTH >= 320,
  String(scanner._internals.LIVE_MAX_WIDTH));

// ── 6.5 相机被拒时，必须能说出是「哪一层」拦的 ──────────────────
// 手机上相机权限有两层（站点层 / 系统给浏览器 App 的权限），表现却是同一句
// NotAllowedError。只说「去站点设置里允许相机」，用户改完还是不行就会来回问。
console.log("== 相机被拒：分清站点层与系统层 ==");

sandbox.navigator.permissions = { query: async () => ({ state: "denied" }) };
const hintSite = await scanner._internals.cameraDeniedHint({ name: "NotAllowedError" });
check("站点层被记成「已阻止」-> 指向地址栏图标",
  hintSite.includes("已阻止") && hintSite.includes("地址栏") && !hintSite.includes("系统设置"),
  hintSite);

sandbox.navigator.permissions = { query: async () => ({ state: "prompt" }) };
const hintApp = await scanner._internals.cameraDeniedHint({ name: "NotAllowedError" });
check("站点没拦 -> 说明是系统没给浏览器相机权限",
  hintApp.includes("系统设置") && !hintApp.includes("地址栏"), hintApp);

sandbox.navigator.permissions = { query: async () => { throw new Error("unsupported"); } };
const hintUnknown = await scanner._internals.cameraDeniedHint({ name: "NotAllowedError" });
check("查不到权限状态 -> 两处都列出来",
  hintUnknown.includes("①") && hintUnknown.includes("②"), hintUnknown);
check("提示带上错误码（手机没法开控制台，只能靠截图）",
  hintUnknown.includes("NotAllowedError"), hintUnknown);

// ── 6.6 服务端 Permissions-Policy 把相机关掉时必须认出来 ─────────
// 真实事故（2026-09-16）：app/main.py 的 _harden() 写的是 camera=()，空括号 =
// 对「所有来源」（含本站自己）禁用相机。浏览器读到就直接把 getUserMedia 拒成
// NotAllowedError，**权限弹窗一次都不会弹** —— 现象和「手机没给浏览器相机权限」
// 一模一样。用户换了两台手机、两个浏览器（安卓 Edge / 鸿蒙自带）全开不了相机，
// 照着提示改手机设置永远改不好。这条断言钉住「能认出来、且指向服务端」。
console.log("== 服务端把相机禁掉：要指向服务端，别让人去改手机 ==");

sandbox.document.featurePolicy = { allowsFeature: (f) => f !== "camera" };
check("policyBlocksCamera 能认出被策略拦掉",
  scanner._internals.policyBlocksCamera() === true);
const policyReason = scanner.cameraBlockReason();
check("被策略拦掉 -> 原因指向 Permissions-Policy，并推「拍照识别」",
  policyReason.includes("Permissions-Policy") && policyReason.includes("拍照识别"),
  policyReason);
check("被策略拦掉 -> 不再指路到手机权限设置",
  !policyReason.includes("地址栏") && !policyReason.includes("系统设置"), policyReason);

// 权限状态还报 granted（鸿蒙那边就是「相机已允许」），也必须先说服务端
sandbox.navigator.permissions = { query: async () => ({ state: "granted" }) };
const policyHint = await scanner._internals.cameraDeniedHint({ name: "NotAllowedError" });
check("策略拦掉时优先说服务端，不顺着权限状态指错路",
  policyHint.includes("服务端") && !policyHint.includes("系统设置")
  && !policyHint.includes("地址栏"), policyHint);
check("策略拦掉时给出服务端该怎么改（camera=(self)）",
  policyHint.includes("camera=(self)"), policyHint);

sandbox.document.featurePolicy = { allowsFeature: () => true };
check("策略允许时不算被拦", scanner._internals.policyBlocksCamera() === false);
delete sandbox.document.featurePolicy;
check("浏览器没有该 API 时不误报", scanner._internals.policyBlocksCamera() === false);

// ── 6.7 诊断函数必须真的接在失败分支上（上一轮的教训）───────────
// cameraDeniedHint 写好了、也导出了，但 getUserMedia 的 catch 里还是旧那句
// 硬编码 —— 函数成了死代码，用户看到的报错文案一个字都没变。单测调得到它，
// 所以只测函数本身抓不住，必须钉源码。
console.log("== 诊断提示真的接在 getUserMedia 失败分支上 ==");

const scanSrc = fs.readFileSync(SCAN_JS, "utf8");
check("catch 分支调用了 cameraDeniedHint",
  /await\s+cameraDeniedHint\(/.test(scanSrc), "cameraDeniedHint 没人调（死代码）");
check("旧的硬编码权限提示已清掉",
  !scanSrc.includes("请在浏览器地址栏的站点设置里允许相机"), "旧文案还在");

sandbox.navigator.permissions = undefined;

// ── 6.8 扫码入口只剩相机（扫码枪输入框已按用户要求移除）──────────
// 用户原话：「把这个在界面上删了吧用不到」。那个 input 在手机上就是一块死 UI
// （没有键盘，光标放进去也没法扫），但它是「扫码」这个功能的原始实现，
// 以后改槽位弹窗时很容易顺手复制回来，所以钉一条断言。
console.log("== 扫码入口只剩相机 ==");

const scanGunLeft = (appSrc.match(/id="bindScan"|handleScan/g) || []).join(",");
check("槽位弹窗里不再有扫码枪输入框", scanGunLeft === "", `残留 ${scanGunLeft}`);
check("槽位弹窗仍保留「相机扫码」入口",
  /scanForSlotBind\(/.test(appSrc), "找不到 scanForSlotBind");
check("料盘页工具栏的扫码按钮也在",
  /onclick="scanSpoolCode\(\)"/.test(appSrc) || /scanSpoolCode\(/.test(appSrc),
  "找不到 scanSpoolCode");

// ── 7. 扫码深链在「应用已经开着」时也要生效 ─────────────────────
console.log("== 扫码深链（系统相机扫出来的 #spool= / #bind= 要能被应用接住） ==");

// 手机上最常见的用法：应用开着 → 用系统相机扫二维码 → 浏览器只换 hash 不重载页面。
// 以前没有 hashchange 监听，用户看到的是「扫了，什么都没发生」。
check("注册了 window hashchange 监听",
  windowListeners.has("hashchange") && windowListeners.get("hashchange").length > 0,
  JSON.stringify([...windowListeners.keys()]));

// ── 汇总 ────────────────────────────────────────────────────────
console.log("");
if (FAILED.length) {
  console.log(`通过 ${PASSED.length} 项，失败 ${FAILED.length} 项`);
  console.log(`失败项： ${JSON.stringify(FAILED)}`);
  process.exit(1);
}
console.log(`通过 ${PASSED.length} 项，失败 0 项`);
console.log("界面口径自测全部通过。");
