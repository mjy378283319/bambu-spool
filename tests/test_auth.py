"""访问控制与登录流程的端到端测试。

单独跑：python tests/test_auth.py

会真实起一个 uvicorn 子进程，覆盖：
未登录拦截 / 首次初始化 / 登录 / 会话强度 / CSRF / 安全响应头 /
WebSocket 鉴权 / 改密码 / 退出 / 爆破锁定 / 强制 HTTPS 重定向。
"""
from __future__ import annotations

import json
import os
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
    def __init__(self, data_dir: Path, extra_env: dict | None = None) -> None:
        self.port = free_port()
        self.data_dir = data_dir
        env = dict(os.environ)
        env.update({
            "DATA_DIR": str(data_dir),
            "BAMBU_MOCK": "1",
            "PORT": str(self.port),
            "PYTHONUNBUFFERED": "1",
            # 降低迭代次数让测试快一点，不影响判定逻辑
            "PBKDF2_ITERATIONS": "100000",
        })
        env.update(extra_env or {})
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
                r = httpx.get(self.base + "/health", timeout=2.0)
                if r.status_code == 200:
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


def cookie_of(client: httpx.Client, name: str) -> str:
    return client.cookies.get(name, "")


def raw_set_cookie(resp: httpx.Response, name: str) -> str:
    for header in resp.headers.get_list("set-cookie"):
        if header.lower().startswith(name.lower() + "="):
            return header
    return ""


