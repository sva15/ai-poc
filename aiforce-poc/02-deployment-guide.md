# AIForce POC — Deployment Guide (AWS Lambda Console)

## Overview

This guide walks you through deploying the POC Lambda function using the **AWS Lambda Console** (no CLI, no zip files, no layers).

---

## Step 1: Create the Lambda Function

1. Go to **AWS Lambda Console** → **Create function**
2. Choose **Author from scratch**
3. Settings:
   * **Function name**: `aiforce-poc`
   * **Runtime**: `Python 3.12`
   * **Architecture**: `x86_64`
   * **Permissions**: Use an existing role that has:
     - `bedrock:InvokeModel` permission
     - Basic Lambda execution role
4. Click **Create function**

---

## Step 2: Paste the Code

1. In the **Code** tab, open the `lambda_function.py` file in the inline editor
2. **Delete** all existing code
3. **Copy and paste** the entire contents of `lambda_function.py` from this repository
4. Click **Deploy**

---

## Step 3: Set Environment Variables

Go to **Configuration** → **Environment variables** → **Edit** and add:

| Key | Value | Description |
|-----|-------|-------------|
| `AIFORCE_BASE_URL` | `https://54.91.159.104` | AIForce platform URL |
| `AIFORCE_AUTH_TOKEN` | `your-bearer-token` | Your AIForce auth token |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-haiku-20240307-v1:0` | Bedrock model to use |
| `AWS_REGION` | `us-east-1` | AWS region for Bedrock |
| `SECURITY_GROUP` | `poc-security-group` | Default SGS security group |

Click **Save**.

---

## Step 4: Increase Timeout

1. Go to **Configuration** → **General configuration** → **Edit**
2. Set **Timeout** to `1 min 0 sec`
3. Set **Memory** to `256 MB` (optional, default 128 MB is usually fine)
4. Click **Save**

---

## Step 5: Test the Function

Go to the **Test** tab and follow the scenarios in `03-testing-guide.md`.

---

## File Structure

The entire Lambda is a single file:

```
lambda_function.py     ← paste this into the Lambda console editor
```

**No layers, no dependencies, no zip files needed.**

- `urllib` — built into Python (for HTTP calls to PES, SGS, GCS, G3S)
- `boto3` — built into Lambda runtime (for Bedrock calls)
