"""
YouTube Transcript Extraction Service

This service provides functionality to extract transcripts and metadata from YouTube videos.
"""

import re
import asyncio
from typing import Optional
from urllib.parse import urlparse, parse_qs

import httpx
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
from pydantic import BaseModel


class VideoMetadata(BaseModel):
    """Schema for YouTube video metadata."""
    video_id: str
    title: str
    author_name: str
    author_url: str
    thumbnail_url: Optional[str] = None


class TranscriptSegment(BaseModel):
    """Schema for a single transcript segment."""
    text: str
    start: float
    duration: float


class TranscriptResult(BaseModel):
    """Schema for complete transcript result."""
    video_id: str
    language: str
    language_code: str
    is_generated: bool
    segments: list[TranscriptSegment]
    full_text: str


class VideoProcessingResult(BaseModel):
    """Schema for complete video processing result."""
    metadata: VideoMetadata
    transcript: TranscriptResult


class YouTubeServiceError(Exception):
    """Base exception for YouTube service errors."""
    pass


class InvalidURLError(YouTubeServiceError):
    """Raised when YouTube URL is invalid."""
    pass


class VideoNotFoundError(YouTubeServiceError):
    """Raised when video is not found or unavailable."""
    pass


class TranscriptNotAvailableError(YouTubeServiceError):
    """Raised when transcript is not available."""
    pass


