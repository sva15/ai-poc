# AIForce Platform — Master Overview & Cross-Service Flows

> This document explains how all four foundational services work together.  
> Read the individual service guides for endpoint-level details.

---

## Service Summary

| Service | Role | Analogy |
|---------|------|---------|
| **G3S** | AI Gateway — Routes all LLM/Embedding/Speech calls | API Gateway |
| **PES** | Prompt Workbench — Store, test, execute, evaluate prompts | Prompt Database + IDE |
| **SGS** | Security Firewall — Scans input/output for safety issues | WAF for LLM traffic |
| **GCS** | Quality & Compliance — Metrics, validation, datasets, observability | QA + Compliance team |

---

## How They Connect

```
┌──────────────────────────────────────────────────────────────────┐
│                      YOUR APPLICATION                            │
│                                                                  │
│  Store prompts ──→ PES (Prompt Engineering Service)              │
│                      │                                           │
│                      ├── Scans input ──→ SGS (Security)          │
│                      │                    │                      │
│                      │                    └── is_safe? → Yes     │
│                      │                                           │
│                      ├── Calls LLM ──→ G3S (AI Gateway)          │
│                      │                    │                      │
│                      │                    └── Routes to Bedrock   │
│                      │                                           │
│                      ├── Scans output ──→ SGS (Security)         │
│                      │                                           │
│                      └── Returns response to your app            │
│                                                                  │
│  Evaluate quality ──→ GCS (Governance & Compliance)              │
│                      │                                           │
│                      ├── Runs metrics (accuracy, relevance)      │
│                      ├── Logs traces (full audit trail)          │
│                      └── Compliance scanning                     │
│                                                                  │
│  Track costs ──→ G3S (Model Consumption API)                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## Real-World Use Case Flows

---

### Use Case 1: "Customer Support Chatbot"

**Goal:** Build a chatbot that answers customer questions safely and accurately.

**Endpoints used (in order):**

| Step | Service | Endpoint | What Happens |
|------|---------|----------|--------------|
| 1 | G3S | `POST /configuration/save_llm_configuration` | Register your Bedrock Claude model |
| 2 | SGS | `POST /security-groups/register` | Create "support-bot" security group |
| 3 | SGS | `PUT /security-groups/support-bot/config` | Enable PII detection (redact=true), toxicity, prompt injection |
| 4 | PES | `POST /prompt_studio/save_prompt` | Save: "You are a helpful support agent for {{COMPANY}}. Answer: {{QUESTION}}" |
| 5 | PES | `POST /prompt_studio/test_prompt` | Test with sample questions |
| 6 | GCS | `POST /datasets/upload` | Upload 50 Q&A test pairs (CSV) |
| 7 | PES | `POST /prompt_studio/evaluate_prompt_dataset` | Evaluate prompt on test dataset |
| 8 | PES | `GET /prompt_studio/evaluation_status/{id}` | Poll until evaluation completes |
| **RUNTIME** | | | |
| 9 | SGS | `POST /sgs/scan/prompt` | Scan user question for PII/injection |
| 10 | PES | `POST /prompt_studio/execute_prompt` | Execute the stored prompt with user's question |
| 11 | SGS | `POST /sgs/scan/output` | Scan bot response for safety |
| 12 | GCS | `POST /logs/trace/create` | Create audit trace |
| 13 | GCS | `POST /logs/trace/llm_call` | Log the LLM call details |

---

### Use Case 2: "RAG-Based Knowledge Assistant"

**Goal:** Answer questions using company documents (vector search + LLM).

| Step | Service | Endpoint | What Happens |
|------|---------|----------|--------------|
| 1 | G3S | `POST /configuration/save_embedding_configuration` | Register Titan Embedding model |
| 2 | G3S | `POST /configuration/save_llm_configuration` | Register Claude for answering |
| 3 | G3S | `POST /llm/embeddings` | Embed all documents → store in VectorDB |
| 4 | PES | `POST /prompt_studio/save_prompt` | Save RAG prompt: "Using this context: {{CONTEXT}}, answer: {{QUESTION}}" |
| 5 | GCS | `POST /datasets/upload` | Upload RAG test dataset (with context column) |
| 6 | GCS | `POST /validate/rag` | Validate RAG pipeline quality (faithfulness, context relevancy) |
| **RUNTIME** | | | |
| 7 | G3S | `POST /llm/embeddings` | Embed user question |
| 8 | — | VectorDB search | Find similar documents (your infra) |
| 9 | SGS | `POST /sgs/scan/prompt` | Scan question + context for safety |
| 10 | G3S | `POST /llm/call` | Send context + question to Claude |
| 11 | SGS | `POST /sgs/scan/output` | Scan answer for safety |
| 12 | GCS | `POST /logs/trace/create` + `llm_call` + `embedding-search` | Full observability |

---

### Use Case 3: "Automated Report Generator"

**Goal:** Generate financial/medical reports from structured data.

| Step | Service | Endpoint | What Happens |
|------|---------|----------|--------------|
| 1 | PES | `POST /prompt_studio/save_prompt` | Save: "Generate a {{REPORT_TYPE}} report for {{COMPANY}} using: {{DATA}}" |
| 2 | PES | `POST /prompt_studio/test_prompt` | Test with sample data |
| 3 | PES | `POST /prompt_studio/compliance/scan-compliance` | Scan prompt for regulatory compliance |
| 4 | GCS | `POST /custom/metrics/` | Create custom metric: "report_formatting_score" |
| 5 | GCS | `POST /datasets/upload` | Upload test data + expected reports |
| 6 | GCS | `POST /validate/prompt` | Validate formatting, accuracy |
| **RUNTIME** | | | |
| 7 | SGS | `POST /sgs/scan/prompt` | Scan input data for PII |
| 8 | PES | `POST /prompt_studio/execute_prompt` | Generate report |
| 9 | SGS | `POST /sgs/scan/output` | Scan report for leaked secrets/PII |
| 10 | GCS | `POST /logs/trace/create` | Audit trail |

---

### Use Case 4: "Multi-Tenant AI Platform"

**Goal:** Serve multiple clients from one platform with isolated security.

| Step | Service | Endpoint | What Happens |
|------|---------|----------|--------------|
| 1 | SGS | `PUT /security-groups/config-control` | Set `enforce_scanner_state=true` (global policy) |
| 2 | SGS | `POST /security-groups/register` × N | Create per-client groups: "client-acme", "client-globex" |
| 3 | SGS | `PUT /security-groups/client-acme/config` | Acme: strict PII, block competitor names |
| 4 | SGS | `PUT /security-groups/client-globex/config` | Globex: relaxed PII, allow code output |
| 5 | G3S | `POST /configuration/save_llm_configuration` × N | Per-client model configs (cost tiers) |
| 6 | PES | `POST /prompt_studio/save_prompt` × N | Client-specific prompts (private, per project) |
| **RUNTIME** | | | |
| 7 | SGS | `POST /sgs/scan/prompt` | Use client's security group for scanning |
| 8 | PES | `POST /prompt_studio/execute_prompt` | Execute client's prompt with their LLM config |
| 9 | G3S | `GET /model-consumption/consumption` | Track per-client costs: `?project_id=acme_project` |

---

### Use Case 5: "AI Governance & Compliance Audit"

**Goal:** Continuously monitor AI quality and maintain compliance.

| Step | Service | Endpoint | What Happens |
|------|---------|----------|--------------|
| 1 | GCS | `GET /config/metrics/` | Review all available evaluation metrics |
| 2 | GCS | `PUT /config/metric_config/hallucination` | Set hallucination threshold to 0.9 (strict) |
| 3 | GCS | `POST /custom/metrics/` | Create "medical_accuracy" custom metric |
| 4 | GCS | `POST /datasets/create` + `upload` | Upload golden test dataset |
| 5 | GCS | `POST /validate/prompt` | Run weekly evaluation of all production prompts |
| 6 | GCS | `GET /validate/evaluation-status` | Get results |
| 7 | GCS | `GET /compliance/compliance-guidelines` | Review compliance frameworks |
| 8 | GCS | `POST /compliance/scan-compliance` | Scan prompts against regulatory standards |
| 9 | GCS | `GET /logs/` | Review all traces for the last 30 days |
| 10 | G3S | `GET /model-consumption/consumption` | Cost audit |

---

## Sample CSV Files

The following test CSVs are included for testing endpoints that require file uploads:

| File | Columns | Use With |
|------|---------|----------|
| `sample-csvs/gcs_prompt_dataset.csv` | `input`, `expected_output` | `POST /validate/prompt` and `POST /datasets/upload` (use_case_type=prompt) |
| `sample-csvs/gcs_rag_dataset.csv` | `input`, `retrieved_context`, `expected_output` | `POST /validate/rag` and `POST /datasets/upload` (use_case_type=rag) |
| `sample-csvs/gcs_agent_dataset.csv` | `input`, `expected_output`, `actual_output`, `tool_data` | `POST /validate/agent` and `POST /datasets/upload` (use_case_type=agent) |
| `sample-csvs/pes_prompt_dataset.csv` | `input`, `expected_output` | `POST /pes/prompt_studio/datasets/upload` and `POST /pes/prompt_studio/evaluate_prompt_dataset` |

---

## Quick Reference: Which Endpoint Do I Need?

| I want to... | Service | Endpoint |
|---|---|---|
| Call an LLM | G3S | `POST /g3s/llm/call` |
| Generate embeddings | G3S | `POST /g3s/llm/embeddings` |
| Store a prompt | PES | `POST /pes/prompt_studio/save_prompt` |
| Retrieve a prompt | PES | `GET /pes/prompt_studio/get_prompt_details/{id}` |
| Execute a stored prompt | PES | `POST /pes/prompt_studio/execute_prompt` |
| List all prompts | PES | `GET /pes/prompt_studio/list_prompt` |
| Scan input for PII/safety | SGS | `POST /sgs/scan/prompt` |
| Scan output for safety | SGS | `POST /sgs/scan/output` |
| Create a security group | SGS | `POST /sgs/security-groups/register` |
| Configure scanners | SGS | `PUT /sgs/security-groups/{name}/config` |
| Evaluate prompt quality | GCS | `POST /validate/prompt` |
| Evaluate RAG quality | GCS | `POST /validate/rag` |
| Create a test dataset | GCS | `POST /datasets/create` |
| Upload test data | GCS | `POST /datasets/upload` |
| Create an audit trace | GCS | `POST /logs/trace/create` |
| View all traces | GCS | `GET /logs/` |
| Check compliance | GCS | `POST /compliance/scan-compliance` |
| Track model costs | G3S | `GET /g3s/model-consumption/consumption` |
| Health check any service | ALL | `GET /check_health` |
