"""
GCS Lambda — Governance, Risk & Compliance Service
AWS Lambda handler for metrics, validation, datasets, logs, testing, and compliance.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.aiforce_client import GCSClient


def get_client():
    return GCSClient(
        base_url=os.environ.get("AIFORCE_BASE_URL", "https://54.91.159.104"),
        auth_token=os.environ["AIFORCE_AUTH_TOKEN"]
    )


def lambda_handler(event, context):
    """
    Lambda handler — routes GCS operations.

    Supported actions:
        check_auth,
        list_metrics, update_metric_config, reset_metric_configs,
        create_custom_metric, list_custom_metrics, update_custom_metric,
        delete_custom_metric, create_and_install_packages, vulnerability_check,
        validate_prompt, validate_rag, validate_agent, get_evaluation_status,
        create_dataset, list_datasets, download_dataset_template,
        upload_dataset, get_dataset_items, get_dataset_item,
        update_dataset_item, delete_dataset_item, delete_dataset,
        create_trace, log_llm_call, log_output, log_embedding_search,
        add_event, get_trace, delete_trace, list_traces,
        test_prompt_evaluator, test_rag_evaluator, test_agent_evaluator,
        list_compliance_guidelines, scan_compliance, get_compliance_status,
        get_llm_configuration_proxy, health_check
    """
    action = event.get("action", "")
    payload = event.get("payload", {})
    client = get_client()

    actions = {
        # ── Registration ────────────────────────────────────────
        "check_auth": lambda: client.check_auth(),

        # ── Metric Configuration ────────────────────────────────
        "list_metrics": lambda: client.list_metrics(
            metrics_name=payload.get("metrics_name"),
            applicability=payload.get("applicability"),
            state=payload.get("state"),
            llm_based=payload.get("llm_based"),
            custom=payload.get("custom"),
            page=payload.get("page", 1),
            limit=payload.get("limit", 10),
        ),
        "update_metric_config": lambda: client.update_metric_config(
            metric_name=payload["metric_name"],
            applicability=payload["applicability"],
            config=payload["config"],
        ),
        "reset_metric_configs": lambda: client.reset_metric_configs(
            metric_names=payload["metric_names"]
        ),

        # ── Custom Metrics ──────────────────────────────────────
        "create_custom_metric": lambda: client.create_custom_metric(metric=payload),
        "list_custom_metrics": lambda: client.list_custom_metrics(
            metric_name=payload.get("metric_name"),
            applicability=payload.get("applicability"),
            llm_based=payload.get("llm_based"),
            state=payload.get("state"),
            status=payload.get("status"),
            page=payload.get("page", 1),
            limit=payload.get("limit", 10),
        ),
        "update_custom_metric": lambda: client.update_custom_metric(
            metric_name=payload["metric_name"],
            applicability=payload["applicability"],
            body=payload["body"],
        ),
        "delete_custom_metric": lambda: client.delete_custom_metric(
            metric_name=payload["metric_name"]
        ),
        "create_and_install_packages": lambda: client.create_and_install_packages(
            packages=payload["packages"],
            environment=payload.get("environment"),
        ),
        "vulnerability_check": lambda: client.vulnerability_check(
            script=payload["script"],
            packages=payload["packages"],
        ),

        # ── Validation ──────────────────────────────────────────
        "validate_prompt": lambda: client.validate_prompt(request=payload),
        "validate_rag": lambda: client.validate_rag(request=payload),
        "validate_agent": lambda: client.validate_agent(request=payload),
        "get_evaluation_status": lambda: client.get_evaluation_status(
            request_id=payload.get("request_id")
        ),

        # ── Dataset Management ──────────────────────────────────
        "create_dataset": lambda: client.create_dataset(
            name=payload["name"],
            description=payload.get("description", ""),
            use_case_type=payload.get("use_case_type", "prompt"),
        ),
        "list_datasets": lambda: client.list_datasets(
            applicability=payload.get("applicability"),
            use_case_type=payload.get("use_case_type"),
            page=payload.get("page"),
            limit=payload.get("limit"),
            time_filter=payload.get("time"),
            name=payload.get("name"),
        ),
        "download_dataset_template": lambda: client.download_dataset_template(
            use_case_type=payload["use_case_type"]
        ),
        "upload_dataset": lambda: client.upload_dataset(
            file_path=payload["file_path"],
            dataset_name=payload["dataset_name"],
            use_case_type=payload.get("use_case_type", "prompt"),
        ),
        "get_dataset_items": lambda: client.get_dataset_items(
            name=payload["name"],
            page=payload.get("page"),
            limit=payload.get("limit"),
        ),
        "get_dataset_item": lambda: client.get_dataset_item(item_id=payload["item_id"]),
        "update_dataset_item": lambda: client.update_dataset_item(
            item_id=payload["item_id"],
            data=payload["data"],
        ),
        "delete_dataset_item": lambda: client.delete_dataset_item(item_id=payload["item_id"]),
        "delete_dataset": lambda: client.delete_dataset(name=payload["name"]),

        # ── Logs & Observability ────────────────────────────────
        "create_trace": lambda: client.create_trace(
            name=payload["name"],
            session_id=payload.get("session_id"),
            metadata=payload.get("metadata"),
        ),
        "log_llm_call": lambda: client.log_llm_call(trace_data=payload),
        "log_output": lambda: client.log_output(trace_data=payload),
        "log_embedding_search": lambda: client.log_embedding_search(trace_data=payload),
        "add_event": lambda: client.add_event(event_data=payload),
        "get_trace": lambda: client.get_trace(trace_id=payload["trace_id"]),
        "delete_trace": lambda: client.delete_trace(trace_id=payload["trace_id"]),
        "list_traces": lambda: client.list_traces(
            limit=payload.get("limit", 10),
            page=payload.get("page", 1),
            name=payload.get("name"),
            session_id=payload.get("session_id"),
            environment=payload.get("environment"),
            hours=payload.get("hours"),
        ),

        # ── Testing Evaluators ──────────────────────────────────
        "test_prompt_evaluator": lambda: client.test_prompt_evaluator(request=payload),
        "test_rag_evaluator": lambda: client.test_rag_evaluator(request=payload),
        "test_agent_evaluator": lambda: client.test_agent_evaluator(request=payload),

        # ── Compliance ──────────────────────────────────────────
        "list_compliance_guidelines": lambda: client.list_compliance_guidelines(
            page=payload.get("page"),
            limit=payload.get("limit"),
        ),
        "scan_compliance": lambda: client.scan_compliance(request=payload),
        "get_compliance_status": lambda: client.get_compliance_status(
            request_id=payload.get("request_id")
        ),

        # ── G3S Proxy ───────────────────────────────────────────
        "get_llm_configuration_proxy": lambda: client.get_llm_configuration_proxy(
            config_id=payload.get("config_id")
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
