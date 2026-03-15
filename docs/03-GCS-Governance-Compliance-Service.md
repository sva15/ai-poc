# GCS — Governance, Risk & Compliance Service (Complete Guide)

> **Base URL:** `https://54.91.159.104/gcs`  
> **Auth:** All endpoints require `Authorization: Bearer <token>` (except health check and root)  
> **Version:** 2.0.1

---

## What is GCS?

GCS is the **quality and compliance engine** for your AI applications. It ensures your LLM outputs are:
- **Accurate** — Factual correctness, relevance checks
- **Auditable** — Full observability traces for every LLM call
- **Compliant** — Regulatory compliance scanning (GDPR, HIPAA, SOC2, etc.)
- **Measurable** — Configurable evaluation metrics with pass/fail thresholds

**Think of GCS as:**
- Your AI quality assurance team (automated)
- Your compliance auditor (always on)
- Your observability platform (traces + logs)
- Your test framework (datasets + evaluations)

---

## Service Modules

GCS is organized into **7 modules**: Registration, Metric Config, Custom Metrics, Validation, Dataset Management, Logs/Observability, and Testing.

---

## Module 1: Registration

### `GET /register/protected-resource`

**What it does:** Validates your bearer token and confirms access.

**Use Cases:**
1. **Auth test** — Verify your token works before making other calls
2. **Connection check** — Test that your service can reach GCS
3. **Token debugging** — Confirm your token has the right org/project context

---

## Module 2: Metric Configuration

### `GET /config/metrics/`

**What it does:** Lists all available evaluation metrics with filters.

**Key Inputs:**
| Param | Description |
|-------|-------------|
| `metricsName` | Search by metric name |
| `applicability` | Filter: `llm` or `nonllm` |
| `state` | Filter: `active` or `inactive` |
| `llm_based` | `true` = LLM-judge metrics, `false` = script-based |
| `custom` | `true` = custom metrics only |
| `page`, `limit` | Pagination |

**Use Cases:**
1. **Discover built-in metrics** — See what metrics are available (factual_correctness, relevance, toxicity, hallucination, coherence, etc.)
2. **Filter for prompt metrics** — `?applicability=llm&state=active` to see active LLM metrics
3. **Find custom vs built-in** — `?custom=true` to list only your custom-defined metrics
4. **LLM-judge metrics** — `?llm_based=true` to find metrics that use an LLM to evaluate (as opposed to regex/script)
5. **Admin dashboard** — Populate a metrics management UI

**Built-in Metrics include:**
- `factual_correctness` — Does the output match known facts?
- `answer_relevancy` — Is the response relevant to the question?
- `hallucination` — Does the output contain fabricated info?
- `coherence` — Is the output logically consistent?
- `toxicity` — Does the output contain harmful content?
- `context_relevancy` — (RAG) Is the retrieved context relevant?
- `faithfulness` — (RAG) Is the answer grounded in the context?

---

### `PUT /config/metric_config/{metric_name}`

**What it does:** Updates a metric's configuration (threshold, state, applicability).

**Key Inputs:** `metric_name` (path), `applicability` (query), body: `MetricConfigUpdate`

**Use Cases:**
1. **Adjust threshold** — Lower the `hallucination` threshold from 0.9 to 0.7 if your use case is more tolerant
2. **Disable a metric** — Set `state=inactive` if a metric is too noisy
3. **Change applicability** — Make a metric apply to `nonllm` use cases too
4. **Fine-tune for domain** — Set healthcare prompts to use a stricter `factual_correctness` threshold

---

### `POST /config/metric_config/reset`

**What it does:** Resets metric configurations to factory defaults.

**Content-Type:** `application/json` (MetricResetRequest — list of metric names)

**Use Cases:**
1. **Undo bad configs** — Reset metrics after experimental threshold changes broke evaluations
2. **New environment setup** — Reset all metrics to defaults when setting up a new project
3. **Troubleshooting** — Reset a specific metric that's producing unexpected results

---

## Module 3: Custom Metrics

### `POST /custom/metrics/`

**What it does:** Creates a custom evaluation metric — either script-based (Python) or LLM-judge.

**Content-Type:** `application/json` (MetricDefinitionCreate)

