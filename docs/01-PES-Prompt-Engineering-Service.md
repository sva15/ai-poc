# PES — Prompt Engineering Service (Complete Guide)

> **Base URL:** `https://54.91.159.104/pes`  
> **Auth:** All endpoints require `Authorization: Bearer <token>`  
> **Version:** 2.0.1

---

## What is PES?

PES is your **centralized prompt management system**. Think of it as replacing your database for storing prompts — instead of manually storing prompts in a DB table and retrieving them to send to Bedrock, PES gives you:

- ✅ A **versioned prompt store** where you save, update, and retrieve prompts
- ✅ **Domain-based grouping** via the `is_public` flag (public collection = shared across projects, private = project-specific)
- ✅ **Prompt lifecycle** — save → test → evaluate → execute → compliance scan
- ✅ **Variable templating** — store prompts with `{{VARIABLE}}` placeholders, inject values at runtime
- ✅ **Direct LLM execution** — execute prompts directly through PES (which routes through G3S to your Bedrock model)

### How PES Replaces Your Database for Prompts

| Before (Your DB) | Now (PES) |
|---|---|
| Store prompt text in a DB table | `POST /save_prompt` — stores with versioning, metadata |
| Query DB to get a prompt | `GET /get_prompt_details/{id}` — retrieves full prompt with config |
| Manually send to Bedrock SDK | `POST /execute_prompt` — PES sends to Bedrock via G3S gateway |
| No versioning | Built-in `version` + `parent_prompt_id` for lineage |
| No testing | `POST /test_prompt` — test before publishing |
| No grouping | `is_public` + `publish_status` + search/filter |

### How to Group Prompts by Domain

PES supports grouping through these mechanisms:

1. **`is_public` flag** — `true` = shared (public collection), `false` = project-specific (private)
2. **Naming conventions** — Use prefixes like `healthcare_`, `finance_`, `legal_` in prompt names
3. **`search` filter on list** — Filter prompts by domain prefix when listing
4. **`publish_status`** — `true` = production-ready, `false` = draft/experimental
5. **Projects** — Each project in AIForce acts as a top-level domain boundary (prompts are scoped to projects via your auth token)

**Example Domain Organization:**
```
Project: "Healthcare App"
  ├── healthcare_diagnosis_v1 (published, private)
  ├── healthcare_summarizer_v2 (published, public — shared)
  └── healthcare_triage_draft (draft, private)

Project: "Finance App"
  ├── finance_risk_assessment_v1 (published, private)
  ├── finance_fraud_detector_v1 (published, private)
  └── finance_report_gen_draft (draft, private)
```

---

## Endpoint-by-Endpoint Flow & Use Cases

---

### 1. `POST /pes/prompt_studio/save_prompt`

**What it does:** Creates and saves a new prompt with all its configuration.

**Content-Type:** `application/x-www-form-urlencoded`

**Key Inputs:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ | Prompt name (use domain prefix!) |
| `user_prompt` | string | ✅ | The actual prompt text with `{{variables}}` |
| `system_prompt` | string | ❌ | System instructions for the LLM |
| `lm_config_id` | int | ✅ | Which LLM config to use (from G3S) |
| `examples` | JSON string | ❌ | Few-shot examples |
| `lm_params` | JSON string | ❌ | Advanced params like `{"temperature": 0.7, "max_token": 2048}` |
| `mcp_enabled` | bool | ❌ | Enable Model Context Protocol |
| `is_public` | bool | ❌ | `true` = shared across projects |
| `publish_status` | bool | ✅ | `true` = published, `false` = draft |
| `version` | string | ❌ | Version tag like "v1.0" |
| `parent_prompt_id` | int | ❌ | Link to parent prompt for versioning chain |
| `varriables` | JSON string | ❌ | Define variable names and types |
| `evaluation` | JSON string | ❌ | Evaluation config |

