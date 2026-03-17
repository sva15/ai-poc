"""
AIForce Agent POC — MCP Tool Server (Lambda + Kong + ALB)

MCP server that handles JSON-RPC protocol directly.
Works with Kong Lambda plugin (aws_gateway_compatible, payload_version=1, proxy_integration).

Route: /dev/aiforce-mcp-tool
No external dependencies — pure native Python.

Tools:
  - get_weather(city)          : Returns weather data for a city
  - calculate(expression)      : Evaluates a math expression
  - get_company_info(company)  : Returns company profile data
"""

import json
from datetime import datetime, timezone


# ─── MCP Protocol Constants ─────────────────────────────────────────

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "aiforce-poc-tools"
SERVER_VERSION = "1.0.0"


# ─── Tool Definitions (MCP Schema) ──────────────────────────────────

TOOLS = [
    {
        "name": "get_weather",
        "description": "Get current weather for a city. Returns temperature in Celsius, weather condition, humidity, and wind speed.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "Name of the city to get weather for. Supported: New York, London, Tokyo, Mumbai, Sydney, Paris, Dubai, Singapore."
                }
            },
            "required": ["city"]
        }
    },
    {
        "name": "calculate",
        "description": "Evaluate a mathematical expression safely. Supports +, -, *, /, ** (power), and parentheses. Example: '(10 + 5) * 2'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate."
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "get_company_info",
        "description": "Get company information including sector, headquarters, employee count, and a brief description. Available: TechCorp, HealthPlus, GreenEnergy, FinanceHub.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "Name of the company to look up."
                }
            },
            "required": ["company_name"]
        }
    }
]


# ─── Tool Implementations ───────────────────────────────────────────

def tool_get_weather(city):
    """Get weather for a city."""
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


def tool_calculate(expression):
    """Evaluate a math expression."""
    try:
        allowed = set("0123456789+-*/.() ")
        if not all(c in allowed for c in expression):
            return json.dumps({"error": "Invalid characters in expression", "expression": expression})
        result = eval(expression)
        return json.dumps({"expression": expression, "result": round(result, 6)})
    except Exception as e:
        return json.dumps({"error": str(e), "expression": expression})


def tool_get_company_info(company_name):
    """Get company information."""
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


# Tool dispatch map
TOOL_HANDLERS = {
    "get_weather": lambda args: tool_get_weather(args.get("city", "Unknown")),
    "calculate": lambda args: tool_calculate(args.get("expression", "0")),
    "get_company_info": lambda args: tool_get_company_info(args.get("company_name", "Unknown")),
}


# ─── MCP Protocol Handlers ──────────────────────────────────────────

def handle_initialize(request_id, params):
    """Handle MCP initialize handshake."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {"listChanged": False}
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION
            }
        }
    }


def handle_tools_list(request_id, params):
    """Handle tools/list — return all available tools."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": TOOLS
        }
    }


def handle_tools_call(request_id, params):
    """Handle tools/call — execute a specific tool."""
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Tool not found: {tool_name}"
            }
        }

    try:
        result_text = handler(arguments)
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {"type": "text", "text": result_text}
                ]
            }
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32000,
                "message": f"Tool execution error: {str(e)}"
            }
        }


def handle_ping(request_id, params):
    """Handle ping."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {}
    }


# Method dispatch map
METHOD_HANDLERS = {
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
    "ping": handle_ping,
}

# Notification methods (no response expected)
NOTIFICATION_METHODS = {"notifications/initialized", "initialized"}


# ─── Lambda Handler ─────────────────────────────────────────────────

def lambda_handler(event, context):
    """
    AWS Lambda handler for MCP server.
    Works with Kong Lambda plugin (aws_gateway_compatible, payload_version=1, proxy_integration).

    Kong sends API Gateway v1 format:
    {
        "httpMethod": "POST",
        "path": "/dev/aiforce-mcp-tool",
        "headers": {...},
        "body": "{\"jsonrpc\": \"2.0\", ...}",
        ...
    }
    """
    print(f"[MCP] Event received: httpMethod={event.get('httpMethod')}, path={event.get('path')}")

    http_method = event.get("httpMethod", "GET")
    path = event.get("path", "/")

    # Health check / GET requests
    if http_method == "GET":
        return api_response(200, {
            "status": "ok",
            "server": SERVER_NAME,
            "version": SERVER_VERSION,
            "tools": [t["name"] for t in TOOLS],
            "mcp_protocol": MCP_PROTOCOL_VERSION,
        })

    # Only POST is valid for MCP
    if http_method != "POST":
        return api_response(405, {"error": "Method not allowed. Use POST for MCP requests."})

    # Parse body
    body = event.get("body", "")
    if event.get("isBase64Encoded"):
        import base64
        body = base64.b64decode(body).decode("utf-8")

    if not body:
        return api_response(400, {"error": "Empty request body"})

    try:
        request = json.loads(body)
    except json.JSONDecodeError as e:
        print(f"[MCP] JSON parse error: {e}")
        return api_response(400, {"jsonrpc": "2.0", "error": {"code": -32700, "message": f"Parse error: {str(e)}"}})

    print(f"[MCP] Method: {request.get('method')}, ID: {request.get('id')}")

    # Handle JSON-RPC request
    method = request.get("method", "")
    request_id = request.get("id")
    params = request.get("params", {})

    # Notifications (no response expected, but we return 202 for Kong)
    if method in NOTIFICATION_METHODS:
        print(f"[MCP] Notification: {method}")
        return api_response(200, {"jsonrpc": "2.0", "id": request_id, "result": {}})

    # Dispatch to handler
    handler = METHOD_HANDLERS.get(method)
    if not handler:
        print(f"[MCP] Unknown method: {method}")
        return api_response(200, {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        })

    result = handler(request_id, params)
    print(f"[MCP] Response for {method}: success")
    return api_response(200, result)


def api_response(status_code, body):
    """Build API Gateway v1 proxy integration response for Kong."""
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
