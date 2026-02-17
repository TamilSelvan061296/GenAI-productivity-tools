# GenAI Productivity Tools - Technical Documentation

## 1. Project Overview

GenAI Productivity Tools is an AI-powered suite designed to help users efficiently consume and retain information from YouTube videos. The application automatically generates searchable, structured markdown summaries from YouTube video transcripts and provides a chat interface for interacting with the accumulated knowledge base.

### Core Capabilities

- **YouTube Video Summarization**: Automatically fetch video transcripts and generate comprehensive markdown summaries
- **Personal Knowledge Base**: Store, browse, and search through video summaries
- **AI Chat Agent**: Interact with a LangGraph-powered agent that can answer questions about your video summaries
- **Web Dashboard**: User-friendly interface for all features

---

## 2. Architecture

The project uses a multi-component architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                     GenAI-productivity-tools                     │
├──────────────────┬──────────────────────┬───────────────────────┤
│  youtube-summarizer │     mcp-client        │      web-ui          │
│  (MCP Server)       │  (CLI Client)         │   (Web Dashboard)    │
├──────────────────┼──────────────────────┼───────────────────────┤
│  - FastMCP server  │  - LangGraph agent    │   - FastAPI backend  │
│  - YouTube         │  - MCP client        │   - Vanilla JS/HTML  │
│    transcript API  │  - Azure OpenAI LLM   │   - WebSocket chat   │
│  - Tool: fetch_    │  - Tools: youtube +   │   - REST API         │
│    youtube_        │    filesystem        │                      │
│    transcript      │                      │                      │
└──────────────────┴──────────────────────┴───────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │   Shared Knowledge Base       │
              │   (markdown files in          │
              │   knowledge_youtube/)        │
              └───────────────────────────────┘
```

---

## 3. Components

### 3.1 youtube-summarizer (MCP Server)

**Purpose**: Provides tools for the AI agent to interact with YouTube

**Key Files**:
- `server.py` - MCP server using FastMCP framework
- `instructions.md` - Summarization prompt/guidelines

**Technology Stack**:
- FastMCP (MCP framework)
- youtube-transcript-api

**Tools Provided**:
- `fetch_youtube_transcript(video_id)` - Fetches transcript from YouTube videos

**Location**: `/home/tamil/work/GenAI-productivity-tools/youtube-summarizer/`

---

### 3.2 mcp-client (CLI Client)

**Purpose**: Command-line interface for interacting with the agent

**Key Files**:
- `langgraph_client.py` - Main CLI entry point

**Technology Stack**:
- LangGraph (agent orchestration)
- LangChain
- MultiServerMCPClient

**Dependencies**:
```
anthropic>=0.57.1
langchain-mcp-adapters>=0.1.9
langgraph>=0.5.2
mcp>=1.11.0
youtube-transcript-api>=1.1.1
```

**Location**: `/home/tamil/work/GenAI-productivity-tools/mcp-client/`

---

### 3.3 web-ui (Web Dashboard)

**Purpose**: User-friendly web interface for all features

**Backend Key Files**:
- `main.py` - FastAPI application
- `config.py` - Configuration
- `services/agent.py` - LangGraph agent wrapper
- `services/knowledge_base.py` - Knowledge base service

**Frontend Files**:
- `index.html` - Main HTML interface

**Backend Technology**:
- FastAPI
- Uvicorn
- LangGraph
- AzureChatOpenAI

**Frontend Technology**:
- Vanilla JavaScript
- HTML/CSS
- Marked.js (markdown rendering)

**Location**: `/home/tamil/work/GenAI-productivity-tools/web-ui/`

---

## 4. Data Flow

### 4.1 Summarizing a YouTube Video

```
User Input (YouTube URL)
        │
        ▼
┌───────────────────┐
│  Web UI / CLI     │
│  (user request)   │
└────────┬──────────┘
         │
         ▼
┌──────────────────────────────┐
│  FastAPI Backend            │
│  (web-ui/backend/main.py)   │
└─────────────┬────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│  AgentService (agent.py)                │
│  - Initializes LLM (Azure OpenAI)      │
│  - Connects to MCP servers             │
│    - YouTube MCP Server                 │
│    - Filesystem MCP Server (Docker)    │
└─────────────┬───────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────┐
│  LangGraph Agent Graph                  │
│  ┌──────────────────────────────────┐   │
│  │ 1. LLM receives user prompt     │   │
│  │ 2. LLM decides to call tools    │   │
│  │ 3. ToolNode executes tools:      │   │
│  │    - fetch_youtube_transcript    │   │
│  │    - write_file (to knowledge)   │   │
│  │ 4. LLM generates summary         │   │
│  └──────────────────────────────────┘   │
└─────────────┬────────────────────────────┘
              │
              ▼
┌─────────────────────────────┐
│  Summary saved to          │
│  knowledge_youtube/        │
│  (e.g., video_summary.md)  │
└─────────────────────────────┘
```

### 4.2 Chatting with the Agent

```
User sends message via WebSocket
        │
        ▼
┌─────────────────────────────┐
│  ChatConnectionManager     │
│  (manages connections)    │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  AgentService.chat()                │
│  - Sends message to LangGraph       │
│  - Maintains conversation history   │
└─────────────┬───────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  LangGraph Agent                    │
│  - Uses tools to access knowledge   │
│  - Answers questions                │
└─────────────┬───────────────────────┘
              │
              ▼
