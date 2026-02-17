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

## Instructions

1. First, fetch the transcript using the fetch_youtube_transcript tool

2. Analyze the transcript and identify the video type from these categories:
   - **Technical/Tutorial**: Coding, software, how-to guides, demos
   - **Science/Research**: Studies, experiments, scientific explanations
   - **Interview/Podcast**: Conversations, Q&A, discussions
   - **Documentary/Narrative**: Stories, journeys, biographical content
   - **News/Analysis**: Current events, opinion pieces, market analysis
   - **Motivational/Self-help**: Personal development, mindset, life advice
   - **Educational/Explainer**: Concept explanations, lectures, courses

3. Classify the video into exactly ONE of these folder categories:
   - **tech** — Coding, software, AI, tutorials, technical demos, technology
   - **science** — Studies, experiments, scientific explanations, health, research
   - **business** — Startups, finance, markets, entrepreneurship, investing, productivity
   - **culture** — Politics, society, history, documentaries, entertainment, interviews about life/society
   - **general** — Anything that doesn't clearly fit the above categories

4. Create a summary adapted to the video type:

   **For Technical/Tutorial:**
   - What problem does it solve? Prerequisites if any
   - Step-by-step breakdown of the approach
   - Key code concepts, commands, or techniques
   - Common pitfalls or tips mentioned

   **For Science/Research:**
   - What question or hypothesis is explored?
   - Key findings and the evidence behind them
   - Methodology overview (if relevant)
   - Implications and limitations

   **For Interview/Podcast:**
   - Who are the participants and their background?
   - Main topics discussed and different viewpoints
   - Most insightful exchanges or revelations
   - Key quotes with context

   **For Documentary/Narrative:**
   - What's the central story or theme?
   - Key characters or subjects and their journey
   - Major turning points or revelations
   - Emotional core and message

   **For News/Analysis:**
   - What's the main event or topic?
   - Key facts vs opinions (distinguish clearly)
   - Different perspectives presented
   - Implications and what to watch for

   **For Motivational/Self-help:**
   - Core message or philosophy
   - Main principles or frameworks
   - Actionable advice and steps
   - Personal stories or examples used

   **For Educational/Explainer:**
   - What concept is being explained?
   - How is it broken down? (analogies, examples)
   - Key definitions and relationships
   - How it connects to broader knowledge

## General Guidelines (Apply to All Types)

- Follow the video's natural flow with smooth transitions
- Provide context for quotes and key points
- Focus on extracting real knowledge and actionable takeaways
- Write coherently, not as disconnected bullet points

## Format

- Title (H1): Capture the video's essence
- Video Type: [Detected type] (in italics, right after title)
- Overview paragraph
- Main content sections (H2) appropriate to the type
- Key Takeaways section

5. Save the summary to the appropriate category subfolder using write_file tool.
   Filename: /projects/knowledge_youtube/{{category}}/[Descriptive_Title].md

   For example, if the category is "tech":
   /projects/knowledge_youtube/tech/Building_AI_Agents.md

6. End your response with this exact line (replace values accordingly):
   CATEGORY: {{category}}"""

        response = await self.graph.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )

        final_message = response["messages"][-1].content if response["messages"] else "Processing complete"

        # Parse category from LLM response
        category = None
        for line in final_message.split("\n"):
            if line.strip().startswith("CATEGORY:"):
                category = line.strip().split(":", 1)[1].strip().lower()
                if category not in ("tech", "science", "business", "culture", "general"):
                    category = "general"
                break

        return {
            "status": "success",
            "message": final_message,
            "summary_path": None,
            "category": category,
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
