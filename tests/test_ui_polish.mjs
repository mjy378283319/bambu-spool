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
    // 真的把节点挂上去：钻取那条断言要看「下拉里有没有补出这个 option」
    appendChild(node) {
      this.children.push(node);
      if (node && node.tagName === "OPTION") this.options.push(node);
      return node;
    },
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
  // 定时器不真跑：push 进队列，测试里用 __flushTimers 手动触发。
  // closeModal 的 back() 现在延迟一拍，竞态测试要能控制「这一拍」的时机。
  __timers: [],
  __flushTimers: () => { while (sandbox.__timers.length) sandbox.__timers.shift()(); },
  setTimeout: (fn) => { sandbox.__timers.push(fn); return sandbox.__timers.length; },
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
  // 视图路由与弹窗都靠 history 改地址。
  //
  // ⚠️ 2026-09-18 修正：这里原来只实现了 replaceState，pushState 是个空函数 ——
  // 于是「后退键能不能用」这类断言根本无从验起（历史栈永远是空的）。
  // 现在做一个**真的历史栈**：pushState 入栈、back() 出栈，两者都改 location.hash。
  // 注意浏览器语义：pushState/replaceState **不派发 hashchange**（这正是防自激的关键），
  // back() 才派发 popstate。所以这里也不触发监听器，让测试自己去调。
  history: (() => {
    const stack = [];
    const setHash = (url) => {
      const i = String(url || "").indexOf("#");
      sandbox.location.hash = i >= 0 ? String(url).slice(i) : "";
    };
    return {
      get _stack() { return stack.slice(); },
      _reset() { stack.length = 0; },
      replaceState(_state, _title, url) {
        if (stack.length) stack[stack.length - 1] = sandbox.location.hash;
        else stack.push(sandbox.location.hash);
        setHash(url);
        stack[stack.length - 1] = sandbox.location.hash;
      },
      pushState(_state, _title, url) {
        setHash(url);
        stack.push(sandbox.location.hash);
      },
      back() {
        if (stack.length < 2) return;      // 只有一条记录，后退无处可去
        stack.pop();
        sandbox.location.hash = stack[stack.length - 1];
      },
    };
  })(),
};
sandbox.window = sandbox;
sandbox.globalThis = sandbox;
// 按 id 缓存元素：钻取这类「给下拉赋值、再读回来」的断言必须拿到同一个对象。
// 每次 getElementById 都发一个新的 stub 的话，写进去的值下一次调用就读不出来了，
// 断言会永远是「看起来通过了」（写这条时实测过，确实读不到）。
const elCache = new Map();
sandbox.document = {
  getElementById(id) {
    if (!elCache.has(id)) elCache.set(id, stubEl());
    return elCache.get(id);
  },
  querySelector: () => stubEl(),
  querySelectorAll: () => [],
  createElement: (tag) => {
    const el = stubEl();
    el.tagName = String(tag || "").toUpperCase();
    return el;
  },
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
  VIEW_NAMES, syncHashView, VIEW_STORE_KEY, lastRememberedView, rememberView, applyHashRoute,
  SUMMARY_DRILL_FIELDS, summaryPriceStats, priceStatCards, summaryTable, renderBrandDist,
  jobRowActions,
} = dbg;
const scanner = sandbox.window.spoolScanner;
if (!scanner) {
  console.error("scan.js 没有导出 window.spoolScanner，无法自测。");
  process.exit(1);
}

// 新加的自测钩子必须真的在 panelDebug 里 —— 少了它就是 `undefined is not a function`，
// 报错信息会指向测试文件而不是「忘了导出」，查起来要绕一圈。
for (const name of [
  "openRebindUsage", "submitRebindUsage", "renderSpoolPicker", "renderRebindTargets",
  "onRebindTargetInput", "pickRebindTarget", "refreshRebindTargetPicked",
  "spoolPickerHtml", "fillPickerAfterPick",
  "syncFilterOptions", "loadCatalog",
  "jumpToSpoolsNoPrice", "clearNoPriceFilter", "syncNoPriceChip",
  "armComboInputs", "armComboInput", "comboRender", "comboClose", "comboOptions",
  "canonicalBrand",
  "applyBrandTare", "onTareInput",
]) {
  if (typeof dbg[name] !== "function") {
    console.error(`panelDebug 缺少导出：${name}（app.js 末尾的 window.panelDebug 里补上）`);
    process.exit(1);
  }
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

// 档位拆拆合合的历史（都写在 PRICE_BANDS 的注释里）：用户 2026-09-18 反馈
// 盘太少，40-50 与 50 以上各只有一两盘太碎，合并回「¥40 以上」上不封顶。
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
// 左开右闭：正好 40 元归「¥30 - 40」，45 与 50 都归「¥40 以上」
check("边界价落对档（40 归 30-40 档；45 与 50 都在「¥40 以上」）",
  p10.buckets.find((b) => b.label === "¥30 - 40").count === 0
  && p10.buckets.find((b) => b.label === "¥40 以上").count === 2
  && p10.buckets.find((b) => b.label === "¥10 - 20").count === 1, JSON.stringify(p10.buckets));
check("每一档的占比之和约为 100%",
  Math.abs(p10.buckets.reduce((s, b) => s + b.percent, 0) - 100) < 0.01);

const hi = priceBuckets([{ price: 1200 }]);
check("单盘 1200 元也只出固定五档", hi.buckets.length === 5, String(hi.buckets.length));
check("最后一档「¥40 以上」兜住最高价",
  hi.buckets[hi.buckets.length - 1].count === 1, JSON.stringify(hi.buckets.map((b) => b.label)));

// 边界 40 只能落一档（左开右闭：40 归 30-40，40.01 才算 40 以上）
const merged = priceBuckets([{ price: 39.99 }, { price: 40 }, { price: 88 }]);
check("合并后不重不漏（39.99 与 40 都在 30-40，88 在 40 以上）",
  merged.buckets.find((b) => b.label === "¥30 - 40").count === 2
  && merged.buckets.find((b) => b.label === "¥40 以上").count === 1,
  JSON.stringify(merged.buckets.map((b) => `${b.label}=${b.count}`)));
check("边界价 40 只落一档（不会被 30-40 和 40 以上重复计数）",
  merged.buckets.reduce((s, b) => s + b.count, 0) === 3,
  JSON.stringify(merged.buckets.map((b) => `${b.label}=${b.count}`)));

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
// 比的是「次操作行比主操作行小」，不是写死 11.5px —— 整体放大那一轮字号全调过一次，
// 写死数值的断言立刻误报（实测过：放大后这里就红了，代码其实没问题）。
const rulePx = (rule) => {
  const m = rule.match(/font-size:\s*([\d.]+)px/);
  return m ? parseFloat(m[1]) : NaN;
};
const subBtnRule = (cssSrc.match(/\.row-actions\.sub button\s*\{([^}]*)\}/) || [, ""])[1];
const mainBtnRule = (cssSrc.match(/\.row-actions button\s*\{([^}]*)\}/) || [, ""])[1];
check("次操作行字号更小、颜色更淡（视觉上分主次）",
  rulePx(subBtnRule) < rulePx(mainBtnRule)
  && /\.row-actions\.sub\s*\{[^}]*margin-top/.test(cssSrc),
  `sub=${rulePx(subBtnRule)} main=${rulePx(mainBtnRule)}`);
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

// ── 15. 视图路由：刷新后留在原页面 ──────────────────────────────
console.log("== 视图路由（刷新要停在原页面，不能每次都被弹回仪表盘） ==");

