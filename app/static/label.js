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

  // 4×4 有序抖动矩阵，用来把「耗材颜色深浅」表现成 1 位打印机上可打印的网点
  const BAYER4 = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
  ];

  const LABEL_PRESETS = [
    { w: 40, h: 30 },
    { w: 50, h: 30 },
    { w: 60, h: 40 },
    { w: 50, h: 40 },
  ];

  // 二维码单个模块的目标物理尺寸。太小（<0.3mm）手机难扫，太大占版面。
  // 按它反推「每模块几个点」，而不是按总点宽反推 —— 后者会让二维码的实际
  // 物理尺寸随 dpi 漂移（203dpi 只有 2 点/模块 ≈ 0.25mm，偏小且难扫）。
  const QR_MODULE_MM = 0.34;

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
    ble: { device: null, server: null, char: null, notify: null, chunk: 182, services: [], writes: [] },
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

  function hexToRgb(hex) {
    const s = String(hex || "").replace("#", "").trim();
    if (s.length === 3) {
      return [parseInt(s[0] + s[0], 16), parseInt(s[1] + s[1], 16), parseInt(s[2] + s[2], 16)];
    }
    if (s.length >= 6) {
      return [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)];
    }
    return [128, 128, 128];
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
   *  二维码固定在右下角：右上角留给料盘名，长名字才不会被压到看不清。 */
  function layoutOf(wMm, hMm) {
    return {
      pad: Math.max(1.1, wMm * 0.032),
      swMm: Math.min(hMm * 0.25, wMm * 0.15),
      name: hMm * 0.163,
      sub: hMm * 0.31,
      main: hMm * 0.473,
      loc: hMm * 0.63,
      foot: hMm * 0.9,
    };
  }

  /** 色块：用有序抖动把颜色的深浅画成网点，1 位热敏纸上也能看出「深/浅」。 */
  function drawSwatch(ctx, xMm, yMm, sizeMm, hex, dpi) {
    const x0 = Math.round(mm2dot(xMm, dpi));
    const y0 = Math.round(mm2dot(yMm, dpi));
    const px = Math.max(4, Math.round(mm2dot(sizeMm, dpi)));
    const [r, g, b] = hexToRgb(hex);
    // Rec.709 亮度 → 墨量：颜色越深，网点越密
    const lum = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
    const ink = Math.max(0, Math.min(1, 1 - lum));

    ctx.fillStyle = "#fff";
    ctx.fillRect(x0, y0, px, px);
    ctx.fillStyle = "#000";
    for (let y = 0; y < px; y++) {
      for (let x = 0; x < px; x++) {
        if (BAYER4[y & 3][x & 3] < ink * 16) ctx.fillRect(x0 + x, y0 + y, 1, 1);
      }
    }
    const lw = Math.max(1, Math.round(mm2dot(0.22, dpi)));
    ctx.lineWidth = lw;
    ctx.strokeStyle = "#000";
    ctx.strokeRect(x0 + lw / 2, y0 + lw / 2, px - lw, px - lw);
  }

  /** 写字：超宽先缩字号到 70%，还超就截断加省略号。返回最终画出的文本。 */
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
      while (size > sizeMm * 0.7) {
        size -= 0.1;
        ctx.font = fontAt(size);
        if (ctx.measureText(out).width <= maxDots) break;
      }
      while (out.length > 1 && ctx.measureText(out + "…").width > maxDots) {
        out = out.slice(0, -1);
      }
      if (out !== s) out += "…";
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

  function loadQrImage(spoolId, box) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => resolve(null);
      img.src = "/api/labels/spool/" + spoolId + ".png?box=" + box;
    });
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
    // 倍率由「模块目标物理尺寸」反推；内容特别长导致二维码过大时退回一档再取一次。
    let box = Math.max(2, Math.min(4, Math.round(mm2dot(QR_MODULE_MM, dpi))));
    let qr = await loadQrImage(spool.id, box);
    let qrMm = qr ? qr.naturalWidth / mm2dot(1, dpi) : 0;
    if (qr && qrMm > cfg.wMm * 0.42 && box > 1) {
      box -= 1;
      qr = await loadQrImage(spool.id, box);
      qrMm = qr ? qr.naturalWidth / mm2dot(1, dpi) : 0;
    }
    const qrTopMm = cfg.hMm - L.pad - qrMm;
    if (qr) {
      ctx.drawImage(qr, Math.round(mm2dot(cfg.wMm - L.pad - qrMm, dpi)), Math.round(mm2dot(qrTopMm, dpi)));
    }
    // 与二维码同一水平带的文字必须让开它的左边界
    const lowerMax = (qr ? cfg.wMm - L.pad - qrMm - 0.8 : cfg.wMm - L.pad) - L.pad;

    drawSwatch(ctx, L.pad, L.pad, L.swMm, spool.color_hex, dpi);

    const textX = L.pad + L.swMm + Math.max(0.8, cfg.wMm * 0.032);
    const nameMax = cfg.wMm - L.pad - textX;
    drawText(ctx, dpi, spool.name, textX, L.name, cfg.hMm * 0.11, { bold: true, maxMm: nameMax });

    const parts = [spool.brand, spool.material].filter(Boolean);
    if (spool.finish && spool.finish !== "普通") parts.push(spool.finish);
    const sub = parts.join(" · ");
    drawText(ctx, dpi, sub, textX, L.sub, cfg.hMm * 0.077, { maxMm: nameMax });

    // 余量：左边「余 x / 总」，右边百分比 + 偏低标记
    const remain = Math.round(spool.remaining_weight);
    const initial = Math.round(spool.initial_weight);
    drawText(ctx, dpi, "余 " + remain + " g / " + initial + " g", L.pad, L.main,
      cfg.hMm * 0.103, { bold: true, maxMm: cfg.wMm * 0.6 });
    const pct = Math.round(spool.remaining_percent || 0) + "%";
    drawText(ctx, dpi, (spool.is_low ? "偏低 " : "") + pct, cfg.wMm - L.pad, L.main,
      cfg.hMm * 0.09, { align: "right", bold: spool.is_low, maxMm: cfg.wMm * 0.3 });

    if (spool.location) {
      drawText(ctx, dpi, "位置 " + spool.location, L.pad, L.loc, cfg.hMm * 0.08,
        { maxMm: lowerMax });
    }

    // 编号放在页脚开头（原来贴在二维码上，会压坏码）
    const foot = ["#" + spool.id];
    if (spool.color_name) foot.push(spool.color_name);
    if (spool.color_hex) foot.push(String(spool.color_hex).toUpperCase());
    drawText(ctx, dpi, foot.join(" · "), L.pad, L.foot, cfg.hMm * 0.067, { maxMm: lowerMax });

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
      // ESC d n：走 n 行，把标签送过撕纸口
      parts.push(Uint8Array.from([0x1b, 0x64, Math.max(0, cfg.feed | 0) & 0xff]));
    }
    return concatBytes(parts);
  }

  /* ── 蓝牙 ───────────────────────────────────────────────── */

  function bleState() {
    return LABEL.ble;
  }

  async function bleConnect(showAll) {
    if (!supportsBle()) {
      throw new Error("当前浏览器不支持 Web Bluetooth。请用电脑版 Chrome / Edge，或安卓 Chrome；iPhone 上只能用「下载标签图」。");
    }
    const st = LABEL.ble;
    if (st.char && st.device && st.device.gatt.connected) return st;

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
    const server = await device.gatt.connect();
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

    st.device = device;
    st.server = server;
    st.char = writeChar;
    st.notify = notifyChar;
    st.chunk = writeChar && writeChar.properties.writeWithoutResponse ? 182 : 64;
    st.services = seen;
    st.writes = allWrites.map((c) => c.uuid);
    st.notifyUuid = notifyChar ? notifyChar.uuid : "";

    if (!writeChar) {
      throw new Error("连上了 " + (device.name || "设备") + "，但没找到可写特征。请到「诊断」里看服务列表并反馈。");
    }
    return st;
  }

  async function bleWriteAll(bytes, onProgress) {
    const st = LABEL.ble;
    if (!st.char) throw new Error("蓝牙未连接");
    const useNoResp = !!st.char.properties.writeWithoutResponse;
    let size = st.chunk;
    let sent = 0;
    const parts = [];
    while (sent < bytes.length) {
      const end = Math.min(sent + size, bytes.length);
      const chunk = bytes.subarray(sent, end);
      try {
        if (useNoResp) await st.char.writeValueWithoutResponse(chunk);
        else await st.char.writeValue(chunk);
      } catch (err) {
        // 多半是单包超了链路 MTU，减半重试
        if (size > 24) {
          size = Math.max(24, Math.floor(size / 2));
          st.chunk = size;
          parts.push("分包降到 " + size + " 字节重试");
          continue;
        }
        throw err;
      }
      sent = end;
      if (onProgress) onProgress(sent, bytes.length);
      // 无应答写入没有流控，节奏太快打印机会丢数据
      if (useNoResp) await sleep(12);
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

  function bleDisconnect() {
    const st = LABEL.ble;
    try {
      if (st.device && st.device.gatt.connected) st.device.gatt.disconnect();
    } catch (err) {
      /* 已经断了就算了 */
    }
    LABEL.ble = {
      device: null, server: null, char: null, notify: null,
      chunk: 182, services: [], writes: [],
    };
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
      labelProgress("正在渲染标签…");
      const canvas = await labelCanvas();
      const raster = packRaster(canvas, cfg.density);
      const job = buildEscPosJob(raster, cfg);
      const started = Date.now();
      const notes = await bleWriteAll(job, (sent, total) => {
        labelProgress("正在发送 " + Math.round((sent / total) * 100) + "%（" + sent + "/" + total + " 字节）");
      });
      const secs = ((Date.now() - started) / 1000).toFixed(1);
      labelProgress(
        "已发送 " + job.length + " 字节，用时 " + secs + " 秒，分包 " + LABEL.ble.chunk + " 字节" +
        (notes.length ? "；" + notes.join("；") : "")
      );
      toast("标签已发送到 " + (LABEL.ble.device.name || "打印机"), "ok");
      renderBlePanel();
    } catch (err) {
      labelProgress("失败：" + err.message);
      toast(err.message, "err");
    } finally {
      LABEL.busy = false;
    }
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
  window.labelDebug = { renderLabel, packRaster, buildEscPosJob, loadCfg, mm2dot };

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
