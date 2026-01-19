"""
Gemini AI Integration Service

Provides functionality to analyze YouTube videos and generate travel itineraries
using Google's Gemini model with a dual-agent architecture:
- Internet Search Agent: Has Google Search grounding for real-time information
- Tool Call Agent: Generates structured JSON responses and can call the search agent
"""

import json
import re
from typing import Optional

import google.generativeai as genai
import google.ai.generativelanguage as glm
from google.generativeai.types import GenerationConfig
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
from services.youtube_video_service import VideoTravelInfo, MultiVideoTravelInfo


class GeminiServiceError(Exception):
    """Base exception for Gemini service errors."""
    pass


class APIKeyNotConfiguredError(GeminiServiceError):
    """Raised when Gemini API key is not configured."""
    pass


class GenerationError(GeminiServiceError):
    """Raised when content generation fails."""
    pass


def _create_search_tool() -> glm.Tool:
    """Create the search internet tool for function calling."""
    return glm.Tool(
        function_declarations=[
            glm.FunctionDeclaration(
                name="search_internet",
                description="Search the internet for real-time information about places, prices, opening hours, reviews, or any current travel information. Use this when you need up-to-date information that might not be in your training data.",
                parameters=glm.Schema(
                    type=glm.Type.OBJECT,
                    properties={
                        "query": glm.Schema(
                            type=glm.Type.STRING,
                            description="The search query to find information about. Be specific and include location names."
                        ),
                        "context": glm.Schema(
                            type=glm.Type.STRING,
                            description="Additional context about what kind of information you're looking for (e.g., 'prices', 'opening hours', 'reviews', 'nearby attractions')"
                        )
                    },
                    required=["query"]
                )
            )
        ]
    )


