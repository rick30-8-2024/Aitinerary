"""
YouTube API Router

Provides endpoints for YouTube video validation and travel information extraction.
Uses Gemini's native video processing capability for analyzing travel content.
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, field_validator
from typing import Optional

from services.youtube_video_service import (
    youtube_video_service,
    InvalidURLError,
    VideoProcessingError,
    YouTubeVideoServiceError,
    VideoTravelInfo,
    MultiVideoTravelInfo,
    Place,
    Activity,
    HiddenGem,
    FoodRecommendation,
    TravelTip
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
    video_id: Optional[str] = None
    normalized_url: Optional[str] = None
    error: Optional[str] = None


class TravelInfoRequest(BaseModel):
    """Request schema for travel info extraction."""
    urls: list[str]
    
    @field_validator("urls")
    @classmethod
    def validate_urls_not_empty(cls, v):
        if not v:
            raise ValueError("At least one URL is required")
        if len(v) > 5:
            raise ValueError("Maximum 5 URLs allowed per request")
        return v


class TravelInfoResponse(BaseModel):
    """Response schema for travel info extraction."""
    success: bool
    destination: str
    summary: str
    places: list[Place]
    activities: list[Activity]
    hidden_gems: list[HiddenGem]
    food_recommendations: list[FoodRecommendation]
    travel_tips: list[TravelTip]
    best_time_to_visit: Optional[str] = None
    budget_info: Optional[str] = None
    duration_suggested: Optional[str] = None


class MultiVideoTravelInfoResponse(BaseModel):
    """Response schema for multi-video travel info extraction."""
    success: bool
    video_count: int
    combined_destination: str
    videos: list[VideoTravelInfo]
    all_places: list[Place]
    all_activities: list[Activity]
    all_hidden_gems: list[HiddenGem]
    all_food_recommendations: list[FoodRecommendation]
    all_travel_tips: list[TravelTip]


class SingleVideoRequest(BaseModel):
    """Request schema for single video processing."""
    url: str


class TranscriptRequest(BaseModel):
    """Request schema for transcript extraction."""
    url: str


class TranscriptResponse(BaseModel):
    """Response schema for transcript extraction."""
    success: bool
    video_url: str
    transcript: str


class SummaryResponse(BaseModel):
    """Response schema for video summary."""
    success: bool
    video_url: str
    summary: str


@router.post("/validate", response_model=URLValidateResponse)
async def validate_youtube_url(
    request: URLValidateRequest,
    current_user: UserInDB = Depends(get_current_user)
) -> URLValidateResponse:
    """
    Validate a YouTube URL and return normalized URL.
    
    - **url**: YouTube video URL to validate
    
    Returns normalized URL if valid.
    """
    try:
        normalized_url = youtube_video_service._validate_youtube_url(request.url)
        video_id = normalized_url.split("v=")[-1]
        
        return URLValidateResponse(
            valid=True,
            video_id=video_id,
            normalized_url=normalized_url,
            error=None
        )
    except InvalidURLError as e:
        return URLValidateResponse(
            valid=False,
            video_id=None,
            normalized_url=None,
            error=str(e)
        )


@router.post("/travel-info", response_model=TravelInfoResponse)
async def extract_travel_info(
    request: SingleVideoRequest,
    current_user: UserInDB = Depends(get_current_user)
) -> TravelInfoResponse:
    """
    Extract travel information from a single YouTube video.
    
    - **url**: YouTube video URL
    
    Returns detailed travel information extracted from the video.
    """
    try:
        result = await youtube_video_service.extract_travel_info(request.url)
        
        return TravelInfoResponse(
            success=True,
            destination=result.destination,
            summary=result.summary,
            places=result.places,
            activities=result.activities,
            hidden_gems=result.hidden_gems,
            food_recommendations=result.food_recommendations,
            travel_tips=result.travel_tips,
            best_time_to_visit=result.best_time_to_visit,
            budget_info=result.budget_info,
            duration_suggested=result.duration_suggested
        )
        
    except InvalidURLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except VideoProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except YouTubeVideoServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/travel-info/multiple", response_model=MultiVideoTravelInfoResponse)
async def extract_multiple_travel_info(
    request: TravelInfoRequest,
    current_user: UserInDB = Depends(get_current_user)
) -> MultiVideoTravelInfoResponse:
    """
    Extract travel information from multiple YouTube videos.
    
    - **urls**: List of YouTube video URLs (max 5)
    
    Returns combined travel information from all videos.
    """
    try:
        result = await youtube_video_service.extract_travel_info_from_multiple(request.urls)
        
        return MultiVideoTravelInfoResponse(
            success=True,
            video_count=len(result.videos),
            combined_destination=result.combined_destination,
            videos=result.videos,
            all_places=result.all_places,
            all_activities=result.all_activities,
            all_hidden_gems=result.all_hidden_gems,
            all_food_recommendations=result.all_food_recommendations,
            all_travel_tips=result.all_travel_tips
        )
        
    except InvalidURLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except YouTubeVideoServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/transcript", response_model=TranscriptResponse)
async def extract_transcript(
    request: TranscriptRequest,
    current_user: UserInDB = Depends(get_current_user)
) -> TranscriptResponse:
    """
    Extract transcript from a YouTube video using Gemini.
    
    - **url**: YouTube video URL
    
    Returns the video transcript.
    """
    try:
        transcript = await youtube_video_service.get_transcript(request.url)
        
        return TranscriptResponse(
            success=True,
            video_url=request.url,
            transcript=transcript
        )
        
    except InvalidURLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except VideoProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except YouTubeVideoServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/summarize", response_model=SummaryResponse)
async def summarize_video(
    request: SingleVideoRequest,
    current_user: UserInDB = Depends(get_current_user)
) -> SummaryResponse:
    """
    Get a summary of a YouTube video.
    
    - **url**: YouTube video URL
    
    Returns a comprehensive summary of the video content.
    """
    try:
        summary = await youtube_video_service.summarize_video(request.url)
        
        return SummaryResponse(
            success=True,
            video_url=request.url,
            summary=summary
        )
        
    except InvalidURLError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except VideoProcessingError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except YouTubeVideoServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
