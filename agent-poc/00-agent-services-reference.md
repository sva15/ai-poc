# AIForce Agent Services — Complete Reference

## Overview

AIForce provides **4 services** for building, managing, and executing AI Agents:

| Service | Full Name | Purpose |
|---------|-----------|---------|
| **AMS** | Agent Management Service | Create, configure, test, and evaluate individual agents |
| **AES** | Agent Executor Service | Create multi-agent usecases (workflows) and execute them |
| **TCS** | Tools & Connector Service | Publish and manage tools that agents can use |
| **MCS** | MCP Studio Service | Connect external MCP servers to provide tools/prompts/resources to agents |

### How They Connect

```
                        ┌─────────────────────────────────┐
                        │       Your External MCP Server   │
                        │  (exposes tools via SSE/HTTP)    │
                        └──────────────┬──────────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐
                    │  MCS — MCP Studio Service            │
                    │  Registers external MCP servers       │
                    │  Discovers tools/prompts/resources    │
                    │  Makes tools available to agents      │
                    └──────────────────┬──────────────────┘
                                       │
┌──────────────┐    ┌──────────────────▼──────────────────┐    ┌──────────────┐
│  PES         │───▶│  AMS — Agent Management Service      │◀───│  SGS         │
│  (Prompts)   │    │  Creates individual agents            │    │  (Security)  │
│              │    │  Links: LLM + prompt + tools + SGS    │    │              │
└──────────────┘    └──────────────────┬──────────────────┘    └──────────────┘
                                       │
                    ┌──────────────────▼──────────────────┐    ┌──────────────┐
                    │  AES — Agent Executor Service        │───▶│  GCS         │
                    │  Combines agents into usecases        │    │  (Tracing)   │
                    │  Supervisor or Graph patterns         │    │              │
                    │  Executes with tracing                │    └──────────────┘
                    └─────────────────────────────────────┘
```

---

# Service 1: AMS — Agent Management Service

## What It Does
AMS is where you create and manage **individual agents**. Each agent has a name, a linked LLM model, an optional prompt, optional tools, and an optional security group. You can test agents directly or evaluate them against metrics.

## Endpoints

### 1.1 Create Agent
**`POST /ams/agentic-studio/agents`**

Creates a new agent with its configuration.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_name` | string | Yes | Unique name for the agent |
| `description` | string | Yes | What the agent does |
| `llm_model_id` | integer | Yes | LLM configuration ID (from G3S) |
| `design_pattern_id` | integer | No | Design pattern for the agent |
| `framework_id` | integer | No | Framework to use |
| `security_group_id` | integer | No | SGS security group for guardrails |
| `human_input_mode` | string | No | When to ask for human input |
| `max_consecutive_reply` | integer | No | Max replies before stopping |
| `prompt_id` | integer | No | PES prompt ID to use as instructions |
| `rag_ids` | list | No | RAG pipeline IDs for knowledge retrieval |
| `tool_ids` | list | No | Tool IDs from TCS to give the agent |
| `a2a_enabled` | boolean | No | Agent-to-Agent protocol enabled |
| `mcp_enabled` | boolean | No | MCP tools enabled |
| `is_public` | boolean | No | Whether the agent is publicly accessible |
| `version` | string | No | Version identifier |
| `agent_config` | object | No | Additional agent configuration |
| `publish_status` | string | No | Draft / Published |

**Use case**: Create a customer support agent linked to your prompt from PES, your security group from SGS, and tools from TCS/MCP.

---

### 1.2 List Agents
**`GET /ams/agentic-studio/agents`**

Returns all agents. Supports pagination and search.

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number |
| `page_size` | integer | Items per page |
| `search` | string | Search by agent name |
| `publish_status` | string | Filter by Draft/Published |

**Use case**: Browse all agents created on the platform, search by name.

---

### 1.3 Get Agent Details
**`GET /ams/agentic-studio/agents/{agent_id}`**

Returns full configuration of a specific agent by ID.

**Use case**: Verify agent configuration before execution.

---

### 1.4 Update Agent
**`PUT /ams/agentic-studio/agents/{agent_id}`**

Updates an existing agent's configuration.

**Use case**: Modify an agent's prompt, tools, or LLM model after creation.

---

### 1.5 Delete Agent
**`DELETE /ams/agentic-studio/agents/{agent_id}`**

Removes an agent permanently.

---

### 1.6 Duplicate Agent
**`POST /ams/agentic-studio/agents/{agent_id}/duplicate`**

Creates a copy of an existing agent with a new name.

| Parameter | Type | Description |
|-----------|------|-------------|
| `duplicate_agent_name` | string | Name for the duplicate |
| `description` | string | Description for the duplicate |

**Use case**: Clone an agent to create a variant with different tools or prompts.

---

### 1.7 Execute Agent
**`POST /ams/agentic-studio/agent-execution`**

Runs an agent with user input. This is the main testing/execution endpoint.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent` | integer | Yes | Agent ID to execute |
| `input` | string | Yes | User input (text or message list) |
| `session_id` | integer | No | Session ID for conversation continuity |
| `stream` | boolean | No | Stream response (default: false) |
| `mode` | string | No | Execution mode |

