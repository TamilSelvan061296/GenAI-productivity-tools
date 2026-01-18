# Technical Documentation - GenAI Productivity Tools Web UI

This document provides an in-depth technical overview of the Web UI architecture, design decisions, and implementation details. It's written to help you understand not just *what* was built, but *why* specific choices were made.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack Decisions](#technology-stack-decisions)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Integration with Existing Systems](#integration-with-existing-systems)
6. [Data Flow](#data-flow)
7. [Key Design Patterns](#key-design-patterns)
8. [Security Considerations](#security-considerations)
9. [Error Handling Strategy](#error-handling-strategy)
10. [Performance Considerations](#performance-considerations)
11. [Lessons Learned & Debugging Notes](#lessons-learned--debugging-notes)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              BROWSER                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │   Browse    │  │    Chat     │  │ New Summary │                      │
│  │    Tab      │  │    Tab      │  │    Tab      │                      │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                      │
│         │                │                │                              │
│         │    REST API    │   WebSocket    │    REST API                 │
└─────────┼────────────────┼────────────────┼─────────────────────────────┘
          │                │                │
          ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         FASTAPI SERVER                                   │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │
│  │ /api/summaries  │  │  /api/chat/ws   │  │ /api/summarize  │         │
│  │   (REST)        │  │  (WebSocket)    │  │   (REST)        │         │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘         │
│           │                    │                    │                   │
│           ▼                    ▼                    ▼                   │
│  ┌─────────────────┐  ┌─────────────────────────────────────┐          │
│  │ KnowledgeBase   │  │         AgentService                │          │
│  │    Service      │  │  (LangGraph + MCP Client)           │          │
│  └────────┬────────┘  └────────┬───────────────┬────────────┘          │
│           │                    │               │                        │
└───────────┼────────────────────┼───────────────┼────────────────────────┘
            │                    │               │
            ▼                    ▼               ▼
    ┌───────────────┐   ┌───────────────┐  ┌───────────────┐
    │  Filesystem   │   │   YouTube     │  │  Filesystem   │
    │  (Direct)     │   │  MCP Server   │  │  MCP Server   │
    │               │   │  (uv run)     │  │  (Docker)     │
    └───────┬───────┘   └───────┬───────┘  └───────┬───────┘
            │                   │                  │
            ▼                   ▼                  ▼
    ┌───────────────┐   ┌───────────────┐  ┌───────────────┐
    │ knowledge_    │   │   YouTube     │  │ knowledge_    │
    │ youtube/*.md  │   │   API         │  │ youtube/*.md  │
    └───────────────┘   └───────────────┘  └───────────────┘
```

### Why This Architecture?

1. **Separation of Concerns**: Each layer has a single responsibility
   - Frontend: User interaction only
   - Routers: HTTP/WebSocket protocol handling
   - Services: Business logic
   - External: Data sources

2. **Async Throughout**: Python's `asyncio` enables handling many concurrent users without blocking

3. **Stateless REST + Stateful WebSocket**:
   - REST for simple CRUD operations (browsing summaries)
   - WebSocket for real-time chat (maintains conversation state)

---

## Technology Stack Decisions

### Backend: FastAPI

**Why FastAPI over Flask/Django?**

| Criteria | FastAPI | Flask | Django |
|----------|---------|-------|--------|
| Async Support | Native | Extension needed | Limited |
| WebSocket | Built-in | Extension needed | Channels needed |
| Type Hints | First-class | Optional | Optional |
| Auto Documentation | Yes (OpenAPI) | No | No |
| Performance | High | Medium | Medium |
| Learning Curve | Low | Low | High |

**Decision**: FastAPI was chosen because:
- Native async support matches the async LangGraph client
- Built-in WebSocket support for real-time chat
- Pydantic integration for request/response validation
- Auto-generated API documentation at `/docs`

### Frontend: Vanilla HTML/CSS/JS

**Why not React/Vue/Svelte?**

| Criteria | Vanilla JS | React | Vue |
|----------|------------|-------|-----|
| Bundle Size | 0 KB | ~40 KB | ~30 KB |
| Build Step | None | Required | Required |
| Learning Curve | None | Medium | Low |
| Complexity | Low | High | Medium |
| Maintainability | Good for small apps | Better for large apps | Better for large apps |

**Decision**: Vanilla JS was chosen because:
- This is a relatively simple 3-tab interface
- No build step means faster development iteration
- Easier to understand and debug
- No framework lock-in
- The app doesn't need complex state management

**Trade-off**: If the app grows significantly (10+ components, complex state), migrating to a framework would be beneficial.

### Real-time Communication: WebSocket

**Why WebSocket over Server-Sent Events (SSE) or Polling?**

| Method | Bidirectional | Latency | Complexity | Browser Support |
|--------|---------------|---------|------------|-----------------|
| WebSocket | Yes | Low | Medium | Universal |
| SSE | No (server→client only) | Low | Low | Good |
| Long Polling | Yes | High | High | Universal |

**Decision**: WebSocket was chosen because:
- Chat requires bidirectional communication (user sends, server responds)
- Low latency for responsive feel
- Maintains persistent connection for conversation context
- Native browser support without polyfills

---

## Backend Architecture

### Directory Structure

```
backend/
├── __init__.py
├── main.py              # FastAPI app entry point
├── config.py            # Configuration management
├── models/
│   ├── __init__.py
│   └── schemas.py       # Pydantic models for API
├── routers/
│   ├── __init__.py
│   ├── summaries.py     # REST endpoints for knowledge base
│   └── chat.py          # WebSocket + summarization endpoints
└── services/
    ├── __init__.py
    ├── knowledge_base.py # File operations on summaries
    └── agent.py          # LangGraph agent wrapper
```

### Why This Structure?

This follows a **layered architecture** pattern:

1. **Routers Layer** (`routers/`): Handles HTTP concerns
   - Request parsing
   - Response formatting
   - Route definitions
   - Protocol-specific logic (REST vs WebSocket)

2. **Services Layer** (`services/`): Contains business logic
   - Decoupled from HTTP layer
   - Can be tested independently
   - Reusable across different routers

3. **Models Layer** (`models/`): Data structures
   - Pydantic models for validation
   - Shared between layers

**Benefits**:
- Each file has a single responsibility
- Easy to test each layer in isolation
- New endpoints can reuse existing services
- Changes to one layer don't affect others

### Configuration Management (`config.py`)

```python
class Settings:
    MODEL_NAME: str = os.environ.get("MODEL_NAME", "gpt-4.1")
    API_VERSION: str = os.environ.get("API_VERSION", "2024-12-01-preview")
    # ... more settings
```

**Design Decisions**:

1. **Environment Variables**: Secrets (API keys) are loaded from `.env`
   - Never hardcoded in source code
   - Easy to change between environments (dev/prod)

2. **Path Resolution**: Uses `Path(__file__)` for relative paths
   ```python
   YOUTUBE_SERVER_DIR: str = str(
       Path(__file__).parent.parent.parent / "youtube-summarizer"
   )
   ```
   - Works regardless of where the app is run from
   - No hardcoded absolute paths in code

3. **Singleton Pattern**: `settings = Settings()` creates one instance
   - Configuration loaded once at startup
   - Shared across all modules

### Pydantic Models (`models/schemas.py`)

```python
class SummaryMetadata(BaseModel):
    filename: str
    title: str
    file_path: str
    modified_date: datetime
    preview: str
```

**Why Pydantic?**

1. **Automatic Validation**: Invalid data raises clear errors
2. **Type Coercion**: Strings automatically converted to datetime
3. **Serialization**: Easy JSON conversion
4. **Documentation**: Generates OpenAPI schema

**Design Decision - Separate Metadata vs Detail**:
```python
class SummaryMetadata(BaseModel):  # For list view
    preview: str  # First 200 chars

class SummaryDetail(BaseModel):    # For detail view
    content: str  # Full content
```

This reduces bandwidth - list view doesn't need full content.

### Knowledge Base Service (`services/knowledge_base.py`)

```python
class KnowledgeBaseService:
    async def list_all(self) -> list[SummaryMetadata]:
        summaries = []
        for file_path in self.base_path.glob("*.md"):
            meta = await self._extract_metadata(file_path)
            summaries.append(meta)
        return sorted(summaries, key=lambda x: x.modified_date, reverse=True)
```

**Design Decisions**:

1. **Async File I/O**: Uses `aiofiles` for non-blocking reads
   ```python
   async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
       content = await f.read()
   ```
   - Doesn't block the event loop while reading files
   - Allows handling other requests during I/O

2. **Title Extraction**: Parses H1 heading from markdown
   ```python
   def _extract_title(self, content: str) -> str:
       for line in content.strip().split("\n"):
           if line.startswith("# "):
               return line[2:].strip()
       return "Untitled"
   ```
   - No external markdown parser needed
   - Simple and fast

3. **Security - Path Traversal Prevention**:
   ```python
   safe_filename = Path(filename).name  # Removes directory components
   file_path = self.base_path / safe_filename
   ```
   - Prevents `../../etc/passwd` style attacks
   - Only allows files in the knowledge base directory

4. **Singleton Service**: `kb_service = KnowledgeBaseService()`
   - One instance shared across requests
   - Configuration loaded once

### Agent Service (`services/agent.py`)

This is the most complex service - it wraps the LangGraph agent for web use.

```python
class AgentService:
    @classmethod
    async def create(cls) -> "AgentService":
        # 1. Initialize LLM
        llm = AzureChatOpenAI(...)

        # 2. Initialize MCP Client with multiple servers
        mcp_client = MultiServerMCPClient({
            "youtube_server": {...},
            "filesystem": {...},
        })

        # 3. Get tools and build graph
        tools = await mcp_client.get_tools()

        # 4. Create LangGraph state machine
        builder = StateGraph(MessagesState)
        builder.add_node(call_model)
        builder.add_node(ToolNode(tools))
        # ... edges
        graph = builder.compile()

        return cls(graph, mcp_client, tools)
```

**Design Decisions**:

1. **Factory Pattern** (`@classmethod async def create`):
   - `__init__` can't be async in Python
   - Factory method allows async initialization
   - Clear separation of construction and initialization

2. **MCP Client Configuration**:
   ```python
   "youtube_server": {
       "command": "uv",
       "args": ["--directory", settings.YOUTUBE_SERVER_DIR, "run", "python", settings.YOUTUBE_SERVER_PATH],
       "transport": "stdio",
   }
   ```

   **Why `uv --directory` instead of just `python`?**
   - The YouTube server has its own dependencies (`youtube_transcript_api`)
   - Running with `uv` ensures the correct virtual environment
   - `--directory` sets the working directory for dependency resolution

3. **LangGraph State Machine**:
   ```
   START → call_model → [tools_condition] → tools → call_model → ...
                    ↓
                  END (if no tool calls)
   ```

   **Why this pattern?**
   - The model decides if it needs to call tools
   - If tools are called, results go back to the model
   - Model can chain multiple tool calls
   - Eventually terminates when no more tools needed

4. **Conversation History Management**:
   ```python
   async def chat(self, message: str, history: list) -> str:
       history.append({"role": "user", "content": message})
       response = await self.graph.ainvoke({"messages": history})
       # Update history with response...
   ```

   - History is passed by reference (list)
   - Modified in place to maintain conversation context
   - Enables multi-turn conversations

### WebSocket Chat Router (`routers/chat.py`)

```python
class ChatConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.agents: dict[str, AgentService] = {}
        self.histories: dict[str, list] = {}
```

**Design Decisions**:

1. **Connection Manager Pattern**:
   - Tracks all active WebSocket connections
   - Each connection has its own agent instance
   - Enables proper cleanup on disconnect

2. **Per-Connection Agent**:
   ```python
   async def connect(self, websocket: WebSocket, conversation_id: str):
       self.agents[conversation_id] = await AgentService.create()
   ```

   **Why create agent per connection?**
   - Each conversation needs its own state
   - MCP clients aren't thread-safe
   - Clean separation between users

   **Trade-off**: More memory usage, but necessary for isolation.

3. **Conversation ID**:
   ```python
   conversation_id = str(uuid.uuid4())
   ```

   - Unique identifier for each chat session
   - Sent to client for potential session resumption
   - Used to track agent and history

4. **Message Protocol**:
   ```python
   await manager.send_message(conversation_id, {"type": "typing"})
   await manager.send_message(conversation_id, {"type": "message", "content": response})
   ```

   Message types:
   - `connected`: Initial connection with conversation_id
   - `typing`: Server is processing (shows loading indicator)
   - `message`: Actual response content
   - `error`: Error occurred

### REST Summarize Endpoint

```python
@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_video(request: SummarizeRequest):
    video_id = extract_video_id(request.youtube_url)
    agent = await AgentService.create()
    result = await agent.summarize_video(video_id)
    return SummarizeResponse(**result)
```

**Why REST instead of WebSocket for summarization?**

1. **Request-Response Pattern**: One request, one response
2. **No Real-time Updates Needed**: User waits for completion
3. **Simpler Client Code**: Just a fetch() call
4. **Cacheable**: Could add caching later

**Video ID Extraction**:
```python
def extract_video_id(url: str) -> str | None:
    patterns = [
        r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",  # Direct video ID
    ]
```

- Handles multiple YouTube URL formats
- Also accepts raw video IDs
- Returns None for invalid URLs (triggers 400 error)

---

## Frontend Architecture

### File Structure

```
frontend/
├── index.html          # Single HTML page with all tabs
├── css/
│   └── styles.css      # All styling
└── js/
    ├── app.js          # Tab switching, utilities
    ├── summaries.js    # Browse tab logic
    ├── chat.js         # Chat tab + WebSocket
    └── summarize.js    # New Summary tab
```

### Why Single HTML Page?

This is a **Single Page Application (SPA)** pattern without a framework:

1. **No Page Reloads**: Tab switching is instant
2. **Shared State**: JavaScript variables persist across tabs
3. **Simpler Server**: Just serve static files

### Tab Switching Implementation

```javascript
// Show corresponding content
tabContents.forEach(content => {
    content.classList.remove('active');
    if (content.id === `${targetTab}-tab`) {
        content.classList.add('active');
    }
});
```

**CSS Controls Visibility**:
```css
.tab-content {
    display: none;
}
.tab-content.active {
    display: block;
}
```

**Why CSS classes instead of JavaScript style manipulation?**

1. **Separation of Concerns**: JS handles logic, CSS handles presentation
2. **Easier Transitions**: Can add CSS animations
3. **Debuggable**: Can inspect classes in DevTools

### WebSocket Chat Implementation

```javascript
function initChat() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/api/chat/ws`);
```

**Design Decisions**:

1. **Protocol Detection**: Automatically uses `wss:` for HTTPS
2. **Lazy Initialization**: Only connects when Chat tab is opened
   ```javascript
   if (targetTab === 'chat' && !window.chatInitialized) {
       initChat();
   }
   ```
   - Saves resources if user never opens Chat
   - Faster initial page load

3. **Auto-Reconnect**:
   ```javascript
   ws.onclose = () => {
       setTimeout(() => {
           if (document.getElementById('chat-tab').classList.contains('active')) {
               initChat();
           }
       }, 3000);
   };
   ```
   - Reconnects after 3 seconds
   - Only if Chat tab is still active

4. **Message Rendering with Markdown**:
   ```javascript
   if (role === 'assistant') {
       msgEl.innerHTML = marked.parse(content);
   }
   ```
   - Uses `marked.js` library for markdown
   - Only parses assistant messages (user messages are plain text)

### Fetch API Usage

```javascript
const response = await fetch(`${API_BASE}/summaries`);
const data = await response.json();
```

**Why async/await over callbacks?**

1. **Cleaner Code**: No callback hell
2. **Error Handling**: Can use try/catch
3. **Sequential Operations**: Easy to chain requests

---

## Integration with Existing Systems

### YouTube Summarizer MCP Server

The existing `youtube-summarizer/server.py` is a FastMCP server:

```python
@mcp.tool()
def fetch_youtube_transcript(video_id: str) -> str:
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
    return " ".join([item['text'] for item in transcript_list])
```

**Integration Challenge**: The server has its own dependencies.

**Solution**: Use `uv --directory` to run with correct environment:
```python
"command": "uv",
"args": ["--directory", settings.YOUTUBE_SERVER_DIR, "run", "python", settings.YOUTUBE_SERVER_PATH]
```

### Filesystem MCP Server (Docker)

```python
"filesystem": {
    "command": "docker",
    "args": [
        "run", "-i", "--rm",
        "--mount", f"type=bind,src={settings.KNOWLEDGE_BASE_PATH},dst=/projects/knowledge_youtube",
        "mcp/filesystem",
        "/projects/knowledge_youtube"
    ],
    "transport": "stdio",
}
```

**Why Docker for filesystem access?**

1. **Sandboxing**: Limits access to specific directory
2. **Standard MCP Server**: `mcp/filesystem` is an official image
3. **Consistent Behavior**: Same across different host systems

**Mount Path Decision**:
- Host: `/home/tamil/work/.../knowledge_youtube`
- Container: `/projects/knowledge_youtube`

The agent must use `/projects/knowledge_youtube` in prompts because that's what the container sees.

---

## Data Flow

### Browse Summaries Flow

```
User clicks summary card
         │
         ▼
summaries.js: viewSummary(filename)
         │
         ▼
fetch(`/api/summaries/${filename}`)
         │
         ▼
FastAPI Router: get_summary()
         │
         ▼
KnowledgeBaseService.get_by_filename()
         │
         ▼
aiofiles reads markdown file
         │
         ▼
SummaryDetail model created
         │
         ▼
JSON response to browser
         │
         ▼
marked.parse() renders markdown
         │
         ▼
innerHTML updated with rendered HTML
```

### Chat Message Flow

```
User types message and clicks Send
         │
         ▼
chat.js: sendMessage()
         │
         ▼
ws.send(JSON.stringify({ message }))
         │
         ▼
FastAPI WebSocket: websocket_chat()
         │
         ▼
ChatConnectionManager handles message
         │
         ▼
AgentService.chat(message, history)
         │
         ▼
LangGraph StateGraph processes:
  1. call_model node → LLM decides action
  2. If tool needed → ToolNode executes
  3. Results back to call_model
  4. Repeat until no more tools
         │
         ▼
Final response extracted
         │
         ▼
WebSocket sends {type: "message", content: ...}
         │
         ▼
chat.js: addMessage('assistant', content)
         │
         ▼
marked.parse() + innerHTML update
```

### New Summary Flow

```
User enters YouTube URL, clicks Summarize
         │
         ▼
summarize.js: click handler
         │
         ▼
fetch('/api/summarize', {method: 'POST', body: {youtube_url}})
         │
         ▼
FastAPI Router: summarize_video()
         │
         ▼
extract_video_id(url) → video_id
         │
         ▼
AgentService.create() → new agent
         │
         ▼
agent.summarize_video(video_id)
         │
         ▼
LangGraph executes prompt:
  1. fetch_youtube_transcript tool → transcript
  2. LLM generates summary
  3. write_file tool → saves to /projects/knowledge_youtube/
         │
         ▼
Response with success message
         │
         ▼
Browser shows success, refreshes summary list
```

---

## Key Design Patterns

### 1. Factory Pattern (AgentService)

```python
@classmethod
async def create(cls) -> "AgentService":
    # Complex async initialization
    return cls(graph, mcp_client, tools)
```

**When to use**: When object creation involves async operations or complex setup.

### 2. Singleton Pattern (KnowledgeBaseService)

```python
# At module level
kb_service = KnowledgeBaseService()

# In router
from ..services.knowledge_base import kb_service
```

**When to use**: When you need exactly one instance shared across the app.

### 3. Connection Manager Pattern (WebSocket)

```python
class ChatConnectionManager:
    active_connections: dict[str, WebSocket]
    agents: dict[str, AgentService]
    histories: dict[str, list]
```

**When to use**: Managing multiple stateful connections.

### 4. Repository Pattern (KnowledgeBaseService)

```python
class KnowledgeBaseService:
    async def list_all(self) -> list[SummaryMetadata]
    async def search(self, query: str) -> list[SummaryMetadata]
    async def get_by_filename(self, filename: str) -> SummaryDetail
```

**When to use**: Abstracting data access from business logic.

---

## Security Considerations

### 1. Path Traversal Prevention

```python
safe_filename = Path(filename).name  # Strips directory components
```

Without this, a request to `/api/summaries/../../etc/passwd` could read system files.

### 2. CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Current**: Allows all origins (development convenience)
**Production**: Should restrict to specific domains

### 3. Input Validation

```python
class SummarizeRequest(BaseModel):
    youtube_url: str  # Pydantic validates type

def extract_video_id(url: str) -> str | None:
    # Regex validates format
```

### 4. Environment Variables for Secrets

```python
SUBSCRIPTION_KEY = os.environ.get("SUBSCRIPTION_KEY")
```

Never commit `.env` files with real keys.

---

## Error Handling Strategy

### Backend Errors

```python
@router.get("/{filename}")
async def get_summary(filename: str):
    summary = await kb_service.get_by_filename(filename)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary not found")
    return summary
```

**Pattern**: Raise `HTTPException` for client errors, let unexpected errors propagate (500).

### WebSocket Errors

```python
try:
    response = await agent.chat(user_message, history)
    await manager.send_message(conversation_id, {"type": "message", "content": response})
except Exception as e:
    await manager.send_message(conversation_id, {"type": "error", "content": str(e)})
```

**Pattern**: Catch errors and send error message type to client.

### Frontend Errors

```javascript
try {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed');
    // ...
} catch (error) {
    container.innerHTML = `<div class="error">${error.message}</div>`;
}
```

**Pattern**: Show user-friendly error messages in the UI.

---

## Performance Considerations

### 1. Async I/O

All file operations use `aiofiles`:
```python
async with aiofiles.open(file_path, "r") as f:
    content = await f.read()
```

This prevents blocking the event loop during file reads.

### 2. Lazy Loading

- Chat WebSocket only connects when tab is opened
- Summaries loaded on-demand, not at page load

### 3. Preview Truncation

```python
preview = content[:200] + "..."
```

List view shows truncated content, reducing bandwidth.

### 4. Potential Improvements

1. **Caching**: Add Redis/in-memory cache for summaries
2. **Pagination**: Paginate summary list for large knowledge bases
3. **Connection Pooling**: Reuse MCP client connections
4. **Streaming**: Stream LLM responses for faster perceived performance

---

## Lessons Learned & Debugging Notes

### Issue 1: YouTube Server Module Not Found

**Symptom**: `ModuleNotFoundError: No module named 'youtube_transcript_api'`

**Cause**: Running `python server.py` used system Python, not the virtual environment.

**Solution**: Use `uv --directory <path> run python server.py` to use the correct environment.

### Issue 2: Filesystem MCP Path Error

**Symptom**: `Access denied - path outside allowed directories`

**Cause**: Agent tried to write to `/app/knowledge_base/` but container only allows `/projects/knowledge_youtube/`.

**Solution**: Updated prompt to explicitly specify `/projects/knowledge_youtube/` path.

### Issue 3: Chat/Summarize Tabs Blank

**Symptom**: Clicking Chat or New Summary tabs showed blank content.

**Cause**: HTML had `class="tab-content hidden"` and CSS had `.hidden { display: none !important; }`. The `!important` overrode `.tab-content.active { display: block; }`.

**Solution**: Removed `hidden` class from HTML. CSS `.tab-content` already handles visibility through `active` class.

**Lesson**: Avoid `!important` in CSS - it makes debugging harder.

### Issue 4: Browser Caching

**Symptom**: Changes to JS/HTML not reflected in browser.

**Cause**: Browser aggressively caches static files.

**Solution**:
- During development: Hard refresh (Ctrl+Shift+R)
- For production: Add cache-busting query params or use versioned filenames

---

## Conclusion

This architecture balances simplicity with extensibility. Key principles followed:

1. **Separation of Concerns**: Each component has one job
2. **Async First**: Non-blocking operations throughout
3. **Minimal Dependencies**: Vanilla JS frontend, focused backend
4. **Security by Default**: Input validation, path sanitization
5. **Clear Data Flow**: Easy to trace requests through the system

The codebase is designed to be understandable and maintainable, prioritizing clarity over cleverness.
