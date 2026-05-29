from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> None:
    package_dir = Path(__file__).resolve().parents[1]
    parent_dir = package_dir.parent
    python = sys.executable
    params = StdioServerParameters(
        command=python,
        args=["-m", "ble_mcp.server"],
        cwd=str(parent_dir),
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [tool.name for tool in tools.tools]
            required = {
                "known_facts",
                "controller_profile",
                "build_heating_frame",
                "map_audio_to_level",
                "build_audio_level_frame",
                "decode_control_notify",
                "set_heating",
            }
            missing = sorted(required.difference(names))
            if missing:
                raise SystemExit(f"missing tools: {', '.join(missing)}")

            heat = await session.call_tool("build_heating_frame", {"on": True, "seq": 1})
            mapped = await session.call_tool(
                "map_audio_to_level",
                {
                    "volume_percent": 3,
                    "threshold_percent": 1,
                    "gain": 8,
                    "multiplier": 100,
                    "max_level": 100,
                },
            )
            decoded = await session.call_tool("decode_control_notify", {"payload_hex": "010700030501fa"})

            print(
                json.dumps(
                    {
                        "tool_count": len(names),
                        "required_ok": True,
                        "build_heating_frame": heat.content[0].text,
                        "map_audio_to_level": mapped.content[0].text,
                        "decode_control_notify": decoded.content[0].text,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )


if __name__ == "__main__":
    asyncio.run(main())
