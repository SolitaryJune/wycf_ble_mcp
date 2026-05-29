"""Thin BLE wrapper around bleak.

The module intentionally exposes raw GATT operations first. The actual TFProtocol
payload format should be promoted to high-level helpers only after a confirmed
`TFBLEWrite` log line is captured from the patched APK.
"""

from __future__ import annotations

import asyncio
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .known import (
    CONTROL_UUID_CANDIDATES,
    OTA_NOTIFY_UUID,
    OTA_SERVICE_UUID,
    OTA_WRITE_UUID,
    TOY_NAME_PREFIXES,
)


HEX_RE = re.compile(r"^[0-9a-fA-F]*$")
MACOS_HELPER_ENV = "BLE_MCP_IN_MACOS_HELPER"
MACOS_HELPER_APP_ENV = "BLE_MCP_PYTHON_APP"


@dataclass
class BleDeviceInfo:
    address: str
    name: str | None
    rssi: int | None
    metadata: dict[str, Any]


@dataclass
class BleCharacteristicInfo:
    service_uuid: str
    uuid: str
    description: str
    properties: list[str]
    is_control_candidate: bool
    is_ota: bool


def _import_bleak() -> Any:
    try:
        import bleak  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Missing dependency: bleak. Install with `python -m pip install -r ble_mcp/requirements.txt`."
        ) from exc
    return bleak


def _macos_python_app() -> Path | None:
    env_app = os.environ.get(MACOS_HELPER_APP_ENV)
    if env_app:
        app = Path(env_app).expanduser()
        if app.exists():
            return app

    bundled_app = Path(__file__).resolve().parent / "artifacts" / "BleMcpPython.app"
    if bundled_app.exists():
        return bundled_app

    base_prefix = Path(getattr(sys, "base_prefix", sys.prefix))
    app = base_prefix / "Resources" / "Python.app"
    if app.exists():
        return app
    for candidate in (
        Path("/opt/homebrew/opt/python@3.14/Frameworks/Python.framework/Versions/3.14/Resources/Python.app"),
        Path("/opt/homebrew/opt/python@3.13/Frameworks/Python.framework/Versions/3.13/Resources/Python.app"),
        Path("/opt/homebrew/opt/python@3.12/Frameworks/Python.framework/Versions/3.12/Resources/Python.app"),
    ):
        if candidate.exists():
            return candidate
    return None


def _should_use_macos_helper() -> bool:
    if os.environ.get(MACOS_HELPER_ENV) == "1":
        return False
    if platform.system() != "Darwin":
        return False
    return _macos_python_app() is not None


