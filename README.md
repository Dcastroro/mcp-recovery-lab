# MCP Recovery Lab

**A tiny local MCP server that fails on purpose, so you can test how your agent recovers.**

An agent's happy path is easy to demo. What happens when a tool returns an error? Does it retry a temporary failure, stop when a service is unavailable, and avoid inventing an answer?

MCP Recovery Lab provides a simulated, read-only order lookup over MCP stdio. It makes no network requests and uses no credentials or model provider. Each process starts with fresh state.

## Try it

Requires Python 3.10+ and Git. Clone the repository and install it locally:

```bash
git clone https://github.com/Dcastroro/mcp-recovery-lab.git
cd mcp-recovery-lab
python -m pip install .
mcp-recovery-lab --scenario transient
```

The last command runs a **stdio server**, so it waits for an MCP client rather than displaying a UI. Add it to an MCP client that supports local stdio servers, using its own configuration format. For clients that accept the common `mcpServers` format:

```json
{
  "mcpServers": {
    "recovery-lab": {
      "command": "mcp-recovery-lab",
      "args": ["--scenario", "transient"]
    }
  }
}
```

Ask your agent: **“What's the status of order ORD-100? If the tool temporarily fails, try it once more.”** The first valid lookup returns a tool error and the next returns `shipped`. Start a new server process to reset the scenario. You can also invoke the server with `python -m mcp_recovery_lab.server --scenario transient` if your client cannot find the console script.

To see a complete exchange without configuring an agent, install the optional official MCP Python client (`python -m pip install mcp`) and run `python examples/client.py`. It discovers the tool, receives the simulated failure, and retries once.

### Run a Pydantic AI agent without an API key

```bash
python -m pip install "pydantic-ai-slim[mcp]>=2.66,<3"
python examples/pydantic_agent.py
```

This example connects a real Pydantic AI `Agent` to the lab through MCP. A scripted `FunctionModel` calls the tool, sees the temporary error and retries once; assertions verify the two calls and final result. The model decisions are deliberately scripted: the example verifies the framework integration and recovery path, **not** how an LLM would behave. No model service is called. To verify every scenario with the official MCP Python client, run `python examples/verify_scenarios.py`.

## Scenarios

| Scenario | `lookup_order` behavior for `ORD-100` | What to observe |
| --- | --- | --- |
| `healthy` | Returns the simulated shipped status. | Normal lookup. |
| `transient` | First valid lookup fails; subsequent lookups succeed. | Whether the client notices and retries. |
| `rate-limit` | First two valid lookups return a simulated limit error, then succeed. | Whether retries are bounded; the fixture does not impose a real delay. |
| `stale` | First lookup reports `processing` at revision 1; later lookups report `shipped` at revision 2. | How an agent handles conflicting observations and revision information. |
| `unavailable` | Every lookup fails. | Whether the agent reports uncertainty. |

Unknown order IDs return a tool error and do not consume the transient failure. These are simulated outcomes, not a production service or a measure of model quality. The server does not judge an agent's answer, implement transport fault injection, or validate arbitrary MCP servers.

## Run the checks

```bash
python -m unittest discover -s tests -v
```

The suite includes a real subprocess speaking newline-delimited JSON-RPC over stdio. No network or credentials are needed for the server or tests. MCP clients and models are separate software and may have their own costs or network access.

## How it works

The server supports the MCP `initialize`, `ping`, `tools/list`, and `tools/call` methods needed for this example, plus notifications. It offers one tool, `lookup_order`. It intentionally implements a small subset of MCP: it is a teaching and testing fixture, not a general MCP framework. Only use simulated order identifiers with it.

## Contributing

Small, reproducible examples and bug reports are welcome. Please include the client, Python version, scenario, and steps to reproduce. Do not include real prompts, private data, or credentials in issues or examples.

MIT license.
