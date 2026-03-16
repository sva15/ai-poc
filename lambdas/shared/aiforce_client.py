"""
AIForce Shared HTTP Client
Reusable client for all four AIForce foundational services (PES, G3S, SGS, GCS).
Handles authentication, error handling, and request formatting using ONLY native Python libraries (urllib).
"""

import json
import logging
import time
import urllib.request
import urllib.error
import urllib.parse
import ssl
import uuid

logger = logging.getLogger(__name__)


class AIForceClient:
    """Base HTTP client for AIForce REST APIs (urllib architecture)."""

    def __init__(self, base_url: str, auth_token: str, timeout: int = 30, max_retries: int = 2):
        """
        Args:
            base_url: Base URL (e.g., "https://54.91.159.104")
            auth_token: Bearer token for authentication
            timeout: Request timeout in seconds
            max_retries: Number of retries on failure
        """
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self.max_retries = max_retries

        self.default_headers = {
            "Authorization": f"Bearer {auth_token}",
            "Accept": "application/json",
        }
        
        # Disable SSL warnings for self-signed certs (common in dev/POC)
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def _build_url(self, path: str, params: dict = None) -> str:
        """Build full URL from path and query parameters."""
        url = f"{self.base_url}{path}"
        if params:
            # Filter out None values
            params = {k: v for k, v in params.items() if v is not None}
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}"
        return url

    def _request(self, method: str, path: str, params: dict = None, 
                 data: bytes = None, headers: dict = None) -> dict:
        """
        Make an HTTP request with retry logic using built-in urllib.

        Returns:
            dict with keys: success, status_code, data, error
        """
        url = self._build_url(path, params)
        
        req_headers = self.default_headers.copy()
        if headers:
            req_headers.update(headers)

        request = urllib.request.Request(url, data=data, headers=req_headers, method=method.upper())

        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"[{method.upper()}] {url} (attempt {attempt + 1})")
                
                with urllib.request.urlopen(request, timeout=self.timeout, context=self.ssl_context) as response:
                    status_code = response.getcode()
                    resp_body = response.read().decode('utf-8')

                    try:
                        resp_data = json.loads(resp_body) if resp_body else None
                    except json.JSONDecodeError:
                        resp_data = resp_body

                    return {
                        "success": True,
                        "status_code": status_code,
                        "data": resp_data,
                        "error": None
                    }

            except urllib.error.HTTPError as e:
                resp_body = e.read().decode('utf-8')
                try:
                    resp_data = json.loads(resp_body) if resp_body else None
                except json.JSONDecodeError:
                    resp_data = resp_body
                    
                error_msg = resp_data if isinstance(resp_data, str) else json.dumps(resp_data)
                logger.warning(f"HTTP {e.code}: {error_msg}")
                return {
                    "success": False,
                    "status_code": e.code,
                    "data": resp_data,
                    "error": f"HTTP {e.code}: {error_msg}"
                }

            except urllib.error.URLError as e:
                logger.warning(f"Connection/Timeout URL error on attempt {attempt + 1}: {e.reason}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                return {
                    "success": False,
                    "status_code": 0,
                    "data": None,
                    "error": f"Network Error: {str(e.reason)}"
                }
                
            except TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                return {
                    "success": False,
                    "status_code": 408,
                    "data": None,
                    "error": f"Request timed out after {self.timeout}s"
                }

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return {
                    "success": False,
                    "status_code": 0,
                    "data": None,
                    "error": f"Unexpected error: {str(e)}"
                }

        return {"success": False, "status_code": 0, "data": None, "error": "Max retries exceeded"}

    # ── Convenience methods ──────────────────────────────────────────

    def get(self, path: str, params: dict = None) -> dict:
        """HTTP GET request."""
        return self._request("GET", path, params=params)

    def post_json(self, path: str, body: dict) -> dict:
        """HTTP POST with JSON body."""
        data = json.dumps(body).encode('utf-8')
        headers = {"Content-Type": "application/json"}
        return self._request("POST", path, data=data, headers=headers)

    def post_form(self, path: str, data: dict) -> dict:
        """HTTP POST with form-urlencoded body."""
        form_data = urllib.parse.urlencode(data).encode('utf-8')
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        return self._request("POST", path, data=form_data, headers=headers)

    def post_multipart(self, path: str, files: dict, data: dict = None) -> dict:
        """HTTP POST with natively built multipart/form-data."""
        boundary = uuid.uuid4().hex
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        
        body = bytearray()
        
        # Add form fields
        if data:
            for key, value in data.items():
                body.extend(f"--{boundary}\r\n".encode('utf-8'))
                body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode('utf-8'))
                body.extend(f"{value}\r\n".encode('utf-8'))
                
        # Add file fields 
        for field_name, file_handle in files.items():
            filename = getattr(file_handle, "name", "upload.csv").split("/")[-1]
            file_content = file_handle.read()
            if isinstance(file_content, str):
                file_content = file_content.encode('utf-8')
                
            body.extend(f"--{boundary}\r\n".format(boundary).encode('utf-8'))
            body.extend(f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode('utf-8'))
            body.extend(b'Content-Type: application/octet-stream\r\n\r\n')
            body.extend(file_content)
            body.extend(b'\r\n')
            
        body.extend(f"--{boundary}--\r\n".encode('utf-8'))
        
        return self._request("POST", path, data=bytes(body), headers=headers)

    def put_json(self, path: str, body: dict, params: dict = None) -> dict:
        """HTTP PUT with JSON body."""
        data = json.dumps(body).encode('utf-8')
        headers = {"Content-Type": "application/json"}
        return self._request("PUT", path, params=params, data=data, headers=headers)

    def delete(self, path: str, params: dict = None) -> dict:
        """HTTP DELETE request."""
        return self._request("DELETE", path, params=params)

    def health_check(self, service_path: str = "/check_health") -> dict:
        """Check service health."""
        return self.get(service_path)