**Use Cases:**
1. **Store a customer support prompt** — Save a templated prompt like "You are a support agent for {{COMPANY}}. Help with: {{ISSUE}}" with temperature=0.3
2. **Create a healthcare diagnosis template** — Store a medical summarization prompt as private, linked to a specific Bedrock Claude config
3. **Version a prompt** — Save v2 of an existing prompt by setting `parent_prompt_id` to the v1 prompt ID
4. **Create a shared prompt library** — Set `is_public=true` so other projects can reuse your finance report template
5. **Draft an experimental prompt** — Set `publish_status=false` to save a work-in-progress prompt

**Flow:**
```
Your App → POST /save_prompt (name, user_prompt, lm_config_id, ...)
         → PES saves to DB with project/org context from your token
         → Returns: { prompt_id, name, version, created_at }
```

---

### 2. `GET /pes/prompt_studio/list_prompt`

**What it does:** Lists all prompts with filtering and pagination.

**Key Inputs:**
| Param | Type | Description |
|-------|------|-------------|
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 10, 0 = all) |
| `search` | string | Filter by name (alphanumeric, max 255 chars) |
| `is_public` | bool | Filter public/private prompts |
| `publish_status` | bool | Filter published/draft |

**Use Cases:**
1. **List all healthcare prompts** — `GET /list_prompt?search=healthcare&publish_status=true`
2. **Browse shared prompt library** — `GET /list_prompt?is_public=true`
3. **Find all drafts** — `GET /list_prompt?publish_status=false`
4. **Paginate large prompt collections** — `GET /list_prompt?page=2&page_size=20`
5. **Application startup** — Load all published prompts for a specific domain into a cache

---

### 3. `GET /pes/prompt_studio/get_prompt_details/{prompt_id}`

**What it does:** Retrieves the full prompt object with all config, variables, examples.

**Use Cases:**
1. **Retrieve prompt to send to Bedrock** — Get full prompt text + system prompt + LLM config to construct your Bedrock request
2. **Display prompt in a UI** — Show prompt details in an admin dashboard
3. **Clone a prompt** — Retrieve details of an existing prompt, modify, and save as a new version
4. **Audit trail** — Check what prompt was used for a specific interaction

**Flow (Replace Database Pattern):**
```
Your App → GET /get_prompt_details/42
         → Returns: { name, user_prompt, system_prompt, lm_config_id, variables, ... }
         → Your App takes user_prompt, substitutes variables
         → Calls POST /execute_prompt OR directly calls Bedrock with the retrieved prompt
```

---

### 4. `POST /pes/prompt_studio/test_prompt`

**What it does:** Runs a prompt against the configured LLM without saving/executing. Think of it as a "dry run."

**Content-Type:** `application/x-www-form-urlencoded`

**Key Inputs:**
| Field | Required | Description |
|-------|----------|-------------|
| `user_prompt` | ✅ | The prompt text to test |
| `system_prompt` | ❌ | System instructions |
| `lm_config_id` | ✅ | LLM config ID |
| `lm_params` | ❌ | JSON with temperature, max_token, format |
| `mcp_enabled` | ❌ | Enable MCP |
| `varriables` | ❌ | Variable values as JSON |
| `promptId` | ✅ | Prompt ID to test |

**Use Cases:**
1. **Iterate on prompt wording** — Test different phrasings before publishing
2. **Compare model outputs** — Test the same prompt with different `lm_config_id` values (GPT-4 vs Claude)
3. **Validate variable substitution** — Ensure `{{NAME}}` and `{{CONTEXT}}` render correctly
4. **A/B test prompts** — Compare v1 vs v2 of a prompt side by side
5. **Demo to stakeholders** — Test prompts in a safe sandbox before going live

---

### 5. `POST /pes/prompt_studio/generate_prompt`

**What it does:** Auto-generates a prompt based on a description. Uses LLM to create the prompt for you.

**Content-Type:** `application/json` (PromptGenerateRequest)