def _run_macos_helper(operation: str, payload: dict[str, Any], timeout: float) -> Any:
    app = _macos_python_app()
    if app is None:
        raise RuntimeError("Python.app not found for macOS BLE helper")

    helper = Path(__file__).with_name("macos_ble_helper.py")
    if not helper.exists():
        raise RuntimeError(f"macOS BLE helper missing: {helper}")

    with tempfile.TemporaryDirectory(prefix="ble_mcp_") as tmpdir:
        tmp = Path(tmpdir)
        request_path = tmp / "request.json"
        response_path = tmp / "response.json"
        request_path.write_text(
            json.dumps({"operation": operation, "payload": payload}, ensure_ascii=False),
            encoding="utf-8",
        )

        env = os.environ.copy()
        env[MACOS_HELPER_ENV] = "1"
        site_packages = Path(sys.prefix) / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
        existing_pythonpath = env.get("PYTHONPATH", "")
        paths = [str(Path(__file__).resolve().parent.parent), str(site_packages)]
        if existing_pythonpath:
            paths.append(existing_pythonpath)
        env["PYTHONPATH"] = os.pathsep.join(paths)

        subprocess.run(
            [
                "open",
                "-a",
                str(app),
                "--args",
                str(helper),
                str(request_path),
                str(response_path),
            ],
            check=True,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if response_path.exists() and response_path.stat().st_size > 0:
                response = json.loads(response_path.read_text(encoding="utf-8"))
                if response.get("ok"):
                    return response.get("result")
                raise RuntimeError(response.get("error") or "macOS BLE helper failed")
            time.sleep(0.1)
        raise TimeoutError(f"macOS BLE helper timed out during {operation}")


def normalize_hex(payload_hex: str) -> str:
    payload = re.sub(r"[^0-9a-fA-F]", "", payload_hex).lower()
    if len(payload) % 2 != 0:
        raise ValueError("hex payload length must be even")
    if not HEX_RE.match(payload):
        raise ValueError("payload must be hex")
    return payload


def is_probable_toy_name(name: str | None, prefixes: tuple[str, ...] = TOY_NAME_PREFIXES) -> bool:
    if not name:
        return False
    lower = name.lower()
    return any(lower.startswith(prefix.lower()) for prefix in prefixes)


async def scan(duration: float = 5.0, name_prefix: str | None = None, include_all: bool = False) -> list[dict[str, Any]]:
    if _should_use_macos_helper():
        return await asyncio.to_thread(
            _run_macos_helper,
            "scan",
            {"duration": duration, "name_prefix": name_prefix, "include_all": include_all},
            duration + 30.0,
        )

    bleak = _import_bleak()
    devices = await bleak.BleakScanner.discover(timeout=duration, return_adv=False)
    prefix = name_prefix.lower() if name_prefix else None
    results: list[dict[str, Any]] = []
    for device in devices:
        name = getattr(device, "name", None)
        if not include_all:
            if prefix:
                if not (name or "").lower().startswith(prefix):
                    continue
            elif not is_probable_toy_name(name):
                continue
        results.append(
            asdict(
                BleDeviceInfo(
                    address=getattr(device, "address", ""),
                    name=name,
                    rssi=getattr(device, "rssi", None),
                    metadata=getattr(device, "metadata", {}) or {},
                )
            )
        )
    return results


async def discover(address: str, timeout: float = 20.0) -> list[dict[str, Any]]:
    if _should_use_macos_helper():
        return await asyncio.to_thread(
            _run_macos_helper,
            "discover",
            {"address": address, "timeout": timeout},
            timeout + 30.0,
        )

    bleak = _import_bleak()
    results: list[dict[str, Any]] = []
    async with bleak.BleakClient(address, timeout=timeout) as client:
        if hasattr(client, "get_services"):
            services = await client.get_services()
        else:
            services = client.services
        for service in services:
            service_uuid = str(service.uuid).lower()
            for characteristic in service.characteristics:
                uuid = str(characteristic.uuid).lower()
                results.append(
                    asdict(
                        BleCharacteristicInfo(
                            service_uuid=service_uuid,
                            uuid=uuid,
                            description=getattr(characteristic, "description", "") or "",
                            properties=list(getattr(characteristic, "properties", []) or []),
                            is_control_candidate=uuid in CONTROL_UUID_CANDIDATES
                            or service_uuid in CONTROL_UUID_CANDIDATES,
                            is_ota=service_uuid == OTA_SERVICE_UUID
                            or uuid in {OTA_WRITE_UUID, OTA_NOTIFY_UUID},
                        )
                    )
                )
    return results


async def write_raw(
    address: str,
    characteristic_uuid: str,
    payload_hex: str,
    *,
    response: bool = False,
    timeout: float = 20.0,
    allow_ota: bool = False,
) -> dict[str, Any]:
    if _should_use_macos_helper():
        return await asyncio.to_thread(
            _run_macos_helper,
            "write_raw",
            {
                "address": address,
                "characteristic_uuid": characteristic_uuid,
                "payload_hex": payload_hex,
                "response": response,
                "timeout": timeout,
                "allow_ota": allow_ota,
            },
            timeout + 30.0,
        )

    characteristic_uuid = characteristic_uuid.lower()
    if not allow_ota and characteristic_uuid == OTA_WRITE_UUID:
        raise ValueError("refusing to write OTA characteristic without allow_ota=True")
    payload = bytes.fromhex(normalize_hex(payload_hex))

    bleak = _import_bleak()
    async with bleak.BleakClient(address, timeout=timeout) as client:
        await client.write_gatt_char(characteristic_uuid, payload, response=response)
        return {
            "address": address,
            "characteristic_uuid": characteristic_uuid,
            "payload_hex": payload.hex(),
            "length": len(payload),
            "response": response,
        }


async def notify_for(
    address: str,
    characteristic_uuid: str,
    *,
    seconds: float = 10.0,
    timeout: float = 20.0,
) -> list[dict[str, str]]:
    if _should_use_macos_helper():
        return await asyncio.to_thread(
            _run_macos_helper,
            "notify_for",
            {"address": address, "characteristic_uuid": characteristic_uuid, "seconds": seconds, "timeout": timeout},
            timeout + seconds + 30.0,
        )

    characteristic_uuid = characteristic_uuid.lower()
    bleak = _import_bleak()
    events: list[dict[str, str]] = []

    def callback(sender: Any, data: bytearray) -> None:
        events.append({"sender": str(sender), "data_hex": bytes(data).hex()})

    async with bleak.BleakClient(address, timeout=timeout) as client:
        await client.start_notify(characteristic_uuid, callback)
        await asyncio.sleep(seconds)
        await client.stop_notify(characteristic_uuid)
    return events


def run(coro: Any) -> Any:
    return asyncio.run(coro)
