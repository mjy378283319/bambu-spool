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
    "PLA", "PLA-CF", "PLA-AERO", "PETG", "PETG-CF", "PETG-HT", "ABS", "ASA", "ASA-CF",
    "PC", "PA", "PA-CF", "PA6-CF", "PAHT-CF", "TPU", "TPU-AMS", "PVA", "BVOH",
    "HIPS", "PPS", "PPS-CF", "PPA-CF", "PP", "PCTG", "PE", "EVA", "PHA", "其他",
]

# ── 外观（表面工艺） ────────────────────────────────────────────
# 「外观」是耗材的表面质感，和材料、颜色各自独立：同样是 PLA 黑色，
# 普通、哑光、丝绸是三种不同的货，价格也不一样。所以要单独存一列。
FINISH_PRESETS = [
    "普通", "亮面", "哑光", "磨砂", "丝绸", "珠光", "金属",
    "半透", "透明", "渐变", "双色", "木纹", "碳纤", "夜光", "其他",
]

# 中英别名 -> 规范名（键按「小写 + 去空格」归一）
FINISH_ALIASES: dict[str, str] = {
    "matte": "哑光",
    "matt": "哑光",
    "silk": "丝绸",
    "silky": "丝绸",
    "glossy": "亮面",
    "gloss": "亮面",
    "basic": "普通",
    "standard": "普通",
    "normal": "普通",
    "frosted": "磨砂",
    "translucent": "半透",
    "transparent": "透明",
    "clear": "透明",
    "metallic": "金属",
    "sparkle": "珠光",
    "glow": "夜光",
    "luminous": "夜光",
    "wood": "木纹",
    "cf": "碳纤",
    "carbon": "碳纤",
    "rainbow": "渐变",
    "gradient": "渐变",
    "dualtone": "双色",
    "twotone": "双色",
    # 中文写法：牌子上印的是「丝滑」「丝光」的比「丝绸」还多
    "丝滑": "丝绸",
    "丝光": "丝绸",
    "丝绸面": "丝绸",
    "磨砂面": "磨砂",
    "半透明": "半透",
}
_FINISH_LOOKUP: dict[str, str] = {f.lower().replace(" ", ""): f for f in FINISH_PRESETS}
_FINISH_LOOKUP.update({k.lower().replace(" ", ""): v for k, v in FINISH_ALIASES.items()})

# 从颜色名里反推外观的关键词，**顺序敏感**：
#   - 丝绸要在哑光前面：「丝绸哑光」该算丝绸（那是丝绸料的表面光泽）；
#   - 半透要在透明前面：「半透明黑」里同时含「半透」和「透明」，
#     透明排在前面的话半透盘会被判成全透明（踩过）。
_FINISH_KEYWORDS = [
    ("丝绸", "丝绸"), ("silk", "丝绸"), ("丝滑", "丝绸"), ("丝光", "丝绸"),
    ("哑光", "哑光"), ("磨砂", "磨砂"), ("matte", "哑光"), ("matt", "哑光"),
    ("珠光", "珠光"), ("金属", "金属"), ("metallic", "金属"),
    ("夜光", "夜光"), ("glow", "夜光"), ("luminous", "夜光"),
    ("半透", "半透"), ("translucent", "半透"),
    ("透明", "透明"), ("clear", "透明"),
    ("渐变", "渐变"), ("rainbow", "渐变"), ("gradient", "渐变"),
    ("双色", "双色"), ("twotone", "双色"),
    ("木纹", "木纹"), ("wood", "木纹"),
    ("碳纤", "碳纤"), ("carbon", "碳纤"),
    ("亮面", "亮面"), ("gloss", "亮面"),
]


def normalize_finish(value: str) -> str:
    """把外观写法归一到预设名（matte → 哑光），未收录的自定义值原样保留。"""
    name = (value or "").strip()
    if not name:
        return ""
    return _FINISH_LOOKUP.get(name.lower().replace(" ", ""), name)


def infer_finish(color_name: str) -> str:
    """从颜色名里猜外观。只用于老数据回填与「按槽位建料盘」的预填。

    历史版本里「外观」是接口层用 `"哑光" in color_name` 现算的假字段，
    回填时沿用同一套规则，升级后界面显示不变。
    """
    text = (color_name or "").lower()
    for keyword, finish in _FINISH_KEYWORDS:
        if keyword in text:
            return finish
    return "普通"


