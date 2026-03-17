"""
AIForce Agent POC — MCP Tool Server (Lambda + ALB)

FastMCP server with HTTP transport, deployed on AWS Lambda behind ALB.
Route: /dev/aiforce-mcp-tool
MCP endpoint: /dev/aiforce-mcp-tool/mcp/

Tools:
  - get_weather(city)        : Returns weather data for a city
  - calculate(expression)    : Evaluates a math expression
  - get_company_info(company): Returns company profile data
"""

from fastmcp import FastMCP
from mangum import Mangum
import json
from datetime import datetime, timezone

# ─── Create MCP Server ──────────────────────────────────────────────

mcp = FastMCP(
    "aiforce-poc-tools",
    stateless_http=True,
)


# ─── Tool 1: Weather ────────────────────────────────────────────────

@mcp.tool()
def get_weather(city: str) -> str:
    """Get current weather for a city. Returns temperature in Celsius, weather condition, humidity, and wind speed."""
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
    """Evaluate a mathematical expression safely. Supports +, -, *, /, ** (power), and parentheses. Example: '(10 + 5) * 2'"""
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
    """Get company information including sector, headquarters, employee count, and a brief description."""
    companies = {
        "TechCorp": {
            "name": "TechCorp",
            "sector": "Technology",
            "headquarters": "San Francisco, CA",
            "founded": 2010,
            "employees": 5000,
            "revenue": "$1.2B",
            "description": "A leading technology company specializing in cloud computing and AI solutions for enterprise customers.",
        },
        "HealthPlus": {
            "name": "HealthPlus",
            "sector": "Healthcare",
            "headquarters": "Boston, MA",
            "founded": 2005,
            "employees": 8000,
            "revenue": "$3.5B",
            "description": "A healthcare technology company providing electronic health records and telemedicine platforms to hospitals.",
        },
        "GreenEnergy": {
            "name": "GreenEnergy",
            "sector": "Renewable Energy",
            "headquarters": "Austin, TX",
            "founded": 2015,
            "employees": 2000,
            "revenue": "$500M",
            "description": "A clean energy startup focused on solar panel manufacturing and battery storage solutions.",
        },
        "FinanceHub": {
            "name": "FinanceHub",
            "sector": "Financial Services",
            "headquarters": "New York, NY",
            "founded": 2008,
            "employees": 12000,
            "revenue": "$8B",
            "description": "A global financial services firm offering investment banking, wealth management, and trading platforms.",
        },
    }
    info = companies.get(company_name, {
        "name": company_name,
        "sector": "Unknown",
        "headquarters": "Not available",
        "description": f"No detailed information available for {company_name}. Try: TechCorp, HealthPlus, GreenEnergy, or FinanceHub.",
    })
    return json.dumps(info)


# ─── ASGI App + Lambda Handler ──────────────────────────────────────

app = mcp.streamable_http_app()

# Mangum adapts ASGI app for Lambda behind ALB
# api_gateway_base_path strips the ALB route prefix
lambda_handler = Mangum(app, api_gateway_base_path="/dev/aiforce-mcp-tool")
