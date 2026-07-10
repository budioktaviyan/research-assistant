import logging
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

logger = logging.getLogger(__name__)

GATEWAY_URL = "https://researchassistant-workshop-gateway-5qv5hyhepq.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp"

def get_streamable_http_mcp_client() -> MCPClient:
    """Returns an MCP Client connected to AgentCore Gateway"""
    return MCPClient(lambda: streamablehttp_client(GATEWAY_URL))