# 品牌 -> 空盘皮重（g）。多数塑料盘在 190~250g，纸质盘更轻。
# 官方数据来自厂商规格，未覆盖的品牌用户可手工填写。
#
# 注意：一个品牌只保留一条规范名（中文名优先），不要同时写「Bambu Lab」和
# 「拓竹」这类中英双份——那会让新建料盘的品牌下拉框出现重复项。
# 历史数据里的英文写法由下面的 BRAND_ALIASES 统一归并。
BRAND_SPOOL_WEIGHTS: dict[str, list[float]] = {
    "拓竹": [250.0, 190.0],            # 塑料盘 250g / 可重复使用盘 190g
    "Polymaker": [140.0, 220.0],      # 纸盘 140±7g（官方，PolyTerra/PolyLite 1kg）/ 旧塑料盘 220g
    "大简": [200.0, 150.0],            # 塑料盘约 200g / 纸盘约 150g（估算，建议用称重校准修正）
    "爱丽兹 Allizz": [200.0],
    "Kexcelled": [240.0],
    "兰博": [200.0],                   # 官网未公布空盘重量，估算值，建议称重校准
    "魔创": [200.0],                   # 官网未公布空盘重量，估算值，建议称重校准
}
# 说明：eSUN 易生 / 三绿 Sunlu / 创想三维 Creality / JAYO / Overture / Prusament
# 曾经在列表里，现已按下架处理（用不到的品牌留在下拉里只会拖长候选）。
# 老库里若有这些品牌的料盘，数据不动，只是不再出现在预设中；
# 用户如果想再要，可以在「设置 → 自定义品牌」里自己加回来。

# 品牌别名 -> 规范名。键统一按「小写 + 去掉空格」归一，值必须是
# BRAND_SPOOL_WEIGHTS 里的规范名（或用户自定义的写法）。
# 常用于：老数据里存的英文名、第三方导入的简写、用户在输入框里手打的变体。
BRAND_ALIASES: dict[str, str] = {
    "bambulab": "拓竹",
    "bambulab拓竹": "拓竹",
    "拓竹科技": "拓竹",
    "bambu": "拓竹",
    "polymaker": "Polymaker",
    "poly maker": "Polymaker",
    "kexcelled": "Kexcelled",
    "kecelled": "Kexcelled",
    "allizz": "爱丽兹 Allizz",
    "爱丽兹": "爱丽兹 Allizz",
    "大简petg": "大简",
}

# 规范名自己也进查找表，这样 normalize_brand 可以一把梭
_BRAND_LOOKUP: dict[str, str] = {
    name.lower().replace(" ", ""): name for name in BRAND_SPOOL_WEIGHTS
}
_BRAND_LOOKUP.update(
    {alias.lower().replace(" ", ""): target for alias, target in BRAND_ALIASES.items()}
)

# 品牌下拉框的候选：规范名去重后 + 「其他」
BRAND_PRESETS = list(BRAND_SPOOL_WEIGHTS.keys()) + ["其他"]


def normalize_brand(value: str) -> str:
    """把品牌写法归一到规范名（「Bambu Lab」→「拓竹」），未收录的原样返回。

    只做映射不做校验：用户填的自定义品牌依然允许存在，只是不会命中预设皮重。
    """
    name = (value or "").strip()
    if not name:
        return ""
    return _BRAND_LOOKUP.get(name.lower().replace(" ", ""), name)

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


# ── 品牌专属配色预设 ────────────────────────────────────────────
# 数据来源：Polymaker 官方站点（us.polymaker.com / eu-wholesale.polymaker.com）
# 商品页的色卡。official=True 表示 HEX 直接取自官方页面；False 表示官方仅公布
# 色名、该 HEX 是按色名推断的近似值（界面会加角标提示）。
def _c(name: str, en: str, hex_value: str, official: bool = True) -> dict:
    return {"name": name, "en": en, "hex": hex_value, "official": official}


# Panchroma™ Basic PLA（US 商品页 28 色）
POLYMAKER_PANCHROMA_PLA: list[dict] = [
    _c("黑色", "Black", "#080A0D"),
    _c("白色", "White", "#EBF7FF"),
    _c("冷白", "Cold White", "#D9DFE5"),
    _c("红色", "Red", "#E72F1D"),
    _c("橙色", "Orange", "#F67405"),
    _c("品红", "Magenta", "#F24574"),
    _c("粉色", "Pink", "#F1A1AF"),
    _c("酒红", "Wine Red", "#D60212"),
    _c("柠檬黄", "Lemon Yellow", "#EED230"),
    _c("黄色", "Yellow", "#FFE800"),
    _c("奶油白", "Cream", "#EED1A8"),
    _c("米色", "Beige", "#C2AB72"),
    _c("棕褐", "Tan", "#A79E82"),
    _c("棕色", "Brown", "#55331A"),
    _c("绿色", "Green", "#06924D"),
    _c("青柠绿", "Lime Green", "#D5D701"),
    _c("丛林绿", "Jungle Green", "#4E742D"),
    _c("橄榄绿", "Olive Green", "#948902"),
    _c("暗橄榄绿", "Dark Olive Drab", "#575B54"),
    _c("天蓝", "Azure Blue", "#0066D9"),
    _c("蓝色", "Blue", "#003776"),
    _c("水蓝", "Aqua Blue", "#5EBDDB"),
    _c("石蓝", "Stone Blue", "#487BA2"),
    _c("品牌青", "Polymaker Teal", "#4CC0C7"),
    _c("钢灰", "Steel Grey", "#616469"),
    _c("灰色", "Grey", "#8C9099"),
    _c("深灰", "Dark Grey", "#485259"),
    _c("紫色", "Purple", "#6C47B2"),
]

