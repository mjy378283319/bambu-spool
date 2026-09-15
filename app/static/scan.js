/* 手机扫码：料盘二维码 / 槽位二维码。
 *
 * 最早的做法是「把光标放进输入框，用扫码枪扫」—— 那是给桌面 + USB 扫码枪设计的，
 * 手机上根本没有键盘，这个输入框等于死的（用户原话：「什么手机浏览器无法扫码，
 * 在槽位里不能扫码」）。于是补上真正的相机扫码；后来用户确认扫码枪用不到，
 * 那个输入框也删掉了，这里成了唯一的扫码入口。
 *
 * 三层降级，尽量让每台手机都能用：
 *   1. BarcodeDetector + 实时相机：安卓 Chrome 有原生解码器，最省电最快；
 *   2. jsQR + 实时相机：iOS Safari 等没有 BarcodeDetector 的浏览器，
 *      自己逐帧解码（jsQR 已本地化到 static/vendor/jsQR.js，不依赖外网 CDN）；
 *   3. 拍一张照片再解码：http 页面拿不到 getUserMedia（浏览器只允许在 HTTPS
 *      或 localhost 下开相机），但 <input capture> 是调系统相机 App，不受这个限制，
 *      所以「拍一张」在内网 http 部署下反而是唯一能用的那条路。
 *
 * 三层都不行时不能只丢一句「不支持」：要把原因说清楚（没 HTTPS / 没权限 / 没摄像头），
 * 并把用户留在手动输入上，别让人卡在一个按了没反应的按钮前面。
 */
