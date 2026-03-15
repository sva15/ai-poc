# SGS — Security Guardrails Service (Complete Guide)

> **Base URL:** `https://54.91.159.104/sgs`  
> **Auth:** All endpoints require `Authorization: Bearer <token>` (except health check and root)  
> **Version:** 2.0.1

---

## What is SGS?

SGS is the **security firewall for your AI pipeline**. It scans both:
- **Input prompts** (before they reach the LLM) — catching PII, injection attacks, toxicity, secrets
- **LLM outputs** (before they reach the user) — catching hallucinated PII, toxic content, banned topics

**Think of SGS as:**
- A **WAF (Web Application Firewall)** but for LLM traffic
- Your **PII redaction engine** — auto-removes names, SSNs, credit cards from prompts
- Your **prompt injection shield** — detects "ignore all previous instructions" attacks
- Your **content moderation layer** — blocks toxic, hateful, or off-topic content

### Master → Group Hierarchy

SGS uses a **two-tier configuration system:**

```
MASTER Security Group (Global defaults)
  ├── All scanners defined here are the DEFAULTS
  ├── control_config:
  │     ├── disable_all_scanners: false     (kill switch)
  │     ├── enforce_scanner_state: true     (strict mode — children inherit states)
  │     └── force_override_child_config: false (authority — override child settings)
  │
  ├── Security Group: "healthcare-app"  → Custom thresholds for healthcare
  ├── Security Group: "finance-api"     → Strict PII scanning, custom banned terms
  └── Security Group: "internal-chat"   → Relaxed settings for internal use
```

---

## Scanner Types Available

SGS provides these built-in scanners for both input and output:

| Scanner | What It Detects | Key Config |
|---------|----------------|------------|
| **Detect PII** | Names, emails, phones, credit cards, SSNs, IPs, etc. | `entity_types`, `redact`, `threshold` |
| **Detect Prompt Injection** | "Ignore previous instructions" attacks | `threshold` |
| **Detect Toxicity** | Hate speech, harassment, offensive content | `threshold` |
| **Detect Secrets** | AWS keys, API tokens, GitHub tokens, JWTs, private keys, etc. | `secrets` list, `redact`, `redact_mode` |
| **Detect Code Language** | Code snippets (Python, SQL, etc.) — block or allow | `languages`, `is_blocked`, `threshold` |
| **Detect Banned Topics** | Religion, politics, or any custom topics | `topics` list, `threshold` |
| **Detect Banned Substrings** | Specific words or phrases | `substrings` list, `case_sensitive` |
| **Detect Competitors** | Mentions of competitor brand names | `competitors` list, `threshold` |
| **Regex-based Sanitization** | Custom regex patterns | `patterns`, `is_blocked`, `redact` |
| **Token Limit Enforcement** | Prompts exceeding token limits | `limit` (default 4096) |

---

## Endpoint-by-Endpoint Flow & Use Cases

---

### 1. `GET /sgs/register/token-context`

**What it does:** Debug endpoint — shows what token context (org, project, user) is extracted from your bearer token.

**Use Cases:**
1. **Debug auth** — Verify your token contains the expected organization and project
2. **Troubleshoot** — When security groups aren't loading, check if token has right context

---

## Security Group Management

### 2. `GET /sgs/security-groups/config-control`

**What it does:** Reads the master security group's control flags.

**Response Example:**
```json
{
  "state": "active",
  "control_config": {
    "disable_all_scanners": false,
    "enforce_scanner_state": true,
    "force_override_child_config": false
  }
}
```

**Use Cases:**
1. **Check global policy** — See if master overrides are active
2. **Audit security posture** — Verify the master config matches your security requirements
3. **Troubleshoot** — If scanners aren't working, check if `disable_all_scanners` is true

---

### 3. `PUT /sgs/security-groups/config-control`

**What it does:** Sets the master security group's global control flags.

**Key Inputs:**
| Field | Description |
|-------|-------------|
| `state` | `active` or `inactive` — globally enable/disable the master group |
| `control_config.disable_all_scanners` | **Kill switch** — disables ALL scanners across ALL groups |
| `control_config.enforce_scanner_state` | **Strict mode** — child groups inherit master's scanner enabled/disabled states |
| `control_config.force_override_child_config` | **Authority mode** — child group configs are ignored, master config is used everywhere |

**Use Cases:**
1. **Emergency kill switch** — Set `disable_all_scanners=true` if scanning causes latency in production
2. **Enforce global policy** — Set `enforce_scanner_state=true` to prevent individual groups from disabling PII detection
3. **Lock down** — Set `force_override_child_config=true` during a security audit to ensure all groups use identical scanning
4. **Disable for testing** — Temporarily set master to `inactive` for load testing without guardrails

---

### 4. `POST /sgs/security-groups/register` ⭐

**What it does:** Creates a new security group (inherits master config by default).

