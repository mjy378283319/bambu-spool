"""彩多屋（CAILAB）官方配色预设 —— 由 scripts/build_cailab_colors.py 自动生成，勿手改。

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


# 彩多屋 金属 PLA（官方在售 7 色，来源 cailab3d.com）
CAILAB_METALLIC_PLA: list[dict] = [
    _c('Cobalt Blue ATM2152', 'Cobalt Blue', '#385068'),
    _c('Iridium Gold ATM4645', 'Iridium Gold', '#D0B8A8'),
    _c('Red oak ATM7516', 'Red oak', '#682808'),
    _c('Silver ATM422', 'Silver', '#C0C0C0'),
    _c('Amber Gold ATM6003', 'Amber Gold', '#E0B860'),
    _c('Black Walmut ATM2469', 'Black Walmut', '#402820'),
    _c('Oxide Green ATM568', 'Oxide Green', '#003018'),
]

# 彩多屋 PLA-CF（官方在售 1 色，来源 cailab3d.com）
CAILAB_PLA_CF: list[dict] = [
    _c('Black', 'Black', '#505050'),
]

# 彩多屋 哑光 PLA（官方在售 12 色，来源 cailab3d.com）
CAILAB_MATTE_PLA: list[dict] = [
    _c('Ivory MT9003', 'Ivory', '#F0F0E8'),
    _c('Rose Quartz MT1404', 'Rose Quartz', '#C8A098'),
    _c('Pudding Yellow MT2001', 'Pudding Yellow', '#E8D888'),
    _c('Latte MT2317', 'Latte', '#A88058'),
    _c("Robin's Egg Blue MT319", "Robin's Egg Blue", '#58A898'),
    _c('Beige MT4030', 'Beige', '#E0C0A0'),
    _c('Hazy Blue MT6109', 'Hazy Blue', '#708090'),
    _c('Matcha Green MT7492', 'Matcha Green', '#B0B860'),
    _c('Black MT419', 'Black', '#101010'),
    _c('Sakura Pink MT6050', 'Sakura Pink', '#E0B0C0'),
    _c('Misty Lilac MT256', 'Misty Lilac', '#B8A0C0'),
    _c('Muted Olive MT6178', 'Muted Olive', '#A0D0A8'),
]

# 彩多屋 PETG-CF（官方在售 9 色，来源 cailab3d.com）
CAILAB_PETG_CF: list[dict] = [
    _c('Wine Red', 'Wine Red', '#B87068'),
    _c('Green', 'Green', '#409888'),
    _c('Blue', 'Blue', '#7078B8'),
    _c('Purple', 'Purple', '#A078B0'),
    _c('Gray', 'Gray', '#C8C8C0'),
    _c('Black', 'Black', '#686868'),
    _c('Matcha Green', 'Matcha Green', '#B0D0A8'),
    _c('Misty Blue', 'Misty Blue', '#C8C0D8'),
    _c('Sandy Beige', 'Sandy Beige', '#E8B8B8'),
]

# 彩多屋 丝绸 PLA（官方在售 17 色，来源 cailab3d.com）
CAILAB_SILK_PLA: list[dict] = [
    _c('Sunshine Gold AS123', 'Sunshine Gold', '#F0A000'),
    _c('Gold AS6006', 'Gold', '#886000'),
    _c('Blue AS2145', 'Blue', '#002070'),
    _c('Red AS199', 'Red', '#A00800'),
    _c('Silver AS422', 'Silver', '#606068'),
    _c('Pearl White AS9003', 'Pearl White', '#D8D8C8'),
    _c('Rose AS205', 'Rose', '#B01048'),
    _c('Xmas Green AS347', 'Xmas Green', '#005818'),
    _c('Midnight  Black AS419', 'Midnight  Black', '#202020'),
    _c('Copper AS471', 'Copper', '#683810'),
    _c('Coral Pink AS1775', 'Coral Pink', '#F87070'),
    _c('Crimson AS1807', 'Crimson', '#600000'),
    _c('Purple AS2602', 'Purple', '#680050'),
    _c('Brown Copper AS4013', 'Brown Copper', '#602808'),
    _c("Robin's Egg Blue AS319", "Robin's Egg Blue", '#60B0A0'),
    _c('Bronze AS5767', 'Bronze', '#606030'),
    _c('Taro Purple AS256', 'Taro Purple', '#C8B0D0'),
]

# 彩多屋 三色丝绸 PLA（官方在售 41 色，来源 cailab3d.com）
CAILAB_TRI_SILK_PLA: list[dict] = [
    _c('Red&Black SP001', 'Red&Black', '#CCCCCC'),
    _c('Magenta&Gold SP002', 'Magenta&Gold', '#CCCCCC'),
    _c('Blue&Green SP003', 'Blue&Green', '#CCCCCC'),
    _c('Green&Gold SP004', 'Green&Gold', '#CCCCCC'),
    _c('Purple&Blue SP005', 'Purple&Blue', '#CCCCCC'),
    _c('Blue&Gold SP006', 'Blue&Gold', '#CCCCCC'),
    _c('Silver&Gold SP007', 'Silver&Gold', '#CCCCCC'),
    _c('Black&Gold SP008', 'Black&Gold', '#CCCCCC'),
    _c('Pink&Gold SP009', 'Pink&Gold', '#CCCCCC'),
    _c('Rose&Azure SP010', 'Rose&Azure', '#CCCCCC'),
    _c('Pink&Lilac SP011', 'Pink&Lilac', '#CCCCCC'),
    _c('Blue&Silver SP012', 'Blue&Silver', '#CCCCCC'),
    _c('Purple&Gold SP013', 'Purple&Gold', '#CCCCCC'),
    _c('Red&Gold SP014', 'Red&Gold', '#CCCCCC'),
    _c('Black&Green SP015', 'Black&Green', '#CCCCCC'),
    _c('Black&Purple SP016', 'Black&Purple', '#CCCCCC'),
    _c('Black&Silver SP017', 'Black&Silver', '#CCCCCC'),
    _c('Purple&Green SP018', 'Purple&Green', '#CCCCCC'),
    _c('Magenta&Green SP019', 'Magenta&Green', '#CCCCCC'),
    _c('Sakura white SP020', 'Sakura white', '#CCCCCC'),
    _c('Moonlight Pink SP021', 'Moonlight Pink', '#CCCCCC'),
    _c('Gold&Lavender SP022', 'Gold&Lavender', '#CCCCCC'),
    _c('Blue&Black SP023', 'Blue&Black', '#CCCCCC'),
    _c('Blue&Copper SP024', 'Blue&Copper', '#CCCCCC'),
    _c('PURPLE&BLUE&YELLOW SAN001', 'PURPLE&BLUE&YELLOW', '#CCCCCC'),
    _c('RED&YELLOW&GREEN SAN002', 'RED&YELLOW&GREEN', '#CCCCCC'),
    _c('RED&GREEN&BLUE SAN003', 'RED&GREEN&BLUE', '#CCCCCC'),
    _c('GREEN&GOLD&PURPLE SAN004', 'GREEN&GOLD&PURPLE', '#CCCCCC'),
    _c('TRISTLE&SAGE&GRAPE SAN005', 'TRISTLE&SAGE&GRAPE', '#CCCCCC'),
    _c('GOLD&SILVER&COPPER SAN007', 'GOLD&SILVER&COPPER', '#CCCCCC'),
    _c('YELLOW&GREEN&BLUE SAN008', 'YELLOW&GREEN&BLUE', '#CCCCCC'),
    _c('COPPER&PURPLE&GREEN SAN010', 'COPPER&PURPLE&GREEN', '#CCCCCC'),
    _c('TURQUOISE&TEAL&AMBER SAN011', 'TURQUOISE&TEAL&AMBER', '#CCCCCC'),
    _c('RED&GOLD&PURPLE SAN012', 'RED&GOLD&PURPLE', '#CCCCCC'),
    _c('GREEN&RED&PURPLE SAN013', 'GREEN&RED&PURPLE', '#CCCCCC'),
    _c('GREEN&GOLD&BLACK SAN014', 'GREEN&GOLD&BLACK', '#CCCCCC'),
    _c('BLACK&PURPLE&GOLD SAN015', 'BLACK&PURPLE&GOLD', '#CCCCCC'),
    _c('Purple Crush SS001', 'Purple Crush', '#CCCCCC'),
    _c('Royal Mirage SS002', 'Royal Mirage', '#CCCCCC'),
    _c('Four Primary Colors SS003', 'Four Primary Colors', '#CCCCCC'),
    _c('Steampunk SS004', 'Steampunk', '#CCCCCC'),
]

# 彩多屋 PLA+（官方在售 34 色，来源 cailab3d.com）
CAILAB_PLA_PLUS: list[dict] = [
    _c('Red AC199', 'Red', '#E03030'),
    _c('Begonia AC190', 'Begonia', '#F87888'),
    _c('Yellow AC107', 'Yellow', '#E8D020'),
    _c('Orange AC021', 'Orange', '#F86838'),
    _c('Gray AC11', 'Gray', '#282830'),
    _c('Blue AC2145', 'Blue', '#002878'),
    _c('Magenta AC239', 'Magenta', '#D03088'),
    _c('Black AC419', 'Black', '#000000'),
    _c('Chocolate AC476', 'Chocolate', '#503828'),
    _c('Light Blue AC635', 'Light Blue', '#A8E8E0'),
    _c('Orange AC1655', 'Orange', '#E05000'),
    _c('Cyan AC2925', 'Cyan', '#2888D0'),
    _c('Peach Fuzz AC6023', 'Peach Fuzz', '#E8B080'),
    _c('Sakura Pink AC6050', 'Sakura Pink', '#F8D0E0'),
    _c('Hunter Green AC6060', 'Hunter Green', '#183028'),
    _c('Lime AC6192', 'Lime', '#E0F038'),
    _c('Desert AC7501', 'Desert', '#C8B080'),
    _c('Lavender AC2725', 'Lavender', '#484088'),
    _c('Olive Green AC2306', 'Olive Green', '#484818'),
    _c('Brown AC2317', 'Brown', '#987048'),
    _c('Green AC2420', 'Green', '#008000'),
    _c('Silver ATM422', 'Silver', '#C0C0C0'),
    _c('White AC9003', 'White', '#E8E8E8'),
    _c('Violet AC266', 'Violet', '#481070'),
    _c('Army Green AC5753', 'Army Green', '#384020'),
    _c('Crimson AC1807', 'Crimson', '#500000'),
    _c('Light Gray AC421', 'Light Gray', '#808080'),
    _c('Lilac AC2583', 'Lilac', '#9048B0'),
    _c('Mango Yellow AC2010', 'Mango Yellow', '#F8B810'),
    _c('Old Glory Blue AC281', 'Old Glory Blue', '#204078'),
    _c('Mustard Yellow AC115', 'Mustard Yellow', '#E0C030'),
    _c('Clear ACL', 'Clear ACL', '#C0C0C0'),
    _c('DARK BROWN AC7517', 'DARK BROWN', '#805028'),
    _c('Apricot AC7604', 'Apricot', '#D8C0B8'),
]

# 彩多屋 PETG（官方在售 29 色，来源 cailab3d.com）
CAILAB_PETG: list[dict] = [
    _c('Black G419', 'Black', '#000000'),
    _c('Blue G2145', 'Blue', '#082878'),
    _c('White G9003', 'White', '#E0E0E0'),
    _c('Translucent  GCL', 'Translucent  GCL', '#C0C0C0'),
    _c('Gray G11', 'Gray', '#585860'),
    _c('Red G199', 'Red', '#E84848'),
    _c('Yellow G107', 'Yellow', '#E8D858'),
    _c('Orange G021', 'Orange', '#F86828'),
    _c('Olive Green G2306', 'Olive Green', '#485028'),
    _c('Brown G2317', 'Brown', '#603820'),
    _c('Green G2420', 'Green', '#00A000'),
    _c('Purple G2725', 'Purple', '#483078'),
    _c('Cyan G2925', 'Cyan', '#0088D0'),
    _c('Peach Cream G6023', 'Peach Cream', '#F8D0B8'),
    _c('Pink G6050', 'Pink', '#F8D0D0'),
    _c('Hunter Green G2265', 'Hunter Green', '#406038'),
    _c('Golden G6005', 'Golden', '#D8A030'),
    _c('Grass Green G2421', 'Grass Green', '#80D840'),
    _c('Beige G155', 'Beige', '#F8E8A8'),
    _c('Ice Blue G635', 'Ice Blue', '#C0E0E0'),
    _c('Silver G422', 'Silver', '#E0E0E0'),
    _c('Coffee G2469', 'Coffee', '#382010'),
    _c('Dark Blue G2369', 'Dark Blue', '#281890'),
    _c('Translucent Blue G637', 'Translucent Blue', '#B0E0F8'),
    _c('Translucent Brown G728', 'Translucent Brown', '#F8E0C8'),
    _c('Translucent Green G6142', 'Translucent Green', '#00D0A8'),
    _c('Translucent Pink G176', 'Translucent Pink', '#F8A8A8'),
    _c('Translucent Yellow G6192', 'Translucent Yellow', '#F8F878'),
    _c('Translucent Orange G1375', 'Translucent Orange', '#F89848'),
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
