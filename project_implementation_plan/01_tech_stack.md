# Aitinerary - Technology Stack

## Backend Framework

### FastAPI (Python 3.11+)
**Why FastAPI:**
- Async support out of the box (crucial for AI API calls)
- Automatic OpenAPI documentation
- Pydantic for data validation
- High performance (comparable to Node.js and Go)
- Easy to learn and maintain

**Research Areas:**
- FastAPI dependency injection for database connections
- Background tasks for long-running itinerary generation

---

## Database

### MongoDB (via Motor - async driver)
**Why MongoDB over PostgreSQL:**
- **Flexible schema** - Itineraries have variable structure (different days, activities)
- **Fast reads** - Document model allows fetching entire itinerary in one query
- **Easy scaling** - Horizontal scaling with sharding when needed
- **JSON-native** - Natural fit for API responses and Gemini outputs

**Collections:**
```
users
├── _id
├── email
├── password_hash
├── created_at
└── preferences (optional saved defaults)

itineraries
├── _id
├── user_id
├── title
├── youtube_urls[]
├── user_preferences{}
├── generated_content{}
├── created_at
└── updated_at
```

**Research Areas:**
- MongoDB Atlas vs self-hosted on Railway
- Indexing strategies for user queries
- Motor async driver patterns

---

## AI & APIs

### Google Gemini 2.5 Flash
**Why Gemini 2.5 Flash:**
- **Grounding with Google Search** - Real-time, accurate information
- **Grounding with Google Maps** - Place details, reviews, scam warnings
- **Cost-effective** - Optimized for high-volume, low-latency
- **Long context** - 1M tokens input, handles multiple video transcripts

**Integration via:**
- `google-generativeai` Python SDK

**Research Areas:**
- Structured output (JSON mode) for consistent itinerary format
- Grounding API configuration
- Rate limiting and quota management
- Prompt engineering for optimal itinerary generation

### YouTube Transcript Extraction
**Library:** `youtube-transcript-api`
- No API key required
- Extracts auto-generated and manual captions
- Fast and reliable

**Fallback:** If no transcript available, inform user (don't use Gemini audio processing for MVP - too slow/expensive)

---

## Authentication

### JWT (JSON Web Tokens)
**Libraries:**
- `python-jose` - JWT encoding/decoding
- `passlib[bcrypt]` - Password hashing

**Flow:**
1. User logs in with email/password
2. Server validates and returns JWT access token
3. Token stored in HTTP-only cookie or localStorage
4. Token sent with each request in Authorization header
5. Auto-refresh before expiry

**Research Areas:**
- Refresh token rotation strategy
- Secure cookie configuration

---

## Frontend

### Vanilla HTML/CSS/JS
**Why no framework:**
- Simple application with few pages
- Faster initial load
- No build step required
- Easier to serve from FastAPI

**Pages:**
| Page | Purpose |
|------|---------|
| login.html | User authentication |
| dashboard.html | Main interface, input URLs and preferences |
| itinerary.html | View and export generated itinerary |

**Libraries (CDN):**
- **jsPDF** - Core PDF generation
- **html2pdf.js** - HTML to PDF conversion (uses jsPDF + html2canvas)
- **Font Awesome** - Icons (optional)

---

## Deployment

### Railway
**Services:**
1. **Web Service** - FastAPI application
2. **MongoDB** - Database (Railway's MongoDB plugin or MongoDB Atlas)

**Environment Variables:**
```
GEMINI_API_KEY=
MONGODB_URI=
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Research Areas:**
- Railway's MongoDB plugin vs MongoDB Atlas free tier
- Health check endpoints for Railway
- Logging configuration

---

## Development Tools

### Package Management
- `pip` with `requirements.txt`
- Virtual environment (`venv`)

### Code Quality
- Type hints throughout
- Pydantic for validation

### Testing
- `pytest` for unit tests
- `pytest-asyncio` for async tests
- `httpx` for API testing

---

## Dependency Summary

```txt
# requirements.txt

# Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0

# Database
motor>=3.3.0
pymongo>=4.6.0

# AI & APIs
google-generativeai>=0.8.0
youtube-transcript-api>=0.6.0

# Authentication
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4

# Utilities
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
python-multipart>=0.0.6

# Development
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx>=0.26.0
```
