"""拓竹云 HTTP 客户端。

事实来源（均已核对源码）：
- 接口地址来自 greghesp/ha-bambulab 的 pybambu/const.py `BAMBU_URL`
- 区域切换规则：China 时 api.bambulab.com → api.bambulab.cn
- 登录流程、验证码登录、2FA、JWT 取 uid：pybambu/bambu_cloud.py
- 任务历史字段 `weight` / `amsDetailMapping[].{filamentId,weight}` 来自
  bambu_cloud.py `get_tasklist()` 的返回结构注释

注意：拓竹云接口在 Cloudflare 后面。若装了 curl_cffi 就用它模仿浏览器指纹，
否则回退到 httpx + 拓竹官方客户端请求头。
"""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

try:  # pragma: no cover - 取决于运行环境
    from curl_cffi import requests as _curl_requests

    CURL_AVAILABLE = True
except Exception:  # pragma: no cover
    _curl_requests = None
    CURL_AVAILABLE = False


class BambuCloudError(Exception):
    pass


class CloudflareBlocked(BambuCloudError):
    pass


class AuthRequired(BambuCloudError):
    """需要验证码或 2FA。"""

    def __init__(self, login_type: str, message: str = "", tfa_key: str = ""):
        super().__init__(message or login_type)
        self.login_type = login_type
        self.tfa_key = tfa_key


