import re
from typing import Dict, Any, Optional
from youtube_transcript_api import YouTubeTranscriptApi


def extract_youtube_video_id(url_or_id: str) -> Optional[str]:
    """Extract YouTube 11-character video ID from any YouTube URL format or raw ID."""
    url_or_id = url_or_id.strip()
    if len(url_or_id) == 11 and not any(c in url_or_id for c in "/?.=&"):
        return url_or_id

    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[&?]|$)',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/shorts\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/watch\?v=([0-9A-Za-z_-]{11})'
    ]
    for p in patterns:
        m = re.search(p, url_or_id)
        if m:
            return m.group(1)
    return None


def fetch_youtube_transcript(url_or_id: str, languages=('en', 'hi', 'ta', 'es', 'fr', 'de')) -> Dict[str, Any]:
    """
    Fetch full transcript from YouTube video URL or ID.
    Works seamlessly both locally and inside Cloud Run / Docker.
    """
    video_id = extract_youtube_video_id(url_or_id)
    if not video_id:
        return {
            "success": False,
            "error": f"Could not extract valid video ID from: '{url_or_id}'",
            "text": "",
            "videoId": None
        }

    try:
        api = YouTubeTranscriptApi()
        
        # Try fetching with preferred languages or default
        try:
            transcript = api.fetch(video_id, languages=languages)
        except Exception:
            transcript = api.fetch(video_id)

        snippets = getattr(transcript, 'snippets', transcript)
        full_text = " ".join([getattr(s, 'text', str(s)).strip() for s in snippets])
        
        # Clean transcript formatting
        full_text = re.sub(r'\[.*?\]', '', full_text)
        full_text = re.sub(r'\s+', ' ', full_text).strip()

        return {
            "success": True,
            "videoId": video_id,
            "charCount": len(full_text),
            "text": full_text
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to retrieve transcript: {str(e)}",
            "text": "",
            "videoId": video_id
        }
