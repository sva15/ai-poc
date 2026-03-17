# Agent POC — Deployment Guide

## Architecture

```
AIForce MCS                  ALB                     Lambda
     |                        |                        |
     |-- POST /mcp/ -------> | /dev/aiforce-mcp-tool  |
     |                        |-- forward -----------> |
     |                        |                        | FastMCP handles MCP protocol
     |                        |                        | Returns tool results
     |                        |<- response ----------- |
     |<- MCP response ------- |                        |
```

---

## Step 1: Build the Deployment Package (ZIP)

Since FastMCP and mangum are external libraries, we need a ZIP package (not console paste).

### On your local machine (requires Python 3.12):

```bash
# Create a build directory
mkdir mcp-lambda-build
cd mcp-lambda-build

# Install dependencies into a package directory
pip install fastmcp mangum -t ./package

# Copy the Lambda code
cp ../agent-poc/lambda_function.py ./package/

# Create the ZIP
cd package
zip -r ../mcp-lambda.zip .
cd ..
```

### On Windows (PowerShell):

```powershell
# Create build directory
New-Item -ItemType Directory -Path mcp-lambda-build -Force
Set-Location mcp-lambda-build

# Install dependencies
pip install fastmcp mangum -t .\package

# Copy Lambda code
Copy-Item ..\agent-poc\lambda_function.py .\package\

# Create ZIP
Compress-Archive -Path .\package\* -DestinationPath .\mcp-lambda.zip -Force
```

This creates `mcp-lambda.zip` (~10-30 MB depending on dependencies).

---

## Step 2: Create Lambda Function

1. Go to **AWS Lambda Console** → **Create function**
2. **Function name**: `aiforce-mcp-tools`
3. **Runtime**: Python 3.12
4. **Architecture**: x86_64
5. Click **Create function**

---

## Step 3: Upload ZIP

1. In the Lambda function page, go to **Code** tab
2. Click **Upload from** → **.zip file**
3. Upload the `mcp-lambda.zip` file
4. Click **Save**

---

## Step 4: Configure Lambda

### Handler
Set handler to: `lambda_function.lambda_handler`

### Timeout
Set to **60 seconds** (Configuration → General configuration → Edit)

### Memory
Set to **256 MB** minimum (FastMCP + mangum need more memory than the previous POC)

### No environment variables needed
The MCP tool server is self-contained — no external API calls.

---

## Step 5: Configure ALB Target Group

1. Create a **Target Group** pointing to the Lambda function
2. Configure ALB listener rule:
   - **Path pattern**: `/dev/aiforce-mcp-tool/*`
   - **Forward to**: The Lambda target group

The final MCP endpoint URL will be:
```
http://<alb-url>/kong-api/dev/aiforce-mcp-tool/mcp/
```

---

## Step 6: Verify

Test the Lambda directly from the console with an ALB-style event:

```json
{
  "requestContext": {
    "elb": {
      "targetGroupArn": "arn:aws:elasticloadbalancing:region:123456789:targetgroup/my-tg/abc123"
    }
  },
  "httpMethod": "POST",
  "path": "/dev/aiforce-mcp-tool/mcp/",
  "headers": {
    "content-type": "application/json"
  },
  "body": "{\"jsonrpc\": \"2.0\", \"method\": \"initialize\", \"id\": 1, \"params\": {\"protocolVersion\": \"2024-11-05\", \"capabilities\": {}, \"clientInfo\": {\"name\": \"test\", \"version\": \"1.0\"}}}",
  "isBase64Encoded": false
}
```

Expected: HTTP 200 with MCP initialization response containing server info and tool capabilities.
