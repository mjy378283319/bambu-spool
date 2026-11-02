"""数据备份：整库快照 + 密钥 + 清单，打包成一个 zip。

为什么是「快照」而不是直接复制 .db：
    SQLite 在写入过程中直接 `cp` 可能拿到半截事务的库。这里用 sqlite3 的
    backup API（`src.backup(dst)`），由 SQLite 自己保证一致性，运行中也能安全备份。

为什么要把 secret.key 一起打包：
    拓竹账号密码是用 data/secret.key 加密后存进库里的。只还原库、不还原密钥，
    密码就永远解不开了 —— 换台 NAS 恢复时会表现为「账号已保存但一直登录失败」。

不备份的内容：
    data/covers 里的打印封面图（纯展示，可由云端重新拉取）。
    备份包里有 MANIFEST.json 说明，恢复后封面会显示为占位图，其余数据完整。
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shutil
import sqlite3
import time
import zipfile
from datetime import datetime
from pathlib import Path

from .config import settings
from .db import session_scope
from .models import Setting
from .notify import notify

logger = logging.getLogger("bambu-spool.backup")

BACKUP_SUBDIR = "backups"
NAME_PREFIX = "bambu_spool_"
NAME_SUFFIX = ".zip"
DB_ENTRY = "bambu_spool.db"
SECRET_ENTRY = "secret.key"
MANIFEST_ENTRY = "MANIFEST.json"

# 恢复前的校验：这些表缺了就不认这个包（防止误传别的 sqlite 文件把库打坏）
# 注意账号表叫 app_user / app_session（不是 user）—— 别想当然
REQUIRED_TABLES = {
    "spool", "usage_record", "print_job", "slot_binding", "setting", "app_user",
}

# 文件名安全白名单：只允许本模块自己生成的名字，杜绝路径穿越
NAME_RE = re.compile(r"^bambu_spool_\d{8}_\d{6}_[a-z\-]+(?:_\d+)?\.zip$")

# 配置项默认值
DEFAULTS = {"auto": True, "interval_hours": 24, "keep": 14}
KEY_AUTO = "backup_auto"
KEY_INTERVAL = "backup_interval_hours"
KEY_KEEP = "backup_keep"
KEY_LAST_AT = "backup_last_at"
KEY_LAST_OK = "backup_last_ok"
KEY_LAST_MSG = "backup_last_message"


# ── 路径 ────────────────────────────────────────────────
def backup_dir() -> Path:
    """备份目录：跟着数据卷走，容器里是 /data/backups。"""
    d = settings.data_dir / BACKUP_SUBDIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def _db_path() -> Path:
    """真实数据库文件路径。

    不直接用 settings.db_path：用户可以用 DATABASE_URL 把库指到别的挂载点，
    这时 db_path 只是默认值，照着它备份会备到空库（或干脆备出一个不存在的文件）。
    """
    url = settings.database_url
    if not url.startswith("sqlite"):
        raise RuntimeError("当前数据源不是 SQLite，无法做整库备份")
    if ":memory:" in url:
        raise RuntimeError("内存数据库无法备份")
    raw = url.split("sqlite:///", 1)[-1] if "sqlite:///" in url else ""
    raw = raw.split("?", 1)[0]
    return Path(raw) if raw else settings.db_path


# ── 配置项（存 Setting 表，跟着库走，升级镜像不丢）────────
def _read_setting(session, key: str, default: str) -> str:
    row = session.get(Setting, key)
    if row is None or row.value == "":
        return default
    return row.value


def _write_setting(session, key: str, value: str) -> None:
    row = session.get(Setting, key)
    if row is None:
        session.add(Setting(key=key, value=value))
    else:
        row.value = value
        session.add(row)


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def get_config() -> dict:
    with session_scope() as session:
        auto = _read_setting(session, KEY_AUTO, "1" if DEFAULTS["auto"] else "0")
        interval = _read_setting(session, KEY_INTERVAL, str(DEFAULTS["interval_hours"]))
        keep = _read_setting(session, KEY_KEEP, str(DEFAULTS["keep"]))
    try:
        interval_i = _clamp(int(float(interval)), 1, 24 * 30)
    except (TypeError, ValueError):
        interval_i = DEFAULTS["interval_hours"]
    try:
        keep_i = _clamp(int(float(keep)), 1, 200)
    except (TypeError, ValueError):
        keep_i = DEFAULTS["keep"]
    return {"auto": auto.strip() in ("1", "true", "yes", "on"), "interval_hours": interval_i, "keep": keep_i}


def save_config(auto=None, interval_hours=None, keep=None) -> dict:
    with session_scope() as session:
        if auto is not None:
            _write_setting(session, KEY_AUTO, "1" if auto else "0")
        if interval_hours is not None:
            _write_setting(session, KEY_INTERVAL, str(_clamp(int(interval_hours), 1, 24 * 30)))
        if keep is not None:
            _write_setting(session, KEY_KEEP, str(_clamp(int(keep), 1, 200)))
    return get_config()


def last_result() -> dict:
    with session_scope() as session:
        at = _read_setting(session, KEY_LAST_AT, "")
        ok = _read_setting(session, KEY_LAST_OK, "")
        msg = _read_setting(session, KEY_LAST_MSG, "")
    return {"at": at, "ok": (ok == "1") if ok else None, "message": msg}


def _record_result(ok: bool, message: str) -> None:
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with session_scope() as session:
            _write_setting(session, KEY_LAST_AT, stamp)
            _write_setting(session, KEY_LAST_OK, "1" if ok else "0")
            _write_setting(session, KEY_LAST_MSG, message)
    except Exception as exc:  # 连日志都别因为记状态而失败
        logger.warning("记录备份结果失败：%s", exc)


# ── 快照 ────────────────────────────────────────────────
def _counts(db_file: Path) -> dict:
    """统计各表行数（只读打开快照，用来在界面说清「备了些什么」）。"""
    out = {}
    try:
        con = sqlite3.connect(f"file:{db_file.as_posix()}?mode=ro", uri=True)
        try:
            for table in ("spool", "usage_record", "print_job", "slot_binding", "setting"):
                try:
                    out[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                except sqlite3.Error:
                    out[table] = 0
        finally:
            con.close()
    except sqlite3.Error as exc:
        logger.warning("统计备份内容失败：%s", exc)
    return out


def db_counts() -> dict:
    """当前库各表行数，用于界面说明「备份会包含些什么」。"""
    return _counts(_db_path())


def _app_version() -> str:
    try:
        from .main import app as _app  # 延迟导入，避免模块级循环依赖

        return str(getattr(_app, "version", ""))
    except Exception:
        return ""


def _snapshot(db_file: Path, target: Path) -> None:
    """用 SQLite 自己的 backup API 做一致性快照（运行中也能安全执行）。"""
    src = sqlite3.connect(f"file:{db_file.as_posix()}?mode=ro", uri=True, timeout=15)
    dst = sqlite3.connect(str(target))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


# ── 生成备份 ────────────────────────────────────────────
def prune(keep: int) -> list:
    """只保留最近 keep 份；永远至少留一份。返回被删掉的文件名。"""
    keep = _clamp(int(keep), 1, 200)
    files = _sorted_backups()
    removed = []
    for path in files[keep:]:
        try:
            path.unlink()
            removed.append(path.name)
        except OSError as exc:
            logger.warning("清理旧备份失败 %s：%s", path.name, exc)
    return removed


def create_backup(reason: str = "manual", keep: int | None = None) -> dict:
    """生成一份备份。失败会抛异常，并先把失败原因写进 Setting 供界面显示。"""
    if reason not in ("manual", "auto", "pre-restore"):
        reason = "manual"
    cfg = get_config()
    keep_n = cfg["keep"] if keep is None else _clamp(int(keep), 1, 200)

    d = backup_dir()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{NAME_PREFIX}{stamp}_{reason}"
    final = d / f"{base}{NAME_SUFFIX}"
    if final.exists():  # 同一秒内连点两次：加序号，别覆盖已有备份
        n = 1
        while (d / f"{base}_{n}{NAME_SUFFIX}").exists():
            n += 1
        base = f"{base}_{n}"
        final = d / f"{base}{NAME_SUFFIX}"

    tmp_zip = d / f".tmp_{base}{NAME_SUFFIX}"
    tmp_db = d / f".tmp_{base}_{DB_ENTRY}"

    try:
        _snapshot(_db_path(), tmp_db)
        counts = _counts(tmp_db)
        manifest = {
            "app": "bambu-spool",
            "app_version": _app_version(),
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "reason": reason,
            "tables": counts,
            "includes": [DB_ENTRY] + ([SECRET_ENTRY] if settings.secret_key_path.exists() else []),
            "excludes": ["data/covers（打印封面图，可由云端重新拉取）"],
        }
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            zf.write(tmp_db, DB_ENTRY)
            if settings.secret_key_path.exists():
                zf.write(settings.secret_key_path, SECRET_ENTRY)
            zf.writestr(MANIFEST_ENTRY, json.dumps(manifest, ensure_ascii=False, indent=2))
        os.replace(tmp_zip, final)
    except Exception as exc:
        for junk in (tmp_zip, tmp_db):
            try:
                junk.unlink()
            except OSError:
                pass
        logger.error("备份失败：%s", exc, exc_info=True)
        _record_result(False, f"备份失败：{exc}")
        raise
    finally:
        try:
            tmp_db.unlink()
        except OSError:
            pass

    removed = prune(keep_n)
    size = final.stat().st_size
    _record_result(True, f"已生成 {final.name}（{size / 1024:.0f} KB）")
    logger.info("备份完成：%s（%s 字节）", final.name, size)
    return {
        "name": final.name,
        "size": size,
        "created_at": final.stat().st_mtime,
        "reason": reason,
        "counts": counts,
        "removed": removed,
    }


def _sorted_backups() -> list:
    """按生成时间倒序（新 → 旧）。用 mtime 纳秒，同一秒内连续备份也能排对。"""
    files = []
    for path in backup_dir().glob(f"{NAME_PREFIX}*{NAME_SUFFIX}"):
        try:
            files.append((path.stat().st_mtime_ns, path))
        except OSError:
            continue
    files.sort(key=lambda item: item[0], reverse=True)
    return [path for _, path in files]


def list_backups() -> list:
    out = []
    for path in _sorted_backups():
        m = NAME_RE.match(path.name)
        reason = "unknown"
        if m:
            reason = path.name.split("_")[-1].removesuffix(NAME_SUFFIX)
            if reason.isdigit():  # 同秒重复时的 _1 后缀
                parts = path.stem.split("_")
                reason = parts[-2] if len(parts) >= 2 else reason
        try:
            st = path.stat()
        except OSError:
            continue
        out.append(
            {
                "name": path.name,
                "size": st.st_size,
                "created_at": st.st_mtime,
                "reason": reason,
            }
        )
    return out


def latest_backup_ts() -> float | None:
    files = _sorted_backups()
    if not files:
        return None
    try:
        return files[0].stat().st_mtime
    except OSError:
        return None


# ── 恢复 ────────────────────────────────────────────────
def _validate_bundle(path: Path) -> tuple[Path, Path | None]:
    """校验备份包，解出库与密钥到临时文件。

    返回 (临时库路径, 临时密钥路径或 None)；不合格直接抛 ValueError。
    调用方负责清理这两个临时文件。
    """
    if not NAME_RE.match(path.name):
        raise ValueError("备份文件名不合法")
    if not path.is_file():
        raise ValueError("备份文件不存在")
    if not zipfile.is_zipfile(path):
        raise ValueError("这不是有效的备份包（不是 zip）")

    d = backup_dir()
    stamp = int(time.time())
    tmp_db = d / f".restore_{stamp}_{DB_ENTRY}"
    tmp_key = d / f".restore_{stamp}_{SECRET_ENTRY}"
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        if DB_ENTRY not in names:
            raise ValueError("备份包里没有数据库文件")
        tmp_db.write_bytes(zf.read(DB_ENTRY))
        if SECRET_ENTRY in names:
            tmp_key.write_bytes(zf.read(SECRET_ENTRY))
        else:
            tmp_key = None
        del names

    try:
        con = sqlite3.connect(str(tmp_db))
        try:
            status = con.execute("PRAGMA integrity_check").fetchone()[0]
            if str(status).lower() != "ok":
                raise ValueError(f"备份库校验失败：{status}")
            tables = {row[0] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        finally:
            con.close()
    except sqlite3.Error as exc:
        tmp_db.unlink(missing_ok=True)
        if tmp_key:
            tmp_key.unlink(missing_ok=True)
        raise ValueError(f"备份库无法打开：{exc}") from exc

    missing = REQUIRED_TABLES - tables
    if missing:
        tmp_db.unlink(missing_ok=True)
        if tmp_key:
            tmp_key.unlink(missing_ok=True)
        raise ValueError("备份库里缺少这些表：" + "、".join(sorted(missing)))

    return tmp_db, tmp_key


def restore_from(name: str) -> dict:
    """从已有备份恢复。恢复前会自动先备一份当前数据，避免「恢复了错的包」不可逆。"""
    path = backup_dir() / name
    tmp_db, tmp_key = _validate_bundle(path)

    pre = None
    try:
        pre = create_backup("pre-restore")

        src = sqlite3.connect(str(tmp_db))
        dst = sqlite3.connect(str(_db_path()), timeout=20)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()

        if tmp_key and tmp_key.exists():
            shutil.copy2(tmp_key, settings.secret_key_path)
            try:
                settings.secret_key_path.chmod(0o600)
            except OSError:
                pass
    except Exception as exc:
        logger.error("恢复失败：%s", exc, exc_info=True)
        _record_result(False, f"恢复失败：{exc}")
        raise
    finally:
        tmp_db.unlink(missing_ok=True)
        if tmp_key:
            Path(tmp_key).unlink(missing_ok=True)

    msg = f"已从 {name} 恢复（恢复前已自动备份为 {pre['name'] if pre else '—'}）"
    _record_result(True, msg)
    logger.info(msg)
    return {"ok": True, "message": msg, "pre_restore": pre["name"] if pre else None}


def delete_backup(name: str) -> None:
    if not NAME_RE.match(name):
        raise ValueError("备份文件名不合法")
    path = backup_dir() / name
    if not path.is_file():
        raise ValueError("备份文件不存在")
    path.unlink()


# ── 定时器 ──────────────────────────────────────────────
async def scheduler_loop() -> None:
    """每 10 分钟看一眼该不该备份。间隔没到就什么都不做，开销可以忽略。"""
    await asyncio.sleep(180)  # 启动后先让数据库初始化跑完
    while True:
        try:
            cfg = await asyncio.to_thread(get_config)
            if cfg["auto"]:
                last = await asyncio.to_thread(latest_backup_ts)
                due = last is None or (time.time() - last) >= cfg["interval_hours"] * 3600
                if due:
                    info = await asyncio.to_thread(create_backup, "auto")
                    logger.info("自动备份完成：%s", info.get("name"))
                    await notify("耗材管家 · 备份完成", f"已生成 {info.get('name')}")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # 自动备份失败不能拖垮整个服务
            logger.error("自动备份失败：%s", exc, exc_info=True)
            try:
                await notify("耗材管家 · 备份失败", str(exc))
            except Exception:
                pass
        await asyncio.sleep(600)
