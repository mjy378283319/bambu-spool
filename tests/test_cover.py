"""打印成果图（云端 cover 抓取 / 本地缓存 / 接口）自测。

覆盖：
  - save_cover：正常 png 落盘、文件名带 job_id、扩展名按 URL 推断
  - save_cover：非 200 / 非图片 content-type / 太小 / 空 URL / 空 job_id → 返回空串且不落盘
  - save_cover：网络异常被吞住（**扣重不能因为抓图挂了而失败**）
  - cover_media_type：各扩展名 → MIME，认不出的退回 png
  - /api/jobs/{id}/cover：正常 200 + 正确 content-type；无图 404；文件丢失 404；未登录 401
  - /api/jobs/{id} 返回 cover_file / has_cover 字段（前端据此决定要不要请求图片）
  - 数据库迁移：PrintJob 老表补出 cover_file 列

运行： python tests/test_cover.py
"""
from __future__ import annotations

import os
import shutil
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ["BAMBU_MOCK"] = "1"
os.environ["DATA_DIR"] = os.path.join(ROOT, "data", "testcover")
os.environ["ALLOW_PUBLIC_SETUP"] = "1"

import httpx  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

from app.api import routes  # noqa: E402
from app.core import covers  # noqa: E402
from app.db import init_db, session_scope  # noqa: E402
from app.main import app  # noqa: E402
from app.models import PrintJob  # noqa: E402

PASSED: list[str] = []
FAILED: list[str] = []

PNG_BODY = b"\x89PNG\r\n\x1a\n" + b"\x00" * 800      # 够大、带真 PNG magic
TINY_BODY = b"\x89PNG\r\n\x1a\n"                     # 只有 8 字节


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSED.append(label)
        print(f"  [通过] {label}")
    else:
        FAILED.append(label)
        print(f"  [失败] {label} {detail}")


def reset() -> None:
    from app.db import engine
    try:
        engine.dispose()
    except Exception:
        pass
    data_dir = os.environ["DATA_DIR"]
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir, ignore_errors=True)
    os.makedirs(data_dir, exist_ok=True)
    init_db()


class FakeResp:
    def __init__(self, status: int = 200, body: bytes = PNG_BODY, ctype: str = "image/png"):
        self.status_code = status
        self.content = body
        self.headers = {"content-type": ctype}


def patch_httpx(monkey_target):
    """把 covers.httpx.get 换成返回 `monkey_target` 的桩。

    monkey_target 可以是 FakeResp，也可以是要抛的异常实例。
    """
    def _fake_get(url, **kwargs):
        if isinstance(monkey_target, BaseException):
            raise monkey_target
        return monkey_target
    covers.httpx.get = _fake_get


def restore_httpx() -> None:
    covers.httpx.get = httpx.get


def test_save_cover_ok() -> None:
    reset()
    url = "https://bbl-prod-model.oss-cn-shanghai.aliyuncs.com/private/x/plate_1.png?X-Amz-Expires=1800&sig=abc"
    patch_httpx(FakeResp())
    try:
        name = covers.save_cover(url, 7)
        check("save_cover 正常返回文件名", name == "7.png", repr(name))
        path = covers.cover_dir() / name
        check("save_cover 文件真的落盘", path.is_file(), str(path))
        check("save_cover 字节数一致", path.read_bytes() == PNG_BODY,
              str(path.stat().st_size if path.is_file() else "无文件"))
        # 扩展名要跟着 URL 走（带 query 也要认出来）
        for u, want in [
            ("https://x/a/plate_1.png?X-Amz-Signature=z", "11.png"),
            ("https://x/a/plate_2.JPG", "11.jpg"),
            ("https://x/a/plate_2.jpeg", "11.jpeg"),
            ("https://x/a/plate_3.webp", "11.webp"),
            ("https://x/a/noext?q=1", "11.png"),
        ]:
            got = covers.save_cover(u, 11)
            check(f"扩展名推断 {u.split('?')[0].rsplit('/', 1)[-1]}", got == want, f"{got} != {want}")
    finally:
        restore_httpx()


