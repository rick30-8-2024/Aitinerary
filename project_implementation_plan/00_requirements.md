# Aitinerary - Requirements Document

## Project Overview
Aitinerary is an AI-powered travel itinerary generator that creates personalized travel plans by analyzing YouTube travel vlogs and combining them with user preferences.

## Core Functionality

### 1. YouTube Video Analysis
- Accept one or multiple YouTube URLs as input
- Extract transcripts from YouTube videos (using `youtube-transcript-api`)
- Analyze transcript content using Gemini 2.5 Flash to identify:
  - Places mentioned
  - Activities shown
  - Local recommendations (food, experiences)
  - Potential warnings/scams mentioned

### 2. AI-Powered Itinerary Generation
- Use Gemini 2.5 Flash with:
  - **Google Search Grounding** - For up-to-date information, pricing, and reviews
  - **Google Maps Grounding** - For place details, opening hours, reviews, and scam warnings
- Combine insights from ALL provided videos into ONE comprehensive itinerary
- Generate day-by-day breakdown with time slots

### 3. User Preferences (Pre-Generation Input)
| Preference | Type | Required | Description |
|------------|------|----------|-------------|
| Budget | Range/Number | Yes | Total trip budget in user's currency |
| Trip Type | Select | Yes | Family / Friends / Solo / Couple |
| Activity Style | Select | Yes | Sporty/Adventure / Relaxing / Mixed |
| Number of Travelers | Number | Yes | How many people traveling |
| Trip Duration | Number | Yes | Number of days for the itinerary |
| Dietary Restrictions | Multi-select | No | Vegetarian, Vegan, Halal, Kosher, Allergies, None |
| Mobility Constraints | Text/Select | No | Wheelchair, Limited walking, Elderly, None |
| Must-Visit Places | Text | No | Specific places from video they want to visit |
| Additional Notes | Text | No | Any other preferences |

### 4. Itinerary Output Structure
Each generated itinerary should include:
- **Day-by-day breakdown** with morning/afternoon/evening slots
- **Place details** (name, brief description, why it's recommended)
- **Estimated costs** per activity/entry
- **Travel time** between locations
- **Local food recommendations** with cuisine type and price range
- **Scam warnings** from Google Maps reviews (if any)
- **Alternative options** (in case of bad weather, closures)

### 5. PDF Export
- Client-side PDF generation using jsPDF + html2pdf.js
- No server load for PDF generation
- Professional, printable itinerary format

## Authentication & Authorization

### Requirements
- User login with email/password
- Auto-login if session is valid (redirect logged-in users from login → dashboard)
- Auto-logout redirect (unauthenticated users from dashboard → login)
- Session management with JWT tokens

### User Data Storage
- MongoDB for user accounts
- Store generated itineraries per user for future access

## Technical Constraints

### Deployment
- **Platform**: Railway
- **Database**: MongoDB (hosted on Railway)
- **Scale**: Start small, designed for high-scale later

### Project Structure
```
Aitinerary/
├── app.py                          # Main FastAPI application
├── api/
│   └── routers/                    # API route handlers
│       ├── auth.py                 # Authentication endpoints
│       ├── itinerary.py            # Itinerary generation endpoints
│       └── user.py                 # User management endpoints
├── page_serving_routers/
│   ├── pages/                      # HTML files
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   └── itinerary.html
│   ├── css/                        # Stylesheets
│   ├── js/                         # JavaScript files
│   └── images/                     # Static images
├── services/                       # Business logic
│   ├── gemini_service.py           # Gemini API integration
│   ├── youtube_service.py          # YouTube transcript extraction
│   └── pdf_service.py              # PDF generation helpers (if needed)
├── models/                         # Pydantic models & DB schemas
├── config/                         # Configuration management
├── .env                            # Environment variables
└── requirements.txt
```

## Non-Functional Requirements

### Performance
- Fast itinerary generation (target: < 30 seconds for basic itinerary)
- Quick page loads
- Efficient database queries with indexing

### Security
- Password hashing (bcrypt)
- JWT token-based authentication
- HTTPS in production
- Input validation and sanitization

### Scalability
- Stateless API design for horizontal scaling
- MongoDB for flexible document storage
- Async operations where possible

## Future Considerations (Out of Scope for MVP)
- Social sharing of itineraries
- Collaborative trip planning
- Integration with booking platforms
- Mobile app
- Multi-language support
