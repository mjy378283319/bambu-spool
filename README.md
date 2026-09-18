# 拓竹耗材管家 (Bambu Spool)

自托管的拓竹 3D 打印机耗材管理系统，核心是**打印完成自动扣重**。一个 Docker 容器跑起来，
中文界面，数据全在自己手里，**不要求打印机和服务器在同一局域网**。

对标 [Mars Printer Hub](https://wiki.hcgl.top/) 的 AMS 槽位可视化、料盘绑定、自动扣重与使用历史。

![仪表盘](https://gcore.jsdelivr.net/gh/mjy378283319/bambu-spool@main/docs/screenshot-dashboard.png)

| 耗材汇总 | 手机端扫码 |
|---|---|
| ![耗材汇总](https://gcore.jsdelivr.net/gh/mjy378283319/bambu-spool@main/docs/screenshot-summary.png) | ![手机端扫码](https://gcore.jsdelivr.net/gh/mjy378283319/bambu-spool@main/docs/screenshot-scan.png) |

| 料盘库存 | 打印记录 |
|---|---|
| ![料盘库存](https://gcore.jsdelivr.net/gh/mjy378283319/bambu-spool@main/docs/screenshot-spools.png) | ![打印记录](https://gcore.jsdelivr.net/gh/mjy378283319/bambu-spool@main/docs/screenshot-jobs.png) |

## 它解决什么问题

多色打印最烦的是不知道每盘料还剩多少。这里把记账完全自动化：

1. 绑定拓竹账号 → 自动同步账号下的打印机
2. 把 **AMS 每个槽位**绑定到**具体哪一盘料**
3. 开始打印 → 自动开一条任务记录
4. 打印结束 → 从云端任务历史取**每个槽位实际用了多少克**
5. 自动扣减对应料盘余量，留下可追溯的使用流水；扣错了可一键转到另一盘料

## 功能

### 品牌配色卡

录料盘时点色块即填色名与色值，内置 **13 个品牌 · 140 个系列 · 1811 个色号**：

| 品牌 | 系列 | 色号 | 色值来源 |
|---|---|---|---|
| Polymaker | 3 | 104 | 官方公布 |
| Kexcelled | 5 | 200 | 商品图提色（近似） |
| 拓竹 | 4 | 82 | 官方 Hex Code Table |
| 大简 | 2 | 49 | 官方店 SKU |
| 兰博 | 30 | 213 | 商品图提色（近似） |
| 魔创 | 8 | 152 | 淘宝官方店 SKU |
| 锐造 | 12 | 122 | 商品图提色（近似） |
| JAYO | 12 | 225 | 官网 products.json |
| 天瑞 | 21 | 249 | 官网 |
| iBOSS | 9 | 44 | 官网 |
| R3D | 19 | 132 | 官网 |
| 爱丽兹 Allizz | 7 | 89 | 官网 Color Options |
| 彩多屋 | 8 | 150 | 官网 products.json（色号官方 / HEX 提色近似） |

无法从官方确认的 HEX 在界面上标注为近似值；三色丝绸、彩虹渐变这类没有单一定义色的系列
不参与色值比对（用中性占位灰）。

### 图片识色 · 找同色耗材

库存页右上角「图片识色」：拖入照片（也可选文件、Ctrl+V 粘贴、手机拍照）自动提取主色，回答两件事——
**库里哪盘最接近**（按余量与存放位置列出，告诉你该用哪盘）、**想买新的买哪个**（对全部内置色号匹配，
每个品牌给出最接近的一个色）。

可点图精确吸色、手动增删色，按材料 / 品牌过滤，色差上限（ΔE）可调；从结果点「建料盘」会预填
品牌、材料、色名、色值、皮重。色差用 **CIEDE2000**（不是 RGB 距离），主色提取在浏览器 Canvas
完成，容器不需要图像处理依赖。**空盘皮重**按品牌带出（选完品牌自动填），优先用**上秤实测值**
而非厂商标称（大简/拓竹/Kexcelled/爱酷乐 239、魔创 220、兰博 160、Polymaker 150 g）；
没实测的走估算档，注释已标明。

### 耗材价格与每打印费用

每盘料登记**整盘价格（¥）**，自动算三笔账：**耗材总价值**（在用料盘整盘价之和）、
**库存余值**（单价 × 当前余量）、**每次打印耗材费**（各槽位用量 × 对应单价之和，并汇总累计）。
未登记价格的料盘不计入金额（显示「—」）。老数据按当前单价实时折算，改价后历史打印费跟着更新。

### 耗材汇总

单独一页回答：一共多少盘、花了多少钱、用了多少、还剩多少。顶部是**库存数据概览**（材料环形图 +
使用状态分段条）与**品牌分布**并排，往下是价格区间分布，最后按**品牌 / 材料 / 外观**三张表拆开：

| 列 | 口径 |
|---|---|
| 盘数 | 该分组在用料盘数（不含已归档） |
| 满盘净重 | 各盘 `initial_weight` 之和 |
| 已用 / 剩余 | 各盘 `used_weight` / `remaining_weight` 之和 |
| 余量 | 剩余 ÷ 满盘净重 |
| 采购金额 | 各盘整盘价之和 |
| 每盘均价 | 采购金额 ÷ **登记过价的盘数**——没填价的盘不拉低均价 |

图例、状态行、品牌名、表格里的分组名都可点击钻取：点材料只统计那种材料，点状态跳到库存对应标签页，
点品牌跳到该品牌的库存明细。概览页顶部还有三张本周卡（打印时长 / 成功打印 / 耗材消耗），
按**浏览器时区**切日——东八区晚上看到的「今天」不会被算进 UTC 的昨天。

### 料盘管理

- **删除**：没流水的直接删；有流水的先提示条数，确认后连同流水一起删，并清掉槽位绑定、
  把任务明细的引用置空但**保留克重**。
- **归档**：暂时不用的料盘用归档，从默认列表隐去、统计口径分开算。
- **品牌归一**：「拓竹 / Bambu Lab」这类中英变体只保留一条规范名，老库启动时幂等收口一次。
- **外观（表面工艺）**：与材料、颜色并列，15 种预设（普通 / 亮面 / 哑光 / 磨砂 / 丝绸 / 珠光 /
  金属 / 半透 / 透明 / 渐变 / 双色 / 木纹 / 碳纤 / 夜光 / 其他）。填颜色名时自动预填
  （「哑光黑」→ 哑光，丝绸优先于哑光、半透优先于透明），点色卡时系列名带外观的一起带过来；
  **两种预填都只在你没选过时动手**。
- **自定义品牌**：设置页可加自己的品牌，存数据库，升级镜像不丢。

### 真机照片

在 `app/static/printer/` 放一张以机型命名的照片即生效，**不用改代码、不用重启**：
`p2s.jpg → P2S`、`a1mini.png → A1MINI`。没有对应机型或图片加载失败时退回内联 SVG 示意图；
喷嘴 / 仓温 / 热床浮标是实时读数，照旧叠在照片上。仓库里那张 P2S 照片是用
`scripts/build_printer_photo.py` 处理过的：

```bash
python scripts/build_printer_photo.py 我的照片.jpg --probe          # 1) 量机身范围
python scripts/build_printer_photo.py 我的照片.jpg app/static/printer/p2s.jpg \
    --crop 498,650,1857,2018 --canvas 720x876 --fit-width 0.86     # 2) 裁成展示框尺寸
```

素材上压了别的东西（如官方 App 截图的温度胶囊）加 `--heal x0,y0,x1,y1` 修掉。

### 手机扫码

每盘料有二维码标签，扫一下直接跳到那盘料详情。入口：库存页「扫码」、槽位绑定弹窗「相机扫码」、
或用手机自带相机扫贴纸上的网址。

三层降级：① 安卓 Chrome 的原生 `BarcodeDetector`；② 本地化的
[jsQR](https://github.com/cozmo/jsQR)（Apache-2.0，不依赖外网 CDN）逐帧解码；
③ `<input capture>` 拍照识别——浏览器只在 HTTPS / localhost 下允许开相机，
**内网 http 部署时这条路是唯一能用的**。

认码：`#spool=<id>` 料盘码、`#bind=<printer>:<ams>:<tray>` 槽位码、纯数字当料盘号。
App 已开着时靠 `hashchange` 就地跳转。

> ⚠️ **实时相机开不了，先查响应头，别急着改手机权限。** `Permissions-Policy: camera=()` 的括号里是空集，
> 意思是「任何来源都不许，包括本站自己」，浏览器**直接拒绝且完全不弹权限窗**，现象和「手机没把相机权限
> 给浏览器」一模一样，于是改系统设置、换浏览器、换手机全都无解。正确写法是 `camera=(self)`
> （见 `app/main.py` 的 `_harden()`）；前端 `scan.js` 的 `policyBlocksCamera()` 会认出这种情形并把提示指向服务端。

### 标签打印（蓝牙直打 · 汉印 T260LR）

- **蓝牙直打**（电脑版 Chrome / Edge、安卓 Chrome）：整张标签在浏览器里画成 1 位位图 →
  打包成 ESC/POS 光栅指令 → 经 Web Bluetooth 直发打印机。
- **导出标签图**（iPhone 走这条）：存成 PNG，在**汉码** App 里用「图片打印」导入
  （汉码无对外 API / URL Scheme，网页调不起它）。

可调：尺寸预设 40×30 / 50×30 / 60×40 / 50×40 mm、打印头 203 / 300 dpi、浓度 1–8、份数 1–50，
改动即时存本地；另有「批量 A4 拼版」。版式是「左边文字 + 右边二维码」，**没有色块**（热敏纸只有黑白），
颜色信息以 `#147DB5` 留在页脚。

二维码在服务端按**整数个点 / 模块**出图（1 位位图里是 1:1 贴进去的，缩放就不是整数像素、
模块边界糊成灰边就扫不出来）：`?dots=N` 给定总点宽、`?box=N` 给定每模块占几个点，
响应头 `X-QR-Dots` / `X-QR-Modules` 回传实际尺寸。渲染放在浏览器 Canvas 是因为镜像没有中文字体。

| 汉印 T260LR | 情况 |
|---|---|
| 仿真协议 | 汉码私有协议（非 TSPL / CPCL），已知指令以 `GS` 开头 → **ESC/POS 派生** |
| 通信接口 | **仅蓝牙**（USB-C 只充电），不支持云打印 |
| PC 驱动 / 由汉码 App 自动打 | 均不可用 |

**已知限制**：Web Bluetooth 只在 Chrome / Edge（桌面 + 安卓）上有，**iOS Safari 完全不支持**；
要求 https 或 localhost，`http://192.168.x.x` 下按钮是灰的（挂 HTTPS 反代即可）；
蓝牙链路**尚未在真机 T260LR 上实测**，协议依据官方知识库的指令样本推断。

### 打印成果图

打印记录列表每行有一张成果缩略图，点开任务详情能看到大图（点图新窗口打开原图）。

> ⚠️ **这张图是切片时的盘面预览图，不是摄像头实拍。** 云端任务接口只给这个（文件名形如
> `plate_1.png`），摄像头画面云端不提供——要拿只能走局域网模式的摄像头流。界面上如实标注了这一点。

云端给的 `cover` 是阿里云 OSS 的**预签名链接**（`X-Amz-Expires=1800`），**30 分钟就失效**，
所以结算那一刻就把字节下载到 `DATA_DIR/covers/<任务ID>.png`，界面只读本地那份。

抓图**失败不影响扣重**：`app/core/covers.py` 吞掉所有异常并记日志，非 200 / 非图片 content-type /
不足 512 字节一律跳过，任务照常结算、料照常扣。校准类任务本来就没有成果图，这种情况列表显示「—」。

### 界面

顶部图标导航、卡片式统计；料盘页是状态标签 + 筛选栏 + 表格 + 分页；仪表盘带「最近使用 / 最近添加 /
库存不足」三栏。纯手写 CSS，没有 UI 框架，手机上也能用。

**设备面板**左栏是机器照片（或 SVG 示意图）+ 打印状态 / 层数 / 进度条 + 温度 + 风扇；
右栏按单元列出 AMS A/B/C/D、AMS HT 与外挂料盘，每槽一根竖直料条，右上角一圈状态标记：
绿勾＝已绑定、黄叹＝有料未登记、青实心＝正在使用、虚线圈＝空槽。

**风扇与温度口径**（照官方 App 与真机报文对齐）：

| 项 | 口径 |
|---|---|
| 风扇转速 | MQTT 的 `*_fan_speed` 是 **0–15 的 PWM 档位，不是百分比**，`值/15×100` 再按 10% 取整：`14 → 90%`、`15 → 100%` |
| 风扇通道名 | 部件冷却 / 辅助部件冷却 / 腔体 / 热端。P2S 整机共 3 个风扇、**不配外排风扇**（选配套件），没装的档显示「未安装」 |
| P2S 辅助风扇报在哪 | 不在 `big_fan1`（真机报文恒 0），而在 `device.airduct.parts` 的 `func==0` 部件，其 `state` **本身即百分比**，不能再除 15 |
| 仓温 | P2S 在 `device.ctc.info.temp`（32 位打包：低 16 位当前、高 16 位目标），X1 在 `print.chamber_temper`。只读后者 P2S 永远「—」 |

AMS 编号按官方语义归一：`ams_id` 0–3 是普通 AMS（A/B/C/D），128–131 是 AMS HT（HT A/HT D）。
湿度兼容两种口径——普通 AMS 报 0–5 档（显示「湿度 3 级 · 正常」），AMS HT 报百分比（显示「湿度 21%」）。
槽位克重优先用本系统台账的实测余重，没绑定时按 `remain% × 官方标称满重` 估算。

## 数据来源

```text
拓竹打印机 + AMS ──(云 MQTT，实时状态)──┐
        └──(云端任务记录)────────────▶ 本服务：状态解析 / 库存与绑定 / 自动扣重 / Web 界面
```

克重取自拓竹云 `GET /v1/user-service/my/tasks`（每条任务带 `weight` 与 `amsDetailMapping[]`
每槽克重），是切片软件算的理论值，**精度 0.1 g 量级**。实时状态走云 MQTT，只读。

## 快速开始

```bash
docker compose up -d                                      # 拉预构建镜像（推荐）
docker compose -f docker-compose.build.yml up -d --build  # 拉不动 ghcr 时本地构建
```

打开 `http://NAS地址:8971`：

1. 创建管理员账号（密码至少 8 位），创建后入口自动关闭
2. 登录 → 设置 → 填拓竹账号密码（中国大陆账号选「中国大陆」区域）
3. 点「同步设备」，打印机就出现了
4. 回仪表盘点 AMS 槽位，绑定到对应料盘
5. 之后每次打印都自动记账

> **登录成功但一台设备都没有？** 多半是区域选错——表现不是登录失败，而是设备列表接口打到了另一个
> 域名、于是永远是空的。设置页账号卡片下有「区域不对？」入口，改完会用保存的密码在新区域重新登录并同步。

### 部署到 Unraid

**A. Compose Manager 插件（推荐）**：应用 → Community Applications 装 `Compose Manager` →
Docker 页面 → `Add New Stack` 命名 `bambu-spool` → 粘贴 `docker-compose.yml`，
把 `./data` 改成 `/mnt/user/appdata/bambu-spool` → `Compose Up`。

**B. 在 Unraid 终端里跑**

```bash
mkdir -p /mnt/user/appdata/bambu-spool && cd /mnt/user/appdata/bambu-spool
git clone https://github.com/mjy378283319/bambu-spool.git repo && cd repo && docker compose up -d
```

**C. 图形界面手工建容器**：Docker 页面 → Add Container

| 字段 | 值 |
|---|---|
| Repository | `ghcr.io/mjy378283319/bambu-spool:latest` |
| Network Type | `Bridge` |
| Port | `8971` → `8971`（TCP） |
| Path | `/data` → `/mnt/user/appdata/bambu-spool` |
| Variable | `BAMBU_REGION=china`、`PUID=99`、`PGID=100`、`TASK_POLL_INTERVAL=60` |
| **Icon URL** | 见下方[容器图标](#容器图标) |

##### 容器图标

Unraid 的容器图标不会从镜像自动读，得填一个**公网可访问的图片直链**：

```text
https://gcore.jsdelivr.net/gh/mjy378283319/bambu-spool@main/icon.png       # ① CDN，国内可达，首选
https://raw.githubusercontent.com/mjy378283319/bambu-spool/main/icon.png   # ② 直连 GitHub，海外可用
```

> Unraid 拉图标是一次**服务端直连**，与你浏览器走不走代理无关。国内网络下 `raw.githubusercontent.com`
> 常被 DNS 污染（解析到 `0.0.0.0`），填进去就是永远转圈不出图。两条都可以 `curl -sI` 验证，
> 返回 `image/png` 且约 48 KB 就是对的。

> **拉取报 `denied`**：GHCR 上的包还是私有，去
> `https://github.com/users/mjy378283319/packages/container/bambu-spool/settings`
> 把 Visibility 改成 Public，或先 `docker login ghcr.io` 再拉。
> **`PUID` / `PGID`**：容器先把数据目录改成这两个身份再运行。Unraid 的 appdata 归 `nobody:users`
> （99:100），普通 Linux 通常改 `1000:1000`，设 `0` 表示不降权。

### 没有打印机也想先看看

```bash
docker run --rm -p 8971:8971 -e BAMBU_MOCK=1 ghcr.io/mjy378283319/bambu-spool:latest
```

模拟模式虚拟一台 P2S + AMS 2 Pro，循环跑「准备 → 打印 → 完成」，扣重链路完全真实。

## 配置项

| 变量 | 默认 | 说明 |
|---|---|---|
| `DATA_DIR` | `/data` | 数据目录，**必须持久化**（存 SQLite 和加密密钥） |
| `PORT` | `8971` | 监听端口 |
| `DATABASE_URL` | SQLite | 可换 PostgreSQL |
| `SESSION_TTL_DAYS` | `30` | 登录会话有效期（天），每次访问滑动续期 |
| `LOGIN_MAX_ATTEMPTS` | `5` | 登录失败锁定阈值 |
| `LOGIN_LOCKOUT_MINUTES` | `15` | 锁定时长（分钟） |
| `PBKDF2_ITERATIONS` | `300000` | 口令哈希迭代次数，弱 CPU 的 NAS 可降到 100000 |
| `BAMBU_REGION` | `china` | `china` / `global` |
| `BAMBU_MOCK` | `0` | `1` 启用模拟打印机 |
| `TASK_POLL_INTERVAL` | `60` | 云端任务轮询间隔（秒），也是扣重的最大延迟 |
| `TASK_MATCH_WINDOW_MINUTES` | `20` | 任务结束后回查云端记录的时间窗 |
| `DEDUCT_ON_FAILURE` | `true` | 失败任务是否按进度比例扣重 |
| `MIN_PROGRESS_TO_RECORD` | `1.0` | 低于此进度视为误触，不记 |
| `NOTIFY_WEBHOOK` | 空 | 通知地址，POST `{"title","message"}` |
| `TOKEN_RENEW_BEFORE_HOURS` | `3` | 令牌剩余多久时自动续期 |

完整列表见 [.env.example](.env.example)。

### 挂到公网（Lucky / Nginx 反代）

| 变量 | 默认 | 说明 |
|---|---|---|
| `TRUST_PROXY` | `true` | 信任反代传来的 `X-Forwarded-*` 头，挂在 Lucky / Nginx 后面必须保持开启 |
| `REQUIRE_HTTPS` | `false` | 设为 `true` 后检测到外部是 http 会 308 跳 https。**公网强烈建议开启** |
| `COOKIE_SECURE` | `auto` | 会话 Cookie 的 Secure 标志，按实际协议自动判断 |
| `ALLOW_PUBLIC_SETUP` | `false` | 是否允许从公网 IP 完成「首次创建管理员」，默认只允许内网直连 |
| `ALLOWED_ORIGINS` | 空 | 跨站写操作检查的白名单，非浏览器客户端需要时填，逗号分隔 |

推荐路径：先在内网打开 `http://NAS地址:8971` 创建好管理员账号，再用 Lucky 把域名反代到 8971 端口
并给容器加 `REQUIRE_HTTPS=true`。登录接口有失败锁定（默认 5 次 / 15 分钟），密码走 PBKDF2 存储，
会话 Cookie 为 HttpOnly。

## 更新

```bash
docker compose pull && docker compose up -d
```

镜像由 GitHub Actions 在每次推送到 `main` 时自动构建，标签 `latest`；数据在 `/data` 卷里，
更新不会丢。想锁版本可以用 `sha-xxxxxxx` 这类标签。

## 关于拓竹账号与隐私

- 登录用的是拓竹官方云接口，和 Bambu Studio / Handy 走同一套。
- **密码只有勾选「保存密码」时才存到本地**，且用数据目录里的密钥文件做 Fernet 加密；
  不保存则令牌过期后需重新登录（约 24 小时一次）。
- 本项目**只读**：不发送打印指令、不上传任何东西到拓竹云之外的第三方。
- 所有记录都存在你自己的数据库里。

## 重要限制（请务必了解）

| 限制 | 影响 | 应对 |
|---|---|---|
| 打印任务必须**经拓竹云端发起** | **局域网模式本地发送、U 盘打印不进云端记录**，拿不到克重 | 在打印记录里手动录入用量，或改用云端发起 |
| 克重是切片估算值 | 精度 0.1 g 量级，不是称重实测 | 定期用「称重校准」按实际秤读数修正 |
| 非实时 | 打印结束后要等一个轮询周期才扣重 | 调小 `TASK_POLL_INTERVAL` |
| 扣重依赖槽位绑定正确 | 没绑定的槽位只记流水、不动任何料盘 | 在仪表盘把槽位绑好；绑错了可在详情页转移 |
| AMS `remain` 只有整数百分比 | 1 kg 料盘 1% ≈ 10 g | 余量以本系统的克重台账为准 |
| 蓝牙标签打印需要 Chrome/Edge + HTTPS | iOS Safari 用不了 | iPhone 用「导出标签图」；局域网访问挂 HTTPS 反代 |
| 标签二维码接口需要登录 | 拿标签图得带会话 | 属预期行为；需要外发就先下载 PNG |

## 本地开发

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

BAMBU_MOCK=1 python -m uvicorn app.main:app --reload --port 8971

python tests/test_flow.py              # 端到端扣重链路
python tests/test_auth.py              # 登录与访问控制（会真起一个 uvicorn 子进程）
python tests/test_color.py             # 图片识色与 CIEDE2000 配色匹配
python tests/test_price.py             # 每盘价格 / 耗材总价值 / 每次打印耗材费
python tests/test_admin.py             # 料盘删除保护、品牌归一与历史迁移、色卡覆盖
python tests/test_ams.py               # AMS / AMS HT 编号归一、槽位克重折算
python tests/test_fans_temps.py        # 风扇 0-15 档位换算、仓温两个来源
python tests/test_finish_summary.py    # 外观字段归一与回填、耗材汇总与时区切日
python tests/test_cloud_endpoints.py   # 拓竹云接口地址与验证码登录状态流转（离线）
python tests/test_labels.py            # 标签二维码取整、?box / ?dots 与响应头
python tests/test_slot_label.py        # 槽位展示名：AMS A-D / HT A-D / 外挂料盘
python tests/test_cover.py             # 打印成果图：云端 cover 抓取、本地缓存、取图接口
python tests/test_brand_icon.py        # 应用图标文件、ICO 结构与三种引用
python tests/test_readme.py            # README 的图片直链、色卡数字与文档引用是否过期

node tests/test_label_raster.mjs       # 1 位光栅打包、ESC/POS 报文与标签渲染尺寸
node tests/test_panel_fill.mjs         # 风扇命名与料条高度口径
node tests/test_ui_polish.mjs          # 界面口径：外观预填、扫码、相机归因、成果图、汇总页、料盘搜索、筛选与皮重

PYTHON=python node scripts/shot_ui.mjs # 浏览器实拍验收（截图 + 断言，不进 CI）
```

> `tests/*.mjs` 是纯函数自测（跑在 node 的 vm 沙箱里，不需要浏览器），CI 里跑的是这些；
> `scripts/shot_ui.mjs` 走真浏览器 + 真服务，用来抓「截图看着还行但其实是坏的」那类问题
> （图片 404 了布局还在、温度浮标飘出卡片、hash 深链没跳转、表格比卡片宽把按钮顶出去）。
> 它还会扫 1440 / 1280 桌面宽度与 320 / 360 / 390 / 430 手机宽度，断言**任何视图都不横向溢出**。

`data/` 整个目录都是**运行时可再生的**（自测库、截图工装的临时浏览器 profile），已被 gitignore。
注意别把手工起的验证服务留在后台——它们各自用 `DATA_DIR` 指着 `data/` 下的子目录，
不退出就会一直占着端口和那些 SQLite 文件（表现为目录删不掉、`Device or resource busy`）：

```bash
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ? CommandLine -match 'uvicorn'   # Windows
```

代码结构：

```text
app/
├─ cloud/       拓竹云 HTTP 客户端、云 MQTT 连接、模拟数据源
├─ core/        状态解析、任务状态机、扣重引擎、中枢编排、成果图抓取
├─ api/         REST 接口与 WebSocket
├─ catalog.py   机型 / 材料 / 皮重 / 外观 / 颜色 / HMS 错误码对照表与品牌色卡
├─ brands.py    自定义品牌（存设置表，升级镜像不丢）
├─ colors.py    色彩工具（Lab 转换、CIEDE2000 色差、配色匹配）
├─ printer_art.py 真机照片的发现（扫 static/printer/）与 SVG 降级
└─ static/      无构建步骤的前端（原生 HTML/CSS/JS）
   ├─ app.js     界面与接口调用
   ├─ scan.js    手机相机扫码（BarcodeDetector → jsQR → 拍照识别）
   ├─ label.js   标签渲染、1 位光栅打包、ESC/POS 报文与 Web Bluetooth
   ├─ printer/   真机照片（<机型>.jpg）
   └─ vendor/    jsQR（Apache-2.0，本地化，含许可证）

scripts/build_printer_photo.py   把实物照片处理成可用的机型图（裁剪 / 修掉浮标 / 补背景）
scripts/build_cailab_colors.py   抓彩多屋官方商城色卡，生成 app/brand_colors_cailab.py
scripts/shot_ui.mjs              无头浏览器实拍验收（截图 + 断言）
scripts/seed_demo_job.py         给模拟模式灌一条演示打印任务（实拍验收用）
```

色卡抓取脚本两段跑：`--fetch` 把官方 `/products.json` 与每个色号的色块图缓存到 `data/_cailab_src/`，
`--build` 再离线生成色卡模块（色号为官方货号，HEX 取自色块图采样，因此 `official=False`）。

## 路线图

**待做**

- [ ] 打印机侧中继（同局域网时走 FTPS 读切片文件，拿到实测实时扣重）
- [ ] 标签打印真机验证与协议微调（T260LR 实测）
- [ ] 摄像头画面（局域网模式下取真实最后一帧）

**已完成**：耗材成本与报价、耗材汇总页与本周三张卡（按浏览器时区切日）、料盘删除与归档、
品牌写法归一与自定义品牌、界面与设备面板重构（AMS / AMS HT / 外挂料盘槽位可视化）、
风扇口径修正与 P2S 仓温读取、真机照片、标签打印、手机扫码、外观字段、料盘行内快捷操作与表头排序、
耗材汇总可视化（材料环形图 + 状态分段条 + 价格区间 + 品牌分布钻取）、打印记录跳转料盘 / 更改料盘、
打印成果图、槽位绑定下拉自愈、刷新后停留在当前视图、全站字号与间距放大。

## 致谢与参考

协议与接口事实均来自以下开源项目的源码与文档，感谢这些作者：

- [greghesp/ha-bambulab](https://github.com/greghesp/ha-bambulab)（MIT）—— 云客户端、MQTT 字段、机型与 HMS 表
- [Doridian/OpenBambuAPI](https://github.com/Doridian/OpenBambuAPI)（GFDL）—— 协议文档
- [coelacant1/Bambu-Lab-Cloud-API](https://github.com/coelacant1/Bambu-Lab-Cloud-API) —— 云 API 字段
- [Donkie/Spoolman](https://github.com/Donkie/Spoolman)（MIT）—— 数据模型参考
- [Rdiger-36/bambulab-ams-spoolman-filamentstatus](https://github.com/Rdiger-36/bambulab-ams-spoolman-filamentstatus)（GPL-3.0）—— 切片文件扣重思路
- [cozmo/jsQR](https://github.com/cozmo/jsQR)（Apache-2.0）—— 纯 JS 二维码解码器，原样放在
  `app/static/vendor/jsQR.js`（许可证见同目录 `LICENSE-jsQR.txt`）；放本地而非引 CDN，
  是因为这个应用常常跑在没有外网的内网里。

本项目其余代码全部独立编写，未复制上述项目的源码。

## 许可

MIT
