"""
YouTube API Router

Provides endpoints for YouTube video validation and transcript extraction.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, HttpUrl, field_validator

from services.youtube_service import (
    youtube_service,
    InvalidURLError,
    VideoNotFoundError,
    TranscriptNotAvailableError,
    ProxyError,
    YouTubeServiceError,
    VideoMetadata,
    TranscriptResult,
    VideoProcessingResult
)
from api.dependencies import get_current_user
from models.user import UserInDB


router = APIRouter(prefix="/api/youtube", tags=["YouTube"])


class URLValidateRequest(BaseModel):
    """Request schema for URL validation."""
    url: str


class URLValidateResponse(BaseModel):
    """Response schema for URL validation."""
    valid: bool
    video_id: str | None = None
    title: str | None = None
    author: str | None = None
    error: str | None = None


class TranscriptRequest(BaseModel):
    """Request schema for transcript extraction."""
    urls: list[str]
    languages: list[str] = ["en"]
    
    @field_validator("urls")
    @classmethod
    def validate_urls_not_empty(cls, v):
        if not v:
            raise ValueError("At least one URL is required")
        if len(v) > 5:
            raise ValueError("Maximum 5 URLs allowed per request")
        return v


class TranscriptResponse(BaseModel):
    """Response schema for transcript extraction."""
    success: bool
    results: dict
    total_videos: int
    successful_count: int
    failed_count: int


class SingleVideoRequest(BaseModel):
    """Request schema for single video processing."""
    url: str
    languages: list[str] = ["en"]


class SingleVideoResponse(BaseModel):
    """Response schema for single video processing."""
    success: bool
    video_id: str
    metadata: VideoMetadata
    transcript: TranscriptResult


@router.post("/validate", response_model=URLValidateResponse)
async def validate_youtube_url(
    request: URLValidateRequest,
    current_user: UserInDB = Depends(get_current_user)
) -> URLValidateResponse:
    """
    Validate a YouTube URL and return basic video information.
    
    - **url**: YouTube video URL to validate
    
    Returns video ID, title, and author if valid.
    """
    result = await youtube_service.validate_url(request.url)
    
    return URLValidateResponse(
        valid=result.get("valid", False),
        video_id=result.get("video_id"),
        title=result.get("title"),
        author=result.get("author"),
        error=result.get("error")
    )


@router.post("/transcript", response_model=TranscriptResponse)
async def extract_transcripts(
    request: TranscriptRequest,
    current_user: UserInDB = Depends(get_current_user)
) -> TranscriptResponse:
    """
    Extract transcripts from multiple YouTube videos.
    
    - **urls**: List of YouTube video URLs (max 5)
    - **languages**: Preferred languages for transcripts (default: ["en"])
    
    Returns transcripts and metadata for each video.
    """
    results = await youtube_service.process_multiple_videos(
        request.urls, 
        request.languages
    )
    
    successful = sum(1 for r in results.values() if isinstance(r, VideoProcessingResult))
    failed = len(results) - successful
    
    serialized_results = {}
    for url, result in results.items():
        if isinstance(result, VideoProcessingResult):
            serialized_results[url] = {
                "success": True,
                "metadata": result.metadata.model_dump(),
                "transcript": result.transcript.model_dump()
            }
        else:
            serialized_results[url] = {
                "success": False,
                "error": result.get("error"),
                "error_type": result.get("error_type")
            }
    
    return TranscriptResponse(
        success=successful > 0,
        results=serialized_results,
        total_videos=len(results),
        successful_count=successful,
        failed_count=failed
    )


@router.post("/process", response_model=SingleVideoResponse)
async def process_single_video(
    request: SingleVideoRequest,
    current_user: UserInDB = Depends(get_current_user)
) -> SingleVideoResponse:
    """
    Process a single YouTube video to extract metadata and transcript.
    
    - **url**: YouTube video URL
    - **languages**: Preferred languages for transcript (default: ["en"])
    
    Returns complete metadata and transcript for the video.
    """
    try:
        result = await youtube_service.process_video(request.url, request.languages)
        
        return SingleVideoResponse(
            success=True,
            video_id=result.metadata.video_id,
            metadata=result.metadata,
            transcript=result.transcript
        )
        
    except InvalidURLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except VideoNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except TranscriptNotAvailableError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except ProxyError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except YouTubeServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/metadata/{video_id}")
async def get_video_metadata(
    video_id: str,
    current_user: UserInDB = Depends(get_current_user)
) -> VideoMetadata:
    """
    Get metadata for a YouTube video by ID.
    
    - **video_id**: 11-character YouTube video ID
    
    Returns video title, author, and thumbnail URL.
    """
    try:
        return await youtube_service.get_video_metadata(video_id)
    except VideoNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except YouTubeServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/proxy-stats")
async def get_proxy_stats(
    current_user: UserInDB = Depends(get_current_user)
) -> dict:
    """
    Get current proxy pool statistics for monitoring.
    
    Returns information about available proxies, their health status,
    and recent success/failure rates.
    """
    return youtube_service.get_proxy_stats()
