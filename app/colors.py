"""色彩工具与配色匹配。

为什么不是简单的 RGB 欧氏距离：RGB 空间的距离和人眼感知不成正比——同样是
RGB 差 30，深蓝之间的差别肉眼几乎看不出来，而绿色之间已经明显不是一个色。
所以统一转到 CIE Lab，用 **CIEDE2000** 算色差（ΔE00，小于 1 基本看不出差别，
2 以内算同色，5 左右能看出但接近，10 以上是两种颜色）。

图像本身的主色提取放在前端（Canvas），这里只接收若干 HEX 做匹配——好处是
容器不用装 Pillow，且用户可以在浏览器里用吸管微调后再发请求。
"""
from __future__ import annotations

import math
from typing import Iterable, Iterator

from .catalog import (
    BRAND_COLOR_SERIES,
    MATERIAL_COLOR_SERIES,
)

# ── sRGB ↔ CIE Lab ────────────────────────────────────────────
# D65 白点
_WHITE = (0.95047, 1.00000, 1.08883)
_DELTA = 6.0 / 29.0


def parse_hex(value: str) -> tuple[int, int, int] | None:
    """宽松解析 #RGB / #RRGGBB / RRGGBB / #RRGGBBAA，失败返回 None。"""
    if not value:
        return None
    text = str(value).strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) < 6:
        return None
    text = text[:6]
    try:
        return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))
    except ValueError:
        return None


def normalize_hex(value: str) -> str:
    rgb = parse_hex(value)
    if rgb is None:
        return "#000000"
    return "#%02X%02X%02X" % rgb


def _srgb_channel(value: int) -> float:
    c = value / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def rgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    """sRGB(0-255) → CIE Lab（D65）。"""
    r, g, b = (_srgb_channel(v) for v in rgb)
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b

    def f(t: float) -> float:
        return t ** (1.0 / 3.0) if t > _DELTA ** 3 else t / (3 * _DELTA ** 2) + 4.0 / 29.0

    fx, fy, fz = f(x / _WHITE[0]), f(y / _WHITE[1]), f(z / _WHITE[2])
    return (116.0 * fy - 16.0, 500.0 * (fx - fy), 200.0 * (fy - fz))


def hex_to_lab(value: str) -> tuple[float, float, float] | None:
    rgb = parse_hex(value)
    if rgb is None:
        return None
    return rgb_to_lab(rgb)


def delta_e00(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
    k_l: float = 1.0,
    k_c: float = 1.0,
    k_h: float = 1.0,
) -> float:
    """CIEDE2000 色差。典型量级：<1 看不出，2 同色，5 接近，>10 明显不同。

    实现遵循 Sharma / Wu / Dalal (2005) 的参考公式，已用该论文的 34 组标准
    测试向量校验（见 tests/test_color.py）。
    """
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2

    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2.0
    c_bar7 = c_bar ** 7
    g = 0.5 * (1.0 - math.sqrt(c_bar7 / (c_bar7 + 25.0 ** 7)))

    a1p = (1.0 + g) * a1
    a2p = (1.0 + g) * a2
    c1p = math.hypot(a1p, b1)
    c2p = math.hypot(a2p, b2)

    h1p = 0.0 if (a1p == 0 and b1 == 0) else math.degrees(math.atan2(b1, a1p)) % 360.0
    h2p = 0.0 if (a2p == 0 and b2 == 0) else math.degrees(math.atan2(b2, a2p)) % 360.0

    d_lp = l2 - l1
    d_cp = c2p - c1p

    if c1p * c2p == 0:
        d_hp = 0.0
    elif abs(h2p - h1p) <= 180.0:
        d_hp = h2p - h1p
    elif h2p - h1p > 180.0:
        d_hp = h2p - h1p - 360.0
    else:
        d_hp = h2p - h1p + 360.0

    d_big_h = 2.0 * math.sqrt(c1p * c2p) * math.sin(math.radians(d_hp / 2.0))

    l_bar = (l1 + l2) / 2.0
    c_barp = (c1p + c2p) / 2.0

    if c1p * c2p == 0:
        h_barp = h1p + h2p
    elif abs(h1p - h2p) <= 180.0:
        h_barp = (h1p + h2p) / 2.0
    elif h1p + h2p < 360.0:
        h_barp = (h1p + h2p + 360.0) / 2.0
    else:
        h_barp = (h1p + h2p - 360.0) / 2.0

    t = (
        1.0
        - 0.17 * math.cos(math.radians(h_barp - 30.0))
        + 0.24 * math.cos(math.radians(2.0 * h_barp))
        + 0.32 * math.cos(math.radians(3.0 * h_barp + 6.0))
        - 0.20 * math.cos(math.radians(4.0 * h_barp - 63.0))
    )
    d_theta = 30.0 * math.exp(-(((h_barp - 275.0) / 25.0) ** 2))
    r_c = 2.0 * math.sqrt(c_barp ** 7 / (c_barp ** 7 + 25.0 ** 7))
    s_l = 1.0 + (0.015 * (l_bar - 50.0) ** 2) / math.sqrt(20.0 + (l_bar - 50.0) ** 2)
    s_c = 1.0 + 0.045 * c_barp
    s_h = 1.0 + 0.015 * c_barp * t
    r_t = -math.sin(math.radians(2.0 * d_theta)) * r_c

    term_l = d_lp / (k_l * s_l)
    term_c = d_cp / (k_c * s_c)
    term_h = d_big_h / (k_h * s_h)
    return math.sqrt(term_l ** 2 + term_c ** 2 + term_h ** 2 + r_t * term_c * term_h)