**Key Inputs:** `SecurityGroupRegisterRequest` with `name` and optional `description`

**Use Cases:**
1. **Per-application groups** — Create "healthcare-chatbot" group with extra-strict PII settings
2. **Per-environment groups** — Create "dev-relaxed" with lower thresholds, "prod-strict" with high thresholds
3. **Per-client groups** — Create "client-acme" with custom banned topics/substrings
4. **Regulatory groups** — Create "hipaa-compliant" with healthcare-specific scanners enabled

**Flow:**
```
POST /security-groups/register
  { name: "healthcare-chatbot", description: "Strict PII + HIPAA compliance" }
  → Creates group inheriting all master scanner configs
  → Now customize with PUT /security-groups/healthcare-chatbot/config
```

---

### 5. `GET /sgs/security-groups/list`

**What it does:** Lists all security groups.

**Key Inputs:**
| Param | Description |
|-------|-------------|
| `state` | Filter: `active` or `inactive` |
| `include_master` | Include master group in the list |
| `state_only` | Return only group names and states (lightweight) |

**Use Cases:**
1. **Admin dashboard** — Show all security groups and their states
2. **Active groups only** — `?state=active` to see which groups are actively scanning
3. **Dropdown population** — List group names for a UI selector
4. **Audit** — Review all configured security groups and their statuses

---

### 6. `PUT /sgs/security-groups/{group_name}/config` ⭐

**What it does:** Configures the scanner settings for a specific security group.

**Content-Type:** `application/json` (SecurityGroupConfigRequest)

**Key Inputs:**
| Field | Description |
|-------|-------------|
| `state` | `active` / `inactive` for this group |
| `description` | Updated description |
| `config_data.input_safety_guards` | Configure input scanners (see scanner table above) |
| `config_data.output_safety_guards` | Configure output scanners |

**Each scanner has:**
- `enabled` — true/false
- `config` — Scanner-specific settings (threshold, entity_types, etc.)
- `description` — What this scanner does

**Use Cases:**
1. **Stricter PII for healthcare** — Enable PII detection with `redact=true` and low threshold
2. **Block competitor mentions** — Add competitor names to `Detect Competitors` scanner
3. **Custom banned words** — Add industry-specific banned substrings
4. **Relax for internal tools** — Lower thresholds or disable non-critical scanners
5. **Enable regex patterns** — Add custom regex patterns for SSNs, account numbers, etc.
6. **Set token limits** — Limit input to 2048 tokens for a cost-conscious application

**Example — Configure strict healthcare scanning:**
```json
{
  "state": "active",
  "config_data": {
    "input_safety_guards": {
      "Detect PII": {
        "enabled": true,
        "config": {
          "entity_types": ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", "CREDIT_CARD"],
          "redact": true,
          "threshold": 0.6
        }
      },
      "Detect Prompt Injection": {
        "enabled": true,
        "config": { "threshold": 0.7 }
      }
    },
    "output_safety_guards": {
      "Detect PII": {
        "enabled": true,
        "config": { "redact": true, "threshold": 0.6 }
      },
      "Detect Toxicity": {
        "enabled": true,
        "config": { "threshold": 0.5 }
      }
    }
  }
}
```

---

### 7. `GET /sgs/security-groups/{group_name}/config`

**What it does:** Gets the scanner configuration for a security group.

