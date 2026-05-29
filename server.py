from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import bridge
from .audio_level import read_system_volume
from .ble import discover, notify_for, scan, write_raw, write_raw_sequence
from .known import (
    CONFIRMED_CONTROL_COMMANDS,
    CONFIRMED_CONTROL_UUIDS,
    CONTROL_UUID_CANDIDATES,
    OTA_NOTIFY_UUID,
    OTA_SERVICE_UUID,
    OTA_WRITE_UUID,
    PRODUCT_IDS,
    TFGTC_COMMANDS,
    TFGTC_STATE_FIELDS,
)
from .log_parser import parse_write_text
from .protocol import (
    CONTROL_WRITE_UUID,
    CONTROL_WRITE_WITH_RESPONSE_UUID,
    COMMAND_HEATING_SWITCH,
    COMMAND_TELESCOPIC_LEVEL,
    CONTROL_NOTIFY_UUID,
    CONTROL_SERVICE_UUID,
    decode_control_notification,
    describe_audio_level_frame,
    describe_heating_frame,
    describe_level_frame,
    describe_named_level_frame,
    describe_random_telescopic_frame,
    describe_random_telescopic_sequence,
    describe_telescopic_frame,
    map_audio_level,
)


mcp = FastMCP(
    "tryfun-ble",
    instructions=(
        "Local BLE controller for the TryFun CTF target. Use scan/discover first, "
        "then write raw confirmed payloads. Do not write OTA UUIDs unless explicitly allowed."
    ),
)


@mcp.tool()
def known_facts() -> dict[str, Any]:
    """Return APK-derived product IDs, UUID candidates, OTA UUIDs, and bridge commands."""
    return {
        "products": PRODUCT_IDS,
        "ota": {
            "service": OTA_SERVICE_UUID,
            "write": OTA_WRITE_UUID,
            "notify": OTA_NOTIFY_UUID,
        },
        "control_uuid_candidates": CONTROL_UUID_CANDIDATES,
        "confirmed_control_uuids": CONFIRMED_CONTROL_UUIDS,
        "confirmed_control_commands": CONFIRMED_CONTROL_COMMANDS,
        "tfgtc_bridge_commands": TFGTC_COMMANDS,
        "tfgtc_state_fields": TFGTC_STATE_FIELDS,
        "status": "Black Hole Max telescopic and heating controls are available. Other functions still require dynamic write logs.",
    }


@mcp.tool()
def read_system_audio_volume() -> dict[str, Any]:
    """Read the OS volume setting of the current audio device."""
    return read_system_volume()


@mcp.tool()
def controller_profile() -> dict[str, Any]:
    """Return the local controller profile, confirmed UUIDs, and known local web UI path."""
    return {
        "device_name": "TF-BHMAX",
        "macos_corebluetooth_uuid": "32D7BA9B-008B-6312-B4D6-0A6FAA6B26D0",
        "android_ble_mac": "5C:65:E7:3A:9E:D6",
        "service_uuid": CONTROL_SERVICE_UUID,
        "telescopic_write_uuid": CONTROL_WRITE_UUID,
        "heating_write_uuid": CONTROL_WRITE_WITH_RESPONSE_UUID,
        "notify_uuid": CONTROL_NOTIFY_UUID,
        "web_controller": "/Users/a24/ble_mcp/web/index.html",
        "web_url": "http://localhost:8000/web/index.html",
    }


@mcp.tool()
async def scan_devices(duration: float = 5.0, name_prefix: str | None = None, include_all: bool = False) -> list[dict[str, Any]]:
    """Scan BLE devices. By default filters for TryFun-looking names."""
    return await scan(duration=duration, name_prefix=name_prefix, include_all=include_all)


@mcp.tool()
async def discover_gatt(address: str, timeout: float = 20.0) -> list[dict[str, Any]]:
    """Connect to a BLE device and list GATT characteristics."""
    return await discover(address=address, timeout=timeout)


@mcp.tool()
async def write_raw_hex(
    address: str,
    characteristic_uuid: str,
    payload_hex: str,
    response: bool = False,
    timeout: float = 20.0,
    allow_ota: bool = False,
) -> dict[str, Any]:
    """Write raw hex to a BLE characteristic. Requires confirmed payloads from logcat/sniffing."""
    return await write_raw(
        address=address,
        characteristic_uuid=characteristic_uuid,
        payload_hex=payload_hex,
        response=response,
        timeout=timeout,
        allow_ota=allow_ota,
    )


@mcp.tool()
async def collect_notifications(
    address: str,
    characteristic_uuid: str,
    seconds: float = 10.0,
    timeout: float = 20.0,
) -> list[dict[str, str]]:
    """Subscribe to a notify characteristic for a short interval and return received bytes."""
    return await notify_for(address=address, characteristic_uuid=characteristic_uuid, seconds=seconds, timeout=timeout)


