"""颜色覆盖统计：官方色卡「应有什么颜色」对照库存「已入库什么颜色」。

口径（2026-11-16 定案，别改错）：
  - **应有色** = 色卡（BRAND_COLOR_SERIES）里这个品牌、这个材料、这些耗材系列
    登记的全部颜色。每个系列**只归一个材料**：显式 MATERIAL_COLOR_SERIES 优先
    （长材料键先认，PLA-CF 不会被 PLA 抢走），否则系列名前缀匹配最长材料键，
    再兜底「其他」。
    ⚠️ 绝不能对每种材料都调 `color_series_for()` 再汇总：material="PLA+" 会
    同时命中 "PLA" 和 "PLA+" 两个键，同一个 PLA 系列被算进三组 —— 实测
    4531 色被放大成 9978，界面上的「应有色」直接翻倍。
  - **已有色** = 在库料盘（archived=False）里能匹配到某个色卡颜色的色种。
    匹配优先中文/英文名（去空格、忽略大小写），再看 HEX 完全相同；
    一盘只算一个色（名称优先，避免同 HEX 的不同色互相串）。
  - **每种颜色的具体数量** = 该颜色对应的**料盘数**（不是余量、不是克重）。
    同一个色有 3 盘就记 3，但「已有色数」仍只算 1 种。
  - **缺色** = 色卡里有、库存里一盘都没有的颜色。已归档的盘不算「已有」。
  - 品牌用 `normalize_brand()` 归一（Bambu Lab → 拓竹）。料盘材料按最长前缀
    归到该品牌实际有的材料组（PLA+ / PETG-HF 归到 PLA / PETG）；查不到色卡的
    盘单独列出来，不硬塞进「其他」凑数 —— 自定义品牌本来就没有官方色卡可比。

这个模块只做纯计算、不碰 session，便于直接单测；接口在 routes 里包一层。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable

from .catalog import (
    BRAND_COLOR_SERIES,
    MATERIALS,
    MATERIAL_COLOR_SERIES,
    normalize_brand,
    normalize_color,
)


def _name_key(value: Any) -> str:
    """颜色名归一：去全部空白 + 忽略大小写。

    色卡名有「象牙 白 / 象牙白」、英文名有 "Cold White / coldwhite" 两种写法，
    不去空格会把同一个色误判成缺色。
    """
    return "".join(str(value or "").split()).casefold()


def _series_material(series_name: Any) -> str:
    """一个耗材系列 -> 唯一材料键。显式映射优先，长键先认。"""
    name = str(series_name or "").strip()
    norm = name.replace(" ", "").upper()
    for material in sorted(MATERIAL_COLOR_SERIES, key=len, reverse=True):
        if name in MATERIAL_COLOR_SERIES[material]:
            return material
    for material in sorted(set(MATERIALS) | set(MATERIAL_COLOR_SERIES),
                           key=len, reverse=True):
        if norm.startswith(material.replace(" ", "").upper()):
            return material
    return "其他"


def _spool_material(value: Any, available: Iterable[str]) -> str | None:
    """料盘材料 -> 该品牌实际存在的材料组（最长前缀）。

    PLA+ 在只有 PLA 系列的品牌里要归到 PLA 组，否则用户明明有 PLA+ 的黑色盘，
    统计却说 PLA 缺黑色。available 只传这个品牌真正有的材料组。
    """
    text = str(value or "").strip().upper().replace(" ", "")
    if not text:
        return None
    for material in sorted(set(available), key=len, reverse=True):
        if material == "其他":
            continue
        if text.startswith(material.replace(" ", "").upper()):
            return material
    # 不要把 PLA/PA 这类盘兜进「其他」组：那个组里是 PolySmooth 等系列，
    # 同名色（黑色）会被误认成已有，统计就假绿了。
    return None


def build_color_stats(spools: Iterable[Any]) -> dict:
    """按 品牌 -> 材料 -> 色卡系列 统计颜色覆盖。"""
    live = [s for s in spools if not getattr(s, "archived", False)]

    stock_by_brand: dict[str, list[Any]] = defaultdict(list)
    for spool in live:
        stock_by_brand[normalize_brand(getattr(spool, "brand", ""))].append(spool)

    brands_out: list[dict] = []
    seen_colors: set[tuple[str, str]] = set()
    seen_owned: set[tuple[str, str]] = set()
    # 记对象身份而不是「品牌+材料+色名」三元组：同名同色的两盘里可能只有一盘
    # 真正命中色卡（另一盘材料不同），用三元组会把没命中的那盘也误记为已匹配。
    matched_ids: set[int] = set()

    for brand, series_map in BRAND_COLOR_SERIES.items():
        buckets: dict[str, list[tuple[str, list[dict]]]] = defaultdict(list)
        for series_name, colors in series_map.items():
            if colors:
                buckets[_series_material(series_name)].append((series_name, colors))
        if not buckets:
            continue

        brand_stock = stock_by_brand.get(brand, [])
        materials_out: list[dict] = []

        for material in sorted(buckets):
            groups = buckets[material]

            # 同一颜色可能在多个系列里重复出现（例：不同系列的「黑色」）。
            # 按颜色名归并成一行，series 字段记第一次出现的那个系列。
            catalog: list[dict] = []
            by_key: dict[str, dict] = {}
            for series_name, colors in groups:
                for color in colors:
                    name = str(color.get("name") or "").strip()
                    hexv = normalize_color(color.get("hex"))
                    key = _name_key(name) or hexv
                    if not key or (key == "#000000" and not name):
                        continue
                    item = by_key.get(key)
                    if item is None:
                        item = {
                            "name": name or str(color.get("en") or "") or "未命名",
                            "en": str(color.get("en") or ""),
                            "hex": hexv,
                            "series": series_name,
                            "official": bool(color.get("official", True)),
                            "count": 0,
                            "keys": set(),
                        }
                        by_key[key] = item
                        catalog.append(item)
                    for candidate in (name, color.get("en"), hexv):
                        norm = _name_key(candidate) if candidate != hexv else hexv
                        if norm:
                            item["keys"].add(norm)

            if not catalog:
                continue

            # 库存匹配：名称优先，HEX 兜底；一盘只认一个色。
            for spool in brand_stock:
                if _spool_material(getattr(spool, "material", ""), buckets) != material:
                    continue
                name = _name_key(getattr(spool, "color_name", ""))
                hexv = normalize_color(getattr(spool, "color_hex", ""))
                hit = None
                if name:
                    hit = next((c for c in catalog if name in c["keys"]), None)
                if hit is None and hexv and hexv != "#000000":
                    hit = next((c for c in catalog if hexv in c["keys"]), None)
                if hit is None:
                    continue
                hit["count"] += 1
                matched_ids.add(id(spool))

            owned = [c for c in catalog if c["count"] > 0]
            missing = [c for c in catalog if c["count"] == 0]
            for c in catalog:
                key = _name_key(c["name"]) or c["hex"]
                seen_colors.add((brand, key))
                if c["count"] > 0:
                    seen_owned.add((brand, key))
                c.pop("keys", None)  # set 不能直接 JSON 序列化

            materials_out.append({
                "material": material,
                "series": [s for s, _ in groups],
                "catalog_count": len(catalog),
                "owned_count": len(owned),
                "missing_count": len(missing),
                "coverage": round(len(owned) / len(catalog) * 100, 1) if catalog else 0.0,
                "owned": owned,
                "missing": missing,
            })

        if not materials_out:
            continue
        brands_out.append({
            "brand": brand,
            "materials": materials_out,
            "catalog_count": sum(m["catalog_count"] for m in materials_out),
            "owned_count": sum(m["owned_count"] for m in materials_out),
            "missing_count": sum(m["missing_count"] for m in materials_out),
        })

    # 没有官方色卡可比的盘：按 品牌/材料/颜色 聚合，别悄悄丢掉
    unmatched: dict[tuple[str, str, str], int] = defaultdict(int)
    for spool in live:
        if id(spool) in matched_ids:
            continue
        brand = normalize_brand(getattr(spool, "brand", ""))
        material = getattr(spool, "material", "") or "未填写"
        color = getattr(spool, "color_name", "") or "未填写"
        unmatched[(brand, material, color)] += 1
    unmatched_out = [
        {"brand": b, "material": m, "color_name": c, "count": n}
        for (b, m, c), n in sorted(unmatched.items(), key=lambda kv: -kv[1])
    ]

    total_catalog = len(seen_colors)
    total_owned = len(seen_owned)
    return {
        "totals": {
            "brand_count": len(brands_out),
            "group_count": sum(len(b["materials"]) for b in brands_out),
            "catalog_count": total_catalog,           # 去重后的色种（同名跨材料只算一次）
            "catalog_entries": sum(sum(m["catalog_count"] for m in b["materials"])
                                   for b in brands_out),  # 各组条目之和
            "owned_count": total_owned,
            "missing_count": max(0, total_catalog - total_owned),
            "coverage": round(total_owned / total_catalog * 100, 1) if total_catalog else 0.0,
            "spool_count": len(live),
            "matched_spool_count": len(matched_ids),
            "unmatched_spool_count": sum(x["count"] for x in unmatched_out),
        },
        "brands": brands_out,
        "unmatched": unmatched_out,
    }
