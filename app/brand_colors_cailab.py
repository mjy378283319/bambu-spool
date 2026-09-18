"""彩多屋（CAILAB）官方配色预设 —— 由 scripts/build_cailab_colors.py 自动生成，勿手改。

数据来源：cailab3d.com 官方商城 `/products.json`（Shopify 结构化数据）。
- **色名与官方色号（AC199 / MT9003 / G419 …）是官方字段**，直接取自 variant 标题；
- **HEX 不是官方公布的**，是从官方逐色色片图取主色得到的**近似值** → official=False。
  取色方式见脚本 `_dominant_hex()`：量化后取中心区众数，避开白底与文字水印。
- 三色丝绸这类多色交织的没有「单一定义色」，改取**前三个主色**（hex/hex2/hex3），
  前端把色块画成三段渐变；主色 hex 仍按近似值对待（选中标记/识色比对都用它）。
  实在没有图可取的才落回中性灰 #CCCCCC 占位。

重新生成：
    python scripts/build_cailab_colors.py --fetch && python scripts/build_cailab_colors.py --build
"""


def _c(name: str, en: str, hex_value: str, hex2: str = "", hex3: str = "") -> dict:
    # 彩多屋不公布 Hex Code Table，全部按近似值处理；hex2/hex3 只在三色系列给
    d = {"name": name or en, "en": en, "hex": hex_value, "official": False}
    if hex2:
        d["hex2"] = hex2
        d["hex3"] = hex3 or hex2
    return d


# 彩多屋 金属 PLA（官方在售 7 色，来源 cailab3d.com）
CAILAB_METALLIC_PLA: list[dict] = [
    _c('钴蓝色 ATM2152', 'Cobalt Blue', '#385068'),
    _c('铱金 ATM4645', 'Iridium Gold', '#D0B8A8'),
    _c('红橡木 ATM7516', 'Red oak', '#682808'),
    _c('银色 ATM422', 'Silver', '#C0C0C0'),
    _c('琥珀金 ATM6003', 'Amber Gold', '#E0B860'),
    _c('黑胡桃 ATM2469', 'Black Walmut', '#402820'),
    _c('氧化绿 ATM568', 'Oxide Green', '#003018'),
]

# 彩多屋 PLA-CF（官方在售 1 色，来源 cailab3d.com）
CAILAB_PLA_CF: list[dict] = [
    _c('黑色', 'Black', '#505050'),
]

# 彩多屋 哑光 PLA（官方在售 12 色，来源 cailab3d.com）
CAILAB_MATTE_PLA: list[dict] = [
    _c('象牙白 MT9003', 'Ivory', '#F0F0E8'),
    _c('粉晶 MT1404', 'Rose Quartz', '#C8A098'),
    _c('布丁黄 MT2001', 'Pudding Yellow', '#E8D888'),
    _c('拿铁色 MT2317', 'Latte', '#A88058'),
    _c("Robin's Egg Blue MT319", "Robin's Egg Blue", '#58A898'),
    _c('米色 MT4030', 'Beige', '#E0C0A0'),
    _c('雾蓝色 MT6109', 'Hazy Blue', '#708090'),
    _c('抹茶绿 MT7492', 'Matcha Green', '#B0B860'),
    _c('黑色 MT419', 'Black', '#101010'),
    _c('樱花粉 MT6050', 'Sakura Pink', '#E0B0C0'),
    _c('雾丁香紫 MT256', 'Misty Lilac', '#B8A0C0'),
    _c('灰橄榄绿 MT6178', 'Muted Olive', '#A0D0A8'),
]

# 彩多屋 PETG-CF（官方在售 9 色，来源 cailab3d.com）
CAILAB_PETG_CF: list[dict] = [
    _c('酒红色', 'Wine Red', '#B87068'),
    _c('绿色', 'Green', '#409888'),
    _c('蓝色', 'Blue', '#7078B8'),
    _c('紫色', 'Purple', '#A078B0'),
    _c('灰色', 'Gray', '#C8C8C0'),
    _c('黑色', 'Black', '#686868'),
    _c('抹茶绿', 'Matcha Green', '#B0D0A8'),
    _c('雾霾蓝', 'Misty Blue', '#C8C0D8'),
    _c('沙米色', 'Sandy Beige', '#E8B8B8'),
]

