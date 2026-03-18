# Agent POC — Custom Script Tool Flow

Since the external MCP approach throws a UI/DB error when saving, we will use AIForce's native **Custom Script Tool** functionality via TCS.

This guide covers:
1. Creating a custom Python script tool inside TCS
2. Creating an Agent that uses this tool
3. Uploading an evaluation dataset
4. Evaluating the Agent (required before publishing)
5. Executing the Agent

---

## Step 1: Create a Custom Script Tool (TCS)

In TCS, `tool_type = 1` means **Custom Script**. The execution engine runs whatever Python code you provide in the `connector_script` field. Note that the platform will pass an `INPUT` dictionary containing the defined parameters, and expects the result to be stored in an `OUTPUT` variable.

```bash
curl -k -X POST "AIFORCE_URL/tcs/tools_library/publish_tool" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MathCalculator",
    "description": "Calculates basic mathematical expressions like (15 + 20) * 3",
    "tool_type": 1,
    "auth_type": 0,
    "publish_status": true,
    "is_active": true,
    "mcp_enabled": false,
    "is_public": true,
    "connector_script": "def calculate(expression):\n    try:\n        return str(eval(expression))\n    except Exception as e:\n        return str(e)\n\nOUTPUT = calculate(INPUT.get(\"expression\", \"0\"))",
    "function_list": ["calculate"],
    "input_details": {
      "expression": {
        "type": "string",
        "description": "The math expression to calculate"
      }
    },
    "output_details": {
      "result": {
        "type": "string",
        "description": "The result of the calculation"
      }
    },
    "virtual_env_name": "",
    "package_list": [],
    "documentation_type": null,
    "api_list": [],
    "connector_methods": [],
    "connector_actions": [],
    "authorization_type": 0,
    "authorization_config": [],
    "connector_properties": [],
    "json_schema": null,
    "is_connector": false,
    "vault_enabled": false
  }'
```

**What happens here:**
1. The AI decides it needs to use "MathCalculator" and generates the `"expression"` input.
2. The platform sets `INPUT = {"expression": "..."}`.
3. The platform executes the Python script string.
4. The script binds the result to the `OUTPUT` variable.
5. The platform returns the `OUTPUT` back to the LLM.

**Copy the `tool_id` from the response.**

---

## Step 2: Create the Agent (AMS)

Create the Agent and attach the `tool_id` from Step 1.

```bash
curl -k -X POST "AIFORCE_URL/ams/agentic-studio/agents" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "MathAgent",
    "description": "An agent that helps users with math problems using a calculator tool",
    "llm_model_id": 1, 
    "tools": [YOUR_TOOL_ID_HERE],
    "mcp_enabled": false,
    "publish_status": "Draft"
  }'
```
*(Replace `llm_model_id` with a valid ID from your environment, and `YOUR_TOOL_ID_HERE` with the ID from Step 1).*

**Copy the `agent_id` from the response.**

---

## Step 3: Evaluation Dataset Upload

Before an agent can be published, it must be evaluated. We first need to upload a dataset.
This endpoint accepts `multipart/form-data` with a file (usually CSV or JSON depending on the platform's exact implementation). 

> Note: If the platform UI is easier for this specific step, upload the CSV via the UI. The format generally requires `user_input` and `expected_output` columns.

If doing it via curl (assuming a JSON file named `dataset.json`):

**`dataset.json`**
```json
[
  {
    "user_input": "What is 15 * 10?",
    "expected_output": "150"
  },
  {
    "user_input": "Calculate 250 / 5",
    "expected_output": "50"
  }
]
```

```bash
curl -k -X POST "AIFORCE_URL/ams/agentic-studio/datasets/upload" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -F "name=MathEvalDataset" \
  -F "file=@dataset.json"
```

**Copy the `dataset_id` from the response.**

---

## Step 4: Evaluate the Agent

Run the evaluation job against the Draft agent.

```bash
curl -k -X POST "AIFORCE_URL/ams/agentic-studio/evaluate_agent" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": YOUR_AGENT_ID,
    "prompt_name": "math_evaluation",
    "agent_prompt": "Answer the math question accurately.",
    "metric_datasets": [YOUR_DATASET_ID]
  }'
```

After evaluation is complete, the agent can be marked as `Published` via a normal update call (`PUT /ams/agentic-studio/agents/{agent_id}` with `publish_status: "Published"`).

---

## Step 5: Execute the Agent

Once published (or if the platform allows execution in Draft mode for testing):

```bash
curl -k -X POST "AIFORCE_URL/ams/agentic-studio/agent-execution" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "agent": YOUR_AGENT_ID,
    "input": "I have 12 boxes, each containing 24 apples. If I sell 50 apples, how many are left?"
  }'
```

Expected Behavior:
1. Agent receives the complex question.
2. Agent realizes it needs to do `(12 * 24) - 50`.
3. Agent calls the `MathCalculator` custom script tool with that expression.
4. Python script runs via `eval()` and sets `OUTPUT = 238`.
5. Agent formulates the final response: "You have 238 apples left."
