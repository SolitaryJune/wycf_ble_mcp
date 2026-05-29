"""Confirmed TryFun BLE control frames.

The values in this module are based on dynamic `TFBLEWrite` logs captured from
the Spring Yuanli/TryFun app controlling a Black Hole Max device.
"""

from __future__ import annotations

import random
import time
from dataclasses import asdict, dataclass
from typing import Any


CONTROL_SERVICE_UUID = "0000ffac-0000-1000-8000-00805f9b34fb"
CONTROL_WRITE_UUID = "0000ffb7-0000-1000-8000-00805f9b34fb"
CONTROL_WRITE_WITH_RESPONSE_UUID = "0000ffb5-0000-1000-8000-00805f9b34fb"
CONTROL_NOTIFY_UUID = "0000ffb8-0000-1000-8000-00805f9b34fb"

OP_SET_LEVEL = 0x02
COMMAND_TELESCOPIC_LEVEL = 0x0C
COMMAND_HEATING_SWITCH = 0x05

COMMAND_NAMES = {
    "telescopic": COMMAND_TELESCOPIC_LEVEL,
    "heat": COMMAND_HEATING_SWITCH,
    "heating": COMMAND_HEATING_SWITCH,
    "伸缩": COMMAND_TELESCOPIC_LEVEL,
    "加热": COMMAND_HEATING_SWITCH,
}


@dataclass
class ControlFrame:
    seq: int
    op: int
    command_id: int
    level: int
    checksum: int
    payload_hex: str


@dataclass
class AudioLevelMapping:
    volume_percent: float
    threshold_percent: float
    gain: float
    multiplier: float
    max_level: int
    normalized: float
    raw_level: float
    inverted: bool
    level: int


