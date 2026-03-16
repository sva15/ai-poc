# AIForce POC — Prerequisites Setup

Before deploying the Lambda function, run these `curl` commands to set up prompts and security groups in the AIForce platform.

> **Replace** `YOUR_TOKEN` with your actual AIForce Bearer token.
> **Base URL**: `https://54.91.159.104`

---

## Step 1: Health Checks

Verify all services are running:

```bash
# PES Health
curl -k -X GET "https://54.91.159.104/check_health" \
  -H "Authorization: Bearer YOUR_TOKEN"

# SGS Health
curl -k -X GET "https://54.91.159.104/sgs/check_health" \
  -H "Authorization: Bearer YOUR_TOKEN"

# GCS Health
curl -k -X GET "https://54.91.159.104/check_health" \
  -H "Authorization: Bearer YOUR_TOKEN"

# G3S Health
curl -k -X GET "https://54.91.159.104/g3s/check_health" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Step 2: Get LLM Config ID from G3S

You need a valid `lm_config_id` to save prompts. List available configs:

```bash
curl -k -X GET "https://54.91.159.104/g3s/configuration/list_llm_configuration?page=1&page_size=10" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept: application/json"
```

**Note down** the `id` field from the response — you'll use it as `lm_config_id` in the next steps.

---

## Step 3: Create Prompt A — Customer Support (Safe Prompt)

This prompt uses variables `{{COMPANY}}` and `{{QUESTION}}`:

```bash
curl -k -X POST "https://54.91.159.104/pes/prompt_studio/save_prompt" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=poc_customer_support" \
  -d "user_prompt=You are a helpful customer support assistant for {{COMPANY}}. A customer asks: {{QUESTION}}. Please provide a clear and professional response." \
  -d "system_prompt=You are a professional customer support agent. Be concise, empathetic, and solution-oriented." \
  -d "lm_config_id=1" \
  -d "publish_status=true" \
  -d "is_public=false" \
  -d "version=1.0" \
  -d 'varriables={"COMPANY":"string","QUESTION":"string"}' \
  -d 'lm_params={"temperature":0.7,"max_token":1024}'
```

> **Note**: The field is spelled `varriables` (with double 'r') — this matches the AIForce API spec.

**Save the `prompt_id`** from the response — you'll use it in test scenarios.

---

## Step 4: Create Prompt B — PII Test Prompt

This prompt is designed to generate output that may contain PII (to test output scanning):

```bash
curl -k -X POST "https://54.91.159.104/pes/prompt_studio/save_prompt" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "name=poc_pii_test" \
  -d "user_prompt=Write a short example customer profile for {{NAME}} including their email, phone number, and a brief account summary." \
  -d "system_prompt=You are a data entry assistant. Create realistic sample customer profiles with contact details." \
  -d "lm_config_id=1" \
  -d "publish_status=true" \
  -d "is_public=false" \
  -d "version=1.0" \
  -d 'varriables={"NAME":"string"}' \
  -d 'lm_params={"temperature":0.7,"max_token":512}'
```

**Save the `prompt_id`** from the response.

---

## Step 5: Verify Prompts Were Created

```bash
curl -k -X GET "https://54.91.159.104/pes/prompt_studio/list_prompt?page=1&page_size=10" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept: application/json"
```

You should see both `poc_customer_support` and `poc_pii_test` in the list.

---

## Step 6: Register Security Group in SGS

```bash
curl -k -X POST "https://54.91.159.104/sgs/security-groups/register" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "poc-security-group",
    "description": "POC security group for input and output scanning with PII, toxicity, and prompt injection detection"
  }'
```

---

## Step 7: Configure Scanners on the Security Group

```bash
curl -k -X PUT "https://54.91.159.104/sgs/security-groups/poc-security-group/config" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "state": "active",
    "config_data": {
      "input_safety_guards": {
        "Detect PII": {
          "enabled": true,
          "config": {
            "entity_types": ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD", "US_SSN"],
            "redact": true,
            "threshold": 0.6
          }
        },
        "Detect Prompt Injection": {
          "enabled": true,
          "config": { "threshold": 0.7 }
        },
        "Detect Toxicity": {
          "enabled": true,
          "config": { "threshold": 0.8 }
        }
      },
      "output_safety_guards": {
        "Detect PII": {
          "enabled": true,
          "config": {
            "entity_types": ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"],
            "redact": true,
            "threshold": 0.6
          }
        },
        "Detect Toxicity": {
          "enabled": true,
          "config": { "threshold": 0.8 }
        }
      }
    }
  }'
```

---

## Step 8: Verify Security Group Configuration

```bash
# List all groups
curl -k -X GET "https://54.91.159.104/sgs/security-groups/list" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get specific group config
curl -k -X GET "https://54.91.159.104/sgs/security-groups/poc-security-group/config?view=effective" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Summary of IDs to Note

After completing the steps above, note down these values — you'll need them for the Lambda:

| Item | Where to Find |
|------|---------------|
| `lm_config_id` | Step 2 response → `id` field |
| Prompt A `prompt_id` | Step 3 response → `prompt_id` or `id` field |
| Prompt B `prompt_id` | Step 4 response → `prompt_id` or `id` field |
| Security Group Name | `poc-security-group` (created in Step 6) |

These IDs will be used in the Lambda test events (see `03-testing-guide.md`).
