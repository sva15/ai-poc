"""
SGS Lambda — Security Guardrails Service
AWS Lambda handler for security scanning, group management, and master config.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.aiforce_client import SGSClient


def get_client():
    return SGSClient(
        base_url=os.environ.get("AIFORCE_BASE_URL", "https://54.91.159.104"),
        auth_token=os.environ["AIFORCE_AUTH_TOKEN"]
    )


def lambda_handler(event, context):
    """
    Lambda handler — routes SGS operations.

    Supported actions:
        get_token_context,
        get_master_control, set_master_control,
        register_security_group, list_security_groups,
        configure_security_group, get_security_group_config,
        delete_security_group,
        get_master_scanners, update_master_scanners,
        scan_prompt, scan_output,
        health_check
    """
    action = event.get("action", "")
    payload = event.get("payload", {})
    client = get_client()

    actions = {
        # ── Auth Debug ──────────────────────────────────────────
        "get_token_context": lambda: client.get_token_context(),

        # ── Master Control ──────────────────────────────────────
        "get_master_control": lambda: client.get_master_control(),
        "set_master_control": lambda: client.set_master_control(
            state=payload.get("state"),
            control_config=payload.get("control_config"),
        ),

        # ── Security Group CRUD ─────────────────────────────────
        "register_security_group": lambda: client.register_security_group(
            name=payload["name"],
            description=payload.get("description", ""),
        ),
        "list_security_groups": lambda: client.list_security_groups(
            state=payload.get("state"),
            include_master=payload.get("include_master", False),
            state_only=payload.get("state_only", False),
        ),
        "configure_security_group": lambda: client.configure_security_group(
            group_name=payload["group_name"],
            config=payload["config"],
        ),
        "get_security_group_config": lambda: client.get_security_group_config(
            group_name=payload["group_name"],
            view=payload.get("view", "effective"),
        ),
        "delete_security_group": lambda: client.delete_security_group(
            group_name=payload["group_name"]
        ),

        # ── Master Scanners ─────────────────────────────────────
        "get_master_scanners": lambda: client.get_master_scanners(),
        "update_master_scanners": lambda: client.update_master_scanners(
            config=payload
        ),

        # ── Scanning (Core) ─────────────────────────────────────
        "scan_prompt": lambda: client.scan_prompt(
            prompt_name=payload["prompt_name"],
            input_prompt=payload["input_prompt"],
            variables=payload.get("variables", {}),
            security_group=payload["security_group"],
        ),
        "scan_output": lambda: client.scan_output(
            prompt_name=payload["prompt_name"],
            output=payload["output"],
            prompt=payload["prompt"],
            security_group=payload["security_group"],
        ),

        # ── Health ──────────────────────────────────────────────
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
