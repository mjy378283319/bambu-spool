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
const {
  inferFinish, finishFromSeries, finishChoices, regionLabel, printerPhoto, parseScanText, state,
  spoolUseState, useStateTally, USE_STATE_META, priceBuckets, sortSpools,
  summaryMaterials, donutChart, allSlotEntries,
  spoolOptionHtml, bindCandidates,
} = dbg;
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

// ── 1b. 色卡系列名 -> 外观，以及「保存时外观到底发没发出去」 ────────────
console.log("== 色卡系列名里的外观 + 保存链路 ==");

// 用户反馈：「选择了哑光、选完色卡、保存后还是普通」。
// 真凶是 saveSpool() 的 payload 里压根没有 finish —— 表单上那个输入框从
// 加进来的第一天（e32a12b）起就没接过线，后端一直收得好好的也救不回来。
// 先把这个钉死：这条断言要是早写，bug 活不到今天。
check("saveSpool 的 payload 里带着 finish（读的就是表单上的外观输入框）",
  /finish:\s*document\.getElementById\("f_finish"\)\.value/.test(appSrc),
  "payload 里少了 finish —— 外观填了也存不进去");

const seriesCases = [
  ["PLA 哑光", "哑光"],
  ["PLA 丝绸", "丝绸"],
  ["PETG 哑光", "哑光"],
  ["哑光双色", "哑光"],       // 「双色」不许盖过「哑光」
  ["哑光三色", "哑光"],
  ["丝绸彩虹", "丝绸"],
  ["金属色", "金属"],
  ["PLA", ""],                // 系列名没写外观 -> 空串
  ["PLA+", ""],
  ["HT-PLA", ""],
  ["", ""],
];
for (const [series, want] of seriesCases) {
  const got = finishFromSeries(series);
  check(`finishFromSeries(${JSON.stringify(series)}) -> ${JSON.stringify(want)}`,
    got === want, `实际 ${JSON.stringify(got)}`);
}
// 「猜不出」和「确定是普通」是两回事：点普通色卡里的颜色不该把用户已经选好的
// 哑光改回普通 —— 那只是把「选了又被改掉」换个方向再犯一遍。
check("系列名没写外观时给空串而不是「普通」（否则会拿它去覆盖用户的选择）",
  finishFromSeries("PLA") === "" && finishFromSeries("PETG") === "",
  JSON.stringify([finishFromSeries("PLA"), finishFromSeries("PETG")]));
check("自动预填只在当前是空或「普通」时才动手（不覆盖用户已选的外观）",
  /function applyInferredFinish[\s\S]{0,400}?if \(cur && cur !== "普通"\) return;/.test(appSrc),
  "applyInferredFinish 少了「已有明确选择就不动」的早退");
check("色卡色块把系列名一起传下去（不然不知道点的是哪张卡）",
  /pickPresetColor\('\$\{esc\(c\.hex\)\}', '\$\{esc\(c\.name\)\}', '\$\{esc\(g\.series\)\}'\)/.test(appSrc),
  "pickPresetColor 没收到系列名");

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

// ── 8. 料盘状态口径（库存页标签页 与 汇总页概览图 共用一套） ─────
// 两处各写一套判定，就会出现「概览说 53 盘消耗完、点进标签页只剩 3 盘」。
// 判定与统计都只留 spoolUseState / useStateTally 一个实现，这里钉住语义。
console.log("== 料盘状态（消耗完 / 未拆封 / 用了一部分） ==");

const stateOf = (spool) => spoolUseState(spool);
check("余量为 0 -> 消耗完",
  stateOf({ remaining_weight: 0, used_weight: 1000 }) === "empty");
check("余量为 0 且还装在机器上 -> 仍是消耗完（不是使用中）",
  stateOf({ remaining_weight: 0, used_weight: 1000, slots: [{ label: "AMS A · 槽位 A1" }] }) === "empty");
check("没有任何用量、也没装机器 -> 未拆封",
  stateOf({ remaining_weight: 1000, used_weight: 0, usage_count: 0 }) === "unused");
