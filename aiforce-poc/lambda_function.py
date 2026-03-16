"""
AIForce POC — Simple Lambda Function
Demonstrates: PES → SGS Input Scan → Bedrock → SGS Output Scan → GCS Trace → G3S Cost

No external dependencies — uses only urllib (native) and boto3 (built-in on Lambda).
"""

import json
import ssl
import time
import os
import urllib.request
import urllib.error
import urllib.parse
import uuid
from datetime import datetime

import boto3

# ─── Configuration from Environment Variables ────────────────────────
BASE_URL = os.environ.get("AIFORCE_BASE_URL", "https://54.91.159.104")
AUTH_TOKEN = os.environ.get("AIFORCE_AUTH_TOKEN", "")
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
SECURITY_GROUP = os.environ.get("SECURITY_GROUP", "poc-security-group")

# Model pricing (per 1K tokens) — update as needed
PRICING = {
    "anthropic.claude-3-haiku-20240307-v1:0": {"input": 0.00025, "output": 0.00125},
    "anthropic.claude-3-sonnet-20240229-v1:0": {"input": 0.003, "output": 0.015},
    "anthropic.claude-3-5-sonnet-20240620-v1:0": {"input": 0.003, "output": 0.015},
    "amazon.titan-text-express-v1": {"input": 0.0002, "output": 0.0006},
}

# SSL context for self-signed certs
SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


# ─── HTTP Helper (native urllib) ─────────────────────────────────────

def api_call(method, path, body=None, content_type="application/json"):
    """Make an HTTP call to AIForce services. Returns parsed JSON or error dict."""
    url = f"{BASE_URL}{path}"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Accept": "application/json",
    }

    data = None
    if body is not None:
        if content_type == "application/json":
            data = json.dumps(body).encode("utf-8")
        elif content_type == "application/x-www-form-urlencoded":
            data = urllib.parse.urlencode(body).encode("utf-8")
        headers["Content-Type"] = content_type

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30, context=SSL_CTX) as resp:
            resp_body = resp.read().decode("utf-8").strip()
            try:
                parsed = json.loads(resp_body) if resp_body else {}
            except json.JSONDecodeError:
                parsed = resp_body  # return raw string if not valid JSON
            return {"success": True, "status": resp.getcode(), "data": parsed}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            err_data = json.loads(err_body)
        except Exception:
            err_data = err_body
        return {"success": False, "status": e.code, "error": err_data}
    except Exception as e:
        return {"success": False, "status": 0, "error": str(e)}


# ─── Service Functions ───────────────────────────────────────────────

def get_prompt(prompt_id):
    """Step 1: Retrieve prompt from PES by ID."""
    print(f"[PES] Getting prompt details for ID: {prompt_id}")
    result = api_call("GET", f"/pes/prompt_studio/get_prompt_details/{prompt_id}")
    if result["success"]:
        raw = result["data"]
        # API may wrap in {"data": ...} — unwrap it
        data = raw.get("data", raw) if isinstance(raw, dict) else raw
        # data could be a list (e.g., [{...}]) or a dict
        if isinstance(data, list):
            data = data[0] if data else {}
        print(f"[PES] ✅ Retrieved prompt: {data.get('name', 'unknown')}")
        return data
    else:
        print(f"[PES] ❌ Failed: {result.get('error')}")
        return None


def substitute_variables(template, variables):
    """Step 2: Replace {{variable}} placeholders in the prompt."""
    resolved = template
    for key, value in variables.items():
        resolved = resolved.replace("{{" + key + "}}", str(value))
    print(f"[VARS] ✅ Substituted {len(variables)} variables")
    return resolved


