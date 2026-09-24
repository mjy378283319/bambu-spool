/* ══════════════════════════════════════════════════════════════════
 * 标签打印：浏览器渲染 → PNG → 汉印 HMarkService（官方驱动）出纸
 * ══════════════════════════════════════════════════════════════════
 *
 * 为什么在浏览器里渲染而不是服务端：
 *   容器镜像 python:3.12-slim 没有中文字体，服务端画中文要额外装 ~5MB 字体包；
 *   浏览器 Canvas 直接用系统字体，中文天然可用，而且预览就是最终效果。
 *
 * 打印通道（1.0.0 起**只剩一条**）：
 *   USB / 官方驱动 —— 浏览器原生 WebSocket 连本机「汉印 HMark Services」
 *   （官方驱动自带，ws://127.0.0.1:9004），把标签 PNG 交给 Windows 打印池 +
 *   汉印驱动出纸。实测 PrintNum=3 零串位；定位/节距全部由驱动负责。
 *
 * ★ 蓝牙（Web Bluetooth 直发 ESC/POS）已在 1.0.0 **整体删除**：
 *   这台固件「不按全 0 垫行走纸、FF 走 0」，多份内容逐张往上爬约 2.4mm，
 *   0.12.8~0.12.34 连改十几版都没稳住（根因在固件，无解）。
 *   想考古这段历史看 git 0.12.36 及更早，或 .workbuddy 日志 2026-09-2x。
 *   想加回来：新开一个大版本号，别在 1.x 里混。
 *
 * 已知限制：
 *   HMarkService 只在 Windows PC 上有 —— 手机端打不了，只能「下载标签图」
 *   存相册后用汉码 App 放图片打印。
 */

