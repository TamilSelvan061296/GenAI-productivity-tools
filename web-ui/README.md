# GenAI Productivity Tools - Web UI

A web dashboard for browsing YouTube video summaries, chatting with an AI agent, and generating new summaries from YouTube videos.

---

## Features

- **Browse Summaries**: View and search all YouTube video summaries in your knowledge base
- **Chat Interface**: Have conversations with an AI agent that can access your summaries and tools
- **New Summary**: Generate summaries from YouTube videos by providing a URL

---

## Prerequisites

Before running the web UI, ensure you have the following installed:

### 1. Python 3.12+

Check your Python version:
```bash
python --version
# Should be 3.12 or higher
```

### 2. uv (Python Package Manager)

Install uv if you don't have it:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify installation:
```bash
uv --version
```

### 3. Docker

Required for the filesystem MCP server.

Install Docker: https://docs.docker.com/get-docker/

Verify installation:
```bash
docker --version
```

Pull the required MCP filesystem image:
```bash
docker pull mcp/filesystem
```

### 4. Azure OpenAI API Access

You need Azure OpenAI credentials:
- Endpoint URL
- API Key
- Deployment name

---

## Installation

### 1. Clone the Repository (if not already done)

```bash
git clone <repository-url>
cd GenAI-productivity-tools
```

### 2. Navigate to the Web UI Directory

```bash
cd web-ui
```

### 3. Install Dependencies

```bash
uv sync
```

This installs all required Python packages including:
- FastAPI
- Uvicorn
- LangGraph
- LangChain
- And more...

### 4. Configure Environment Variables

Create a `.env` file in the `web-ui` directory:

```bash
cp .env.example .env
# Or create manually:
```

Edit `.env` with your Azure OpenAI credentials:

```env
# Azure OpenAI Configuration
ENDPOINT = "https://your-resource.openai.azure.com/"
MODEL_NAME = "gpt-4.1"
DEPLOYMENT = "gpt-4.1"
SUBSCRIPTION_KEY = "your-api-key-here"
API_VERSION = "2024-12-01-preview"

# Knowledge Base Path (optional - defaults to ../youtube-summarizer/knowledge_youtube)
KNOWLEDGE_BASE_PATH = "/path/to/your/knowledge_youtube"

# Server Settings (optional)
HOST = "0.0.0.0"
PORT = 8000
```

---

## Running the Server

### Development Mode (with auto-reload)

```bash
cd web-ui
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode

```bash
cd web-ui
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Verify the Server is Running

Open your browser and navigate to:
- **Web UI**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

---

## Using the Web UI

### Browse Summaries Tab

1. The default tab shows all summaries in your knowledge base
2. **Search**: Type in the search box and click "Search" to filter summaries
3. **Clear**: Click "Clear" to reset the search and show all summaries
4. **View Summary**: Click on any summary card to view the full content
5. **Back**: Click "Back to list" to return to the summary grid

### Chat Tab

1. Click the "Chat" tab to open the chat interface
2. Wait for the status to show "Connected" (green)
3. Type your message in the text area
4. Press Enter or click "Send" to send your message
5. The AI agent can:
   - Answer questions about your summaries
   - Search through your knowledge base
   - Provide information based on the video content

**Example prompts:**
- "What summaries do you have about AI?"
- "Summarize the key points from the Bill Gates interview"
- "What are the productivity tips mentioned in the videos?"

### New Summary Tab

1. Click the "New Summary" tab
2. Enter a YouTube video URL in the input field
   - Supported formats:
     - `https://www.youtube.com/watch?v=VIDEO_ID`
     - `https://youtu.be/VIDEO_ID`
     - `VIDEO_ID` (just the 11-character ID)
