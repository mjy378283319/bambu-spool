"""数据备份自测。

覆盖：
  - GET /api/backup：默认配置（自动开 / 24 小时 / 留 14 份）、内容统计
  - POST /api/backup：生成 zip，包内有库 + MANIFEST（有密钥时也带上）
  - POST /api/backup/restore：改完数据再恢复，数据回到备份点
  - 恢复前自动生成 pre-restore 备份（不让人为误操作不可逆）
  - 保留策略：超过 keep 份自动删最旧，且永远至少留一份
  - 非法文件名（路径穿越）被拒
  - 下载 / 删除

运行： python tests/test_backup.py
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DATA_DIR = os.path.join(ROOT, "data", "testbackup")
# 必须在 import app 之前清干净：config 在导入时就会建目录
shutil.rmtree(DATA_DIR, ignore_errors=True)

os.environ["BAMBU_MOCK"] = "1"
os.environ["DATA_DIR"] = DATA_DIR
os.environ["ALLOW_PUBLIC_SETUP"] = "1"

from starlette.testclient import TestClient  # noqa: E402

from app import backup as backup_mod  # noqa: E402
from app.main import app  # noqa: E402

FAILS: list[str] = []
CHECKS = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if not ok:
        FAILS.append(f"{name} {detail}".strip())
        print(f"  FAIL  {name} {detail}")
    else:
        print(f"  ok    {name}")


def new_spool(client, name: str) -> int:
    r = client.post("/api/spools", json={
        "name": name, "brand": "大简", "material": "PLA",
        "spool_weight": 254, "initial_weight": 1000, "remaining_weight": 1000,
    })
    assert r.status_code in (200, 201), r.text
    return r.json()["id"] if "id" in r.json() else r.json()["spool"]["id"]


def spool_names(client) -> list[str]:
    r = client.get("/api/spools")
    assert r.status_code == 200, r.text
    data = r.json()
    rows = data["spools"] if isinstance(data, dict) and "spools" in data else data
    return sorted(row["name"] for row in rows)


def run() -> None:
    with TestClient(app) as client:
        r = client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})
        check("初始化管理员", r.status_code in (200, 201), r.text[:120])

        new_spool(client, "备份前的料")
        check("准备数据", spool_names(client) == ["备份前的料"], str(spool_names(client)))

        # ── 状态与默认配置 ──
        st = client.get("/api/backup")
        check("GET /api/backup 200", st.status_code == 200, st.text[:120])
        body = st.json()
        check("默认自动备份开启", body["config"]["auto"] is True)
        check("默认间隔 24 小时", body["config"]["interval_hours"] == 24)
        check("默认保留 14 份", body["config"]["keep"] == 14)
        check("返回备份目录", bool(body["dir"]))
        check("统计到 1 盘料", body["counts"].get("spool") == 1, str(body["counts"]))

        # ── 手动备份 ──
        r = client.post("/api/backup")
        check("POST /api/backup 200", r.status_code == 200, r.text[:200])
        info = r.json()["backup"]
        name = info["name"]
        path = os.path.join(DATA_DIR, "backups", name)
        check("备份文件落盘", os.path.isfile(path), path)
        check("文件名合规", name.startswith("bambu_spool_") and name.endswith(".zip"), name)
        check("备份非空", os.path.getsize(path) > 1024, str(os.path.getsize(path)))

        with zipfile.ZipFile(path) as zf:
            entries = set(zf.namelist())
            manifest = json.loads(zf.read("MANIFEST.json"))
        check("包含数据库", "bambu_spool.db" in entries, str(entries))
        check("包含清单", "MANIFEST.json" in entries)
        check("清单记录了行数", manifest["tables"].get("spool") == 1, str(manifest.get("tables")))
        check("清单记录了版本", bool(manifest.get("app_version")), str(manifest.get("app_version")))

        # ── 改数据后恢复 ──
        new_spool(client, "备份后的料")
        check("恢复前有 2 盘料", spool_names(client) == ["备份前的料", "备份后的料"], str(spool_names(client)))

        r = client.post("/api/backup/restore", json={"name": name})
        check("恢复返回 200", r.status_code == 200, r.text[:200])
        if r.status_code == 200:
            res = r.json()
            check("恢复提示需要重新登录", res.get("relogin_required") is True)
            check("自动生成 pre-restore 备份", bool(res.get("pre_restore")), str(res))
        check("数据回到备份点", spool_names(client) == ["备份前的料"], str(spool_names(client)))

        names = [b["name"] for b in client.get("/api/backup").json()["backups"]]
        check("磁盘上多了 pre-restore 备份", len(names) == 2, str(names))
        check("其中一份是 pre-restore",
              any("pre-restore" in n for n in names), str(names))

        # ── 保留策略 ──
        r = client.post("/api/backup/config", json={"keep": 2, "interval_hours": 6, "auto": False})
        check("保存配置 200", r.status_code == 200, r.text[:120])
        cfg = r.json()["config"]
        check("配置生效", cfg["keep"] == 2 and cfg["interval_hours"] == 6 and cfg["auto"] is False, str(cfg))

        for _ in range(3):
            client.post("/api/backup")
        left = client.get("/api/backup").json()["backups"]
        check("只保留 2 份", len(left) == 2, str([b["name"] for b in left]))

        r = client.post("/api/backup/config", json={"keep": 0, "interval_hours": 0})
        cfg = r.json()["config"]
        check("非法数值被夹到下限", cfg["keep"] == 1 and cfg["interval_hours"] == 1, str(cfg))

        # ── 下载 / 删除 / 非法名 ──
        target = left[0]["name"]
        dl = client.get(f"/api/backup/download/{target}")
        check("下载 200", dl.status_code == 200, str(dl.status_code))
        check("下载是 zip", dl.content[:2] == b"PK", str(dl.content[:2]))
        check("下载带附件名", "attachment" in dl.headers.get("content-disposition", ""),
              dl.headers.get("content-disposition", ""))

        bad = client.get("/api/backup/download/..%2F..%2Fetc%2Fpasswd")
        check("非法下载名被拒", bad.status_code in (400, 404), str(bad.status_code))

        r = client.post("/api/backup/restore", json={"name": "../../etc/passwd"})
        check("非法恢复名被拒", r.status_code in (400, 404), str(r.status_code))

        r = client.post("/api/backup/restore", json={"name": "bambu_spool_20990101_000000_manual.zip"})
        check("不存在的备份被拒", r.status_code == 400, str(r.status_code))

        r = client.delete(f"/api/backup/{target}")
        check("删除 200", r.status_code == 200, r.text[:120])
        check("删除后文件消失", not os.path.isfile(os.path.join(DATA_DIR, "backups", target)))

        # ── 直接调模块：至少留一份 ──
        backup_mod.prune(1)
        check("prune 不会删光", len(backup_mod.list_backups()) >= 1,
              str([b["name"] for b in backup_mod.list_backups()]))


def main() -> int:
    run()
    print()
    if FAILS:
        print(f"FAILED: {len(FAILS)} / {CHECKS}")
        for f in FAILS:
            print("  -", f)
        return 1
    print(f"ALL PASSED ({CHECKS} checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
