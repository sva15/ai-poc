# Agent POC — Deployment Guide

## Architecture

```
AIForce MCS                Kong (ALB)                    Lambda
     |                        |                            |
     |-- MCP request -------> | /dev/aiforce-mcp-tool/mcp |
     |   (JSON-RPC over HTTP) |                            |
     |                        |-- Kong Lambda Plugin -----> |
     |                        |   aws_gateway_compatible    |
     |                        |   payload_version = 1       | FastMCP (streamable HTTP)
     |                        |   proxy_integration = true  | Mangum (ASGI → Lambda)
     |                        |                            |
     |                        |<-- API Gateway v1 resp --- |
     |<-- MCP response ------ |                            |
```

---

## Step 1: Build the ZIP Deployment Package

FastMCP and mangum are external libraries — you need a ZIP package.

### Windows (PowerShell):

```powershell
# Navigate to the agent-poc directory
cd C:\Users\svara\Downloads\aiforce-poc\agent-poc

# Clean previous build
if (Test-Path .\build) { Remove-Item -Recurse -Force .\build }

# Install dependencies into build folder
pip install fastmcp mangum "mcp[cli]" requests -t .\build\package

# Copy Lambda code into package
Copy-Item .\lambda_function.py .\build\package\

# Create ZIP
Set-Location .\build\package
Compress-Archive -Path .\* -DestinationPath ..\mcp-lambda.zip -Force
Set-Location ..\..

# The ZIP is at: agent-poc\build\mcp-lambda.zip
Write-Host "ZIP created at: build\mcp-lambda.zip"
```

### Linux/Mac:

```bash
cd agent-poc
rm -rf build && mkdir -p build/package
pip install fastmcp mangum "mcp[cli]" requests -t build/package/
cp lambda_function.py build/package/
cd build/package && zip -r ../mcp-lambda.zip . && cd ../..
```

---

## Step 2: Create Lambda Function

1. **AWS Lambda Console** → **Create function**
2. **Function name**: `aiforce-mcp-tools`
3. **Runtime**: Python 3.12
4. **Architecture**: x86_64
5. Click **Create function**

---

## Step 3: Upload ZIP

1. In the Lambda function page → **Code** tab
2. Click **Upload from** → **.zip file**
3. Upload `build/mcp-lambda.zip`
4. Click **Save**

---

## Step 4: Configure Lambda

| Setting | Value |
|---------|-------|
| **Handler** | `lambda_function.lambda_handler` |
| **Timeout** | 60 seconds |
| **Memory** | 256 MB |

No environment variables needed — the MCP tools are self-contained.

---

## Step 5: Kong Configuration

Your existing Kong setup:

| Setting | Value |
|---------|-------|
| ALB route | Forwards to Kong |
| Kong Service | Points to Lambda |
| Kong Route | `/dev/aiforce-mcp-tool` |
| Kong Lambda Plugin | `aws_gateway_compatible` = true |
| | `payload_version` = 1 |
| | `proxy_integration` = true |

### Important: Kong strip_path setting

This controls what path Lambda receives from Kong:

| Kong `strip_path` | Path Lambda receives | `api_gateway_base_path` in code |
|-------------------|---------------------|--------------------------------|
| `true` (default) | `/mcp` | `""` (empty — change the code) |
| `false` | `/dev/aiforce-mcp-tool/mcp` | `"/dev/aiforce-mcp-tool"` (current default) |

**If your Kong route has `strip_path=true`**, change line 119 in the Lambda code:
```python
# FROM:
lambda_handler = Mangum(app, lifespan="off", api_gateway_base_path="/dev/aiforce-mcp-tool")
# TO:
lambda_handler = Mangum(app, lifespan="off", api_gateway_base_path="")
```

---

## Step 6: Verify from Lambda Console

Test the Lambda directly from the Console with this test event:

```json
{
  "httpMethod": "POST",
  "path": "/dev/aiforce-mcp-tool/mcp",
  "headers": {
    "content-type": "application/json",
    "accept": "application/json, text/event-stream"
  },
  "body": "{\"jsonrpc\":\"2.0\",\"method\":\"initialize\",\"id\":1,\"params\":{\"protocolVersion\":\"2024-11-05\",\"capabilities\":{},\"clientInfo\":{\"name\":\"test\",\"version\":\"1.0\"}}}",
  "isBase64Encoded": false
}
```

Expected: HTTP 200 with MCP server info and capabilities.

For `strip_path=true`, change `"path"` to `"/mcp"`.

---

## Step 7: Verify via Kong (curl)

### Initialize
```bash
curl -X POST "http://YOUR_ALB_URL/kong-api/dev/aiforce-mcp-tool/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
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

### List Tools
```bash
curl -X POST "http://YOUR_ALB_URL/kong-api/dev/aiforce-mcp-tool/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 2,
    "params": {}
  }'
```

### Call a Tool
```bash
curl -X POST "http://YOUR_ALB_URL/kong-api/dev/aiforce-mcp-tool/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
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

---

## Troubleshooting

### "Empty reply from server"
1. **Check CloudWatch Logs** for the Lambda — look for errors
2. **Test Lambda directly** from Console first (Step 6) — if that works, the issue is in Kong/path
3. **Check `strip_path`** — most common issue. If Lambda Console test works but curl via Kong fails, it's a path mismatch
4. **Check `api_gateway_base_path`** — must match what Kong sends (see Step 5 table)

### Lambda Console test returns 404
- FastMCP serves at `/mcp` — make sure the `path` in your test event ends with `/mcp`
- Check if `api_gateway_base_path` is stripping too much or too little

### Lambda Console test returns 500
- Check CloudWatch for the Python stack trace
- Ensure the ZIP was built with Python 3.12 (same as Lambda runtime)

### Kong returns 502 Bad Gateway
- Lambda response format issue — mangum should handle this, but check logs
- Ensure `proxy_integration = true` in Kong plugin config
