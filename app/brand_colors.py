"""品牌配色预设（自动生成 + 人工核对，勿手改排序）。

数据来源：
- Kexcelled：kexcelled3d.com 官方商品页色名（中/英），HEX 从官方产品图取主色，为近似值；
  K5 PETG Rapid 的 HEX 直接从官方 Shopify 商品图逐色取主色（2026-09-16）
- 兰博：tyzh.com 官网产品图取主色 + 常规色人工校正，均为近似值
- 魔创：淘宝官方店（shop462851793）商品 SKU 色名 + SKU 图取主色，均为近似值
- 拓竹：store.bambulab.com 官方公布的 Hex Code Table（PLA Basic / PLA Matte / PETG Basic
  / PETG HF），这些是官方色值（official=True）
- 大简：京东/淘宝官方店在售 SKU 色名 + 官方微博展示色，HEX 为近似值
"""

def _c(name: str, en: str, hex_value: str) -> dict:
    # 该文件里的 HEX 均非官方公布色值，一律视为近似值
    # ⚠️ name 是界面显示名（前端点色块时会把 name 填进「颜色名」输入框）。
    # 2026-09-19 起全部品牌的 name 都是中文（en 保留原名做对照/识色备注）；
    # 新增品牌时务必直接填中文名，别再传空串。
    return {"name": name or en, "en": en, "hex": hex_value, "official": False}

def _co(name: str, en: str, hex_value: str) -> dict:
    # 厂商官方公布的色值（拓竹 Hex Code Table）
    return {"name": name or en, "en": en, "hex": hex_value, "official": True}

KEXCELLED_K5_PLA: list[dict] = [
    _c('凯蒂粉', 'Kitty Pink', '#FBB3BA'),
    _c('暗玫瑰粉', 'Dark Rose Pink', '#683440'),
    _c('白色', 'White', '#E5E5E5'),
    _c('草绿', 'Grass Green', '#7FD530'),
    _c('橙色', 'Orange', '#FC6A17'),
    _c('粉蓝色', 'Pinkish Blue', '#2DCDCC'),
    _c('粉色', 'Pink', '#FC737F'),
    _c('肤色', 'Skin', '#F0DBCC'),
    _c('古铜', 'Copper', '#6F5033'),
    _c('骨白', 'Bone White', '#F3E4AC'),
    _c('黑色', 'Black', '#1C1C1C'),
    _c('红色', 'Red', '#D0070D'),
    _c('湖蓝', 'Lake Blue', '#2193E8'),
    _c('黄色', 'Yellow', '#FEEC03'),
    _c('灰蓝', 'Gray Blue', '#778491'),
    _c('灰色', 'Gray', '#888888'),
    _c('金色', 'Gold', '#D8AB62'),
    _c('酒红', 'Wine Red', '#5F1413'),
    _c('孔雀蓝', 'Peacock Blue', '#00949E'),
    _c('蓝色', 'Blue', '#2239A7'),
    _c('蓝紫色', 'Blue Purple', '#6226B1'),
    _c('浅紫色', 'Light Purple', '#554BBA'),
    _c('绿色', 'Green', '#1E8436'),
    _c('美式肤色', 'American Skin', '#ECD5C6'),
    _c('嫩绿', 'Peak Green', '#C4EB69'),
    _c('七分白', 'Seven White', '#E5E5E5'),
    _c('浅橙色', 'Light Orange', '#FC9319'),
    _c('浅蓝色', 'Light Blue', '#68BCF2'),
    _c('浅棕色', 'Light Brown', '#C17D3D'),
    _c('巧克力', 'Chocolate', '#4C210B'),
    _c('青碧色', 'Bluish Green', '#00BF7F'),
    _c('青色', 'Cyan', '#41E9B7'),
    _c('青铜', 'Bronze', '#816D45'),
    _c('三原色品红', 'Process Magenta', '#CE3696'),
    _c('三原色青', 'Process Cyan', '#258DDB'),
    _c('森林绿', 'Forest Green', '#0D3E29'),
    _c('深黄色', 'Dark Yellow', '#F8B00A'),
    _c('墨绿', 'Dark Green', '#004E3E'),
    _c('桃粉色', 'Peach Pink', '#F0CED8'),
    _c('天空蓝', 'Sky Blue', '#3EA6DC'),
    _c('杏仁黄', 'Almond Yellow', '#ECF59C'),
    _c('血红', 'Blood Red', '#8D0C15'),
    _c('薰衣草紫', 'Lavender purple', '#886CBF'),
    _c('银色', 'Silver', '#B9BABF'),
    _c('荧光橙', 'Fluorescent Orange', '#FF6207'),
    _c('荧光红', 'Fluorescent Red', '#FA2B6E'),
    _c('荧光黄', 'Fluorescent Yellow', '#EEFD04'),
    _c('荧光绿', 'Fluorescent Green', '#71F03F'),
    _c('紫色', 'Purple', '#B131A5'),
    _c('自然色', 'Natural', '#ECE8DF'),
    _c('棕色', 'Brown', '#7C4628'),
]

KEXCELLED_K5_PLA_MATTE: list[dict] = [
    _c('牛皮纸', 'Matte Kraft', '#BBA572'),
    _c('肤色', 'Skin', '#D9C8BA'),
    _c('薄粉色', 'Slender Pink', '#E4D6D8'),
    _c('薄荷绿', 'Mint Green', '#C4CF84'),
    _c('薄绿', 'Slender Green', '#A3C7B6'),
    _c('薄紫', 'Slender Purple', '#CFCBD7'),
    _c('宝蓝色', 'Royal blue', '#2C3867'),
    _c('冰蓝', 'Ice blue', '#9CC8E2'),
    _c('车厘子红', 'Chelsea Red', '#8D2425'),
    _c('橙红', 'Orange Red', '#D66E27'),
    _c('赤陶土', 'Matte Terracotta', '#BF9485'),
    _c('淡橘色', 'Pastel orange', '#E6A13B'),
    _c('淡绿色', 'Plastel Green', '#CAD9BF'),
    _c('淡紫', 'Lavender', '#D9D7DD'),
    _c('丁香紫', 'Lilac Purple', '#BDAEDE'),
    _c('浅黄', 'Light Yellow', '#E2DB91'),
    _c('枫炽红', 'Maple Red', '#CC2320'),
    _c('橄榄绿', 'Matte Olive Green', '#3A4A2C'),
    _c('高贵紫', 'Noble Purple', '#9380CB'),
    _c('海军蓝', 'Matte Navy', '#2C3A4D'),
    _c('消光黑', 'Matte Black', '#252626'),
    _c('消光黄', 'Matte Yellow', '#E8C812'),
    _c('灰白', 'Offwhite', '#D5CDBF'),
    _c('焦糖橙', 'Burnt Orange', '#BA6E35'),
    _c('芥末黄', 'Matte Mustard Yellow', '#C69C2E'),
    _c('芥末绿', 'Mustard Green', '#92892C'),
    _c('军绿', 'Army Green', '#343D1A'),
    _c('科技灰', 'Matte Tech Gray', '#9CA0A0'),
    _c('青碧色', 'Bluish Gray', '#407079'),
    _c('栗色', 'Maroon', '#611226'),
    _c('麦芽色', 'Matte Malt Clay', '#756347'),
    _c('明黄', 'Hot yellow', '#D5D93A'),
    _c('奶黄', 'Creamy yellow', '#E0DFC0'),
    _c('奶绿', 'Milk Green', '#D9E4CA'),
    _c('嫩青', 'Vivid Cyan', '#ABDACB'),
    _c('暖灰', 'Matte Warm Gray', '#8B8677'),
    _c('浅赤陶土', 'Light Matte Terracotta', '#CE9F97'),
    _c('浅肤色', 'Light Skin', '#E6D9D2'),
    _c('浅米白', 'Light Beige', '#CDCABE'),
    _c('浅木色', 'Light Wood', '#C4BCB2'),
    _c('浅棕色', 'Light Brown', '#846549'),
    _c('青绿', 'Green Aurora', '#26B694'),
    _c('晴蓝', 'Sunny Blue', '#A6C3DF'),
    _c('珊瑚粉', 'Coral Pink', '#EACED4'),
    _c('深棕', 'Dark Brown', '#413421'),
    _c('水蓝', 'Aqua Blue', '#C3D5DD'),
    _c('松绿', 'Pine Green', '#1A6044'),
    _c('松石绿', 'Matte Turquoise', '#47C2C7'),
    _c('桃粉色', 'Peach Pink', '#F0CED8'),
    _c('藤紫', 'Rattan Purple', '#B7A8D2'),
    _c('白色', 'White', '#DFDFDF'),
    _c('烟灰', 'Ash Gray', '#404243'),
    _c('烟熏紫', 'Ash Purple', '#715D61'),
    _c('夜岩黑', 'Nightstone black', '#2C2B2B'),
    _c('棕色', 'Brown', '#534026'),
]

KEXCELLED_K5_PETG: list[dict] = [
    _c('棕色', 'Brown', '#74361D'),
    _c('白色', 'White', '#E3E3E2'),
    _c('博世蓝绿色', 'Bosch Blue Green', '#375659'),
    _c('草绿', 'Grass Green', '#7AD13F'),
    _c('橙色', 'Orange', '#E1612A'),
    _c('杜瓦特黄色', 'Dewalt Yellow', '#F2A93F'),
    _c('粉蓝色', 'Pinkish Blue', '#8EE9ED'),
    _c('粉色', 'Pink', '#FF7E8A'),
    _c('肤色', 'Skin', '#F0E1D0'),
    _c('古铜', 'Copper', '#693B1D'),
    _c('光扩散', 'Diffuse Clear White', '#ECE6E1'),
    _c('赫拉克勒斯蓝', 'Hercules Blue', '#165A8C'),
    _c('黑色', 'Black', '#181818'),
    _c('红色', 'Red', '#F13931'),
    _c('湖蓝', 'Lake Blue', '#1A92E5'),
    _c('黄色', 'Yellow', '#FDE81E'),
    _c('灰蓝', 'Gray Blue', '#70798C'),
    _c('灰色', 'Gray', '#9F9FA3'),
    _c('金色', 'Gold', '#D39939'),
    _c('孔雀蓝', 'Peacock Blue', '#13AFDF'),
    _c('蓝色', 'Blue', '#1F2CA1'),
    _c('蓝紫色', 'Blue Purple', '#6F34AC'),
    _c('绿色', 'Green', '#33B362'),
    _c('嫩绿', 'Peak Green', '#D0E172'),
    _c('浅橙色', 'Light Orange', '#FC7A0E'),
    _c('浅紫色', 'Light Purple', '#8F76D5'),
    _c('浅棕色', 'Light Brown', '#C27321'),
    _c('巧克力', 'Chocolate', '#3F2019'),
    _c('青色', 'Cyan', '#96E6C8'),
    _c('青铜', 'Bronze', '#615439'),
    _c('深黄色', 'Dark Yellow', '#E6A514'),
    _c('墨绿', 'Dark Green', '#0A5D6B'),
    _c('透明白', 'Transparent White', '#E7E6E5'),
    _c('透明勃肯第红', 'Transparent Burgundy', '#CD111B'),
    _c('透明橙', 'Transparent Orange', '#ED9F12'),
    _c('透明粉', 'Transparent Pink', '#F5CCD4'),
    _c('透明橄榄绿', 'Transparent Olive Green', '#83981F'),
    _c('透明黑', 'Transparent Black', '#65605D'),
    _c('透明红', 'Transparent Red', '#F42F38'),
    _c('透明黄', 'Transparent Yellow', '#FDE41C'),
    _c('透明蓝', 'Transparent Blue', '#5974B9'),
    _c('透明墨绿', 'Transparent Dark Green', '#2E6C27'),
    _c('透明浅紫', 'Transparent Light Purple', '#CFB0E3'),
    _c('透明水晶绿', 'Transparent Crystal Green', '#89D0C5'),
    _c('透明丝绸蓝', 'Transparent Silk Blue', '#9DD3E3'),
    _c('透明棕', 'Transparent Brown', '#7F573F'),
    _c('透明博世蓝绿', 'Transparent Bosch Blue Green', '#1A5760'),
    _c('银色', 'Silver', '#C1C2C2'),
    _c('荧光绿', 'Fluorescent Green', '#64F44F'),
    _c('遮光白', 'Light-shielding White', '#E2E2E2'),
    _c('紫色', 'Purple', '#D848B7'),
    _c('Natural', 'Natural', '#EEE8DA'),
]

KEXCELLED_K5_PETG_MATTE: list[dict] = [
    _c('苹果绿', '', '#A9CD48'),
    _c('风趣蓝', '', '#BCC7E0'),
    _c('军绿', '', '#3B4C2E'),
    _c('黑色', 'Black', '#1E1F1F'),
    _c('温馨黄', '', '#DAC9A0'),
    _c('焦糖橙', '', '#CCAD8F'),
    _c('车厘子红', '', '#5F1C22'),
    _c('藏青色', '', '#2F353F'),
    _c('金穗黄', '', '#F2EC12'),
    _c('风韵紫', '', '#646079'),
    _c('雾霭蓝', '', '#6D7C90'),
    _c('茱萸粉', '', '#E0C0C2'),
    _c('鼠尾草绿', '', '#C4D9BE'),
    _c('暖灰', '', '#D6D2CE'),
    _c('白色', 'White', '#DCDCDC'),
    _c('肤色', 'Skin', '#F2E1CE'),
    _c('巧克力', 'Chocolate', '#63422E'),
    _c('赤陶土', '', '#DE8E75'),
    _c('炽果橙', '', '#FA792A'),
    _c('枫炽红', '', '#AF2B25'),
    _c('莫兰迪绿', '', '#244F59'),
    _c('松石绿', '', '#50C3CA'),
]

