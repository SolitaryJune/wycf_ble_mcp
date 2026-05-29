from __future__ import annotations

import argparse
import json
from typing import Any

from . import bridge
from .audio_level import read_system_volume
from .ble import discover, notify_for, run, scan, write_raw, write_raw_sequence
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
from .log_parser import dumps_json, parse_write_file, parse_write_text
from .protocol import (
    CONTROL_WRITE_UUID,
    CONTROL_WRITE_WITH_RESPONSE_UUID,
    COMMAND_HEATING_SWITCH,
    COMMAND_TELESCOPIC_LEVEL,
    decode_control_notification,
    describe_audio_level_frame,
    describe_heating_frame,
    describe_level_frame,
    describe_random_telescopic_frame,
    describe_random_telescopic_sequence,
    describe_telescopic_frame,
    map_audio_level,
)


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def cmd_known(_: argparse.Namespace) -> None:
    print_json(
        {
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
        }
    )


def cmd_system_volume(_: argparse.Namespace) -> None:
    print_json(read_system_volume())


def cmd_scan(args: argparse.Namespace) -> None:
    print_json(run(scan(args.duration, args.name_prefix, args.all)))


def cmd_discover(args: argparse.Namespace) -> None:
    print_json(run(discover(args.address, args.timeout)))


def cmd_write(args: argparse.Namespace) -> None:
    print_json(
        run(
            write_raw(
                args.address,
                args.characteristic,
                args.hex,
                response=args.response,
                timeout=args.timeout,
                allow_ota=args.allow_ota,
            )
        )
    )


def cmd_notify(args: argparse.Namespace) -> None:
    print_json(run(notify_for(args.address, args.characteristic, seconds=args.seconds, timeout=args.timeout)))


def cmd_parse_log(args: argparse.Namespace) -> None:
    if args.file:
        print(dumps_json(parse_write_file(args.file)))
    else:
        print(dumps_json(parse_write_text(args.text or "")))


def cmd_bridge(args: argparse.Namespace) -> None:
    kwargs: dict[str, Any] = {}
    if args.session_id:
        kwargs["session_id"] = args.session_id
    if args.product_id:
        kwargs["product_id"] = args.product_id
    if args.commands:
        kwargs["commands"] = args.commands
    if args.limited_product_ids:
        kwargs["limited_product_ids"] = args.limited_product_ids
    kwargs["with_response"] = args.with_response
    if args.seconds is not None:
        kwargs["seconds"] = args.seconds
    if args.complete is not None:
        kwargs["complete"] = args.complete
    print(bridge.build(args.name, **kwargs))


def cmd_build_level(args: argparse.Namespace) -> None:
    print_json(describe_level_frame(args.command_id, args.level, args.seq))


def cmd_build_telescopic(args: argparse.Namespace) -> None:
    print_json(describe_telescopic_frame(args.level, args.seq))


def cmd_build_random(args: argparse.Namespace) -> None:
    print_json(describe_random_telescopic_frame(args.min_level, args.max_level, args.seq))


def cmd_build_random_sequence(args: argparse.Namespace) -> None:
    print_json(
        describe_random_telescopic_sequence(
            args.count,
            args.min_level,
            args.max_level,
            args.interval_ms,
            args.seq,
        )
    )


def cmd_build_heating(args: argparse.Namespace) -> None:
    print_json(describe_heating_frame(args.on, args.seq))


def cmd_audio_map(args: argparse.Namespace) -> None:
    print_json(map_audio_level(args.volume, args.threshold, args.gain, args.multiplier, args.max_level))


def cmd_build_audio_level(args: argparse.Namespace) -> None:
    print_json(
        describe_audio_level_frame(
            args.volume,
            args.threshold,
            args.gain,
            args.multiplier,
            args.max_level,
            args.seq,
        )
    )


def cmd_decode_notify(args: argparse.Namespace) -> None:
    print_json(decode_control_notification(args.hex))


def cmd_telescopic(args: argparse.Namespace) -> None:
    frame = describe_level_frame(COMMAND_TELESCOPIC_LEVEL, args.level, args.seq)
    print_json(
        run(
            write_raw(
                args.address,
                CONTROL_WRITE_UUID,
                frame["payload_hex"],
                response=args.response,
                timeout=args.timeout,
                allow_ota=False,
            )
        )
    )


def cmd_random(args: argparse.Namespace) -> None:
    generated = describe_random_telescopic_frame(args.min_level, args.max_level, args.seq)
    frame = generated["frame"]
    result = run(
        write_raw(
            args.address,
            CONTROL_WRITE_UUID,
            frame["payload_hex"],
            response=False,
            timeout=args.timeout,
            allow_ota=False,
        )
    )
    result["random"] = generated
    print_json(result)