def test_save_cover_skips() -> None:
    reset()
    url = "https://x/plate_1.png"
    cases = [
        ("非 200", FakeResp(status=403, body=b"<error>", ctype="application/xml")),
        ("content-type 不是图片", FakeResp(ctype="text/html")),
        ("没有 content-type", FakeResp(ctype="")),
        ("内容太小（占位图/错误页）", FakeResp(body=TINY_BODY)),
    ]
    for label, resp in cases:
        patch_httpx(resp)
        try:
            name = covers.save_cover(url, 21)
            check(f"跳过：{label}", name == "", repr(name))
        finally:
            restore_httpx()
    check("跳过的用例一个文件都没留下", list(covers.cover_dir().glob("21.*")) == [],
          str(list(covers.cover_dir().glob("*"))))

    # 空 URL / 空 job_id：连请求都不该发
    calls: list[str] = []

    def _spy(u, **kw):
        calls.append(u)
        return FakeResp()

    covers.httpx.get = _spy
    try:
        check("空 URL 直接返回空串", covers.save_cover("", 5) == "")
        check("空 job_id 直接返回空串", covers.save_cover(url, 0) == "")
        check("空入参没有发起请求", calls == [], str(calls))
    finally:
        restore_httpx()


def test_save_cover_never_raises() -> None:
    """抓图失败绝不能让扣重崩掉——异常必须被吞住。"""
    reset()
    for label, exc in [
        ("连接失败", httpx.ConnectError("boom")),
        ("超时", httpx.ReadTimeout("slow")),
        ("DNS 挂了", httpx.ConnectError("getaddrinfo failed")),
        ("奇怪的异常", RuntimeError("unexpected")),
    ]:
        patch_httpx(exc)
        try:
            got = covers.save_cover("https://x/plate_1.png", 31)
            check(f"异常吞住不抛出：{label}", got == "", repr(got))
        except BaseException as e:  # noqa: BLE001
            check(f"异常吞住不抛出：{label}", False, f"抛出了 {type(e).__name__}")
        finally:
            restore_httpx()
    check("异常用例也没留下文件", list(covers.cover_dir().glob("31.*")) == [],
          str(list(covers.cover_dir().glob("*"))))


def test_media_type() -> None:
    check("media_type png", covers.cover_media_type("3.png") == "image/png")
    check("media_type jpg", covers.cover_media_type("3.jpg") == "image/jpeg")
    check("media_type jpeg", covers.cover_media_type("3.jpeg") == "image/jpeg")
    check("media_type webp", covers.cover_media_type("3.webp") == "image/webp")
    check("media_type 大写扩展名", covers.cover_media_type("3.PNG") == "image/png")
    check("media_type 认不出退回 png", covers.cover_media_type("3.bin") == "image/png")


def test_migration_column() -> None:
    """老库（没有 cover_file 列）升级后必须补出这一列，否则查询直接报错。"""
    reset()
    import sqlite3
    from app.config import settings
    # 路径必须取自 settings，不能猜——写死 "bambu.db" 会连到一个刚被建出来的空库，
    # PRAGMA 返回空列表，断言看着「失败」其实是被测对象根本没被打开（假断言）。
    db_path = str(settings.db_path)
    check("测试库文件存在", os.path.exists(db_path), db_path)
    # 表名以模型为准（`__tablename__ = "print_job"`），不能凭印象写 "printjob"——
    # 写错了 PRAGMA 会静静返回空列表，看着像「列丢了」，其实是查错了表。
    from app.models import PrintJob
    table = PrintJob.__tablename__
    con = sqlite3.connect(db_path)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    check(f"存在 {table} 表", table in tables, str(sorted(tables)))
    cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    con.close()
    check("列数不为 0（确认真读到了表）", len(cols) > 0, str(len(cols)))
    check("print_job 表有 cover_file 列", "cover_file" in cols, str(sorted(cols)))
    check("print_job 表保留 cover_url 列", "cover_url" in cols, str(sorted(cols)))

    # 迁移逻辑本身：把老库的列删掉再跑一次迁移，列必须回来
    # （这是唯一能证明「迁移真的在干活」的方式——只看列存在，模型建表也能过）
    import app.db as dbmod
    con = sqlite3.connect(db_path)
    con.execute(f"ALTER TABLE {table} DROP COLUMN cover_file")
    con.commit()
    con.close()
    # 必须先把连接池丢掉：SQLAlchemy 缓存的表结构还是旧的，
    # 直接跑迁移会 ADD 一列「已经存在」的列 → duplicate column name 报错。
    dbmod.engine.dispose()
    dbmod._migrate_columns()
    con = sqlite3.connect(db_path)
    cols_after = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    con.close()
    check("删掉 cover_file 后迁移能补回来", "cover_file" in cols_after, str(sorted(cols_after)))