(function () {
  "use strict";

  const LABEL_FAMILY =
    '"Microsoft YaHei","PingFang SC","Hiragino Sans GB","Noto Sans CJK SC","Source Han Sans SC",system-ui,sans-serif';

  // 4×4 有序抖动矩阵已随色块一起移除：热敏打印机只有黑白两色，
  // 打印出来的「颜色深浅」网点既认不出颜色、又占版面。

  const LABEL_PRESETS = [
    { w: 40, h: 30 },
    { w: 50, h: 30 },
    { w: 60, h: 40 },
    { w: 50, h: 40 },
  ];

  // 二维码在标签上占的版面：宽最多取 62%、高最多占满（留上下留白）。
  // 之前按「模块 0.34mm」反推，203dpi 下二维码只有 11mm 见方，比手机屏幕上的
  // 小程序码还小、扫起来要贴很近；现在直接按版面反推倍率，实际结果是
  // 「宽度的 50%~58%」——50×30 标签上约 27.8mm 见方，接近半张标签。
  // 每模块仍是整数个点、绝不缩放，所以取到的是不超过目标尺寸的最大整数倍率。
  const QR_WIDTH_RATIO = 0.62;

  const LS_KEY = "bambu.label.cfg";

  const LABEL = {
    cfg: null,
    spoolId: 0,
    busy: false,
    renderToken: 0,
  };

  /* ── 小工具 ─────────────────────────────────────────────── */

  function mm2dot(mm, dpi) {
    return (mm / 25.4) * dpi;
  }

  /* ── 配置 ───────────────────────────────────────────────── */

  // cfgRev：改版式参数默认值时 +1。旧存档 rev 不一致时整份回本版默认
  //  —— 不然 localStorage 里旧版的实验开关/版式参数会被永远沿用。
  // 1.0.0（大版本）：蓝牙通道整体删除，配置里只剩版式字段；旧存档一律重置。
  const CFG_REV = 9;

  function defaultCfg() {
    // footMargin = 底部留白（mm）：画布高度 = 标签高 − 留白。
    //   2.75mm 对齐汉码官方抓包（50×30 标签内容区 218 行 = 27.25mm），0.12.36 的
    //   死区/居中几何都是在这个值上调出来的 —— 别动，面板上也不再暴露这个旋钮。
    // topShiftMm = 内容整体下移（mm）：1.5mm 让内容块上下留白对称、落标签正中
    //   （09-22 用户要求居中 + 09-24 真机验证通过）。同样不再暴露。
    return {
      wMm: 50, hMm: 30, dpi: 203, copies: 1,
      footMargin: 2.75, topShiftMm: 1.5, cfgRev: CFG_REV,
    };
  }

  function loadCfg() {
    if (LABEL.cfg) return LABEL.cfg;
    const cfg = defaultCfg();
    try {
      const raw = localStorage.getItem(LS_KEY);
      const saved = raw ? JSON.parse(raw) : null;
      if (saved && Number(saved.cfgRev) === CFG_REV) Object.assign(cfg, saved);
    } catch (err) {
      /* 配置坏了就用默认值 */
    }
    LABEL.cfg = cfg;
    return cfg;
  }

  function saveCfg() {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(LABEL.cfg));
    } catch (err) {
      /* 隐私模式下写不了，忽略 */
    }
  }

  /* ── 渲染 ───────────────────────────────────────────────── */

  /** 版式全部用毫米算，再换算成点，这样换尺寸/换 dpi 都不用改代码。
   *  二维码固定在右侧、占满整个高度；左侧文字列纵向**按实际行数均分**：
   *  只固定「第一行基线」和「页脚基线」，中间的行摊开铺满，
   *  行数少了间距自动变大也不会留出一大块空白（固定几档 y 值时，
   *  副行省略后会空一块）。 */
  function layoutOf(wMm, hMm) {
    const pad = Math.max(1.1, wMm * 0.032);
    // ★ 打印头右侧有一段**物理打不出来的死区**（标尺图实测：50mm 标签只打到 47mm，
    //   最后 ~2.8mm 纯白无墨；汉印官方样图同样在右侧留 2.91mm 白边 —— 互相印证）。
    //   右侧留白 = 左侧 pad + 1.8mm 保险，确保二维码/页脚不越界被裁竖线。
    //   （0.12.35 之前左右同用 1.6mm，QR 右缘落在死区里，用户截图右竖线被裁。）
    const padR = pad + 1.8;
    return {
      pad, padR,
      top: hMm * 0.155,  // 第一行文字基线
      foot: hMm * 0.91,  // 页脚基线（固定在最下面，不参与均分）
    };
  }

  /** 有效内容高度（mm）= 标签高 − 底部留白。
   *  留白 2.75mm 对齐汉码官方抓包（1.0.0 前的蓝牙通道靠它防串位；现在保持
   *  同一几何，已验证的居中/死区版式不用重调）。 */
  function effHeightMm(hMm, footMarginMm) {
    const h = Number(hMm) || 0;
    const m = Math.max(0, Number(footMarginMm) || 0);
    return Math.max(6, h - m);
  }

  /** 光栅高度（点）。50×30 标签 + 留白 2.75mm → 218 行，与汉码官方抓包逐行一致。
   *  抽成纯函数是为了让测试能钉住这个数（改留白/尺寸时不会悄悄跑偏）。 */
  function rasterRowsFor(hMm, footMarginMm, dpi) {
    return Math.max(8, Math.round(mm2dot(effHeightMm(hMm, footMarginMm), dpi)));
  }

  /** 写字：超宽先缩字号，还超就截断加省略号。返回最终画出的文本。
   *
   *  收缩下限取 62%：二维码放大到近半张标签后，文字列只剩 ~21mm（50×30 标签），
   *  像「Polymaker PETG 黑色」这种 16 字符的名字按原字号放不下。原来下限是 70%，
   *  缩到底仍会截断；放到 62% 这类名字刚好能整串放下，
   *  而 62% 在 203dpi 下仍有 15.6px，热敏纸上依然清楚。 */
  function drawText(ctx, dpi, text, xMm, baseMm, sizeMm, opt) {
    opt = opt || {};
    const s = String(text == null ? "" : text);
    const weight = opt.bold ? "700" : "400";
    const fontAt = (mm) => `${weight} ${mm2dot(mm, dpi)}px ${LABEL_FAMILY}`;

    let size = sizeMm;
    let out = s;
    ctx.font = fontAt(size);
    const maxDots = opt.maxMm ? mm2dot(opt.maxMm, dpi) : 0;
    if (maxDots && ctx.measureText(out).width > maxDots) {
      while (size > sizeMm * 0.62) {
        size -= 0.1;
        ctx.font = fontAt(size);
        if (ctx.measureText(out).width <= maxDots) break;
      }
      // 缩到下限后仍然放不下才截断。缩完能放下就别碰它 —— 否则会为了给
      // 省略号腾地方白砍掉几个字（整串明明塞得下），这是之前的一个真 bug。
      if (ctx.measureText(out).width > maxDots) {
        while (out.length > 1 && ctx.measureText(out + "…").width > maxDots) {
          out = out.slice(0, -1);
        }
        if (out !== s) out += "…";
      }
    }

    ctx.fillStyle = "#000";
    ctx.textBaseline = "alphabetic";
    const w = ctx.measureText(out).width;
    let x = mm2dot(xMm, dpi);
    if (opt.align === "right") x -= w;
    else if (opt.align === "center") x -= w / 2;
    ctx.fillText(out, x, mm2dot(baseMm, dpi));
    return out;
  }

  /** 去重：名字里已经出现过的信息不再重复印（页脚用）。
   *  例如名字叫「魔创 PLA 天蓝色」时，页脚不再带「天蓝色」。 */
  function dedupeAgainst(name, parts) {
    const out = [];
    for (const p of parts) {
      const t = String(p == null ? "" : p).trim();
      if (!t || name.includes(t)) continue;
      out.push(t);
    }
    return out;
  }

  /** 从料盘名里剥掉品牌/材料/外观，剩下的是「这盘料自己的名字」。
   *  自动拼的名字（品牌 材料 颜色）剥完只剩颜色，正好当第三行，
   *  不会跟第一、二行重复；手动起的名（如「厨房测试盘」）原样保留。 */
  function residualName(name, parts) {
    let out = String(name == null ? "" : name);
    for (const p of parts) {
      const t = String(p == null ? "" : p).trim();
      if (!t) continue;
      out = out.split(t).join(" ");
    }
    return out.replace(/[·•,，、/\\|\-—]+/g, " ").replace(/\s+/g, " ").trim();
  }

  function loadQrImage(spoolId, box) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = "/api/labels/spool/" + spoolId + ".png?box=" + box;
    });
  }

  /** 由「目标点数」和「模块数」反推每模块几个点。
   *  取不超过目标的**最大整数倍率**（至少 1），这样二维码 1:1 贴上去即可，
   *  绝不缩放；代价是实际尺寸可能比目标小一点，但绝不会糊掉扫描不出。
   *  没有模块数（取图失败）时退回 4，跟旧默认一致。 */
  function qrBoxFor(targetDots, modules) {
    if (!modules || modules <= 0) return 4;
    return Math.max(1, Math.floor(targetDots / modules));
  }

  /** 画一张料盘标签。返回 canvas（尺寸 = 标签实际点数，高度已扣掉底部留白）。 */
  async function renderLabel(spool, cfg) {
    const dpi = cfg.dpi;
    const wDots = Math.max(8, Math.round(mm2dot(cfg.wMm, dpi)));
    // 关键：画布高度 = 标签高 − 底部留白，版式也按这个有效高度排版。
    // 2.75mm 留白 + 1.5mm 内容下移是 09-22~09-24 真机验证过的居中几何，别动。
    const hEff = effHeightMm(cfg.hMm, cfg.footMargin);
    const hDots = rasterRowsFor(cfg.hMm, cfg.footMargin, dpi);
    const canvas = document.createElement("canvas");
    canvas.width = wDots;
    canvas.height = hDots;

    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, wDots, hDots);

    const L = layoutOf(cfg.wMm, hEff);
    // 内容整体下移（mm）：抵消「打出来内容偏上」这类**固定纸位误差**。
    //   只挪内容、不改画布高度 ⇒ 打印长度与字节数都不变（125 点 ≈ 0.6mm@203dpi，
    //   上限 3mm：再多会把底部页脚挤出画面）。上限/下限都在这里兜住，
    //   面板上那 0~3 的限制只是 UI，真正生效的是这一行。
    const dyMm = Math.max(0, Math.min(3, Number(cfg.topShiftMm) || 0));
    const dyDots = mm2dot(dyMm, dpi);

    // 二维码：服务端按整数倍模块出图，这里 1:1 贴上去，绝不缩放。
    // 先用 box=4 探出模块数（模块数只跟内容/静区有关，跟 box 无关），
    // 再由「想要多大」反推倍率，取不超过目标尺寸的最大整数倍率。
    const probe = await loadQrImage(spool.id, 4);
    const modules = probe ? Math.round(probe.naturalWidth / 4) : 0;
    const padDots = mm2dot(L.pad, dpi);
    const padRDots = mm2dot(L.padR, dpi);
    const targetDots = Math.min(wDots * QR_WIDTH_RATIO, Math.max(8, hDots - padDots * 2 - dyDots));
    const box = qrBoxFor(targetDots, modules);
    const qr = (probe && box === 4 ? probe : await loadQrImage(spool.id, box)) || probe;
    const qrDots = qr ? qr.naturalWidth : 0;
    const qrMm = qrDots / mm2dot(1, dpi);
    if (qr) {
      // x 用 padR：右侧死区（实测 ~2.8mm）之外才打得出墨
      ctx.drawImage(qr, wDots - Math.round(padRDots) - qrDots, Math.round(padDots + dyDots));
    }
    // 文字列的右边界：让开二维码
    const textMax = (qr ? cfg.wMm - L.padR - qrMm - 0.8 : cfg.wMm - L.padR) - L.pad;

    const textX = L.pad;
    const name = String(spool.name || "");

    // 左侧文字固定四行：
    //   1 品牌  2 类型·外观  3 名字（剥掉品牌/材料后剩下的，通常是颜色名）
    //   4 余量（含总量）
    // 有「位置」就在第 4 行下面再补一行；页脚（编号·色值）固定在最下面不动。
    // 行数不固定，所以中间各行按实际行数均分纵向空间，不留大片空白。
    const typeText = [spool.material, spool.finish && spool.finish !== "普通" ? spool.finish : ""]
      .filter(Boolean).join(" · ");
    const ownName = residualName(name, [spool.brand, spool.material, spool.finish])
      || spool.color_name || name;
    const remain = Math.round(spool.remaining_weight);
    const initial = Math.round(spool.initial_weight);
    const rows = [
      { text: spool.brand, size: 0.088 },
      { text: typeText, size: 0.085 },
      { text: ownName, size: 0.100, bold: true },
      { text: "余 " + remain + " g / " + initial + " g", size: 0.098, bold: true },
      { text: spool.location ? "位置 " + spool.location : "", size: 0.065 },
    ].filter((r) => String(r.text == null ? "" : r.text).trim());

    const topBase = L.top + dyMm;
    const bottomBase = L.foot - hEff * 0.115 + dyMm; // 最后一行与页脚之间留一行字高的空
    const n = rows.length;
    rows.forEach((row, i) => {
      const y = n > 1 ? topBase + ((bottomBase - topBase) * i) / (n - 1) : topBase;
      drawText(ctx, dpi, String(row.text), textX, y, hEff * row.size,
        { bold: !!row.bold, maxMm: textMax });
    });

    // 页脚：编号 + 色值；颜色名只在名字里没写时才补上（否则又是重复）
    const foot = ["#" + spool.id, ...dedupeAgainst(name, [spool.color_name])];
    if (spool.color_hex) foot.push(String(spool.color_hex).toUpperCase());
    drawText(ctx, dpi, foot.join(" · "), textX, L.foot + dyMm, hEff * 0.062, { maxMm: textMax });

    return canvas;
  }

  /* ── 对外动作 ───────────────────────────────────────────── */

  function currentSpool() {
    return (S.spools || []).find((s) => s.id === LABEL.spoolId) || null;
  }

  async function labelCanvas() {
    const spool = currentSpool();
    if (!spool) throw new Error("请先选一盘料");
    return renderLabel(spool, loadCfg());
  }

  /** 面板上打出正在运行的后端版本：截图就能自证「容器里到底是哪一版」。
   *  以前版本号只在设置页，标签面板的截图看不出新旧 —— 「两个旋钮在哪呢」这类
   *  排查每次都要先问一轮「你拉镜像了吗」。取 /api/system/status 的 version，
   *  拿不到写「未知」（不写 undefined，免得在界面上露馅）。
   *  ⚠️ 别再在这里硬写版本号：后端两处（main.py / routes.py）已经要同改了。 */
  function runningVersion() {
    const v = S && S.status && S.status.version;
    return v ? String(v) : "未知";
  }

  async function labelRefresh() {
    const token = ++LABEL.renderToken;
    const host = document.getElementById("labelPreviewHost");
    if (!host) return;
    host.innerHTML = '<div class="empty-state">正在渲染…</div>';
    try {
      const canvas = await labelCanvas();
      if (token !== LABEL.renderToken) return; // 期间又改了参数，丢弃这次结果
      canvas.className = "label-canvas";
      host.innerHTML = "";
      host.appendChild(canvas);
      const spool = currentSpool();
      const cfg = loadCfg();
      const info = document.getElementById("labelInfo");
      if (info) {
        info.textContent =
          Math.round(cfg.wMm) + "×" + Math.round(cfg.hMm) + " mm · " + cfg.dpi + " dpi · " +
          canvas.width + "×" + canvas.height + " 点" +
          " · 版本 " + runningVersion() +
          (spool && spool.name ? " · " + spool.name : "");
      }
    } catch (err) {
      host.innerHTML = '<div class="empty-state">渲染失败：' + esc(err.message) + "</div>";
    }
  }

  async function labelDownload() {
    try {
      const spool = currentSpool();
      const canvas = await labelCanvas();
      const blob = await new Promise((r) => canvas.toBlob(r, "image/png"));
      if (!blob) throw new Error("导出 PNG 失败");
      const safe = String(spool.name || "料盘").replace(/[\\/:*?"<>|]/g, "_");
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "标签-" + spool.id + "-" + safe + ".png";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 4000);
      toast("标签图已导出，手机上存进相册后可用汉码 App 放图片打印", "ok");
    } catch (err) {
      toast(err.message, "err");
    }
  }

  /* ── USB / 官方驱动通道（汉印 HMarkService）───────────────────────
   *
   * 为什么要有第二条路（0.12.35）：BLE 直发 ESC/POS 时这台固件「不按全 0 垫行走纸、
   * FF 走 0」，多份内容逐张往上爬约 2.4mm —— 0.12.31~0.12.34 连改三次都没稳住。
   * 官方网页走的是「Windows 打印池 + 汉印驱动」，定位由驱动负责，实测 PrintNum=3 不串位。
   * 这条路的前提：本机装了「汉印 HMark Services」，且打印机用 **USB** 接着。
   */

  var HMARK_URL = "ws://127.0.0.1:9004/";

  /** 连本机 HMarkService。官方网页就是这么连的，浏览器原生 WebSocket 即可
   *  （Node 的内置 WebSocket 反而会被 SuperSocket 1.6 拒掉，别照搬那套手写帧）。 */
  function hmarkConnect() {
    return new Promise(function (resolve, reject) {
      var ws;
      try {
        ws = new WebSocket(HMARK_URL);
      } catch (e) {
        reject(new Error("无法创建连接：" + e.message));
        return;
      }
      var timer = setTimeout(function () {
        try { ws.close(); } catch (e) { /* ignore */ }
        reject(new Error("连接超时：本机没装「汉印 HMark Services」或它没在运行"));
      }, 5000);
      ws.onopen = function () { clearTimeout(timer); resolve(ws); };
      ws.onerror = function () {
        clearTimeout(timer);
        reject(new Error(
          "连不上汉印打印服务（" + HMARK_URL + "）。确认本机装了「汉印 HMark Services」" +
          "并且正在运行，打印机用 USB 接在本机"
        ));
      };
    });
  }

  /** 发一条命令并等回包。
   *  ★ 外层格式是「命令名 + 空格 + JSON」：`hmarkwebclient {…}`
   *    —— SuperSocket 子协议的默认约定，不是 JSON 再包一层 key。这个错了服务端会静默不回。
   *  回包形如 {"fun":"outputPrintting","code":200,"data":"output Success"}。 */
  function hmarkCall(ws, fun, data, timeoutMs) {
    return new Promise(function (resolve, reject) {
      var timer = setTimeout(function () {
        reject(new Error("打印服务无响应（" + fun + "）"));
      }, timeoutMs || 30000);
      ws.onmessage = function (ev) {
        var o = null;
        try { o = JSON.parse(ev.data); } catch (e) { o = null; }
        if (!o) return;
        if (o.fun && o.fun !== fun) return;   // 别的命令的回包，继续等
        clearTimeout(timer);
        resolve(o);
      };
      ws.send("hmarkwebclient " + JSON.stringify({ fun: fun, data: data }));
    });
  }

  /** 从本机打印机列表里挑一台汉印的。用户选过就记住（存 localStorage）。 */
  function hmarkPickPrinter(list) {
    var names = [];
    try { names = JSON.parse(list) || []; } catch (e) { names = []; }
    if (!names.length) return "HPRT HM-T260LR";
    var saved = "";
    try { saved = localStorage.getItem("bambu.hmarkPrinter") || ""; } catch (e) { saved = ""; }
    if (saved && names.indexOf(saved) >= 0) return saved;
    for (var i = 0; i < names.length; i++) {
      if (/HPRT|HM-|hprt/i.test(names[i])) return names[i];
    }
    return names[0];
  }

  /** 组装 outputPrintting 的文档。
   *
   *  ★★ 结构逐字照抄 2026-09-24 从本机 HMarkService 日志里抓到的 **官方网页真实报文**。
   *     别再照着反编译源码「猜」—— 猜了几十个变体全是 404。与猜测版本的关键差异：
   *       · 根是 PrtLable（不是 LabelData），还带着 ?xml 声明头和 "#comment":[]；
   *       · ObjectList 直接挂在 PrtLable 下、是 **数组**，中间没有 GraphicsList 这一层；
   *       · LabelPage 的 MeasureUnit/LabelShape/Height/Width 是 XML **属性**（@ 前缀），
   *         其余（Rows/Columns/各 Margin/PrinterName/PrintNum…）是子元素；
   *       · AreaSize 与 DrawObject 的宽高用「4 单位/mm」（官方 50×30mm → 200×120）；
   *       · Image 元素里放 **裸 base64 PNG**，不能带 data:image/png;base64, 前缀。
   */
  function hmarkDoc(b64, printer, copies, unitW, unitH, cfg) {
    var wMm = Number(cfg.wMm) || 50;
    var hMm = Number(cfg.hMm) || 30;
    return {
      "?xml": { "@version": "1.0", "@encoding": "utf-8" },
      PrtLable: {
        "#comment": [],
        FileInfo: { Creator: { "@Platform": "Web", "@Version": "V2.6.4" } },
        PictureArea: {
          AreaSize: { "@Width": Math.round(wMm * 4), "@Height": Math.round(hMm * 4) },
          LabelPage: {
            "@MeasureUnit": "Mm",
            "@LabelShape": "Rectangle",
            "@Height": hMm.toFixed(3),
            "@Width": wMm.toFixed(3),
            Rows: 1, Columns: 1, RowSpacing: 0, ColumnSpacing: 0,
            LeftMargin: 0, RightMargin: 0, UpperMargin: 0, LowerMargin: 0,
            LabelWidth: wMm.toFixed(3), LabelHeight: hMm.toFixed(3),
            Background: "", PrintBackground: "False",
            PrinterName: printer,
            PrintNum: Math.max(1, Number(copies) || 1)
          }
        },
        ObjectList: [{
          "@Count": 1, page: 1, row: 1, cloumn: 1,
          DrawObject: [{
            Id: String(Date.now() % 100000000), zOrder: 0, Name: "label",
            OriginalImage: "", Mirror: "None", Inverse: "False", Halftone: "None",
            ISParticipating: "True", ImageFilePath: "", Image: b64,
            StartX: 0, StartY: 0, Width: unitW, Height: unitH, AngleRound: 0,
            Data: null, Type: "Image", Color: "-16777216", PenWidth: 0,
            DashStyle: 0, FillColor: "-16777216", Lock: "False"
          }]
        }]
      }
    };
  }

  /** USB / 驱动打印：把标签 PNG 交给本机汉印服务出纸。 */
  async function labelPrintUsb() {
    if (LABEL.busy) return;
    LABEL.busy = true;
    var ws = null;
    try {
      var cfg = loadCfg();
      var canvas = await labelCanvas();
      var dataUrl = canvas.toDataURL("image/png");
      var b64 = dataUrl.slice(dataUrl.indexOf(",") + 1);
      var dpi = Number(cfg.dpi) || 203;
      var mmPerDot = 25.4 / dpi;
      // 图片绘制尺寸换算成「4 单位/mm」，与官方一致（50mm → 200）
      var unitW = Math.round(canvas.width * mmPerDot * 4);
      var unitH = Math.round(canvas.height * mmPerDot * 4);

      toast("正在连接汉印打印服务…", "ok");
      ws = await hmarkConnect();
      var printers = await hmarkCall(ws, "getComputerPrinters", null, 8000);
      var printer = hmarkPickPrinter(printers.data);
      try { localStorage.setItem("bambu.hmarkPrinter", printer); } catch (e) { /* ignore */ }

      var doc = hmarkDoc(b64, printer, cfg.copies, unitW, unitH, cfg);
      var res = await hmarkCall(ws, "outputPrintting", doc, 60000);
      if (Number(res.code) !== 200) {
        throw new Error("打印失败（code " + res.code + "）：" + (res.data || "无说明"));
      }
      toast("已通过汉印驱动送到 " + printer + "（" + Math.max(1, Number(cfg.copies) || 1) + " 份）", "ok");
    } catch (err) {
      toast(err.message, "err");
    } finally {
      if (ws) { try { ws.close(); } catch (e) { /* ignore */ } }
      LABEL.busy = false;
    }
  }

  function labelA4() {
    const ids = (S.spools || []).map((s) => s.id).join(",");
    window.open("/api/labels/sheet?ids=" + ids, "_blank");
  }

  /* ── 弹窗界面 ───────────────────────────────────────────── */

  async function openLabelDialog(spoolId) {
    // 料盘列表是分页懒加载的：站在仪表盘上时 S.spools 还是空的（只有 S.dashSpools），
    // 不补这一次请求，从仪表盘点「打印标签」会误报「还没有料盘」。
    if (!(S.spools || []).length) {
      try {
        if (typeof loadSpools === "function") await loadSpools();
      } catch (err) {
        /* 拉不到就退回仪表盘那份 */
      }
    }
    let spools = (S.spools || []).filter((s) => !s.archived);
    if (!spools.length) spools = (S.dashSpools || []).filter((s) => !s.archived);
    if (!spools.length) {
      toast("还没有料盘，先添加一盘料", "err");
      return;
    }
    // 用完的料盘（余量 ≤ 0）排到最后：打印标签几乎总是给在用的料打，
    // 0 g 的料盘留在顶部只会天天碍眼（用户 09-24 要求）。
    spools = spools
      .slice()
      .sort((a, b) => (a.remaining_weight > 0 ? 0 : 1) - (b.remaining_weight > 0 ? 0 : 1));
    const cfg = loadCfg();
    if (spoolId) LABEL.spoolId = spoolId;
    if (!LABEL.spoolId || !spools.some((s) => s.id === LABEL.spoolId)) {
      // 默认选中第一个**还有料**的料盘，而不是排在后面的用完料盘
      const first = spools.find((s) => s.remaining_weight > 0) || spools[0];
      LABEL.spoolId = first.id;
    }

    const spoolOptions = spools
      .map(
        (s) =>
          '<option value="' + s.id + '"' + (s.id === LABEL.spoolId ? " selected" : "") + ">" +
          esc(s.name) + "（" + Math.round(s.remaining_weight) + " g）</option>"
      )
      .join("");

    const sizeOptions = LABEL_PRESETS.map(
      (p) =>
        '<option value="' + p.w + "x" + p.h + '"' +
        (p.w === cfg.wMm && p.h === cfg.hMm ? " selected" : "") + ">" +
        p.w + "×" + p.h + " mm</option>"
    ).join("");

    const body =
      '<div class="label-layout">' +
        '<div class="label-form">' +
          '<label class="field"><span>料盘</span><select id="labelSpool" onchange="labelPickSpool(this.value)">' +
            spoolOptions + "</select></label>" +
          '<label class="field"><span>标签尺寸</span><select id="labelSize" onchange="labelPickSize(this.value)">' +
            sizeOptions + '<option value="custom">自定义…</option></select></label>' +
          '<div class="row" id="labelCustom" style="gap:8px;display:none">' +
            '<label class="field"><span>宽 mm</span><input type="number" id="labelW" value="' + cfg.wMm +
              '" min="20" max="80" step="1" onchange="labelPickCustom()" /></label>' +
            '<label class="field"><span>高 mm</span><input type="number" id="labelH" value="' + cfg.hMm +
              '" min="10" max="120" step="1" onchange="labelPickCustom()" /></label>' +
          "</div>" +
          '<label class="field"><span>打印头分辨率</span><select id="labelDpi" onchange="labelPickDpi(this.value)">' +
            '<option value="203"' + (cfg.dpi === 203 ? " selected" : "") + ">203 dpi（8 点/mm）</option>" +
            '<option value="300"' + (cfg.dpi === 300 ? " selected" : "") + ">300 dpi（12 点/mm）</option>" +
          "</select></label>" +
          '<label class="field"><span>份数</span><input type="number" id="labelCopies" min="1" max="50" value="' +
            cfg.copies + '" onchange="labelPickCopies(this.value)" /></label>' +
        "</div>" +
        '<div class="label-side">' +
          '<div id="labelPreviewHost" class="label-preview"></div>' +
          '<div class="tiny muted" id="labelInfo" style="margin-top:6px"></div>' +
        "</div>" +
      "</div>" +
      // 说明与排查收进折叠区（默认收起）。1.0.0 起只剩 USB 一条通道，说明也只剩四条。
      '<details class="label-diag label-help"><summary>操作说明 / 排查（点开）</summary><ul>' +
        "<li><b>怎么打</b>：打印机用 <b>USB 线接这台电脑</b>，电脑上装着汉印官方驱动" +
        "（「汉印 HMark Services」服务在跑），点下面的「<b>USB 打印（驱动）</b>」即可。" +
        "定位/节距由 Windows 打印池 + 汉印驱动负责，实测连打 3 份零串位。</li>" +
        "<li><b>点打印没反应 / 提示连不上服务</b> ⇒ 本机没装汉印官方驱动或服务没起：" +
        "确认装了「汉印 HMark Services」（网页打印插件），打印机 USB 接在本机。" +
        "手机浏览器打不了（服务只在电脑上），手机用「下载标签图」存相册后走汉码 App。</li>" +
        "<li><b>右侧竖线 / 二维码右缘被裁</b> ⇒ 打印头右侧有一段<b>物理死区</b>：标尺图实测 50mm 标签" +
        "只打到 47mm，最后 ~2.8mm 打不出墨（汉印官方样图同样右留 2.91mm 白边）。" +
        "1.0.0 版式右侧留白已自动加上这段（左侧 1.6 + 1.8mm），旧版打的东西别拿来判断版式。</li>" +
        "<li><b>蓝牙打印去哪了</b> ⇒ 1.0.0 起<b>整体删除</b>：这台固件不按垫行走纸、" +
        "FF 走 0，多份内容逐张往上爬，0.12.8~0.12.34 连改十几版没稳住，根因在固件无解。" +
        "USB 驱动通道实测稳定，就不再留蓝牙那条路了。</li>" +
        "<li><b>版本看着旧 / 面板和说明对不上</b>：先 <code>Ctrl+F5</code> 强刷一次，" +
        "再看预览图下面那行的 <code>版本 x.y.z</code>：比最新发布低就说明容器还跑着旧镜像，" +
        "<code>docker compose pull</code> 再 <code>up -d</code>。</li>" +
      "</ul></details>";

    openModal(
      "标签打印",
      body,
      '<button onclick="closeModal()">关闭</button>' +
        '<button onclick="labelA4()">批量 A4 拼版</button>' +
        '<button onclick="labelDownload()">下载标签图</button>' +
        '<button class="primary" onclick="labelPrintUsb()">USB 打印（驱动）</button>',
      true
    );

    labelRefresh();
  }

  function labelPickSpool(value) {
    LABEL.spoolId = parseInt(value, 10) || 0;
    labelRefresh();
  }

  function syncSizeSelect() {
    const cfg = loadCfg();
    const sel = document.getElementById("labelSize");
    const box = document.getElementById("labelCustom");
    if (!sel || !box) return;
    const hit = LABEL_PRESETS.find((p) => p.w === cfg.wMm && p.h === cfg.hMm);
    sel.value = hit ? cfg.wMm + "x" + cfg.hMm : "custom";
    box.style.display = hit ? "none" : "flex";
    const w = document.getElementById("labelW");
    const h = document.getElementById("labelH");
    if (w) w.value = cfg.wMm;
    if (h) h.value = cfg.hMm;
  }

  function labelPickSize(value) {
    const cfg = loadCfg();
    if (value === "custom") {
      syncSizeSelect();
      return;
    }
    const [w, h] = value.split("x").map(Number);
    cfg.wMm = w;
    cfg.hMm = h;
    saveCfg();
    syncSizeSelect();
    labelRefresh();
  }

  function labelPickCustom() {
    const cfg = loadCfg();
    const w = parseFloat((document.getElementById("labelW") || {}).value);
    const h = parseFloat((document.getElementById("labelH") || {}).value);
    if (w >= 20 && w <= 80) cfg.wMm = w;
    if (h >= 10 && h <= 120) cfg.hMm = h;
    saveCfg();
    labelRefresh();
  }

  function labelPickDpi(value) {
    const cfg = loadCfg();
    cfg.dpi = parseInt(value, 10) === 300 ? 300 : 203;
    saveCfg();
    labelRefresh();
  }

  function labelPickCopies(value) {
    const cfg = loadCfg();
    cfg.copies = Math.max(1, Math.min(50, parseInt(value, 10) || 1));
    saveCfg();
  }

  /* ── 导出到全局（onclick 要用） ─────────────────────────── */

  // 无头测试用：把渲染暴露出来，便于在浏览器里直接核对版式结果。
  window.labelDebug = { renderLabel, loadCfg, mm2dot, layoutOf, qrBoxFor, dedupeAgainst, residualName, effHeightMm, rasterRowsFor, runningVersion };

  Object.assign(window, {
    openLabelDialog,
    labelRefresh,
    labelDownload,
    labelPrintUsb,
    labelA4,
    labelPickSpool,
    labelPickSize,
    labelPickCustom,
    labelPickDpi,
    labelPickCopies,
  });
})();
