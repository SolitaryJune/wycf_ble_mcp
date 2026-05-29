"""Helpers for extracting BLE write facts from patched Android logcat output."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
SHORT_UUID_RE = re.compile(r"\b[0-9a-fA-F]{4}\b")
MAC_RE = re.compile(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}")


@dataclass
class BleWriteLog:
    line: str
    device: str | None = None
    service_uuid: str | None = None
    characteristic_uuid: str | None = None
    write_type: str | None = None
    payload_hex: str | None = None


def normalize_hex(value: str) -> str:
    """Normalize common byte dump formats into lowercase compact hex."""
    value = value.strip()
    if not value:
        return ""
    if value.startswith("[") and value.endswith("]"):
        parts = re.split(r"[\s,]+", value.strip("[] "))
        out = []
        for part in parts:
            if not part:
                continue
            if part.lower().startswith("0x"):
                out.append(f"{int(part, 16) & 0xff:02x}")
            else:
                out.append(f"{int(part, 10) & 0xff:02x}")
        return "".join(out)
    return re.sub(r"[^0-9a-fA-F]", "", value).lower()


def expand_uuid(value: str) -> str:
    value = value.strip().lower()
    if UUID_RE.fullmatch(value):
        return value
    if SHORT_UUID_RE.fullmatch(value):
        return f"0000{value}-0000-1000-8000-00805f9b34fb"
    return value


def parse_write_lines(lines: Iterable[str]) -> list[BleWriteLog]:
    writes: list[BleWriteLog] = []
    for raw in lines:
        line = raw.rstrip("\n")
        if "TFBLEWrite" not in line and "writeCharacteristic" not in line:
            continue
        entry = BleWriteLog(line=line)

        mac = MAC_RE.search(line)
        if mac:
            entry.device = mac.group(0)

        uuids = [m.group(0).lower() for m in UUID_RE.finditer(line)]
        if len(uuids) >= 1:
            entry.service_uuid = uuids[0]
        if len(uuids) >= 2:
            entry.characteristic_uuid = uuids[1]

        uuid_pattern = r"(" + UUID_RE.pattern + r"|" + SHORT_UUID_RE.pattern + r")"

        for key in ("service_uuid", "serviceUuid", "service"):
            match = re.search(key + r"\s*[=:]\s*" + uuid_pattern, line, re.I)
            if match:
                entry.service_uuid = expand_uuid(match.group(1))
                break

        for key in ("characteristic_uuid", "characteristicUuid", "characteristic", "char"):
            match = re.search(key + r"\s*[=:]\s*" + uuid_pattern, line, re.I)
            if match:
                entry.characteristic_uuid = expand_uuid(match.group(1))
                break

        match = re.search(r"write[_ -]?type\s*[=:]\s*([A-Za-z0-9_-]+)", line, re.I)
        if match:
            entry.write_type = match.group(1).strip()

        match = re.search(r"dec\s*[=:]\s*(\[[^\]]+\])", line, re.I)
        if match:
            hex_value = normalize_hex(match.group(1))
            if hex_value:
                entry.payload_hex = hex_value

        for key in ("payload", "value", "data", "bytes"):
            if entry.payload_hex:
                break
            match = re.search(key + r"\s*[=:]\s*(\[[^\]]+\]|(?:0x)?[0-9a-fA-F][0-9a-fA-F\s,:-]*)", line, re.I)
            if match:
                hex_value = normalize_hex(match.group(1))
                if hex_value:
                    entry.payload_hex = hex_value
                    break

        writes.append(entry)
    return writes


def parse_write_text(text: str) -> list[dict[str, str | None]]:
    return [asdict(item) for item in parse_write_lines(text.splitlines())]


def parse_write_file(path: str | Path) -> list[dict[str, str | None]]:
    return parse_write_text(Path(path).read_text(encoding="utf-8", errors="replace"))


def dumps_json(items: list[dict[str, str | None]]) -> str:
    return json.dumps(items, ensure_ascii=False, indent=2)
