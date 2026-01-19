"""
YouTube Video Processing Service using Google GenAI.

This service uses Gemini's native YouTube video processing to extract
travel information directly from video content, bypassing transcript APIs.
"""

import os
import re
import logging
import asyncio
from typing import Optional
from pydantic import BaseModel, Field

from google import genai
from google.genai import types
from dotenv import load_dotenv

from config.settings import settings

logger = logging.getLogger(__name__)


class Place(BaseModel):
    """A place or location mentioned in the video."""
    name: str = Field(description="Name of the place")
    category: str = Field(description="Category: city, landmark, restaurant, hotel, attraction, etc.")
    description: Optional[str] = Field(default=None, description="Brief description from the video")
    tips: Optional[str] = Field(default=None, description="Any tips mentioned about this place")


class Activity(BaseModel):
    """An activity or experience mentioned in the video."""
    name: str = Field(description="Name or description of the activity")
    location: Optional[str] = Field(default=None, description="Where this activity takes place")
    duration: Optional[str] = Field(default=None, description="How long the activity takes")
    cost: Optional[str] = Field(default=None, description="Cost if mentioned")
    tips: Optional[str] = Field(default=None, description="Tips for doing this activity")


class HiddenGem(BaseModel):
    """A hidden gem or lesser-known spot mentioned in the video."""
    name: str = Field(description="Name of the hidden gem")
    location: Optional[str] = Field(default=None, description="Location details")
    why_special: str = Field(description="Why this is considered a hidden gem")


class FoodRecommendation(BaseModel):
    """Food or dining recommendations from the video."""
    name: str = Field(description="Name of dish, restaurant, or food item")
    location: Optional[str] = Field(default=None, description="Where to find it")
    description: Optional[str] = Field(default=None, description="Description from the video")
    price_range: Optional[str] = Field(default=None, description="Price range if mentioned")


class TravelTip(BaseModel):
    """A travel tip or advice from the video."""
    tip: str = Field(description="The travel tip or advice")
    category: str = Field(description="Category: transportation, budget, safety, timing, etc.")


class VideoTravelInfo(BaseModel):
    """Complete travel information extracted from a YouTube video."""
    video_url: str = Field(description="The YouTube video URL")
    video_title: Optional[str] = Field(default=None, description="Title if detected")
    destination: str = Field(description="Main destination(s) featured in the video")
    summary: str = Field(description="Brief summary of the video content")
    places: list[Place] = Field(default_factory=list, description="Places mentioned")
    activities: list[Activity] = Field(default_factory=list, description="Activities shown/mentioned")
    hidden_gems: list[HiddenGem] = Field(default_factory=list, description="Hidden gems discovered")
    food_recommendations: list[FoodRecommendation] = Field(default_factory=list, description="Food recommendations")
    travel_tips: list[TravelTip] = Field(default_factory=list, description="Travel tips and advice")
    best_time_to_visit: Optional[str] = Field(default=None, description="Best time to visit if mentioned")
    budget_info: Optional[str] = Field(default=None, description="Budget information if mentioned")
    duration_suggested: Optional[str] = Field(default=None, description="Suggested trip duration")
    transcript_excerpt: Optional[str] = Field(default=None, description="Key transcript excerpt")


class MultiVideoTravelInfo(BaseModel):
    """Travel information extracted from multiple YouTube videos."""
    videos: list[VideoTravelInfo] = Field(description="Information from each video")
    combined_destination: str = Field(description="Combined destination summary")
    all_places: list[Place] = Field(default_factory=list, description="All unique places from all videos")
    all_activities: list[Activity] = Field(default_factory=list, description="All unique activities")
    all_hidden_gems: list[HiddenGem] = Field(default_factory=list, description="All hidden gems")
    all_food_recommendations: list[FoodRecommendation] = Field(default_factory=list, description="All food recommendations")
    all_travel_tips: list[TravelTip] = Field(default_factory=list, description="All travel tips")


class YouTubeVideoServiceError(Exception):
    """Base exception for YouTube video service errors."""
    pass


class VideoProcessingError(YouTubeVideoServiceError):
    """Raised when video processing fails."""
    pass


class InvalidURLError(YouTubeVideoServiceError):
    """Raised when YouTube URL is invalid."""
    pass


