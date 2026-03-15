# G3S — GenAI Gateway & Guardrail Service (Complete Guide)

> **Base URL:** `https://54.91.159.104/g3s`  
> **Auth:** All endpoints require `Authorization: Bearer <token>`  
> **Version:** 2.0.1

---

## What is G3S?

G3S is the **central AI gateway** — it sits between your application and the LLM providers (Bedrock, OpenAI, Azure, etc.). Every LLM call, embedding request, and speech-to-text request routes through G3S.

**Think of it as your AI API Gateway that:**
- Routes LLM calls to the right provider/model
- Manages all model configurations (LLM, embedding, speech) in one place
- Tracks token consumption and costs
- Provides a unified API regardless of which provider you use

---

## Endpoint-by-Endpoint Flow & Use Cases

---

### 1. `POST /g3s/llm/call` ⭐ MOST IMPORTANT

**What it does:** Sends a prompt to any configured LLM (Bedrock Claude, GPT-4, etc.) and returns the response. This is the **core gateway endpoint**.

**Content-Type:** `application/json` (LLMCallRequest)

**Key Inputs:**
| Field | Description |
|-------|-------------|
| `messages` | Array of `{role, content}` messages (system, user, assistant) |
| `config_id` | Which LLM config to use (maps to a specific model + provider) |
| `temperature` | Creativity level (0.0-1.0) |
| `max_tokens` | Maximum response length |

**Use Cases:**
1. **Unified LLM access** — Call any model (Bedrock Claude, GPT-4, Gemini) through the same API. Switch models by changing `config_id`
2. **Chatbot backend** — Send conversation history as messages, get AI response
3. **Text generation** — Generate reports, summaries, code through a single endpoint
4. **Multi-model comparison** — Send the same prompt to different configs and compare outputs
5. **Cost control** — G3S tracks every call's token usage automatically

**Flow:**
```
Your App → POST /g3s/llm/call
           { config_id: 42, messages: [{role: "user", content: "Summarize..."}] }
         → G3S looks up config 42 → Bedrock Claude 3 Sonnet
         → Forwards request to AWS Bedrock
         → Returns: { response, usage: { prompt_tokens, completion_tokens } }
```

---

### 2. `POST /g3s/llm/embeddings` ⭐

**What it does:** Generates vector embeddings for text input. Essential for RAG (Retrieval Augmented Generation) and semantic search.

**Content-Type:** `application/json` (EmbeddingRequest)

**Use Cases:**
1. **RAG pipeline** — Convert documents into embeddings for vectorDB storage (Pinecone, OpenSearch, pgvector)
2. **Semantic search** — Embed user queries to find similar documents
3. **Similarity matching** — Compare two texts by computing cosine similarity of their embeddings
4. **Document classification** — Embed documents and cluster them by topic
5. **Recommendation engine** — Find similar items based on embedding distance

**Flow:**
```
Your App → POST /g3s/llm/embeddings
           { model: "titan-embed-text-v2", input: "Patient shows symptoms of..." }
         → G3S routes to Bedrock Titan Embeddings
         → Returns: { embeddings: [0.023, -0.045, ...], usage: { total_tokens: 15 } }
         → Your App stores in VectorDB
```

---

### 3. `POST /g3s/configuration/save_llm_configuration`

**What it does:** Creates a new LLM model configuration. This is how you register a Bedrock/OpenAI model for use across the platform.

**Content-Type:** `application/json` (LLMConfig)

**Key Inputs:**
| Field | Description |
|-------|-------------|
| `name` | Config name (e.g., "bedrock-claude-3-sonnet") |
| `provider` | Model provider (aws_bedrock, openai, azure, etc.) |
| `model_id` | Specific model ID |
| `api_key` / `credentials` | Provider credentials |
| `default_params` | Default temperature, max_tokens, etc. |

**Use Cases:**
1. **Register Bedrock Claude** — Set up a config pointing to `anthropic.claude-3-sonnet` on Bedrock
2. **Register GPT-4** — Add an OpenAI config for comparison testing
3. **Environment configs** — Create separate configs for dev (cheap model) and prod (powerful model)
4. **Customer-specific models** — Create configs with different parameters per customer/tenant
5. **Cost tiers** — Config with `max_tokens=500` for quick responses, another with `max_tokens=4000` for detailed responses

---

### 4. `GET /g3s/configuration/list_llm_configuration`

**What it does:** Lists all LLM configurations with pagination and search.

**Key Inputs:** `page`, `page_size`, `search`

**Use Cases:**
1. **Dropdown population** — Fill a UI dropdown with available models for users to select
2. **Discover available models** — See what LLMs are configured in your org
3. **Search configs** — `?search=claude` to find all Claude configurations
4. **Inventory management** — Review all model configs across your organization

---

### 5. `GET /g3s/configuration/llm_configuration/{llm_id}`

**What it does:** Gets a single LLM config by ID.

**Use Cases:**
1. **Verify config before execution** — Check model details before sending a prompt
2. **Display config details** — Show model name, provider, parameters in an admin UI
3. **Configuration audit** — Review what settings a specific config uses

