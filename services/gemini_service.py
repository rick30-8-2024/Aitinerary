"""
Gemini AI Integration Service

Provides functionality to analyze YouTube transcripts and generate travel itineraries
using Google's Gemini 2.5 Flash model with a dual-agent architecture:
- Internet Search Agent: Has Google Search grounding for real-time information
- Tool Call Agent: Generates structured JSON responses and can call the search agent
"""

import json
import re
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel

from config.settings import settings
from models.preferences import UserPreferences
from models.itinerary import (
    Itinerary,
    TranscriptAnalysis,
    DayPlan,
    Activity,
    MealRecommendation,
    BudgetBreakdown
)
from services.youtube_service import VideoProcessingResult


class GeminiServiceError(Exception):
    """Base exception for Gemini service errors."""
    pass


class APIKeyNotConfiguredError(GeminiServiceError):
    """Raised when Gemini API key is not configured."""
    pass


class GenerationError(GeminiServiceError):
    """Raised when content generation fails."""
    pass


SEARCH_INTERNET_TOOL = types.FunctionDeclaration(
    name="search_internet",
    description="Search the internet for real-time information about places, prices, opening hours, reviews, or any current travel information. Use this when you need up-to-date information that might not be in your training data.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query to find information about. Be specific and include location names."
            },
            "context": {
                "type": "string",
                "description": "Additional context about what kind of information you're looking for (e.g., 'prices', 'opening hours', 'reviews', 'nearby attractions')"
            }
        },
        "required": ["query"]
    }
)