class GeminiService:
    """Service for AI-powered transcript analysis and itinerary generation using dual-agent architecture."""
    
    MODEL_NAME = settings.GEMINI_MODEL_NAME or "gemini-2.5-flash-preview-05-20"
    
    def __init__(self):
        """Initialize the Gemini service."""
        self._configured = False
        self._model: Optional[genai.GenerativeModel] = None
        self._search_model: Optional[genai.GenerativeModel] = None
    
    def _configure(self):
        """Configure the Gemini API with the API key."""
        if not settings.GEMINI_API_KEY:
            raise APIKeyNotConfiguredError(
                "GEMINI_API_KEY is not configured. Please set it in your environment variables."
            )
        
        if not self._configured:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._configured = True
    
    def _get_model(self) -> genai.GenerativeModel:
        """Get or create the main Gemini model."""
        self._configure()
        
        if self._model is None:
            self._model = genai.GenerativeModel(self.MODEL_NAME)
        
        return self._model
    
    def _get_search_model(self) -> genai.GenerativeModel:
        """Get or create the search-enabled Gemini model."""
        self._configure()
        
        if self._search_model is None:
            self._search_model = genai.GenerativeModel(self.MODEL_NAME)
        
        return self._search_model
    
    def _get_tool_model(self) -> genai.GenerativeModel:
        """Get or create the tool-calling Gemini model."""
        self._configure()
        
        return genai.GenerativeModel(
            self.MODEL_NAME,
            tools=[_create_search_tool()]
        )
    
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
        model = self._get_search_model()
        
        search_prompt = f"""Search the internet and provide detailed, accurate information for: {query}
        
{"Context: " + context if context else ""}

Provide:
1. Current and accurate information
2. Specific details like prices, addresses, opening hours if relevant
3. Recent reviews or ratings if available
4. Any warnings or important notes

Be concise but thorough. Format the response as clear, readable text."""
        
        try:
            response = await model.generate_content_async(
                search_prompt,
                generation_config=GenerationConfig(
                    temperature=0.3,
                    top_p=0.95,
                ),
                tools="google_search_retrieval"
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
        model = self._get_tool_model()
        
        chat = model.start_chat(history=[])
        
        tool_calls_made = 0
        
        response = await chat.send_message_async(
            prompt,
            generation_config=GenerationConfig(
                temperature=0.7,
                top_p=0.95,
            )
        )
        
        while tool_calls_made < max_tool_calls:
            if not response.candidates or not response.candidates[0].content.parts:
                raise GenerationError("Empty response from Gemini API")
            
            response_parts = response.candidates[0].content.parts
            
            function_calls = []
            for part in response_parts:
                if hasattr(part, 'function_call') and part.function_call:
                    function_calls.append(part.function_call)
            
            if not function_calls:
                text_parts = []
                for part in response_parts:
                    if hasattr(part, 'text') and part.text:
                        text_parts.append(part.text)
                if text_parts:
                    return "".join(text_parts)
                raise GenerationError("No text or function calls in response")
            
            function_responses = []
            for fc in function_calls:
                if fc.name == "search_internet":
                    args = dict(fc.args) if fc.args else {}
                    query = args.get("query", "")
                    context = args.get("context")
                    
                    search_result = await self._internet_search_agent(query, context)
                    tool_calls_made += 1
                    
                    function_responses.append(
                        glm.Part(
                            function_response=glm.FunctionResponse(
                                name="search_internet",
                                response={"result": search_result}
                            )
                        )
                    )
            
            response = await chat.send_message_async(function_responses)
        
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

Be thorough and extract all relevant travel information. If something is not mentioned, use empty list or null.

IMPORTANT: Respond with a valid JSON object only, no additional text."""
    
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
- Total Budget: {preferences.budget} {preferences.currency}
- Trip Type: {preferences.trip_type}
- Activity Style: {preferences.activity_style}
- Number of Travelers: {preferences.num_travelers}
- Accommodation Preference: {preferences.accommodation_preference} (for budget calculation only - we don't recommend specific hotels)
- Dietary Restrictions: {', '.join(preferences.dietary_restrictions) if preferences.dietary_restrictions else 'None'}
- Mobility Constraints: {preferences.mobility_constraints or 'None'}
- Start Date: {preferences.start_date or 'Flexible'}

MUST VISIT PLACES (User Requested):
{chr(10).join(f'- {place}' for place in preferences.must_visit_places) if preferences.must_visit_places else 'None specified'}

ADDITIONAL NOTES:
{preferences.additional_notes or 'None'}

IMPORTANT: You have access to the search_internet tool to look up current information about:
- Opening hours and prices for attractions
- Local delicacies and authentic food spots
- Hidden gems and local markets
- Recent travel advisories or warnings

Use the search_internet tool to:
- Search for local delicacies of {analysis.destination} to add to meal recommendations
- Find hidden gems or local markets that tourists often miss
- Verify current prices and opening hours

CRITICAL GUIDELINES FOR ITINERARY GENERATION:

1. **COMMUTE/TRANSPORT INFORMATION:**
   - ONLY include transport_mode if it was explicitly mentioned in the vlog
   - If not mentioned in the vlog, set transport_mode to null
   - Do NOT make up transport information - it must be from the vlog content

2. **MEAL RECOMMENDATIONS:**
   - ONLY recommend restaurants/eateries that were actually shown or mentioned in the vlogs
   - If no meals were mentioned in the vlog, you can use search_internet to find LOCAL DELICACIES
   - For local delicacies found via internet search, set is_local_delicacy to true and add a note like "Local delicacy - you might want to try this if you're in the area"
   - Do NOT make up random restaurant names or recommendations
   - If no reliable meal info is available, leave the meals array empty for that day

3. **ACCOMMODATION:**
   - DO NOT include any hotel or accommodation recommendations in the itinerary
   - DO NOT suggest specific hotels, hostels, or stay options
   - Calculate the remaining budget after all activities, food, and transport
   - This remaining amount is the "accommodation_budget" - what's left for the traveler to book their own stay

4. **HIDDEN GEMS & LOCAL MARKETS:**
   - If the vlog mentioned any hidden gems, local markets, or off-the-beaten-path locations, INCLUDE them
   - Use search_internet to find additional hidden gems or local markets in {analysis.destination}
   - Mark these with is_hidden_gem: true in the activity

5. **SAME PLACE MULTIPLE TIMES:**
   - It's OK to include the same place multiple times if there are different events/experiences at different times
   - For example: "Marina Beach" with event_name "Sunrise View" and "Marina Beach" with event_name "Evening Market" are valid separate activities
   - ALWAYS provide an event_name for each activity - this is a short 2-4 word description of what you'll do there
   - The title displayed to the user will be "place_name - event_name" (e.g., "Triveni Ghat - Exploring" or "Triveni Ghat - Ganga Aarti")

6. **UNKNOWN COSTS:**
   - If you cannot find or verify the actual cost from the vlog or internet search, set cost_unknown to true
   - This applies to estimated_cost in activities, transport_cost for commute, and estimated_cost in meals
   - When cost is unknown, set the cost value to 0 and cost_unknown to true
   - Do NOT show 0 as the cost - that confuses users. Mark it as unknown instead.
   - For transport costs, if you add a commute but don't know the price, set transport_cost to 0 and transport_cost_unknown to true

7. **NO FABRICATED CONTENT:**
   - Do not add example activities, example costs, or placeholder recommendations
   - Every item must come from the vlog content or verified internet search
   - If the vlog didn't cover enough content for a full day, include fewer activities rather than making things up

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
                    "place_name": "Name of location (e.g., 'Triveni Ghat')",
                    "event_name": "Short purpose/event at this place (e.g., 'Exploring', 'Ganga Aarti', 'Sunrise View')",
                    "description": "What to do there",
                    "estimated_cost": 0,
                    "cost_unknown": false,
                    "transport_cost": 0,
                    "transport_cost_unknown": false,
                    "transport_mode": "Only if mentioned in vlog, otherwise null",
                    "tips": ["tip1", "tip2"],
                    "warnings": ["warning1"],
                    "booking_required": false,
                    "weather_alternative": "Alternative activity or null",
                    "is_hidden_gem": false,
                    "source": "vlog or internet_search"
                }}
            ],
            "meals": [
                {{
                    "meal_type": "breakfast/lunch/dinner",
                    "place_name": "Restaurant name from vlog OR Local dish name",
                    "cuisine": "Type of food",
                    "estimated_cost": 0,
                    "cost_unknown": false,
                    "dietary_notes": "Dietary info or null",
                    "recommendation_reason": "Why recommended - must reference vlog or local delicacy",
                    "is_local_delicacy": false,
                    "source": "vlog or internet_search"
                }}
            ],
            "total_estimated_cost": 0,
            "walking_distance": "Distance or null",
            "notes": "Additional notes or null"
        }}
    ],
    "total_budget_estimate": 0,
    "budget_breakdown": {{
        "food": 0,
        "activities": 0,
        "transportation": 0,
        "shopping": 0,
        "miscellaneous": 0,
        "subtotal_without_accommodation": 0,
        "accommodation_budget": 0,
        "total": 0
    }},
    "accommodation_note": "Your remaining budget for accommodation is X {preferences.currency}. Based on your {preferences.accommodation_preference} preference, you can choose your own hotel/stay.",
    "general_tips": ["tip1", "tip2"],
    "packing_suggestions": ["item1", "item2"],
    "emergency_contacts": ["contact1"],
    "language_phrases": ["phrase1"],
    "best_time_to_visit": "Best season/months or null",
    "weather_info": "Expected weather or null"
}}

BUDGET CALCULATION LOGIC:
1. Calculate total cost of activities, food, transportation, shopping, and miscellaneous
2. subtotal_without_accommodation = sum of all above
3. accommodation_budget = {preferences.budget} - subtotal_without_accommodation
4. total = {preferences.budget} (user's total budget)

IMPORTANT:
- The accommodation_budget represents what's left for the traveler to book their own stay
- DO NOT recommend specific hotels - leave that choice to the traveler
- Make the itinerary practical and achievable
- Only include reliable information from vlogs or verified internet search
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
        model = self._get_model()
        
        prompt = self._build_transcript_analysis_prompt(
            transcript, video_title, video_author
        )
        
        try:
            response = await model.generate_content_async(
                prompt,
                generation_config=GenerationConfig(
                    temperature=0.3,
                    top_p=0.95,
                )
            )
            
            if not response.text:
                raise GenerationError("Empty response from Gemini API")
            
            data = self._extract_json_from_response(response.text)
            
            if isinstance(data, list):
                if not data:
                    raise GenerationError("Empty list response from Gemini API")
                data = data[0]
            
            destination = data.get("destination") or "Unknown"
            if isinstance(destination, list):
                destination = ", ".join(str(d) for d in destination[:3]) if destination else "Unknown"
            
            best_time = data.get("best_time_to_visit")
            if isinstance(best_time, dict):
                best_time = next(iter(best_time.values()), None) if best_time else None
            elif isinstance(best_time, list):
                best_time = best_time[0] if best_time else None
            
            return TranscriptAnalysis(
                destination=destination,
                places_mentioned=data.get("places_mentioned") or [],
                activities_mentioned=data.get("activities_mentioned") or [],
                local_tips=data.get("local_tips") or [],
                warnings=data.get("warnings") or [],
                estimated_costs=data.get("estimated_costs") or {},
                best_time_to_visit=best_time,
                key_highlights=data.get("key_highlights") or []
            )
            
        except json.JSONDecodeError as e:
            raise GenerationError(f"Failed to parse Gemini response: {str(e)}")
        except Exception as e:
            raise GenerationError(f"Transcript analysis failed: {str(e)}")
    
    def convert_video_info_to_analysis(
        self,
        video_info: VideoTravelInfo
    ) -> TranscriptAnalysis:
        """
        Convert VideoTravelInfo from the new video service to TranscriptAnalysis format.
        
        Args:
            video_info: VideoTravelInfo from youtube_video_service
            
        Returns:
            TranscriptAnalysis compatible with itinerary generation
        """
        places_mentioned = [place.name for place in video_info.places]
        if video_info.hidden_gems:
            places_mentioned.extend([gem.name for gem in video_info.hidden_gems])
        if video_info.food_recommendations:
            places_mentioned.extend([f"{food.name} ({food.location})" if food.location else food.name
                                    for food in video_info.food_recommendations])
        
        activities_mentioned = [act.name for act in video_info.activities]
        
        local_tips = [tip.tip for tip in video_info.travel_tips]
        
        warnings = [tip.tip for tip in video_info.travel_tips
                   if tip.category in ("safety", "scam", "warning", "caution")]
        
        estimated_costs = {}
        for act in video_info.activities:
            if act.cost:
                estimated_costs[act.name] = act.cost
        for food in video_info.food_recommendations:
            if food.price_range:
                estimated_costs[food.name] = food.price_range
        
        key_highlights = []
        key_highlights.extend([place.name for place in video_info.places[:5]])
        key_highlights.extend([gem.name for gem in video_info.hidden_gems[:3]])
        key_highlights.extend([act.name for act in video_info.activities[:5]])
        
        return TranscriptAnalysis(
            destination=video_info.destination,
            places_mentioned=places_mentioned,
            activities_mentioned=activities_mentioned,
            local_tips=local_tips,
            warnings=warnings,
            estimated_costs=estimated_costs,
            best_time_to_visit=video_info.best_time_to_visit,
            key_highlights=key_highlights[:10]
        )
    
    def convert_multi_video_info_to_analysis(
        self,
        multi_video_info: MultiVideoTravelInfo
    ) -> TranscriptAnalysis:
        """
        Convert MultiVideoTravelInfo to TranscriptAnalysis format.
        
        Args:
            multi_video_info: MultiVideoTravelInfo from multiple videos
            
        Returns:
            Combined TranscriptAnalysis
        """
        places_mentioned = [place.name for place in multi_video_info.all_places]
        if multi_video_info.all_hidden_gems:
            places_mentioned.extend([gem.name for gem in multi_video_info.all_hidden_gems])
        if multi_video_info.all_food_recommendations:
            places_mentioned.extend([f"{food.name} ({food.location})" if food.location else food.name
                                    for food in multi_video_info.all_food_recommendations])
        
        activities_mentioned = [act.name for act in multi_video_info.all_activities]
        
        local_tips = [tip.tip for tip in multi_video_info.all_travel_tips]
        
        warnings = [tip.tip for tip in multi_video_info.all_travel_tips
                   if tip.category in ("safety", "scam", "warning", "caution")]
        
        estimated_costs = {}
        for act in multi_video_info.all_activities:
            if act.cost:
                estimated_costs[act.name] = act.cost
        for food in multi_video_info.all_food_recommendations:
            if food.price_range:
                estimated_costs[food.name] = food.price_range
        
        best_time = None
        for video_info in multi_video_info.videos:
            if video_info.best_time_to_visit:
                best_time = video_info.best_time_to_visit
                break
        
        key_highlights = []
        key_highlights.extend([place.name for place in multi_video_info.all_places[:5]])
        key_highlights.extend([gem.name for gem in multi_video_info.all_hidden_gems[:3]])
        key_highlights.extend([act.name for act in multi_video_info.all_activities[:5]])
        
        return TranscriptAnalysis(
            destination=multi_video_info.combined_destination,
            places_mentioned=places_mentioned,
            activities_mentioned=activities_mentioned,
            local_tips=local_tips,
            warnings=warnings,
            estimated_costs=estimated_costs,
            best_time_to_visit=best_time,
            key_highlights=key_highlights[:10]
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
                activities = []
                for act in day_data.get("activities", []):
                    if act.get("warnings") is None:
                        act["warnings"] = []
                    if act.get("tips") is None:
                        act["tips"] = []
                    activities.append(Activity(**act))
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
                food=max(0, budget_data.get("food", 0)),
                activities=max(0, budget_data.get("activities", 0)),
                transportation=max(0, budget_data.get("transportation", 0)),
                shopping=max(0, budget_data.get("shopping", 0)),
                miscellaneous=max(0, budget_data.get("miscellaneous", 0)),
                subtotal_without_accommodation=max(0, budget_data.get("subtotal_without_accommodation", 0)),
                accommodation_budget=max(0, budget_data.get("accommodation_budget", 0)),
                total=max(0, budget_data.get("total", data.get("total_budget_estimate", 0)))
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
                accommodation_note=data.get("accommodation_note"),
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
    
    async def generate_itinerary_from_video_info(
        self,
        video_info: VideoTravelInfo,
        preferences: UserPreferences
    ) -> tuple[TranscriptAnalysis, Itinerary]:
        """
        Generate itinerary from a single VideoTravelInfo.
        
        Args:
            video_info: VideoTravelInfo from youtube_video_service
            preferences: User travel preferences
            
        Returns:
            Tuple of (TranscriptAnalysis, Itinerary)
        """
        analysis = self.convert_video_info_to_analysis(video_info)
        
        video_titles = [video_info.video_title or video_info.video_url]
        
        itinerary = await self.generate_itinerary(
            analysis, preferences, video_titles
        )
        
        return analysis, itinerary
    
    async def generate_itinerary_from_multi_video_info(
        self,
        multi_video_info: MultiVideoTravelInfo,
        preferences: UserPreferences
    ) -> tuple[TranscriptAnalysis, Itinerary]:
        """
        Generate itinerary from MultiVideoTravelInfo.
        
        Args:
            multi_video_info: MultiVideoTravelInfo from multiple videos
            preferences: User travel preferences
            
        Returns:
            Tuple of (TranscriptAnalysis, Itinerary)
        """
        analysis = self.convert_multi_video_info_to_analysis(multi_video_info)
        
        video_titles = []
        for video_info in multi_video_info.videos:
            video_titles.append(video_info.video_title or video_info.video_url)
        
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
- Logistics
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
                activities = []
                for act in day_data.get("activities", []):
                    if act.get("warnings") is None:
                        act["warnings"] = []
                    if act.get("tips") is None:
                        act["tips"] = []
                    activities.append(Activity(**act))
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
                food=budget_data.get("food", 0),
                activities=budget_data.get("activities", 0),
                transportation=budget_data.get("transportation", 0),
                shopping=budget_data.get("shopping", 0),
                miscellaneous=budget_data.get("miscellaneous", 0),
                subtotal_without_accommodation=budget_data.get("subtotal_without_accommodation", 0),
                accommodation_budget=budget_data.get("accommodation_budget", 0),
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
                accommodation_note=data.get("accommodation_note", itinerary.accommodation_note),
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
        """Close the Gemini service and release resources."""
        self._model = None
        self._search_model = None
        self._configured = False


gemini_service = GeminiService()
