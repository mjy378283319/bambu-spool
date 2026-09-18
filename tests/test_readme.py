"""README 的自检：图片打不开、数字过期、文档引用腐烂，这三类都要钉住。

单独跑：python tests/test_readme.py

为什么要有这个文件：
- **图片打不开**：README 里写相对路径 `docs/x.png`，GitHub 会把它解析到
  `raw.githubusercontent.com`，这个域名在国内常被污染 → 用户看到的就是一片空白。
  所以图片必须是 https 绝对地址，且走 jsDelivr，并且反解出的仓库路径真有文件。
- **数字过期**：品牌色卡的总数/分品牌色数是手工写的，加过一次色卡就会对不上
  （这次就发现写的是「122 系列 1564 色」，实际是 132 / 1661）。
  所以直接拿 `catalog.BRAND_COLOR_SERIES` 的实际统计来比对。
- **文档腐烂**：本地开发那一节列了十几个测试命令，新增/改名测试后很容易漏改，
  于是把「命令里的文件存在」和「tests/ 下的文件都被列到」两个方向都断言一遍。
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

PASSED: list[str] = []
FAILED: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(label)
        print(f"  ✓ {label}" + (f"  ({detail})" if detail else ""))
    else:
        FAILED.append(label)
        print(f"  ✗ {label}" + (f"  ({detail})" if detail else ""))


def readme_text() -> str:
    with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as fh:
        return fh.read()


REPO = "mjy378283319/bambu-spool"


# ── 一、图片：必须是能打开的绝对直链 ────────────────────────────────
print("\n[1] 图片直链")
md = readme_text()
images = re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", md)
check("README 里至少有三张截图", len(images) >= 3, f"{len(images)} 张")

relative = [u for u in images if not u.startswith("http")]
check("没有相对路径的图片（相对路径会被解析到常被污染的 raw 域名）",
      not relative, str(relative))

# 图片 src 必须是 https 且走 jsDelivr。raw.githubusercontent.com 只在「容器图标」那节
# 作为备选写在代码块里，不该出现在 markdown 图片语法里。
#
# ⚠️ 域名必须是 **gcore**.jsdelivr.net。默认的 cdn.jsdelivr.net 对 `/gh/` 路径会 301 到
# raw.githubusercontent.com，国内 DNS 污染下那一步就断了 —— 现象是「README 图片全打不开」，
# 而 curl 看 cdn 那条只显示 301，很容易误判成「链接写错了」。
# gcore 节点直接回源，实测 200 / image/png。别改回 cdn。
CDN_HOST = "gcore.jsdelivr.net"
check("图片全是 https 绝对地址", all(u.startswith("https://") for u in images))
cdn = [u for u in images if u.startswith(f"https://{CDN_HOST}/gh/{REPO}@")]
check(f"图片全部走 {CDN_HOST} CDN", len(cdn) == len(images), f"{len(cdn)}/{len(images)}")
old_cdn = [u for u in images if u.startswith("https://cdn.jsdelivr.net/")]
check("没有用会 301 到 raw 域名的 cdn.jsdelivr.net（国内打不开）",
      not old_cdn, str(old_cdn))
raw_src = [u for u in images if "raw.githubusercontent.com" in u]
check("图片 src 里没有 raw.githubusercontent.com", not raw_src, str(raw_src))

# 反解出仓库路径，逐个确认文件真的存在——链接写错和文件不存在是一回事
missing = []
for url in images:
    m = re.search(re.escape(CDN_HOST) + r"/gh/" + re.escape(REPO) + r"@[^/]+/([^?\s]+)", url)
    rel = m.group(1) if m else None
    if not rel or not os.path.isfile(os.path.join(ROOT, rel)):
        missing.append(rel or url)
check("每张图反解出的仓库路径都真实存在", not missing, str(missing))

# 顶部第一张就是仪表盘（用户最先看到的那张）
check("首图是仪表盘截图", "screenshot-dashboard.png" in images[0], images[0])


# ── 二、锚点与章节 ────────────────────────────────────────────────
print("\n[2] 锚点与章节")
headings = re.findall(r"^#{1,6}\s+(.+?)\s*$", md, re.M)


def slug(title: str) -> str:
    """GitHub 的标题锚点：小写、空格转 -、只留字母数字和部分符号。"""
    s = title.strip().lower()
    s = re.sub(r"[`*_.()\[\]（）·/｜|、：:,，。！!？?~「」“”\"']", "", s)
    s = re.sub(r"\s+", "-", s)
    return s


slugs = {slug(h) for h in headings}
anchors = re.findall(r"\]\(#([^)]+)\)", md)
bad_anchor = [a for a in anchors if a not in slugs]
# 先断言「确实有锚点」——不写这条的话，锚点全被删光时 not bad_anchor 依然为真
check("README 里确有内部锚点", len(anchors) >= 1, f"{len(anchors)} 个")
check("所有内部锚点都指向真实存在的标题", bool(anchors) and not bad_anchor, str(bad_anchor))

required = ["它解决什么问题", "功能", "数据来源", "快速开始", "配置项",
            "部署到 Unraid", "重要限制", "本地开发", "路线图", "许可"]
# 标题可能带括号后缀（如「重要限制（请务必了解）」），按前缀匹配
absent = [t for t in required if not any(h == t or h.startswith(t + "（") for h in headings)]
check("必备章节齐全", not absent, str(absent))


# ── 三、色卡数字：直接跟代码里的数据对 ─────────────────────────────
print("\n[3] 品牌色卡数字")
from app.catalog import BRAND_COLOR_SERIES  # noqa: E402

real = {brand: (len(series), sum(len(v) for v in series.values()))
        for brand, series in BRAND_COLOR_SERIES.items()}

m = re.search(r"(\d+)\s*个品牌\s*·\s*(\d+)\s*个系列\s*·\s*(\d+)\s*个色号", md)
check("README 写了色卡总数", m is not None)
if m:
    b, s_, c = (int(x) for x in m.groups())
    rb, rs, rc = len(real), sum(v[0] for v in real.values()), sum(v[1] for v in real.values())
    check("品牌总数与代码一致", b == rb, f"README {b} / 代码 {rb}")
    check("系列总数与代码一致", s_ == rs, f"README {s_} / 代码 {rs}")
    check("色号总数与代码一致", c == rc, f"README {c} / 代码 {rc}")

# 分品牌那张表：品牌集合、系列数、色号数都要对得上
# 小节被删掉时不要抛 IndexError——那只会让整个测试崩掉，看不出是哪一条不达标
parts = md.split("### 品牌配色卡", 1)
sec = parts[1].split("\n###", 1)[0] if len(parts) > 1 else ""
check("README 有「品牌配色卡」小节且带分品牌表", bool(sec) and "| 品牌 |" in sec)
rows = re.findall(r"^\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", sec, re.M)
check("品牌表里至少列了 10 个品牌", len(rows) >= 10, f"{len(rows)} 行")
listed = {name: (int(a), int(b)) for name, a, b in rows}
check("表里没多写代码里没有的品牌",
      set(listed) <= set(real), str(set(listed) - set(real)))
check("代码里的品牌一个都没漏写",
      set(real) <= set(listed), str(set(real) - set(listed)))
for name, (ns, nc) in listed.items():
    if name in real:
        check(f"{name} 的系列/色号与代码一致",
              real[name] == (ns, nc), f"README {ns}/{nc} 代码 {real[name][0]}/{real[name][1]}")


# ── 四、文档里引用的文件与符号真的存在 ─────────────────────────────
print("\n[4] 引用就位")
rel_paths = [
    ".env.example", "docker-compose.yml", "docker-compose.build.yml",
    "icon.png", "icon.svg", "app/main.py", "app/catalog.py",
    "app/static/vendor/jsQR.js", "app/static/vendor/LICENSE-jsQR.txt",
    "scripts/build_printer_photo.py", "scripts/shot_ui.mjs",
    "scripts/seed_demo_job.py",
]
for rel in rel_paths:
    check(f"README 提到的 {rel} 存在", os.path.exists(os.path.join(ROOT, rel)))
check("README 提到的 app/static/printer/ 目录存在",
      os.path.isdir(os.path.join(ROOT, "app", "static", "printer")))

# 指到源码里的函数名，改名字后文档就会说谎
main_py = open(os.path.join(ROOT, "app", "main.py"), encoding="utf-8").read()
check("app/main.py 里真有 _harden()", "def _harden(" in main_py)
scan_js = open(os.path.join(ROOT, "app", "static", "scan.js"), encoding="utf-8").read()
check("scan.js 里真有 policyBlocksCamera()", "policyBlocksCamera" in scan_js)


# ── 五、本地开发那一节的命令没有腐烂 ───────────────────────────────
print("\n[5] 开发命令")
cmds = re.findall(r"^\s*(?:python|node)\s+((?:tests|scripts)/[\w./]+\.(?:py|mjs))", md, re.M)
check("README 列出了测试命令", len(cmds) >= 10, f"{len(cmds)} 条")
bad_cmd = [c for c in cmds if not os.path.isfile(os.path.join(ROOT, c))]
check("每条命令指向的文件都存在", not bad_cmd, str(bad_cmd))

have = sorted(
    f for f in os.listdir(os.path.join(ROOT, "tests"))
    if f.startswith("test_") and f.endswith((".py", ".mjs"))
)
unlisted = [f for f in have if f"tests/{f}" not in md]
check("tests/ 下每个测试文件都在 README 里出现过", not unlisted, str(unlisted))


# ── 六、别再胀回去 ────────────────────────────────────────────────
print("\n[6] 篇幅")
lines = md.splitlines()
# 历史上是 671 行 / 21.7k 字符，大半是「为什么这么做」的铺陈，2026-09-16 精简到
# 约 400 行 / 15k 字符。这两条上界就是防它再胀回去——把旧版拷回来必然红。
check("README 不超过 440 行", len(lines) <= 440, f"{len(lines)} 行")
check("README 不超过 16000 字符", len(md) <= 16000, f"{len(md)} 字符")
check("没有 CRLF 换行（.gitattributes 要求 eol=lf）", "\r\n" not in md)

print(f"\n通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
if FAILED:
    for label in FAILED:
        print(f"  - {label}")
    sys.exit(1)