def delta_e_hex(hex1: str, hex2: str) -> float | None:
    lab1, lab2 = hex_to_lab(hex1), hex_to_lab(hex2)
    if lab1 is None or lab2 is None:
        return None
    return delta_e00(lab1, lab2)


# ── 匹配等级 ──────────────────────────────────────────────────
# (ΔE00 上界, 文字说明)。数值参考 CIEDE2000 的常用经验阈值。
_MATCH_LEVELS = (
    (1.0, "几乎一致"),
    (2.0, "同色"),
    (4.0, "非常接近"),
    (8.0, "接近"),
    (15.0, "略有差异"),
)


def match_level(delta_e: float) -> str:
    for bound, label in _MATCH_LEVELS:
        if delta_e < bound:
            return label
    return "差异明显"


def match_percent(delta_e: float) -> int:
    """把 ΔE 折成 0-100 的相似度，仅用于界面直观排序展示。

    以 ΔE00=20 视作完全不同做线性压缩；这是展示口径，不是严格的色度学结论。
    """
    return max(0, min(100, int(round(100.0 * (1.0 - min(delta_e, 20.0) / 20.0)))))


# ── 色卡索引 ──────────────────────────────────────────────────
# 色卡是静态数据，Lab 值算一次缓存起来即可。
_CATALOG_INDEX: dict[str, list[dict]] | None = None


def catalog_index() -> dict[str, list[dict]]:
    """按材料名归类、并预先算好 Lab 的完整色卡索引。

    返回 {材料名: [条目...]}；另有特殊键 "*" 保存全部条目（材料筛选为空时用）。
    """
    global _CATALOG_INDEX
    if _CATALOG_INDEX is not None:
        return _CATALOG_INDEX

    buckets: dict[str, list[dict]] = {}
    everything: list[dict] = []

    for brand, series_map in BRAND_COLOR_SERIES.items():
        for series_name, colors in series_map.items():
            for color in colors:
                hex_value = normalize_hex(color.get("hex", ""))
                lab = hex_to_lab(hex_value)
                if lab is None:
                    continue
                entry = {
                    "brand": brand,
                    "series": series_name,
                    "name": color.get("name", ""),
                    "en": color.get("en", ""),
                    "hex": hex_value,
                    "official": bool(color.get("official", True)),
                    # 多色交织料（三色丝绸）：色值只是「从料饼图上取的其中一个主色」，
                    # 不代表整盘料的颜色。**必须排除在识色匹配之外** ——
                    # 否则拍一张红色照片会推出一盘红黑金三色料，看着像对上了、其实是错的。
                    # 界面照样显示它（点色块能把颜色名填进去），只是不拿它去比 ΔE。
                    "multicolor": bool(color.get("hex2")),
                    "lab": lab,
                }
                everything.append(entry)

    # 材料 → 系列名的映射是全局的（系列名在不同品牌下可重名），
    # 所以这里按「材料 → 该材料允许的系列名集合」反查。
    for material, series_names in MATERIAL_COLOR_SERIES.items():
        allowed = set(series_names)
        buckets[material] = [e for e in everything if e["series"] in allowed]

    buckets["*"] = everything
    _CATALOG_INDEX = buckets
    return buckets


def _catalog_entries(material: str = "", brands: Iterable[str] | None = None) -> list[dict]:
    index = catalog_index()
    mat = (material or "").strip().upper()
    if mat:
        # 与 color_series_for() 保持一致：前缀匹配，PLA 命中 PLA / PLA-CF 等
        pool: list[dict] = []
        seen: set[int] = set()
        for key, entries in index.items():
            if key == "*" or not mat.startswith(key):
                continue
            for entry in entries:
                if id(entry) not in seen:
                    seen.add(id(entry))
                    pool.append(entry)
    else:
        pool = list(index["*"])

    want = {b.strip() for b in brands or [] if b and b.strip()}
    if want:
        pool = [e for e in pool if e["brand"] in want]
    return pool


def _public(entry: dict, delta_e: float) -> dict:
    return {
        "brand": entry["brand"],
        "series": entry["series"],
        "name": entry["name"],
        "en": entry.get("en", ""),
        "hex": entry["hex"],
        "official": entry.get("official", True),
        "delta_e": round(delta_e, 2),
        "percent": match_percent(delta_e),
        "level": match_level(delta_e),
    }


