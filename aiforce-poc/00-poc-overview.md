# AIForce POC — Complete Overview

## What is This?

A **single Lambda function** that demonstrates the full AIForce platform integration across all 4 foundational services. No external dependencies — no layers, no `pip install`, just native Python + `boto3`.

---

## Architecture Flow

```
User Input (mode: "standard" or "test_prompt")
    |
    v
[1] PES: Get Prompt --- Retrieve managed prompt template by ID
    |
[2] Substitute Variables --- Replace {{COMPANY}}, {{QUESTION}} etc.
    |
    v
[3] SGS: Scan Input --- Check for PII, toxicity, prompt injection
    |
    |-- UNSAFE -> Block request, return error
    |
    v  SAFE
    |──── MODE: standard ────┐               ┌──── MODE: test_prompt ────┐
    |                        |               |                           |
[4] Bedrock: Call LLM      [8] G3S Cost  OR  [4] PES: test_prompt API    |
    | (via boto3)            |               | (Calls LLM internally)    |
    v                        v               v                           v
    └────────────────────────┴───────────────┴───────────────────────────┘
    |
    v
[5] SGS: Scan Output --- Check LLM response for PII, toxicity
    |
    v
[6] GCS: Create Trace --- Start observability trace
    |
[7] GCS: Log LLM Call --- Record tokens, cost, latency
    |
    v
[8] G3S: Get Cost --- Fetch platform consumption data
    |
[9] GCS: Add Events --- Log input-scan, bedrock-call, output-scan events
    |
[10] GCS: Update Output --- Attach final response to trace
    |
    v
Return: response + scan results + trace_id + cost
```

---

## Services Used (8 endpoints across 4 services)

| # | Service | Endpoint | Purpose |
|---|---------|----------|---------|
| 1 | **PES** | `GET /pes/prompt_studio/get_prompt_details/{id}` | Retrieve prompt template |
| 2 | **SGS** | `POST /sgs/scan/prompt` | Scan input for safety |
| 3 | **SGS** | `POST /sgs/scan/output` | Scan LLM output for safety |
| 4 | **GCS** | `POST /gcs/logs/trace/create` | Create observability trace |
| 5 | **GCS** | `POST /gcs/logs/trace/llm_call` | Log LLM call (tokens, cost) |
| 6 | **GCS** | `POST /gcs/logs/trace/add_event` | Add step events to trace |
| 7 | **GCS** | `POST /gcs/logs/trace/update_output` | Update trace with final output |
| 8 | **G3S** | `GET /g3s/model-consumption/consumption` | Platform cost tracking |

---

## What Each Service Does

### PES — Prompt Engineering Service
Manages prompts centrally. Prompts can have variables like `{{COMPANY}}` that get substituted at runtime. The POC retrieves prompts by ID so you don't hardcode them in the Lambda.

### SGS — Security Guardrails Service
Scans both inputs and outputs using configurable scanners:
- **Input**: PII detection/redaction, prompt injection detection, toxicity detection
- **Output**: PII detection/redaction, toxicity detection

If input is flagged as unsafe, the Lambda **blocks the Bedrock call entirely**.

### GCS — Governance & Compliance Service
Provides full observability:
- **Traces**: Every Lambda execution creates a trace with a unique `trace_id`
- **LLM Calls**: Tokens, cost, latency, model details are logged
- **Events**: Each step (input scan, Bedrock call, output scan) is logged as a separate event
- **Output**: Final LLM response is attached to the trace

### G3S — GenAI Gateway Service
Provides model configuration management and cost tracking. The POC queries the consumption endpoint to show platform-wide usage data.

---

## Files in This Folder

| File | Description |
|------|-------------|
| `00-poc-overview.md` | This document — full POC explanation |
| `01-prerequisites.md` | Curl commands to set up prompts and security groups |
| `02-deployment-guide.md` | How to deploy via AWS Lambda Console |
| `03-testing-guide.md` | 6 test scenarios (positive + negative) with JSON payloads |
| `lambda_function.py` | The Lambda code — single file, ~420 lines, no layers |