KEXCELLED_K5_PETG_RAPID: list[dict] = [
    # 独立产品线（THE K5™ PETG Rapid），20 色与普通 K5 PETG 完全不同；
    # 用户实购的「日落橙 / 星雾紫」就在这一系列（此前只录了普通版，对不上）。
    _c('奶油绿', 'Cream Green', '#E2E7B0'),
    _c('白色', 'White', '#F9F9FA'),
    _c('薄荷蓝', 'Mint Blue', '#61C9CF'),
    _c('黑色', 'Black', '#202020'),
    _c('红色', 'Red', '#F32A23'),
    _c('黄色', 'Yellow', '#FEEE26'),
    _c('灰色', 'Gray', '#A1A1A1'),
    _c('金色', 'Gold', '#D79B3D'),
    _c('金属紫', 'Metallic Purple', '#8F6AA9'),
    _c('蓝色', 'Blue', '#2829BF'),
    _c('日落橙', 'Sunset Orange', '#F5510B'),
    _c('绿色', 'Green', '#3BAA57'),
    _c('摩卡棕', 'Mocha Brown', '#6C4C36'),
    _c('柔粉', 'Soft Pink', '#CEB4AF'),
    _c('裸粉', 'Nude Pink', '#ECE2D6'),
    _c('苔藓绿', 'Moss Green', '#305B17'),
    _c('太空灰', 'Space Gray', '#A3A1A5'),
    _c('透明白', 'Clear White', '#EFEDED'),
    _c('星雾紫', 'Mist Purple', '#5C30B4'),
    _c('银色', 'Silver', '#B9B9BA'),
]

# ── 拓竹（官方 Hex Code Table，official=True）─────────────────────
BAMBU_PLA_BASIC: list[dict] = [
    _co('玉石白', 'Jade White', '#FFFFFF'),
    _co('米色', 'Beige', '#F7E6DE'),
    _co('金色', 'Gold', '#E4BD68'),
    _co('银色', 'Silver', '#A6A9AA'),
    _co('灰色', 'Gray', '#8E9089'),
    _co('青铜色', 'Bronze', '#847D48'),
    _co('棕色', 'Brown', '#9D432C'),
    _co('可可棕', 'Cocoa Brown', '#6F5034'),
    _co('酒红色', 'Maroon Red', '#9D2235'),
    _co('红色', 'Red', '#C12E1F'),
    _co('品红', 'Magenta', '#EC008C'),
    _co('粉色', 'Pink', '#F55A74'),
    _co('热粉色', 'Hot Pink', '#F5547C'),
    _co('橙色', 'Orange', '#FF6A13'),
    _co('南瓜橙', 'Pumpkin Orange', '#FF9016'),
    _co('向日葵黄', 'Sunflower Yellow', '#FEC600'),
    _co('黄色', 'Yellow', '#F4EE2A'),
    _co('亮绿色', 'Bright Green', '#BECF00'),
    _co('拓竹绿', 'Bambu Green', '#00AE42'),
    _co('槲寄生绿', 'Mistletoe Green', '#3F8E43'),
    _co('绿松石', 'Turquoise', '#00B1B7'),
    _co('青色', 'Cyan', '#0086D6'),
    _co('蓝色', 'Blue', '#0A2989'),
    _co('钴蓝', 'Cobalt Blue', '#0056B8'),
    _co('紫色', 'Purple', '#5E43B7'),
    _co('靛紫', 'Indigo Purple', '#482960'),
    _co('蓝灰', 'Blue Gray', '#5B6579'),
    _co('浅灰', 'Light Gray', '#D1D3D5'),
    _co('深灰', 'Dark Gray', '#545454'),
    _co('黑色', 'Black', '#000000'),
]

BAMBU_PLA_MATTE: list[dict] = [
    _co('象牙白', 'Ivory White', '#FFFFFF'),
    _co('骨白', 'Bone White', '#CBC6B8'),
    _co('拿铁棕', 'Latte Brown', '#D3B7A7'),
    _co('焦糖', 'Caramel', '#AE835B'),
    _co('赤陶', 'Terracotta', '#B15533'),
    _co('沙漠黄', 'Desert Tan', '#E8DBB7'),
    _co('烟灰', 'Ash Gray', '#9B9EA0'),
    _co('水泥灰', 'Nardo Gray', '#757575'),
    _co('丁香紫', 'Lilac Purple', '#AE96D4'),
    _co('樱花粉', 'Sakura Pink', '#E8AFCF'),
    _co('李子紫', 'Plum', '#950051'),
    _co('柑橘橙', 'Mandarin Orange', '#F99963'),
    _co('柠檬黄', 'Lemon Yellow', '#F7D959'),
    _co('猩红', 'Scarlet Red', '#DE4343'),
    _co('深红', 'Dark Red', '#BB3D43'),
    _co('深棕', 'Dark Brown', '#7D6556'),
    _co('黑巧克力', 'Dark Chocolate', '#4D3324'),
    _co('深绿', 'Dark Green', '#68724D'),
    _co('苹果绿', 'Apple Green', '#C2E189'),
    _co('草绿', 'Grass Green', '#61C680'),
    _co('冰蓝', 'Ice Blue', '#A3D8E1'),
    _co('天蓝', 'Sky Blue', '#56B7E6'),
    _co('海军蓝', 'Marine Blue', '#0078BF'),
    _co('深蓝', 'Dark Blue', '#042F56'),
    _co('炭黑', 'Charcoal', '#000000'),
]

BAMBU_PETG_BASIC: list[dict] = [
    _co('白色', 'White', '#FFFFFF'),
    _co('红色', 'Red', '#D6001C'),
    _co('橙色', 'Orange', '#FF671F'),
    _co('黄色', 'Yellow', '#FCE300'),
    _co('群青蓝', 'Reflex Blue', '#001489'),
    _co('宝蓝', 'Navy Blue', '#0086D6'),
    _co('雾蓝', 'Misty Blue', '#688197'),
    _co('绿色', 'Green', '#009639'),
    _co('松绿', 'Pine Green', '#034638'),
    _co('深棕', 'Dark Brown', '#4F2C1D'),
    _co('深米色', 'Dark Beige', '#DBC8B6'),
    _co('灰色', 'Gray', '#7F7E83'),
    _co('黑色', 'Black', '#000000'),
]

BAMBU_PETG_HF: list[dict] = [
    _co('白色', 'White', '#FFFFFF'),
    _co('本色', 'Nature', '#F9F7F2'),
    _co('灰色', 'Gray', '#9EA2A2'),
    _co('蓝灰', 'Blue Gray', '#688197'),
    _co('金色', 'Gold', '#B28B33'),
    _co('红色', 'Red', '#D6001C'),
    _co('橙色', 'Orange', '#FF671F'),
    _co('黄色', 'Yellow', '#FCE300'),
    _co('青柠绿', 'Lime Green', '#7CD82B'),
    _co('绿色', 'Green', '#009639'),
    _co('湖蓝', 'Lake Blue', '#0069B1'),
    _co('蓝色', 'Blue', '#001489'),
    _co('紫色', 'Purple', '#9E007E'),
    _co('黑色', 'Black', '#000000'),
]

# ── 大简（GreatSimple，中山大简科技）───────────────────────────────
# 色名取自天猫/京东官方店在售 SKU；HEX 为近似值（官方未公布色值）。
# PETG HF 全 40 色取自天猫官方店商品页 SKU 列表截图取色（2026-09-16，
# 商品 id=944008246964）；其中 9 色为早期已确认色。
# 2026-09-19 用户确认：大简家没有普通 PETG，全系都是 PETG HF ——
# 原「PETG」系列整体并入「PETG HF」，不再单列。
DASU_PETG_HF: list[dict] = [
    _c('白色', 'White', '#E9E9E7'),
    _c('黑色', 'Black', '#222325'),
    _c('灰色', 'Gray', '#8E9091'),
    _c('天蓝色', 'Sky Blue', '#5596E3'),
    _c('橘色', 'Orange', '#FD641F'),
    _c('透明色', 'Transparent', '#E3E7E2'),
    _c('透明紫', 'Transparent Purple', '#B7B1CC'),
    _c('透明绿', 'Transparent Green', '#CBEBAF'),
    _c('透明蓝', 'Transparent Blue', '#B7D9EA'),
    _c('绿色', 'Green', '#67D548'),
    _c('松石绿', 'Turquoise', '#3AA4A9'),
    _c('苹果绿', 'Apple Green', '#A0BF45'),
    _c('青色', 'Cyan Blue', '#3776CE'),
    _c('蓝色', 'Blue', '#2147EA'),
    _c('深蓝色', 'Dark Blue', '#1F3B70'),
    _c('樱花粉', 'Sakura Pink', '#F0B9C4'),
    _c('柠檬黄', 'Lemon Yellow', '#BCBF3D'),
    _c('玫红色', 'Rose Red', '#C45A7C'),
    _c('红色', 'Red', '#C54243'),
    _c('香芋紫', 'Taro Purple', '#A88BC4'),
    _c('紫罗兰', 'Violet', '#5252A0'),
    _c('绀紫色', 'Indigo Purple', '#45395C'),
    _c('紫色', 'Purple', '#645BB1'),
    _c('肤色', 'Skin Tone', '#E8DCCF'),
    _c('暗金色', 'Dark Gold', '#6B5636'),
    _c('拿铁色', 'Latte', '#9E8F75'),
    _c('粉红色', 'Pink', '#E779A4'),
    _c('棕色', 'Brown', '#5E433D'),
    _c('青铜色', 'Bronze', '#4F482F'),
    _c('金色', 'Gold', '#9C7D4B'),
    _c('米白色', 'Off White', '#E3E3DF'),
    _c('玫紫色', 'Magenta Purple', '#A13B9D'),
    _c('桃红色', 'Peach Red', '#BD408B'),
    _c('黄色', 'Yellow', '#F2DD00'),
    _c('杏色', 'Apricot', '#C6B7BA'),
    _c('深灰色', 'Dark Gray', '#4E4E4E'),
    _c('银色', 'Silver', '#D6D6D7'),
    _c('透明粉', 'Transparent Pink', '#EBDDE3'),
    _c('薄荷蓝', 'Mint Blue', '#A8D8D8'),
    _c('蓝灰色', 'Blue Gray', '#565E68'),
]

