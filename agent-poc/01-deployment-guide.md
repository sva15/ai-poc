# Agent POC — Deployment Guide

## Architecture

```
AIForce MCS                Kong (ALB)                Lambda
     |                        |                        |
     |-- MCP JSON-RPC -----> | /dev/aiforce-mcp-tool  |
     |   (initialize,        |                        |
     |    tools/list,         |-- Kong Lambda Plugin -> |
     |    tools/call)         |   (payload_version=1,  |
     |                        |    proxy_integration)   | Handles MCP protocol
     |                        |                        | Returns tool results
     |                        |<- API GW v1 response - |
     |<- MCP response ------- |                        |
```

**Kong Lambda Plugin Config**:
- `aws_gateway_compatible` = enabled
- `payload_version` = 1 (API Gateway REST v1 format)
- `proxy_integration` = enabled

---

## Step 1: Create Lambda Function

1. Go to **AWS Lambda Console** → **Create function**
2. **Function name**: `aiforce-mcp-tools`
3. **Runtime**: Python 3.12
4. **Architecture**: x86_64
5. Click **Create function**

---

## Step 2: Paste the Code

1. Open `lambda_function.py` from the `agent-poc/` directory
2. **Paste it directly** into the Lambda Console inline editor
3. Click **Deploy**

> **No ZIP needed.** This version uses only native Python (`json`, `datetime`). No external dependencies.

---

## Step 3: Configure Lambda

### Handler
Verify handler is set to: `lambda_function.lambda_handler`

### Timeout
Set to **30 seconds** (Configuration → General configuration → Edit)

### Memory
**128 MB** is sufficient (no external libraries)

---

## Step 4: Kong Gateway Configuration

Your existing Kong setup:
- **ALB route** → Kong
- **Kong Service** → with route `/dev/aiforce-mcp-tool`
- **Kong Lambda Plugin** on this service:
  - `aws_gateway_compatible` = true
  - `payload_version` = 1
  - `proxy_integration` = true

Make sure the Kong route's `strip_path` setting matches what the Lambda expects.

---

## Step 5: Verify with curl

### Test 1: Health Check (GET)
```bash
curl "http://YOUR_ALB_URL/kong-api/dev/aiforce-mcp-tool"
```

Expected:
```json
{
  "status": "ok",
  "server": "aiforce-poc-tools",
  "version": "1.0.0",
  "tools": ["get_weather", "calculate", "get_company_info"],
  "mcp_protocol": "2024-11-05"
}
```

### Test 2: MCP Initialize (POST)
```bash
curl -X POST "http://YOUR_ALB_URL/kong-api/dev/aiforce-mcp-tool" \
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

### Test 3: List Tools (POST)
```bash
curl -X POST "http://YOUR_ALB_URL/kong-api/dev/aiforce-mcp-tool" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 2,
    "params": {}
  }'
```

### Test 4: Call a Tool Directly (POST)
```bash
curl -X POST "http://YOUR_ALB_URL/kong-api/dev/aiforce-mcp-tool" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 3,
    "params": {
      "name": "get_weather",
      "arguments": {"city": "Tokyo"}
    }
  }'
```

Expected:
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"city\": \"Tokyo\", \"temperature_celsius\": 28, ...}"
      }
    ]
  }
}
```

---

## Troubleshooting

### "Empty reply from server"
- Check Lambda **CloudWatch Logs** for errors
- Verify Kong route `strip_path` setting
- Test Lambda directly from Console with this test event:

```json
{
  "httpMethod": "POST",
  "path": "/dev/aiforce-mcp-tool",
  "headers": {
    "content-type": "application/json"
  },
  "body": "{\"jsonrpc\":\"2.0\",\"method\":\"tools/list\",\"id\":1,\"params\":{}}",
  "isBase64Encoded": false
}
```

### Kong path issues
If Kong strips the path before forwarding, the Lambda receives `path: "/"` instead of `path: "/dev/aiforce-mcp-tool"`. This is fine — the Lambda handles all paths the same way.

### Response format
Lambda returns proper API Gateway v1 proxy integration format:
```json
{
  "statusCode": 200,
  "headers": {"Content-Type": "application/json", ...},
  "body": "...",
  "isBase64Encoded": false
}
```
This is what Kong's proxy_integration expects.