check("用掉一部分 -> 使用中",
  stateOf({ remaining_weight: 700, used_weight: 300, usage_count: 1 }) === "in_use");
check("刚装到机器上、还没打印 -> 使用中",
  stateOf({ remaining_weight: 1000, used_weight: 0, usage_count: 0, slots: [{ label: "x" }] }) === "in_use");
// Number(null) === 0：余量字段缺失时被当成「0 克」就会凭空多出一堆「用完的盘」
check("余量字段缺失 + 没用过 -> 未拆封（别把「没数据」当 0 克）",
  stateOf({ used_weight: 0, usage_count: 0 }) === "unused",
  stateOf({ used_weight: 0, usage_count: 0 }));
check("余量为空串 + 有用量 -> 使用中",
  stateOf({ remaining_weight: "", used_weight: 120, usage_count: 1 }) === "in_use");

const tally = useStateTally([
  { remaining_weight: 0, used_weight: 1000 },
  { remaining_weight: 0, used_weight: 900 },
  { remaining_weight: 800, used_weight: 200, usage_count: 1 },
  { remaining_weight: 1000, used_weight: 0, usage_count: 0 },
]);
check("按状态点数正确", tally.empty === 2 && tally.in_use === 1 && tally.unused === 1,
  JSON.stringify(tally));
check("总数等于实际盘数", tally.total === 4, String(tally.total));
check("空列表不炸", useStateTally([]).total === 0 && useStateTally(undefined).total === 0);
check("三种状态都有标签与对应标签页",
  ["unused", "in_use", "empty"].every((k) => USE_STATE_META[k]
    && USE_STATE_META[k].label && USE_STATE_META[k].color && USE_STATE_META[k].tab));

// ── 9. 价格区间分档（固定五档） ────────────────────────────────
console.log("== 价格区间分布（固定五档、不重不漏） ==");

const emptyBuckets = priceBuckets([]);
check("没有料盘 -> 没有档", emptyBuckets.buckets.length === 0, JSON.stringify(emptyBuckets));
const noPrice = priceBuckets([{ price: 0 }, { price: 0 }]);
check("全都没登记价格 -> 没有档，但记下未登记数量",
  noPrice.buckets.length === 0 && noPrice.unpriced === 2, JSON.stringify(noPrice));

const EXPECTED_BANDS = ["¥0 - 10", "¥10 - 20", "¥20 - 30", "¥30 - 40", "¥40 以上"];
const p10 = priceBuckets([
  { price: 45 }, { price: 50 }, { price: 12 }, { price: 0 },
]);
check("固定五档：0-10 / 10-20 / 20-30 / 30-40 / 40以上",
  p10.buckets.length === 5 && p10.buckets.every((b, i) => b.label === EXPECTED_BANDS[i]),
  JSON.stringify(p10.buckets.map((b) => b.label)));
check("未登记价格的盘不计入档内", p10.buckets.reduce((s, b) => s + b.count, 0) === 3,
  String(p10.buckets.reduce((s, b) => s + b.count, 0)));
check("未登记数量单独给出（界面要提一句）", p10.unpriced === 1, String(p10.unpriced));
// 左开右闭：正好 50 元归「¥40 以上」，12 元归「¥10 - 20」
check("边界价落对档（45 与 50 同在「¥40 以上」，12 在「¥10 - 20」）",
  p10.buckets.find((b) => b.label === "¥40 以上").count === 2
  && p10.buckets.find((b) => b.label === "¥10 - 20").count === 1, JSON.stringify(p10.buckets));
check("每一档的占比之和约为 100%",
  Math.abs(p10.buckets.reduce((s, b) => s + b.percent, 0) - 100) < 0.01);

const hi = priceBuckets([{ price: 1200 }]);
check("单盘 1200 元也只出固定五档", hi.buckets.length === 5, String(hi.buckets.length));
check("最后一档「¥40 以上」兜住最高价",
  hi.buckets[hi.buckets.length - 1].count === 1, JSON.stringify(hi.buckets.map((b) => b.label)));