@mcp.tool()
def parse_tfblewrite_log(log_text: str) -> list[dict[str, str | None]]:
    """Parse patched APK logcat lines containing TFBLEWrite/writeCharacteristic details."""
    return parse_write_text(log_text)


@mcp.tool()
def build_control_level_frame(command_id: int, level: int, seq: int | None = None) -> dict[str, Any]:
    """Build a confirmed level-control frame. Use command_id=0x0c for telescopic."""
    return describe_level_frame(command_id, level, seq)


@mcp.tool()
def build_named_control_frame(name: str, level: int, seq: int | None = None) -> dict[str, Any]:
    """Build a named frame. Names include telescopic/伸缩 and heating/heat/加热."""
    return describe_named_level_frame(name, level, seq)


@mcp.tool()
def build_telescopic_frame(level: int, seq: int | None = None) -> dict[str, Any]:
    """Build a telescopic level frame for UUID 0000ffb7."""
    return describe_telescopic_frame(level, seq)


@mcp.tool()
def build_random_telescopic_frame(
    min_level: int = 0,
    max_level: int = 100,
    seq: int | None = None,
) -> dict[str, Any]:
    """Pick a random telescopic level in range and build one ffb7 frame."""
    return describe_random_telescopic_frame(min_level, max_level, seq)


@mcp.tool()
def build_random_telescopic_sequence(
    count: int = 10,
    min_level: int = 0,
    max_level: int = 100,
    interval_ms: int = 500,
    seq: int | None = None,
) -> dict[str, Any]:
    """Build a finite random telescopic frame sequence for auto mode."""
    return describe_random_telescopic_sequence(count, min_level, max_level, interval_ms, seq)


@mcp.tool()
def build_heating_frame(on: bool, seq: int | None = None) -> dict[str, Any]:
    """Build a heating switch frame for UUID 0000ffb5."""
    return describe_heating_frame(on, seq)


@mcp.tool()
def decode_control_notify(payload_hex: str) -> dict[str, Any]:
    """Decode an ffb8 notification payload, including ack/status frames."""
    return decode_control_notification(payload_hex)


@mcp.tool()
def map_audio_to_level(
    volume_percent: float,
    threshold_percent: float = 1.0,
    gain: float = 8.0,
    multiplier: float = 1.0,
    max_level: int = 100,
) -> dict[str, Any]:
    """Map a 0..100 audio volume/amplitude value to a 0..100 telescopic level."""
    return map_audio_level(volume_percent, threshold_percent, gain, multiplier, max_level)


@mcp.tool()
def build_audio_level_frame(
    volume_percent: float,
    threshold_percent: float = 1.0,
    gain: float = 8.0,
    multiplier: float = 1.0,
    max_level: int = 100,
    seq: int | None = None,
) -> dict[str, Any]:
    """Map audio volume to telescopic level and build the corresponding ffb7 frame."""
    return describe_audio_level_frame(volume_percent, threshold_percent, gain, multiplier, max_level, seq)


