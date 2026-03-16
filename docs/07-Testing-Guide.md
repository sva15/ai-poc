# AIForce POC — Testing Guide

This guide covers how to test your AIForce POC components, from running the local orchestrator to testing the individual AWS Lambda functions you deployed.

---

## 1. Testing the Full End-to-End POC Flow (AWS Lambda Console)

The `orchestrator.py` has been adapted to run entirely within a single AWS Lambda function. This simulates a real-world flow from setup, configuration to prompt execution, and cost tracking.

### Prerequisites
You must have deployed the `aiforce-poc-orchestrator` Lambda function as described in **Step 5** of the [Deployment Guide](06-Deployment-Guide.md), including setting the environment variables (`AIFORCE_AUTH_TOKEN`, `AWS_REGION`, etc.).

### Running the Orchestrator

1. Open the [AWS Lambda Console](https://console.aws.amazon.com/lambda).
2. Navigate to your `aiforce-poc-orchestrator` function.
3. Select the **Test** tab.
4. Create a new test event with the following JSON payload (you can customize the question and company):

```json
{
  "question": "How do I reset my account password?",
  "company": "TechCorp Solutions"
}
```

5. Click **Save** and then **Test**.

### Expected Execution Log Output
The Lambda response will contain a `logs` string that captures the complete stdout flow. It will look like this:

* **Phase 1 (Setup):** Health checks pass (✅), LLM configs listed, Prompt saved, SGS config complete.
* **Phase 2 (Execute):** Shows Direct Bedrock interaction for the specific question you asked in the Test Event. Input & Output tokens consumed should be visible along with Security scan checkpoints.
* **Phase 4 (Cost Report):** Cost of the executed query + historical G3S platform-wide data + recent GCS trace summaries.

*If any step fails, you'll see a `⚠️` or `❌` in the logs indicating which service or payload failed.*

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
