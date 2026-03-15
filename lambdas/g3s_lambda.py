"""
G3S Lambda — GenAI Gateway & Guardrail Service
AWS Lambda handler for LLM config management, model calls, and consumption tracking.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.aiforce_client import G3SClient


def get_client():
    return G3SClient(
        base_url=os.environ.get("AIFORCE_BASE_URL", "https://54.91.159.104"),
        auth_token=os.environ["AIFORCE_AUTH_TOKEN"]
    )


def lambda_handler(event, context):
    """
    Lambda handler — routes G3S operations.

    Supported actions:
        llm_call, generate_embeddings,
        save_llm_config, list_llm_configs, get_llm_config, update_llm_config, delete_llm_config,
        save_embedding_config, list_embedding_configs, update_embedding_config, delete_embedding_config,
        save_speech_config, list_speech_configs, update_speech_config, delete_speech_config,
        install_packages, get_consumption, get_config_names, health_check
    """
    action = event.get("action", "")
    payload = event.get("payload", {})
    client = get_client()

    actions = {
        # ── LLM Calls ───────────────────────────────────────────
        "llm_call": lambda: client.llm_call(request=payload),
        "generate_embeddings": lambda: client.generate_embeddings(request=payload),

        # ── LLM Config CRUD ─────────────────────────────────────
        "save_llm_config": lambda: client.save_llm_config(config=payload),
        "list_llm_configs": lambda: client.list_llm_configs(
            page=payload.get("page", 1),
            page_size=payload.get("page_size", 10),
            search=payload.get("search"),
        ),
        "get_llm_config": lambda: client.get_llm_config(llm_id=payload["llm_id"]),
        "update_llm_config": lambda: client.update_llm_config(
            config_id=payload["config_id"],
            config={k: v for k, v in payload.items() if k != "config_id"},
        ),
        "delete_llm_config": lambda: client.delete_llm_config(config_id=payload["config_id"]),

        # ── Embedding Config CRUD ────────────────────────────────
        "save_embedding_config": lambda: client.save_embedding_config(config=payload),
        "list_embedding_configs": lambda: client.list_embedding_configs(
            page=payload.get("page", 1),
            page_size=payload.get("page_size", 10),
            search=payload.get("search"),
        ),
        "update_embedding_config": lambda: client.update_embedding_config(
            config_id=payload["config_id"],
            config={k: v for k, v in payload.items() if k != "config_id"},
        ),
        "delete_embedding_config": lambda: client.delete_embedding_config(
            config_id=payload["config_id"]
        ),

        # ── Speech Config CRUD ───────────────────────────────────
        "save_speech_config": lambda: client.save_speech_config(config=payload),
        "list_speech_configs": lambda: client.list_speech_configs(
            page=payload.get("page", 1),
            page_size=payload.get("page_size", 10),
            search=payload.get("search"),
        ),
        "update_speech_config": lambda: client.update_speech_config(
            config_id=payload["config_id"],
            config={k: v for k, v in payload.items() if k != "config_id"},
        ),
        "delete_speech_config": lambda: client.delete_speech_config(
            config_id=payload["config_id"]
        ),

        # ── Packages ────────────────────────────────────────────
        "install_packages": lambda: client.install_packages(request=payload),

        # ── Consumption / Cost Tracking ──────────────────────────
        "get_consumption": lambda: client.get_consumption(
            project_id=payload.get("project_id"),
            config_name=payload.get("config_name"),
            date_filter=payload.get("date_filter"),
            custom_start=payload.get("custom_start"),
            custom_end=payload.get("custom_end"),
        ),
        "get_config_names": lambda: client.get_config_names(
            lm_type=payload.get("lm_type", 1)
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
