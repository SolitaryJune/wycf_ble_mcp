"""LaunchServices BLE helper for macOS.

Running CoreBluetooth from a shell-launched Homebrew Python can be killed by
TCC before permissions are requested. This helper is launched through
Python.app so macOS reads its Info.plist Bluetooth usage string.
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from pathlib import Path
from typing import Any


def _load_request(path: str) -> tuple[str, dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return str(data["operation"]), dict(data.get("payload") or {})


async def _dispatch(operation: str, payload: dict[str, Any]) -> Any:
    from ble_mcp.ble import discover, notify_for, scan, write_raw

    if operation == "scan":
        return await scan(
            duration=float(payload.get("duration", 5.0)),
            name_prefix=payload.get("name_prefix"),
            include_all=bool(payload.get("include_all", False)),
        )
    if operation == "discover":
        return await discover(str(payload["address"]), timeout=float(payload.get("timeout", 20.0)))
    if operation == "write_raw":
        return await write_raw(
            address=str(payload["address"]),
            characteristic_uuid=str(payload["characteristic_uuid"]),
            payload_hex=str(payload["payload_hex"]),
            response=bool(payload.get("response", False)),
            timeout=float(payload.get("timeout", 20.0)),
            allow_ota=bool(payload.get("allow_ota", False)),
        )
    if operation == "notify_for":
        return await notify_for(
            address=str(payload["address"]),
            characteristic_uuid=str(payload["characteristic_uuid"]),
            seconds=float(payload.get("seconds", 10.0)),
            timeout=float(payload.get("timeout", 20.0)),
        )
    raise KeyError(f"unknown operation: {operation}")


def main() -> None:
    request_path, response_path = sys.argv[1], sys.argv[2]
    try:
        operation, payload = _load_request(request_path)
        result = asyncio.run(_dispatch(operation, payload))
        response = {"ok": True, "result": result}
    except Exception:
        response = {"ok": False, "error": traceback.format_exc()}
    Path(response_path).write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
