"""抓彩多屋（CAILAB）官方色卡，生成 app/brand_colors_cailab.py。

数据源：官网 cailab3d.com 是 Shopify 站，`/products.json?limit=250` 直接给出
**官方色名 + 官方色号**（AC199 / MT9003 / G419 / ATM422 …），逐色还有一张
官方色片图 —— HEX 就从这些色片图取主色，属**近似值**（官方不公布 Hex Code Table，
这点跟拓竹不一样，所以 official=False）。

为什么用 products.json 而不是爬 HTML：官方色号是这家最有价值的字段
（同一颜色在 PLA+ / PETG / ABS 下色号前缀不同：AC / G / ABS），
JSON 里结构化给全了，爬页面反而会漏。

两段式：先 `--fetch` 下载并缓存 JSON 与色片图，再 `--build` 生成 py 文件。
第二次跑不必重新联网（图片缓存在 raw/ 下）。

用法：
    python scripts/build_cailab_colors.py --fetch
    python scripts/build_cailab_colors.py --build
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "_cailab_src"
OUT = ROOT / "app" / "brand_colors_cailab.py"

PRODUCTS_URL = "https://www.cailab3d.com/products.json?limit=250"

# 只收 PLA / PETG 主系列（本系统的品牌色卡是按材料挂的，ABS/CF 等先不进）。
# key = products.json 里的标题关键字，value = (界面系列名, 材料, 变量名后缀)
#
# ⚠️ 变量名后缀必须**手写且唯一**，不能从系列名推：系列名里有「哑光 PLA / 丝绸 PLA /
# 三色丝绸 PLA / 金属 PLA」，自动把非字母数字换成下划线后全都变成 `PLA`，
# 几个变量互相覆盖 —— 表现为「每个系列都显示成同一个系列的色」。
SERIES_MAP = {
    "PLA Plus Filament (PLA+ Bio)": ("PLA+", "pla", "PLA_PLUS"),
    "Matte PLA Filament": ("哑光 PLA", "pla", "MATTE_PLA"),
    "PLA Silk Glossy Filament": ("丝绸 PLA", "pla", "SILK_PLA"),
    "Multicolor Color PLA Silk Filament": ("三色丝绸 PLA", "pla", "TRI_SILK_PLA"),
    "PLA Metallic Filament": ("金属 PLA", "pla", "METALLIC_PLA"),
    "PETG Filament": ("PETG", "petg", "PETG"),
    "PETG-CF Filament": ("PETG-CF", "petg", "PETG_CF"),
    "PLA-CF Filament": ("PLA-CF", "pla", "PLA_CF"),
}

# 三色/渐变色系（多色块交织）没有单一定义色，跳过取色、只留名字
MULTICOLOR_HINTS = ("&", "+", "Rainbow", "Shift", "Collection")

_CJK = re.compile(r"[\u4e00-\u9fff]")


def _fetch() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    dst = CACHE / "products.json"
    print(f"下载 {PRODUCTS_URL}")
    r = httpx.get(PRODUCTS_URL, timeout=60, follow_redirects=True)
    r.raise_for_status()
    dst.write_bytes(r.content)
    print(f"  已存 {dst}（{len(r.content)} 字节）")

    data = json.loads(r.content)
    want = _products(data)
    n = 0
    for prod in want:
        for _color, url in _color_images(prod):
            if not url:
                continue
            name = _img_name(url)
            target = CACHE / name
            if target.exists():
                continue
            try:
                ir = httpx.get(url, timeout=40, follow_redirects=True)
                if ir.status_code == 200:
                    target.write_bytes(ir.content)
                    n += 1
            except Exception as exc:  # noqa: BLE001
                print(f"  取图失败 {name}: {exc}")
    print(f"  色片图新增 {n} 张")


def _products(data: dict) -> list[dict]:
    out = []
    for p in data.get("products", []):
        for key in SERIES_MAP:
            if p["title"].startswith(key):
                out.append(p)
                break
    return out


def _img_name(url: str) -> str:
    return url.split("?")[0].rsplit("/", 1)[-1]


def _color_images(prod: dict) -> list[tuple[str, str]]:
    """返回 [(色名, 色片图 URL)]，按官方 variant 顺序。"""
    pairs: list[tuple[str, str]] = []
    for v in prod.get("variants", []):
        title = str(v.get("title") or "")
        # variant 标题形如 "Red AC199 / 1KG"，取第一段
        color = title.split(" / ")[0].strip()
        if not color or color.lower() == "default title":
            continue
        img = (v.get("featured_image") or {}).get("src") or ""
        src = img or _match_image(prod, color)
        if (color, src) not in pairs:
            pairs.append((color, src))
    return pairs


def _match_image(prod: dict, color: str) -> str:
    """variant 没带图时，去产品图里按色号（如 AC199）文件名找。"""
    code = ""
    m = re.search(r"\b([A-Z]{1,4}\d{2,6})\b", color)
    if m:
        code = m.group(1)
    for im in prod.get("images", []):
        src = im.get("src") or ""
        if code and code.lower() in src.lower():
            return src
    return ""


def _dominant_hex(path: Path) -> str:
    """从色片图取主色。

    官方色片图是「圆角色块 + 白底 + 少量文字水印」，直接取全图平均值会被白底冲淡，
    所以**取画面中心 1/3 区域的众数色**（色块本体），再对相似色做一次归并。
    """
    from PIL import Image

    with Image.open(path) as im:
        im = im.convert("RGB")
        w, h = im.size
        box = im.crop((w // 3, h // 3, w * 2 // 3, h * 2 // 3))
        box = box.resize((60, 60), Image.Resampling.BILINEAR)
        counts: dict[tuple[int, int, int], int] = {}
        for px in box.getdata():
            # 量化到 8 级，避免 JPEG/PNG 抗锯齿噪点把同一色拆成一堆近邻
            q = (px[0] // 8 * 8, px[1] // 8 * 8, px[2] // 8 * 8)
            counts[q] = counts.get(q, 0) + 1
    # 白底若不小心进了中心区，别把它当主色
    items = sorted(counts.items(), key=lambda kv: -kv[1])
    for (r, g, b), _c in items:
        if r > 235 and g > 235 and b > 235:
            continue
        return f"#{r:02X}{g:02X}{b:02X}"
    return "#CCCCCC"


def _split_name(color: str) -> tuple[str, str]:
    """把 "Red AC199" 拆成 (中文名, 英文名, 官方色号)。"""
    m = re.search(r"\b([A-Z]{1,4}\d{2,6})\b", color)
    code = m.group(1) if m else ""
    plain = re.sub(r"\b[A-Z]{1,4}\d{2,6}\b", "", color).strip(" -/")
    return plain, code


def build() -> int:
    src = CACHE / "products.json"
    if not src.exists():
        print(f"缺少 {src}，先跑 --fetch")
        return 1

    data = json.loads(src.read_bytes())
    blocks: list[str] = []
    stats: list[str] = []

    for prod in _products(data):
        key = next(k for k in SERIES_MAP if prod["title"].startswith(k))
        series, material, varname = SERIES_MAP[key]
        rows: list[str] = []
        for color, url in _color_images(prod):
            en, code = _split_name(color)
            if not en:
                continue
            # 整个「三色丝绸」系列都是多色交错，没有单一定义色。
            # 不能只按名字里有没有 &/+ 判断 —— Sakura white / Moonlight / SS001 这些
            # 名字里没有分隔符，会漏判、被取到一个根本不代表它的色值。
            is_multi = series == "三色丝绸 PLA" or any(h in color for h in MULTICOLOR_HINTS)
            if is_multi or not url:
                # 没有单一定义色的：用中性灰占位（只做名字候选），
                # 前端点色块仍能把颜色名填进去，不会留空
                hexv = "#CCCCCC"
            else:
                img = CACHE / _img_name(url)
                hexv = _dominant_hex(img) if img.exists() else "#CCCCCC"
            label = en + (f" {code}" if code else "")
            rows.append(f"    _c({label!r}, {en!r}, {hexv!r}),")
        if rows:
            var = f"CAILAB_{varname}"
            blocks.append(
                f"# 彩多屋 {series}（官方在售 {len(rows)} 色，来源 cailab3d.com）\n"
                f"{var}: list[dict] = [\n" + "\n".join(rows) + "\n]\n"
            )
            stats.append(f"{series}: {len(rows)} 色")

    header = '''"""彩多屋（CAILAB）官方配色预设 —— 由 scripts/build_cailab_colors.py 自动生成，勿手改。