# 彩多屋 丝绸 PLA（官方在售 17 色，来源 cailab3d.com）
CAILAB_SILK_PLA: list[dict] = [
    _c('阳光金 AS123', 'Sunshine Gold', '#F0A000'),
    _c('金色 AS6006', 'Gold', '#886000'),
    _c('蓝色 AS2145', 'Blue', '#002070'),
    _c('红色 AS199', 'Red', '#A00800'),
    _c('银色 AS422', 'Silver', '#606068'),
    _c('珍珠白 AS9003', 'Pearl White', '#D8D8C8'),
    _c('玫红色 AS205', 'Rose', '#B01048'),
    _c('圣诞绿 AS347', 'Xmas Green', '#005818'),
    _c('午夜黑 AS419', 'Midnight  Black', '#202020'),
    _c('铜 AS471', 'Copper', '#683810'),
    _c('珊瑚粉 AS1775', 'Coral Pink', '#F87070'),
    _c('绯红 AS1807', 'Crimson', '#600000'),
    _c('紫色 AS2602', 'Purple', '#680050'),
    _c('棕铜 AS4013', 'Brown Copper', '#602808'),
    _c("Robin's Egg Blue AS319", "Robin's Egg Blue", '#60B0A0'),
    _c('青铜色 AS5767', 'Bronze', '#606030'),
    _c('香芋紫 AS256', 'Taro Purple', '#C8B0D0'),
]

# 彩多屋 三色丝绸 PLA（官方在售 41 色，来源 cailab3d.com）
CAILAB_TRI_SILK_PLA: list[dict] = [
    _c('红色&黑色 SP001', 'Red&Black', '#303030', '#606060', '#903C3C'),
    _c('品红&金色 SP002', 'Magenta&Gold', '#E49C30', '#B40C48', '#D82478'),
    _c('蓝色&绿色 SP003', 'Blue&Green', '#006018', '#006078', '#009C30'),
    _c('绿色&金色 SP004', 'Green&Gold', '#009C24', '#9CCC30', '#549000'),
    _c('紫色&蓝色 SP005', 'Purple&Blue', '#001884', '#0048B4', '#90249C'),
    _c('蓝色&金色 SP006', 'Blue&Gold', '#6C6C00', '#0C3060', '#243018'),
    _c('银色&金色 SP007', 'Silver&Gold', '#C0B490', '#847800', '#F0F0E4'),
    _c('黑色&金色 SP008', 'Black&Gold', '#242424', '#484848', '#6C6C6C'),
    _c('粉色&金色 SP009', 'Pink&Gold', '#D8783C', '#F07878', '#FC9CA8'),
    _c('玫红色&天 SP010', 'Rose&Azure', '#006CC0', '#003090', '#B448C0'),
    _c('粉色&丁香 SP011', 'Pink&Lilac', '#546CB4', '#789CD8', '#9C60CC'),
    _c('蓝色&银色 SP012', 'Blue&Silver', '#002460', '#E4E4F0', '#8490A8'),
    _c('紫色&金色 SP013', 'Purple&Gold', '#6C0060', '#B48400', '#843C18'),
    _c('红色&金色 SP014', 'Red&Gold', '#9C0C0C', '#B47800', '#C03030'),
    _c('黑色&绿色 SP015', 'Black&Green', '#0C0C0C', '#303030', '#545454'),
    _c('黑色&紫色 SP016', 'Black&Purple', '#0C000C', '#303030', '#60006C'),
    _c('黑色&银色 SP017', 'Black&Silver', '#242424', '#484848', '#6C6C6C'),
    _c('紫色&绿色 SP018', 'Purple&Green', '#6C0060', '#309048', '#9C2490'),
    _c('品红&绿色 SP019', 'Magenta&Green', '#900060', '#3C9048', '#C03084'),
    _c('樱花白 SP020', 'Sakura white', '#FC90B4', '#F0CCD8', '#E46090'),
    _c('月光粉 SP021', 'Moonlight Pink', '#B4609C', '#D884C0', '#F0E4F0'),
    _c('金色&薰衣草紫 SP022', 'Gold&Lavender', '#6C5484', '#9C9024', '#9078A8'),
    _c('蓝色&黑色 SP023', 'Blue&Black', '#242424', '#005478', '#484848'),
    _c('蓝色&铜 SP024', 'Blue&Copper', '#904824', '#C07854', '#54240C'),
    _c('紫色&蓝色&黄色 SAN001', 'PURPLE&BLUE&YELLOW', '#484848', '#90CCFC', '#906000'),
    _c('红色&黄色&绿色 SAN002', 'RED&YELLOW&GREEN', '#FCC0E4', '#3C5400', '#484848'),
    _c('红色&绿色&蓝色 SAN003', 'RED&GREEN&BLUE', '#FCC0E4', '#484848', '#006054'),
    _c('绿色&金色&紫色 SAN004', 'GREEN&GOLD&PURPLE', '#FCCCD8', '#485400', '#484848'),
    _c('蓟&鼠尾草&葡萄 SAN005', 'TRISTLE&SAGE&GRAPE', '#484848', '#B4CC90', '#F0E4FC'),
    _c('金色&银色&铜 SAN007', 'GOLD&SILVER&COPPER', '#604800', '#F0CCCC', '#484848'),
    _c('黄色&绿色&蓝色 SAN008', 'YELLOW&GREEN&BLUE', '#484848', '#006C48', '#84D8FC'),
    _c('铜&紫色&绿色 SAN010', 'COPPER&PURPLE&GREEN', '#54180C', '#484848', '#CCFCF0'),
    _c('绿松石&水鸭绿&琥珀 SAN011', 'TURQUOISE&TEAL&AMBER', '#003C54', '#303000', '#484848'),
    _c('红色&金色&紫色 SAN012', 'RED&GOLD&PURPLE', '#480C6C', '#242424', '#FCF0C0'),
    _c('绿色&红色&紫色 SAN013', 'GREEN&RED&PURPLE', '#480030', '#183000', '#D884F0'),
    _c('绿色&金色&黑色 SAN014', 'GREEN&GOLD&BLACK', '#003018', '#CCCC84', '#3C3C3C'),
    _c('黑色&紫色&金色 SAN015', 'BLACK&PURPLE&GOLD', '#242424', '#546030', '#E4F0B4'),
    _c('紫色气泡 SS001', 'Purple Crush', '#C0CCF0', '#604884', '#242424'),
    _c('皇家幻影 SS002', 'Royal Mirage', '#242424', '#E4D830', '#CC90B4'),
    _c('四原色 SS003', 'Four Primary Colors', '#242424', '#1818B4', '#480C60'),
    _c('蒸汽朋克 SS004', 'Steampunk', '#000C00', '#E4E4E4', '#183048'),
]

