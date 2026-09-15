"""标签打印自测：二维码取整与标签接口。

为什么专门测「取整」：
  1 位热敏标签把二维码 1:1 贴进位图，一旦缩放就不是「整数个点/模块」，
  模块边界会被糊成灰边，手机扫不出来。所以服务端必须保证
    图片像素边长 == 总模块数 × 整数倍率
  这里的断言就是钉住这条不变量。

覆盖：
  - _qr_module_count：一致性（同内容返回同值）、含静区、等于 17+4N+2×静区
  - _qr_png：像素边长 = 总模块数 × box；静区确实留白；非法 box 兜底
  - _qr_png_fit：倍率向下取整，不超目标点宽；目标过小时兜底成 1 点/模块
  - GET /api/labels/spool/{id}.png?box=N：回传 X-QR-Dots / X-QR-Modules 且
    图片边长与 X-QR-Dots 对齐；box 上限 16
  - ?dots=N：同样整数倍率、不超 N
  - 两个参数都不给：行为与老接口一致（默认 8 点/模块），且**不带**响应头
  - box 优先于 dots
  - 未登录 401、料盘不存在 404、槽位标签与 A4 拼版仍可用

运行： python tests/test_labels.py
"""
from __future__ import annotations

import io
import os
import shutil
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ["BAMBU_MOCK"] = "1"
os.environ["DATA_DIR"] = os.path.join(ROOT, "data", "testlabels")
# 让测试客户端（非内网来源）也能完成首次初始化
os.environ["ALLOW_PUBLIC_SETUP"] = "1"

from PIL import Image  # noqa: E402
from sqlmodel import select  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from app.api.routes import _qr_module_count, _qr_png, _qr_png_fit  # noqa: E402
from app.db import init_db, session_scope  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Spool  # noqa: E402

PASSED: list[str] = []
FAILED: list[str] = []

SAMPLE = "http://example.test/#spool=1"
BORDER = 2


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(label)
        print(f"  [通过] {label}")
    else:
        FAILED.append(label)
        print(f"  [失败] {label} {detail}")


def reset() -> None:
    from app.db import engine
    try:
        engine.dispose()  # 关闭连接池，Windows 上才能删掉 db 文件
    except Exception:
        pass
    data_dir = os.environ["DATA_DIR"]
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir, ignore_errors=True)
    os.makedirs(data_dir, exist_ok=True)
    init_db()


def png_size(data: bytes) -> tuple[int, int]:
    """直接读 PNG 的 IHDR，避免依赖解码库。"""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("不是 PNG")
    width, height = struct.unpack(">II", data[16:24])
    return int(width), int(height)


def seed_spool() -> int:
    with session_scope() as session:
        spool = Spool(
            name="测试料盘 PLA 深空黑", brand="拓竹", material="PLA",
            color_name="深空黑", color_hex="#1A1A1A", spool_weight=250.0,
            initial_weight=1000.0, remaining_weight=640.0,
        )
        session.add(spool)
        session.commit()
        return int(spool.id)


def login_client() -> TestClient:
    client = TestClient(app)
    r = client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})
    if r.status_code != 200:
        raise RuntimeError(f"初始化管理员失败：{r.status_code} {r.text}")
    return client


# ── 1. 模块数（纯函数） ───────────────────────────────────────────
def test_module_count() -> None:
    print("== 二维码总模块数 ==")
    total = _qr_module_count(SAMPLE, border=BORDER)
    check("同内容结果稳定", _qr_module_count(SAMPLE, border=BORDER) == total, str(total))
    check("含静区（比模块数大 2×静区）", total == _qr_module_count(SAMPLE, border=0) + BORDER * 2,
          f"{total} vs {_qr_module_count(SAMPLE, border=0)}")
    # QR 的模块数满足 17 + 4N（N 为版本号），所以 (模块数 - 17) 能被 4 整除
    check("模块数符合 17+4N", (_qr_module_count(SAMPLE, border=0) - 17) % 4 == 0,
          str(_qr_module_count(SAMPLE, border=0)))
    check("静区 0 与 4 差 8", _qr_module_count(SAMPLE, border=4) - _qr_module_count(SAMPLE, border=0) == 8)
    longer = _qr_module_count("http://example.test/#spool=" + "9" * 120, border=BORDER)
    check("内容变长会升版本", longer > total, f"{longer} vs {total}")