**Input formats supported**:
- Simple string: `"What is the capital of India?"`
- Message list: `[{"content": "What is the capital of India?", "role": "user"}]`

**Use case**: Test an agent with a question, get back the agent's response including any tool calls.

---

### 1.8 Get Dropdown Options
**`GET /ams/agentic-studio/dropdowns`**

Returns available options for agent configuration (frameworks, patterns, models).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Dropdown name to fetch |

**Use case**: Before creating an agent, call this to discover available `framework_id`, `design_pattern_id`, `llm_model_id` values.

---

### 1.9 Bulk Fetch Agents
**`POST /ams/agentic-studio/agents/bulk-fetch`**

Fetch multiple agents by their IDs in a single call.

**Use case**: When building a usecase, fetch all participating agents at once.

---

### 1.10 Upload Files
**`POST /ams/agentic-studio/upload-files`**

Upload files to the agent's workspace.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | array | Yes | Files to upload |
| `namespace` | string | Yes | Storage namespace |

**Use case**: Provide reference documents for the agent to use.

---

### 1.11 Agent Trace Logs
**`GET /ams/agentic-studio/trace/logs/{trace_id}`**

Fetch detailed trace logs for an agent execution by trace ID.

**Use case**: After executing an agent, use the `trace_id` from the response to see step-by-step what the agent did — which tools it called, what it reasoned about, etc.

---

### 1.12 List Security Groups
**`GET /ams/agentic-studio/list_security_group`**

Lists all security groups accessible to the user (from SGS).

**Use case**: Before creating an agent, check which security groups are available to link.

---

### 1.13 Get Metrics
**`GET /ams/agentic-studio/metrics`**

Returns available evaluation metrics for agents.

| Parameter | Type | Description |
|-----------|------|-------------|
| `applicability` | string | Filter by applicability |
| `custom` | boolean | Filter custom metrics |
| `llm-based` | boolean | Filter LLM-based metrics |

**Use case**: Discover which quality metrics you can evaluate your agent against.

---

### 1.14 Get Datasets
**`GET /ams/agentic-studio/datasets`**

Lists datasets available for agent evaluation.

| Parameter | Type | Description |
|-----------|------|-------------|
| `applicability` | string | `llm` or `non_llm` |
| `page` / `limit` | integer | Pagination |

---

### 1.15 Upload Dataset
**`POST /ams/agentic-studio/datasets/upload`**

Upload a test dataset for agent evaluation.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Dataset name |
| `description` | string | Yes | What the dataset tests |
| `file` | file | Yes | CSV/JSON test data file |
| `applicability` | string | No | Default: `llm` |
| `use_case_type` | string | No | Default: `agent` |

---

### 1.16 Evaluate Agent
**`POST /ams/agentic-studio/evaluate_agent`**

