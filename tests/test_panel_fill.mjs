/* 设备面板前端口径自测（node 直跑，不需要浏览器）。
 *
 * app.js 是给浏览器写的普通脚本（末尾直接 boot()），这里用 vm 把它跑在一个
 * 最小沙箱里：补上 document / window / localStorage / setInterval，并把末尾的
 * boot() 摘掉（它会发真实请求），然后校验 window.panelDebug 暴露出来的纯函数。
 *
 * 为什么要测这两个函数：
 *   1) fanChannels —— 风扇四行的**名字**是用户拿着拓竹 App 截图逐字对过的
 *      （部件 / 右(辅助) / 左(辅助) / 外排）。名字是给机器看的配置，写错了
 *      肉眼扫一眼很容易滑过去，所以把字符串钉死。
 *   2) filFill —— 料条高度按余重算。用户原话「不要耗材一直是满的」，
 *      而「满格」正好是最不容易被发现的错误状态（看起来很正常）。
 *
 * 运行： node tests/test_panel_fill.mjs
 */
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const SRC = path.join(ROOT, "app", "static", "app.js");

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
    style: {},
    dataset: {},
    classList: {
      add() {}, remove() {}, toggle() {}, contains() { return false; },
    },
    innerHTML: "",
    outerHTML: "",
    textContent: "",
    value: "",
    checked: false,
    hidden: false,
    disabled: false,
    files: [],
    children: [],
    options: [],
    selectedIndex: 0,
    appendChild(node) { return node; },
    removeChild() {},
    remove() {},
    setAttribute() {},
    getAttribute() { return null; },
    hasAttribute() { return false; },
    removeAttribute() {},
    addEventListener() {},
    removeEventListener() {},
    querySelector() { return stubEl(); },
    querySelectorAll() { return []; },
    closest() { return stubEl(); },
    contains() { return false; },
    focus() {},
    blur() {},
    click() {},
    scrollIntoView() {},
    insertAdjacentHTML() {},
    replaceChildren() {},
    getBoundingClientRect() {
      return { top: 0, left: 0, right: 0, bottom: 0, width: 0, height: 0 };
    },
    getContext() { return null; },
    toDataURL() { return ""; },
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
  fetch: () => new Promise(() => {}), // 永挂起：boot() 已被摘掉，这里只是兜底
  WebSocket: class { constructor() { this.readyState = 0; } send() {} close() {} addEventListener() {} },
  alert() {},
  confirm: () => false,
  prompt: () => null,
  btoa: (s) => Buffer.from(s, "binary").toString("base64"),
  atob: (s) => Buffer.from(s, "base64").toString("binary"),
  Blob: class {},
  URL: { createObjectURL: () => "", revokeObjectURL() {} },
  navigator: { clipboard: { writeText: async () => {} }, bluetooth: undefined },
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
  addEventListener() {},
  removeEventListener() {},
  body: stubEl(),
  head: stubEl(),
  documentElement: stubEl(),
  cookie: "",
};
sandbox.window.addEventListener = () => {};
sandbox.window.matchMedia = () => ({ matches: false, addEventListener() {}, addListener() {} });
sandbox.window.localStorage = localStorageStub;

const ctx = vm.createContext(sandbox);
let src = fs.readFileSync(SRC, "utf8");
// 末尾的 boot() 会去发请求、连 WebSocket，自测里不需要它
src = src.replace(/^boot\(\);\s*$/m, "");
vm.runInContext(src, ctx, { filename: "app.js" });

const dbg = sandbox.window.panelDebug;
if (!dbg) {
  console.error("app.js 没有导出 window.panelDebug，无法自测（是不是被改掉了？）");
  process.exit(1);
}
const { fanChannels, filFill, MIN_FILL_PCT } = dbg;

// ── 1. 风扇四行命名 ─────────────────────────────────────────────
console.log("== 风扇通道命名（P2S / X2 对齐拓竹 App「空调系统」页） ==");

for (const model of ["P2S", "p2s", "X2", "X2C"]) {
  const rows = fanChannels({ model });
  const names = rows.map((r) => r[1]);
  check(`${model} 四行命名与顺序：部件 / 右(辅助) / 左(辅助) / 外排`,
    names.join("/") === "部件/右(辅助)/左(辅助)/外排", names.join("/"));
  check(`${model} 四行键位正确`,
    rows.map((r) => r[0]).join(",") === "cooling,aux,secondary,exhaust",
    rows.map((r) => r[0]).join(","));
  check(`${model} 四行都是必显（缺件由值是否为 null 决定，不靠隐藏行）`,
    rows.every((r) => r[2] === true));
}

