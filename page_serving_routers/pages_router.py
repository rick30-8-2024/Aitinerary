"""
Pages Router

Serves HTML pages for the frontend application.
"""

from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse


router = APIRouter(tags=["Pages"])

PAGES_DIR = Path(__file__).parent / "pages"


@router.get("/")
async def root():
    """Serve the landing page."""
    return FileResponse(PAGES_DIR / "landing.html")


@router.get("/login")
async def login_page():
    """Serve the login page."""
    return FileResponse(PAGES_DIR / "login.html")


@router.get("/dashboard")
async def dashboard_page():
    """Serve the dashboard page."""
    return FileResponse(PAGES_DIR / "dashboard.html")


@router.get("/itinerary/{itinerary_id}")
async def itinerary_page(itinerary_id: str):
    """Serve the itinerary view page."""
    return FileResponse(PAGES_DIR / "itinerary.html")


@router.get("/shared/{share_code}")
async def shared_itinerary_page(share_code: str):
    """Serve the shared itinerary view page."""
    return FileResponse(PAGES_DIR / "itinerary.html")


@router.get("/terms")
async def terms_page():
    """Serve the Terms & Conditions page."""
    return FileResponse(PAGES_DIR / "terms.html")


@router.get("/privacy")
async def privacy_page():
    """Serve the Privacy Policy page."""
    return FileResponse(PAGES_DIR / "privacy.html")


@router.get("/refund")
async def refund_page():
    """Serve the Refund Policy page."""
    return FileResponse(PAGES_DIR / "refund.html")
