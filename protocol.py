"""Confirmed TryFun BLE control frames.

The values in this module are based on dynamic `TFBLEWrite` logs captured from
the Spring Yuanli/TryFun app controlling a Black Hole Max device.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import asdict, dataclass, field
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


@dataclass
class AudioBeatReactiveState:
    """Mutable state for one drum/beat reactive audio stream."""

    noise_floor: float = 0.0
    beat_envelope: float = 0.0
    last_beat_at_ms: float = -1_000_000_000.0
    elapsed_total_ms: float = 0.0
    flux_history: list[float] = field(default_factory=list)


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


def _map_normalized_audio_level(
    normalized: float,
    multiplier: float,
    max_level: int,
) -> tuple[float, int]:
    multiplier_value = clamp_float(float(multiplier), -100.0, 100.0)
    max_level_value = clamp_int(int(max_level), 0, 100)
    if normalized <= 0 or max_level_value == 0:
        return 0.0, 0

    raw_level = clamp_float(float(normalized), 0.0, 1.0) * max_level_value * abs(multiplier_value)
    if multiplier_value < 0:
        level = clamp_int(round(max_level_value - raw_level), 0, 100)
    else:
        level = clamp_int(round(raw_level), 0, 100)
    return raw_level, level


def map_audio_beat_level(
    state: AudioBeatReactiveState,
    low_beat_energy_percent: float,
    low_beat_flux_percent: float,
    voice_energy_percent: float = 0.0,
    beat_energy_percent: float | None = None,
    beat_flux_percent: float | None = None,
    elapsed_ms: float = 16.7,
    threshold_percent: float = 1.0,
    gain: float = 8.0,
    multiplier: float = 1.0,
    max_level: int = 100,
    filter_voice: bool = True,
    filter_noise: bool = True,
    drum_only: bool = True,
    beat_sensitivity: float = 0.8,
    beat_release_ms: float = 80.0,
) -> dict[str, Any]:
    """Map beat/drum audio features to a telescopic level.

    Inputs are normalized feature percentages from an upstream analyzer:
    low_beat_* should represent roughly 70..260 Hz, voice_energy should
    represent roughly 300..3400 Hz. The state is mutated so repeated calls
    behave like the Web Audio controller.
    """

    low_energy = clamp_float(float(low_beat_energy_percent), 0.0, 100.0) / 100.0
    low_flux = clamp_float(float(low_beat_flux_percent), 0.0, 100.0) / 100.0
    voice_energy = clamp_float(float(voice_energy_percent), 0.0, 100.0) / 100.0
    beat_energy = low_energy if beat_energy_percent is None else clamp_float(float(beat_energy_percent), 0.0, 100.0) / 100.0
    beat_flux = low_flux if beat_flux_percent is None else clamp_float(float(beat_flux_percent), 0.0, 100.0) / 100.0
    elapsed = clamp_float(float(elapsed_ms), 1.0, 10_000.0)
    threshold = clamp_float(float(threshold_percent), 0.0, 99.0) / 100.0
    gain_value = clamp_float(float(gain), 0.0, 100.0)
    multiplier_value = clamp_float(float(multiplier), -100.0, 100.0)
    max_level_value = clamp_int(int(max_level), 0, 100)
    sensitivity = clamp_float(float(beat_sensitivity), 0.5, 4.0)
    release = clamp_float(float(beat_release_ms), 60.0, 800.0)

    trigger_energy = low_energy if drum_only else beat_energy
    trigger_flux = low_flux if drum_only else beat_flux

    if filter_noise:
        if state.noise_floor == 0:
            state.noise_floor = trigger_energy
        else:
            follow = 0.18 if trigger_energy < state.noise_floor else 0.006
            state.noise_floor = state.noise_floor * (1 - follow) + trigger_energy * follow
    else:
        state.noise_floor = 0.0

    gate = threshold + (state.noise_floor if filter_noise else 0.0)
    flux_average = sum(state.flux_history) / len(state.flux_history) if state.flux_history else 0.0
    flux_deviation = (
        math.sqrt(sum((item - flux_average) ** 2 for item in state.flux_history) / len(state.flux_history))
        if state.flux_history
        else 0.0
    )
    min_flux = 0.02 if drum_only else (0.016 if filter_noise else 0.008)
    flux_threshold = max(min_flux, flux_average + flux_deviation * (3.4 / sensitivity))
    beat_cooldown = clamp_float(release * 4, 220.0, 360.0)
    ready = len(state.flux_history) >= 8
    in_cooldown = state.elapsed_total_ms - state.last_beat_at_ms < beat_cooldown
    voice_dominant = (
        bool(filter_voice)
        and voice_energy > max(0.04, low_energy * (1.1 if drum_only else 1.8))
        and low_flux < flux_threshold * (1.4 if drum_only else 0.75)
    )
    candidate = (
        ready
        and not in_cooldown
        and max_level_value > 0
        and trigger_energy > gate
        and trigger_flux > flux_threshold
    )
    onset = candidate and not voice_dominant

    if onset:
        flux_strength = clamp_float((trigger_flux - flux_threshold) / max(flux_threshold, min_flux), 0.0, 2.0)
        energy_strength = clamp_float((trigger_energy - gate) / max(0.02, 0.22 - gate), 0.0, 1.0)
        beat_strength = clamp_float(max(energy_strength, flux_strength * 0.65) * gain_value * 0.16, 0.28, 1.0)
        state.beat_envelope = max(state.beat_envelope, beat_strength)
        state.last_beat_at_ms = state.elapsed_total_ms
    else:
        state.beat_envelope *= math.exp(-elapsed / release)
        if state.beat_envelope < 0.025:
            state.beat_envelope = 0.0

    state.flux_history.append(trigger_flux)
    if len(state.flux_history) > 80:
        del state.flux_history[:-80]
    state.elapsed_total_ms += elapsed

    raw_level, level = _map_normalized_audio_level(state.beat_envelope, multiplier_value, max_level_value)
    return {
        "mode": "drum_only" if drum_only else "beat",
        "level": level,
        "raw_level": raw_level,
        "normalized": state.beat_envelope,
        "onset": onset,
        "candidate": candidate,
        "suppressed_by_voice": candidate and voice_dominant,
        "voice_dominant": voice_dominant,
        "trigger_energy_percent": round(trigger_energy * 100.0, 6),
        "trigger_flux_percent": round(trigger_flux * 100.0, 6),
        "voice_energy_percent": round(voice_energy * 100.0, 6),
        "gate_percent": round(gate * 100.0, 6),
        "noise_floor_percent": round(state.noise_floor * 100.0, 6),
        "flux_threshold_percent": round(flux_threshold * 100.0, 6),
        "flux_history_count": len(state.flux_history),
        "elapsed_total_ms": round(state.elapsed_total_ms, 3),
        "options": {
            "threshold_percent": threshold * 100.0,
            "gain": gain_value,
            "multiplier": multiplier_value,
            "max_level": max_level_value,
            "filter_voice": bool(filter_voice),
            "filter_noise": bool(filter_noise),
            "drum_only": bool(drum_only),
            "beat_sensitivity": sensitivity,
            "beat_release_ms": release,
        },
    }


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


def describe_audio_beat_frame(
    state: AudioBeatReactiveState,
    low_beat_energy_percent: float,
    low_beat_flux_percent: float,
    voice_energy_percent: float = 0.0,
    beat_energy_percent: float | None = None,
    beat_flux_percent: float | None = None,
    elapsed_ms: float = 16.7,
    threshold_percent: float = 1.0,
    gain: float = 8.0,
    multiplier: float = 1.0,
    max_level: int = 100,
    filter_voice: bool = True,
    filter_noise: bool = True,
    drum_only: bool = True,
    beat_sensitivity: float = 0.8,
    beat_release_ms: float = 80.0,
    seq: int | None = None,
) -> dict[str, Any]:
    mapping = map_audio_beat_level(
        state,
        low_beat_energy_percent,
        low_beat_flux_percent,
        voice_energy_percent,
        beat_energy_percent,
        beat_flux_percent,
        elapsed_ms,
        threshold_percent,
        gain,
        multiplier,
        max_level,
        filter_voice,
        filter_noise,
        drum_only,
        beat_sensitivity,
        beat_release_ms,
    )
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
