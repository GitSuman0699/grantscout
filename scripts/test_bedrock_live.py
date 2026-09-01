"""Script to test live AWS Bedrock connectivity with the model IDs in .env."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load root .env
root_dir = Path(__file__).parent.parent
load_dotenv(root_dir / ".env")

import boto3
from strands.models.bedrock import BedrockModel

aws_region = os.getenv("AWS_REGION", "us-east-1")
model_id = os.getenv("BEDROCK_MODEL_ID")
fast_model_id = os.getenv("BEDROCK_FAST_MODEL_ID")
premium_model_id = os.getenv("BEDROCK_PREMIUM_MODEL_ID", model_id)

print("=" * 60)
print("TESTING LIVE AMAZON BEDROCK CONNECTIVITY")
print("=" * 60)
print(f"AWS Region: {aws_region}")
print(f"BEDROCK_MODEL_ID: {model_id}")
print(f"BEDROCK_FAST_MODEL_ID: {fast_model_id}")
print(f"BEDROCK_PREMIUM_MODEL_ID: {premium_model_id}")
print("-" * 60)

# Test raw boto3 bedrock-runtime client
try:
    client = boto3.client("bedrock-runtime", region_name=aws_region)
    print("[1] Testing raw boto3 bedrock-runtime client initialization... OK")
except Exception as e:
    print(f"[1] Failed to initialize boto3 client: {e}")
    sys.exit(1)

from strands import Agent

# Test Model 1: Standard/Premium Sonnet
print(f"\n[2] Testing invocation for Sonnet ({model_id})...")
try:
    model = BedrockModel(model_id=model_id, region_name=aws_region)
    agent = Agent(model=model, system_prompt="You are a helpful assistant. Keep answers under 10 words.")
    res = agent("Say 'Bedrock Sonnet is working!'")
    print(f"    SUCCESS: {res}")
except Exception as e:
    print(f"    ERROR for {model_id}: {e}")

# Test Model 2: Fast Haiku
print(f"\n[3] Testing invocation for Haiku ({fast_model_id})...")
try:
    fast_model = BedrockModel(model_id=fast_model_id, region_name=aws_region)
    fast_agent = Agent(model=fast_model, system_prompt="You are a helpful assistant. Keep answers under 10 words.")
    fast_res = fast_agent("Say 'Bedrock Haiku is working!'")
    print(f"    SUCCESS: {fast_res}")
except Exception as e:
    print(f"    ERROR for {fast_model_id}: {e}")
