# Step 5: Itinerary API & Storage

## Objective
Create API endpoints for itinerary generation and MongoDB storage for saving/retrieving itineraries.

## Prerequisites
- Step 1 completed (Project Setup)
- Step 2 completed (Authentication)
- Step 3 completed (YouTube Transcript Service)
- Step 4 completed (Gemini AI Integration)

## Implementation Details

### 5.1 Itinerary Collection Schema
```javascript
{
  _id: ObjectId,
  user_id: ObjectId,           // Reference to user
  title: String,               // Auto-generated or user-provided
  destination: String,
  youtube_urls: [String],      // Original video URLs
  video_titles: [String],      // Extracted video titles
  user_preferences: {
    budget: Number,
    currency: String,
    trip_type: String,
    activity_style: String,
    num_travelers: Number,
    trip_duration_days: Number,
    dietary_restrictions: [String],
    mobility_constraints: String,
    must_visit_places: [String],
    additional_notes: String
  },
  generated_content: {         // Full itinerary JSON
    summary: String,
    days: [...],
    total_budget_estimate: Number,
    budget_breakdown: {...},
    general_tips: [String]
  },
  status: String,              // "generating", "completed", "failed"
  created_at: Date,
  updated_at: Date
}

// Indexes
{ user_id: 1, created_at: -1 }  // Fast user history lookup
{ status: 1 }                    // For admin monitoring
```

### 5.2 Itinerary Router (`api/routers/itinerary.py`)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/itinerary/generate` | POST | Yes | Start itinerary generation |
| `/api/itinerary/status/{id}` | GET | Yes | Check generation status |
| `/api/itinerary/{id}` | GET | Yes | Get full itinerary |
| `/api/itinerary/list` | GET | Yes | List user's itineraries |
| `/api/itinerary/{id}` | DELETE | Yes | Delete an itinerary |

### 5.3 Generation Flow
```
1. Client POSTs to /generate with:
   - youtube_urls: [...]
   - preferences: {...}

2. Server validates input:
   - Check all URLs are valid YouTube links
   - Validate preferences schema

3. Create itinerary record with status="generating"
   - Return itinerary ID immediately

4. Background task starts:
   a. Extract transcripts from all videos
   b. Analyze transcripts with Gemini
   c. Generate itinerary with grounding
   d. Save result, update status="completed"

5. Client polls /status/{id} until complete
   - Or use WebSocket for real-time updates (future)
```

### 5.4 Request/Response Models

**Generate Request:**
```python
class GenerateRequest(BaseModel):
    youtube_urls: list[HttpUrl]
    preferences: UserPreferences
    title: str | None = None  # Optional custom title
```

**Generate Response:**
```python
class GenerateResponse(BaseModel):
    itinerary_id: str
    status: str
    message: str
```

**Itinerary Response:**
```python
class ItineraryResponse(BaseModel):
    id: str
    title: str
    destination: str
    youtube_urls: list[str]
    preferences: UserPreferences
    content: Itinerary
    created_at: datetime
```

### 5.5 Background Tasks
Use FastAPI's `BackgroundTasks` for async generation:
```python
@router.post("/generate")
async def generate_itinerary(
    request: GenerateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    itinerary_id = await create_itinerary_record(...)
    background_tasks.add_task(process_generation, itinerary_id)
    return {"itinerary_id": itinerary_id, "status": "generating"}
```

## Research Areas
- FastAPI BackgroundTasks vs Celery for long-running tasks
- MongoDB aggregation for itinerary statistics
- Optimistic concurrency for status updates

## Expected Outcome
- Users can trigger itinerary generation
- Generation runs asynchronously with status polling
- Itineraries stored in MongoDB with user association
- Users can view history and retrieve past itineraries

## Estimated Effort
2-3 days

## Dependencies
- Step 1: Project Setup
- Step 2: Authentication
- Step 3: YouTube Transcript Service
- Step 4: Gemini AI Integration
