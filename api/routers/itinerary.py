"""
Itinerary API Router

Provides endpoints for itinerary generation, status checking, and CRUD operations.
"""

import uuid
import asyncio
import logging
import traceback
from typing import Optional, Literal
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field, HttpUrl
from bson import ObjectId

logger = logging.getLogger(__name__)

from config.database import database
from config.logging_utils import log_debug, log_step, log_success, log_error, log_progress
from api.dependencies import get_current_user
from models.user import UserResponse
from models.preferences import UserPreferences
from models.itinerary import (
    Itinerary,
    ItineraryInDB,
    ItineraryResponse,
    ItineraryListItem,
    TranscriptAnalysis,
)
from services.youtube_video_service import youtube_video_service, YouTubeVideoServiceError
from services.gemini_service import gemini_service, GeminiServiceError


router = APIRouter(prefix="/api/itinerary", tags=["Itinerary"])


class GenerateRequest(BaseModel):
    """Request schema for itinerary generation."""
    
    youtube_urls: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="List of YouTube URLs to analyze (1-5)"
    )
    preferences: UserPreferences = Field(..., description="User travel preferences")
    title: Optional[str] = Field(default=None, description="Optional custom title")
    destination_name: Optional[str] = Field(default=None, description="Name of destination for itinerary naming")


class GenerateResponse(BaseModel):
    """Response schema for itinerary generation initiation."""
    
    itinerary_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    """Response schema for generation status check."""
    
    itinerary_id: str
    status: Literal["generating", "completed", "failed"]
    message: Optional[str] = None
    progress: Optional[int] = None


def get_itineraries_collection():
    """Get the itineraries collection."""
    return database.db.itineraries


async def create_itinerary_indexes():
    """Create indexes for the itineraries collection."""
    collection = get_itineraries_collection()
    await collection.create_index([("user_id", 1), ("created_at", -1)])
    await collection.create_index([("status", 1)])
    await collection.create_index([("share_code", 1)], sparse=True)


