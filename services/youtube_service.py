"""
YouTube Transcript Extraction Service

This service provides functionality to extract transcripts and metadata from YouTube videos
with free proxy rotation support, anti-detection measures, and smart fallback chain.
"""

import re
import asyncio
import random
import time
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

import httpx
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
from pydantic import BaseModel

from config.settings import settings

logger = logging.getLogger(__name__)


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
]


class VideoMetadata(BaseModel):
    """Schema for YouTube video metadata."""
    video_id: str
    title: str
    author_name: str
    author_url: str
    thumbnail_url: Optional[str] = None


class TranscriptSegment(BaseModel):
    """Schema for a single transcript segment."""
    text: str
    start: float
    duration: float


class TranscriptResult(BaseModel):
    """Schema for complete transcript result."""
    video_id: str
    language: str
    language_code: str
    is_generated: bool
    segments: list[TranscriptSegment]
    full_text: str


class VideoProcessingResult(BaseModel):
    """Schema for complete video processing result."""
    metadata: VideoMetadata
    transcript: TranscriptResult


class YouTubeServiceError(Exception):
    """Base exception for YouTube service errors."""
    pass


class InvalidURLError(YouTubeServiceError):
    """Raised when YouTube URL is invalid."""
    pass


class VideoNotFoundError(YouTubeServiceError):
    """Raised when video is not found or unavailable."""
    pass


class TranscriptNotAvailableError(YouTubeServiceError):
    """Raised when transcript is not available."""
    pass


class ProxyError(YouTubeServiceError):
    """Raised when all proxies have failed."""
    pass


class FreeProxy:
    """Represents a free proxy with quality scoring."""
    
    def __init__(self, ip: str, port: str, protocol: str = "http"):
        self.ip = ip
        self.port = port
        self.protocol = protocol
        self.successes = 0
        self.failures = 0
        self.last_used: Optional[datetime] = None
        self.is_blocked = False
        self.block_until: Optional[datetime] = None
        self.response_times: list[float] = []
    
    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.ip}:{self.port}"
    
    @property
    def score(self) -> float:
        """Calculate quality score based on success rate and response time."""
        total = self.successes + self.failures
        if total == 0:
            return 0.5
        
        success_rate = self.successes / total
        avg_response = sum(self.response_times[-10:]) / len(self.response_times[-10:]) if self.response_times else 5.0
        response_score = max(0, 1 - (avg_response / 10))
        
        return (success_rate * 0.7) + (response_score * 0.3)
    
    def record_success(self, response_time: float = 1.0):
        self.successes += 1
        self.last_used = datetime.utcnow()
        self.response_times.append(response_time)
        if len(self.response_times) > 20:
            self.response_times = self.response_times[-20:]
        self.is_blocked = False
        self.block_until = None
    
    def record_failure(self):
        self.failures += 1
        self.last_used = datetime.utcnow()
        
        if self.failures >= 3 and self.successes == 0:
            self.is_blocked = True
            self.block_until = datetime.utcnow() + timedelta(minutes=30)
        elif self.failures >= 5:
            self.is_blocked = True
            self.block_until = datetime.utcnow() + timedelta(minutes=15)
    
    def is_available(self) -> bool:
        if not self.is_blocked:
            return True
        
        if self.block_until and datetime.utcnow() > self.block_until:
            self.is_blocked = False
            self.failures = max(0, self.failures - 2)
            return True
        
        return False


