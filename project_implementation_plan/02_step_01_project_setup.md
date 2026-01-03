# Step 1: Project Setup & Core Structure

## Objective
Set up the FastAPI project structure, virtual environment, and configuration management.

## Prerequisites
- Python 3.11+ installed
- MongoDB instance available (local or Railway)
- Gemini API key obtained from Google AI Studio

## Implementation Details

### 1.1 Create Project Structure
```
Aitinerary/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── api/
│   ├── __init__.py
│   └── routers/
│       └── __init__.py
├── page_serving_routers/
│   ├── __init__.py
│   ├── pages/
│   ├── css/
│   ├── js/
│   └── images/
├── services/
│   └── __init__.py
├── models/
│   └── __init__.py
└── config/
    └── __init__.py
```

### 1.2 Create Configuration Module (`config/settings.py`)
- Use `pydantic-settings` for environment variable management
- Define settings for:
  - MongoDB connection string
  - Gemini API key
  - JWT secret and algorithm
  - Token expiration times

### 1.3 Create Main Application (`app.py`)
- Initialize FastAPI app with metadata
- Mount static files (css, js, images)
- Include API routers
- Add CORS middleware (for development)
- Create startup/shutdown events for DB connection

### 1.4 Create Database Connection (`config/database.py`)
- Async MongoDB connection using Motor
- Connection pooling
- Health check function

## Research Areas
- FastAPI lifespan events for async startup/shutdown
- Motor connection pool best practices
- Environment variable management with Pydantic Settings

## Expected Outcome
- Running FastAPI application with health check endpoint
- Database connection established on startup
- Static file serving working
- Environment configuration in place

## Estimated Effort
1-2 days

## Dependencies
None (this is the first step)