@mcp.tool()
async def set_telescopic_level(
    address: str,
    level: int,
    seq: int | None = None,
    response: bool = False,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Set Black Hole Max telescopic level using confirmed UUID 0000ffb7 and command 0x0c."""
    frame = describe_level_frame(COMMAND_TELESCOPIC_LEVEL, level, seq)
    result = await write_raw(
        address=address,
        characteristic_uuid=CONTROL_WRITE_UUID,
        payload_hex=str(frame["payload_hex"]),
        response=response,
        timeout=timeout,
        allow_ota=False,
    )
    result["frame"] = frame
    return result


@mcp.tool()
async def set_random_telescopic_level(
    address: str,
    min_level: int = 0,
    max_level: int = 100,
    seq: int | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Pick one random telescopic level and send it immediately."""
    generated = describe_random_telescopic_frame(min_level, max_level, seq)
    frame = generated["frame"]
    result = await write_raw(
        address=address,
        characteristic_uuid=CONTROL_WRITE_UUID,
        payload_hex=str(frame["payload_hex"]),
        response=False,
        timeout=timeout,
        allow_ota=False,
    )
    result["random"] = generated
    return result


@mcp.tool()
async def run_random_telescopic_sequence(
    address: str,
    count: int = 10,
    min_level: int = 0,
    max_level: int = 100,
    interval_ms: int = 500,
    stop_after: bool = True,
    seq: int | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Run a finite random auto-mode sequence over one BLE connection."""
    sequence = describe_random_telescopic_sequence(count, min_level, max_level, interval_ms, seq)
    frames = list(sequence["frames"])
    stop_frame = None
    if stop_after:
        last_seq = int(frames[-1]["seq"]) if frames else 0
        stop_frame = describe_telescopic_frame(0, (last_seq + 1) & 0xFF)
        frames.append(stop_frame)

    result = await write_raw_sequence(
        address=address,
        characteristic_uuid=CONTROL_WRITE_UUID,
        payload_hexes=[str(frame["payload_hex"]) for frame in frames],
        response=False,
        timeout=timeout,
        allow_ota=False,
        interval_ms=int(sequence["interval_ms"]),
    )
    result["sequence"] = sequence
    result["stop_after"] = bool(stop_after)
    if stop_frame is not None:
        result["stop_frame"] = stop_frame
    return result


@mcp.tool()
async def stop_telescopic(address: str, seq: int | None = None, timeout: float = 20.0) -> dict[str, Any]:
    """Set telescopic level to 0."""
    return await set_telescopic_level(address=address, level=0, seq=seq, response=False, timeout=timeout)


@mcp.tool()
async def set_control_level(
    address: str,
    command_id: int,
    level: int,
    seq: int | None = None,
    response: bool = False,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Send a generic confirmed level-control frame by command id."""
    frame = describe_level_frame(command_id, level, seq)
    result = await write_raw(
        address=address,
        characteristic_uuid=CONTROL_WRITE_UUID,
        payload_hex=str(frame["payload_hex"]),
        response=response,
        timeout=timeout,
        allow_ota=False,
    )
    result["frame"] = frame
    return result


@mcp.tool()
async def set_heating(
    address: str,
    on: bool,
    seq: int | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Toggle observed Black Hole Max heating switch using UUID 0000ffb5 and command 0x05."""
    frame = describe_level_frame(COMMAND_HEATING_SWITCH, 1 if on else 0, seq)
    result = await write_raw(
        address=address,
        characteristic_uuid=CONTROL_WRITE_WITH_RESPONSE_UUID,
        payload_hex=str(frame["payload_hex"]),
        response=True,
        timeout=timeout,
        allow_ota=False,
    )
    result["frame"] = frame
    return result


@mcp.tool()
async def emergency_stop(
    address: str,
    stop_heating: bool = False,
    seq: int | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Stop telescopic motion immediately, optionally also turning heating off."""
    result: dict[str, Any] = {"telescopic": await stop_telescopic(address=address, seq=seq, timeout=timeout)}
    if stop_heating:
        result["heating"] = await set_heating(address=address, on=False, seq=seq, timeout=timeout)
    return result


@mcp.tool()
async def set_telescopic_from_audio_level(
    address: str,
    volume_percent: float,
    threshold_percent: float = 1.0,
    gain: float = 8.0,
    multiplier: float = 1.0,
    max_level: int = 100,
    seq: int | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Map a supplied audio volume/amplitude to telescopic level and send it."""
    mapped = describe_audio_level_frame(volume_percent, threshold_percent, gain, multiplier, max_level, seq)
    result = await write_raw(
        address=address,
        characteristic_uuid=CONTROL_WRITE_UUID,
        payload_hex=str(mapped["frame"]["payload_hex"]),
        response=False,
        timeout=timeout,
        allow_ota=False,
    )
    result.update(mapped)
    return result


@mcp.tool()
async def set_telescopic_from_system_volume(
    address: str,
    source: str = "output_volume",
    threshold_percent: float = 1.0,
    gain: float = 8.0,
    multiplier: float = 1.0,
    max_level: int = 100,
    seq: int | None = None,
    timeout: float = 20.0,
) -> dict[str, Any]:
    """Read the OS volume setting, map it to telescopic level, and send it."""
    volume = read_system_volume()
    if source not in volume:
        raise KeyError(f"volume source not found: {source}")
    result = await set_telescopic_from_audio_level(
        address=address,
        volume_percent=float(volume[source]),
        threshold_percent=threshold_percent,
        gain=gain,
        multiplier=multiplier,
        max_level=max_level,
        seq=seq,
        timeout=timeout,
    )
    result["system_volume"] = volume
    result["source"] = source
    return result


@mcp.tool()
def build_tfgtc_bridge_command(
    name: str,
    session_id: str | None = None,
    product_id: str | None = None,
    commands: list[str] | None = None,
    limited_product_ids: list[str] | None = None,
    with_response: bool = True,
    seconds: int | None = None,
    complete: bool | None = None,
) -> str:
    """Build Unity-side tfgtc:// bridge command strings recovered from TFGTC.dll."""
    kwargs: dict[str, Any] = {"with_response": with_response}
    if session_id is not None:
        kwargs["session_id"] = session_id
    if product_id is not None:
        kwargs["product_id"] = product_id
    if commands is not None:
        kwargs["commands"] = commands
    if limited_product_ids is not None:
        kwargs["limited_product_ids"] = limited_product_ids
    if seconds is not None:
        kwargs["seconds"] = seconds
    if complete is not None:
        kwargs["complete"] = complete
    return bridge.build(name, **kwargs)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