**Use Cases:**
1. **Kickstart prompt engineering** — Describe what you need: "Generate a prompt for summarizing medical records" → PES creates a well-structured prompt
2. **Non-technical users** — Let business users describe their need in plain English; PES generates the technical prompt
3. **Prompt ideation** — Generate multiple prompt variants to compare

---

### 6. `POST /pes/prompt_studio/execute_prompt`

**What it does:** Executes a saved prompt with variable injection. This is the **primary production endpoint** — replaces your direct Bedrock calls.

**Content-Type:** `application/json` (ExecutePromptRequest)

**Use Cases:**
1. **Production LLM calls** — Execute `finance_risk_assessment_v1` with `{"company": "Acme Corp", "data": "..."}` variables
2. **Chatbot backend** — Retrieve a conversational prompt and execute with user's message as a variable
3. **Batch processing** — Loop through records, executing the same prompt with different variable values
4. **Microservice integration** — Any Lambda/service can call this endpoint instead of managing Bedrock SDK directly

**Flow:**
```
Your App → POST /execute_prompt
           { "prompt_id": 42, "variables": {"CUSTOMER": "John", "ISSUE": "billing"} }
         → PES retrieves prompt from store
         → Substitutes {{CUSTOMER}} and {{ISSUE}}
         → Routes through G3S to Bedrock/Claude/GPT
         → Returns: { response, trace_id, token_usage }
```

---

### 7. `GET /pes/prompt_studio/metrics`

**What it does:** Fetches available evaluation metrics from GCS (the compliance service).

**Key Inputs:** `applicability` (default: "prompt"), `state`, `custom`, `llm-based`

**Use Cases:**
1. **Discover available metrics** — List all metrics you can use to evaluate your prompts
2. **Filter for prompt-specific metrics** — `?applicability=prompt&state=active`
3. **Find LLM-based vs rule-based metrics** — `?llm-based=true` or `?llm-based=false`

---

### 8. `GET /pes/prompt_studio/datasets`

**What it does:** Lists all datasets available for prompt evaluation.

**Use Cases:**
1. **Find test datasets** — See what evaluation datasets are available
2. **Filter by type** — `?applicability=llm` for LLM evaluation datasets

---

### 9. `POST /pes/prompt_studio/datasets/upload`

**What it does:** Uploads a CSV/Excel dataset for prompt evaluation.

**Content-Type:** `multipart/form-data`

**Use Cases:**
1. **Upload golden test set** — Upload a CSV with input/expected_output pairs for regression testing
2. **Create domain-specific test data** — Upload healthcare Q&A pairs to evaluate healthcare prompts

> 📄 See `sample-csvs/pes_prompt_dataset.csv` for the required format.

---

### 10. `POST /pes/prompt_studio/evaluate_prompt_dataset`

**What it does:** Runs a prompt against a dataset using configured evaluation metrics. Returns a `request_id` (async).

**Content-Type:** `application/json` (PromptDatasetValidationRequest)

**Use Cases:**
1. **Regression testing** — Evaluate your prompt against 100 test cases before deploying a new version
2. **Quality benchmarking** — Score prompts on factual correctness, relevance, toxicity
3. **Compare prompt versions** — Run v1 and v2 against the same dataset, compare scores
4. **CI/CD integration** — Automatically evaluate prompts in your deployment pipeline

**Flow:**
```
POST /evaluate_prompt_dataset → Returns { request_id: "abc-123" }
  ↓ (polling)
GET /evaluation_status/abc-123 → Returns { status: "running" }
GET /evaluation_status/abc-123 → Returns { status: "completed", results: [...] }
```

---

### 11. `GET /pes/prompt_studio/trace/logs/{trace_id}`

**What it does:** Fetches detailed trace logs for a specific execution.

**Use Cases:**
1. **Debug a failed execution** — See exactly what was sent to the LLM and what came back
2. **Audit trail** — Review the full request/response chain for compliance
3. **Performance analysis** — Check token usage, latency for specific executions