**Key Inputs:**
| Field | Description |
|-------|-------------|
| `name` | Metric name |
| `metric_type` | `script` or `llm_based` |
| `script` | Python code for script-based metrics |
| `packages` | pip packages to install |
| `llm_config` | LLM to use for LLM-judge metrics |
| `evaluation_prompt` | Judge prompt for LLM-based metrics |
| `applicability` | `llm` or `nonllm` |

**Use Cases:**
1. **Domain-specific quality check** — Create a "medical_accuracy" metric that checks if healthcare outputs use correct terminology
2. **Brand voice checker** — LLM-judge metric that evaluates if responses match your brand guidelines
3. **JSON schema validator** — Script metric that validates if LLM output matches expected JSON structure
4. **Regex compliance checker** — Script metric that checks for prohibited patterns in output
5. **Custom hallucination scorer** — LLM-judge metric with domain-specific grounding rules
6. **Latency scorer** — Script metric that scores based on response time

---

### `GET /custom/metrics/`

**What it does:** Lists all custom metrics with filters.

**Key Inputs:** `metric_name`, `applicability`, `llm_based`, `state`, `status`, `page`, `limit`

**Use Cases:**
1. **Review custom metrics** — List all custom metrics you've created
2. **Filter by status** — `?status=published` to see production-ready custom metrics
3. **Find LLM-judge metrics** — `?llm_based=true` to see all LLM-based custom evaluators

---

### `PUT /custom/metrics/update`

**What it does:** Updates a custom metric's script, prompt, or config.

**Use Cases:**
1. **Fix a bug in custom script** — Update the Python evaluation code
2. **Improve judge prompt** — Refine the LLM evaluation prompt for better accuracy
3. **Add packages** — Install additional pip dependencies for the script

---

### `DELETE /custom/metrics/{metric_name}`

**What it does:** Deletes a custom metric.

**Use Cases:**
1. **Remove deprecated metrics** — Clean up metrics no longer in use
2. **Replace with improved version** — Delete v1 metric, create v2

---

### `POST /custom/metrics/create_and_install_packages`

**What it does:** Creates a Python virtual environment and installs packages for custom metrics.

**Key Inputs:** `packages` (list), optional `environment` name

**Use Cases:**
1. **Set up eval environment** — Install `nltk`, `rouge-score`, `bert-score` for NLP-based evaluations
2. **Install domain libraries** — Install `medspacy` for healthcare text processing metrics
3. **Dependency management** — Ensure all packages are available before running custom metric scripts

---

### `POST /custom/metrics/vulnerability_check`

**What it does:** Scans Python scripts and packages for security vulnerabilities using LLM analysis.

**Key Inputs:** `script` (Python code), `packages` (list of package names)

**Use Cases:**
1. **Security review** — Before deploying a custom metric script, check for vulnerable code patterns
2. **Package audit** — Verify that pip packages don't have known vulnerabilities
3. **Code review automation** — Automated security scanning for user-submitted evaluation scripts

---

## Module 4: Validation (Evaluation)

### `POST /validate/prompt` ⭐

**What it does:** Validates/evaluates a prompt dataset against configured metrics. Runs evaluation asynchronously.

**Content-Type:** `application/json` (PromptDatasetValidationRequest)

**Use Cases:**
1. **Quality gate** — Before deploying a new prompt version, validate it scores above thresholds on all metrics
2. **Regression testing** — Run your prompt against 100 test cases to ensure v2 doesn't regress vs v1
3. **Comparative evaluation** — Run two different prompts against the same dataset, compare scores
4. **Automated QA** — Integrate into CI/CD to block deployments if quality drops
5. **Benchmark new models** — Evaluate the same prompt on Claude 2 vs Claude 3 to quantify improvement

**Flow:**
```
POST /validate/prompt
  { dataset_name: "healthcare-qa", metrics: ["factual_correctness", "relevance"], ... }
  → Returns: { request_id: "abc-123" }
  
GET /validate/evaluation-status?request_id=abc-123
  → { status: "running", progress: 45 }
  
GET /validate/evaluation-status?request_id=abc-123
  → { status: "completed", results: { factual_correctness: 0.92, relevance: 0.88 } }
```

---

### `POST /validate/rag` ⭐

**What it does:** Validates a RAG (Retrieval Augmented Generation) pipeline using RAG-specific metrics.