---

### 6. `PUT /g3s/configuration/update_llm_configuration/{config_id}`

**What it does:** Updates an existing LLM configuration.

**Use Cases:**
1. **Change default temperature** — Update from 0.7 to 0.3 for more deterministic outputs
2. **Rotate API keys** — Update credentials without creating a new config
3. **Model upgrade** — Switch from Claude 2 to Claude 3 in the same config
4. **Tune parameters** — Adjust max_tokens, top_p, etc. based on production observations

---

### 7. `DELETE /g3s/configuration/delete_llm_configuration`

**What it does:** Deletes an LLM config by `config_id` (query param).

**Use Cases:**
1. **Remove deprecated models** — Delete configs for discontinued models
2. **Clean up test configs** — Remove configs created during testing
3. **Security** — Remove configs with compromised credentials

---

### 8-12. Embedding Configuration CRUD

Same pattern as LLM configs but for embedding models:

| Endpoint | Method | Use Case |
|----------|--------|----------|
| `save_embedding_configuration` | POST | Register a new embedding model (e.g., Titan Embed v2, Ada-002) |
| `list_embedding_configuration` | GET | List all available embedding models |
| `update_embedding_configuration/{id}` | PUT | Update embedding model settings |
| `delete_embedding_configuration` | DELETE | Remove obsolete embedding configs |

**Why separate from LLM?** Embedding models have different configurations — dimensions, input limits, and no temperature/max_tokens.

---

### 13-16. Speech Model Configuration CRUD

Same pattern for speech/audio models (TTS, STT):

| Endpoint | Method | Use Case |
|----------|--------|----------|
| `save_speech_model_configuration` | POST | Register a TTS/STT model (e.g., Polly, Whisper) |
| `list_speech_model_configuration` | GET | List available speech models |
| `update_speech_model_configuration/{id}` | PUT | Update voice/language settings |
| `delete_speech_model_configuration/{id}` | DELETE | Remove speech configs |

**Use Cases:**
1. **Voice assistants** — Configure text-to-speech for conversational AI
2. **Transcription** — Set up speech-to-text for call center analysis
3. **Multi-language support** — Configure different voices/languages per config

---

### 17. `POST /g3s/configuration/install_packages`

**What it does:** Installs Python packages for security/custom metric scripts.

**Content-Type:** `application/json` (PackageRequest)

**Use Cases:**
1. **Install dependencies** — Install packages needed by custom evaluation scripts
2. **Security packages** — Install security scanning libraries

---

### 18. `GET /g3s/model-consumption/consumption` ⭐ COST TRACKING

**What it does:** Retrieves token usage and cost records with filters.

**Key Inputs:**
| Param | Description |
|-------|-------------|
| `project_id` | Filter by project |
| `config_name` | Filter by model config (partial match) |
| `date_filter` | `last_7_days`, `last_30_days`, or `custom` |
| `custom_start` | Start date (ISO format) for custom range |
| `custom_end` | End date (ISO format) for custom range |

**Use Cases:**
1. **Monthly cost report** — `?date_filter=last_30_days` to see total token usage
2. **Per-model cost analysis** — `?config_name=claude` to see Claude-specific costs
3. **Budget monitoring** — Track daily consumption and alert when approaching limits
4. **Project chargebacks** — `?project_id=5` to see costs per project
5. **Usage dashboards** — Build executive dashboards showing AI spending trends

---

### 19. `GET /g3s/model-consumption/config_list`

**What it does:** Lists config names available for consumption filtering.

**Key Input:** `lm_type` (1=LLM, 2=Embedding, 3=Speech)

**Use Cases:**
1. **Populate cost report filters** — Get list of model names for a dropdown
2. **Categorize costs** — See costs by model type (LLM vs Embedding vs Speech)

---

### 20. `GET /check_health`

**Use Case:** Health monitoring, load balancer checks.

---

## Complete Flow: Using G3S as Your AI Gateway

```
┌─────────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. SETUP (Admin/DevOps)                                     │
│     ├── Save LLM config         → POST /configuration/save_llm_configuration
│     │     { name: "prod-claude", provider: "bedrock", model: "claude-3-sonnet" }
│     ├── Save embedding config   → POST /configuration/save_embedding_configuration
│     │     { name: "prod-titan-embed", model: "titan-embed-text-v2" }
│     └── List all configs        → GET /configuration/list_llm_configuration
│                                                              │
│  2. RUNTIME (Application Code)                               │
│     ├── LLM Call                → POST /llm/call
│     │     { config_id: 42, messages: [...] }                 │
│     ├── Generate Embeddings     → POST /llm/embeddings
│     │     { model: "titan-embed", input: "..." }             │
│     └── (G3S automatically logs consumption)                 │
│                                                              │
│  3. MONITORING (Finance/Ops)                                 │
│     ├── Check costs             → GET /model-consumption/consumption
│     │     ?date_filter=last_30_days&config_name=claude        │
│     └── Health check            → GET /check_health          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```