Response sent back via WebSocket
```

### 4.3 Browsing Summaries

```
User accesses Browse tab
        │
        ▼
GET /api/summaries
        │
        ▼
┌─────────────────────────────────────┐
│  KnowledgeBaseService              │
│  - Scans knowledge_youtube/*.md    │
│  - Extracts metadata               │
│  - Returns summary list             │
└─────────────┬───────────────────────┘
              │
              ▼
Frontend displays grid of summaries
```

---

## 5. Key Features

### 5.1 YouTube Video Summarization

**Supported URL Formats**:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- Direct video ID

**Adaptive Summarization Types**:
- Technical/Tutorial
- Science/Research
- Interview/Podcast
- Documentary/Narrative
- News/Analysis
- Motivational/Self-help
- Educational/Explainer

**Output Format** (Markdown):
- Title (H1)
- Video type
- Overview
- Main content sections (H2)
- Key Takeaways

---

### 5.2 Knowledge Base Management

- Stores summaries as markdown files in `knowledge_youtube/`
- Full-text search across titles and content
- Metadata extraction (title, modified date, preview)
- File-based storage (no database required)

---

### 5.3 AI Chat Interface

- Real-time WebSocket-based chat
- Maintains conversation history
- Can access both YouTube tools and knowledge base
- Context-aware responses

---

### 5.4 Web Dashboard

**Three Main Tabs**:
- **Browse**: View and search summaries
- **Chat**: Interactive AI conversations
- **New Summary**: Generate summaries from URLs

---

## 6. API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/summaries` | GET | List all summaries |
| `/api/summaries/search?q=<query>` | GET | Search summaries |
| `/api/summaries/<filename>` | GET | Get specific summary |
| `/api/chat/ws` | WebSocket | Real-time chat |
| `/api/summarize` | POST | Create new summary |

---

## 7. Configuration

The project uses Azure OpenAI with the following configuration:

| Parameter | Value |
|-----------|-------|
| Model | GPT-4.1 |
| API Version | 2024-12-01-preview |
| Deployment | gpt-4.1 |
| Configuration | Via `.env` file |

**Required Environment Variables**:
```
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_ENDPOINT=<your-endpoint>
AZURE_OPENAI_DEPLOYMENT=gpt-4.1
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

---

## 8. Technology Stack

### Backend
- **Framework**: FastAPI
- **Server**: Uvicorn
- **AI Agent**: LangGraph, LangChain
- **LLM Provider**: Azure OpenAI (GPT-4.1)
- **MCP**: FastMCP, MultiServerMCPClient
- **YouTube**: youtube-transcript-api

### Frontend
- **Language**: Vanilla JavaScript
- **Markup**: HTML5
- **Styling**: CSS3
- **Markdown**: Marked.js
- **Communication**: WebSocket, REST API

### Development
- **Python**: 3.11+
- **Protocol**: MCP (Model Context Protocol)

---

## 9. Directory Structure

```
GenAI-productivity-tools/
├── youtube-summarizer/           # MCP Server
│   ├── server.py                # FastMCP server
│   ├── instructions.md          # Summarization prompts
│   └── knowledge_youtube/       # Summaries storage
│       └── *.md                 # Video summaries
├── mcp-client/                  # CLI Client
│   └── langgraph_client.py      # Main CLI entry
├── web-ui/                      # Web Dashboard
│   ├── backend/
│   │   ├── main.py             # FastAPI app
│   │   ├── config.py           # Configuration
│   │   └── services/
│   │       ├── agent.py        # LangGraph agent
│   │       └── knowledge_base.py
│   └── frontend/
│       └── index.html          # Main UI
└── .env                         # Environment config
```

---

## 10. Installation & Setup

### Prerequisites
- Python 3.11+
- Azure OpenAI API access

### Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd GenAI-productivity-tools
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**
   ```bash
   # Install main dependencies
   pip install -r requirements.txt

   # Or install individually
   pip install fastapi uvicorn langgraph langchain-azure-openai
   pip install anthropic langchain-mcp-adapters mcp
   pip install youtube-transcript-api
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure OpenAI credentials
   ```

5. **Run the application**
   ```bash
   # Start web UI
   cd web-ui/backend
   uvicorn main:app --reload

   # Or use the MCP client directly
   cd mcp-client
   python langgraph_client.py
   ```

---

## 11. Usage Examples

### Summarize a YouTube Video

```python
# Via web UI
# 1. Navigate to http://localhost:8000
# 2. Go to "New Summary" tab
# 3. Enter YouTube URL
# 4. Click "Generate Summary"
```

### Chat with the Knowledge Base

```python
# Via web UI
# 1. Navigate to http://localhost:8000
# 2. Go to "Chat" tab
# 3. Ask questions about your video summaries
```

### Browse Summaries

```python
# Via web UI
# 1. Navigate to http://localhost:8000
# 2. Go to "Browse" tab
# 3. Search or view all summaries
```

---

## 12. License

[Specify license here]

---

## 13. Contributing

[Specify contribution guidelines here]

---

*Generated on: 2026-02-15*
*Repository: GenAI-productivity-tools*
*Branch: feature/ui-dashboard*
