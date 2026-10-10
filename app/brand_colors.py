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
    _c('丝绸青铜', 'Silk Bronze', '#B87333'),
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

# ---- 爱丽兹 Allizz（淘宝/天猫旗舰店色卡，商品图提色，近似值；部分沿用既有 hex）----


# ASA (沿用既有)

ALLIZZ_ASA: list[dict] = [
    _c('黑色', 'Black', '#151719'),
    _c('蓝色', 'Blue', '#4160D7'),
    _c('灰色', 'Gray', '#636566'),
    _c('绿色', 'Green', '#019283'),
    _c('红色', 'Red', '#E02F30'),
    _c('白色', 'White', '#D9D8D9'),


]


# PETG Translucent (沿用既有)

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


# ABS  (6 色)

ALLIZZ_ABS: list[dict] = [
    _c('柔肤色', 'ABB3100', '#E4C9B0'),
    _c('白色', 'ABB8000', '#E5E5E5'),
    _c('黑色', 'ABB8900', '#1C1C1C'),
    _c('冷白', 'ABB8001', '#ECECEC'),
    _c('灰色', 'ABB8400', '#888888'),
    _c('消防红', 'ABB1600', '#C21E1E'),

]

# PETG HF  (30 色)

ALLIZZ_PETG_HF: list[dict] = [
    _c('黑色', 'AEB8900', '#1C1C1C'),
    _c('白色', 'AEB8000', '#E5E5E5'),
    _c('奶白色', 'AEB8001', '#F3EAD9'),
    _c('肤色', 'AEB3100', '#F0DBCC'),
    _c('冷灰色', 'AEB8400', '#363A41'),
    _c('铁灰色', 'AEB8700', '#4A4D50'),
    _c('浅灰色', 'AEB8300', '#C6C6C6'),
    _c('蓝灰色', 'AEB6601', '#565E68'),
    _c('青色', 'AEB5500', '#41E9B7'),
    _c('克莱因蓝', 'AEB6700', '#2A49B3'),
    _c('湖蓝色', 'AEB6500', '#0097D3'),
    _c('蓝色', 'AEB6600', '#2239A7'),
    _c('紫罗兰', 'AEB7500', '#5252A0'),
    _c('绿色', 'AEB4502', '#1E8436'),
    _c('柠檬绿', 'AEB4400', '#85B742'),
    _c('薄荷绿', 'AEB4500', '#C4CF84'),
    _c('军绿色', 'AEB4700', '#788142'),
    _c('橄榄绿', 'AEB4501', '#3A4A2C'),
    _c('墨绿色', 'AEB4600', '#47522A'),
    _c('酒红色', 'AEB1700', '#5F261E'),
    _c('大红色', 'AEB1501', '#C81F1A'),
    _c('朱砂红', 'AEB1401', '#B11A14'),
    _c('品红色', 'AEB1500', '#B23167'),
    _c('冰粉色', 'AEB1300', '#F2C9D4'),
    _c('樱花粉', 'AEB1200', '#F0B9C4'),
    _c('橙色', 'AEB2500', '#FC6A17'),
    _c('黄色', 'AEB3500', '#FEEC03'),
    _c('米黄色', 'AEB3200', '#D9C48A'),
    _c('咖啡色', 'AEB1800', '#7F4434'),
    _c('棕色', 'AEB1600', '#7C4628'),

]

# PLA Matte  (30 色)

ALLIZZ_PLA_MATTE: list[dict] = [
    _c('莫兰迪灰绿', 'APE4300', '#7E8B7A'),
    _c('莫兰迪绿', 'APE4402', '#244F59'),
    _c('莫兰迪蓝', 'APE6400', '#6E84A0'),
    _c('浅紫色', 'APE7200', '#554BBA'),
    _c('南瓜橙', 'APE2300', '#D97B2B'),
    _c('芒果黄', 'APE3400', '#E8C84B'),
    _c('湖蓝色', 'APE6500', '#0097D3'),
    _c('普罗旺斯番茄红', 'APE1600', '#C23B2E'),
    _c('芝麻黑', 'APE8900', '#2B2B2B'),
    _c('椰奶白', 'APE8000', '#F0E9D8'),
    _c('草木灰', 'APE8700', '#9A9B92'),
    _c('西瓜红', 'APE1400', '#D83A3A'),
    _c('榴莲黄', 'APE3600', '#C9A93A'),
    _c('白橡木', 'APE2100', '#E4DCC3'),
    _c('白桃粉', 'APE1100', '#F4C4C0'),
    _c('麦芽绿', 'APE4400', '#B7C66A'),
    _c('薄荷蓝', 'APE6300', '#61C9CF'),
    _c('抹茶绿', 'APE4401', '#657654'),
    _c('樱花粉', 'APE1101', '#F0B9C4'),
    _c('拿铁褐', 'APE1300', '#B98E5E'),
    _c('桃粉色', 'APE1200', '#F0CED8'),
    _c('鹅黄色', 'APE3300', '#E8D24B'),
    _c('绿松石', 'APE4500', '#2E9B9B'),
    _c('柠檬黄', 'APE3500', '#BCBF3D'),
    _c('玫红', 'APE1301', '#D64A6A'),
    _c('焦糖棕', 'APE1800', '#8A5A3A'),
    _c('棕色', 'APE1602', '#7C4628'),
    _c('木色', 'APE1601', '#B98E5E'),
    _c('奶绿', 'APE4200', '#D9E4CA'),
    _c('米黄色', '米黄色', '#D9C48A'),

]

# PLA Silk  (19 色)

ALLIZZ_PLA_SILK: list[dict] = [
    _c('丝绸淡雅金', 'APS9700', '#BCBFC3'),
    _c('丝绸纯金色', 'APS9600', '#BCBFC3'),
    _c('丝绸亮金', 'APS9502', '#E99601'),
    _c('丝绸土豪金Pro', 'APS9504', '#BCBFC3'),
    _c('丝绸银', 'APS9501', '#E6E7F5'),
    _c('丝绸亮银', 'APS9500', '#8E8C8D'),
    _c('丝绸红', 'APS1400', '#B62B49'),
    _c('丝绸橙', 'APS2500', '#FE9342'),
    _c('丝绸黄', 'APS3500', '#E3B403'),
    _c('丝绸绿', 'APS4500', '#08852F'),
    _c('丝绸牛奶绿', 'APS4300', '#BCBFC3'),
    _c('丝绸蓝', 'APS6500', '#434345'),
    _c('丝绸紫', 'APS7500', '#7B58B6'),
    _c('丝绸蓝紫', 'APS7600', '#522C74'),
    _c('丝绸黑', 'APS8900', '#CBC9CE'),
    _c('丝绸白', 'APS8000', '#DADAD6'),
    _c('丝绸粉', 'APS1300', '#F2F2F2'),
    _c('丝绸水晶粉', 'APS1100', '#F2C6D2'),
    _c('丝绸土豪金', '丝绸土豪金', '#D9A93A'),

]

# TPU95A  (2 色)

ALLIZZ_TPU95A: list[dict] = [
    _c('黑色', 'ATB8920', '#1C1C1C'),
    _c('白色', 'ATB8020', '#E5E5E5'),

]

# PLA Pro  (34 色)

ALLIZZ_PLA_PRO: list[dict] = [
    _c('PRO黑色', 'APP8900', '#1A1A1A'),
    _c('PRO白色', 'APP8000', '#F2F2F2'),
    _c('PRO银色', 'APP9500', '#BFC2C4'),
    _c('PRO灰色', 'APP8500', '#9A9DA0'),
    _c('PRO蓝灰色', 'APP6600', '#7E97A8'),
    _c('PRO红砖色', 'APP1700', '#9A3B2E'),
    _c('PRO品红色', 'APP1500', '#B23A8C'),
    _c('PRO红色', 'APP1501', '#C81F1A'),
    _c('PRO橙色', 'APP2600', '#E06A1F'),
    _c('PRO黄色', 'APP3500', '#F2C81E'),
    _c('PRO肤色', 'APP3100', '#E4C9B0'),
    _c('PRO嫩绿色', 'APP4301', '#8FCB5A'),
    _c('PRO橄榄绿', 'APP4500', '#6B7233'),
    _c('PRO赛车绿', 'APP4300', '#1F6B3A'),
    _c('PRO苹果绿', 'APP4200', '#7BC043'),
    _c('PRO绿色', 'APP4501', '#2E9B4F'),
    _c('PRO墨绿色', 'APP4600', '#1F4D2E'),
    _c('PRO松绿色', 'APP4701', '#3E8E5A'),
    _c('PRO军绿色', 'APP4700', '#5C6B3A'),
    _c('PRO粉色', 'APP1200', '#EEB6C4'),
    _c('PRO青色', 'APP5500', '#22A7C9'),
    _c('PRO天蓝色', 'APP6200', '#6EAFE2'),
    _c('PRO蓝色', 'APP6601', '#2B5CB8'),
    _c('PRO兰花紫', 'APP7700', '#7A5BB0'),
    _c('PRO紫色', 'APP7701', '#5A3C79'),
    _c('PRO蜜桃粉', 'APP1300', '#F4C4C0'),
    _c('PRO深咖色', 'APP1800', '#4A2E20'),
    _c('PRO榴莲黄', 'APP3600', '#C9A93A'),
    _c('PRO巧克力色', 'APP1701', '#503726'),
    _c('PRO骨骼色', 'APP3200', '#E8E2D4'),
    _c('PRO浅棕色', 'APP1301', '#B98C5E'),
    _c('PRO棕色', 'APP1600', '#7A4F37'),
    _c('PRO大理石', 'APM8100', '#CFCFCF'),
    _c('闪光银', 'APC9600', '#C8CBD0'),

]

# PLA Basic  (9 色)