LANBO_SERIES: dict[str, list[dict]] = {
    'ABS耗材': [
        _c('白色', '', '#D3D2D6'),
        _c('黑色', '', '#2C2B2B'),
        _c('红色', '', '#F90124'),
        _c('蓝色', '', '#0166FE'),
    ],
    'PETG耗材': [
        _c('雾霾蓝', '', '#BCCBE0'),
        _c('白色', '', '#D3D2D6'),
        _c('珠光白', '', '#D6CDCB'),
        _c('肤色', '', '#FAD2B8'),
        _c('草绿色', '', '#76FB85'),
        _c('草莓红', '', '#F75078'),
        _c('橙黄', '', '#FE9112'),
        _c('蛋黄', '', '#FEB43A'),
        _c('黑色', '', '#282828'),
        _c('红色', '', '#F90129'),
        _c('黄色', '', '#F5D437'),
        _c('灰色', '', '#9392A2'),
        _c('活力橙', '', '#FF8140'),
        _c('咖啡色', '', '#7F4434'),
        _c('科技灰', '', '#373133'),
    ],
    'PETG彩虹': [
        _c('海苔', '', '#144527'),
        _c('黑紫', '', '#2E2245'),
        _c('火焰', '', '#FE4221'),
        _c('青柠', '', '#A6F8A0'),
        _c('噬魂', '', '#960812'),
        _c('琉璃红', '', '#B3A6E3'),
        _c('琉璃蓝', '', '#63B9B8'),
        _c('深空', '', '#15156F'),
    ],
    'PLA耗材': [
        _c('化石灰', '', '#292929'),
        _c('薄荷绿', '', '#6EEC9B'),
        _c('橘色', '', '#FF4514'),
        _c('紫色', '', '#A838D8'),
        _c('奶黄', '', '#FEE1A9'),
        _c('粉红', '', '#FF92C3'),
        _c('青色', '', '#A3E5D9'),
        _c('咖啡色', '', '#B85542'),
        _c('大理石', '', '#CFCED7'),
        _c('肤色', '', '#FAD2B8'),
        _c('金色', '', '#F4A61E'),
        _c('本色', '', '#363638'),
        _c('仿木色', '', '#C29A7F'),
        _c('蓝色', '', '#0090E9'),
        _c('宝石蓝', '', '#0166FE'),
    ],
    'PLA+耗材': [
        _c('白色', '', '#CDCCD2'),
        _c('薄荷绿', '', '#6EEC9B'),
        _c('本色', '', '#355584'),
        _c('橙黄', '', '#FFA22E'),
        _c('粉红', '', '#FD87B9'),
        _c('海军灰', '', '#465565'),
        _c('黑色', '', '#353534'),
        _c('红色', '', '#E41B21'),
        _c('黄色', '', '#D6B832'),
        _c('灰色', '', '#9392A2'),
        _c('金色', '', '#FFAC22'),
        _c('橘色', '', '#F66949'),
        _c('科技灰', '', '#B4BABA'),
        _c('蓝色', '', '#3195E9'),
        _c('亮绿', '', '#ABE136'),
    ],
    'PLA哑光': [
        _c('白色', '', '#CCC8D2'),
        _c('薄荷绿', '', '#A7E7B3'),
        _c('橙黄', '', '#E5890E'),
        _c('灰色', '', '#C2C2CC'),
        _c('黑色', '', '#2E2D2F'),
        _c('红色', '', '#C43036'),
        _c('科技灰', '', '#666269'),
        _c('抹茶绿', '', '#657654'),
        _c('可可棕', '', '#B96952'),
        _c('蓝色', '', '#429BDF'),
        _c('绿色', '', '#39B258'),
        _c('沙漠黄', '', '#D8B487'),
        _c('香芋紫', '', '#B5B4FA'),
        _c('水泥灰', '', '#3A3A3A'),
    ],
    'TPU耗材（95A）': [
        _c('宝石蓝', '', '#3A4AFF'),
        _c('透明', '', '#254C85'),
        _c('透明橙', '', '#E3B9A7'),
        _c('透明绿', '', '#C7FB94'),
        _c('透明红', '', '#E3B9A8'),
        _c('透明黄', '', '#F7F066'),
        _c('黑色', '', '#32323E'),
        _c('肤色', '', '#F4D7BD'),
        _c('蓝色', '', '#75CAFF'),
        _c('灰色', '', '#87828A'),
        _c('雪白色', '', '#D3CED4'),
        _c('绿色', '', '#79E797'),
    ],
    'TPU彩虹': [
        _c('软糖', '', '#F5CA66'),
        _c('清新绿', '', '#86D6C4'),
        _c('蓝白', '', '#68B8F5'),
        _c('紫白', '', '#A386ED'),
        _c('红白', '', '#FF7583'),
    ],
    'PLA金属色': [
        _c('极光绿', '', '#3AB8B4'),
        _c('香槟金', '', '#9A8163'),
        _c('深海蓝', '', '#3B6BAB'),
        _c('玫瑰金', '', '#B14844'),
    ],
    'PLA木质': [
        _c('黑胡桃木', '', '#3F3633'),
        _c('红橡木', '', '#964531'),
        _c('樱桃木', '', '#7A5844'),
        _c('原木色', '', '#EAC5A8'),
    ],
    '其他': [
        _c('大卷装', '', '#16161A'),
    ],
    'PLA水晶彩虹': [
        _c('蓝红', '', '#D594F2'),
        _c('黄绿', '', '#87F196'),
        _c('红紫', '', '#9643D1'),
        _c('蓝绿', '', '#66E3DE'),
    ],
    'PLA水晶闪点': [
        _c('蓝色', '', '#47A2FF'),
        _c('青色', '', '#84E2E1'),
        _c('天蓝色', '', '#87D4E0'),
        _c('紫色', '', '#B786FB'),
        _c('绿色', '', '#97D551'),
        _c('粉色', '', '#D67A99'),
    ],
    'PLA丝绸彩虹': [
        _c('童话', '', '#FFB1E3'),
        _c('mini糖果', '', '#FF9496'),
        _c('芭乐', '', '#FCC6D3'),
        _c('马卡龙', '', '#F6C457'),
        _c('冰淇淋', '', '#F4D9C8'),
        _c('宇宙', '', '#82A6E7'),
        _c('糖果', '', '#8EA1E6'),
        _c('花仙子', '', '#A5E0D0'),
        _c('晚霞', '', '#F4C5FF'),
        _c('黑紫', '', '#3F3744'),
        _c('红金', '', '#E73433'),
        _c('蓝绿', '', '#143759'),
    ],
    'PLA丝绸三色': [
        _c('红黄蓝', '', '#1C2CFD'),
        _c('红金紫', '', '#9E00C0'),
        _c('红蓝绿', '', '#FF62A3'),
        _c('黄绿紫', '', '#138900'),
        _c('金红蓝', '', '#28254B'),
        _c('金蓝红铜', '', '#CA4803'),
        _c('金绿玫红', '', '#FF64A6'),
        _c('蓝绿橙', '', '#0505C3'),
        _c('绿紫铜', '', '#6600C6'),
    ],
    'PLA丝绸双色': [
        _c('蓝红', '', '#D200AD'),
        _c('蓝银', '', '#75BAFA'),
        _c('金绿', '', '#008B2A'),
        _c('红黑', '', '#382D3B'),
        _c('黑紫', '', '#3B313D'),
        _c('黄绿', '', '#C6FB93'),
        _c('金粉', '', '#552336'),
        _c('金紫', '', '#F18230'),
        _c('银黑', '', '#393D48'),
        _c('深蓝深绿', '', '#006217'),
        _c('金红', '', '#FF762B'),
        _c('蓝金', '', '#C3B11E'),
    ],
    'PLA星空闪点': [
        _c('蓝紫', '', '#84798F'),
        _c('蓝色', '', '#0C3A45'),
        _c('绿色', '', '#123829'),
        _c('紫色', '', '#4E1354'),
    ],
    'PLA哑光双色': [
        _c('粉绿', '', '#F68EB6'),
        _c('黑红', '', '#421916'),
        _c('蓝绿', '', '#75D2CB'),
        _c('蓝红', '', '#C977E4'),
        _c('黄绿', '', '#84E674'),
        _c('橙深紫', '', '#F48353'),
        _c('橙红', '', '#F85643'),
    ],
    'PLA哑光岩石': [
        _c('冰川蓝', '', '#75C2F5'),
        _c('矿石红', '', '#C76053'),
        _c('日光橙', '', '#FEA56D'),
        _c('熔岩黑', '', '#3B343F'),
        _c('深海蓝', '', '#36357A'),
        _c('松石绿', '', '#578380'),
    ],
    'PLA夜光彩虹': [
        _c('', '01', '#FFA800'),
        _c('', '02', '#FFA800'),
        _c('', '03', '#FFA800'),
        _c('', '04', '#FEA6CC'),
    ],
    'PLA夜光': [
        _c('绿色', '', '#00F983'),
        _c('蓝色', '', '#00A5FF'),
    ],
    'PLA哑光彩虹': [
        _c('彩虹色', '', '#FED6E3'),
        _c('棒棒糖', '', '#E7C1FA'),
        _c('', '02', '#F6B3D5'),
        _c('黄绿橙', '', '#F7D873'),
        _c('蓝红', '', '#FCB4E8'),
        _c('红珊瑚', '', '#D1CC82'),
        _c('红白', '', '#FFB6D6'),
        _c('蓝棕白', '', '#F9B094'),
        _c('蓝白', '', '#99C3F0'),
        _c('蓝绿', '', '#95FFA1'),
    ],
    'PLA丝绸': [
        _c('冰翠粉', '', '#004489'),
        _c('冰翠青', '', '#D8FFED'),
        _c('冰翠蓝', '', '#B5E5EA'),
        _c('苹果绿', '', '#CFFF92'),
        _c('薰衣草紫', '', '#D4C1E3'),
        _c('白色', '', '#CACACA'),
        _c('亮金色', '', '#FFD906'),
        _c('金色', '', '#FFA800'),
        _c('法老金', '', '#D99A31'),
        _c('青铜色', '', '#C5C13C'),
        _c('红铜色', '', '#B0561A'),
        _c('桃粉色', '', '#FDC8E8'),
        _c('亮银色', '', '#CFD2E0'),
        _c('银灰色', '', '#BDC0CD'),
        _c('黑色', '', '#353239'),
    ],
    'PLA哑光三色': [
        _c('粉黄蓝', '', '#FF9ADA'),
        _c('红黄蓝', '', '#FF3723'),
        _c('红蓝绿', '', '#E30029'),
    ],
    'PETG哑光': [
        _c('樱花粉', '', '#FAD7DA'),
        _c('嫩绿', '', '#C3EA84'),
        _c('浅蓝', '', '#B5E4EB'),
        _c('葡萄紫', '', '#D7A2E3'),
        _c('蛋黄', '', '#F1D393'),
        _c('肤色', '', '#FBD8C4'),
        _c('蓝色', '', '#6CB6F1'),
        _c('中国红', '', '#E14135'),
        _c('灰色', '', '#939197'),
        _c('棕色', '', '#E99974'),
        _c('绿色', '', '#37B792'),
        _c('橙色', '', '#FF7247'),
        _c('白色', '', '#C7C7C8'),
        _c('黑色', '', '#323232'),
    ],
    'PLA碳纤维': [
        _c('PLA碳纤维', '', '#322F2E'),
    ],
    'PETG玻纤/碳纤维': [
        _c('PETG碳纤维', '', '#31353B'),
    ],
    'PETG玻纤': [
        _c('黑色', '', '#302925'),
        _c('白色', '', '#CAC5C5'),
    ],
    'PETG夜光彩虹': [
        _c('', '05', '#6696FF'),
    ],
    'PETG夜光': [
        _c('橙色', '', '#E77602'),
        _c('绿色', '', '#00F983'),
        _c('蓝色', '', '#00A5FF'),
    ],
}

MOCRE_PLA: list[dict] = [
    _c('白色', "", '#DEDCDD'),
    _c('浅灰色', "", '#8A8A8A'),
    _c('灰色', "", '#7A7A79'),
    _c('黑色', "", '#1E1F21'),
    _c('红色', "", '#C60D1D'),
    _c('红橙', "", '#DA2821'),
    _c('黄色', "", '#E1BE02'),
    _c('黄橙', "", '#FB5413'),
    _c('粉色', "", '#CD808E'),
    _c('绿色', "", '#016B37'),
    _c('棕绿色（青铜）', "", '#836833'),
    _c('天蓝色', "", '#147DB5'),
    _c('蓝色', "", '#052AB8'),
    _c('紫色', "", '#5F3AAE'),
    _c('紫红色', "", '#BC1172'),
    _c('浅肤色', "", '#C09B80'),
    _c('浅咖色', "", '#6A4C41'),
    _c('深棕色', "", '#6B3A28'),
    _c('红棕色', "", '#512724'),
    _c('丝绸银色', "", '#AAAAA7'),
    _c('原木色', "", '#B99981'),
    _c('胡桃木色', "", '#9E775A'),
    _c('大理石', "", '#B2B3AF'),
]

MOCRE_PLA_MATTE: list[dict] = [
    _c('奶白', "", '#BDBCBC'),
    _c('灰色', "", '#969595'),
    _c('深灰色', "", '#5D5D5D'),
    _c('黑色', "", '#343434'),
    _c('香蕉黄', "", '#CFC399'),
    _c('沙漠黄', "", '#BDAA87'),
    _c('黄色', "", '#CCB70C'),
    _c('柘黄色', "", '#D0A808'),
    _c('黄橙', "", '#E68E2A'),
    _c('粉色', "", '#C5A7AC'),
    _c('天蓝', "", '#5DA8CB'),
    _c('香芋紫', "", '#9874A9'),
    _c('消防红', "", '#C1373B'),
    _c('浅肤色', "", '#C1B3A6'),
    _c('浅卡其', "", '#958F81'),
    _c('浅咖色', "", '#8E6C47'),
    _c('苏军绿', "", '#515B3D'),
    _c('绿色', "", '#119B42'),
    _c('海军蓝', "", '#273A5A'),
    _c('红棕', "", '#773F38'),
    _c('巧克力棕', "", '#705540'),
]

MOCRE_PLA_PLUS: list[dict] = [
    _c('白色', "", '#BBBBBB'),
    _c('灰色', "", '#7C7C7A'),
    _c('黑色', "", '#232325'),
    _c('绿色', "", '#098838'),
    _c('蓝色', "", '#0B35B5'),
    _c('仿木色', "", '#C3A984'),
    _c('黄色', "", '#D2AE0A'),
    _c('红色', "", '#BF1C20'),
    _c('深棕色', "", '#64312A'),
]

MOCRE_HT_PLA: list[dict] = [
    _c('白色', "", '#C4C4C4'),
    _c('灰色', "", '#838383'),
    _c('深灰色', "", '#47464B'),
    _c('黑色', "", '#292A2C'),
    _c('浅肤色', "", '#BAA68B'),
    _c('浅咖色', "", '#9F7C5C'),
    _c('绿色', "", '#189338'),
    _c('天蓝色', "", '#419CC9'),
    _c('蓝色', "", '#0E449E'),
    _c('黄色', "", '#D6BA1B'),
]

MOCRE_PETG: list[dict] = [
    _c('透明', "", '#D4D4D3'),
    _c('白色', "", '#DBDAD8'),
    _c('正白色', "", '#D2D2D2'),
    _c('遮光白', "", '#DADADC'),
    _c('奶白色', "", '#D6D5D3'),
    _c('浅灰色', "", '#979799'),
    _c('灰色', "", '#757575'),
    _c('黑色', "", '#28292B'),
    _c('肤色', "", '#D7C5B6'),
    _c('粉色', "", '#D6AFC2'),
    _c('樱花粉', "", '#D6879A'),
    _c('洋红色', "", '#D4318C'),
    _c('天蓝色', "", '#2492C6'),
    _c('蓝色', "", '#01318C'),
    _c('藏蓝色', "", '#28355F'),
    _c('牧田蓝', "", '#056979'),
    _c('清新绿', "", '#90C3B0'),
    _c('薄荷绿', "", '#66C8C9'),
    _c('青碧色', "", '#01B89A'),
    _c('草绿', "", '#7CBE02'),
    _c('荧光绿', "", '#28BF01'),
    _c('军绿色', "", '#3C5534'),
    _c('香芋紫', "", '#AC7DC5'),
    _c('黛紫色', "", '#3E2D79'),
    _c('香蕉黄', "", '#D8C47B'),
    _c('锌黄色', "", '#F1BD11'),
    _c('荧光橙', "", '#FE5F07'),
    _c('黄橙', "", '#FB7017'),
    _c('红橙', "", '#E94824'),
    _c('消防红', "", '#B51C2E'),
    _c('红色', "", '#D41D2C'),
    _c('浅咖色', "", '#8A6143'),
    _c('棕色', "", '#693833'),
    _c('金属银', "", '#918F90'),
    _c('金属蓝灰', "", '#676E78'),
    _c('金属枪灰色', "", '#6A6A6C'),
    _c('金属青铜', "", '#83723E'),
    _c('金属黄铜', "", '#9B734F'),
    _c('金属古铜', "", '#814431'),
    _c('金属红铜', "", '#924A3B'),
    _c('金属紫', "", '#7C5584'),
    _c('金属蓝色', "", '#4D708B'),
    _c('金属绿色', "", '#3F665F'),
]

MOCRE_PETG_MATTE: list[dict] = [
    _c('奶白色', "", '#BDBDBA'),
    _c('浅灰色', "", '#979691'),
    _c('灰色', "", '#7A7A7A'),
    _c('深灰色', "", '#58585A'),
    _c('黑色', "", '#363636'),
    _c('卡其色', "", '#A58B7C'),
    _c('香蕉黄', "", '#CFC399'),
    _c('沙漠黄', "", '#B39B7A'),
    _c('锌黄', "", '#D9B107'),
    _c('粉色', "", '#BF9DAD'),
    _c('浅肤色', "", '#C1B3A6'),
    _c('清新绿', "", '#8FBEA2'),
    _c('薄荷绿', "", '#68BAB4'),
    _c('嫩芽绿', "", '#96B410'),
    _c('草绿', "", '#83B909'),
    _c('军绿', "", '#4A5942'),
    _c('苏军绿', "", '#4E563B'),
    _c('橄榄绿', "", '#394133'),
    _c('消防红', "", '#AC1E2C'),
    _c('天蓝', "", '#44A0C1'),
    _c('牧田蓝', "", '#165966'),
    _c('黄橙', "", '#D66B2C'),
    _c('丁香紫', "", '#B8A6BE'),
    _c('香芋紫', "", '#8F769F'),
    _c('长春花蓝', "", '#5C4899'),
    _c('克莱因蓝', "", '#1D2780'),
    _c('浅咖色', "", '#876245'),
    _c('棕色', "", '#6B3D34'),
]

