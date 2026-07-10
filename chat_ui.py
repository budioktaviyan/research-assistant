"""
Web Chat UI for AgentCore Harness — single-file FastAPI app with SSE streaming.

Run:
    uv pip install fastapi uvicorn boto3
    uv run python chat_ui.py

Open: http://localhost:8000
"""

import json
import uuid
import boto3
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse

app = FastAPI()

# --- Configuration ---
HARNESS_ARN = "arn:aws:bedrock-agentcore:us-west-2:009835630890:harness/harness_budioktaviyan-tUUQoIzsYr"
REGION = "us-west-2"


def generate_session_id() -> str:
    """Generate a session ID with minimum 33 characters."""
    return f"session-{uuid.uuid4().hex}"  # 40 chars


HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Research Assistant</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f7f7f8;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .header {
            background: #ffffff;
            border-bottom: 1px solid #e5e5e5;
            padding: 16px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .header h1 {
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
        }

        .header .session-info {
            font-size: 12px;
            color: #888;
            font-family: monospace;
        }

        .new-chat-btn {
            padding: 8px 16px;
            background: #1a1a1a;
            color: #fff;
            border: none;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
        }

        .new-chat-btn:hover {
            background: #333;
        }

        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .message {
            max-width: 720px;
            width: 100%;
            margin: 0 auto;
            padding: 16px 20px;
            border-radius: 12px;
            line-height: 1.6;
            font-size: 15px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .message.user {
            background: #1a1a1a;
            color: #fff;
            align-self: flex-end;
            margin-left: auto;
            margin-right: 0;
            max-width: 600px;
        }

        .message.assistant {
            background: #ffffff;
            color: #1a1a1a;
            border: 1px solid #e5e5e5;
            align-self: flex-start;
            margin-left: 0;
            margin-right: auto;
            max-width: 680px;
        }

        .message.assistant.streaming {
            border-color: #007aff;
        }

        .input-area {
            background: #ffffff;
            border-top: 1px solid #e5e5e5;
            padding: 16px 24px;
        }

        .input-wrapper {
            max-width: 720px;
            margin: 0 auto;
            display: flex;
            gap: 12px;
        }

        .input-wrapper textarea {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            font-size: 15px;
            font-family: inherit;
            resize: none;
            outline: none;
            transition: border-color 0.2s;
            min-height: 44px;
            max-height: 120px;
        }

        .input-wrapper textarea:focus {
            border-color: #007aff;
        }

        .send-btn {
            padding: 12px 20px;
            background: #007aff;
            color: #fff;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.2s;
            align-self: flex-end;
        }

        .send-btn:hover {
            background: #005ecb;
        }

        .send-btn:disabled {
            background: #ccc;
            cursor: not-allowed;
        }

        .empty-state {
            display: flex;
            align-items: center;
            justify-content: center;
            flex: 1;
            color: #888;
            font-size: 16px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>Research Assistant</h1>
            <div class="session-info" id="sessionInfo"></div>
        </div>
        <button class="new-chat-btn" onclick="newChat()">New Chat</button>
    </div>

    <div class="chat-container" id="chatContainer">
        <div class="empty-state" id="emptyState">Start a conversation...</div>
    </div>

    <div class="input-area">
        <div class="input-wrapper">
            <textarea id="userInput" placeholder="Type your message..." rows="1"
                      onkeydown="handleKeyDown(event)"></textarea>
            <button class="send-btn" id="sendBtn" onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        let sessionId = generateSessionId();
        let isStreaming = false;
        let chatHistory = [];  // Track messages for multi-turn

        document.getElementById('sessionInfo').textContent = `Session: ${sessionId}`;

        function generateSessionId() {
            return 'session-' + crypto.randomUUID().replace(/-/g, '');
        }

        function newChat() {
            sessionId = generateSessionId();
            chatHistory = [];
            document.getElementById('sessionInfo').textContent = `Session: ${sessionId}`;
            document.getElementById('chatContainer').innerHTML =
                '<div class="empty-state" id="emptyState">Start a conversation...</div>';
            document.getElementById('userInput').focus();
        }

        function handleKeyDown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        }

        function autoResize(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
        }

        document.getElementById('userInput').addEventListener('input', function() {
            autoResize(this);
        });

        function appendMessage(role, content) {
            const emptyState = document.getElementById('emptyState');
            if (emptyState) emptyState.remove();

            const container = document.getElementById('chatContainer');
            const msg = document.createElement('div');
            msg.className = `message ${role}`;
            msg.textContent = content;
            container.appendChild(msg);
            container.scrollTop = container.scrollHeight;
            return msg;
        }

        async function sendMessage() {
            const input = document.getElementById('userInput');
            const text = input.value.trim();
            if (!text || isStreaming) return;

            isStreaming = true;
            document.getElementById('sendBtn').disabled = true;
            input.value = '';
            autoResize(input);

            appendMessage('user', text);

            // Add user message to history
            chatHistory.push({role: 'user', content: [{text: text}]});

            const assistantMsg = appendMessage('assistant', '');
            assistantMsg.classList.add('streaming');

            let fullResponse = '';

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        messages: chatHistory,
                        session_id: sessionId
                    })
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\\n');
                    buffer = lines.pop();

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            if (data === '[DONE]') continue;
                            try {
                                const parsed = JSON.parse(data);
                                if (parsed.text) {
                                    fullResponse += parsed.text;
                                    assistantMsg.textContent = fullResponse;
                                    document.getElementById('chatContainer').scrollTop =
                                        document.getElementById('chatContainer').scrollHeight;
                                }
                            } catch (e) {}
                        }
                    }
                }
            } catch (error) {
                fullResponse = `Error: ${error.message}`;
                assistantMsg.textContent = fullResponse;
            }

            // Add assistant response to history for multi-turn
            if (fullResponse && !fullResponse.startsWith('Error:')) {
                chatHistory.push({role: 'assistant', content: [{text: fullResponse}]});
            }

            assistantMsg.classList.remove('streaming');
            isStreaming = false;
            document.getElementById('sendBtn').disabled = false;
            input.focus();
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    session_id = body.get("session_id", generate_session_id())

    async def event_stream():
        try:
            client = boto3.client("bedrock-agentcore", region_name=REGION)

            response = client.invoke_harness(
                harnessArn=HARNESS_ARN,
                runtimeSessionId=session_id,
                messages=messages,
            )

            # Process the EventStream response
            event_stream_body = response.get("stream")
            if event_stream_body:
                for event in event_stream_body:
                    # Extract text from contentBlockDelta events
                    if "contentBlockDelta" in event:
                        delta = event["contentBlockDelta"].get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            yield f"data: {json.dumps({'text': text})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'text': f'Error: {str(e)}'})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
