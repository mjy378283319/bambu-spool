"""静态对照表：机型、材料、品牌皮重、颜色、HMS 错误码。

数据来源：greghesp/ha-bambulab 的 const.py（机型枚举、HMS 模块、阶段名）
         + Mars Printer Hub 开放接口文档暴露的型号码映射。
"""
from __future__ import annotations

# ── 机型代码映射 ────────────────────────────────────────────────
MODEL_CODE_TO_NAME = {
    "BL-P001": "X1C",
    "C11": "P1P",
    "C12": "P1S",
    "C13": "X1E",
    "N1": "A1 mini",
    "N2S": "A1",
    "N6-V2": "X2D",
    "N7-V2": "P2S",
    "O1C2-V2": "H2C",
    "O1D": "H2D",
    "O1S": "H2S",
}

# 型号 -> 是否支持腔温 / 摄像头等，用于界面按需展示
MODEL_FEATURES = {
    "X1C": {"chamber_temp": True, "camera": True},
    "X1E": {"chamber_temp": True, "camera": True},
    "P1P": {"chamber_temp": False, "camera": True},
    "P1S": {"chamber_temp": True, "camera": True},
    "A1": {"chamber_temp": False, "camera": True},
    "A1 mini": {"chamber_temp": False, "camera": True},
    "P2S": {"chamber_temp": True, "camera": True},
    "H2D": {"chamber_temp": True, "camera": True},
    "H2S": {"chamber_temp": True, "camera": True},
    "H2C": {"chamber_temp": True, "camera": True},
}

# ── 打印状态 ────────────────────────────────────────────────────
GCODE_STATE_LABELS = {
    "IDLE": "空闲",
    "PREPARE": "准备中",
    "RUNNING": "打印中",
    "PAUSE": "已暂停",
    "FINISH": "已完成",
    "FAILED": "失败",
    "SLICING": "切片中",
    "INIT": "初始化",
    "OFFLINE": "离线",
}

# 运行中的状态集合：任务结束判定要用
ACTIVE_STATES = {"PREPARE", "RUNNING", "PAUSE"}
TERMINAL_STATES = {"FINISH", "FAILED", "IDLE", "OFFLINE"}

# 阶段名，来自 ha-bambulab const.py 的 CURRENT_STAGE_IDS
STAGE_LABELS = {
    -1: "空闲", 0: "打印中", 1: "自动调平", 2: "热床预热", 3: "振动补偿",
    4: "换料中", 5: "暂停等待", 6: "断料暂停", 7: "加热喷嘴", 8: "挤出校准",
    9: "扫描热床", 10: "首层检测", 11: "识别热床板", 12: "激光雷达校准",
    13: "回零", 14: "清洁喷嘴", 15: "检查喷嘴温度", 16: "用户暂停",
    17: "前门异常暂停", 19: "挤出流量校准", 22: "退料中", 23: "丢步暂停",
    24: "进料中", 25: "电机噪声校准", 26: "AMS 掉线暂停", 29: "腔体降温",
    30: "用户 G 代码暂停", 33: "切刀异常暂停", 34: "首层异常暂停",
    35: "喷嘴堵塞暂停", 42: "检查门盖", 49: "腔体加热", 51: "打印校准线",
    52: "检查材料", 58: "热预处理", 63: "等待腔温平衡", 66: "净化腔体空气",
    72: "热端类型检测", 73: "热床板对齐检测", 77: "准备 AMS", 255: "空闲",
}

AMS_MODEL_LABELS = {
    "AMS": "AMS",
    "AMS Lite": "AMS Lite",
    "AMS 2 Pro": "AMS 2 Pro",
    "AMS HT": "AMS HT",
}

# ── HMS 错误码 ─────────────────────────────────────────────────
HMS_SEVERITY = {
    1: "致命",
    2: "严重",
    3: "一般",
    4: "提示",
}

HMS_MODULE_BY_CODE = {
    0x05: "主板",
    0x0C: "视觉模组",
    0x07: "AMS",
    0x08: "工具头",
    0x03: "运动控制",
}


