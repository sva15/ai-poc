"""
AIForce POC — Complete Orchestrator
Demonstrates the full end-to-end flow using all four foundational services.

Flow:
  1. SETUP   — Save prompt to PES, create security group in SGS
  2. EXECUTE — Retrieve prompt → Scan input (SGS) → Call Bedrock directly → Scan output (SGS) → Log trace (GCS)
  3. EVALUATE — Upload dataset, run evaluation, check compliance
  4. REPORT  — Token usage + cost summary

Usage:
  export AIFORCE_AUTH_TOKEN="your-token"
  export AWS_REGION="us-east-1"
  python orchestrator.py
"""

import json
import re
import sys
import time
import logging
import uuid
from datetime import datetime

# Add parent dir for imports
sys.path.insert(0, "..")

from config import (
    AIFORCE_BASE_URL, AIFORCE_AUTH_TOKEN,
    AWS_REGION, BEDROCK_MODEL_ID,
    DEFAULT_TEMPERATURE, DEFAULT_MAX_TOKENS,
    SECURITY_GROUP_NAME, PROMPT_DOMAIN_PREFIX,
    TRACE_ENVIRONMENT, get_pricing, G3S_LLM_CONFIG_ID,
)
from bedrock_client import BedrockClient

# Import AIForce service clients
try:
    # Try importing directly (when deployed as Lambda with shared folder in root)
    from shared.aiforce_client import PESClient, G3SClient, SGSClient, GCSClient
except ModuleNotFoundError:
    # Fallback for local execution
    sys.path.insert(0, "../lambdas")
    from shared.aiforce_client import PESClient, G3SClient, SGSClient, GCSClient

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("poc")


