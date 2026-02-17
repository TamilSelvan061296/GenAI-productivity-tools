# GenAI Productivity Tools - Complete Technical Reference

A multi-component AI productivity suite that transforms YouTube videos into a searchable, markdown-based personal knowledge base. Built with LangGraph agents, the Model Context Protocol (MCP), and a FastAPI web dashboard.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Component Deep Dive](#3-component-deep-dive)
4. [Technology Stack](#4-technology-stack)
5. [Data Models](#5-data-models)
6. [API Reference](#6-api-reference)
7. [Data Flow Diagrams](#7-data-flow-diagrams)
8. [Design Patterns](#8-design-patterns)
9. [Configuration Reference](#9-configuration-reference)
10. [Directory Structure](#10-directory-structure)
11. [Dependency Map](#11-dependency-map)
12. [Security Model](#12-security-model)
13. [Error Handling](#13-error-handling)
14. [Setup & Installation](#14-setup--installation)
15. [Development Guide](#15-development-guide)

---

## 1. Project Overview

### What It Does

- **Summarizes YouTube videos** by fetching transcripts and generating adaptive markdown summaries across 7 content categories (Technical, Science, Interview, Documentary, News, Motivational, Educational)
- **Manages a personal knowledge base** of video summaries stored as markdown files with full-text search
- **Provides an AI chat agent** (via WebSocket) that can answer questions using tools and conversation history
- **Exposes a web dashboard** with three tabs: Browse, Chat, and New Summary

### How It Works

A LangGraph-powered agent orchestrates the workflow. It connects to two MCP servers (YouTube transcript fetcher and a Docker-based filesystem writer), decides which tools to call, and produces structured output. The web UI communicates with this agent over REST and WebSocket endpoints served by FastAPI.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          BROWSER (Frontend)                         │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐       │
│  │  Browse Tab   │   │   Chat Tab   │   │  New Summary Tab │       │
│  │ (summaries.js)│   │  (chat.js)   │   │ (summarize.js)   │       │
│  └──────┬───────┘   └──────┬───────┘   └────────┬─────────┘       │
│         │ REST              │ WebSocket          │ REST             │
└─────────┼──────────────────┼────────────────────┼──────────────────┘
          │                  │                    │
          ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND (web-ui)                       │
│                                                                     │
│  ┌──────────────────┐  ┌────────────────────┐  ┌────────────────┐  │
│  │ GET /api/summaries│  │ WS /api/chat/ws   │  │POST /api/      │  │
│  │ GET /api/summaries│  │                    │  │   summarize    │  │
│  │    /search        │  │ ChatConnection     │  │                │  │
│  │ GET /api/summaries│  │   Manager          │  │ extract_       │  │
│  │    /<filename>    │  │                    │  │   video_id()   │  │
│  └────────┬─────────┘  └────────┬───────────┘  └───────┬────────┘  │
│           │                     │                       │           │
│           ▼                     ▼                       ▼           │
│  ┌─────────────────┐   ┌──────────────────────────────────────┐    │
│  │ KnowledgeBase   │   │         AgentService                 │    │
│  │    Service       │   │  ┌─────────────────────────────┐    │    │
│  │                  │   │  │   LangGraph StateGraph       │    │    │
│  │ - list_all()     │   │  │                             │    │    │
│  │ - search()       │   │  │  START → call_model ──┐    │    │    │
│  │ - get_by_        │   │  │          ▲            │    │    │    │
│  │   filename()     │   │  │          │     tools_condition  │    │
│  │                  │   │  │       tools ←─────────┘    │    │    │
│  └────────┬─────────┘   │  │          │                 │    │    │
│           │              │  │          └──── END         │    │    │
│           │              │  └─────────────────────────────┘    │    │
│           │              └──────┬─────────────────┬───────────┘    │
└───────────┼─────────────────────┼─────────────────┼────────────────┘
            │                     │                 │
            ▼                     ▼                 ▼
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │  Filesystem   │    │  YouTube     │    │  Filesystem  │
    │  (Direct I/O) │    │  MCP Server  │    │  MCP Server  │
    │               │    │  (uv run,    │    │  (Docker,    │
    │  aiofiles     │    │   stdio)     │    │   stdio)     │
    └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
           │                   │                   │
           ▼                   ▼                   ▼
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │ knowledge_   │    │  YouTube     │    │ knowledge_   │
    │ youtube/*.md │    │  Transcript  │    │ youtube/*.md │
    │              │    │  API         │    │              │
    └──────────────┘    └──────────────┘    └──────────────┘
```

### Communication Protocols

| Connection | Protocol | Purpose |
|---|---|---|
| Browser ↔ Browse API | HTTP REST | CRUD operations on summaries |
| Browser ↔ Chat API | WebSocket (`ws://` / `wss://`) | Bidirectional real-time chat |
| Browser ↔ Summarize API | HTTP REST (POST) | Trigger video summarization |
| Backend ↔ YouTube MCP Server | stdio (subprocess) | Fetch video transcripts |
| Backend ↔ Filesystem MCP Server | stdio (Docker container) | Write summary files |

---

## 3. Component Deep Dive

### 3.1 youtube-summarizer (MCP Server)

**Role**: Exposes the `fetch_youtube_transcript` tool over the Model Context Protocol.

**Entry point**: `youtube-summarizer/server.py`

```python
# FastMCP server with a single tool
mcp = FastMCP("youtube_server")

@mcp.tool()
def fetch_youtube_transcript(video_id: str) -> str:
    ytt_api = YouTubeTranscriptApi()
    fetched_transcript = ytt_api.fetch(video_id)
    return format_transcript_response(fetched_transcript)
```

- **Transport**: stdio (launched as subprocess by the web-ui backend)
- **Launch command**: `uv --directory <youtube-summarizer-dir> run python server.py`
- **Dependencies**: `mcp[cli]>=1.11.0`, `youtube-transcript-api>=1.1.1`
- **Storage**: Summaries are written to `knowledge_youtube/` by the filesystem MCP server, not by this server directly

### 3.2 mcp-client (CLI Client)

**Role**: Standalone command-line interface for interacting with the LangGraph agent.

**Entry point**: `mcp-client/langgraph_client.py`

- **Usage**: `cd mcp-client && uv run langgraph_client.py`
- **Interface**: Interactive REPL loop
- **Connects to**: Same two MCP servers (YouTube + filesystem)
- **LLM**: Azure OpenAI via `langchain-openai`
- **Dependencies**: `anthropic>=0.57.1`, `langchain-mcp-adapters>=0.1.9`, `langgraph>=0.5.2`, `mcp>=1.11.0`, `python-dotenv>=1.1.1`, `youtube-transcript-api>=1.1.1`

### 3.3 web-ui (Web Dashboard)

**Role**: Primary user interface — a FastAPI backend serving a vanilla JS frontend.

#### Backend (`web-ui/backend/`)

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app init, CORS, router registration, static file mount |
| `config.py` | Singleton `Settings` class loading env vars via `python-dotenv` |
| `models/schemas.py` | Pydantic models for all API request/response shapes |
| `routers/summaries.py` | REST endpoints for browsing and searching the knowledge base |
| `routers/chat.py` | WebSocket chat endpoint + POST summarize endpoint |
| `services/agent.py` | `AgentService` — factory-created LangGraph agent wrapper |
| `services/knowledge_base.py` | `KnowledgeBaseService` — async file I/O on markdown files |

#### Frontend (`web-ui/frontend/`)

| File | Responsibility |
|---|---|
| `index.html` | SPA shell with three tab sections |
| `css/styles.css` | All styling (~460 lines), responsive grid, chat UI |
| `js/app.js` | Tab switching, utility functions (`escapeHtml`, `formatDate`) |
| `js/summaries.js` | Fetches/renders summary cards, search with debouncing |
| `js/chat.js` | WebSocket lifecycle, auto-reconnect, markdown message rendering |
| `js/summarize.js` | YouTube URL form submission |

**External CDN dependency**: [Marked.js](https://cdn.jsdelivr.net/npm/marked/marked.min.js) for client-side markdown → HTML rendering.

---

## 4. Technology Stack

### Backend

| Technology | Version Constraint | Purpose |
|---|---|---|
| Python | >= 3.12 | Runtime |
| FastAPI | >= 0.115.0 | Web framework (async, WebSocket, auto-docs) |
| Uvicorn | >= 0.35.0 | ASGI server |
| LangGraph | >= 0.5.2 | Agent state machine orchestration |
| LangChain OpenAI | >= 0.3.27 | Azure OpenAI LLM integration |
| langchain-mcp-adapters | >= 0.1.9 | MCP ↔ LangChain tool bridge |
| MCP | >= 1.11.0 | Model Context Protocol SDK |
| FastMCP | (via `mcp[cli]`) | MCP server framework |
| youtube-transcript-api | >= 1.1.1 | YouTube transcript fetching |
| aiofiles | >= 24.0.0 | Non-blocking file I/O |
| python-dotenv | >= 1.1.1 | `.env` file loading |
| websockets | >= 14.0 | WebSocket protocol support |
| Pydantic | (via FastAPI) | Data validation and serialization |

### Frontend

| Technology | Delivery | Purpose |
|---|---|---|
| Vanilla JavaScript (ES6+) | Static files | UI logic, no framework |
| HTML5 | Static files | Markup |
| CSS3 | Static files | Styling, responsive layout |
| Marked.js | CDN | Markdown rendering |
| WebSocket API | Browser native | Real-time chat |
| Fetch API | Browser native | REST calls |

### Infrastructure

| Technology | Purpose |
|---|---|
| uv | Python package management and script runner |
| Docker | Sandboxed filesystem MCP server (`mcp/filesystem` image) |
| Azure OpenAI (GPT-4.1) | LLM provider |

---

## 5. Data Models

Defined in `web-ui/backend/models/schemas.py` using Pydantic:

```python
class SummaryMetadata(BaseModel):
    filename: str           # e.g. "AI_vs_Human_Developers.md"
    title: str              # Extracted from H1 heading
    file_path: str          # Absolute filesystem path
    modified_date: datetime # File modification timestamp
    preview: str            # First 200 chars of content

class SummaryDetail(BaseModel):
    filename: str
    title: str
    content: str            # Full markdown content
    modified_date: datetime

class SummaryListResponse(BaseModel):
    summaries: List[SummaryMetadata]
    total: int

class ChatMessage(BaseModel):
    role: str               # "user" or "assistant"
    content: str

class SummarizeRequest(BaseModel):
    youtube_url: str

class SummarizeResponse(BaseModel):
    status: str             # "success" or "error"
    message: str            # Agent's confirmation message
    summary_path: Optional[str]
```

**Design note**: `SummaryMetadata` (list view) uses a 200-char `preview` to reduce bandwidth. `SummaryDetail` (detail view) carries the full `content`.

---

## 6. API Reference

### REST Endpoints

| Method | Endpoint | Request | Response | Description |
|---|---|---|---|---|
| GET | `/api/health` | — | `{"status": "healthy"}` | Health check |
| GET | `/api/summaries` | — | `SummaryListResponse` | List all summaries, sorted newest first |
| GET | `/api/summaries/search?q=<query>` | Query param `q` | `SummaryListResponse` | Full-text search in filenames and content |
| GET | `/api/summaries/<filename>` | Path param | `SummaryDetail` or 404 | Get full summary content |
| POST | `/api/summarize` | `SummarizeRequest` JSON body | `SummarizeResponse` | Generate summary from YouTube URL |

### WebSocket Endpoint

**URL**: `/api/chat/ws`

**Message protocol** (JSON over WebSocket):

| Direction | Type | Payload | Description |
|---|---|---|---|
| Server → Client | `connected` | `{type, conversation_id}` | Connection established, includes session UUID |
| Client → Server | — | `{message: "..."}` | User chat message |
| Server → Client | `typing` | `{type}` | Agent is processing (show loading indicator) |
| Server → Client | `message` | `{type, content}` | Agent response (markdown) |
| Server → Client | `error` | `{type, content}` | Error message |

**Lifecycle**:
1. Client opens WebSocket → server creates new `AgentService` instance + conversation history
2. Server sends `connected` with UUID
3. Client sends messages → server responds with `typing` then `message`
4. On disconnect → server cleans up agent, history, and connection

### Auto-Generated Docs

FastAPI provides interactive API docs at runtime:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Example cURL Commands

```bash
# List all summaries
curl http://localhost:8000/api/summaries

# Search summaries
curl "http://localhost:8000/api/summaries/search?q=productivity"

# Get a specific summary
curl http://localhost:8000/api/summaries/Ray_Dalio_On_Wealth_Money_and_India_Summary.md

# Summarize a new video
curl -X POST http://localhost:8000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

---

## 7. Data Flow Diagrams

### 7.1 Video Summarization Flow

```
User enters YouTube URL in browser
        │
        ▼
POST /api/summarize  { youtube_url: "https://youtu.be/abc123" }
        │
        ▼
extract_video_id(url)  →  "abc123"
        │
        ▼
AgentService.create()  →  new LangGraph agent + MCP connections
        │
        ▼
agent.summarize_video("abc123")
        │
        ▼
┌─────────────────────────────────────────────────┐
│  LangGraph StateGraph Execution                 │
│                                                 │
│  1. call_model → LLM reads prompt, decides to   │
│     call fetch_youtube_transcript               │
│  2. ToolNode → YouTube MCP Server fetches       │
│     transcript via youtube-transcript-api       │
│  3. call_model → LLM analyzes transcript,       │
│     detects genre, generates markdown summary   │
│  4. ToolNode → Filesystem MCP Server writes     │
│     file to /projects/knowledge_youtube/        │
│  5. call_model → LLM confirms completion        │
│     (no more tool calls → END)                  │
└─────────────────────────────────────────────────┘
        │
        ▼
SummarizeResponse { status: "success", message: "..." }
        │
        ▼
Browser displays success, user can browse new summary
```

### 7.2 Chat Flow

```
User types message → chat.js sends via WebSocket
        │
        ▼
websocket_chat() handler receives JSON
        │
        ▼
Sends { type: "typing" } to client
        │
        ▼
AgentService.chat(message, history)
        │
        ▼
LangGraph agent processes with full conversation history
(may call tools: read files, fetch transcripts, etc.)
        │
        ▼
Response extracted from final message
        │
        ▼
Sends { type: "message", content: "..." } via WebSocket
        │
        ▼
chat.js renders markdown with marked.parse()
```

### 7.3 Browse/Search Flow

```
Browser loads page or user searches
        │
        ▼
GET /api/summaries  (or /api/summaries/search?q=...)
        │
        ▼
KnowledgeBaseService.list_all() or .search()
        │
        ▼
Glob knowledge_youtube/*.md → aiofiles reads each file
        │
        ▼
Extract metadata (H1 title, preview, modified date)
        │
        ▼
Sort by modified_date descending → JSON response
        │
        ▼
summaries.js renders grid of cards
        │
User clicks card → GET /api/summaries/<filename>
        │
        ▼
KnowledgeBaseService.get_by_filename()
        │
        ▼
Full markdown content → marked.parse() → rendered HTML
```

---

## 8. Design Patterns

### Factory Pattern — `AgentService.create()`

Python `__init__` cannot be async. The `@classmethod async def create()` factory handles async initialization (MCP client connections, tool loading, graph compilation) and returns a fully initialized instance.

```python
@classmethod
async def create(cls) -> "AgentService":
    llm = AzureChatOpenAI(...)
    mcp_client = MultiServerMCPClient({...})
    tools = await mcp_client.get_tools()
    # ... build graph
    return cls(graph, mcp_client, tools)
```

### Singleton Pattern — `KnowledgeBaseService`

Module-level instantiation ensures a single shared instance:

```python
kb_service = KnowledgeBaseService()  # services/knowledge_base.py
```

Routers import this singleton directly. Configuration is loaded once at startup.

### Connection Manager Pattern — `ChatConnectionManager`

Manages the lifecycle of multiple concurrent WebSocket sessions:

```python
class ChatConnectionManager:
    active_connections: dict[str, WebSocket]   # connection_id → socket
    agents: dict[str, AgentService]            # connection_id → agent
    histories: dict[str, list]                 # connection_id → message history
```

Each connection gets its own agent instance for state isolation.

### Repository Pattern — `KnowledgeBaseService`

Abstracts file system access behind a clean interface (`list_all`, `search`, `get_by_filename`), decoupling data access from HTTP/routing logic.

### Layered Architecture — Backend Structure

```
Routers (HTTP/WS protocol handling)
    ↓
Services (business logic)
    ↓
External (MCP servers, filesystem, LLM)
```

Each layer has a single responsibility and can be tested independently.

---

## 9. Configuration Reference

### Environment Variables (`.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `ENDPOINT` | Yes | `""` | Azure OpenAI endpoint URL |
| `SUBSCRIPTION_KEY` | Yes | `""` | Azure OpenAI API key |
| `MODEL_NAME` | No | `gpt-4.1` | Model name |
| `DEPLOYMENT` | No | `gpt-4.1` | Azure deployment name |
| `API_VERSION` | No | `2024-12-01-preview` | Azure API version |
| `KNOWLEDGE_BASE_PATH` | No | `../youtube-summarizer/knowledge_youtube` | Absolute path to summary storage |
| `HOST` | No | `0.0.0.0` | Server bind address |
| `PORT` | No | `8000` | Server bind port |

### Settings Class (`web-ui/backend/config.py`)

```python
class Settings:
    MODEL_NAME: str       # From env or "gpt-4.1"
    API_VERSION: str      # From env or "2024-12-01-preview"
    DEPLOYMENT: str       # From env or "gpt-4.1"
    ENDPOINT: str         # From env
    SUBSCRIPTION_KEY: str # From env
    KNOWLEDGE_BASE_PATH: str  # Resolved relative to project root
    YOUTUBE_SERVER_DIR: str   # Computed: <project>/youtube-summarizer/
    YOUTUBE_SERVER_PATH: str  # Computed: <project>/youtube-summarizer/server.py
    HOST: str
    PORT: int

settings = Settings()  # Singleton
```

Path resolution uses `Path(__file__).parent.parent.parent` to work from any working directory.

---

## 10. Directory Structure

```
GenAI-productivity-tools/
├── README.md                           # Project overview
├── TECHNICAL_DOCS.md                   # High-level technical docs
├── ARCHITECTURE.md                     # This file
├── .gitignore                          # Excludes .venv, .env, __pycache__, etc.
│
├── youtube-summarizer/                 # MCP Server component
│   ├── server.py                       # FastMCP server (fetch_youtube_transcript tool)
│   ├── instructions.md                 # Adaptive summarization prompt template
│   ├── pyproject.toml                  # Dependencies: mcp[cli], youtube-transcript-api
│   ├── README.md
│   └── knowledge_youtube/              # Shared knowledge base storage
│       ├── AI_vs_Human_Developers_Why_Automation_Isnt_Replacing_Coders_Anytime_Soon.md
│       ├── Andrew_Ng_AI_Landscape_Market_India_Strategy.md
│       ├── Ray_Dalio_On_Wealth_Money_and_India_Summary.md
│       └── ... (18+ summary files)
│
├── mcp-client/                         # CLI Client component
│   ├── langgraph_client.py             # Interactive REPL agent
│   ├── pyproject.toml                  # Dependencies
│   ├── .env                            # Azure OpenAI credentials
│   └── README.md
│
└── web-ui/                             # Web Dashboard component (primary)
    ├── README.md                       # User guide
    ├── TECHNICAL.md                    # Detailed architecture doc
    ├── pyproject.toml                  # Dependencies
    ├── .env                            # Azure OpenAI credentials
    ├── backend/
    │   ├── __init__.py
    │   ├── main.py                     # FastAPI app, CORS, static mount
    │   ├── config.py                   # Settings singleton
    │   ├── models/
    │   │   ├── __init__.py
    │   │   └── schemas.py              # Pydantic request/response models
    │   ├── routers/
    │   │   ├── __init__.py
    │   │   ├── summaries.py            # GET /api/summaries endpoints
    │   │   └── chat.py                 # WebSocket + POST /api/summarize
    │   └── services/
    │       ├── __init__.py
    │       ├── agent.py                # AgentService (LangGraph wrapper)
    │       └── knowledge_base.py       # KnowledgeBaseService (file ops)
    └── frontend/
        ├── index.html                  # SPA shell (3 tabs)
        ├── css/
        │   └── styles.css              # Responsive styling (~460 lines)
        └── js/
            ├── app.js                  # Tab switching, utilities
            ├── summaries.js            # Browse tab logic
            ├── chat.js                 # WebSocket chat logic
            └── summarize.js            # New Summary form logic
```

---

## 11. Dependency Map

### Inter-component Dependencies

```
web-ui (backend)
  ├── imports → youtube-summarizer/server.py (launched as MCP subprocess via uv)
  ├── imports → mcp/filesystem Docker image (launched as MCP subprocess)
  ├── reads/writes → youtube-summarizer/knowledge_youtube/*.md
  └── calls → Azure OpenAI API (GPT-4.1)

mcp-client
  ├── imports → youtube-summarizer/server.py (launched as MCP subprocess via uv)
  ├── imports → mcp/filesystem Docker image (launched as MCP subprocess)
  └── calls → Azure OpenAI API (GPT-4.1)

youtube-summarizer
  └── calls → YouTube Transcript API (external)
```

### Python Package Dependencies by Component

**youtube-summarizer** (`pyproject.toml`):
```
mcp[cli] >= 1.11.0
youtube-transcript-api >= 1.1.1
```

**mcp-client** (`pyproject.toml`):
```
anthropic >= 0.57.1
langchain-mcp-adapters >= 0.1.9
langchain-openai >= 0.3.27
langgraph >= 0.5.2
mcp >= 1.11.0
python-dotenv >= 1.1.1
youtube-transcript-api >= 1.1.1
```

**web-ui** (`pyproject.toml`):
```
fastapi >= 0.115.0
uvicorn[standard] >= 0.35.0
websockets >= 14.0
aiofiles >= 24.0.0
langchain-mcp-adapters >= 0.1.9
langchain-openai >= 0.3.27
langgraph >= 0.5.2
mcp >= 1.11.0
python-dotenv >= 1.1.1
```

---

## 12. Security Model

### Path Traversal Prevention

`KnowledgeBaseService.get_by_filename()` strips directory components:

```python
safe_filename = Path(filename).name  # "../../etc/passwd" → "passwd"
file_path = self.base_path / safe_filename
```

Only files with `.md` extension inside the knowledge base directory are served.

### Filesystem Sandboxing

The filesystem MCP server runs inside Docker with a bind mount limited to the knowledge base directory:

```python
"args": [
    "run", "-i", "--rm",
    "--mount", f"type=bind,src={settings.KNOWLEDGE_BASE_PATH},dst=/projects/knowledge_youtube",
    "mcp/filesystem",
    "/projects/knowledge_youtube",
]
```

The agent can only write to `/projects/knowledge_youtube/` inside the container.

### Secret Management

- API keys loaded from `.env` files via `python-dotenv`
- `.env` files excluded from version control via `.gitignore`
- No secrets hardcoded in source code

### CORS

Currently configured for development with `allow_origins=["*"]`. Should be restricted to specific domains in production.

### Input Validation

- Pydantic models validate all API request shapes and types
- `extract_video_id()` uses regex to validate YouTube URL formats
- Invalid URLs return HTTP 400

---

## 13. Error Handling

### Backend Strategy

| Layer | Pattern | Example |
|---|---|---|
| Routers (REST) | `raise HTTPException(status_code, detail)` | 404 for missing summary, 400 for invalid URL |
| Routers (WebSocket) | Send `{type: "error", content}` message | Agent processing failures |
| Services | Exceptions propagate to router layer | File not found, MCP connection errors |
| Summarize endpoint | `try/except → HTTPException(500)` | Wraps agent errors |

### Frontend Strategy

```javascript
try {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed');
    // ...
} catch (error) {
    container.innerHTML = `<div class="error">${error.message}</div>`;
}
```

WebSocket auto-reconnects after 3 seconds on disconnect (only if Chat tab is active).

---

## 14. Setup & Installation

### Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | >= 3.12 | `python --version` |
| uv | Latest | `uv --version` |
| Docker | Any recent | `docker --version` |
| Azure OpenAI | API access | Endpoint + API key |

### Step-by-step

```bash
# 1. Clone the repository
git clone <repository-url>
cd GenAI-productivity-tools

# 2. Pull the Docker image for filesystem MCP server
docker pull mcp/filesystem

# 3. Install youtube-summarizer dependencies
cd youtube-summarizer && uv sync && cd ..

# 4. Install web-ui dependencies
cd web-ui && uv sync

# 5. Configure environment
cp .env.example .env   # or create manually
# Edit .env with your Azure OpenAI credentials:
#   ENDPOINT = "https://your-resource.openai.azure.com/"
#   SUBSCRIPTION_KEY = "your-api-key"
#   MODEL_NAME = "gpt-4.1"
#   DEPLOYMENT = "gpt-4.1"
#   API_VERSION = "2024-12-01-preview"

# 6. Start the web server
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` in your browser.

### Alternative: CLI Client

```bash
cd mcp-client
cp .env.example .env   # configure credentials
uv sync
uv run langgraph_client.py
```

---

## 15. Development Guide

### Running in Development Mode

```bash
cd web-ui
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag auto-restarts the server on Python file changes. Frontend changes (HTML/CSS/JS) are served directly as static files and take effect on browser refresh.

### Adding a New API Endpoint

1. Define Pydantic models in `backend/models/schemas.py`
2. Create or extend a router in `backend/routers/`
3. If business logic is needed, add a service in `backend/services/`
4. Register the router in `backend/main.py` if new

### Adding a New MCP Tool

1. Add the tool function in `youtube-summarizer/server.py` with the `@mcp.tool()` decorator
2. The tool is automatically available to the agent (discovered via `mcp_client.get_tools()`)

### Supported YouTube URL Formats

The `extract_video_id()` function handles:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- Raw 11-character video ID

### Adaptive Summarization Types

The agent prompt in `AgentService.summarize_video()` instructs the LLM to detect the video genre and adapt the summary structure:

| Genre | Focus Areas |
|---|---|
| Technical/Tutorial | Problem, step-by-step breakdown, code concepts, pitfalls |
| Science/Research | Hypothesis, findings, methodology, implications |
| Interview/Podcast | Participants, topics, viewpoints, key quotes |
| Documentary/Narrative | Story, characters, turning points, message |
| News/Analysis | Facts vs opinions, perspectives, implications |
| Motivational/Self-help | Core message, principles, actionable advice |
| Educational/Explainer | Concept, breakdown, definitions, connections |

### Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| `Address already in use` | Port 8000 occupied | `fuser -k 8000/tcp` or use `--port 8001` |
| Chat stuck on "Connecting..." | Docker not running or MCP connection failed | Check `docker ps`, check server logs |
| `ModuleNotFoundError: youtube_transcript_api` | Missing dependencies | `cd youtube-summarizer && uv sync` |
| `Access denied - path outside allowed directories` | Agent writing to wrong path | Verify prompt uses `/projects/knowledge_youtube/` |
| Browser shows stale content | Browser cache | Hard refresh: Ctrl+Shift+R |

---

*Generated: 2026-02-15 | Branch: feature/ui-dashboard | Python 3.12+ | uv managed*
