# partna-mcp

MCP server for the Partna partner programme: an agent registers members, reports
payments and refunds, issues partner links and reads the numbers. Money does not
pass through the server — it only moves facts and reads figures.

English · [Русский](README.ru.md)

## What is inside

A package with a port and adapters:

```
MCP tools
      │
      ▼
 port PartnerApi  — operations mirror the core's use cases
      ├── HttpBackend  — over the public facts contract (this package)
      └── LocalBackend — in the closed core repository, calls use cases
```

Tools do not know where they travel: `PARTNA_BACKEND=http` talks to a bridge or
to the core over HTTP. The local adapter is installed separately and exists only
where the database is reachable.

## Tools

| Tool | What it does |
|---|---|
| `status` | service reachability, mode, whether a key is set |
| `partner_link` | a partner's link for their clients |
| `claim` | bind a client to a partner code |
| `member` | a programme member and who invited them |
| `order` | a client paid |
| `refund` | a client was refunded |
| `referral_status` | whether a client is bound, and to which code |
| `dashboard` | partner summary |
| `payouts` | payout history |

Write tools accept `dry_run`: it shows the request body and sends nothing.

## Running

```bash
export PARTNA_BRIDGE_URL=https://partna.client.com
export PARTNA_BRIDGE_TOKEN=...        # bridge token, if it is set
export PARTNA_ENGINE_URL=https://networks.partna.dev
export PARTNA_API_KEY=...             # tenant key for reads
uvx partna-mcp
```

Transport is stdio. Wiring it into a client:

```json
{
  "mcpServers": {
    "partna": {
      "command": "uvx",
      "args": ["partna-mcp"],
      "env": {
        "PARTNA_BRIDGE_URL": "https://partna.client.com",
        "PARTNA_ENGINE_URL": "https://networks.partna.dev",
        "PARTNA_API_KEY": "..."
      }
    }
  }
}
```

Without a bridge, set only `PARTNA_ENGINE_URL` and `PARTNA_API_KEY`: facts go
straight to the core using its paths.

## Rules

- `eventId` is unique forever: one fact — one identifier, a retry must not create
  a second accrual.
- Keys come from the environment only; tools never accept them as arguments and
  never print them in responses.
- Errors come back as the service text, without stacks and without secrets.

## Contract

The five operations are described in
[partna-bridge/spec](https://github.com/partna-dev/partna-bridge/blob/main/spec/README.md).
Golden cases live inside the package (`src/partna_mcp/golden/`) and are readable
through `partna_mcp.golden.load_cases()`: the shared reference for the HTTP and
the local adapter — the same input must give the same answer.

## License

MIT — see [LICENSE](LICENSE).
