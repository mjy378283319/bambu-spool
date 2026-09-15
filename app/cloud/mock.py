"""模拟数据源：在没有真实打印机与拓竹账号时，跑通完整链路。

会模拟一台 P2S + AMS 2 Pro：
  空闲 → 准备中 → 打印中（进度递增）→ 已完成 → 空闲
并同步给出与云端任务记录同构的用量数据，让扣重逻辑得到真实验证。
"""
from __future__ import annotations

import random
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

MessageHandler = Callable[[str, dict], None]

MOCK_TRAYS = [
    {"tray_type": "PLA", "tray_sub_brands": "PLA Basic", "tray_color": "1A1A1AFF",
     "tray_info_idx": "GFA00", "tag_uid": "1111111111111111", "remain": 82, "tray_weight": "1000"},
    {"tray_type": "PETG", "tray_sub_brands": "PETG HF", "tray_color": "1E88E5FF",
     "tray_info_idx": "GFG02", "tag_uid": "2222222222222222", "remain": 64, "tray_weight": "1000"},
    {"tray_type": "", "tray_sub_brands": "", "tray_color": "00000000",
     "tray_info_idx": "", "tag_uid": "0000000000000000", "remain": -1, "tray_weight": "1000"},
    {"tray_type": "PLA", "tray_sub_brands": "PLA Matte", "tray_color": "EC407AFF",
     "tray_info_idx": "GFA01", "tag_uid": "4444444444444444", "remain": 41, "tray_weight": "1000"},
]

MOCK_USAGE = [
    {"filamentId": "GFA00", "filamentType": "PLA", "sourceColor": "1A1A1AFF",
     "targetColor": "1A1A1AFF", "weight": 9.42, "ams": 0},
    {"filamentId": "GFG02", "filamentType": "PETG", "sourceColor": "1E88E5FF",
     "targetColor": "1E88E5FF", "weight": 3.16, "ams": 1},
]

# AMS HT 的 ams_id 固定从 128 起，只带一个槽位；湿度按百分比上报（普通 AMS 是 0-5 档位）
MOCK_HT_ID = 128
MOCK_HT_TRAY = {
    "tray_type": "PLA", "tray_sub_brands": "PLA", "tray_color": "4FC3F7FF",
    "tray_info_idx": "GFA00", "tag_uid": "0000000000000000", "remain": 24,
    "tray_weight": "1000",
}

# 外挂料盘（vt_tray）
MOCK_EXT_TRAY = {
    "tray_type": "PLA", "tray_sub_brands": "PLA", "tray_color": "1A1A1AFF",
    "tray_info_idx": "GFA00", "tag_uid": "0000000000000000", "remain": 76,
    "tray_weight": "1000",
}

# 仓温 32 位打包值：低 16 位 = 当前 27℃，高 16 位 = 目标 0（P2S 的 ctc 口径）
MOCK_CHAMBER_TEMP = 27


