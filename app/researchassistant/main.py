from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.tools.mcp.mcp_client import MCPClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig, RetrievalConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager
from model.load import load_model

app = BedrockAgentCoreApp()
log = app.logger

# AgentCore Gateway endpoint — provides web search tools (auth handled by gateway)
GATEWAY_URL = "https://researchassistant-workshop-gateway-5qv5hyhepq.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp"

# AgentCore Memory
MEMORY_ID = "arn:aws:bedrock-agentcore:us-west-2:009835630890:memory/researchassistant_ResearchAssistantMemory-DnZ93qEt7e"
ACTOR_ID = "workshop-user"
REGION = "us-west-2"

DEFAULT_SYSTEM_PROMPT = """
You are a research assistant. You are helpful, provide clear and accurate answers
from general knowledge, admit when you are unsure about something, and keep your
responses concise.

You have persistent memory across sessions. You remember user preferences, facts
about the user, and past conversation summaries. When relevant, reference what you
know about the user to provide personalized and contextual responses.

When you don't know the answer or aren't confident, say so honestly rather than
guessing. Focus on being informative and direct.

You have access to web search tools. Use them when the user asks about current
events, recent information, or topics that benefit from up-to-date sources.
"""

# MCP client connecting to AgentCore Gateway
gateway_client = MCPClient(lambda: streamablehttp_client(GATEWAY_URL))

tools = [gateway_client]


def _extract_prompt(payload: dict):
    """Accept harness-style messages[], tool_results[], or plain prompt string payloads."""
    if "messages" in payload:
        return payload["messages"]
    if "tool_results" in payload:
        return [{"role": "user", "content": [{"toolResult": {
            "toolUseId": tr["toolUseId"],
            "status": tr.get("status", "success"),
            "content": tr.get("content", []),
        }} for tr in payload["tool_results"]]}]
    return payload.get("prompt", "")


@app.entrypoint
async def invoke(payload, context):
    log.info("Invoking Research Assistant.....")

    session_id = getattr(context, 'session_id', 'default-session')

    # Configure AgentCore Memory with long-term retrieval from all namespaces
    memory_config = AgentCoreMemoryConfig(
        memory_id=MEMORY_ID,
        session_id=session_id,
        actor_id=ACTOR_ID,
        retrieval_config={
            "/users/{actorId}/facts": RetrievalConfig(
                top_k=10,
                relevance_score=0.3,
            ),
            "/users/{actorId}/preferences": RetrievalConfig(
                top_k=5,
                relevance_score=0.5,
            ),
            "/summaries/{actorId}/{sessionId}": RetrievalConfig(
                top_k=5,
                relevance_score=0.5,
            ),
        },
    )

    with AgentCoreMemorySessionManager(
        agentcore_memory_config=memory_config,
        region_name=REGION,
    ) as session_manager:
        agent = Agent(
            model=load_model(),
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            tools=tools,
            session_manager=session_manager,
        )

        prompt = _extract_prompt(payload)

        async for event in agent.stream_async(prompt):
            if not isinstance(event, dict) or "event" not in event:
                continue
            cbs = event["event"].get("contentBlockStart")
            if cbs is not None and not cbs.get("start"):
                continue
            yield event


if __name__ == "__main__":
    app.run()