**Content-Type:** `application/json` (RagDatasetValidationRequest)

**Use Cases:**
1. **RAG pipeline QA** — Evaluate if your retrieval system returns relevant context
2. **Faithfulness check** — Verify the LLM answer is grounded in the retrieved documents (not hallucinating)
3. **Context relevancy** — Measure if the vector search returns relevant passages
4. **End-to-end RAG score** — Answer correctness = how well the final answer matches expected output
5. **Chunking strategy evaluation** — Compare different document chunking approaches by their RAG scores

> 📄 Use `sample-csvs/gcs_rag_dataset.csv` for testing this endpoint.

---

### `POST /validate/agent` ⭐

**What it does:** Validates an AI agent's output using agent-specific metrics.

**Content-Type:** `application/json` (AgentEvaluationRequest)

**Use Cases:**
1. **Agent QA** — Evaluate if your AI agent produces correct actions/answers
2. **Tool usage validation** — Check if the agent uses the right tools for the right tasks
3. **Multi-step reasoning** — Evaluate complex agent workflows with tool data
4. **Agent benchmarking** — Compare different agent architectures against the same dataset

> 📄 Use `sample-csvs/gcs_agent_dataset.csv` for testing this endpoint.

---

### `GET /validate/evaluation-status`

**What it does:** Polls status of async evaluation jobs.

**Key Input:** `request_id` (query param)

**Use Cases:**
1. **Poll until complete** — Check every 5 seconds until evaluation finishes
2. **Status dashboard** — Show progress of running evaluations
3. **Batch status** — Query without `request_id` to see all recent evaluations

---

## Module 5: Dataset Management

### `POST /datasets/create`

**What it does:** Creates a new empty dataset for evaluation.

**Key Inputs:**
| Field | Description |
|-------|-------------|
| `name` | Unique name (3-100 chars, no special chars) |
| `description` | Optional description |
| `use_case_type` | `prompt`, `rag`, or `agent` |

**Use Cases:**
1. **Create test dataset** — Set up a "healthcare-prompt-tests" dataset
2. **Organize by domain** — Create separate datasets per business domain
3. **Use case separation** — Separate datasets for prompt, RAG, and agent evaluations

---

### `GET /datasets/`

**What it does:** Lists all datasets with filters.

**Key Inputs:** `applicability`, `use_case_type`, `page`, `limit`, `time`, `name`

**Use Cases:**
1. **Browse datasets** — List all available datasets in your project
2. **Filter by type** — `?use_case_type=rag` to find RAG-specific datasets
3. **Search by name** — `?name=healthcare` to find healthcare datasets
4. **Time filter** — `?time=Past 24 hours` to see recently created datasets

---

### `GET /datasets/download`

**What it does:** Downloads a dataset template CSV file.

**Key Input:** `use_case_type` (prompt, rag, or agent)

**Use Cases:**
1. **Get template** — Download the correct CSV format for your use case type
2. **Onboard new users** — Give team members a template to fill with test data
3. **Format reference** — Check what columns are required for each dataset type

---

### `POST /datasets/upload`

**What it does:** Uploads a CSV/XLS/XLSX file to create a dataset with items.

**Content-Type:** `multipart/form-data`

**Use Cases:**
1. **Bulk upload** — Upload 100 test cases from a spreadsheet
2. **Import from existing QA** — Convert your existing QA spreadsheets to evaluation datasets
3. **Automated dataset creation** — Scripts can upload generated test data

> 📄 See `sample-csvs/gcs_prompt_dataset.csv`, `gcs_rag_dataset.csv`, and `gcs_agent_dataset.csv` for formats.

---

### `GET /datasets/items`

**What it does:** Lists all items in a dataset.

**Key Inputs:** `name` (required — dataset name), `page`, `limit`

**Use Cases:**
1. **Preview dataset** — Browse the test cases before running evaluation
2. **Data quality check** — Review inputs and expected outputs for correctness
3. **Paginate large datasets** — Browse through hundreds of items

---

### `GET /datasets/items/{item_id}`

**What it does:** Gets a single dataset item by ID.

**Use Cases:**
1. **Inspect specific item** — Review a single test case in detail
2. **Debug failed evaluations** — Check the input/expected_output for items that failed

---

### `PUT /datasets/items/{item_id}`

