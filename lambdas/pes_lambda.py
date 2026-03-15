"""
PES Lambda — Prompt Engineering Service
AWS Lambda handler for all PES prompt management operations.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.aiforce_client import PESClient


def get_client():
    """Initialize PES client from environment variables."""
    return PESClient(
        base_url=os.environ.get("AIFORCE_BASE_URL", "https://54.91.159.104"),
        auth_token=os.environ["AIFORCE_AUTH_TOKEN"]
    )


def lambda_handler(event, context):
    """
    Lambda handler — routes to PES operations based on event["action"].

    Supported actions:
        save_prompt, update_prompt, delete_prompt, list_prompts,
        get_prompt, generate_prompt, test_prompt, execute_prompt,
        get_metrics, list_datasets, upload_dataset,
        evaluate_prompt_dataset, get_evaluation_status,
        get_trace_logs, scan_compliance, get_compliance_status,
        health_check
    """
    action = event.get("action", "")
    payload = event.get("payload", {})
    client = get_client()

    actions = {
        # ── Prompt CRUD ──────────────────────────────────────────
        "save_prompt": lambda: client.save_prompt(
            name=payload["name"],
            user_prompt=payload["user_prompt"],
            lm_config_id=payload["lm_config_id"],
            system_prompt=payload.get("system_prompt", ""),
            publish_status=payload.get("publish_status", False),
            is_public=payload.get("is_public", False),
            version=payload.get("version", "v1.0"),
            variables=payload.get("variables"),
            lm_params=payload.get("lm_params"),
            examples=payload.get("examples"),
            mcp_enabled=payload.get("mcp_enabled", False),
            parent_prompt_id=payload.get("parent_prompt_id"),
            evaluation=payload.get("evaluation"),
        ),

        "update_prompt": lambda: client.update_prompt(
            prompt_id=payload["prompt_id"],
            **{k: v for k, v in payload.items() if k != "prompt_id"}
        ),

        "delete_prompt": lambda: client.delete_prompt(
            prompt_id=payload["prompt_id"]
        ),

        "list_prompts": lambda: client.list_prompts(
            page=payload.get("page", 1),
            page_size=payload.get("page_size", 10),
            search=payload.get("search"),
            is_public=payload.get("is_public"),
            publish_status=payload.get("publish_status"),
        ),

        "get_prompt": lambda: client.get_prompt_details(
            prompt_id=payload["prompt_id"]
        ),

        # ── Prompt Operations ────────────────────────────────────
        "generate_prompt": lambda: client.generate_prompt(request=payload),

        "test_prompt": lambda: client.test_prompt(
            prompt_id=payload["prompt_id"],
            user_prompt=payload["user_prompt"],
            lm_config_id=payload["lm_config_id"],
            system_prompt=payload.get("system_prompt", ""),
            lm_params=payload.get("lm_params"),
            variables=payload.get("variables"),
            mcp_enabled=payload.get("mcp_enabled", False),
        ),

        "execute_prompt": lambda: client.execute_prompt(request=payload),

        # ── Metrics & Datasets ───────────────────────────────────
        "get_metrics": lambda: client.get_metrics(
            applicability=payload.get("applicability", "prompt"),
            state=payload.get("state"),
            custom=payload.get("custom"),
            llm_based=payload.get("llm_based"),
        ),

        "list_datasets": lambda: client.list_datasets(
            applicability=payload.get("applicability")
        ),

        "upload_dataset": lambda: client.upload_dataset(
            file_path=payload["file_path"]
        ),

        # ── Evaluation ───────────────────────────────────────────
        "evaluate_prompt_dataset": lambda: client.evaluate_prompt_dataset(request=payload),

        "get_evaluation_status": lambda: client.get_evaluation_status(
            request_id=payload["request_id"]
        ),

        # ── Trace Logs ───────────────────────────────────────────
        "get_trace_logs": lambda: client.get_trace_logs(
            trace_id=payload["trace_id"]
        ),

        # ── Compliance ───────────────────────────────────────────
        "scan_compliance": lambda: client.scan_compliance(request=payload),

        "get_compliance_status": lambda: client.get_compliance_status(
            request_id=payload["request_id"]
        ),

        # ── Health ───────────────────────────────────────────────
        "health_check": lambda: client.health_check(),
    }

    if action not in actions:
        return {
            "statusCode": 400,
            "body": json.dumps({
                "error": f"Unknown action: {action}",
                "available_actions": list(actions.keys())
            })
        }

    result = actions[action]()

    return {
        "statusCode": result.get("status_code", 200) if result.get("success") else 500,
        "body": json.dumps(result, default=str)
    }