class FreeProxyProvider:
    """Fetches and manages free proxies from ProxyScrape API."""
    
    PROXYSCRAPE_API = "https://api.proxyscrape.com/v2/"
    
    def __init__(self):
        self._proxies: list[FreeProxy] = []
        self._last_refresh: Optional[datetime] = None
        self._refresh_interval = settings.FREE_PROXY_REFRESH_INTERVAL
        self._min_pool_size = settings.FREE_PROXY_MIN_POOL_SIZE
        self._lock = asyncio.Lock()
    
    async def _fetch_proxies_from_api(self) -> list[FreeProxy]:
        """Fetch fresh proxies from ProxyScrape API."""
        proxies = []
        
        params = {
            "request": "displayproxies",
            "protocol": "http",
            "timeout": settings.FREE_PROXY_TIMEOUT_MS,
            "country": "all",
            "ssl": "yes",
            "anonymity": settings.FREE_PROXY_ANONYMITY,
            "format": "json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.PROXYSCRAPE_API, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if isinstance(data, dict) and "proxies" in data:
                        for proxy_data in data["proxies"]:
                            if isinstance(proxy_data, dict):
                                ip = proxy_data.get("ip", "")
                                port = str(proxy_data.get("port", ""))
                                if ip and port:
                                    proxies.append(FreeProxy(ip, port, "http"))
                            elif isinstance(proxy_data, str) and ":" in proxy_data:
                                parts = proxy_data.split(":")
                                if len(parts) == 2:
                                    proxies.append(FreeProxy(parts[0], parts[1], "http"))
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, str) and ":" in item:
                                parts = item.split(":")
                                if len(parts) == 2:
                                    proxies.append(FreeProxy(parts[0], parts[1], "http"))
                    
                    logger.info(f"Fetched {len(proxies)} proxies from ProxyScrape API (JSON)")
        except Exception as e:
            logger.warning(f"Failed to fetch JSON proxies: {e}")
        
        if not proxies:
            try:
                params["format"] = "text"
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(self.PROXYSCRAPE_API, params=params)
                    
                    if response.status_code == 200:
                        lines = response.text.strip().split("\n")
                        for line in lines:
                            line = line.strip()
                            if ":" in line:
                                parts = line.split(":")
                                if len(parts) == 2:
                                    proxies.append(FreeProxy(parts[0], parts[1], "http"))
                        
                        logger.info(f"Fetched {len(proxies)} proxies from ProxyScrape API (text)")
            except Exception as e:
                logger.warning(f"Failed to fetch text proxies: {e}")
        
        return proxies
    
    async def get_proxies(self, count: int = 10) -> list[FreeProxy]:
        """Get available proxies, refreshing if needed."""
        async with self._lock:
            should_refresh = (
                self._last_refresh is None or
                datetime.utcnow() - self._last_refresh > timedelta(seconds=self._refresh_interval) or
                len([p for p in self._proxies if p.is_available()]) < self._min_pool_size
            )
            
            if should_refresh:
                new_proxies = await self._fetch_proxies_from_api()
                if new_proxies:
                    existing_ips = {p.ip for p in self._proxies}
                    for proxy in new_proxies:
                        if proxy.ip not in existing_ips:
                            self._proxies.append(proxy)
                    
                    self._proxies = [p for p in self._proxies if p.is_available() or p.score > 0.3]
                    self._last_refresh = datetime.utcnow()
                    logger.info(f"Proxy pool now contains {len(self._proxies)} proxies")
            
            available = [p for p in self._proxies if p.is_available()]
            available.sort(key=lambda p: p.score, reverse=True)
            
            return available[:count]
    
    def get_proxy_by_url(self, url: str) -> Optional[FreeProxy]:
        """Find a proxy by its URL."""
        for proxy in self._proxies:
            if proxy.url == url:
                return proxy
        return None
    
    def record_success(self, proxy_url: str, response_time: float = 1.0):
        """Record successful request for a proxy."""
        proxy = self.get_proxy_by_url(proxy_url)
        if proxy:
            proxy.record_success(response_time)
    
    def record_failure(self, proxy_url: str):
        """Record failed request for a proxy."""
        proxy = self.get_proxy_by_url(proxy_url)
        if proxy:
            proxy.record_failure()
    
    def get_stats(self) -> dict:
        """Get statistics about the proxy pool."""
        available = [p for p in self._proxies if p.is_available()]
        return {
            "total_proxies": len(self._proxies),
            "available_proxies": len(available),
            "blocked_proxies": len(self._proxies) - len(available),
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None,
            "top_proxies": [
                {"url": p.url, "score": round(p.score, 2), "successes": p.successes, "failures": p.failures}
                for p in sorted(available, key=lambda x: x.score, reverse=True)[:5]
            ]
        }


class ProxyHealth:
    """Tracks health status of a manual proxy."""
    
    def __init__(self, proxy_url: str):
        self.proxy_url = proxy_url
        self.failures = 0
        self.successes = 0
        self.last_failure: Optional[datetime] = None
        self.last_success: Optional[datetime] = None
        self.is_blocked = False
        self.block_until: Optional[datetime] = None
    
    def record_success(self):
        self.successes += 1
        self.last_success = datetime.utcnow()
        self.failures = 0
        self.is_blocked = False
        self.block_until = None
    
    def record_failure(self):
        self.failures += 1
        self.last_failure = datetime.utcnow()
        
        if self.failures >= 3:
            self.is_blocked = True
            self.block_until = datetime.utcnow() + timedelta(minutes=5)
    
    def is_available(self) -> bool:
        if not self.is_blocked:
            return True
        
        if self.block_until and datetime.utcnow() > self.block_until:
            self.is_blocked = False
            self.failures = 0
            return True
        
        return False