数据来源：cailab3d.com 官方商城 `/products.json`（Shopify 结构化数据）。
- **色名与官方色号（AC199 / MT9003 / G419 …）是官方字段**，直接取自 variant 标题；
- **HEX 不是官方公布的**，是从官方逐色色片图取主色得到的**近似值** → official=False。
  取色方式见脚本 `_dominant_hex()`：量化后取中心区众数，避开白底与文字水印。
- 三色丝绸 / 彩虹渐变这类没有「单一定义色」的，HEX 留中性灰 #CCCCCC（只做名字候选，
  别当成真实颜色去比对），避免拿一个假色值去误导识色。

重新生成：
    python scripts/build_cailab_colors.py --fetch && python scripts/build_cailab_colors.py --build
"""


def _c(name: str, en: str, hex_value: str) -> dict:
    # 彩多屋不公布 Hex Code Table，全部按近似值处理
    return {"name": name or en, "en": en, "hex": hex_value, "official": False}


'''

    body = "\n".join(blocks)

    # 汇总成 BRAND_COLOR_SERIES_EXTRA / MATERIAL_COLOR_SERIES_EXTRA 供 catalog 合并
    var_lines = []
    for prod in _products(data):
        key = next(k for k in SERIES_MAP if prod["title"].startswith(k))
        series, _mat, varname = SERIES_MAP[key]
        var = f"CAILAB_{varname}"
        var_lines.append((series, var))

    seen: list[tuple[str, str]] = []
    for s, v in var_lines:
        if not any(s == s2 for s2, _ in seen):
            seen.append((s, v))

    extra = ['BRAND_COLOR_SERIES_EXTRA: dict[str, dict[str, list[dict]]] = {',
             '    "彩多屋": {']
    for s, v in seen:
        extra.append(f'        {s!r}: {v},')
    extra.append('    },')
    extra.append('}')
    extra.append('')
    extra.append('# 材料 -> 适用系列（PLA 挂 PLA 系，PETG 挂 PETG 系）')
    extra.append('MATERIAL_COLOR_SERIES_EXTRA: dict[str, list[str]] = {')
    pla = [s for s, _ in seen if 'PLA' in s or s == 'PLA+']
    petg = [s for s, _ in seen if 'PETG' in s]
    extra.append(f'    "PLA": {pla!r},')
    extra.append(f'    "PETG": {petg!r},')
    extra.append('}')
    extra.append('')

    OUT.write_bytes((header + body + "\n" + "\n".join(extra)).replace("\r\n", "\n").encode("utf-8"))
    print(f"已生成 {OUT}")
    for s in stats:
        print("  ", s)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="下载官方 JSON 与色片图到 data/_cailab_src")
    ap.add_argument("--build", action="store_true", help="用缓存生成 app/brand_colors_cailab.py")
    a = ap.parse_args()
    if not (a.fetch or a.build):
        ap.print_help()
        sys.exit(0)
    if a.fetch:
        _fetch()
    if a.build:
        sys.exit(build())
