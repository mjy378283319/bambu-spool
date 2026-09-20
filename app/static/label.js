/* ══════════════════════════════════════════════════════════════════
 * 标签打印：渲染 → ESC/POS 光栅 → Web Bluetooth 直发（或导出 PNG）
 * ══════════════════════════════════════════════════════════════════
 *
 * 为什么在浏览器里渲染而不是服务端：
 *   容器镜像 python:3.12-slim 没有中文字体，服务端画中文要额外装 ~5MB 字体包；
 *   浏览器 Canvas 直接用系统字体，中文天然可用，而且预览就是最终效果。
 *   同一张位图既能导出 PNG（存手机 → 汉码 App 放图片打印），
 *   也能就地打包成 ESC/POS 光栅指令经蓝牙直接发给打印机。
 *
 * 关于汉印 T260LR（用户机型）：
 *   官方规格里它的仿真协议是「Hanma print Protocol」（汉码私有协议），不是 TSPL/CPCL，
 *   驱动/工具栏 N/A，通信接口只有蓝牙（USB-C 仅充电），也不支持云打印。
 *   但官方知识库的故障排查页给过真实指令：
 *       1d 73 65 74 70 01   ← GS "setp" 01  切到标签纸模式
 *       1d 73 65 74 4c      ← GS "setL"     间隙学习/校准
 *   0x1d 就是 ESC/POS 的 GS，说明它是 ESC/POS 派生指令集。
 *   所以这里按 ESC/POS 标准光栅指令 GS v 0 整张贴图打印；
 *   若这台机器不吃这套指令，用下面的「诊断」看原始收发，再按实际协议调。
 *
 * 已知限制：
 *   Web Bluetooth 只在 Chrome / Edge（桌面 + Android）上有；
 *   iOS Safari 完全不支持，iPhone 上只能用「下载标签图」这条路。
 *   另外 Web Bluetooth 要求安全上下文（HTTPS 或 localhost），
 *   用 http://192.168.x.x:8971 打开时按钮会是灰的。
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

  // 已知的热敏打印机 BLE 服务。ff00 是 Marklife/Phomemo/汉印 HM300L 那一系，
  // 18f0 是 WebBluetoothCG 示例里的打印服务，ffe0/fff0 是常见透传服务。
  const BLE_SERVICES = [
    "0000ff00-0000-1000-8000-00805f9b34fb",
    "0000ffe0-0000-1000-8000-00805f9b34fb",
    "0000fff0-0000-1000-8000-00805f9b34fb",
    "0000ff80-0000-1000-8000-00805f9b34fb",
    "000018f0-0000-1000-8000-00805f9b34fb",
    "0000ff90-0000-1000-8000-00805f9b34fb",
    "e7810a71-73ae-499d-8c15-faa9aef0c3f2",
    "49535343-fe7d-4ae5-8fa9-9fafd205e455",
  ];

  // 优先尝试的写特征（对应上面服务的写通道）
  const BLE_WRITE_CHARS = [
    "0000ff02-0000-1000-8000-00805f9b34fb",
    "00002af1-0000-1000-8000-00805f9b34fb",
    "0000ffe1-0000-1000-8000-00805f9b34fb",
    "0000fff2-0000-1000-8000-00805f9b34fb",
    "0000ff01-0000-1000-8000-00805f9b34fb",
    "0000ff91-0000-1000-8000-00805f9b34fb",
    "49535343-8841-43f4-a8d4-ecbe34729bb3",
  ];

  const LS_KEY = "bambu.label.cfg";

  const LABEL = {
    cfg: null,
    spoolId: 0,
    ble: { device: null, server: null, char: null, notify: null, chunk: 20, services: [], writes: [] },
    busy: false,
    progress: "",
    probeLog: [],
    renderToken: 0,
  };

  /* ── 小工具 ─────────────────────────────────────────────── */

  function mm2dot(mm, dpi) {
    return (mm / 25.4) * dpi;
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  function concatBytes(parts) {
    let total = 0;
    for (const p of parts) total += p.length;
    const out = new Uint8Array(total);
    let at = 0;
    for (const p of parts) {
      out.set(p, at);
      at += p.length;
    }
    return out;
  }

  function bytesToHex(bytes) {
    return Array.from(bytes)
      .map((b) => b.toString(16).padStart(2, "0"))
      .join(" ");
  }

  function parseHex(text) {
    const clean = String(text || "").replace(/0x/gi, " ").replace(/[^0-9a-fA-F]/g, " ").trim();
    if (!clean) return new Uint8Array(0);
    const parts = clean.split(/\s+/).filter(Boolean);
    // 允许「1b40」这种连写：长度为偶数且没有空格时按两字符一组切
    const tokens = parts.length === 1 && parts[0].length > 2 && parts[0].length % 2 === 0
      ? parts[0].match(/../g)
      : parts;
    const out = [];
    for (const t of tokens) {
      const v = parseInt(t, 16);
      if (!Number.isNaN(v)) out.push(v & 0xff);
    }
    return Uint8Array.from(out);
  }

  function supportsBle() {
    return typeof navigator !== "undefined" && !!navigator.bluetooth;
  }

  /* ── 配置 ───────────────────────────────────────────────── */

  function defaultCfg() {
    return { wMm: 50, hMm: 30, dpi: 203, density: 4, copies: 1, feed: 2, showAll: false };
  }

  function loadCfg() {
    if (LABEL.cfg) return LABEL.cfg;
    const cfg = defaultCfg();
    try {
      const raw = localStorage.getItem(LS_KEY);
      if (raw) Object.assign(cfg, JSON.parse(raw));
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
    return {
      pad: Math.max(1.1, wMm * 0.032),
      top: hMm * 0.155,  // 第一行文字基线
      foot: hMm * 0.91,  // 页脚基线（固定在最下面，不参与均分）
    };
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

  /** 画一张料盘标签。返回 canvas（尺寸 = 标签实际点数）。 */
  async function renderLabel(spool, cfg) {
    const dpi = cfg.dpi;
    const wDots = Math.max(8, Math.round(mm2dot(cfg.wMm, dpi)));
    const hDots = Math.max(8, Math.round(mm2dot(cfg.hMm, dpi)));
    const canvas = document.createElement("canvas");
    canvas.width = wDots;
    canvas.height = hDots;

    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, wDots, hDots);

    const L = layoutOf(cfg.wMm, cfg.hMm);

    // 二维码：服务端按整数倍模块出图，这里 1:1 贴上去，绝不缩放。
    // 先用 box=4 探出模块数（模块数只跟内容/静区有关，跟 box 无关），
    // 再由「想要多大」反推倍率，取不超过目标尺寸的最大整数倍率。
    const probe = await loadQrImage(spool.id, 4);
    const modules = probe ? Math.round(probe.naturalWidth / 4) : 0;
    const padDots = mm2dot(L.pad, dpi);
    const targetDots = Math.min(wDots * QR_WIDTH_RATIO, hDots - padDots * 2);
    const box = qrBoxFor(targetDots, modules);
    const qr = (probe && box === 4 ? probe : await loadQrImage(spool.id, box)) || probe;
    const qrDots = qr ? qr.naturalWidth : 0;
    const qrMm = qrDots / mm2dot(1, dpi);
    if (qr) {
      ctx.drawImage(qr, wDots - Math.round(padDots) - qrDots, Math.round(padDots));
    }
    // 文字列的右边界：让开二维码
    const textMax = (qr ? cfg.wMm - L.pad - qrMm - 0.8 : cfg.wMm - L.pad) - L.pad;

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

    const topBase = L.top;
    const bottomBase = L.foot - cfg.hMm * 0.115; // 最后一行与页脚之间留一行字高的空
    const n = rows.length;
    rows.forEach((row, i) => {
      const y = n > 1 ? topBase + ((bottomBase - topBase) * i) / (n - 1) : topBase;
      drawText(ctx, dpi, String(row.text), textX, y, cfg.hMm * row.size,
        { bold: !!row.bold, maxMm: textMax });
    });

    // 页脚：编号 + 色值；颜色名只在名字里没写时才补上（否则又是重复）
    const foot = ["#" + spool.id, ...dedupeAgainst(name, [spool.color_name])];
    if (spool.color_hex) foot.push(String(spool.color_hex).toUpperCase());
    drawText(ctx, dpi, foot.join(" · "), textX, L.foot, cfg.hMm * 0.062, { maxMm: textMax });

    return canvas;
  }

  /* ── 位图打包 ───────────────────────────────────────────── */

  /** canvas → 1 位光栅。返回行宽（字节）与 MSB-first 的位数据。 */
  function packRaster(canvas, density) {
    const w = canvas.width;
    const h = canvas.height;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    const img = ctx.getImageData(0, 0, w, h).data;

    // 浓度 1..8 → 阈值 126..182。阈值越高越多像素判成黑，打出来越浓。
    const thr = 118 + Math.max(1, Math.min(8, density)) * 8;
    const bytesPerRow = Math.ceil(w / 8);
    const out = new Uint8Array(bytesPerRow * h);

    for (let y = 0; y < h; y++) {
      const rowAt = y * bytesPerRow;
      const srcAt = y * w * 4;
      for (let x = 0; x < w; x++) {
        const i = srcAt + x * 4;
        // Rec.709 亮度；白底黑字，低于阈值记 1（黑）
        const lum = 0.2126 * img[i] + 0.7152 * img[i + 1] + 0.0722 * img[i + 2];
        if (lum < thr) out[rowAt + (x >> 3)] |= 0x80 >> (x & 7);
      }
    }
    return { bytes: out, widthDots: w, heightDots: h, bytesPerRow };
  }

  /** 组装 ESC/POS 作业：初始化 → 标签纸模式 → 光栅 → 走纸。 */
  function buildEscPosJob(raster, cfg) {
    const parts = [];
    parts.push(Uint8Array.from([0x1b, 0x40])); // ESC @ 复位
    // GS "setp" 01 —— 官方知识库给的「标签纸设置指令」，切到间隙标签模式
    parts.push(Uint8Array.from([0x1d, 0x73, 0x65, 0x74, 0x70, 0x01]));

    const copies = Math.max(1, Math.min(50, cfg.copies || 1));
    for (let c = 0; c < copies; c++) {
      parts.push(
        Uint8Array.from([
          0x1d, 0x76, 0x30, 0x00, // GS v 0 m=0 光栅位图
          raster.bytesPerRow & 0xff, (raster.bytesPerRow >> 8) & 0xff,
          raster.heightDots & 0xff, (raster.heightDots >> 8) & 0xff,
        ])
      );
      parts.push(raster.bytes);
      // FF (0x0c)：间隙走纸到下一标签起点。
      // 汉印官方多张连打抓包确认：连打不串位的关键就是每张结尾发 FF 而非 ESC d n。
      // ESC d n 是固定行数进给，对不准标签间距会逐张累积漂移；FF 在间隙标签模式下
      // 走纸到下一个标签起点，所以汉码一次连打多张都不偏。
      parts.push(Uint8Array.from([0x0c]));
    }
    return concatBytes(parts);
  }

  /* ── 蓝牙 ───────────────────────────────────────────────── */

  function bleState() {
    return LABEL.ble;
  }

  // 给一个 promise 套超时：到点直接 reject，避免 Windows BLE 上 writeValue 永久挂起把 LABEL.busy 锁死
  function withTimeout(p, ms, msg) {
    return new Promise((resolve, reject) => {
      const t = setTimeout(() => reject(new Error(msg)), ms);
      p.then(
        (v) => { clearTimeout(t); resolve(v); },
        (e) => { clearTimeout(t); reject(e); }
      );
    });
  }

  // 无感重连：已有 device 引用时不重新弹窗。Windows 上 gatt.connected 可能是僵尸(true 但链路已死)，
  // 这种情况由「发送失败后的重试路径」强制 disconnect 处理，这里只在明确未连时才 connect。
  async function ensureConnected(device) {
    if (device.gatt.connected) return device.gatt; // 信任健康连接
    return await withTimeout(device.gatt.connect(), 8000, "蓝牙连接超时");
  }

  // 重新枚举服务/特征并写回 LABEL.ble。连接重建后必须重枚举，否则拿到的是死特征。
  async function negotiate(device, server) {
    const services = await server.getPrimaryServices();
    const seen = [];
    let writeChar = null;
    let notifyChar = null;
    const allWrites = [];

    for (const svc of services) {
      const chars = await svc.getCharacteristics();
      const row = { uuid: svc.uuid, chars: [] };
      for (const ch of chars) {
        const props = ch.properties || {};
        row.chars.push({
          uuid: ch.uuid,
          write: !!props.write,
          writeNoResp: !!props.writeWithoutResponse,
          notify: !!props.notify || !!props.indicate,
        });
        if (props.write || props.writeWithoutResponse) allWrites.push(ch);
        if (props.notify || props.indicate) notifyChar = notifyChar || ch;
      }
      seen.push(row);
    }

    for (const want of BLE_WRITE_CHARS) {
      const found = allWrites.find((c) => c.uuid.toLowerCase() === want.toLowerCase());
      if (found) {
        writeChar = found;
        break;
      }
    }
    if (!writeChar) writeChar = allWrites[0] || null;

    const st = LABEL.ble;
    st.device = device;
    st.server = server;
    st.char = writeChar;
    st.notify = notifyChar;
    // 优先应答写入（有流控、失败可感知、浏览器按 MTU 自动分包）；不支持才退回无应答 20 字节
    st.chunk = writeChar && writeChar.properties.write ? 182 : 20;
    st.services = seen;
    st.writes = allWrites.map((c) => c.uuid);
    st.notifyUuid = notifyChar ? notifyChar.uuid : "";

    if (!writeChar) {
      throw new Error("连上了 " + (device.name || "设备") + "，但没找到可写特征。请到「诊断」里看服务列表并反馈。");
    }
    return st;
  }

  async function bleConnect(showAll) {
    if (!supportsBle()) {
      throw new Error("当前浏览器不支持 Web Bluetooth。请用电脑版 Chrome / Edge，或安卓 Chrome；iPhone 上只能用「下载标签图」。");
    }
    const st = LABEL.ble;
    // 已有配对设备：优先无感重连（不重新弹窗）。只有真正断开/首次才 requestDevice。
    if (st.device && st.device.gatt) {
      if (st.char && st.device.gatt.connected) return st; // 健康连接直接复用，不重连（避免每次打印都断链）
      try {
        const server = await ensureConnected(st.device);
        return await negotiate(st.device, server);
      } catch (e) {
        // 重连失败，落到下面的重新配对
      }
    }
    // 重新配对
    LABEL.ble = {
      device: null, server: null, char: null, notify: null,
      chunk: 20, services: [], writes: [],
    };
    const opts = showAll
      ? { acceptAllDevices: true, optionalServices: BLE_SERVICES }
      : {
          filters: [
            { namePrefix: "HM-" },
            { namePrefix: "T260" },
            { namePrefix: "HPRT" },
            { namePrefix: "HereLabel" },
          ],
          optionalServices: BLE_SERVICES,
        };

    const device = await navigator.bluetooth.requestDevice(opts);
    device.addEventListener("gattserverdisconnected", onGattDisconnected);
    const server = await withTimeout(device.gatt.connect(), 8000, "蓝牙连接超时");
    return await negotiate(device, server);
  }

  async function bleWriteAll(bytes, onProgress) {
    const st = LABEL.ble;
    if (!st.char) throw new Error("蓝牙未连接");
    const char = st.char;
    const useAck = !!char.properties.write;              // 优先应答写入：有流控、失败可感知
    const useNoResp = !useAck && !!char.properties.writeWithoutResponse;
    if (!useAck && !useNoResp) throw new Error("特征不支持写入");
    const size = useAck ? 182 : 20;                      // 应答写由浏览器按 MTU 分包；无应答写必须 ≤ MTU(20)
    let sent = 0;
    const parts = [];
    while (sent < bytes.length) {
      const end = Math.min(sent + size, bytes.length);
      const chunk = bytes.subarray(sent, end);
      try {
        if (useAck) {
          // 套 6s 超时：Windows BLE 上某包 writeValue 可能永远不回，不超时就会把 LABEL.busy 锁死成「卡死」
          const w = char.writeValue(chunk);
          w.catch(() => {});                             // 超时后底层 reject 静默化，避免 unhandled rejection
          await withTimeout(w, 6000, "蓝牙写入超时");
        } else {
          await char.writeValueWithoutResponse(chunk);
        }
      } catch (err) {
        // 无应答写单包超长：降到 20 字节兜底重试
        if (!useAck && size > 20) { size = 20; parts.push("无应答写超长，改 20 字节分包"); continue; }
        throw err;
      }
      sent = end;
      if (onProgress) onProgress(sent, bytes.length);
      if (useNoResp) await sleep(20);                     // 无应答写无流控，≥20ms 才稳
    }
    return parts;
  }

  async function bleSendRaw(bytes, label) {
    const st = LABEL.ble;
    if (!st.char) throw new Error("蓝牙未连接");
    const notices = [];
    if (st.notify) {
      st.notify.addEventListener("characteristicvaluechanged", function onEvt(evt) {
        notices.push(bytesToHex(new Uint8Array(evt.target.value.buffer)));
        st.notify.removeEventListener("characteristicvaluechanged", onEvt);
      });
      try {
        await st.notify.startNotifications();
      } catch (err) {
        notices.push("（订阅通知失败：" + err.message + "）");
      }
    }
    await bleWriteAll(bytes);
    if (st.notify) await sleep(900);
    LABEL.probeLog.unshift({
      at: new Date().toLocaleTimeString("zh-CN"),
      what: label || "原始指令",
      sent: bytesToHex(bytes),
      recv: notices.length ? notices.join(" | ") : "无回执",
    });
    LABEL.probeLog = LABEL.probeLog.slice(0, 8);
    return notices;
  }

  function bleDisconnect(keepDevice) {
    const st = LABEL.ble;
    const dev = st.device;
    try {
      if (st.device && st.device.gatt && st.device.gatt.connected) st.device.gatt.disconnect();
    } catch (err) {
      /* 已经断了就算了 */
    }
    LABEL.ble = {
      // keepDevice=true：保留 device 引用，让重试路径走「无感重连」而不是重新弹窗配对
      device: keepDevice ? (dev || null) : null,
      server: null, char: null, notify: null,
      chunk: 20, services: [], writes: [],
    };
    renderBlePanel();
  }

  // 物理断电 / 系统空闲掉链：清空状态，下次连接重新枚举，避免卡在僵尸连接上
  function onGattDisconnected() {
    LABEL.ble = {
      device: null, server: null, char: null, notify: null,
      chunk: 20, services: [], writes: [],
    };
    if (typeof renderBlePanel === "function") renderBlePanel();
    toast("打印机已断开，请重新连接", "err");
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
      const raster = packRaster(canvas, cfg.density);
      const info = document.getElementById("labelInfo");
      if (info) {
        const bytes = raster.bytesPerRow * raster.heightDots;
        info.textContent =
          Math.round(cfg.wMm) + "×" + Math.round(cfg.hMm) + " mm · " + cfg.dpi + " dpi · " +
          raster.widthDots + "×" + raster.heightDots + " 点 · " + bytes + " 字节" +
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

  async function labelPrintBle() {
    if (LABEL.busy) return;
    LABEL.busy = true;
    try {
      const cfg = loadCfg();
      labelProgress("正在连接蓝牙…");
      await bleConnect(cfg.showAll);
      const canvas = await labelCanvas();
      const raster = packRaster(canvas, cfg.density);
      const job = buildEscPosJob(raster, cfg);
      try {
        await sendJob(job);
      } catch (err) {
        // 发送中途链路断了（Windows 僵尸连接 / 蓝牙掉线）→ 强制真实断开、保留设备引用，
        // 走无感重连后整份重发一次。ESC @ 会在打印机端复位，整份重发是安全的。
        labelProgress("发送中断，正在重建链路重试…");
        const dev = LABEL.ble.device;
        try {
          if (dev && dev.gatt) {
            const d = dev.gatt.disconnect();
            if (d && typeof d.catch === "function") d.catch(() => {});
          }
        } catch (e) { /* ignore */ }
        await sleep(300);
        bleDisconnect(true); // 保留 device，下次 bleConnect 无感重连（不重新弹窗）
        await bleConnect(cfg.showAll);
        const canvas2 = await labelCanvas();
        const raster2 = packRaster(canvas2, cfg.density);
        await sendJob(buildEscPosJob(raster2, cfg));
      }
      toast("标签已发送到 " + (LABEL.ble.device.name || "打印机"), "ok");
      renderBlePanel();
    } catch (err) {
      labelProgress("失败：" + err.message);
      toast(err.message, "err");
    } finally {
      LABEL.busy = false;
    }
  }

  async function sendJob(job) {
    const started = Date.now();
    const notes = await bleWriteAll(job, (sent, total) => {
      labelProgress("正在发送 " + Math.round((sent / total) * 100) + "%（" + sent + "/" + total + " 字节）");
    });
    const secs = ((Date.now() - started) / 1000).toFixed(1);
    labelProgress(
      "已发送 " + job.length + " 字节，用时 " + secs + " 秒，分包 " + LABEL.ble.chunk + " 字节" +
      (notes.length ? "；" + notes.join("；") : "")
    );
  }

  async function labelBleProbe() {
    try {
      await bleConnect(loadCfg().showAll);
      if (!LABEL.ble.notify) {
        LABEL.probeLog.unshift({
          at: new Date().toLocaleTimeString("zh-CN"),
          what: "状态查询",
          sent: "10 04 04",
          recv: "该设备没有可通知的特征，无法读回执",
        });
      } else {
        await bleSendRaw(parseHex("10 04 04"), "状态查询 DLE EOT 4");
      }
      renderBlePanel();
    } catch (err) {
      toast(err.message, "err");
    }
  }

  async function labelBleCalibrate() {
    try {
      await bleConnect(loadCfg().showAll);
      // 官方知识库：1d 73 65 74 4c = GS "setL"，间隙/黑标学习
      await bleSendRaw(parseHex("1D 73 65 74 4C"), "间隙学习（GS setL）");
      toast("已下发间隙学习指令，打印机会走一段纸做定位", "ok");
      renderBlePanel();
    } catch (err) {
      toast(err.message, "err");
    }
  }

  async function labelBleRaw() {
    const box = document.getElementById("labelRawHex");
    if (!box) return;
    try {
      await bleConnect(loadCfg().showAll);
      const bytes = parseHex(box.value);
      if (!bytes.length) throw new Error("没有可发送的字节");
      await bleSendRaw(bytes, "手动原始指令");
      renderBlePanel();
      toast("已发送 " + bytes.length + " 字节", "ok");
    } catch (err) {
      toast(err.message, "err");
    }
  }

  function labelBleDisconnect() {
    bleDisconnect();
    renderBlePanel();
    toast("已断开蓝牙", "ok");
  }

  function labelA4() {
    const ids = (S.spools || []).map((s) => s.id).join(",");
    window.open("/api/labels/sheet?ids=" + ids, "_blank");
  }

  /* ── 弹窗界面 ───────────────────────────────────────────── */

  function labelProgress(msg) {
    LABEL.progress = msg;
    const el = document.getElementById("labelBleStatus");
    if (el) el.textContent = msg;
  }

  function renderBlePanel() {
    const host = document.getElementById("labelBlePanel");
    if (!host) return;
    const st = LABEL.ble;
    const connected = !!(st.char && st.device && st.device.gatt && st.device.gatt.connected);

    const svcRows = st.services
      .map(
        (s) =>
          "<li><code>" + esc(s.uuid) + "</code><br>" +
          s.chars
            .map(
              (c) =>
                "&nbsp;&nbsp;<code>" + esc(c.uuid) + "</code> " +
                (c.write ? '<span class="tag teal">write</span>' : "") +
                (c.writeNoResp ? '<span class="tag teal">writeNoResp</span>' : "") +
                (c.notify ? '<span class="tag">notify</span>' : "")
            )
            .join("<br>") +
          "</li>"
      )
      .join("");

    const logRows = LABEL.probeLog
      .map(
        (r) =>
          "<li><b>" + esc(r.at) + "</b> " + esc(r.what) +
          '<div class="tiny muted">发送：' + esc(r.sent) + "</div>" +
          '<div class="tiny muted">回执：' + esc(r.recv) + "</div></li>"
      )
      .join("");

    host.innerHTML =
      '<div class="row" style="gap:8px;flex-wrap:wrap;align-items:center">' +
        '<span class="dot ' + (connected ? "ok" : "bad") + '"></span>' +
        "<span class=\"small\">" +
          (connected
            ? esc(st.device.name || "未命名设备") + " 已连接"
            : "未连接") +
        "</span>" +
        '<span class="spacer"></span>' +
        (connected
          ? '<button class="sm" onclick="labelBleDisconnect()">断开</button>'
          : '<button class="sm" onclick="labelBleConnect()">连接打印机</button>') +
      "</div>" +
      (connected
        ? '<div class="small muted" style="margin-top:6px">写特征 <code>' + esc(st.char.uuid) +
          "</code> · 分包 " + st.chunk + " 字节 · 服务 " + st.services.length + " 个</div>"
        : "") +
      '<div class="label-ble-tests">' +
        '<button class="sm" onclick="labelBleProbe()">查询状态（不耗纸）</button>' +
        '<button class="sm" onclick="labelBleCalibrate()">间隙学习（走一段纸）</button>' +
      "</div>" +
      '<label class="field" style="margin-top:10px"><span>原始指令（十六进制）</span>' +
        '<input id="labelRawHex" placeholder="例如 1B 40" /></label>' +
      '<button class="sm" onclick="labelBleRaw()">发送原始指令</button>' +
      (svcRows ? '<details class="label-diag"><summary>发现的服务与特征</summary><ul>' + svcRows + "</ul></details>" : "") +
      (logRows ? '<details class="label-diag" open><summary>收发记录</summary><ul>' + logRows + "</ul></details>" : "");
  }

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
    const cfg = loadCfg();
    if (spoolId) LABEL.spoolId = spoolId;
    if (!LABEL.spoolId || !spools.some((s) => s.id === LABEL.spoolId)) {
      LABEL.spoolId = spools[0].id;
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
          '<label class="field"><span>浓度</span><input type="range" id="labelDensity" min="1" max="8" value="' +
            cfg.density + '" oninput="labelPickDensity(this.value)" /></label>' +
          '<label class="field"><span>份数</span><input type="number" id="labelCopies" min="1" max="50" value="' +
            cfg.copies + '" onchange="labelPickCopies(this.value)" /></label>' +
          '<label class="field check"><input type="checkbox" id="labelShowAll"' +
            (cfg.showAll ? " checked" : "") + ' onchange="labelPickShowAll(this.checked)" />' +
            "<span>蓝牙列表显示全部设备（找不到打印机时勾上）</span></label>" +
        "</div>" +
        '<div class="label-side">' +
          '<div id="labelPreviewHost" class="label-preview"></div>' +
          '<div class="tiny muted" id="labelInfo" style="margin-top:6px"></div>' +
          '<div class="small" id="labelBleStatus" style="margin-top:8px"></div>' +
          '<div class="card" style="margin-top:10px;padding:10px"><div id="labelBlePanel"></div></div>' +
        "</div>" +
      "</div>" +
      '<p class="hint">汉印 T260LR 用的是私有「汉码协议」，这台机器没网口、USB 只充电，' +
      "所以只能走蓝牙。打印原理是把整张标签当位图用 ESC/POS 光栅指令 <code>GS v 0</code> 发过去" +
      "（官方知识库的校准指令 <code>1D 73 65 74 4C</code> 也是 ESC/POS 派生，所以这套大概率可用）。" +
      "要是打不出内容，先点「查询状态」看有没有回执：有回执说明链路通，可调浓度或换尺寸重试；" +
      "完全没回执则是指令集不匹配，「收发记录」里能看到实际发出的字节，" +
      "也可以在那里用「原始指令」手工试协议。</p>";

    openModal(
      "标签打印",
      body,
      '<button onclick="closeModal()">关闭</button>' +
        '<button onclick="labelA4()">批量 A4 拼版</button>' +
        '<button onclick="labelDownload()">下载标签图</button>' +
        '<button class="primary" onclick="labelPrintBle()">蓝牙打印</button>',
      true
    );

    renderBlePanel();
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

  function labelPickDensity(value) {
    const cfg = loadCfg();
    cfg.density = Math.max(1, Math.min(8, parseInt(value, 10) || 4));
    saveCfg();
    labelRefresh();
  }

  function labelPickCopies(value) {
    const cfg = loadCfg();
    cfg.copies = Math.max(1, Math.min(50, parseInt(value, 10) || 1));
    saveCfg();
  }

  function labelPickShowAll(checked) {
    const cfg = loadCfg();
    cfg.showAll = !!checked;
    saveCfg();
  }

  /* ── 导出到全局（onclick 要用） ─────────────────────────── */

  // 无头测试用：把渲染与打包暴露出来，便于在浏览器里直接核对 1 位位图结果。
  // 只读、不改状态，留着对排查打印问题是真有帮助。
  window.labelDebug = { renderLabel, packRaster, buildEscPosJob, loadCfg, mm2dot, layoutOf, qrBoxFor, dedupeAgainst, residualName };

  Object.assign(window, {
    openLabelDialog,
    labelRefresh,
    labelDownload,
    labelPrintBle,
    labelBleProbe,
    labelBleCalibrate,
    labelBleRaw,
    labelBleDisconnect,
    labelBleConnect: async function () {
      try {
        await bleConnect(loadCfg().showAll);
        renderBlePanel();
        toast("蓝牙已连接", "ok");
      } catch (err) {
        toast(err.message, "err");
      }
    },
    labelA4,
    labelPickSpool,
    labelPickSize,
    labelPickCustom,
    labelPickDpi,
    labelPickDensity,
    labelPickCopies,
    labelPickShowAll,
  });
})();
