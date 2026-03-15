# Master Endpoint Testing Flow (AWS Lambda Console)

This guide provides a comprehensive, sequential testing flow for **all endpoints across all four AIForce foundational services**. 

By following this flow in the **AWS Lambda Console**, you will verify the complete lifecycle: configuring models (G3S) → setting up security (SGS) → managing prompts (PES) → tracking observability and compliance (GCS).

---

## Prerequisites
1. Open the [AWS Lambda Console](https://console.aws.amazon.com/lambda).
2. For each test, select the corresponding function (`aiforce-g3s`, `aiforce-sgs`, `aiforce-pes`, `aiforce-gcs`).
3. Go to the **Test** tab, create a new event, paste the JSON, and click **Test**.
4. **Important**: Note the IDs returned in earlier steps (like `config_id` or `prompt_id`), as you will need to insert them into the payloads of later steps.

---

## Phase 1: G3S (GenAI Gateway Service)
**Function Name:** `aiforce-g3s`  
*Goal: Health check, configure LLMs, Embeddings, and verify consumption.*

### 1.1 Health Check
```json
{ "action": "health_check" }
```

### 1.2 Save LLM Configuration
*Note: Save the `config_id` returned in the response for the next steps.*
```json
{
  "action": "save_llm_configuration",
  "payload": {
    "model_name": "claude-3-sonnet",
    "provider": "anthropic",
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0"
  }
}
```

### 1.3 List LLM Configurations
```json
{
  "action": "list_llm_configs",
  "payload": { "page": 1, "page_size": 10 }
}
```

### 1.4 Get Specific LLM Configuration
*Replace `1` with your actual LLM config_id.*
```json
{
  "action": "get_llm_config",
  "payload": { "llm_id": 1 }
}
```

### 1.5 Update LLM Configuration
```json
{
  "action": "update_llm_config",
  "payload": {
    "config_id": 1,
    "max_tokens": 4096
  }
}
```

### 1.6 Save & List Embedding Configuration
```json
{
  "action": "save_embedding_config",
  "payload": { "model_name": "titan-embed", "model_id": "amazon.titan-embed-text-v1" }
}
```
```json
{ "action": "list_embedding_configs", "payload": {} }
```

### 1.7 Save & List Speech Configuration
```json
{
  "action": "save_speech_config",
  "payload": { "model_name": "nova-micro", "model_id": "amazon.nova-micro-v1" }
}
```
```json
{ "action": "list_speech_configs", "payload": {} }
```

### 1.8 Direct LLM Call (via Gateway)
```json
{
  "action": "llm_call",
  "payload": {
    "lm_config_id": 1,
    "messages": [{"role": "user", "content": "Hello!"}]
  }
}
```

### 1.9 Check Token Consumption & Costs
```json
{
  "action": "get_consumption",
  "payload": { "date_filter": "last_7_days" }
}
```

### 1.10 Cleanup Configurations (Delete)
```json
{ "action": "delete_llm_config", "payload": { "config_id": 1 } }
```
```json
{ "action": "delete_embedding_config", "payload": { "config_id": 1 } }
```
```json
{ "action": "delete_speech_config", "payload": { "config_id": 1 } }
```

---

## Phase 2: SGS (Security Guardrails Service)
**Function Name:** `aiforce-sgs`  
*Goal: Create a security group, configure scanners, and test pre/post-flight scanning.*

### 2.1 Health Check & Token Context
```json
{ "action": "health_check" }
```
```json
{ "action": "get_token_context" }
```

### 2.2 Register Security Group
```json
{
  "action": "register_security_group",
  "payload": {
    "name": "master-poc-group",
    "description": "POC security scanning group"
  }
}
```

### 2.3 Configure Security Group Scanners
```json
{
  "action": "configure_security_group",
  "payload": {
    "group_name": "master-poc-group",
    "config": {
      "state": "active",
      "config_data": {
        "input_safety_guards": {
          "Detect PII": { "enabled": true, "config": { "redact": true } },
          "Detect Prompt Injection": { "enabled": true }
        }
      }
    }
  }
}
```

### 2.4 List & Get Security Groups
```json
{ "action": "list_security_groups", "payload": {} }
```
```json
{
  "action": "get_security_group_config",
  "payload": { "group_name": "master-poc-group", "view": "effective" }
}
```

### 2.5 Test Input Scanning (Pre-flight)
```json
{
  "action": "scan_prompt",
  "payload": {
    "prompt_name": "test_prompt",
    "input_prompt": "My phone number is 555-0199.",
    "security_group": "master-poc-group"
  }
}
```

### 2.6 Test Output Scanning (Post-flight)
```json
{
  "action": "scan_output",
  "payload": {
    "prompt_name": "test_prompt",
    "prompt": "What is my phone number?",
    "output": "Your number is 555-0199.",
    "security_group": "master-poc-group"
  }
}
```

### 2.7 Master Control & Scanners
```json
{ "action": "get_master_control" }
```
```json
{ "action": "get_master_scanners" }
```

### 2.8 Cleanup (Delete Group)
```json
{
  "action": "delete_security_group",
  "payload": { "group_name": "master-poc-group" }
}
```

---

## Phase 3: PES (Prompt Engineering Service)
**Function Name:** `aiforce-pes`  
*Goal: Manage the prompt lifecycle, test execution, and trigger compliance.*

### 3.1 Health Check
```json
{ "action": "health_check" }
```

### 3.2 Save Prompt
*Note: Save the returned `prompt_id` for following steps.*
```json
{
  "action": "save_prompt",
  "payload": {
    "name": "poc_greeting_v1",
    "user_prompt": "Hello {{NAME}}, welcome to {{COMPANY}}!",
    "system_prompt": "You are a friendly assistant.",
    "lm_config_id": 1,
    "variables": {"NAME": "string", "COMPANY": "string"}
  }
}
```

### 3.3 List & Get Prompt Details
```json
{ "action": "list_prompts", "payload": { "search": "poc_greeting" } }
```
```json
{
  "action": "get_prompt",
  "payload": { "prompt_id": 1 }
}
```

### 3.4 Update Prompt
```json
{
  "action": "update_prompt",
  "payload": {
    "prompt_id": 1,
    "system_prompt": "You are a very enthusiastic assistant!"
  }
}
```

### 3.5 Test & Execute Prompt
```json
{
  "action": "test_prompt",
  "payload": {
    "prompt_id": 1,
    "user_prompt": "Hello John, welcome to TechCorp!",
    "lm_config_id": 1
  }
}
```
```json
{
  "action": "execute_prompt",
  "payload": {
    "prompt_id": 1,
    "variables": {"NAME": "John", "COMPANY": "TechCorp"}
  }
}
```

### 3.6 Auto-Generate a Prompt
```json
{
  "action": "generate_prompt",
  "payload": { "description": "A prompt that translates English to French" }
}
```

### 3.7 Metrics & Dataset Evaluation
```json
{ "action": "get_metrics", "payload": { "applicability": "prompt" } }
```
```json
{ "action": "list_datasets", "payload": { "applicability": "prompt" } }
```

### 3.8 Prompt Compliance Scan
```json
{
  "action": "scan_compliance",
  "payload": { "prompt_id": 1 }
}
```
*(Check status using the `request_id` returned above)*
```json
{
  "action": "get_compliance_status",
  "payload": { "request_id": "YOUR_REQUEST_ID" }
}
```

### 3.9 Cleanup (Delete Prompt)
```json
{ "action": "delete_prompt", "payload": { "prompt_id": 1 } }
```

---

## Phase 4: GCS (Governance & Compliance Service)
**Function Name:** `aiforce-gcs`  
*Goal: Tracing, Observability, Datasets, and Validation.*

### 4.1 Health & Auth Check
```json
{ "action": "health_check" }
```
```json
{ "action": "check_auth" }
```

### 4.2 Metrics Management
```json
{ "action": "list_metrics", "payload": { "applicability": "llm" } }
```
```json
{ "action": "list_custom_metrics", "payload": {} }
```

### 4.3 Create a Trace & Log a Call
*Note: Save the `trace_id` returned.*
```json
{
  "action": "create_trace",
  "payload": {
    "name": "full-poc-trace",
    "session_id": "session-999"
  }
}
```
*Replace `YOUR_TRACE_ID` below:*
```json
{
  "action": "log_llm_call",
  "payload": {
    "trace_id": "YOUR_TRACE_ID",
    "input": "Hello",
    "output": "Hi there!",
    "model": "claude-3",
    "input_tokens": 10,
    "output_tokens": 5,
    "latency_ms": 450
  }
}
```
```json
{
  "action": "add_event",
  "payload": {
    "trace_id": "YOUR_TRACE_ID",
    "event_name": "security_scan_passed",
    "event_data": {"score": 0.99}
  }
}
```

### 4.4 Retrieve Traces
```json
{ "action": "list_traces", "payload": { "hours": 24 } }
```
```json
{
  "action": "get_trace",
  "payload": { "trace_id": "YOUR_TRACE_ID" }
}
```

### 4.5 Dataset Management
```json
{
  "action": "create_dataset",
  "payload": {
    "name": "poc-validation-set",
    "use_case_type": "rag"
  }
}
```
```json
{ "action": "list_datasets", "payload": {} }
```

### 4.6 Validation Endpoints (Prompt/RAG/Agent)
```json
{
  "action": "validate_prompt",
  "payload": {
    "dataset_id": 1,
    "metrics": ["toxicity", "relevance"]
  }
}
```

### 4.7 Compliance Guidelines
```json
{ "action": "list_compliance_guidelines", "payload": {} }
```

### 4.8 Cleanup (Delete Trace & Dataset)
```json
{ "action": "delete_trace", "payload": { "trace_id": "YOUR_TRACE_ID" } }
```
```json
{ "action": "delete_dataset", "payload": { "name": "poc-validation-set" } }
```

---
**End of Master Testing Flow.** By executing these payloads sequentially in the AWS Lambda Console, you will have successfully tested all CRUD operations, execution pathways, and observability hooks for the entire API suite.