class YouTubeVideoService:
    """Service for extracting travel information from YouTube videos using Gemini."""
    
    YOUTUBE_URL_PATTERNS = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
    ]
    
    TRAVEL_EXTRACTION_PROMPT = """You are a travel information extraction expert. Watch this YouTube video and extract all travel-related information.

Extract the following information in a structured format:

1. **Destination**: What is the main destination/location featured?

2. **Summary**: Provide a 2-3 sentence summary of what the video covers.

3. **Places to Visit**: List all places mentioned including:
   - Name and category (city, landmark, restaurant, hotel, attraction, etc.)
   - Any description or tips given

4. **Activities**: What activities or experiences are shown or recommended?
   - Include duration, cost, and tips if mentioned

5. **Hidden Gems**: Any off-the-beaten-path or lesser-known spots?
   - Explain why they're special

6. **Food Recommendations**: Any restaurants, dishes, or food experiences?
   - Include locations and price ranges if mentioned

7. **Travel Tips**: Any practical advice given?
   - Categorize as: transportation, budget, safety, timing, packing, etc.

8. **Best Time to Visit**: Is there a recommended season or time?

9. **Budget Info**: Any cost estimates or budget tips?

10. **Suggested Duration**: How long should someone spend at this destination?

Please provide detailed, actionable information that a traveler could use to plan their trip.
Format your response as a structured JSON object."""

    def __init__(self):
        """Initialize the YouTube video service."""
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        self._client = genai.Client(api_key=api_key)
        self._model = os.getenv("GEMINI_MODEL_NAME") or "gemini-2.0-flash"
    
    def _validate_youtube_url(self, url: str) -> str:
        """Validate and normalize a YouTube URL."""
        url = url.strip()
        
        for pattern in self.YOUTUBE_URL_PATTERNS:
            match = re.search(pattern, url)
            if match:
                video_id = match.group(1)
                return f"https://www.youtube.com/watch?v={video_id}"
        
        raise InvalidURLError(f"Invalid YouTube URL format: {url}")
    
    def _sync_generate_content(self, model: str, contents: types.Content):
        """Synchronous wrapper for generate_content to be run in thread pool."""
        return self._client.models.generate_content(model=model, contents=contents)
    
    async def extract_travel_info(self, youtube_url: str) -> VideoTravelInfo:
        """
        Extract travel information from a single YouTube video.
        
        Args:
            youtube_url: The YouTube video URL
            
        Returns:
            VideoTravelInfo with extracted travel data
        """
        normalized_url = self._validate_youtube_url(youtube_url)
        logger.info(f"Extracting travel info from: {normalized_url}")
        
        try:
            contents = types.Content(
                parts=[
                    types.Part(
                        file_data=types.FileData(file_uri=normalized_url)
                    ),
                    types.Part(text=self.TRAVEL_EXTRACTION_PROMPT),
                ]
            )
            
            response = await asyncio.to_thread(
                self._sync_generate_content,
                self._model,
                contents
            )
            
            raw_response = response.text
            logger.debug(f"Raw response: {raw_response[:500]}...")
            
            travel_info = self._parse_travel_response(raw_response, normalized_url)
            return travel_info
            
        except Exception as e:
            logger.error(f"Error processing video {normalized_url}: {e}")
            raise VideoProcessingError(f"Failed to process video: {str(e)}")
    
    async def extract_travel_info_from_multiple(
        self, 
        youtube_urls: list[str]
    ) -> MultiVideoTravelInfo:
        """
        Extract travel information from multiple YouTube videos.
        
        Args:
            youtube_urls: List of YouTube video URLs
            
        Returns:
            MultiVideoTravelInfo with combined travel data
        """
        video_infos = []
        
        for url in youtube_urls:
            try:
                info = await self.extract_travel_info(url)
                video_infos.append(info)
            except YouTubeVideoServiceError as e:
                logger.warning(f"Failed to process {url}: {e}")
                video_infos.append(VideoTravelInfo(
                    video_url=url,
                    destination="Unknown (processing failed)",
                    summary=f"Error processing video: {str(e)}",
                ))
        
        return self._combine_video_info(video_infos)
    
    async def extract_travel_info_combined(
        self,
        youtube_urls: list[str]
    ) -> VideoTravelInfo:
        """
        Extract travel information from multiple videos in a single request.
        
        Note: Gemini documentation says only ONE YouTube URL per request is supported.
        This method will process videos sequentially and combine results.
        
        Args:
            youtube_urls: List of YouTube video URLs
            
        Returns:
            Combined VideoTravelInfo
        """
        if len(youtube_urls) == 1:
            return await self.extract_travel_info(youtube_urls[0])
        
        multi_info = await self.extract_travel_info_from_multiple(youtube_urls)
        
        combined = VideoTravelInfo(
            video_url=", ".join(youtube_urls),
            destination=multi_info.combined_destination,
            summary=f"Combined information from {len(youtube_urls)} videos",
            places=multi_info.all_places,
            activities=multi_info.all_activities,
            hidden_gems=multi_info.all_hidden_gems,
            food_recommendations=multi_info.all_food_recommendations,
            travel_tips=multi_info.all_travel_tips,
        )
        
        return combined
    
    def _parse_travel_response(self, response_text: str, video_url: str) -> VideoTravelInfo:
        """Parse the Gemini response into VideoTravelInfo structure."""
        import json
        
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(1)
        else:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
            else:
                json_text = None
        
        places = []
        activities = []
        hidden_gems = []
        food_recommendations = []
        travel_tips = []
        destination = "Unknown"
        summary = ""
        best_time = None
        budget_info = None
        duration = None
        
        if json_text:
            try:
                data = json.loads(json_text)
                
                destination = data.get("destination", data.get("Destination", "Unknown"))
                summary = data.get("summary", data.get("Summary", ""))
                
                for place_data in data.get("places", data.get("Places", data.get("places_to_visit", []))):
                    if isinstance(place_data, dict):
                        places.append(Place(
                            name=place_data.get("name", "Unknown"),
                            category=place_data.get("category", "attraction"),
                            description=place_data.get("description"),
                            tips=place_data.get("tips")
                        ))
                    elif isinstance(place_data, str):
                        places.append(Place(name=place_data, category="attraction"))
                
                for activity_data in data.get("activities", data.get("Activities", [])):
                    if isinstance(activity_data, dict):
                        activities.append(Activity(
                            name=activity_data.get("name", "Unknown"),
                            location=activity_data.get("location"),
                            duration=activity_data.get("duration"),
                            cost=activity_data.get("cost"),
                            tips=activity_data.get("tips")
                        ))
                    elif isinstance(activity_data, str):
                        activities.append(Activity(name=activity_data))
                
                for gem_data in data.get("hidden_gems", data.get("Hidden Gems", [])):
                    if isinstance(gem_data, dict):
                        hidden_gems.append(HiddenGem(
                            name=gem_data.get("name", "Unknown"),
                            location=gem_data.get("location"),
                            why_special=gem_data.get("why_special", gem_data.get("description", "Local favorite"))
                        ))
                    elif isinstance(gem_data, str):
                        hidden_gems.append(HiddenGem(name=gem_data, why_special="Mentioned in video"))
                
                for food_data in data.get("food_recommendations", data.get("Food Recommendations", [])):
                    if isinstance(food_data, dict):
                        food_recommendations.append(FoodRecommendation(
                            name=food_data.get("name", "Unknown"),
                            location=food_data.get("location"),
                            description=food_data.get("description"),
                            price_range=food_data.get("price_range")
                        ))
                    elif isinstance(food_data, str):
                        food_recommendations.append(FoodRecommendation(name=food_data))
                
                for tip_data in data.get("travel_tips", data.get("Travel Tips", [])):
                    if isinstance(tip_data, dict):
                        travel_tips.append(TravelTip(
                            tip=tip_data.get("tip", str(tip_data)),
                            category=tip_data.get("category", "general")
                        ))
                    elif isinstance(tip_data, str):
                        travel_tips.append(TravelTip(tip=tip_data, category="general"))
                
                best_time_raw = data.get("best_time_to_visit", data.get("Best Time to Visit"))
                if isinstance(best_time_raw, dict):
                    best_time = ", ".join(f"{k}: {v}" for k, v in best_time_raw.items())
                else:
                    best_time = best_time_raw
                
                budget_info_raw = data.get("budget_info", data.get("Budget Info"))
                if isinstance(budget_info_raw, dict):
                    budget_info = ", ".join(f"{k}: {v}" for k, v in budget_info_raw.items())
                else:
                    budget_info = budget_info_raw
                
                duration_raw = data.get("duration_suggested", data.get("Suggested Duration"))
                if isinstance(duration_raw, dict):
                    duration = ", ".join(f"{k}: {v}" for k, v in duration_raw.items())
                else:
                    duration = duration_raw
                
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON response: {e}")
        
        if not summary:
            summary = self._extract_summary_from_text(response_text)
        
        if destination == "Unknown":
            destination = self._extract_destination_from_text(response_text)
        
        return VideoTravelInfo(
            video_url=video_url,
            destination=destination,
            summary=summary,
            places=places,
            activities=activities,
            hidden_gems=hidden_gems,
            food_recommendations=food_recommendations,
            travel_tips=travel_tips,
            best_time_to_visit=best_time,
            budget_info=budget_info,
            duration_suggested=duration
        )
    
    def _extract_summary_from_text(self, text: str) -> str:
        """Extract a summary from unstructured text."""
        lines = text.split('\n')
        for line in lines:
            if len(line) > 50 and not line.startswith('#') and not line.startswith('*'):
                return line.strip()[:500]
        return "Travel video content"
    
    def _extract_destination_from_text(self, text: str) -> str:
        """Extract destination from unstructured text."""
        destination_patterns = [
            r'destination[:\s]+([A-Z][a-zA-Z\s,]+)',
            r'visit(?:ing)?\s+([A-Z][a-zA-Z\s,]+)',
            r'travel(?:ing)?\s+to\s+([A-Z][a-zA-Z\s,]+)',
        ]
        
        for pattern in destination_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:100]
        
        return "Unknown destination"
    
    def _combine_video_info(self, video_infos: list[VideoTravelInfo]) -> MultiVideoTravelInfo:
        """Combine travel information from multiple videos."""
        all_places = []
        all_activities = []
        all_hidden_gems = []
        all_food_recommendations = []
        all_travel_tips = []
        
        destinations = set()
        
        for info in video_infos:
            destinations.add(info.destination)
            all_places.extend(info.places)
            all_activities.extend(info.activities)
            all_hidden_gems.extend(info.hidden_gems)
            all_food_recommendations.extend(info.food_recommendations)
            all_travel_tips.extend(info.travel_tips)
        
        seen_places = set()
        unique_places = []
        for place in all_places:
            if place.name.lower() not in seen_places:
                seen_places.add(place.name.lower())
                unique_places.append(place)
        
        seen_activities = set()
        unique_activities = []
        for activity in all_activities:
            if activity.name.lower() not in seen_activities:
                seen_activities.add(activity.name.lower())
                unique_activities.append(activity)
        
        return MultiVideoTravelInfo(
            videos=video_infos,
            combined_destination=", ".join(destinations),
            all_places=unique_places,
            all_activities=unique_activities,
            all_hidden_gems=all_hidden_gems,
            all_food_recommendations=all_food_recommendations,
            all_travel_tips=all_travel_tips
        )
    
    async def get_transcript(self, youtube_url: str) -> str:
        """
        Get transcript from a YouTube video using Gemini.
        
        Args:
            youtube_url: The YouTube video URL
            
        Returns:
            Transcript text
        """
        normalized_url = self._validate_youtube_url(youtube_url)
        
        try:
            contents = types.Content(
                parts=[
                    types.Part(
                        file_data=types.FileData(file_uri=normalized_url)
                    ),
                    types.Part(text="Please provide a complete transcript of this video. Include timestamps if possible."),
                ]
            )
            
            response = await asyncio.to_thread(
                self._sync_generate_content,
                self._model,
                contents
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error getting transcript for {normalized_url}: {e}")
            raise VideoProcessingError(f"Failed to get transcript: {str(e)}")
    
    async def summarize_video(self, youtube_url: str) -> str:
        """
        Get a summary of a YouTube video.
        
        Args:
            youtube_url: The YouTube video URL
            
        Returns:
            Summary text
        """
        normalized_url = self._validate_youtube_url(youtube_url)
        
        try:
            contents = types.Content(
                parts=[
                    types.Part(
                        file_data=types.FileData(file_uri=normalized_url)
                    ),
                    types.Part(text="Please provide a comprehensive summary of this video in 3-5 paragraphs."),
                ]
            )
            
            response = await asyncio.to_thread(
                self._sync_generate_content,
                self._model,
                contents
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error summarizing {normalized_url}: {e}")
            raise VideoProcessingError(f"Failed to summarize video: {str(e)}")


youtube_video_service = YouTubeVideoService()
