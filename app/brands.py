"""自定义品牌清单。

预设品牌写在 `catalog.BRAND_SPOOL_WEIGHTS` 里（跟着代码走）；用户自己加的牌子
存在 Setting 表里（跟着数据库走），这样升级镜像不会把用户录进去的品牌刷掉。

规则：
- 只存用户新增的，不复制预设，避免两边各存一份后对不上。
- 归一化用 `normalize_brand`：既能把「bambu lab」认成「拓竹」，也能让
  「自家作坊」这种没收录的写法原样通过。
- 允许删除预设以外的任何品牌；删除只影响下拉候选，不会动已经录好的料盘。
"""
from __future__ import annotations

import json

from sqlmodel import Session

from .catalog import BRAND_PRESETS, normalize_brand
from .models import Setting

KEY = "custom_brands"


def load_custom_brands(session: Session) -> list[str]:
    """读自定义品牌（保持用户添加的顺序）。"""
    row = session.get(Setting, KEY)
    if row is None or not row.value:
        return []
    try:
        data = json.loads(row.value)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(x).strip() for x in data if str(x).strip()]


def save_custom_brands(session: Session, names: list[str]) -> list[str]:
    cleaned: list[str] = []
    for name in names:
        brand = normalize_brand(name)
        if brand and brand not in cleaned:
            cleaned.append(brand)
    row = session.get(Setting, KEY)
    if row is None:
        session.add(Setting(key=KEY, value=json.dumps(cleaned, ensure_ascii=False)))
    else:
        row.value = json.dumps(cleaned, ensure_ascii=False)
        session.add(row)
    session.flush()
    return cleaned


def add_custom_brand(session: Session, name: str) -> list[str]:
    """新增一个自定义品牌。已是预设品牌时直接返回，不重复登记。"""
    brand = normalize_brand(name)
    if not brand:
        return load_custom_brands(session)
    current = load_custom_brands(session)
    if brand in BRAND_PRESETS or brand in current:
        return current
    return save_custom_brands(session, current + [brand])


def remove_custom_brand(session: Session, name: str) -> list[str]:
    brand = normalize_brand(name)
    current = load_custom_brands(session)
    if brand not in current:
        return current
    return save_custom_brands(session, [b for b in current if b != brand])


def brand_choices(session: Session) -> list[str]:
    """品牌下拉的候选：预设 + 自定义，「其他」永远排最后。

    `custom` 里若混进「其他」要滤掉，否则它会同时出现在中间和末尾，下拉里
    看着就像有两个一样的选项（`add_custom_brand` 已经拦了，这里是兜底）。
    """
    custom = [b for b in load_custom_brands(session) if b != "其他"]
    head = [b for b in BRAND_PRESETS if b != "其他" and b not in custom]
    return head + custom + ["其他"]
