# AIForce POC — Deployment Guide

This guide details how to deploy the AIForce POC Lambda functions to AWS. Since all four Lambdas share the same HTTP client (`lambdas/shared/aiforce_client.py`), we will package the shared code with each Lambda function.

## Prerequisites

1.  **AWS CLI**: Installed and configured with your credentials (`aws configure`).
2.  **IAM Role**: You need an IAM execution role for the Lambda functions that allows basic execution (e.g., `AWSLambdaBasicExecutionRole`). *Optional: If your Lambdas need to call other AWS services directly (like Bedrock), attach the `AmazonBedrockFullAccess` policy.*

---

## Step 1: Create the Lambda Execution Role

If you don't already have one, create an IAM role for your Lambdas:

```bash
# 1. Create a trust policy file (trust-policy.json)
cat <<EOF > trust-policy.json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# 2. Create the role
aws iam create-role \
  --role-name aiforce-lambda-role \
  --assume-role-policy-document file://trust-policy.json

# 3. Attach basic execution policy for CloudWatch logs
aws iam attach-role-policy \
  --role-name aiforce-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

Keep the Role ARN handy (e.g., `arn:aws:iam::123456789012:role/aiforce-lambda-role`).

---

## Step 2: Package and Deploy the Lambdas

We will deploy four distinct Lambda functions: `aiforce-pes`, `aiforce-g3s`, `aiforce-sgs`, and `aiforce-gcs`.

Navigate to the `lambdas` directory where your code resides:

```bash
cd lambdas
```

### 1. Deploy PES (Prompt Engineering Service)

```bash
# Package the code and shared client
zip -r pes_lambda.zip pes_lambda.py shared/

# Create the function
aws lambda create-function \
  --function-name aiforce-pes \
  --runtime python3.9 \
  --handler pes_lambda.lambda_handler \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/aiforce-lambda-role \
  --zip-file fileb://pes_lambda.zip \
  --timeout 30

# Clean up
rm pes_lambda.zip
```

### 2. Deploy G3S (GenAI Gateway Service)

```bash
# Package the code
zip -r g3s_lambda.zip g3s_lambda.py shared/

# Create the function
aws lambda create-function \
  --function-name aiforce-g3s \
  --runtime python3.9 \
  --handler g3s_lambda.lambda_handler \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/aiforce-lambda-role \
  --zip-file fileb://g3s_lambda.zip \
  --timeout 30

# Clean up
rm g3s_lambda.zip
```

### 3. Deploy SGS (Security Guardrails Service)

```bash
# Package the code
zip -r sgs_lambda.zip sgs_lambda.py shared/

# Create the function
aws lambda create-function \
  --function-name aiforce-sgs \
  --runtime python3.9 \
  --handler sgs_lambda.lambda_handler \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/aiforce-lambda-role \
  --zip-file fileb://sgs_lambda.zip \
  --timeout 30

# Clean up
rm sgs_lambda.zip
```

### 4. Deploy GCS (Governance & Compliance Service)

```bash
# Package the code
zip -r gcs_lambda.zip gcs_lambda.py shared/

# Create the function
aws lambda create-function \
  --function-name aiforce-gcs \
  --runtime python3.9 \
  --handler gcs_lambda.lambda_handler \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/aiforce-lambda-role \
  --zip-file fileb://gcs_lambda.zip \
  --timeout 30

# Clean up
rm gcs_lambda.zip
```

---

## Step 3: Configure Environment Variables

The Lambdas require `AIFORCE_BASE_URL` and `AIFORCE_AUTH_TOKEN` to function. Update all four functions with your specifics:

```bash
export VARIABLES="Variables={AIFORCE_BASE_URL=https://54.91.159.104,AIFORCE_AUTH_TOKEN=your-bearer-token-here}"

aws lambda update-function-configuration --function-name aiforce-pes --environment "$VARIABLES"
aws lambda update-function-configuration --function-name aiforce-g3s --environment "$VARIABLES"
aws lambda update-function-configuration --function-name aiforce-sgs --environment "$VARIABLES"
aws lambda update-function-configuration --function-name aiforce-gcs --environment "$VARIABLES"
```

---

## Step 4: Optional API Gateway Setup

To invoke your Lambdas via HTTP endpoints, you can configure an **Amazon API Gateway** (HTTP API or REST API).

1. Go to the API Gateway Console.
2. Create an **HTTP API**.
3. Create routes mapping to your functions:
   * `POST /pes` → Integration: `aiforce-pes`
   * `POST /g3s` → Integration: `aiforce-g3s`
   * `POST /sgs` → Integration: `aiforce-sgs`
   * `POST /gcs` → Integration: `aiforce-gcs`
4. Deploy the API and note the Invoke URL.

---

## Updating Lambdas Later

To update the code without recreating the function:

```bash
cd lambdas
zip -r pes_lambda.zip pes_lambda.py shared/

aws lambda update-function-code \
  --function-name aiforce-pes \
  --zip-file fileb://pes_lambda.zip
```

---

## Step 5: Deploying the Full POC Orchestrator as a Single Lambda (Console)

If you want to run the entire Test Orchestrator inside a single AWS Lambda function via the AWS Console, follow these steps:

1. **Create the Function:**
   * Go to AWS Lambda Console.
   * Click **Create function**.
   * **Function name:** `aiforce-poc-orchestrator`
   * **Runtime:** Python 3.9+
   * **Execution role:** Use the `aiforce-lambda-role` we created in Step 1 (Ensure it has Bedrock permissions).
2. **Upload the Code Structure:**
   In the Lambda Code source editor, you must replicate this exact file structure:
   * Delete the default `lambda_function.py`.
   * Create `orchestrator.py` and paste the contents of `poc/orchestrator.py`.
   * Create `config.py` and paste the contents of `poc/config.py`.
   * Create `bedrock_client.py` and paste the contents of `poc/bedrock_client.py`.
   * Create a new folder named `shared`.
   * Inside `shared`, create `__init__.py` and paste the contents of `lambdas/shared/__init__.py`.
   * Inside `shared`, create `aiforce_client.py` and paste the contents of `lambdas/shared/aiforce_client.py`.
3. **Add the `requests` Library Layer:**
   Since AWS Lambda does not include the `requests` library by default:
   * Scroll down to **Layers** -> **Add a layer**.
   * Choose **AWS layers** or specify an ARN for the `requests` library in your specific region (e.g., `arn:aws:lambda:us-east-1:770693421928:layer:Klayers-p310-requests:8`). Alternatively, you can upload a zip file containing the `requests` package.
4. **Configure the Handler:**
   * Under **Runtime settings**, click **Edit**.
   * Change the **Handler** from `lambda_function.lambda_handler` to `orchestrator.lambda_handler`.
5. **Set Environment Variables:**
   * `AIFORCE_BASE_URL` = `https://54.91.159.104`
   * `AIFORCE_AUTH_TOKEN` = `your-bearer-token`
   * `AWS_REGION` = `us-east-1` (or your preferred Bedrock region)
6. **Increase Timeout:**
   * Under **Configuration** -> **General configuration**, increase the **Timeout** to at least **1 min 0 sec** (calling 4 APIs + Bedrock takes time).

