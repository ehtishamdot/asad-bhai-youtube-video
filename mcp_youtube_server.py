import re
from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from youtube_transcript_api import YouTubeTranscriptApi
from tools.google import YouTubeTool, extract_video_id

mcp = FastMCP(
    'YouTube Server',
    dependencies=[
        'youtube_transcript_api',
        'google-api-python-client',
        'google-auth-httplib2',
        'google-auth-oauthlib'
    ],
)

yt_tool = YouTubeTool(r'<Google Cloud Client Secret File Path')

mcp.add_tool(yt_tool.get_video_info, name='Get-Video-Info', description='Get video information from YouTube')
mcp.add_tool(yt_tool.get_channel_info, name='Get-Channel-Info', description='Get channel information from YouTube')
mcp.add_tool(yt_tool.search_channel, name='Search-Channel', description='Search for YouTube channels')
mcp.add_tool(yt_tool.search_playlist, name='Search-Playlist', description='Search for YouTube playlists')
mcp.add_tool(yt_tool.search_videos, name='Search-Videos', description='Search for YouTube videos')
mcp.add_tool(yt_tool.get_channel_videos, name='Get-Channel-Videos', description='Get videos uploaded by a YouTube channel')
mcp.add_tool(extract_video_id, name='Extract-Video-ID', description='Extract YouTube Video ID from a given string')

@mcp.tool(name='Download-YouTube-Video-Transcript', description='Download the transcript of a YouTube video')
def download_transcript(video_id: str, include_timestamp: bool = False) -> str:
    """
    Download the transcript for a YouTube video.

    Args:
        video_id: YouTube video ID or URL.

    Returns:
        str: Transcript text of the video.
    """
    video_id = extract_video_id(video_id)
    if not video_id:
        return 'Invalid YouTube video ID or URL.'

    try:
        if include_timestamp:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = str(transcript)
        else:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = '\n'.join([entry['text'] for entry in transcript])

        return transcript_text
    except Exception as e:
        return f'Error downloading transcript: {str(e)}'
    
if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')    