---

## Prerequisites Summary

Before deploying, you must:

1. **G3S**: List LLM configs to get `lm_config_id`
2. **PES**: Create Prompt A (safe customer support prompt with `{{COMPANY}}`, `{{QUESTION}}`)
3. **PES**: Create Prompt B (PII test prompt with `{{NAME}}`)
4. **SGS**: Register a security group (`poc-security-group`)
5. **SGS**: List available master scanners
6. **SGS**: Configure scanners (only enable PII, Toxicity, Prompt Injection)

All steps use `curl` commands documented in `01-prerequisites.md`.

---

## Lambda Input/Output

### Input Event (Standard Mode)
```json
{
  "mode": "standard",
  "prompt_id": 3,
  "variables": {
    "COMPANY": "TechCorp",
    "QUESTION": "How do I reset my password?"
  },
  "security_group": "poc-security-group"
}
```

### Input Event (Dynamic Test Mode)
```json
{
  "mode": "test_prompt",
  "user_prompt": "Write a short poem about {{TOPIC}}",
  "system_prompt": "You are a poet.",
  "variables": {
    "TOPIC": "cybersecurity"
  },
  "lm_config_id": 1,
  "security_group": "poc-security-group"
}
```

### Output Response
```json
{
  "statusCode": 200,
  "body": {
    "timestamp": "2025-03-16T08:30:00Z",
    "prompt_id": 3,
    "prompt_name": "poc_customer_support",
    "session_id": "poc-session-abc12345",
    "resolved_prompt": "You are a helpful customer support assistant for TechCorp...",
    "input_scan": { "is_safe": true, "is_redacted": false },
    "bedrock": {
      "success": true,
      "response": "Thank you for contacting TechCorp...",
      "input_tokens": 45,
      "output_tokens": 120,
      "total_tokens": 165,
      "total_cost": 0.000161,
      "latency_ms": 1200
    },
    "output_scan": { "is_safe": true, "is_redacted": false },
    "trace_id": "abc-123-xyz",
    "trace_output_updated": true,
    "cost": {
      "this_call": {
        "input_tokens": 45,
        "output_tokens": 120,
        "total_cost_usd": 0.000161,
        "model": "anthropic.claude-3-haiku-20240307-v1:0"
      },
      "g3s_platform_consumption": [ ... ]
    },
    "response": "Thank you for contacting TechCorp..."
  }
}
```

---

## Test Scenarios

| # | Scenario | Type | What's Tested |
|---|----------|------|---------------|
| 1 | Safe question | Positive | Full happy path — all 10 steps |
| 2 | PII in variables | Negative | Input PII detection & redaction |
| 3 | Toxic input | Negative | Toxicity blocking (Bedrock skipped) |
| 4 | Prompt injection | Negative | Injection detection (Bedrock skipped) |
| 5 | PII in output | Negative | Output PII screening |
| 6 | Consistency check | Positive | Verifies flow works repeatedly |
| 7 | Dynamic prompt testing | Positive | Tests `test_prompt` mode without saving a prompt |

See `03-testing-guide.md` for exact JSON test events.

---

## Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `AIFORCE_BASE_URL` | `https://54.91.159.104` | AIForce platform URL |
| `AIFORCE_AUTH_TOKEN` | Your token | Bearer auth token |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-haiku-20240307-v1:0` | Bedrock model |
| `AWS_REGION` | `us-east-1` | AWS region |
| `SECURITY_GROUP` | `poc-security-group` | Default security group |

---

## Technical Details

- **Runtime**: Python 3.12 on AWS Lambda
- **Dependencies**: `urllib` (native), `boto3` (built into Lambda)
- **Layers**: None required
- **Timeout**: 60 seconds recommended
- **Memory**: 128–256 MB
- **Handler**: `lambda_function.lambda_handler`