def cmd_random_loop(args: argparse.Namespace) -> None:
    sequence = describe_random_telescopic_sequence(
        args.count,
        args.min_level,
        args.max_level,
        args.interval_ms,
        args.seq,
    )
    frames = list(sequence["frames"])
    stop_frame = None
    if args.stop_after:
        last_seq = int(frames[-1]["seq"]) if frames else 0
        stop_frame = describe_telescopic_frame(0, (last_seq + 1) & 0xFF)
        frames.append(stop_frame)

    result = run(
        write_raw_sequence(
            args.address,
            CONTROL_WRITE_UUID,
            [frame["payload_hex"] for frame in frames],
            response=False,
            timeout=args.timeout,
            allow_ota=False,
            interval_ms=sequence["interval_ms"],
        )
    )
    result["sequence"] = sequence
    result["stop_after"] = bool(args.stop_after)
    if stop_frame is not None:
        result["stop_frame"] = stop_frame
    print_json(result)


def cmd_heating(args: argparse.Namespace) -> None:
    level = 1 if args.on else 0
    frame = describe_level_frame(COMMAND_HEATING_SWITCH, level, args.seq)
    print_json(
        run(
            write_raw(
                args.address,
                CONTROL_WRITE_WITH_RESPONSE_UUID,
                frame["payload_hex"],
                response=True,
                timeout=args.timeout,
                allow_ota=False,
            )
        )
    )


def cmd_stop(args: argparse.Namespace) -> None:
    frame = describe_level_frame(COMMAND_TELESCOPIC_LEVEL, 0, args.seq)
    print_json(
        run(
            write_raw(
                args.address,
                CONTROL_WRITE_UUID,
                frame["payload_hex"],
                response=False,
                timeout=args.timeout,
                allow_ota=False,
            )
        )
    )


