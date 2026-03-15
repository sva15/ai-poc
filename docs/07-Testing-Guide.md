# AIForce POC — Testing Guide

This guide covers how to test your AIForce POC components, from running the local orchestrator to testing the individual AWS Lambda functions you deployed.

---

## 1. Testing the Full End-to-End Flow Locally

The `orchestrator.py` script is the best way to test the integration of all services together. It simulates a real-world flow from setup, configuration to prompt execution and cost tracking.

### Prerequisites

You need the `requests` and `boto3` libraries installed:

```bash
cd poc
pip install -r requirements.txt
```

### Setting Environment Variables

Set the credentials before running:

**Linux / Mac:**
```bash
export AIFORCE_AUTH_TOKEN="your-aiforce-bearer-token"
export AWS_REGION="us-east-1"
# Optional Overrides:
# export BEDROCK_MODEL_ID="anthropic.claude-3-sonnet-20240229-v1:0"
# export SECURITY_GROUP_NAME="my-test-group"
```

**Windows PowerShell:**
```powershell
$env:AIFORCE_AUTH_TOKEN="your-aiforce-bearer-token"
$env:AWS_REGION="us-east-1"
```

### Running the Orchestrator

```bash
python orchestrator.py
```

**Expected Output Breakdown:**
* **Phase 1 (Setup):** Health checks pass (✅), LLM configs listed, Prompt saved, SGS config complete.
* **Phase 2 (Execute):** Should process 3 queries. Shows Direct Bedrock interaction. Input & Output tokens consumed should be visible. 
* **Phase 3 (Evaluate):** Checks metric listing and dataset uploads.
* **Phase 4 (Cost Report):** Cost of the 3 executed queries + historical G3S data.

*If any step fails, you'll see a `⚠️` or `❌` indicating which service or payload failed.*

---

## 2. Testing the Lambda Functions via AWS Lambda Console

Once you have deployed the Lambdas (see the [Deployment Guide](06-Deployment-Guide.md)), you can test them directly using the AWS Lambda Console.

1. Open the [AWS Lambda Console](https://console.aws.amazon.com/lambda).
2. Click on the function you want to test (e.g., `aiforce-pes`, `aiforce-sgs`, etc.).
3. Select the **Test** tab.
4. Create a new test event and copy-paste the JSON payloads below. Click **Save** and then **Test**.

### Test 1: PES (Health Check)
**Function**: `aiforce-pes`
**Event JSON**:
```json
{
  "action": "health_check"
}
```
*Expected Output: `{"statusCode": 200, "body": "{\"success\": true, ...}"}`*

### Test 2: G3S (List LLM configurations)
**Function**: `aiforce-g3s`
**Event JSON**:
```json
{
  "action": "list_llm_configs",
  "payload": {
    "page_size": 5
  }
}
```

### Test 3: SGS (Scan Input Prompt)
**Function**: `aiforce-sgs`
**Event JSON**:
```json
{
  "action": "scan_prompt",
  "payload": {
    "prompt_name": "test_prompt",
    "input_prompt": "Hello AI, you are an idiot.",
    "security_group": "poc-security-group"
  }
}
```

### Test 4: GCS (Create a Trace)
**Function**: `aiforce-gcs`
**Event JSON**:
```json
{
  "action": "create_trace",
  "payload": {
    "name": "lambda-console-test",
    "session_id": "console-12345"
  }
}
```

---

## 3. Testing Datasets

You'll find mock CSVs in the `sample-csvs` directory for testing evaluating endpoints:

* **`gcs_prompt_dataset.csv`**: Basic prompt evaluations with `input`, `expected_output` columns. Use it with GCS Dataset Upload capabilities.
* **`gcs_rag_dataset.csv`**: RAG testing inputs (with `retrieved_context`).
* **`gcs_agent_dataset.csv`**: For testing tool usage outputs.
* **`pes_prompt_dataset.csv`**: For prompt compliance testing in PES.

## 4. Common Troubleshooting

* `HTTP 401 Unauthorized`: Ensure `AIFORCE_AUTH_TOKEN` is correct. The token might have expired.
* `Timeout on attempt`: The EC2 host `54.91.159.104` might be blocked by your network firewall. Ensure port 443 is accessible. Also increase Lambda timeout beyond the default 3 seconds (we recommend 30s).
* `"Unknown action"`: Verify your `action` string against the `actions` dictionary in the `lambda_handler` of the respective service.
* `boto3 AccessDeniedException`: For the orchestrator Bedrock tests, your AWS IAM Role/User requires `bedrock:InvokeModel` permissions.
