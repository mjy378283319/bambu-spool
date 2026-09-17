"""应用图标与 favicon 的端到端测试。

单独跑：python tests/test_brand_icon.py

覆盖：
- 图标文件在仓库/静态目录就位（根目录 icon.png / icon.svg、static 下 favicon.ico / apple-touch-icon.png）
- **未登录**也能取到 /favicon.ico 与 /static/icon.svg（登录页自身要显示图标，
  这些路径必须在外壳放行名单里；掉进鉴权中间件就会 401，书签栏一片空白）
- /favicon.ico 返回真正的 ICO（含多尺寸），不是 HTML 错误页
- index.html 正确引用了 ico / svg / apple-touch-icon 三种图标
- README 里给出的容器图标直链，反解出的仓库路径真实存在
- Dockerfile 会把图标打进镜像，且 .dockerignore 没有把它们排除掉
"""
from __future__ import annotations

import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

PASS = 0
FAIL = 0
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  \033[32m✓\033[0m {label}" + (f"  ({detail})" if detail else ""))
    else:
        FAIL += 1
        FAILURES.append(label)
        print(f"  \033[31m✗\033[0m {label}" + (f"  ({detail})" if detail else ""))


def section(title: str) -> None:
    print(f"\n\033[1m{title}\033[0m")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Server:
    def __init__(self, data_dir: Path) -> None:
        self.port = free_port()
        env = dict(os.environ)
        env.update({
            "DATA_DIR": str(data_dir),
            "BAMBU_MOCK": "1",
            "PORT": str(self.port),
            "PYTHONUNBUFFERED": "1",
            "PBKDF2_ITERATIONS": "100000",
        })
        self.proc = subprocess.Popen(
            [PY, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(self.port), "--log-level", "warning"],
            cwd=str(ROOT), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        self.base = f"http://127.0.0.1:{self.port}"

    def wait(self, timeout: float = 60.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                return False
            try:
                if httpx.get(self.base + "/health", timeout=2.0).status_code == 200:
                    return True
            except Exception:
                time.sleep(0.3)
        return False

    def stop(self) -> None:
        try:
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass

    def output(self) -> str:
        try:
            return (self.proc.stdout.read() or "")[-4000:]  # type: ignore[union-attr]
        except Exception:
            return ""


# ── ICO 极简解析：只读 ICONDIR 头与条目数，确认不是伪装成 ico 的别的东西 ──
def parse_ico(payload: bytes) -> dict:
    """返回 {'n': 条目数, 'sizes': [(w,h), ...]}；不是 ICO 则 raise。"""
    if len(payload) < 6:
        raise ValueError("too short")
    reserved, ico_type, count = (
        int.from_bytes(payload[0:2], "little"),
        int.from_bytes(payload[2:4], "little"),
        int.from_bytes(payload[4:6], "little"),
    )
    if reserved != 0 or ico_type != 1:
        raise ValueError(f"不是 ICO（reserved={reserved} type={ico_type}）")
    sizes = []
    for i in range(count):
        off = 6 + i * 16
        if len(payload) < off + 16:
            break
        w = payload[off] or 256
        h = payload[off + 1] or 256
        sizes.append((w, h))
    return {"n": count, "sizes": sizes}


def main() -> int:
    section("一、图标文件就位")

    root_png = ROOT / "icon.png"
    root_svg = ROOT / "icon.svg"
    static_svg = ROOT / "app" / "static" / "icon.svg"
    static_ico = ROOT / "app" / "static" / "favicon.ico"
    static_touch = ROOT / "app" / "static" / "apple-touch-icon.png"
    docs_png = ROOT / "docs" / "icon-512.png"

    for label, path, min_size in (
        ("根目录 icon.png（Unraid 取图就指这里）", root_png, 5000),
        ("根目录 icon.svg", root_svg, 500),
        ("app/static/icon.svg", static_svg, 500),
        ("app/static/favicon.ico", static_ico, 1000),
        ("app/static/apple-touch-icon.png", static_touch, 1000),
        ("docs/icon-512.png（README 引用）", docs_png, 5000),
    ):
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        check(label, exists and size >= min_size,
              f"{size} B" if exists else "缺失")

    section("二、ICO 结构正确（浏览器书签栏要靠它）")
    if static_ico.exists():
        try:
            info = parse_ico(static_ico.read_bytes())
            check("favicon.ico 是合法 ICO", True, f"{info['n']} 个条目")
            check("含 16x16（标签页）", (16, 16) in info["sizes"],
                  str(info["sizes"]))
            check("含 32x32（任务栏/书签）", (32, 32) in info["sizes"],
                  str(info["sizes"]))
        except Exception as e:
            check("favicon.ico 是合法 ICO", False, str(e))
            check("含 16x16（标签页）", False, "无法解析")
            check("含 32x32（任务栏/书签）", False, "无法解析")
    else:
        check("favicon.ico 是合法 ICO", False, "文件缺失")
        check("含 16x16（标签页）", False, "文件缺失")
        check("含 32x32（任务栏/书签）", False, "文件缺失")

    section("三、index.html 三种图标引用齐全")
    html = (ROOT / "app" / "static" / "index.html").read_text(encoding="utf-8")
    check("引用 svg 图标", 'rel="icon"' in html and "/static/icon.svg" in html)
    check("引用 /favicon.ico", "/favicon.ico" in html)
    check("引用 apple-touch-icon",
          "apple-touch-icon" in html and "apple-touch-icon.png" in html)
    # apple-touch-icon 必须是 PNG：Safari 对 SVG 版支持不一致
    at = re.search(r'rel="apple-touch-icon"[^>]*href="([^"]+)"', html)
    check("apple-touch-icon 指向 PNG（不是 SVG）",
          bool(at) and at.group(1).endswith(".png"),
          at.group(1) if at else "未找到")

    section("五、README 给出的容器图标直链，指向的文件真在仓库里")
    # 用户实际踩的坑：按 README 填了 Icon URL 却始终不出图。除了网络问题，
    # 还有一种情况是链接写错/指向不存在的路径 —— 这里把 URL 反解成仓库路径做校验。
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    # 两种形态都要抓：
    #   https://raw.githubusercontent.com/<o>/<r>/<ref>/<path>
    #   https://cdn.jsdelivr.net/gh/<o>/<r>@<ref>/<path>
    raw_urls = re.findall(
        r"raw\.githubusercontent\.com/mjy378283319/bambu-spool/[^/\s]+/([^\s`)\"']+)", readme)
    cdn_urls = re.findall(
        r"cdn\.jsdelivr\.net/gh/mjy378283319/bambu-spool@[^/\s]+/([^\s`)\"']+)", readme)
    icon_urls = raw_urls + cdn_urls
    check("README 至少给出一个图标直链", len(icon_urls) >= 1, str(icon_urls))
    check("raw 与 jsDelivr 两种直链都给了（用户网络可能只通一条）",
          len(raw_urls) >= 1 and len(cdn_urls) >= 1,
          f"raw={len(raw_urls)} cdn={len(cdn_urls)}")
    for rel in icon_urls:
        rel = rel.rstrip(".,;")            # 句末标点不算路径
        target = ROOT / rel
        check(f"直链指向的文件存在：{rel}",
              target.is_file(), f"{target.stat().st_size} B" if target.is_file() else "缺失")
    check("首选直链是 jsDelivr CDN（raw 域名国内常被污染）",
          "cdn.jsdelivr.net/gh/mjy378283319/bambu-spool" in readme)

    section("六、Dockerfile / .dockerignore 会把图标带进镜像")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    check("Dockerfile 有 COPY icon.png icon.svg",
          bool(re.search(r"^COPY\s+icon\.png\s+icon\.svg\s", dockerfile, re.M)))
    check("Dockerfile 声明 OCI 图标相关 label",
          "org.opencontainers.image.title" in dockerfile
          and "org.opencontainers.image.source" in dockerfile)
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    ignored = [
        ln.strip() for ln in dockerignore.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    ]
    check("icon.png 未被 .dockerignore 排除", "icon.png" not in ignored)
    check("icon.svg 未被 .dockerignore 排除", "icon.svg" not in ignored)

    section("七、未登录也能取到图标（登录页本身要显示 logo）")
    data_dir = ROOT / "data" / ".icontest"
    shutil.rmtree(data_dir, ignore_errors=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    srv = Server(data_dir)
    print(f"  启动测试服务：{srv.base}")
    if not srv.wait():
        print("服务启动失败：\n" + srv.output())
        return 1

    anon = httpx.Client(base_url=srv.base, timeout=15.0)
    try:
        # 1) /favicon.ico：匿名可访问，返回真 ICO
        r = anon.get("/favicon.ico")
        check("/favicon.ico 匿名可访问", r.status_code == 200, f"HTTP {r.status_code}")
        ct = r.headers.get("content-type", "")
        check("/favicon.ico 不是 401/404", r.status_code not in (401, 404),
              f"HTTP {r.status_code}")
        if r.status_code == 200:
            try:
                info = parse_ico(r.content)
                check("返回体是合法 ICO", True, f"{info['n']} 条目 / {len(r.content)} B")
            except Exception as e:
                check("返回体是合法 ICO", False, str(e))
            check("Content-Type 是 image/*", ct.startswith("image/"), ct)
        # 2) /static/icon.svg：匿名可访问
        r2 = anon.get("/static/icon.svg")
        check("/static/icon.svg 匿名可访问", r2.status_code == 200,
              f"HTTP {r2.status_code}")
        check("svg 的 Content-Type 正确",
              "svg" in r2.headers.get("content-type", ""),
              r2.headers.get("content-type", ""))
        # 3) /static/apple-touch-icon.png
        r3 = anon.get("/static/apple-touch-icon.png")
        check("/static/apple-touch-icon.png 匿名可访问",
              r3.status_code == 200, f"HTTP {r3.status_code}")
        # 4) /favicon.ico 不能被鉴权挡住（回归点：路径必须在 OPEN_EXACT 里）
        check("/favicon.ico 响应不含未登录提示",
              b"unauthenticated" not in r.content
              and "未登录" not in r.text[:200], "未泄露鉴权 JSON")
    finally:
        anon.close()
        srv.stop()

    print()
    if FAIL:
        print(f"\033[31m{FAIL} 项失败\033[0m（通过 {PASS}）")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print(f"\033[32m全部通过\033[0m（{PASS} 项）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