const x1 = fanChannels({ model: "X1C" }).map((r) => r[1]);
check("X1 等无自适应风道组件的机型仍用「腔体风扇」那套命名",
  x1.join("/") === "部件冷却风扇/辅助部件冷却风扇/腔体风扇/热端风扇", x1.join("/"));
check("非 P2S/X2 不出现「外排」这一行", !x1.includes("外排"));
check("机型缺失不炸", Array.isArray(fanChannels({})) && Array.isArray(fanChannels(null)));

// ── 2. 料条高度 = 余重 ÷ 满盘容量 ───────────────────────────────
console.log("== 料条高度（按剩余克重，不再一律满格） ==");

const near = (a, b) => Math.abs(a - b) < 0.05;

const f1 = filFill({ initial_weight: 1000, remaining_weight: 248 }, null);
check("拓竹 1kg 盘剩 248g → 24.8%", near(f1.pct, 24.8) && f1.known, JSON.stringify(f1));

const f2 = filFill({ initial_weight: 1000, remaining_weight: 218 }, null);
check("剩 218g → 21.8%", near(f2.pct, 21.8) && f2.known, JSON.stringify(f2));

const f3 = filFill({ initial_weight: 1000, remaining_weight: 1000 }, null);
check("全新盘才画满格", near(f3.pct, 100), JSON.stringify(f3));

const f4 = filFill({ initial_weight: 1000, remaining_weight: 0 }, null);
check("空盘留一条可见的边（不被夹成 0）", near(f4.pct, MIN_FILL_PCT), JSON.stringify(f4));

const f5 = filFill({ initial_weight: 250, remaining_weight: 248 }, null);
check("250g 小盘剩 248g → 99.2%（按各自满盘容量算，不是按 1kg）",
  near(f5.pct, 99.2), JSON.stringify(f5));

const f6 = filFill(null, { tray_weight: 1000, remain_weight_g: 500, remain: 50 });
check("没绑定料盘时用机器上报的余重 500g → 50%",
  near(f6.pct, 50) && f6.known, JSON.stringify(f6));

const f7 = filFill(null, { remain: 30 });
check("只有百分比时退回 remain → 30%", near(f7.pct, 30) && f7.known, JSON.stringify(f7));

const f8 = filFill(null, null);
check("什么都不知道 → 压暗处理（known=false），由界面显示未知",
  f8.known === false, JSON.stringify(f8));

// 这是写这组测试时抓出来的真 bug：Number(null) === 0、Number("") === 0，
// 于是「字段缺失」被当成「余重 0 克」，料条被画成一小条且 known 还是 true，
// 「未知」状态永远不出现。
const f8b = filFill(null, { tray_weight: 1000, remain_weight_g: null, remain: null });
check("余重字段是 null（机器没上报）→ 未知，不是 0 克",
  f8b.known === false, JSON.stringify(f8b));
const f8c = filFill(null, { tray_weight: 1000, remain_weight_g: "", remain: "" });
check("余重字段是空串 → 未知，不是 0 克",
  f8c.known === false, JSON.stringify(f8c));
const f8d = filFill({ initial_weight: 1000, remaining_weight: null }, null);
check("台账余重是 null → 未知", f8d.known === false, JSON.stringify(f8d));
const f8e = filFill(null, { remain_weight_g: 0 });
check("真的剩 0 克 → known=true（和「不知道」要区分开）",
  f8e.known === true && near(f8e.pct, MIN_FILL_PCT), JSON.stringify(f8e));

const f9 = filFill({ initial_weight: 1000 }, { tray_weight: 1000, remain_weight_g: 700 });
check("台账没有余重时回落到机器上报（700g → 70%）",
  near(f9.pct, 70) && f9.known, JSON.stringify(f9));

const f10 = filFill({ initial_weight: 0, remaining_weight: 300 }, { tray_weight: 1000, remain_weight_g: 300 });
check("满盘容量为 0（脏数据）不除零、走下一级来源",
  Number.isFinite(f10.pct) && near(f10.pct, 30), JSON.stringify(f10));

const f11 = filFill({ initial_weight: 1000, remaining_weight: 5000 }, null);
check("余重超过满盘（补录写多了）夹到 100%", near(f11.pct, 100), JSON.stringify(f11));

console.log(`\n通过 ${PASSED.length} 项，失败 ${FAILED.length} 项`);
if (FAILED.length) {
  console.log("失败项：", FAILED);
  process.exit(1);
}
console.log("全部通过");
