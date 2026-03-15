# AIForce POC — Architecture & Running Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                              USER                                   │
│                     "How do I reset my password?"                    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATOR                                 │
│                     (poc/orchestrator.py)                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─── STEP 1 ──────────────────────────────────────────────────┐    │
│  │  GET prompt from PES                                        │    │
│  │  PES /get_prompt_details/42                                 │    │
│  │  Returns: template + system prompt + config                 │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                           │                                          │
│                           ▼                                          │
│  ┌─── STEP 2 ──────────────────────────────────────────────────┐    │
│  │  Substitute variables                                       │    │
│  │  "{{COMPANY}}" → "TechCorp"                                 │    │
│  │  "{{QUESTION}}" → "How do I reset my password?"             │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                           │                                          │
│                           ▼                                          │
│  ┌─── STEP 3: PRE-FLIGHT SECURITY ─────────────────────────────┐    │
│  │  SGS /scan/prompt                                           │    │
│  │  Checks: PII, Prompt Injection, Toxicity, Secrets           │    │
│  │  Result: is_safe + sanitized_text (PII redacted)           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                           │                                          │
│                     is_safe? ──No──→ BLOCK & RETURN                  │
│                           │                                          │
│                          Yes                                         │
│                           │                                          │
│                           ▼                                          │
│  ┌─── STEP 4: DIRECT BEDROCK CALL ─────────────────────────────┐    │
│  │  boto3.client("bedrock-runtime").invoke_model()             │    │
│  │  Model: anthropic.claude-3-sonnet                           │    │
│  │  ⚡ NOT through G3S — direct to AWS                         │    │
│  │  Returns: response + input_tokens + output_tokens + cost    │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                           │                                          │
│                           ▼                                          │
│  ┌─── STEP 5: POST-FLIGHT SECURITY ────────────────────────────┐    │
│  │  SGS /scan/output                                           │    │
│  │  Checks: PII in output, Toxicity, Banned topics             │    │
│  │  Result: is_safe + sanitized_text (if needed)              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                           │                                          │
│                           ▼                                          │
│  ┌─── STEP 6: OBSERVABILITY ───────────────────────────────────┐    │
│  │  GCS /logs/trace/create → trace_id                          │    │
│  │  GCS /logs/trace/llm_call → log tokens, cost, latency      │    │
│  │  GCS /logs/trace/update_output → log final response         │    │
│  │  GCS /logs/trace/add_event → log security scan results     │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                           │                                          │
│                           ▼                                          │
│  ┌─── STEP 7: RETURN ─────────────────────────────────────────┐     │
│  │  Response + Token Usage + Cost + Security Status            │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
aiforce-poc/
├── docs/                               # Service documentation
│   ├── 00-Master-Overview.md           # Cross-service flows & quick reference
│   ├── 01-PES-Prompt-Engineering-Service.md
│   ├── 02-G3S-GenAI-Gateway-Service.md
│   ├── 03-GCS-Governance-Compliance-Service.md
│   ├── 04-SGS-Security-Guardrails-Service.md
│   └── 05-POC-Architecture.md          # ← This file
│
├── lambdas/                            # One Lambda per service (all 92 endpoints)
│   ├── shared/
│   │   └── aiforce_client.py           # Shared HTTP client + 4 service classes
│   ├── pes_lambda.py                   # PES: 16 prompt management actions
│   ├── g3s_lambda.py                   # G3S: 18 gateway/config actions
│   ├── sgs_lambda.py                   # SGS: 12 security actions
│   └── gcs_lambda.py                   # GCS: 38 governance/compliance actions
│
├── poc/                                # Complete POC orchestrator
│   ├── config.py                       # Configuration + model pricing table
│   ├── bedrock_client.py               # Direct Bedrock calls via boto3
│   ├── orchestrator.py                 # End-to-end flow (5 phases)
│   └── requirements.txt               # Python dependencies
│
├── sample-csvs/                        # Test data files
│   ├── gcs_prompt_dataset.csv          # Prompt evaluation (10 Q&A pairs)
│   ├── gcs_rag_dataset.csv             # RAG evaluation (5 context-question pairs)
│   ├── gcs_agent_dataset.csv           # Agent evaluation (5 tool-usage examples)
│   └── pes_prompt_dataset.csv          # PES evaluation (5 business prompts)
│
├── g3s.json                            # G3S OpenAPI spec
├── pes.json                            # PES OpenAPI spec
├── gcs.json                            # GCS OpenAPI spec
└── sgs.json                            # SGS OpenAPI spec
```

## How to Run

### Prerequisites

1. Python 3.9+
2. AWS credentials configured (`aws configure` or IAM role)
3. AIForce auth token

### Setup

```bash
cd aiforce-poc/poc

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export AIFORCE_AUTH_TOKEN="your-aiforce-bearer-token"
export AWS_REGION="us-east-1"
export BEDROCK_MODEL_ID="anthropic.claude-3-sonnet-20240229-v1:0"
export SECURITY_GROUP_NAME="poc-security-group"

# On Windows PowerShell:
$env:AIFORCE_AUTH_TOKEN = "your-aiforce-bearer-token"
$env:AWS_REGION = "us-east-1"
$env:BEDROCK_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"
```

### Run the POC

```bash
cd aiforce-poc/poc
python orchestrator.py
```

### What the POC Does (5 Phases)

| Phase | What Happens |
|-------|-------------|
| **1. Setup** | Health checks all 4 services, lists G3S LLM configs, saves a prompt to PES, creates & configures an SGS security group |
| **2. Execute** (×3 queries) | For each query: retrieves prompt from PES → scans input via SGS → calls Bedrock directly → scans output via SGS → logs trace in GCS |
| **3. Evaluate** | Lists GCS metrics, uploads test dataset, scans prompt compliance |
| **4. Cost Report** | Local token/cost summary + G3S platform-wide consumption data + GCS trace summary |
| **5. Cleanup** (optional) | Deletes test prompt and security group |

### Token Usage & Cost Output

The POC outputs detailed cost information for every Bedrock call:

```
📊 Tokens: 450 input + 230 output
⏱️ Latency: 1,234ms
💰 Cost: $0.004800

SESSION TOTAL: 3 calls, 2,040 tokens, $0.014400
```

## Lambda Deployment

Each Lambda can be deployed independently. They use the same shared client:

```bash
# Package a Lambda
cd lambdas
zip -r pes_lambda.zip pes_lambda.py shared/

# Deploy to AWS
aws lambda update-function-code \
  --function-name aiforce-pes \
  --zip-file fileb://pes_lambda.zip

# Set environment variables
aws lambda update-function-configuration \
  --function-name aiforce-pes \
  --environment "Variables={AIFORCE_BASE_URL=https://54.91.159.104,AIFORCE_AUTH_TOKEN=your-token}"
```

### Lambda Invocation Examples

```json
// PES: Save a prompt
{
  "action": "save_prompt",
  "payload": {
    "name": "my_prompt_v1",
    "user_prompt": "Help with: {{QUESTION}}",
    "lm_config_id": 1,
    "publish_status": true
  }
}

// SGS: Scan input
{
  "action": "scan_prompt",
  "payload": {
    "prompt_name": "my_prompt_v1",
    "input_prompt": "Tell me about {{NAME}}",
    "variables": {"NAME": "John Doe"},
    "security_group": "my-group"
  }
}

// GCS: Create trace
{
  "action": "create_trace",
  "payload": {
    "name": "my-trace",
    "session_id": "session-123"
  }
}

// G3S: Get consumption
{
  "action": "get_consumption",
  "payload": {
    "date_filter": "last_7_days"
  }
}
```