# ── 2. 出图尺寸（纯函数） ─────────────────────────────────────────
def test_png_dimensions() -> None:
    print("== 出图尺寸 ==")
    total = _qr_module_count(SAMPLE, border=BORDER)
    for box in (1, 4, 8, 16):
        data = _qr_png(SAMPLE, box=box, border=BORDER)
        w, h = png_size(data)
        check(f"box={box} 边长 = 模块数×{box}", w == total * box and h == total * box, f"{w}x{h}")

    img = Image.open(io.BytesIO(_qr_png(SAMPLE, box=8, border=BORDER))).convert("L")
    w, h = img.size
    quiet = BORDER * 8
    corners = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    check("四角留白（静区）", all(img.getpixel(p) == 255 for p in corners),
          str([img.getpixel(p) for p in corners]))
    # 静区内侧那一列仍应是白
    check("静区宽度足额", img.getpixel((quiet - 1, h // 2)) == 255)
    inner = [img.getpixel((x, h // 2)) for x in range(quiet, w - quiet)]
    check("数据区有黑像素", any(v < 128 for v in inner))

    check("非法 box 兜底成 1", png_size(_qr_png(SAMPLE, box=0, border=BORDER)) == (total, total))
    check("负数 box 兜底成 1", png_size(_qr_png(SAMPLE, box=-3, border=BORDER)) == (total, total))


# ── 3. 按目标点宽取整（纯函数） ───────────────────────────────────
def test_fit_rounding() -> None:
    print("== 目标点宽向下取整 ==")
    total = _qr_module_count(SAMPLE, border=BORDER)
    for target in (total, total * 3, total * 3 + 2, total * 4 - 1, 400, 1000):
        data, actual = _qr_png_fit(SAMPLE, target, border=BORDER)
        box = actual // total
        check(f"dots={target}：点宽不超目标", actual <= target, f"actual={actual}")
        check(f"dots={target}：点宽是模块数整数倍", actual == box * total, f"actual={actual} box={box}")
        check(f"dots={target}：点宽取最大整数倍率", (box + 1) * total > target, f"box={box}")
        check(f"dots={target}：出图边长与回传一致", png_size(data) == (actual, actual),
              f"{png_size(data)} vs {actual}")

    _, tiny = _qr_png_fit(SAMPLE, 1, border=BORDER)
    check("目标过小时兜底 1 点/模块", tiny == total, str(tiny))
    _, zero = _qr_png_fit(SAMPLE, 0, border=BORDER)
    check("目标为 0 时不崩且兜底", zero == total, str(zero))
    _, negative = _qr_png_fit(SAMPLE, -50, border=BORDER)
    check("目标为负时不崩且兜底", negative == total, str(negative))


# ── 4. HTTP：box 参数 ────────────────────────────────────────────
def test_http_box() -> None:
    print("== HTTP：?box ==")
    reset()
    spool_id = seed_spool()
    client = login_client()
    url = f"/api/labels/spool/{spool_id}.png"
    total = _qr_module_count(f"http://testserver/#spool={spool_id}", border=BORDER)

    r = client.get(url, params={"box": 4})
    check("box=4 返回 200", r.status_code == 200, str(r.status_code))
    check("box=4 是 PNG", r.headers.get("content-type", "").startswith("image/png"),
          r.headers.get("content-type", ""))
    check("box=4 回传 X-QR-Modules", r.headers.get("X-QR-Modules") == str(total),
          str(r.headers.get("X-QR-Modules")))
    check("box=4 回传 X-QR-Dots = 模块数×4", r.headers.get("X-QR-Dots") == str(total * 4),
          str(r.headers.get("X-QR-Dots")))
    check("box=4 图片边长与 X-QR-Dots 对齐", png_size(r.content) == (total * 4, total * 4),
          str(png_size(r.content)))
    check("box=4 禁缓存", r.headers.get("cache-control") == "no-store", str(r.headers.get("cache-control")))

    r = client.get(url, params={"box": 99})
    check("box 上限收到 16", r.headers.get("X-QR-Dots") == str(total * 16),
          str(r.headers.get("X-QR-Dots")))
    check("box=99 出图不超过 16 倍", png_size(r.content) == (total * 16, total * 16))

    r2 = client.get(url, params={"box": 4})
    check("同内容两次出图一致", r2.content == client.get(url, params={"box": 4}).content)


# ── 5. HTTP：dots 参数 ───────────────────────────────────────────
def test_http_dots() -> None:
    print("== HTTP：?dots ==")
    reset()
    spool_id = seed_spool()
    client = login_client()
    url = f"/api/labels/spool/{spool_id}.png"
    total = _qr_module_count(f"http://testserver/#spool={spool_id}", border=BORDER)

    target = total * 3 + 1
    r = client.get(url, params={"dots": target})
    dots = int(r.headers.get("X-QR-Dots", "0"))
    check("dots 返回 200", r.status_code == 200, str(r.status_code))
    check("dots：回传点宽不超目标", 0 < dots <= target, f"dots={dots} target={target}")
    check("dots：点宽是模块数整数倍", dots % total == 0, f"dots={dots} total={total}")
    check("dots：取到最大整数倍率", dots == total * 3, f"dots={dots}")
    check("dots：图片边长与回传对齐", png_size(r.content) == (dots, dots), str(png_size(r.content)))
    check("dots：禁缓存", r.headers.get("cache-control") == "no-store")

    r = client.get(url, params={"dots": 5})
    check("dots 过小时兜底 1 点/模块且仍出图",
          r.status_code == 200 and int(r.headers["X-QR-Dots"]) == total,
          f"{r.status_code} {r.headers.get('X-QR-Dots')}")

    # box 优先于 dots：同时给两个时按 box 走
    r = client.get(url, params={"box": 2, "dots": total * 7})
    check("box 优先于 dots", r.headers.get("X-QR-Dots") == str(total * 2),
          str(r.headers.get("X-QR-Dots")))


# ── 6. HTTP：默认行为与其它标签接口 ──────────────────────────────
def test_http_default_and_others() -> None:
    print("== HTTP：默认行为与其它标签 ==")
    reset()
    spool_id = seed_spool()
    client = login_client()
    total = _qr_module_count(f"http://testserver/#spool={spool_id}", border=BORDER)

    r = client.get(f"/api/labels/spool/{spool_id}.png")
    check("不带参数返回 200", r.status_code == 200, str(r.status_code))
    check("不带参数仍是 PNG", r.headers.get("content-type", "").startswith("image/png"))
    check("不带参数维持默认 8 点/模块", png_size(r.content) == (total * 8, total * 8),
          str(png_size(r.content)))
    check("不带参数不下发 X-QR-Dots（旧行为不变）", "X-QR-Dots" not in r.headers,
          str(dict(r.headers)))

    r = client.get(f"/api/labels/spool/{spool_id}.png", params={"box": 0, "dots": 0})
    check("box=0/dots=0 走默认分支", r.status_code == 200 and "X-QR-Dots" not in r.headers,
          str(r.status_code))

    r = client.get("/api/labels/spool/99999.png")
    check("料盘不存在返回 404", r.status_code == 404, str(r.status_code))

    r = client.get("/api/labels/slot/1/0/0.png")
    check("槽位标签可用", r.status_code == 200 and png_size(r.content)[0] > 0,
          f"{r.status_code} {png_size(r.content) if r.status_code == 200 else ''}")

    r = client.get("/api/labels/sheet")
    check("A4 拼版返回 HTML", r.status_code == 200 and "text/html" in r.headers.get("content-type", ""),
          r.headers.get("content-type", ""))
    check("A4 拼版含料盘名", "测试料盘" in r.text, r.text[:120])

    r = client.get("/api/labels/sheet", params={"ids": str(spool_id)})
    check("A4 拼版可按 id 过滤", r.status_code == 200 and "测试料盘" in r.text)

    anon = TestClient(app)
    r = anon.get(f"/api/labels/spool/{spool_id}.png")
    check("未登录被拦 401", r.status_code == 401, str(r.status_code))
    r = anon.get("/api/labels/sheet")
    check("未登录看不了拼版页 401", r.status_code == 401, str(r.status_code))


if __name__ == "__main__":
    test_module_count()
    test_png_dimensions()
    test_fit_rounding()
    test_http_box()
    test_http_dots()
    test_http_default_and_others()
    print(f"\n通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        print("失败项：", FAILED)
        sys.exit(1)
    print("全部通过")