def scan_input(prompt_name, input_prompt, variables, security_group):
    """Step 3: Scan input prompt via SGS before calling Bedrock."""
    print(f"[SGS] Scanning input prompt...")
    result = api_call("POST", "/sgs/scan/prompt", body={
        "prompt_name": prompt_name,
        "input_prompt": input_prompt,
        "variables": variables,
        "security_group": security_group,
    })
    if result["success"]:
        data = result["data"].get("data", result["data"])
        is_safe = data.get("is_safe", True)
        is_redacted = data.get("is_redacted", False)
        print(f"[SGS] ✅ Input scan complete — safe={is_safe}, redacted={is_redacted}")
        return data
    else:
        print(f"[SGS] ⚠️ Input scan failed: {result.get('error')}")
        return {"is_safe": True, "scan_error": result.get("error")}


def test_prompt_via_pes(user_prompt, system_prompt, variables, lm_config_id=1):
    """Test a prompt dynamically targeting PES /test_prompt without saving it."""
    print(f"[PES] Testing prompt dynamically...")
    
    # PES test_prompt expects variables as a list of objects, not a simple dict
    formatted_vars = []
    if variables:
        for k, v in variables.items():
            formatted_vars.append({
                "name": k,
                "value": v,
                "isFileInput": False,
                "isRequired": True
            })

    payload = {
        "user_prompt": user_prompt,
        "system_prompt": system_prompt or "",
        "varriables": json.dumps(formatted_vars),
        "lm_config_id": lm_config_id,
        "promptId": 0,  # 0 indicates unsaved
    }
    result = api_call("POST", "/pes/prompt_studio/test_prompt", body=payload, content_type="application/x-www-form-urlencoded")
    if result["success"]:
        data = result["data"]
        # Response might be nested data
        if isinstance(data, dict):
            data = data.get("data", data)
        print(f"[PES] ✅ Prompt test execution complete")
        return data
    else:
        print(f"[PES] ⚠️ Prompt test failed: {result.get('error')}")
        return {"error": result.get("error")}


def call_bedrock(user_prompt, system_prompt=""):
    """Step 4: Call Bedrock directly via boto3."""
    print(f"[BEDROCK] Calling model: {BEDROCK_MODEL_ID}")
    client = boto3.client("bedrock-runtime", region_name=AWS_REGION)

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "temperature": 0.7,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    if system_prompt:
        body["system"] = system_prompt

    start = time.time()
    try:
        response = client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(body),
            contentType="application/json",
            accept="application/json",
        )
        latency_ms = int((time.time() - start) * 1000)
        result = json.loads(response["body"].read())

        # Extract response text
        output_text = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                output_text += block["text"]

        # Token usage
        usage = result.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        # Cost calculation
        pricing = PRICING.get(BEDROCK_MODEL_ID, {"input": 0.001, "output": 0.002})
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]

        print(f"[BEDROCK] ✅ Response received — {input_tokens + output_tokens} tokens, ${input_cost + output_cost:.6f}, {latency_ms}ms")

        return {
            "success": True,
            "response": output_text,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "total_cost": round(input_cost + output_cost, 6),
            "latency_ms": latency_ms,
            "model": BEDROCK_MODEL_ID,
        }
    except Exception as e:
        print(f"[BEDROCK] ❌ Error: {e}")
        return {"success": False, "error": str(e)}


def scan_output(prompt_name, output_text, input_prompt, security_group):
    """Step 5: Scan LLM output via SGS."""
    print(f"[SGS] Scanning output...")
    result = api_call("POST", "/sgs/scan/output", body={
        "prompt_name": prompt_name,
        "output": output_text,
        "prompt": input_prompt,
        "security_group": security_group,
    })
    if result["success"]:
        data = result["data"].get("data", result["data"])
        is_safe = data.get("is_safe", True)
        is_redacted = data.get("is_redacted", False)
        print(f"[SGS] ✅ Output scan complete — safe={is_safe}, redacted={is_redacted}")
        return data
    else:
        print(f"[SGS] ⚠️ Output scan failed: {result.get('error')}")
        return {"is_safe": True, "scan_error": result.get("error")}