const navViews = [...new Set([...htmlSrc.matchAll(/data-view="([^"]+)"/g)].map((m) => m[1]))];
check("导航栏里每个视图都有对应的 hash 名（新增视图最容易漏这一处）",
  navViews.length > 0 && navViews.every((v) => VIEW_NAMES.includes(v)),
  `nav=${JSON.stringify(navViews)} VIEW_NAMES=${JSON.stringify(VIEW_NAMES)}`);
check("VIEW_NAMES 含汇总页（漏了它，#view=summary 会被当无效 hash 掉回仪表盘）",
  VIEW_NAMES.includes("summary"), JSON.stringify(VIEW_NAMES));
// 注意：这里用**运行时**断言而不是「源码里出现了 syncHashView(name)」——
// 后者连被注释掉的那行都能匹配上（写这条时实测：把调用注释掉，测试照样全绿）。
// dashboard 不触发任何数据加载，用来验证路由最干净。
sandbox.location.hash = "";
sandbox.switchView("dashboard");
check("switchView 之后地址栏记下了当前视图（刷新就靠它回来）",
  sandbox.location.hash === "#view=dashboard", sandbox.location.hash || "(空)");
sandbox.location.hash = "";
// ⚠️ 2026-09-18 改了：原来钉的是「用 replaceState」——那条断言把
// 「后退键完全不可用」这个 bug 一起钉死了（replaceState 一个历史条目都不建）。
// 现在要求 pushState（真建条目）+ 不许用 location.hash 赋值（那会触发 hashchange 自激）。
check("写地址用 pushState 真建历史条目（用户报的后退键不能用就是这个）",
  /history\.pushState\(null, "", "#view=" \+ name\)/.test(appSrc)
  && !/location\.hash\s*=\s*["'`]#view/.test(appSrc),
  "视图路由必须用 pushState 且不许用 location.hash 赋值");
check("applyHashRoute 认识 #view=<name>", /hash\.startsWith\("view="\)/.test(appSrc));
check("#view= 的名字要过白名单（不能拿任意字符串去 switchView）",
  /if \(VIEW_NAMES\.includes\(name\)\) \{ switchView\(name\); return; \}/.test(appSrc));
// ⚠️ 用**运行时**行为断言，不要去匹配源码里的多行块（上一版的正则就是这么假红的）。
// 用户报的 bug 是「每次刷新都回仪表盘」：地址栏干净时（按 F5 就是这样），
// 应该回上次那个视图；从没记录过才落仪表盘。
sandbox.location.hash = "";
localStorageStub.clear();
sandbox.switchView("dashboard");
sandbox.location.reload = () => {};
await sandbox.applyHashRoute({ initial: true });
check("首次打开（localStorage 也没有记录）落仪表盘",
  state.view === "dashboard", JSON.stringify(state.view));

sandbox.location.hash = "";
sandbox.switchView("jobs");
await sandbox.applyHashRoute({ initial: true });
check("hash 为空但记过视图时，启动落回那个视图（不是仪表盘）",
  state.view === "jobs", JSON.stringify(state.view));

sandbox.location.hash = "";
localStorageStub.clear();
await sandbox.applyHashRoute({ initial: true });
check("记录被清掉后启动又回到仪表盘（兜底仍在）",
  state.view === "dashboard", JSON.stringify(state.view));
sandbox.switchView("dashboard");
// 深链弹窗关掉后要把地址换回 #view=（否则随手刷新又弹回来）。
// 现在 closeModal 走的是 history.replaceState（不是 syncHashView）——
// 用 replaceState 是刻意的：这条记录本来就代表「那个深链」，
// 关掉弹窗应当**原地改写**它，而不是再压一条新的（否则后退会退进死循环）。
check("关掉深链弹窗会把 hash 换成 #view=（否则随手刷新又把它弹回来）",
  /function closeModal\([\s\S]{0,600}?history\.replaceState\(null, "", "#view=" \+ \(S\.view \|\| "dashboard"\)\)/
    .test(appSrc));

sandbox.location.hash = "";
syncHashView("summary");
check("切到汇总页后地址栏是 #view=summary",
  sandbox.location.hash === "#view=summary", sandbox.location.hash);

sandbox.location.hash = "#spool=12";
syncHashView("spools");
check("扫码深链不被 #view= 盖掉（盖了刷新就找不到那盘料了）",
  sandbox.location.hash === "#spool=12", sandbox.location.hash);
syncHashView("spools", true);
check("强制写入时深链换成 #view=spools（关弹窗那条路径）",
  sandbox.location.hash === "#view=spools", sandbox.location.hash);
sandbox.location.hash = "";

// ── 15b. 后退 / 前进键（用户报「鼠标侧键和浏览器后退都用不了」）───────────
console.log("== 后退键：视图切换与弹窗开关都要能退回去 ==");

// 真验一次历史栈：切两个视图，然后 back()，看能不能退回来。
// 只断言「源码里调了 pushState」是不够的 —— 那样拦不住「push 了但 popstate
// 没接上」，用户按后退仍然毫无反应（正是这次的 bug）。
sandbox.history._reset();
sandbox.location.hash = "";
sandbox.document.getElementById("modalHost").innerHTML = "";
sandbox.switchView("dashboard");
sandbox.switchView("spools");
check("切视图后历史栈里有多条记录（后退才有地方可退）",
  sandbox.history._stack.length >= 2, JSON.stringify(sandbox.history._stack));

check("挂了 popstate 监听（没挂的话后退键按下去界面不动）",
  (windowListeners.get("popstate") || []).length === 1,
  `popstate 监听数=${(windowListeners.get("popstate") || []).length}`);

// back() 之后手动派发 popstate（沙箱不自动派发，浏览器会自动）
sandbox.history.back();
for (const fn of windowListeners.get("popstate") || []) await fn({});
await new Promise((r) => setTimeout(r, 10));
check("后退一次回到上一个视图",
  state.view === "dashboard" && sandbox.location.hash === "#view=dashboard",
  `view=${state.view} hash=${sandbox.location.hash}`);

// 弹窗也要能退：开弹窗 → 后退 → 弹窗关掉
sandbox.history._reset();
sandbox.location.hash = "";
sandbox.switchView("dashboard");
sandbox.openModal("测试弹窗", "<p>内容</p>");
check("开弹窗会压一条 #modal 历史",
  sandbox.history._stack.includes("#modal"), JSON.stringify(sandbox.history._stack));
sandbox.history.back();
for (const fn of windowListeners.get("popstate") || []) await fn({});
await new Promise((r) => setTimeout(r, 10));
check("后退键能把弹窗关掉（用户的直觉：先退弹窗，再退页面）",
  sandbox.document.getElementById("modalHost").innerHTML === "",
  sandbox.document.getElementById("modalHost").innerHTML.slice(0, 80));
check("关弹窗这一次后退不会连视图一起退掉（一次后退只做一件事）",
  state.view === "dashboard", state.view);

// applyHashRoute 遇到 #modal 不能把视图切走 —— 它只是个「弹窗开着」的标记
sandbox.location.hash = "#modal";
sandbox.switchView("spools");
await sandbox.applyHashRoute();
check("applyHashRoute 遇到 #modal 不切视图（它不是落点，只是标记）",
  state.view === "spools", state.view);
sandbox.location.hash = "";
sandbox.switchView("dashboard");

// ── 16. 汇总页钻取 + 均价卡 ─────────────────────────────────────
console.log("== 耗材汇总：点名字钻到库存、每盘均价 ==");

// 后端 _group_summary 把空品牌/空材料归到「未填写」，把空外观归到「普通」。
// 前端的 norm 必须与它一字不差，否则点了汇总表里的名字跳过去是空列表。
check("空品牌归到「未填写」（与后端 _group_summary 同口径）",
  SUMMARY_DRILL_FIELDS.brand.norm({ brand: "" }) === "未填写"
  && SUMMARY_DRILL_FIELDS.brand.norm({ brand: "  " }) === "未填写"
  && SUMMARY_DRILL_FIELDS.brand.norm({ brand: "拓竹" }) === "拓竹");
check("空材料归到「未填写」",
  SUMMARY_DRILL_FIELDS.material.norm({ material: "" }) === "未填写"
  && SUMMARY_DRILL_FIELDS.material.norm({ material: "PLA" }) === "PLA");
check("空外观归到「普通」而不是「未填写」（外观有默认值，跟前两项不一样）",
  SUMMARY_DRILL_FIELDS.finish.norm({ finish: "" }) === "普通"
  && SUMMARY_DRILL_FIELDS.finish.norm({ finish: "丝绸" }) === "丝绸");

const spoolForDrill = (id, brand, material, finish) => ({
  id, brand, material, finish, price: 0, name: `料${id}`,
  remaining_weight: 500, used_weight: 500, initial_weight: 1000,
  archived: false, slots: [],
});
state.spools = [
  spoolForDrill(1, "拓竹", "PLA", "丝绸"),
  spoolForDrill(2, "", "PLA", ""),      // 没填品牌、没填外观，材料还是 PLA
  spoolForDrill(3, "Polymaker", "PETG", "哑光"),
];

// 运行时断言：真的点一次，再真的问筛选器要列表。
// 只断言「HTML 里有 jumpToSpoolsByField」是没用的 —— 函数写错、norm 对不上，
// 按钮照样在，跳过去却是个空列表。
// 先给其它筛选塞点脏数据再钻取。不先污染就断言「被清空」是假断言 ——
// 从没设过值当然也是空的，把 resetSpoolFilters 删掉照样全绿（实测过）。
sandbox.document.getElementById("spoolPriceMin").value = "50";
sandbox.document.getElementById("spoolSearch").value = "随便搜点什么";
sandbox.jumpToSpoolsByField("brand", "拓竹");
check("点品牌名 -> 切到料盘库存页", state.view === "spools", String(state.view));
check("点品牌名 -> 库存列表只剩这个品牌",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)) === "[1]",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)));
check("钻取只留这一个条件（关键词 / 价格区间被清掉，否则两个条件叠一起看着像没生效）",
  sandbox.document.getElementById("spoolPriceMin").value === ""
  && sandbox.document.getElementById("spoolSearch").value === "",
  `min=${sandbox.document.getElementById("spoolPriceMin").value} `
  + `kw=${sandbox.document.getElementById("spoolSearch").value}`);

sandbox.jumpToSpoolsByField("brand", "未填写");
check("点「未填写」也能筛出空品牌的那些盘（norm 口径不一致就跳过去是空列表）",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)) === "[2]",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)));
check("「未填写」不在下拉选项里时会补一个 option（直接 sel.value= 会静默变空字符串）",
  sandbox.document.getElementById("spoolBrand").value === "未填写"
  && sandbox.document.getElementById("spoolBrand").options.some((o) => o.value === "未填写"));

sandbox.jumpToSpoolsByField("material", "PLA");
check("点材料名 -> 只剩这种材料",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)) === "[1,2]",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)));
sandbox.jumpToSpoolsByField("finish", "普通");
check("点外观「普通」-> 只剩没填外观的盘",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)) === "[2]",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)));
sandbox.resetSpoolFilters();

// 汇总表：名称列可点 + 每盘均价列
const drillRow = {
  name: "拓竹", count: 3, price: 300, priced_count: 2,
  initial_g: 3000, remaining_g: 1500, used_g: 1500,
  stock_value: 150, remaining_percent: 50,
};
const tbl = summaryTable([drillRow], "", "brand");
// 只看「每盘均价」那一格。断言绝不能写成 `html.includes("未登记")` ——
// 采购金额列在无价时也写「未登记」，那样写等于什么都验不出来
// （写这条时实测：把分母改成总盘数，测试依然 204 项全绿）。
const cellOf = (html, label) => {
  const m = html.match(new RegExp(`data-label="${label}">([\\s\\S]*?)</td>`));
  return m ? m[1] : "";
};
check("汇总表的名称是可点的按钮（带钻取维度）",
  /class="cell-link"/.test(tbl) && /jumpToSpoolsByField\('brand', this\.dataset\.value\)/.test(tbl),
  tbl.slice(0, 300));
check("名称用 data-value 传值，不拼进 JS 字符串字面量（品牌名带引号会打断 onclick）",
  /data-value="拓竹"/.test(tbl));
check("汇总表有「每盘均价」列", /每盘均价/.test(tbl));
// 关键：分母是 priced_count(2) 不是 count(3)。写错的话这里会变成 ¥100.00。
check("每盘均价按「登记过价的盘数」算，不是按总盘数（¥300 / 2 = ¥150）",
  cellOf(tbl, "每盘均价").includes("¥150.00"), cellOf(tbl, "每盘均价"));
const noPriceRow = summaryTable([{ ...drillRow, price: 0, priced_count: 0 }], "", "brand");
check("一组里一条价格都没有时均价格写「未登记」，不是 ¥0.00",
  cellOf(noPriceRow, "每盘均价").includes("未登记")
  && !cellOf(noPriceRow, "每盘均价").includes("¥0.00"),
  cellOf(noPriceRow, "每盘均价"));
check("不给钻取维度时名称是普通文本（不是按钮）",
  !/class="cell-link"/.test(summaryTable([drillRow], "", "")));

// 均价卡
const ps = summaryPriceStats([
  { price: 100, initial_weight: 1000 }, { price: 200, initial_weight: 1000 },
  { price: 300, initial_weight: 1000 }, { price: 0, initial_weight: 1000 },
]);
check("每盘均价的分母只算登记过价的盘（100+200+300）/3 = ¥200，不是 /4 = ¥150",
  ps.perSpool === 200 && ps.priced === 3 && ps.unpriced === 1, JSON.stringify(ps));
check("每公斤价按满盘净重折算（¥200 / 1000g = ¥200/kg）", ps.perKg === 200, String(ps.perKg));
check("价格区间取最低 / 最高", ps.min === 100 && ps.max === 300, `${ps.min}~${ps.max}`);
const psEmpty = summaryPriceStats([{ price: 0, initial_weight: 1000 }]);
check("一条价格都没有时数值是 null（交给调用方填文案，不许拿 0 冒充）",
  psEmpty.perSpool === null && psEmpty.perKg === null && psEmpty.priced === 0);

// 「不要留空」：没有价格时两张卡都得有内容，不能是个空格子
const cardsNone = priceStatCards();
const valueHtmls = [...cardsNone.matchAll(/<div class="value">([\s\S]*?)<\/div>/g)].map((m) => m[1]);
check("没登记价格时均价卡也不留空（两张卡的值都不是空串）",
  valueHtmls.length === 2 && valueHtmls.every((v) => v.trim().length > 0),
  JSON.stringify(valueHtmls));
check("没登记价格时写「未登记」并说明去哪儿补",
  cardsNone.includes("未登记") && cardsNone.includes("料盘库存"));