// 覆盖面：任意价格都必须落进恰好一档
let covered = true;
for (const p of [1, 7.5, 10, 33, 49.99, 50, 99, 100, 333, 999]) {
  const bs = priceBuckets([{ price: p }]).buckets;
  const n = bs.reduce((s, b) => s + b.count, 0);
  if (n !== 1) { covered = false; console.log(`    价格 ${p} 落进了 ${n} 档`); }
}
check("任意价格都恰好落进一档（不重不漏）", covered);

// ── 10. 表头排序 ────────────────────────────────────────────────
console.log("== 料盘表排序 ==");

const sortPool = [
  { id: 3, remaining_weight: 100, price: 60, last_used_at: "2026-09-10T10:00:00" },
  { id: 1, remaining_weight: 900, price: 0, last_used_at: null },
  { id: 2, remaining_weight: 500, price: 120, last_used_at: "2026-09-12T10:00:00" },
];

state.spoolSort = { key: "id", dir: "asc" };
check("默认按 ID 升序", sortSpools(sortPool).map((s) => s.id).join(",") === "1,2,3");

state.spoolSort = { key: "remaining_weight", dir: "desc" };
check("按剩余量降序",
  sortSpools(sortPool).map((s) => s.id).join(",") === "1,2,3",
  sortSpools(sortPool).map((s) => s.id).join(","));
state.spoolSort = { key: "remaining_weight", dir: "asc" };
check("按剩余量升序",
  sortSpools(sortPool).map((s) => s.id).join(",") === "3,2,1");

state.spoolSort = { key: "last_used_at", dir: "desc" };
check("按使用时间降序，从没用过的排在最后",
  sortSpools(sortPool).map((s) => s.id).join(",") === "2,3,1",
  sortSpools(sortPool).map((s) => s.id).join(","));

// 同值时按 ID 兜底：否则翻页时同一批料会来回跳
state.spoolSort = { key: "price", dir: "desc" };
const tie = sortSpools([{ id: 9, price: 50 }, { id: 4, price: 50 }, { id: 7, price: 80 }]);
check("排序值相同时按 ID 兜底（顺序稳定）",
  tie.map((s) => s.id).join(",") === "7,4,9", tie.map((s) => s.id).join(","));
check("排序不会改动原数组（只返回新数组）",
  sortPool.map((s) => s.id).join(",") === "3,1,2", sortPool.map((s) => s.id).join(","));
state.spoolSort = { key: "id", dir: "asc" };

// ── 11. 料盘行里的快捷入口 + 打印机布局 ─────────────────────────
console.log("== 料盘行操作 / 打印机布局（源码级） ==");

const cssSrc = fs.readFileSync(path.join(ROOT, "app", "static", "style.css"), "utf8");
check("每行有「详情」入口", /onclick="openSpoolDetail\(\$\{spool\.id\}\)"/.test(appSrc));
check("每行有「绑定」入口", /onclick="openBindSpoolDialog\(\$\{spool\.id\}\)"/.test(appSrc));
check("每行有「克隆」入口", /onclick="openCloneSpoolDialog\(\$\{spool\.id\}\)"/.test(appSrc));
check("克隆走的是「新增」而不是编辑（forceNew）",
  /openSpoolDialog\(\{[\s\S]{0,600}?\},\s*true,\s*src\.name\)/.test(appSrc),
  "openCloneSpoolDialog 没有传 forceNew");
check("绑定弹窗能解绑（spool_id 允许传 null）",
  /spool_id:\s*unbind\s*\?\s*null\s*:\s*spoolId/.test(appSrc));
// 7 个操作按钮分两组排版。原因不是审美：一行 7 个在 1440px 下比表格宽 ~72px，
// 会把表格顶出卡片（更窄的窗口直接出整页横向滚动条）。
// 显式分组是唯一可预测的排法 —— 「不分组 + flex-wrap」实测会被自动布局压到 181px、
// 竖着堆成 4 行（给容器 max-width、给单元格 width 提示都救不回来）。
check("库存行操作分两组（主操作一行 + 次操作一行）",
  /class="row-actions main"/.test(appSrc) && /class="row-actions sub"/.test(appSrc));