def create_trace(trace_name, input_prompt, session_id):
    """Step 6: Create a trace in GCS for observability."""
    print(f"[GCS] Creating trace: {trace_name}")
    result = api_call("POST", "/gcs/logs/trace/create", body={
        "input": input_prompt[:2000],
        "username": "poc-user",
        "session_id": session_id,
        "trace_name": trace_name,
        "environment": "Design",
        "metadata": {"source": "aiforce-poc-lambda"},
    })
    if result["success"]:
        data = result["data"].get("data", result["data"])
        trace_id = data.get("trace_id", data.get("id", ""))
        print(f"[GCS] ✅ Trace created: {trace_id}")
        return trace_id
    else:
        print(f"[GCS] ⚠️ Trace creation failed: {result.get('error')}")
        return None


def log_llm_call(trace_id, prompt, output, bedrock_result):
    """Step 7: Log the LLM call details in the GCS trace."""
    print(f"[GCS] Logging LLM call to trace: {trace_id}")
    result = api_call("POST", "/gcs/logs/trace/llm_call", body={
        "trace_id": trace_id,
        "type": "LLM Call",
        "model": bedrock_result.get("model", BEDROCK_MODEL_ID),
        "prompt": prompt[:2000],
        "output": output[:2000],
        "input_tokens": bedrock_result.get("input_tokens", 0),
        "output_tokens": bedrock_result.get("output_tokens", 0),
        "total_tokens": bedrock_result.get("total_tokens", 0),
        "total_cost": bedrock_result.get("total_cost", 0),
        "environment": "Design",
        "metadata": {
            "latency_ms": str(bedrock_result.get("latency_ms", 0)),
            "model_id": BEDROCK_MODEL_ID,
        },
    })
    if result["success"]:
        print(f"[GCS] ✅ LLM call logged")
    else:
        print(f"[GCS] ⚠️ LLM call log failed: {result.get('error')}")


def get_cost_from_g3s():
    """Step 8: Get platform-wide consumption data from G3S."""
    print(f"[G3S] Fetching consumption data...")
    result = api_call("GET", "/g3s/model-consumption/consumption?date_filter=last_7_days")
    if result["success"]:
        raw = result["data"]
        if isinstance(raw, dict):
            data = raw.get("data", raw)
        else:
            data = raw
        print(f"[G3S] Consumption data retrieved")
        return data
    else:
        print(f"[G3S] Consumption fetch failed: {result.get('error')}")
        return None


def add_trace_event(trace_id, event_name, level, status_message, metadata=None):
    """Step 9: Add a custom event/span to the GCS trace."""
    print(f"[GCS] Adding event '{event_name}' to trace: {trace_id}")
    body = {
        "trace_id": trace_id,
        "name": event_name,
        "level": level,
        "status_message": status_message,
        "environment": "Design",
    }
    if metadata:
        body["metadata"] = metadata
    result = api_call("POST", "/gcs/logs/trace/add_event", body=body)
    if result["success"]:
        print(f"[GCS] Event '{event_name}' added")
    else:
        print(f"[GCS] Event add failed: {result.get('error')}")
    return result.get("success", False)


def update_trace_output(trace_id, final_output):
    """Step 10: Update the trace with the final LLM output."""
    print(f"[GCS] Updating trace output: {trace_id}")
    result = api_call("POST", "/gcs/logs/trace/update_output", body={
        "trace_id": trace_id,
        "output": final_output[:2000],
    })
    if result["success"]:
        print(f"[GCS] Trace output updated")
    else:
        print(f"[GCS] Trace output update failed: {result.get('error')}")
    return result.get("success", False)



# ─── Lambda Handler ──────────────────────────────────────────────────