class PESClient(AIForceClient):
    """Client for PES (Prompt Engineering Service)."""
    PREFIX = "/pes/prompt_studio"

    def save_prompt(self, name: str, user_prompt: str, lm_config_id: int,
                    system_prompt: str = "", publish_status: bool = False,
                    is_public: bool = False, version: str = "v1.0",
                    variables: dict = None, lm_params: dict = None,
                    examples: list = None, mcp_enabled: bool = False,
                    parent_prompt_id: int = None, evaluation: dict = None) -> dict:
        """Save a new prompt to PES."""
        form_data = {
            "name": name,
            "user_prompt": user_prompt,
            "lm_config_id": str(lm_config_id),
            "system_prompt": system_prompt,
            "publish_status": str(publish_status).lower(),
            "is_public": str(is_public).lower(),
            "version": version,
            "mcp_enabled": str(mcp_enabled).lower(),
        }
        if variables:
            form_data["varriables"] = json.dumps(variables)
        if lm_params:
            form_data["lm_params"] = json.dumps(lm_params)
        if examples:
            form_data["examples"] = json.dumps(examples)
        if parent_prompt_id:
            form_data["parent_prompt_id"] = str(parent_prompt_id)
        if evaluation:
            form_data["evaluation"] = json.dumps(evaluation)
        return self.post_form(f"{self.PREFIX}/save_prompt", data=form_data)

    def update_prompt(self, prompt_id: int, **kwargs) -> dict:
        """Update an existing prompt."""
        form_data = {}
        for key, value in kwargs.items():
            if isinstance(value, (dict, list)):
                form_data[key] = json.dumps(value)
            elif isinstance(value, bool):
                form_data[key] = str(value).lower()
            else:
                form_data[key] = str(value)
        return self.post_form(f"{self.PREFIX}/update_prompt/{prompt_id}", data=form_data)

    def delete_prompt(self, prompt_id: int) -> dict:
        """Delete a prompt."""
        return self.post_json(f"{self.PREFIX}/delete_prompt", body={"prompt_id": prompt_id})

    def list_prompts(self, page: int = 1, page_size: int = 10,
                     search: str = None, is_public: bool = None,
                     publish_status: bool = None) -> dict:
        """List prompts with optional filters."""
        params = {"page": page, "page_size": page_size}
        if search:
            params["search"] = search
        if is_public is not None:
            params["is_public"] = is_public
        if publish_status is not None:
            params["publish_status"] = publish_status
        return self.get(f"{self.PREFIX}/list_prompt", params=params)

    def get_prompt_details(self, prompt_id: int) -> dict:
        """Get full prompt details by ID."""
        return self.get(f"{self.PREFIX}/get_prompt_details/{prompt_id}")

    def generate_prompt(self, request: dict) -> dict:
        """Auto-generate a prompt from a description."""
        return self.post_json(f"{self.PREFIX}/generate_prompt", body=request)

    def test_prompt(self, prompt_id: int, user_prompt: str, lm_config_id: int,
                    system_prompt: str = "", lm_params: dict = None,
                    variables: dict = None, mcp_enabled: bool = False) -> dict:
        """Test a prompt against the LLM (dry run)."""
        form_data = {
            "promptId": str(prompt_id),
            "user_prompt": user_prompt,
            "lm_config_id": str(lm_config_id),
            "system_prompt": system_prompt,
            "mcp_enabled": str(mcp_enabled).lower(),
        }
        if lm_params:
            form_data["lm_params"] = json.dumps(lm_params)
        if variables:
            form_data["varriables"] = json.dumps(variables)
        return self.post_form(f"{self.PREFIX}/test_prompt", data=form_data)

    def execute_prompt(self, request: dict) -> dict:
        """Execute a stored prompt with variables."""
        return self.post_json(f"{self.PREFIX}/execute_prompt", body=request)

    def get_metrics(self, applicability: str = "prompt", state: str = None,
                    custom: bool = None, llm_based: bool = None) -> dict:
        """Fetch available evaluation metrics from GCS."""
        params = {"applicability": applicability}
        if state:
            params["state"] = state
        if custom is not None:
            params["custom"] = custom
        if llm_based is not None:
            params["llm-based"] = llm_based
        return self.get(f"{self.PREFIX}/metrics", params=params)

    def list_datasets(self, applicability: str = None) -> dict:
        """List datasets for prompt evaluation."""
        params = {}
        if applicability:
            params["applicability"] = applicability
        return self.get(f"{self.PREFIX}/datasets", params=params)

    def upload_dataset(self, file_path: str) -> dict:
        """Upload a dataset CSV file."""
        with open(file_path, "rb") as f:
            return self.post_multipart(f"{self.PREFIX}/datasets/upload", files={"file": f})

    def evaluate_prompt_dataset(self, request: dict) -> dict:
        """Evaluate a prompt against a dataset (async)."""
        return self.post_json(f"{self.PREFIX}/evaluate_prompt_dataset", body=request)

    def get_evaluation_status(self, request_id: str) -> dict:
        """Poll evaluation status."""
        return self.get(f"{self.PREFIX}/evaluation_status/{request_id}")

    def get_trace_logs(self, trace_id: str) -> dict:
        """Fetch trace logs for a specific execution."""
        return self.get(f"{self.PREFIX}/trace/logs/{trace_id}")

    def scan_compliance(self, request: dict) -> dict:
        """Trigger a compliance scan for a prompt."""
        return self.post_json(f"{self.PREFIX}/compliance/scan-compliance", body=request)

    def get_compliance_status(self, request_id: str) -> dict:
        """Poll compliance scan status."""
        return self.get(f"{self.PREFIX}/compliance/compliance-status/{request_id}")