class GeminiService:
    """Service for AI-powered transcript analysis and itinerary generation using dual-agent architecture."""
    
    MODEL_NAME = "gemini-2.5-flash"
    
    def __init__(self):
        """Initialize the Gemini service."""
        self._client: Optional[genai.Client] = None
        self._async_client = None
    
    def _get_client(self) -> genai.Client:
        """Get or create the Gemini client."""
        if not settings.GEMINI_API_KEY:
            raise APIKeyNotConfiguredError(
                "GEMINI_API_KEY is not configured. Please set it in your environment variables."
            )
        
        if self._client is None:
            self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        
        return self._client
    
    @property
    def aio(self):
        """Get async client interface."""
        return self._get_client().aio
    
    async def _internet_search_agent(self, query: str, context: Optional[str] = None) -> str:
        """
        Internet Search Agent - Uses Google Search grounding for real-time information.
        
        This agent can access the internet but cannot return structured JSON.
        It returns plain text search results.
        
        Args:
            query: The search query
            context: Additional context for the search
            
        Returns:
            Search results as plain text
        """
        client = self._get_client()
        
        search_prompt = f"""Search the internet and provide detailed, accurate information for: {query}
        
{"Context: " + context if context else ""}

Provide:
1. Current and accurate information
2. Specific details like prices, addresses, opening hours if relevant
3. Recent reviews or ratings if available
4. Any warnings or important notes

Be concise but thorough. Format the response as clear, readable text."""
        
        try:
            response = await client.aio.models.generate_content(
                model=self.MODEL_NAME,
                contents=search_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    top_p=0.95,
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            
            return response.text or "No search results found."
            
        except Exception as e:
            return f"Search failed: {str(e)}"
    
    async def _tool_call_agent(
        self,
        prompt: str,
        max_tool_calls: int = 10
    ) -> str:
        """
        Tool Call Agent - Generates structured JSON responses with ability to search internet.
        
        This agent uses JSON response mode and can call the internet search agent
        through function calling when it needs real-time information.
        
        Args:
            prompt: The generation prompt
            max_tool_calls: Maximum number of search calls allowed
            
        Returns:
            JSON string response
        """
        client = self._get_client()
        
        messages = [
            types.Content(
                role="user",
                parts=[types.Part(text=prompt)]
            )
        ]
        
        tool_calls_made = 0
        
        while tool_calls_made < max_tool_calls:
            response = await client.aio.models.generate_content(
                model=self.MODEL_NAME,
                contents=messages,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    top_p=0.95,
                    tools=[types.Tool(function_declarations=[SEARCH_INTERNET_TOOL])]
                )
            )
            
            if not response.candidates or not response.candidates[0].content.parts:
                raise GenerationError("Empty response from Gemini API")
            
            response_parts = response.candidates[0].content.parts
            
            function_calls = [
                part.function_call for part in response_parts 
                if hasattr(part, 'function_call') and part.function_call
            ]
            
            if not function_calls:
                text_parts = [part.text for part in response_parts if hasattr(part, 'text') and part.text]
                if text_parts:
                    return "".join(text_parts)
                raise GenerationError("No text or function calls in response")
            
            messages.append(types.Content(
                role="model",
                parts=response_parts
            ))
            
            function_responses = []
            for fc in function_calls:
                if fc.name == "search_internet":
                    args = dict(fc.args) if fc.args else {}
                    query = args.get("query", "")
                    context = args.get("context")
                    
                    search_result = await self._internet_search_agent(query, context)
                    tool_calls_made += 1
                    
                    function_responses.append(
                        types.Part(function_response=types.FunctionResponse(
                            name="search_internet",
                            response={"result": search_result}
                        ))
                    )
            
            messages.append(types.Content(
                role="user",
                parts=function_responses
            ))
        
        raise GenerationError(f"Exceeded maximum tool calls ({max_tool_calls})")
    
    def _build_transcript_analysis_prompt(
        self, 
        transcript: str, 
        video_title: str,
        video_author: str
    ) -> str:
        """Build the prompt for transcript analysis."""
        return f"""Analyze this travel vlog transcript and extract structured travel information.

VIDEO INFORMATION:
- Title: {video_title}
- Channel: {video_author}

TRANSCRIPT:
{transcript[:50000]}

TASK:
Extract the following information from the transcript:

1. **destination**: The main travel destination featured in the video
2. **country**: The country of the destination (if identifiable)
3. **places_mentioned**: List ALL specific places mentioned (attractions, restaurants, hotels, neighborhoods, beaches, etc.)
4. **activities_mentioned**: List all activities shown or recommended (tours, experiences, adventures)
5. **local_tips**: Extract any local tips, recommendations, or insider knowledge shared
6. **warnings**: Note any warnings, things to avoid, or scam alerts mentioned
7. **estimated_costs**: Extract any prices or cost estimates mentioned (as a dictionary with item: cost)
8. **best_time_to_visit**: Best time/season to visit if mentioned
9. **key_highlights**: The top 5-10 highlights or must-do experiences from this video

Be thorough and extract all relevant travel information. If something is not mentioned, use empty list or null."""
    
    def _build_itinerary_generation_prompt(
        self,
        analysis: TranscriptAnalysis,
        preferences: UserPreferences,
        video_titles: list[str]
    ) -> str:
        """Build the prompt for itinerary generation."""
        return f"""Create a detailed {preferences.trip_duration_days}-day travel itinerary for {analysis.destination} based on the following information.

SOURCE VIDEOS ANALYZED:
{chr(10).join(f'- {title}' for title in video_titles)}

EXTRACTED PLACES FROM VIDEOS:
{chr(10).join(f'- {place}' for place in analysis.places_mentioned[:30])}

ACTIVITIES FROM VIDEOS:
{chr(10).join(f'- {activity}' for activity in analysis.activities_mentioned[:20])}

LOCAL TIPS FROM VIDEOS:
{chr(10).join(f'- {tip}' for tip in analysis.local_tips[:15])}

TRAVELER PROFILE:
- Budget: {preferences.budget} {preferences.currency}
- Trip Type: {preferences.trip_type}
- Activity Style: {preferences.activity_style}
- Number of Travelers: {preferences.num_travelers}
- Accommodation Preference: {preferences.accommodation_preference}
- Dietary Restrictions: {', '.join(preferences.dietary_restrictions) if preferences.dietary_restrictions else 'None'}
- Mobility Constraints: {preferences.mobility_constraints or 'None'}
- Start Date: {preferences.start_date or 'Flexible'}

MUST VISIT PLACES (User Requested):
{chr(10).join(f'- {place}' for place in preferences.must_visit_places) if preferences.must_visit_places else 'None specified'}

ADDITIONAL NOTES:
{preferences.additional_notes or 'None'}

IMPORTANT: You have access to the search_internet tool to look up current information about:
- Opening hours and prices for attractions
- Restaurant reviews and current prices
- Hotel availability and rates
- Recent travel advisories or warnings
- Local transportation options and costs

Use the search_internet tool to verify and update information when needed, especially for:
- Prices and costs (search for current rates)
- Opening hours (may have changed)
- Popular restaurants (check recent reviews)
- Safety information (recent advisories)

TASK:
Generate a comprehensive day-by-day itinerary. You MUST respond with a valid JSON object with this exact structure:

{{
    "title": "A catchy title for this itinerary",
    "destination": "Main destination",
    "country": "Country name",
    "summary": "2-3 sentence overview of the trip",
    "days": [
        {{
            "day_number": 1,
            "date": "YYYY-MM-DD or null",
            "theme": "Theme for the day",
            "summary": "Brief summary of the day",
            "activities": [
                {{
                    "time_slot": "HH:MM - HH:MM",
                    "place_name": "Name of place",
                    "description": "What to do there",
                    "estimated_cost": 0,
                    "estimated_duration": "Duration string",
                    "travel_time_from_previous": "Time from previous or null",
                    "transport_mode": "walk/taxi/metro/bus or null",
                    "tips": ["tip1", "tip2"],
                    "warnings": ["warning1"],
                    "booking_required": false,
                    "weather_alternative": "Alternative activity or null"
                }}
            ],
            "meals": [
                {{
                    "meal_type": "breakfast/lunch/dinner",
                    "place_name": "Restaurant name",
                    "cuisine": "Type of food",
                    "estimated_cost": 0,
                    "dietary_notes": "Dietary info or null",
                    "recommendation_reason": "Why recommended"
                }}
            ],
            "total_estimated_cost": 0,
            "walking_distance": "Distance or null",
            "notes": "Additional notes or null"
        }}
    ],
    "total_budget_estimate": 0,
    "budget_breakdown": {{
        "accommodation": 0,
        "food": 0,
        "activities": 0,
        "transportation": 0,
        "shopping": 0,
        "miscellaneous": 0,
        "total": 0
    }},
    "general_tips": ["tip1", "tip2"],
    "packing_suggestions": ["item1", "item2"],
    "emergency_contacts": ["contact1"],
    "language_phrases": ["phrase1"],
    "best_time_to_visit": "Best season/months or null",
    "weather_info": "Expected weather or null"
}}

IMPORTANT GUIDELINES:
- Use the search_internet tool to verify current prices, opening hours, and availability
- Include realistic travel times between locations
- Look for recent reviews mentioning scams or issues
- Balance the budget across days
- Include a mix of activities matching the traveler's style
- Consider the group type ({preferences.trip_type}) when selecting activities
- Account for dietary restrictions in meal recommendations
- Suggest alternatives for any activities with mobility concerns
- Make the itinerary practical and achievable
- RESPOND ONLY WITH THE JSON OBJECT, no additional text"""
    
    async def analyze_transcript(
        self,
        transcript: str,
        video_title: str,
        video_author: str
    ) -> TranscriptAnalysis:
        """
        Analyze a transcript to extract travel information.
        
        Args:
            transcript: Full transcript text
            video_title: Title of the video
            video_author: Channel/author name
            
        Returns:
            TranscriptAnalysis with extracted information
        """
        client = self._get_client()
        
        prompt = self._build_transcript_analysis_prompt(
            transcript, video_title, video_author
        )
        
        try:
            response = await client.aio.models.generate_content(
                model=self.MODEL_NAME,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                    top_p=0.95,
                )
            )
            
            if not response.text:
                raise GenerationError("Empty response from Gemini API")
            
            data = json.loads(response.text)
            
            return TranscriptAnalysis(
                destination=data.get("destination") or "Unknown",
                places_mentioned=data.get("places_mentioned") or [],
                activities_mentioned=data.get("activities_mentioned") or [],
                local_tips=data.get("local_tips") or [],
                warnings=data.get("warnings") or [],
                estimated_costs=data.get("estimated_costs") or {},
                best_time_to_visit=data.get("best_time_to_visit"),
                key_highlights=data.get("key_highlights") or []
            )
            
        except json.JSONDecodeError as e:
            raise GenerationError(f"Failed to parse Gemini response: {str(e)}")
        except Exception as e:
            raise GenerationError(f"Transcript analysis failed: {str(e)}")
    
    async def analyze_multiple_transcripts(
        self,
        video_results: list[VideoProcessingResult]
    ) -> TranscriptAnalysis:
        """
        Analyze multiple video transcripts and combine the results.
        
        Args:
            video_results: List of processed video results
            
        Returns:
            Combined TranscriptAnalysis
        """
        if not video_results:
            raise ValueError("At least one video result is required")
        
        if len(video_results) == 1:
            result = video_results[0]
            return await self.analyze_transcript(
                result.transcript.full_text,
                result.metadata.title,
                result.metadata.author_name
            )
        
        combined_transcript = "\n\n---VIDEO BREAK---\n\n".join(
            f"[{r.metadata.title}]\n{r.transcript.full_text[:15000]}"
            for r in video_results
        )
        
        combined_title = " + ".join(r.metadata.title for r in video_results)
        combined_author = ", ".join(set(r.metadata.author_name for r in video_results))
        
        return await self.analyze_transcript(
            combined_transcript,
            combined_title,
            combined_author
        )
    
    def _extract_json_from_response(self, text: str) -> dict:
        """
        Extract JSON from a response that may contain additional text.
        
        Args:
            text: Response text that may contain JSON
            
        Returns:
            Parsed JSON dictionary
        """
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
        raise json.JSONDecodeError("No JSON object found in response", text, 0)
    
    async def generate_itinerary(
        self,
        analysis: TranscriptAnalysis,
        preferences: UserPreferences,
        video_titles: list[str]
    ) -> Itinerary:
        """
        Generate a complete itinerary using the dual-agent architecture.
        
        The Tool Call Agent generates the itinerary and can call the Internet Search Agent
        when it needs real-time information about prices, hours, etc.
        
        Args:
            analysis: Transcript analysis results
            preferences: User travel preferences
            video_titles: Titles of source videos
            
        Returns:
            Complete Itinerary object
        """
        prompt = self._build_itinerary_generation_prompt(
            analysis, preferences, video_titles
        )
        
        try:
            response_text = await self._tool_call_agent(prompt, max_tool_calls=15)
            
            if not response_text:
                raise GenerationError("Empty response from Gemini API")
            
            data = self._extract_json_from_response(response_text)
            
            days = []
            for day_data in data.get("days", []):
                activities = [
                    Activity(**act) for act in day_data.get("activities", [])
                ]
                meals = [
                    MealRecommendation(**meal) for meal in day_data.get("meals", [])
                ]
                days.append(DayPlan(
                    day_number=day_data.get("day_number", 1),
                    date=day_data.get("date"),
                    theme=day_data.get("theme", "Exploration Day"),
                    summary=day_data.get("summary", ""),
                    activities=activities,
                    meals=meals,
                    total_estimated_cost=day_data.get("total_estimated_cost", 0),
                    walking_distance=day_data.get("walking_distance"),
                    notes=day_data.get("notes")
                ))
            
            budget_data = data.get("budget_breakdown", {})
            budget_breakdown = BudgetBreakdown(
                accommodation=budget_data.get("accommodation", 0),
                food=budget_data.get("food", 0),
                activities=budget_data.get("activities", 0),
                transportation=budget_data.get("transportation", 0),
                shopping=budget_data.get("shopping", 0),
                miscellaneous=budget_data.get("miscellaneous", 0),
                total=budget_data.get("total", data.get("total_budget_estimate", 0))
            )
            
            return Itinerary(
                title=data.get("title", f"Trip to {analysis.destination}"),
                destination=data.get("destination", analysis.destination),
                country=data.get("country"),
                summary=data.get("summary", ""),
                days=days,
                total_budget_estimate=data.get("total_budget_estimate", 0),
                currency=preferences.currency,
                budget_breakdown=budget_breakdown,
                general_tips=data.get("general_tips", []),
                packing_suggestions=data.get("packing_suggestions", []),
                emergency_contacts=data.get("emergency_contacts", []),
                language_phrases=data.get("language_phrases", []),
                best_time_to_visit=data.get("best_time_to_visit"),
                weather_info=data.get("weather_info")
            )
            
        except json.JSONDecodeError as e:
            raise GenerationError(f"Failed to parse itinerary response: {str(e)}")
        except Exception as e:
            raise GenerationError(f"Itinerary generation failed: {str(e)}")
    
    async def generate_itinerary_from_videos(
        self,
        video_results: list[VideoProcessingResult],
        preferences: UserPreferences
    ) -> tuple[TranscriptAnalysis, Itinerary]:
        """
        Complete pipeline: analyze videos and generate itinerary.
        
        Args:
            video_results: Processed video results
            preferences: User travel preferences
            
        Returns:
            Tuple of (TranscriptAnalysis, Itinerary)
        """
        analysis = await self.analyze_multiple_transcripts(video_results)
        
        video_titles = [r.metadata.title for r in video_results]
        
        itinerary = await self.generate_itinerary(
            analysis, preferences, video_titles
        )
        
        return analysis, itinerary
    
    async def refine_itinerary(
        self,
        itinerary: Itinerary,
        feedback: str
    ) -> Itinerary:
        """
        Refine an existing itinerary based on user feedback using the dual-agent architecture.
        
        Args:
            itinerary: Existing itinerary to refine
            feedback: User feedback for improvements
            
        Returns:
            Refined Itinerary
        """
        prompt = f"""Refine this travel itinerary based on user feedback.

CURRENT ITINERARY:
{itinerary.model_dump_json(indent=2)}

USER FEEDBACK:
{feedback}

IMPORTANT: You have access to the search_internet tool to look up current information if needed.
Use it to verify any changes in prices, hours, or availability.

TASK:
Modify the itinerary to address the user's feedback while maintaining:
- The overall structure and format
- Realistic timings and logistics
- Budget considerations
- The same destination and duration

Return the complete refined itinerary as a valid JSON object with the same structure as the input.
RESPOND ONLY WITH THE JSON OBJECT, no additional text."""
        
        try:
            response_text = await self._tool_call_agent(prompt, max_tool_calls=10)
            
            if not response_text:
                raise GenerationError("Empty response from Gemini API")
            
            data = self._extract_json_from_response(response_text)
            
            days = []
            for day_data in data.get("days", []):
                activities = [
                    Activity(**act) for act in day_data.get("activities", [])
                ]
                meals = [
                    MealRecommendation(**meal) for meal in day_data.get("meals", [])
                ]
                days.append(DayPlan(
                    day_number=day_data.get("day_number", 1),
                    date=day_data.get("date"),
                    theme=day_data.get("theme", "Exploration Day"),
                    summary=day_data.get("summary", ""),
                    activities=activities,
                    meals=meals,
                    total_estimated_cost=day_data.get("total_estimated_cost", 0),
                    walking_distance=day_data.get("walking_distance"),
                    notes=day_data.get("notes")
                ))
            
            budget_data = data.get("budget_breakdown", {})
            budget_breakdown = BudgetBreakdown(
                accommodation=budget_data.get("accommodation", 0),
                food=budget_data.get("food", 0),
                activities=budget_data.get("activities", 0),
                transportation=budget_data.get("transportation", 0),
                shopping=budget_data.get("shopping", 0),
                miscellaneous=budget_data.get("miscellaneous", 0),
                total=budget_data.get("total", data.get("total_budget_estimate", 0))
            )
            
            return Itinerary(
                title=data.get("title", itinerary.title),
                destination=data.get("destination", itinerary.destination),
                country=data.get("country", itinerary.country),
                summary=data.get("summary", itinerary.summary),
                days=days,
                total_budget_estimate=data.get("total_budget_estimate", itinerary.total_budget_estimate),
                currency=data.get("currency", itinerary.currency),
                budget_breakdown=budget_breakdown,
                general_tips=data.get("general_tips", itinerary.general_tips),
                packing_suggestions=data.get("packing_suggestions", itinerary.packing_suggestions),
                emergency_contacts=data.get("emergency_contacts", itinerary.emergency_contacts),
                language_phrases=data.get("language_phrases", itinerary.language_phrases),
                best_time_to_visit=data.get("best_time_to_visit", itinerary.best_time_to_visit),
                weather_info=data.get("weather_info", itinerary.weather_info)
            )
            
        except Exception as e:
            raise GenerationError(f"Itinerary refinement failed: {str(e)}")
    
    def close(self):
        """Close the Gemini client and release resources."""
        if self._client is not None:
            self._client.close()
            self._client = None


gemini_service = GeminiService()