ALLIZZ_PLA_BASIC: list[dict] = [
    _c('黑色', 'APB8900', '#1C1C1C'),
    _c('白色', 'APB8000', '#E5E5E5'),
    _c('红色', '红色', '#D0070D'),
    _c('绿色', '绿色', '#1E8436'),
    _c('墨绿色', '墨绿色', '#47522A'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('紫色', '紫色', '#B131A5'),
    _c('浅棕色', '浅棕色', '#C17D3D'),
    _c('闪光银', 'APC9600', '#C8CBD0'),

]

# PETG Metal  (14 色)

ALLIZZ_PETG_METAL: list[dict] = [
    _c('寒武岩灰蓝', 'AEC6600', '#6E8499'),
    _c('松湖绿', 'AEC4600', '#4E9A6E'),
    _c('钛暮紫', 'AEC7700', '#7A5B9A'),
    _c('金属紫', 'AEC7600', '#8F6AA9'),
    _c('闪光银', 'AEC9600', '#C8CBD0'),
    _c('金属银', 'AEC9500', '#E3A87E'),
    _c('黑镍色', 'AEC8900', '#393939'),
    _c('香槟金', 'AEC9700', '#9A8163'),
    _c('黄铜色', 'AEC3600', '#C58807'),
    _c('铜色', 'AEC1700', '#7D614B'),
    _c('红铜色', 'AEC1600', '#B0561A'),
    _c('琥珀金', 'AEC9601', '#B8902A'),
    _c('大理石', 'AEM8100', '#CFCED7'),
    _c('钛空橙', 'AEC2600', '#E07A2A'),

]

# PETG Shiny  (2 色)

ALLIZZ_PETG_SHINY: list[dict] = [
    _c('闪耀黑', 'AEG8900', '#15181A'),
    _c('闪耀红', 'AEG1700', '#C81F1A'),

]

# PETG CF  (2 色)

ALLIZZ_PETG_CF: list[dict] = [
    _c('PETG-CF 15%', 'AEF8961', '#26262A'),
    _c('PETG-CF 5%', 'AEF8960', '#34343A'),

]

# PLA Translucent  (6 色)

ALLIZZ_PLA_TRANSLUCENT: list[dict] = [
    _c('天青绿', 'APT4300', '#7FBF9A'),
    _c('碧落蓝', 'APT6300', '#5FA8D8'),
    _c('霜雾白', 'APT8000', '#EAEFF2'),
    _c('日照橙', 'APT2300', '#E07A2A'),
    _c('云胭粉', 'APT1300', '#EFC6D2'),
    _c('烟罗紫', 'APT7300', '#9B7FC0'),

]

# PLA Silk Multi  (8 色)

ALLIZZ_PLA_SILK_MULTI: list[dict] = [
    _c('丝绸双色蓝绿', 'APS9550', '#BCBFC3'),
    _c('丝绸双色红蓝', 'APS9551', '#BCBFC3'),
    _c('丝绸三色红金绿', 'APS9552', '#BCBFC3'),
    _c('丝绸三色红金蓝', 'APS9554', '#BCBFC3'),
    _c('丝绸三色蓝绿红', 'APS9553', '#BCBFC3'),
    _c('丝绸三色金银铜', 'APS9555', '#BCBFC3'),
    _c('丝绸三色青橙绿', 'APS9556', '#BCBFC3'),
    _c('丝绸三色紫金红', 'APS9557', '#BCBFC3'),

]

# ABS Metal  (4 色)

ALLIZZ_ABS_METAL: list[dict] = [
    _c('黑镍色', 'ABC8900', '#393939'),
    _c('氧化铝', 'ABC9500', '#AEB2B6'),
    _c('闪亮银', 'ABC9600', '#C5C8CC'),
    _c('香槟金', 'ABC9700', '#9A8163'),

]

# PA CF  (1 色)

ALLIZZ_PA_CF: list[dict] = [
    _c('黑色', 'AOF8960', '#1C1C1C'),

]

# PETG Matte  (11 色)

ALLIZZ_PETG_MATTE: list[dict] = [
    _c('黑', 'AEE8900', '#1A1A1A'),
    _c('白色', 'AEE8000', '#E5E5E5'),
    _c('浅灰色', 'AEE8300', '#C6C6C6'),
    _c('肤色', 'AEE3100', '#F0DBCC'),
    _c('红色', 'AEE1500', '#D0070D'),
    _c('橙色', 'AEE2400', '#FC6A17'),
    _c('柠檬绿', 'AEE4300', '#85B742'),
    _c('军绿色', 'AEE4700', '#788142'),
    _c('青色', 'AEE5500', '#41E9B7'),
    _c('湖蓝色', 'AEE6500', '#0097D3'),
    _c('克莱因蓝', 'AEE6700', '#2A49B3'),

]

# PETG Transparent  (11 色)

ALLIZZ_PETG_TRANSPARENT: list[dict] = [
    _c('透明黑', 'AET8900', '#65605D'),
    _c('透明红', 'AET1500', '#F42F38'),
    _c('透明橙', 'AET2500', '#ED9F12'),
    _c('透明黄', 'AET3500', '#FDE41C'),
    _c('透明绿', 'AET4500', '#CBEBAF'),
    _c('透明青蓝', 'AET5500', '#7FD0D8'),
    _c('透明蓝', 'AET6500', '#5974B9'),
    _c('透明紫', 'AET7500', '#B7B1CC'),
    _c('透明橘', 'AET2501', '#E89A6A'),
    _c('透明茶', 'AET2300', '#C9A86A'),
    _c('透明色', 'AET8000', '#E3E7E2'),

]


# ---- 三绿 Sunlu（天猫/淘宝旗舰店色卡，商品图提色，近似值）----

# PLA Basic  (20 色)

SUNLU_PLA_BASIC: list[dict] = [
    _c('黑', '黑', '#1A1A1A'),
    _c('白', '白', '#FFFFFF'),
    _c('暗夜黑', '暗夜黑', '#121212'),
    _c('灰', '灰', '#9A9A9A'),
    _c('红', '红', '#D32F2F'),
    _c('黄', '黄', '#FDD835'),
    _c('绿色', '绿色', '#1E8436'),
    _c('青色', '青色', '#41E9B7'),
    _c('阳光橙', '阳光橙', '#F87D1D'),
    _c('橄榄绿', '橄榄绿', '#3A4A2C'),
    _c('克莱因蓝', '克莱因蓝', '#2A49B3'),
    _c('薰衣草紫', '薰衣草紫', '#886CBF'),
    _c('瓷白色', '瓷白色', '#F5F0E6'),
    _c('骨白色', '骨白色', '#DBD4C2'),
    _c('栗黑色', '栗黑色', '#2B1B17'),
    _c('品红色', '品红色', '#B23167'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('橡木色', '橡木色', '#C19A6B'),
    _c('咖棕色', '咖棕色', '#6F4E37'),
    _c('粉色', '粉色', '#FC737F'),

]


# PLA Matte  (20 色)

SUNLU_PLA_MATTE: list[dict] = [
    _c('哑光红', '哑光红', '#771923'),
    _c('哑光白', '哑光白', '#D5D4D9'),
    _c('哑光黑', '哑光黑', '#282828'),
    _c('哑光灰', '哑光灰', '#454442'),
    _c('哑光绿', '哑光绿', '#2F7D3A'),
    _c('哑光紫', '哑光紫', '#A19CD7'),
    _c('哑光橙', '哑光橙', '#F68601'),
    _c('哑光橄榄绿', '哑光橄榄绿', '#3B393A'),
    _c('哑光淡黄色', '哑光淡黄色', '#FDD835'),
    _c('哑光浅蓝色', '哑光浅蓝色', '#1E88E5'),
    _c('哑光陶泥色', '哑光陶泥色', '#C89B7B'),
    _c('白', '白', '#FFFFFF'),
    _c('黑', '黑', '#1A1A1A'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('青', '青', '#00ACC1'),
    _c('红', '红', '#D32F2F'),
    _c('紫', '紫', '#7B1FA2'),
    _c('粉', '粉', '#EC407A'),
    _c('灰', '灰', '#9A9A9A'),
    _c('透明色', '透明色', '#E3E7E2'),

]


# PLA Transparent  (7 色)

SUNLU_PLA_TRANSPARENT: list[dict] = [
    _c('透明色', '透明色', '#E3E7E2'),
    _c('透明草莓酱', '透明草莓酱', '#F6C9CE'),
    _c('透明紫提冻', '透明紫提冻', '#7B1FA2'),
    _c('透明薄雾黑', '透明薄雾黑', '#1A1A1A'),
    _c('透明雾海蓝', '透明雾海蓝', '#1E88E5'),
    _c('透明芒果汁', '透明芒果汁', '#F3E5A0'),
    _c('透明薄荷冰', '透明薄荷冰', '#C8EBD8'),

]


# PLA Silk  (35 色)

SUNLU_PLA_SILK: list[dict] = [
    _c('丝绸黄金', '丝绸黄金', '#FDD835'),
    _c('丝绸黑', '丝绸黑', '#CBC9CE'),
    _c('丝绸红', '丝绸红', '#B62B49'),
    _c('丝绸银', '丝绸银', '#E6E7F5'),
    _c('丝绸白', '丝绸白', '#DADAD6'),
    _c('丝绸蓝', '丝绸蓝', '#434345'),
    _c('丝绸青铜', '丝绸青铜', '#74714C'),
    _c('丝绸黄铜', '丝绸黄铜', '#FDD835'),
    _c('丝绸红铜', '丝绸红铜', '#E77C5C'),
    _c('丝绸黄', '丝绸黄', '#E3B403'),
    _c('丝绸绿', '丝绸绿', '#08852F'),
    _c('丝绸紫', '丝绸紫', '#7B58B6'),
    _c('丝绸灰', '丝绸灰', '#D7D7D7'),
    _c('丝绸橙', '丝绸橙', '#FE9342'),
    _c('丝绸粉', '丝绸粉', '#F2F2F2'),
    _c('丝绸西瓜红', '丝绸西瓜红', '#F79296'),
    _c('丝绸双色黑金', '丝绸双色黑金', '#1A1A1A'),
    _c('丝绸双色黑蓝', '丝绸双色黑蓝', '#1A1A1A'),
    _c('丝绸双色黑绿', '丝绸双色黑绿', '#1A1A1A'),
    _c('丝绸双色黑紫', '丝绸双色黑紫', '#1A1A1A'),
    _c('丝绸双色粉金', '丝绸双色粉金', '#EC407A'),
    _c('丝绸双色红金', '丝绸双色红金', '#D32F2F'),
    _c('丝绸双色红蓝', '丝绸双色红蓝', '#BCBFC3'),
    _c('丝绸双色绿紫', '丝绸双色绿紫', '#388E3C'),
    _c('丝绸双色蓝绿', '丝绸双色蓝绿', '#BCBFC3'),
    _c('丝绸双色黑白', '丝绸双色黑白', '#1A1A1A'),
    _c('丝绸三色蓝绿紫', '丝绸三色蓝绿紫', '#1E88E5'),
    _c('丝绸三色红黄绿', '丝绸三色红黄绿', '#D32F2F'),
    _c('丝绸三色橙蓝绿', '丝绸三色橙蓝绿', '#F57C00'),
    _c('丝绸三色红黄蓝', '丝绸三色红黄蓝', '#D32F2F'),
    _c('丝绸三色黑金紫', '丝绸三色黑金紫', '#1A1A1A'),
    _c('丝绸四色黑灰红黄', '丝绸四色黑灰红黄', '#1A1A1A'),
    _c('丝绸四色红黄绿黑', '丝绸四色红黄绿黑', '#D32F2F'),
    _c('丝绸四色蓝紫橙黄', '丝绸四色蓝紫橙黄', '#1E88E5'),
    _c('丝绸四色蓝紫红金', '丝绸四色蓝紫红金', '#1E88E5'),

]


# PETG  (42 色)

SUNLU_PETG: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('骨白色', '骨白色', '#DBD4C2'),
    _c('瓷白色', '瓷白色', '#F5F0E6'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('暗夜黑', '暗夜黑', '#121212'),
    _c('栗黑色', '栗黑色', '#2B1B17'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('灰色', '灰色', '#888888'),
    _c('红色', '红色', '#D0070D'),
    _c('淡彩蓝', '淡彩蓝', '#7EC8E3'),
    _c('大地绿', '大地绿', '#4A7023'),
    _c('开心果绿', '开心果绿', '#93C572'),
    _c('透明色', '透明色', '#E3E7E2'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('明黄色', '明黄色', '#FDD835'),
    _c('阳光橙', '阳光橙', '#F87D1D'),
    _c('绿色', '绿色', '#1E8436'),
    _c('克莱因蓝', '克莱因蓝', '#2A49B3'),
    _c('薰衣草紫', '薰衣草紫', '#886CBF'),
    _c('青色', '青色', '#41E9B7'),
    _c('咖棕色', '咖棕色', '#6F4E37'),
    _c('橡木色', '橡木色', '#C19A6B'),
    _c('橄榄绿', '橄榄绿', '#3A4A2C'),
    _c('品红色', '品红色', '#B23167'),
    _c('淡紫色', '淡紫色', '#7B1FA2'),
    _c('奶黄色', '奶黄色', '#FDD835'),
    _c('水粉色', '水粉色', '#F0CBE0'),
    _c('蜜桃粉', '蜜桃粉', '#FFD1DC'),
    _c('裸粉色', '裸粉色', '#EC407A'),
    _c('鼠尾草绿', '鼠尾草绿', '#C4D9BE'),
    _c('削光金', '削光金', '#D4AF37'),
    _c('梅子紫', '梅子紫', '#7B1FA2'),
    _c('深青蓝', '深青蓝', '#00ACC1'),
    _c('勃艮第红', '勃艮第红', '#D32F2F'),
    _c('透明紫', '透明紫', '#B7B1CC'),
    _c('透明红', '透明红', '#F42F38'),
    _c('透明黄', '透明黄', '#FDE41C'),
    _c('透明绿', '透明绿', '#CBEBAF'),
    _c('透明蓝', '透明蓝', '#5974B9'),
    _c('透明橙', '透明橙', '#ED9F12'),
    _c('天空蓝', '天空蓝', '#3EA6DC'),
    _c('薄荷绿', '薄荷绿', '#C4CF84'),

]


# PETG 2.0  (21 色)

SUNLU_PETG_2_0: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('灰色', '灰色', '#888888'),
    _c('红色', '红色', '#D0070D'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('胭粉色', '胭粉色', '#F4A6C0'),
    _c('蜜桃粉', '蜜桃粉', '#FFD1DC'),
    _c('骨白色', '骨白色', '#DBD4C2'),
    _c('阳光橙', '阳光橙', '#F87D1D'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('明黄色', '明黄色', '#FDD835'),
    _c('绿色', '绿色', '#1E8436'),
    _c('薰衣草紫', '薰衣草紫', '#886CBF'),
    _c('湖水蓝', '湖水蓝', '#5DADE2'),
    _c('青色', '青色', '#41E9B7'),
    _c('橡木色', '橡木色', '#C19A6B'),
    _c('咖棕色', '咖棕色', '#6F4E37'),
    _c('品红色', '品红色', '#B23167'),
    _c('克莱因蓝', '克莱因蓝', '#2A49B3'),
    _c('橄榄绿', '橄榄绿', '#3A4A2C'),
    _c('哑光明黄色', '哑光明黄色', '#FDD835'),

]


# PETG Matte  (11 色)

SUNLU_PETG_MATTE: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('灰色', '灰色', '#888888'),
    _c('红色', '红色', '#D0070D'),
    _c('绿色', '绿色', '#1E8436'),
    _c('粉色', '粉色', '#FC737F'),
    _c('薄荷绿', '薄荷绿', '#C4CF84'),
    _c('天空蓝', '天空蓝', '#3EA6DC'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('橙色', '橙色', '#FC6A17'),

]


# TPU95A  (16 色)

SUNLU_TPU95A: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('灰色', '灰色', '#888888'),
    _c('红色', '红色', '#D0070D'),
    _c('绿色', '绿色', '#1E8436'),
    _c('晴空蓝', '晴空蓝', '#1E88E5'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('半透明', '半透明', '#DFE9EF'),
    _c('透明红', '透明红', '#F42F38'),
    _c('透明蓝', '透明蓝', '#5974B9'),
    _c('丝绸浅蓝', '丝绸浅蓝', '#1E88E5'),
    _c('丝绸酒红', '丝绸酒红', '#D32F2F'),
    _c('丝绸黑', '丝绸黑', '#CBC9CE'),
    _c('丝绸深蓝', '丝绸深蓝', '#1E88E5'),
    _c('丝绸奶油白', '丝绸奶油白', '#FFFFFF'),
    _c('阳光橙', '阳光橙', '#F87D1D'),

]


# ABS  (17 色)

SUNLU_ABS: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('灰色', '灰色', '#888888'),
    _c('红色', '红色', '#D0070D'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('绿色', '绿色', '#1E8436'),
    _c('青色', '青色', '#41E9B7'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('棕咖色', '棕咖色', '#6F4E37'),
    _c('品红色', '品红色', '#B23167'),
    _c('橄榄绿', '橄榄绿', '#3A4A2C'),
    _c('克莱因蓝', '克莱因蓝', '#2A49B3'),
    _c('阳光橙', '阳光橙', '#F87D1D'),
    _c('金色', '金色', '#D8AB62'),
    _c('银色', '银色', '#B9BABF'),
    _c('咖棕色', '咖棕色', '#6F4E37'),
    _c('半透明', '半透明', '#DFE9EF'),

]


# ASA  (8 色)

SUNLU_ASA: list[dict] = [
    _c('本色', '本色', '#363638'),
    _c('红�色', '红�色', '#D32F2F'),
    _c('绿色', '绿色', '#1E8436'),
    _c('紫色', '紫色', '#B131A5'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('灰色', '灰色', '#888888'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('黑色', '黑色', '#1C1C1C'),

]


# PA6-GF  (2 色)

SUNLU_PA6_GF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('灰色', '灰色', '#888888'),

]


# ---- eSUN 易生（天猫/淘宝旗舰店色卡，商品页 SKU 提色，近似值）----

# PLA+  (56 色)

ESUN_PLA_PLUS: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('奶油白', '奶油白', '#FFFDD0'),
    _c('骨头白', '骨头白', '#FFFFFF'),
    _c('冷白色', '冷白色', '#CCD3D7'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('银色', '银色', '#B9BABF'),
    _c('水泥灰', '水泥灰', '#3A3A3A'),
    _c('灰色', '灰色', '#888888'),
    _c('红色', '红色', '#D0070D'),
    _c('砖红', '砖红', '#D32F2F'),
    _c('浅卡其', '浅卡其', '#C3B091'),
    _c('浅米黄', '浅米黄', '#FDD835'),
    _c('皮肤色', '皮肤色', '#E8C39E'),
    _c('消防红', '消防红', '#C21E1E'),
    _c('RGB红', 'RGB红', '#D32F2F'),
    _c('天青', '天青', '#00ACC1'),
    _c('RGB蓝', 'RGB蓝', '#1E88E5'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('淡蓝色', '淡蓝色', '#1E88E5'),
    _c('雾霾蓝', '雾霾蓝', '#BCCBE0'),
    _c('糖果蓝', '糖果蓝', '#1E88E5'),
    _c('深空蓝', '深空蓝', '#1E88E5'),
    _c('深蓝色', '深蓝色', '#1F3B70'),
    _c('长春花蓝', '长春花蓝', '#5744A2'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('杏仁黄', '杏仁黄', '#ECF59C'),
    _c('金色', '金色', '#D8AB62'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('杏橘', '杏橘', '#FFB347'),
    _c('珊瑚橘', '珊瑚橘', '#FF7F50'),
    _c('粉色', '粉色', '#FC737F'),
    _c('糖果粉', '糖果粉', '#EC407A'),
    _c('桃粉', '桃粉', '#FFD1DC'),
    _c('RGB绿', 'RGB绿', '#388E3C'),
    _c('松韵', '松韵', '#7CB342'),
    _c('青翠', '青翠', '#00ACC1'),
    _c('嫩绿色', '嫩绿色', '#388E3C'),
    _c('薄荷绿', '薄荷绿', '#C4CF84'),
    _c('橄榄绿', '橄榄绿', '#3A4A2C'),
    _c('抹茶绿', '抹茶绿', '#657654'),
    _c('松绿色', '松绿色', '#388E3C'),
    _c('绿色', '绿色', '#1E8436'),
    _c('芥子绿', '芥子绿', '#388E3C'),
    _c('草绿', '草绿', '#7FD530'),
    _c('丁香紫', '丁香紫', '#BDAEDE'),
    _c('紫色', '紫色', '#B131A5'),
    _c('浅棕色', '浅棕色', '#C17D3D'),
    _c('棕色', '棕色', '#7C4628'),
    _c('桃红色', '桃红色', '#BD408B'),
    _c('蜜橘橙', '蜜橘橙', '#F57C00'),
    _c('马卡龙', '马卡龙', '#F6C457'),
    _c('渐变色', '渐变色', '#6999D7'),
    _c('金银', '金银', '#D4AF37'),
    _c('红蓝', '红蓝', '#D32F2F'),
    _c('易生青翠', '易生青翠', '#00ACC1'),
    _c('易生松韵', '易生松韵', '#7CB342'),

]


# PLA Basic  (28 色)

ESUN_PLA_BASIC: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('冷白色', '冷白色', '#CCD3D7'),
    _c('骨头白', '骨头白', '#FFFFFF'),
    _c('银色', '银色', '#B9BABF'),
    _c('灰色', '灰色', '#888888'),
    _c('水泥灰', '水泥灰', '#3A3A3A'),
    _c('浅灰', '浅灰', '#D2D8D8'),
    _c('天空蓝', '天空蓝', '#3EA6DC'),
    _c('天青', '天青', '#00ACC1'),
    _c('浅蓝', '浅蓝', '#B5E4EB'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('深蓝', '深蓝', '#1E88E5'),
    _c('绿色', '绿色', '#1E8436'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('松韵', '松韵', '#7CB342'),
    _c('红色', '红色', '#D0070D'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('粉色', '粉色', '#FC737F'),
    _c('芭比粉', '芭比粉', '#EC407A'),
    _c('橄榄绿色', '橄榄绿色', '#719764'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('紫色', '紫色', '#B131A5'),
    _c('葡萄紫', '葡萄紫', '#D7A2E3'),
    _c('消防红色', '消防红色', '#D32F2F'),
    _c('棕色', '棕色', '#7C4628'),
    _c('米黄色', '米黄色', '#D9C48A'),
    _c('嫩绿色', '嫩绿色', '#388E3C'),

]


# PLA Matte  (38 色)

ESUN_PLA_MATTE: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('奶油白', '奶油白', '#FFFDD0'),
    _c('杏仁黄', '杏仁黄', '#ECF59C'),
    _c('桃粉色', '桃粉色', '#F0CED8'),
    _c('浅卡其', '浅卡其', '#C3B091'),
    _c('莫兰迪紫', '莫兰迪紫', '#7B1FA2'),
    _c('水泥灰', '水泥灰', '#3A3A3A'),
    _c('深灰色', '深灰色', '#4E4E4E'),
    _c('薄荷绿', '薄荷绿', '#C4CF84'),
    _c('消防红', '消防红', '#C21E1E'),
    _c('抹茶绿', '抹茶绿', '#657654'),
    _c('莫兰迪绿', '莫兰迪绿', '#244F59'),
    _c('天青', '天青', '#00ACC1'),
    _c('湖蓝色', '湖蓝色', '#0097D3'),
    _c('丁香紫', '丁香紫', '#BDAEDE'),
    _c('草莓红', '草莓红', '#F75078'),
    _c('蜜橘橙', '蜜橘橙', '#F57C00'),
    _c('棕色', '棕色', '#7C4628'),
    _c('橄榄绿', '橄榄绿', '#3A4A2C'),
    _c('深蓝', '深蓝', '#1E88E5'),
    _c('绿紫', '绿紫', '#388E3C'),
    _c('红黑', '红黑', '#382D3B'),
    _c('红蓝', '红蓝', '#D32F2F'),
    _c('紫黄', '紫黄', '#7B1FA2'),
    _c('紫蓝', '紫蓝', '#7B1FA2'),
    _c('绿粉', '绿粉', '#388E3C'),
    _c('绿蓝', '绿蓝', '#388E3C'),
    _c('黑白', '黑白', '#1A1A1A'),
    _c('渐变色', '渐变色', '#6999D7'),
    _c('马卡龙', '马卡龙', '#F6C457'),
    _c('水果糖', '水果糖', '#FF69B4'),
    _c('稻禾', '稻禾', '#C2B280'),
    _c('深海', '深海', '#006994'),
    _c('旭日', '旭日', '#FF8C00'),
    _c('黄白青', '黄白青', '#FDD835'),
    _c('黄粉紫', '黄粉紫', '#FDD835'),
    _c('粉黛', '粉黛', '#EC407A'),
    _c('乌黑', '乌黑', '#1A1A1A'),

]


# PLA Silk  (29 色)

ESUN_PLA_SILK: list[dict] = [
    _c('烈日色', '烈日色', '#FFD700'),
    _c('朝霞色', '朝霞色', '#FFA07A'),
    _c('珊瑚色', '珊瑚色', '#FF7F50'),
    _c('宇宙色', '宇宙色', '#2E3192'),
    _c('森林色', '森林色', '#228B22'),
    _c('广寒宫', '广寒宫', '#B0C4DE'),
    _c('花果山', '花果山', '#8B4513'),
    _c('火焰山', '火焰山', '#FF4500'),
    _c('瑶池', '瑶池', '#DDA0DD'),
    _c('龙宫', '龙宫', '#1E90FF'),
    _c('-金', '-金', '#D4AF37'),
    _c('银色', '银色', '#B9BABF'),
    _c('玫瑰金', '玫瑰金', '#B14844'),
    _c('红铜', '红铜', '#D32F2F'),
    _c('青铜', '青铜', '#816D45'),
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('天青', '天青', '#00ACC1'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('浅蓝', '浅蓝', '#B5E4EB'),
    _c('灰色', '灰色', '#888888'),
    _c('粉色', '粉色', '#FC737F'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('紫色', '紫色', '#B131A5'),
    _c('绿色', '绿色', '#1E8436'),
    _c('青蓝单色', '青蓝单色', '#00ACC1'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('红色', '红色', '#D0070D'),
    _c('绿黄单色', '绿黄单色', '#388E3C'),

]


# PLA Marble  (1 色)

ESUN_PLA_MARBLE: list[dict] = [
    _c('大理石', '大理石', '#CFCED7'),

]


# PLA Rainbow  (11 色)

ESUN_PLA_RAINBOW: list[dict] = [
    _c('冰透粉', '冰透粉', '#EC407A'),
    _c('冰透青', '冰透青', '#00ACC1'),
    _c('冰透绿', '冰透绿', '#388E3C'),
    _c('冰透焰火', '冰透焰火', '#FF6B35'),
    _c('黄粉', '黄粉', '#FDD835'),
    _c('紫蓝青', '紫蓝青', '#7B1FA2'),
    _c('紫蓝灰', '紫蓝灰', '#7B1FA2'),
    _c('橙灰', '橙灰', '#F57C00'),
    _c('紫红', '紫红', '#7B1FA2'),
    _c('黄绿蓝', '黄绿蓝', '#FDD835'),
    _c('透明蓝白', '透明蓝白', '#1E88E5'),

]


# PLA 魔幻双色  (4 色)

ESUN_PLA_MAGIC: list[dict] = [
    _c('暗耀金', '暗耀金', '#D4AF37'),
    _c('暗耀绿', '暗耀绿', '#388E3C'),
    _c('暗耀紫', '暗耀紫', '#7B1FA2'),
    _c('暗耀蓝', '暗耀蓝', '#1E88E5'),

]


# PLA 变色龙  (5 色)

ESUN_PLA_CHAMELEON: list[dict] = [
    _c('北极星', '北极星', '#2E3192'),
    _c('科技黑', '科技黑', '#1A1A1A'),
    _c('树莓红', '树莓红', '#D32F2F'),
    _c('星云紫', '星云紫', '#7B1FA2'),
    _c('银河蓝', '银河蓝', '#C0C0C0'),

]


# PLA Wood  (5 色)

ESUN_PLA_WOOD: list[dict] = [
    _c('原色', '原色', '#D66F76'),
    _c('白桦木', '白桦木', '#FFFFFF'),
    _c('白杨木', '白杨木', '#FFFFFF'),
    _c('胡桃木', '胡桃木', '#5C4033'),
    _c('橡木', '橡木', '#C19A6B'),

]


# PETG Basic  (15 色)

ESUN_PETG_BASIC: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('银色', '银色', '#B9BABF'),
    _c('红色', '红色', '#D0070D'),
    _c('灰色', '灰色', '#888888'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('透浅紫', '透浅紫', '#7B1FA2'),
    _c('透浅绿', '透浅绿', '#388E3C'),
    _c('透浅蓝', '透浅蓝', '#1E88E5'),
    _c('透浅粉', '透浅粉', '#EC407A'),
    _c('透橙', '透橙', '#F57C00'),
    _c('透蓝', '透蓝', '#1E88E5'),
    _c('透绿', '透绿', '#388E3C'),
    _c('透浅橙', '透浅橙', '#F57C00'),
    _c('透红', '透红', '#D32F2F'),

]


# PETG Matte  (16 色)

ESUN_PETG_MATTE: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('汉白玉', '汉白玉', '#FFFFFF'),
    _c('水泥灰', '水泥灰', '#3A3A3A'),
    _c('深灰', '深灰', '#4A4A4A'),
    _c('浅卡其', '浅卡其', '#C3B091'),
    _c('桃粉', '桃粉', '#FFD1DC'),
    _c('杏仁黄', '杏仁黄', '#ECF59C'),
    _c('杏橘', '杏橘', '#FFB347'),
    _c('浅蓝', '浅蓝', '#B5E4EB'),
    _c('丁香紫', '丁香紫', '#BDAEDE'),
    _c('薄荷绿', '薄荷绿', '#C4CF84'),
    _c('抹茶绿', '抹茶绿', '#657654'),
    _c('青砖', '青砖', '#00ACC1'),
    _c('砖红', '砖红', '#D32F2F'),
    _c('陶褐', '陶褐', '#8B5A2B'),
    _c('土棕', '土棕', '#6D4C41'),

]


# PETG Transparent  (14 色)

ESUN_PETG_TRANSPARENT: list[dict] = [
    _c('透明色', '透明色', '#E3E7E2'),
    _c('透明蓝', '透明蓝', '#5974B9'),
    _c('透明绿', '透明绿', '#CBEBAF'),
    _c('透明橙', '透明橙', '#ED9F12'),
    _c('透浅橙星空', '透浅橙星空', '#F57C00'),
    _c('透红星空', '透红星空', '#D32F2F'),
    _c('透浅紫星空', '透浅紫星空', '#7B1FA2'),
    _c('透浅蓝星空', '透浅蓝星空', '#1E88E5'),
    _c('透浅绿星空', '透浅绿星空', '#388E3C'),
    _c('透浅粉星空', '透浅粉星空', '#EC407A'),
    _c('透橙星空', '透橙星空', '#F57C00'),
    _c('透蓝星空', '透蓝星空', '#1E88E5'),
    _c('透绿星空', '透绿星空', '#388E3C'),
    _c('透明星空', '透明星空', '#B8C6E0'),

]


# PETG+HS  (9 色)

ESUN_PETG_HS: list[dict] = [
    _c('实黑', '实黑', '#1A1A1A'),
    _c('实白', '实白', '#FFFFFF'),
    _c('实灰', '实灰', '#9A9A9A'),
    _c('实橙', '实橙', '#F57C00'),
    _c('实银', '实银', '#C0C0C0'),
    _c('实蓝', '实蓝', '#1E88E5'),
    _c('实黄', '实黄', '#FDD835'),
    _c('消防红', '消防红', '#C21E1E'),
    _c('实绿', '实绿', '#388E3C'),

]


# PETG 夜光  (2 色)

ESUN_PETG_GLOW: list[dict] = [
    _c('蓝色', '蓝色', '#2239A7'),
    _c('绿色', '绿色', '#1E8436'),

]


# PETG UV变色  (2 色)

ESUN_PETG_UV: list[dict] = [
    _c('红色', '红色', '#D0070D'),
    _c('深蓝', '深蓝', '#1E88E5'),

]


# ABS  (13 色)

ESUN_ABS: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('暖白色', '暖白色', '#FFFFFF'),
    _c('银色', '银色', '#B9BABF'),
    _c('白色', '白色', '#E5E5E5'),
    _c('灰色', '灰色', '#888888'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('紫色', '紫色', '#B131A5'),
    _c('绿色', '绿色', '#1E8436'),
    _c('冷白色', '冷白色', '#CCD3D7'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('淡蓝色', '淡蓝色', '#1E88E5'),
    _c('消防红', '消防红', '#C21E1E'),
    _c('黄色', '黄色', '#FEEC03'),

]


# ABS+  (10 色)

ESUN_ABS_PLUS: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('银色', '银色', '#B9BABF'),
    _c('冷白色', '冷白色', '#CCD3D7'),
    _c('淡蓝色', '淡蓝色', '#1E88E5'),
    _c('消防红', '消防红', '#C21E1E'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('灰色', '灰色', '#888888'),
    _c('紫色', '紫色', '#B131A5'),

]


# ABS-CF  (5 色)

ESUN_ABS_CF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('暗红', '暗红', '#D32F2F'),
    _c('暗紫', '暗紫', '#7B1FA2'),
    _c('暗蓝', '暗蓝', '#1E88E5'),
    _c('暗绿', '暗绿', '#388E3C'),

]


# ASA+  (9 色)

ESUN_ASA_PLUS: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('红色', '红色', '#D0070D'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('灰色', '灰色', '#888888'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('冷白', '冷白', '#ECECEC'),
    _c('绿色', '绿色', '#1E8436'),
    _c('白色', '白色', '#E5E5E5'),
    _c('银色', '银色', '#B9BABF'),

]


# TPU95A  (22 色)

ESUN_TPU95A: list[dict] = [
    _c('透明色', '透明色', '#E3E7E2'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('灰色', '灰色', '#888888'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('红色', '红色', '#D0070D'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('绿色', '绿色', '#1E8436'),
    _c('渐变', '渐变', '#9099A6'),
    _c('透明蓝', '透明蓝', '#5974B9'),
    _c('透明绿', '透明绿', '#CBEBAF'),
    _c('透明粉', '透明粉', '#F5CCD4'),
    _c('透明紫', '透明紫', '#B7B1CC'),
    _c('透明黄', '透明黄', '#FDE41C'),
    _c('透明橙', '透明橙', '#ED9F12'),
    _c('透明红', '透明红', '#F42F38'),
    _c('三文鱼色', '三文鱼色', '#FA8072'),
    _c('本色', '本色', '#363638'),
    _c('-LW轻质白色0.', '-LW轻质白色0.', '#FFFFFF'),
    _c('-LW轻质黑色0.', '-LW轻质黑色0.', '#1A1A1A'),
    _c('-LW轻质灰色0.', '-LW轻质灰色0.', '#9A9A9A'),

]


# PVA  (1 色)

ESUN_PVA: list[dict] = [
    _c('黄色', '黄色', '#FEEC03'),

]


# PA  (2 色)

ESUN_PA: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),

]


# PA-CF  (1 色)

ESUN_PA_CF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]


# ---- Inslogic（天猫/淘宝商品页 SKU 提色，近似值）----

# PLA Pro  (14 色)

INSLOGIC_PLA_PRO: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('灰色', '灰色', '#888888'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('绿色', '绿色', '#1E8436'),
    _c('红色', '红色', '#D0070D'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('青色', '青色', '#41E9B7'),
    _c('咖棕色', '咖棕色', '#6F4E37'),
    _c('橄榄绿色', '橄榄绿色', '#719764'),
    _c('粉色', '粉色', '#FC737F'),
    _c('紫色', '紫色', '#B131A5'),
    _c('橙色', '橙色', '#FC6A17'),

]


# PLA Matte  (15 色)

INSLOGIC_PLA_MATTE: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('灰色', '灰色', '#888888'),
    _c('红色', '红色', '#D0070D'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('粉色', '粉色', '#FC737F'),
    _c('紫色', '紫色', '#B131A5'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('骨白', '骨白', '#F3E4AC'),
    _c('浅蓝', '浅蓝', '#B5E4EB'),
    _c('橄榄绿', '橄榄绿', '#3A4A2C'),
    _c('木色', '木色', '#B98E5E'),
    _c('陶泥色', '陶泥色', '#686254'),
    _c('淡黄', '淡黄', '#FFF6A9'),

]


# PLA Silk  (21 色)

INSLOGIC_PLA_SILK: list[dict] = [
    _c('银色', '银色', '#B9BABF'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('红色', '红色', '#D0070D'),
    _c('粉色', '粉色', '#FC737F'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('紫色', '紫色', '#B131A5'),
    _c('黄金色', '黄金色', '#D59435'),
    _c('红铜色', '红铜色', '#B0561A'),
    _c('黄铜色', '黄铜色', '#C58807'),
    _c('青铜色', '青铜色', '#4F482F'),
    _c('粉金双色', '粉金双色', '#9099A6'),
    _c('红蓝双色', '红蓝双色', '#9099A6'),
    _c('红金双色', '红金双色', '#9099A6'),
    _c('蓝绿双色', '蓝绿双色', '#9099A6'),
    _c('蓝绿紫三色', '蓝绿紫三色', '#9099A6'),
    _c('红黄蓝三色', '红黄蓝三色', '#9099A6'),
    _c('黑灰红黄四色', '黑灰红黄四色', '#9099A6'),
    _c('蓝紫橙黄四色', '蓝紫橙黄四色', '#9099A6'),
    _c('蓝紫红金四色', '蓝紫红金四色', '#9099A6'),
    _c('红黄绿黑四色', '红黄绿黑四色', '#9099A6'),

]


# PETG Pro  (11 色)

INSLOGIC_PETG_PRO: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('灰色', '灰色', '#888888'),
    _c('粉色', '粉色', '#FC737F'),
    _c('天空蓝', '天空蓝', '#3EA6DC'),
    _c('薄荷绿', '薄荷绿', '#C4CF84'),
    _c('红色', '红色', '#D0070D'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('绿色', '绿色', '#1E8436'),
    _c('橙色', '橙色', '#FC6A17'),

]


# PETG 2.0  (20 色)

INSLOGIC_PETG_2_0: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('灰色', '灰色', '#888888'),
    _c('胭粉色', '胭粉色', '#F4A6C0'),
    _c('湖水蓝', '湖水蓝', '#5DADE2'),
    _c('红色', '红色', '#D0070D'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('绿色', '绿色', '#1E8436'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('明黄色', '明黄色', '#FDD835'),
    _c('蜜桃粉', '蜜桃粉', '#FFD1DC'),
    _c('薰衣草紫', '薰衣草紫', '#886CBF'),
    _c('青色', '青色', '#41E9B7'),
    _c('橡木色', '橡木色', '#C19A6B'),
    _c('骨白色', '骨白色', '#DBD4C2'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('咖棕色', '咖棕色', '#6F4E37'),
    _c('品红色', '品红色', '#B23167'),
    _c('克莱因蓝', '克莱因蓝', '#2A49B3'),
    _c('橄榄绿', '橄榄绿', '#3A4A2C'),

]


# PETG-CF  (1 色)

INSLOGIC_PETG_CF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]


# ABS  (3 色)

INSLOGIC_ABS: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('灰色', '灰色', '#888888'),

]


# TPU95A  (2 色)

INSLOGIC_TPU95A: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),

]


# TPU90A  (2 色)

INSLOGIC_TPU90A: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),

]


# PA6/66  (2 色)

INSLOGIC_PA6_66: list[dict] = [
    _c('本色', '本色', '#363638'),
    _c('黑色', '黑色', '#1C1C1C'),

]


# PA12-CF  (1 色)

INSLOGIC_PA12_CF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]


# ---- FusRock / 闪铸 Flashforge（天猫/淘宝商品页 SKU 提色，近似值）----

# PLA-Aero Pro  (3 色)

FUSROCK_PLA_AERO_PRO: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('灰色', '灰色', '#888888'),
    _c('军绿色', '军绿色', '#788142'),

]


# PETG-HF  (11 色)

FUSROCK_PETG_HF: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('绿色', '绿色', '#1E8436'),
    _c('紫色', '紫色', '#B131A5'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('红色', '红色', '#D0070D'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('灰色', '灰色', '#888888'),
    _c('棕色', '棕色', '#7C4628'),

]


# PETG-GF  (6 色)

FUSROCK_PETG_GF: list[dict] = [
    _c('磨砂黑', '磨砂黑', '#949494'),
    _c('磨砂白', '磨砂白', '#E3E0D7'),
    _c('磨砂红', '磨砂红', '#B62422'),
    _c('磨砂蓝', '磨砂蓝', '#0B4693'),
    _c('磨砂紫', '磨砂紫', '#5B4B8A'),
    _c('磨砂绿', '磨砂绿', '#27B148'),

]


# PETG-CF HF  (1 色)

FUSROCK_PETG_CF_HF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]


# PET-CF  (1 色)

FUSROCK_PET_CF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]


# PET-GF  (8 色)

FUSROCK_PET_GF: list[dict] = [
    _c('米白色', '米白色', '#E3E3DF'),
    _c('灰色', '灰色', '#888888'),
    _c('红色', '红色', '#D0070D'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('天蓝色', '天蓝色', '#5596E3'),
    _c('橘橙色', '橘橙色', '#F97C01'),
    _c('棕色', '棕色', '#7C4628'),
    _c('白色', '白色', '#E5E5E5'),

]


# ABS  (14 色)

FUSROCK_ABS: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('灰色', '灰色', '#888888'),
    _c('红色', '红色', '#D0070D'),
    _c('米白', '米白', '#F5F0E6'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('紫色', '紫色', '#B131A5'),
    _c('绿色', '绿色', '#1E8436'),
    _c('军绿色', '军绿色', '#788142'),
    _c('棕色', '棕色', '#7C4628'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('银色', '银色', '#B9BABF'),

]


# ABS-HF  (4 色)

FUSROCK_ABS_HF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('米白色', '米白色', '#E3E3DF'),
    _c('灰色', '灰色', '#888888'),
    _c('白色', '白色', '#E5E5E5'),

]


# ABS-GF  (9 色)

FUSROCK_ABS_GF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('灰色', '灰色', '#888888'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('紫色', '紫色', '#B131A5'),
    _c('草绿', '草绿', '#7FD530'),
    _c('军绿', '军绿', '#343D1A'),
    _c('红色', '红色', '#D0070D'),

]


# NexABS-CF20  (1 色)

FUSROCK_NEXABS_CF20: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]


# ASA  (13 色)

FUSROCK_ASA: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('米白色', '米白色', '#E3E3DF'),
    _c('白色', '白色', '#E5E5E5'),
    _c('红色', '红色', '#D0070D'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('灰色', '灰色', '#888888'),
    _c('绿色', '绿色', '#1E8436'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('棕色', '棕色', '#7C4628'),
    _c('紫色', '紫色', '#B131A5'),
    _c('军绿色', '军绿色', '#788142'),
    _c('银色', '银色', '#B9BABF'),

]


# ASA-Aero LT  (5 色)

FUSROCK_ASA_AERO_LT: list[dict] = [
    _c('本白色', '本白色', '#C54D5F'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('红色', '红色', '#D0070D'),
    _c('灰色', '灰色', '#888888'),
    _c('黄色', '黄色', '#FEEC03'),

]


# NexASA-CF20  (1 色)

FUSROCK_NEXASA_CF20: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]


# TPU 95A HF  (5 色)

FUSROCK_TPU_95A_HF: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('鲜绿色', '鲜绿色', '#3CB371'),
    _c('灰色', '灰色', '#888888'),
    _c('透明色', '透明色', '#E3E7E2'),

]


# TPU 85A  (5 色)

FUSROCK_TPU_85A: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('透明', '透明', '#254C85'),
    _c('鲜绿色', '鲜绿色', '#3CB371'),

]


# TPU 90A HF  (3 色)

FUSROCK_TPU_90A_HF: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('鲜绿色', '鲜绿色', '#3CB371'),

]


# TPU-Aero  (4 色)

FUSROCK_TPU_AERO: list[dict] = [
    _c('本白色', '本白色', '#C54D5F'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('荧光绿', '荧光绿', '#71F03F'),
    _c('肤色', '肤色', '#F0DBCC'),

]


# TPU 64D  (2 色)

FUSROCK_TPU_64D: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),

]


# TPU 78D  (2 色)

FUSROCK_TPU_78D: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),

]


# PAHT  (2 色)

FUSROCK_PAHT: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('本色', '本色', '#363638'),

]


# PA-CF  (1 色)

FUSROCK_PA_CF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]


# NexPA-CF25  (1 色)

FUSROCK_NEXPA_CF25: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]


# NexPA-GF25  (4 色)

FUSROCK_NEXPA_GF25: list[dict] = [
    _c('本色', '本色', '#363638'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('蓝色', '蓝色', '#2239A7'),

]


# PAHT-GF  (8 色)

FUSROCK_PAHT_GF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('本色', '本色', '#363638'),
    _c('红色', '红色', '#D0070D'),
    _c('灰色', '灰色', '#888888'),
    _c('棕色', '棕色', '#7C4628'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('深灰色', '深灰色', '#4E4E4E'),

]


# PEBA 95A  (1 色)

FUSROCK_PEBA_95A: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]


# PC/ABS  (2 色)

FUSROCK_PC_ABS: list[dict] = [
    _c('本色', '本色', '#363638'),
    _c('黑色', '黑色', '#1C1C1C'),

]


# S-Multi  (1 色)

FUSROCK_S_MULTI: list[dict] = [
    _c('本色', '本色', '#363638'),

]


# S-PAHT  (2 色)

FUSROCK_S_PAHT: list[dict] = [
    _c('本色', '本色', '#363638'),
    _c('黑色', '黑色', '#1C1C1C'),

]


# ---- 闪铸 Flashforge（官网 products.json 官方色名，HEX 近似）----

# HS PLA  (27 色)

FLASHFORGE_HS_PLA: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),
    _c('白色', 'White', '#E5E5E5'),
    _c('紫色', 'Purple', '#B131A5'),
    _c('浅粉色', 'Light Pink', '#F8C8D8'),
    _c('橙色', 'Orange', '#FC6A17'),
    _c('本色', 'Natural', '#363638'),
    _c('黄色', 'Yellow', '#FEEC03'),
    _c('蓝色', 'Blue', '#2239A7'),
    _c('青色', 'Cyan', '#41E9B7'),
    _c('冰蓝', 'Ice Blue', '#9CC8E2'),
    _c('品红', 'Magenta', '#E93096'),
    _c('天空蓝', 'Sky Blue', '#3EA6DC'),
    _c('荧光橙', 'Neon Orange', '#FF6207'),
    _c('宝石红', 'Ruby Red', '#C2183C'),
    _c('荧光黄', 'Neon Yellow', '#EEFD04'),
    _c('纯绿', 'Pure Green', '#2E9E4F'),
    _c('极光绿', 'Aurora Green', '#3AB8B4'),
    _c('极光紫', 'Aurora Purple', '#9A6BD6'),
    _c('极光红', 'Aurora Red', '#FF5A6E'),
    _c('橄榄绿', 'Oliver Green', '#3A4A2C'),
    _c('铁灰', 'Iron Gray', '#5A5A5A'),
    _c('夜光旋律', 'Luminous Melody', '#9099A6'),
    _c('浅棕色', 'Ligjht Brown', '#C17D3D'),
    _c('星空紫', 'Galaxy Purple', '#3E2A63'),
    _c('星空蓝', 'Galaxy Blue', '#27356B'),
    _c('星空黑', 'Galaxy Black', '#14161C'),
    _c('变色龙彩虹糖', 'Chameleon Rainbow Candy', '#9099A6'),

]


# HS PLA 多色  (7 色)

FLASHFORGE_HS_PLA_MULTI: list[dict] = [
    _c('钛烧色', 'Burnt Titanium', '#9099A6'),
    _c('深渊紫', 'Abyssal Purple', '#9099A6'),
    _c('深渊红', 'Abyssal Red', '#9099A6'),
    _c('天际蓝', 'Skydiver', '#9099A6'),
    _c('玫瑰石英', 'Rose Quartz', '#9099A6'),
    _c('星云紫', 'Nebula Purple', '#9099A6'),
    _c('钛烧+深渊红', 'Burnt Titanium&Abyssal Red', '#9099A6'),

]


# HS PLA 彩虹  (3 色)

FLASHFORGE_HS_PLA_RAINBOW: list[dict] = [
    _c('糖果色', 'Candy', '#9099A6'),
    _c('珊瑚色', 'Corals', '#9099A6'),
    _c('夏日遐想', 'Summer Reverie', '#9099A6'),

]


# HS PETG  (13 色)

FLASHFORGE_HS_PETG: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),
    _c('白色', 'White', '#E5E5E5'),
    _c('黄色', 'Yellow', '#FEEC03'),
    _c('蓝色', 'Blue', '#2239A7'),
    _c('绿色', 'Green', '#1E8436'),
    _c('橙色', 'Orange', '#FC6A17'),
    _c('玫瑰红', 'Rose', '#C71585'),
    _c('粉色', 'Pink', '#FC737F'),
    _c('紫色', 'Purple', '#B131A5'),
    _c('灰色', 'Gray', '#888888'),
    _c('棕色', 'Brown', '#7C4628'),
    _c('金色', 'Gold', '#D8AB62'),
    _c('银白', 'Sliver', '#D6D9DD'),

]


# HS PETG 金属  (6 色)

FLASHFORGE_HS_PETG_METALLIC: list[dict] = [
    _c('蓝色', 'Blue', '#2239A7'),
    _c('绿色', 'Green', '#1E8436'),
    _c('紫色', 'Purple', '#B131A5'),
    _c('金色', 'Gold', '#D8AB62'),
    _c('红色', 'Red', '#D0070D'),
    _c('银色', 'Silver', '#B9BABF'),

]


# HS PETG 透明  (6 色)

FLASHFORGE_HS_PETG_TRANSP: list[dict] = [
    _c('黄色', 'Yellow', '#FEEC03'),
    _c('绿色', 'Green', '#1E8436'),
    _c('紫色', 'Purple', '#B131A5'),
    _c('天空蓝', 'Sky Blue', '#3EA6DC'),
    _c('宝石红', 'Ruby Red', '#C2183C'),
    _c('透明', 'Transparent', '#254C85'),

]


# HS PETG 多色  (1 色)

FLASHFORGE_HS_PETG_MULTI: list[dict] = [
    _c('钛烧色', 'Burnt Titanium', '#9099A6'),

]


# PLA Basic  (16 色)

FLASHFORGE_PLA_BASIC: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),
    _c('白色', 'White', '#E5E5E5'),
    _c('本色', 'Natural', '#363638'),
    _c('绿色', 'Green', '#1E8436'),
    _c('棕色', 'Brown', '#7C4628'),
    _c('肤色', 'Skin', '#F0DBCC'),
    _c('黄色', 'Yellow', '#FEEC03'),
    _c('橙色', 'Orange', '#FC6A17'),
    _c('蓝色', 'Blue', '#2239A7'),
    _c('银色', 'Silver', '#B9BABF'),
    _c('金色', 'Gold', '#D8AB62'),
    _c('粉色', 'Pink', '#FC737F'),
    _c('浅绿色', 'Light Green', '#A5D66A'),
    _c('红色', 'Red', '#D0070D'),
    _c('灰色', 'Gray', '#888888'),
    _c('紫色', 'Purple', '#B131A5'),

]