class ProxyManager:
    """Manages proxy rotation with support for free and manual proxies."""
    
    def __init__(self, manual_proxy_urls: list[str]):
        self._manual_proxies: dict[str, ProxyHealth] = {}
        for url in manual_proxy_urls:
            self._manual_proxies[url] = ProxyHealth(url)
        
        self._free_proxy_provider = FreeProxyProvider() if settings.USE_FREE_PROXIES else None
        self._current_index = 0
    
    @property
    def has_manual_proxies(self) -> bool:
        return len(self._manual_proxies) > 0
    
    @property
    def has_free_proxies(self) -> bool:
        return self._free_proxy_provider is not None
    
    async def get_free_proxies(self, count: int = 5) -> list[str]:
        """Get free proxy URLs."""
        if not self._free_proxy_provider:
            return []
        
        proxies = await self._free_proxy_provider.get_proxies(count)
        return [p.url for p in proxies]
    
    def get_available_manual_proxies(self) -> list[str]:
        """Get list of currently available manual proxy URLs."""
        return [
            url for url, health in self._manual_proxies.items()
            if health.is_available()
        ]
    
    def get_next_manual_proxy(self) -> Optional[str]:
        """Get next available manual proxy using round-robin."""
        available = self.get_available_manual_proxies()
        
        if not available:
            all_blocked = [h for h in self._manual_proxies.values() if h.is_blocked]
            if all_blocked:
                soonest = min(all_blocked, key=lambda h: h.block_until or datetime.max)
                if soonest.block_until:
                    soonest.is_blocked = False
                    soonest.failures = 0
                    return soonest.proxy_url
            return None
        
        random.shuffle(available)
        return available[0]
    
    def record_manual_success(self, proxy_url: str):
        """Record successful request for a manual proxy."""
        if proxy_url in self._manual_proxies:
            self._manual_proxies[proxy_url].record_success()
    
    def record_manual_failure(self, proxy_url: str):
        """Record failed request for a manual proxy."""
        if proxy_url in self._manual_proxies:
            self._manual_proxies[proxy_url].record_failure()
    
    def record_free_success(self, proxy_url: str, response_time: float = 1.0):
        """Record successful request for a free proxy."""
        if self._free_proxy_provider:
            self._free_proxy_provider.record_success(proxy_url, response_time)
    
    def record_free_failure(self, proxy_url: str):
        """Record failed request for a free proxy."""
        if self._free_proxy_provider:
            self._free_proxy_provider.record_failure(proxy_url)
    
    def get_stats(self) -> dict:
        """Get statistics about all proxies."""
        manual_stats = {
            url: {
                "successes": health.successes,
                "failures": health.failures,
                "is_blocked": health.is_blocked,
                "is_available": health.is_available()
            }
            for url, health in self._manual_proxies.items()
        }
        
        free_stats = self._free_proxy_provider.get_stats() if self._free_proxy_provider else None
        
        return {
            "manual_proxies": manual_stats,
            "free_proxies": free_stats
        }