def hms_severity(code: int) -> str:
    return HMS_SEVERITY.get((code >> 16) & 0xFF, "未知")


def hms_module(code: int) -> str:
    return HMS_MODULE_BY_CODE.get((code >> 24) & 0xFF, "未知")


def hms_text(attr: int, code: int) -> str:
    return f"HMS_{attr:08X}_{code:08X}"


# ── 材料与皮重 ─────────────────────────────────────────────────
MATERIALS = [
    "PLA", "PLA-CF", "PLA-AERO", "PETG", "PETG-CF", "ABS", "ASA", "ASA-CF",
    "PC", "PA", "PA-CF", "PA6-CF", "PAHT-CF", "TPU", "TPU-AMS", "PVA", "BVOH",
    "HIPS", "PPS", "PPS-CF", "PPA-CF", "PP", "PCTG", "PE", "EVA", "PHA", "其他",
]

# 品牌 -> 空盘皮重（g）。多数塑料盘在 190~250g，纸质盘更轻。
# 官方数据来自厂商规格，未覆盖的品牌用户可手工填写。
BRAND_SPOOL_WEIGHTS: dict[str, list[float]] = {
    "Bambu Lab": [250.0, 190.0],      # 塑料盘 250g / 可重复使用盘 190g
    "拓竹": [250.0, 190.0],
    "eSUN 易生": [230.0, 200.0],
    "Polymaker": [220.0],
    "爱丽兹 Allizz": [200.0],
    "Kexcelled": [240.0],
    "三绿 Sunlu": [180.0, 200.0],
    "创想三维 Creality": [200.0],
    "JAYO": [180.0],
    "Overture": [220.0],
    "Prusament": [200.0],
}

BRAND_PRESETS = list(BRAND_SPOOL_WEIGHTS.keys()) + ["其他"]

# 常见颜色预设（名称 -> HEX）。参考 Mars Printer Hub 与主流耗材厂配色。
COLOR_PRESETS: list[dict[str, str]] = [
    {"name": "黑色", "hex": "#1A1A1A"},
    {"name": "白色", "hex": "#FFFFFF"},
    {"name": "灰色", "hex": "#9A9A9A"},
    {"name": "银色", "hex": "#C0C0C0"},
    {"name": "红色", "hex": "#D32F2F"},
    {"name": "橙色", "hex": "#F57C00"},
    {"name": "黄色", "hex": "#FDD835"},
    {"name": "绿色", "hex": "#388E3C"},
    {"name": "青色", "hex": "#00ACC1"},
    {"name": "蓝色", "hex": "#1E88E5"},
    {"name": "深蓝色", "hex": "#1A237E"},
    {"name": "紫色", "hex": "#7B1FA2"},
    {"name": "粉色", "hex": "#EC407A"},
    {"name": "棕色", "hex": "#6D4C41"},
    {"name": "米白", "hex": "#EFE6D8"},
    {"name": "克莱因蓝", "hex": "#0033A0"},
    {"name": "哑光黑", "hex": "#2B2B2B"},
    {"name": "透明", "hex": "#E8F4F8"},
]


def spool_weight_options(brand: str) -> list[float]:
    return BRAND_SPOOL_WEIGHTS.get(brand, [])


def normalize_color(value: str) -> str:
    """把拓竹的 RRGGBBAA / #RRGGBB / #RRGGBBAA 统一成 #RRGGBB。"""
    if not value:
        return "#000000"
    v = value.strip().lstrip("#").upper()
    if len(v) >= 6:
        return "#" + v[:6]
    if len(v) == 3:
        return "#" + "".join(c * 2 for c in v)
    return "#000000"


def model_display_name(model_code: str) -> str:
    if not model_code:
        return ""
    return MODEL_CODE_TO_NAME.get(model_code.upper(), model_code)


def build_spool_name(brand: str, material: str, color_name: str) -> str:
    parts = [p for p in (brand, material, color_name) if p]
    return " ".join(parts)