class YouTubeService:
    """Service for extracting transcripts and metadata from YouTube videos."""
    
    YOUTUBE_URL_PATTERNS = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
    ]
    
    OEMBED_URL = "https://www.youtube.com/oembed"
    
    def __init__(self):
        """Initialize the YouTube service."""
        self._transcript_api = YouTubeTranscriptApi()
    
    async def extract_video_id(self, url: str) -> str:
        """
        Extract video ID from various YouTube URL formats.
        
        Args:
            url: YouTube video URL
            
        Returns:
            11-character video ID
            
        Raises:
            InvalidURLError: If URL format is not recognized
        """
        url = url.strip()
        
        for pattern in self.YOUTUBE_URL_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        parsed = urlparse(url)
        if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
            query_params = parse_qs(parsed.query)
            if 'v' in query_params:
                video_id = query_params['v'][0]
                if len(video_id) == 11:
                    return video_id
        
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
        
        raise InvalidURLError(f"Invalid YouTube URL format: {url}")
    
    async def get_video_metadata(self, video_id: str) -> VideoMetadata:
        """
        Fetch video metadata using YouTube oEmbed API.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            VideoMetadata object with title, author, thumbnail
            
        Raises:
            VideoNotFoundError: If video is not found
        """
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.OEMBED_URL,
                    params={"url": video_url, "format": "json"},
                    timeout=10.0
                )
                
                if response.status_code == 404:
                    raise VideoNotFoundError(f"Video not found: {video_id}")
                
                response.raise_for_status()
                data = response.json()
                
                return VideoMetadata(
                    video_id=video_id,
                    title=data.get("title", "Unknown Title"),
                    author_name=data.get("author_name", "Unknown Author"),
                    author_url=data.get("author_url", ""),
                    thumbnail_url=data.get("thumbnail_url")
                )
                
            except httpx.HTTPStatusError as e:
                raise VideoNotFoundError(f"Video not found or unavailable: {video_id}") from e
            except httpx.RequestError as e:
                raise YouTubeServiceError(f"Network error fetching metadata: {str(e)}") from e
    
    def _fetch_transcript_sync(
        self, 
        video_id: str, 
        languages: list[str]
    ) -> TranscriptResult:
        """
        Synchronous method to fetch transcript (runs in thread pool).
        
        Args:
            video_id: YouTube video ID
            languages: List of preferred languages
            
        Returns:
            TranscriptResult object
        """
        try:
            transcript_list = self._transcript_api.list(video_id)
            
            transcript = None
            try:
                transcript = transcript_list.find_manually_created_transcript(languages)
            except NoTranscriptFound:
                try:
                    transcript = transcript_list.find_generated_transcript(languages)
                except NoTranscriptFound:
                    try:
                        transcript = transcript_list.find_transcript(languages)
                    except NoTranscriptFound:
                        available = list(transcript_list)
                        if available:
                            transcript = available[0]
            
            if transcript is None:
                raise TranscriptNotAvailableError(
                    f"No transcript available for video: {video_id}"
                )
            
            fetched = transcript.fetch()
            
            segments = [
                TranscriptSegment(
                    text=segment.text,
                    start=segment.start,
                    duration=segment.duration
                )
                for segment in fetched
            ]
            
            full_text = " ".join(segment.text for segment in segments)
            
            return TranscriptResult(
                video_id=video_id,
                language=transcript.language,
                language_code=transcript.language_code,
                is_generated=transcript.is_generated,
                segments=segments,
                full_text=full_text
            )
            
        except TranscriptsDisabled:
            raise TranscriptNotAvailableError(
                f"Transcripts are disabled for video: {video_id}"
            )
        except VideoUnavailable:
            raise VideoNotFoundError(f"Video unavailable: {video_id}")
        except NoTranscriptFound:
            raise TranscriptNotAvailableError(
                f"No transcript found for video: {video_id}"
            )
    
    async def get_transcript(
        self, 
        video_id: str, 
        languages: list[str] = None
    ) -> TranscriptResult:
        """
        Fetch transcript for a video.
        
        Args:
            video_id: YouTube video ID
            languages: List of preferred languages (default: ['en'])
            
        Returns:
            TranscriptResult with segments and full text
            
        Raises:
            TranscriptNotAvailableError: If no transcript available
            VideoNotFoundError: If video is unavailable
        """
        if languages is None:
            languages = ['en']
        
        return await asyncio.to_thread(
            self._fetch_transcript_sync, 
            video_id, 
            languages
        )
    
    async def process_video(
        self, 
        url: str, 
        languages: list[str] = None
    ) -> VideoProcessingResult:
        """
        Process a YouTube video URL to extract metadata and transcript.
        
        Args:
            url: YouTube video URL
            languages: List of preferred languages
            
        Returns:
            VideoProcessingResult with metadata and transcript
        """
        video_id = await self.extract_video_id(url)
        
        metadata, transcript = await asyncio.gather(
            self.get_video_metadata(video_id),
            self.get_transcript(video_id, languages)
        )
        
        return VideoProcessingResult(
            metadata=metadata,
            transcript=transcript
        )
    
    async def process_multiple_videos(
        self, 
        urls: list[str], 
        languages: list[str] = None
    ) -> dict[str, VideoProcessingResult | dict]:
        """
        Process multiple YouTube URLs.
        
        Args:
            urls: List of YouTube video URLs
            languages: List of preferred languages
            
        Returns:
            Dictionary mapping URLs to their processing results or errors
        """
        results = {}
        
        for url in urls:
            try:
                result = await self.process_video(url, languages)
                results[url] = result
            except YouTubeServiceError as e:
                results[url] = {"error": str(e), "error_type": type(e).__name__}
        
        return results
    
    async def validate_url(self, url: str) -> dict:
        """
        Validate a YouTube URL and return basic info.
        
        Args:
            url: YouTube video URL
            
        Returns:
            Dictionary with validation result
        """
        try:
            video_id = await self.extract_video_id(url)
            metadata = await self.get_video_metadata(video_id)
            return {
                "valid": True,
                "video_id": video_id,
                "title": metadata.title,
                "author": metadata.author_name
            }
        except InvalidURLError:
            return {"valid": False, "error": "Invalid YouTube URL format"}
        except VideoNotFoundError:
            return {"valid": False, "error": "Video not found or unavailable"}
        except YouTubeServiceError as e:
            return {"valid": False, "error": str(e)}


youtube_service = YouTubeService()