(function () {
  "use strict";

  const LIVE_MAX_WIDTH = 640;   // 逐帧解码的取样宽度：再大只是白烧电
  const PHOTO_MAX_WIDTH = 1200; // 单张照片可以给大一点，识别率优先
  const FRAME_INTERVAL = 120;   // ≈8 帧/秒，够快也够省

  /* ── 从扫码文本里认出「这是什么码」 ──────────────────────
   * 本系统自己生成的二维码内容是（见 app/api/routes.py）：
   *   料盘码  <base>/#spool=<id>
   *   槽位码  <base>/#bind=<printer>:<ams>:<tray>
   * 但用户也可能扫到别人家的码、或者只拿到一个裸数字，所以这里放宽：
   * 纯数字当料盘号，带 #spool= / #bind= 的取参数（? 或 & 开头也认）。 */
  function parseScan(text) {
    const s = String(text == null ? "" : text).trim();
    if (!s) return null;
    let m = s.match(/[#&?]bind=(-?\d+):(-?\d+):(-?\d+)/);
    if (m) return { kind: "bind", printer: +m[1], ams: +m[2], tray: +m[3] };
    m = s.match(/[#&?]spool=(\d+)/);
    if (m) return { kind: "spool", id: +m[1] };
    m = s.match(/^(\d{1,9})$/);
    if (m) return { kind: "spool", id: +m[1] };
    return null;
  }

  function canUseCamera() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  }

  /** 当前环境为什么开不了相机 —— 直接写给人看，别只说「不支持」。 */
  function cameraBlockReason() {
    if (!window.isSecureContext) {
      return "手机浏览器只在 HTTPS（或 localhost）下才允许网页开相机。"
        + "当前是 http 地址，请用「拍照识别」，或者给服务配上 HTTPS 反向代理。";
    }
    if (!canUseCamera()) {
      return "这个浏览器不提供网页相机接口，请用「拍照识别」，或改用 Chrome / Safari。";
    }
    return "";
  }

  /** 相机被拒时，替用户判断出「到底是哪一层拦的」。
   *
   *  手机上的相机权限有两层，任何一层没开，网页拿到的都是同一句 NotAllowedError：
   *    ① 站点层：浏览器把这个站点的相机记成了「已阻止」；
   *    ② 应用层：系统没把相机权限给浏览器这个 App 本身。
   *  前两版只丢一句「去站点设置里允许相机」，人照着改完还是不行 —— 因为拦他的
   *  其实是另一层。手机浏览器又没有控制台可看，所以这里用 permissions.query
   *  把两层分开，把该点哪里直接写进提示里。 */
  async function cameraDeniedHint(err) {
    const name = (err && err.name) || "";
    const code = name ? `（错误码 ${name}）` : "";
    let site = "";
    try {
      if (navigator.permissions && navigator.permissions.query) {
        const status = await navigator.permissions.query({ name: "camera" });
        site = (status && status.state) || "";
      }
    } catch (e) {
      // 有的浏览器不认 camera 这个权限名，查不到就退回下面那句通用提示
    }
    if (site === "denied") {
      return `浏览器把这个网站的相机记成「已阻止」了${code}。`
        + "点地址栏左边的图标 → 权限 → 相机 → 改成「允许」，刷新页面再点「重试相机」。";
    }
    if (site === "prompt" || site === "granted") {
      return `网站这边没被拦，是手机没把相机权限给浏览器 App${code}。`
        + "到「系统设置 → 应用 → 浏览器 → 权限 → 相机」里允许，回来点「重试相机」。";
    }
    return `没有拿到相机权限${code}。两处都要看：`
      + "① 地址栏左边的图标 → 权限 → 相机 → 允许；"
      + "② 系统设置 → 应用 → 浏览器 → 权限 → 相机 → 允许。改完刷新页面再点「重试相机」。";
  }

  /* ── 运行时状态 ─────────────────────────────────────── */
  const state = {
    overlay: null,
    video: null,
    canvas: null,
    stream: null,
    detector: null,
    timer: 0,
    facing: "environment",
    onResult: null,
    onCancel: null,
    done: false,
    decoding: false,
    live: false,
  };

  function makeDetector() {
    if (typeof window.BarcodeDetector !== "function") return null;
    try {
      return new window.BarcodeDetector({ formats: ["qr_code"] });
    } catch (err) {
      // 有的实现只支持 formats 的子集，构造失败就当没有，交给 jsQR
      return null;
    }
  }

  /* ── 解码 ───────────────────────────────────────────── */
  /** 解一帧，返回识别到的字符串（没识别到返回 ""）。
   *
   *  BarcodeDetector.detect 是异步的，所以这里整体异步；同一帧不重入
   *  （上一帧还没解完就跳过这一帧，否则慢机器上会堆一屁股任务）。 */
  async function decodeCanvas(canvas, ctx, allowInvert) {
    if (state.detector) {
      try {
        const found = await state.detector.detect(canvas);
        if (found && found.length) return String(found[0].rawValue || "");
      } catch (err) {
        // 有些机型偶发解码异常，不致命：这一帧当没扫到
      }
      return "";
    }
    if (typeof window.jsQR !== "function") return "";
    const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
    // 实时预览不做反色尝试（慢一倍且几乎用不到）；单张照片才值得试
    const hit = window.jsQR(image.data, image.width, image.height, {
      inversionAttempts: allowInvert ? "attemptBoth" : "dontInvert",
    });
    return hit && hit.data ? String(hit.data) : "";
  }

  function drawToCanvas(source, maxWidth) {
    const vw = source.videoWidth || source.naturalWidth || source.width;
    const vh = source.videoHeight || source.naturalHeight || source.height;
    if (!vw || !vh) return null;
    const scale = Math.min(1, maxWidth / vw);
    const canvas = state.canvas;
    canvas.width = Math.max(1, Math.round(vw * scale));
    canvas.height = Math.max(1, Math.round(vh * scale));
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return null;
    ctx.drawImage(source, 0, 0, canvas.width, canvas.height);
    return ctx;
  }

  async function tick() {
    if (state.done || !state.video) return;
    if (!state.decoding && state.video.readyState >= 2) {
      state.decoding = true;
      const ctx = drawToCanvas(state.video, LIVE_MAX_WIDTH);
      const text = ctx ? await decodeCanvas(state.canvas, ctx, false) : "";
      state.decoding = false;
      if (state.done) return;
      if (text) { finish(text); return; }
    }
    state.timer = setTimeout(tick, FRAME_INTERVAL);
  }

  /** 扫到了就收工：先摘掉 onCancel，否则 close() 会把「扫到了」又当成「取消了」。 */
  function finish(text) {
    if (state.done) return;
    state.done = true;
    const cb = state.onResult;
    state.onCancel = null;
    state.onResult = null;
    close();
    if (cb) cb(text);
  }

  /* ── 界面 ───────────────────────────────────────────── */
  function node(selector) {
    return state.overlay ? state.overlay.querySelector(selector) : null;
  }

  function note(message, cls) {
    const box = node(".scan-note");
    if (!box) return;
    box.textContent = message || "";
    box.className = "scan-note" + (cls ? " " + cls : "");
  }

  /** 显示/隐藏一个按钮，并维护 hidden 与 hidden 属性的一致性。
   *  （用 hidden 属性而不是 display:none，是为了让无障碍工具也认。） */
  function show(selector, visible, label) {
    const el = node(selector);
    if (!el) return;
    if (label) el.textContent = label;
    el.hidden = !visible;
  }

  function buildOverlay(title, hint) {
    const wrap = document.createElement("div");
    wrap.className = "scan-overlay";
    wrap.innerHTML = `
      <div class="scan-panel" role="dialog" aria-label="扫码">
        <div class="scan-head">
          <b></b>
          <button type="button" class="scan-close" aria-label="关闭">✕</button>
        </div>
        <div class="scan-stage">
          <video class="scan-video" playsinline muted autoplay></video>
          <div class="scan-frame"></div>
          <div class="scan-note"></div>
        </div>
        <div class="scan-actions">
          <label class="btn scan-photo">拍照识别
            <input type="file" accept="image/*" capture="environment" hidden />
          </label>
          <button type="button" class="btn scan-retry" hidden>重试相机</button>
          <button type="button" class="btn scan-switch" hidden>切换摄像头</button>
        </div>
        <div class="scan-hint"></div>
      </div>`;
    // 标题和提示走 textContent：它们可能带用户填的机型名，别拼进 HTML
    wrap.querySelector(".scan-head b").textContent = title;
    wrap.querySelector(".scan-hint").textContent = hint;
    document.body.appendChild(wrap);
    return wrap;
  }

  async function countCameras() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return 1;
    try {
      const devices = await navigator.mediaDevices.enumerateDevices();
      return devices.filter((d) => d.kind === "videoinput").length || 1;
    } catch (err) {
      return 1;
    }
  }

  function stopCamera() {
    if (state.timer) { clearTimeout(state.timer); state.timer = 0; }
    if (state.stream) {
      state.stream.getTracks().forEach((track) => track.stop());
      state.stream = null;
    }
    if (state.video) state.video.srcObject = null;
    state.live = false;
  }

  /** 打开/重启相机。切换摄像头、重试也走这里。 */
  async function startCamera() {
    stopCamera();
    if (state.done) return false;
    try {
      state.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: state.facing },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
    } catch (err) {
      const name = (err && err.name) || "";
      if (name === "NotAllowedError" || name === "SecurityError") {
        note("没有拿到相机权限。请在浏览器地址栏的站点设置里允许相机，再点「重试相机」。", "warn");
      } else if (name === "NotFoundError" || name === "OverconstrainedError") {
        note("没找到可用的摄像头，请用「拍照识别」。", "warn");
      } else {
        note(`打不开相机（${(err && err.message) || name}），请用「拍照识别」。`, "warn");
      }
      if (state.video) state.video.hidden = true;
      show(".scan-retry", true);
      show(".scan-switch", false);
      node(".scan-photo").classList.add("primary");
      return false;
    }
    state.live = true;
    state.done = false;
    state.video.hidden = false;
    state.video.srcObject = state.stream;
    try { await state.video.play(); } catch (err) { /* iOS 偶尔要用户再点一下，忽略 */ }
    note("把二维码放进框里", "");
    show(".scan-retry", false);
    const many = (await countCameras()) > 1;
    if (!state.done) show(".scan-switch", many);
    if (!state.done) tick();
    return true;
  }

  /** 单张照片解码。用 <input capture> 调系统相机，
   *  所以 http 页面也能用 —— 这是内网部署下的主力路径。 */
  async function scanPhoto(file) {
    if (!file || state.done) return;
    if (!state.detector && typeof window.jsQR !== "function") {
      note("这个浏览器缺少二维码解码能力，请手动输入料盘号。", "warn");
      return;
    }
    note("正在识别照片…", "");
    let source = null;
    try {
      source = await loadImage(file);
    } catch (err) {
      note("照片读不出来，换一张再试。", "warn");
      return;
    }
    const ctx = drawToCanvas(source, PHOTO_MAX_WIDTH);
    const text = ctx ? await decodeCanvas(state.canvas, ctx, true) : "";
    if (typeof source.close === "function") source.close();
    if (state.done) return;
    if (text) { finish(text); return; }
    note("照片里没找到二维码。把码拍正、拍清楚一点，或者靠近一点再试。", "warn");
  }

  function loadImage(file) {
    if (typeof createImageBitmap === "function") {
      return createImageBitmap(file).catch(() => loadViaImg(file));
    }
    return loadViaImg(file);
  }

  function loadViaImg(file) {
    return new Promise((resolve, reject) => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => { URL.revokeObjectURL(url); resolve(img); };
      img.onerror = () => { URL.revokeObjectURL(url); reject(new Error("decode failed")); };
      img.src = url;
    });
  }

  function close() {
    const wasOpen = !!state.overlay;
    state.done = true;
    stopCamera();
    const wrap = state.overlay;
    state.overlay = null;
    state.video = null;
    state.canvas = null;
    state.detector = null;
    if (wrap && wrap.parentNode) wrap.parentNode.removeChild(wrap);
    document.body.classList.remove("scan-open");
    const cancel = state.onCancel;
    state.onCancel = null;
    state.onResult = null;
    if (wasOpen && cancel) cancel();
  }

  /* ── 对外入口 ───────────────────────────────────────── */
  /** 打开扫码界面。
   *  @param {{title?:string, hint?:string,
   *           onResult:(text:string)=>void, onCancel?:()=>void}} options */
  function openScanner(options) {
    const opts = options || {};
    if (state.overlay) close();

    state.onResult = opts.onResult || null;
    state.onCancel = opts.onCancel || null;
    state.done = false;
    state.decoding = false;
    state.facing = "environment";
    state.canvas = document.createElement("canvas");
    state.detector = makeDetector();

    state.overlay = buildOverlay(
      opts.title || "扫二维码",
      opts.hint || "对准料盘或槽位上贴的二维码。用手机自带相机扫同一个码，也会直接跳到对应位置。",
    );
    state.video = node(".scan-video");
    document.body.classList.add("scan-open");

    node(".scan-close").addEventListener("click", close);
    state.overlay.addEventListener("click", (event) => {
      if (event.target === state.overlay) close();
    });

    node(".scan-retry").addEventListener("click", () => {
      note("正在打开相机…", "");
      startCamera();
    });
    node(".scan-switch").addEventListener("click", () => {
      state.facing = state.facing === "environment" ? "user" : "environment";
      note("正在切换摄像头…", "");
      startCamera();
    });

    const fileInput = node(".scan-photo input");
    fileInput.addEventListener("change", (event) => {
      const file = event.target.files && event.target.files[0];
      event.target.value = "";   // 允许重拍同一个文件
      scanPhoto(file);
    });

    if (!state.detector && typeof window.jsQR !== "function") {
      note("这个浏览器没有可用的二维码解码器，请手动输入料盘号。", "warn");
      state.video.hidden = true;
      show(".scan-switch", false);
      return;
    }

    const blocked = cameraBlockReason();
    if (blocked) {
      // 开不了实时相机：把原因说清楚，并把「拍照识别」推成主按钮
      state.video.hidden = true;
      show(".scan-switch", false);
      note(blocked, "warn");
      node(".scan-photo").classList.add("primary");
      return;
    }

    note("正在打开相机…", "");
    startCamera();
  }

  window.spoolScanner = {
    open: openScanner,
    close,
    parseScan,
    cameraBlockReason,
    // 自测用：tests/test_ui_polish.mjs 的「扫码认码」「相机可用性」两组会调这几个
    _internals: {
      state, LIVE_MAX_WIDTH, PHOTO_MAX_WIDTH, FRAME_INTERVAL,
      cameraDeniedHint,
    },
  };
})();