**Key Input:** `view` — `raw` (only this group's overrides) or `effective` (merged with master config)

**Use Cases:**
1. **View effective config** — See the final merged config (master + group overrides) — `?view=effective`
2. **View raw overrides** — See only what this group has customized vs master — `?view=raw`
3. **Compare configs** — Fetch raw configs for two groups and compare differences
4. **Audit custom rules** — Check what specific changes a group has vs the master

---

### 8. `DELETE /sgs/security-groups/{group_name}`

**What it does:** Permanently deletes a security group.

**Use Cases:**
1. **Decommission app** — Remove security group when an application is retired
2. **Clean up test groups** — Delete groups created during testing
3. **Reorganize** — Delete old groups and create new ones with better naming

---

### 9. `GET /sgs/security-groups/master/scanners`

**What it does:** Gets the master security group's scanner configuration (the defaults all groups inherit).

**Use Cases:**
1. **View global defaults** — See what scanners are enabled/disabled by default
2. **Planning** — Before creating a new group, check what it will inherit
3. **Compliance review** — Verify master config meets your organization's security baseline

---

### 10. `PUT /sgs/security-groups/master/scanners`

**What it does:** Updates the master scanner configuration. Changes propagate to all child groups (depending on control flags).

**Use Cases:**
1. **Set org-wide defaults** — Enable PII detection across all groups by default
2. **Add new scanner globally** — Enable a new scanner type for all groups at once
3. **Adjust default thresholds** — Tighten/loosen global security posture
4. **New compliance requirement** — Add banned topics/substrings that must apply everywhere

---

## Core Scanning Endpoints

### 11. `POST /sgs/scan/prompt` ⭐⭐ MOST IMPORTANT

**What it does:** Scans a prompt (with variable substitution) for safety issues BEFORE it reaches the LLM.

**Content-Type:** `application/json`

**Key Inputs:**
| Field | Required | Description |
|-------|----------|-------------|
| `prompt_name` | ✅ | Identifier for audit logging |
| `input_prompt` | ✅ | Prompt text with `{{VARIABLE}}` placeholders |
| `variables` | ✅ | JSON object with variable values |
| `security_group` | ✅ | Which security group's scanner config to use |

**Response includes:**
```json
{
  "is_safe": true/false,
  "sanitized_text": "...",    // PII redacted version
  "is_redacted": true/false,
  "results": {
    "Detect PII": { "score": 0.95, "threshold": 0.8, "is_pass": false, "redact_enabled": true },
    "Detect Toxicity": { "score": 0.02, "threshold": 0.8, "is_pass": true }
  }
}
```

**Use Cases:**
1. **Pre-flight PII check** — Scan user input for PII before sending to LLM. If `is_redacted=true`, use `sanitized_text` instead
2. **Prevent prompt injection** — Detect and block "ignore all instructions" attacks
3. **Block toxic prompts** — Reject user inputs with hate speech or offensive content
4. **Secret detection** — Catch accidental API key/password leaks in user prompts
5. **Code injection prevention** — Block SQL injection or malicious code in prompts
6. **Competitor brand filtering** — Detect and flag prompts mentioning competitors
7. **Production pipeline** — Every prompt passes through SGS before hitting the LLM

**Flow:**
```
User sends: "Write about {{NAME}} who lives at {{ADDRESS}}"
Variables: { NAME: "John Doe", ADDRESS: "123 Main St" }

POST /sgs/scan/prompt →
  Resolved: "Write about John Doe who lives at 123 Main St"
  Scanners detect PII (PERSON, LOCATION)
  
Response:
  is_safe: false
  sanitized_text: "Write about [REDACTED] who lives at [REDACTED]"
  is_redacted: true
  
Your App: Use sanitized_text for LLM call instead of original
```

---

### 12. `POST /sgs/scan/output` ⭐⭐

**What it does:** Scans LLM output for safety issues BEFORE returning to the user.

**Content-Type:** `application/json`

**Key Inputs:**
| Field | Description |
|-------|-------------|
| `prompt_name` | Identifier for audit logging |
| `output` | The LLM's response to scan |
| `prompt` | The original prompt (for context) |
| `security_group` | Which group's output scanners to use |

**Use Cases:**
1. **Output PII filtering** — LLM might hallucinate real-looking PII — scan and redact
2. **Toxic output blocking** — Block LLM responses containing harmful content
3. **Banned topic enforcement** — Ensure the LLM doesn't discuss politics, religion, etc.
4. **Secret leakage prevention** — Block responses that contain patterns matching API keys or passwords
5. **Code output control** — Block or allow code in responses based on your policy
6. **Complete security loop** — Input scan + Output scan = full protection

---

### 13. `GET /check_health`

**Use Case:** Health monitoring, load balancer checks.

---

## Complete Security Pipeline Flow

```
┌───────────────────────────────────────────────────────────────────┐
│                    YOUR APPLICATION                                │
├───────────────────────────────────────────────────────────────────┤
│                                                                    │
│  1. SETUP (One-time, Admin)                                        │
│     ├── Check master config   → GET /security-groups/config-control│
│     ├── Create security group → POST /security-groups/register     │
│     │     { name: "my-app-group" }                                 │
│     └── Configure scanners    → PUT /security-groups/my-app-group/config
│           Enable: PII (redact=true), Toxicity, Prompt Injection    │
│           Disable: Code Language (we want code in our outputs)     │
│                                                                    │
│  2. RUNTIME (Every Request)                                        │
│     ├── User sends prompt                                          │
│     │                                                              │
│     ├── STEP A: Scan Input    → POST /sgs/scan/prompt              │
│     │     Input: "Tell me about John Doe (SSN: 123-45-6789)"       │
│     │     Result: is_safe=false, sanitized="Tell me about          │
│     │             [REDACTED] (SSN: [REDACTED])"                    │
│     │                                                              │
│     ├── STEP B: Send to LLM   → POST /g3s/llm/call                │
│     │     Use sanitized_text (PII removed)                         │
│     │                                                              │
│     ├── STEP C: Scan Output   → POST /sgs/scan/output              │
│     │     Input: LLM response text                                 │
│     │     Result: is_safe=true → safe to return to user            │
│     │                                                              │
│     └── Return final response to user                              │
│                                                                    │
│  3. MONITORING                                                     │
│     ├── List active groups    → GET /security-groups/list          │
│     └── View effective config → GET /security-groups/my-app-group/config?view=effective
│                                                                    │
└───────────────────────────────────────────────────────────────────┘
```