class G3SClient(AIForceClient):
    """Client for G3S (GenAI Gateway & Guardrail Service)."""
    PREFIX = "/g3s"

    # ── LLM Calls ────────────────────────────────────────────────────
    def llm_call(self, request: dict) -> dict:
        """Execute an LLM call through the gateway."""
        return self.post_json(f"{self.PREFIX}/llm/call", body=request)

    def generate_embeddings(self, request: dict) -> dict:
        """Generate text embeddings."""
        return self.post_json(f"{self.PREFIX}/llm/embeddings", body=request)

    # ── LLM Configuration ───────────────────────────────────────────
    def save_llm_config(self, config: dict) -> dict:
        return self.post_json(f"{self.PREFIX}/configuration/save_llm_configuration", body=config)

    def list_llm_configs(self, page: int = 1, page_size: int = 10, search: str = None) -> dict:
        params = {"page": page, "page_size": page_size}
        if search:
            params["search"] = search
        return self.get(f"{self.PREFIX}/configuration/list_llm_configuration", params=params)

    def get_llm_config(self, llm_id: int) -> dict:
        return self.get(f"{self.PREFIX}/configuration/llm_configuration/{llm_id}")

    def update_llm_config(self, config_id: int, config: dict) -> dict:
        return self.put_json(f"{self.PREFIX}/configuration/update_llm_configuration/{config_id}", body=config)

    def delete_llm_config(self, config_id: int) -> dict:
        return self.delete(f"{self.PREFIX}/configuration/delete_llm_configuration", params={"config_id": config_id})

    # ── Embedding Configuration ──────────────────────────────────────
    def save_embedding_config(self, config: dict) -> dict:
        return self.post_json(f"{self.PREFIX}/configuration/save_embedding_configuration", body=config)

    def list_embedding_configs(self, page: int = 1, page_size: int = 10, search: str = None) -> dict:
        params = {"page": page, "page_size": page_size}
        if search:
            params["search"] = search
        return self.get(f"{self.PREFIX}/configuration/list_embedding_configuration", params=params)

    def update_embedding_config(self, config_id: int, config: dict) -> dict:
        return self.put_json(f"{self.PREFIX}/configuration/update_embedding_configuration/{config_id}", body=config)

    def delete_embedding_config(self, config_id: int) -> dict:
        return self.delete(f"{self.PREFIX}/configuration/delete_embedding_configuration", params={"config_id": config_id})

    # ── Speech Configuration ─────────────────────────────────────────
    def save_speech_config(self, config: dict) -> dict:
        return self.post_json(f"{self.PREFIX}/configuration/save_speech_model_configuration", body=config)

    def list_speech_configs(self, page: int = 1, page_size: int = 10, search: str = None) -> dict:
        params = {"page": page, "page_size": page_size}
        if search:
            params["search"] = search
        return self.get(f"{self.PREFIX}/configuration/list_speech_model_configuration", params=params)

    def update_speech_config(self, config_id: int, config: dict) -> dict:
        return self.put_json(f"{self.PREFIX}/configuration/update_speech_model_configuration/{config_id}", body=config)

    def delete_speech_config(self, config_id: int) -> dict:
        return self.delete(f"{self.PREFIX}/configuration/delete_speech_model_configuration/{config_id}")

    # ── Packages ─────────────────────────────────────────────────────
    def install_packages(self, request: dict) -> dict:
        return self.post_json(f"{self.PREFIX}/configuration/install_packages", body=request)

    # ── Consumption Tracking ─────────────────────────────────────────
    def get_consumption(self, project_id: int = None, config_name: str = None,
                        date_filter: str = None, custom_start: str = None,
                        custom_end: str = None) -> dict:
        """Get model consumption/cost records."""
        params = {}
        if project_id:
            params["project_id"] = project_id
        if config_name:
            params["config_name"] = config_name
        if date_filter:
            params["date_filter"] = date_filter
        if custom_start:
            params["custom_start"] = custom_start
        if custom_end:
            params["custom_end"] = custom_end
        return self.get(f"{self.PREFIX}/model-consumption/consumption", params=params)

    def get_config_names(self, lm_type: int = 1) -> dict:
        """Get config names by LLM type (1=LLM, 2=Embedding, 3=Speech)."""
        return self.get(f"{self.PREFIX}/model-consumption/config_list", params={"lm_type": lm_type})