Run a quality evaluation on an agent against specific metrics and datasets.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_id` | integer | No | Agent ID to evaluate |
| `prompt_name` | string | Yes | Prompt identifier |
| `agent_prompt` | string | Yes | The user input to test |
| `metric_datasets` | array | Yes | Metrics + datasets to evaluate against |
| `expected_output` | string | No | Expected agent response |
| `context` | array | No | Context documents |
| `agent_output` | string | No | Pre-existing agent output to evaluate |
| `actual_tool_calls` | array | No | What tools the agent actually called |
| `expected_tool_calls` | array | No | What tools were expected |
| `agent_trace_messages` | array | No | Full conversation trace |

**Metric/Dataset example**:
```json
{
  "metric_datasets": [
    {"dataset": "ds_task_completion", "metric": "Task Completion"}
  ]
}
```

**Use case**: Evaluate whether your agent completes tasks correctly, uses the right tools, and produces quality responses.

---

### 1.17 Get Evaluation Report
**`GET /ams/agentic-studio/get_agent_evaluation_report/{agent_id}`**

Fetch the evaluation results for a previously evaluated agent.

---

# Service 2: AES — Agent Executor Service

## What It Does
AES manages **usecases** — multi-agent workflows where multiple agents collaborate. It supports two patterns:
- **Supervisor Pattern (0)**: One supervisor agent orchestrates worker agents
- **Graphical Pattern (1)**: Agents connected in a directed graph (DAG) with custom flow

## Endpoints

### 2.1 Create Usecase
**`POST /aes/usecases`**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Usecase name |
| `requirement` | string | Yes | What the usecase should accomplish |
| `pattern_type` | integer | Yes | `0` = Supervisor, `1` = Graphical |
| `description` | string | Yes | Detailed description |
| `category_id` | integer | Yes | Category to organize under |
| `usecase_json` | object | No | Agent IDs, graph nodes, plan |
| `publish_status` | string | No | `Draft` or `Published` |

**usecase_json format**:
```json
{
  "agent_ids": [1, 2, 3],
  "graph_nodes": {"edges": [], "nodes": []},
  "plan": "optional plan text",
  "planner_chat_history": [{"content": "...", "role": "..."}],
  "test_chat_history": [{"content": "...", "role": "..."}]
}
```

**Use case**: Define a workflow where Agent A (researcher) passes results to Agent B (writer) orchestrated by a supervisor.

---

### 2.2 List Usecases
**`GET /aes/usecases`**

Returns all usecases with pagination, search, and filtering.

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` / `page_size` | integer | Pagination |
| `search` | string | Search by name |
| `category_id` | integer | Filter by category |
| `publish_status` | string | Filter by status |

---

### 2.3 Get/Update/Delete Usecase
- **`GET /aes/usecases/{usecase_id}`** — Get details
- **`PUT /aes/usecases/{usecase_id}`** — Update
- **`DELETE /aes/usecases/{usecase_id}`** — Delete

---

### 2.4 Planning Agent
**`POST /aes/usecases/plan`**

Uses an LLM to automatically generate a plan for how agents should collaborate.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `requirement` | string | Yes | What the usecase should achieve |
| `pattern_type` | integer | Yes | `0` = Supervisor, `1` = Graphical |
| `selected_agents` | array | No | Specific agent IDs to consider |

**Use case**: Describe what you want ("research a topic and write a blog post") and the LLM generates a plan assigning agents.

---

### 2.5 Execute Usecase
**`POST /aes/usecases/execute`**

Execute a usecase (interactive/test mode).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `usecase` | integer | Yes | Usecase ID |
| `input` | string | No | User input |
| `messages` | array | No | Message list format |
| `session_id` | integer | No | For conversation continuity |
| `stream` | boolean | No | Stream response |
| `thread_id` | string | No | For DAG-based usecases |

---

### 2.6 Run Execution (Async)
**`POST /aes/executions`**

Queue a usecase execution asynchronously with optional callback.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `usecase_id` | integer | Yes | Usecase ID |
| `input` | object | Yes | Execution input |
| `execution_id` | integer | No | Continue existing execution |
| `reference_id` | string | No | Your external reference ID |
| `callback_url` | string | No | URL to call when done |

**Use case**: Submit a long-running usecase execution and get notified via callback when complete.

---

