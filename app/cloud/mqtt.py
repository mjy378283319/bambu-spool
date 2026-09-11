"""拓竹云 MQTT 客户端。

连接参数（已核对 ha-bambulab pybambu/const.py 与 coelacant1 API_MQTT.md）：
- broker: cn.mqtt.bambulab.com / us.mqtt.bambulab.com，端口 8883，TLS
- username: u_{uid}，password: accessToken
- 订阅 device/{serial}/report；发往 device/{serial}/request 触发全量推送

一个账号只维持一条连接，订阅多台设备的主题，避免触发拓竹的连接数限制。
"""
from __future__ import annotations

import json
import ssl
import threading
import time
from typing import Callable, Optional

import paho.mqtt.client as mqtt

MessageHandler = Callable[[str, dict], None]
StatusHandler = Callable[[str, bool, str], None]  # serial/scope, connected, reason


class CloudMqttConnection:
    """一条账号级云 MQTT 连接，可订阅多台打印机。"""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        on_message: MessageHandler,
        on_status: Optional[StatusHandler] = None,
        keepalive: int = 30,
        client_id: str = "",
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.keepalive = keepalive
        self._on_message = on_message
        self._on_status = on_status
        self._serials: set[str] = set()
        self._lock = threading.Lock()
        self._connected = False
        self._last_error = ""
        self._stop = False

        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id or f"bambu_spool_{int(time.time())}",
            protocol=mqtt.MQTTv311,
            clean_session=True,
        )
        self._client.username_pw_set(username, password)
        # 云 broker 用公共 CA 签发证书，正常校验
        context = ssl.create_default_context()
        self._client.tls_set_context(context)
        self._client.on_connect = self._handle_connect
        self._client.on_disconnect = self._handle_disconnect
        self._client.on_message = self._handle_message

    # ── 生命周期 ──────────────────────────────────────────────
    def start(self) -> None:
        self._stop = False
        self._client.connect_async(self.host, 8883, self.keepalive)
        self._client.loop_start()

    def stop(self) -> None:
        self._stop = True
        try:
            self._client.disconnect()
        except Exception:
            pass
        try:
            self._client.loop_stop()
        except Exception:
            pass

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def last_error(self) -> str:
        return self._last_error

    # ── 订阅 ─────────────────────────────────────────────────
    def set_serials(self, serials: list[str]) -> None:
        """更新要订阅的设备集合，自动补齐/取消订阅。"""
        wanted = {s for s in serials if s}
        with self._lock:
            added = wanted - self._serials
            removed = self._serials - wanted
            self._serials = wanted
        if self._connected:
            for serial in added:
                self._subscribe(serial)
            for serial in removed:
                try:
                    self._client.unsubscribe(f"device/{serial}/report")
                except Exception:
                    pass

    def _subscribe(self, serial: str) -> None:
        try:
            self._client.subscribe(f"device/{serial}/report", qos=0)
            self.publish(f"device/{serial}/request", self._pushall_payload())
        except Exception as exc:  # pragma: no cover
            self._last_error = str(exc)

    @staticmethod
    def _pushall_payload() -> dict:
        return {"pushing": {"sequence_id": "1", "command": "pushall"}}

    def request_pushall(self, serial: str = "") -> None:
        targets = [serial] if serial else sorted(self._serials)
        for item in targets:
            self.publish(f"device/{item}/request", self._pushall_payload())

    def publish(self, topic: str, payload: dict) -> None:
        try:
            self._client.publish(topic, json.dumps(payload), qos=0)
        except Exception as exc:
            self._last_error = str(exc)

    # ── 回调 ─────────────────────────────────────────────────
    def _handle_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        ok = int(getattr(reason_code, "value", reason_code) or 0) == 0
        self._connected = ok
        if ok:
            self._last_error = ""
            with self._lock:
                serials = sorted(self._serials)
            for serial in serials:
                self._subscribe(serial)
        else:
            self._last_error = f"连接被拒绝，返回码 {reason_code}"
        if self._on_status:
            self._on_status("mqtt", ok, self._last_error)

    def _handle_disconnect(self, client, userdata, flags, reason_code, properties=None) -> None:
        self._connected = False
        reason = f"连接断开（{reason_code}）"
        if not self._stop:
            self._last_error = reason
        if self._on_status:
            self._on_status("mqtt", False, reason)

    def _handle_message(self, client, userdata, message) -> None:
        topic = message.topic or ""
        parts = topic.split("/")
        if len(parts) < 3:
            return
        serial = parts[1]
        try:
            payload = json.loads(message.payload.decode("utf-8", errors="replace"))
        except (ValueError, UnicodeDecodeError):
            return
        if isinstance(payload, dict):
            try:
                self._on_message(serial, payload)
            except Exception:  # 单条消息解析失败不影响连接
                pass
