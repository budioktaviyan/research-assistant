"""Invoke an AgentCore Harness with streaming response via boto3."""

import json
import uuid
import boto3

HARNESS_ARN = "arn:aws:bedrock-agentcore:us-west-2:009835630890:harness/harness_budioktaviyan-tUUQoIzsYr"
REGION = "us-west-2"

# Session ID minimal 33 karakter
SESSION_ID = f"session-{uuid.uuid4().hex}"  # 40 karakter total


def invoke_harness(prompt: str):
    client = boto3.client("bedrock-agentcore-runtime", region_name=REGION)

    response = client.invoke_harness(
        harnessArn=HARNESS_ARN,
        sessionId=SESSION_ID,
        payload=json.dumps({"prompt": prompt}),
    )

    # Stream response
    event_stream = response.get("body") or response.get("responseStream")
    if event_stream:
        for event in event_stream:
            if "chunk" in event:
                chunk = event["chunk"]
                text = chunk.get("bytes", b"").decode("utf-8")
                print(text, end="", flush=True)
    else:
        # Fallback jika tidak streaming
        body = response.get("body", "")
        if hasattr(body, "read"):
            body = body.read().decode("utf-8")
        print(body)

    print()  # newline di akhir


if __name__ == "__main__":
    user_prompt = input("Prompt: ")
    invoke_harness(user_prompt)