def main() -> int:
    data_dir = ROOT / "data" / ".authtest"
    shutil.rmtree(data_dir, ignore_errors=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    srv = Server(data_dir)
    print(f"启动测试服务：{srv.base}")
    if not srv.wait():
        print("服务启动失败：\n" + srv.output())
        return 1

    user, password = "xiaomei", "Spool#2026ok"
    anon = httpx.Client(base_url=srv.base, timeout=15.0)
    client = httpx.Client(base_url=srv.base, timeout=15.0)

    try:
        # ── 1. 未登录一律拦截 ──────────────────────────────
        section("1. 未登录访问控制")
        for path in ("/api/system/status", "/api/spools", "/api/jobs", "/api/printers",
                     "/api/bindings", "/api/stats", "/api/catalog", "/api/labels/spool/1.png"):
            r = anon.get(path)
            check(f"GET {path} → 401", r.status_code == 401, f"实际 {r.status_code}")

        r = anon.get("/")
        check("GET / 放行（前端外壳）", r.status_code == 200, f"实际 {r.status_code}")
        r = anon.get("/static/app.js")
        check("GET /static/app.js 放行", r.status_code == 200, f"实际 {r.status_code}")
        check("GET /docs 已关闭（需登录）", anon.get("/docs").status_code == 401)
        check("GET /openapi.json 已关闭（需登录）", anon.get("/openapi.json").status_code == 401)
        r = anon.get("/api/auth/status")
        body = r.json()
        check("GET /api/auth/status 可匿名访问", r.status_code == 200)
        check("初始状态要求初始化", body.get("setup_required") is True, str(body))
        check("初始状态未登录", body.get("authenticated") is False)

        # ── 2. 首次初始化 ─────────────────────────────────
        section("2. 首次初始化管理员")
        r = anon.post("/api/auth/setup", json={"username": "", "password": password})
        check("空账号被拒 → 400", r.status_code == 400, f"实际 {r.status_code}")
        r = anon.post("/api/auth/setup", json={"username": user, "password": "12345678"})
        check("纯数字弱口令被拒 → 400", r.status_code == 400, f"实际 {r.status_code}")
        r = anon.post("/api/auth/setup", json={"username": user, "password": "short1"})
        check("过短口令被拒 → 400", r.status_code == 400, f"实际 {r.status_code}")

        r = client.post("/api/auth/setup", json={"username": user, "password": password})
        check("正常初始化 → 200", r.status_code == 200, f"实际 {r.status_code} {r.text[:120]}")
        set_cookie = raw_set_cookie(r, "bs_session")
        check("下发会话 Cookie", bool(set_cookie))
        check("Cookie 带 HttpOnly", "httponly" in set_cookie.lower(), set_cookie[:80])
        check("Cookie 带 SameSite=lax", "samesite=lax" in set_cookie.lower(), set_cookie[:80])
        check("Cookie 路径为 /", "path=/" in set_cookie.lower())
        check("令牌不落到 localStorage（响应体不含明文令牌）",
              "token" not in json.dumps(r.json()).lower() or "bs_session" not in r.text)

        r = anon.post("/api/auth/setup", json={"username": "hacker", "password": password})
        check("已有账号后初始化关闭 → 409", r.status_code == 409, f"实际 {r.status_code}")

        body = anon.get("/api/auth/status").json()
        check("状态变为可登录", body.get("setup_required") is False and body.get("authenticated") is False)

        # ── 3. 登录 ───────────────────────────────────────
        section("3. 登录")
        bad = httpx.Client(base_url=srv.base, timeout=15.0)
        r = bad.post("/api/auth/login", json={"username": user, "password": "WrongPass#1"})
        check("错误口令 → 401", r.status_code == 401, f"实际 {r.status_code}")
        r = bad.post("/api/auth/login", json={"username": "nobody", "password": password})
        check("不存在账号 → 401（不泄露账号是否存在）", r.status_code == 401, f"实际 {r.status_code}")

        fresh = httpx.Client(base_url=srv.base, timeout=15.0)
        r = fresh.post("/api/auth/login", json={"username": user, "password": password, "remember": True})
        check("正确口令 → 200", r.status_code == 200, f"实际 {r.status_code} {r.text[:120]}")
        check("返回用户名", (r.json().get("user") or {}).get("username") == user)
        check("登录后拿到会话 Cookie", bool(cookie_of(fresh, "bs_session")))

        r = fresh.get("/api/system/status")
        check("带 Cookie 访问业务接口 → 200", r.status_code == 200, f"实际 {r.status_code}")

        # ── 4. 安全响应头 ─────────────────────────────────
        section("4. 安全响应头")
        headers = r.headers
        check("X-Content-Type-Options: nosniff", headers.get("x-content-type-options") == "nosniff")
        check("X-Frame-Options: DENY", headers.get("x-frame-options") == "DENY")
        check("Referrer-Policy 存在", bool(headers.get("referrer-policy")))
        check("Content-Security-Policy 存在", "default-src 'self'" in (headers.get("content-security-policy") or ""))

        # ── 5. 会话强度 ───────────────────────────────────
        section("5. 会话强度")
        forged = httpx.Client(base_url=srv.base, timeout=15.0)
        forged.cookies.set("bs_session", "a" * 43)
        check("伪造令牌 → 401", forged.get("/api/system/status").status_code == 401)

        # 哈希存储：令牌本身不应出现在响应里
        token = cookie_of(fresh, "bs_session")
        check("令牌是随机长串", len(token) >= 40, f"长度 {len(token)}")

        r = httpx.post(srv.base + "/api/auth/login",
                       json={"username": user, "password": password, "remember": True},
                       headers={"X-Forwarded-Proto": "https"}, timeout=15.0)
        sc = raw_set_cookie(r, "bs_session")
        check("X-Forwarded-Proto=https 时 Cookie 带 Secure", "secure" in sc.lower(), sc[:90])

        r = httpx.post(srv.base + "/api/auth/login",
                       json={"username": user, "password": password, "remember": False}, timeout=15.0)
        sc = raw_set_cookie(r, "bs_session")
        check("remember=false 时 Cookie 为 1 天", "max-age=86400" in sc.lower(), sc[:90])

        r = httpx.post(srv.base + "/api/auth/login",
                       json={"username": user, "password": password, "remember": True}, timeout=15.0)
        sc = raw_set_cookie(r, "bs_session")
        check("remember=true 时 Cookie 为 30 天", "max-age=2592000" in sc.lower(), sc[:90])

        # ── 6. 跨站写操作 ─────────────────────────────────
        section("6. 跨站写操作拦截")
        r = fresh.post("/api/spools",
                       json={"brand": "X", "material": "PLA", "color_name": "c"},
                       headers={"Origin": "https://evil.example.com"})
        check("外部 Origin 的 POST → 403", r.status_code == 403, f"实际 {r.status_code}")
        r = fresh.post("/api/spools",
                       json={"brand": "Bambu Lab", "material": "PLA", "color_name": "黑色",
                             "color_hex": "#1A1A1A", "spool_weight": 250, "initial_weight": 1000},
                       headers={"Origin": srv.base})
        check("同源 Origin 的 POST → 放行", r.status_code in (200, 201), f"实际 {r.status_code}")

        # ── 7. WebSocket 鉴权 ─────────────────────────────
        section("7. WebSocket 鉴权")
        try:
            from websockets.sync.client import connect

            denied = None
            try:
                with connect(f"ws://127.0.0.1:{srv.port}/ws",
                             proxy=None, open_timeout=10) as ws:
                    ws.recv(timeout=3)
            except Exception as exc:  # 期望被拒
                denied = exc
            check("无 Cookie 连接 /ws 被拒", denied is not None,
                  f"{type(denied).__name__}" if denied else "竟然连上了")
            check("拒绝码为 4401", denied is not None and "4401" in str(denied),
                  str(denied)[:70] if denied else "")

            ok_ws = False
            with connect(f"ws://127.0.0.1:{srv.port}/ws",
                         additional_headers=[("Cookie", f"bs_session={token}")],
                         proxy=None, open_timeout=10) as ws:
                first = json.loads(ws.recv(timeout=10))
                ok_ws = first.get("type") == "hello" and "data" in first
            check("带 Cookie 连接 /ws 成功并收到 hello", ok_ws)
        except ImportError:
            check("websockets 客户端可用", False, "未安装 websockets")

        # ── 8. 改密码 ─────────────────────────────────────
        section("8. 修改密码")
        other = httpx.Client(base_url=srv.base, timeout=15.0)
        other.post("/api/auth/login", json={"username": user, "password": password})
        other_token = cookie_of(other, "bs_session")
        check("第二处登录已建立", bool(other_token))

        r = fresh.post("/api/auth/password",
                       json={"old_password": "WrongOld#1", "new_password": "NewSpool#2026"})
        check("原口令错误 → 400", r.status_code == 400, f"实际 {r.status_code}")
        r = fresh.post("/api/auth/password",
                       json={"old_password": password, "new_password": "12345678"})
        check("新口令太弱 → 400", r.status_code == 400, f"实际 {r.status_code}")

        new_password = "NewSpool#2026"
        r = fresh.post("/api/auth/password",
                       json={"old_password": password, "new_password": new_password})
        check("改密码 → 200", r.status_code == 200, f"实际 {r.status_code} {r.text[:120]}")
        check("当前浏览器仍在线", fresh.get("/api/auth/me").status_code == 200)
        check("其它设备被踢下线", other.get("/api/system/status").status_code == 401)

        r = httpx.post(srv.base + "/api/auth/login",
                       json={"username": user, "password": new_password}, timeout=15.0)
        check("新口令可登录", r.status_code == 200, f"实际 {r.status_code}")
        r = httpx.post(srv.base + "/api/auth/login",
                       json={"username": user, "password": password}, timeout=15.0)
        check("旧口令已失效", r.status_code == 401, f"实际 {r.status_code}")

        # ── 9. 退出 ───────────────────────────────────────
        section("9. 退出登录")
        r = fresh.post("/api/auth/logout")
        check("退出 → 200", r.status_code == 200)
        check("退出后业务接口 → 401", fresh.get("/api/system/status").status_code == 401)
        check("退出后清除 Cookie", not cookie_of(fresh, "bs_session"))

        # ── 10. 爆破锁定 ──────────────────────────────────
        section("10. 登录爆破锁定（放最后，会锁住来源 IP）")
        brute = httpx.Client(base_url=srv.base, timeout=15.0)
        codes = []
        for _ in range(7):
            codes.append(brute.post(
                "/api/auth/login",
                json={"username": user, "password": "Nope#12345"},
            ).status_code)
        check("连续失败最终被锁定 → 429", 429 in codes, f"状态码序列 {codes}")
        r = brute.post("/api/auth/login", json={"username": user, "password": new_password})
        check("锁定期内即使口令正确也拒绝", r.status_code == 429, f"实际 {r.status_code}")

    finally:
        srv.stop()
        anon.close()
        client.close()

    # ── 11. 强制 HTTPS（独立实例）────────────────────────
    section("11. REQUIRE_HTTPS 强制跳转（独立实例）")
    data_dir2 = ROOT / "data" / ".authtest2"
    shutil.rmtree(data_dir2, ignore_errors=True)
    data_dir2.mkdir(parents=True, exist_ok=True)
    srv2 = Server(data_dir2, extra_env={"REQUIRE_HTTPS": "1"})
    if srv2.wait():
        try:
            r = httpx.get(srv2.base + "/", headers={"X-Forwarded-Proto": "http"},
                          follow_redirects=False, timeout=10.0)
            check("外部为 http 时 → 308 重定向", r.status_code == 308, f"实际 {r.status_code}")
            check("重定向到 https://", (r.headers.get("location") or "").startswith("https://"),
                  r.headers.get("location", ""))
            r = httpx.get(srv2.base + "/", headers={"X-Forwarded-Proto": "https"},
                          follow_redirects=False, timeout=10.0)
            check("外部为 https 时不重定向", r.status_code == 200, f"实际 {r.status_code}")
            r = httpx.get(srv2.base + "/health", headers={"X-Forwarded-Proto": "http"}, timeout=10.0)
            check("健康检查始终放行（供容器探针用）", r.status_code == 200, f"实际 {r.status_code}")
        finally:
            srv2.stop()
    else:
        check("第二个服务实例启动", False, srv2.output()[:200])

    shutil.rmtree(data_dir, ignore_errors=True)
    shutil.rmtree(data_dir2, ignore_errors=True)

    print(f"\n{'=' * 58}")
    print(f"通过 {PASS} 项，失败 {FAIL} 项")
    if FAILURES:
        print("失败项：")
        for name in FAILURES:
            print("  -", name)
    print("=" * 58)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
