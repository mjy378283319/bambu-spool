"""库存颜色统计：按 品牌 → 材料 → 外观系列，列出**当前有库存**的颜色与缺色。

口径（2026-11-16 第三版，用户改口后定案，别改回去）：
  - 只统计 `archived=False` 且 `remaining_weight > 0` 的料盘 —— 已归档、已用尽的
    都不算「有库存」，否则统计里会冒出一堆「买了但用完了」的色，和用户直觉不符。
  - **没买过的外观整体不显示**（用户原话「未购买或库存为零的耗材不显示」）；
    但只要这个外观买过至少一个色，就把**该外观色卡里还没入库的颜色**列出来，
    并给出 总数 / 已有 / 缺失 三个数（用户 2026-11-16 第二次要求）。
  - **PLA 必须按外观拆分**：`PLA Basic / PLA Matte / PLA Silk / PLA Wood …`
    各自一行，不能把所有 PLA 系列合并成一行。分组键就是色卡系列名。
  - 每个系列**只归一个材料**：显式 MATERIAL_COLOR_SERIES 优先（长材料键先认，
    PLA-CF 不被 PLA 抢走），否则系列名前缀匹配最长材料键，再兜底「其他」。
  - 颜色匹配优先中文/英文名（去空格、忽略大小写），再 HEX 完全相同；
    一盘只算一个色、且只归一个系列（按外观顺序先命中先得），数量 = 料盘数。
  - 品牌用 `normalize_brand()` 归一（Bambu Lab → 拓竹）；料盘材料按最长前缀
    归到该品牌实际有的材料组（PLA+ / PETG-HF 归到 PLA / PETG）。

★ 总数 / 已有 / 缺失 的层级口径：
  外观系列层 = 该系列自己的色卡（去重后）；
  材料层 / 品牌层 = **已显示外观的色卡并集去重**（「黑色」同时在 Basic 和 Matte
  里只算一次），否则合计会虚高，用户会以为自己缺了一倍的色。

展示顺序（前端照这个顺序渲染，别在 JS 里另排一套）：
  品牌：按有库存的颜色种数降序，再按名称；
  材料：按 MATERIALS 的固定顺序（PLA → PETG → ABS → …）；
  系列/外观：Basic(普通) → Matte(哑光) → Silk(丝绸) → Galaxy(星空) →
            Marble(大理石) → Wood(木纹) → Metal(金属) → Sparkle(珠光) →
            Glow(夜光) → Translucent(半透) → CF(碳纤) → 其他。

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
    normalize_finish,
)

# 系列名关键词 -> 中文外观名。**顺序敏感**：具体词必须排在泛化词前，
# 否则「PLA Basic」会被后面的规则抢先。最后一个 ("pla",) 是纯 PLA 系列的兜底。
SERIES_FINISH_RULES: list[tuple[tuple[str, ...], str]] = [
    (("basic", "基础", "标准", "standard"), "普通"),
    (("matte", "哑光"), "哑光"),
    (("silk", "丝绸"), "丝绸"),
    (("galaxy", "星空"), "星空"),
    (("marble", "大理石"), "大理石"),
    (("wood", "木纹"), "木纹"),
    (("metal", "金属"), "金属"),
    (("sparkle", "闪粉", "珠光"), "珠光"),
    (("glow", "夜光", "luminous"), "夜光"),
    (("translucent", "半透", "透明"), "半透"),
    (("cf", "碳纤"), "碳纤"),
    # 没有外观修饰词的基础系列：PETG / ABS / ASA / PC / TPU / PVA …
    (("petg", "abs", "asa", "pc", "tpu", "pva", "hips", "pps"), "普通"),
    # 纯 PLA（Panchroma PLA 这类）也是普通外观，权重与 PLA Basic 一致
    (("pla",), "普通"),
]

MATERIAL_ORDER = {name: i for i, name in enumerate(MATERIALS)}


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


def _series_finish(series_name: Any) -> tuple[str, int]:
    """系列名 -> (中文外观, 排序权重)。权重越小越靠前。"""
    low = str(series_name or "").casefold()
    for index, (words, label) in enumerate(SERIES_FINISH_RULES):
        if any(word in low for word in words):
            # 「普通」不分先后：Basic、Panchroma PLA、PETG 都排在第一梯队，
            # 不能因为兜底规则在列表末尾就排到所有特殊外观后面。
            return label, 10 if label == "普通" else (index + 1) * 10
    return "其他", 900


def _spool_material(value: Any, available: Iterable[str]) -> str | None:
    """料盘材料 -> 该品牌实际存在的材料组（最长前缀）。

    PLA+ 在只有 PLA 系列的品牌里要归到 PLA 组；但**不要**把 PLA/PA 兜进
    「其他」组 —— 那个组里是 PolySmooth 等系列，同名色会被误认成已有。
    """
    text = str(value or "").strip().upper().replace(" ", "")
    if not text:
        return None
    for material in sorted(set(available), key=len, reverse=True):
        if material == "其他":
            continue
        if text.startswith(material.replace(" ", "").upper()):
            return material
    return None


def _has_stock(spool: Any) -> bool:
    if getattr(spool, "archived", False):
        return False
    try:
        return float(getattr(spool, "remaining_weight", 0) or 0) > 0
    except (TypeError, ValueError):
        return False


def build_color_stats(spools: Iterable[Any]) -> dict:
    """按 品牌 → 材料 → 外观系列 统计有库存的颜色。"""
    live = [s for s in spools if _has_stock(s)]

    stock_by_brand: dict[str, list[Any]] = defaultdict(list)
    for spool in live:
        stock_by_brand[normalize_brand(getattr(spool, "brand", ""))].append(spool)

    brands_out: list[dict] = []
    seen_colors: set[tuple[str, str]] = set()
    all_catalog: set[tuple[str, str]] = set()
    matched_ids: set[int] = set()

    for brand, series_map in BRAND_COLOR_SERIES.items():
        brand_stock = stock_by_brand.get(brand, [])
        if not brand_stock:
            continue

        # 先把该品牌的系列按材料分桶，并在桶内按外观顺序排好
        buckets: dict[str, list[tuple[int, str, list[dict]]]] = defaultdict(list)
        for series_name, colors in series_map.items():
            if not colors:
                continue
            finish, order = _series_finish(series_name)
            buckets[_series_material(series_name)].append((order, series_name, colors))
        if not buckets:
            continue
        for bucket in buckets.values():
            bucket.sort(key=lambda item: (item[0], item[1]))

        materials_out: list[dict] = []
        brand_catalog: set[str] = set()
        brand_owned: set[str] = set()
        for material in sorted(buckets, key=lambda m: (MATERIAL_ORDER.get(m, 999), m)):
            # 每个系列单独建颜色索引：只统计这个系列自己的色卡颜色
            series_defs: list[dict] = []
            for order, series_name, colors in buckets[material]:
                catalog: list[dict] = []
                by_key: dict[str, dict] = {}
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
                series_defs.append({
                    "series": series_name,
                    "finish": _series_finish(series_name)[0],
                    "order": order,
                    "catalog": catalog,
                })

            if not series_defs:
                continue

            # 匹配：一个盘只归一个系列（按外观顺序先命中先得），避免同一盘
            # 在 PLA Basic 和 PLA Matte 里被各算一次。
            for spool in brand_stock:
                if id(spool) in matched_ids:
                    continue
                if _spool_material(getattr(spool, "material", ""), buckets) != material:
                    continue
                name = _name_key(getattr(spool, "color_name", ""))
                hexv = normalize_color(getattr(spool, "color_hex", ""))
                # 同名色常同时出现在 Basic / Matte / Aero 几个系列里，光按名称匹配
                # 会把哑光黑算进 PLA Basic。先按料盘的「外观」字段归到同外观系列，
                # 同外观里再优先 Basic（最常见、最通用），最后才按展示顺序。
                spool_finish = normalize_finish(getattr(spool, "finish", "")) or "普通"
                ordered = sorted(series_defs, key=lambda d: (
                    0 if d["finish"] == spool_finish else 1,
                    0 if "basic" in d["series"].casefold() else 1,
                    d["order"], d["series"],
                ))
                for definition in ordered:
                    catalog = definition["catalog"]
                    hit = None
                    if name:
                        hit = next((c for c in catalog if name in c["keys"]), None)
                    if hit is None and hexv and hexv != "#000000":
                        hit = next((c for c in catalog if hexv in c["keys"]), None)
                    if hit is None:
                        continue
                    hit["count"] += 1
                    # 记下具体是哪几盘：前端色块要能点进去看/改这盘料。
                    # 只存 id，不存对象 —— 统计接口的返回要能直接 JSON 序列化。
                    sid = getattr(spool, "id", None)
                    if sid is not None:
                        hit.setdefault("spool_ids", []).append(sid)
                    definition["spool_count"] = definition.get("spool_count", 0) + 1
                    matched_ids.add(id(spool))
                    break

            series_out: list[dict] = []
            material_catalog: dict[str, dict] = {}
            material_owned: set[str] = set()
            for definition in series_defs:
                owned = [c for c in definition["catalog"] if c["count"] > 0]
                if not owned:
                    continue  # 没买过的外观不显示
                for c in owned:
                    c.pop("keys", None)
                    key = _name_key(c["name"]) or c["hex"]
                    seen_colors.add((brand, key))
                    material_owned.add(key)
                # 该外观的完整色卡（去重后）与未入库的颜色
                for c in definition["catalog"]:
                    key = _name_key(c["name"]) or c["hex"]
                    material_catalog.setdefault(key, {"name": c["name"], "hex": c["hex"]})
                missing = [
                    {"name": c["name"], "en": c["en"], "hex": c["hex"]}
                    for c in definition["catalog"] if c["count"] <= 0
                ]
                series_out.append({
                    "series": definition["series"],
                    "finish": definition["finish"],
                    "order": definition["order"],
                    "catalog_count": len(definition["catalog"]),
                    "color_count": len(owned),
                    "missing_count": len(missing),
                    "spool_count": sum(c["count"] for c in owned),
                    "colors": owned,
                    "missing": missing,
                })

            if not series_out:
                continue
            brand_catalog.update(material_catalog)
            brand_owned.update(material_owned)
            materials_out.append({
                "material": material,
                "catalog_count": len(material_catalog),
                "color_count": len(material_owned),
                "missing_count": len(material_catalog) - len(material_owned),
                "spool_count": sum(s["spool_count"] for s in series_out),
                "series": series_out,
            })

        if not materials_out:
            continue
        all_catalog.update((brand, key) for key in brand_catalog)
        brands_out.append({
            "brand": brand,
            "material_count": len(materials_out),
            "series_count": sum(len(m["series"]) for m in materials_out),
            "catalog_count": len(brand_catalog),
            "color_count": len(brand_owned),
            "missing_count": len(brand_catalog) - len(brand_owned),
            "spool_count": sum(m["spool_count"] for m in materials_out),
            "materials": materials_out,
        })

    # 有库存但没有官方色卡可比的盘：单列，不硬塞进统计
    # 键 -> 料盘 id 列表（不存对象，接口要能直接 JSON 序列化）。
    # 前端拿这些 id 把「没有官方色卡」的条目点进料盘详情，否则这栏只是死名单。
    unmatched: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for spool in live:
        if id(spool) in matched_ids:
            continue
        brand = normalize_brand(getattr(spool, "brand", ""))
        material = getattr(spool, "material", "") or "未填写"
        color = getattr(spool, "color_name", "") or "未填写"
        sid = getattr(spool, "id", None)
        unmatched[(brand, material, color)].append(sid)
    unmatched_out = [
        {
            "brand": b,
            "material": m,
            "color_name": c,
            "count": len(ids),
            "spool_ids": [sid for sid in ids if sid is not None],
        }
        for (b, m, c), ids in sorted(unmatched.items(), key=lambda kv: -len(kv[1]))
    ]

    # 品牌按「有库存的颜色种数」降序，其次是料盘数
    brands_out.sort(key=lambda b: (-b["color_count"], -b["spool_count"], b["brand"]))
    return {
        "totals": {
            "brand_count": len(brands_out),
            "material_count": sum(len(b["materials"]) for b in brands_out),
            "series_count": sum(b["series_count"] for b in brands_out),
            # 色卡口径与统计口径同源：只算「已经买过至少一个色的外观」，
            # 没买过的外观整个不进统计，别在这里把它算成「缺失」。
            "catalog_count": len(all_catalog),
            "color_count": len(seen_colors),
            "missing_count": len(all_catalog) - len(seen_colors),
            "spool_count": len(matched_ids),
            "unmatched_spool_count": sum(x["count"] for x in unmatched_out),
        },
        "brands": brands_out,
        "unmatched": unmatched_out,
    }