**What it does:** Updates a dataset item.

**Use Cases:**
1. **Fix incorrect expected output** — Update the gold standard answer
2. **Add context** — Add retrieval context to an existing prompt test case
3. **Enrich data** — Add tool_data to convert a prompt item to an agent evaluation item

---

### `DELETE /datasets/items/{item_id}`

**What it does:** Deletes a single item from a dataset.

**Use Cases:**
1. **Remove bad data** — Delete items with incorrect ground truth
2. **Trim dataset** — Remove outlier items that skew evaluation results

---

### `DELETE /datasets/{name}`

**What it does:** Permanently deletes an entire dataset by name.

**Use Cases:**
1. **Clean up old datasets** — Remove datasets from completed projects
2. **Start fresh** — Delete and recreate a dataset with corrected data

---

## Module 6: Logs & Observability

### `POST /logs/trace/create` ⭐

**What it does:** Creates a new observability trace. A trace represents a single end-to-end AI interaction (from user input → LLM calls → final output).

**Key Inputs:** `CreateTraceRequest` (name, session_id, metadata)

**Use Cases:**
1. **Request tracing** — Create a trace for every incoming user query to track the full pipeline
2. **Session grouping** — Use `session_id` to link multiple traces into a conversation
3. **Environment tagging** — Tag traces as dev/staging/prod
4. **Debug trail** — Every traced request can be inspected for debugging

**Flow:**
```
POST /logs/trace/create → { trace_id: "abc-123" }
  ↓
POST /logs/trace/llm_call → Log the LLM call within this trace
  ↓
POST /logs/trace/update_output → Log the final output
```

---

### `POST /logs/trace/llm_call`

**What it does:** Logs an LLM call as a span within an existing trace.

**Use Cases:**
1. **Log every LLM interaction** — Record input, output, model, latency, tokens
2. **Multi-call tracing** — If one request makes 3 LLM calls, log each as a separate span
3. **Cost attribution** — Track token usage per trace for billing
4. **Debugging** — See exactly what was sent to and received from the LLM

---

### `POST /logs/trace/update_output`

**What it does:** Logs the final output of a trace (after all processing is done).

**Use Cases:**
1. **Complete the trace** — Record what was finally returned to the user
2. **Post-processing audit** — See if any modification was made between LLM response and final output
3. **Guardrail tracking** — Compare raw LLM output vs post-guardrail output

---

### `POST /logs/trace/embedding-search`

**What it does:** Logs an embedding search (vector DB query) as part of a trace.

**Use Cases:**
1. **RAG observability** — Log the vector search query and retrieved documents
2. **Debug RAG quality** — See what context was retrieved for each query
3. **Retrieval performance** — Track search latency and result counts

---

### `POST /logs/trace/add_event`

**What it does:** Adds a custom event to an existing trace.

**Use Cases:**
1. **Log business events** — "user_feedback_positive" or "prompt_guardrail_triggered"
2. **Milestone markers** — Track key steps in your pipeline
3. **Error logging** — Log exceptions or warnings within a trace context

---

### `GET /logs/{trace_id}`

**What it does:** Retrieves a full trace with all its spans, events, and metadata.

**Use Cases:**
1. **Debug a specific request** — View the complete lifecycle of an AI interaction
2. **Audit trail** — Provide compliance auditors with full request traces
3. **Performance analysis** — Analyze token usage, latency breakdowns for a specific request

---

### `DELETE /logs/{trace_id}`

**What it does:** Removes a trace permanently.

**Use Cases:**
1. **Data retention** — Delete old traces per data retention policy
2. **GDPR compliance** — Remove traces containing PII upon user request
3. **Clean test data** — Remove traces from load/integration testing

---

### `GET /logs/`

**What it does:** Lists all traces with filtering and pagination.

**Key Inputs:** `limit`, `page`, `name`, `session_id`, `environment`, `hours`

**Use Cases:**
1. **Activity dashboard** — `?hours=24` to see last 24 hours of AI activity
2. **Session replay** — `?session_id=user-session-42` to see all interactions in a conversation
3. **Environment filter** — `?environment=production` to see only prod traffic
4. **Search by name** — `?name=customer-support` to find specific trace types
5. **Debugging** — Find and inspect recent traces to troubleshoot issues

