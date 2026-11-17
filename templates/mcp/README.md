# Connect your agent to IsaFlow (MCP)

IsaFlow's MCP server: `https://app.isaflow.co.za/api/mcp` (Streamable HTTP, OAuth).
No token goes in any file. The first time the agent calls IsaFlow, a browser opens: **you** sign in and choose
the company. Choose the company you are migrating — the same login can hold several companies.

Name the server `isaflow-<short>` (e.g. `isaflow-example`) so it is obvious which company it is for.
Put the config in the company's `04_Finance/Agentic_Accounting` folder (project scope) where the agent supports it.

## Claude Code / Claude Desktop (Code)
`.mcp.json` in the working folder:
```json
{ "mcpServers": { "isaflow-<short>": { "type": "http", "url": "https://app.isaflow.co.za/api/mcp" } } }
```

## OpenAI Codex (CLI / IDE)
```
codex mcp add isaflow-<short> --url https://app.isaflow.co.za/api/mcp
codex mcp login isaflow-<short>
```
or in `~/.codex/config.toml` (or `.codex/config.toml` in a trusted project):
```toml
[mcp_servers.isaflow-<short>]
url = "https://app.isaflow.co.za/api/mcp"
```

## Cursor
`.cursor/mcp.json` in the working folder:
```json
{ "mcpServers": { "isaflow-<short>": { "url": "https://app.isaflow.co.za/api/mcp" } } }
```

## Any other agent
Any MCP client that supports remote Streamable HTTP servers with OAuth works: give it the URL above.

## Chat-only assistants (e.g. ChatGPT in the browser)
They cannot run the scripts or reach your folders. Use them only to talk you through the playbook; the posting
and checks need an agent with file access, a terminal and MCP.

## Check the connection
Ask the agent to call `list_companies` and `company_profile`. The company name, VAT number and company id must be
the company you are migrating. Record the id in the company's `AGENTS.md`.