class MockSource:
    def __init__(self, serial: str = "01S00A0000000000"):
        self.serial = serial
        self._emit: Optional[MessageHandler] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = False
        self._job_started: Optional[datetime] = None
        self._current_task_id = ""

    # ── 生命周期 ────────────────────────────────────────────
    def start(self, emit: MessageHandler) -> None:
        self._emit = emit
        self._stop = False
        self._thread = threading.Thread(target=self._run, name="mock-printer", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop = True
        if self._thread:
            self._thread.join(timeout=3)

    def current_job_started(self) -> Optional[datetime]:
        return self._job_started

    # ── 内部 ────────────────────────────────────────────────
    def _push(self, print_block: dict) -> None:
        if self._emit:
            self._emit(self.serial, {"print": print_block})

    def _base(self) -> dict:
        return {
            "ams": {
                "ams": [
                    {
                        "id": "0",
                        "info": "AMS 2 Pro",
                        "humidity": "3",
                        "temp": "31.5",
                        "tray": [
                            {"id": str(i), **tray,
                             "tray_diameter": "1.75", "nozzle_temp_min": "190",
                             "nozzle_temp_max": "240", "tray_uuid": tray["tag_uid"]}
                            for i, tray in enumerate(MOCK_TRAYS)
                        ],
                    },
                    {
                        "id": str(MOCK_HT_ID),
                        "info": "AMS HT",
                        "humidity": "21",
                        "temp": "27.9",
                        "tray": [
                            {"id": "0", **MOCK_HT_TRAY,
                             "tray_diameter": "1.75", "nozzle_temp_min": "190",
                             "nozzle_temp_max": "240", "tray_uuid": "0000000000000000"}
                        ],
                    },
                ],
                # 位串与 MOCK_TRAYS 对齐：槽位 1/2/4 有料，槽位 3 为空（0b1011）
                "tray_exist_bits": "b",
                "tray_now": "255",
                "tray_tar": "255",
                "ams_exist_bits": "1",
            },
            "vt_tray": dict(MOCK_EXT_TRAY),
            "gcode_state": "IDLE",
            "stg_cur": 255,
            "mc_percent": 0,
            "mc_remaining_time": 0,
            "layer_num": 0,
            "total_layer_num": 0,
            "nozzle_temper": 28.0,
            "nozzle_target_temper": 0,
            "bed_temper": 26.0,
            "bed_target_temper": 0,
            # 风扇上报的是 0-15 的 PWM 档位（15 = 100%），不是百分比。
            # P2S 的辅助风扇**不在 big_fan1 里报** —— 真机上 big_fan1/big_fan2
            # 都是 0，它报在自适应风道切换组件的 parts 里，且 state 本身就是百分比。
            # 模拟的是一台装齐选配件的 P2S：左侧辅助风扇 + 外排风扇套件。
            "cooling_fan_speed": "0",
            "big_fan1_speed": "0",
            # 外排风扇套件在真机上走哪一路尚未坐实，这里按 big_fan2 档位模拟
            "big_fan2_speed": "0",
            "heatbreak_fan_speed": "15",
            # P2S 真机结构：仓温在 device.ctc.info.temp（低 16 位当前值、高 16 位目标值）；
            # airduct.parts 里 func 0 是风扇、func 6/8 是风门机构。
            # id 16 = 右(辅助)（自适应风道组件自带），id 32 = 风门，
            # id 160 = 左(辅助)（选配，ha-bambulab 也按这个 id 认）。
            "device": {
                "ctc": {"info": {"temp": MOCK_CHAMBER_TEMP}, "state": 0},
                "airduct": {
                    "modeCur": 0,
                    "modeList": [{"modeId": 0, "ctrl": [16, 32, 160], "off": []}],
                    "parts": [
                        {"func": 0, "id": 16, "state": 0},
                        {"func": 6, "id": 32, "state": 0},
                        {"func": 0, "id": 160, "state": 0},
                    ],
                },
            },
            "aux_part_fan": True,
            "wifi_signal": "-45dBm",
            "lights_report": [{"node": "chamber_light", "mode": "on"}],
            "hms": [],
            "fun": "3EC1AFFF9CFF",
            "task_id": "",
            "subtask_name": "",
            "print_type": "idle",
        }

    def _run(self) -> None:
        # 先推一次空闲状态
        self._push(self._base())
        while not self._stop:
            if not self._sleep(6):
                return
            cycle = ["PREPARE", "RUNNING", "FINISH"]
            for phase in cycle:
                if self._stop:
                    return
                if phase == "PREPARE":
                    block = self._base()
                    block.update({"gcode_state": "PREPARE", "stg_cur": 1, "mc_percent": 0,
                                  "subtask_name": "WALL-E_机械臂.stl", "print_type": "cloud",
                                  "task_id": ""})
                    self._push(block)
                    if not self._sleep(10):
                        return
                elif phase == "RUNNING":
                    self._current_task_id = f"mock-{random.randint(100000, 999999)}"
                    self._job_started = datetime.utcnow()
                    total_layers = 120
                    for step in range(1, 21):
                        if self._stop:
                            return
                        percent = step * 5
                        block = self._base()
                        block.update({
                            "gcode_state": "RUNNING",
                            "stg_cur": 0,
                            "mc_percent": percent,
                            "mc_remaining_time": max(0, (20 - step) * 2),
                            "layer_num": int(total_layers * percent / 100),
                            "total_layer_num": total_layers,
                            "subtask_name": "WALL-E_机械臂.stl",
                            "task_id": self._current_task_id,
                            "print_type": "cloud",
                            "nozzle_temper": 219.5,
                            "nozzle_target_temper": 220,
                            "bed_temper": 59.8,
                            "bed_target_temper": 60,
                            # 打印中，四路各不同：部件 10/15 ≈ 70%、
                            # 右(辅助) 90%、左(辅助) 40%、外排 9/15 = 60%
                            "cooling_fan_speed": "10",
                            "big_fan2_speed": "9",
                            "heatbreak_fan_speed": "15",
                        })
                        block["device"]["ctc"]["info"]["temp"] = MOCK_CHAMBER_TEMP + 8
                        for part in block["device"]["airduct"]["parts"]:
                            if part["id"] == 16:
                                part["state"] = 90
                            elif part["id"] == 160:
                                part["state"] = 40
                        # 官方 RFID 料盘的余量随打印缓慢下降
                        block["ams"]["tray_now"] = "0"
                        block["ams"]["ams"][0]["tray"][0]["remain"] = 82 - int(percent / 12)
                        block["ams"]["ams"][0]["tray"][1]["remain"] = 64 - int(percent / 30)
                        self._push(block)
                        if not self._sleep(4):
                            return
                else:
                    block = self._base()
                    block.update({"gcode_state": "FINISH", "stg_cur": 255, "mc_percent": 100,
                                  "subtask_name": "WALL-E_机械臂.stl",
                                  "task_id": self._current_task_id, "print_type": "cloud"})
                    block["ams"]["ams"][0]["tray"][0]["remain"] = 74
                    block["ams"]["ams"][0]["tray"][1]["remain"] = 61
                    self._push(block)
                    if not self._sleep(12):
                        return
                    self._push(self._base())

    def _sleep(self, seconds: float) -> bool:
        """可中断睡眠。返回 False 表示被要求停止。"""
        deadline = time.time() + seconds
        while time.time() < deadline:
            if self._stop:
                return False
            time.sleep(0.2)
        return True

    # ── 模拟云端任务记录 ─────────────────────────────────────
    def build_task(self) -> dict:
        started = self._job_started or datetime.utcnow()
        return {
            "id": random.randint(30000000, 40000000),
            "title": "WALL-E_机械臂.stl",
            "cover": "",
            "status": 4,
            "startTime": (started - timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "endTime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "weight": round(sum(item["weight"] for item in MOCK_USAGE), 2),
            "length": 4185,
            "costTime": 1320,
            "deviceId": self.serial,
            "deviceModel": "P2S",
            "deviceName": "模拟 P2S",
            "plateIndex": 1,
            "mode": "cloud_file",
            "amsDetailMapping": [dict(item) for item in MOCK_USAGE],
        }
