# AIForce POC — Work Summary

## Project Overview

**Objective**: Validate the AIForce platform by integrating all four foundational services (PES, SGS, GCS, G3S) with AWS Bedrock in a single end-to-end proof of concept. The goal was to demonstrate that AIForce can manage prompts, enforce security guardrails, provide observability, and track costs — all within a production-like AWS Lambda deployment.

**Duration**: March 16, 2026

**Platform**: AIForce (hosted at `https://54.91.159.104`) + AWS Lambda + Amazon Bedrock

---

## Task 1: Service Health Verification

**What was done**: Verified that all four AIForce foundational services were running and reachable.

**Services checked**:
| Service | Endpoint | Purpose |
|---------|----------|---------|
| PES (Prompt Engineering Service) | `/check_health` | Manages prompt templates |
| SGS (Security Guardrails Service) | `/sgs/check_health` | Scans inputs/outputs for security risks |
| GCS (Governance & Compliance Service) | `/check_health` | Traces and observability |
| G3S (GenAI Gateway Service) | `/g3s/check_health` | LLM config and cost tracking |

**How**: Ran `curl` health check commands against each service to confirm HTTP 200 responses.

**Outcome**: All four services responded as healthy and ready for integration.

---

## Task 2: LLM Configuration Discovery

**What was done**: Queried the G3S service to discover available LLM configurations.

**Endpoint used**: `GET /g3s/configuration/list_llm_configuration?page=1&page_size=10`

**Why this matters**: Every prompt saved in PES requires a `lm_config_id` — this links the prompt to a specific LLM model configuration (e.g., Claude 3 Haiku, Titan). The `lm_config_id` was retrieved from the G3S response and used in subsequent prompt creation steps.

**Outcome**: Retrieved `lm_config_id = 1` which was used for all prompts.

---

## Task 3: Prompt Creation in PES

**What was done**: Created two managed prompts in the Prompt Engineering Service (PES) — one for positive testing and one for negative (PII) testing.

### Prompt A — Customer Support (Safe Prompt)
- **Name**: `poc_customer_support`
- **User Prompt Template**: `"You are a helpful customer support assistant for {{COMPANY}}. A customer asks: {{QUESTION}}. Please provide a clear and professional response."`
- **System Prompt**: `"You are a professional customer support agent. Be concise, empathetic, and solution-oriented."`
- **Variables**: `{{COMPANY}}` (company name), `{{QUESTION}}` (customer question)
- **LLM Parameters**: Temperature 0.7, Max Tokens 1024

