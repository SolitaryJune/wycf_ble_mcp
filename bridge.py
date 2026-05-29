"""Helpers for Unity-side TFGTC bridge command strings.

These are not BLE frames. They are the higher-level Flutter bridge URLs that
Unity sends as `tfgtc://...`; Dart then translates them into BLE TFProtocol
frames.
"""

from __future__ import annotations

from urllib.parse import quote

from .known import TFGTC_COMMANDS


def bool_arg(value: bool) -> str:
    return "True" if value else "False"


def join_commands(commands: list[str] | tuple[str, ...]) -> str:
    return "|".join(commands)


def create_session() -> str:
    return TFGTC_COMMANDS["create_session"]


def stop(session_id: str, with_response: bool = True) -> str:
    return TFGTC_COMMANDS["stop"].format(session_id=session_id, with_response=bool_arg(with_response))


def pause(session_id: str) -> str:
    return TFGTC_COMMANDS["pause"].format(session_id=session_id)


def resume(session_id: str) -> str:
    return TFGTC_COMMANDS["resume"].format(session_id=session_id)


def execute(session_id: str, commands: list[str] | tuple[str, ...], with_response: bool = True) -> str:
    return TFGTC_COMMANDS["execute"].format(
        session_id=session_id,
        with_response=bool_arg(with_response),
        commands=quote(join_commands(commands), safe="|,:={}\"[]"),
    )


def get_state(session_id: str) -> str:
    return TFGTC_COMMANDS["get_state"].format(session_id=session_id)


def select_product_to_play_with(
    session_id: str,
    product_id: str,
    limited_product_ids: list[str] | tuple[str, ...] | None = None,
) -> str:
    return TFGTC_COMMANDS["select_product_to_play_with"].format(
        session_id=session_id,
        product_id=product_id,
        limited_product_ids=join_commands(tuple(limited_product_ids or ())),
    )


def build(name: str, **kwargs: object) -> str:
    """Build any known TFGTC bridge command by name."""
    key = name.strip().lower()
    if key == "create_session":
        return create_session()
    if key == "stop":
        return stop(str(kwargs["session_id"]), bool(kwargs.get("with_response", True)))
    if key == "pause":
        return pause(str(kwargs["session_id"]))
    if key == "resume":
        return resume(str(kwargs["session_id"]))
    if key == "execute":
        commands = kwargs.get("commands", [])
        if isinstance(commands, str):
            commands = [commands]
        return execute(str(kwargs["session_id"]), list(commands), bool(kwargs.get("with_response", True)))
    if key == "get_state":
        return get_state(str(kwargs["session_id"]))
    if key == "select_product_to_play_with":
        limited = kwargs.get("limited_product_ids", [])
        if isinstance(limited, str):
            limited = [limited]
        return select_product_to_play_with(str(kwargs["session_id"]), str(kwargs["product_id"]), list(limited))
    if key in TFGTC_COMMANDS:
        return TFGTC_COMMANDS[key].format(**kwargs)
    raise KeyError(f"unknown TFGTC command: {name}")
