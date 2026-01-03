"""Main FastAPI application entry point for Aitinerary."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from config.database import database
from api.routers.auth import router as auth_router
from api.routers.youtube import router as youtube_router
from api.routers.itinerary import router as itinerary_router, create_itinerary_indexes
from page_serving_routers.pages_router import router as pages_router
from services.auth_service import create_email_index
from services.gemini_service import gemini_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    await database.connect()
    print(f"Connected to MongoDB: {settings.DATABASE_NAME}")
    await create_email_index()
    await create_itinerary_indexes()
    print("Database indexes created")
    yield
    gemini_service.close()
    print("Gemini service closed")
    await database.disconnect()
    print("Disconnected from MongoDB")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered travel itinerary generator from YouTube videos",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/css", StaticFiles(directory="page_serving_routers/css"), name="css")
app.mount("/js", StaticFiles(directory="page_serving_routers/js"), name="js")
app.mount("/images", StaticFiles(directory="page_serving_routers/images"), name="images")
app.mount("/fonts", StaticFiles(directory="page_serving_routers/fonts"), name="fonts")

app.include_router(auth_router)
app.include_router(youtube_router)
app.include_router(itinerary_router)
app.include_router(pages_router)


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    db_healthy = await database.health_check()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