### Prompt B — PII Test Prompt
- **Name**: `poc_pii_test`
- **User Prompt Template**: `"Write a short example customer profile for {{NAME}} including their email, phone number, and a brief account summary."`
- **System Prompt**: `"You are a data entry assistant. Create realistic sample customer profiles with contact details."`
- **Variables**: `{{NAME}}` (person's name)
- **LLM Parameters**: Temperature 0.7, Max Tokens 512

**Endpoint used**: `POST /pes/prompt_studio/save_prompt` (form-urlencoded)

**Key technical detail**: The PES API uses the field name `varriables` (with double 'r') — this is the API's actual spelling and must be matched exactly in requests. Variables are passed as a JSON string mapping variable names to their types.

**Outcome**: Both prompts were created and assigned unique `prompt_id` values (Prompt A = ID 3, Prompt B = ID 4) which were used in Lambda test events.

---

## Task 4: Security Group Registration in SGS

**What was done**: Registered a new security group named `poc-security-group` in the Security Guardrails Service.

**Endpoint used**: `POST /sgs/security-groups/register`

**What is a Security Group?** A security group in SGS is a named configuration that defines which scanners should run when input or output is being validated. Think of it as a "security policy" — you choose which checks to enable, how strict each threshold should be, and whether to block or just flag.

**Outcome**: Security group `poc-security-group` was registered and ready for scanner configuration.

---

## Task 5: Master Scanner Discovery

**What was done**: Listed all available scanners on the platform to understand which security checks are supported.

**Endpoint used**: `GET /sgs/security-groups/master/scanners`

**Why this was important**: The SGS platform comes with a set of installed scanners, but not all scanners listed in the API documentation are necessarily installed. Using an unsupported scanner name in the configuration causes an "unsupported scanner" error. This discovery step was essential to avoid failed configurations.

**Scanners discovered**: The master scanner list revealed the exact names, configurations, and capabilities of each available scanner, including thresholds, entity types for PII, and toggle options.

**Issue encountered**: Initial configuration attempts used scanner names from the Swagger/OpenAPI documentation examples (like `Detect Bias`), but these were not all installed on the platform. The discovery step resolved this by showing only the actually-available scanners.

**Outcome**: Identified the correct scanner names supported on the platform for use in Step 6.

---

## Task 6: Security Scanner Configuration

**What was done**: Configured the `poc-security-group` with specific input and output scanners.

**Endpoint used**: `PUT /sgs/security-groups/poc-security-group/config`

### Input Scanners Enabled

| Scanner | Threshold | What It Detects |
|---------|-----------|-----------------|
| Detect PII | 0.6 | Names, emails, phone numbers, credit cards, SSNs — redacts if found |
| Detect Prompt Injection | 0.7 | Attempts to override or manipulate LLM instructions |
| Detect Toxicity | 0.8 | Offensive, hateful, or harmful language |

### Output Scanners Enabled

| Scanner | Threshold | What It Detects |
|---------|-----------|-----------------|
| Detect PII | 0.6 | PII in LLM responses — redacts if found |
| Detect Toxicity | 0.8 | Toxic or harmful language in LLM output |

**Key technical detail**: Each scanner in the configuration requires three fields: `description` (text), `enabled` (true/false), and `config` (scanner-specific settings like thresholds, entity types). Missing the `description` field causes the API to reject the request.

**Issues encountered and resolved**:
1. **First attempt failed**: Used a simplified config format without `description` fields — API rejected it
2. **Second attempt (Swagger defaults)**: Copied the full example from the OpenAPI spec which had **all scanners enabled** (including Banned Topics, Competitors, Relevance, Code Language, etc.) — this caused the safe prompt "How do I reset my password?" to be flagged as unsafe because aggressive scanners like Detect Relevance (0.3 threshold) were too strict
3. **Third attempt (final)**: Configured only the 3 needed input scanners and 2 output scanners with appropriate thresholds — safe prompts passed correctly

**Outcome**: Security group properly configured with targeted scanners. Safe inputs pass through; PII, toxic, and injection inputs are correctly flagged.

---

## Task 7: Lambda Function Deployment

**What was done**: Deployed the POC Lambda function to AWS using the Lambda Console.

### Deployment Steps Performed
1. Created a new Lambda function in the AWS Console (Python 3.12 runtime)
2. Pasted the `lambda_function.py` code directly into the inline editor
3. Configured environment variables:
   | Variable | Value |
   |----------|-------|
   | `AIFORCE_BASE_URL` | `https://54.91.159.104` |
   | `AIFORCE_AUTH_TOKEN` | Bearer token for AIForce API |
   | `BEDROCK_MODEL_ID` | `anthropic.claude-3-haiku-20240307-v1:0` |
   | `AWS_REGION` | `us-east-1` |
   | `SECURITY_GROUP` | `poc-security-group` |
4. Increased timeout from default 3 seconds to 60 seconds (LLM calls + multiple API calls take time)
5. Configured IAM role with `bedrock:InvokeModel` permission

**Key technical detail**: No Lambda layers were needed. The function uses only native Python libraries (`urllib`, `json`, `ssl`, `uuid`, `datetime`, `os`, `time`) plus `boto3` which is pre-installed in the Lambda runtime. This simplifies deployment — just paste the code and test.

**Outcome**: Lambda function deployed and accessible from the Lambda Console test interface.

---

## Task 8: Testing — PES-Based Flow (6 Scenarios)

**What was done**: Executed 6 test scenarios through the Lambda Console to validate the complete AIForce integration.

### Scenario 1: Safe Question (Positive)
- **Input**: prompt_id=3, COMPANY="TechCorp", QUESTION="How do I reset my password?"
- **Expected**: Input passes SGS scan → Bedrock generates response → Output passes SGS scan → Trace created in GCS
- **Result**: Full flow completed successfully. All scans passed, LLM response received, trace ID generated, cost tracked.

### Scenario 2: PII in Input Variables (Negative)
- **Input**: prompt_id=3, COMPANY="TechCorp", QUESTION contains PII like email/SSN
- **Expected**: SGS input scanner detects PII and either redacts or flags
- **Result**: PII detected in input, redaction applied, Bedrock called with sanitized text

### Scenario 3: Toxic Input (Negative)
- **Input**: prompt_id=3, variables contain toxic/offensive language
- **Expected**: SGS input scanner flags as unsafe → Bedrock call skipped entirely
- **Result**: Request blocked at input scan stage, "Request blocked — input failed safety scan" returned

### Scenario 4: Prompt Injection (Negative)
- **Input**: prompt_id=3, QUESTION contains injection attempt like "Ignore all instructions..."
- **Expected**: Prompt injection scanner flags as unsafe → Bedrock call skipped
- **Result**: Injection detected, request blocked

### Scenario 5: PII in Output (Negative)
- **Input**: prompt_id=4 (PII test prompt), NAME="John Smith"
- **Expected**: Bedrock generates profile with PII → Output scanner detects and redacts PII
- **Result**: Output scanned, PII detected in response, redacted version returned

### Scenario 6: Consistency Check (Positive)
- **Input**: Same as Scenario 1 — re-run to verify consistency
- **Expected**: Same successful flow as Scenario 1
- **Result**: Consistent behavior confirmed

**Issues encountered and resolved during testing**:
1. **PES response parsing**: The API returned prompt data wrapped in a list `[{...}]` instead of a dict — caused "prompt name unknown" error. Fixed by handling list responses.
2. **G3S consumption response**: Returned a list directly instead of `{"data": [...]}` — caused `AttributeError: list object has no attribute get`. Fixed by checking response type.
3. **GCS trace creation failed**: "expecting value: line 1 column 1 (char 0)" — caused by missing `/gcs` prefix on GCS endpoint URLs. Fixed by adding the correct URL prefix.
4. **SGS "unsupported scanner" error**: Scanner names from documentation didn't match installed scanners. Fixed by querying master scanners first (Task 5).

---

## Task 9: Testing — Dynamic Prompt Flow (No PES)

**What was done**: Tested prompts dynamically by passing raw prompt text directly to the Lambda, bypassing PES entirely.

**Why this was needed**: The PES-based flow requires prompts to be saved in PES first (assigned a `prompt_id`). The dynamic mode allows testing any prompt on-the-fly without pre-registration — useful for rapid iteration, ad-hoc testing, and scenarios where prompt management isn't needed.

### Dynamic Test — Safe Question
- **Input**: mode="dynamic", user_prompt and system_prompt passed directly with COMPANY="TechCorp", QUESTION="How do I reset my password?"
- **Flow**: Variable substitution → SGS input scan → Bedrock → SGS output scan → GCS tracing → G3S cost
- **Result**: Full flow completed. Identical safety and observability coverage as the PES-based flow.

### Dynamic Test — PII Test
- **Input**: mode="dynamic", PII-triggering prompt with NAME="John Smith"
- **Result**: Output PII scanning detected and redacted personal information.

**Key technical detail**: SGS doesn't actually look up prompts from PES — the `prompt_name` field in scan requests is just a label for tracking/logging. This means any string can be used as a prompt name, and the actual prompt text is what gets scanned. This architectural insight enabled the dynamic testing mode.

---

## Task 10: Observability Verification (GCS)

**What was done**: Verified that every Lambda execution generates comprehensive observability data in the Governance & Compliance Service.

### What gets traced for every execution:

| Data Point | GCS Endpoint | What's Recorded |
|------------|-------------|-----------------|
| **Trace creation** | `POST /gcs/logs/trace/create` | Session ID, input prompt, user, environment, timestamp |
| **LLM call details** | `POST /gcs/logs/trace/llm_call` | Model used, tokens (input/output), cost, latency, prompt and response text |
| **Input scan event** | `POST /gcs/logs/trace/add_event` | SGS scan result (safe/unsafe), scanner used, redaction status |
| **Bedrock call event** | `POST /gcs/logs/trace/add_event` | Token count, cost, model ID |
| **Output scan event** | `POST /gcs/logs/trace/add_event` | SGS output scan result, redaction status |
| **Final output** | `POST /gcs/logs/trace/update_output` | The final LLM response (after any redaction) |

**Outcome**: Every execution produces a traceable record with a unique `trace_id`. The trace contains step-by-step events showing exactly what happened at each stage — useful for auditing, debugging, and compliance reporting.

---

## Task 11: Cost Tracking Verification (G3S)

**What was done**: Verified that platform-wide model consumption data is accessible through G3S.

**Endpoint used**: `GET /g3s/model-consumption/consumption?date_filter=last_7_days`

**What's tracked**:
- Per-call cost calculation: Input tokens × rate + Output tokens × rate
- Model used (e.g., `anthropic.claude-3-haiku-20240307-v1:0`)
- Platform-wide consumption aggregated over configurable time periods

**Outcome**: Each Lambda response includes both the individual call cost and the platform-wide consumption data from G3S.

---

## Summary of AIForce Services Validated

| Service | Endpoints Tested | Capabilities Validated |
|---------|-----------------|----------------------|
| **PES** | Get prompt details, List prompts | Centralized prompt management with variable templates |
| **SGS** | Scan prompt, Scan output, Register group, Configure scanners, Master scanners | Input/output security scanning, PII redaction, toxicity detection, prompt injection detection |
| **GCS** | Create trace, Log LLM call, Add event, Update output | Full observability — traces, events, LLM call logging |
| **G3S** | List LLM configurations, Get consumption | Model configuration management, cost tracking |

## Artifacts Produced

| File | Description |
|------|-------------|
| `00-poc-overview.md` | Complete POC architecture and endpoint documentation |
| `01-prerequisites.md` | Step-by-step curl commands for platform setup |
| `02-deployment-guide.md` | Lambda Console deployment instructions |
| `03-testing-guide.md` | 6 test scenarios with JSON payloads |
| `lambda_function.py` | Single-file Lambda function (two modes: PES-based + Dynamic) |
