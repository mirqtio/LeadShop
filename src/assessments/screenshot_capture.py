"""
PRP-006: ScreenshotOne Integration
Automated screenshot capture with desktop/mobile viewports and S3 storage
"""

import asyncio
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import quote
import base64
import io

import httpx
from PIL import Image
from pydantic import BaseModel, Field

from src.core.config import settings
from src.models.assessment_cost import AssessmentCost

logger = logging.getLogger(__name__)

# Pydantic Models for Screenshot Data
class ScreenshotMetadata(BaseModel):
    """Screenshot capture metadata."""
    viewport: str = Field(..., description="Viewport type: desktop or mobile")
    width: int = Field(..., description="Screenshot width in pixels")
    height: int = Field(..., description="Screenshot height in pixels")
    file_size_bytes: int = Field(..., description="File size in bytes")
    format: str = Field(..., description="Image format (webp)")
    quality: int = Field(..., description="Image quality percentage")
    capture_timestamp: str = Field(..., description="When screenshot was captured")
    s3_url: Optional[str] = Field(None, description="S3 storage URL")
    signed_url: Optional[str] = Field(None, description="Signed URL for access")
    capture_duration_ms: int = Field(0, description="Time taken to capture")

class ScreenshotResults(BaseModel):
    """Complete screenshot capture results."""
    url: str = Field(..., description="Target website URL")
    success: bool = Field(..., description="Overall capture success")
    desktop_screenshot: Optional[ScreenshotMetadata] = Field(None, description="Desktop screenshot data")
    mobile_screenshot: Optional[ScreenshotMetadata] = Field(None, description="Mobile screenshot data")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    total_duration_ms: int = Field(0, description="Total processing time")
    cost_records: List[Any] = Field(default_factory=list, description="Cost tracking records")
    
    class Config:
        arbitrary_types_allowed = True

class ScreenshotCaptureError(Exception):
    """Custom exception for screenshot capture errors"""
    pass