def clamp_float(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    return min(maximum, max(minimum, value))


def normalize_level_range(min_level: int = 0, max_level: int = 100) -> tuple[int, int]:
    low = clamp_int(int(min_level), 0, 100)
    high = clamp_int(int(max_level), 0, 100)
    return (low, high) if low <= high else (high, low)


def auto_seq() -> int:
    """Return a changing 4-bit sequence value like the official app uses."""
    return int(time.monotonic() * 10) & 0x0F


def normalize_byte(value: int, name: str) -> int:
    if not 0 <= value <= 0xFF:
        raise ValueError(f"{name} must be in range 0..255")
    return value


def level_checksum(command_id: int, level: int) -> int:
    """Checksum seen in app logs: last byte is `-(command_id + level) & 0xff`."""
    return (-(normalize_byte(command_id, "command_id") + normalize_byte(level, "level"))) & 0xFF


def build_level_frame(command_id: int, level: int, seq: int | None = None) -> bytes:
    seq_value = auto_seq() if seq is None else normalize_byte(seq, "seq")
    command_value = normalize_byte(command_id, "command_id")
    level_value = normalize_byte(level, "level")
    return bytes(
        [
            seq_value,
            OP_SET_LEVEL,
            0x00,
            0x03,
            command_value,
            level_value,
            level_checksum(command_value, level_value),
        ]
    )


def build_named_level_frame(name: str, level: int, seq: int | None = None) -> bytes:
    key = name.strip().lower()
    if key not in COMMAND_NAMES:
        raise KeyError(f"unknown control name: {name}")
    return build_level_frame(COMMAND_NAMES[key], level, seq)


def describe_level_frame(command_id: int, level: int, seq: int | None = None) -> dict[str, Any]:
    payload = build_level_frame(command_id, level, seq)
    return asdict(
        ControlFrame(
            seq=payload[0],
            op=payload[1],
            command_id=payload[4],
            level=payload[5],
            checksum=payload[6],
            payload_hex=payload.hex(),
        )
    )


def describe_named_level_frame(name: str, level: int, seq: int | None = None) -> dict[str, Any]:
    key = name.strip().lower()
    if key not in COMMAND_NAMES:
        raise KeyError(f"unknown control name: {name}")
    frame = describe_level_frame(COMMAND_NAMES[key], level, seq)
    frame["name"] = key
    frame["characteristic_uuid"] = (
        CONTROL_WRITE_WITH_RESPONSE_UUID if COMMAND_NAMES[key] == COMMAND_HEATING_SWITCH else CONTROL_WRITE_UUID
    )
    frame["response"] = COMMAND_NAMES[key] == COMMAND_HEATING_SWITCH
    return frame


def describe_telescopic_frame(level: int, seq: int | None = None) -> dict[str, Any]:
    frame = describe_level_frame(COMMAND_TELESCOPIC_LEVEL, level, seq)
    frame["name"] = "telescopic"
    frame["characteristic_uuid"] = CONTROL_WRITE_UUID
    frame["response"] = False
    return frame


def describe_random_telescopic_frame(
    min_level: int = 0,
    max_level: int = 100,
    seq: int | None = None,
) -> dict[str, Any]:
    low, high = normalize_level_range(min_level, max_level)
    level = random.randint(low, high)
    return {
        "mode": "random",
        "min_level": low,
        "max_level": high,
        "level": level,
        "frame": describe_telescopic_frame(level, seq),
    }


def describe_random_telescopic_sequence(
    count: int = 10,
    min_level: int = 0,
    max_level: int = 100,
    interval_ms: int = 500,
    seq: int | None = None,
) -> dict[str, Any]:
    low, high = normalize_level_range(min_level, max_level)
    frame_count = clamp_int(int(count), 1, 1000)
    interval = clamp_int(int(interval_ms), 50, 60000)
    start_seq = auto_seq() if seq is None else normalize_byte(seq, "seq")
    frames = [
        describe_telescopic_frame(random.randint(low, high), (start_seq + index) & 0xFF)
        for index in range(frame_count)
    ]
    return {
        "mode": "random_sequence",
        "count": frame_count,
        "min_level": low,
        "max_level": high,
        "interval_ms": interval,
        "frames": frames,
    }


def describe_heating_frame(on: bool, seq: int | None = None) -> dict[str, Any]:
    frame = describe_level_frame(COMMAND_HEATING_SWITCH, 1 if on else 0, seq)
    frame["name"] = "heating"
    frame["on"] = bool(on)
    frame["characteristic_uuid"] = CONTROL_WRITE_WITH_RESPONSE_UUID
    frame["response"] = True
    return frame


def map_audio_level(
    volume_percent: float,
    threshold_percent: float = 1.0,
    gain: float = 8.0,
    multiplier: float = 1.0,
    max_level: int = 100,
) -> dict[str, Any]:
    volume = clamp_float(float(volume_percent), 0.0, 100.0)
    threshold = clamp_float(float(threshold_percent), 0.0, 99.0)
    gain_value = clamp_float(float(gain), 0.0, 100.0)
    multiplier_value = clamp_float(float(multiplier), -100.0, 100.0)
    max_level_value = clamp_int(int(max_level), 0, 100)
    if volume <= threshold or max_level_value == 0:
        normalized = 0.0
        raw_level = 0.0
        level = 0
    else:
        normalized = ((volume - threshold) / max(1.0, 100.0 - threshold)) * gain_value * abs(multiplier_value)
        raw_level = normalized * max_level_value
        if multiplier_value < 0:
            level = clamp_int(round(max_level_value - raw_level), 0, 100)
        else:
            level = clamp_int(round(raw_level), 0, 100)
    return asdict(
        AudioLevelMapping(
            volume_percent=volume,
            threshold_percent=threshold,
            gain=gain_value,
            multiplier=multiplier_value,
            max_level=max_level_value,
            normalized=normalized,
            raw_level=raw_level,
            inverted=multiplier_value < 0,
            level=level,
        )
    )


def describe_audio_level_frame(
    volume_percent: float,
    threshold_percent: float = 1.0,
    gain: float = 8.0,
    multiplier: float = 1.0,
    max_level: int = 100,
    seq: int | None = None,
) -> dict[str, Any]:
    mapping = map_audio_level(volume_percent, threshold_percent, gain, multiplier, max_level)
    frame = describe_telescopic_frame(int(mapping["level"]), seq)
    return {"mapping": mapping, "frame": frame}


def decode_control_notification(payload_hex: str) -> dict[str, Any]:
    clean = "".join(ch for ch in payload_hex if ch in "0123456789abcdefABCDEF")
    if len(clean) % 2 != 0:
        raise ValueError("payload_hex must contain an even number of hex digits")
    payload = bytes.fromhex(clean)
    result: dict[str, Any] = {"payload_hex": payload.hex(), "length": len(payload)}
    if len(payload) == 7 and payload[1] == 0x07:
        result.update(
            {
                "type": "ack",
                "seq": payload[0],
                "op": payload[1],
                "command_id": payload[4],
                "level": payload[5],
                "checksum": payload[6],
            }
        )
        return result
    if len(payload) == 19:
        fields = {
            f"0x{payload[index]:02x}": payload[index + 1]
            for index in range(8, len(payload) - 1, 2)
        }
        result.update(
            {
                "type": "status",
                "seq": payload[0],
                "op": payload[1],
                "fields": fields,
                "heating_on": bool(fields.get("0x05", 0)),
                "checksum": payload[-1],
            }
        )
        return result
    result["type"] = "unknown"
    return result