# Panchroma™ Matte PLA（原 PolyTerra™ PLA，US 商品页 52 色）
POLYMAKER_PANCHROMA_MATTE: list[dict] = [
    _c("哑光炭黑", "Matte Charcoal Black", "#2F2E30"),
    _c("哑光棉白", "Matte Cotton White", "#F4EFEB"),
    _c("哑光木棕", "Matte Wood Brown", "#AB7449"),
    _c("哑光日出橙", "Matte Sunrise Orange", "#F88B17"),
    _c("哑光森林绿", "Matte Forest Green", "#60AD70"),
    _c("哑光极地青", "Matte Arctic Teal", "#61BCC3"),
    _c("哑光化石灰", "Matte Fossil Grey", "#8A8C94"),
    _c("哑光樱花粉", "Matte Sakura Pink", "#EAADBD"),
    _c("哑光草原黄", "Matte Savannah Yellow", "#F3C432"),
    _c("哑光宝石蓝", "Matte Sapphire Blue", "#0163A6"),
    _c("哑光薰衣草紫", "Matte Lavender Purple", "#9572BF"),
    _c("哑光大地棕", "Matte Earth Brown", "#7C594A"),
    _c("哑光熔岩红", "Matte Lava Red", "#ED2F2E"),
    _c("哑光荷花粉", "Matte Lotus Pink", "#DD76C0"),
    _c("哑光青柠绿", "Matte Lime Green", "#D7D602"),
    _c("哑光天空蓝", "Matte Sky Blue", "#1AC5FC"),
    _c("哑光烟灰", "Matte Ash Grey", "#485155"),
    _c("哑光电光靛", "Matte Electric Indigo", "#6858A9"),
    _c("哑光阳光黄", "Matte Sunshine Yellow", "#F9DA07"),
    _c("哑光草绿", "Matte Grass Green", "#32BC46"),
    _c("哑光电光洋红", "Matte Electric Magenta", "#D33A6D"),
    _c("哑光海沫绿", "Matte Seafoam Green", "#7DD4BE"),
    _c("哑光树莓蓝", "Matte Raspberry Blue", "#5472D0"),
    _c("哑光酒红", "Matte Wine Burgundy", "#753E4C"),
    _c("哑光祖母绿", "Matte Emerald Green", "#22624F"),
    _c("哑光军红", "Matte Army Red", "#BF312E"),
    _c("哑光军浅绿", "Matte Army Light Green", "#AB8C02"),
    _c("哑光军米色", "Matte Army Beige", "#DBBAA5"),
    _c("哑光军紫", "Matte Army Purple", "#36364A"),
    _c("哑光军棕", "Matte Army Brown", "#795A4D"),
    _c("哑光军蓝", "Matte Army Blue", "#2E4462"),
    _c("哑光军深绿", "Matte Army Dark Green", "#5F6244"),
    _c("哑光马卡龙花生", "Matte Pastel Peanut", "#BF9573"),
    _c("哑光马卡龙蜜桃", "Matte Pastel Peach", "#F6BF8B"),
    _c("哑光马卡龙香蕉", "Matte Pastel Banana", "#F7D475"),
    _c("哑光马卡龙薄荷", "Matte Pastel Mint", "#D2DEBB"),
    _c("哑光马卡龙糖果", "Matte Pastel Candy", "#F0D6D9"),
    _c("哑光马卡龙冰蓝", "Matte Pastel Ice", "#A4D0DF"),
    _c("哑光马卡龙西瓜", "Matte Pastel Watermelon", "#EE474B"),
    _c("哑光马卡龙长春花", "Matte Pastel Periwinkle", "#ADB4E6"),
    _c("哑光马卡龙珊瑚", "Matte Pastel Coral", "#F09A7E"),
    _c("哑光马卡龙米色", "Matte Pastel Beige", "#E4D0B0"),
    _c("哑光莫兰迪红", "Matte Muted Red", "#D84B2E"),
    _c("哑光莫兰迪蓝", "Matte Muted Blue", "#5F778E"),
    _c("哑光莫兰迪紫", "Matte Muted Purple", "#7C5C78"),
    _c("哑光莫兰迪绿", "Matte Muted Green", "#777E71"),
    _c("哑光莫兰迪白", "Matte Muted White", "#BBADA4"),
    _c("哑光莫兰迪苔绿", "Matte Muted Moss", "#92864F"),
    _c("哑光莫兰迪青", "Matte Muted Teal", "#5D989E"),
    _c("哑光莫兰迪藕紫", "Matte Muted Mauve", "#A36D82"),
    _c("哑光莫兰迪赤陶", "Matte Muted Terracotta", "#C06443"),
    _c("哑光玫瑰", "Matte Rose", "#CF6076"),
]

