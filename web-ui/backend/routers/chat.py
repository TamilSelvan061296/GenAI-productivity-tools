import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from ..services.agent import AgentService, extract_video_id
from ..models.schemas import SummarizeRequest, SummarizeResponse

router = APIRouter(prefix="/api", tags=["chat"])

# Store active conversations (in-memory for simplicity)
conversations: dict[str, dict] = {}


class ChatConnectionManager:
    """Manages WebSocket connections and their associated agents"""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.agents: dict[str, AgentService] = {}
        self.histories: dict[str, list] = {}

    async def connect(self, websocket: WebSocket, conversation_id: str):
        await websocket.accept()
        self.active_connections[conversation_id] = websocket
        self.histories[conversation_id] = []
        # Create agent for this connection
        self.agents[conversation_id] = await AgentService.create()

    def disconnect(self, conversation_id: str):
        if conversation_id in self.active_connections:
            del self.active_connections[conversation_id]
        if conversation_id in self.agents:
            del self.agents[conversation_id]
        if conversation_id in self.histories:
            del self.histories[conversation_id]

    async def send_message(self, conversation_id: str, message: dict):
        if conversation_id in self.active_connections:
            await self.active_connections[conversation_id].send_json(message)


manager = ChatConnectionManager()


@router.websocket("/chat/ws")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with the agent"""
    conversation_id = str(uuid.uuid4())

    try:
        await manager.connect(websocket, conversation_id)

        # Send conversation ID to client
        await manager.send_message(
            conversation_id, {"type": "connected", "conversation_id": conversation_id}
        )

        while True:
            data = await websocket.receive_json()
            user_message = data.get("message", "")

            if not user_message.strip():
                continue

            # Send typing indicator
            await manager.send_message(conversation_id, {"type": "typing"})

            try:
                # Get response from agent
                agent = manager.agents[conversation_id]
                history = manager.histories[conversation_id]
                response = await agent.chat(user_message, history)

                # Send response
                await manager.send_message(
                    conversation_id, {"type": "message", "content": response}
                )
            except Exception as e:
                await manager.send_message(
                    conversation_id,
                    {"type": "error", "content": f"Error processing message: {str(e)}"},
                )

    except WebSocketDisconnect:
        manager.disconnect(conversation_id)
    except Exception as e:
        manager.disconnect(conversation_id)
        raise e


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_video(request: SummarizeRequest):
    """Submit a YouTube URL for summarization"""
    # Extract video ID from URL
    video_id = extract_video_id(request.youtube_url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL")

    try:
        # Create a temporary agent for this request
        agent = await AgentService.create()

        # Use agent to fetch transcript and generate summary
        result = await agent.summarize_video(video_id)
        return SummarizeResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error summarizing video: {str(e)}")
