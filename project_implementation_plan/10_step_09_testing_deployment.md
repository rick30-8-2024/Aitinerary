# Step 9: Testing & Deployment

## Objective
Test the application thoroughly and deploy to Railway.

## Prerequisites
- All previous steps completed
- Railway account set up
- MongoDB Atlas or Railway MongoDB ready

## Implementation Details

### 9.1 Unit Tests

**Test Files Structure:**
```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── test_auth.py             # Authentication tests
├── test_youtube_service.py  # YouTube extraction tests
├── test_gemini_service.py   # AI service tests (mocked)
└── test_itinerary_api.py    # API integration tests
```

**Key Test Cases:**

| Module | Test Case |
|--------|-----------|
| Auth | User registration creates hashed password |
| Auth | Login returns valid JWT |
| Auth | Invalid credentials return 401 |
| Auth | Protected routes reject invalid tokens |
| YouTube | Valid YouTube URLs parsed correctly |
| YouTube | Invalid URLs return appropriate error |
| YouTube | Transcript extraction works (mock) |
| Itinerary | Generation creates record with "generating" status |
| Itinerary | User can only access own itineraries |
| Itinerary | Delete removes itinerary |

### 9.2 Integration Tests

**Test Scenarios:**
1. Full user flow: Register → Login → Generate → View → Export
2. Auth flow: Login → Auto-redirect → Logout → Redirect to login
3. Error handling: Invalid YouTube URL → Appropriate error message

### 9.3 Manual Testing Checklist

**Authentication:**
- [ ] Registration with valid email/password
- [ ] Login with correct credentials
- [ ] Login with wrong password shows error
- [ ] Auto-redirect when already logged in
- [ ] Logout clears session and redirects

**Dashboard:**
- [ ] YouTube URL validation works
- [ ] All preference fields save correctly
- [ ] Generate button triggers API call
- [ ] Progress modal shows status updates
- [ ] Past itineraries load correctly

**Itinerary:**
- [ ] Full itinerary renders correctly
- [ ] Day sections expandable
- [ ] PDF export downloads file
- [ ] PDF formatting is readable

### 9.4 Railway Deployment

**Project Structure for Railway:**
```
Aitinerary/
├── app.py              # Entry point
├── requirements.txt    # Dependencies
├── Procfile           # Optional: web: uvicorn app:app --host 0.0.0.0 --port $PORT
└── railway.toml       # Optional: Railway config
```

**Environment Variables (Railway Dashboard):**
```
GEMINI_API_KEY=your_key
MONGODB_URI=mongodb+srv://...
JWT_SECRET_KEY=generated_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ENVIRONMENT=production
```

**Deployment Steps:**
1. Connect GitHub repository to Railway
2. Add MongoDB plugin OR use MongoDB Atlas URI
3. Set environment variables
4. Deploy and verify health check
5. Configure custom domain (optional)

### 9.5 Production Checklist

**Security:**
- [ ] JWT secret is strong and unique
- [ ] HTTPS enforced
- [ ] CORS configured for production domain
- [ ] Rate limiting on auth endpoints
- [ ] Input validation on all endpoints

**Performance:**
- [ ] MongoDB indexes created
- [ ] Async operations used throughout
- [ ] Static files cached properly

**Monitoring:**
- [ ] Health check endpoint working
- [ ] Error logging configured
- [ ] Railway metrics enabled

### 9.6 Procfile / Start Command
```
web: uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}
```

## Research Areas
- Railway deployment best practices
- MongoDB Atlas connection from Railway
- Production logging setup

## Expected Outcome
- All tests passing
- Application deployed on Railway
- Custom domain configured (optional)
- Production-ready security measures

## Estimated Effort
2-3 days

## Dependencies
- All previous steps