check("有两张均价卡（6 + 2 = 8 张，宽屏 4×2 正好两行，末行不留空位）",
  (cardsNone.match(/class="stat/g) || []).length === 2,
  String((cardsNone.match(/class="stat/g) || []).length));
check("均价卡里不再有「平均每公斤」（按反馈删掉了）",
  !/平均每公斤/.test(cardsNone));

// 真跑一次 renderSummary，数一数 stat 卡总数：宽屏四列，卡数不是 4 的倍数就会空一格
state.stats = {
  spool_count: 4, archived_count: 0, price_total: 600, used_total: 1500,
  remaining_total: 2500, used_value: 300, stock_value: 300, print_cost_total: 12.5,
  by_brand: [], by_material_detail: [], by_finish: [],
};
state.summarySpools = [
  { price: 100, initial_weight: 1000 }, { price: 200, initial_weight: 1000 },
  { price: 300, initial_weight: 1000 }, { price: 0, initial_weight: 1000 },
];
sandbox.renderSummary();
const summaryHost = sandbox.document.getElementById("summaryStats");
const statCount = (summaryHost.innerHTML.match(/class="stat/g) || []).length;
check("汇总页统计卡总数是 8 张（宽屏四列 4×2，末行不留空位）",
  statCount === 8 && statCount % 4 === 0, `共 ${statCount} 张`);
// 8 张要排成两行得靠四列；容器类名写在 index.html 里（沙箱不解析 HTML，直接读文件）。
// 少了 cols-4 就会退回全局三列 → 3+3+2，末行空一格，正是「不要留空」要避免的。
const indexHtml = fs.readFileSync(path.join(ROOT, "app", "static", "index.html"), "utf8");
check("汇总页统计容器带 cols-4（四列的开关，缺了它 8 张会排成 3+3+2）",
  /class="grid-stats cols-4"\s+id="summaryStats"/.test(indexHtml),
  (indexHtml.match(/<div class="[^"]*grid-stats[^"]*"[^>]*>/g) || []).join(" | "));
check("CSS 里定义了 .grid-stats.cols-4 的四列规则",
  /\.grid-stats\.cols-4\s*\{[^}]*repeat\(4,/.test(
    fs.readFileSync(path.join(ROOT, "app", "static", "style.css"), "utf8")));
check("统计卡里出现「平均每盘单价」", /平均每盘单价/.test(summaryHost.innerHTML));
state.stats = null;
state.spools = [];
state.summarySpools = [];

// ── 17. 打印记录：查看料盘 / 更改料盘 ───────────────────────────
console.log("== 打印记录：跳转耗材、更改盘料 ==");

state.spools = [
  { id: 1, name: "A 盘", archived: false, remaining_weight: 500 },
  { id: 2, name: "B 盘", archived: false, remaining_weight: 500 },
  { id: 3, name: "C 盘（已归档）", archived: true, remaining_weight: 500 },
];
// 运行时断言：真的开一次弹窗，读 modalHost 里渲染出来的 HTML。
// 只断言「源码里有 openRebindUsage」拦不住「下拉是空的」—— 那正是用户看到的「点了没反应」。
//
// ⚠️ 2026-09-18 改：这个弹窗从纯 <select> 换成了可搜索的输入框 + 候选列表
// （用户反馈「还是无法直接输入」）。所以这里不再找 `<option>`，改成找候选按钮；
// 「默认选中当前那盘」也换成了读 `S.rebindUsage.targetId` + 提示行文案。
await sandbox.openRebindUsage(11, 1);
const rebindHtml = sandbox.document.getElementById("modalHost").innerHTML;
const rebindListHtml = () => sandbox.document.getElementById("rebindSpoolList").innerHTML;
check("「更改料盘」弹窗里是可搜索的输入框（不再是纯下拉）",
  /id="rebindSpoolSearch"/.test(rebindHtml) && !/id="rebindSpool"/.test(rebindHtml),
  rebindHtml.slice(0, 300));
check("下拉默认选中当前那盘（打开就能看出改的是哪条）",
  state.rebindUsage.targetId === 1
  && /A 盘/.test(sandbox.document.getElementById("rebindSpoolPicked").innerHTML),
  `targetId=${state.rebindUsage && state.rebindUsage.targetId}`);
check("候选里有其它在库料盘",
  /data-id="2"/.test(rebindListHtml()), rebindListHtml().slice(0, 300));
check("归档的料盘不进候选（改扣到归档盘上没意义）",
  !/data-id="3"/.test(rebindListHtml()), rebindListHtml().slice(0, 300));
check("弹窗里说明了会「先退回再扣到新盘」", /退回/.test(rebindHtml));
check("候选里默认全列（点开就像个普通下拉，不用先打字）",
  (rebindListHtml().match(/pick-item/g) || []).length === 2,
  `候选数=${(rebindListHtml().match(/pick-item/g) || []).length}`);
// 当前盘是归档盘时例外：必须留在候选里，否则打开看到空列表会以为绑定丢了
await sandbox.openRebindUsage(11, 3);
check("当前那盘即使已归档也要留在候选里",
  /data-id="3"/.test(rebindListHtml())
  && state.rebindUsage.targetId === 3
  && /C 盘（已归档）/.test(sandbox.document.getElementById("rebindSpoolPicked").innerHTML),
  rebindListHtml().slice(0, 300));
// 没有流水（usage_id = 0）时不该弹窗 —— 弹了也改不动
sandbox.document.getElementById("modalHost").innerHTML = "SENTINEL";
await sandbox.openRebindUsage(0, 1);
check("没有扣重流水时不弹改绑窗（弹了也改不动）",
  sandbox.document.getElementById("modalHost").innerHTML === "SENTINEL",
  sandbox.document.getElementById("modalHost").innerHTML.slice(0, 120));
sandbox.closeModal();
state.spools = [];

// ── 17b. 槽位弹窗里的「解绑耗材」 ────────────────────────────────
// 用户对着「AMS · 槽位 1」那个弹窗说「在这个界面增加一个解绑耗材按钮」。
// 两个最容易写错的地方：
//   ① 槽位没绑料盘时也摆一个「解绑耗材」→ 点了什么都不发生，像是坏了；
//   ② 复用 toggleSpoolBinding 解绑 → 它解完会 openBindSpoolDialog（另一盘料的绑定页），
//      人还在槽位页等着，弹窗却被换成别的，等于点一下就被弹走了。
console.log("");
console.log("── 槽位弹窗：解绑耗材 ──");

// 造一台只有 AMS 0 / 槽位 1 的机器，并让该槽位绑在料盘 1 上
state.printers_full = [{
  id: 5, name: "P2S", model: "P2S", serial: "01P00A000000001", online: true,
  state: {
    ams: [{ ams_id: 0, name: "AMS A", trays: [
      { tray_id: 0, label: "PLA 黑", color: "#111111", remain: 80, has_rfid: false },
    ] }],
  },
}];
state.bindingMap = { "5:0:0": { spool_id: 1, spool: { id: 1, name: "A 盘" } } };
state.spools = [{ id: 1, name: "A 盘", archived: false, remaining_weight: 500 }];

sandbox.openSlotDialog(5, 0, 0);
let slotHtml = sandbox.document.getElementById("modalHost").innerHTML;
check("槽位弹窗标题是「AMS A · 槽位 A1」（AMS 名 + 槽位字母+号，别写成 AMS 0）",
  /<h3>AMS A\s*·\s*槽位\s*A1<\/h3>/.test(slotHtml), slotHtml.slice(0, 200));
check("已绑定时出现「解绑耗材」按钮",
  /解绑耗材/.test(slotHtml), slotHtml.slice(0, 400));
check("点它调的是 unbindSlotSpool(打印机, ams, 槽位, 当前料盘id) —— 不是 toggleSpoolBinding",
  /unbindSlotSpool\(5,0,0,1\)/.test(slotHtml) && !/toggleSpoolBinding/.test(slotHtml),
  (slotHtml.match(/onclick="[^"]*[Bb]ind[^"]*"/g) || []).join(" "));
check("旁边写清当前绑的是哪盘（点之前能核对）",
  /当前绑定/.test(slotHtml) && /A 盘/.test(slotHtml));
check("槽位弹窗仍保留了「保存绑定」", /saveBinding\(5,0,0\)/.test(slotHtml));

// 解绑成功后必须重开**同一个槽位**的弹窗，而不是跳去料盘页
let bindCalls = [];
const origFetch = sandbox.fetch;
sandbox.fetch = async (url, opts) => {
  bindCalls.push({ url, body: opts && opts.body ? JSON.parse(opts.body) : null });
  return { ok: true, status: 200, json: async () => ({}) };
};
// 解绑时还会顺带 loadBindings / loadStatus（刷新界面上的槽位标记），
// 所以只挑出发往 /api/bindings 且带 body 的那一次来判。
const putCalls = () => bindCalls.filter((c) => c.url === "/api/bindings" && c.body);
state.bindingMap = { "5:0:0": { spool_id: 1, spool: { id: 1, name: "A 盘" } } };
await sandbox.unbindSlotSpool(5, 0, 0, 1);
check("解绑打的是 PUT /api/bindings 且 spool_id 为 null",
  putCalls().length === 1 && putCalls()[0].body.spool_id === null,
  JSON.stringify(bindCalls));
check("请求带上了槽位三件套（printer/ams/tray）",
  putCalls().length === 1 && putCalls()[0].body.printer_id === 5
  && putCalls()[0].body.ams_id === 0 && putCalls()[0].body.tray_id === 0,
  JSON.stringify(bindCalls));
// 解绑前把 bindingMap 清空，模拟服务端已生效；重开弹窗时应当不再有解绑按钮
state.bindingMap = {};
slotHtml = sandbox.document.getElementById("modalHost").innerHTML;
check("解绑后重开的是同一个槽位弹窗（标题还是 AMS A · 槽位 A1，没被换成料盘绑定页）",
  /<h3>AMS A\s*·\s*槽位\s*A1<\/h3>/.test(slotHtml)
  && !/绑定槽位 ·/.test(slotHtml), slotHtml.slice(0, 200));
check("解绑后弹窗里不再有「解绑耗材」（没绑定了就不该摆这个键）",
  !/解绑耗材/.test(slotHtml), slotHtml.slice(0, 400));

// 已经没绑定时再点一次：不该发请求，只提示
bindCalls = [];
await sandbox.unbindSlotSpool(5, 0, 0, 1);
check("槽位已解绑时重复点不重复发请求", putCalls().length === 0, JSON.stringify(bindCalls));

// 弹窗开着的时候别处改了这个槽位 → 不许误删后来绑上去的那盘
bindCalls = [];
state.bindingMap = { "5:0:0": { spool_id: 2, spool: { id: 2, name: "B 盘" } } };
await sandbox.unbindSlotSpool(5, 0, 0, 1);   // 弹窗里记的还是料盘 1
check("绑定已被改成别的盘时不误删（不发请求）", putCalls().length === 0, JSON.stringify(bindCalls));
sandbox.fetch = origFetch;
sandbox.closeModal();
state.printers_full = [];
state.bindingMap = {};
state.spools = [];

// ── 17c. 「转到另一盘料」的目标料盘：能打字搜索 ──────────────────
// 用户原话「这个目标料盘要能输入，直接打关键字就能出来相关的料盘」。
// 原来是个纯 <select>，料盘一多只能上下翻。
// 这里最容易漏的线：选中值从 input.value 挪到了 S.moveTargetId ——
// 一旦 doMoveUsage 还去读 input.value（人打的是搜索词！），转移就会
// 把 spool_id 发成 NaN / 错盘。所以**必须**验「选中 → 发出去的 id 是哪个」。
console.log("");
console.log("── 转移消耗：可搜索的目标料盘 ──");

state.spools = [
  { id: 1, name: "魔创 PLA 天蓝色", brand: "魔创", material: "PLA", finish: "普通", color_name: "天蓝色", color_hex: "#3b82f6", remaining_weight: 0 },
  { id: 2, name: "大简 PETG-HT 工程黑", brand: "大简", material: "PETG-HT", finish: "普通", color_name: "工程黑", color_hex: "#1f2937", remaining_weight: 560 },
  { id: 3, name: "Polymaker PLA 哑光 哑光灰", brand: "Polymaker", material: "PLA", finish: "哑光", color_name: "哑光灰", color_hex: "#9ca3af", remaining_weight: 720 },
  { id: 4, name: "拓竹 PETG 透明 透明蓝", brand: "拓竹", material: "PETG", finish: "透明", color_name: "透明蓝", color_hex: "#7dd3fc", remaining_weight: 880 },
  { id: 9, name: "已归档的盘", brand: "魔创", material: "PLA", finish: "普通", color_name: "黑", color_hex: "#000", remaining_weight: 100, archived: true },
];

// 过滤口径：品牌 / 材料 / 外观 / 颜色 / 名字 / 编号都要能搜到
check("搜品牌能命中（「魔创」）",
  sandbox.spoolMatches(state.spools[0], "魔创") === true);
check("搜材料能命中（「PETG」同时命中 PETG 与 PETG-HT）",
  sandbox.spoolMatches(state.spools[1], "PETG") === true
  && sandbox.spoolMatches(state.spools[3], "PETG") === true);
check("搜外观能命中（「哑光」）",
  sandbox.spoolMatches(state.spools[2], "哑光") === true);
check("搜颜色能命中（「透明」）",
  sandbox.spoolMatches(state.spools[3], "透明") === true);
check("搜编号能命中（「3」匹配到 id=3）",
  sandbox.spoolMatches(state.spools[2], "3") === true);
check("多个关键字是 AND（「魔创 天蓝」命中，「魔创 透明」不命中）",
  sandbox.spoolMatches(state.spools[0], "魔创 天蓝") === true
  && sandbox.spoolMatches(state.spools[0], "魔创 透明") === false);
check("大小写不敏感（「polymaker」能搜到 Polymaker）",
  sandbox.spoolMatches(state.spools[2], "polymaker") === true);
check("空关键字全部命中（默认就是「不筛」）",
  sandbox.spoolMatches(state.spools[0], "") === true
  && sandbox.spoolMatches(state.spools[0], "   ") === true);
check("搜不到东西时返回 false（交给界面出「没有匹配」提示）",
  sandbox.spoolMatches(state.spools[0], "这个牌子根本不存在") === false);

// 打开弹窗：默认选中第一个候选（不能是「没选」——点了确认才发现没选就太晚了）
// ⚠️ 这个 fetch 桩**必须 resolve**。写成 `new Promise(() => {})`（永不落地）的话，
// doMoveUsage 里的 `await api(...)` 永远挂在那儿，顶层 `await sandbox.doMoveUsage(31)`
// 也永远不返回 → Node 直接以「unsettled top-level await」退出码 13 收场，
// 而且**已跑过的断言照样打印**，grep 一下看着像全绿（这个坑踩过一次，记在这儿）。
let moveCalls = [];
sandbox.fetch = async (url, opts) => {
  if (String(url).includes("/api/usages/") && String(url).includes("/move")) {
    moveCalls.push({ url: String(url), body: JSON.parse((opts || {}).body || "{}") });
  }
  return { ok: true, status: 200, json: async () => ({}) };
};
sandbox.openMoveDialog(31, 1, -7.1);
const moveList = sandbox.document.getElementById("moveTargetList").innerHTML;
const movePicker = sandbox.document.getElementById("moveTargetPicked").innerHTML;
check("弹窗里候选默认全列出来（不预筛，点开就像个普通下拉）",
  (moveList.match(/pick-item/g) || []).length === 4, `候选数=${(moveList.match(/pick-item/g) || []).length}`);
check("归档的料盘不进候选（不能把消耗转到已归档的盘上）",
  !/已归档的盘/.test(moveList), moveList.slice(0, 200));
check("打开时默认选中第一盘并在提示里写明选了谁",
  state.moveTargetId === 1 && /魔创 PLA 天蓝色/.test(movePicker),
  `id=${state.moveTargetId} picked=${movePicker}`);
check("输入框初始是空的（不能把选中项当搜索词填进去，那样会把别的候选滤掉）",
  (sandbox.document.getElementById("moveTargetSearch").value || "") === "",
  sandbox.document.getElementById("moveTargetSearch").value);

// 打字过滤：这一条直接对着用户的原话「打关键字就能出来相关的料盘」
sandbox.document.getElementById("moveTargetSearch").value = "PETG";
sandbox.onMoveTargetInput();
const filtered = sandbox.document.getElementById("moveTargetList").innerHTML;
check("打「PETG」后只剩 PETG 相关的两盘",
  (filtered.match(/pick-item/g) || []).length === 2,
  `过滤后=${(filtered.match(/pick-item/g) || []).length}`);
check("打「PETG」后不相关的盘（魔创 PLA）被滤掉", !/魔创 PLA/.test(filtered));

sandbox.document.getElementById("moveTargetSearch").value = "不存在的关键字";
sandbox.onMoveTargetInput();
check("搜不到时给出「没有匹配」的提示而不是空白框",
  /没有匹配/.test(sandbox.document.getElementById("moveTargetList").innerHTML));

// 点选：选中值必须落到 S.moveTargetId，而且输入框回填成名字
sandbox.pickMoveTarget(3);
check("点选后 S.moveTargetId 跟着变",
  state.moveTargetId === 3, `id=${state.moveTargetId}`);
check("点选后输入框回填成料盘名（人看得懂自己选了什么）",
  sandbox.document.getElementById("moveTargetSearch").value === "Polymaker PLA 哑光 哑光灰",
  sandbox.document.getElementById("moveTargetSearch").value);
check("点选后提示行写的是新选中的那盘",
  /Polymaker PLA 哑光 哑光灰/.test(sandbox.document.getElementById("moveTargetPicked").innerHTML));
check("点选后列表重新列全（否则回填的名字会自己变成筛选词）",
  (sandbox.document.getElementById("moveTargetList").innerHTML.match(/pick-item/g) || []).length === 4);

// 最关键的线：确认转移时发出去的 spool_id 必须是**选中的那盘**，
// 不是输入框里的文字（那是搜索词，parseInt 出来是 NaN）
moveCalls = [];
await sandbox.doMoveUsage(31);
await new Promise((r) => setTimeout(r, 10));
const sent = moveCalls.filter((c) => c.body && c.body.spool_id != null);
check("确认转移时发的是选中料盘的 id（不是输入框里的文字）",
  sent.length === 1 && sent[0].body.spool_id === 3, JSON.stringify(moveCalls));

// 没选中时不许发请求（要提示，不能让用户对着没反应的按钮发呆）
state.moveTargetId = null;
moveCalls = [];
await sandbox.doMoveUsage(31);
check("没选中料盘时不发请求（只提示）",
  moveCalls.filter((c) => c.body && c.body.spool_id != null).length === 0,
  JSON.stringify(moveCalls));

sandbox.fetch = origFetch;
sandbox.closeModal();
sandbox.document.getElementById("modalHost").innerHTML = "";
state.spools = [];

// ── 17d. 库存页关键字框与转移弹窗共用一份口径 ────────────────────
// 这两处各写过一套过滤：库存页是整串 substring，还漏了「外观 / 编号」；
// 转移弹窗按词 AND。结果就是同一个词在一个地方搜得到、换个地方搜不到。
// 现在两边都走 spoolMatches / spoolSearchText，断言直接钉住「同一份实现」。
console.log("");
console.log("── 库存页关键字框与转移弹窗同一口径 ──");

const kwSpools = [
  { id: 1, name: "魔创 PLA 天蓝色", brand: "魔创", material: "PLA", finish: "普通", color_name: "天蓝色", location: "A 盘 A1", color_hex: "#3b82f6", remaining_weight: 0 },
  { id: 2, name: "大简 PETG-HT 工程黑", brand: "大简", material: "PETG-HT", finish: "普通", color_name: "工程黑", location: "", note: "打印机器人外壳用", color_hex: "#1f2937", remaining_weight: 560 },
  { id: 3, name: "Polymaker PLA 哑光 哑光灰", brand: "Polymaker", material: "PLA", finish: "哑光", color_name: "哑光灰", location: "AMS B2", color_hex: "#9ca3af", remaining_weight: 720 },
];
check("库存页能按外观搜（「哑光」）—— 老实现漏了 finish",
  kwSpools.filter((s) => sandbox.spoolFilteredByKeyword(s, "哑光")).length === 1);
check("库存页能按编号搜（「3」）—— 老实现漏了 id",
  kwSpools.filter((s) => sandbox.spoolFilteredByKeyword(s, "3")).length === 1);
check("库存页能按位置搜（「B2」）—— 提示语一直写着「位置」，老实现是有的，别删回去",
  kwSpools.filter((s) => sandbox.spoolFilteredByKeyword(s, "B2")).length === 1);
check("库存页能按备注搜（「机器人」）",
  kwSpools.filter((s) => sandbox.spoolFilteredByKeyword(s, "机器人")).length === 1);
check("多词按 AND 收窄（「魔创 天蓝」命中，「魔创 工程黑」不命中）",
  kwSpools.filter((s) => sandbox.spoolFilteredByKeyword(s, "魔创 天蓝")).length === 1
  && kwSpools.filter((s) => sandbox.spoolFilteredByKeyword(s, "魔创 工程黑")).length === 0);
check("同一个词在两处结果一致（这正是「各写一套」会坏掉的地方）",
  kwSpools.every((s) => sandbox.spoolFilteredByKeyword(s, "PETG") === sandbox.spoolMatches(s, "PETG")));

// 库存页整条链路（标签页 + 关键字）也要能跑通：塞数据进 state、把关键字填进框
state.spools = kwSpools.slice();
state.spoolTab = "all";
sandbox.document.getElementById("spoolSearch").value = "哑光 灰";
const kwList = sandbox.filteredSpools();
check("filteredSpools 认多词（「哑光 灰」只留 Polymaker 那盘）",
  kwList.length === 1 && kwList[0].id === 3,
  kwList.map((s) => s.id).join(","));
sandbox.document.getElementById("spoolSearch").value = "";
check("关键字清空后全部回来", sandbox.filteredSpools().length === 3);

sandbox.document.getElementById("modalHost").innerHTML = "";
state.spools = [];


// ── 17e. 「更改料盘」也要能打字搜索 ──────────────────────────────
// 用户原话「还是无法直接输入」。上一轮只把「转移消耗」那个弹窗改成了可搜索，
// 这个弹窗还是个纯 <select>，用户以为改过了、一试还是没有 —— 所以两条路
// **必须共用同一套组件**，而不是各写一份。这里的断言就是钉「共用」这件事：
// 同一个 renderSpoolPicker、同一个过滤口径、同一个空结果文案。
console.log("");
console.log("── 更改料盘：可搜索的目标料盘 ──");

state.spools = [
  { id: 1, name: "魔创 PLA 天蓝色", brand: "魔创", material: "PLA", finish: "普通", color_name: "天蓝色", color_hex: "#3b82f6", remaining_weight: 0 },
  { id: 2, name: "大简 PETG-HT 工程黑", brand: "大简", material: "PETG-HT", finish: "普通", color_name: "工程黑", color_hex: "#1f2937", remaining_weight: 560 },
  { id: 3, name: "Polymaker PLA 哑光 哑光灰", brand: "Polymaker", material: "PLA", finish: "哑光", color_name: "哑光灰", color_hex: "#9ca3af", remaining_weight: 720 },
  { id: 9, name: "已归档的盘", brand: "魔创", material: "PLA", finish: "普通", color_name: "黑", color_hex: "#000", remaining_weight: 100, archived: true },
];

await sandbox.openRebindUsage(31, 2);
const rbList = sandbox.document.getElementById("rebindSpoolList").innerHTML;
check("「更改料盘」里是输入框 + 候选列表（不再是纯下拉）",
  typeof sandbox.document.getElementById("rebindSpoolSearch") === "object"
  && /pick-item/.test(rbList));
check("候选默认全列（不预筛）", (rbList.match(/pick-item/g) || []).length === 3,
  `候选数=${(rbList.match(/pick-item/g) || []).length}`);
check("归档的料盘不进候选", !/已归档的盘/.test(rbList));
check("默认选中「原来那盘」（一眼能看出当前扣的是哪盘）",
  state.rebindUsage && state.rebindUsage.targetId === 2
  && /大简 PETG-HT 工程黑/.test(sandbox.document.getElementById("rebindSpoolPicked").innerHTML),
  `targetId=${state.rebindUsage && state.rebindUsage.targetId}`);
check("输入框初始为空（选中项不能当搜索词填进去）",
  (sandbox.document.getElementById("rebindSpoolSearch").value || "") === "");

// 打字过滤
sandbox.document.getElementById("rebindSpoolSearch").value = "哑光";
sandbox.onRebindTargetInput();
const rbFiltered = sandbox.document.getElementById("rebindSpoolList").innerHTML;
check("打「哑光」后只剩那一盘", (rbFiltered.match(/pick-item/g) || []).length === 1
  && /Polymaker/.test(rbFiltered), rbFiltered.slice(0, 200));

sandbox.document.getElementById("rebindSpoolSearch").value = "zzz查不到";
sandbox.onRebindTargetInput();
check("搜不到时给提示（与转移弹窗同一句文案）",
  /没有匹配/.test(sandbox.document.getElementById("rebindSpoolList").innerHTML));

// 点选
sandbox.pickRebindTarget(3);
check("点选后 S.rebindUsage.targetId 跟着变",
  state.rebindUsage.targetId === 3, `targetId=${state.rebindUsage.targetId}`);
check("点选后输入框回填成料盘名",
  sandbox.document.getElementById("rebindSpoolSearch").value === "Polymaker PLA 哑光 哑光灰",
  sandbox.document.getElementById("rebindSpoolSearch").value);
check("点选后列表重新列全", 
  (sandbox.document.getElementById("rebindSpoolList").innerHTML.match(/pick-item/g) || []).length === 3);

// 最关键的线：提交时发出去的 spool_id 必须是选中的那盘，不是输入框里的搜索词
let rebindCalls = [];
sandbox.fetch = async (url, opts) => {
  if (String(url).includes("/api/usages/") && String(url).includes("/move")) {
    rebindCalls.push({ url: String(url), body: JSON.parse((opts || {}).body || "{}") });
  }
  return { ok: true, status: 200, json: async () => ({}) };
};
sandbox.document.getElementById("rebindSpoolSearch").value = "哑光";
await sandbox.submitRebindUsage();
await new Promise((r) => setTimeout(r, 10));
const rbSent = rebindCalls.filter((c) => c.body && c.body.spool_id != null);
check("提交时发的是选中料盘的 id（不是输入框里的搜索词，parseInt 会得 NaN）",
  rbSent.length === 1 && rbSent[0].body.spool_id === 3, JSON.stringify(rebindCalls));

// 选回原来那盘 → 必须拦住（否则「确认更改」点下去什么都没发生，用户以为坏了）
//
// ⚠️ 提交成功后会 `S.rebindUsage = null` 并 `loadSpools()` —— 上面那个 fetch 桩
// 不返回 `spools` 字段，于是 S.spools 被清成空数组，重开弹窗会走「还没有料盘可改扣」
// 的早退分支。这是**桩的问题不是应用的问题**，所以这里补回数据再重开。
rebindCalls = [];
state.spools = [
  { id: 1, name: "魔创 PLA 天蓝色", brand: "魔创", material: "PLA", finish: "普通", color_name: "天蓝色", color_hex: "#3b82f6", remaining_weight: 0 },
  { id: 2, name: "大简 PETG-HT 工程黑", brand: "大简", material: "PETG-HT", finish: "普通", color_name: "工程黑", color_hex: "#1f2937", remaining_weight: 560 },
  { id: 3, name: "Polymaker PLA 哑光 哑光灰", brand: "Polymaker", material: "PLA", finish: "哑光", color_name: "哑光灰", color_hex: "#9ca3af", remaining_weight: 720 },
];
await sandbox.openRebindUsage(31, 2);
check("重开弹窗时 state 被重新填上（提交成功后是 null，不能接着改）",
  state.rebindUsage !== null && state.rebindUsage.targetId === 2,
  JSON.stringify(state.rebindUsage));
state.rebindUsage.targetId = 2;              // 就是原来那盘
await sandbox.submitRebindUsage();
check("改成原来那盘时不发请求（提示「没变化」）",
  rebindCalls.length === 0, JSON.stringify(rebindCalls));

// 没选中 → 拦住
rebindCalls = [];
state.spools = [
  { id: 1, name: "魔创 PLA 天蓝色", brand: "魔创", material: "PLA", finish: "普通", color_name: "天蓝色", color_hex: "#3b82f6", remaining_weight: 0 },
  { id: 2, name: "大简 PETG-HT 工程黑", brand: "大简", material: "PETG-HT", finish: "普通", color_name: "工程黑", color_hex: "#1f2937", remaining_weight: 560 },
  { id: 3, name: "Polymaker PLA 哑光 哑光灰", brand: "Polymaker", material: "PLA", finish: "哑光", color_name: "哑光灰", color_hex: "#9ca3af", remaining_weight: 720 },
];
await sandbox.openRebindUsage(31, 2);
state.rebindUsage.targetId = 0;
await sandbox.submitRebindUsage();
check("没选料盘时不发请求", rebindCalls.length === 0, JSON.stringify(rebindCalls));

// 提交成功之后 state 必须清掉：否则再点一次会重复发一遍同样的请求
rebindCalls = [];
state.spools = [
  { id: 1, name: "魔创 PLA 天蓝色", brand: "魔创", material: "PLA", finish: "普通", color_name: "天蓝色", color_hex: "#3b82f6", remaining_weight: 0 },
  { id: 2, name: "大简 PETG-HT 工程黑", brand: "大简", material: "PETG-HT", finish: "普通", color_name: "工程黑", color_hex: "#1f2937", remaining_weight: 560 },
  { id: 3, name: "Polymaker PLA 哑光 哑光灰", brand: "Polymaker", material: "PLA", finish: "哑光", color_name: "哑光灰", color_hex: "#9ca3af", remaining_weight: 720 },
];
await sandbox.openRebindUsage(31, 2);
state.rebindUsage.targetId = 3;
await sandbox.submitRebindUsage();
await new Promise((r) => setTimeout(r, 10));
check("恢复正常路径发得出去（上面几条拦住的是真该拦的）",
  rebindCalls.filter((c) => c.body && c.body.spool_id === 3).length === 1,
  JSON.stringify(rebindCalls));
check("提交成功后 S.rebindUsage 被清空（防重复提交）",
  state.rebindUsage === null, JSON.stringify(state.rebindUsage));

sandbox.fetch = origFetch;
sandbox.closeModal();
sandbox.document.getElementById("modalHost").innerHTML = "";
state.spools = [];


// ── 17f. 筛选下拉只列「库存里真有的值」 ──────────────────────────
// 用户原话「在这三个选项中，只显示已经在库存的料盘，没有的不要显示相关信息」。
// 原来那里填的是**全量预设**（二十几个品牌 / 28 种材料 / 15 种外观），
// 绝大多数一盘料都没有 —— 选中它们只会得到空列表，看着像「筛坏了」。
//
// 这里必须钉三件事，缺一条就会回归：
//   ① 选项来自 S.spools，不是 S.catalog
//   ② 取值走 SUMMARY_DRILL_FIELDS.*.norm()（filteredSpools 的比对口径），
//      否则「未填写」和空串会变成两个互不相同的值，选中哪个都筛不出东西
//   ③ loadCatalog 不许再回来覆写这三个下拉（它会用全量预设把结果盖掉）
console.log("");
console.log("── 库存页筛选下拉只列库存里真有的值 ──");

state.spools = [
  { id: 1, brand: "拓竹", material: "PETG", finish: "普通", color_name: "黑", color_hex: "#000", remaining_weight: 100 },
  { id: 2, brand: "拓竹", material: "PLA", finish: "哑光", color_name: "白", color_hex: "#fff", remaining_weight: 200 },
  { id: 3, brand: "Polymaker", material: "PLA", finish: "哑光", color_name: "灰", color_hex: "#888", remaining_weight: 300 },
  { id: 4, brand: "", material: "", finish: "", color_name: "未知", color_hex: "#666", remaining_weight: 50 },
];
// 目录里放一堆库存里没有的品牌/材料/外观：正确的实现应当完全无视它们
state.catalog = {
  brands: ["拓竹", "Polymaker", "大简", "魔创", "兰博", "Kexcelled", "爱酷乐", "爱丽兹 Allizz",
           "锐造", "JAYO", "天瑞", "iBOSS", "R3D", "彩多屋"],
  materials: ["PLA", "PETG", "PETG-HT", "ABS", "ASA", "TPU", "PA", "PC", "PVA", "HIPS"],
  finishes: ["普通", "亮面", "哑光", "磨砂", "丝绸", "珠光", "金属", "半透", "透明", "渐变",
             "双色", "木纹", "碳纤", "夜光", "其他"],
  colors: [],
};
sandbox.syncFilterOptions();

// ⚠️ 别用 `el.options` 读结果：沙箱的 stubEl 把 `options` 当成普通数组，
// 而 refillSelect 走的是 `sel.innerHTML = "..."` —— innerHTML 在桩里不解析，
// 所以 `.options` 永远是**上一次 appendChild 留下的残渣**。
// 第一次写这几条断言时就是这么红的（也有几条因此假绿过），所以改成解析 innerHTML。
const optValues = (id) => {
  const html = String(sandbox.document.getElementById(id).innerHTML || "");
  return [...html.matchAll(/<option[^>]*value="([^"]*)"/g)].map((m) => m[1]);
};
const optCount = (id) => {
  const html = String(sandbox.document.getElementById(id).innerHTML || "");
  return (html.match(/<option/g) || []).length;
};
const brandOpts = optValues("spoolBrand");
const matOpts = optValues("spoolMaterial");
const finOpts = optValues("spoolFinish");
check("三个下拉都真的被重填了（不是空 HTML）",
  brandOpts.length > 0 && matOpts.length > 0 && finOpts.length > 0,
  `brand=${brandOpts.length} material=${matOpts.length} finish=${finOpts.length}`);

// ⚠️ 断言用**集合**比而不是排好序的字符串：这几个下拉的排序走
// `localeCompare(..., "zh")`，而中文字的先后由 ICU 的拼音表决定 ——
// 「普通」和「哑光」谁在前跟环境有关，钉死顺序会得到一条随时会红的假断言。
const asSet = (arr) => [...new Set(arr.filter(Boolean))].sort().join(",");
check("品牌下拉只列库存里有的（拓竹 / Polymaker / 未填写）",
  asSet(brandOpts) === ["Polymaker", "拓竹", "未填写"].sort().join(","),
  JSON.stringify(brandOpts));
check("库存里没有的品牌一个都不出现（大简 / 魔创 / 爱酷乐 等）",
  !brandOpts.includes("大简") && !brandOpts.includes("魔创") && !brandOpts.includes("爱酷乐"),
  JSON.stringify(brandOpts));
check("材料下拉只列库存里有的（PLA / PETG / 未填写）",
  asSet(matOpts) === ["PETG", "PLA", "未填写"].sort().join(","), JSON.stringify(matOpts));
check("外观下拉只列库存里有的（普通 / 哑光）",
  asSet(finOpts) === ["普通", "哑光"].sort().join(","), JSON.stringify(finOpts));
check("材料里没有库存中不存在的值（PETG-HT / ABS 等）",
  !matOpts.includes("PETG-HT") && !matOpts.includes("ABS"), JSON.stringify(matOpts));
check("外观里没有库存中不存在的值（丝绸 / 磨砂 等）",
  !finOpts.includes("丝绸") && !finOpts.includes("磨砂"), JSON.stringify(finOpts));

// 缺失值必须按 norm 口径收成一个值 —— 「未填写」「普通」各只出现一次
check("空品牌收成「未填写」且只一次",
  brandOpts.filter((v) => v === "未填写").length === 1, JSON.stringify(brandOpts));
check("空材料收成「未填写」且只一次",
  matOpts.filter((v) => v === "未填写").length === 1, JSON.stringify(matOpts));
check("空外观收成「普通」（norm 口径）且不重复",
  finOpts.filter((v) => v === "普通").length === 1, JSON.stringify(finOpts));
check("每个下拉都带一个空值占位项（「全部 X」）",
  brandOpts[0] === "" && matOpts[0] === "" && finOpts[0] === "",
  `${JSON.stringify(brandOpts[0])} ${JSON.stringify(matOpts[0])} ${JSON.stringify(finOpts[0])}`);

// 选中下拉里的值，必须真能筛出料盘 —— 这才是「只列有的」的意义
state.spoolTab = "all";
state.spoolSort = { key: "id", dir: "asc" };
sandbox.document.getElementById("spoolSearch").value = "";
sandbox.document.getElementById("spoolBrand").value = "拓竹";
check("选中「拓竹」能筛出 2 盘（选项不是摆设）",
  sandbox.filteredSpools().length === 2, String(sandbox.filteredSpools().length));
sandbox.document.getElementById("spoolBrand").value = "未填写";
check("选中「未填写」能筛出那盘没写品牌的",
  sandbox.filteredSpools().length === 1 && sandbox.filteredSpools()[0].id === 4,
  sandbox.filteredSpools().map((s) => s.id).join(","));
sandbox.document.getElementById("spoolBrand").value = "";
sandbox.document.getElementById("spoolFinish").value = "哑光";
check("选中「哑光」能筛出 2 盘",
  sandbox.filteredSpools().length === 2, String(sandbox.filteredSpools().length));
sandbox.document.getElementById("spoolFinish").value = "";

// 空库：只剩「全部 X」一项，别退回全量预设
state.spools = [];
sandbox.syncFilterOptions();
check("空库时品牌下拉只剩「全部品牌」一项",
  optCount("spoolBrand") === 1, JSON.stringify(optValues("spoolBrand")));
check("空库时材料下拉只剩「全部材料」一项",
  optCount("spoolMaterial") === 1, JSON.stringify(optValues("spoolMaterial")));
check("空库时外观下拉只剩「全部外观」一项",
  optCount("spoolFinish") === 1, JSON.stringify(optValues("spoolFinish")));

// loadCatalog 不许再回来把这些下拉覆写成全量预设（上一次的回归点）
state.spools = [{ id: 1, brand: "拓竹", material: "PLA", finish: "普通", color_name: "黑", color_hex: "#000", remaining_weight: 10 }];
sandbox.syncFilterOptions();
const beforeCatalog = sandbox.document.getElementById("spoolBrand").innerHTML;
sandbox.fetch = async () => ({ ok: true, status: 200, json: async () => ({
  brands: ["拓竹", "Polymaker", "大简", "魔创", "兰博", "Kexcelled", "爱酷乐", "其他"],
  materials: ["PLA", "PETG", "PETG-HT"], finishes: ["普通", "哑光", "丝绸"], colors: [],
  preset_brands: ["拓竹", "Polymaker"],
}) });
await sandbox.loadCatalog();
check("loadCatalog 不去动这三个筛选下拉（谁后跑谁说了算的竞态已消除）",
  sandbox.document.getElementById("spoolBrand").innerHTML === beforeCatalog,
  `前=${beforeCatalog.slice(0, 90)} 后=${String(sandbox.document.getElementById("spoolBrand").innerHTML).slice(0, 90)}`);
check("loadCatalog 之后仍是「只有拓竹」而不是全量预设",
  optValues("spoolBrand").filter(Boolean).join(",") === "拓竹",
  JSON.stringify(optValues("spoolBrand")));

sandbox.fetch = origFetch;
state.spools = [];


// ── 17g. 自绘组合框（原生 datalist 的替代） ──────────────────────
// 两轮反馈合起来逼出来的方案：①「每次都要先删除才能选择」——原生 datalist
// 拿输入框当前值做子串过滤，没有属性能关；②「把这个下拉列表加长」——原生
// 弹层高度写死约 4 行半，CSS 够不着。现在 armComboInput 把 list 属性摘掉、
// 换成自己画的浮层：全量候选、可滚动、点击即选、值不用清空。
console.log("");
console.log("── 自绘组合框（全量候选、点击即选、高度可控） ──");

// ① 源码级接线检查
check("两个 datalist 输入框还在弹窗里（外观 / 颜色名称，HTML 是数据源）",
  /id="f_finish"[^>]*list="finishList"/.test(appSrc)
  && /id="f_color_name"[^>]*list="colorList"/.test(appSrc));
check("openModal 里调用了 armComboInputs（写了函数不等于接上了）",
  /armComboInputs\(host\)/.test(appSrc), "openModal 里没挂");
check("armComboInput 会摘掉 list 属性（留着的话原生弹层跟自绘的一起出）",
  /removeAttribute\("list"\)/.test(appSrc));
check("armComboInput 有幂等保护（每次开弹窗都会扫一遍，不能重复挂）",
  /dataset\.comboArmed === "1"/.test(appSrc) || /_comboArmed/.test(appSrc));
check("浮层挂在 body 上（弹窗 overflow 会把挂在弹窗里的 absolute 浮层裁掉）",
  /document\.body\.appendChild\(pop\)/.test(appSrc));
const CSS_SRC = fs.readFileSync(path.join(ROOT, "app", "static", "style.css"), "utf8");
check(".combo-pop 是 fixed 定位（浮层随输入框定位，不随弹窗滚动）",
  /\.combo-pop\s*\{[^}]*position:\s*fixed/.test(CSS_SRC));
check(".combo-pop 有 max-height（用户要求下拉能「加长」——本质是可滚动）",
  /\.combo-pop\s*\{[^}]*max-height:\s*300px/.test(CSS_SRC));
check("候选是现读 datalist 的（renderColorPresets 会实时改写颜色候选，不能缓存）",
  /function comboOptions\(el\)/.test(appSrc)
  && /_comboListId/.test(appSrc));

// ② 行为级：摘 list 属性 + 候选现读
function fakeInput(listId) {
  const attrs = {};
  if (listId) attrs.list = listId;   // 模拟 <input list="finishList">：armComboInput 要能读到并摘掉
  return {
    dataset: {}, value: "", _listeners: {},
    addEventListener(t, fn) { (this._listeners[t] = this._listeners[t] || []).push(fn); },
    getAttribute: (k) => (k in attrs ? attrs[k] : null),
    setAttribute: (k, v) => { attrs[k] = String(v); },
    removeAttribute: (k) => { delete attrs[k]; },
    getBoundingClientRect: () => ({ top: 100, left: 10, bottom: 130, width: 200, height: 30 }),
    focus() {}, dispatchEvent() {},
  };
}
const fakeFinish = fakeInput("finishList");
sandbox.armComboInput(fakeFinish);
check("arm 之后 list 属性被摘掉（原生弹层不再出现）",
  fakeFinish.getAttribute("list") === null && fakeFinish._comboListId === "finishList",
  JSON.stringify({ list: fakeFinish.getAttribute("list"), id: fakeFinish._comboListId }));
check("arm 是幂等的（再 arm 一次不重复挂监听）",
  (fakeFinish._listeners.mousedown || []).length === 1
  && (fakeFinish._listeners.focus || []).length === 1);

const FINISH_OPTS = ["普通", "亮面", "哑光", "磨砂", "丝绸", "珠光", "金属", "夜光"];
sandbox.document.getElementById("finishList").querySelectorAll = () =>
  FINISH_OPTS.map((v) => ({ value: v }));
check("comboOptions 从 datalist 现读候选（不缓存，改写后是新的）",
  JSON.stringify(sandbox.comboOptions(fakeFinish)) === JSON.stringify(FINISH_OPTS),
  JSON.stringify(sandbox.comboOptions(fakeFinish)));

// ③ 浮层渲染：全量 / 过滤 / 空态
const bodyKids = () => sandbox.document.body.children.length;
fakeFinish.value = "哑光";   // 当前值要能落到「选中标记」上，否则没有任何 item 该高亮
sandbox.comboRender(fakeFinish, "");
{
  const pop = sandbox.document.body.children[sandbox.document.body.children.length - 1];
  check("聚焦展开的是全量候选（不是被当前值过滤过的残列表）",
    FINISH_OPTS.every((v) => pop.innerHTML.includes(v)), pop.innerHTML.slice(0, 200));
  check("当前值带选中标记", pop.innerHTML.includes("active") && pop.innerHTML.includes("哑光"));
}
sandbox.comboRender(fakeFinish, "磨");
{
  const pop = sandbox.document.body.children[sandbox.document.body.children.length - 1];
  check("打字后候选按子串收窄",
    pop.innerHTML.includes("磨砂") && !pop.innerHTML.includes("丝绸"),
    pop.innerHTML.slice(0, 200));
}
sandbox.comboRender(fakeFinish, "不存在的工艺");
{
  const pop = sandbox.document.body.children[sandbox.document.body.children.length - 1];
  check("没有匹配项时提示「直接输入自定义值」而不是空浮层",
    pop.innerHTML.includes("直接输入自定义值"));
}

// ── 17g-2. 弹窗竞态：关一个、开一个 ──────────────────────────────
// 用户反馈「手动补录消耗、称重校准、编辑都进不去了」。根因：closeModal 里的
// history.back() 是异步的 —— popstate 还没回来，新弹窗已经开了；popstate 一到
// 就把刚打开的新弹窗当垃圾关掉。修法：back() 延迟一拍，期间弹窗重新打开就作废。
console.log("");
console.log("── 弹窗竞态（详情弹窗里点「手动补录/校准/编辑」进不去的根因） ──");

const modalHost = () => sandbox.document.getElementById("modalHost");
// 场景 A：普通关闭 —— back 延迟一拍
sandbox.history._reset();
sandbox.location.hash = "#view=spools";
sandbox.history.replaceState(null, "", "#view=spools");
sandbox.history.pushState(null, "", "#modal");
modalHost().innerHTML = "<div>旧弹窗</div>";
sandbox.closeModal();
check("closeModal 立即清空弹窗内容", modalHost().innerHTML === "");
check("back() 延迟一拍：flush 之前地址还停在 #modal",
  sandbox.location.hash === "#modal", sandbox.location.hash);
sandbox.__flushTimers();
check("flush 之后地址退回视图记录（该退的一条没少）",
  sandbox.location.hash === "#view=spools", sandbox.location.hash);

// 场景 B：关了马上开新的 —— back 必须作废
sandbox.history._reset();
sandbox.location.hash = "#view=spools";
sandbox.history.replaceState(null, "", "#view=spools");
sandbox.history.pushState(null, "", "#modal");
modalHost().innerHTML = "<div>详情弹窗</div>";
sandbox.closeModal();
modalHost().innerHTML = "<div>手动补录消耗</div>";   // openUseDialog 同步顶上
sandbox.__flushTimers();
check("换弹窗时 back 作废：新弹窗还在、地址也没被退掉",
  modalHost().innerHTML === "<div>手动补录消耗</div>" && sandbox.location.hash === "#modal",
  `hash=${sandbox.location.hash}`);
// 新弹窗正常关闭：还是只退一条记录（closeModal 自己会清空 host 并排程 back）
sandbox.closeModal();
sandbox.__flushTimers();
check("新弹窗关闭后地址退回视图（历史记录没有堆积）",
  sandbox.location.hash === "#view=spools", sandbox.location.hash);
// 源码级：这个延迟只能长存在 closeModal 里
check("closeModal 的 back() 走 setTimeout 延迟（同步 back 会关掉刚打开的替换弹窗）",
  /function closeModal[\s\S]{0,900}setTimeout\(/.test(appSrc));

// ── 17g-3. 「另有 N 盘未登记价格」钻取 ───────────────────────────
console.log("");
console.log("── 汇总页「未登记价格」钻到库存 ──");

state.spools = [
  { ...spoolForDrill(1, "拓竹", "PLA", "丝绸"), price: 0 },
  { ...spoolForDrill(2, "兰博", "PETG", ""), price: 42.79 },
  { ...spoolForDrill(3, "Kexcelled", "PLA", ""), price: 0 },
];
sandbox.jumpToSpoolsNoPrice();
check("点了之后切到库存页", state.view === "spools", String(state.view));
check("只留没登记价格的盘",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)) === "[1,3]",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)));
check("芯片可见（隐藏开关没有芯片就是「列表少了不知道为什么」）",
  sandbox.document.getElementById("noPriceChip").style.display === "");
check("汇总页计数真的换成了可点的按钮（源码级）",
  /class="linklike" onclick="jumpToSpoolsNoPrice\(\)"/.test(appSrc));

// 别的钻取入口必须把这个隐藏开关关掉，否则两个条件叠一起筛出空列表
sandbox.jumpToSpoolsByField("brand", "拓竹");
check("点品牌钻取会顺带关掉「未登记」开关（resetSpoolFilters 统一收口）",
  !state.spoolNoPrice
  && sandbox.document.getElementById("noPriceChip").style.display === "none");
check("关掉之后列表恢复该品牌的全部盘",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)) === "[1]",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)));

sandbox.jumpToSpoolsNoPrice();
sandbox.clearNoPriceFilter();
check("芯片可以手动关掉，关掉后恢复完整列表",
  JSON.stringify(sandbox.filteredSpools().map((s) => s.id)) === "[1,2,3]"
  && sandbox.document.getElementById("noPriceChip").style.display === "none");

state.spoolNoPrice = true;
sandbox.jumpToSpoolsByPrice(40, "");
check("点价格档钻取也关掉「未登记」开关（互斥条件不能叠加）",
  !state.spoolNoPrice);

// ── 17g-4. 品牌色卡：归一 + 前缀兜底 ─────────────────────────────
// 用户反馈「拓竹、兰博、kexcelled 怎么都没有色卡」。两个根因都在数据接线：
// ① CAILAB 的材料映射用字典覆盖顶掉了前面全部品牌的映射；② 兰博官网的系列名
// （「PLA耗材」这类）从不在映射表里。这里钉住前端查找的两个补丁。
console.log("");
console.log("── 品牌官方色卡：品牌归一 + 系列前缀兜底 ──");

state.catalog = {
  ...(state.catalog || {}),
  brand_lookup: { bambulab: "拓竹", bambu: "拓竹", kexcelled: "Kexcelled", kecelled: "Kexcelled" },
  color_series: {
    "拓竹": { "PLA Basic": [{ name: "黑色", hex: "#000000" }], "PETG HF": [{ name: "白", hex: "#ffffff" }] },
    "Kexcelled": { "K5 PLA": [{ name: "黑", hex: "#111111" }] },
    "兰博": { "PLA耗材": [{ name: "白", hex: "#eeeeee" }], "PETG耗材": [{ name: "雾霾蓝", hex: "#BCCBE0" }] },
  },
  material_color_series: { "PLA": ["PLA Basic", "K5 PLA"], "PETG": ["PETG HF"] },
};
check("别名「Bambu Lab」归一成「拓竹」",
  sandbox.canonicalBrand("Bambu Lab") === "拓竹", sandbox.canonicalBrand("Bambu Lab"));
check("小写「kexcelled」也能归一（色卡按规范名做键）",
  sandbox.canonicalBrand("kexcelled") === "Kexcelled");
check("没收录的品牌原样返回（自定义品牌不能被改坏）",
  sandbox.canonicalBrand("自家作坊") === "自家作坊");
check("空值安全", sandbox.canonicalBrand("") === "" && sandbox.canonicalBrand(null) === "");

const gBambu = sandbox.presetGroupsFor("Bambu Lab", "PLA");
check("老写法「Bambu Lab」也能查到拓竹色卡（归一先行）",
  gBambu.length === 1 && gBambu[0].series === "PLA Basic",
  JSON.stringify(gBambu.map((g) => g.series)));
const gLanbo = sandbox.presetGroupsFor("兰博", "PETG");
check("兰博「PETG耗材」靠前缀兜底命中（显式映射里没有这个名字）",
  gLanbo.some((g) => g.series === "PETG耗材"), JSON.stringify(gLanbo.map((g) => g.series)));
const gBambuPetg = sandbox.presetGroupsFor("拓竹", "PETG");
check("显式映射照常命中（兜底不能把老路径弄坏）",
  gBambuPetg.some((g) => g.series === "PETG HF"), JSON.stringify(gBambuPetg.map((g) => g.series)));
check("不同材料的前缀不误伤（兰博 PLA 系列不会混进 PETG）",
  !sandbox.presetGroupsFor("兰博", "PETG").some((g) => g.series === "PLA耗材"));
check("没有色卡数据的品牌返回空数组而不是报错",
  JSON.stringify(sandbox.presetGroupsFor("自家作坊", "PLA")) === "[]");
check("presetGroupsFor 查之前先过 canonicalBrand（源码级）",
  /const seriesMap = all\[canonicalBrand\(brand\)\]/.test(appSrc));


// ── 17h. 选品牌自动带出实测皮重 ──────────────────────────────────
// 用户刚报了一批上秤实测的空盘重量。选完品牌还要自己记数字太没必要，
// 但**绝不能把用户手填的皮重冲掉** —— 那比不带更糟。
console.log("");
console.log("── 选品牌自动带出实测皮重 ──");

state.catalog = {
  ...(state.catalog || {}),
  spool_weights: {
    "拓竹": [239, 190],
    "Polymaker": [150, 220],
    "大简": [239, 150],
    "魔创": [220, 200],
    "兰博": [160, 200],
    "Kexcelled": [239, 240],
    "爱酷乐": [239],
  },
};
const tareEl = () => sandbox.document.getElementById("f_spool_weight");

// ① 全新表单（皮重还是默认 250）→ 选品牌带出实测值
tareEl().value = String(sandbox.TARE_DEFAULT);
tareEl().dataset = {};
sandbox.applyBrandTare("大简");
check("皮重还是默认值时，选「大简」带出实测 239",
  Number(tareEl().value) === 239, String(tareEl().value));

// ② 换品牌：上一次是自动带的 → 应该换成新品牌的
tareEl().value = "239";
tareEl().dataset = { autoTare: "1" };
sandbox.applyBrandTare("Polymaker");
check("上一档是自动带的，换品牌时跟着换成新品牌的实测值（150）",
  Number(tareEl().value) === 150, String(tareEl().value));

// ③ 用户手填过 → 不许动
tareEl().value = "123";
tareEl().dataset = { autoTare: "" };    // onTareInput 打过的标记
sandbox.applyBrandTare("拓竹");
check("用户手填的皮重不会被品牌带出来的值冲掉",
  Number(tareEl().value) === 123, String(tareEl().value));

// ④ 自定义品牌没数据 → 什么都不做（不能清成空）
sandbox.applyBrandTare("自家作坊");
check("没收录的品牌不改动皮重框（不会清空）",
  Number(tareEl().value) === 123, String(tareEl().value));

// ⑤ 每个实测品牌的首选值都要能带对
const wantTares = { "拓竹": 239, "Polymaker": 150, "大简": 239, "魔创": 220,
                    "兰博": 160, "Kexcelled": 239, "爱酷乐": 239 };
const tareHits = [];
for (const [brand, want] of Object.entries(wantTares)) {
  tareEl().value = String(sandbox.TARE_DEFAULT);
  tareEl().dataset = {};
  sandbox.applyBrandTare(brand);
  tareHits.push(`${brand}:${tareEl().value}${Number(tareEl().value) === want ? "" : "✗"}`);
}
check("七个实测品牌带出来的皮重都对",
  !tareHits.some((h) => h.includes("✗")), tareHits.join(" "));

// ⑥ 用户在皮重框里打字后，标记必须被清掉（否则下一步换品牌又会覆盖）
tareEl().value = "180";
tareEl().dataset = { autoTare: "1" };
sandbox.onTareInput();
check("在皮重框里打字会清掉「自动带出」标记",
  tareEl().dataset.autoTare === "", JSON.stringify(tareEl().dataset));
sandbox.applyBrandTare("魔创");
check("打字之后再换品牌，手填的值仍然是安全的",
  Number(tareEl().value) === 180, String(tareEl().value));

// ⑦ 源码级：皮重框真的挂了 oninput（不然标记永远清不掉，会一直覆盖用户的值）
check("皮重输入框挂了 oninput=onTareInput()（漏了就永远覆盖用户填的值）",
  /id="f_spool_weight"[\s\S]{0,120}oninput="onTareInput\(\)"/.test(appSrc));
check("onBrandChoice 里真的调了 applyBrandTare（写了函数不等于接上了）",
  /function onBrandChoice\(\)[\s\S]{0,600}applyBrandTare\(sel\.value\)/.test(appSrc));

// ── 18. 打印记录列表行内的「耗材 / 绑定」两个键 ──────────────────
// 用户要的是「列表里直接点」，不是「先进详情再点」。最容易错的是：
// ① 一个任务绑了多盘时会以为是死键；② 没有流水时按钮还能点（点了弹不出东西）。
console.log("");
console.log("── 打印记录列表行内操作 ──");

const oneSpoolJob = {
  id: 7,
  filaments: [{ spool_id: 12, usage_id: 31, spool_name: "A 盘" }],
};
const html1 = jobRowActions(oneSpoolJob);
check("只绑一盘时给「跳转料盘」直接跳那一盘",
  /jumpToSpoolFromJob\(12\)/.test(html1), html1);
check("只绑一盘时也给了「更改料盘」",
  /openRebindUsage\(31,\s*12\)/.test(html1), html1);
check("两个键都在，不是只剩一个", (html1.match(/<button/g) || []).length === 2, html1);

const multiJob = {
  id: 8,
  filaments: [
    { spool_id: 12, usage_id: 31, spool_name: "A 盘" },
    { spool_id: 13, usage_id: 32, spool_name: "B 盘" },
  ],
};
const html2 = jobRowActions(multiJob);
check("绑了多盘时按钮改成「打开详情挑一盘」（不许闷掉）",
  /openJobDetail\(8\)/.test(html2), html2);
check("多盘时按钮上带盘数提示", /耗材\s*\(2\)|耗材 \(2\)/.test(html2), html2);
check("多盘时「绑定」也带流水条数", /绑定 \(2\)/.test(html2), html2);

// 绑了料但**没有扣重流水**（历史数据 / 手动绑定）：跳料盘能用，改扣不能用。
// 这才是「一个键禁用、另一个可用」的真实场景 —— 上一版我拿 spool_id=0 去试，
// 那种明细会直接落到「整格占位」分支，测的是另一条路。
const noUsageJob = { id: 11, filaments: [{ spool_id: 12, usage_id: 0, spool_name: "A 盘" }] };
const html5 = jobRowActions(noUsageJob);
check("有绑定没流水时：跳料盘仍可用（料盘是存在的）",
  /jumpToSpoolFromJob\(12\)/.test(html5), html5);
check("有绑定没流水时：改扣按钮是禁用态",
  /<button class="sm" disabled[^>]*>(?:(?!<\/button>)[\s\S])*绑定/.test(html5), html5);

const noFilJob = { id: 10, filaments: [] };
const html4 = jobRowActions(noFilJob);
check("没有明细时整格显示占位符，不是空白",
  html4.trim().length > 0 && !/<button/.test(html4), JSON.stringify(html4));
// 点行内按钮不该顺带把行本身的事件也触发了（否则会连着进详情）
check("行内按钮都 stopPropagation（不然点一下会连进详情）",
  (html1.match(/stopPropagation/g) || []).length >= 2, html1);

// ── 19. 品牌分布卡 ──────────────────────────────────────────────
// 用户截图里的「品牌分布」。三条底线：盘数要对、不能有空格子、点得动。
console.log("");
console.log("── 汇总页品牌分布 ──");

const bdHost = sandbox.document.getElementById("brandDist");
state.summarySpools = [
  { brand: "Polymaker", material: "PLA", price: 100 },
  { brand: "Polymaker", material: "PLA", price: 120 },
  { brand: "Polymaker", material: "PLA", price: 80 },   // 三盘，稳居第一
  { brand: "拓竹", material: "PLA", price: 90 },
  { brand: "拓竹", material: "PETG", price: null },     // 没登记价
  { brand: "大简", material: "PETG", price: 0 },        // 0 也不算有价
];
renderBrandDist();
const bdHtml = bdHost.innerHTML;
check("品牌按盘数排序（多的在前）",
  bdHtml.indexOf("Polymaker") < bdHtml.indexOf("拓竹")
  && bdHtml.indexOf("拓竹") < bdHtml.indexOf("大简"), bdHtml.slice(0, 200));
check("三个品牌都画出来了",
  bdHtml.includes("Polymaker") && bdHtml.includes("拓竹") && bdHtml.includes("大简"), bdHtml.slice(0, 200));
check("点品牌行调 jumpToSpoolsByField('brand', …)",
  /jumpToSpoolsByField\('brand'/.test(bdHtml), bdHtml.slice(0, 300));
check("品牌名走 data-value（不是拼进 onclick 字符串里）",
  /data-value="Polymaker"/.test(bdHtml), bdHtml.slice(0, 300));

// 均价：Polymaker 三盘 100/120/80 -> 100；分母只算登记过的盘
const bdText = bdHtml.replace(/<[^>]+>/g, " ");
check("均价按「登记过价的盘」算（(100+120+80)/3 = 100）",
  /100\.00/.test(bdText), bdText.slice(0, 400));
check("一盘都没登记价的品牌明说未登记，不留空",
  /未登记价格/.test(bdText), bdText.slice(0, 400));
// 「不留空」是用户的明确要求：每个 bd-sub 都得有字
const subs = bdHtml.match(/<span class="bd-sub">[\s\S]*?<\/span>/g) || [];
check("每一行的价格说明位置都有内容",
  subs.length === 3 && subs.every((s) => s.replace(/<[^>]+>/g, "").trim().length > 0),
  JSON.stringify(subs));

// 筛选到某材料时，品牌分布要跟着只剩那一种材料
state.summaryFilter = "PETG";
renderBrandDist();
const bdFiltered = bdHost.innerHTML;
check("筛选材料后品牌分布只剩该材料涉及的品牌",
  !bdFiltered.includes("Polymaker") && bdFiltered.includes("拓竹") && bdFiltered.includes("大简"),
  bdFiltered.slice(0, 200));
state.summaryFilter = "";
state.summarySpools = [];
renderBrandDist();
check("没有料盘时品牌分布给空态而不是空白",
  /empty-state/.test(bdHost.innerHTML), bdHost.innerHTML.slice(0, 160));

const counter = sandbox.document.getElementById("brandDistCount");
state.summarySpools = [
  { brand: "A", price: 1 }, { brand: "A", price: 1 }, { brand: "B", price: 1 },
];
renderBrandDist();
check("右上角计数写了品牌数与总盘数",
  /2\s*个品牌/.test(counter.textContent) && /共\s*3\s*盘/.test(counter.textContent),
  JSON.stringify(counter.textContent));
state.summarySpools = [];

// ── 20. 刷新后留在原页面（localStorage 兜底） ────────────────────
console.log("");
console.log("── 刷新后停在原视图 ──");
localStorageStub.clear();
check("没记录过时 lastRememberedView() 返回空串（交给 dashboard 兜底）",
  lastRememberedView() === "", JSON.stringify(lastRememberedView()));
rememberView("jobs");
check("记住之后读得回来", lastRememberedView() === "jobs", JSON.stringify(lastRememberedView()));
// 手写的脏值（老版本、或用户自己改过）不许放行，否则 refresh 会掉进一个不存在的视图
localStorageStub.setItem(VIEW_STORE_KEY, "not-a-view");
check("存了非法视图名时当作没存（不会跳到空白页）",
  lastRememberedView() === "", JSON.stringify(lastRememberedView()));
check("VIEW_STORE_KEY 是稳定的（改了会丢老用户的记录）",
  VIEW_STORE_KEY === "bambu.lastView", VIEW_STORE_KEY);
// 深链（#spool= / #bind=）不该把 localStorage 记录冲掉：切视图时就要记下
localStorageStub.clear();
syncHashView("summary");
check("切视图会把视图名写进 localStorage",
  lastRememberedView() === "summary", JSON.stringify(lastRememberedView()));

// ── 打印成果图（cover） ─────────────────────────────────────────
// 这一段专门盯「下拉空着也能通过」那类假断言：断言不能只看「有 img」，
// 要同时验「有图时才出图」「无图时不许出破图」两个方向。
console.log("");
console.log("── 打印成果图 ──");
{
  const okJob = { id: 42, cover_file: "42.png", has_cover: true };
  const noJob = { id: 43, cover_file: "", has_cover: false };
  // 最容易错的一种：文件名还在（文件被别人清掉了），has_cover=False
  const staleJob = { id: 44, cover_file: "44.png", has_cover: false };

  check("有成果图 → 地址指向本地接口",
    sandbox.jobCoverUrl(okJob) === "/api/jobs/42/cover", sandbox.jobCoverUrl(okJob));
  check("无成果图 → 地址是空串（不许拼出一个 404 的地址）",
    sandbox.jobCoverUrl(noJob) === "", sandbox.jobCoverUrl(noJob));
  check("文件名在但文件已丢 → 也当无图（has_cover 才作数）",
    sandbox.jobCoverUrl(staleJob) === "", sandbox.jobCoverUrl(staleJob));
  check("job 为 null 不炸", sandbox.jobCoverUrl(null) === "");

  const thumbOk = sandbox.jobThumbHtml(okJob);
  check("列表缩略图：有图时确实渲染出 <img>", /<img[^>]*class="job-thumb"/.test(thumbOk), thumbOk);
  check("列表缩略图：src 指向本地成果图接口",
    /src="\/api\/jobs\/42\/cover"/.test(thumbOk), thumbOk);
  check("列表缩略图：点击不会连带打开详情弹窗（stopPropagation）",
    /stopPropagation/.test(thumbOk), thumbOk);
  check("列表缩略图：点击走 openJobCover 开新窗口",
    /openJobCover\(42\)/.test(thumbOk), thumbOk);

  const thumbNo = sandbox.jobThumbHtml(noJob);
  check("列表缩略图：无图时不渲染 <img>（占位而不是破图）",
    !/<img/.test(thumbNo), thumbNo);
  check("列表缩略图：无图时给出破折号占位", /—/.test(thumbNo), thumbNo);

  const blockOk = sandbox.jobCoverBlock(okJob);
  check("详情：有图时渲染 <img>", /<img[^>]*src="\/api\/jobs\/42\/cover"/.test(blockOk), blockOk);
  check("详情：说明了这是切片盘面预览图、不是摄像头实拍",
    /切片盘面预览图/.test(blockOk) && /不是摄像头实拍/.test(blockOk), blockOk);

  const blockNo = sandbox.jobCoverBlock(noJob);
  check("详情：无图时不渲染 <img>", !/<img/.test(blockNo), blockNo);
  check("详情：无图时给出解释文案", /没有给成果图/.test(blockNo), blockNo);

  // 深链/异常入口：job.id 缺失时不许拼出 /api/jobs/NaN/cover
  check("job.id 缺失时 openJobCover 不拼出 NaN",
    !/NaN/.test(String(sandbox.jobCoverUrl({ id: undefined, has_cover: true }))),
    String(sandbox.jobCoverUrl({ id: undefined, has_cover: true })));
}

// ── 汇总 ────────────────────────────────────────────────────────
console.log("");
if (FAILED.length) {
  console.log(`通过 ${PASSED.length} 项，失败 ${FAILED.length} 项`);
  console.log(`失败项： ${JSON.stringify(FAILED)}`);
  process.exit(1);
}
console.log(`通过 ${PASSED.length} 项，失败 0 项`);
console.log("界面口径自测全部通过。");
