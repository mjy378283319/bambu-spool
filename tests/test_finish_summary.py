"""外观字段、自定义品牌、区域显示与耗材汇总自测。

覆盖（全部对应一轮真实用户反馈）：
  1. 外观（finish）是数据库里的真列，不是接口层现算的假字段：
     normalize_finish / infer_finish 的口径、建单改单能落库、_migrate_finish 回填老库
  2. 自定义品牌：存 Setting 表（升级镜像不丢），可增可删，删了不影响已录料盘
  3. 区域显示：/api/system/status 的 account.region 必须带出来 ——
     少了这一项前端拿到 undefined，设置页就永远显示「海外」（用户原话：
     「为什么我的账户显示是海外」）
  4. 统计接口 /api/stats：
     - 「今天 / 本周」按客户端时区切（东八区晚上看到的今天不能被算进 UTC 的昨天）
     - by_brand / by_material_detail / by_finish 三个分组汇总的数字要对得上

运行： python tests/test_finish_summary.py
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ["BAMBU_MOCK"] = "1"
os.environ["DATA_DIR"] = os.path.join(ROOT, "data", "testfinish")
os.environ["ALLOW_PUBLIC_SETUP"] = "1"

from sqlmodel import select  # noqa: E402

from app.api import routes  # noqa: E402
from app.catalog import FINISH_PRESETS, build_spool_name, infer_finish, normalize_finish  # noqa: E402
from app.db import _migrate_finish, engine, init_db, session_scope  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Spool, UsageRecord  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

PASSED: list[str] = []
FAILED: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(label)
        print(f"  [通过] {label}")
    else:
        FAILED.append(label)
        print(f"  [失败] {label} {detail}")


def reset() -> None:
    try:
        engine.dispose()
    except Exception:
        pass
    data_dir = os.environ["DATA_DIR"]
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir, ignore_errors=True)
    os.makedirs(data_dir, exist_ok=True)
    init_db()


# ── 1. 外观归一 / 推断 ───────────────────────────────────────────
def test_finish_pure() -> None:
    print("== 外观归一与推断（纯函数） ==")
    check("外观预设无重复", len(FINISH_PRESETS) == len(set(FINISH_PRESETS)), str(FINISH_PRESETS))
    check("预设第一项是「普通」（默认值）", FINISH_PRESETS[0] == "普通", str(FINISH_PRESETS))

    for raw, want in [
        ("matte", "哑光"), ("MATT", "哑光"), ("silk", "丝绸"), ("丝滑", "丝绸"),
        ("glossy", "亮面"), ("半透明", "半透"), ("translucent", "半透"),
        ("哑光", "哑光"), ("", ""), ("   ", ""),
    ]:
        got = normalize_finish(raw)
        check(f"normalize_finish({raw!r}) -> {want!r}", got == want, f"实际 {got!r}")

    # 未收录的写法原样保留：用户自己写在颜色名里的工艺不该被吃掉
    check("未收录写法原样返回", normalize_finish("电镀镜面") == "电镀镜面", normalize_finish("电镀镜面"))

    for text, want in [
        ("丝绸白", "丝绸"), ("丝滑白", "丝绸"), ("PLA Silk 金", "丝绸"),
        ("哑光黑", "哑光"), ("Matte 黑", "哑光"),
        ("磨砂红", "磨砂"), ("金属银", "金属"), ("珠光白", "珠光"),
        ("碳纤黑", "碳纤"), ("夜光绿", "夜光"), ("木纹棕", "木纹"),
        ("亮面黑", "亮面"), ("双色红蓝", "双色"), ("彩虹渐变", "渐变"),
        ("普通黑", "普通"), ("黑色", "普通"), ("", "普通"),
    ]:
        got = infer_finish(text)
        check(f"infer_finish({text!r}) -> {want}", got == want, f"实际 {got}")

    # 关键词顺序敏感，这两条是踩过的坑，钉死防回归
    check("「半透明黑」判半透而不是透明", infer_finish("半透明黑") == "半透", infer_finish("半透明黑"))
    check("「丝绸哑光白」判丝绸而不是哑光", infer_finish("丝绸哑光白") == "丝绸", infer_finish("丝绸哑光白"))

    # 默认名：只有非「普通」才把外观写进名字，免得满屏「普通 黑色」
    plain = build_spool_name("拓竹", "PLA", "黑色")
    check("普通外观不进默认名", "普通" not in plain, plain)
    check("非普通外观进默认名", "哑光" in build_spool_name("拓竹", "PLA", "黑色", "哑光"),
          build_spool_name("拓竹", "PLA", "黑色", "哑光"))
    check("外观为空时等于普通", build_spool_name("拓竹", "PLA", "黑色", "") == plain)


# ── 2. 迁移：给老库回填外观 ──────────────────────────────────────
def test_migration() -> None:
    print("== _migrate_finish：老库回填 ==")
    reset()
    with session_scope() as session:
        # 直接写 finish=""，模拟升级前的库（那时这一列还不存在）
        session.add(Spool(name="丝绸白", brand="拓竹", material="PLA", color_name="丝绸白",
                          color_hex="#FFFFFF", initial_weight=1000.0, remaining_weight=900.0,
                          finish=""))
        session.add(Spool(name="哑光黑", brand="拓竹", material="PLA", color_name="哑光黑",
                          color_hex="#1A1A1A", initial_weight=1000.0, remaining_weight=800.0,
                          finish=""))
        session.add(Spool(name="手工填过", brand="拓竹", material="PLA", color_name="黑色",
                          color_hex="#1A1A1A", initial_weight=1000.0, remaining_weight=700.0,
                          finish="珠光"))
        session.commit()

    _migrate_finish()
    with session_scope() as session:
        rows = {s.name: s.finish for s in session.exec(select(Spool)).all()}
    check("颜色名带工艺的回填成丝绸", rows.get("丝绸白") == "丝绸", str(rows))
    check("颜色名带工艺的回填成哑光", rows.get("哑光黑") == "哑光", str(rows))
    check("用户手填过的值不被覆盖", rows.get("手工填过") == "珠光", str(rows))

    # 幂等：再跑一次结果不变（升级流程里可能被调用多次）
    _migrate_finish()
    with session_scope() as session:
        again = {s.name: s.finish for s in session.exec(select(Spool)).all()}
    check("回填是幂等的", again == rows, f"{again} != {rows}")


# ── 3. HTTP：外观落库 + 自定义品牌 ───────────────────────────────
def test_http_finish_and_brands() -> None:
    print("== HTTP：外观落库 / 自定义品牌 ==")
    reset()
    client = TestClient(app)
    client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})

    r = client.post("/api/spools", json={
        "brand": "Polymaker", "material": "PLA", "color_name": "丝绸白",
        "color_hex": "#F4F1EA", "finish": "silk",
        "initial_weight": 1000, "price": 120.0,
    })
    check("建单成功", r.status_code == 200, r.text)
    body = r.json()
    check("外观写入时已归一（silk -> 丝绸）", body.get("finish") == "丝绸", str(body.get("finish")))
    check("默认名带上外观", "丝绸" in body.get("name", ""), str(body.get("name")))
    sid = body["id"]

    r = client.patch(f"/api/spools/{sid}", json={"finish": "哑光"})
    check("改单能改外观", r.status_code == 200 and r.json().get("finish") == "哑光", r.text)

    r = client.post("/api/spools", json={
        "brand": "拓竹", "material": "PLA", "color_name": "黑色",
        "color_hex": "#1A1A1A", "initial_weight": 1000,
    })
    check("不填外观默认「普通」", r.json().get("finish") == "普通", str(r.json().get("finish")))

    # 目录接口要给出外观候选，前端下拉靠它
    r = client.get("/api/catalog")
    check("catalog 带 finishes", r.status_code == 200 and "丝绸" in r.json().get("finishes", []), r.text[:200])
    check("catalog 带 preset_brands", "拓竹" in r.json().get("preset_brands", []), r.text[:200])
    r = client.get("/api/spools?archived=false")
    finishes = {s["finish"] for s in r.json().get("spools", [])}
    check("列表里能看到外观", "哑光" in finishes and "普通" in finishes, str(finishes))

    # 自定义品牌
    r = client.post("/api/brands", json={"name": "自家作坊"})
    check("新增自定义品牌", r.status_code == 200 and "自家作坊" in r.json().get("custom_brands", []), r.text)
    r = client.post("/api/brands", json={"name": "自家作坊"})
    check("重复新增不产生重复项",
          r.json().get("custom_brands", []).count("自家作坊") == 1, str(r.json().get("custom_brands")))
    r = client.post("/api/brands", json={"name": "  "})
    check("空品牌名被拒", r.status_code == 400, str(r.status_code))

    r = client.get("/api/catalog")
    brands = r.json().get("brands", [])
    check("自定义品牌进了候选", "自家作坊" in brands, str(brands))
    check("候选末尾是「其他」", brands[-1] == "其他", str(brands))
    check("已删除的品牌不在候选里",
          not any(b in brands for b in ("eSUN 易生", "三绿 Sunlu", "Overture", "Prusament")), str(brands))

    r = client.delete("/api/brands/自家作坊")
    check("删除自定义品牌", r.status_code == 200 and "自家作坊" not in r.json().get("custom_brands", []), r.text)
    with session_scope() as session:
        still = session.get(Spool, sid)
    check("删品牌不影响已录料盘", still is not None and still.finish == "哑光", str(still and still.finish))

    # 自定义品牌要活过「重启」：它存 Setting 表，不在内存里
    from app.brands import load_custom_brands
    client.post("/api/brands", json={"name": "重启测试牌"})
    with session_scope() as session:
        check("自定义品牌落在 Setting 表里（升级 / 重启都不丢）",
              "重启测试牌" in load_custom_brands(session), str(load_custom_brands(session)))


# ── 4. HTTP：区域显示 ────────────────────────────────────────────
def test_region() -> None:
    print("== 区域显示（设置页「中国大陆 / 海外」的数据源） ==")
    reset()
    client = TestClient(app)
    client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})

    r = client.get("/api/system/status")
    check("status 200", r.status_code == 200, str(r.status_code))
    body = r.json()
    check("顶层带 region", body.get("region") in ("china", "global"), str(body.get("region")))
    account = body.get("account") or {}
    # 就是这一条：漏了它前端 `undefined === "china"` 为假，永远显示「海外」
    check("account.region 存在（不是 undefined）",
          "region" in account and account.get("region") in ("china", "global"), str(account))
    check("account.region 与顶层一致", account.get("region") == body.get("region"),
          f"{account.get('region')} vs {body.get('region')}")

    # 未登录拓竹账号时不该崩，也不该假装切成功
    r = client.post("/api/account/region", json={"region": "global"})
    check("未登录时切区域被明确拒绝（400）", r.status_code == 400, f"{r.status_code} {r.text[:120]}")
    r = client.post("/api/account/region", json={"region": "mars"})
    check("非法区域被拒", r.status_code == 400, f"{r.status_code} {r.text[:120]}")


# ── 5. 统计：时区与分组汇总 ──────────────────────────────────────
def test_timezone_helpers() -> None:
    print("== 时区换算（「今天 / 本周」的边界） ==")
    tz8 = routes._client_tz(480)     # 北京时间
    tz0 = routes._client_tz(0)       # UTC

    check("北京时间 = UTC+8", tz8.utcoffset(None) == timedelta(hours=8), str(tz8.utcoffset(None)))
    check("分钟数被夹到 ±14 小时以内", routes._client_tz(99999).utcoffset(None) == timedelta(hours=14))
    check("负数也被夹住", routes._client_tz(-99999).utcoffset(None) == timedelta(hours=-14))

    # 直接调用接口函数时 FastAPI 的默认值是个 Query 对象，转不动就退回 UTC，
    # 不能让整个统计接口 500（这个坑真踩过）
    class _FakeQuery:
        pass

    check("拿到非数字（Query 默认值）时退回 UTC，不抛异常",
          routes._client_tz(_FakeQuery()).utcoffset(None) == timedelta(0))
    check("None 退回 UTC", routes._client_tz(None).utcoffset(None) == timedelta(0))

    # 东八区晚上 8 点 = UTC 12 点；东八区凌晨 4 点那天在 UTC 还是前一天晚上
    check("UTC 00:30 在北京是当天", routes._local_day(datetime(2026, 1, 1, 0, 30), tz8) == "2026-01-01")
    check("UTC 20:00 在北京已经跨到第二天",
          routes._local_day(datetime(2026, 1, 1, 20, 0), tz8) == "2026-01-02")
    check("同一个时刻在 UTC 还是 1 月 1 日",
          routes._local_day(datetime(2026, 1, 1, 20, 0), tz0) == "2026-01-01")
    check("时间为空返回空串", routes._local_day(None, tz8) == "")

    today_local = datetime.now(timezone.utc).astimezone(tz8).date()
    start1 = routes._local_day_start(1, tz8).replace(tzinfo=timezone.utc).astimezone(tz8)
    check("最近 1 天 = 今天零点", start1.date() == today_local and (start1.hour, start1.minute) == (0, 0),
          str(start1))
    start7 = routes._local_day_start(7, tz8).replace(tzinfo=timezone.utc).astimezone(tz8)
    check("最近 7 天含今天（起点是 6 天前的零点）",
          start7.date() == today_local - timedelta(days=6), f"{start7.date()} vs {today_local}")
    check("返回的是 naive UTC（库里就是这么存的）",
          routes._local_day_start(7, tz8).tzinfo is None)


def test_stats_summary() -> None:
    print("== /api/stats：本周 + 按品牌 / 材料 / 外观汇总 ==")
    reset()
    client = TestClient(app)
    client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})

    seed = [
        # 品牌, 材料, 外观, 满盘, 剩余, 已用, 价格
        ("拓竹", "PLA", "普通", 1000.0, 600.0, 400.0, 100.0),
        ("拓竹", "PLA", "哑光", 1000.0, 200.0, 800.0, 120.0),
        ("Polymaker", "PETG", "丝绸", 1000.0, 900.0, 100.0, 150.0),
    ]
    ids = []
    for brand, material, finish, initial, remaining, used, price in seed:
        r = client.post("/api/spools", json={
            "brand": brand, "material": material, "color_name": f"{finish}测试",
            "color_hex": "#888888", "finish": finish,
            "initial_weight": initial, "remaining_weight": remaining,
            "used_weight": used, "price": price,
        })
        assert r.status_code == 200, r.text
        ids.append(r.json()["id"])

    # 本周的一笔打印：一个已完成任务 + 一条自动扣重流水
    now = datetime.utcnow()
    with session_scope() as session:
        session.add(UsageRecord(spool_id=ids[0], weight_g=120.0, source="auto",
                                note="本周打印", created_at=now))
        session.add(UsageRecord(spool_id=ids[1], weight_g=30.0, source="manual",
                                note="本周手动", created_at=now))
        session.commit()

    # 走 HTTP 调接口：顺带验证 tz_minutes 这个查询参数能被解析出来
    r = client.get("/api/stats?tz_minutes=480")
    check("stats 200（带 tz_minutes）", r.status_code == 200, r.text[:200])
    st = r.json()

    week = st.get("week") or {}
    check("返回 week 区块", bool(week), str(list(st.keys())))
    check("week.days = 7", week.get("days") == 7, str(week))
    check("week.used_g 只算本周的 auto/manual 流水",
          abs(week.get("used_g", 0) - 150.0) < 0.01, str(week.get("used_g")))
    check("week.week_start 是 naive UTC 字符串", "T" in str(week.get("start", "")), str(week.get("start")))
    for key in ("print_seconds", "print_hours", "success_count", "job_count"):
        check(f"week 带 {key}", key in week, str(week))

    # 分组汇总：盘数 / 价格 / 余量都要对得上
    by_brand = {row["name"]: row for row in st.get("by_brand", [])}
    check("按品牌分组：拓竹 2 盘", by_brand.get("拓竹", {}).get("count") == 2, str(by_brand))
    check("按品牌分组：拓竹采购额 220", abs(by_brand.get("拓竹", {}).get("price", 0) - 220.0) < 0.01,
          str(by_brand.get("拓竹")))
    check("按品牌分组：拓竹剩余 800g",
          abs(by_brand.get("拓竹", {}).get("remaining_g", 0) - 800.0) < 0.01, str(by_brand.get("拓竹")))
    check("按品牌分组：余量百分比 = 剩余/满盘",
          abs(by_brand.get("拓竹", {}).get("remaining_percent", 0) - 40.0) < 0.01,
          str(by_brand.get("拓竹")))
    check("按品牌分组：Polymaker 1 盘", by_brand.get("Polymaker", {}).get("count") == 1, str(by_brand))

    by_material = {row["name"]: row for row in st.get("by_material_detail", [])}
    check("按材料分组：PLA 2 盘", by_material.get("PLA", {}).get("count") == 2, str(by_material))
    check("按材料分组：PETG 1 盘", by_material.get("PETG", {}).get("count") == 1, str(by_material))

    by_finish = {row["name"]: row for row in st.get("by_finish", [])}
    check("按外观分组：普通 / 哑光 / 丝绸各 1 盘",
          all(by_finish.get(k, {}).get("count") == 1 for k in ("普通", "哑光", "丝绸")), str(by_finish))
    check("按外观分组的三个键都在", set(by_finish) == {"普通", "哑光", "丝绸"}, str(set(by_finish)))

    # 删掉的盘不该再算进库存汇总（库里的料盘列表本身是留着的）
    before = len(by_brand)
    r = client.delete(f"/api/spools/{ids[2]}?force=true")
    check("删除料盘成功", r.status_code == 200, r.text[:120])
    r = client.get("/api/stats")
    check("不传 tz_minutes 也能正常返回（按 UTC 切）", r.status_code == 200, r.text[:120])
    by_brand2 = {row["name"]: row for row in r.json().get("by_brand", [])}
    check("已删除料盘从品牌汇总里消失", "Polymaker" not in by_brand2, str(by_brand2))
    check("品牌分组少了一组", len(by_brand2) == before - 1, f"{len(by_brand2)} vs {before}")
    check("其它分组的数字没被带歪",
          by_brand2.get("拓竹", {}).get("count") == 2, str(by_brand2))


# ── 主流程 ───────────────────────────────────────────────────────
def main() -> int:
    test_finish_pure()
    test_migration()
    test_http_finish_and_brands()
    test_region()
    test_timezone_helpers()
    test_stats_summary()

    print("")
    print("=" * 58)
    if FAILED:
        print(f"通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
        print(f"失败项： {FAILED}")
        return 1
    print(f"通过 {len(PASSED)} 项，失败 0 项")
    print("=" * 58)
    return 0


if __name__ == "__main__":
    sys.exit(main())