async def mark_timed_out_itineraries():
    """Mark itineraries as failed if they have been generating for more than 5 minutes."""
    collection = get_itineraries_collection()
    timeout_threshold = datetime.utcnow() - timedelta(minutes=5)
    
    try:
        result = await collection.update_many(
            {
                "status": "generating",
                "created_at": {"$lt": timeout_threshold}
            },
            {
                "$set": {
                    "status": "failed",
                    "status_message": "Generation timed out after 5 minutes",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            log_debug(f"Marked {result.modified_count} itineraries as failed due to timeout", prefix="TIMEOUT")
    except Exception as e:
        log_error(f"Error checking for timed out itineraries: {str(e)}", prefix="TIMEOUT")


async def process_itinerary_generation(
    itinerary_id: str,
    user_id: str,
    youtube_urls: list[str],
    preferences: UserPreferences,
    title: Optional[str],
    destination_name: Optional[str] = None
):
    """
    Background task to process itinerary generation.
    
    This function:
    1. Extracts transcripts from YouTube videos
    2. Analyzes transcripts with Gemini AI
    3. Generates the itinerary with Google Search grounding
    4. Saves the result to MongoDB
    5. Checks if itinerary still exists before saving
    """
    collection = get_itineraries_collection()
    
    log_step("Starting itinerary generation", 1, 4)
    log_debug(f"itinerary_id={itinerary_id}, user_id={user_id}", prefix="ITINERARY")
    log_debug(f"YouTube URLs: {youtube_urls}", prefix="ITINERARY")
    log_debug(f"Destination: {destination_name or 'Not specified'}", prefix="ITINERARY")
    
    async def check_itinerary_exists():
        """Check if the itinerary still exists in the database"""
        try:
            itinerary = await collection.find_one({"_id": ObjectId(itinerary_id)})
            return itinerary is not None
        except Exception:
            return False
    
    try:
        if not await check_itinerary_exists():
            log_error(f"Itinerary {itinerary_id} was deleted during processing. Stopping generation.", prefix="ITINERARY")
            return
        
        log_step("Analyzing YouTube videos with Gemini AI", 1, 4)
        await collection.update_one(
            {"_id": ObjectId(itinerary_id)},
            {"$set": {"progress": 10, "status_message": "Analyzing YouTube videos..."}}
        )
        
        video_titles = []
        
        try:
            log_debug(f"Processing {len(youtube_urls)} videos with Gemini native video processing", prefix="VIDEO")
            
            if len(youtube_urls) == 1:
                video_info = await youtube_video_service.extract_travel_info(youtube_urls[0])
                video_titles = [video_info.video_title or video_info.video_url]
                log_success(f"Extracted travel info from video: {video_info.destination}", prefix="VIDEO")
                
                await collection.update_one(
                    {"_id": ObjectId(itinerary_id)},
                    {"$set": {"progress": 40, "status_message": "Generating itinerary..."}}
                )
                
                if not await check_itinerary_exists():
                    log_error(f"Itinerary {itinerary_id} was deleted during processing. Stopping generation.", prefix="ITINERARY")
                    return
                
                analysis, itinerary = await gemini_service.generate_itinerary_from_video_info(
                    video_info, preferences
                )
            else:
                multi_video_info = await youtube_video_service.extract_travel_info_from_multiple(youtube_urls)
                for video_info in multi_video_info.videos:
                    video_titles.append(video_info.video_title or video_info.video_url)
                log_success(f"Extracted travel info from {len(youtube_urls)} videos: {multi_video_info.combined_destination}", prefix="VIDEO")
                
                await collection.update_one(
                    {"_id": ObjectId(itinerary_id)},
                    {"$set": {"progress": 40, "status_message": "Generating itinerary..."}}
                )
                
                if not await check_itinerary_exists():
                    log_error(f"Itinerary {itinerary_id} was deleted during processing. Stopping generation.", prefix="ITINERARY")
                    return
                
                analysis, itinerary = await gemini_service.generate_itinerary_from_multi_video_info(
                    multi_video_info, preferences
                )
            
            log_success(f"Gemini analysis complete. Detected destination: {analysis.destination}", prefix="GEMINI")
            
        except YouTubeVideoServiceError as e:
            error_msg = f"Failed to process videos: {str(e)}. Please try with different videos."
            log_error(error_msg, prefix="VIDEO")
            raise Exception(error_msg)
        
        if not await check_itinerary_exists():
            log_error(f"Itinerary {itinerary_id} was deleted during processing. Stopping generation.", prefix="ITINERARY")
            return
        
        log_step("Finalizing itinerary", 3, 4)
        await collection.update_one(
            {"_id": ObjectId(itinerary_id)},
            {"$set": {"progress": 90, "status_message": "Finalizing itinerary..."}}
        )
        
        if destination_name:
            final_title = f"{destination_name} Trip - {datetime.utcnow().strftime('%B %Y')}"
        else:
            final_title = title or itinerary.title or f"Trip to {analysis.destination}"
        
        if not await check_itinerary_exists():
            log_error(f"Itinerary {itinerary_id} was deleted before final save. Generation completed but not saved.", prefix="ITINERARY")
            return
        
        share_code = str(uuid.uuid4())[:8]
        
        itinerary_data = itinerary.model_dump()
        itinerary_data.update({
            "title": final_title,
            "youtube_urls": youtube_urls,
            "video_titles": video_titles,
            "user_preferences": preferences.model_dump(),
            "transcript_analysis": analysis.model_dump(),
            "destination_name": destination_name,
            "status": "completed",
            "progress": 100,
            "status_message": "Itinerary generated successfully",
            "share_code": share_code,
            "updated_at": datetime.utcnow()
        })
        
        await collection.update_one(
            {"_id": ObjectId(itinerary_id)},
            {"$set": itinerary_data}
        )
        
        log_step("Itinerary saved to database", 4, 4)
        log_success(f"Generation completed successfully for itinerary_id={itinerary_id}", prefix="ITINERARY")
        
    except Exception as e:
        log_error(f"Generation failed: {str(e)}", prefix="ITINERARY")
        logger.error(f"[ITINERARY] Full traceback: {traceback.format_exc()}")
        await collection.update_one(
            {"_id": ObjectId(itinerary_id)},
            {
                "$set": {
                    "status": "failed",
                    "status_message": str(e),
                    "updated_at": datetime.utcnow()
                }
            }
        )


@router.post("/generate", response_model=GenerateResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_itinerary(
    request: GenerateRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Start asynchronous itinerary generation from YouTube videos.
    
    Returns immediately with an itinerary ID for status polling.
    Uses asyncio.create_task for true concurrent processing.
    """
    log_debug(f"Received generation request from user_id={current_user.id}", prefix="GENERATE")
    log_debug(f"YouTube URLs: {request.youtube_urls}", prefix="GENERATE")
    log_debug(f"Destination: {request.destination_name or 'Not specified'}", prefix="GENERATE")
    
    collection = get_itineraries_collection()
    
    initial_title = request.title or "Generating..."
    if request.destination_name:
        initial_title = f"{request.destination_name} Trip"
    
    initial_record = {
        "user_id": current_user.id,
        "youtube_urls": request.youtube_urls,
        "user_preferences": request.preferences.model_dump(),
        "destination_name": request.destination_name,
        "status": "generating",
        "progress": 0,
        "status_message": "Starting generation...",
        "title": initial_title,
        "destination": request.destination_name or "",
        "summary": "",
        "days": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_public": False,
        "viewed": False
    }
    
    log_debug("Inserting initial record into database...", prefix="GENERATE")
    result = await collection.insert_one(initial_record)
    itinerary_id = str(result.inserted_id)
    log_success(f"Created itinerary record with id={itinerary_id}", prefix="GENERATE")
    
    asyncio.create_task(
        process_itinerary_generation(
            itinerary_id,
            current_user.id,
            request.youtube_urls,
            request.preferences,
            request.title,
            request.destination_name
        )
    )
    logger.info(f"[GENERATE] Background task started immediately for itinerary_id={itinerary_id}")
    
    return GenerateResponse(
        itinerary_id=itinerary_id,
        status="generating",
        message="Your itinerary generation is in progress and will take some time. Once generated, you'll find it in 'My Itineraries'."
    )


@router.get("/status/{itinerary_id}", response_model=StatusResponse)
async def get_generation_status(
    itinerary_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Check the status of an itinerary generation task."""
    collection = get_itineraries_collection()
    
    try:
        itinerary = await collection.find_one({
            "_id": ObjectId(itinerary_id),
            "user_id": current_user.id
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid itinerary ID")
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    return StatusResponse(
        itinerary_id=itinerary_id,
        status=itinerary.get("status", "generating"),
        message=itinerary.get("status_message"),
        progress=itinerary.get("progress", 0)
    )


@router.get("/list", response_model=list[ItineraryListItem])
async def list_itineraries(
    skip: int = 0,
    limit: int = 20,
    current_user: UserResponse = Depends(get_current_user)
):
    """List all itineraries for the current user including in-progress ones."""
    await mark_timed_out_itineraries()
    
    collection = get_itineraries_collection()
    
    cursor = collection.find(
        {"user_id": current_user.id}
    ).sort("created_at", -1).skip(skip).limit(limit)
    
    itineraries = []
    async for itinerary in cursor:
        status = itinerary.get("status", "completed")
        itineraries.append(ItineraryListItem(
            id=str(itinerary["_id"]),
            title=itinerary.get("title", "Generating..."),
            destination=itinerary.get("destination", ""),
            summary=itinerary.get("summary", ""),
            total_days=len(itinerary.get("days", [])),
            total_budget_estimate=itinerary.get("total_budget_estimate", 0),
            currency=itinerary.get("currency", "USD"),
            created_at=itinerary.get("created_at", datetime.utcnow()),
            is_public=itinerary.get("is_public", False),
            viewed=itinerary.get("viewed", False),
            status=status,
            status_message=itinerary.get("status_message"),
            progress=itinerary.get("progress", 0) if status == "generating" else None
        ))
    
    return itineraries


@router.get("/{itinerary_id}", response_model=ItineraryResponse)
async def get_itinerary(
    itinerary_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get a complete itinerary by ID."""
    collection = get_itineraries_collection()
    
    try:
        itinerary = await collection.find_one({
            "_id": ObjectId(itinerary_id),
            "user_id": current_user.id
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid itinerary ID")
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    if itinerary.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Itinerary is not ready. Status: {itinerary.get('status')}"
        )
    
    return ItineraryResponse(
        id=str(itinerary["_id"]),
        title=itinerary.get("title", ""),
        destination=itinerary.get("destination", ""),
        country=itinerary.get("country"),
        summary=itinerary.get("summary", ""),
        days=itinerary.get("days", []),
        total_budget_estimate=itinerary.get("total_budget_estimate", 0),
        currency=itinerary.get("currency", "USD"),
        budget_breakdown=itinerary.get("budget_breakdown", {}),
        general_tips=itinerary.get("general_tips", []),
        packing_suggestions=itinerary.get("packing_suggestions", []),
        emergency_contacts=itinerary.get("emergency_contacts", []),
        language_phrases=itinerary.get("language_phrases", []),
        best_time_to_visit=itinerary.get("best_time_to_visit"),
        weather_info=itinerary.get("weather_info"),
        youtube_urls=itinerary.get("youtube_urls", []),
        created_at=itinerary.get("created_at", datetime.utcnow()),
        is_public=itinerary.get("is_public", False),
        share_code=itinerary.get("share_code")
    )


@router.get("/shared/{share_code}", response_model=ItineraryResponse)
async def get_shared_itinerary(share_code: str):
    """Get a publicly shared itinerary by share code."""
    collection = get_itineraries_collection()
    
    itinerary = await collection.find_one({
        "share_code": share_code,
        "is_public": True
    })
    
    if not itinerary:
        raise HTTPException(status_code=404, detail="Shared itinerary not found")
    
    return ItineraryResponse(
        id=str(itinerary["_id"]),
        title=itinerary.get("title", ""),
        destination=itinerary.get("destination", ""),
        country=itinerary.get("country"),
        summary=itinerary.get("summary", ""),
        days=itinerary.get("days", []),
        total_budget_estimate=itinerary.get("total_budget_estimate", 0),
        currency=itinerary.get("currency", "USD"),
        budget_breakdown=itinerary.get("budget_breakdown", {}),
        general_tips=itinerary.get("general_tips", []),
        packing_suggestions=itinerary.get("packing_suggestions", []),
        emergency_contacts=itinerary.get("emergency_contacts", []),
        language_phrases=itinerary.get("language_phrases", []),
        best_time_to_visit=itinerary.get("best_time_to_visit"),
        weather_info=itinerary.get("weather_info"),
        youtube_urls=itinerary.get("youtube_urls", []),
        created_at=itinerary.get("created_at", datetime.utcnow()),
        is_public=itinerary.get("is_public", False),
        share_code=itinerary.get("share_code")
    )


@router.patch("/{itinerary_id}/viewed")
async def mark_as_viewed(
    itinerary_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Mark an itinerary as viewed."""
    collection = get_itineraries_collection()
    
    try:
        result = await collection.update_one(
            {"_id": ObjectId(itinerary_id), "user_id": current_user.id},
            {"$set": {"viewed": True, "updated_at": datetime.utcnow()}}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid itinerary ID")
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    return {"message": "Marked as viewed"}


@router.patch("/{itinerary_id}/visibility")
async def update_visibility(
    itinerary_id: str,
    is_public: bool,
    current_user: UserResponse = Depends(get_current_user)
):
    """Toggle itinerary public visibility for sharing."""
    collection = get_itineraries_collection()
    
    try:
        result = await collection.update_one(
            {"_id": ObjectId(itinerary_id), "user_id": current_user.id},
            {"$set": {"is_public": is_public, "updated_at": datetime.utcnow()}}
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid itinerary ID")
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    itinerary = await collection.find_one({"_id": ObjectId(itinerary_id)})
    
    return {
        "message": "Visibility updated",
        "is_public": is_public,
        "share_code": itinerary.get("share_code") if is_public else None
    }


@router.delete("/{itinerary_id}")
async def delete_itinerary(
    itinerary_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Delete an itinerary."""
    collection = get_itineraries_collection()
    
    try:
        result = await collection.delete_one({
            "_id": ObjectId(itinerary_id),
            "user_id": current_user.id
        })
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid itinerary ID")
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    return {"message": "Itinerary deleted successfully"}
