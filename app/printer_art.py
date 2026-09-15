"""真机照片的发现与降级。

仪表盘上原来画的是内联 SVG 示意图，用户要的是「真实的相对应的机器图片」。
照片放在 app/static/printer/ 下，文件名就是机型（大小写不敏感）：
    printer/p2s.jpg      → P2S
    printer/x1c.jpg      → X1C
    printer/a1mini.png   → A1MINI

放文件即生效，不需要改代码：后端把目录扫成 {机型: 静态URL} 交给前端，
前端按当前机型挑一张；目录里没有对应机型时自动退回内联 SVG 示意图，
所以只有 P2S 一张照片也不会让其它机型开天窗。

换图/加图的做法见 README「换成你自己的机器照片」一节，
脚本是 scripts/build_printer_photo.py。
"""
from __future__ import annotations

from pathlib import Path

STATIC_DIR = Path(__file__).resolve().parent / "static"
PHOTO_DIR = STATIC_DIR / "printer"
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def printer_image_map() -> dict[str, str]:
    """扫描照片目录 → {机型大写: /static/printer/xxx.jpg}。

    目录不存在或为空都返回 {}（前端会全部走 SVG 兜底），不抛异常：
    仪表盘不该因为少放一张图就打不开。
    """
    out: dict[str, str] = {}
    try:
        entries = sorted(PHOTO_DIR.iterdir())
    except OSError:
        return out
    for path in entries:
        if not path.is_file() or path.suffix.lower() not in PHOTO_EXTS:
            continue
        # 同名不同后缀时按后缀顺序取最后一个，避免出现两张图随机命中
        out[path.stem.upper()] = f"/static/printer/{path.name}"
    return out