# PLA Crystal  (9 色)

FLASHFORGE_PLA_CRYSTAL: list[dict] = [
    _c('彩虹糖', 'Rainbow Candy', '#9099A6'),
    _c('人鱼之泪', 'Mermaid Tears', '#9099A6'),
    _c('夏日遐想', 'Summer Reverie', '#9099A6'),
    _c('绿野仙踪绿', 'Oz Wizard Green', '#9099A6'),
    _c('薄荷冰沙', 'Mint Slush', '#9099A6'),
    _c('深海秘境', 'Deep Sea Realm', '#9099A6'),
    _c('夏夜萤火', 'Summer Night Fireflies', '#9099A6'),
    _c('粉海豚', 'Pink Dolphin', '#9099A6'),
    _c('哥特玫瑰', 'Gothic Rose', '#6E2639'),

]


# PLA Pro  (17 色)

FLASHFORGE_PLA_PRO: list[dict] = [
    _c('玫瑰红', 'Rose', '#C71585'),
    _c('棕色', 'Brown', '#7C4628'),
    _c('肤色', 'Skin', '#F0DBCC'),
    _c('冷白', 'Cool White', '#ECECEC'),
    _c('黑色', 'Black', '#1C1C1C'),
    _c('黄色', 'Yellow', '#FEEC03'),
    _c('白色', 'White', '#E5E5E5'),
    _c('银灰', 'Silver  Gray', '#B8BCC2'),
    _c('绿色', 'Green', '#1E8436'),
    _c('本色', 'Natural', '#363638'),
    _c('橙色', 'Orange', '#FC6A17'),
    _c('灰色', 'Gray', '#888888'),
    _c('粉色', 'Pink', '#FC737F'),
    _c('银色', 'Silver', '#B9BABF'),
    _c('紫色', 'Purple', '#B131A5'),
    _c('红色', 'Red', '#D0070D'),
    _c('蓝色', 'Blue', '#2239A7'),

]


