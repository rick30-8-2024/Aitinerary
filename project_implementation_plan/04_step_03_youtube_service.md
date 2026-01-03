# Step 3: YouTube Transcript Extraction Service

## Objective
Create a service to extract transcripts from YouTube videos for analysis.

## Prerequisites
- Step 1 completed (Project Setup)

## Implementation Details

### 3.1 YouTube Service (`services/youtube_service.py`)

**Core Functions:**
```python
async def extract_video_id(url: str) -> str:
    """Extract video ID from various YouTube URL formats."""
    # Handle: youtube.com/watch?v=ID, youtu.be/ID, youtube.com/v/ID, etc.

async def get_transcript(video_id: str, languages: list = ['en']) -> str:
    """Fetch transcript for a video, return as formatted text."""

async def get_video_metadata(video_id: str) -> dict:
    """Get video title, duration, channel name (via oEmbed API)."""

async def process_multiple_videos(urls: list[str]) -> dict:
    """Process multiple URLs, return combined transcript and metadata."""
```

### 3.2 URL Validation & Parsing
Support these YouTube URL formats:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/v/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`
- With additional parameters (playlist, timestamp, etc.)

### 3.3 Transcript Processing
- Fetch transcript using `youtube-transcript-api`
- Combine all transcript segments into readable text
- Preserve timestamps for reference (optional)
- Handle missing transcripts gracefully

### 3.4 Error Handling
| Error | Response |
|-------|----------|
| Invalid URL | "Invalid YouTube URL format" |
| Video not found | "Video not found or unavailable" |
| No transcript | "No transcript available for this video" |
| Rate limited | Retry with backoff, then inform user |

### 3.5 API Endpoint (`api/routers/youtube.py`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/youtube/validate` | POST | Validate YouTube URLs |
| `/api/youtube/transcript` | POST | Extract transcript from URLs |

## Research Areas
- `youtube-transcript-api` language fallback options
- Video oEmbed API for metadata without API key
- Handling auto-generated vs manual transcripts

## Expected Outcome
- Can extract transcripts from any valid YouTube URL
- Graceful error handling for edge cases
- Returns formatted, readable transcript text
- Video metadata (title, channel) available

## Estimated Effort
1-2 days

## Dependencies
- Step 1: Project Setup