---

## Module 7: Testing Evaluators

### `POST /test/prompt`

**What it does:** Runs a single manual LLM evaluation for prompt testing. Tests one input against the evaluator without needing a full dataset.

**Key Inputs:** `PromptTestRequest` (prompt, actual_output, expected_output, execution/evaluation model config, threshold)

**Use Cases:**
1. **Quick metric test** — Test if a single prompt/response pair passes your metrics before running full evaluation
2. **Metric calibration** — Adjust thresholds by testing individual examples
3. **Demo evaluations** — Show stakeholders how a metric scores a specific example

---

### `POST /test/rag`

**What it does:** Tests a single RAG evaluation — prompt + retrieved_context + output.

**Key inputs include:** `prompt`, `actual_output`, `retrieved_context`, `expected_output`, `threshold`

**Use Cases:**
1. **Test RAG quality** — Check if context_relevancy and faithfulness pass for a single example
2. **Debug retrieval issues** — Test with different contexts to see how scores change
3. **Calibrate RAG thresholds** — Find the right threshold for your RAG pipeline

---

### `POST /test/agent`

**What it does:** Tests a single agent evaluation — prompt + agent output + tool data.

**Key inputs include:** `prompt`, `actual_output`, `expected_output`, tool usage data, `threshold`

**Use Cases:**
1. **Test agent scoring** — Check if agent tool usage is evaluated correctly
2. **Debug agent evaluator** — Test edge cases in agent behavior
3. **Validate agent changes** — Quick-check after modifying agent logic

---

## Module 8: Compliance Check

### `GET /compliance/compliance-guidelines`

**What it does:** Lists all available compliance frameworks/guidelines.

**Key Inputs:** `page`, `limit`

**Use Cases:**
1. **Discover frameworks** — See what compliance standards are available (NIST AI RMF, EU AI Act, ISO 42001, etc.)
2. **Audit preparation** — Review which guidelines your prompts should comply with
3. **Populate UI dropdown** — List framework options for users to select during compliance scanning

---

### `POST /compliance/scan-compliance`

**What it does:** Triggers an async compliance scan for a prompt against regulatory frameworks.

**Content-Type:** `application/json` (ScanRequest)

**Use Cases:**
1. **Regulatory compliance** — Scan prompts against EU AI Act, NIST AI RMF
2. **Pre-deployment gate** — Block deployment until compliance scan passes
3. **Periodic audits** — Schedule regular compliance scans of all production prompts
4. **New regulation onboarding** — When a new regulation is added, scan all existing prompts

---

### `GET /compliance/compliance-status`

**What it does:** Polls compliance scan status.

**Key Input:** `request_id`

**Use Cases:**
1. **Wait for results** — Poll until scan status is "completed"
2. **CI/CD integration** — Gate deployments on compliance scan completion

---

## Module 9: G3S Proxy

### `GET /g3sproxy/llm_configuration`

**What it does:** Proxy endpoint that fetches LLM config from G3S through GCS. Useful when GCS needs to know about LLM configs without direct G3S access.

**Key Input:** `config_id` (optional)

**Use Cases:**
1. **Cross-service config lookup** — GCS needs to know which LLM model a config points to for evaluation
2. **Unified API** — Access LLM configs through GCS when you're already authenticated there

---

## Complete Observability Flow

```
┌─────────────────────────────────────────────────────────────┐
│                YOUR AI APPLICATION                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Start trace       → POST /logs/trace/create              │
│                          Returns: trace_id                   │
│                                                              │
│  2. Log embedding     → POST /logs/trace/embedding-search    │
│     search               (query, results, latency)           │
│                                                              │
│  3. Log LLM call      → POST /logs/trace/llm_call            │
│                          (input, output, tokens, model)       │
│                                                              │
│  4. Log guardrail     → POST /logs/trace/add_event           │
│     check                ("guardrail_passed")                 │
│                                                              │
│  5. Log final output  → POST /logs/trace/update_output       │
│                          (final response to user)             │
│                                                              │
│  6. Evaluate quality  → POST /validate/prompt                │
│                          (run metrics on the output)          │
│                                                              │
│  7. View trace later  → GET /logs/{trace_id}                 │
│                          (full audit trail)                   │
└─────────────────────────────────────────────────────────────┘
```