class SGSClient(AIForceClient):
    """Client for SGS (Security Guardrails Service)."""
    PREFIX = "/sgs"

    # ── Auth Debug ───────────────────────────────────────────────────
    def get_token_context(self) -> dict:
        return self.get(f"{self.PREFIX}/register/token-context")

    # ── Master Control ───────────────────────────────────────────────
    def get_master_control(self) -> dict:
        return self.get(f"{self.PREFIX}/security-groups/config-control")

    def set_master_control(self, state: str = None, control_config: dict = None) -> dict:
        body = {}
        if state:
            body["state"] = state
        if control_config:
            body["control_config"] = control_config
        return self.put_json(f"{self.PREFIX}/security-groups/config-control", body=body)

    # ── Security Group Management ────────────────────────────────────
    def register_security_group(self, name: str, description: str = "") -> dict:
        return self.post_json(f"{self.PREFIX}/security-groups/register",
                              body={"name": name, "description": description})

    def list_security_groups(self, state: str = None, include_master: bool = False,
                             state_only: bool = False) -> dict:
        params = {}
        if state:
            params["state"] = state
        if include_master:
            params["include_master"] = include_master
        if state_only:
            params["state_only"] = state_only
        return self.get(f"{self.PREFIX}/security-groups/list", params=params)

    def configure_security_group(self, group_name: str, config: dict) -> dict:
        return self.put_json(f"{self.PREFIX}/security-groups/{group_name}/config", body=config)

    def get_security_group_config(self, group_name: str, view: str = "effective") -> dict:
        return self.get(f"{self.PREFIX}/security-groups/{group_name}/config", params={"view": view})

    def delete_security_group(self, group_name: str) -> dict:
        return self.delete(f"{self.PREFIX}/security-groups/{group_name}")

    # ── Master Scanners ──────────────────────────────────────────────
    def get_master_scanners(self) -> dict:
        return self.get(f"{self.PREFIX}/security-groups/master/scanners")

    def update_master_scanners(self, config: dict) -> dict:
        return self.put_json(f"{self.PREFIX}/security-groups/master/scanners", body=config)

    # ── Scanning ─────────────────────────────────────────────────────
    def scan_prompt(self, prompt_name: str, input_prompt: str,
                    variables: dict, security_group: str) -> dict:
        """Pre-flight: Scan a prompt for safety issues."""
        return self.post_json(f"{self.PREFIX}/scan/prompt", body={
            "prompt_name": prompt_name,
            "input_prompt": input_prompt,
            "variables": variables,
            "security_group": security_group
        })

    def scan_output(self, prompt_name: str, output: str,
                    prompt: str, security_group: str) -> dict:
        """Post-flight: Scan LLM output for safety issues."""
        return self.post_json(f"{self.PREFIX}/scan/output", body={
            "prompt_name": prompt_name,
            "output": output,
            "prompt": prompt,
            "security_group": security_group
        })