# PLA 多色  (4 色)

FLASHFORGE_PLA_MULTI: list[dict] = [
    _c('钛烧色', 'Burnt Titanium', '#9099A6'),
    _c('星云紫', 'Nebula Purple', '#9099A6'),
    _c('玫瑰石英', 'Rose Quartz', '#9099A6'),
    _c('天际蓝', 'Skydiver', '#9099A6'),

]


# PLA Silk+  (27 色)

FLASHFORGE_PLA_SILK: list[dict] = [
    _c('红色', 'Red', '#D0070D'),
    _c('金色', 'Gold', '#D8AB62'),
    _c('银色', 'Silver', '#B9BABF'),
    _c('黑色', 'Black', '#1C1C1C'),
    _c('白色', 'White', '#E5E5E5'),
    _c('绿色', 'Green', '#1E8436'),
    _c('肤色', 'Skin', '#F0DBCC'),
    _c('紫罗兰', 'Violet', '#5252A0'),
    _c('古铜色', 'Bronze', '#8C6A3B'),
    _c('金属灰', 'Metal Gray', '#8A8F98'),
    _c('银蓝双色', 'Dual Color (Sliver&Blue)', '#9099A6'),
    _c('黑红双色', 'Dual Color (Black & Red)', '#9099A6'),
    _c('黑绿双色', 'Dual Color (Black & Green)', '#9099A6'),
    _c('金红紫三色', 'Tri-Color (Gold & Red & Purple)', '#9099A6'),
    _c('金银铜三色', 'Tri-Color (Gold & Silver & Copper)', '#9099A6'),
    _c('黑金紫三色', 'Tri-Color (Black & Gold & Purple)', '#9099A6'),
    _c('冷白', 'Cool White', '#ECECEC'),
    _c('珍珠白', 'Pearl White', '#F3F1E8'),
    _c('木槿紫', 'Hibiscus Purple', '#8E5EA2'),
    _c('玫瑰粉', 'Rose Pink', '#F2789F'),
    _c('奶油粉', 'Cream Pink', '#FBE3E6'),
    _c('奶油黄', 'Cream Yellow', '#FFF0B5'),
    _c('晴空蓝', 'Clear Sky Blue', '#1E88E5'),
    _c('竹绿', 'Bamboo Green', '#6A9B3C'),
    _c('绿松石绿', 'Turquoise Green', '#38CAB7'),
    _c('香槟粉', 'Champagne Pink', '#F2DCD2'),
    _c('奶蓝', 'Milk Blue', '#BFD9E8'),

]


# PLA Silk+ 彩虹  (7 色)

FLASHFORGE_PLA_SILK_RAINBOW: list[dict] = [
    _c('金属彩虹', 'Metal Rainbow', '#9099A6'),
    _c('金红双色', 'Gold&Red', '#9099A6'),
    _c('银蓝', 'Sliver&Blue', '#9099A6'),
    _c('梦幻三色', 'Dreamy Trio', '#9099A6'),
    _c('糖果色', 'Candy', '#9099A6'),
    _c('马卡龙', 'Macaron', '#9099A6'),
    _c('梦幻粉彩', 'Dreamy Pastel', '#9099A6'),

]


# PLA Silk+ 双色  (4 色)

FLASHFORGE_PLA_SILK_DUAL: list[dict] = [
    _c('蓝玫双色', 'Blue&Rose', '#9099A6'),
    _c('粉黄双色', 'Pink&Yellow', '#9099A6'),
    _c('蓝绿双色', 'Blue&Green', '#9099A6'),
    _c('银蓝', 'Sliver&Blue', '#9099A6'),

]


# PLA-CF  (7 色)

FLASHFORGE_PLA_CF: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),
    _c('午夜蓝', 'Midnight Blue', '#1B2A4A'),
    _c('玛萨拉红', 'Marsala', '#7E2B3A'),
    _c('藕粉色', 'Dusty Pink', '#D8A7A0'),
    _c('航海蓝', 'Sailor Blue', '#1F4E79'),
    _c('鸢尾紫', 'Iris Purple', '#5A4E9E'),
    _c('火山岩灰', 'Volcanic Rock Gray', '#4E4B48'),

]


# ABS Basic  (3 色)

FLASHFORGE_ABS_BASIC: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),
    _c('白色', 'White', '#E5E5E5'),
    _c('钛烧色', 'Burnt Titanium', '#9099A6'),

]


# ABS Pro  (1 色)

FLASHFORGE_ABS_PRO: list[dict] = [
    _c('宝石红', 'Ruby Red', '#C2183C'),

]


# ASA  (14 色)

FLASHFORGE_ASA: list[dict] = [
    _c('本色', 'Natural', '#363638'),
    _c('蓝色', 'Blue', '#2239A7'),
    _c('闪粉白', 'Sparkle White', '#EC407A'),
    _c('闪粉蓝', 'Sparkle Blue', '#EC407A'),
    _c('闪粉墨绿', 'Sparkle Black Green', '#EC407A'),
    _c('黄绿', 'Yellow Green', '#87F196'),
    _c('天空蓝', 'Sky Blue', '#3EA6DC'),
    _c('铁灰', 'Iron Gray', '#5A5A5A'),
    _c('闪粉天蓝', 'Sparkle Sky Blue', '#EC407A'),
    _c('闪粉黑', 'Sparkle Black', '#EC407A'),
    _c('黑色', 'Black', '#1C1C1C'),
    _c('白色', 'White', '#E5E5E5'),
    _c('交通红', 'Traffic Red', '#E43226'),
    _c('多色钛烧', 'Multicolor Burnt Titanium', '#9099A6'),

]


# ASA-CF  (3 色)

FLASHFORGE_ASA_CF: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),
    _c('午夜蓝', 'Midnight Blue', '#1B2A4A'),
    _c('玛萨拉红', 'Marsala', '#7E2B3A'),

]


# PET-CF  (1 色)

FLASHFORGE_PET_CF: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),

]


# PET-GF  (1 色)

FLASHFORGE_PET_GF: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),

]


# PETG-CF  (8 色)

FLASHFORGE_PETG_CF: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),
    _c('玛萨拉红', 'Marsala', '#7E2B3A'),
    _c('航海蓝', 'Sailor Blue', '#1F4E79'),
    _c('鸢尾紫', 'Iris Purple', '#5A4E9E'),
    _c('藕粉色', 'Dusty Pink', '#D8A7A0'),
    _c('草绿色', 'Grass Green', '#76FB85'),
    _c('午夜蓝', 'Midnight Blue', '#1B2A4A'),
    _c('火山岩灰', 'Volcanic Rock Gray', '#4E4B48'),

]


# ---- Nature3d / 造物新材料（金华 Nature 3D，淘宝官方店 SKU 提色，近似值）----

# PLA Pro  (15 色)

