"""Exercise the transient scenario with the official MCP Python client."""
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_recovery_lab.server", "--scenario", "transient"],
    )
    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Tools:", ", ".join(tool.name for tool in (await session.list_tools()).tools))
            for attempt in (1, 2):
                result = await session.call_tool("lookup_order", {"order_id": "ORD-100"})
                assert result.is_error == (attempt == 1), f"Unexpected result on attempt {attempt}"
                print(f"Attempt {attempt}: {'error' if result.is_error else 'success'} - {result.content[0].text}")
                if not result.is_error:
                    break


if __name__ == "__main__":
    asyncio.run(main())