check("主操作组就是这轮新增的三个（详情 / 绑定 / 克隆）",
  /class="row-actions main">[\s\S]{0,700}?详情[\s\S]{0,300}?绑定[\s\S]{0,300}?克隆/.test(appSrc));
check("次操作组是排在后排的四个",
  /class="row-actions sub">[\s\S]{0,700}?标签[\s\S]{0,400}?补录[\s\S]{0,400}?校准[\s\S]{0,400}?删除/.test(appSrc));
check("次操作行字号更小、颜色更淡（视觉上分主次）",
  /\.row-actions\.sub button\s*\{[^}]*font-size:\s*11\.5px/.test(cssSrc)
  && /\.row-actions\.sub\s*\{[^}]*margin-top/.test(cssSrc));
// 桌面端两行都不换行（换行会连带把列宽算窄 → 又回到竖着堆的老问题）
const rowActionsRule = (cssSrc.match(/\.row-actions\s*\{([^}]*)\}/) || [, ""])[1];
check("桌面端两组操作都不换行（flex-wrap 只在窄屏媒体查询里开）",
  !/flex-wrap/.test(rowActionsRule), rowActionsRule.trim());
check("表头渲染用 sortHead（可点击排序）",
  (appSrc.match(/sortHead\("/g) || []).length >= 4, "可排序的列少于 4 个");
check("点表头切换排序方向", /function toggleSpoolSort\(/.test(appSrc));

// 风扇卡从左侧列挪到右侧列底部：右下角那块空白就是它要填的地方
const layoutFn = appSrc.slice(appSrc.indexOf("function renderPrinterCard("), appSrc.indexOf("async function requestPushall("));
const idxUnits = layoutFn.indexOf("renderUnits(");
const idxFan = layoutFn.indexOf("renderFanCard(");
check("风扇状态已排到 AMS 单元之后（右下角）",
  idxFan > idxUnits && idxUnits > 0, `units@${idxUnits} fan@${idxFan}`);
check("风扇卡带 grow 类（撑满剩余高度，右下角不留空白）",
  /renderFanCard[\s\S]{0,400}?pcard grow fan-card/.test(appSrc));
check("风扇四条通道包了一层 .fan-rows（用于均匀分布）",
  /<div class="fan-rows">/.test(appSrc));
check("两列改成等高（align-items: stretch）",
  /\.printer-layout\s*\{[^}]*align-items:\s*stretch/.test(cssSrc));
check("单列窄屏下不再硬撑高度", /\.pcard\.grow\s*\{\s*flex:\s*none/.test(cssSrc));
// 只给右列风扇卡 flex:1 不够：右列会变成较高的那一列，空白从右下角搬到左下角。
// 左列的照片卡也要吃下多余高度，两列的**内容**才都顶到底边。
check("风扇卡 flex:1（把右列撑到底）",
  /\.pcard\.grow\s*\{[^}]*flex:\s*1/.test(cssSrc));
check("照片卡也 flex:1（把左列撑到底，否则空白只是换个角）",
  /\.photo-card\s*\{[^}]*flex:\s*1/.test(cssSrc));
check("单列窄屏下照片卡也恢复自然高度",
  /\.photo-card\s*\{\s*flex:\s*none/.test(cssSrc));

// ── 12. 汇总页概览图 ────────────────────────────────────────────
console.log("== 耗材汇总：环形图与价格分布 ==");

const mats = summaryMaterials([
  { material: "PLA", remaining_weight: 500 }, { material: "PLA", remaining_weight: 300 },
  { material: "PETG", remaining_weight: 100 },
]);
check("按材料聚合、按盘数排序",
  mats.length === 2 && mats[0].label === "PLA" && mats[0].count === 2 && mats[0].remaining === 800,
  JSON.stringify(mats));
check("没填材料的归到「未填写」",
  summaryMaterials([{ material: "", remaining_weight: 1 }])[0].label === "未填写");

const donut = donutChart([
  { label: "PLA", value: 3, color: "#2563eb" },
  { label: "PETG", value: 1, color: "#16a34a" },
]);
check("环形图是合法 SVG", donut.startsWith("<svg") && donut.includes("</svg>"));
check("环形图中心写总盘数", /class="donut-total"[^>]*>4</.test(donut), donut.slice(0, 200));
// 弧长之和必须等于周长，否则末段会跟首段重叠或留缝
const box = 176, thick = 28, circ = 2 * Math.PI * ((box - thick) / 2);
const arcs = [...donut.matchAll(/stroke-dasharray="([\d.]+) ([\d.]+)"/g)]
  .map((m) => parseFloat(m[1]));
check("各段弧长之和 = 周长（不留缝不重叠）",
  Math.abs(arcs.reduce((a, b) => a + b, 0) - circ) < 0.5,
  `${arcs.join("+")} vs ${circ.toFixed(2)}`);
check("空数据也能出图（不抛异常）", donutChart([]).includes("<svg"));
check("环形图文字显式上色（全局 svg{fill:none} 会把字吃掉）",
  /\.donut-total\s*\{[^}]*fill:\s*var\(--text\)/.test(cssSrc));
// 同一类陷阱的另一半：全局 `svg { width:16px; height:16px }`（图标尺寸）会盖掉
// SVG 标签上的 width/height **属性**（属性优先级低于任意 CSS 规则），
// 环形图会被压成 16px 的小点，而弧长计算全都还是对的 —— 断言必须管到「渲染尺寸」。
const donutCss = (cssSrc.match(/\.donut\s*\{([^}]*)\}/) || [, ""])[1];
const donutW = donutCss.match(/width:\s*(\d+)px/);
check("环形图显式声明宽度（≥140px，否则被全局 svg 16px 规则压扁）",
  !!donutW && Number(donutW[1]) >= 140, donutCss.trim());
check("环形图高度自适应（height: auto，配 viewBox 保持正方形）",
  /height:\s*auto/.test(donutCss), donutCss.trim());

const slots = allSlotEntries();
check("没有打印机时不返回槽位（界面提示去同步设备）", slots.length === 0, JSON.stringify(slots));

// 摊平成清单时，普通 AMS 的 A1 和 AMS HT 的 A1 必须能区分开：
// 卡片里两者都写「A1」（各自卡片头有 AMS A / HT A），但扁平列表里会撞在一起。
state.printers_full = [{
  id: 1, name: "测试机", serial: "S1",
  state: {
    ams: [
      { ams_id: 0, name: "AMS A", trays: [{ ams_id: 0, tray_id: 0, occupied: true, color: "#111", tray_type: "PLA" }] },
      { ams_id: 128, name: "HT A", trays: [{ ams_id: 128, tray_id: 0, occupied: true, color: "#222", tray_type: "PLA" }] },
    ],
    external_spool: { occupied: true, color: "#333", tray_type: "PETG" },
  },
}];
const entries = allSlotEntries();
const slotLabels = entries.map((e) => e.label).join(" | ");
check("槽位摊平后含 AMS / AMS HT / 外挂三路", entries.length === 3, String(entries.length));
check("AMS 的 A1 与 AMS HT 的 A1 在清单里能区分",
  slotLabels.includes("AMS A 槽位 1") && slotLabels.includes("HT A 槽位 1"), slotLabels);
check("外挂料盘单独一路（amsId = -1，与绑定接口同口径）",
  entries.some((e) => e.amsId === -1 && e.label.includes("外挂料盘")), slotLabels);
check("清单里的标签带上机器名（多台机器时能分辨）",
  entries.every((e) => e.label.startsWith("测试机 · ")), slotLabels);
state.printers_full = [];

// ── 13. 页面结构（顺序与容器，改 HTML 时最容易漏） ───────────────
console.log("== 页面结构 ==");

const htmlSrc = fs.readFileSync(path.join(ROOT, "app", "static", "index.html"), "utf8");
const idxPrinter = htmlSrc.indexOf('id="printerCards"');
const idxWeek = htmlSrc.indexOf('id="weekStats"');
const idxStock = htmlSrc.indexOf('id="dashStats"');
check("仪表盘顺序：打印机状态 -> 本周概览 -> 库存与费用",
  idxPrinter > 0 && idxPrinter < idxWeek && idxWeek < idxStock,
  `printer@${idxPrinter} week@${idxWeek} stock@${idxStock}`);
check("料盘库存多了「已用尽」标签页", /data-tab="empty"/.test(htmlSrc));
check("汇总页有库存概览容器", /id="summaryOverview"/.test(htmlSrc));
check("汇总页有价格区间分布容器", /id="priceDist"/.test(htmlSrc));
check("概览的筛选态有清除按钮", /id="overviewClear"/.test(htmlSrc));

// ── 14. 绑定下拉里的料盘候选 ─────────────────────────────────────
console.log("== 槽位绑定下拉：候选与文案 ==");

const opNormal = spoolOptionHtml({ id: 3, name: "哑光黑", remaining_weight: 640 });
check("常规料盘：名字 + 余量",
  /value="3"/.test(opNormal) && /哑光黑（余 640 g）/.test(opNormal), opNormal);
const opNull = spoolOptionHtml({ id: 4, name: "缺字段", remaining_weight: null });
check("余量缺失写「余量未知」，不会变成 0 g（Number(null) === 0）",
  /余量未知/.test(opNull) && !/余 0 g/.test(opNull), opNull);
const opArch = spoolOptionHtml({ id: 5, name: "旧料", remaining_weight: 100, archived: true });
check("归档料盘标注「已归档」", /已归档/.test(opArch), opArch);
const opSel = spoolOptionHtml({ id: 6, name: "当前", remaining_weight: 10 }, true);
check("被选中的那项带 selected", / selected/.test(opSel), opSel);
check("没要求选中时不乱加 selected", !/ selected/.test(opNormal), opNormal);

state.spools = [
  { id: 1, name: "在用", archived: false, remaining_weight: 100 },
  { id: 2, name: "归档", archived: true, remaining_weight: 50 },
  { id: 3, name: "归档但正绑着", archived: true, remaining_weight: 30 },
];
check("归档料盘不进候选（绑上去没意义）",
  bindCandidates(0).map((s) => s.id).join(",") === "1",
  bindCandidates(0).map((s) => s.id).join(","));
check("当前正绑着的那盘归档料要保留（否则弹窗看着像绑定丢了）",
  bindCandidates(3).map((s) => s.id).join(",") === "1,3",
  bindCandidates(3).map((s) => s.id).join(","));

// 源码级：料盘列表不能在「只进过仪表盘」时缺席
check("启动（enterApp）就把料盘列表拉回来，不再只靠进库存页触发",
  /await loadSpools\(\)\.catch/.test(appSrc) && /await loadSpools\(\)\.catch/.test(
    appSrc.slice(appSrc.indexOf("async function enterApp"), appSrc.indexOf("async function enterApp") + 700)),
  "enterApp 里没看到 loadSpools");
check("槽位弹窗在列表为空时会自己补拉一次",
  /if \(!\(S\.spools \|\| \[\]\)\.length\) ensureSpoolOptions\(boundId\)/.test(appSrc));
check("bind= 深链也会确保料盘列表已加载（与 spool= 分支口径一致）",
  /loadPrinters\(\)\.catch\(\(\) => \{\}\);\s*\/\/[^\n]*\n\s*if \(!\(S\.spools \|\| \[\]\)\.length\) await loadSpools/.test(appSrc)
  || (appSrc.match(/if \(!\(S\.spools \|\| \[\]\)\.length\) await loadSpools\(\)\.catch/g) || []).length >= 2,
  String((appSrc.match(/await loadSpools\(\)\.catch/g) || []).length));

state.spools = [];

// ── 汇总 ────────────────────────────────────────────────────────
console.log("");
if (FAILED.length) {
  console.log(`通过 ${PASSED.length} 项，失败 ${FAILED.length} 项`);
  console.log(`失败项： ${JSON.stringify(FAILED)}`);
  process.exit(1);
}
console.log(`通过 ${PASSED.length} 项，失败 0 项`);
console.log("界面口径自测全部通过。");
