"""
Direct Bedrock Client
Calls AWS Bedrock directly via boto3 — bypasses G3S gateway.
Captures full token usage and calculates cost.
"""

import json
import time
import logging

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class BedrockClient:
    """Direct AWS Bedrock client with token tracking and cost calculation."""

    def __init__(self, region: str = "us-east-1", model_id: str = None,
                 pricing: dict = None):
        """
        Args:
            region: AWS region
            model_id: Default Bedrock model ID
            pricing: Dict with input_cost_per_1k and output_cost_per_1k
        """
        self.region = region
        self.model_id = model_id
        self.pricing = pricing or {"input_cost_per_1k": 0.003, "output_cost_per_1k": 0.015}

        self.client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region
        )

    def invoke_model(self, user_prompt: str, system_prompt: str = "",
                     temperature: float = 0.7, max_tokens: int = 2048,
                     model_id: str = None) -> dict:
        """
        Call Bedrock Claude model directly.

        Returns:
            dict with: response, input_tokens, output_tokens, cost,
                       latency_ms, model_id, success, error
        """
        model = model_id or self.model_id
        start_time = time.time()

        try:
            # Build Claude messages format
            messages = [{"role": "user", "content": user_prompt}]

            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system_prompt:
                request_body["system"] = system_prompt

            logger.info(f"Calling Bedrock model: {model}")

            response = self.client.invoke_model(
                modelId=model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )

            # Parse response
            response_body = json.loads(response["body"].read())
            latency_ms = int((time.time() - start_time) * 1000)

            # Extract token usage
            usage = response_body.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            total_tokens = input_tokens + output_tokens

            # Calculate cost
            input_cost = (input_tokens / 1000) * self.pricing["input_cost_per_1k"]
            output_cost = (output_tokens / 1000) * self.pricing["output_cost_per_1k"]
            total_cost = input_cost + output_cost

            # Extract response text
            content = response_body.get("content", [])
            response_text = ""
            for block in content:
                if block.get("type") == "text":
                    response_text += block.get("text", "")

            result = {
                "success": True,
                "response": response_text,
                "model_id": model,
                "stop_reason": response_body.get("stop_reason", ""),

                # Token usage
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,

                # Cost breakdown
                "input_cost_usd": round(input_cost, 6),
                "output_cost_usd": round(output_cost, 6),
                "total_cost_usd": round(total_cost, 6),

                # Performance
                "latency_ms": latency_ms,

                # Pricing used
                "pricing": self.pricing,

                "error": None,
            }

            logger.info(
                f"Bedrock response: {input_tokens} input + {output_tokens} output tokens "
                f"= ${total_cost:.6f} in {latency_ms}ms"
            )

            return result

        except ClientError as e:
            latency_ms = int((time.time() - start_time) * 1000)
            error_code = e.response["Error"]["Code"]
            error_msg = e.response["Error"]["Message"]
            logger.error(f"Bedrock error: {error_code} - {error_msg}")

            return {
                "success": False,
                "response": None,
                "model_id": model,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "input_cost_usd": 0,
                "output_cost_usd": 0,
                "total_cost_usd": 0,
                "latency_ms": latency_ms,
                "pricing": self.pricing,
                "error": f"{error_code}: {error_msg}",
            }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Unexpected error calling Bedrock: {e}")

            return {
                "success": False,
                "response": None,
                "model_id": model,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "input_cost_usd": 0,
                "output_cost_usd": 0,
                "total_cost_usd": 0,
                "latency_ms": latency_ms,
                "pricing": self.pricing,
                "error": str(e),
            }

    def invoke_with_conversation(self, messages: list, system_prompt: str = "",
                                  temperature: float = 0.7, max_tokens: int = 2048,
                                  model_id: str = None) -> dict:
        """
        Call Bedrock with a full conversation history.

        Args:
            messages: List of {role, content} dicts (user/assistant turns)
            system_prompt: System instructions
            temperature: LLM temperature
            max_tokens: Max output tokens
            model_id: Override model

        Returns:
            Same format as invoke_model()
        """
        model = model_id or self.model_id
        start_time = time.time()

        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages,
            }

            if system_prompt:
                request_body["system"] = system_prompt

            response = self.client.invoke_model(
                modelId=model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )

            response_body = json.loads(response["body"].read())
            latency_ms = int((time.time() - start_time) * 1000)

            usage = response_body.get("usage", {})
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)

            input_cost = (input_tokens / 1000) * self.pricing["input_cost_per_1k"]
            output_cost = (output_tokens / 1000) * self.pricing["output_cost_per_1k"]

            content = response_body.get("content", [])
            response_text = "".join(
                block.get("text", "") for block in content if block.get("type") == "text"
            )

            return {
                "success": True,
                "response": response_text,
                "model_id": model,
                "stop_reason": response_body.get("stop_reason", ""),
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "input_cost_usd": round(input_cost, 6),
                "output_cost_usd": round(output_cost, 6),
                "total_cost_usd": round(input_cost + output_cost, 6),
                "latency_ms": latency_ms,
                "pricing": self.pricing,
                "error": None,
            }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "response": None,
                "model_id": model,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "input_cost_usd": 0,
                "output_cost_usd": 0,
                "total_cost_usd": 0,
                "latency_ms": latency_ms,
                "pricing": self.pricing,
                "error": str(e),
            }
