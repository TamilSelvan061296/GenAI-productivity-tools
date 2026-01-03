from typing import Any
from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi

# initialize the MCP server
mcp = FastMCP("youtube_server")


# Helper functions
def format_transcript_response(transcript_object: str) -> str:
    """
    Formats the youtube transcript response
    """
    transcripts: list[str] = []
    for snippet in transcript_object:
        transcripts.append(snippet.text)
    final_transcript = "".join(transcripts)
    return final_transcript


# tool execution handler
@mcp.tool()
def fetch_youtube_transcript(video_id: str) -> str:
    """
    Fetch the youtube transcipt give a video_id
    Args:
        video_id: For eg: https://www.youtube.com/watch?v=12345 the ID is 12345

    Returns:
        Transcript of the given video_id
    """
    ytt_api = YouTubeTranscriptApi()
    fetched_transcript = ytt_api.fetch(video_id)
    final_transcript = format_transcript_response(fetched_transcript)
    return final_transcript


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")