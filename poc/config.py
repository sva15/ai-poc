"""
POC Configuration
Contains all settings for the AIForce POC.
Update these values with your actual credentials before running.
"""

import os

# ── AIForce Platform ─────────────────────────────────────────────────
AIFORCE_BASE_URL = os.environ.get("AIFORCE_BASE_URL", "https://54.91.159.104")
AIFORCE_AUTH_TOKEN = os.environ.get("AIFORCE_AUTH_TOKEN", "YOUR_TOKEN_HERE")

# ── AWS Bedrock (Direct Calls) ──────────────────────────────────────
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

# ── LLM Parameters ──────────────────────────────────────────────────
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2048

# ── SGS Security Group ──────────────────────────────────────────────
SECURITY_GROUP_NAME = os.environ.get("SECURITY_GROUP_NAME", "poc-security-group")

# ── Pricing (per 1000 tokens) ───────────────────────────────────────
# Update these based on your AWS Bedrock pricing
MODEL_PRICING = {
    "anthropic.claude-3-sonnet-20240229-v1:0": {
        "input_cost_per_1k": 0.003,      # $3.00 per 1M input tokens
        "output_cost_per_1k": 0.015,     # $15.00 per 1M output tokens
    },
    "anthropic.claude-3-haiku-20240307-v1:0": {
        "input_cost_per_1k": 0.00025,    # $0.25 per 1M input tokens
        "output_cost_per_1k": 0.00125,   # $1.25 per 1M output tokens
    },
    "anthropic.claude-3-5-sonnet-20241022-v2:0": {
        "input_cost_per_1k": 0.003,      # $3.00 per 1M input tokens
        "output_cost_per_1k": 0.015,     # $15.00 per 1M output tokens
    },
    "amazon.titan-text-express-v1": {
        "input_cost_per_1k": 0.0002,
        "output_cost_per_1k": 0.0006,
    },
    # Add more models as needed
    "default": {
        "input_cost_per_1k": 0.003,
        "output_cost_per_1k": 0.015,
    }
}


def get_pricing(model_id: str) -> dict:
    """Get pricing for a specific model, falling back to default."""
    return MODEL_PRICING.get(model_id, MODEL_PRICING["default"])


# ── G3S LLM Config ID (set after saving config via G3S) ─────────────
# This is the config_id returned by G3S when you register a model.
# The POC setup phase will save a config and store the ID here.
G3S_LLM_CONFIG_ID = os.environ.get("G3S_LLM_CONFIG_ID", None)

# ── Prompt Names (Domain prefixes for organization) ──────────────────
PROMPT_DOMAIN_PREFIX = os.environ.get("PROMPT_DOMAIN_PREFIX", "poc")

# ── GCS Trace Settings ──────────────────────────────────────────────
TRACE_ENVIRONMENT = os.environ.get("TRACE_ENVIRONMENT", "development")
