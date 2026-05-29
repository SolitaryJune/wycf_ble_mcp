"""Small helpers for host audio volume state.

This reads the OS volume setting of the current audio device. Live sound
amplitude is handled in the HTML controller through Web Audio.
"""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
from typing import Any


def _run_text(argv: list[str]) -> str:
    return subprocess.check_output(argv, text=True, stderr=subprocess.STDOUT).strip()


def _parse_macos_volume_settings(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in re.findall(r"([a-z ]+):([^,]+)", text):
        normalized_key = key.strip().replace(" ", "_")
        raw = value.strip()
        if raw.lower() in {"true", "false"}:
            result[normalized_key] = raw.lower() == "true"
            continue
        try:
            result[normalized_key] = int(raw)
        except ValueError:
            result[normalized_key] = raw
    return result


def read_system_volume() -> dict[str, Any]:
    system = platform.system()
    if system == "Darwin":
        settings_text = _run_text(["osascript", "-e", "get volume settings"])
        result = _parse_macos_volume_settings(settings_text)
        result["platform"] = "Darwin"
        result["raw"] = settings_text

        switch_audio_source = shutil.which("SwitchAudioSource")
        if switch_audio_source:
            try:
                result["current_output_device"] = _run_text([switch_audio_source, "-c"])
            except subprocess.CalledProcessError:
                pass

        result["note"] = "OS volume setting for the current audio device, not live sound amplitude."
        return result

    return {
        "platform": system,
        "supported": False,
        "note": "Only macOS output/input volume settings are implemented here. Use the HTML audio reactive mode for live amplitude.",
    }