class GCSClient(AIForceClient):
    """Client for GCS (Governance, Risk & Compliance Service)."""

    # ── Registration ─────────────────────────────────────────────────
    def check_auth(self) -> dict:
        return self.get("/register/protected-resource")

    # ── Metric Configuration ─────────────────────────────────────────
    def list_metrics(self, metrics_name: str = None, applicability: str = None,
                     state: str = None, llm_based: bool = None,
                     custom: bool = None, page: int = 1, limit: int = 10) -> dict:
        params = {"page": page, "limit": limit}
        if metrics_name:
            params["metricsName"] = metrics_name
        if applicability:
            params["applicability"] = applicability
        if state:
            params["state"] = state
        if llm_based is not None:
            params["llm_based"] = llm_based
        if custom is not None:
            params["custom"] = custom
        return self.get("/config/metrics/", params=params)

    def update_metric_config(self, metric_name: str, applicability: str, config: dict) -> dict:
        return self.put_json(f"/config/metric_config/{metric_name}",
                             body=config, params={"applicability": applicability})

    def reset_metric_configs(self, metric_names: list) -> dict:
        return self.post_json("/config/metric_config/reset", body={"metric_names": metric_names})

    # ── Custom Metrics ───────────────────────────────────────────────
    def create_custom_metric(self, metric: dict) -> dict:
        return self.post_json("/custom/metrics/", body=metric)

    def list_custom_metrics(self, metric_name: str = None, applicability: str = None,
                            llm_based: bool = None, state: str = None,
                            status: str = None, page: int = 1, limit: int = 10) -> dict:
        params = {"page": page, "limit": limit}
        if metric_name:
            params["metric_name"] = metric_name
        if applicability:
            params["applicability"] = applicability
        if llm_based is not None:
            params["llm_based"] = llm_based
        if state:
            params["state"] = state
        if status:
            params["status"] = status
        return self.get("/custom/metrics/", params=params)

    def update_custom_metric(self, metric_name: str, applicability: str, body: dict) -> dict:
        return self.put_json("/custom/metrics/update",
                             body=body, params={"metric_name": metric_name, "applicability": applicability})

    def delete_custom_metric(self, metric_name: str) -> dict:
        return self.delete(f"/custom/metrics/{metric_name}")

    def create_and_install_packages(self, packages: list, environment: str = None) -> dict:
        body = {"packages": packages}
        if environment:
            body["environment"] = environment
        return self.post_json("/custom/metrics/create_and_install_packages", body=body)

    def vulnerability_check(self, script: str, packages: list) -> dict:
        return self.post_json("/custom/metrics/vulnerability_check",
                              body={"script": script, "packages": packages})

    # ── Validation ───────────────────────────────────────────────────
    def validate_prompt(self, request: dict) -> dict:
        return self.post_json("/validate/prompt", body=request)

    def validate_rag(self, request: dict) -> dict:
        return self.post_json("/validate/rag", body=request)

    def validate_agent(self, request: dict) -> dict:
        return self.post_json("/validate/agent", body=request)

    def get_evaluation_status(self, request_id: str = None) -> dict:
        params = {}
        if request_id:
            params["request_id"] = request_id
        return self.get("/validate/evaluation-status", params=params)

    # ── Dataset Management ───────────────────────────────────────────
    def create_dataset(self, name: str, description: str = "", use_case_type: str = "prompt") -> dict:
        return self.post_json("/datasets/create", body={
            "name": name, "description": description, "use_case_type": use_case_type
        })

    def list_datasets(self, applicability: str = None, use_case_type: str = None,
                      page: int = None, limit: int = None, time_filter: str = None,
                      name: str = None) -> dict:
        params = {}
        if applicability:
            params["applicability"] = applicability
        if use_case_type:
            params["use_case_type"] = use_case_type
        if page:
            params["page"] = page
        if limit:
            params["limit"] = limit
        if time_filter:
            params["time"] = time_filter
        if name:
            params["name"] = name
        return self.get("/datasets/", params=params)

    def download_dataset_template(self, use_case_type: str) -> dict:
        return self.get("/datasets/download", params={"use_case_type": use_case_type})

    def upload_dataset(self, file_path: str, dataset_name: str, use_case_type: str = "prompt") -> dict:
        with open(file_path, "rb") as f:
            return self.post_multipart("/datasets/upload",
                                       files={"file": f},
                                       data={"name": dataset_name, "use_case_type": use_case_type})

    def get_dataset_items(self, name: str, page: int = None, limit: int = None) -> dict:
        params = {"name": name}
        if page:
            params["page"] = page
        if limit:
            params["limit"] = limit
        return self.get("/datasets/items", params=params)

    def get_dataset_item(self, item_id: str) -> dict:
        return self.get(f"/datasets/items/{item_id}")

    def update_dataset_item(self, item_id: str, data: dict) -> dict:
        return self.put_json(f"/datasets/items/{item_id}", body=data)

    def delete_dataset_item(self, item_id: str) -> dict:
        return self.delete(f"/datasets/items/{item_id}")

    def delete_dataset(self, name: str) -> dict:
        return self.delete(f"/datasets/{name}")

    # ── Logs & Observability ─────────────────────────────────────────
    def create_trace(self, name: str, session_id: str = None, metadata: dict = None) -> dict:
        body = {"name": name}
        if session_id:
            body["session_id"] = session_id
        if metadata:
            body["metadata"] = metadata
        return self.post_json("/logs/trace/create", body=body)

    def log_llm_call(self, trace_data: dict) -> dict:
        return self.post_json("/logs/trace/llm_call", body=trace_data)

    def log_output(self, trace_data: dict) -> dict:
        return self.post_json("/logs/trace/update_output", body=trace_data)

    def log_embedding_search(self, trace_data: dict) -> dict:
        return self.post_json("/logs/trace/embedding-search", body=trace_data)

    def add_event(self, event_data: dict) -> dict:
        return self.post_json("/logs/trace/add_event", body=event_data)

    def get_trace(self, trace_id: str) -> dict:
        return self.get(f"/logs/{trace_id}")

    def delete_trace(self, trace_id: str) -> dict:
        return self.delete(f"/logs/{trace_id}")

    def list_traces(self, limit: int = 10, page: int = 1, name: str = None,
                    session_id: str = None, environment: str = None,
                    hours: int = None) -> dict:
        params = {"limit": limit, "page": page}
        if name:
            params["name"] = name
        if session_id:
            params["session_id"] = session_id
        if environment:
            params["environment"] = environment
        if hours:
            params["hours"] = hours
        return self.get("/logs/", params=params)

    # ── Testing Evaluators ───────────────────────────────────────────
    def test_prompt_evaluator(self, request: dict) -> dict:
        return self.post_json("/test/prompt", body=request)

    def test_rag_evaluator(self, request: dict) -> dict:
        return self.post_json("/test/rag", body=request)

    def test_agent_evaluator(self, request: dict) -> dict:
        return self.post_json("/test/agent", body=request)

    # ── Compliance ───────────────────────────────────────────────────
    def list_compliance_guidelines(self, page: int = None, limit: int = None) -> dict:
        params = {}
        if page:
            params["page"] = page
        if limit:
            params["limit"] = limit
        return self.get("/compliance/compliance-guidelines", params=params)

    def scan_compliance(self, request: dict) -> dict:
        return self.post_json("/compliance/scan-compliance", body=request)

    def get_compliance_status(self, request_id: str = None) -> dict:
        params = {}
        if request_id:
            params["request_id"] = request_id
        return self.get("/compliance/compliance-status", params=params)

    # ── G3S Proxy ────────────────────────────────────────────────────
    def get_llm_configuration_proxy(self, config_id: int = None) -> dict:
        params = {}
        if config_id:
            params["config_id"] = config_id
        return self.get("/g3sproxy/llm_configuration", params=params)