MOCRE_ASA: list[dict] = [
    _c('白色', "", '#C9C9C9'),
    _c('本色', "", '#CBC7BC'),
    _c('灰色', "", '#808080'),
    _c('黑色', "", '#282828'),
    _c('锌黄', "", '#EABB3B'),
    _c('黄橙', "", '#DA782F'),
    _c('红色', "", '#CE2B2C'),
    _c('绿色', "", '#2A8D3B'),
    _c('蓝色', "", '#0F60AC'),
]

MOCRE_ABS: list[dict] = [
    _c('白色', "", '#C1C1C1'),
    _c('奶白', "", '#D2CFCA'),
    _c('本色', "", '#BDB9B0'),
    _c('灰色', "", '#848380'),
    _c('黑色', "", '#28292B'),
    _c('锌黄', "", '#DEB817'),
    _c('橙色', "", '#FE661A'),
    _c('红色', "", '#EC2026'),
    _c('蓝色', "", '#0A6ADD'),
]

# ---- 锐造（官方商品页 SKU 色名 + 商品图取主色，近似值）----

RUIZAO_PLA: list[dict] = [
    _c('白色', 'White', '#EBEBEB'),
    _c('黑色', 'Black', '#2D2D2D'),
    _c('灰色', 'Grey', '#808690'),
    _c('天空蓝', 'Sky Blue', '#88D6FB'),
    _c('阳光橙', 'Sunny Orange', '#F87D1D'),
    _c('橄榄绿', 'Olive Green', '#6B935E'),
    _c('樱桃红', '', '#D03E41'),
    _c('樱花粉', 'Sakura Pink', '#F9C9DB'),
    _c('薄荷绿色', 'Mint Green', '#57E4C6'),
    _c('巧克力', '', '#5F4745'),
    _c('原白色', '', '#E2E8EA'),
    _c('原青色', '', '#6597FE'),
    _c('柠檬黄', 'Lemon Yellow', '#F1EE89'),
    _c('原黄色', '', '#FCF01F'),
    _c('原品红色', '', '#E857C7'),
    _c('黑色 无盘', 'Black', '#3F3F3F'),
    _c('黑色 有盘', 'Black', '#464646'),
    _c('橄榄绿色', 'Olive Green', '#719764'),
    _c('橙色', 'Orange', '#FD8730'),
    _c('仿木色', '', '#E5CEAF'),
    _c('肤色', 'Skin Tone', '#F2D3C6'),
    _c('咖啡色', 'Coffee', '#A1845A'),
    _c('透明', 'Transparent', '#DCDCDC'),
    _c('银色', 'Silver', '#CACCE1'),
    _c('薄荷绿', 'Mint Green', '#5AE6C9'),
]

RUIZAO_PETG: list[dict] = [
    _c('黑色', 'Black', '#3D3D3D'),
    _c('白色', 'White', '#EBEBEB'),
    _c('蓝色', 'Blue', '#444AC5'),
    _c('红色', 'Red', '#ED2B2C'),
    _c('咖啡色', 'Coffee', '#95764D'),
    _c('巧克力色', 'Chocolate', '#503726'),
    _c('橄榄绿色', 'Olive Green', '#7C7D7B'),
    _c('绿色', 'Green', '#41E04C'),
    _c('黄色', 'Yellow', '#DFDF04'),
    _c('肤色', 'Skin Tone', '#F2D0C2'),
    _c('橙色', 'Orange', '#FB7B25'),
    _c('灰色', 'Grey', '#969A9B'),
    _c('阳光橙', 'Sunny Orange', '#E86C2E'),
    _c('樱花粉', 'Sakura Pink', '#F8BCC4'),
    _c('天空蓝', 'Sky Blue', '#42D1EF'),
    _c('薄荷绿', 'Mint Green', '#3DDBC4'),
    _c('透明色', 'Transparent', '#E8E2D8'),
    _c('粉色', 'Pink', '#FE9CCA'),
    _c('碳纤维', '', '#383838'),
    _c('橄榄绿', 'Olive Green', '#70825A'),
    _c('巧克力', '', '#835C52'),
]

RUIZAO_PLA_大理石: list[dict] = [
    _c('花岗岩', '', '#B4B5B5'),
    _c('炭烟黑', '', '#B9B8B6'),
    _c('栗木褐', '', '#BAA184'),
    _c('水泥灰', '', '#7F7E7F'),
    _c('砖红色', '', '#7B4538'),
    _c('森林绿', '', '#ACB3AC'),
]

RUIZAO_PLA_哑光: list[dict] = [
    _c('白色', 'White', '#EBEBEB'),
    _c('黑色', 'Black', '#2D2D2D'),
    _c('灰色', 'Grey', '#808690'),
    _c('原黄色', '', '#FCF01F'),
    _c('樱花粉', 'Sakura Pink', '#F9C9DB'),
    _c('阳光橙', 'Sunny Orange', '#F87D1D'),
    _c('橄榄绿', 'Olive Green', '#6B935E'),
    _c('樱桃红', '', '#D03E41'),
    _c('柠檬黄', 'Lemon Yellow', '#F1EE89'),
    _c('天空蓝', 'Sky Blue', '#88D6FB'),
    _c('巧克力', '', '#5F4745'),
    _c('薄荷绿', 'Mint Green', '#57E4C6'),
    _c('原青色', '', '#6597FE'),
    _c('原白色', '', '#E2E8EA'),
    _c('原品红', '', '#E857C7'),
]

RUIZAO_PLA_BASIC: list[dict] = [
    _c('黑色', 'Black', '#646464'),
    _c('白色', 'White', '#E9E9E9'),
    _c('肤色', 'Skin Tone', '#F2D3C6'),
    _c('透明色', 'Transparent', '#DCDCDC'),
    _c('樱花粉', 'Sakura Pink', '#FCA8BC'),
    _c('银色', 'Silver', '#CACCE1'),
    _c('橙色', 'Orange', '#FD8730'),
    _c('仿木色', '', '#E5CEAF'),
    _c('橄榄绿', 'Olive Green', '#70825A'),
    _c('巧克力', '', '#835C52'),
    _c('咖啡色', 'Coffee', '#A1845A'),
]

RUIZAO_PLA_丝绸: list[dict] = [
    _c('黄金 丝绸', '', '#ECC625'),
    _c('白色 丝绸', 'White', '#E4E4E4'),
    _c('银色 丝绸', 'Silver', '#B9C0CC'),
    _c('灰色 丝绸', 'Grey', '#9CA1A5'),
    _c('粉色 丝绸', 'Pink', '#EEA8BE'),
    _c('红铜 丝绸', '', '#B96C59'),
    _c('西瓜红 丝绸', 'Watermelon Red', '#ED617A'),
    _c('黄色 丝绸', 'Yellow', '#F8F641'),
    _c('彩虹01', '', '#F0F0F0'),
    _c('彩虹02', '', '#EAEAEA'),
    _c('彩虹03', '', '#F2F2F2'),
    _c('彩虹04', '', '#E1F5FE'),
    _c('丝绸金', '', '#F2F2F2'),
    _c('丝绸银', '', '#E6E7F5'),
    _c('丝绸黄色', '', '#F2F2F2'),
    _c('丝绸灰', '', '#D7D7D7'),
    _c('丝绸粉', '', '#F2F2F2'),
    _c('丝绸红铜', '', '#E77C5C'),
    _c('丝绸西瓜红', '', '#F79296'),
    _c('丝绸白色', '', '#F2F2F2'),
]

RUIZAO_ABS: list[dict] = [
    _c('白色', 'White', '#E9E9E9'),
    _c('灰色', 'Grey', '#A1A1A3'),
    _c('黑色', 'Black', '#404040'),
    _c('透明色', 'Transparent', '#DBDBDB'),
]

RUIZAO_PETG_哑光: list[dict] = [
    _c('白色 哑光', 'White', '#EBECEE'),
    _c('黑色 哑光', 'Black', '#4A4A4A'),
    _c('灰色 哑光', 'Grey', '#6F7276'),
    _c('橙色 哑光', 'Orange', '#FDC076'),
    _c('粉色 哑光', 'Pink', '#FE9CCA'),
    _c('天空蓝 哑光', 'Sky Blue', '#56E3FE'),
    _c('薄荷绿 哑光', 'Mint Green', '#3AEACD'),
]

RUIZAO_PETGCF: list[dict] = [
    _c('碳纤维', '', '#383838'),
]

RUIZAO_PETG_夜光: list[dict] = [
    _c('夜光白', 'Glow White', '#61EC8F'),
    _c('夜光绿', 'Glow Green', '#498B60'),
    _c('夜光黄', '', '#BCF149'),
    _c('夜光红', '', '#F65B14'),
    _c('夜光蓝', 'Glow Blue', '#52D5FE'),
]

RUIZAO_PLA_夜光: list[dict] = [
    _c('夜光红', '', '#FE4E4E'),
    _c('夜光绿', 'Glow Green', '#45FC77'),
    _c('夜光黄', '', '#CAFF5A'),
    _c('夜光蓝', 'Glow Blue', '#4ADAFE'),
    _c('夜光白', 'Glow White', '#DAE4CC'),
]

RUIZAO_PLA_木质: list[dict] = [
    _c('原木色', 'Wood', '#99826E'),
    _c('枫木色', 'Maple', '#BCA281'),
]

# ---- JAYO（官方商品页 SKU 色名 + 商品图取主色，近似值）----

JAYO_HS_PETG_哑光: list[dict] = [
    _c('黑色', 'Black', '#6C6C6C'),
    _c('蓝色', 'Blue', '#3432BA'),
    _c('灰色', 'Gray', '#676767'),
    _c('绿色', 'Green', '#29E739'),
    _c('薄荷绿色', 'Mint Green', '#44D9C2'),
    _c('橙色', 'Orange', '#F46136'),
    _c('粉色', 'Pink', '#FAA1D2'),
    _c('红色', 'Red', '#F2585A'),
    _c('天空蓝色', 'Sky Blue', '#59C2F2'),
    _c('白色', 'White', '#D4D4D4'),
    _c('黄色', 'Yellow', '#F6F344'),


]

JAYO_HS_PLA: list[dict] = [
    _c('黑色', 'Black', '#282928'),
    _c('蓝色', 'Blue', '#575857'),
    _c('灰色', 'Gray', '#636363'),
    _c('绿色 1.1K', 'Green 1.1K', '#17D238'),
    _c('橄榄绿色', 'Olive Green', '#435733'),
    _c('橙色', 'Orange', '#FD7401'),
    _c('粉色', 'Pink', '#5A5B59'),
    _c('红色', 'Red', '#636362'),
    _c('白色', 'White', '#E2EBF9'),
    _c('黄色', 'Yellow', '#F3DA08'),


]

JAYO_HS_PLA_哑光: list[dict] = [
    _c('黑色', 'Black', '#363636'),
    _c('樱桃红色', 'Cherry Red', '#C62728'),
    _c('巧克力色', 'chocolate', '#654538'),
    _c('灰色', 'Gray', '#949493'),
    _c('柠檬黄色', 'Lemon Yellow', '#DBD761'),
    _c('薄荷绿色', 'Mint Green', '#656364'),
    _c('橄榄绿色', 'Olive Green', '#536332'),
    _c('樱花粉色', 'Sakura Pink', '#F5B0B3'),
    _c('天空蓝色', 'Sky Blue', '#64C5DA'),
    _c('阳光橙色', 'Sunny Orange', '#E86329'),
    _c('白色', 'White', '#E2EBF9'),


]

JAYO_HS_PLA_大理石: list[dict] = [
    _c('混凝土灰', 'Ashen Concrete', '#838383'),
    _c('砖红色', 'Brick Red', '#742516'),
    _c('栗棕色', 'Chestnut Brown', '#D3C9C7'),
    _c('森林绿', 'Forest Green', '#BBC6C2'),
    _c('奥利奥大理石', 'Oreo Marble', '#C3C7C8'),
    _c('暗影灰', 'Shadow Storm', '#D3D7D8'),


]

JAYO_PETG: list[dict] = [
    _c('米色', 'Beige', '#F8D8C7'),
    _c('黑色', 'Black', '#777777'),
    _c('蓝色', 'Blue', '#3552EB'),
    _c('樱桃红色', 'Cherry Red', '#F54753'),
    _c('巧克力色', 'Chocolate', '#674337'),
    _c('咖啡色', 'Coffee', '#B78A61'),
    _c('青色', 'Cyan', '#29C0E0'),
    _c('灰色', 'Gray', '#666666'),
    _c('绿色', 'Green', '#15D834'),
    _c('柠檬黄色', 'Lemon Yellow', '#E9E661'),
    _c('薄荷绿色', 'Mint Green', '#33C7B7'),
    _c('橄榄绿色', 'Olive Green', '#69825A'),
    _c('橙色', 'Orange', '#F58536'),
    _c('粉色', 'Pink', '#FDA0B4'),
    _c('紫色', 'Purple', '#8454E7'),
    _c('红色', 'Red', '#C53535'),
    _c('樱花粉色', 'Sakura Pink', '#F2C8D2'),
    _c('银色', 'Silver', '#A2A2AA'),
    _c('天空蓝色', 'Sky Blue', '#29C0E0'),
    _c('阳光橙色', 'Sunny Orange', '#F68058'),
    _c('透明色', 'Transparent', '#979391'),
    _c('透明蓝色', 'Transparent Blue', '#0843C5'),
    _c('透明绿色', 'Transparent Green', '#02A004'),
    _c('透明橙色', 'Transparent Orange', '#E86129'),
    _c('透明红色', 'Transparent Red', '#D63436'),
    _c('透明黄色', 'Transparent Yellow', '#C5B402'),
    _c('白色', 'White', '#F6F6F6'),
    _c('黄色', 'Yellow', '#F5D41C'),


]