3. Click "Summarize"
4. Wait for the process to complete (may take 1-2 minutes)
5. On success, the summary is saved to your knowledge base
6. Switch to "Browse Summaries" to see the new summary

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/summaries` | GET | List all summaries |
| `/api/summaries/search?q=<query>` | GET | Search summaries |
| `/api/summaries/<filename>` | GET | Get specific summary |
| `/api/chat/ws` | WebSocket | Real-time chat |
| `/api/summarize` | POST | Create new summary |

### Example API Calls

**List all summaries:**
```bash
curl http://localhost:8000/api/summaries
```

**Search summaries:**
```bash
curl "http://localhost:8000/api/summaries/search?q=productivity"
```

**Get specific summary:**
```bash
curl http://localhost:8000/api/summaries/Productivity_Tips_for_Startup_Founders.md
```

**Create new summary:**
```bash
curl -X POST http://localhost:8000/api/summarize \
  -H "Content-Type: application/json" \
  -d '{"youtube_url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

---

## Troubleshooting

### Server won't start

**Error**: `Address already in use`

Another process is using port 8000. Either:
1. Stop the other process: `fuser -k 8000/tcp`
2. Use a different port: `--port 8001`

### Chat shows "Connecting..." forever

1. Check if Docker is running: `docker ps`
2. Check server logs for MCP connection errors
3. Ensure the YouTube summarizer server path is correct

### Summarization fails

**Error**: `ModuleNotFoundError: youtube_transcript_api`

The YouTube server dependencies aren't installed:
```bash
cd ../youtube-summarizer
uv sync
```

**Error**: `Access denied - path outside allowed directories`

The agent tried to save to wrong path. This should be fixed, but if it happens, ensure the prompt uses `/projects/knowledge_youtube/` path.

### Changes not appearing in browser

The browser may be caching old files. Do a hard refresh:
- **Windows/Linux**: Ctrl + Shift + R
- **Mac**: Cmd + Shift + R

### WebSocket disconnects frequently

1. Check your network connection
2. The server may have restarted - refresh the page
3. Check server logs for errors

---

## Directory Structure

```
web-ui/
├── README.md              # This file
├── TECHNICAL.md           # Technical documentation
├── pyproject.toml         # Python dependencies
├── .env                   # Environment variables (create this)
├── backend/
│   ├── main.py            # FastAPI application
│   ├── config.py          # Configuration
│   ├── models/
│   │   └── schemas.py     # Data models
│   ├── routers/
│   │   ├── summaries.py   # Summary endpoints
│   │   └── chat.py        # Chat & summarize endpoints
│   └── services/
│       ├── knowledge_base.py  # File operations
│       └── agent.py           # AI agent wrapper
└── frontend/
    ├── index.html         # Main HTML page
    ├── css/
    │   └── styles.css     # Styling
    └── js/
        ├── app.js         # Tab switching
        ├── summaries.js   # Browse functionality
        ├── chat.js        # Chat functionality
        └── summarize.js   # Summarize functionality
```

---

## Development

### Running with Auto-Reload

For development, use the `--reload` flag:
```bash
uv run uvicorn backend.main:app --reload
```

The server will automatically restart when you modify Python files.

### Viewing API Documentation

FastAPI generates interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Adding New Features

1. **New API endpoint**: Add to `backend/routers/`
2. **New service**: Add to `backend/services/`
3. **New data model**: Add to `backend/models/schemas.py`
4. **Frontend changes**: Edit files in `frontend/`

See `TECHNICAL.md` for detailed architecture documentation.

---

## Configuration Reference

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENDPOINT` | Yes | - | Azure OpenAI endpoint URL |
| `MODEL_NAME` | Yes | - | Model name (e.g., gpt-4.1) |
| `DEPLOYMENT` | Yes | - | Azure deployment name |
| `SUBSCRIPTION_KEY` | Yes | - | Azure API key |
| `API_VERSION` | Yes | - | API version |
| `KNOWLEDGE_BASE_PATH` | No | `../youtube-summarizer/knowledge_youtube` | Path to summaries |
| `HOST` | No | `0.0.0.0` | Server host |
| `PORT` | No | `8000` | Server port |

---

## Related Documentation

- **Technical Documentation**: See `TECHNICAL.md` for architecture details
- **YouTube Summarizer**: See `../youtube-summarizer/README.md`
- **MCP Client**: See `../mcp-client/README.md`

---

## License

[Add your license here]

---

## Contributing

[Add contribution guidelines here]
