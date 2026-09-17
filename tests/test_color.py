"""图片识色的配色匹配测试。

分两层：
  1. 纯逻辑——CIEDE2000 用 Sharma/Wu/Dalal (2005) 的 34 组标准测试向量校验，
     这是色差公式能否用于「找同色耗材」的前提。
  2. HTTP 端到端——真起一个 uvicorn，建管理员、登录，打 /api/color/match。

运行： python tests/test_color.py
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
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


# ══ 1. 色值解析 ════════════════════════════════════════════════
section("1. 色值解析与归一化")

from app.catalog import BRAND_PRESETS, normalize_brand  # noqa: E402

from app.colors import (  # noqa: E402
    catalog_index,
    delta_e00,
    delta_e_hex,
    hex_to_lab,
    match_catalog,
    match_inventory,
    match_level,
    match_percent,
    normalize_hex,
    parse_hex,
    recommend_brands,
    resolve_colors,
    rgb_to_lab,
)

check("#RRGGBB 解析", parse_hex("#3a7d44") == (0x3A, 0x7D, 0x44))
check("不带 # 也能解析", parse_hex("3A7D44") == (0x3A, 0x7D, 0x44))
check("#RGB 简写展开", parse_hex("#abc") == (0xAA, 0xBB, 0xCC))
check("带 Alpha 只取前六位", parse_hex("#3A7D4480") == (0x3A, 0x7D, 0x44))
check("乱码返回 None", parse_hex("zzz") is None and parse_hex("") is None)
check("归一化成大写", normalize_hex("#3a7d44") == "#3A7D44")
check("非法色值兜底为黑", normalize_hex("nope") == "#000000")


# ══ 2. sRGB → Lab ══════════════════════════════════════════════
section("2. sRGB → CIE Lab 基准值")

white = rgb_to_lab((255, 255, 255))
black = rgb_to_lab((0, 0, 0))
check("白色 L*≈100", abs(white[0] - 100.0) < 0.01, f"L={white[0]:.4f}")
check("白色 a*,b*≈0", abs(white[1]) < 0.01 and abs(white[2]) < 0.01,
      f"a={white[1]:.4f} b={white[2]:.4f}")
check("黑色 L*=0", abs(black[0]) < 1e-9 and abs(black[1]) < 1e-9)
check("中灰 L*≈53.6", abs(rgb_to_lab((128, 128, 128))[0] - 53.585) < 0.05,
      f"L={rgb_to_lab((128,128,128))[0]:.3f}")
# 纯红 sRGB 的 Lab 参考值约 (53.24, 80.09, 67.20)
red = rgb_to_lab((255, 0, 0))
check("纯红 Lab 对齐参考值", abs(red[0] - 53.24) < 0.1 and abs(red[1] - 80.09) < 0.15
      and abs(red[2] - 67.20) < 0.15, f"({red[0]:.2f}, {red[1]:.2f}, {red[2]:.2f})")


# ══ 3. CIEDE2000（Sharma 标准向量） ════════════════════════════
section("3. CIEDE2000 对照 Sharma 标准测试向量（34 组）")

SHARMA = [
    ((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485), 2.0425),
    ((50.0000, 3.1571, -77.2803), (50.0000, 0.0000, -82.7485), 2.8615),
    ((50.0000, 2.8361, -74.0200), (50.0000, 0.0000, -82.7485), 3.4412),
    ((50.0000, -1.3802, -84.2814), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -1.1848, -84.8006), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, -0.9009, -85.5211), (50.0000, 0.0000, -82.7485), 1.0000),
    ((50.0000, 0.0000, 0.0000), (50.0000, -1.0000, 2.0000), 2.3669),
    ((50.0000, -1.0000, 2.0000), (50.0000, 0.0000, 0.0000), 2.3669),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0009), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0010), 7.1792),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0011), 7.2195),
    ((50.0000, 2.4900, -0.0010), (50.0000, -2.4900, 0.0012), 7.2195),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0009, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0010, -2.4900), 4.8045),
    ((50.0000, -0.0010, 2.4900), (50.0000, 0.0011, -2.4900), 4.7461),
    ((50.0000, 2.5000, 0.0000), (50.0000, 0.0000, -2.5000), 4.3065),
    ((50.0000, 2.5000, 0.0000), (73.0000, 25.0000, -18.0000), 27.1492),
    ((50.0000, 2.5000, 0.0000), (61.0000, -5.0000, 29.0000), 22.8977),
    ((50.0000, 2.5000, 0.0000), (56.0000, -27.0000, -3.0000), 31.9030),
    ((50.0000, 2.5000, 0.0000), (58.0000, 24.0000, 15.0000), 19.4535),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.1736, 0.5854), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2972, 0.0000), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 1.8634, 0.5757), 1.0000),
    ((50.0000, 2.5000, 0.0000), (50.0000, 3.2592, 0.3350), 1.0000),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
    ((63.0109, -31.0961, -5.8663), (62.8187, -29.7946, -4.0864), 1.2630),
    ((61.2901, 3.7196, -5.3901), (61.4292, 2.2480, -4.9620), 1.8731),
    ((35.0831, -44.1164, 3.7933), (35.0232, -40.0716, 1.5901), 1.8645),
    ((22.7233, 20.0904, -46.6940), (23.0331, 14.9730, -42.5619), 2.0373),
    ((36.4612, 47.8580, 18.3852), (36.2715, 50.5065, 21.2231), 1.4146),
    ((90.8027, -2.0831, 1.4410), (91.1528, -1.6435, 0.0447), 1.4441),
    ((90.9257, -0.5406, -0.9208), (88.6381, -0.8985, -0.7239), 1.5381),
    ((6.7747, -0.2908, -2.4247), (5.8714, -0.0985, -2.2286), 0.6377),
    ((2.0776, 0.0795, -1.1350), (0.9033, -0.0636, -0.5514), 0.9082),
]

worst = 0.0
worst_pair = None
bad = 0
for lab1, lab2, expected in SHARMA:
    got = delta_e00(lab1, lab2)
    diff = abs(got - expected)
    if diff > worst:
        worst, worst_pair = diff, (lab1, lab2, expected, got)
    if diff > 0.0001:
        bad += 1
check(f"34 组全部误差 < 1e-4", bad == 0,
      f"最大偏差 {worst:.2e}" + (f" @ {worst_pair}" if bad else ""))

check("色差对称", abs(delta_e00(SHARMA[8][0], SHARMA[8][1])
                   - delta_e00(SHARMA[8][1], SHARMA[8][0])) < 1e-9)
check("同色色差为 0", delta_e00((50.0, 10.0, -10.0), (50.0, 10.0, -10.0)) == 0.0)
check("HEX 版色差同值", abs((delta_e_hex("#000000", "#FFFFFF") or 0) - 100.0) < 1.0,
      f"黑白色差 {delta_e_hex('#000000', '#FFFFFF'):.2f}")


# ══ 4. 匹配等级 ════════════════════════════════════════════════
section("4. 匹配等级与相似度")

check("ΔE 0.5 → 几乎一致", match_level(0.5) == "几乎一致")
check("ΔE 1.5 → 同色", match_level(1.5) == "同色")
check("ΔE 3 → 非常接近", match_level(3) == "非常接近")
check("ΔE 6 → 接近", match_level(6) == "接近")
check("ΔE 12 → 略有差异", match_level(12) == "略有差异")
check("ΔE 30 → 差异明显", match_level(30) == "差异明显")
check("相似度随色差单调下降", match_percent(0) == 100 and match_percent(10) == 50
      and match_percent(30) == 0, f"{match_percent(0)}/{match_percent(10)}/{match_percent(30)}")


# ══ 5. 色卡匹配 ════════════════════════════════════════════════
section("5. 品牌色卡匹配")

index = catalog_index()
total = len(index["*"])
check("色卡索引非空", total > 500, f"{total} 色")
check("索引含 4 个品牌以上", len({e['brand'] for e in index['*']}) >= 4,
      "/".join(sorted({e["brand"] for e in index["*"]})))
check("每条都预算好 Lab", all(len(e["lab"]) == 3 for e in index["*"]))

# 精确色应排在第一位且色差为 0
hit = match_catalog("#003776", limit=3)
check("精确色首位且 ΔE=0", bool(hit) and hit[0]["delta_e"] == 0.0 and hit[0]["hex"] == "#003776",
      f"{hit[0]['brand']}/{hit[0]['series']}/{hit[0]['name']}" if hit else "无结果")
check("结果按色差升序", all(hit[i]["delta_e"] <= hit[i + 1]["delta_e"] for i in range(len(hit) - 1)))

# 材料过滤
pla_only = match_catalog("#003776", material="PLA", limit=20)
petg_only = match_catalog("#003776", material="PETG", limit=20)
check("PLA 过滤后不含 PETG 系列",
      all(e["series"] != "PETG" for e in pla_only), f"{len(pla_only)} 条")
check("PETG 过滤后只含 PETG 系列",
      all("PETG" in e["series"] for e in petg_only), f"{len(petg_only)} 条")

# 品牌过滤
one_brand = match_catalog("#003776", brands=["兰博"], limit=10)
check("品牌过滤生效", all(e["brand"] == "兰博" for e in one_brand), f"{len(one_brand)} 条")

# 阈值
tight = match_catalog("#003776", limit=20, max_delta_e=0.5)
loose = match_catalog("#003776", limit=20, max_delta_e=40.0)
check("阈值收紧结果变少", len(tight) < len(loose) or len(tight) <= 1,
      f"ΔE<0.5 → {len(tight)} 条；ΔE<40 → {len(loose)} 条")

# limit
check("limit 生效", len(match_catalog("#003776", limit=2, max_delta_e=99)) == 2)

# 跨品牌推荐
near = match_catalog("#003776", limit=20, max_delta_e=99)
brand_best = recommend_brands(near)
check("每个品牌只留一个", len(brand_best) == len({e['brand'] for e in brand_best}),
      f"{len(brand_best)} 个品牌")
check("品牌推荐按色差升序",
      all(brand_best[i]["delta_e"] <= brand_best[i + 1]["delta_e"] for i in range(len(brand_best) - 1)))
check("品牌推荐含最优品牌", brand_best and brand_best[0]["brand"] == "Polymaker",
      brand_best[0]["brand"] if brand_best else "空")

# 非法输入
check("非法色值不炸", match_catalog("不是颜色") == [] and match_catalog("") == [])


# ══ 5b. 新增品牌色卡（拓竹 / 大简 / Kexcelled K5 PETG Rapid）══════
section("5b. 新增品牌色卡")

brands_in_index = {e["brand"] for e in index["*"]}
check("索引含拓竹品牌", "拓竹" in brands_in_index, "/".join(sorted(brands_in_index)))
check("索引含大简品牌", "大简" in brands_in_index)
check("品牌总数随新色卡增至 ≥12", len(brands_in_index) >= 12, f"{len(brands_in_index)} 个")
check("色卡总量随新品牌增长 > 1600", total > 1600, f"{total} 色")

# ── 每一条颜色都必须有可显示的 name ────────────────────────────────
# 前端点色块时把 name 填进「颜色名」输入框（app.js pickPresetColor）。
# 只抓到英文名的品牌（JAYO / 天瑞 / iBOSS / R3D / 爱丽兹）曾经 name 传空串，
# 表现为「点色块没反应 / 存进去的颜色没名字」。_c()/_co() 已统一兜底成英文名。
_blank = [(e["brand"], e["series"], e["name"]) for e in index["*"]
          if not (e.get("name") or "").strip()]
check("没有无名颜色（name 不可为空）", not _blank, f"{len(_blank)} 条，例：{_blank[:3]}")
check("每个品牌至少有一条带名字的颜色",
      all(any((e.get("name") or "").strip() for e in index["*"] if e["brand"] == b)
          for b in brands_in_index))

def _find(brand, series, name):
    for e in index["*"]:
        if e["brand"] == brand and e["series"] == series and e["name"] == name:
            return e
    return None

# Kexcelled 实购的 K5 PETG Rapid 系列（此前色卡只有普通 K5 PETG 故对不上）
rapid = [e for e in index["*"] if e["brand"] == "Kexcelled" and e["series"] == "K5 PETG Rapid"]
check("Kexcelled K5 PETG Rapid 系列已收录", len(rapid) >= 18, f"{len(rapid)} 色")
hit_sunset = _find("Kexcelled", "K5 PETG Rapid", "日落橙")
check("Kexcelled 日落橙 已补录且色值正确",
      hit_sunset is not None and hit_sunset["hex"].upper() == "#F5510B",
      hit_sunset["hex"] if hit_sunset else "缺失")
hit_mist = _find("Kexcelled", "K5 PETG Rapid", "星雾紫")
check("Kexcelled 星雾紫 已补录且色值正确",
      hit_mist is not None and hit_mist["hex"].upper() == "#5C30B4",
      hit_mist["hex"] if hit_mist else "缺失")

# 拓竹官方 Hex Code Table（official=True）
bambu_jade = _find("拓竹", "PLA Basic", "玉石白")
check("拓竹 玉石白 官方色值正确",
      bambu_jade is not None and bambu_jade["hex"].upper() == "#FFFFFF"
      and bambu_jade.get("official") is True,
      f"{bambu_jade['hex']}/{bambu_jade.get('official')}" if bambu_jade else "缺失")
bambu_green = _find("拓竹", "PLA Basic", "拓竹绿")
check("拓竹 拓竹绿 官方色值正确",
      bambu_green is not None and bambu_green["hex"].upper() == "#00AE42",
      bambu_green["hex"] if bambu_green else "缺失")
bambu_count = sum(1 for e in index["*"] if e["brand"] == "拓竹")
check("拓竹四系列共 82 色", bambu_count == 82, f"{bambu_count} 色")
check("拓竹色块均为官方色值", all(e.get("official") is True for e in index["*"] if e["brand"] == "拓竹"))

# 大简 PETG HF（近似值，HEX 取自官方店/微博展示）
dasu_taro = _find("大简", "PETG HF", "香芋紫")
check("大简 香芋紫 已收录", dasu_taro is not None and dasu_taro["hex"].upper() == "#A88BC4",
      dasu_taro["hex"] if dasu_taro else "缺失")
dasu_pink = _find("大简", "PETG HF", "樱花粉")
check("大简 樱花粉 已收录", dasu_pink is not None and dasu_pink["hex"].upper() == "#F0B9C4",
      dasu_pink["hex"] if dasu_pink else "缺失")

# 大简 通用 PETG 基础系列（40 色，取自天猫店 SKU 列表截图取色 2026-09-16）
dasu_petg_all = [e for e in index["*"] if e["brand"] == "大简" and e["series"] == "PETG"]
check("大简 PETG 基础系列共 40 色", len(dasu_petg_all) == 40, f"{len(dasu_petg_all)} 色")
for nm, hx in (("红色", "#C54243"), ("黄色", "#F2DD00"), ("松石绿", "#3AA4A9"),
               ("拿铁色", "#9E8F75"), ("薄荷蓝", "#A8D8D8"), ("蓝灰色", "#565E68")):
    e = _find("大简", "PETG", nm)
    check(f"大简 PETG {nm} 色值正确",
          e is not None and e["hex"].upper() == hx, e["hex"] if e else "缺失")
# 同名色在 PETG 与 PETG HF 两系列中色值一致（透明蓝/香芋紫/樱花粉）
for nm in ("透明蓝", "香芋紫", "樱花粉", "黑色", "绀紫色"):
    a, b = _find("大简", "PETG", nm), _find("大简", "PETG HF", nm)
    check(f"大简 {nm} 两系列色值一致",
          a is not None and b is not None and a["hex"].upper() == b["hex"].upper(),
          f"{a['hex'] if a else '缺失'} vs {b['hex'] if b else '缺失'}")


# ══ 5c. 彩多屋（CAILAB）═══════════════════════════════════════════
# 数据源是官网 Shopify 的 /products.json：**色名与官方色号是官方字段**，
# HEX 是从官方逐色色片图取主色得到的近似值（官方不公布 Hex Code Table）。
# 断言要盯住这两件事：色号没被拆掉、近似值的 official 标成 False。
section("5c. 彩多屋（CAILAB）色卡")

cai = [e for e in index["*"] if e["brand"] == "彩多屋"]
check("索引含彩多屋品牌", "彩多屋" in brands_in_index, "/".join(sorted(brands_in_index)))
check("彩多屋色数 ≥140（官方在售）", len(cai) >= 140, f"{len(cai)} 色")

cai_series = {e["series"] for e in cai}
for s, want in (("PLA+", 34), ("PETG", 29), ("哑光 PLA", 12), ("丝绸 PLA", 17),
                ("三色丝绸 PLA", 41), ("金属 PLA", 7), ("PETG-CF", 9), ("PLA-CF", 1)):
    n = sum(1 for e in cai if e["series"] == s)
    check(f"彩多屋 {s} 共 {want} 色", n == want, f"{n} 色")

# 官方色号必须保留在显示名里 —— 这是这家品牌最有辨识度的字段，
# 拆丢了就没法跟包装/官方页对上号
for series, code in (("PLA+", "AC199"), ("PETG", "G419"), ("哑光 PLA", "MT9003"),
                     ("丝绸 PLA", "AS199"), ("金属 PLA", "ATM422")):
    hit = next((e for e in cai if e["series"] == series
                and code in (e.get("name") or "")), None)
    check(f"彩多屋 {series} 保留官方色号 {code}", hit is not None,
          str([e["name"] for e in cai if e["series"] == series][:4]))

# 关键色值抽查（近似值，但要在合理范围内：名实相符）
for series, nm, want in (("PLA+", "Silver", "#C0C0C0"), ("哑光 PLA", "Latte", "#A88058"),
                         ("哑光 PLA", "Matcha Green", "#B0B860"),
                         ("金属 PLA", "Silver", "#C0C0C0")):
    hit = next((x for x in cai if x["series"] == series and x.get("en") == nm), None)
    check(f"彩多屋 {series} {nm} 色值正确",
          hit is not None and hit["hex"].upper() == want,
          hit["hex"] if hit else "缺失")

# 近似值必须标 official=False，别冒充官方色值
check("彩多屋色块均标 official=False（HEX 非官方公布）",
      all(e.get("official") is False for e in cai))
check("彩多屋每条都有可显示名（点色块能填出颜色名）",
      all((e.get("name") or "").strip() for e in cai))

# 渐变/三色这类没有「单一定义色」的，HEX 必须是中性占位灰，
# 否则会拿一个假色值去参与 ΔE 匹配、推荐出根本不存在的颜色
multi = [e for e in cai if e["series"] == "三色丝绸 PLA"]
check("三色丝绸用中性占位灰（不拿假色去比对）",
      all(e["hex"].upper() == "#CCCCCC" for e in multi),
      str(sorted({e["hex"] for e in multi}))[:80])

# 品牌写法归一
for variant in ("cailab", "CAILAB", "CaiLab", "cailab3d", "彩多屋旗舰店"):
    check(f"品牌归一 {variant} → 彩多屋",
          normalize_brand(variant) == "彩多屋", normalize_brand(variant))
check("彩多屋在品牌下拉预设里", "彩多屋" in BRAND_PRESETS)


# ══ 6. 料盘匹配 ════════════════════════════════════════════════
section("6. 库中料盘匹配")

from app.models import Spool  # noqa: E402

spools = [
    Spool(id=1, name="Polymaker PLA 蓝色", brand="Polymaker", material="PLA",
          color_name="蓝色", color_hex="#003776", remaining_weight=800.0, initial_weight=1000.0),
    Spool(id=2, name="兰博 PLA 深蓝", brand="兰博", material="PLA",
          color_name="深蓝", color_hex="#0B2A5B", remaining_weight=200.0, initial_weight=1000.0),
    Spool(id=3, name="大简 PETG-HT 黑", brand="大简", material="PETG-HT",
          color_name="黑", color_hex="#111111", remaining_weight=950.0, initial_weight=1000.0),
    Spool(id=4, name="已归档的红料", brand="魔创", material="PLA",
          color_name="红", color_hex="#D32F2F", remaining_weight=500.0, initial_weight=1000.0,
          archived=True),
]

inv = match_inventory("#003776", spools, limit=5, max_delta_e=20.0)
check("精确色命中对应料盘", bool(inv) and inv[0]["spool_id"] == 1, f"{inv[0]['name']}" if inv else "无")
check("料盘结果带余量", bool(inv) and "remaining_weight" in inv[0])
check("归档料默认排除", all(e["spool_id"] != 4 for e in inv))
inv_all = match_inventory("#D32F2F", spools, limit=5, max_delta_e=20.0, include_archived=True)
check("可选包含归档", any(e["spool_id"] == 4 for e in inv_all))
inv_mat = match_inventory("#003776", spools, material="PETG", limit=5, max_delta_e=99.0)
check("材料过滤排除 PLA", all(e["material"].startswith("PETG") for e in inv_mat),
      f"{[e['name'] for e in inv_mat]}")
check("库中无近似色时返回空",
      match_inventory("#00FF00", spools, max_delta_e=1.0) == [])


# ══ 7. 入参归一化 ══════════════════════════════════════════════
section("7. 入参归一化")

norm = resolve_colors([{"hex": "#3a7d44", "weight": 2.0}, {"hex": "#3A7D44", "weight": 2.0},
                       "#f57c00"])
check("重复色合并", len(norm) == 2, f"{[c['hex'] for c in norm]}")
check("权重归一化到 1", abs(sum(c["weight"] for c in norm) - 1.0) < 1e-6,
      str([c["weight"] for c in norm]))
check("重复项权重累加", norm[0]["weight"] == 0.8, f"{norm[0]['weight']}")
check("权重排序与首次出现顺序一致", norm[0]["hex"] == "#3A7D44")
check("带 Lab 回填", all(len(c["lab"]) == 3 for c in norm))
check("非法色被丢弃", len(resolve_colors(["nope", "#fff"])) == 1)
check("纯字符串也能吃", resolve_colors(["#000000"])[0]["weight"] == 1.0)


# ══ 8. HTTP 端到端 ═════════════════════════════════════════════
section("8. 接口端到端（真实 uvicorn）")

DATA_DIR = ROOT / "data" / "testcolor"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


class Server:
    def __init__(self) -> None:
        if DATA_DIR.exists():
            shutil.rmtree(DATA_DIR, ignore_errors=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.port = free_port()
        env = dict(os.environ)
        env.update({
            "DATA_DIR": str(DATA_DIR),
            "BAMBU_MOCK": "1",
            "PORT": str(self.port),
            "PYTHONUNBUFFERED": "1",
            "ALLOW_PUBLIC_SETUP": "1",
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
            try:
                if httpx.get(self.base + "/health", timeout=2).status_code == 200:
                    return True
            except Exception:  # noqa: BLE001
                time.sleep(0.3)
        return False

    def stop(self) -> None:
        self.proc.terminate()
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.proc.kill()


server = Server()
if not server.wait():
    check("测试服务启动", False, "uvicorn 未在 60s 内就绪")
else:
    check("测试服务启动", True)
    client = httpx.Client(base_url=server.base, timeout=30.0)
    try:
        # 未登录应被拦
        r = client.post("/api/color/match", json={"colors": [{"hex": "#003776"}]})
        check("未登录访问被拦", r.status_code == 401, f"HTTP {r.status_code}")

        r = client.post("/api/auth/setup",
                        json={"username": "xiaomei", "password": "spool-test-2026"})
        check("初始化管理员", r.status_code == 200, f"HTTP {r.status_code}")
        r = client.post("/api/auth/login",
                        json={"username": "xiaomei", "password": "spool-test-2026", "remember": True})
        check("登录", r.status_code == 200, f"HTTP {r.status_code}")

        # 建两盘料供匹配
        for payload in (
            {"brand": "Polymaker", "material": "PLA", "color_name": "蓝色", "color_hex": "#003776",
             "initial_weight": 1000, "spool_weight": 140},
            {"brand": "兰博", "material": "PLA", "color_name": "深蓝", "color_hex": "#0B2A5B",
             "initial_weight": 1000, "spool_weight": 200},
        ):
            r = client.post("/api/spools", json=payload)
            check(f"建料盘 {payload['brand']}", r.status_code == 200, f"HTTP {r.status_code}")

        # 正常匹配
        r = client.post("/api/color/match", json={
            "colors": [{"hex": "#0B2A5B", "weight": 1.0}],
            "limit": 5,
            "max_delta_e": 15,
        })
        check("匹配接口 200", r.status_code == 200, f"HTTP {r.status_code}")
        data = r.json()
        colors = data.get("colors") or []
        check("返回一个颜色结果", len(colors) == 1)
        if colors:
            first = colors[0]
            check("色卡匹配非空", len(first.get("catalog") or []) > 0,
                  f"{len(first.get('catalog') or [])} 条")
            check("料盘匹配非空", len(first.get("inventory") or []) > 0,
                  f"{len(first.get('inventory') or [])} 条")
            check("精确色命中第一盘", first["inventory"][0]["spool_id"] == 2,
                  first["inventory"][0]["name"] if first.get("inventory") else "无")
            check("返回品牌推荐", len(first.get("brands") or []) > 0,
                  f"{len(first.get('brands') or [])} 个品牌")
            check("权重归一为 1", first["weight"] == 1.0)
            check("带 Lab 值", len(first.get("lab") or []) == 3)
        check("返回色卡总量", (data.get("catalog") or {}).get("total", 0) > 500,
              str((data.get("catalog") or {}).get("total")))
        check("返回参与比对的料盘数", data.get("spool_count") == 2,
              str(data.get("spool_count")))

        # 材料过滤 + 品牌过滤
        r = client.post("/api/color/match", json={
            "colors": ["#003776"], "material": "PETG", "limit": 5, "max_delta_e": 60,
        })
        body = r.json()["colors"][0]
        check("材料过滤生效（PETG 不含 PLA 系列）",
              all(e["series"] != "Panchroma PLA" for e in body["catalog"]))
        check("材料过滤也作用于料盘", all(e["material"].startswith("PETG")
                                     for e in body.get("inventory", [])))

        r = client.post("/api/color/match", json={
            "colors": ["#003776"], "brands": ["魔创"], "limit": 3, "max_delta_e": 60,
        })
        body2 = r.json()["colors"][0]
        check("品牌过滤生效", all(e["brand"] == "魔创" for e in body2["catalog"]),
              f"{len(body2['catalog'])} 条")

        # scope
        r = client.post("/api/color/match", json={"colors": ["#003776"], "scope": "catalog"})
        body3 = r.json()["colors"][0]
        check("scope=catalog 不查库存", "inventory" not in body3 and "catalog" in body3)
        r = client.post("/api/color/match", json={"colors": ["#003776"], "scope": "inventory"})
        body4 = r.json()["colors"][0]
        check("scope=inventory 不查色卡", "catalog" not in body4 and "inventory" in body4)

        # 阈值外兜底：给 nearest 但不给 matches
        r = client.post("/api/color/match", json={
            "colors": ["#00FF00"], "max_delta_e": 1.0,
        })
        body5 = r.json()["colors"][0]
        check("阈值内无结果时给 nearest", not body5["catalog"] and body5.get("nearest_catalog"),
              str((body5.get("nearest_catalog") or {}).get("name")))

        # 空颜色 -> 400
        r = client.post("/api/color/match", json={"colors": []})
        check("空颜色返回 400", r.status_code == 400, f"HTTP {r.status_code}")

        # 全非法色值 -> 400
        r = client.post("/api/color/match", json={"colors": ["zzz", ""]})
        check("全非法色值返回 400", r.status_code == 400, f"HTTP {r.status_code}")

        # 多色一次匹配
        r = client.post("/api/color/match", json={
            "colors": [{"hex": "#003776", "weight": 0.6}, {"hex": "#D32F2F", "weight": 0.4}],
            "limit": 3, "max_delta_e": 15,
        })
        body6 = r.json()["colors"]
        check("多色一次匹配", len(body6) == 2 and abs(sum(c["weight"] for c in body6) - 1.0) < 1e-6)
        check("每色独立给结果", all(len(c.get("catalog") or []) > 0 for c in body6))

        # 跨站写拦截（POST 带外部 Origin）
        r = client.post("/api/color/match", json={"colors": ["#003776"]},
                        headers={"Origin": "https://evil.example.com"})
        check("外部 Origin 被拒", r.status_code == 403, f"HTTP {r.status_code}")
    finally:
        client.close()
        server.stop()


# ══ 汇总 ═══════════════════════════════════════════════════════
print("\n" + "=" * 58)
print(f"通过 {PASS} 项，失败 {FAIL} 项")
if FAILURES:
    print("失败项：")
    for item in FAILURES:
        print("  -", item)
print("=" * 58)
sys.exit(1 if FAIL else 0)