def cmd_set_level(args: argparse.Namespace) -> None:
    frame = describe_level_frame(args.command_id, args.level, args.seq)
    print_json(
        run(
            write_raw(
                args.address,
                CONTROL_WRITE_UUID,
                frame["payload_hex"],
                response=args.response,
                timeout=args.timeout,
                allow_ota=False,
            )
        )
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TryFun CTF BLE/MCP local controller")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("known", help="print static facts extracted from APK/DLL")
    p.set_defaults(func=cmd_known)

    p = sub.add_parser("system-volume", help="read current OS audio volume setting")
    p.set_defaults(func=cmd_system_volume)

    p = sub.add_parser("scan", help="scan BLE devices")
    p.add_argument("--duration", type=float, default=5.0)
    p.add_argument("--name-prefix", default=None)
    p.add_argument("--all", action="store_true", help="include non-toy-looking devices")
    p.set_defaults(func=cmd_scan)

    p = sub.add_parser("discover", help="connect and list GATT services/characteristics")
    p.add_argument("address")
    p.add_argument("--timeout", type=float, default=20.0)
    p.set_defaults(func=cmd_discover)

    p = sub.add_parser("write", help="write raw hex to a characteristic")
    p.add_argument("address")
    p.add_argument("characteristic")
    p.add_argument("hex")
    p.add_argument("--response", action="store_true")
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--allow-ota", action="store_true", help="allow writes to known OTA characteristic")
    p.set_defaults(func=cmd_write)

    p = sub.add_parser("notify", help="subscribe to notifications for a short interval")
    p.add_argument("address")
    p.add_argument("characteristic")
    p.add_argument("--seconds", type=float, default=10.0)
    p.add_argument("--timeout", type=float, default=20.0)
    p.set_defaults(func=cmd_notify)

    p = sub.add_parser("parse-log", help="parse patched APK logcat TFBLEWrite lines")
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--file")
    src.add_argument("--text")
    p.set_defaults(func=cmd_parse_log)

    p = sub.add_parser("build-level", help="build a confirmed TryFun level-control frame")
    p.add_argument("command_id", type=lambda x: int(x, 0), help="e.g. 0x0c for telescopic")
    p.add_argument("level", type=int, help="0..255; official UI uses 0..100")
    p.add_argument("--seq", type=lambda x: int(x, 0), default=None, help="0..255; defaults to auto")
    p.set_defaults(func=cmd_build_level)

    p = sub.add_parser("build-telescopic", help="build a telescopic frame")
    p.add_argument("level", type=int)
    p.add_argument("--seq", type=lambda x: int(x, 0), default=None)
    p.set_defaults(func=cmd_build_telescopic)

    p = sub.add_parser("build-random", help="build one random telescopic frame")
    p.add_argument("--min-level", type=int, default=0)
    p.add_argument("--max-level", type=int, default=100)
    p.add_argument("--seq", type=lambda x: int(x, 0), default=None)
    p.set_defaults(func=cmd_build_random)

    p = sub.add_parser("build-random-sequence", help="build a finite random telescopic frame sequence")
    p.add_argument("--count", type=int, default=10)
    p.add_argument("--min-level", type=int, default=0)
    p.add_argument("--max-level", type=int, default=100)
    p.add_argument("--interval-ms", type=int, default=500)
    p.add_argument("--seq", type=lambda x: int(x, 0), default=None)
    p.set_defaults(func=cmd_build_random_sequence)

    p = sub.add_parser("build-heating", help="build a heating on/off frame")
    state = p.add_mutually_exclusive_group(required=True)
    state.add_argument("--on", action="store_true")
    state.add_argument("--off", action="store_true")
    p.add_argument("--seq", type=lambda x: int(x, 0), default=None)
    p.set_defaults(func=cmd_build_heating)

    p = sub.add_parser("audio-map", help="map volume percent to telescopic level")
    p.add_argument("volume", type=float, help="0..100 volume/amplitude")
    p.add_argument("--threshold", type=float, default=1.0)
    p.add_argument("--gain", type=float, default=8.0)
    p.add_argument("--multiplier", type=float, default=1.0)
    p.add_argument("--max-level", type=int, default=100)
    p.set_defaults(func=cmd_audio_map)

    p = sub.add_parser("build-audio-level", help="map volume percent and build a telescopic frame")
    p.add_argument("volume", type=float)
    p.add_argument("--threshold", type=float, default=1.0)
    p.add_argument("--gain", type=float, default=8.0)
    p.add_argument("--multiplier", type=float, default=1.0)
    p.add_argument("--max-level", type=int, default=100)
    p.add_argument("--seq", type=lambda x: int(x, 0), default=None)
    p.set_defaults(func=cmd_build_audio_level)

    p = sub.add_parser("decode-notify", help="decode an ffb8 notification payload")
    p.add_argument("hex")
    p.set_defaults(func=cmd_decode_notify)

    p = sub.add_parser("telescopic", help="set Black Hole Max telescopic level through confirmed BLE frame")
    p.add_argument("address")
    p.add_argument("level", type=int, help="0..100 from the official slider")
    p.add_argument("--seq", type=lambda x: int(x, 0), default=None)
    p.add_argument("--response", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--timeout", type=float, default=20.0)
    p.set_defaults(func=cmd_telescopic)

    p = sub.add_parser("random", help="pick and send one random telescopic level")
    p.add_argument("address")
    p.add_argument("--min-level", type=int, default=0)
    p.add_argument("--max-level", type=int, default=100)
    p.add_argument("--seq", type=lambda x: int(x, 0), default=None)
    p.add_argument("--timeout", type=float, default=20.0)
    p.set_defaults(func=cmd_random)

    p = sub.add_parser("random-loop", help="run a finite random telescopic auto-mode sequence")
    p.add_argument("address")
    p.add_argument("--count", type=int, default=10)
    p.add_argument("--min-level", type=int, default=0)
    p.add_argument("--max-level", type=int, default=100)
    p.add_argument("--interval-ms", type=int, default=500)
    p.add_argument("--stop-after", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--seq", type=lambda x: int(x, 0), default=None)
    p.add_argument("--timeout", type=float, default=20.0)
    p.set_defaults(func=cmd_random_loop)

    p = sub.add_parser("stop", help="set Black Hole Max telescopic level to 0")
    p.add_argument("address")
    p.add_argument("--seq", type=lambda x: int(x, 0), default=None)
    p.add_argument("--timeout", type=float, default=20.0)
    p.set_defaults(func=cmd_stop)

    p = sub.add_parser("heating", help="toggle observed Black Hole Max heating switch frame")
    p.add_argument("address")
    state = p.add_mutually_exclusive_group(required=True)
    state.add_argument("--on", action="store_true")
    state.add_argument("--off", action="store_true")
    p.add_argument("--seq", type=lambda x: int(x, 0), default=None)
    p.add_argument("--timeout", type=float, default=20.0)
    p.set_defaults(func=cmd_heating)

    p = sub.add_parser("set-level", help="send a confirmed generic level-control frame by command id")
    p.add_argument("address")
    p.add_argument("command_id", type=lambda x: int(x, 0), help="e.g. 0x0c for telescopic")
    p.add_argument("level", type=int)
    p.add_argument("--seq", type=lambda x: int(x, 0), default=None)
    p.add_argument("--response", action=argparse.BooleanOptionalAction, default=False)
    p.add_argument("--timeout", type=float, default=20.0)
    p.set_defaults(func=cmd_set_level)

    p = sub.add_parser("bridge", help="build Unity-side tfgtc:// bridge command strings")
    p.add_argument("name")
    p.add_argument("--session-id")
    p.add_argument("--product-id")
    p.add_argument("--commands", nargs="*")
    p.add_argument("--limited-product-ids", nargs="*")
    p.add_argument("--with-response", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--seconds", type=int)
    p.add_argument("--complete", action=argparse.BooleanOptionalAction)
    p.set_defaults(func=cmd_bridge)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