class YouTubeService:
    """Service for extracting transcripts and metadata from YouTube videos."""
    
    YOUTUBE_URL_PATTERNS = [
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
    ]
    
    OEMBED_URL = "https://www.youtube.com/oembed"
    
    def __init__(self):
        proxy_list = settings.get_proxy_list()
        self._proxy_manager = ProxyManager(proxy_list)
        self._max_retries = settings.YOUTUBE_MAX_RETRIES
        self._timeout = settings.YOUTUBE_PROXY_TIMEOUT
        self._transcript_api = YouTubeTranscriptApi()
        self._delay_min = settings.REQUEST_DELAY_MIN
        self._delay_max = settings.REQUEST_DELAY_MAX
    
    def _get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        return random.choice(USER_AGENTS)
    
    async def _apply_request_delay(self):
        """Apply a random delay to avoid detection."""
        delay = random.uniform(self._delay_min, self._delay_max)
        await asyncio.sleep(delay)
    
    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff delay."""
        base_delay = 2
        max_delay = 30
        jitter = random.uniform(0, 1)
        delay = min(base_delay ** attempt + jitter, max_delay)
        return delay
    
    def _create_transcript_api_with_proxy(self, proxy_url: str) -> YouTubeTranscriptApi:
        """Create a YouTubeTranscriptApi instance configured with a proxy."""
        proxy_config = GenericProxyConfig(
            http_url=proxy_url,
            https_url=proxy_url
        )
        return YouTubeTranscriptApi(proxy_config=proxy_config)
    
    async def extract_video_id(self, url: str) -> str:
        """Extract video ID from various YouTube URL formats."""
        url = url.strip()
        
        for pattern in self.YOUTUBE_URL_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        parsed = urlparse(url)
        if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
            query_params = parse_qs(parsed.query)
            if 'v' in query_params:
                video_id = query_params['v'][0]
                if len(video_id) == 11:
                    return video_id
        
        if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
            return url
        
        raise InvalidURLError(f"Invalid YouTube URL format: {url}")
    
    async def get_video_metadata(self, video_id: str) -> VideoMetadata:
        """Fetch video metadata using YouTube oEmbed API."""
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.OEMBED_URL,
                    params={"url": video_url, "format": "json"},
                    timeout=10.0,
                    headers={"User-Agent": self._get_random_user_agent()}
                )
                
                if response.status_code == 404:
                    raise VideoNotFoundError(f"Video not found: {video_id}")
                
                response.raise_for_status()
                data = response.json()
                
                return VideoMetadata(
                    video_id=video_id,
                    title=data.get("title", "Unknown Title"),
                    author_name=data.get("author_name", "Unknown Author"),
                    author_url=data.get("author_url", ""),
                    thumbnail_url=data.get("thumbnail_url")
                )
                
            except httpx.HTTPStatusError as e:
                raise VideoNotFoundError(f"Video not found or unavailable: {video_id}") from e
            except httpx.RequestError as e:
                raise YouTubeServiceError(f"Network error fetching metadata: {str(e)}") from e
    
    def _fetch_transcript_with_api(
        self,
        api: YouTubeTranscriptApi,
        video_id: str,
        languages: list[str]
    ) -> TranscriptResult:
        """Fetch transcript using a specific API instance."""
        try:
            transcript_list = api.list(video_id)
            
            transcript = None
            try:
                transcript = transcript_list.find_manually_created_transcript(languages)
            except NoTranscriptFound:
                try:
                    transcript = transcript_list.find_generated_transcript(languages)
                except NoTranscriptFound:
                    try:
                        transcript = transcript_list.find_transcript(languages)
                    except NoTranscriptFound:
                        available = list(transcript_list)
                        if available:
                            transcript = available[0]
            
            if transcript is None:
                raise TranscriptNotAvailableError(
                    f"No transcript available for video: {video_id}"
                )
            
            fetched = transcript.fetch()
            
            segments = [
                TranscriptSegment(
                    text=segment.text,
                    start=segment.start,
                    duration=segment.duration
                )
                for segment in fetched
            ]
            
            full_text = " ".join(segment.text for segment in segments)
            
            return TranscriptResult(
                video_id=video_id,
                language=transcript.language,
                language_code=transcript.language_code,
                is_generated=transcript.is_generated,
                segments=segments,
                full_text=full_text
            )
            
        except TranscriptsDisabled:
            raise TranscriptNotAvailableError(
                f"Transcripts are disabled for video: {video_id}"
            )
        except VideoUnavailable:
            raise VideoNotFoundError(f"Video unavailable: {video_id}")
        except NoTranscriptFound:
            raise TranscriptNotAvailableError(
                f"No transcript found for video: {video_id}"
            )
    
    async def _fetch_transcript_sync(
        self, 
        video_id: str, 
        languages: list[str]
    ) -> TranscriptResult:
        """Async method to fetch transcript with fallback chain."""
        
        logger.info(f"Attempting to fetch transcript for video: {video_id}")
        
        try:
            logger.debug("Trying direct request without proxy...")
            result = await asyncio.to_thread(
                self._fetch_transcript_with_api,
                self._transcript_api,
                video_id,
                languages
            )
            logger.info(f"Direct request succeeded for video: {video_id}")
            return result
        except (TranscriptNotAvailableError, VideoNotFoundError):
            raise
        except Exception as e:
            logger.warning(f"Direct request failed: {str(e)}")
        
        if self._proxy_manager.has_free_proxies:
            logger.debug("Trying free proxies...")
            free_proxy_urls = await self._proxy_manager.get_free_proxies(10)
            
            for attempt, proxy_url in enumerate(free_proxy_urls):
                try:
                    await self._apply_request_delay()
                    
                    start_time = time.time()
                    api = self._create_transcript_api_with_proxy(proxy_url)
                    result = await asyncio.to_thread(
                        self._fetch_transcript_with_api,
                        api,
                        video_id,
                        languages
                    )
                    response_time = time.time() - start_time
                    
                    self._proxy_manager.record_free_success(proxy_url, response_time)
                    logger.info(f"Free proxy succeeded: {proxy_url} (took {response_time:.2f}s)")
                    return result
                    
                except (TranscriptNotAvailableError, VideoNotFoundError):
                    self._proxy_manager.record_free_success(proxy_url, 1.0)
                    raise
                    
                except Exception as e:
                    self._proxy_manager.record_free_failure(proxy_url)
                    logger.warning(f"Free proxy {proxy_url} failed: {str(e)}")
                    
                    if attempt < len(free_proxy_urls) - 1:
                        backoff = self._calculate_backoff(attempt)
                        logger.debug(f"Backing off for {backoff:.1f}s before next attempt")
                        await asyncio.sleep(backoff)
        
        if self._proxy_manager.has_manual_proxies:
            logger.debug("Trying manual proxies...")
            retries = 0
            last_error = None
            
            while retries < self._max_retries:
                proxy_url = self._proxy_manager.get_next_manual_proxy()
                
                if proxy_url is None:
                    break
                
                try:
                    await self._apply_request_delay()
                    
                    api = self._create_transcript_api_with_proxy(proxy_url)
                    result = await asyncio.to_thread(
                        self._fetch_transcript_with_api,
                        api,
                        video_id,
                        languages
                    )
                    self._proxy_manager.record_manual_success(proxy_url)
                    logger.info(f"Manual proxy succeeded: {proxy_url}")
                    return result
                    
                except (TranscriptNotAvailableError, VideoNotFoundError):
                    self._proxy_manager.record_manual_success(proxy_url)
                    raise
                    
                except Exception as e:
                    self._proxy_manager.record_manual_failure(proxy_url)
                    last_error = e
                    retries += 1
                    logger.warning(f"Manual proxy {proxy_url} failed: {str(e)}")
                    
                    if retries < self._max_retries:
                        backoff = self._calculate_backoff(retries)
                        await asyncio.sleep(backoff)
        
        raise ProxyError(
            f"All proxy attempts failed for video {video_id}. "
            "The video may be blocked or all proxies are unavailable."
        )
    
    async def get_transcript(
        self, 
        video_id: str, 
        languages: list[str] = None
    ) -> TranscriptResult:
        """Fetch transcript for a video with automatic proxy rotation."""
        if languages is None:
            languages = ['en']
        
        return await self._fetch_transcript_sync(video_id, languages)
    
    async def process_video(
        self, 
        url: str, 
        languages: list[str] = None
    ) -> VideoProcessingResult:
        """Process a YouTube video URL to extract metadata and transcript."""
        video_id = await self.extract_video_id(url)
        
        metadata, transcript = await asyncio.gather(
            self.get_video_metadata(video_id),
            self.get_transcript(video_id, languages)
        )
        
        return VideoProcessingResult(
            metadata=metadata,
            transcript=transcript
        )
    
    async def process_multiple_videos(
        self, 
        urls: list[str], 
        languages: list[str] = None
    ) -> dict[str, VideoProcessingResult | dict]:
        """Process multiple YouTube URLs."""
        results = {}
        
        for url in urls:
            try:
                result = await self.process_video(url, languages)
                results[url] = result
            except YouTubeServiceError as e:
                results[url] = {"error": str(e), "error_type": type(e).__name__}
        
        return results
    
    async def validate_url(self, url: str) -> dict:
        """Validate a YouTube URL and return basic info."""
        try:
            video_id = await self.extract_video_id(url)
            metadata = await self.get_video_metadata(video_id)
            return {
                "valid": True,
                "video_id": video_id,
                "title": metadata.title,
                "author": metadata.author_name
            }
        except InvalidURLError:
            return {"valid": False, "error": "Invalid YouTube URL format"}
        except VideoNotFoundError:
            return {"valid": False, "error": "Video not found or unavailable"}
        except YouTubeServiceError as e:
            return {"valid": False, "error": str(e)}
    
    def get_proxy_stats(self) -> dict:
        """Get current proxy health statistics."""
        return self._proxy_manager.get_stats()


youtube_service = YouTubeService()