### 2.7 List/Get/Delete Executions
- **`GET /aes/executions`** — List all executions
  - Filter by: `usecase_id`, `reference_id`, `exec_status` (0=New, 1=In Progress, 2=Completed, 3=Failed)
- **`GET /aes/executions/{execution_id}`** — Get result
- **`DELETE /aes/executions/{execution_id}`** — Delete

---

### 2.8 Download Execution Result
**`GET /aes/executions/{execution_id}/result-pdf`**

Download execution output as a PDF document.

---

### 2.9 Get Trace Logs
**`GET /aes/usecase/traces/{trace_id}/logs`**

Fetch detailed trace logs for a usecase execution.

---

### 2.10 Categories & Catalogues

Categories organize usecases, catalogues group categories.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/aes/categories` | POST | Create category |
| `/aes/categories` | GET | List categories |
| `/aes/categories/{id}` | GET/PUT/DELETE | Manage category |
| `/aes/catalogues` | GET | List catalogues |
| `/aes/catalogue-permissions` | POST/GET | Manage permissions |

---

### 2.11 Get Usecase Agent Tools
**`GET /aes/usecases/agents-tools`**

Shows which agents have disconnected tools (tools that are configured but not accessible).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | integer | Yes | Agent to check |

---

### 2.12 Upload Files / Download Outputs

- **`POST /aes/upload-files`** — Upload files for a usecase
- **`POST /aes/usecase/download_outputs`** — Download agent outputs as ZIP

---

# Service 3: TCS — Tools & Connector Service

## What It Does
TCS manages **tools** that agents can use — API connectors, scripts, code functions. Tools are code-based capabilities that extend what an agent can do beyond just LLM responses.

## Endpoints

### 3.1 Publish Tool
**`POST /tcs/tools_library/publish_tool`**

Create and publish a new tool.

**Use case**: Create a weather API tool, a database query tool, or a calculator tool that agents can call.

---

### 3.2 List Tools
**`GET /tcs/tools_library`**

Returns all available tools.

**Use case**: See what tools are available to assign to agents.

---

### 3.3 Get Tool Details
**`GET /tcs/tools_library/{tool_id}`**

Get full details of a specific tool.

---

### 3.4 Update/Delete Tool
- **`PUT /tcs/tools_library`** — Update tool
- **`DELETE /tcs/tools_library`** — Delete tool

---

### 3.5 Execute Tool
**`POST /tcs/tools_library/{tool_id}/execute`**

Directly execute a tool (for testing).

**Use case**: Test a tool independently before assigning it to an agent.

---

### 3.6 Extract API Methods
**`GET /tcs/tools_library/get_extracted_methods`**
**`POST /tcs/tools_library/extract_api_method`**

Extract callable methods from an API specification.

**Use case**: Upload an OpenAPI spec and TCS auto-discovers the methods that can be turned into tools.

---

### 3.7 Generate Function / API Code / JSON Schema
- **`POST /tcs/tools_library/generate_function`** — Auto-generate tool function code
- **`POST /tcs/tools_library/generate_api_code`** — Generate API integration code
- **`POST /tcs/tools_library/generate_json_schema`** — Generate JSON schema for a tool

---

### 3.8 Run Script
**`POST /tcs/tools_library/run_script`**

Execute a custom script.

---

### 3.9 OAuth Configuration
- **`POST /tcs/tools_library/save_oauth_config`** — Save OAuth config
- **`PUT /tcs/tools_library/update_oauth_config`** — Update OAuth config
- **`GET /tcs/tools_library/list_oauth_configs`** — List configs
- **`DELETE /tcs/tools_library/delete_oauth_config`** — Delete config
- **`GET /tcs/oauth/authorize`** — Start OAuth flow

**Use case**: Configure OAuth for tools that connect to APIs requiring authentication (Google, GitHub, etc.).

---

# Service 4: MCS — MCP Studio Service

## What It Does
MCS is the **Model Context Protocol (MCP)** integration layer. It allows you to connect **external MCP servers** to AIForce, making their tools, prompts, and resources available to agents. This is the key service for our POC approach.

### MCP Concept
MCP is a protocol for externalizing AI agent tools. Instead of building tools inside TCS, you run a separate MCP server that exposes tools via a standard protocol. AIForce connects to it and makes those tools available to agents.

**Why MCP matters**:
- Tools can be hosted anywhere (your own server, cloud function, Docker container)
- Tools are not locked into the AIForce platform
- Standard protocol — works with multiple AI platforms
- You control the tool server independently

## Endpoints

### 4.1 List MCP Servers
**`GET /mcs/mcp_studio/servers`**

Returns all registered MCP servers with their connection status.

**Use case**: See what external MCP servers are connected to the platform.

---

### 4.2 Register MCP Server
**`POST /mcs/mcp_studio/servers`**

Register a new external MCP server with AIForce.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Server name |
| `transport` | integer | Yes | Transport type: `1` = Stdio, `2` = SSE |
| `description` | string | No | What this server provides |
| `command` | string | No | Command to launch (for Stdio) |
| `arguments` | string | No | Command arguments |
| `variables` | array | No | Environment variables `[{"key":"k","value":"v"}]` |
| `server_url` | string | No | Server URL (for SSE transport) |
| `auth_type` | integer | No | `1`=None, `2`=Bearer, `3`=Header, `4`=Custom |
| `auth_credentials` | array | No | Auth credentials `[{"key":"k","value":"v"}]` |
| `is_active` | boolean | No | Active status (default: true) |

**For our POC (SSE transport)**:
```json
{
  "name": "my-external-tools",
  "transport": 2,
  "server_url": "https://your-server.com/mcp/sse",
  "auth_type": 1,
  "description": "External MCP server with custom tools"
}
```

**Use case**: Register your external MCP server's SSE endpoint so AIForce can discover and use its tools.

---

### 4.3 Update MCP Server
**`PUT /mcs/mcp_studio/servers/{mcp_id}`**

Update an existing MCP server configuration.

---

### 4.4 Get MCP Server / Config
- **`GET /mcs/mcp_studio/servers/{mcp_id}`** — Get server details
- **`GET /mcs/mcp_studio/server/{mcp_id}/config`** — Get formatted server config

---

### 4.5 Delete MCP Server
**`DELETE /mcs/mcp_studio/servers/{mcp_id}`**

Removes the MCP server and deactivates its primitives.

---

### 4.6 Execute MCP Tool
**`POST /mcs/mcp_studio/servers/{mcp_id}/execute`**

Execute a specific tool/prompt/resource on the MCP server.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `method` | string | Yes | The method to call |
| `params` | object | Yes | Parameters for the method |

**Use case**: Directly test a tool on an MCP server before using it in an agent.

---

### 4.7 List Primitives
**`GET /mcs/mcp_studio/servers/{mcp_id}/primitives`**

Shows all tools, prompts, and resources discovered from the MCP server.

**Primitive types**:
| Type ID | Type | Description |
|---------|------|-------------|
| `1` | Tool | A callable function/action |
| `2` | Prompt | A prompt template |
| `3` | Resource | A data resource (file, database, etc.) |

---

### 4.8 Update Primitives Status
**`POST /mcs/mcp_studio/servers/{mcp_id}/primitives`**

Activate or deactivate specific primitives.

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | `active` or `inactive` |

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Primitive name |
| `primitive_type` | integer | Yes | 1=Tool, 2=Prompt, 3=Resource |

**Use case**: Enable only specific tools from an MCP server for use by agents.

---

### 4.9 Add/Remove/Deactivate Primitives
- **`POST /mcs/mcp_studio/primitives/add-primitives`** — Add a new primitive
- **`POST /mcs/mcp_studio/servers/{mcp_id}/remove-primitives`** — Remove primitives
- **`POST /mcs/mcp_studio/primitives/{primitive_id}/deactivate`** — Deactivate a primitive

---

### 4.10 AIForce Primitives
Connect existing AIForce tools/prompts to an MCP server:

- **`POST /mcs/mcp_studio/servers/{mcp_id}/aiforce_primitives`** — Add AIForce primitives to MCP server
- **`GET /mcs/mcp_studio/servers/{mcp_id}/aiforce_primitives`** — List AIForce primitives on MCP server
- **`DELETE /mcs/mcp_studio/servers/{mcp_id}/aiforce_primitives/{primitive_id}`** — Remove
- **`GET /mcs/mcp_studio/aiforce_primitives`** — List all AIForce primitives across all servers

---

# POC Approach: MCP External Tools

## Architecture

```
┌──────────────────────────────────┐
│  Your External MCP Server        │
│  (Python SSE server)             │
│                                  │
│  Tools exposed:                  │
│  - get_weather(city)             │
│  - calculate(expression)         │
│  - search_knowledge(query)       │
│                                  │
│  Runs on: EC2 / Lambda / Docker  │
│  Protocol: SSE (Server-Sent Events)│
└──────────────┬───────────────────┘
               │ HTTPS / SSE
               ▼
