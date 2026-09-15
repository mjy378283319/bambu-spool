"""拓竹云接口地址与登录状态流转的离线自测（不联网）。

背景：短信验证码接口曾经写成 https://api.bambulab.cn/api/v1/...（多一段 /api），
拓竹网关返回 404 {"error_msg":"404 Route Not Found"}，用户在设置页只看到一条莫名其妙的报错。
这里把地址固定死，并检查「改用验证码登录」后状态是否变成 verifyCode（前端据此显示验证码输入框）。

用法：python tests/test_cloud_endpoints.py
"""
from __future__ import annotations

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

os.environ["BAMBU_MOCK"] = "1"
os.environ["DATA_DIR"] = os.path.join(ROOT, "data", "testcloud")
os.environ["ALLOW_PUBLIC_SETUP"] = "1"

PASSED = 0
FAILED: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASSED
    if condition:
        PASSED += 1
    else:
        FAILED.append(f"{name}{(' — ' + detail) if detail else ''}")


def reset() -> None:
    from app import db

    try:
        db.engine.dispose()
    except Exception:
        pass
    data_dir = os.environ["DATA_DIR"]
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir, ignore_errors=True)
    os.makedirs(data_dir, exist_ok=True)
    db.init_db()


# ── 接口地址 ────────────────────────────────────────────────
def test_endpoints() -> None:
    from app.cloud.api import ApiClient

    c_cn = ApiClient("china")
    c_gl = ApiClient("global")

    # 短信验证码：不带多余的 /api 段（这正是当初 404 的原因）
    check(
        "中国区短信接口地址",
        c_cn.sms_url == "https://api.bambulab.cn/v1/user-service/user/sendsmscode",
        c_cn.sms_url,
    )
    check("/api 段不得出现", "/api/v1/user-service/user/sendsmscode" not in c_cn.sms_url, c_cn.sms_url)
    check(
        "海外区短信接口地址",
        c_gl.sms_url == "https://api.bambulab.com/v1/user-service/user/sendsmscode",
        c_gl.sms_url,
    )

    # 其余接口保持与上游 ha-bambulab 一致
    check("登录接口", c_cn._url("/v1/user-service/user/login") ==
          "https://api.bambulab.cn/v1/user-service/user/login")
    check("邮箱验证码接口", c_cn._url("/v1/user-service/user/sendemail/code") ==
          "https://api.bambulab.cn/v1/user-service/user/sendemail/code")
    check("2FA 接口", ApiClient.TFA_URL == "https://bambulab.com/api/sign-in/tfa")
    check("CSRF 接口", ApiClient.CSRF_URL == "https://bambulab.com/api/sign-in/csrf")
    check("MQTT 中国区", c_cn.mqtt_host == "cn.mqtt.bambulab.com")
    check("MQTT 海外区", c_gl.mqtt_host == "us.mqtt.bambulab.com")

    # 未知区域回退到中国区
    check("未知区域回退", ApiClient("mars").region == "china")


def test_sms_body() -> None:
    """request_sms_code 必须提交 phone + type=codeLogin。"""
    from app.cloud.api import ApiClient

    captured: dict = {}

    class FakeResp:
        status_code = 200
        text = "{}"

    client = ApiClient("china")

    def fake_request(method, url, token="", body=None, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["body"] = body
        return FakeResp()

    client._request = fake_request  # type: ignore[method-assign]
    client.request_sms_code("13352093556")

    check("短信方法为 POST", captured.get("method") == "POST", str(captured.get("method")))
    check("短信地址正确", captured.get("url") == client.sms_url, str(captured.get("url")))
    check("提交 phone 字段", (captured.get("body") or {}).get("phone") == "13352093556",
          str(captured.get("body")))
    check("提交 type=codeLogin", (captured.get("body") or {}).get("type") == "codeLogin",
          str(captured.get("body")))


def test_gateway_404_hint() -> None:
    """网关 404 要给出人能看懂的提示，而不是甩原始 JSON。"""
    from app.cloud.api import ApiClient, BambuCloudError

    class FakeResp:
        status_code = 404
        text = '{"error_msg":"404 Route Not Found"}'

    try:
        ApiClient._check(FakeResp())
        check("网关 404 应抛错", False, "没有抛异常")
    except BambuCloudError as exc:
        message = str(exc)
        check("404 提示可读", "接口地址无效" in message, message)
        check("404 不再暴露原始 JSON", "error_msg" not in message, message)


def test_request_code_sets_status() -> None:
    """点「改用验证码登录」后，账号状态要变成 verifyCode，前端才会显示验证码输入框。"""
    import asyncio

    from sqlmodel import select

    from app import db
    from app.cloud import api as api_module
    from app.core.hub import hub
    from app.models import CloudAccount

    reset()

    sent: dict = {}

    def fake_sms(self, phone):
        sent["phone"] = phone

    def fake_email(self, email):
        sent["email"] = email

    api_module.ApiClient.request_sms_code = fake_sms  # type: ignore[method-assign]
    api_module.ApiClient.request_email_code = fake_email  # type: ignore[method-assign]

    message = asyncio.run(hub.request_code("13352093556", "china"))
    check("短信已触发", sent.get("phone") == "13352093556", str(sent))
    check("返回文案含手机号", "13352093556" in message, message)

    with db.session_scope() as session:
        acc = session.exec(select(CloudAccount)).first()
        check("账号已建档", acc is not None)
        if acc:
            check("状态为 verifyCode", acc.status == "verifyCode", acc.status)
            check("账号名已保存", acc.account == "13352093556", acc.account)

    # 邮箱走另一条分支
    message = asyncio.run(hub.request_code("me@example.com", "china"))
    check("邮箱分支已触发", sent.get("email") == "me@example.com", str(sent))
    check("邮箱文案正确", "me@example.com" in message, message)


def main() -> int:
    for fn in (test_endpoints, test_sms_body, test_gateway_404_hint, test_request_code_sets_status):
        try:
            fn()
        except Exception as exc:  # pragma: no cover - 汇总输出
            FAILED.append(f"{fn.__name__} 抛异常: {type(exc).__name__}: {exc}")

    print(f"通过 {PASSED} 项")
    if FAILED:
        print(f"失败 {len(FAILED)} 项：")
        for item in FAILED:
            print("  -", item)
        return 1
    print("全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
