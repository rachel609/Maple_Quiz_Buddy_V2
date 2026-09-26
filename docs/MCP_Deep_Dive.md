# MCP (Model Context Protocol) - Deep Dive

## What is MCP?

**Model Context Protocol** — an open-source standard protocol released by Anthropic in 2024. The core problem it solves:

> How does an LLM interact with the outside world?

Previously, every AI application reinvented the wheel — OpenAI had Function Calling, LangChain had Tools, every vendor had a different format. MCP unifies this interface, similar to how USB standardized peripheral connections.

---

## Overall Architecture

```
┌─────────────────────────────────────────────────┐
│              Host (Host Application)             │
│  Claude Desktop / Claude Code / IDE / Your App   │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ MCP      │  │ MCP      │  │ MCP      │       │
│  │ Client A │  │ Client B │  │ Client C │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
└───────┼──────────────┼──────────────┼────────────┘
        │              │              │
   (transport)    (transport)    (transport)
        │              │              │
   ┌────▼─────┐  ┌────▼─────┐  ┌────▼─────┐
   │ MCP      │  │ MCP      │  │ MCP      │
   │ Server   │  │ Server   │  │ Server   │
   │ (GitHub) │  │ (Database)│  │ (Gmail)  │
   └──────────┘  └──────────┘  └──────────┘
```

Three roles:

### Host
The application running the LLM. Examples: Claude Desktop, VS Code + Copilot, your own chatbot. The Host manages the entire lifecycle and decides which Servers to connect to.

### Client
A component inside the Host. Each Client maintains a 1:1 connection with one Server. Claude Desktop can connect to multiple Servers simultaneously because it runs multiple Clients internally.

### Server
**The part you write.** It exposes capabilities for the LLM to use. A single Server can provide three types of capabilities —

---

## Three Primitives

### 1. Tools — LLM Actively Calls These

**Direction: LLM → Server (model-controlled)**

The LLM decides on its own when to call and which tool to use. Equivalent to Function Calling, but with a standardized format.

```python
@server.tool()
async def query_database(sql: str) -> str:
    """Execute a read-only SQL query"""
    result = db.execute(sql)
    return json.dumps(result)
```

When the user says "look up last month's sales," the LLM decides to call `query_database` and constructs the SQL itself.

**Key characteristics:**
- Input parameters described with JSON Schema
- Must be confirmed by the user before execution (security mechanism)
- Similar to a POST request — has side effects

### 2. Resources — LLM Reads Data

**Direction: Application → Server (application-controlled)**

It's not the LLM that decides what to read — the application layer (Host) decides what data to feed to the LLM. Similar to a read-only REST API.

```python
@server.resource("file://{path}")
async def read_file(path: str) -> str:
    """Read a local file"""
    return open(path).read()
```

**Key characteristics:**
- Identified by URI: `file://xxx`, `db://users/123`, `github://repo/issues`
- Read-only, no side effects (similar to a GET request)
- Can have MIME types (text/plain, application/json, image/png)
- Supports subscriptions — automatic notifications when data changes

### 3. Prompts — Preset Interaction Templates

**Direction: User → Server (user-controlled)**

Templates that the user actively chooses to trigger — NOT decided by the LLM. In Claude Desktop, these appear in the `/` slash command menu.

```python
@server.prompt()
async def code_review(language: str, code: str):
    """Review code for best practices"""
    return f"Review this {language} code:\n\n{code}\n\nFocus on security and performance."
```

**Key characteristics:**
- Triggered by the user, not by the AI
- Can accept parameters
- Returns pre-filled messages (system/user) that are fed directly to the LLM

### Comparison Table

| | Tools | Resources | Prompts |
|---|---|---|---|
| Who triggers | LLM itself | Application layer | User |
| Analogy | POST API | GET API | Shortcut template |
| Has side effects | Yes | No | No |
| Requires confirmation | Yes | No | No |

---

## Transport Layer

MCP is not tied to a specific transport mechanism. Currently two options:

### stdio (Standard Input/Output)
- Server runs as a subprocess, communicating via stdin/stdout
- **This is what Claude Desktop uses**
- Runs locally, zero network configuration

```json
// claude_desktop_config.json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["path/to/server.py"]
    }
  }
}
```

### SSE (Server-Sent Events) / Streamable HTTP
- Runs over HTTP, suitable for remote deployment
- Can run in the cloud, multiple Clients connecting to the same Server

---

## Protocol Lifecycle

```
Client                          Server
  │                               │
  │──── initialize ──────────────>│  (1) Handshake: exchange versions & capabilities
  │<─── initialize result ────────│
  │                               │
  │──── initialized ─────────────>│  (2) Confirmation complete
  │                               │
  │──── tools/list ──────────────>│  (3) Capability discovery
  │<─── tool list ────────────────│
  │                               │
  │──── resources/list ──────────>│
  │<─── resource list ────────────│
  │                               │
  │      ... normal operation ... │  (4) Call tools, read resources
  │                               │
  │──── tools/call ──────────────>│
  │<─── tool result ──────────────│
  │                               │
  │──── shutdown ────────────────>│  (5) Graceful shutdown
  │<─── (close) ──────────────────│
```

1. **Initialize** — Handshake: both sides exchange supported protocol versions and capabilities (which primitives are supported)
2. **Discovery** — Client asks Server what tools/resources/prompts are available
3. **Operation** — Normal calls during the session
4. **Shutdown** — Close the connection gracefully

---

## Additional Capabilities

### Sampling (Reverse Invocation)
The Server can request the LLM to generate content in reverse. For example, if your MCP Server needs AI help summarizing a block of text, it can use sampling to have the Host's LLM do it.

### Roots
The Client tells the Server "here are the directories you're allowed to operate on," restricting the permission scope.

### Logging
The Server can send logs to the Client for debugging purposes.

### Notifications
Bidirectional notifications — the Server can notify the Client when its tool list changes so the Client can refresh. When a Resource's content changes, it can push updates.

---

## Why MCP Matters

**Before MCP:**
Every AI application built its own integrations — Slack bot writes its own API adapter, GitHub Copilot builds its own file reader. N applications x M data sources = N x M integrations.

**After MCP:**
Write one Server once, and every MCP-compatible Host can use it. GitHub writes one MCP Server, and Claude Desktop, VS Code, JetBrains can all connect. It becomes N + M instead of N x M.

It's the USB-C of the AI world.

---

## Further Reading

- Official spec: https://modelcontextprotocol.io
- Python SDK: `pip install mcp`
- TypeScript SDK: `npm install @modelcontextprotocol/sdk`
