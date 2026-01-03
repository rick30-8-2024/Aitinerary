# Step 4: Gemini AI Integration Service

## Objective
Integrate Gemini 2.5 Flash with Google Search and Google Maps grounding to generate intelligent travel itineraries.

## Prerequisites
- Step 1 completed (Project Setup)
- Step 3 completed (YouTube Transcript Service)
- Gemini API key with grounding features enabled

## Implementation Details

### 4.1 Gemini Service (`services/gemini_service.py`)

**Core Functions:**
```python
async def analyze_transcript(transcript: str, video_metadata: dict) -> dict:
    """Analyze transcript to extract places, activities, recommendations."""

async def generate_itinerary(
    transcript_analysis: dict,
    user_preferences: UserPreferences
) -> Itinerary:
    """Generate complete itinerary using grounding."""

async def enrich_with_maps_data(places: list[str]) -> list[PlaceDetails]:
    """Use Google Maps grounding to get place details, reviews, warnings."""
```

### 4.2 Gemini Configuration
```python
import google.generativeai as genai

genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    tools=[
        genai.Tool.from_google_search_retrieval(
            google_search_retrieval=genai.GoogleSearchRetrieval()
        ),
        # Google Maps grounding configuration
    ]
)
```

### 4.3 User Preferences Model (`models/preferences.py`)
```python
class UserPreferences(BaseModel):
    budget: float
    currency: str = "USD"
    trip_type: Literal["family", "friends", "solo", "couple"]
    activity_style: Literal["sporty", "relaxing", "mixed"]
    num_travelers: int
    trip_duration_days: int
    dietary_restrictions: list[str] = []
    mobility_constraints: str | None = None
    must_visit_places: list[str] = []
    additional_notes: str | None = None
```

### 4.4 Itinerary Model (`models/itinerary.py`)
```python
class Activity(BaseModel):
    time_slot: str  # "09:00 - 11:00"
    place_name: str
    description: str
    estimated_cost: float
    travel_time_from_previous: str | None
    tips: list[str] = []
    warnings: list[str] = []  # Scam alerts from reviews

class DayPlan(BaseModel):
    day_number: int
    date: str | None
    theme: str  # "Cultural Exploration", "Beach Day", etc.
    activities: list[Activity]
    meals: list[MealRecommendation]
    total_estimated_cost: float

class Itinerary(BaseModel):
    title: str
    destination: str
    summary: str
    days: list[DayPlan]
    total_budget_estimate: float
    budget_breakdown: dict
    general_tips: list[str]
    emergency_contacts: list[str] = []  # Local emergency numbers
```

### 4.5 Prompt Engineering

**Transcript Analysis Prompt:**
```
Analyze this travel vlog transcript and extract:
1. All places mentioned (attractions, restaurants, hotels)
2. Activities shown or recommended
3. Local tips and recommendations
4. Any warnings or things to avoid
5. Estimated costs mentioned

Transcript: {transcript}
Video Title: {title}
```

**Itinerary Generation Prompt:**
```
Create a detailed {days}-day travel itinerary for {destination} based on:

TRAVELER PROFILE:
- Budget: {budget} {currency}
- Trip Type: {trip_type}
- Style: {activity_style}
- Travelers: {num_travelers}
- Dietary: {dietary_restrictions}
- Mobility: {mobility_constraints}

PLACES TO INCLUDE (from video analysis):
{places_list}

MUST VISIT:
{must_visit_places}

Generate a day-by-day itinerary with:
- Morning, afternoon, evening activities
- Realistic time slots and travel times
- Cost estimates per activity
- Local food recommendations for each meal
- Any scam warnings from recent reviews
- Alternative options for bad weather

Use Google Search for current prices and Google Maps for:
- Opening hours
- Recent reviews (look for scam mentions)
- Travel times between locations
```

### 4.6 Structured Output (JSON Mode)
Configure Gemini to return structured JSON matching our Itinerary model schema for reliable parsing.

## Research Areas
- Gemini 2.5 Flash structured output / JSON mode
- Google Maps grounding API configuration
- Token usage optimization for long transcripts
- Error handling for grounding failures

## Expected Outcome
- Transcript analysis extracts actionable travel information
- Itinerary generation uses real-time data via grounding
- Structured, parseable output matching our models
- Scam warnings and tips from Google Maps reviews included

## Estimated Effort
3-4 days

## Dependencies
- Step 1: Project Setup
- Step 3: YouTube Transcript Service