class ScreenshotOneClient:
    """ScreenshotOne API client with retry logic and optimization."""
    
    BASE_URL = "https://api.screenshotone.com/take"
    COST_PER_SCREENSHOT = 0.20  # $0.002 in cents
    MAX_FILE_SIZE = 500 * 1024  # 500KB
    TIMEOUT = 30  # 30 seconds
    MAX_RETRIES = 3
    
    # Viewport configurations
    DESKTOP_VIEWPORT = {"width": 1920, "height": 1080}
    MOBILE_VIEWPORT = {"width": 390, "height": 844}
    
    def __init__(self):
        self.api_key = settings.SCREENSHOTONE_API_KEY
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)
        
    async def _capture_screenshot(self, url: str, viewport: Dict[str, int], viewport_name: str) -> Optional[ScreenshotMetadata]:
        """Capture a single screenshot with specified viewport."""
        
        if not self.api_key:
            raise ScreenshotCaptureError("ScreenshotOne API key not configured")
        
        start_time = time.time()
        
        # ScreenshotOne API parameters
        params = {
            "access_key": self.api_key,
            "url": url,
            "viewport_width": viewport["width"],
            "viewport_height": viewport["height"],
            "device_scale_factor": 1,
            "format": "webp",
            "image_quality": 85,
            "block_ads": True,
            "block_cookie_banners": True,
            "block_trackers": True,
            "full_page": True,
            "lazy_load_wait": 3000,  # Wait 3s for lazy loading
            "delay": 2000,  # Wait 2s before capture
            "timeout": self.TIMEOUT * 1000  # Convert to milliseconds
        }
        
        # Mobile-specific settings
        if viewport_name == "mobile":
            params.update({
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
                "device_scale_factor": 2,
                "mobile": True,
                "touch": True
            })
        
        try:
            response = await self.client.get(self.BASE_URL, params=params)
            
            if response.status_code == 200:
                # Get image data
                image_data = response.content
                
                # Validate image and get metadata
                try:
                    image = Image.open(io.BytesIO(image_data))
                    actual_width, actual_height = image.size
                    file_size = len(image_data)
                    
                    # Validate file size
                    if file_size > self.MAX_FILE_SIZE:
                        logger.warning(f"Screenshot file size {file_size} bytes exceeds limit {self.MAX_FILE_SIZE}")
                        # Could implement compression here if needed
                    
                    # Validate format
                    if image.format.lower() != 'webp':
                        logger.warning(f"Screenshot format {image.format} is not WebP as expected")
                    
                    duration_ms = int((time.time() - start_time) * 1000)
                    
                    return ScreenshotMetadata(
                        viewport=viewport_name,
                        width=actual_width,
                        height=actual_height,
                        file_size_bytes=file_size,
                        format=image.format.lower(),
                        quality=85,
                        capture_timestamp=datetime.now(timezone.utc).isoformat(),
                        capture_duration_ms=duration_ms
                    )
                    
                except Exception as img_error:
                    logger.error(f"Image validation failed: {img_error}")
                    raise ScreenshotCaptureError(f"Invalid image data received: {img_error}")
                    
            else:
                error_msg = f"ScreenshotOne API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                raise ScreenshotCaptureError(error_msg)
                
        except httpx.TimeoutException:
            logger.error(f"ScreenshotOne API timeout for {url}")
            raise ScreenshotCaptureError("Screenshot capture timed out")
        except Exception as e:
            logger.error(f"ScreenshotOne API request failed: {e}")
            raise ScreenshotCaptureError(f"Screenshot capture failed: {str(e)}")
    
    async def capture_screenshots_with_retry(self, url: str) -> Tuple[Optional[ScreenshotMetadata], Optional[ScreenshotMetadata]]:
        """Capture both desktop and mobile screenshots with retry logic."""
        
        desktop_screenshot = None
        mobile_screenshot = None
        
        # Capture desktop screenshot
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"Capturing desktop screenshot for {url} (attempt {attempt + 1})")
                desktop_screenshot = await self._capture_screenshot(url, self.DESKTOP_VIEWPORT, "desktop")
                break
            except ScreenshotCaptureError as e:
                logger.warning(f"Desktop screenshot attempt {attempt + 1} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    logger.error(f"Desktop screenshot failed after {self.MAX_RETRIES} attempts")
                else:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
        
        # Capture mobile screenshot
        for attempt in range(self.MAX_RETRIES):
            try:
                logger.info(f"Capturing mobile screenshot for {url} (attempt {attempt + 1})")
                mobile_screenshot = await self._capture_screenshot(url, self.MOBILE_VIEWPORT, "mobile")
                break
            except ScreenshotCaptureError as e:
                logger.warning(f"Mobile screenshot attempt {attempt + 1} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    logger.error(f"Mobile screenshot failed after {self.MAX_RETRIES} attempts")
                else:
                    # Exponential backoff
                    await asyncio.sleep(2 ** attempt)
        
        return desktop_screenshot, mobile_screenshot
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

async def capture_website_screenshots(url: str, lead_id: int) -> ScreenshotResults:
    """
    Main entry point for website screenshot capture.
    
    Args:
        url: Target website URL
        lead_id: Database ID of the lead
        
    Returns:
        Complete screenshot capture results with cost tracking
    """
    start_time = time.time()
    cost_records = []
    
    try:
        if not settings.SCREENSHOTONE_API_KEY:
            raise ScreenshotCaptureError("ScreenshotOne API key not configured")
        
        # Create cost tracking records for both screenshots
        desktop_cost = AssessmentCost.create_screenshot_cost(
            lead_id=lead_id,
            cost_cents=ScreenshotOneClient.COST_PER_SCREENSHOT,
            viewport="desktop",
            response_status="pending"
        )
        mobile_cost = AssessmentCost.create_screenshot_cost(
            lead_id=lead_id,
            cost_cents=ScreenshotOneClient.COST_PER_SCREENSHOT,
            viewport="mobile", 
            response_status="pending"
        )
        cost_records.extend([desktop_cost, mobile_cost])
        
        # Initialize screenshot client
        screenshot_client = ScreenshotOneClient()
        
        try:
            # Capture screenshots
            logger.info(f"Starting screenshot capture for: {url}")
            desktop_screenshot, mobile_screenshot = await screenshot_client.capture_screenshots_with_retry(url)
            
            # Update cost records with success/failure
            end_time = time.time()
            total_duration = int((end_time - start_time) * 1000)
            
            if desktop_screenshot:
                desktop_cost.response_status = "success"
                desktop_cost.response_time_ms = desktop_screenshot.capture_duration_ms
            else:
                desktop_cost.response_status = "failed"
                desktop_cost.response_time_ms = total_duration // 2
                desktop_cost.error_message = "Desktop screenshot capture failed"
            
            if mobile_screenshot:
                mobile_cost.response_status = "success"
                mobile_cost.response_time_ms = mobile_screenshot.capture_duration_ms
            else:
                mobile_cost.response_status = "failed"
                mobile_cost.response_time_ms = total_duration // 2
                mobile_cost.error_message = "Mobile screenshot capture failed"
            
            # Determine overall success
            success = desktop_screenshot is not None or mobile_screenshot is not None
            error_message = None
            
            if not success:
                error_message = "Both desktop and mobile screenshot captures failed"
            elif not desktop_screenshot:
                error_message = "Desktop screenshot capture failed"
            elif not mobile_screenshot:
                error_message = "Mobile screenshot capture failed"
            
            logger.info(f"Screenshot capture completed for {url}: desktop={'✅' if desktop_screenshot else '❌'}, mobile={'✅' if mobile_screenshot else '❌'}")
            
            return ScreenshotResults(
                url=url,
                success=success,
                desktop_screenshot=desktop_screenshot,
                mobile_screenshot=mobile_screenshot,
                error_message=error_message,
                total_duration_ms=total_duration,
                cost_records=cost_records
            )
            
        finally:
            await screenshot_client.close()
            
    except ScreenshotCaptureError as e:
        # Update cost records with error
        end_time = time.time()
        total_duration = int((end_time - start_time) * 1000)
        
        for cost_record in cost_records:
            cost_record.response_status = "error"
            cost_record.response_time_ms = total_duration // 2
            cost_record.error_message = str(e)[:500]
        
        logger.error(f"Screenshot capture failed for {url}: {e}")
        
        return ScreenshotResults(
            url=url,
            success=False,
            error_message=str(e),
            total_duration_ms=total_duration,
            cost_records=cost_records
        )
    
    except Exception as e:
        # Update cost records with unexpected error
        end_time = time.time()
        total_duration = int((end_time - start_time) * 1000)
        
        for cost_record in cost_records:
            cost_record.response_status = "error"
            cost_record.response_time_ms = total_duration // 2
            cost_record.error_message = str(e)[:500]
        
        logger.error(f"Unexpected error in screenshot capture for {url}: {e}")
        
        return ScreenshotResults(
            url=url,
            success=False,
            error_message=f"Screenshot capture failed: {str(e)}",
            total_duration_ms=total_duration,
            cost_records=cost_records
        )

# Add create_screenshot_cost method to AssessmentCost model
def create_screenshot_cost_method(cls, lead_id: int, cost_cents: float = 0.20, viewport: str = "desktop", response_status: str = "success", response_time_ms: Optional[int] = None, error_message: Optional[str] = None):
    """
    Create cost record for ScreenshotOne API call.
    
    Args:
        lead_id: ID of the lead being assessed
        cost_cents: Cost in cents (default $0.002)
        viewport: Screenshot viewport (desktop/mobile)
        response_status: success, error, timeout, failed
        response_time_ms: API response time in milliseconds
        error_message: Error message if applicable
        
    Returns:
        AssessmentCost instance
    """
    now = datetime.now(timezone.utc)
    
    return cls(
        lead_id=lead_id,
        service_name="screenshotone",
        api_endpoint=f"https://api.screenshotone.com/take?viewport={viewport}",
        cost_cents=cost_cents,
        currency="USD",
        request_timestamp=now,
        response_status=response_status,
        response_time_ms=response_time_ms,
        api_quota_used=True,  # ScreenshotOne API counts against quota
        rate_limited=False,
        retry_count=0,
        error_message=error_message,
        daily_budget_date=now.strftime("%Y-%m-%d"),
        monthly_budget_date=now.strftime("%Y-%m")
    )

# Monkey patch the method to AssessmentCost
AssessmentCost.create_screenshot_cost = classmethod(create_screenshot_cost_method)