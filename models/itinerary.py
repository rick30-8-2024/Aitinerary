"""
Itinerary Models

Defines schemas for travel itineraries generated from YouTube video analysis.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PlaceDetails(BaseModel):
    """Schema for place details with Google Maps data."""
    
    name: str = Field(..., description="Name of the place")
    address: Optional[str] = Field(default=None, description="Full address")
    category: str = Field(..., description="Category (restaurant, attraction, hotel, etc.)")
    rating: Optional[float] = Field(default=None, ge=0, le=5, description="Google rating")
    review_count: Optional[int] = Field(default=None, ge=0, description="Number of reviews")
    price_level: Optional[str] = Field(default=None, description="Price level indicator ($, $$, $$$)")
    opening_hours: Optional[list[str]] = Field(default=None, description="Opening hours by day")
    google_maps_url: Optional[str] = Field(default=None, description="Google Maps link")
    photo_url: Optional[str] = Field(default=None, description="Photo URL")


class MealRecommendation(BaseModel):
    """Schema for meal recommendations."""
    
    meal_type: str = Field(..., description="breakfast, lunch, dinner, or snack")
    place_name: str = Field(..., description="Restaurant or food place name")
    cuisine: Optional[str] = Field(default=None, description="Type of cuisine")
    estimated_cost: float = Field(..., ge=0, description="Estimated cost per person")
    dietary_notes: Optional[str] = Field(default=None, description="Dietary information")
    recommendation_reason: Optional[str] = Field(default=None, description="Why this is recommended")
    place_details: Optional[PlaceDetails] = Field(default=None, description="Detailed place info")


class Activity(BaseModel):
    """Schema for a single activity in the itinerary."""
    
    time_slot: str = Field(..., description="Time range (e.g., '09:00 - 11:00')")
    place_name: str = Field(..., description="Name of the place/activity")
    description: str = Field(..., description="Description of the activity")
    estimated_cost: float = Field(default=0, ge=0, description="Estimated cost")
    estimated_duration: str = Field(..., description="Expected duration (e.g., '2 hours')")
    travel_time_from_previous: Optional[str] = Field(
        default=None, 
        description="Travel time from previous activity"
    )
    transport_mode: Optional[str] = Field(
        default=None,
        description="Recommended transport (walk, taxi, metro, etc.)"
    )
    tips: list[str] = Field(default_factory=list, description="Helpful tips for this activity")
    warnings: list[str] = Field(default_factory=list, description="Warnings or scam alerts")
    booking_required: bool = Field(default=False, description="Whether advance booking is needed")
    booking_url: Optional[str] = Field(default=None, description="Booking website URL")
    place_details: Optional[PlaceDetails] = Field(default=None, description="Detailed place info")
    weather_alternative: Optional[str] = Field(
        default=None,
        description="Alternative activity for bad weather"
    )


class DayPlan(BaseModel):
    """Schema for a single day's plan in the itinerary."""
    
    day_number: int = Field(..., ge=1, description="Day number in the trip")
    date: Optional[str] = Field(default=None, description="Actual date (YYYY-MM-DD)")
    theme: str = Field(..., description="Theme of the day (e.g., 'Cultural Exploration')")
    summary: str = Field(..., description="Brief summary of the day's activities")
    activities: list[Activity] = Field(default_factory=list, description="List of activities")
    meals: list[MealRecommendation] = Field(default_factory=list, description="Meal recommendations")
    total_estimated_cost: float = Field(default=0, ge=0, description="Total cost for the day")
    walking_distance: Optional[str] = Field(default=None, description="Approximate walking distance")
    notes: Optional[str] = Field(default=None, description="Additional notes for the day")


class BudgetBreakdown(BaseModel):
    """Schema for budget breakdown by category."""
    
    accommodation: float = Field(default=0, ge=0)
    food: float = Field(default=0, ge=0)
    activities: float = Field(default=0, ge=0)
    transportation: float = Field(default=0, ge=0)
    shopping: float = Field(default=0, ge=0)
    miscellaneous: float = Field(default=0, ge=0)
    total: float = Field(default=0, ge=0)


class TranscriptAnalysis(BaseModel):
    """Schema for analyzed transcript data."""
    
    destination: str = Field(..., description="Main destination identified")
    places_mentioned: list[str] = Field(default_factory=list, description="All places mentioned")
    activities_mentioned: list[str] = Field(default_factory=list, description="Activities shown/mentioned")
    local_tips: list[str] = Field(default_factory=list, description="Local tips and recommendations")
    warnings: list[str] = Field(default_factory=list, description="Warnings or things to avoid")
    estimated_costs: dict = Field(default_factory=dict, description="Cost estimates mentioned")
    best_time_to_visit: Optional[str] = Field(default=None, description="Best time to visit")
    key_highlights: list[str] = Field(default_factory=list, description="Key highlights from video")


class Itinerary(BaseModel):
    """Schema for complete travel itinerary."""
    
    title: str = Field(..., description="Title of the itinerary")
    destination: str = Field(..., description="Main destination")
    country: Optional[str] = Field(default=None, description="Country of destination")
    summary: str = Field(..., description="Brief summary of the trip")
    days: list[DayPlan] = Field(default_factory=list, description="Day-by-day plans")
    total_budget_estimate: float = Field(default=0, ge=0, description="Total estimated budget")
    currency: str = Field(default="USD", description="Currency for all costs")
    budget_breakdown: BudgetBreakdown = Field(
        default_factory=BudgetBreakdown,
        description="Budget breakdown by category"
    )
    general_tips: list[str] = Field(default_factory=list, description="General travel tips")
    packing_suggestions: list[str] = Field(default_factory=list, description="What to pack")
    emergency_contacts: list[str] = Field(default_factory=list, description="Local emergency numbers")
    language_phrases: list[str] = Field(default_factory=list, description="Useful local phrases")
    best_time_to_visit: Optional[str] = Field(default=None, description="Best time to visit")
    weather_info: Optional[str] = Field(default=None, description="Expected weather information")


class ItineraryInDB(Itinerary):
    """Schema for itinerary stored in database."""
    
    id: str = Field(..., description="Unique itinerary ID")
    user_id: str = Field(..., description="ID of the user who created it")
    youtube_urls: list[str] = Field(default_factory=list, description="Source YouTube URLs")
    transcript_analysis: Optional[TranscriptAnalysis] = Field(
        default=None,
        description="Analysis of source transcripts"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_public: bool = Field(default=False, description="Whether itinerary is publicly shareable")
    share_code: Optional[str] = Field(default=None, description="Code for sharing the itinerary")


class ItineraryCreate(BaseModel):
    """Schema for creating a new itinerary request."""
    
    youtube_urls: list[str] = Field(
        ..., 
        min_length=1, 
        max_length=5,
        description="YouTube URLs to analyze"
    )
    preferences: "UserPreferences" = Field(..., description="User travel preferences")
    
    class Config:
        from_attributes = True


class ItineraryResponse(Itinerary):
    """Schema for itinerary API response."""
    
    id: str = Field(..., description="Unique itinerary ID")
    youtube_urls: list[str] = Field(default_factory=list)
    created_at: datetime
    is_public: bool = False
    share_code: Optional[str] = None


class ItineraryListItem(BaseModel):
    """Schema for itinerary list item (summary view)."""
    
    id: str
    title: str
    destination: str
    summary: str
    total_days: int
    total_budget_estimate: float
    currency: str
    created_at: datetime
    is_public: bool


from models.preferences import UserPreferences
ItineraryCreate.model_rebuild()