def lambda_handler(event, context):
    """
    AWS Lambda entry point.

    Event format:
    {
        "mode": "standard" | "test_prompt",  (defaults to standard)
        "prompt_id": 123,                     (required for standard mode)
        "user_prompt": "Hello {{NAME}}",      (required for test_prompt mode)
        "system_prompt": "You are AI...",     (optional for test_prompt mode)
        "variables": {"COMPANY": "TechCorp"},
        "security_group": "poc-security-group"
    }
    """
    print("=" * 60)
    print("  AIForce POC — Lambda Execution Started")
    print("=" * 60)

    # Parse input
    mode = event.get("mode", "standard")
    variables = event.get("variables", {})
    security_group = event.get("security_group", SECURITY_GROUP)
    session_id = f"poc-session-{uuid.uuid4().hex[:8]}"

    # Input validation
    if mode == "standard" and not event.get("prompt_id"):
        return {"statusCode": 400, "body": json.dumps({"error": "prompt_id is required for standard mode"})}
    if mode == "test_prompt" and not event.get("user_prompt"):
        return {"statusCode": 400, "body": json.dumps({"error": "user_prompt is required for test_prompt mode"})}

    if not AUTH_TOKEN:
        return {"statusCode": 400, "body": json.dumps({"error": "AIFORCE_AUTH_TOKEN env var not set"})}

    result = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": mode,
        "session_id": session_id,
    }

    # ── Step 1: Get or Build Prompt ──────────────────────────────
    if mode == "standard":
        prompt_id = event["prompt_id"]
        result["prompt_id"] = prompt_id
        prompt_data = get_prompt(prompt_id)
        if not prompt_data:
            return {"statusCode": 404, "body": json.dumps({"error": f"Prompt {prompt_id} not found"})}

        prompt_name = prompt_data.get("name", f"prompt_{prompt_id}")
        user_prompt_template = prompt_data.get("user_prompt", "")
        system_prompt = prompt_data.get("system_prompt", "")
    else:
        # test_prompt mode
        prompt_name = "dynamic_test_prompt"
        user_prompt_template = event["user_prompt"]
        system_prompt = event.get("system_prompt", "")

    result["prompt_name"] = prompt_name

    # ── Step 2: Substitute variables ─────────────────────────────
    resolved_prompt = substitute_variables(user_prompt_template, variables)
    result["resolved_prompt"] = resolved_prompt

    # ── Step 3: Scan input via SGS ───────────────────────────────
    input_scan = scan_input(prompt_name, user_prompt_template, variables, security_group)
    result["input_scan"] = {
        "is_safe": input_scan.get("is_safe", True),
        "is_redacted": input_scan.get("is_redacted", False),
    }

    # If input is unsafe → stop here
    if not input_scan.get("is_safe", True):
        print("[FLOW] ❌ Input flagged as UNSAFE — skipping Bedrock call")
        result["response"] = "Request blocked — input failed safety scan."
        result["bedrock_skipped"] = True
        return {"statusCode": 200, "body": json.dumps(result, default=str)}

    # Use redacted text if available
    final_prompt = input_scan.get("sanitized_text", resolved_prompt) if input_scan.get("is_redacted") else resolved_prompt

    # ── Step 4: Call LLM (Bedrock OR PES Test) ───────────────────
    if mode == "standard":
        bedrock_result = call_bedrock(final_prompt, system_prompt)
        result["bedrock"] = bedrock_result
        if not bedrock_result.get("success"):
            result["response"] = f"Bedrock error: {bedrock_result.get('error')}"
            return {"statusCode": 500, "body": json.dumps(result, default=str)}
        llm_response = bedrock_result["response"]
    else:
        # For test_prompt, PES calls the LLM configuration defined by lm_config_id
        lm_config_id = event.get("lm_config_id", 1)  # allow override
        test_result = test_prompt_via_pes(final_prompt, system_prompt, variables, lm_config_id)
        result["pes_test"] = test_result
        if "error" in test_result:
            result["response"] = f"PES test error: {test_result.get('error')}"
            return {"statusCode": 500, "body": json.dumps(result, default=str)}
        llm_response = test_result.get("response", str(test_result)) # PES response schema varies
        bedrock_result = {} # Mock bedrock result for downstream trace logging

    # ── Step 5: Scan output via SGS ──────────────────────────────
    output_scan = scan_output(prompt_name, llm_response, final_prompt, security_group)
    result["output_scan"] = {
        "is_safe": output_scan.get("is_safe", True),
        "is_redacted": output_scan.get("is_redacted", False),
    }

    # Use sanitized output if redacted
    if output_scan.get("is_redacted") and output_scan.get("sanitized_text"):
        llm_response = output_scan["sanitized_text"]
        print("[FLOW] ⚠️ Output was redacted — using sanitized version")

    result["response"] = llm_response

    # ── Step 6: Create trace in GCS ──────────────────────────────
    trace_id = create_trace(f"poc-{prompt_name}", final_prompt, session_id)
    result["trace_id"] = trace_id

    # ── Step 7: Log LLM call in GCS ──────────────────────────────
    if trace_id:
        log_llm_call(trace_id, final_prompt, llm_response, bedrock_result)

    # -- Step 8: Get G3S consumption (cost tracking) ---------------
    if mode == "standard":
        g3s_consumption = get_cost_from_g3s()
        result["cost"] = {
            "this_call": {
                "input_tokens": bedrock_result.get("input_tokens", 0),
                "output_tokens": bedrock_result.get("output_tokens", 0),
                "total_tokens": bedrock_result.get("total_tokens", 0),
                "total_cost_usd": bedrock_result.get("total_cost", 0),
                "model": BEDROCK_MODEL_ID,
            },
            "g3s_platform_consumption": g3s_consumption,
        }

    # -- Step 9: Add trace events (observability) ------------------
    if trace_id:
        # Log input scan result as event
        add_trace_event(trace_id, "input-scan",
            "DEFAULT" if result["input_scan"]["is_safe"] else "WARNING",
            f"Input scan: safe={result['input_scan']['is_safe']}, redacted={result['input_scan']['is_redacted']}",
            {"scanner": "SGS", "is_safe": str(result["input_scan"]["is_safe"])})

        # Log Bedrock call as event
        add_trace_event(trace_id, "bedrock-call", "DEFAULT",
            f"Bedrock: {bedrock_result.get('total_tokens', 0)} tokens, ${bedrock_result.get('total_cost', 0):.6f}, {bedrock_result.get('latency_ms', 0)}ms",
            {"model": BEDROCK_MODEL_ID, "tokens": str(bedrock_result.get("total_tokens", 0))})

        # Log output scan result as event
        add_trace_event(trace_id, "output-scan",
            "DEFAULT" if result["output_scan"]["is_safe"] else "WARNING",
            f"Output scan: safe={result['output_scan']['is_safe']}, redacted={result['output_scan']['is_redacted']}",
            {"scanner": "SGS", "is_safe": str(result["output_scan"]["is_safe"])})

    # -- Step 10: Update trace with final output -------------------
    if trace_id:
        update_trace_output(trace_id, llm_response)
        result["trace_output_updated"] = True

    # -- Summary ---------------------------------------------------
    print("\n" + "=" * 60)
    print("  EXECUTION SUMMARY")
    print("=" * 60)
    print(f"  Prompt:       {prompt_name} (ID: {prompt_id})")
    print(f"  Input Safe:   {result['input_scan']['is_safe']}")
    print(f"  Output Safe:  {result['output_scan']['is_safe']}")
    print(f"  Tokens:       {bedrock_result.get('total_tokens', 0)}")
    print(f"  Cost:         ${bedrock_result.get('total_cost', 0):.6f}")
    print(f"  Trace ID:     {trace_id}")
    print(f"  Trace Events: input-scan, bedrock-call, output-scan")
    print(f"  Response:     {llm_response[:100]}...")
    print("=" * 60)

    return {"statusCode": 200, "body": json.dumps(result, default=str)}
