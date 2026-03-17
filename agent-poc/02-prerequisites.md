# Agent POC — Prerequisites & Setup

## Overview

After deploying the MCP Lambda and configuring ALB, follow these steps to:
1. Verify MCP server health
2. Register MCP server in AIForce MCS
3. Discover and activate tools
4. Get required IDs for agent creation
5. Create a single agent in AMS with MCP tools
6. Execute the agent

Replace `YOUR_ALB_URL` with your actual ALB endpoint (e.g., `http://alb-url/kong-api`).
Replace `YOUR_AUTH_TOKEN` with your AIForce Bearer token.
Replace `AIFORCE_URL` with `https://54.91.159.104`.

---

## Step 1: Health Check Services

```bash
# AMS Health
curl -k "AIFORCE_URL/check_health" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"

# AES Health
curl -k "AIFORCE_URL/check_health" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"

# MCS Health
curl -k "AIFORCE_URL/check_health" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

---

## Step 2: Verify MCP Lambda is Working

Send an MCP `initialize` request to your ALB endpoint:

```bash
curl -X POST "YOUR_ALB_URL/dev/aiforce-mcp-tool/mcp/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "id": 1,
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test", "version": "1.0"}
    }
  }'
```

Expected: JSON response with server info and capabilities.

Then list tools:

```bash
curl -X POST "YOUR_ALB_URL/dev/aiforce-mcp-tool/mcp/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 2,
    "params": {}
  }'
```

Expected: List of 3 tools (get_weather, calculate, get_company_info).

---

## Step 3: Register MCP Server in AIForce MCS

```bash
curl -k -X POST "AIFORCE_URL/mcs/mcp_studio/test-connection" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "poc-mcp-tools",
    "server_type": 2,
    "config_type": 2,
    "server_id": "poc-mcp-tools",
    "server_url": "YOUR_ALB_URL/dev/aiforce-mcp-tool",
    "auth_type": 1
  }'
```

If the connection is successful, register the server:

```bash
curl -k -X POST "AIFORCE_URL/mcs/mcp_studio/servers" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "poc-mcp-tools",
    "description": "POC external MCP server with weather, calculator, and company info tools",
    "server_type": 2,
    "config_type": 2,
    "server_id": "poc-mcp-tools",
    "server_url": "YOUR_ALB_URL/dev/aiforce-mcp-tool",
    "auth_type": 1,
    "is_active": true
  }'
```

Note down the `mcp_id` from the response.

Verify registration:

```bash
curl -k "AIFORCE_URL/mcs/mcp_studio/servers" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

---

## Step 4: Discover MCP Tools (Primitives)

After registering, MCS auto-discovers the tools. Verify:

```bash
curl -k "AIFORCE_URL/mcs/mcp_studio/servers/{mcp_id}/primitives" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

Replace `{mcp_id}` with the ID from Step 3.

Expected: 3 primitives of type=1 (Tool):
- `get_weather`
- `calculate`
- `get_company_info`

If tools need activation:

```bash
curl -k -X POST "AIFORCE_URL/mcs/mcp_studio/servers/{mcp_id}/primitives?status=active" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "get_weather", "primitive_type": 1}'
```

Repeat for each tool.

---

## Step 5: Get Dropdown Values for Agent Creation

```bash
# Get available frameworks, design patterns, LLM models
curl -k "AIFORCE_URL/ams/agentic-studio/dropdowns?name=frameworks" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"

curl -k "AIFORCE_URL/ams/agentic-studio/dropdowns?name=design_patterns" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"

curl -k "AIFORCE_URL/ams/agentic-studio/dropdowns?name=llm_models" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

Note down the IDs you want to use (framework_id, design_pattern_id, llm_model_id).

Also list available security groups:

```bash
curl -k "AIFORCE_URL/ams/agentic-studio/list_security_group" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

---

## Step 6: Create Agent with MCP Tools

```bash
curl -k -X POST "AIFORCE_URL/ams/agentic-studio/agents" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "poc-mcp-agent",
    "description": "A POC agent that uses external MCP tools (weather, calculator, company info) to answer user questions",
    "llm_model_id": 1,
    "mcp_enabled": true,
    "publish_status": "Draft"
  }'
```

Note down the `agent_id` from the response.

> **Note**: You may also need to pass `framework_id`, `design_pattern_id`, `security_group_id`, or `tool_ids` depending on what the dropdowns return. Adjust after checking Step 5 results.

Verify:

```bash
curl -k "AIFORCE_URL/ams/agentic-studio/agents/{agent_id}" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

---

## Step 7: Execute Agent

### Test 1: Weather Question
```bash
curl -k -X POST "AIFORCE_URL/ams/agentic-studio/agent-execution" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": AGENT_ID,
    "input": "What is the current weather in Tokyo?"
  }'
```

Expected: Agent calls `get_weather("Tokyo")` → returns temperature, condition, humidity.

### Test 2: Calculator
```bash
curl -k -X POST "AIFORCE_URL/ams/agentic-studio/agent-execution" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": AGENT_ID,
    "input": "Calculate (150 * 3.14) + (200 / 4)"
  }'
```

Expected: Agent calls `calculate("(150 * 3.14) + (200 / 4)")` → returns 521.0.

### Test 3: Company Info
```bash
curl -k -X POST "AIFORCE_URL/ams/agentic-studio/agent-execution" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": AGENT_ID,
    "input": "Tell me about TechCorp - their sector, headquarters, and what they do."
  }'
```

Expected: Agent calls `get_company_info("TechCorp")` → returns company profile.

### Test 4: Multi-Tool Question
```bash
curl -k -X POST "AIFORCE_URL/ams/agentic-studio/agent-execution" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": AGENT_ID,
    "input": "What is the weather in Mumbai and how many employees does HealthPlus have?"
  }'
```

Expected: Agent calls both `get_weather("Mumbai")` and `get_company_info("HealthPlus")`.

---

## Step 8: View Trace Logs

After execution, use the `trace_id` from the response:

```bash
curl -k "AIFORCE_URL/ams/agentic-studio/trace/logs/{trace_id}" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

This shows:
- What the agent reasoned about
- Which MCP tools it called
- Tool parameters and results
- Final response generation

---

## Quick Reference — IDs to Collect

| Item | Where | ID Field |
|------|-------|----------|
| MCP Server | Step 3 response | `mcp_id` |
| LLM Model | Step 5 dropdowns | `llm_model_id` |
| Framework | Step 5 dropdowns | `framework_id` |
| Design Pattern | Step 5 dropdowns | `design_pattern_id` |
| Security Group | Step 5 list | `security_group_id` |
| Agent | Step 6 response | `agent_id` |
| Trace | Step 7 response | `trace_id` |
