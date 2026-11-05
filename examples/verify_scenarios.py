"""Verify all scenarios through the official MCP client and actual stdio transport."""
import asyncio
import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check(scenario, expected_errors):
    params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_recovery_lab.server", "--scenario", scenario])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            observed = []
            for _ in expected_errors:
                result = await session.call_tool("lookup_order", {"order_id": "ORD-100"})
                observed.append(result)
            assert [result.is_error for result in observed] == expected_errors
            if scenario == "stale":
                assert [json.loads(result.content[0].text)["revision"] for result in observed] == [1, 2]
            if scenario == "malformed":
                try:
                    json.loads(observed[0].content[0].text)
                except json.JSONDecodeError:
                    pass
                else:
                    raise AssertionError("Expected invalid JSON in the tool's text content")
    print(f"{scenario}: {len(expected_errors)} calls verified")


async def main():
    for scenario, errors in (
        ("healthy", [False]),
        ("transient", [True, False]),
        ("rate-limit", [True, True, False]),
        ("unavailable", [True, True]),
        ("stale", [False, False]),
        ("permission-denied", [True, True]),
        ("malformed", [False]),
    ):
        await check(scenario, errors)


if __name__ == "__main__":
    asyncio.run(main())
