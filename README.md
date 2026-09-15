# 拓竹耗材管家 (Bambu Spool)

自托管的拓竹（Bambu Lab）3D 打印机耗材管理系统，带**打印完成自动扣重**。
一个 Docker 容器跑起来，中文界面，数据全在自己手里。

对标 [Mars Printer Hub](https://wiki.hcgl.top/) 的核心能力（AMS 槽位可视化、料盘绑定、自动扣重、使用历史），
但开源、免费、可私有部署，并且**不需要打印机和服务器在同一局域网**。

![仪表盘](docs/screenshot-dashboard.png)

| 料盘库存 | 打印记录 |
|---|---|
| ![料盘库存](docs/screenshot-spools.png) | ![打印记录](docs/screenshot-jobs.png) |

---

## 它解决什么问题

多色打印最烦的事之一：不知道每盘料还剩多少。这个项目把这件事完全自动化——

1. 绑定拓竹账号，自动同步账号下的打印机
2. 在界面上把 **AMS 每个槽位** 绑定到**具体哪盘料**
3. 打印机开始打印 → 自动开一条任务记录
4. 打印结束 → 从拓竹云端任务历史拿到**每个槽位实际用了多少克**
5. 自动扣减对应料盘的余量，留下一条可追溯的使用流水
6. 扣错了？在料盘详情里一键把这条消耗转到另一盘料

全程不需要手动记账。

录入料盘时还内置了**品牌配色卡**：选 Polymaker 会按材料带出
Panchroma™ PLA（28 色）、Panchroma™ 哑光 PLA（52 色）、Polymaker™ PETG（24 色）
的官方色号；Kexcelled（K5 PLA 51 色 / PLA 哑光 55 色 / PETG 52 色 / PETG 哑光 22 色）、
兰博（13 个 PLA 系列 + 2 个 PETG 系列）、魔创（8 个系列 152 色：PLA / PLA 哑光 / PLA+ /
HT-PLA / PETG / PETG 哑光 / ASA / ABS，取自官方淘宝店商品 SKU）也已内置。点色块直接填名称和色值；
无法从官方确认的 HEX（Polymaker 部分色号、Kexcelled 与兰博全部、魔创全部取自官方产品图）会标注为近似值。

### 图片识色 · 找同色耗材

料盘库存页右上角的「图片识色」：拖一张照片进来（也可以选文件、Ctrl+V 粘贴，
手机端直接拍照），自动提取画面里的主要颜色，然后帮你回答两个问题——

- **库里现有的料，哪一盘最接近？** 直接按余量、存放位置列出来，告诉你该用哪盘。
- **想买新的，该买哪个品牌哪个色？** 对 4 个品牌 637 个官方色号做匹配，
  每个品牌给出它最接近的一个色，方便横向比价。

颜色支持手动微调：点击图片任意位置可以精确吸色，也能手动加色、删掉不需要的色。
匹配可以按材料、品牌过滤，色差上限（ΔE）可调；从结果里点「建料盘」
品牌、材料、色名、色值、皮重会全部预填好。

色差用的是 **CIEDE2000**（不是简单的 RGB 距离）——同样是数值差 30，
深蓝之间肉眼几乎无差、绿色之间已经明显不同，所以找同色耗材必须用感知色差。
阈值参考：ΔE < 1 看不出差别，< 2 算同色，< 4 非常接近，> 10 就明显是两种颜色了。

图像的主色提取在浏览器里完成（Canvas 聚类 + 吸管），只把最终几个色值发给后端，
所以容器不需要任何图像处理依赖，手机上也够快。

### 耗材价格与每打印费用

每盘料都能登记一个**整盘价格（¥）**，系统据此自动算清三笔账：

- **耗材总价值**：所有在用料盘的整盘价之和（你为这些料花了多少钱）。
- **库存余值**：按「单价 × 当前余量」折算的库存现值（单价 = 整盘价 ÷ 满盘净重）。
- **每次打印耗费料材的价格**：一条打印任务的「耗材费」= 各槽位用量 × 对应料盘单价之和；
  打印记录列表、任务详情都会显示，并汇总出累计打印耗材费。

未登记价格的料盘不计入任何费用汇总（单价/余值显示为「—」）。老数据（打印记录里
没有费用快照）会按当前料盘单价实时折算，所以改价后历史打印费也能跟着更新。

### 料盘管理：删除、归档、品牌归一

录错了能删掉——料盘列表每行的垃圾桶按钮、或料盘详情里的「删除料盘」：

- **没有使用流水的料盘**：直接删除，不拦。
- **有使用流水的料盘**：默认先拦一道（返回 409），弹窗会告诉你这盘料有几条记录，
  确认后才会连同流水一起删。删除时会**顺手收拾干净引用关系**——清掉该料盘的槽位绑定、
  删掉它名下的使用流水、把打印任务明细里的引用置空但**保留克重**（任务本身和历史用量不受影响）。

还没用完但暂时不用的料盘，用「归档」而不是删除，它会从默认列表里隐去，统计口径也分开算。

**品牌归一**：「拓竹」和「Bambu Lab」、「Kexcelled」和「kecelled」这类中英/变体写法
在系统里只会存在一条规范名。新建、编辑料盘时自动归一，老库里已有的历史写法
**启动时自动收口一次**（幂等，自定义品牌不受影响）。这样筛选下拉框就不会出现重复项了。

### 界面

界面参照 [Mars Printer Hub](https://wiki.hcgl.top/) 的观感重做过一遍：顶部图标导航、
卡片式统计、状态标签 + 筛选栏 + 表格 + 底部分页的料盘页，仪表盘带「最近使用 / 最近添加 /
库存不足」三栏。纯手写 CSS，没有 UI 框架，手机上也能用。

**设备面板**按机器分块，左右两栏：

- 左栏是机器示意图（内联 SVG，不依赖外部图片）、打印状态 + 层数 + 进度条、
  温度属性（热床 / 仓温 / 喷嘴当前值-目标值 / 信号）、风扇状态（部件 / 辅助 / 腔体 / 热端）。
- 右栏按单元列出 **AMS A/B/C/D**、**AMS HT** 与外挂料盘。每个槽位是一根竖直料条：
  耗材本色 + 克重标签 + 材料名，右上角一圈状态标记 ——
  绿勾＝已绑定本系统料盘，黄叹＝机器有料但没登记，青实心＝当前正在使用，虚线圈＝空槽。
  没绑定的槽位会连卡片底色一起转成浅琥珀色，避免误以为已经入库。

AMS 编号按官方语义归一：`ams_id` 0–3 是普通 AMS（A/B/C/D），128–131 是 AMS HT（HT A/HT D），
所以不会再出现「AMS 129」这种把 HT 的 id 直接加一拼出来的编号。湿度也兼容两种口径 ——
普通 AMS 上报 0–5 档位（显示为「湿度 3 级 · 正常」），AMS HT 上报百分比（显示为「湿度 21%」）。
槽位克重优先用本系统料盘台账的实测余重，没绑定料盘时按「remain% × 官方标称满重」估算。

应用图标（`app/static/icon.svg` + `docs/icon-512.png`）是一枚料盘造型，
青绿渐变圆角方块 + 盘绕的料丝，可直接用作 Unraid 的容器图标。

## 架构与数据来源

```
拓竹打印机 + AMS 2 Pro
        │
        ├──(云 MQTT，实时状态)──┐
        │                      ▼
        │            ┌──────────────────────┐
        └─(云端任务记录)──▶│  主服务（Docker 容器）  │
                               │  · 状态解析与任务跟踪   │
                               │  · 料盘库存与槽位绑定   │
                               │  · 自动扣重引擎        │
                               │  · 中文 Web 界面       │
                               └──────────────────────┘
```

**克重数据来自拓竹云的 `GET /v1/user-service/my/tasks` 接口**，每条任务记录带
`weight`（本次总克重）和 `amsDetailMapping[]`（每个槽位的克重）。
这是切片软件计算的理论值（体积 × 密度），精度在 **0.1 g 量级**。

实时状态（槽位余量、温度、进度、报错）走拓竹云 MQTT，只读、不受 2025 年固件签名限制影响。

## 快速开始

```bash
git clone https://github.com/mjy378283319/bambu-spool.git
cd bambu-spool

# 方式一：直接拉预构建镜像（推荐）
docker compose up -d

# 方式二：从源码本地构建（拉不动 ghcr 时用这个）
docker compose -f docker-compose.build.yml up -d --build
```

打开 `http://NAS地址:8971`：

1. 首次打开会要求**创建管理员账号**（账号 + 密码，密码至少 8 位）。创建后此入口自动关闭
2. 用该账号登录 → 进「设置」→ 填拓竹账号密码 → 登录拓竹（中国大陆账号选「中国大陆」区域）
3. 点「同步设备」，打印机就出现了
4. 回「仪表盘」，点 AMS 槽位，把槽位绑定到对应料盘
5. 之后每次打印都会自动记账

### 在 Unraid 上部署

**A. Compose Manager 插件（推荐）**

1. 应用 → Community Applications，装 `Compose Manager`
2. Docker 页面 → Compose Manager → `Add New Stack`，命名 `bambu-spool`
3. 粘贴仓库里 `docker-compose.yml` 的内容，把 `./data` 改成 `/mnt/user/appdata/bambu-spool`
4. 点 `Compose Up`

**B. 在 Unraid 终端里跑**

```bash
mkdir -p /mnt/user/appdata/bambu-spool && cd /mnt/user/appdata/bambu-spool
git clone https://github.com/mjy378283319/bambu-spool.git repo
cd repo && docker compose up -d
```

**C. 图形界面手工建容器**

Docker 页面 → Add Container，按下面填：

| 字段 | 值 |
|---|---|
| Repository | `ghcr.io/mjy378283319/bambu-spool:latest` |
| Network Type | `Bridge` |
| Port | `8971` → `8971`（TCP） |
| Path | `/data` → `/mnt/user/appdata/bambu-spool` |
| Variable | `BAMBU_REGION` = `china` |
| Variable | `PUID` = `99` |
| Variable | `PGID` = `100` |
| Variable | `TASK_POLL_INTERVAL` = `60` |

> **拉取报 `denied` 怎么办**：说明 GHCR 上的包还是私有状态。去
> `https://github.com/users/mjy378283319/packages/container/bambu-spool/settings`
> 把 Visibility 改成 Public；或者先 `docker login ghcr.io` 再拉。

> **`PUID` / `PGID` 是干什么的**：容器启动时会先把数据目录改成这两个身份所有，
> 再以该身份运行程序。Unraid 的 appdata 归 `nobody:users`（99:100），
> 保持默认即可；在普通 Linux 上通常要改成 `1000:1000`。
> 设成 `0` 表示不降权、直接以 root 运行。

### 没有打印机也想先看看效果

```bash
docker run --rm -p 8971:8971 -e BAMBU_MOCK=1 ghcr.io/mjy378283319/bambu-spool:latest
```

模拟模式会虚拟一台 P2S + AMS 2 Pro，循环跑「准备 → 打印 → 完成」，
扣重链路完全真实，可以用来验证部署是否正常。

## 配置项

| 变量 | 默认 | 说明 |
|---|---|---|
| `DATA_DIR` | `/data` | 数据目录，**必须持久化**（存 SQLite 和加密密钥） |
| `PORT` | `8971` | 监听端口 |
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

### 挂到公网（Lucky / Nginx 反代）

应用自带完整的账号密码认证，暴露到公网前确认以下几点：

| 变量 | 默认 | 说明 |
|---|---|---|
| `TRUST_PROXY` | `true` | 信任反代传来的 `X-Forwarded-*` 头，挂在 Lucky/Nginx 后面必须保持开启 |
| `REQUIRE_HTTPS` | `false` | 设为 `true` 后，检测到外部是 http 会 308 跳转到 https。**公网强烈建议开启**，且反代要正确传递 `X-Forwarded-Proto` |
| `COOKIE_SECURE` | `auto` | 会话 Cookie 的 Secure 标志。`auto` 会按实际协议自动判断，一般不用动 |
| `ALLOW_PUBLIC_SETUP` | `false` | 是否允许从公网 IP 完成「首次创建管理员」。默认只允许内网直连，防止服务刚上线就被陌生人抢注账号 |
| `ALLOWED_ORIGINS` | 空 | 跨站写操作检查的白名单，非浏览器客户端需要时填，逗号分隔 |

推荐的上线路径：

1. 先在内网打开 `http://NAS地址:8971`，**创建好管理员账号**（此时 `ALLOW_PUBLIC_SETUP=false` 也能创建）
2. 再用 Lucky 把域名反代到 8971 端口，并在容器环境变量里加 `REQUIRE_HTTPS=true`
3. 登录接口有失败锁定（默认 5 次 / 15 分钟），密码走 PBKDF2 存储，会话 Cookie 为 HttpOnly
| `DATABASE_URL` | SQLite | 可换 PostgreSQL |

完整列表见 [.env.example](.env.example)。

## 更新版本

镜像由 GitHub Actions 在每次推送到 `main` 时自动构建，标签 `latest`：

```bash
docker compose pull && docker compose up -d
```

数据在 `/data` 卷里，更新不会丢。想锁版本可以用 `sha-xxxxxxx` 或 `v1.0.0` 这类标签。

## 关于拓竹账号与隐私

- 登录用的是拓竹官方云接口，和 Bambu Studio / Handy 走的是同一套。
- **密码只有在勾选「保存密码」时才会存到本地**，且用数据目录里的密钥文件做 Fernet 加密；
  不保存密码则令牌过期后需要重新登录一次（约 24 小时一次）。
- 本项目**只读**：不发送打印指令、不上传任何东西到拓竹云之外的第三方。
- 所有记录都存在你自己的数据库里。

## 重要限制（请务必了解）

| 限制 | 影响 | 应对 |
|---|---|---|
| 打印任务必须**经拓竹云端发起** | Bambu Studio 云端发送、Bambu Handy 都没问题；**局域网模式本地发送、U 盘打印不会进云端记录**，拿不到克重 | 在「打印记录」里手动录入用量，或改用云端发起 |
| 克重是切片估算值 | 精度 0.1 g 量级，不是称重实测 | 定期用「称重校准」按实际秤读数修正 |
| 非实时 | 打印结束后要等一个轮询周期才扣重 | 调小 `TASK_POLL_INTERVAL` |
| 扣重依赖槽位绑定正确 | 没绑定的槽位只记流水、不动任何料盘 | 在仪表盘把槽位绑好；绑错了可在详情页转移 |
| AMS `remain` 只有整数百分比 | 1 kg 料盘 1% ≈ 10 g，只能做粗略参考 | 余量以本系统的克重台账为准 |

## 本地开发

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

BAMBU_MOCK=1 python -m uvicorn app.main:app --reload --port 8971

# 跑端到端自测（32 项断言，不需要真实打印机）
python tests/test_flow.py

# 访问控制与登录流程（63 项断言，会真起一个 uvicorn 子进程）
python tests/test_auth.py

# 图片识色的配色匹配（77 项断言，CIEDE2000 用 Sharma 标准向量校验）
python tests/test_color.py

# 每盘价格 / 耗材总价值 / 每次打印耗材费（21 项断言）
python tests/test_price.py

# 料盘删除保护、品牌归一与历史数据迁移（55 项断言）
python tests/test_admin.py

# AMS / AMS HT 编号归一、槽位克重折算、位串越界保护（57 项断言）
python tests/test_ams.py

# 拓竹云接口地址与验证码登录状态流转（23 项断言，全程离线）
python tests/test_cloud_endpoints.py
```

代码结构：

```
app/
├─ cloud/     拓竹云 HTTP 客户端、云 MQTT 连接、模拟数据源
├─ core/      状态解析、任务状态机、扣重引擎、中枢编排
├─ api/       REST 接口与 WebSocket
├─ catalog.py 机型 / 材料 / 皮重 / 颜色 / HMS 错误码对照表
├─ colors.py  色彩工具（Lab 转换、CIEDE2000 色差、配色匹配）
└─ static/    无构建步骤的前端（原生 HTML/CSS/JS）
```

## 路线图

- [ ] 打印机侧中继（同局域网部署时走 FTPS 读切片文件，拿到实测 0.1 g 实时扣重）
- [x] 耗材成本统计与报价（每盘价格、耗材总价值、库存余值、每次打印耗材费）
- [x] 料盘删除与归档（带流水保护，删除时清理引用）
- [x] 品牌写法归一（中英/变体合并为一，老库自动迁移）
- [x] 界面重构与应用图标
- [x] 设备面板重做（AMS / AMS HT / 外挂料盘槽位可视化、打印状态、温度与风扇）
- [ ] Bambu Studio 预设导出
- [ ] 多用户
- [ ] 摄像头画面

## 致谢与参考

协议与接口事实均来自以下开源项目的源码与文档，感谢这些作者：

- [greghesp/ha-bambulab](https://github.com/greghesp/ha-bambulab)（MIT）—— 云客户端、MQTT 字段、机型与 HMS 表
- [Doridian/OpenBambuAPI](https://github.com/Doridian/OpenBambuAPI)（GFDL）—— 协议文档
- [coelacant1/Bambu-Lab-Cloud-API](https://github.com/coelacant1/Bambu-Lab-Cloud-API) —— 云 API 字段
- [Donkie/Spoolman](https://github.com/Donkie/Spoolman)（MIT）—— 数据模型参考
- [Rdiger-36/bambulab-ams-spoolman-filamentstatus](https://github.com/Rdiger-36/bambulab-ams-spoolman-filamentstatus)（GPL-3.0）—— 切片文件扣重思路

本项目代码全部独立编写，未复制上述项目的源码。

## 许可

MIT