# 彩多屋 PLA+（官方在售 34 色，来源 cailab3d.com）
CAILAB_PLA_PLUS: list[dict] = [
    _c('红色 AC199', 'Red', '#E03030'),
    _c('秋海棠色 AC190', 'Begonia', '#F87888'),
    _c('黄色 AC107', 'Yellow', '#E8D020'),
    _c('橙色 AC021', 'Orange', '#F86838'),
    _c('灰色 AC11', 'Gray', '#282830'),
    _c('蓝色 AC2145', 'Blue', '#002878'),
    _c('品红 AC239', 'Magenta', '#D03088'),
    _c('黑色 AC419', 'Black', '#000000'),
    _c('巧克力色 AC476', 'Chocolate', '#503828'),
    _c('浅蓝 AC635', 'Light Blue', '#A8E8E0'),
    _c('橙色 AC1655', 'Orange', '#E05000'),
    _c('青色 AC2925', 'Cyan', '#2888D0'),
    _c('蜜桃绒 AC6023', 'Peach Fuzz', '#E8B080'),
    _c('樱花粉 AC6050', 'Sakura Pink', '#F8D0E0'),
    _c('猎人绿 AC6060', 'Hunter Green', '#183028'),
    _c('青柠色 AC6192', 'Lime', '#E0F038'),
    _c('沙漠色 AC7501', 'Desert', '#C8B080'),
    _c('薰衣草紫 AC2725', 'Lavender', '#484088'),
    _c('橄榄绿 AC2306', 'Olive Green', '#484818'),
    _c('棕色 AC2317', 'Brown', '#987048'),
    _c('绿色 AC2420', 'Green', '#008000'),
    _c('银色 ATM422', 'Silver', '#C0C0C0'),
    _c('白色 AC9003', 'White', '#E8E8E8'),
    _c('紫罗兰 AC266', 'Violet', '#481070'),
    _c('军绿色 AC5753', 'Army Green', '#384020'),
    _c('绯红 AC1807', 'Crimson', '#500000'),
    _c('浅灰 AC421', 'Light Gray', '#808080'),
    _c('丁香 AC2583', 'Lilac', '#9048B0'),
    _c('芒果黄 AC2010', 'Mango Yellow', '#F8B810'),
    _c('藏青蓝 AC281', 'Old Glory Blue', '#204078'),
    _c('芥末黄 AC115', 'Mustard Yellow', '#E0C030'),
    _c('透明 ACL', 'Clear ACL', '#C0C0C0'),
    _c('深棕 AC7517', 'DARK BROWN', '#805028'),
    _c('杏色 AC7604', 'Apricot', '#D8C0B8'),
]