JAYO_PLA: list[dict] = [
    _c('米色', 'Beige', '#F9D6C5'),
    _c('黑色', 'Black', '#686868'),
    _c('蓝色', 'Blue', '#3452EA'),
    _c('灰蓝色', 'Blue Gray', '#4377D3'),
    _c('樱桃红色', 'Cherry Red', '#F64752'),
    _c('巧克力色', 'Chocolate', '#664237'),
    _c('咖啡色', 'Coffee', '#7A6243'),
    _c('青色', 'Cyan', '#29C4E1'),
    _c('紫红色', 'Fuchsia', '#E730B6'),
    _c('星河绿', 'Galaxy Green', '#446665'),
    _c('黄金色', 'Gold', '#D59435'),
    _c('草绿色', 'Grass Green', '#297862'),
    _c('灰色', 'Gray', '#686868'),
    _c('绿色', 'Green', '#15D834'),
    _c('灰色', 'Grey', '#737979'),
    _c('柠檬黄色', 'Lemon Yellow', '#E9E661'),
    _c('浅金色', 'Light Gold', '#F5C520'),
    _c('薄荷绿色', 'Mint Green', '#33C7B7'),
    _c('橄榄绿色', 'Olive Green', '#698259'),
    _c('橙色', 'Orange', '#F58738'),
    _c('粉色', 'Pink', '#FFA1B6'),
    _c('荧光黄色', 'Pri-Yellow', '#F2B548'),
    _c('紫色', 'Purple', '#8454E4'),
    _c('红色', 'Red', '#C53334'),
    _c('樱花粉色', 'Sakura Pink', '#FBC9D2'),
    _c('银色', 'Silver', '#A9AAB2'),
    _c('天空蓝色', 'Sky Blue', '#36C2EB'),
    _c('星尘紫色', 'Stardust Purple', '#383258'),
    _c('星辉流彩', 'Starlit Flow', '#44566B'),
    _c('阳光橙色', 'Sunny Orange', '#F78056'),
    _c('透明色', 'Transparent', '#969696'),
    _c('透明蓝色', 'Transparent Blue', '#0746CB'),
    _c('透明绿色', 'Transparent Green', '#01A401'),
    _c('透明橙色', 'Transparent Orange', '#E76129'),
    _c('透明紫色', 'Transparent Purple', '#8453FC'),
    _c('透明红色', 'Transparent Red', '#D73434'),
    _c('透明黄色', 'Transparent Yellow', '#B4A402'),
    _c('白色', 'White', '#F7F7F7'),
    _c('仿木色', 'Wood-Like', '#D9B289'),
    _c('黄色', 'Yellow', '#E8C200'),


]

JAYO_PLA_CLASSIC: list[dict] = [
    _c('黑色', 'Black', '#050505'),
    _c('樱桃红色', 'Cherry Red', '#737373'),
    _c('巧克力色', 'Chocolate', '#525252'),
    _c('灰色', 'Gray', '#646873'),
    _c('柠檬黄色', 'Lemon Yellow', '#E4E867'),
    _c('薄荷绿色', 'Mint Green', '#37C7B0'),
    _c('橄榄绿色', 'Olive Green', '#658B52'),
    _c('樱花粉色', 'Sakura Pink', '#F6B7D2'),
    _c('天空蓝色', 'Sky Blue', '#65C7F5'),
    _c('阳光橙色', 'Sunny Orange', '#F88140'),
    _c('白色', 'White', '#555555'),


]

JAYO_PLA_META: list[dict] = [
    _c('米色', 'Beige', '#FDDAC6'),
    _c('黑色', 'Black', '#6C6C6C'),
    _c('蓝色', 'Blue', '#3938F4'),
    _c('樱桃红色', 'Cherry Red', '#F74158'),
    _c('咖啡色', 'Coffee', '#B78A61'),
    _c('紫红色', 'Fuchsia', '#D63BF1'),
    _c('灰色', 'Gray', '#636568'),
    _c('绿色', 'Green', '#15D836'),
    _c('柠檬黄色', 'Lemon Yellow', '#E5E399'),
    _c('薄荷绿色', 'Mint Green', '#08D2BC'),
    _c('橄榄绿色', 'Olive Green', '#819564'),
    _c('橙色', 'Orange', '#FB9829'),
    _c('粉色', 'Pink', '#FD9AC1'),
    _c('紫色', 'Purple', '#A377E6'),
    _c('红色', 'Red', '#D43939'),
    _c('樱花粉色', 'Sakura Pink', '#F2C8D2'),
    _c('天空蓝色', 'Sky Blue', '#23CBF7'),
    _c('阳光橙色', 'Sunny Orange', '#FD9254'),
    _c('白色', 'White', '#D6D6D6'),
    _c('黄色', 'Yellow', '#F9E329'),


]

JAYO_PLA_哑光: list[dict] = [
    _c('米色', 'Beige', '#F9D6C5'),
    _c('黑色', 'Black', '#6C6C6C'),
    _c('蓝色', 'Blue', '#4438D6'),
    _c('灰蓝色', 'Blue Gray', '#4377D3'),
    _c('骨白色', 'Bone-white', '#DBD4C2'),
    _c('樱桃红色', 'Cherry Red', '#F64752'),
    _c('巧克力色', 'Chocolate', '#664237'),
    _c('咖啡色', 'Coffee', '#7A6243'),
    _c('青色', 'Cyan', '#29C4E1'),
    _c('紫红色', 'Fuchsia', '#E730B6'),
    _c('黄金色', 'Gold', '#D59435'),
    _c('草绿色', 'Grass Green', '#297862'),
    _c('灰色', 'Gray', '#65646A'),
    _c('绿色', 'Green', '#65B763'),
    _c('柠檬黄色', 'Lemon Yellow', '#E9E661'),
    _c('浅蓝色', 'Light Blue', '#87C2F1'),
    _c('浅金色', 'Light Gold', '#F5C520'),
    _c('淡黄色', 'Light Yellow', '#E1F541'),
    _c('薄荷绿色', 'Mint Green', '#33C7B7'),
    _c('橄榄绿色', 'Olive Green', '#556741'),
    _c('橙色', 'Orange', '#FB9857'),
    _c('粉色', 'Pink', '#E476A7'),
    _c('粉蓝色', 'Pink Blue', '#B2D5DB'),
    _c('荧光黄色', 'Pri-Yellow', '#F2B548'),
    _c('紫色', 'Purple', '#B455D7'),
    _c('红色', 'Red', '#D54545'),
    _c('樱花粉色', 'Sakura Pink', '#FBC9D2'),
    _c('银色', 'Silver', '#A9AAB2'),
    _c('天空蓝色', 'Sky Blue', '#36C2EB'),
    _c('阳光橙色', 'Sunny Orange', '#F78056'),
    _c('陶泥色', 'Terracotta', '#686254'),
    _c('透明色', 'Transparent', '#969696'),
    _c('透明蓝色', 'Transparent Blue', '#0746CB'),
    _c('透明绿色', 'Transparent Green', '#01A401'),
    _c('透明橙色', 'Transparent Orange', '#E76129'),
    _c('透明紫色', 'Transparent Purple', '#8453FC'),
    _c('透明红色', 'Transparent Red', '#D73434'),
    _c('透明黄色', 'Transparent Yellow', '#B4A402'),
    _c('白色', 'White', '#152891'),
    _c('仿木色', 'Wood-Like', '#D9B289'),
    _c('黄色', 'Yellow', '#E8C200'),


]

JAYO_PLA_闪点: list[dict] = [
    _c('黑色', 'Black', '#6C6C6C'),
    _c('蓝色', 'Blue', '#84C6E7'),


]

JAYO_PLA_20: list[dict] = [
    _c('米色', 'Beige', '#F9D6C5'),
    _c('黑色', 'Black', '#686868'),
    _c('蓝色', 'Blue', '#3452EA'),
    _c('灰蓝色', 'Blue Gray', '#4377D3'),
    _c('樱桃红色', 'Cherry Red', '#F64752'),
    _c('巧克力色', 'Chocolate', '#664237'),
    _c('咖啡色', 'Coffee', '#7A6243'),
    _c('青色', 'Cyan', '#29C4E1'),
    _c('紫红色', 'Fuchsia', '#E730B6'),
    _c('黄金色', 'Gold', '#D59435'),
    _c('草绿色', 'Grass Green', '#297862'),
    _c('灰色', 'Gray', '#727372'),
    _c('绿色', 'Green', '#15D834'),
    _c('柠檬黄色', 'Lemon Yellow', '#E9E661'),
    _c('浅金色', 'Light Gold', '#F5C520'),
    _c('薄荷绿色', 'Mint Green', '#33C7B7'),
    _c('橄榄绿色', 'Olive Green', '#698259'),
    _c('橙色', 'Orange', '#F58738'),
    _c('粉色', 'Pink', '#FFA1B6'),
    _c('荧光黄色', 'Pri-Yellow', '#F2B548'),
    _c('紫色', 'Purple', '#8454E4'),
    _c('红色', 'Red', '#C53334'),
    _c('樱花粉色', 'Sakura Pink', '#FBC9D2'),
    _c('银色', 'Silver', '#A9AAB2'),
    _c('天空蓝色', 'Sky Blue', '#36C2EB'),
    _c('阳光橙色', 'Sunny Orange', '#F78056'),
    _c('白色', 'White', '#F7F7F7'),
    _c('仿木色', 'Wood-Like', '#D9B289'),
    _c('黄色', 'Yellow', '#E8C200'),


]

JAYO_丝绸_PLA: list[dict] = [
    _c('黑色', 'Black', '#6C6C6C'),
    _c('蓝色', 'Blue', '#14A2D5'),
    _c('黄铜色', 'Brass', '#C58807'),
    _c('青铜色', 'Bronze', '#537857'),
    _c('糖果红', 'Candy Dandy', '#D84962'),
    _c('灰色', 'Gray', '#6A7275'),
    _c('绿色', 'Green', '#08B6A4'),
    _c('浅金色', 'Light Gold', '#E5B344'),
    _c('橙色', 'Orange', '#F58643'),
    _c('粉色', 'Pink', '#F8C6D9'),
    _c('紫色', 'Purple', '#A259A8'),
    _c('红色', 'Red', '#D53245'),
    _c('红铜色', 'Red Copper', '#9B5641'),
    _c('银色', 'Silver', '#8797B1'),
    _c('白色', 'White', '#D8D8D8'),
    _c('黄色', 'Yellow', '#F6E125'),


]

# ---- 天瑞（官方商品页 SKU 色名 + 商品图取主色，近似值）----

TINMORRY_ASA_大理石: list[dict] = [
    _c('浅灰色', 'Light Grey', '#C6C6C6'),


]

TINMORRY_PETGECO: list[dict] = [
    _c('半透紫', 'Translucent Purple', '#530247'),
    _c('半透黄', 'Translucent Yellow', '#F3D900'),
    _c('半透橙', 'Translucent Orange', '#D54307'),
    _c('半透粉', 'Translucent Pink', '#F4D0D3'),
    _c('半透祖母绿', 'Translucent Emerald Green', '#D0D1CB'),
    _c('深灰色', 'Dark Grey', '#353535'),
    _c('卡其色', 'Khaki', '#DBB381'),
    _c('薰衣草紫色', 'Lavender', '#A7A3E4'),
    _c('半透橄榄绿', 'Translucent Olive Green', '#BDCBBA'),
    _c('婴儿蓝', 'Baby Blue', '#87B4D6'),
    _c('骨白色', 'Bone White', '#B7B286'),
    _c('灰色', 'Grey', '#737874'),
    _c('摩卡慕斯棕', 'Mocha Mousse Chocolate Brown', '#866347'),
    _c('地平线绿色', 'Horizon Green', '#01A6B3'),
    _c('冰蓝色', 'Ice Blue', '#B5D8D2'),
    _c('浅灰色', 'Light Grey', '#444444'),
    _c('咖啡色', 'Coffee', '#866849'),
    _c('樱花粉色', 'Sakura Pink', '#EBB4D3'),
    _c('荧光紫红', 'Fluorescent Fuchsia', '#FB31BA'),
    _c('荧光黄色', 'Fluorescent Yellow', '#E2E604'),
    _c('米宝白', 'Meeple White', '#C7C4B4'),
    _c('荧光绿色', 'Fluorescent Green', '#63D603'),
    _c('亮黄色', 'Bright Yellow', '#D7B104'),
    _c('黑色', 'Black', '#2E2C37'),
    _c('天空蓝色', 'Sky Blue', '#0A84C1'),
    _c('透明色', 'Transparent', '#E4E4E4'),
    _c('绿色', 'Green', '#01981D'),
    _c('橄榄绿色', 'Olive Green', '#555827'),
    _c('卡特黄色', 'Carter Yellow', '#D4A601'),
    _c('克莱因蓝', 'Klein Blue', '#2A49B3'),
    _c('杏色', 'Apricot', '#B49B80'),
    _c('象牙白', 'Ivory White', '#DAD8D5'),
    _c('冷白色', 'Cold White', '#CCD3D7'),
    _c('橙色', 'Orange', '#F53409'),
    _c('红色', 'Red', '#850017'),
    _c('长春花蓝', 'Vinca Blue', '#5744A2'),
    _c('薄荷绿色', 'Mint Green', '#01BBB2'),
    _c('粉色', 'Pink', '#F683A0'),
    _c('透明红色', 'Transparent Red', '#960616'),
    _c('透明绿色', 'Transparent Green', '#019800'),
    _c('透明蓝色', 'Transparent Blue', '#025088'),
    _c('肤色', 'Skin', '#D4BAA8'),
    _c('荧光玫红色', 'Fluorescent Rose Red', '#F1377B'),


]

TINMORRY_PLA_大理石: list[dict] = [
    _c('花岗灰色', 'Granite', '#D5D5D4'),
    _c('白色', 'White', '#CACCC9'),
    _c('浅棕', 'Light Brown', '#CBC6C2'),


]

TINMORRY_PLA_CLASSIC: list[dict] = [
    _c('黑色', 'Black', '#242226'),


]

