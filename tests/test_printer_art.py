"""机型图（仪表盘上的真机照片）的静态校验。

单独跑：python tests/test_printer_art.py

只查文件，不起服务：图片错、型号对不上、尺寸不统一都是靠肉眼很难发现的回归，
而这类问题直接影响仪表盘第一眼观感。

覆盖：
- app/static/printer/ 里每张图都能被 printer_image_map() 扫到
- 每张图都是 JPEG、720x876（= 界面 240x292 展示框的 3 倍），且体积合理
- photo_key 归一：带空格的 "A1 mini" 与文件 a1mini.jpg 能对上
- catalog 里所有展示名都有对应图片（漏一张就退回 SVG 示意图）
- 文件名不含空格/非 ASCII（容器里 ls、URL 编码都更省心）
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from app.catalog import MODEL_CODE_TO_NAME  # noqa: E402
from app.printer_art import PHOTO_DIR, photo_key, printer_image_map  # noqa: E402

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


def main() -> int:
    print("机型图校验")
    print("\n1. 目录与扫描")
    check("照片目录存在", PHOTO_DIR.is_dir(), str(PHOTO_DIR))
    files = sorted(p for p in PHOTO_DIR.iterdir() if p.is_file()) if PHOTO_DIR.is_dir() else []
    table = printer_image_map()
    check("每个文件都被扫进映射表", len(table) == len(files), f"{len(table)}/{len(files)}")

    print("\n2. 单张规格")
    for path in files:
        if path.suffix.lower() not in {".jpg", ".jpeg"}:
            check(f"{path.name} 是 JPEG", False, path.suffix)
            continue
        with Image.open(path) as im:
            size, mode = im.size, im.mode
        check(
            f"{path.name} 720x876 RGB/L",
            size == (720, 876) and mode in ("RGB", "L"),
            f"{size} {mode}",
        )
        kb = path.stat().st_size // 1024
        check(f"{path.name} 体积合理", 8 <= kb <= 200, f"{kb}KB")

    print("\n3. 文件名规范")
    for path in files:
        check(
            f"{path.name} 无空格/非 ASCII",
            path.stem.isascii() and " " not in path.stem,
            path.stem,
        )

    print("\n4. 型号匹配")
    check("photo_key 去掉空格", photo_key("A1 mini") == "A1MINI", photo_key("A1 mini"))
    check("photo_key 大小写无关", photo_key("p2s") == "P2S", photo_key("p2s"))
    check("photo_key 去连字符", photo_key("H2D-Pro") == "H2DPRO", photo_key("H2D-Pro"))

    names = sorted(set(MODEL_CODE_TO_NAME.values()))
    for name in names:
        check(f"{name} 有对应图片", bool(table.get(photo_key(name))), table.get(photo_key(name), ""))

    print("\n" + "─" * 52)
    print(f"通过 {PASS} 项，失败 {FAIL} 项")
    if FAILURES:
        for name in FAILURES:
            print(f"  未通过：{name}")
        return 1
    print("机型图校验通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