# 彩多屋 PETG（官方在售 29 色，来源 cailab3d.com）
CAILAB_PETG: list[dict] = [
    _c('黑色 G419', 'Black', '#000000'),
    _c('蓝色 G2145', 'Blue', '#082878'),
    _c('白色 G9003', 'White', '#E0E0E0'),
    _c('半透 GCL', 'Translucent  GCL', '#C0C0C0'),
    _c('灰色 G11', 'Gray', '#585860'),
    _c('红色 G199', 'Red', '#E84848'),
    _c('黄色 G107', 'Yellow', '#E8D858'),
    _c('橙色 G021', 'Orange', '#F86828'),
    _c('橄榄绿 G2306', 'Olive Green', '#485028'),
    _c('棕色 G2317', 'Brown', '#603820'),
    _c('绿色 G2420', 'Green', '#00A000'),
    _c('紫色 G2725', 'Purple', '#483078'),
    _c('青色 G2925', 'Cyan', '#0088D0'),
    _c('蜜桃奶油 G6023', 'Peach Cream', '#F8D0B8'),
    _c('粉色 G6050', 'Pink', '#F8D0D0'),
    _c('猎人绿 G2265', 'Hunter Green', '#406038'),
    _c('金色 G6005', 'Golden', '#D8A030'),
    _c('草绿色 G2421', 'Grass Green', '#80D840'),
    _c('米色 G155', 'Beige', '#F8E8A8'),
    _c('冰蓝色 G635', 'Ice Blue', '#C0E0E0'),
    _c('银色 G422', 'Silver', '#E0E0E0'),
    _c('咖啡色 G2469', 'Coffee', '#382010'),
    _c('深蓝色 G2369', 'Dark Blue', '#281890'),
    _c('半透蓝 G637', 'Translucent Blue', '#B0E0F8'),
    _c('半透棕 G728', 'Translucent Brown', '#F8E0C8'),
    _c('半透绿 G6142', 'Translucent Green', '#00D0A8'),
    _c('半透粉 G176', 'Translucent Pink', '#F8A8A8'),
    _c('半透黄 G6192', 'Translucent Yellow', '#F8F878'),
    _c('半透橙 G1375', 'Translucent Orange', '#F89848'),
]

BRAND_COLOR_SERIES_EXTRA: dict[str, dict[str, list[dict]]] = {
    "彩多屋": {
        '金属 PLA': CAILAB_METALLIC_PLA,
        'PLA-CF': CAILAB_PLA_CF,
        '哑光 PLA': CAILAB_MATTE_PLA,
        'PETG-CF': CAILAB_PETG_CF,
        '丝绸 PLA': CAILAB_SILK_PLA,
        '三色丝绸 PLA': CAILAB_TRI_SILK_PLA,
        'PLA+': CAILAB_PLA_PLUS,
        'PETG': CAILAB_PETG,
    },
}

# 材料 -> 适用系列（PLA 挂 PLA 系，PETG 挂 PETG 系）
MATERIAL_COLOR_SERIES_EXTRA: dict[str, list[str]] = {
    "PLA": ['金属 PLA', 'PLA-CF', '哑光 PLA', '丝绸 PLA', '三色丝绸 PLA', 'PLA+'],
    "PETG": ['PETG-CF', 'PETG'],
}