TINMORRY_PETG_GF: list[dict] = [
    _c('卡特黄色', 'Carter Yellow', '#F2B601'),
    _c('绿松石蓝', 'Turquoise blue', '#018A8A'),
    _c('杏色', 'Apricot', '#C6A383'),
    _c('信号绿', 'Signal Green', '#339B53'),
    _c('交通红', 'Traffic Red', '#E43226'),
    _c('浅灰色', 'Light Grey', '#272727'),
    _c('磨砂杏', 'Frosted  Apricot', '#B39573'),
    _c('磨砂深蓝', 'Frosted Dark Blue', '#5864A4'),
    _c('磨砂松绿', 'Frosted Pine-Green', '#01472A'),
    _c('磨砂水蓝', 'Frosted Water Blue', '#35979C'),
    _c('磨砂棕', 'Frosted Brown', '#A47956'),
    _c('磨砂红宝石红', 'Frosted Ruby Red', '#A61224'),
    _c('磨砂暖浅灰', 'Frosted Warm Light Grey', '#D3D4D4'),
    _c('磨砂白', 'Frosted White', '#E3E0D7'),
    _c('磨砂黑', 'Frosted Black', '#949494'),
    _c('磨砂薄荷绿', 'Frosted Mint green', '#A4E7D1'),
    _c('磨砂藏青蓝', 'Frosted Navy Blue', '#626D83'),
    _c('磨砂深绿', 'Frosted Dark Green', '#838A55'),
    _c('磨砂樱花粉', 'Frosted Sakura Pink', '#EAB4C4'),
    _c('磨砂丁香紫', 'Frosted Lilac purple', '#B3B5E7'),
    _c('磨砂冰蓝', 'Frosted Ice Blue', '#95D6DA'),
    _c('黑色', 'Black', '#282828'),
    _c('磨砂米', 'Frosted Beige', '#C7B284'),
    _c('磨砂卡特黄', 'Frosted Carter Yellow', '#F8C707'),
    _c('磨砂橙', 'Frosted Orange', '#F78431'),
    _c('磨砂绿', 'Frosted Green', '#27B148'),
    _c('磨砂红', 'Frosted Red', '#B62422'),
    _c('磨砂蓝', 'Frosted Blue', '#0B4693'),
    _c('磨砂灰', 'Frosted Grey', '#A2A6A9'),


]

TINMORRY_PETG_哑光: list[dict] = [
    _c('哑光象牙白', 'Matte Ivory White', '#D8D9D4'),
    _c('哑光樱花粉', 'Matte Sakura Pink', '#E9C2D4'),
    _c('哑光白', 'Matte White', '#D5D4D9'),
    _c('哑光雾霾蓝', 'Matte Smog Blue', '#7789A1'),
    _c('哑光暖浅灰', 'Matte Warm Light Grey', '#A59482'),
    _c('哑光猩红红', 'Matte Scarlet Red', '#763230'),
    _c('哑光棕', 'Matte Brown', '#744639'),
    _c('哑光祖母绿', 'Matte Emerald Green', '#366237'),
    _c('哑光浅蓝', 'Matte Light Blue', '#82B4D3'),
    _c('哑光薄荷绿', 'Matte Mint Green', '#85C7C6'),
    _c('哑光黄', 'Matte Yellow', '#E3D30B'),
    _c('哑光黑', 'Matte Black', '#282828'),


]

TINMORRY_PLA: list[dict] = [
    _c('红棕棕', 'Reddish Brown', '#351610'),
    _c('杏色', 'Apricot', '#CABDB7'),
    _c('透明色', 'Transparent', '#C9C2A4'),
    _c('品红', 'Magenta', '#E93096'),
    _c('浅蓝', 'Light Blue', '#8498CB'),
    _c('浅灰色', 'Light Grey', '#353430'),
    _c('柠檬绿', 'Lemon Green', '#85B742'),
    _c('冷白色', 'Cold White', '#E6E5EA'),
    _c('灰色', 'Grey', '#545453'),
    _c('天空蓝色', 'Sky Blue', '#0173CE'),
    _c('暖黄', 'Warm Yellow', '#C7A440'),
    _c('卡其色', 'Khaki', '#C99266'),
    _c('粉色', 'Pink', '#E96B81'),
    _c('宝蓝色', 'Royal Blue', '#162497'),
    _c('蓝色', 'Blue', '#7981C1'),
    _c('薰衣草粉', 'Lavender Pink', '#C47CA5'),
    _c('青色', 'Cyan', '#01C2B3'),
    _c('葡萄紫', 'Grape Purple', '#7751A7'),
    _c('苹果绿', 'Apple Green', '#B4E952'),
    _c('黄色', 'Yellow', '#F8EC01'),
    _c('紫色', 'Purple', '#351752'),
    _c('浅木色', 'Light Wood', '#A68855'),
    _c('红色', 'Red', '#E53836'),
    _c('红豆色', 'Red Bean Colour', '#C35C53'),
    _c('浅橙', 'Light Orange', '#D48868'),
    _c('黑色', 'Black', '#363636'),
    _c('橙色', 'Orange', '#FE7220'),
    _c('绿色', 'Green', '#017237'),


]

TINMORRY_碳纤维系列: list[dict] = [
    _c('黑色', 'Black', '#D1A779'),
    _c('深灰色', 'Dark Grey', '#343434'),
    _c('哑光黑', 'Matte Black', '#252422'),
    _c('碳蓝', 'Carbon Blue', '#3B5673'),
    _c('冷灰色', 'Cool Grey', '#363A41'),
    _c('孔雀绿', 'Peacock Green', '#143844'),
    _c('橄榄绿色', 'Olive Green', '#18171A'),
    _c('大理石灰', 'Marble Grey', '#636C74'),


]

TINMORRY_PETG_闪粉: list[dict] = [
    _c('闪点深金', 'Sparkly Dark Gold', '#463415'),
    _c('闪点绿', 'Sparkly Green', '#14373C'),
    _c('闪点品红', 'Sparkly Magenta', '#662246'),
    _c('闪点青', 'Sparkly Cyan', '#03334C'),
    _c('闪点红', 'Sparkly Red', '#743835'),
    _c('闪点黑', 'Sparkly Black', '#33322F'),
    _c('闪点银', 'Sparkly Silver', '#979798'),
    _c('闪点紫', 'Sparkly Purple', '#533258'),


]

TINMORRY_PETG_夜光: list[dict] = [
    _c('夜光浅橙色', 'Glow Light Orange', '#F5A684'),
    _c('夜光浅蓝色', 'Glow Light Blue', '#85DAD9'),
    _c('夜光玫瑰红色', 'Glow Rose Red', '#FD7B91'),
    _c('夜光黄绿色', 'Glow Yellow Green', '#B6E877'),
    _c('夜光绿色', 'Glow Green', '#01D318'),


]

TINMORRY_PLA_星河: list[dict] = [
    _c('星河紫', 'Galaxy Purple', '#66638B'),
    _c('星河绿', 'Galaxy Green', '#777A72'),
    _c('星河蓝', 'Galaxy Blue', '#747D90'),
    _c('星河棕', 'Galaxy Brown', '#966D5F'),


]

TINMORRY_TPU_95A: list[dict] = [
    _c('浅灰色', 'Light Grey', '#C7C6C2'),
    _c('金属太空灰', 'Metal Space Grey', '#686868'),
    _c('透明灰', 'Transparent grey', '#B4B4B4'),
    _c('金属银', 'Metallic Silver', '#E3A87E'),
    _c('交通黄', 'Traffic Yellow', '#F5B900'),
    _c('肤色', 'Skin', '#B7A487'),
    _c('电信灰', 'Telecom Grey', '#252525'),
    _c('淡粉色', 'Pale Pink', '#FCC3DA'),
    _c('紫罗兰', 'Violet', '#632C66'),
    _c('荧光蓝', 'Neon Blue', '#D5A878'),
    _c('荧光蓝', 'Fluorescent Blue', '#B9906D'),
    _c('荧光紫', 'Fluorescent Purple', '#8550B8'),
    _c('荧光红', 'Fluorescent Red', '#F10129'),
    _c('荧光玫红色', 'Fluorescent Rose Red', '#F22B89'),
    _c('消防橙', 'Fire Safety Orange', '#FF7000'),
    _c('荧光绿色', 'Fluorescent Green', '#57C610'),
    _c('祖母绿', 'Emerald Green', '#01A534'),
    _c('荧光黄色', 'Fluorescent Yellow', '#E7C202'),
    _c('红色', 'Red', '#F53B26'),
    _c('白色', 'White', '#CAC6C3'),
    _c('透明红色', 'Transparent Red', '#850911'),
    _c('透明紫罗兰', 'Transparent Violet', '#141358'),
    _c('透明祖母绿', 'Transparent Emerald Green', '#5A5A58'),
    _c('透明黄', 'Transparent Yellow', '#D3DA01'),
    _c('透明色', 'Transparent', '#E2E3DB'),
    _c('透明绿（1KG 装）', '1 KG， Transparent Green', '#85D700'),
    _c('黑色', 'Black', '#373532'),
    _c('透明蓝色', 'Transparent Blue', '#024290'),


]

TINMORRY_PETG_金属: list[dict] = [
    _c('金属深红', 'Metallic DarkRed', '#822625'),
    _c('金属青铜', 'Metallic Bronze', '#858580'),
    _c('金属午夜绿', 'Metallic Midnight Green', '#4A7A6E'),
    _c('金属绿', 'Metallic Green', '#848B57'),
    _c('金属蓝', 'Metallic Blue', '#61778C'),
    _c('金属玫瑰金', 'Metallic Rose Gold', '#8F8F8F'),
    _c('金属紫', 'Metallic Purple', '#855371'),
    _c('金属香槟金', 'Metallic Champagne Gold', '#907656'),
    _c('金属太空灰', 'Metallic Space Grey', '#7B7B7B'),
    _c('金属银', 'Metallic Silver', '#8A8B8F'),


]

TINMORRY_ABSPRO: list[dict] = [
    _c('紫色', 'Purple', '#7862CA'),
    _c('黑色', 'Black', '#3B3939'),
    _c('冷白色', 'Cold White', '#C6C9D2'),
    _c('暖灰色', 'Warm Grey', '#C2B698'),
    _c('冷灰色', 'Cold Grey', '#737679'),
    _c('青色', 'Cyan', '#75CAB7'),
    _c('橙色', 'Orange', '#FF6403'),
    _c('红色', 'Red', '#84000E'),
    _c('绿色', 'Green', '#00A33D'),
    _c('湖蓝色', 'Lake Blue', '#0097D3'),
    _c('黄色', 'Yellow', '#E3C600'),


]

TINMORRY_PLA_哑光: list[dict] = [
    _c('哑光藏青蓝', 'Matte Navy Blue', '#363636'),
    _c('哑光橄榄绿', 'Matte Olive Green', '#3B393A'),
    _c('哑光南瓜黄', 'Matte Pumpkin Yellow', '#F3A501'),
    _c('哑光柚橙', 'Matte Pomelo Orange', '#FE9870'),
    _c('哑光菠菜绿', 'Matte Spinach Green', '#018668'),
    _c('哑光浅棕', 'Matte Light Brown', '#CBA581'),
    _c('黑色', 'Black', '#34353A'),
    _c('哑光白', 'Matte White', '#E8E6E7'),
    _c('哑光灰', 'Matte Grey', '#454442'),
    _c('哑光棕', 'Matte Brown', '#A66444'),
    _c('哑光黄', 'Matte Yellow', '#F3DA02'),
    _c('哑光橙', 'Matte Orange', '#F68601'),
    _c('哑光浅蓝', 'Matte Light Blue', '#A6D3E6'),
    _c('哑光粉', 'Matte Pink', '#FEA8C5'),
    _c('哑光浅绿', 'Matte Light Green', '#C9E9A9'),
    _c('哑光红', 'Matte Red', '#771923'),
    _c('哑光紫', 'Matte Purple', '#A19CD7'),
    _c('哑光肤色', 'Matte Skin', '#D7C6B4'),


]

TINMORRY_丝绸_PLA: list[dict] = [
    _c('丝绸蓝', 'Silk Blue', '#434345'),
    _c('丝绸玫瑰红', 'Silk Rose Red', '#D34687'),
    _c('丝绸紫', 'Silk Purple', '#7B58B6'),
    _c('丝绸绿', 'Silk Green', '#08852F'),
    _c('丝绸白', 'Silk White', '#DADAD6'),
    _c('丝绸铁黑', 'Silk Iron Black', '#343435'),
    _c('丝绸红', 'Silk Red', '#B62B49'),
    _c('丝绸铜', 'Silk Copper', '#9F4733'),
    _c('丝绸金', 'Silk Gold', '#D99703'),
    _c('丝绸青铜', 'Silk Bronze', '#74714C'),
    _c('丝绸银', 'Silk Silver', '#A6B3BB'),
    _c('浅金', 'Light Gold', '#726A16'),


]

TINMORRY_PETG_星河: list[dict] = [
    _c('星河紫红', 'Galaxy Fuchsia', '#6F718E'),
    _c('星河紫金', 'Galaxy Purple Gold', '#755E60'),
    _c('星河金绿', 'Galaxy Green Gold', '#27393C'),
    _c('星河宝石蓝', 'Galaxy Jewel Blue', '#45427C'),
    _c('星河宝石绿', 'Galaxy Gemstone Green', '#546775'),
    _c('变色蓝紫', 'Chameleon Blue/Purple', '#455869'),


]

TINMORRY_PETG_大理石: list[dict] = [
    _c('大理石幻彩粉', 'Marble Magic Pink', '#D3C7CB'),
    _c('大理石花岗', 'Marble Granite', '#B2B5BA'),
    _c('大理石幻彩紫', 'Marble Magic Purple', '#D6C8D5'),
    _c('大理石幻彩绿', 'Marble Magic Green', '#BAC5BF'),
    _c('大理石幻彩蓝', 'Marble Magic Blue', '#A5B5C2'),
    _c('大理石幻彩棕', 'Marble Magic Brown', '#D2C6C6'),
    _c('大理石浅灰', 'Marble Light Grey', '#82909A'),
    _c('大理石白（1KG 装）', '1 KG， Marble White', '#C7C8CA'),
    _c('大理石浅棕', 'Marble Light Brown', '#E4D1C0'),


]

TINMORRY_ASA: list[dict] = [
    _c('灰色', 'Grey', '#717A7F'),
    _c('橄榄绿色', 'Olive Green', '#748647'),
    _c('蓝色', 'Blue', '#002878'),
    _c('白色', 'White', '#B7B6BC'),
    _c('橙色', 'Orange', '#FC6420'),
    _c('紫色', 'Purple', '#6432A7'),
    _c('红色', 'Red', '#C72822'),
    _c('黑色', 'Black', '#27282A'),


]

