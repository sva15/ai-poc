"""
AIForce Agent POC — MCP Tool Server (FastMCP + Lambda + Kong)

Real FastMCP server using @mcp.tool() decorators.
Deployed on AWS Lambda behind Kong API Gateway.
Compatible with Kong Lambda plugin (aws_gateway_compatible, payload_version=1, proxy_integration).

Route: /dev/aiforce-mcp-tool

Dependencies: fastmcp, mcp[cli], requests
(No mangum needed — Kong event handling is built-in)
"""

from fastmcp import FastMCP
import json
import asyncio
import base64
from datetime import datetime, timezone

# ─── Create FastMCP Server ──────────────────────────────────────────

mcp = FastMCP("aiforce-poc-tools")

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "1.0.0"


# ─── Tool 1: Weather ────────────────────────────────────────────────

@mcp.tool()
def get_weather(city: str) -> str:
    """Get current weather for a city. Returns temperature in Celsius, weather condition, humidity, and wind speed.
    Supported cities: New York, London, Tokyo, Mumbai, Sydney, Paris, Dubai, Singapore.
    """
    weather_data = {
        "New York": {"temp": 22, "condition": "Partly Cloudy", "humidity": 65, "wind_kmh": 18},
        "London": {"temp": 15, "condition": "Rainy", "humidity": 80, "wind_kmh": 25},
        "Tokyo": {"temp": 28, "condition": "Sunny", "humidity": 55, "wind_kmh": 10},
        "Mumbai": {"temp": 32, "condition": "Humid", "humidity": 85, "wind_kmh": 12},
        "Sydney": {"temp": 20, "condition": "Clear", "humidity": 60, "wind_kmh": 22},
        "Paris": {"temp": 18, "condition": "Overcast", "humidity": 70, "wind_kmh": 15},
        "Dubai": {"temp": 38, "condition": "Hot and Sunny", "humidity": 30, "wind_kmh": 8},
        "Singapore": {"temp": 30, "condition": "Thunderstorms", "humidity": 90, "wind_kmh": 20},
    }
    data = weather_data.get(city, {"temp": 25, "condition": "Clear", "humidity": 50, "wind_kmh": 15})
    return json.dumps({
        "city": city,
        "temperature_celsius": data["temp"],
        "condition": data["condition"],
        "humidity_percent": data["humidity"],
        "wind_speed_kmh": data["wind_kmh"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# ─── Tool 2: Calculator ─────────────────────────────────────────────

@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression safely. Supports +, -, *, /, ** (power), and parentheses.
    Example: '(10 + 5) * 2' returns 30.
    """
    try:
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return json.dumps({"error": "Invalid characters in expression", "expression": expression})
        result = eval(expression)
        return json.dumps({"expression": expression, "result": round(result, 6)})
    except Exception as e:
        return json.dumps({"error": str(e), "expression": expression})


# ─── Tool 3: Company Info ───────────────────────────────────────────

@mcp.tool()
def get_company_info(company_name: str) -> str:
    """Get company information including sector, headquarters, employee count, revenue, and a brief description.
    Available companies: TechCorp, HealthPlus, GreenEnergy, FinanceHub.
    """
    companies = {
        "TechCorp": {
            "name": "TechCorp", "sector": "Technology",
            "headquarters": "San Francisco, CA", "founded": 2010,
            "employees": 5000, "revenue": "$1.2B",
            "description": "A leading technology company specializing in cloud computing and AI solutions for enterprise customers.",
        },
        "HealthPlus": {
            "name": "HealthPlus", "sector": "Healthcare",
            "headquarters": "Boston, MA", "founded": 2005,
            "employees": 8000, "revenue": "$3.5B",
            "description": "A healthcare technology company providing electronic health records and telemedicine platforms to hospitals.",
        },
        "GreenEnergy": {
            "name": "GreenEnergy", "sector": "Renewable Energy",
            "headquarters": "Austin, TX", "founded": 2015,
            "employees": 2000, "revenue": "$500M",
            "description": "A clean energy startup focused on solar panel manufacturing and battery storage solutions.",
        },
        "FinanceHub": {
            "name": "FinanceHub", "sector": "Financial Services",
            "headquarters": "New York, NY", "founded": 2008,
            "employees": 12000, "revenue": "$8B",
            "description": "A global financial services firm offering investment banking, wealth management, and trading platforms.",
        },
    }
    info = companies.get(company_name, {
        "name": company_name, "sector": "Unknown",
        "headquarters": "Not available",
        "description": f"No information available for {company_name}. Try: TechCorp, HealthPlus, GreenEnergy, or FinanceHub.",
    })
    return json.dumps(info)


# ─── Tool dispatch (maps tool name → direct function call) ──────────

TOOL_DISPATCH = {
    "get_weather": lambda args: get_weather(args.get("city", "Unknown")),
    "calculate": lambda args: calculate(args.get("expression", "0")),
    "get_company_info": lambda args: get_company_info(args.get("company_name", "Unknown")),
}


# ─── MCP Protocol Handling ──────────────────────────────────────────

def _get_tool_schemas():
    """Build MCP tool schemas. FastMCP registers tools via @mcp.tool(),
    we extract schemas from function signatures for the tools/list response."""
    return [
        {
            "name": "get_weather",
            "description": get_weather.__doc__.strip(),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Name of the city to get weather for."}
                },
                "required": ["city"]
            }
        },
        {
            "name": "calculate",
            "description": calculate.__doc__.strip(),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "The mathematical expression to evaluate."}
                },
                "required": ["expression"]
            }
        },
        {
            "name": "get_company_info",
            "description": get_company_info.__doc__.strip(),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "Name of the company to look up."}
                },
                "required": ["company_name"]
            }
        },
    ]


def handle_mcp_request(body):
    """Process a single MCP JSON-RPC request and return the response."""
    method = body.get("method", "")
    request_id = body.get("id")
    params = body.get("params", {})

    print(f"[MCP] method={method}, id={request_id}")

    # initialize — MCP handshake
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "aiforce-poc-tools", "version": SERVER_VERSION}
            }
        }

    # notifications — acknowledge silently
    if method in ("notifications/initialized", "initialized"):
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}

    # tools/list — return all registered tools
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": _get_tool_schemas()}
        }

    # tools/call — execute a tool
    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        handler = TOOL_DISPATCH.get(tool_name)
        if not handler:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
            }

        try:
            result_text = handler(arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}]
                }
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": f"Tool error: {str(e)}"}
            }

    # ping
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}

    # Unknown method
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }


# ─── Lambda Handler (Kong API Gateway v1 compatible) ────────────────

def lambda_handler(event, context):
    """
    AWS Lambda handler — works with Kong Lambda plugin:
      aws_gateway_compatible = true
      payload_version = 1
      proxy_integration = true

    Kong sends API Gateway v1 events with:
      httpMethod, path, headers, body, isBase64Encoded
    Lambda must return:
      statusCode, headers, body, isBase64Encoded
    """
    print(f"[MCP] Event: httpMethod={event.get('httpMethod')}, path={event.get('path')}")

    http_method = event.get("httpMethod", "GET")

    # Handle GET — simple health/info check
    if http_method == "GET":
        return api_response(200, {
            "status": "ok",
            "server": "aiforce-poc-tools",
            "version": SERVER_VERSION,
            "tools": ["get_weather", "calculate", "get_company_info"],
            "mcp_protocol": MCP_PROTOCOL_VERSION,
        })

    # Handle OPTIONS — CORS preflight
    if http_method == "OPTIONS":
        return api_response(200, {})

    # Only POST for MCP
    if http_method != "POST":
        return api_response(405, {"error": "Method not allowed. Use POST for MCP requests."})

    # Parse body
    body_str = event.get("body", "")
    if event.get("isBase64Encoded") and body_str:
        body_str = base64.b64decode(body_str).decode("utf-8")

    if not body_str:
        return api_response(400, {
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": "Empty request body"}
        })

    try:
        body = json.loads(body_str)
    except json.JSONDecodeError as e:
        return api_response(400, {
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
        })

    # Handle MCP JSON-RPC request
    result = handle_mcp_request(body)
    return api_response(200, result)


def api_response(status_code, body):
    """Build API Gateway v1 proxy integration response (Kong compatible)."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "body": json.dumps(body),
        "isBase64Encoded": False
    }
