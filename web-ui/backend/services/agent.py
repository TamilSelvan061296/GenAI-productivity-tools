import re
from typing import AsyncGenerator

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, MessagesState, START
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import AzureChatOpenAI

from ..config import settings


class AgentService:
    """Wrapper for LangGraph agent, adapted for web use"""

    def __init__(self, graph, mcp_client, tools):
        self.graph = graph
        self.mcp_client = mcp_client
        self.tools = tools

    @classmethod
    async def create(cls) -> "AgentService":
        """Factory method to create an initialized agent"""
        # Initialize LLM (same as existing langgraph_client.py)
        llm = AzureChatOpenAI(
            model_name=settings.MODEL_NAME,
            openai_api_version=settings.API_VERSION,
            azure_deployment=settings.DEPLOYMENT,
            azure_endpoint=settings.ENDPOINT,
            openai_api_key=settings.SUBSCRIPTION_KEY,
        )

        # Initialize MCP client (same config as existing)
        # Use uv run to ensure dependencies are available
        mcp_client = MultiServerMCPClient(
            {
                "youtube_server": {
                    "command": "uv",
                    "args": [
                        "--directory",
                        settings.YOUTUBE_SERVER_DIR,
                        "run",
                        "python",
                        settings.YOUTUBE_SERVER_PATH,
                    ],
                    "transport": "stdio",
                },
                "filesystem": {
                    "command": "docker",
                    "args": [
                        "run",
                        "-i",
                        "--rm",
                        "--mount",
                        f"type=bind,src={settings.KNOWLEDGE_BASE_PATH},dst=/projects/knowledge_youtube",
                        "mcp/filesystem",
                        "/projects/knowledge_youtube",
                    ],
                    "transport": "stdio",
                },
            }
        )

        # Get tools and build graph
        tools = await mcp_client.get_tools()

        def call_model(state: MessagesState):
            response = llm.bind_tools(tools).invoke(state["messages"])
            return {"messages": response}

        builder = StateGraph(MessagesState)
        builder.add_node(call_model)
        builder.add_node(ToolNode(tools))
        builder.add_edge(START, "call_model")
        builder.add_conditional_edges("call_model", tools_condition)
        builder.add_edge("tools", "call_model")
        graph = builder.compile()

        return cls(graph, mcp_client, tools)

    async def chat(self, message: str, history: list) -> str:
        """Send a chat message and get response"""
        history.append({"role": "user", "content": message})

        response = await self.graph.ainvoke({"messages": history})

        # Update history with response
        if response["messages"]:
            answer = response["messages"][-1].content
            history.clear()
            history.extend(
                [
                    {"role": m.type if hasattr(m, "type") else m.get("role", "user"), "content": m.content if hasattr(m, "content") else m.get("content", "")}
                    for m in response["messages"]
                    if hasattr(m, "content") or isinstance(m, dict)
                ]
            )
            return answer
        return "No response generated"

    async def summarize_video(self, video_id: str) -> dict:
        """Summarize a YouTube video using the agent"""
        prompt = f"""Please summarize the YouTube video with ID: {video_id}

1. First, fetch the transcript using the fetch_youtube_transcript tool
2. Then, create a comprehensive summary following the standard format with:
   - A clear title (as H1 heading)
   - Brief overview paragraph
   - Key points section (H2 heading with bullet points)
   - Notable quotes if any
   - Conclusion or call to action
3. Save the summary to a markdown file in /projects/knowledge_youtube/ directory using the write_file tool.
   Use a descriptive filename based on the video title (e.g., /projects/knowledge_youtube/Video_Title_Summary.md)

Return a confirmation when complete."""

        response = await self.graph.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )

        return {
            "status": "success",
            "message": response["messages"][-1].content if response["messages"] else "Processing complete",
            "summary_path": None,
        }


def extract_video_id(url: str) -> str | None:
    """Extract video ID from various YouTube URL formats"""
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",  # Direct video ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
