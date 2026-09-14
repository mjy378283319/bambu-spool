"""账号、登录会话与访问控制。

这套是按「要挂到公网」的标准写的，不是内网玩具：

- 口令用 PBKDF2-HMAC-SHA256 加盐哈希存储，比对一律走 `hmac.compare_digest`，
  既不存明文也不给计时侧信道。
- 会话令牌是 32 字节密码学随机数；数据库里只存它的 SHA-256 摘要，
  所以即使数据库文件泄露，也无法直接拿来冒用登录态。
- Cookie 带 `HttpOnly`（JS 读不到，杜绝 XSS 偷令牌）、`SameSite`，
  `Secure` 按实际协议自动判定（反代场景看 `X-Forwarded-Proto`）。
- 登录失败按来源 IP 计数并锁定，抵御在线爆破。
- 首次创建管理员只允许来自内网 / 回环地址的**直连**（看 TCP 对端，不看
  `X-Forwarded-For`），避免服务一挂上公网就被人抢先注册管理员。
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, Request, Response
from sqlmodel import Field, SQLModel, select

from .config import settings
from .db import session_scope
from .models import utcnow

logger = logging.getLogger("bambu-spool.auth")

COOKIE_NAME = "bs_session"
_PBKDF2_ALGO = "pbkdf2_sha256"


# ══ 数据模型 ═══════════════════════════════════════════════
class User(SQLModel, table=True):
    """后台账号。个人自用场景通常只有一个，但不限制数量。"""

    __tablename__ = "app_user"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str = ""
    display_name: str = ""
    is_admin: bool = True
    disabled: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    last_login_at: Optional[datetime] = Field(default=None)
    last_login_ip: str = ""
    # 改过密码后，此前签发的会话全部失效的标记点
    password_changed_at: datetime = Field(default_factory=utcnow)


class LoginSession(SQLModel, table=True):
    """登录会话。只存令牌摘要，不存令牌本身。"""

    __tablename__ = "app_session"

    id: Optional[int] = Field(default=None, primary_key=True)
    token_hash: str = Field(index=True, unique=True)
    user_id: int = Field(index=True)
    created_at: datetime = Field(default_factory=utcnow)
    expires_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow)
    ip: str = ""
    user_agent: str = ""
    revoked: bool = False


# ══ 口令哈希 ═══════════════════════════════════════════════
def hash_password(password: str) -> str:
    """返回 `pbkdf2_sha256$迭代次数$盐$摘要`，自描述格式便于以后升级迭代次数。"""
    if not password:
        raise ValueError("口令不能为空")
    iterations = settings.pbkdf2_iterations
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "$".join(
        [_PBKDF2_ALGO, str(iterations), salt.hex(), digest.hex()]
    )


def verify_password(password: str, stored: str) -> bool:
    """校验口令。任何解析异常都按「不通过」处理，不外泄细节。"""
    if not password or not stored:
        return False
    try:
        algo, iter_text, salt_hex, digest_hex = stored.split("$")
        if algo != _PBKDF2_ALGO:
            return False
        iterations = int(iter_text)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, AttributeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


def password_strength_error(password: str) -> Optional[str]:
    """返回不合规的原因；合规返回 None。只做最低限度的合理约束。"""
    if len(password or "") < 8:
        return "口令至少 8 位"
    if len(password) > 256:
        return "口令过长"
    if password.isdigit() or password.isalpha():
        return "口令不要只用纯数字或纯字母"
    return None


# ══ 来源地址 ═══════════════════════════════════════════════
def peer_ip(request: Request) -> str:
    """TCP 对端地址。这是唯一不可伪造的来源，用于判断「是否内网直连」。"""
    client = getattr(request, "client", None)
    return (client.host if client else "") or ""


def client_ip(request: Request) -> str:
    """用于限流与审计的来源地址。反代后取 X-Forwarded-For 的第一跳。"""
    if settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            first = forwarded.split(",")[0].strip()
            if first:
                return first
        real = request.headers.get("x-real-ip", "").strip()
        if real:
            return real
    return peer_ip(request)


def is_private_host(host: str) -> bool:
    """判断是否回环 / 内网地址。无法解析时按「不安全」处理。"""
    if not host:
        return False
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        return False
    # IPv4-mapped IPv6（::ffff:192.168.1.5）要还原成 IPv4 再判断
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return bool(addr.is_private or addr.is_loopback or addr.is_link_local)


def is_https(request: Request) -> bool:
    """是否处于 HTTPS 之下。反代场景看 X-Forwarded-Proto。"""
    if request.url.scheme == "https":
        return True
    if settings.trust_proxy:
        return request.headers.get("x-forwarded-proto", "").split(",")[0].strip() == "https"
    return False


# ══ 登录失败限流 ═══════════════════════════════════════════
# 进程内计数即可：单容器部署，重启后清零不影响安全性。
_failures: dict[str, list] = {}


def _prune_failures(now: float) -> None:
    for key in [k for k, v in _failures.items() if v[1] <= now and v[0] == 0]:
        _failures.pop(key, None)


def login_locked_seconds(ip: str) -> int:
    """该来源还剩多少秒处于锁定期。0 表示可以尝试。"""
    entry = _failures.get(ip)
    if not entry:
        return 0
    count, locked_until = entry
    remaining = int(locked_until - time.time())
    return remaining if remaining > 0 else 0


def record_login_failure(ip: str) -> int:
    """记一次失败，返回累计失败次数。达到阈值即进入锁定期。"""
    now = time.time()
    entry = _failures.get(ip) or [0, 0.0]
    count = entry[0] + 1
    locked_until = 0.0
    if count >= settings.login_max_attempts:
        # 超出阈值后，失败越多锁得越久（上限 1 小时）
        over = count - settings.login_max_attempts
        lock_seconds = min(
            settings.login_lockout_minutes * 60 * (2 ** min(over, 5)), 3600
        )
        locked_until = now + lock_seconds
    _failures[ip] = [count, locked_until]
    if len(_failures) > 5000:
        _prune_failures(now)
    return count


def clear_login_failures(ip: str) -> None:
    _failures.pop(ip, None)


def reset_login_failures() -> None:
    """仅测试用。"""
    _failures.clear()


# ══ 会话 ═══════════════════════════════════════════════════
def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user: User, request: Request, days: Optional[int] = None) -> tuple[str, LoginSession]:
    """签发会话，返回 (明文令牌, 会话记录)。明文只在此刻存在于内存中。"""
    ttl_days = days if days is not None else settings.session_ttl_days
    token = secrets.token_urlsafe(32)
    now = utcnow()
    record = LoginSession(
        token_hash=_token_digest(token),
        user_id=int(user.id or 0),
        created_at=now,
        expires_at=now + timedelta(days=ttl_days),
        last_seen_at=now,
        ip=client_ip(request),
        user_agent=(request.headers.get("user-agent", "") or "")[:300],
    )
    with session_scope() as session:
        session.add(record)
        session.flush()
        session.refresh(record)
        # 顺手清理该用户已过期的会话，避免表无限增长
        stale = session.exec(
            select(LoginSession).where(
                LoginSession.user_id == record.user_id,
                LoginSession.expires_at < now,  # type: ignore[operator]
            )
        ).all()
        for old in stale:
            session.delete(old)
    return token, record


def resolve_session(token: str) -> Optional[tuple[LoginSession, User]]:
    """用明文令牌换回会话与用户。过期、被吊销、用户被禁用都返回 None。"""
    if not token:
        return None
    digest = _token_digest(token)
    now = utcnow()
    with session_scope() as session:
        record = session.exec(
            select(LoginSession).where(LoginSession.token_hash == digest)
        ).first()
        if record is None or record.revoked:
            return None
        if record.expires_at < now:
            session.delete(record)
            return None
        user = session.get(User, record.user_id)
        if user is None or user.disabled:
            return None
        # 改过密码之后，旧会话一律作废
        if user.password_changed_at and record.created_at < user.password_changed_at:
            session.delete(record)
            return None

        # 滑动续期：距离上次刷新超过 1 小时才写库，避免每个请求都打数据库
        if (now - record.last_seen_at).total_seconds() > 3600:
            record.last_seen_at = now
            record.expires_at = now + timedelta(days=settings.session_ttl_days)
            session.add(record)
        return record, user


def revoke_session(token: str) -> None:
    if not token:
        return
    digest = _token_digest(token)
    with session_scope() as session:
        record = session.exec(
            select(LoginSession).where(LoginSession.token_hash == digest)
        ).first()
        if record is not None:
            record.revoked = True
            session.add(record)


def revoke_user_sessions(user_id: int) -> int:
    """吊销某用户全部会话（改密码、点「退出所有设备」时用）。"""
    with session_scope() as session:
        rows = session.exec(
            select(LoginSession).where(
                LoginSession.user_id == user_id, LoginSession.revoked == False  # noqa: E712
            )
        ).all()
        for row in rows:
            row.revoked = True
            session.add(row)
        return len(rows)


def active_session_count(user_id: int) -> int:
    now = utcnow()
    with session_scope() as session:
        rows = session.exec(
            select(LoginSession).where(
                LoginSession.user_id == user_id,
                LoginSession.revoked == False,  # noqa: E712
                LoginSession.expires_at > now,  # type: ignore[operator]
            )
        ).all()
        return len(rows)


# ══ 账号 ═══════════════════════════════════════════════════
def user_count() -> int:
    with session_scope() as session:
        return len(session.exec(select(User)).all())


def find_user(username: str) -> Optional[User]:
    name = (username or "").strip()
    if not name:
        return None
    with session_scope() as session:
        return session.exec(select(User).where(User.username == name)).first()


def create_user(
    username: str,
    password: str,
    display_name: str = "",
    is_admin: bool = True,
) -> User:
    name = (username or "").strip()
    if not name:
        raise ValueError("账号不能为空")
    if len(name) > 64:
        raise ValueError("账号过长")
    if any(c.isspace() for c in name):
        raise ValueError("账号不能包含空格")
    problem = password_strength_error(password)
    if problem:
        raise ValueError(problem)
    if find_user(name) is not None:
        raise ValueError("该账号已存在")

    now = utcnow()
    user = User(
        username=name,
        password_hash=hash_password(password),
        display_name=display_name or name,
        is_admin=is_admin,
        created_at=now,
        password_changed_at=now,
    )
    with session_scope() as session:
        session.add(user)
        session.flush()
        session.refresh(user)
    return user


def change_password(user: User, old_password: str, new_password: str, keep_token: str = "") -> int:
    """修改口令。返回被强制下线的其它会话数量。

    `keep_token` 传入当前这把令牌时，当前浏览器不会被踢下线，只清掉别处
    （手机、别的电脑）的登录。不传则全部下线。
    """
    if not verify_password(old_password, user.password_hash):
        raise ValueError("原口令不正确")
    problem = password_strength_error(new_password)
    if problem:
        raise ValueError(problem)

    now = utcnow()
    keep_digest = _token_digest(keep_token) if keep_token else ""
    revoked = 0
    with session_scope() as session:
        row = session.get(User, user.id)
        if row is None:
            raise ValueError("账号不存在")
        row.password_hash = hash_password(new_password)
        row.password_changed_at = now
        session.add(row)

        sessions = session.exec(
            select(LoginSession).where(
                LoginSession.user_id == user.id,
                LoginSession.revoked == False,  # noqa: E712
            )
        ).all()
        for item in sessions:
            if keep_digest and item.token_hash == keep_digest:
                # 保留的这把要跟着 password_changed_at 一起前移，
                # 否则会被「密码改过即作废旧会话」的判定误伤。
                item.created_at = now
                item.last_seen_at = now
                session.add(item)
                continue
            item.revoked = True
            session.add(item)
            revoked += 1
    return revoked


def authenticate(username: str, password: str, request: Request) -> User:
    """校验账号口令。失败一律抛 401，不区分「账号不存在」和「口令错误」。"""
    ip = client_ip(request)
    locked = login_locked_seconds(ip)
    if locked:
        raise HTTPException(
            status_code=429,
            detail=f"失败次数过多，请 {max(1, locked // 60)} 分钟后再试",
        )

    user = find_user(username)
    ok = bool(user) and not user.disabled and verify_password(password, user.password_hash)  # type: ignore[union-attr]
    if not ok:
        count = record_login_failure(ip)
        left = settings.login_max_attempts - count
        logger.warning("登录失败 账号=%s 来源=%s（累计 %d 次）", username, ip, count)
        detail = "账号或口令不正确"
        if 0 < left <= 2:
            detail += f"，再失败 {left} 次将临时锁定"
        raise HTTPException(status_code=401, detail=detail)

    clear_login_failures(ip)
    now = utcnow()
    with session_scope() as session:
        row = session.get(User, user.id)  # type: ignore[arg-type]
        if row is not None:
            row.last_login_at = now
            row.last_login_ip = ip
            session.add(row)
            session.refresh(row)
            user = row
    return user


def bootstrap_admin_from_env() -> None:
    """支持用环境变量在首次启动时直接建好管理员，方便 Unraid 模板化部署。

    只在「一个账号都没有」时生效，已存在账号则忽略，避免误改口令。
    """
    password = (os.getenv("ADMIN_PASSWORD") or "").strip()
    if not password:
        return
    username = (os.getenv("ADMIN_USER") or "admin").strip() or "admin"
    if user_count() > 0:
        logger.info("已存在账号，忽略 ADMIN_PASSWORD 环境变量")
        return
    try:
        create_user(username, password, display_name=username)
        logger.info("已按环境变量创建管理员账号：%s", username)
    except ValueError as exc:
        logger.error("按环境变量创建管理员失败：%s", exc)


# ══ Cookie ════════════════════════════════════════════════
def _secure_cookie(request: Request) -> bool:
    """Secure 标志。显式配置优先，auto 则按实际协议判断。"""
    mode = settings.cookie_secure.lower()
    if mode == "true":
        return True
    if mode == "false":
        return False
    return is_https(request)


def set_session_cookie(response: Response, token: str, request: Request, days: Optional[int] = None) -> None:
    ttl_days = days if days is not None else settings.session_ttl_days
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=int(timedelta(days=ttl_days).total_seconds()),
        path="/",
        httponly=True,
        secure=_secure_cookie(request),
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/", httponly=True, samesite="lax")


def token_from_request(request: Request) -> str:
    """从 Cookie 或 Authorization 头取令牌。后者方便脚本 / 自动化调用。"""
    cookie = request.cookies.get(COOKIE_NAME, "")
    if cookie:
        return cookie
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return ""


def current_user(request: Request) -> Optional[User]:
    resolved = resolve_session(token_from_request(request))
    return resolved[1] if resolved else None


def user_dict(user: Optional[User]) -> dict:
    if user is None:
        return {}
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "is_admin": user.is_admin,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
    }