┌──────────────────────────────────┐
│  MCS — Register MCP Server       │
│  POST /mcs/mcp_studio/servers    │
│  transport=2 (SSE)               │
│  server_url=https://your-server  │
│                                  │
│  Auto-discovers tools:           │
│  GET /mcs/.../primitives         │
└──────────────┬───────────────────┘
               │ Tools available
               ▼
┌──────────────────────────────────┐
│  AMS — Create Agent              │
│  POST /ams/.../agents            │
│  mcp_enabled = true              │
│  Links to MCP server tools       │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  AMS — Execute Agent             │
│  POST /ams/.../agent-execution   │
│  Agent uses MCP tools to answer  │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│  AMS/AES — View Trace Logs       │
│  GET /ams/.../trace/logs/{id}    │
│  See tool calls, reasoning, etc  │
└──────────────────────────────────┘
```

## POC Step-by-Step Plan

### Step 1: Build an External MCP Server
- Simple Python SSE server exposing 2-3 tools
- Example tools: `get_weather`, `calculate`, `search_knowledge`
- Deploy on EC2, Lambda URL, or run locally with ngrok

### Step 2: Register MCP Server in AIForce
- `POST /mcs/mcp_studio/servers` with SSE transport and URL
- Verify with `GET /mcs/mcp_studio/servers`

### Step 3: Discover and Activate Tools
- `GET /mcs/mcp_studio/servers/{mcp_id}/primitives` to see discovered tools
- Activate desired tools via `POST /mcs/mcp_studio/servers/{mcp_id}/primitives`

### Step 4: Create Agent with MCP Tools
- Get dropdowns: `GET /ams/agentic-studio/dropdowns?name=...`
- Create agent: `POST /ams/agentic-studio/agents` with `mcp_enabled=true`

### Step 5: Test Agent Execution
- `POST /ams/agentic-studio/agent-execution` with agent ID + user input
- Agent should use MCP tools to answer

### Step 6: Review Trace Logs
- Use `trace_id` from response to call `GET /ams/agentic-studio/trace/logs/{trace_id}`
- Verify tool calls, reasoning chain, and final output

### Step 7: (Optional) Create Multi-Agent Usecase
- Create category: `POST /aes/categories`
- Create usecase: `POST /aes/usecases` with pattern_type=0 (Supervisor)
- Execute: `POST /aes/usecases/execute`

---

## All Endpoints Quick Reference

### AMS (16 endpoints)
| Method | Endpoint | Action |
|--------|----------|--------|
| POST | `/ams/agentic-studio/agents` | Create agent |
| GET | `/ams/agentic-studio/agents` | List agents |
| POST | `/ams/agentic-studio/agents/bulk-fetch` | Bulk fetch agents |
| GET | `/ams/agentic-studio/agents/{id}` | Get agent |
| PUT | `/ams/agentic-studio/agents/{id}` | Update agent |
| DELETE | `/ams/agentic-studio/agents/{id}` | Delete agent |
| POST | `/ams/agentic-studio/agents/{id}/duplicate` | Duplicate agent |
| POST | `/ams/agentic-studio/agent-execution` | Execute agent |
| GET | `/ams/agentic-studio/dropdowns` | Get dropdown options |
| POST | `/ams/agentic-studio/upload-files` | Upload files |
| GET | `/ams/agentic-studio/trace/logs/{trace_id}` | Get trace logs |
| GET | `/ams/agentic-studio/metrics` | Get evaluation metrics |
| GET | `/ams/agentic-studio/datasets` | Get datasets |
| POST | `/ams/agentic-studio/datasets/upload` | Upload dataset |
| POST | `/ams/agentic-studio/evaluate_agent` | Evaluate agent |
| GET | `/ams/agentic-studio/get_agent_evaluation_report/{id}` | Get evaluation report |
| GET | `/ams/agentic-studio/list_security_group` | List security groups |

### AES (17 endpoints)
| Method | Endpoint | Action |
|--------|----------|--------|
| POST | `/aes/usecases` | Create usecase |
| GET | `/aes/usecases` | List usecases |
| GET | `/aes/usecases/{id}` | Get usecase |
| PUT | `/aes/usecases/{id}` | Update usecase |
| DELETE | `/aes/usecases/{id}` | Delete usecase |
| POST | `/aes/usecases/plan` | AI-generated plan |
| POST | `/aes/usecases/execute` | Execute usecase |
| GET | `/aes/usecases/agents-tools` | Check agent tools |
| POST | `/aes/executions` | Run async execution |
| GET | `/aes/executions` | List executions |
| GET | `/aes/executions/{id}` | Get execution result |
| DELETE | `/aes/executions/{id}` | Delete execution |
| GET | `/aes/executions/{id}/result-pdf` | Download result PDF |
| GET | `/aes/usecase/traces/{trace_id}/logs` | Get trace logs |
| POST/GET | `/aes/categories` | Create/list categories |
| GET/PUT/DELETE | `/aes/categories/{id}` | Manage category |
| GET | `/aes/catalogues` | List catalogues |

### TCS (20 endpoints)
| Method | Endpoint | Action |
|--------|----------|--------|
| POST | `/tcs/tools_library/publish_tool` | Publish tool |
| PUT | `/tcs/tools_library` | Update tool |
| GET | `/tcs/tools_library` | List tools |
| DELETE | `/tcs/tools_library` | Delete tool |
| GET | `/tcs/tools_library/{id}` | Get tool |
| POST | `/tcs/tools_library/{id}/execute` | Execute tool |
| POST | `/tcs/tools_library/extract_api_method` | Extract API methods |
| POST | `/tcs/tools_library/run_script` | Run script |
| POST | `/tcs/tools_library/generate_function` | Generate function |
| POST | `/tcs/tools_library/generate_api_code` | Generate API code |
| POST | `/tcs/tools_library/generate_json_schema` | Generate JSON schema |
| POST/PUT/GET/DELETE | `/tcs/tools_library/*_oauth_config` | OAuth management |
| GET | `/tcs/oauth/authorize` | OAuth flow |

### MCS (15 endpoints)
| Method | Endpoint | Action |
|--------|----------|--------|
| GET | `/mcs/mcp_studio/servers` | List MCP servers |
| POST | `/mcs/mcp_studio/servers` | Register MCP server |
| PUT | `/mcs/mcp_studio/servers/{id}` | Update server |
| DELETE | `/mcs/mcp_studio/servers/{id}` | Delete server |
| GET | `/mcs/mcp_studio/servers/{id}` | Get server |
| GET | `/mcs/mcp_studio/server/{id}/config` | Get server config |
| POST | `/mcs/mcp_studio/servers/{id}/execute` | Execute tool on MCP |
| GET | `/mcs/mcp_studio/servers/{id}/primitives` | List primitives |
| POST | `/mcs/mcp_studio/servers/{id}/primitives` | Update primitive status |
| POST | `/mcs/mcp_studio/servers/{id}/remove-primitives` | Remove primitives |
| POST | `/mcs/mcp_studio/primitives/add-primitives` | Add primitive |
| POST | `/mcs/mcp_studio/primitives/{id}/deactivate` | Deactivate primitive |
| POST/GET/DELETE | `/mcs/mcp_studio/servers/{id}/aiforce_primitives` | AIForce primitives |
| GET | `/mcs/mcp_studio/aiforce_primitives` | List all AF primitives |