class AIForcePOC:
    """
    Complete POC demonstrating all four AIForce foundational services
    with direct Bedrock calls, token tracking, and cost calculation.
    """

    def __init__(self):
        # Initialize service clients
        self.pes = PESClient(base_url=AIFORCE_BASE_URL, auth_token=AIFORCE_AUTH_TOKEN)
        self.g3s = G3SClient(base_url=AIFORCE_BASE_URL, auth_token=AIFORCE_AUTH_TOKEN)
        self.sgs = SGSClient(base_url=AIFORCE_BASE_URL, auth_token=AIFORCE_AUTH_TOKEN)
        self.gcs = GCSClient(base_url=AIFORCE_BASE_URL, auth_token=AIFORCE_AUTH_TOKEN)

        # Initialize Bedrock client (direct calls)
        pricing = get_pricing(BEDROCK_MODEL_ID)
        self.bedrock = BedrockClient(
            region=AWS_REGION,
            model_id=BEDROCK_MODEL_ID,
            pricing=pricing,
        )

        # Session tracking
        self.session_id = str(uuid.uuid4())
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost_usd = 0.0
        self.call_count = 0
        self.saved_prompt_id = None

    # ═══════════════════════════════════════════════════════════════════
    #  PHASE 1: SETUP
    # ═══════════════════════════════════════════════════════════════════

    def setup(self):
        """
        One-time setup:
        1. Check all service health
        2. List available LLM configs from G3S
        3. Save a prompt to PES
        4. Create a security group in SGS
        """
        print("\n" + "=" * 70)
        print("  PHASE 1: SETUP")
        print("=" * 70)

        # ── 1a. Health checks ────────────────────────────────────────
        print("\n🏥 Checking service health...")
        services = {
            "PES": self.pes.health_check(),
            "G3S": self.g3s.health_check(),
            "SGS": self.sgs.health_check(),
            "GCS": self.gcs.health_check("/check_health"),
        }
        for name, result in services.items():
            status = "✅" if result.get("success") else "❌"
            print(f"   {status} {name}: {result.get('data', result.get('error', 'unknown'))}")

        # ── 1b. List LLM configs from G3S ────────────────────────────
        print("\n📋 Listing available LLM configurations from G3S...")
        configs = self.g3s.list_llm_configs(page_size=20)
        if configs.get("success"):
            print(f"   Found {len(configs.get('data', {}).get('items', []))} LLM configs")
            for cfg in configs.get("data", {}).get("items", [])[:5]:
                print(f"   • ID: {cfg.get('id')} | Name: {cfg.get('name')} | Model: {cfg.get('model_id', 'N/A')}")
        else:
            print(f"   ⚠️ Could not list configs: {configs.get('error')}")

        # ── 1c. Save a prompt to PES ─────────────────────────────────
        print("\n💾 Saving prompt to PES...")
        prompt_name = f"{PROMPT_DOMAIN_PREFIX}_customer_support_v1"
        user_prompt = (
            "You are a helpful customer support assistant for {{COMPANY}}. "
            "A customer has the following question:\n\n{{QUESTION}}\n\n"
            "Please provide a clear, professional, and helpful response."
        )
        system_prompt = (
            "You are a professional customer support agent. "
            "Be concise, empathetic, and solution-oriented. "
            "If you don't know the answer, say so and suggest contacting a human agent."
        )

        save_result = self.pes.save_prompt(
            name=prompt_name,
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            lm_config_id=int(G3S_LLM_CONFIG_ID) if G3S_LLM_CONFIG_ID else 1,
            publish_status=True,
            is_public=False,
            version="v1.0",
            variables={"COMPANY": "string", "QUESTION": "string"},
            lm_params={"temperature": DEFAULT_TEMPERATURE, "max_token": DEFAULT_MAX_TOKENS},
        )

        if save_result.get("success"):
            self.saved_prompt_id = save_result.get("data", {}).get("prompt_id") or \
                                   save_result.get("data", {}).get("id")
            print(f"   ✅ Prompt saved: '{prompt_name}' (ID: {self.saved_prompt_id})")
        else:
            print(f"   ⚠️ Save prompt: {save_result.get('error')}")
            # Try listing to find existing prompt
            list_result = self.pes.list_prompts(search=prompt_name)
            if list_result.get("success"):
                items = list_result.get("data", {}).get("items", [])
                if items:
                    self.saved_prompt_id = items[0].get("id") or items[0].get("prompt_id")
                    print(f"   ℹ️ Found existing prompt: ID {self.saved_prompt_id}")

        # ── 1d. Create SGS security group ────────────────────────────
        print("\n🔒 Creating security group in SGS...")
        sg_result = self.sgs.register_security_group(
            name=SECURITY_GROUP_NAME,
            description="POC security group with PII detection, toxicity, and prompt injection scanning"
        )

        if sg_result.get("success"):
            print(f"   ✅ Security group created: '{SECURITY_GROUP_NAME}'")

            # Configure scanners
            print("   🔧 Configuring scanners...")
            config_result = self.sgs.configure_security_group(
                group_name=SECURITY_GROUP_NAME,
                config={
                    "state": "active",
                    "config_data": {
                        "input_safety_guards": {
                            "Detect PII": {
                                "enabled": True,
                                "config": {
                                    "entity_types": [
                                        "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER",
                                        "CREDIT_CARD", "US_SSN", "IP_ADDRESS"
                                    ],
                                    "redact": True,
                                    "threshold": 0.6
                                }
                            },
                            "Detect Prompt Injection": {
                                "enabled": True,
                                "config": {"threshold": 0.7}
                            },
                            "Detect Toxicity": {
                                "enabled": True,
                                "config": {"threshold": 0.8}
                            },
                        },
                        "output_safety_guards": {
                            "Detect PII": {
                                "enabled": True,
                                "config": {
                                    "entity_types": ["PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER"],
                                    "redact": True,
                                    "threshold": 0.6
                                }
                            },
                            "Detect Toxicity": {
                                "enabled": True,
                                "config": {"threshold": 0.8}
                            },
                        }
                    }
                }
            )
            if config_result.get("success"):
                print("   ✅ Scanners configured: PII (redact), Prompt Injection, Toxicity")
            else:
                print(f"   ⚠️ Scanner config: {config_result.get('error')}")
        else:
            print(f"   ⚠️ Security group: {sg_result.get('error')} (might already exist)")

        print("\n✅ SETUP COMPLETE")
        return True

    # ═══════════════════════════════════════════════════════════════════
    #  PHASE 2: EXECUTE (Main Runtime Flow)
    # ═══════════════════════════════════════════════════════════════════

    def execute(self, user_question: str, company_name: str = "TechCorp") -> dict:
        """
        Full runtime flow:
        1. Retrieve prompt from PES
        2. Substitute variables
        3. Scan input via SGS (pre-flight)
        4. Call Bedrock directly (NOT via G3S)
        5. Scan output via SGS (post-flight)
        6. Log trace + LLM call via GCS
        7. Return response with usage stats

        Args:
            user_question: The customer question
            company_name: Company name for the prompt variable

        Returns:
            Complete response with token usage, cost, and security results
        """
        print("\n" + "=" * 70)
        print("  PHASE 2: EXECUTE")
        print("=" * 70)

        self.call_count += 1
        execution_result = {
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "user_question": user_question,
            "company": company_name,
        }

        # ── Step 1: Retrieve prompt from PES ─────────────────────────
        print(f"\n📝 Step 1: Retrieving prompt from PES (ID: {self.saved_prompt_id})...")
        prompt_details = self.pes.get_prompt_details(self.saved_prompt_id)

        if prompt_details.get("success"):
            prompt_data = prompt_details.get("data", {})
            user_prompt_template = prompt_data.get("user_prompt", "")
            system_prompt = prompt_data.get("system_prompt", "")
            print(f"   ✅ Retrieved prompt: '{prompt_data.get('name', 'unknown')}'")
            print(f"   📄 Template: {user_prompt_template[:80]}...")
        else:
            print(f"   ⚠️ Could not retrieve prompt: {prompt_details.get('error')}")
            user_prompt_template = "Help the customer with: {{QUESTION}}"
            system_prompt = "You are a helpful assistant."

        # ── Step 2: Substitute variables ─────────────────────────────
        print("\n🔄 Step 2: Substituting variables...")
        resolved_prompt = user_prompt_template.replace("{{COMPANY}}", company_name)
        resolved_prompt = resolved_prompt.replace("{{QUESTION}}", user_question)
        print(f"   ✅ Resolved prompt: {resolved_prompt[:80]}...")

        # ── Step 3: Scan input via SGS (pre-flight) ──────────────────
        print("\n🛡️ Step 3: Scanning input via SGS (pre-flight)...")
        input_scan = self.sgs.scan_prompt(
            prompt_name=f"{PROMPT_DOMAIN_PREFIX}_customer_support_v1",
            input_prompt=user_prompt_template,
            variables={"COMPANY": company_name, "QUESTION": user_question},
            security_group=SECURITY_GROUP_NAME,
        )

        input_safe = True
        final_prompt = resolved_prompt

        if input_scan.get("success"):
            scan_data = input_scan.get("data", {})
            input_safe = scan_data.get("is_safe", True)
            is_redacted = scan_data.get("is_redacted", False)
            sanitized_text = scan_data.get("sanitized_text", "")

            execution_result["input_scan"] = {
                "is_safe": input_safe,
                "is_redacted": is_redacted,
                "scanner_results": scan_data.get("results", {}),
            }

            if is_redacted and sanitized_text:
                final_prompt = sanitized_text
                print(f"   ⚠️ PII detected and redacted! Using sanitized version.")
                print(f"   🔒 Sanitized: {sanitized_text[:80]}...")
            elif input_safe:
                print(f"   ✅ Input is safe — no issues detected")
            else:
                print(f"   ❌ Input flagged as UNSAFE")
                for scanner, result in scan_data.get("results", {}).items():
                    if not result.get("is_pass", True):
                        print(f"      ⚠️ {scanner}: score={result.get('score')}")
        else:
            print(f"   ⚠️ SGS scan unavailable: {input_scan.get('error')}")

        # ── Step 4: Call Bedrock DIRECTLY ─────────────────────────────
        print(f"\n🤖 Step 4: Calling Bedrock DIRECTLY (model: {BEDROCK_MODEL_ID})...")
        print(f"   ℹ️ NOT routing through G3S — direct boto3 call")

        if not input_safe:
            print("   ❌ Skipping LLM call — input was flagged as unsafe")
            execution_result["response"] = "Request blocked due to safety concerns."
            execution_result["bedrock"] = {"success": False, "error": "Input flagged unsafe by SGS"}
            return execution_result

        bedrock_result = self.bedrock.invoke_model(
            user_prompt=final_prompt,
            system_prompt=system_prompt,
            temperature=DEFAULT_TEMPERATURE,
            max_tokens=DEFAULT_MAX_TOKENS,
        )

        execution_result["bedrock"] = {
            "success": bedrock_result["success"],
            "model_id": bedrock_result["model_id"],
            "input_tokens": bedrock_result["input_tokens"],
            "output_tokens": bedrock_result["output_tokens"],
            "total_tokens": bedrock_result["total_tokens"],
            "input_cost_usd": bedrock_result["input_cost_usd"],
            "output_cost_usd": bedrock_result["output_cost_usd"],
            "total_cost_usd": bedrock_result["total_cost_usd"],
            "latency_ms": bedrock_result["latency_ms"],
        }

        if bedrock_result["success"]:
            llm_response = bedrock_result["response"]
            print(f"   ✅ Response received ({bedrock_result['total_tokens']} tokens, "
                  f"${bedrock_result['total_cost_usd']:.6f})")
            print(f"   📊 Tokens: {bedrock_result['input_tokens']} input + "
                  f"{bedrock_result['output_tokens']} output")
            print(f"   ⏱️ Latency: {bedrock_result['latency_ms']}ms")
            print(f"   💰 Cost: ${bedrock_result['total_cost_usd']:.6f}")

            # Update running totals
            self.total_input_tokens += bedrock_result["input_tokens"]
            self.total_output_tokens += bedrock_result["output_tokens"]
            self.total_cost_usd += bedrock_result["total_cost_usd"]
        else:
            llm_response = f"Error: {bedrock_result['error']}"
            print(f"   ❌ Bedrock error: {bedrock_result['error']}")

        # ── Step 5: Scan output via SGS (post-flight) ────────────────
        print("\n🛡️ Step 5: Scanning output via SGS (post-flight)...")
        output_scan = self.sgs.scan_output(
            prompt_name=f"{PROMPT_DOMAIN_PREFIX}_customer_support_v1",
            output=llm_response,
            prompt=final_prompt,
            security_group=SECURITY_GROUP_NAME,
        )

        if output_scan.get("success"):
            scan_data = output_scan.get("data", {})
            output_safe = scan_data.get("is_safe", True)
            is_redacted = scan_data.get("is_redacted", False)
            sanitized = scan_data.get("sanitized_text", "")

            execution_result["output_scan"] = {
                "is_safe": output_safe,
                "is_redacted": is_redacted,
                "scanner_results": scan_data.get("results", {}),
            }

            if is_redacted and sanitized:
                llm_response = sanitized
                print(f"   ⚠️ Output PII redacted — using sanitized version")
            elif output_safe:
                print(f"   ✅ Output is safe")
            else:
                print(f"   ⚠️ Output flagged — returning sanitized version")
                if sanitized:
                    llm_response = sanitized
        else:
            print(f"   ⚠️ SGS output scan unavailable: {output_scan.get('error')}")

        execution_result["response"] = llm_response

        # ── Step 6: Log trace via GCS ────────────────────────────────
        print("\n📊 Step 6: Logging trace via GCS...")
        trace_result = self.gcs.create_trace(
            name=f"poc-execution-{self.call_count}",
            session_id=self.session_id,
            metadata={
                "environment": TRACE_ENVIRONMENT,
                "prompt_id": str(self.saved_prompt_id),
                "company": company_name,
                "model": BEDROCK_MODEL_ID,
            }
        )

        if trace_result.get("success"):
            trace_id = trace_result.get("data", {}).get("trace_id") or \
                       trace_result.get("data", {}).get("id")
            print(f"   ✅ Trace created: {trace_id}")

            # Log the LLM call within the trace
            llm_log = self.gcs.log_llm_call({
                "trace_id": trace_id,
                "input": final_prompt,
                "output": llm_response[:500],  # Truncate for logging
                "model": BEDROCK_MODEL_ID,
                "system_prompt": system_prompt,
                "input_tokens": bedrock_result.get("input_tokens", 0),
                "output_tokens": bedrock_result.get("output_tokens", 0),
                "total_cost_usd": bedrock_result.get("total_cost_usd", 0),
                "latency_ms": bedrock_result.get("latency_ms", 0),
            })

            if llm_log.get("success"):
                print(f"   ✅ LLM call logged in trace")

            # Log the final output
            output_log = self.gcs.log_output({
                "trace_id": trace_id,
                "output": llm_response[:500],
            })

            # Add an event for the security scan results
            self.gcs.add_event({
                "trace_id": trace_id,
                "event_name": "security_scan_complete",
                "event_data": {
                    "input_safe": execution_result.get("input_scan", {}).get("is_safe", "N/A"),
                    "output_safe": execution_result.get("output_scan", {}).get("is_safe", "N/A"),
                }
            })

            execution_result["trace_id"] = trace_id
        else:
            print(f"   ⚠️ GCS trace: {trace_result.get('error')}")

        # ── Step 7: Print summary ────────────────────────────────────
        print("\n" + "-" * 70)
        print("  EXECUTION SUMMARY")
        print("-" * 70)
        print(f"  Request ID:    {execution_result['request_id']}")
        print(f"  Model:         {BEDROCK_MODEL_ID}")
        print(f"  Input Tokens:  {bedrock_result.get('input_tokens', 0)}")
        print(f"  Output Tokens: {bedrock_result.get('output_tokens', 0)}")
        print(f"  Total Cost:    ${bedrock_result.get('total_cost_usd', 0):.6f}")
        print(f"  Latency:       {bedrock_result.get('latency_ms', 0)}ms")
        print(f"  Input Safe:    {execution_result.get('input_scan', {}).get('is_safe', 'N/A')}")
        print(f"  Output Safe:   {execution_result.get('output_scan', {}).get('is_safe', 'N/A')}")
        print(f"  Trace ID:      {execution_result.get('trace_id', 'N/A')}")
        print("-" * 70)
        print(f"\n📤 Response:\n{llm_response[:500]}")

        return execution_result

    # ═══════════════════════════════════════════════════════════════════
    #  PHASE 3: EVALUATE
    # ═══════════════════════════════════════════════════════════════════

    def evaluate(self, dataset_csv_path: str = None):
        """
        Quality evaluation:
        1. List available metrics from GCS
        2. Upload a test dataset
        3. Run prompt evaluation
        4. Check compliance

        Args:
            dataset_csv_path: Path to CSV test dataset
        """
        print("\n" + "=" * 70)
        print("  PHASE 3: EVALUATE")
        print("=" * 70)

        # ── 3a. List available metrics ───────────────────────────────
        print("\n📏 Listing available evaluation metrics...")
        metrics = self.gcs.list_metrics(applicability="llm", state="active")
        if metrics.get("success"):
            metric_list = metrics.get("data", {}).get("items", [])
            print(f"   Found {len(metric_list)} active metrics:")
            for m in metric_list[:10]:
                print(f"   • {m.get('name', 'unknown')} ({m.get('type', 'N/A')})")
        else:
            print(f"   ⚠️ Could not list metrics: {metrics.get('error')}")

        # ── 3b. Upload dataset ───────────────────────────────────────
        if dataset_csv_path:
            print(f"\n📤 Uploading test dataset: {dataset_csv_path}...")
            upload = self.gcs.upload_dataset(
                file_path=dataset_csv_path,
                dataset_name=f"{PROMPT_DOMAIN_PREFIX}_test_dataset",
                use_case_type="prompt",
            )
            if upload.get("success"):
                print(f"   ✅ Dataset uploaded successfully")
            else:
                print(f"   ⚠️ Upload: {upload.get('error')}")

                # Try creating dataset first, then uploading
                create = self.gcs.create_dataset(
                    name=f"{PROMPT_DOMAIN_PREFIX}_test_dataset",
                    description="POC test dataset",
                    use_case_type="prompt",
                )
                if create.get("success"):
                    print(f"   ✅ Dataset created, retrying upload...")
                    upload = self.gcs.upload_dataset(
                        file_path=dataset_csv_path,
                        dataset_name=f"{PROMPT_DOMAIN_PREFIX}_test_dataset",
                        use_case_type="prompt",
                    )

        # ── 3c. List compliance guidelines ───────────────────────────
        print(f"\n📋 Listing compliance guidelines...")
        guidelines = self.gcs.list_compliance_guidelines()
        if guidelines.get("success"):
            guideline_list = guidelines.get("data", {}).get("items", [])
            print(f"   Found {len(guideline_list)} compliance frameworks:")
            for g in guideline_list[:5]:
                print(f"   • {g.get('name', 'unknown')}")
        else:
            print(f"   ⚠️ Could not list guidelines: {guidelines.get('error')}")

        # ── 3d. Scan prompt compliance via PES ───────────────────────
        if self.saved_prompt_id:
            print(f"\n🔍 Scanning prompt compliance via PES...")
            compliance = self.pes.scan_compliance(request={
                "prompt_id": self.saved_prompt_id,
            })
            if compliance.get("success"):
                request_id = compliance.get("data", {}).get("request_id")
                print(f"   ✅ Compliance scan started: {request_id}")

                # Poll for result (max 30 seconds)
                if request_id:
                    for i in range(6):
                        time.sleep(5)
                        status = self.pes.get_compliance_status(request_id)
                        if status.get("success"):
                            status_val = status.get("data", {}).get("status", "")
                            print(f"   ⏳ Status: {status_val}")
                            if status_val in ("completed", "done", "finished"):
                                print(f"   ✅ Compliance scan completed!")
                                break
            else:
                print(f"   ⚠️ Compliance scan: {compliance.get('error')}")

        print("\n✅ EVALUATION COMPLETE")

    # ═══════════════════════════════════════════════════════════════════
    #  PHASE 4: COST REPORT
    # ═══════════════════════════════════════════════════════════════════

    def cost_report(self):
        """
        Generate a comprehensive cost report:
        1. Local token/cost tracking (from direct Bedrock calls)
        2. G3S consumption data (platform-wide)
        """
        print("\n" + "=" * 70)
        print("  PHASE 4: COST & USAGE REPORT")
        print("=" * 70)

        # ── Local tracking (this session) ────────────────────────────
        total_tokens = self.total_input_tokens + self.total_output_tokens
        print(f"\n📊 This Session (Direct Bedrock Calls):")
        print(f"   Total Calls:       {self.call_count}")
        print(f"   Total Input Tokens:  {self.total_input_tokens:,}")
        print(f"   Total Output Tokens: {self.total_output_tokens:,}")
        print(f"   Total Tokens:        {total_tokens:,}")
        print(f"   Total Cost:          ${self.total_cost_usd:.6f}")
        if self.call_count > 0:
            print(f"   Avg Cost/Call:       ${self.total_cost_usd / self.call_count:.6f}")
            print(f"   Avg Tokens/Call:     {total_tokens // self.call_count:,}")

        # ── G3S consumption (platform-wide) ──────────────────────────
        print(f"\n📈 Platform-Wide Consumption (from G3S):")
        consumption = self.g3s.get_consumption(date_filter="last_7_days")
        if consumption.get("success"):
            data = consumption.get("data", {})
            records = data if isinstance(data, list) else data.get("items", [data])
            print(f"   Last 7 Days Records: {len(records)}")
            for r in records[:5]:
                print(f"   • {r.get('config_name', 'N/A')}: "
                      f"{r.get('total_tokens', 'N/A')} tokens, "
                      f"${r.get('total_cost', 'N/A')}")
        else:
            print(f"   ⚠️ Could not fetch consumption: {consumption.get('error')}")

        # ── Config names ─────────────────────────────────────────────
        config_names = self.g3s.get_config_names(lm_type=1)
        if config_names.get("success"):
            names = config_names.get("data", [])
            print(f"\n   Available LLM Config Names: {', '.join(str(n) for n in names[:5])}")

        # ── GCS trace summary ────────────────────────────────────────
        print(f"\n📝 Recent Traces (from GCS):")
        traces = self.gcs.list_traces(hours=24, limit=5)
        if traces.get("success"):
            trace_list = traces.get("data", {}).get("items", [])
            print(f"   Found {len(trace_list)} traces in last 24 hours")
            for t in trace_list[:5]:
                print(f"   • {t.get('name', 'N/A')} [{t.get('trace_id', t.get('id', 'N/A'))[:8]}...]")
        else:
            print(f"   ⚠️ Could not fetch traces: {traces.get('error')}")

        print("\n" + "=" * 70)
        print(f"  SESSION TOTAL: {self.call_count} calls, "
              f"{total_tokens:,} tokens, ${self.total_cost_usd:.6f}")
        print("=" * 70)

    # ═══════════════════════════════════════════════════════════════════
    #  PHASE 5: CLEANUP (Optional)
    # ═══════════════════════════════════════════════════════════════════

    def cleanup(self):
        """Optional cleanup — remove test data created during setup."""
        print("\n🧹 Cleaning up...")

        if self.saved_prompt_id:
            result = self.pes.delete_prompt(self.saved_prompt_id)
            print(f"   Delete prompt: {'✅' if result.get('success') else '⚠️'}")

        result = self.sgs.delete_security_group(SECURITY_GROUP_NAME)
        print(f"   Delete security group: {'✅' if result.get('success') else '⚠️'}")

        print("   ✅ Cleanup complete")