# Polymaker™ PETG（原 PolyLite™ PETG，官方 24 色；部分色号官方未公布 HEX，为近似值）
POLYMAKER_PETG: list[dict] = [
    _c("黑色", "Black", "#070908"),
    _c("白色", "White", "#F2F1ED", official=False),
    _c("灰色", "Grey", "#8C9099", official=False),
    _c("深灰", "Dark Grey", "#4A5054", official=False),
    _c("银灰", "Silver Grey", "#B7BBBF", official=False),
    _c("粉色", "Pink", "#B288AB"),
    _c("品红", "Magenta", "#E3127E", official=False),
    _c("红色", "Red", "#DD1116"),
    _c("橙色", "Orange", "#F07B22", official=False),
    _c("绿色", "Green", "#1E9E4A", official=False),
    _c("黄色", "Yellow", "#F5D400", official=False),
    _c("青柠绿", "Lime", "#C4D600", official=False),
    _c("深绿", "Dark Green", "#121B13"),
    _c("青色", "Teal", "#17A2A2", official=False),
    _c("电光蓝", "Electric Blue", "#003E70"),
    _c("蓝色", "Blue", "#1B4F9C", official=False),
    _c("深蓝", "Dark Blue", "#030E1A"),
    _c("紫色", "Purple", "#6C47B2", official=False),
    _c("深紫", "Dark Purple", "#2E1A47"),
    _c("军棕", "Army Brown", "#795A4D", official=False),
    _c("星空黑", "Galaxy Black", "#212721"),
    _c("星空深灰", "Galaxy Dark Grey", "#474648"),
    _c("星空蓝", "Galaxy Blue", "#012C61"),
    _c("星空红", "Galaxy Red", "#BF1A11"),
]

# 品牌 -> 系列 -> 色卡
BRAND_COLOR_SERIES: dict[str, dict[str, list[dict]]] = {
    "Polymaker": {
        "Panchroma PLA": POLYMAKER_PANCHROMA_PLA,
        "Panchroma 哑光 PLA": POLYMAKER_PANCHROMA_MATTE,
        "PETG": POLYMAKER_PETG,
    },
}

# 材料 -> 该品牌下适用的系列
MATERIAL_COLOR_SERIES: dict[str, list[str]] = {
    "PLA": ["Panchroma PLA", "Panchroma 哑光 PLA"],
    "PETG": ["PETG"],
}

# Kexcelled / 兰博 / 魔创 的配色数据在 brand_colors.py（自动生成），在此合并
from .brand_colors import (  # noqa: E402
    BRAND_COLOR_SERIES_EXTRA,
    MATERIAL_COLOR_SERIES_EXTRA,
)

BRAND_COLOR_SERIES.update(BRAND_COLOR_SERIES_EXTRA)
for _mat, _series in MATERIAL_COLOR_SERIES_EXTRA.items():
    _existing = MATERIAL_COLOR_SERIES.setdefault(_mat, [])
    MATERIAL_COLOR_SERIES[_mat] = _existing + [s for s in _series if s not in _existing]


def color_series_for(brand: str, material: str) -> list[dict]:
    """返回该品牌+材料组合下可用的官方色卡分组（无预设时返回空列表）。"""
    series = BRAND_COLOR_SERIES.get(brand)
    if not series:
        return []
    mat = (material or "").upper()
    groups: list[dict] = []
    for mat_key, names in MATERIAL_COLOR_SERIES.items():
        if not mat.startswith(mat_key):
            continue
        for name in names:
            colors = series.get(name)
            if colors:
                groups.append({"series": name, "colors": colors})
    return groups


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


def build_spool_name(brand: str, material: str, color_name: str, finish: str = "") -> str:
    """默认名：品牌 + 材料 + [外观] + 颜色。

    外观是「普通」或空的时候不写进去，免得每盘料名里都拖一个没信息量的词；
    丝绸、哑光这类则一定要写 —— 同材料同颜色的两盘货只能靠它区分。
    """
    texture = finish if finish and finish != "普通" else ""
    parts = [p for p in (brand, material, texture, color_name) if p]
    return " ".join(parts)