NATURE3D_PLA_PRO: list[dict] = [
    _c('玫红色', '玫红色', '#C45A7C'),
    _c('银色', '银色', '#B9BABF'),
    _c('本色', '本色', '#363638'),
    _c('棕色', '棕色', '#7C4628'),
    _c('紫色', '紫色', '#B131A5'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('灰色', '灰色', '#888888'),
    _c('红色', '红色', '#D0070D'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('粉色', '粉色', '#FC737F'),
    _c('金色', '金色', '#D8AB62'),
    _c('绿色', '绿色', '#1E8436'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('蓝色', '蓝色', '#2239A7'),

]


# PLA Lite  (20 色)

NATURE3D_PLA_LITE: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('红色', '红色', '#D0070D'),
    _c('紫色', '紫色', '#B131A5'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('绿色', '绿色', '#1E8436'),
    _c('粉色', '粉色', '#FC737F'),
    _c('浅黄', '浅黄', '#E2DB91'),
    _c('冰蓝', '冰蓝', '#9CC8E2'),
    _c('薄荷绿', '薄荷绿', '#C4CF84'),
    _c('奶黄', '奶黄', '#E0DFC0'),
    _c('灰色', '灰色', '#888888'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('淡青', '淡青', '#A8DCD8'),
    _c('冷灰', '冷灰', '#8F9296'),
    _c('午夜蓝', '午夜蓝', '#1B2A4A'),
    _c('珊瑚红', '珊瑚红', '#FF6F61'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('焦橙', '焦橙', '#D2551F'),

]


# PLA 哑光  (28 色)

NATURE3D_PLA_MATTE: list[dict] = [
    _c('薄荷绿', '薄荷绿', '#C4CF84'),
    _c('冰蓝', '冰蓝', '#9CC8E2'),
    _c('淡青', '淡青', '#A8DCD8'),
    _c('紫罗兰', '紫罗兰', '#5252A0'),
    _c('绯红', '绯红', '#C2183C'),
    _c('蜂蜜色', '蜂蜜色', '#E0A52B'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('红色', '红色', '#D0070D'),
    _c('灰色', '灰色', '#888888'),
    _c('白色', '白色', '#E5E5E5'),
    _c('橘红', '橘红', '#FF5A1F'),
    _c('蓝绿', '蓝绿', '#66E3DE'),
    _c('冷灰', '冷灰', '#8F9296'),
    _c('马卡龙粉', '马卡龙粉', '#F8C8D8'),
    _c('芒果黄', '芒果黄', '#E8C84B'),
    _c('奶黄', '奶黄', '#E0DFC0'),
    _c('苹果绿', '苹果绿', '#A9CD48'),
    _c('珊瑚红', '珊瑚红', '#FF6F61'),
    _c('桃红', '桃红', '#D32F2F'),
    _c('午夜蓝', '午夜蓝', '#1B2A4A'),
    _c('灰蓝', '灰蓝', '#778491'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('灰粉', '灰粉', '#D8B4B8'),
    _c('绿色', '绿色', '#1E8436'),
    _c('橙子沙冰', '橙子沙冰', '#FFB07C'),
    _c('浅粉', '浅粉', '#F8C8D8'),
    _c('苹果红', '苹果红', '#D0342C'),
    _c('浅黄', '浅黄', '#E2DB91'),

]


# PLA 丝绸  (28 色)

NATURE3D_PLA_SILK: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('金色', '金色', '#D8AB62'),
    _c('亮金色', '亮金色', '#FFD906'),
    _c('绿色', '绿色', '#1E8436'),
    _c('浅绿色', '浅绿色', '#A5D66A'),
    _c('粉色', '粉色', '#FC737F'),
    _c('红色', '红色', '#D0070D'),
    _c('银色', '银色', '#B9BABF'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('咖啡色', '咖啡色', '#7F4434'),
    _c('紫罗兰', '紫罗兰', '#5252A0'),
    _c('金属灰', '金属灰', '#8A8F98'),
    _c('古铜色', '古铜色', '#8C6A3B'),
    _c('青铜色', '青铜色', '#4F482F'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('清水蓝', '清水蓝', '#6FD3E8'),
    _c('珍珠白', '珍珠白', '#F3F1E8'),
    _c('香槟粉', '香槟粉', '#F2DCD2'),
    _c('盐奶蓝', '盐奶蓝', '#BFD9E8'),
    _c('松石绿', '松石绿', '#47C2C7'),
    _c('箬竹', '箬竹', '#5F8A3E'),
    _c('奶油黄', '奶油黄', '#FFF0B5'),
    _c('奶油粉', '奶油粉', '#FBE3E6'),
    _c('玫瑰粉', '玫瑰粉', '#F2789F'),
    _c('槿紫', '槿紫', '#8E5EA2'),
    _c('冷白', '冷白', '#ECECEC'),

]


# PLA 彩虹  (7 色)

NATURE3D_PLA_RAINBOW: list[dict] = [
    _c('彩虹蜡笔', '彩虹蜡笔', '#9099A6'),
    _c('彩虹珊瑚', '彩虹珊瑚', '#9099A6'),
    _c('马卡龙', '马卡龙', '#9099A6'),
    _c('彩虹', '彩虹', '#9099A6'),
    _c('金属彩虹', '金属彩虹', '#9099A6'),
    _c('彩虹糖', '彩虹糖', '#9099A6'),
    _c('夏日梦境', '夏日梦境', '#9099A6'),

]


# PLA 渐变  (22 色)

NATURE3D_PLA_GRADIENT: list[dict] = [
    _c('深海', '深海', '#9099A6'),
    _c('极光', '极光', '#9099A6'),
    _c('夕阳', '夕阳', '#9099A6'),
    _c('夕夏', '夕夏', '#9099A6'),
    _c('棒棒糖粉', '棒棒糖粉', '#9099A6'),
    _c('棒棒糖紫', '棒棒糖紫', '#9099A6'),
    _c('棒棒糖蓝', '棒棒糖蓝', '#9099A6'),
    _c('橙绿渐变', '橙绿渐变', '#9099A6'),
    _c('黄蓝渐变', '黄蓝渐变', '#9099A6'),
    _c('蓝粉渐变', '蓝粉渐变', '#9099A6'),
    _c('海盐渐变', '海盐渐变', '#9099A6'),
    _c('霞粉贝渐变', '霞粉贝渐变', '#9099A6'),
    _c('暮色幻想', '暮色幻想', '#D58875'),
    _c('蓝银渐变', '蓝银渐变', '#9099A6'),
    _c('渐变4号', '渐变4号', '#9099A6'),
    _c('渐变5号', '渐变5号', '#9099A6'),
    _c('渐变6号', '渐变6号', '#9099A6'),
    _c('渐变7号', '渐变7号', '#9099A6'),
    _c('彩虹', '彩虹', '#9099A6'),
    _c('梦幻渐变棉花糖', '梦幻渐变棉花糖', '#9099A6'),
    _c('彩虹糖果', '彩虹糖果', '#9099A6'),
    _c('彩虹夏日梦境', '彩虹夏日梦境', '#9099A6'),

]


# PLA 闪电  (1 色)

NATURE3D_PLA_LIGHTNING: list[dict] = [
    _c('彩色闪电', '彩色闪电', '#9099A6'),

]


# PLA 大理石  (2 色)

NATURE3D_PLA_MARBLE: list[dict] = [
    _c('本色', '本色', '#363638'),
    _c('棕色', '棕色', '#7C4628'),

]


# PLA 木质  (2 色)

NATURE3D_PLA_WOOD: list[dict] = [
    _c('深木', '深木', '#8B5A2B'),
    _c('浅木', '浅木', '#C19A6B'),

]


# PLA-CF  (6 色)

NATURE3D_PLA_CF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('脏粉', '脏粉', '#C89B94'),
    _c('鸢尾紫色', '鸢尾紫色', '#7B1FA2'),
    _c('火山岩灰', '火山岩灰', '#4E4B48'),
    _c('草绿', '草绿', '#7FD530'),
    _c('水手蓝色', '水手蓝色', '#1E88E5'),

]


# PLA 柔性  (7 色)

NATURE3D_PLA_FLEX: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('红色', '红色', '#D0070D'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('绿色', '绿色', '#1E8436'),
    _c('本色', '本色', '#363638'),

]


# ASA 闪光  (16 色)

NATURE3D_ASA_SPARKLE: list[dict] = [
    _c('象牙白', '象牙白', '#DAD8D5'),
    _c('亮橙', '亮橙', '#FF8C1A'),
    _c('高雅青', '高雅青', '#2E8B8B'),
    _c('风暴灰', '风暴灰', '#6E7276'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('紫色', '紫色', '#B131A5'),
    _c('红色', '红色', '#D0070D'),
    _c('天空蓝', '天空蓝', '#3EA6DC'),
    _c('粉色', '粉色', '#FC737F'),
    _c('糖果绿', '糖果绿', '#A8D96A'),
    _c('樱桃红', '樱桃红', '#D03E41'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('薰衣草', '薰衣草', '#B57EDC'),
    _c('珊瑚红', '珊瑚红', '#FF6F61'),
    _c('墨绿', '墨绿', '#004E3E'),
    _c('阴云灰', '阴云灰', '#8A8D91'),

]


# ABS Pro 闪光  (17 色)

NATURE3D_ABS_PRO_SPARKLE: list[dict] = [
    _c('紫色', '紫色', '#B131A5'),
    _c('黑曜石黑', '黑曜石黑', '#17171A'),
    _c('樱桃红', '樱桃红', '#D03E41'),
    _c('旧铜', '旧铜', '#7A5C3E'),
    _c('长春花', '长春花', '#7B8FE0'),
    _c('高雅青', '高雅青', '#2E8B8B'),
    _c('暗橙', '暗橙', '#C46210'),
    _c('亮橙', '亮橙', '#FF8C1A'),
    _c('风暴灰', '风暴灰', '#6E7276'),
    _c('糖果绿', '糖果绿', '#A8D96A'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('柠檬黄', '柠檬黄', '#BCBF3D'),
    _c('象牙白', '象牙白', '#DAD8D5'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('紫玫红', '紫玫红', '#B03060'),
    _c('珊瑚红', '珊瑚红', '#FF6F61'),
    _c('暗金', '暗金', '#8C6A2F'),

]


# PETG-CF  (6 色)

NATURE3D_PETG_CF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('脏粉', '脏粉', '#C89B94'),
    _c('鸢尾紫色', '鸢尾紫色', '#7B1FA2'),
    _c('火山岩灰', '火山岩灰', '#4E4B48'),
    _c('草绿', '草绿', '#7FD530'),
    _c('水手蓝色', '水手蓝色', '#1E88E5'),

]


# HS PLA  (1 色)

NATURE3D_HS_PLA: list[dict] = [
    _c('本色', '本色', '#363638'),

]


# HS ABS  (1 色)

NATURE3D_HS_ABS: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),

]


# HS PETG  (9 色)

NATURE3D_HS_PETG: list[dict] = [
    _c('紫色', '紫色', '#B131A5'),
    _c('绿色', '绿色', '#1E8436'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('交通红', '交通红', '#E43226'),
    _c('灰色', '灰色', '#888888'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('本色', '本色', '#363638'),
    _c('白色', '白色', '#E5E5E5'),

]


# ---- 卓普 CC3D（杭州卓普新材料，淘宝官方店 SKU 提色，近似值）----

# PLA  (53 色)

ZHUOPU_PLA: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('玉石白', '玉石白', '#D4D5C5'),
    _c('纯白色', '纯白色', '#FFFFFF'),
    _c('乳白色', '乳白色', '#F5F2E8'),
    _c('雪白', '雪白', '#FBFBFB'),
    _c('本色', '本色', '#363638'),
    _c('透明', '透明', '#DDE6EA'),
    _c('金色', '金色', '#D8AB62'),
    _c('终结者灰', '终结者灰', '#4A4E52'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('黑古银', '黑古银', '#3C4045'),
    _c('透明黑', '透明黑', '#4A4A4A'),
    _c('暗灰', '暗灰', '#5A5A5A'),
    _c('灰色', '灰色', '#888888'),
    _c('黑灰', '黑灰', '#3A3A3A'),
    _c('浅灰色', '浅灰色', '#C6C6C6'),
    _c('石板灰', '石板灰', '#6E7276'),
    _c('粉色', '粉色', '#FC737F'),
    _c('深紫', '深紫', '#4A148C'),
    _c('透明绿', '透明绿', '#A8D8B0'),
    _c('绿色', '绿色', '#1E8436'),
    _c('亮绿色', '亮绿色', '#7CB342'),
    _c('军绿色', '军绿色', '#788142'),
    _c('青色', '青色', '#41E9B7'),
    _c('深青', '深青', '#116062'),
    _c('水蓝', '水蓝', '#C3D5DD'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('冰蓝', '冰蓝', '#9CC8E2'),
    _c('亮蓝', '亮蓝', '#2196F3'),
    _c('深宝蓝', '深宝蓝', '#123C78'),
    _c('肉色', '肉色', '#F0DBCC'),
    _c('皮肤色', '皮肤色', '#E8C39E'),
    _c('红色', '红色', '#D0070D'),
    _c('酒红色', '酒红色', '#5F261E'),
    _c('国旗红', '国旗红', '#D0021B'),
    _c('玫红', '玫红', '#D64A6A'),
    _c('橘色', '橘色', '#FD641F'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('橙黄', '橙黄', '#FE9112'),
    _c('亮黄', '亮黄', '#FFEE58'),
    _c('暖黄', '暖黄', '#C7A440'),
    _c('土黄', '土黄', '#C9A227'),
    _c('薰衣草紫', '薰衣草紫', '#886CBF'),
    _c('钢青', '钢青', '#3E6E7E'),
    _c('咖啡色', '咖啡色', '#7F4434'),
    _c('棕色', '棕色', '#7C4628'),
    _c('巧克力棕', '巧克力棕', '#6D4C41'),
    _c('皮革棕', '皮革棕', '#8B5A2B'),
    _c('彩虹', '彩虹', '#9099A6'),
    _c('酒红', '酒红', '#5F1413'),
    _c('品红', '品红', '#E93096'),
    _c('透明红', '透明红', '#E890A0'),
    _c('樱桃红', '樱桃红', '#D03E41'),

]



# PLA Basic  (42 色)

ZHUOPU_PLA_BASIC: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('暖白', '暖白', '#F7F3EA'),
    _c('白色', '白色', '#E5E5E5'),
    _c('荧光白', '荧光白', '#FFFFFF'),
    _c('肉色', '肉色', '#F0DBCC'),
    _c('皮肤色', '皮肤色', '#E8C39E'),
    _c('灰色', '灰色', '#888888'),
    _c('浅灰', '浅灰', '#D2D8D8'),
    _c('木色', '木色', '#B98E5E'),
    _c('枫木', '枫木', '#D9A066'),
    _c('淡橙', '淡橙', '#F57C00'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('淡覆盆子', '淡覆盆子', '#E5739B'),
    _c('红色', '红色', '#D0070D'),
    _c('品红', '品红', '#E93096'),
    _c('覆盆子', '覆盆子', '#C2185B'),
    _c('酒红', '酒红', '#5F1413'),
    _c('浅棕色', '浅棕色', '#C17D3D'),
    _c('棕色', '棕色', '#7C4628'),
    _c('巧克力', '巧克力', '#4C210B'),
    _c('淡蓝', '淡蓝', '#A8C8E0'),
    _c('水蓝', '水蓝', '#C3D5DD'),
    _c('亮蓝', '亮蓝', '#2196F3'),
    _c('海军蓝', '海军蓝', '#2C3A4D'),
    _c('银色', '银色', '#B9BABF'),
    _c('淡粉', '淡粉', '#EC407A'),
    _c('新粉', '新粉', '#EC407A'),
    _c('荧光黄', '荧光黄', '#EEFD04'),
    _c('淡黄', '淡黄', '#FFF6A9'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('荧光绿', '荧光绿', '#71F03F'),
    _c('苹果绿', '苹果绿', '#A9CD48'),
    _c('淡绿', '淡绿', '#388E3C'),
    _c('绿色', '绿色', '#1E8436'),
    _c('草绿', '草绿', '#7FD530'),
    _c('橄榄绿', '橄榄绿', '#3A4A2C'),
    _c('军绿', '军绿', '#343D1A'),
    _c('淡紫', '淡紫', '#D9D7DD'),
    _c('紫色', '紫色', '#B131A5'),
    _c('紫李', '紫李', '#6A1B9A'),
    _c('青色', '青色', '#41E9B7'),
    _c('大理石', '大理石', '#CFCED7'),

]



# PLA MAX  (42 色)

ZHUOPU_PLA_MAX: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('黑古银', '黑古银', '#3C4045'),
    _c('大理石', '大理石', '#CFCED7'),
    _c('白色', '白色', '#E5E5E5'),
    _c('雪白', '雪白', '#FBFBFB'),
    _c('骨色', '骨色', '#E8DEC9'),
    _c('仿古金', '仿古金', '#B08D3F'),
    _c('红色', '红色', '#D0070D'),
    _c('美旗红', '美旗红', '#CE1126'),
    _c('樱桃红', '樱桃红', '#D03E41'),
    _c('砖红', '砖红', '#D32F2F'),
    _c('银灰', '银灰', '#B8BCC2'),
    _c('钢灰', '钢灰', '#7A7F85'),
    _c('蓝灰', '蓝灰', '#6E8CA0'),
    _c('木色', '木色', '#B98E5E'),
    _c('石板灰', '石板灰', '#6E7276'),
    _c('浅灰', '浅灰', '#D2D8D8'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('天蓝', '天蓝', '#3EA6DC'),
    _c('海洋蓝', '海洋蓝', '#1F6FB2'),
    _c('海军蓝', '海军蓝', '#2C3A4D'),
    _c('美旗蓝', '美旗蓝', '#2B5C9B'),
    _c('藏蓝', '藏蓝', '#26385E'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('柠檬黄', '柠檬黄', '#BCBF3D'),
    _c('荧光黄', '荧光黄', '#EEFD04'),
    _c('绿松石', '绿松石', '#2E9B9B'),
    _c('经典绿', '经典绿', '#2E7D32'),
    _c('翡翠绿', '翡翠绿', '#2E8B57'),
    _c('橄榄绿', '橄榄绿', '#3A4A2C'),
    _c('草绿', '草绿', '#7FD530'),
    _c('军绿', '军绿', '#343D1A'),
    _c('荧光绿', '荧光绿', '#71F03F'),
    _c('酸橙绿', '酸橙绿', '#9CCC33'),
    _c('晚砂色', '晚砂色', '#C2A177'),
    _c('粉色', '粉色', '#FC737F'),
    _c('橘色', '橘色', '#FD641F'),
    _c('巧克力色', '巧克力色', '#503726'),
    _c('咖啡棕', '咖啡棕', '#6F4E37'),
    _c('紫色', '紫色', '#B131A5'),
    _c('深紫', '深紫', '#4A148C'),
    _c('沙褐色', '沙褐色', '#B0926A'),

]



# PLA 哑光  (7 色)

ZHUOPU_PLA_MATTE: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('绿色', '绿色', '#1E8436'),
    _c('灰色', '灰色', '#888888'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('红色', '红色', '#D0070D'),
    _c('蓝色', '蓝色', '#2239A7'),

]



# PLA 丝绸  (43 色)

ZHUOPU_PLA_SILK: list[dict] = [
    _c('金属金', '金属金', '#D4AF37'),
    _c('黄金', '黄金', '#FFD700'),
    _c('白金', '白金', '#FFFFFF'),
    _c('土金', '土金', '#C9A227'),
    _c('金黄色', '金黄色', '#FFC107'),
    _c('亮黄', '亮黄', '#FFEE58'),
    _c('银色', '银色', '#B9BABF'),
    _c('亮银', '亮银', '#D8DCE0'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('红铜', '红铜', '#D32F2F'),
    _c('紫铜', '紫铜', '#8E5A3B'),
    _c('粉色', '粉色', '#FC737F'),
    _c('玫红', '玫红', '#D64A6A'),
    _c('紫红', '紫红', '#B03060'),
    _c('葡萄紫', '葡萄紫', '#D7A2E3'),
    _c('紫色', '紫色', '#B131A5'),
    _c('深紫', '深紫', '#4A148C'),
    _c('橘色', '橘色', '#FD641F'),
    _c('红色', '红色', '#D0070D'),
    _c('深玫瑰金', '深玫瑰金', '#B76E79'),
    _c('香槟金', '香槟金', '#E8D3A9'),
    _c('摩卡棕', '摩卡棕', '#6C4C36'),
    _c('铁灰', '铁灰', '#5A5A5A'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('银蓝', '银蓝', '#9BB7C4'),
    _c('搪瓷蓝', '搪瓷蓝', '#2E6E9E'),
    _c('皇家蓝', '皇家蓝', '#1F3F8F'),
    _c('宝石蓝', '宝石蓝', '#0166FE'),
    _c('水鸭蓝', '水鸭蓝', '#3B9C9C'),
    _c('绿色', '绿色', '#1E8436'),
    _c('荧光绿', '荧光绿', '#71F03F'),
    _c('灰绿', '灰绿', '#8A9A7B'),
    _c('翠绿', '翠绿', '#2E9E5B'),
    _c('森绿', '森绿', '#2F6B3C'),
    _c('深青', '深青', '#116062'),
    _c('青金', '青金', '#4F7C8A'),
    _c('青铜', '青铜', '#816D45'),
    _c('淡蓝', '淡蓝', '#A8C8E0'),
    _c('荧光蓝', '荧光蓝', '#00B0FF'),
    _c('桔色', '桔色', '#FF8C1A'),
    _c('粉紫', '粉紫', '#D8A0C8'),
    _c('彩虹', '彩虹', '#9099A6'),

]



# PLA 丝绸双色  (13 色)

ZHUOPU_PLA_SILK_DUO: list[dict] = [
    _c('双色蓝绿', '双色蓝绿', '#9099A6'),
    _c('双色黑金', '双色黑金', '#9099A6'),
    _c('双色黑绿', '双色黑绿', '#9099A6'),
    _c('双色黑红', '双色黑红', '#9099A6'),
    _c('双色红蓝', '双色红蓝', '#9099A6'),
    _c('双色红绿', '双色红绿', '#9099A6'),
    _c('双色红金', '双色红金', '#9099A6'),
    _c('双色金紫', '双色金紫', '#9099A6'),
    _c('双色紫蓝', '双色紫蓝', '#9099A6'),
    _c('双色绿黄', '双色绿黄', '#9099A6'),
    _c('三色黑红金', '三色黑红金', '#9099A6'),
    _c('三色红蓝绿', '三色红蓝绿', '#9099A6'),
    _c('三色蓝黄紫', '三色蓝黄紫', '#9099A6'),

]



# PLA 丝绸彩虹  (7 色)

ZHUOPU_PLA_SILK_RAINBOW: list[dict] = [
    _c('彩虹宇宙系', '彩虹宇宙系', '#9099A6'),
    _c('彩虹糖果系', '彩虹糖果系', '#9099A6'),
    _c('彩虹马卡龙系', '彩虹马卡龙系', '#9099A6'),
    _c('彩虹蓝色系', '彩虹蓝色系', '#9099A6'),
    _c('彩虹红色系', '彩虹红色系', '#9099A6'),
    _c('彩虹森林系', '彩虹森林系', '#9099A6'),
    _c('彩虹黄色系', '彩虹黄色系', '#9099A6'),

]



# PLA 高速丝绸  (5 色)

ZHUOPU_PLA_SILK_HS: list[dict] = [
    _c('黄金', '黄金', '#FFD700'),
    _c('银色', '银色', '#B9BABF'),
    _c('红色', '红色', '#D0070D'),
    _c('翠绿', '翠绿', '#2E9E5B'),
    _c('青金', '青金', '#4F7C8A'),

]



# PLA 金属  (5 色)

ZHUOPU_PLA_METAL: list[dict] = [
    _c('黄金', '黄金', '#FFD700'),
    _c('银色', '银色', '#B9BABF'),
    _c('紫铜', '紫铜', '#8E5A3B'),
    _c('青铜', '青铜', '#816D45'),
    _c('磨砂铜', '磨砂铜', '#A9714B'),

]



# PLA 彩虹  (1 色)

ZHUOPU_PLA_RAINBOW: list[dict] = [
    _c('彩虹', '彩虹', '#9099A6'),

]



# PLA 大理石  (3 色)

ZHUOPU_PLA_MARBLE: list[dict] = [
    _c('大理石', '大理石', '#CFCED7'),
    _c('米色大理石', '米色大理石', '#E3D9C6'),
    _c('灰大理石', '灰大理石', '#A9A6A1'),

]



# PLA 燃烧钛  (1 色)

ZHUOPU_PLA_BURNT_TI: list[dict] = [
    _c('燃烧钛', '燃烧钛', '#9099A6'),

]



# PLA 夜光  (3 色)

ZHUOPU_PLA_GLOW: list[dict] = [
    _c('夜光绿', '夜光绿', '#498B60'),
    _c('夜光蓝', '夜光蓝', '#52D5FE'),
    _c('夜光混色', '夜光混色', '#9099A6'),

]



# PLA 光变  (10 色)

ZHUOPU_PLA_UV: list[dict] = [
    _c('白变黑', '白变黑', '#9099A6'),
    _c('白变树莓红', '白变树莓红', '#9099A6'),
    _c('白变橄榄绿', '白变橄榄绿', '#9099A6'),
    _c('淡绿变墨绿', '淡绿变墨绿', '#9099A6'),
    _c('绿变暗红', '绿变暗红', '#9099A6'),
    _c('黄变绿', '黄变绿', '#9099A6'),
    _c('光变紫', '光变紫', '#9099A6'),
    _c('光变蓝', '光变蓝', '#9099A6'),
    _c('光变黄', '光变黄', '#9099A6'),
    _c('光变红', '光变红', '#9099A6'),

]



# PLA-CF  (1 色)

ZHUOPU_PLA_CF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]



# PLA-GF  (4 色)

ZHUOPU_PLA_GF: list[dict] = [
    _c('本色', '本色', '#363638'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('红色', '红色', '#D0070D'),
    _c('蓝色', '蓝色', '#2239A7'),

]



# PLA Rock  (7 色)

ZHUOPU_PLA_ROCK: list[dict] = [
    _c('虎斑岩', '虎斑岩', '#8A7B6B'),
    _c('花岗岩', '花岗岩', '#B4B5B5'),
    _c('角岩', '角岩', '#6E6A63'),
    _c('蓝片岩', '蓝片岩', '#5B7A8C'),
    _c('砂岩', '砂岩', '#C6B49A'),
    _c('石灰岩', '石灰岩', '#CFCAC2'),
    _c('石英岩', '石英岩', '#B9B3A8'),

]



# PLA-LW  (2 色)

ZHUOPU_PLA_LW: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),

]



# PETG  (45 色)

ZHUOPU_PETG: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('雪白色', '雪白色', '#D3CED4'),
    _c('金色', '金色', '#D8AB62'),
    _c('金属银', '金属银', '#B9BABF'),
    _c('黑蓝', '黑蓝', '#1C2E4A'),
    _c('米色', '米色', '#D8C9A8'),
    _c('杏色', '杏色', '#F0C98D'),
    _c('仿木色', '仿木色', '#C29A7F'),
    _c('透明', '透明', '#DDE6EA'),
    _c('透明蓝', '透明蓝', '#8FB8D8'),
    _c('透明粉', '透明粉', '#F0C0D0'),
    _c('透明红', '透明红', '#E890A0'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('邮箱红', '邮箱红', '#C1272D'),
    _c('红色', '红色', '#D0070D'),
    _c('深红', '深红', '#8C1017'),
    _c('紫红色', '紫红色', '#E730B6'),
    _c('桔色', '桔色', '#FF8C1A'),
    _c('荧光桔', '荧光桔', '#FF6D00'),
    _c('粉色', '粉色', '#FC737F'),
    _c('紫色', '紫色', '#B131A5'),
    _c('透明黄', '透明黄', '#F0E090'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('荧光黄', '荧光黄', '#EEFD04'),
    _c('暖黄', '暖黄', '#C7A440'),
    _c('灰色', '灰色', '#888888'),
    _c('深灰', '深灰', '#4A4A4A'),
    _c('大理石', '大理石', '#CFCED7'),
    _c('绿色', '绿色', '#1E8436'),
    _c('荧光绿', '荧光绿', '#71F03F'),
    _c('绿松石色', '绿松石色', '#40C4B0'),
    _c('薄荷绿', '薄荷绿', '#C4CF84'),
    _c('亮绿', '亮绿', '#ABE136'),
    _c('叶绿', '叶绿', '#4C8C2B'),
    _c('军绿', '军绿', '#343D1A'),
    _c('天蓝', '天蓝', '#3EA6DC'),
    _c('水蓝', '水蓝', '#C3D5DD'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('蓝灰', '蓝灰', '#6E8CA0'),
    _c('湖蓝', '湖蓝', '#2193E8'),
    _c('深蓝', '深蓝', '#1E88E5'),
    _c('土狼棕', '土狼棕', '#8B6B4A'),
    _c('棕色', '棕色', '#7C4628'),
    _c('火岩棕', '火岩棕', '#7A4B2A'),

]



# PETG 燃烧钛  (1 色)

ZHUOPU_PETG_BURNT_TI: list[dict] = [
    _c('燃烧钛', '燃烧钛', '#9099A6'),

]



# PETG 透光  (3 色)

ZHUOPU_PETG_TRANS: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('瓷白', '瓷白', '#F4F2EC'),

]



# TPU 95A  (4 色)

ZHUOPU_TPU_95A: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('灰色', '灰色', '#888888'),
    _c('肤色', '肤色', '#F0DBCC'),

]



# TPU 72D  (7 色)

ZHUOPU_TPU_72D: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('草绿色', '草绿色', '#76FB85'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('红色', '红色', '#D0070D'),
    _c('灰色', '灰色', '#888888'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('透明', '透明', '#DDE6EA'),

]



# TPU 90A  (2 色)

ZHUOPU_TPU_90A: list[dict] = [
    _c('白色', '白色', '#E5E5E5'),
    _c('黑色', '黑色', '#1C1C1C'),

]



# TPU 85A  (8 色)

ZHUOPU_TPU_85A: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('灰色', '灰色', '#888888'),
    _c('草绿色', '草绿色', '#76FB85'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('透明', '透明', '#DDE6EA'),
    _c('荧光绿', '荧光绿', '#71F03F'),
    _c('红色', '红色', '#D0070D'),

]


# ---- 点维 Dowell（洛阳点维电子科技，官网 Color 规格，英文色名译中文 / HEX 近似）----

# PLA  (14 色)

DOWELL_PLA: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('灰色', '灰色', '#888888'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('红色', '红色', '#D0070D'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('粉色', '粉色', '#FC737F'),
    _c('紫色', '紫色', '#B131A5'),
    _c('棕色', '棕色', '#7C4628'),
    _c('玄武岩灰', '玄武岩灰', '#5A5F63'),
    _c('绿色', '绿色', '#1E8436'),
    _c('肤色', '肤色', '#F0DBCC'),
    _c('深棕', '深棕', '#413421'),

]



# PLA 丝绸  (3 色)

DOWELL_PLA_SILK: list[dict] = [
    _c('丝绸金', '丝绸金', '#D4AF37'),
    _c('红铜', '红铜', '#B87333'),
    _c('银色', '银色', '#B9BABF'),

]



# PLA-CF  (1 色)

DOWELL_PLA_CF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]



# PLA 木质  (1 色)

DOWELL_PLA_WOOD: list[dict] = [
    _c('枫木色', '枫木色', '#BCA281'),

]



# ABS  (8 色)

DOWELL_ABS: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('灰色', '灰色', '#888888'),
    _c('红色', '红色', '#D0070D'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('绿色', '绿色', '#1E8436'),
    _c('黄色', '黄色', '#FEEC03'),

]



# ABS-GF  (2 色)

DOWELL_ABS_GF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),

]



# ABS-CF  (1 色)

DOWELL_ABS_CF: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),

]



# PETG  (18 色)

DOWELL_PETG: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#E5E5E5'),
    _c('灰色', '灰色', '#888888'),
    _c('军绿', '军绿', '#343D1A'),
    _c('红色', '红色', '#D0070D'),
    _c('透明', '透明', '#DDE6EA'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('黄色', '黄色', '#FEEC03'),
    _c('绿色', '绿色', '#1E8436'),
    _c('粉色', '粉色', '#FC737F'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('棕色', '棕色', '#7C4628'),
    _c('蜜桃粉白', '蜜桃粉白', '#F7D9CE'),
    _c('荧光橙', '荧光橙', '#FF6207'),
    _c('荧光绿', '荧光绿', '#71F03F'),
    _c('薄荷绿', '薄荷绿', '#C4CF84'),
    _c('深紫', '深紫', '#4A148C'),
    _c('玄武岩灰', '玄武岩灰', '#5A5F63'),

]



# PETG 哑光  (9 色)

DOWELL_PETG_MATTE: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('蓝色', '蓝色', '#2239A7'),
    _c('棕色', '棕色', '#7C4628'),
    _c('灰色', '灰色', '#888888'),
    _c('橄榄绿', '橄榄绿', '#3A4A2C'),
    _c('橙色', '橙色', '#FC6A17'),
    _c('粉色', '粉色', '#FC737F'),
    _c('白色', '白色', '#E5E5E5'),
    _c('黄色', '黄色', '#FEEC03'),

]


# PLA  (8 色)

RAISE3D_PLA: list[dict] = [
    _c('白色', 'White', '#F5F5F5'),
    _c('灰色', 'Grey / RAL 7000', '#78858B'),
    _c('黑色', 'Black / RAL 9011', '#1C1C1C'),
    _c('红色', 'Red / RAL 3028', '#CB3234'),
    _c('蓝色', 'Blue / RAL 5019', '#1B5583'),
    _c('艺术白', 'Art White', '#F0EDE4'),
    _c('黄色', 'Yellow / RAL 1026', '#FFFF00'),
    _c('橙色', 'Orange / RAL 2001', '#C93C20'),

]


# HS PLA  (7 色)

RAISE3D_HS_PLA: list[dict] = [
    _c('白色', 'White', '#E8E8E2'),
    _c('红色', 'Red / RAL 3028', '#CB3234'),
    _c('黑色', 'Black / RAL 9011', '#1C1C1C'),
    _c('灰色', 'Grey / RAL 7045', '#8E959A'),
    _c('蓝色', 'Blue / RAL 5010', '#0E294B'),
    _c('黄色', 'Yellow / RAL 1023', '#FAD201'),
    _c('橙色', 'Orange / RAL 2001', '#C93C20'),

]


# HS PLA Pro  (4 色)

RAISE3D_HS_PLA_PRO: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),
    _c('深蓝', 'Dark Blue / RAL 5003', '#1D1E7C'),
    _c('砖红', 'Brick Red / RAL 3009', '#642424'),
    _c('深绿', 'Dark Green / RAL 6005', '#0F4336'),

]


# ABS  (3 色)

RAISE3D_ABS: list[dict] = [
    _c('黑色', 'Black / RAL 9011', '#1C1C1C'),
    _c('灰色', 'Grey', '#8A8D8F'),
    _c('白色', 'White', '#F5F5F5'),

]


# HS ABS  (3 色)

RAISE3D_HS_ABS: list[dict] = [
    _c('本色', 'Natural', '#E8E0CE'),
    _c('黑色', 'Black', '#1C1C1C'),
    _c('灰色', 'Grey', '#8A8D8F'),

]


# ABS-CF  (1 色)

RAISE3D_ABS_CF: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),

]


# ASA  (1 色)

RAISE3D_ASA: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),

]


# PETG  (4 色)

RAISE3D_PETG: list[dict] = [
    _c('黑色', 'Black / RAL 9011', '#1C1C1C'),
    _c('蓝色', 'Blue / RAL 5002', '#20214F'),
    _c('红色', 'Red / RAL 2002', '#CC2A1E'),
    _c('白色', 'White', '#F5F5F5'),

]


# PETG-ESD  (1 色)

RAISE3D_PETG_ESD: list[dict] = [
    _c('黑色', 'Black / RAL 9011', '#1C1C1C'),

]


# PETG-CF  (1 色)

RAISE3D_PETG_CF: list[dict] = [
    _c('黑色', 'Black / RAL 9011', '#1C1C1C'),

]


# PET-CF  (1 色)

RAISE3D_PET_CF: list[dict] = [
    _c('黑色', 'Black / RAL 7021', '#23282B'),

]


# HS PET-CF  (1 色)

RAISE3D_HS_PET_CF: list[dict] = [
    _c('黑色', 'Black / RAL 9011', '#1C1C1C'),

]


# PET-GF  (4 色)

RAISE3D_PET_GF: list[dict] = [
    _c('黑色', 'Black / RAL 9017', '#222222'),
    _c('红色', 'Red / RAL 3024', '#F80018'),
    _c('橙色', 'Orange / RAL 2007', '#FFA420'),
    _c('灰色', 'Gray / RAL 7040', '#9DA3A6'),

]


# PET 支撑  (1 色)

RAISE3D_PET_SUPPORT: list[dict] = [
    _c('本色', 'Natural', '#EDEAE2'),

]


# PA12-CF  (1 色)

RAISE3D_PA12_CF: list[dict] = [
    _c('黑色', 'Black / RAL 9004', '#282828'),

]


# PA12-CF 支撑  (1 色)

RAISE3D_PA12_CF_SUPPORT: list[dict] = [
    _c('粉色', 'Pink / RAL 3015', '#E2B1B2'),

]


# PPA-CF  (1 色)

RAISE3D_PPA_CF: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),

]


# PPA-CF25  (1 色)

RAISE3D_PPA_CF25: list[dict] = [
    _c('黑色', 'Black', '#1C1C1C'),

]


# PPA-GF  (2 色)

RAISE3D_PPA_GF: list[dict] = [
    _c('本色', 'Natural / RAL 9016', '#E8E0CE'),
    _c('橙色', 'Orange / PMS 151', '#F47B20'),

]


# PPA-GF25  (1 色)

RAISE3D_PPA_GF25: list[dict] = [
    _c('白色', 'White', '#F5F5F5'),

]


# PPA 支撑  (1 色)

RAISE3D_PPA_SUPPORT: list[dict] = [
    _c('紫色', 'Purple / PMS 2635', '#A98FC7'),

]


# PPS-CF  (1 色)

RAISE3D_PPS_CF: list[dict] = [
    _c('黑色', 'Black / RAL 9011', '#1C1C1C'),

]


# PC  (3 色)

RAISE3D_PC: list[dict] = [
    _c('黑色', 'Black / RAL 9011', '#1C1C1C'),
    _c('白色', 'White', '#F5F5F5'),
    _c('透明', 'Transparent', '#DDE6EA'),

]


# TPU 95A  (3 色)

RAISE3D_TPU_95A: list[dict] = [
    _c('本色', 'Natural', '#E6E0D4'),
    _c('黑色', 'Black / RAL 9011', '#1C1C1C'),
    _c('白色', 'White', '#F5F5F5'),

]


# PVA+  (1 色)

RAISE3D_PVA: list[dict] = [
    _c('本色', 'Natural', '#EDEAE0'),

]


# PLA+  (22 色)

FULLJOY_PLAP: list[dict] = [
    _c('曜石黑', '曜石黑', '#1C1C1C'),
    _c('米白色', '米白色', '#F5F0E6'),
    _c('柠檬黄', '柠檬黄', '#FBE313'),
    _c('天蓝色', '天蓝色', '#6FB7E8'),
    _c('森林绿', '森林绿', '#2E7D32'),
    _c('中国红', '中国红', '#C8102E'),
    _c('机甲灰', '机甲灰', '#6E7073'),
    _c('橙黄色', '橙黄色', '#F59B23'),
    _c('樱花粉', '樱花粉', '#F7C5D6'),
    _c('圣诞绿', '圣诞绿', '#1B7A43'),
    _c('古典灰', '古典灰', '#9E9E9E'),
    _c('咖啡色', '咖啡色', '#6F4E37'),
    _c('玉石白', '玉石白', '#F2EFE6'),
    _c('竹子绿', '竹子绿', '#5B8C3E'),
    _c('橘橙色', '橘橙色', '#F26C21'),
    _c('鸢尾花紫', '鸢尾花紫', '#7A5FAE'),
    _c('长春花蓝', '长春花蓝', '#6B7FD7'),
    _c('宝石蓝', '宝石蓝', '#2E5C9E'),
    _c('肤色', '肤色', '#E8C0A8'),
    _c('钴蓝色', '钴蓝色', '#2A5CA8'),
    _c('蒂芙尼蓝', '蒂芙尼蓝', '#81D8D0'),
    _c('桃红色', '桃红色', '#F58FA3'),

]


# PLA 哑光艺术家  (16 色)

FULLJOY_PLA_MATTEART: list[dict] = [
    _c('芭乐绿', '芭乐绿', '#8DB600'),
    _c('复荷紫', '复荷紫', '#9B6FB0'),
    _c('汉麻色', '汉麻色', '#D8C9A0'),
    _c('茄紫色', '茄紫色', '#7A4B8C'),
    _c('橘柚色', '橘柚色', '#F2A03D'),
    _c('孔雀绿', '孔雀绿', '#0F9B8E'),
    _c('珊瑚粉', '珊瑚粉', '#F58CA0'),
    _c('落日橙', '落日橙', '#F26D21'),
    _c('蜜桃杏粉', '蜜桃杏粉', '#F7C6C0'),
    _c('抹茶绿', '抹茶绿', '#A8C66C'),
    _c('珊瑚橙', '珊瑚橙', '#F76F4D'),
    _c('奶茶棕', '奶茶棕', '#C9A87C'),
    _c('浅雾青蓝', '浅雾青蓝', '#A9C7D0'),
    _c('巧克力', '巧克力', '#5A3A22'),
    _c('铜青色', '铜青色', '#5E8B7E'),
    _c('棕绿色', '棕绿色', '#6B7A3A'),

]


# PLA 哑光  (12 色)

FULLJOY_PLA_MATTE: list[dict] = [
    _c('哑光黑', '哑光黑', '#2A2A2A'),
    _c('哑光白', '哑光白', '#F2F2F2'),
    _c('哑光灰', '哑光灰', '#9E9E9E'),
    _c('哑光黄', '哑光黄', '#F5E313'),
    _c('哑光薄荷绿', '哑光薄荷绿', '#A8E0C0'),
    _c('哑光丁香紫', '哑光丁香紫', '#C9A9D4'),
    _c('哑光肤色', '哑光肤色', '#E8C0A8'),
    _c('哑光海军蓝', '哑光海军蓝', '#2A4D8F'),
    _c('哑光浅卡其色', '哑光浅卡其色', '#D8C9A0'),
    _c('哑光沙漠黄', '哑光沙漠黄', '#E8C66C'),
    _c('哑光樱花粉', '哑光樱花粉', '#F7C5D6'),
    _c('哑光中国红', '哑光中国红', '#C8102E'),

]


# PLA 木质  (4 色)

FULLJOY_PLA_WOOD: list[dict] = [
    _c('黑胡桃', '黑胡桃', '#5A3A22'),
    _c('经典桦木', '经典桦木', '#E3C9A0'),
    _c('枫木色', '枫木色', '#E8C99A'),
    _c('陶土褐', '陶土褐', '#B5651D'),

]


# PLA+ 丝绸  (18 色)

FULLJOY_PLAP_SILK: list[dict] = [
    _c('铠甲丝绸金', '铠甲丝绸金', '#C9A227'),
    _c('铂彩丝绸金', '铂彩丝绸金', '#D4AF37'),
    _c('闪电丝绸银', '闪电丝绸银', '#C9CDD2'),
    _c('古典丝绸铜', '古典丝绸铜', '#B87333'),
    _c('丝绸珍珠白', '丝绸珍珠白', '#F5F0E6'),
    _c('丝绸蓝', '丝绸蓝', '#4A7FC0'),
    _c('丝绸黑', '丝绸黑', '#1C1C1C'),
    _c('丝绸咖啡金', '丝绸咖啡金', '#B5895A'),
    _c('丝绸红', '丝绸红', '#C8102E'),
    _c('红蓝', '红蓝', '#8A2B5A'),
    _c('粉金', '粉金', '#E8C8B0'),
    _c('粉蓝', '粉蓝', '#C0C8E8'),
    _c('红黑', '红黑', '#6A1B1B'),
    _c('红金', '红金', '#C9A227'),
    _c('蓝绿', '蓝绿', '#3FA9A0'),
    _c('紫金', '紫金', '#9B6FB0'),
    _c('红绿', '红绿', '#6A8A3A'),
    _c('黑紫', '黑紫', '#4A2A5A'),

]


# PLA 彩虹渐变  (3 色)

FULLJOY_PLA_RAINBOWGRAD: list[dict] = [
    _c('丝绸马卡龙彩虹', '丝绸马卡龙彩虹', '#F7C5D6'),
    _c('丝绸梦幻彩虹', '丝绸梦幻彩虹', '#C0A0E0'),
    _c('丝绸缤纷彩虹', '丝绸缤纷彩虹', '#F0A0C0'),

]


# PLA 水晶  (5 色)

FULLJOY_PLA_CRYS: list[dict] = [
    _c('冰川蓝', '冰川蓝', '#A9D8E8'),
    _c('罗兰紫', '罗兰紫', '#9B6FB0'),
    _c('珊瑚粉', '珊瑚粉', '#F58CA0'),
    _c('琥珀黄', '琥珀黄', '#F2B84B'),
    _c('珊瑚粉白', '珊瑚粉白', '#F8D0D8'),

]


# PLA 合金  (10 色)

FULLJOY_PLA_ALLOY: list[dict] = [
    _c('金属铜', '金属铜', '#B87333'),
    _c('玄铁绿', '玄铁绿', '#3A4A3A'),
    _c('炫彩银', '炫彩银', '#C9CDD2'),
    _c('午夜蓝', '午夜蓝', '#1C2A4A'),
    _c('珍珠白', '珍珠白', '#F5F0E6'),
    _c('金属钛', '金属钛', '#B0B4B8'),
    _c('古典铜', '古典铜', '#B87333'),
    _c('航空灰', '航空灰', '#7A7D82'),
    _c('璀璨玫红', '璀璨玫红', '#D0406A'),
    _c('香槟金', '香槟金', '#E8D3A9'),

]


# PLA+ 丝绸渐变  (13 色)

FULLJOY_PLAP_SILKGRAD: list[dict] = [
    _c('红蓝', '红蓝', '#8A2B5A'),
    _c('粉金', '粉金', '#E8C8B0'),
    _c('粉蓝', '粉蓝', '#C0C8E8'),
    _c('红黑', '红黑', '#6A1B1B'),
    _c('红金', '红金', '#C9A227'),
    _c('蓝绿', '蓝绿', '#3FA9A0'),
    _c('紫金', '紫金', '#9B6FB0'),
    _c('红绿', '红绿', '#6A8A3A'),
    _c('黄绿', '黄绿', '#A8C66C'),
    _c('黑紫', '黑紫', '#4A2A5A'),
    _c('蓝绿紫', '蓝绿紫', '#5A7FC0'),
    _c('红黄蓝', '红黄蓝', '#C0606A'),
    _c('黑金紫', '黑金紫', '#5A4A6A'),

]


# PLA+ 夜光  (2 色)

FULLJOY_PLAP_GLOW: list[dict] = [
    _c('璀璨绿', '璀璨绿', '#7CFC00'),
    _c('璀璨蓝', '璀璨蓝', '#4EC0FF'),

]


# PLA 大理石  (1 色)

FULLJOY_PLA_MARBLE: list[dict] = [
    _c('花岗岩', '花岗岩', '#8A8A8A'),

]


# PETG  (16 色)

FULLJOY_PETG: list[dict] = [
    _c('曜石黑', '曜石黑', '#1C1C1C'),
    _c('玉石白', '玉石白', '#F2EFE6'),
    _c('柠檬黄', '柠檬黄', '#FBE313'),
    _c('樱花粉', '樱花粉', '#F7C5D6'),
    _c('天蓝色', '天蓝色', '#6FB7E8'),
    _c('橘橙色', '橘橙色', '#F26C21'),
    _c('肤色', '肤色', '#E8C0A8'),
    _c('古典灰', '古典灰', '#9E9E9E'),
    _c('透明', '透明', '#DDE6EA'),
    _c('咖啡色', '咖啡色', '#6F4E37'),
    _c('红色', '红色', '#C8102E'),
    _c('古铜色', '古铜色', '#B87333'),
    _c('香槟金', '香槟金', '#E8D3A9'),
    _c('午夜蓝', '午夜蓝', '#1C2A4A'),
    _c('玄铁绿', '玄铁绿', '#3A4A3A'),
    _c('璀璨玫红', '璀璨玫红', '#D0406A'),

]


# ABS 基础  (7 色)

YITAILONG_ABS_BASE: list[dict] = [
    _c('米白色', '米白色', '#F0EAD8'),
    _c('米色', '米色', '#E8DCC0'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('本色', '本色', '#D9D4C5'),
    _c('前本色后黑色', '前本色后黑色', '#EDEAE0'),
    _c('乳白色', '乳白色', '#F5EFE0'),
    _c('白色', '白色', '#F5F5F5'),

]


# HIPS 基础  (1 色)

YITAILONG_HIPS_BASE: list[dict] = [
    _c('白色', '白色', '#F5F5F5'),

]


# PA 基础  (6 色)

YITAILONG_PA_BASE: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#F5F5F5'),
    _c('透明本色', '透明本色', '#DDE6EA'),
    _c('前本色后白色', '前本色后白色', '#EDEAE0'),
    _c('前白色后灰色', '前白色后灰色', '#D0D0D0'),
    _c('本色', '本色', '#D9D4C5'),

]


# PBT 基础  (3 色)

YITAILONG_PBT_BASE: list[dict] = [
    _c('米白色', '米白色', '#F0EAD8'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#F5F5F5'),

]


# PC 基础  (3 色)

YITAILONG_PC_BASE: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#F5F5F5'),
    _c('透明本色', '透明本色', '#DDE6EA'),

]


# PETG 基础  (20 色)

YITAILONG_PETG_BASE: list[dict] = [
    _c('白色', '白色', '#F5F5F5'),
    _c('哑光黑色', '哑光黑色', '#2A2A2A'),
    _c('透明本色', '透明本色', '#DDE6EA'),
    _c('金色闪点', '金色闪点', '#C9A227'),
    _c('透明金色闪点', '透明金色闪点', '#D4C28F'),
    _c('透明', '透明', '#DDE6EA'),
    _c('红色', '红色', '#C8102E'),
    _c('黄色', '黄色', '#FBE313'),
    _c('蓝色', '蓝色', '#2E5C9E'),
    _c('绿色', '绿色', '#2E7D32'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('透明天蓝色', '透明天蓝色', '#BFE0F0'),
    _c('透明绿', '透明绿', '#C8E8C8'),
    _c('透明黄', '透明黄', '#F5EBA8'),
    _c('橙色', '橙色', '#F59B23'),
    _c('哑光黑', '哑光黑', '#2A2A2A'),
    _c('钛金色', '钛金色', '#C9B98F'),
    _c('红蓝渐变', '红蓝渐变', '#8A2B5A'),
    _c('蓝绿过渡色', '蓝绿过渡色', '#3FA9A0'),
    _c('苹果绿', '苹果绿', '#7CB342'),

]


# PETG 夜光  (3 色)

YITAILONG_PETG_GLOW: list[dict] = [
    _c('夜光荧火', '夜光荧火', '#8FE36B'),
    _c('夜光绿', '夜光绿', '#8FE36B'),
    _c('夜光蓝', '夜光蓝', '#5AB8F0'),

]


# PLA 丝绸  (11 色)

YITAILONG_PLA_SILK: list[dict] = [
    _c('丝绸亮金', '丝绸亮金', '#D4AF37'),
    _c('丝绸金', '丝绸金', '#C9A227'),
    _c('丝绸红', '丝绸红', '#C8102E'),
    _c('丝绸红铜', '丝绸红铜', '#B87333'),
    _c('丝绸青铜', '丝绸青铜', '#8C7853'),
    _c('丝绸蓝', '丝绸蓝', '#4A7FC0'),
    _c('丝绸白', '丝绸白', '#F5F0E6'),
    _c('丝绸红黑', '丝绸红黑', '#6A1B1B'),
    _c('丝绸金红', '丝绸金红', '#C0405A'),
    _c('丝绸蓝红', '丝绸蓝红', '#7A4A6A'),
    _c('丝绸深蓝绿', '丝绸深蓝绿', '#1E7A6A'),

]


# PLA 基础  (22 色)

YITAILONG_PLA_BASE: list[dict] = [
    _c('白色', '白色', '#F5F5F5'),
    _c('红色', '红色', '#C8102E'),
    _c('黄色', '黄色', '#FBE313'),
    _c('绿色', '绿色', '#2E7D32'),
    _c('蓝色', '蓝色', '#2E5C9E'),
    _c('灰色', '灰色', '#9E9E9E'),
    _c('黑色', '黑色', '#1C1C1C'),
    _c('橙色', '橙色', '#F59B23'),
    _c('银色', '银色', '#C9CDD2'),
    _c('金色', '金色', '#D4AF37'),
    _c('粉红色', '粉红色', '#F58FA3'),
    _c('透明', '透明', '#DDE6EA'),
    _c('本色', '本色', '#D9D4C5'),
    _c('深灰色', '深灰色', '#5A5C5F'),
    _c('湖蓝色', '湖蓝色', '#2E6FB0'),
    _c('乳白色', '乳白色', '#F5EFE0'),
    _c('珍珠白色', '珍珠白色', '#F7F4EC'),
    _c('亮金色', '亮金色', '#E8D3A9'),
    _c('木色', '木色', '#C9A876'),
    _c('碳纤黑', '碳纤黑', '#2A2A2A'),
    _c('彩虹粉', '彩虹粉', '#F0A0C0'),
    _c('皮肤色', '皮肤色', '#E8C0A8'),

]


# PLA 夜光  (3 色)

YITAILONG_PLA_GLOW: list[dict] = [
    _c('夜光绿', '夜光绿', '#8FE36B'),
    _c('夜光蓝', '夜光蓝', '#5AB8F0'),
    _c('夜光紫', '夜光紫', '#B07CF0'),

]


# PMMA 基础  (2 色)

YITAILONG_PMMA_BASE: list[dict] = [
    _c('白色', '白色', '#F5F5F5'),
    _c('透明色', '透明色', '#DDE6EA'),

]


# POM 基础  (2 色)

YITAILONG_POM_BASE: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('本色', '本色', '#D9D4C5'),

]


# PP 基础  (5 色)

YITAILONG_PP_BASE: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('本色', '本色', '#D9D4C5'),
    _c('白色', '白色', '#F5F5F5'),
    _c('本色透明', '本色透明', '#DDE6EA'),
    _c('乳白色', '乳白色', '#F5EFE0'),

]


# TPU 基础  (18 色)

YITAILONG_TPU_BASE: list[dict] = [
    _c('黑色', '黑色', '#1C1C1C'),
    _c('白色', '白色', '#F5F5F5'),
    _c('红色', '红色', '#C8102E'),
    _c('黄色', '黄色', '#FBE313'),
    _c('蓝色', '蓝色', '#2E5C9E'),
    _c('本色', '本色', '#D9D4C5'),
    _c('橙色', '橙色', '#F59B23'),
    _c('绿色', '绿色', '#2E7D32'),
    _c('浅绿色', '浅绿色', '#8BC34A'),
    _c('粉红色', '粉红色', '#F58FA3'),
    _c('天蓝色', '天蓝色', '#6FB7E8'),
    _c('裸色', '裸色', '#E8D2C0'),
    _c('哑光黄', '哑光黄', '#F0E313'),
    _c('反光', '反光', '#C9CDD2'),
    _c('乳白色', '乳白色', '#F5EFE0'),
    _c('红黄', '红黄', '#E09030'),
    _c('金色', '金色', '#D4AF37'),
    _c('灰色', '灰色', '#9E9E9E'),

]


# TPU 夜光  (3 色)

YITAILONG_TPU_GLOW: list[dict] = [
    _c('夜光绿', '夜光绿', '#8FE36B'),
    _c('夜光黄', '夜光黄', '#D8F04B'),
    _c('夜光蓝', '夜光蓝', '#5AB8F0'),

]


# TPU 渐变  (7 色)

YITAILONG_TPU_GRAD: list[dict] = [
    _c('前白色后黑色', '前白色后黑色', '#C9C9C9'),
    _c('前白后黑渐变', '前白后黑渐变', '#C9C9C9'),
    _c('前绿后黑', '前绿后黑', '#3FA9A0'),
    _c('前橙后黑渐变', '前橙后黑渐变', '#D08A30'),
    _c('前红后黄渐变', '前红后黄渐变', '#E09030'),
    _c('前绿色后蓝色', '前绿色后蓝色', '#3FA9A0'),
    _c('前绿后蓝色', '前绿后蓝色', '#3FA9A0'),

]


# TPU 温变  (2 色)

YITAILONG_TPU_THERMO: list[dict] = [
    _c('温变色', '温变色', '#8C8C94'),
    _c('光变色', '光变色', '#8C8C94'),

]


# TPU 透明  (9 色)

YITAILONG_TPU_TRANS: list[dict] = [
    _c('透明本色', '透明本色', '#DDE6EA'),
    _c('透明浅蓝', '透明浅蓝', '#C8E8F5'),
    _c('透明黄', '透明黄', '#F5EBA8'),
    _c('透明粉红', '透明粉红', '#F5D0E0'),
    _c('透明红色', '透明红色', '#F0C0C0'),
    _c('透明玫瑰紫', '透明玫瑰紫', '#E0C0E8'),
    _c('透明红', '透明红', '#F0C0C0'),
    _c('透明天蓝色', '透明天蓝色', '#BFE0F0'),
    _c('透明', '透明', '#DDE6EA'),

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
        "ASA": ALLIZZ_ASA,
        "PETG Translucent": ALLIZZ_PETG_TRANSLUCENT,
        "ABS": ALLIZZ_ABS,
        "PETG HF": ALLIZZ_PETG_HF,
        "PLA Matte": ALLIZZ_PLA_MATTE,
        "PLA Silk": ALLIZZ_PLA_SILK,
        "TPU95A": ALLIZZ_TPU95A,
        "PLA Pro": ALLIZZ_PLA_PRO,
        "PLA Basic": ALLIZZ_PLA_BASIC,
        "PETG Metal": ALLIZZ_PETG_METAL,
        "PETG Shiny": ALLIZZ_PETG_SHINY,
        "PETG CF": ALLIZZ_PETG_CF,
        "PLA Translucent": ALLIZZ_PLA_TRANSLUCENT,
        "PLA Silk Multi": ALLIZZ_PLA_SILK_MULTI,
        "ABS Metal": ALLIZZ_ABS_METAL,
        "PA CF": ALLIZZ_PA_CF,
        "PETG Matte": ALLIZZ_PETG_MATTE,
        "PETG Transparent": ALLIZZ_PETG_TRANSPARENT,
    },
    "三绿 Sunlu": {
        "PLA Basic": SUNLU_PLA_BASIC,
        "PLA Matte": SUNLU_PLA_MATTE,
        "PLA Transparent": SUNLU_PLA_TRANSPARENT,
        "PLA Silk": SUNLU_PLA_SILK,
        "PETG": SUNLU_PETG,
        "PETG 2.0": SUNLU_PETG_2_0,
        "PETG Matte": SUNLU_PETG_MATTE,
        "TPU95A": SUNLU_TPU95A,
        "ABS": SUNLU_ABS,
        "ASA": SUNLU_ASA,
        "PA6-GF": SUNLU_PA6_GF,
    },
    "eSUN易生": {
        "PLA+": ESUN_PLA_PLUS,
        "PLA Basic": ESUN_PLA_BASIC,
        "PLA Matte": ESUN_PLA_MATTE,
        "PLA Silk": ESUN_PLA_SILK,
        "PLA Marble": ESUN_PLA_MARBLE,
        "PLA Rainbow": ESUN_PLA_RAINBOW,
        "PLA 魔幻双色": ESUN_PLA_MAGIC,
        "PLA 变色龙": ESUN_PLA_CHAMELEON,
        "PLA Wood": ESUN_PLA_WOOD,
        "PETG Basic": ESUN_PETG_BASIC,
        "PETG Matte": ESUN_PETG_MATTE,
        "PETG Transparent": ESUN_PETG_TRANSPARENT,
        "PETG+HS": ESUN_PETG_HS,
        "PETG 夜光": ESUN_PETG_GLOW,
        "PETG UV变色": ESUN_PETG_UV,
        "ABS": ESUN_ABS,
        "ABS+": ESUN_ABS_PLUS,
        "ABS-CF": ESUN_ABS_CF,
        "ASA+": ESUN_ASA_PLUS,
        "TPU95A": ESUN_TPU95A,
        "PVA": ESUN_PVA,
        "PA": ESUN_PA,
        "PA-CF": ESUN_PA_CF,
    },
    "Inslogic": {
        "PLA Pro": INSLOGIC_PLA_PRO,
        "PLA Matte": INSLOGIC_PLA_MATTE,
        "PLA Silk": INSLOGIC_PLA_SILK,
        "PETG Pro": INSLOGIC_PETG_PRO,
        "PETG 2.0": INSLOGIC_PETG_2_0,
        "PETG-CF": INSLOGIC_PETG_CF,
        "ABS": INSLOGIC_ABS,
        "TPU95A": INSLOGIC_TPU95A,
        "TPU90A": INSLOGIC_TPU90A,
        "PA6/66": INSLOGIC_PA6_66,
        "PA12-CF": INSLOGIC_PA12_CF,
    },
    "FusRock": {
        "PLA-Aero Pro": FUSROCK_PLA_AERO_PRO,
        "PETG-HF": FUSROCK_PETG_HF,
        "PETG-GF": FUSROCK_PETG_GF,
        "PETG-CF HF": FUSROCK_PETG_CF_HF,
        "PET-CF": FUSROCK_PET_CF,
        "PET-GF": FUSROCK_PET_GF,
        "ABS": FUSROCK_ABS,
        "ABS-HF": FUSROCK_ABS_HF,
        "ABS-GF": FUSROCK_ABS_GF,
        "NexABS-CF20": FUSROCK_NEXABS_CF20,
        "ASA": FUSROCK_ASA,
        "ASA-Aero LT": FUSROCK_ASA_AERO_LT,
        "NexASA-CF20": FUSROCK_NEXASA_CF20,
        "TPU 95A HF": FUSROCK_TPU_95A_HF,
        "TPU 85A": FUSROCK_TPU_85A,
        "TPU 90A HF": FUSROCK_TPU_90A_HF,
        "TPU-Aero": FUSROCK_TPU_AERO,
        "TPU 64D": FUSROCK_TPU_64D,
        "TPU 78D": FUSROCK_TPU_78D,
        "PAHT": FUSROCK_PAHT,
        "PA-CF": FUSROCK_PA_CF,
        "NexPA-CF25": FUSROCK_NEXPA_CF25,
        "NexPA-GF25": FUSROCK_NEXPA_GF25,
        "PAHT-GF": FUSROCK_PAHT_GF,
        "PEBA 95A": FUSROCK_PEBA_95A,
        "PC/ABS": FUSROCK_PC_ABS,
        "S-Multi": FUSROCK_S_MULTI,
        "S-PAHT": FUSROCK_S_PAHT,
    },
    "闪铸": {
        "HS PLA": FLASHFORGE_HS_PLA,
        "HS PLA 多色": FLASHFORGE_HS_PLA_MULTI,
        "HS PLA 彩虹": FLASHFORGE_HS_PLA_RAINBOW,
        "HS PETG": FLASHFORGE_HS_PETG,
        "HS PETG 金属": FLASHFORGE_HS_PETG_METALLIC,
        "HS PETG 透明": FLASHFORGE_HS_PETG_TRANSP,
        "HS PETG 多色": FLASHFORGE_HS_PETG_MULTI,
        "PLA Basic": FLASHFORGE_PLA_BASIC,
        "PLA Crystal": FLASHFORGE_PLA_CRYSTAL,
        "PLA Pro": FLASHFORGE_PLA_PRO,
        "PLA 多色": FLASHFORGE_PLA_MULTI,
        "PLA Silk+": FLASHFORGE_PLA_SILK,
        "PLA Silk+ 彩虹": FLASHFORGE_PLA_SILK_RAINBOW,
        "PLA Silk+ 双色": FLASHFORGE_PLA_SILK_DUAL,
        "PLA-CF": FLASHFORGE_PLA_CF,
        "ABS Basic": FLASHFORGE_ABS_BASIC,
        "ABS Pro": FLASHFORGE_ABS_PRO,
        "ASA": FLASHFORGE_ASA,
        "ASA-CF": FLASHFORGE_ASA_CF,
        "PET-CF": FLASHFORGE_PET_CF,
        "PET-GF": FLASHFORGE_PET_GF,
        "PETG-CF": FLASHFORGE_PETG_CF,
    },
    "Nature3d": {
        "PLA Pro": NATURE3D_PLA_PRO,
        "PLA Lite": NATURE3D_PLA_LITE,
        "PLA 哑光": NATURE3D_PLA_MATTE,
        "PLA 丝绸": NATURE3D_PLA_SILK,
        "PLA 彩虹": NATURE3D_PLA_RAINBOW,
        "PLA 渐变": NATURE3D_PLA_GRADIENT,
        "PLA 闪电": NATURE3D_PLA_LIGHTNING,
        "PLA 大理石": NATURE3D_PLA_MARBLE,
        "PLA 木质": NATURE3D_PLA_WOOD,
        "PLA-CF": NATURE3D_PLA_CF,
        "PLA 柔性": NATURE3D_PLA_FLEX,
        "ASA 闪光": NATURE3D_ASA_SPARKLE,
        "ABS Pro 闪光": NATURE3D_ABS_PRO_SPARKLE,
        "PETG-CF": NATURE3D_PETG_CF,
        "HS PLA": NATURE3D_HS_PLA,
        "HS ABS": NATURE3D_HS_ABS,
        "HS PETG": NATURE3D_HS_PETG,
    },
    "卓普": {
        "PLA": ZHUOPU_PLA,
        "PLA Basic": ZHUOPU_PLA_BASIC,
        "PLA MAX": ZHUOPU_PLA_MAX,
        "PLA 哑光": ZHUOPU_PLA_MATTE,
        "PLA 丝绸": ZHUOPU_PLA_SILK,
        "PLA 丝绸双色": ZHUOPU_PLA_SILK_DUO,
        "PLA 丝绸彩虹": ZHUOPU_PLA_SILK_RAINBOW,
        "PLA 高速丝绸": ZHUOPU_PLA_SILK_HS,
        "PLA 金属": ZHUOPU_PLA_METAL,
        "PLA 彩虹": ZHUOPU_PLA_RAINBOW,
        "PLA 大理石": ZHUOPU_PLA_MARBLE,
        "PLA 燃烧钛": ZHUOPU_PLA_BURNT_TI,
        "PLA 夜光": ZHUOPU_PLA_GLOW,
        "PLA 光变": ZHUOPU_PLA_UV,
        "PLA-CF": ZHUOPU_PLA_CF,
        "PLA-GF": ZHUOPU_PLA_GF,
        "PLA Rock": ZHUOPU_PLA_ROCK,
        "PLA-LW": ZHUOPU_PLA_LW,
        "PETG": ZHUOPU_PETG,
        "PETG 燃烧钛": ZHUOPU_PETG_BURNT_TI,
        "PETG 透光": ZHUOPU_PETG_TRANS,
        "TPU 95A": ZHUOPU_TPU_95A,
        "TPU 72D": ZHUOPU_TPU_72D,
        "TPU 90A": ZHUOPU_TPU_90A,
        "TPU 85A": ZHUOPU_TPU_85A,
    },
    "点维": {
        "PLA": DOWELL_PLA,
        "PLA 丝绸": DOWELL_PLA_SILK,
        "PLA-CF": DOWELL_PLA_CF,
        "PLA 木质": DOWELL_PLA_WOOD,
        "ABS": DOWELL_ABS,
        "ABS-GF": DOWELL_ABS_GF,
        "ABS-CF": DOWELL_ABS_CF,
        "PETG": DOWELL_PETG,
        "PETG 哑光": DOWELL_PETG_MATTE,
    },
    "Raise3D": {
        "PLA": RAISE3D_PLA,
        "HS PLA": RAISE3D_HS_PLA,
        "HS PLA Pro": RAISE3D_HS_PLA_PRO,
        "ABS": RAISE3D_ABS,
        "HS ABS": RAISE3D_HS_ABS,
        "ABS-CF": RAISE3D_ABS_CF,
        "ASA": RAISE3D_ASA,
        "PETG": RAISE3D_PETG,
        "PETG-ESD": RAISE3D_PETG_ESD,
        "PETG-CF": RAISE3D_PETG_CF,
        "PET-CF": RAISE3D_PET_CF,
        "HS PET-CF": RAISE3D_HS_PET_CF,
        "PET-GF": RAISE3D_PET_GF,
        "PET 支撑": RAISE3D_PET_SUPPORT,
        "PA12-CF": RAISE3D_PA12_CF,
        "PA12-CF 支撑": RAISE3D_PA12_CF_SUPPORT,
        "PPA-CF": RAISE3D_PPA_CF,
        "PPA-CF25": RAISE3D_PPA_CF25,
        "PPA-GF": RAISE3D_PPA_GF,
        "PPA-GF25": RAISE3D_PPA_GF25,
        "PPA 支撑": RAISE3D_PPA_SUPPORT,
        "PPS-CF": RAISE3D_PPS_CF,
        "PC": RAISE3D_PC,
        "TPU 95A": RAISE3D_TPU_95A,
        "PVA+": RAISE3D_PVA,
    },
    "FULLJOY": {
        "PLA+": FULLJOY_PLAP,
        "PLA 哑光艺术家": FULLJOY_PLA_MATTEART,
        "PLA 哑光": FULLJOY_PLA_MATTE,
        "PLA 木质": FULLJOY_PLA_WOOD,
        "PLA+ 丝绸": FULLJOY_PLAP_SILK,
        "PLA 彩虹渐变": FULLJOY_PLA_RAINBOWGRAD,
        "PLA 水晶": FULLJOY_PLA_CRYS,
        "PLA 合金": FULLJOY_PLA_ALLOY,
        "PLA+ 丝绸渐变": FULLJOY_PLAP_SILKGRAD,
        "PLA+ 夜光": FULLJOY_PLAP_GLOW,
        "PLA 大理石": FULLJOY_PLA_MARBLE,
        "PETG": FULLJOY_PETG,
    },
    "易泰龙": {
        "ABS 基础": YITAILONG_ABS_BASE,
        "HIPS 基础": YITAILONG_HIPS_BASE,
        "PA 基础": YITAILONG_PA_BASE,
        "PBT 基础": YITAILONG_PBT_BASE,
        "PC 基础": YITAILONG_PC_BASE,
        "PETG 基础": YITAILONG_PETG_BASE,
        "PETG 夜光": YITAILONG_PETG_GLOW,
        "PLA 丝绸": YITAILONG_PLA_SILK,
        "PLA 基础": YITAILONG_PLA_BASE,
        "PLA 夜光": YITAILONG_PLA_GLOW,
        "PMMA 基础": YITAILONG_PMMA_BASE,
        "POM 基础": YITAILONG_POM_BASE,
        "PP 基础": YITAILONG_PP_BASE,
        "TPU 基础": YITAILONG_TPU_BASE,
        "TPU 夜光": YITAILONG_TPU_GLOW,
        "TPU 渐变": YITAILONG_TPU_GRAD,
        "TPU 温变": YITAILONG_TPU_THERMO,
        "TPU 透明": YITAILONG_TPU_TRANS,
    },
}

MATERIAL_COLOR_SERIES_EXTRA: dict[str, list[str]] = {
    "PLA": [
        "K5 PLA", "K5 PLA 哑光",
        "PLA Basic", "PLA Matte",
        "PLA", "PLA+", "PLA 哑光", "PLA 丝绸", "金属色", "星空闪点", "夜光",
        "丝绸双色", "丝绸三色", "丝绸彩虹", "哑光双色", "哑光三色", "哑光彩虹",
        "HT-PLA", "PLA 大理石", "PLA 夜光", "PLA 木质", "HS PLA", "HS PLA 哑光", "HS PLA 大理石", "PLA Classic", "PLA Meta", "PLA 闪点", "PLA+ 2.0", "丝绸 PLA+", "PLA 星河", "丝绸 PLA", "PLA 金属", "PLA 闪粉", "PLA Wood", "PLA UV变色", "PLA 温变", "HS PLA Pro Matte", "HS PLA Pro", "PLA Marble", "HS PLA Pro Silk", "PLA Translucent", "PLA Pro", "PLA Silk"
    
        "PLA Rainbow",
        "PLA 魔幻双色",
        "PLA 变色龙",
        "PLA-Aero Pro",
        "HS PLA 多色",
        "HS PLA 彩虹",
        "PLA Crystal",
        "PLA 多色",
        "PLA Silk+",
        "PLA Silk+ 彩虹",
        "PLA Silk+ 双色",
        "PLA-CF",
        "PLA Lite",
        "PLA 彩虹",
        "PLA 渐变",
        "PLA 闪电",
        "PLA 柔性",
        "PLA MAX",
        "PLA 丝绸双色",
        "PLA 丝绸彩虹",
        "PLA 高速丝绸",
        "PLA 燃烧钛",
        "PLA 光变",
        "PLA-GF",
        "PLA Rock",
        "PLA-LW",
        "PLA 哑光艺术家",
        "PLA+ 丝绸",
        "PLA 彩虹渐变",
        "PLA 水晶",
        "PLA 合金",
        "PLA+ 丝绸渐变",
        "PLA+ 夜光",
        "PLA 基础",],
    "PETG": ["PETG", "PETG 哑光", "K5 PETG", "K5 PETG 哑光", "K5 PETG Rapid",
             "PETG Basic", "PETG HF", "PETG-CF", "PETG 夜光", "HS PETG 哑光", "PETG-Eco", "PETG GF", "PETG 闪粉", "PETG 金属", "PETG 星河", "PETG 大理石", "PETG Transparent", "HS PETG", "PETG Matte", "PETG Marble", "PETG Translucent",
        "PETG 2.0"
    
        "PETG+HS",
        "PETG UV变色",
        "PETG Pro",
        "PETG-HF",
        "PETG-GF",
        "PETG-CF HF",
        "HS PETG 金属",
        "HS PETG 透明",
        "HS PETG 多色",
        "PETG 燃烧钛",
        "PETG 透光",
        "PETG-ESD",
        "PETG 基础",],
    "PA": ["PA6-GF"
        "PA-CF",
        "PA6/66",
        "PA12-CF",
        "PAHT",
        "NexPA-CF25",
        "NexPA-GF25",
        "PAHT-GF",
        "S-PAHT",
        "PA12-CF 支撑",
        "PPA-CF",
        "PPA-CF25",
        "PPA-GF",
        "PPA-GF25",
        "PPA 支撑",
        "PA 基础",],
    "ASA": ["ASA", "ASA 大理石"
        "ASA+",
        "ASA-Aero LT",
        "NexASA-CF20",
        "ASA-CF",
        "ASA 闪光",],
    "ABS": ["ABS", "ABS-Pro"
        "ABS+",
        "ABS-CF",
        "ABS-HF",
        "ABS-GF",
        "NexABS-CF20",
        "ABS Basic",
        "ABS Pro",
        "ABS Pro 闪光",
        "HS ABS",
        "ABS 基础",],
    "TPU": ["TPU 95A", "TPU", "TPU95A"
        "TPU90A",
        "TPU 95A HF",
        "TPU 85A",
        "TPU 90A HF",
        "TPU-Aero",
        "TPU 64D",
        "TPU 78D",
        "TPU 72D",
        "TPU 90A",
        "TPU 基础",
        "TPU 渐变",
        "TPU 透明",
        "TPU 夜光",
        "TPU 温变",],

    "PVA": [
        "PVA",
    
        "S-Multi",
        "PVA+",],

    "PET": [
        "PET-CF",
        "PET-GF",
    
        "HS PET-CF",
        "PET 支撑",],

    "PEBA": [
        "PEBA 95A",
    ],

    "PC": [
        "PC/ABS",
    
        "PC 基础",],

    "PPS": [
        "PPS-CF",
    ],

    "PBT": [
        "PBT 基础",
    ],

    "PP": [
        "PP 基础",
    ],

    "POM": [
        "POM 基础",
    ],

    "HIPS": [
        "HIPS 基础",
    ],

    "PMMA": [
        "PMMA 基础",
    ],
}