# ── 匹配 ──────────────────────────────────────────────────────
def match_catalog(
    hex_value: str,
    material: str = "",
    brands: Iterable[str] | None = None,
    limit: int = 6,
    max_delta_e: float = 15.0,
) -> list[dict]:
    """在品牌官方色卡里找最接近的颜色。

    ⚠️ 多色交织料（`multicolor`，如三色丝绸）**不参与匹配**：它们的 hex 是从料饼图
    上取的其中一个主色，不代表整盘的颜色；让它参与的话，拍一张红色照片会推出
    一盘红黑金三色料，看着像对上了、其实是错的。界面里它照常显示。
    """
    lab = hex_to_lab(hex_value)
    if lab is None:
        return []
    scored = []
    for entry in _catalog_entries(material, brands):
        if entry.get("multicolor"):
            continue
        distance = delta_e00(lab, entry["lab"])
        if distance <= max_delta_e:
            scored.append((distance, entry))
    scored.sort(key=lambda item: item[0])
    return [_public(entry, distance) for distance, entry in scored[:limit]]


def match_inventory(
    hex_value: str,
    spools: Iterable,
    material: str = "",
    brands: Iterable[str] | None = None,
    limit: int = 6,
    max_delta_e: float = 15.0,
    include_archived: bool = False,
) -> list[dict]:
    """在自家料盘里找最接近的那几盘。spools 传 Spool 模型对象序列。"""
    lab = hex_to_lab(hex_value)
    if lab is None:
        return []

    mat = (material or "").strip().upper()
    want = {b.strip() for b in brands or [] if b and b.strip()}
    scored = []
    for spool in spools:
        if getattr(spool, "archived", False) and not include_archived:
            continue
        if mat and not str(getattr(spool, "material", "")).upper().startswith(mat):
            continue
        if want and getattr(spool, "brand", "") not in want:
            continue
        spool_lab = hex_to_lab(normalize_hex(getattr(spool, "color_hex", "")))
        if spool_lab is None:
            continue
        distance = delta_e00(lab, spool_lab)
        if distance <= max_delta_e:
            scored.append((distance, spool))

    scored.sort(key=lambda item: (item[0], -float(getattr(item[1], "remaining_weight", 0) or 0)))
    out = []
    for distance, spool in scored[:limit]:
        out.append({
            "spool_id": spool.id,
            "name": spool.name,
            "brand": spool.brand,
            "material": spool.material,
            "color_name": spool.color_name,
            "hex": normalize_hex(spool.color_hex),
            "remaining_weight": round(float(spool.remaining_weight or 0), 1),
            "remaining_percent": spool.remaining_percent,
            "is_low": spool.is_low,
            "location": spool.location or "",
            "delta_e": round(distance, 2),
            "percent": match_percent(distance),
            "level": match_level(distance),
        })
    return out


def recommend_brands(matches: Iterable[dict]) -> list[dict]:
    """把色卡匹配结果按品牌收拢，每个品牌只留最接近的那一个色。

    这就是「这个颜色该买哪个品牌」的答案：列表按色差升序，
    第一项就是最接近的品牌与色号。
    """
    best: dict[str, dict] = {}
    for item in matches:
        current = best.get(item["brand"])
        if current is None or item["delta_e"] < current["delta_e"]:
            best[item["brand"]] = item
    return sorted(best.values(), key=lambda item: item["delta_e"])


def resolve_colors(payload_colors: Iterable) -> list[dict]:
    """把入参里的颜色统一成 {hex, weight} 列表，顺手去重与归一化权重。"""
    collected: dict[str, float] = {}
    order: list[str] = []
    for item in payload_colors:
        if isinstance(item, str):
            raw, weight = item, 1.0
        else:
            raw = getattr(item, "hex", None) or (item.get("hex") if isinstance(item, dict) else "")
            weight = getattr(item, "weight", None)
            if weight is None and isinstance(item, dict):
                weight = item.get("weight", 1.0)
            weight = 1.0 if weight is None else float(weight)
        rgb = parse_hex(raw or "")
        if rgb is None:
            continue
        key = "#%02X%02X%02X" % rgb
        if key not in collected:
            collected[key] = 0.0
            order.append(key)
        collected[key] += max(0.0, weight)

    total = sum(collected.values()) or 1.0
    return [
        {"hex": key, "weight": round(collected[key] / total, 4), "lab": list(hex_to_lab(key) or ())}
        for key in order
    ]


def palettes_for_brands(brands: Iterable[str], material: str = "") -> dict[str, int]:
    """各品牌在当前材料下有多少个可选色，用于给「换品牌」提供参考。"""
    counts: dict[str, int] = {}
    for entry in _catalog_entries(material, brands):
        counts[entry["brand"]] = counts.get(entry["brand"], 0) + 1
    return counts


def iter_catalog_summary() -> Iterator[tuple[str, int]]:
    """(品牌, 色数) 概览。"""
    counts: dict[str, int] = {}
    for entry in catalog_index()["*"]:
        counts[entry["brand"]] = counts.get(entry["brand"], 0) + 1
    for brand in sorted(counts, key=lambda b: -counts[b]):
        yield brand, counts[brand]