TINMORRY_PLA_金属: list[dict] = [
    _c('金属太空灰', 'Metallic Space Grey', '#2F2C30'),
    _c('金属黄铜', 'Metallic Brass', '#6D5026'),
    _c('金属玫瑰金', 'Metallic Rose Gold', '#845A4E'),
    _c('金属银', 'Metallic Silver', '#8C8C8C'),


]

TINMORRY_PLA_夜光: list[dict] = [
    _c('夜光绿色', 'Glow Green', '#C8A77E'),


]

# ---- iBOSS（官方商品页 SKU 色名 + 商品图取主色，近似值）----

IBOSS_ABS: list[dict] = [
    _c('黑色', 'Black', '#61676B'),
    _c('白色', 'White', '#E2E4E4'),


]

IBOSS_PETG: list[dict] = [
    _c('黑色', 'Black', '#7C7E84'),
    _c('深蓝色', 'Dark Blue', '#C5D3F1'),
    _c('粉色', 'Pink', '#FCC4EE'),
    _c('金色', 'Gold', '#F4A92F'),
    _c('灰白', 'Gray White', '#DCEAF5'),
    _c('卡其绿', 'Khaki Green', '#A9A25A'),
    _c('透明色', 'Transparent', '#E0E4E8'),
    _c('黄色', 'Yellow', '#FBD13D'),


]

IBOSS_PLA: list[dict] = [
    _c('米色', 'Beige', '#F5F1CC'),
    _c('白大理石', 'White Marble', '#E5EAED'),
    _c('薄荷绿', 'Mint Green', '#CCF4FE'),
    _c('透明色', 'Transparent', '#FEB7F8'),
    _c('透明紫罗兰', 'Transparent Violet', '#EEADEC'),
    _c('水粉色', 'Water Pink', '#F0CBE0'),
    _c('马卡龙粉', 'Macaron Pink', '#FDA898'),
    _c('大理石灰', 'Marble Gray', '#CEDDE1'),
    _c('苹果绿', 'Apple Green', '#D6E542'),
    _c('橄榄绿', 'Olive Green', '#637C5F'),
    _c('赭棕色', 'Terra Brown', '#483221'),
    _c('宝蓝色', 'Royal Blue', '#C2B6AE'),
    _c('浅紫', 'Light Purple', '#DAB8EA'),
    _c('黑色', 'Black', '#43464C'),


]

IBOSS_TPU: list[dict] = [
    _c('蓝色', 'Blue', '#4ED2FA'),
    _c('红色', 'Red', '#E63536'),


]

IBOSS_PLA_夜光: list[dict] = [
    _c('夜光白', 'Glow White', '#E1E0DE'),
    _c('夜光蓝绿色', 'Night Glow Blue-Green', '#65DAD5'),
    _c('夜夜光绿', 'Night Glow Green', '#5AEF4B'),


]

IBOSS_PLA_哑光: list[dict] = [
    _c('冰淇淋色', 'Ice Cream', '#E7E1E2'),
    _c('绿色', 'Green', '#F0B3B2'),


]

IBOSS_丝绸_PLA: list[dict] = [
    _c('丝绸绿', 'Silk Green', '#A3A3B0'),
    _c('丝绸紫', 'Silk Purple', '#B793D0'),
    _c('丝绸金', 'Silk Gold', '#EAE5CC'),
    _c('丝绸红', 'Silk Red', '#B4E8F3'),
    _c('丝绸黑', 'Silk Black', '#CBC9CE'),
    _c('宝石绿', 'Gemstone Green', '#EDD787'),
    _c('金色', 'Gold', '#FCD480'),
    _c('丝绸橙', 'Silk Orange', '#FE9342'),
    _c('丝绸蓝', 'Silk Blue', '#64A4FE'),


]

IBOSS_PLA_闪粉: list[dict] = [
    _c('闪点天蓝', 'Flash Point Sky Blue', '#85BBEE'),
    _c('紫色', 'Purple', '#9584C2'),
    _c('蓝色', 'Blue', '#C2B6AE'),


]

IBOSS_PLA_木质: list[dict] = [
    _c('檀木色', 'Sandal Wood', '#917458'),


]

# ---- R3D（官方商品页 SKU 色名 + 商品图取主色，近似值）----

R3D_PETG_GF: list[dict] = [
    _c('透明色', 'Transparent', '#D5D6C9'),
    _c('深灰色', 'Dark Gray', '#535756'),
    _c('黑色', 'Black', '#252525'),
    _c('青色', 'Cyan', '#4286C3'),
    _c('象牙白', 'Ivory', '#D8D9D4'),
    _c('岩石灰', 'Rock Gray', '#595451'),


]

R3D_PETG_TRANSPARENT: list[dict] = [
    _c('透明色', 'Transparent', '#CACAC0'),
    _c('透明浅粉', 'Transparent Light Powder', '#F7C4D3'),
    _c('透明橙', 'Transparent Orange', '#D58240'),
    _c('透明浅蓝', 'Transparent Light Blue', '#77C7D2'),
    _c('透明祖母绿', 'Transparent Emerald Green', '#237860'),


]

R3D_PLA_WOOD: list[dict] = [
    _c('深木色', 'Dark Wood', '#444444'),


]

R3D_PLA_UV变色: list[dict] = [
    _c('蓝白色', 'White-Blue', '#E5E5E0'),


]

R3D_PLA_温变: list[dict] = [
    _c('紫粉渐变', 'Purple to Pink', '#F58193'),


]

R3D_PLA_夜光: list[dict] = [
    _c('萤火夜光蓝', 'Glow Firefly Blue', '#C4C2B6'),


]

R3D_HS_PLA_PRO_MATTE: list[dict] = [
    _c('哑光暖灰', 'Matte Warm Gray', '#928B77'),
    _c('哑光冷灰', 'Matte Cold Gray', '#879392'),
    _c('哑光藏青蓝', 'Matte Navy Blue', '#162268'),
    _c('哑光赤陶', 'Matte Terracotta', '#A26A5E'),


]

R3D_HS_PLA_PRO: list[dict] = [
    _c('黑色', 'Black', '#222423'),
    _c('白色', 'White', '#E8E9E4'),


]

R3D_PLA_MARBLE: list[dict] = [
    _c('大理石色', 'Marble', '#A8B2B4'),
    _c('砖红色', 'Brick Red', '#953C22'),


]

R3D_PLA_MATTE: list[dict] = [
    _c('哑光黑', 'Matte Black', '#262626'),
    _c('哑光白', 'Matte White', '#D2D3CB'),
    _c('哑光灰', 'Matte Grey', '#979892'),
    _c('哑光碳黑', 'Matte Carbon Black', '#2A2720'),
    _c('哑光瓷', 'Matte Porcelain', '#D3D3C8'),
    _c('哑光芭比粉', 'Matte Barbie Pink', '#B367A2'),
    _c('哑光钴蓝', 'Matte Cobalt Blue', '#2368BA'),
    _c('哑光极光肤', 'Matte Aurora Skin', '#E2C4AA'),
    _c('哑光肤色', 'Matte Skin', '#E5A37E'),
    _c('哑光品红', 'Matte Magenta', '#C31214'),
    _c('哑光酒红', 'Matte Wine', '#64222B'),
    _c('哑光蓝宝石蓝', 'Matte Sapphire Blue', '#1558BA'),
    _c('哑光浅天蓝', 'Matte Light Sky Blue', '#B4C4DD'),
    _c('哑光深绿', 'Matte Dark Green', '#42483A'),
    _c('哑光象牙白', 'Matte Lvory', '#D8D7D3'),
    _c('哑光冰川蓝', 'Matte Glacier Blue', '#C6E5E7'),
    _c('哑光棕', 'Matte Brown', '#643618'),
    _c('哑光鱼肚白', 'Matte Fishbelly White', '#B3B8B2'),
    _c('哑光黄', 'Matte Yellow', '#E7D402'),
    _c('哑光绿松石蓝', 'Matte Turquoise Blue', '#67EBE6'),
    _c('哑光白橡木', 'Matte White Oak', '#E1DDC2'),
    _c('哑光橙', 'Matte Orange', '#FEFEFE'),
    _c('哑光杏花粉', 'Matte Apricot Pollen', '#F799B2'),
    _c('哑光军绿', 'Matte Army Green', '#738657'),
    _c('哑光中国红', 'Matte Chinese Red', '#E56956'),
    _c('哑光燕麦', 'Matte Oats', '#D4B890'),
    _c('哑光紫', 'Matte Purple', '#946BD6'),


]

R3D_ASA: list[dict] = [
    _c('白色', 'White', '#E2E2E2'),
    _c('黑色', 'Black', '#313131'),
    _c('灰黑色', 'Ash Gray', '#343233'),
    _c('灰色', 'Gray', '#646464'),
    _c('军绿色', 'Army Green', '#788142'),
    _c('拿铁色', 'Latte', '#BEA36C'),
    _c('深蓝色', 'Dark Blue', '#3363C7'),
    _c('荧光蓝', 'Fluorescent Blue', '#2B4DC8'),
    _c('浅蓝', 'Light Blue', '#50A5F8'),
    _c('紫色', 'Purple', '#B492EC'),
    _c('红色', 'Red', '#FE4432'),
    _c('荧光红', 'Fluorescent Red', '#F8505A'),
    _c('橙色', 'Orange', '#FE9331'),
    _c('荧光橙', 'Fluorescent Orange', '#FE6A30'),
    _c('荧光黄', 'Fluorescent Yellow', '#FEC458'),
    _c('黄色', 'Yellow', '#FEE132'),
    _c('薄荷绿', 'Mint Green', '#4CD8B9'),
    _c('荧光绿', 'Fluorescent Green', '#64EA65'),


]

R3D_HS_PETG: list[dict] = [
    _c('黑色', 'Black', '#232428'),
    _c('白色', 'White', '#E9E7E3'),


]

R3D_PETG_MATTE: list[dict] = [
    _c('哑光白', 'Matte White', '#D2D4D3'),
    _c('哑光枪灰灰', 'Matte Gunmetal Gray', '#636466'),
    _c('哑光卡其', 'Matte Khaki', '#A48860'),
    _c('哑光黄', 'Matte Yellow', '#E5DD32'),
    _c('哑光深藏青蓝', 'Matte Dark Navy Blue', '#011848'),
    _c('哑光冰川蓝', 'Matte Glacier Blue', '#A8DDE5'),


]

R3D_PETG: list[dict] = [
    _c('黑色', 'Black', '#232227'),
    _c('白色', 'White', '#E4DCC3'),
    _c('暖灰色', 'Warm Gray', '#928775'),
    _c('米白色', 'Off White', '#C8C8C6'),
    _c('橘橙色', 'Tangerine', '#F97C01'),
    _c('咖啡色', 'Coffee', '#523829'),
    _c('拓竹绿', 'Bambu Green', '#46D35A'),
    _c('黄色', 'Yellow', '#F8B401'),
    _c('紫色', 'Purple', '#6742A6'),
    _c('仿木色', 'Faux Wood', '#E5B59A'),
    _c('浅蓝', 'Light Blue', '#1593C9'),
    _c('奶粉色', 'Cream Pink', '#C9B2BA'),
    _c('落雪夜光', 'Snowy Glow', '#D4B6A1'),
    _c('拿铁色', 'Latte', '#836548'),
    _c('粉色', 'Pink', '#D799A6'),
    _c('铅灰色', 'Lead Ash', '#949494'),
    _c('白橡木', 'White Oak', '#E4DCC3'),
    _c('墨绿色', 'Blackish Green', '#47522A'),
    _c('深蓝色', 'Dark Blue', '#1925A2'),
    _c('克莱因蓝', 'Klein Blue', '#161963'),


]

R3D_PETG_MARBLE: list[dict] = [
    _c('大理石花岗', 'Marble Granite', '#A5B5B4'),
    _c('水泥灰', 'Cement Ash', '#949496'),
    _c('砖红色', 'Brick Red', '#93261D'),
    _c('大理石色', 'Marble', '#A7B2B7'),


]

R3D_HS_PLA_PRO_SILK: list[dict] = [
    _c('丝绸白', 'Silk White', '#C9C9C9'),
    _c('丝绸黑', 'Silk Black', '#343338'),
    _c('丝绸铜', 'Silk Copper', '#A85430'),
    _c('丝绸橙', 'Silk Orange', '#D55301'),
    _c('丝绸青铜', 'Silk Bronze', '#485126'),
    _c('丝绸草绿', 'Silk Grass Green', '#D9DAD5'),
    _c('丝绸粉紫', 'Silk Pink Purple', '#C29DC8'),
    _c('丝绸浅粉', 'Silk Light Pink', '#DADBD5'),


]

R3D_PLA_TRANSLUCENT: list[dict] = [
    _c('透明色', 'Transparent', '#545655'),
    _c('半透红', 'Translucent Red', '#E74B24'),
    _c('半透蓝', 'Translucent Blue', '#4487D6'),


]

R3D_PLA_PRO: list[dict] = [
    _c('玉石白', 'Jade White', '#D4D5C5'),
    _c('浅杏', 'Light Apricot', '#E3D6C6'),
    _c('灰色', 'Gray', '#C2C6C7'),
    _c('浅灰', 'Light Gray', '#D2D8D8'),
    _c('红色', 'Red', '#950303'),
    _c('黄色', 'Yellow', '#F3E125'),
    _c('绿松石绿', 'Turquoise Green', '#38CAB7'),
    _c('钴蓝色', 'Cobalt Blue', '#1651B1'),
    _c('深蓝色', 'Dark Blue', '#1442A7'),
    _c('紫色', 'Purple', '#9773D6'),
    _c('品红', 'Magenta', '#A62156'),
    _c('可可棕', 'Cocoa Brown', '#56422A'),
    _c('棕色', 'Brown', '#764325'),


]

R3D_PLA_SILK: list[dict] = [
    _c('丝绸金', 'Silk Gold', '#B67206'),
    _c('丝绸金黄', 'Silk Auratus', '#D6A236'),
    _c('丝绸香槟', 'Silk Champagne', '#C8A772'),
    _c('丝绸红', 'Silk Red', '#530105'),
    _c('丝绸樱花粉', 'Silk Sakura Pink', '#C7A4C2'),
    _c('丝绸黑', 'Silk Black', '#181818'),
    _c('丝绸白银', 'Silk White Silver', '#96A0AA'),
    _c('丝绸白', 'Silk White', '#C9C9C9'),


]

