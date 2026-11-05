"""Run a scripted Pydantic AI agent against the local MCP server, without an LLM."""
import asyncio
import sys

from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset
from pydantic_ai.messages import ModelResponse, RetryPromptPart, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import FunctionModel


def scripted_model(messages, _info):
    """Simulate a model: retry once after the known temporary tool error."""
    results = [part for message in messages for part in message.parts if isinstance(part, (ToolReturnPart, RetryPromptPart))]
    if not results:
        return ModelResponse(parts=[ToolCallPart("lookup_order", {"order_id": "ORD-100"})])
    if len(results) == 1 and results[-1].content == "Temporary upstream failure. Retry may succeed.":
        return ModelResponse(parts=[ToolCallPart("lookup_order", {"order_id": "ORD-100"})])
    latest = results[-1]
    if (len(results) == 2 and isinstance(latest, ToolReturnPart)
            and latest.outcome == "success" and isinstance(latest.content, dict)
            and latest.content.get("order_id") == "ORD-100"
            and latest.content.get("status") == "shipped"):
        return ModelResponse(parts=[TextPart("Order ORD-100 is shipped (simulated data).")])
    return ModelResponse(parts=[TextPart("The order status could not be verified.")])


async def run_scenario(scenario, expected_calls, expected_output):
    transport = StdioTransport(sys.executable, args=["-m", "mcp_recovery_lab.server", "--scenario", scenario])
    toolset = MCPToolset(Client(transport), max_retries=1)
    agent = Agent(FunctionModel(scripted_model), toolsets=[toolset])
    result = await agent.run("Look up order ORD-100; retry a temporary failure once.")
    assert result.output == expected_output
    calls = [part for message in result.all_messages() for part in message.parts if isinstance(part, ToolCallPart)]
    assert len(calls) == expected_calls, f"Expected {expected_calls} MCP tool calls, got {len(calls)}"
    noun = "call" if len(calls) == 1 else "calls"
    print(f"Pydantic AI / {scenario}: {len(calls)} tool {noun}; {result.output}")


async def main():
    await run_scenario("transient", 2, "Order ORD-100 is shipped (simulated data).")
    await run_scenario("permission-denied", 1, "The order status could not be verified.")
    await run_scenario("malformed", 1, "The order status could not be verified.")


if __name__ == "__main__":
    asyncio.run(main())
