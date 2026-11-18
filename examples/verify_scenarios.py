"""Verify all scenarios through the official MCP client and actual stdio transport."""
import argparse
import asyncio
import json
import sys

SCENARIOS = {
    "healthy": [("shipped", None)],
    "transient": ["temporary", ("shipped", None)],
    "rate-limit": ["rate", "rate", ("shipped", None)],
    "unavailable": ["unavailable", "unavailable"],
    "stale": [("processing", 1), ("shipped", 2)],
    "permission-denied": ["denied", "denied"],
    "malformed": ["malformed"],
}


async def check(scenario, expected_steps):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_recovery_lab.server", "--scenario", scenario])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for index, expected in enumerate(expected_steps, start=1):
                result = await session.call_tool("lookup_order", {"order_id": "ORD-100"})
                try:
                    verify_result(result, expected)
                except AssertionError as error:
                    raise AssertionError(f"{scenario}, call {index}: {error}") from error
    print(f"{scenario}: {len(expected_steps)} calls verified")


def verify_result(result, expected):
    errors = {
        "temporary": "temporary",
        "rate": "rate limit",
        "unavailable": "unavailable",
        "denied": "permission denied",
    }
    if len(result.content) != 1 or result.content[0].type != "text":
        raise AssertionError("Expected a single text result")
    text = result.content[0].text
    if isinstance(expected, str) and expected in errors:
        if not result.is_error or errors[expected] not in text.lower():
            raise AssertionError(f"Expected the {expected} tool error")
        return
    if result.is_error:
        raise AssertionError("Expected a successful tool response")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        if expected == "malformed":
            return
        raise AssertionError("Expected valid JSON in the tool text") from None
    if expected == "malformed":
        raise AssertionError("Expected invalid JSON in the tool text")
    status, revision = expected
    if not isinstance(payload, dict) or (
        payload.get("order_id"), payload.get("status")
    ) != ("ORD-100", status):
        raise AssertionError("Unexpected order ID or status")
    if revision is None:
        if "revision" in payload:
            raise AssertionError("Expected a response without a revision")
    elif type(payload.get("revision")) is not int or payload["revision"] != revision:
        raise AssertionError("Expected the exact integer revision")


async def main(scenarios):
    for scenario in scenarios:
        try:
            await asyncio.wait_for(check(scenario, SCENARIOS[scenario]), timeout=15)
        except asyncio.TimeoutError:
            raise SystemExit(f"{scenario}: MCP verification timed out after 15 seconds") from None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, help="Run just this scenario")
    args = parser.parse_args()
    asyncio.run(main([args.scenario] if args.scenario else SCENARIOS))