# ---- 爱丽兹 Allizz（官网 Color Options 色卡，商品图提色，近似值）----

ALLIZZ_ABS: list[dict] = [
    _c('冷白色', 'Cold White', '#E2E2E2'),
    _c('紫色', 'Purple', '#4C2D7E'),
    _c('浅蓝色', 'Light blue', '#AFE5D5'),
    _c('米色', 'Beige', '#E4DBA8'),
    _c('紫红', 'fuchsia', '#AE359A'),
    _c('银色', 'silver', '#858585'),
    _c('天蓝色', 'Sky blue', '#6EAFE2'),
    _c('藏红花黄', 'saffron yellow', '#F1C958'),
    _c('草绿色', 'grass green', '#6F9551'),
    _c('浅橙', 'oranger', '#E99C69'),
    _c('藏青色', 'Navy Blue', '#2E3255'),
    _c('红色', 'red', '#E54B46'),
    _c('黄色', 'yellow', '#F3D603'),
    _c('绿色', 'green', '#38C64B'),
    _c('蓝色', 'blue', '#4969CB'),
    _c('白色', 'ABS white', '#EBEBEB'),
    _c('黑色', 'ABS black', '#303030'),


]

ALLIZZ_ASA: list[dict] = [
    _c('黑色', 'Black', '#151719'),
    _c('蓝色', 'Blue', '#4160D7'),
    _c('灰色', 'Gray', '#636566'),
    _c('绿色', 'Green', '#019283'),
    _c('红色', 'Red', '#E02F30'),
    _c('白色', 'White', '#D9D8D9'),


]

ALLIZZ_PETG_HF: list[dict] = [
    _c('绿色', 'Green', '#126032'),
    _c('品红色', 'Magenta', '#B23167'),
    _c('紫罗兰', 'Violet', '#5A3C79'),
    _c('樱花粉色', 'Cherry Blossom Pink', '#B99894'),
    _c('肤色', 'Skin Color', '#B6A997'),
    _c('柠檬绿', 'Lemon Green', '#57AE4B'),
    _c('橙色', 'Orange', '#CA4F08'),
    _c('浅灰', 'Light Gray', '#818074'),
    _c('白色', 'White', '#E2E2E2'),
    _c('黄色', 'Yellow', '#D5BA30'),
    _c('青色', 'Cyan', '#046EA5'),
    _c('湖蓝色', 'Lake Blue', '#255F99'),
    _c('亮红色', 'Bright Red', '#C10807'),
    _c('朱砂红色', 'Cinnabar Red', '#960F12'),
    _c('米色', 'Beige', '#BEAA7F'),
    _c('黑镍色', 'Black Nickel', '#393939'),
    _c('铜色', 'Copper', '#7D614B'),
    _c('橄榄绿', 'Olive Green', '#606829'),
    _c('克莱因蓝', 'Klein Blue', '#072E6A'),
    _c('酒红色', 'Red Wine', '#5F261E'),
    _c('咖啡色', 'Coffee Color', '#5E3020'),
    _c('深灰色', 'Dark Gray', '#4F4F4F'),
    _c('琥珀金色', 'Amber Gold', '#A99421'),
    _c('红铜色', 'Red Copper', '#8F583F'),
    _c('大理石色', 'Marble PETG', '#CCCCCC'),


]

ALLIZZ_PETG_TRANSLUCENT: list[dict] = [
    _c('透明色', 'Clear', '#E1E6EB'),
    _c('半透黑色', 'Translucent Black', '#3D3A38'),
    _c('半透红色', 'Translucent Red', '#EB8A83'),
    _c('半透橙色', 'Translucent Orange', '#E4A954'),
    _c('半透黄色', 'Translucent Yellow', '#E2E370'),
    _c('半透绿色', 'Translucent Green', '#61EF6B'),
    _c('半透青色', 'Translucent Cyan', '#43D0E8'),
    _c('半透蓝色', 'Translucent Blue', '#42A1E7'),
    _c('半透紫色', 'Translucent Purple', '#A964EB'),


]

ALLIZZ_PLA_MATTE: list[dict] = [
    _c('白色', 'White', '#E2E2E2'),
    _c('冰蓝色', 'Ice Blue', '#86C6D9'),
    _c('橙色', 'orange', '#D1814A'),
    _c('炭黑色', 'charcoal', '#070707'),
    _c('沙漠黄色', 'Desert Yellow', '#B59E6A'),
    _c('绯红色', 'Crimson', '#931B26'),
    _c('深蓝色', 'Deep Blue', '#14264C'),
    _c('深绿色', 'Dark green', '#575C38'),
    _c('棕色', 'brown', '#826252'),
    _c('紫色', 'Purple', '#5A3C79'),
    _c('深棕色', 'Dark Brown', '#674235'),


]

ALLIZZ_PLA_SILK: list[dict] = [
    _c('丝绸亮银', 'Silk Shiny Silver', '#8E8C8D'),
    _c('丝绸银', 'Silk Silver', '#807F85'),
    _c('丝绸亮金', 'Silk Shiny Gold', '#E99601'),
    _c('丝绸白', 'Silk white', '#D3D3D3'),
    _c('丝绸奢华金', 'Silk Luxury Gold', '#FEA910'),
    _c('丝绸黄', 'Silk Yellow', '#E3B403'),
    _c('丝绸橙', 'Silk Orange', '#DA5D0D'),
    _c('丝绸粉', 'Silk Pink', '#DE6C6D'),
    _c('丝绸红', 'Silk Red', '#E41D0E'),
    _c('丝绸紫', 'Silk Purple', '#9035A6'),
    _c('丝绸蓝紫', 'Silk Blueviolet', '#522C74'),
    _c('丝绸蓝', 'Silk Blue', '#1D3062'),
    _c('丝绸幻彩绿', 'Silk Magic Green', '#387E29'),
    _c('丝绸奶绿', 'Silk Milk Green', '#69BC5E'),
    _c('丝绸黑', 'Silk Black', '#030303'),


]

ALLIZZ_TPU95A: list[dict] = [
    _c('红色', 'red', '#D04E44'),
    _c('灰色', 'grey', '#999999'),
    _c('蓝色', 'blue', '#4499D0'),
    _c('黄色', 'yellow', '#E5E12D'),
    _c('白色', 'white', '#E8E8E8'),
    _c('黑色', 'black', '#494949'),


]

BRAND_COLOR_SERIES_EXTRA: dict[str, dict[str, list[dict]]] = {
    "Kexcelled": {
        "K5 PLA": KEXCELLED_K5_PLA,
        "K5 PLA 哑光": KEXCELLED_K5_PLA_MATTE,
        "K5 PETG": KEXCELLED_K5_PETG,
        "K5 PETG 哑光": KEXCELLED_K5_PETG_MATTE,
        "K5 PETG Rapid": KEXCELLED_K5_PETG_RAPID,
    },
    "拓竹": {
        "PLA Basic": BAMBU_PLA_BASIC,
        "PLA Matte": BAMBU_PLA_MATTE,
        "PETG Basic": BAMBU_PETG_BASIC,
        "PETG HF": BAMBU_PETG_HF,
    },
    "大简": {
        "PETG HF": DASU_PETG_HF,
    },
    "兰博": LANBO_SERIES,
    "魔创": {
        "PLA": MOCRE_PLA,
        "PLA 哑光": MOCRE_PLA_MATTE,
        "PLA+": MOCRE_PLA_PLUS,
        "HT-PLA": MOCRE_HT_PLA,
        "PETG": MOCRE_PETG,
        "PETG 哑光": MOCRE_PETG_MATTE,
        "ASA": MOCRE_ASA,
        "ABS": MOCRE_ABS,
    },
    "锐造": {
        "PLA": RUIZAO_PLA,
        "PETG": RUIZAO_PETG,
        "PLA 大理石": RUIZAO_PLA_大理石,
        "PLA 哑光": RUIZAO_PLA_哑光,
        "PLA Basic": RUIZAO_PLA_BASIC,
        "PLA 丝绸": RUIZAO_PLA_丝绸,
        "ABS": RUIZAO_ABS,
        "PETG 哑光": RUIZAO_PETG_哑光,
        "PETG-CF": RUIZAO_PETGCF,
        "PETG 夜光": RUIZAO_PETG_夜光,
        "PLA 夜光": RUIZAO_PLA_夜光,
        "PLA 木质": RUIZAO_PLA_木质,
    },
    "JAYO": {
        "HS PETG 哑光": JAYO_HS_PETG_哑光,
        "HS PLA": JAYO_HS_PLA,
        "HS PLA 哑光": JAYO_HS_PLA_哑光,
        "HS PLA 大理石": JAYO_HS_PLA_大理石,
        "PETG": JAYO_PETG,
        "PLA": JAYO_PLA,
        "PLA Classic": JAYO_PLA_CLASSIC,
        "PLA Meta": JAYO_PLA_META,
        "PLA 哑光": JAYO_PLA_哑光,
        "PLA 闪点": JAYO_PLA_闪点,
        "PLA+ 2.0": JAYO_PLA_20,
        "丝绸 PLA+": JAYO_丝绸_PLA,
    },
    "天瑞": {
        "ASA 大理石": TINMORRY_ASA_大理石,
        "PETG-Eco": TINMORRY_PETGECO,
        "PLA 大理石": TINMORRY_PLA_大理石,
        "PLA Classic": TINMORRY_PLA_CLASSIC,
        "PETG GF": TINMORRY_PETG_GF,
        "PETG 哑光": TINMORRY_PETG_哑光,
        "PLA": TINMORRY_PLA,
        "碳纤维系列": TINMORRY_碳纤维系列,
        "PETG 闪粉": TINMORRY_PETG_闪粉,
        "PETG 夜光": TINMORRY_PETG_夜光,
        "PLA 星河": TINMORRY_PLA_星河,
        "TPU 95A": TINMORRY_TPU_95A,
        "PETG 金属": TINMORRY_PETG_金属,
        "ABS-Pro": TINMORRY_ABSPRO,
        "PLA 哑光": TINMORRY_PLA_哑光,
        "丝绸 PLA": TINMORRY_丝绸_PLA,
        "PETG 星河": TINMORRY_PETG_星河,
        "PETG 大理石": TINMORRY_PETG_大理石,
        "ASA": TINMORRY_ASA,
        "PLA 金属": TINMORRY_PLA_金属,
        "PLA 夜光": TINMORRY_PLA_夜光,
    },
    "iBOSS": {
        "ABS": IBOSS_ABS,
        "PETG": IBOSS_PETG,
        "PLA+": IBOSS_PLA,
        "TPU": IBOSS_TPU,
        "PLA 夜光": IBOSS_PLA_夜光,
        "PLA 哑光": IBOSS_PLA_哑光,
        "丝绸 PLA": IBOSS_丝绸_PLA,
        "PLA 闪粉": IBOSS_PLA_闪粉,
        "PLA 木质": IBOSS_PLA_木质,
    },
    "R3D": {
        "PETG GF": R3D_PETG_GF,
        "PETG Transparent": R3D_PETG_TRANSPARENT,
        "PLA Wood": R3D_PLA_WOOD,
        "PLA UV变色": R3D_PLA_UV变色,
        "PLA 温变": R3D_PLA_温变,
        "PLA 夜光": R3D_PLA_夜光,
        "HS PLA Pro Matte": R3D_HS_PLA_PRO_MATTE,
        "HS PLA Pro": R3D_HS_PLA_PRO,
        "PLA Marble": R3D_PLA_MARBLE,
        "PLA Matte": R3D_PLA_MATTE,
        "ASA": R3D_ASA,
        "HS PETG": R3D_HS_PETG,
        "PETG Matte": R3D_PETG_MATTE,
        "PETG": R3D_PETG,
        "PETG Marble": R3D_PETG_MARBLE,
        "HS PLA Pro Silk": R3D_HS_PLA_PRO_SILK,
        "PLA Translucent": R3D_PLA_TRANSLUCENT,
        "PLA Pro": R3D_PLA_PRO,
        "PLA Silk": R3D_PLA_SILK,
    },
    "爱丽兹 Allizz": {
        "ABS": ALLIZZ_ABS,
        "ASA": ALLIZZ_ASA,
        "PETG HF": ALLIZZ_PETG_HF,
        "PETG Translucent": ALLIZZ_PETG_TRANSLUCENT,
        "PLA Matte": ALLIZZ_PLA_MATTE,
        "PLA Silk": ALLIZZ_PLA_SILK,
        "TPU95A": ALLIZZ_TPU95A,
    },
}

MATERIAL_COLOR_SERIES_EXTRA: dict[str, list[str]] = {
    "PLA": [
        "K5 PLA", "K5 PLA 哑光",
        "PLA Basic", "PLA Matte",
        "PLA", "PLA+", "PLA 哑光", "PLA 丝绸", "金属色", "星空闪点", "夜光",
        "丝绸双色", "丝绸三色", "丝绸彩虹", "哑光双色", "哑光三色", "哑光彩虹",
        "HT-PLA", "PLA 大理石", "PLA 夜光", "PLA 木质", "HS PLA", "HS PLA 哑光", "HS PLA 大理石", "PLA Classic", "PLA Meta", "PLA 闪点", "PLA+ 2.0", "丝绸 PLA+", "PLA 星河", "丝绸 PLA", "PLA 金属", "PLA 闪粉", "PLA Wood", "PLA UV变色", "PLA 温变", "HS PLA Pro Matte", "HS PLA Pro", "PLA Marble", "HS PLA Pro Silk", "PLA Translucent", "PLA Pro", "PLA Silk"
    ],
    "PETG": ["PETG", "PETG 哑光", "K5 PETG", "K5 PETG 哑光", "K5 PETG Rapid",
             "PETG Basic", "PETG HF", "PETG-CF", "PETG 夜光", "HS PETG 哑光", "PETG-Eco", "PETG GF", "PETG 闪粉", "PETG 金属", "PETG 星河", "PETG 大理石", "PETG Transparent", "HS PETG", "PETG Matte", "PETG Marble", "PETG Translucent"],
    "ASA": ["ASA", "ASA 大理石"],
    "ABS": ["ABS", "ABS-Pro"],
    "TPU": ["TPU 95A", "TPU", "TPU95A"],
}