def test_http() -> None:
    reset()
    covers.save_cover  # 确保模块已加载
    client = TestClient(app)
    r = client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})
    check("setup 成功", r.status_code == 200, str(r.status_code))

    # 未登录要 401（跟其他 /api 一致）
    fresh = TestClient(app)
    r = fresh.get("/api/jobs/1/cover")
    check("未登录取成果图 401", r.status_code == 401, str(r.status_code))

    # 不存在的任务
    r = client.get("/api/jobs/999999/cover")
    check("任务不存在 404", r.status_code == 404, str(r.status_code))

    # 有图的任务：先建任务，再手动落一张图
    with session_scope() as s:
        job = PrintJob(printer_id=1, serial="01S00A0000000000", title="有封面的任务",
                       status="finished", source="cloud_task")
        s.add(job)
        s.commit()
        s.refresh(job)
        job_id = job.id
        job.cover_file = "fake"          # 先写成不存在的文件名，验「文件丢失」分支
        s.add(job)
    r = client.get(f"/api/jobs/{job_id}/cover")
    check("有 cover_file 但文件丢失 → 404", r.status_code == 404, str(r.status_code))

    plain = covers.cover_dir() / f"{job_id}.png"
    plain.write_bytes(PNG_BODY)
    with session_scope() as s:
        job = s.get(PrintJob, job_id)
        job.cover_file = f"{job_id}.png"
        s.add(job)

    r = client.get(f"/api/jobs/{job_id}/cover")
    check("取成果图 200", r.status_code == 200, str(r.status_code))
    check("成果图 content-type = image/png",
          r.headers.get("content-type", "").startswith("image/png"), r.headers.get("content-type", ""))
    check("成果图字节数一致", r.content == PNG_BODY, str(len(r.content)))

    # 列表/详情要带上字段，前端才不用瞎猜
    r = client.get(f"/api/jobs/{job_id}")
    check("详情 200", r.status_code == 200, str(r.status_code))
    d = r.json()
    check("详情有 cover_file", d.get("cover_file") == f"{job_id}.png", repr(d.get("cover_file")))
    check("详情有 has_cover=True", d.get("has_cover") is True, repr(d.get("has_cover")))

    # 没图的任务：has_cover 必须是 False（前端据此显示占位）
    with session_scope() as s:
        j2 = PrintJob(printer_id=1, serial="01S00A0000000000", title="没封面的任务",
                      status="finished", source="manual")
        s.add(j2)
        s.commit()
        s.refresh(j2)
        j2_id = j2.id
    d2 = client.get(f"/api/jobs/{j2_id}").json()
    check("无图任务 has_cover=False", d2.get("has_cover") is False, repr(d2.get("has_cover")))
    check("无图任务 cover_file 为空串", d2.get("cover_file") == "", repr(d2.get("cover_file")))
    check("无图任务取图 404", client.get(f"/api/jobs/{j2_id}/cover").status_code == 404)


if __name__ == "__main__":
    print("== 抓取落盘 ==")
    test_save_cover_ok()
    print("== 跳过条件 ==")
    test_save_cover_skips()
    print("== 异常兜底 ==")
    test_save_cover_never_raises()
    print("== MIME 推断 ==")
    test_media_type()
    print("== 列迁移 ==")
    test_migration_column()
    print("== HTTP 端到端 ==")
    test_http()
    print(f"\n通过 {len(PASSED)} 项，失败 {len(FAILED)} 项")
    if FAILED:
        print("失败项：", FAILED)
        sys.exit(1)
    print("全部通过")