---

### 12. `GET /pes/prompt_studio/evaluation_status/{request_id}`

**What it does:** Polls the status of an async evaluation job.

**Use Cases:**
1. **Check evaluation progress** — Poll until status changes from "running" to "completed"
2. **Build status dashboards** — Show evaluation progress in a UI

---

### 13. `POST /pes/prompt_studio/compliance/scan-compliance`

**What it does:** Scans a prompt for compliance with regulations (GDPR, HIPAA, etc.). Async operation.

**Use Cases:**
1. **Pre-deployment compliance check** — Scan prompts for regulatory compliance before going live
2. **Healthcare domain** — Ensure prompts handling PHI are HIPAA-compliant
3. **Finance domain** — Verify prompts meet financial regulatory requirements

---

### 14. `GET /pes/prompt_studio/compliance/compliance-status/{request_id}`

**What it does:** Polls compliance scan status (poll every 5 seconds until final response).

**Use Cases:**
1. **Wait for compliance result** — Poll until scan completes
2. **Gate deployments** — Block prompt deployment until compliance scan passes

---

### 15. `PUT /pes/prompt_studio/update_prompt/{prompt_id}`

**What it does:** Updates an existing prompt's fields.

**Use Cases:**
1. **Fix a typo** in a production prompt without creating a new version
2. **Change LLM config** — Switch from Claude 2 to Claude 3 by updating `lm_config_id`
3. **Publish a draft** — Set `publish_status=true` on a previously drafted prompt
4. **Update system prompt** — Refine the system instructions

---

### 16. `DELETE /pes/prompt_studio/delete_prompt`

**What it does:** Permanently deletes a prompt.

**Use Cases:**
1. **Clean up drafts** — Remove abandoned experimental prompts
2. **Remove deprecated versions** — Delete v1 after v2 is stable
3. **Data hygiene** — Remove prompts that are no longer needed

---

### 17. `GET /check_health`

**What it does:** Returns `{"status": "OK"}` if PES is running.

**Use Cases:**
1. **Health monitoring** — Include in your monitoring/alerting stack
2. **Load balancer health checks** — Configure ALB/NLB to check this endpoint

---

## Complete Flow: Prompt Management with PES + Bedrock

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. SETUP (One-time)                                         │
│     ├── List LLM configs from G3S → GET /g3s/configuration/list_llm_configuration
│     ├── Save prompt to PES      → POST /pes/prompt_studio/save_prompt
│     │     name: "healthcare_diagnosis_v1"                    │
│     │     user_prompt: "Analyze patient {{SYMPTOMS}}..."     │
│     │     lm_config_id: 42  (your Bedrock Claude config)     │
│     │     is_public: false                                   │
│     │     publish_status: true                               │
│     └── Upload test dataset     → POST /pes/prompt_studio/datasets/upload
│                                                              │
│  2. TESTING (Before go-live)                                 │
│     ├── Test prompt             → POST /pes/prompt_studio/test_prompt
│     ├── Evaluate on dataset     → POST /pes/prompt_studio/evaluate_prompt_dataset
│     ├── Poll evaluation         → GET /pes/prompt_studio/evaluation_status/{id}
│     └── Compliance scan         → POST /pes/prompt_studio/compliance/scan-compliance
│                                                              │
│  3. PRODUCTION (Runtime)                                     │
│     ├── List domain prompts     → GET /pes/prompt_studio/list_prompt?search=healthcare
│     ├── Get prompt details      → GET /pes/prompt_studio/get_prompt_details/42
│     ├── Execute with variables  → POST /pes/prompt_studio/execute_prompt
│     │     { prompt_id: 42, variables: { SYMPTOMS: "..." } }  │
│     └── View trace logs         → GET /pes/prompt_studio/trace/logs/{trace_id}
│                                                              │
└─────────────────────────────────────────────────────────────┘
```
