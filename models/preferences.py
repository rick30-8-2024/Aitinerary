"""
User Preferences Models

Defines schemas for user travel preferences used in itinerary generation.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    """Schema for user travel preferences."""
    
    budget: float = Field(..., gt=0, description="Total budget for the trip")
    currency: str = Field(default="USD", description="Currency code (e.g., USD, EUR, INR)")
    trip_type: Literal["family", "friends", "solo", "couple"] = Field(
        ..., 
        description="Type of trip based on travelers"
    )
    activity_style: Literal["sporty", "relaxing", "mixed", "adventure", "cultural"] = Field(
        default="mixed",
        description="Preferred activity style"
    )
    num_travelers: int = Field(..., ge=1, le=50, description="Number of travelers")
    trip_duration_days: int = Field(..., ge=1, le=30, description="Duration of trip in days")
    dietary_restrictions: list[str] = Field(
        default_factory=list,
        description="List of dietary restrictions (e.g., vegetarian, vegan, halal)"
    )
    mobility_constraints: Optional[str] = Field(
        default=None,
        description="Any mobility or accessibility requirements"
    )
    must_visit_places: list[str] = Field(
        default_factory=list,
        description="Specific places that must be included in the itinerary"
    )
    accommodation_preference: Literal["budget", "mid-range", "luxury"] = Field(
        default="mid-range",
        description="Preferred accommodation level"
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Trip start date in YYYY-MM-DD format"
    )
    additional_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Any additional notes or preferences"
    )


class PreferencesCreate(UserPreferences):
    """Schema for creating new preferences (same as UserPreferences)."""
    pass


class PreferencesUpdate(BaseModel):
    """Schema for updating preferences (all fields optional)."""
    
    budget: Optional[float] = Field(default=None, gt=0)
    currency: Optional[str] = None
    trip_type: Optional[Literal["family", "friends", "solo", "couple"]] = None
    activity_style: Optional[Literal["sporty", "relaxing", "mixed", "adventure", "cultural"]] = None
    num_travelers: Optional[int] = Field(default=None, ge=1, le=50)
    trip_duration_days: Optional[int] = Field(default=None, ge=1, le=30)
    dietary_restrictions: Optional[list[str]] = None
    mobility_constraints: Optional[str] = None
    must_visit_places: Optional[list[str]] = None
    accommodation_preference: Optional[Literal["budget", "mid-range", "luxury"]] = None
    start_date: Optional[str] = None
    additional_notes: Optional[str] = Field(default=None, max_length=1000)


class SavedPreferences(UserPreferences):
    """Schema for user's saved default preferences."""
    
    id: str = Field(..., description="Unique identifier for saved preferences")
    user_id: str = Field(..., description="User ID who owns these preferences")
    name: str = Field(..., description="Name for this preference set")
    is_default: bool = Field(default=False, description="Whether this is the user's default")