class ApiClient:
    DOMAINS = {
        "china": "https://api.bambulab.cn",
        "global": "https://api.bambulab.com",
    }
    MQTT_HOSTS = {
        "china": "cn.mqtt.bambulab.com",
        "global": "us.mqtt.bambulab.com",
    }
    # 短信验证码接口固定走 cn 域名（上游 ha-bambulab const.py：SMS_CODE）
    TFA_URL = "https://bambulab.com/api/sign-in/tfa"
    CSRF_URL = "https://bambulab.com/api/sign-in/csrf"

    def __init__(self, region: str = "china"):
        self.region = region if region in self.DOMAINS else "china"

    # ── 基础 ────────────────────────────────────────────────
    @property
    def base(self) -> str:
        return self.DOMAINS[self.region]

    @property
    def mqtt_host(self) -> str:
        return self.MQTT_HOSTS[self.region]

    @property
    def sms_url(self) -> str:
        """短信验证码接口。

        曾经写成 https://api.bambulab.cn/api/v1/...（多一段 /api），
        网关会直接返回 404 {"error_msg":"404 Route Not Found"}。
        正确路径与其它 user-service 接口同级。
        """
        return self._url("/v1/user-service/user/sendsmscode")

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def _headers(self, token: str = "") -> dict[str, str]:
        headers = {
            "User-Agent": "bambu_network_agent/01.09.05.01",
            "X-BBL-Client-Name": "OrcaSlicer",
            "X-BBL-Client-Type": "slicer",
            "X-BBL-Client-Version": "01.09.05.51",
            "X-BBL-Language": "zh-CN",
            "X-BBL-OS-Type": "linux",
            "X-BBL-OS-Version": "6.2.0",
            "X-BBL-Agent-Version": "01.09.05.01",
            "X-BBL-Executable-info": "{}",
            "X-BBL-Agent-OS-Type": "linux",
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _request(
        self,
        method: str,
        url: str,
        token: str = "",
        body: Optional[dict] = None,
        extra_headers: Optional[dict] = None,
        timeout: float = 15.0,
        need_cookies: bool = False,
    ) -> httpx.Response | Any:
        headers = self._headers(token)
        if extra_headers:
            headers.update(extra_headers)

        last_error: Optional[Exception] = None

        # 双重验证依赖 CSRF Cookie，curl_cffi 的简化返回面拿不到 cookie，必须走 httpx
        if CURL_AVAILABLE and not need_cookies:
            try:
                kw: dict[str, Any] = {
                    "timeout": timeout,
                    "impersonate": "chrome",
                    "headers": {"Authorization": f"Bearer {token}"} if token else {},
                }
                resp = _curl_requests.request(method, url, json=body, **kw)
                return _SimpleResponse(resp.status_code, resp.text)
            except Exception as exc:  # 回退到 httpx
                last_error = exc

        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.request(method, url, headers=headers, json=body)
                return resp
        except Exception as exc:
            raise BambuCloudError(f"网络请求失败：{exc}") from (last_error or exc)

    @staticmethod
    def _check(resp, allow_400: bool = False) -> None:
        text = (resp.text or "")
        if resp.status_code == 403:
            low = text.lower()
            if "cloudflare" in low or "just a moment" in low:
                raise CloudflareBlocked(
                    "被拓竹的 Cloudflare 防护拦截。建议安装 curl_cffi，或稍后重试。"
                )
            if "missing_cookie" in low:
                raise AuthRequired("csrf", "需要 CSRF Cookie，请改用验证码登录。")
        if resp.status_code == 429:
            raise BambuCloudError("请求过于频繁，已被限流，请稍后再试。")
        if resp.status_code == 400 and allow_400:
            return
        if resp.status_code == 404 and "route not found" in text.lower():
            # 拓竹网关对未知路径的应答。多数情况是接口地址写错或已变更。
            raise BambuCloudError("拓竹接口地址无效（404）。可能是接口变更，请升级本程序。")
        if resp.status_code >= 400:
            raise BambuCloudError(f"接口返回 {resp.status_code}：{text[:200]}")

    @staticmethod
    def _json(resp) -> dict:
        try:
            return json.loads(resp.text)
        except (ValueError, TypeError) as exc:
            raise BambuCloudError(f"响应不是合法 JSON：{(resp.text or '')[:200]}") from exc

    # ── 登录 ────────────────────────────────────────────────
    def login(self, account: str, password: str) -> dict:
        """密码登录。需要验证码或 2FA 时抛出 AuthRequired。"""
        resp = self._request(
            "POST",
            self._url("/v1/user-service/user/login"),
            body={"account": account, "password": password, "apiError": ""},
        )
        self._check(resp)
        data = self._json(resp)

        token = data.get("accessToken") or ""
        if token:
            return {
                "access_token": token,
                "refresh_token": data.get("refreshToken", ""),
            }

        login_type = data.get("loginType")
        if login_type == "verifyCode":
            raise AuthRequired("verifyCode", "该账号需要邮箱或短信验证码登录。")
        if login_type == "tfa":
            raise AuthRequired(
                "tfa", "该账号开启了双重验证，请输入 6 位动态验证码。", data.get("tfaKey", "")
            )
        raise BambuCloudError(f"登录响应无法识别：{json.dumps(data)[:200]}")

    def request_email_code(self, email: str) -> None:
        resp = self._request(
            "POST",
            self._url("/v1/user-service/user/sendemail/code"),
            body={"email": email, "type": "codeLogin"},
        )
        self._check(resp)

    def request_sms_code(self, phone: str) -> None:
        resp = self._request(
            "POST", self.sms_url, body={"phone": phone, "type": "codeLogin"}
        )
        self._check(resp)

    def login_with_code(self, account: str, code: str) -> dict:
        resp = self._request(
            "POST",
            self._url("/v1/user-service/user/login"),
            body={"account": account, "code": code},
            timeout=20.0,
        )
        self._check(resp, allow_400=True)
        if resp.status_code == 400:
            data = self._json(resp)
            code_num = data.get("code")
            if code_num == 1:
                raise AuthRequired("verifyCode", "验证码已过期，请重新获取。")
            if code_num == 2:
                raise BambuCloudError("验证码不正确。")
            raise BambuCloudError(f"登录失败：{json.dumps(data)[:200]}")
        data = self._json(resp)
        token = data.get("accessToken", "")
        if not token:
            raise BambuCloudError("验证码登录未返回令牌。")
        return {"access_token": token, "refresh_token": data.get("refreshToken", "")}

    def login_with_tfa(self, tfa_key: str, code: str) -> dict:
        csrf = self._request("GET", self.CSRF_URL)
        cookie = ""
        try:
            cookie = csrf.cookies.get("bbl_csrf_token") or ""
        except Exception:
            cookie = ""
        if not cookie:
            raise BambuCloudError("未能取得 CSRF 令牌，无法完成双重验证。")
        resp = self._request(
            "POST",
            self.TFA_URL,
            body={"tfaKey": tfa_key, "tfaCode": code},
            extra_headers={"x-bbl-csrf-token": cookie, "Cookie": f"bbl_csrf_token={cookie}"},
            need_cookies=True,
        )
        self._check(resp)
        try:
            token = resp.cookies.get("token") or ""
        except Exception:
            token = ""
        if not token:
            raise BambuCloudError("双重验证未返回令牌。")
        return {"access_token": token, "refresh_token": ""}

    # ── 账号信息 ─────────────────────────────────────────────
    def get_uid(self, token: str) -> str:
        """从 JWT 里取 uid，失败则退回 preference 接口。"""
        parts = token.split(".")
        if len(parts) == 3:
            try:
                payload = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
                data = json.loads(base64.b64decode(payload))
                uid = data.get("username")
                if uid:
                    return uid if str(uid).startswith("u_") else f"u_{uid}"
            except Exception:
                pass
        try:
            resp = self._request("GET", self._url("/v1/design-user-service/my/preference"), token=token)
            self._check(resp)
            uid = self._json(resp).get("uid")
            if uid:
                return f"u_{uid}"
        except BambuCloudError:
            pass
        return ""

    def get_devices(self, token: str) -> list[dict]:
        resp = self._request("GET", self._url("/v1/iot-service/api/user/bind"), token=token)
        self._check(resp)
        data = self._json(resp)
        return data.get("devices") or []

    def get_tasks(self, token: str, limit: int = 60) -> list[dict]:
        """任务历史。每条含 weight（克）与 amsDetailMapping（每槽位克重）。"""
        url = f"{self._url('/v1/user-service/my/tasks')}?limit={limit}"
        resp = self._request("GET", url, token=token, timeout=25.0)
        self._check(resp)
        data = self._json(resp)
        # 接口在不同版本下用 hits 或 data 承载列表
        return data.get("hits") or data.get("data") or []


@dataclass
class _SimpleResponse:
    """curl_cffi 与 httpx 的最小公共返回面。"""

    status_code: int
    text: str

    @property
    def cookies(self):  # pragma: no cover
        class _NoCookies:
            def get(self, _name):
                return None

        return _NoCookies()


def token_expiry(token: str) -> Optional[datetime]:
    """解析 JWT 的 exp。解析不出来时返回 None。"""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
        data = json.loads(base64.b64decode(payload))
        exp = data.get("exp")
        if exp:
            return datetime.fromtimestamp(int(exp), tz=timezone.utc)
    except Exception:
        return None
    return None


def token_valid_for(token: str, hours: float = 0.0) -> bool:
    if not token:
        return False
    exp = token_expiry(token)
    if exp is None:
        # 不是 JWT 就按刚拿到不久处理
        return True
    return exp - timedelta(hours=hours) > datetime.now(timezone.utc)


def now_ts() -> float:  # pragma: no cover - 便于测试
    return time.time()