# ═══════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

def main():
    """Run the complete POC demonstration."""
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║         AIForce Foundational Services — Complete POC            ║")
    print("║                                                                 ║")
    print("║  PES → Prompt Store    |  G3S → Gateway Config                  ║")
    print("║  SGS → Security Scan   |  GCS → Observability                   ║")
    print("║  Bedrock → Direct LLM Calls (via boto3)                         ║")
    print("╚══════════════════════════════════════════════════════════════════╝")

    poc = AIForcePOC()

    # ── Phase 1: Setup ───────────────────────────────────────────────
    poc.setup()

    # ── Phase 2: Execute — run several example queries ───────────────
    test_queries = [
        {
            "question": "How do I reset my password?",
            "company": "TechCorp",
        },
        {
            "question": "What is your refund policy for digital subscriptions?",
            "company": "TechCorp",
        },
        {
            "question": "My order #12345 hasn't arrived yet. My email is john@example.com "
                        "and my phone is 555-0123. Can you help?",
            "company": "TechCorp",
        },
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n\n{'━' * 70}")
        print(f"  QUERY {i} of {len(test_queries)}")
        print(f"  Question: {query['question'][:60]}...")
        print(f"{'━' * 70}")

        result = poc.execute(
            user_question=query["question"],
            company_name=query["company"],
        )

    # ── Phase 3: Evaluate ────────────────────────────────────────────
    # Use the sample CSV from sample-csvs/ directory
    poc.evaluate(dataset_csv_path="../sample-csvs/gcs_prompt_dataset.csv")

    # ── Phase 4: Cost Report ─────────────────────────────────────────
    poc.cost_report()

    # ── Optional: Cleanup ────────────────────────────────────────────
    # Uncomment the next line to clean up test data:
    # poc.cleanup()

    print("\n\n🎉 POC COMPLETE! Review the output above for the full flow.")


def lambda_handler(event, context):
    """
    AWS Lambda entry point for the POC Orchestrator.
    You can trigger this from the AWS Lambda Console Test tab.
    
    Expected event payload (optional):
    {
        "question": "How do I reset my password?",
        "company": "TechCorp"
    }
    """
    import sys
    from io import StringIO

    # Capture standard output to return in the API response (optional, but helpful for console testing)
    old_stdout = sys.stdout
    sys.stdout = mystdout = StringIO()

    try:
        poc = AIForcePOC()
        
        # ── Phase 1: Setup ───────────────────────────────────────────────
        poc.setup()
        
        # ── Phase 2: Execute ─────────────────────────────────────────────
        user_question = event.get("question", "How do I reset my password?")
        company_name = event.get("company", "TechCorp")
        
        print(f"\n\n{'━' * 70}")
        print(f"  EXECUTING Lambda Event Query")
        print(f"  Question: {user_question}")
        print(f"{'━' * 70}")
        
        execution_result = poc.execute(
            user_question=user_question,
            company_name=company_name,
        )
        
        # ── Phase 4: Cost Report (skipping evaluation to save time in Lambda) ───
        poc.cost_report()
        
        # Restore stdout
        sys.stdout = old_stdout
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "POC executed successfully",
                "execution_result": execution_result,
                "logs": mystdout.getvalue()
            }, default=str)
        }
        
    except Exception as e:
        # Restore stdout on error
        sys.stdout = old_stdout
        logger.error(f"Error in POC orchestrator: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "logs": mystdout.getvalue()
            })
        }

if __name__ == "__main__":
    main()
