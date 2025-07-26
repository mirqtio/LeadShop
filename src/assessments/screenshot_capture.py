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
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import AsyncSessionLocal
from src.models.assessment_cost import AssessmentCost
from src.models.screenshot import Screenshot, ScreenshotType, ScreenshotStatus

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
    screenshots: List[Any] = Field(default_factory=list, description="List of screenshot objects for visual analysis")
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
    TIMEOUT = 120  # 120 seconds to allow for ScreenshotOne's 90-second timeout
    MAX_RETRIES = 3
    
    # Viewport configurations - reduced resolution to avoid file size limits
    DESKTOP_VIEWPORT = {"width": 1280, "height": 720}  # 720p instead of 1080p
    MOBILE_VIEWPORT = {"width": 390, "height": 844}  # Keep mobile as is
    
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
            "image_quality": 75,  # Reduced from 85 to help with file size
            "block_ads": True,
            "block_cookie_banners": True,
            "block_trackers": True,
            "full_page": True,  # Capture full page as required
            "delay": 3,  # Reduced from 30 seconds for faster capture
            "timeout": 90,  # Maximum allowed timeout in seconds
            "ignore_host_errors": True  # Continue even if site blocks requests
        }
        
        # Mobile-specific settings
        if viewport_name == "mobile":
            params.update({
                "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
                "device_scale_factor": 2,
                "full_page": False  # Disable full page for mobile to avoid file size issues
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
                    
                    # Store the image data temporarily for potential S3 upload
                    # This will be handled by the orchestrator or a separate upload process
                    metadata = ScreenshotMetadata(
                        viewport=viewport_name,
                        width=actual_width,
                        height=actual_height,
                        file_size_bytes=file_size,
                        format=image.format.lower() if image.format else 'webp',
                        quality=75,  # Updated to match API setting
                        capture_timestamp=datetime.now(timezone.utc).isoformat(),
                        capture_duration_ms=duration_ms
                    )
                    
                    # Store raw image data as a temporary attribute (not in the model)
                    # This allows the caller to handle S3 upload if needed
                    metadata._raw_image_data = image_data
                    
                    # Create a full base64 data URL for visual analysis
                    # In production, this would be the S3 URL
                    metadata.signed_url = f"data:image/webp;base64,{base64.b64encode(image_data).decode('utf-8')}"
                    
                    return metadata
                    
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

async def save_screenshots_to_db(
    assessment_id: int,
    screenshot_results: ScreenshotResults,
    db: AsyncSession
) -> List[Screenshot]:
    """
    Save screenshot data to the database.
    
    Args:
        assessment_id: ID of the assessment
        screenshot_results: Screenshot capture results
        db: Database session
        
    Returns:
        List of created Screenshot objects
    """
    screenshots = []
    
    try:
        # Save desktop screenshot if available
        if screenshot_results.desktop_screenshot:
            desktop_meta = screenshot_results.desktop_screenshot
            
            # Try to upload to S3 if available
            s3_url = desktop_meta.s3_url
            if not s3_url and hasattr(desktop_meta, '_raw_image_data'):
                s3_url = await upload_screenshot_to_s3(desktop_meta, assessment_id, "desktop")
            
            desktop_screenshot = Screenshot(
                assessment_id=assessment_id,
                url=screenshot_results.url,
                screenshot_type=ScreenshotType.DESKTOP,
                viewport_width=1920,
                viewport_height=1080,
                device_scale_factor=1.0,
                is_mobile=False,
                image_url=s3_url or desktop_meta.signed_url,
                image_format=desktop_meta.format,
                image_width=desktop_meta.width,
                image_height=desktop_meta.height,
                file_size_bytes=desktop_meta.file_size_bytes,
                capture_timestamp=datetime.fromisoformat(desktop_meta.capture_timestamp),
                capture_duration_ms=desktop_meta.capture_duration_ms,
                status=ScreenshotStatus.COMPLETED,
                quality_score=desktop_meta.quality,
                is_complete=True,
                has_errors=False,
                metadata={
                    "viewport": desktop_meta.viewport,
                    "quality": desktop_meta.quality,
                    "s3_uploaded": s3_url is not None
                }
            )
            db.add(desktop_screenshot)
            screenshots.append(desktop_screenshot)
            logger.info(f"Saved desktop screenshot for assessment {assessment_id}")
        
        # Save mobile screenshot if available
        if screenshot_results.mobile_screenshot:
            mobile_meta = screenshot_results.mobile_screenshot
            
            # Try to upload to S3 if available
            s3_url = mobile_meta.s3_url
            if not s3_url and hasattr(mobile_meta, '_raw_image_data'):
                s3_url = await upload_screenshot_to_s3(mobile_meta, assessment_id, "mobile")
            
            mobile_screenshot = Screenshot(
                assessment_id=assessment_id,
                url=screenshot_results.url,
                screenshot_type=ScreenshotType.MOBILE,
                viewport_width=390,
                viewport_height=844,
                device_scale_factor=2.0,
                is_mobile=True,
                image_url=s3_url or mobile_meta.signed_url,
                image_format=mobile_meta.format,
                image_width=mobile_meta.width,
                image_height=mobile_meta.height,
                file_size_bytes=mobile_meta.file_size_bytes,
                capture_timestamp=datetime.fromisoformat(mobile_meta.capture_timestamp),
                capture_duration_ms=mobile_meta.capture_duration_ms,
                status=ScreenshotStatus.COMPLETED,
                quality_score=mobile_meta.quality,
                is_complete=True,
                has_errors=False,
                metadata={
                    "viewport": mobile_meta.viewport,
                    "quality": mobile_meta.quality,
                    "s3_uploaded": s3_url is not None
                },
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            )
            db.add(mobile_screenshot)
            screenshots.append(mobile_screenshot)
            logger.info(f"Saved mobile screenshot for assessment {assessment_id}")
        
        # Handle failed screenshots
        if not screenshot_results.success:
            # Create failed screenshot record for tracking
            failed_screenshot = Screenshot(
                assessment_id=assessment_id,
                url=screenshot_results.url,
                screenshot_type=ScreenshotType.DESKTOP,  # Default to desktop
                viewport_width=1920,
                viewport_height=1080,
                device_scale_factor=1.0,
                is_mobile=False,
                status=ScreenshotStatus.FAILED,
                error_message=screenshot_results.error_message,
                processing_attempts=1,
                has_errors=True,
                metadata={
                    "total_duration_ms": screenshot_results.total_duration_ms,
                    "error": screenshot_results.error_message
                }
            )
            db.add(failed_screenshot)
            screenshots.append(failed_screenshot)
            logger.warning(f"Saved failed screenshot record for assessment {assessment_id}")
        
        # Commit all screenshots
        await db.commit()
        
        # Refresh objects to get generated IDs
        for screenshot in screenshots:
            await db.refresh(screenshot)
        
        return screenshots
        
    except Exception as e:
        logger.error(f"Failed to save screenshots to database: {e}")
        await db.rollback()
        raise


async def capture_website_screenshots(url: str, lead_id: int, assessment_id: Optional[int] = None) -> ScreenshotResults:
    """
    Main entry point for website screenshot capture.
    
    Args:
        url: Target website URL
        lead_id: Database ID of the lead
        assessment_id: Optional assessment ID - if provided, screenshots will be saved to database
        
    Returns:
        Complete screenshot capture results with cost tracking
    """
    start_time = time.time()
    cost_records = []
    
    try:
        if not settings.SCREENSHOTONE_API_KEY:
            logger.warning("ScreenshotOne API key not configured - returning mock results")
            # Return mock results for testing when API key is not configured
            return ScreenshotResults(
                url=url,
                success=False,
                desktop_screenshot=None,
                mobile_screenshot=None,
                error_message="ScreenshotOne API key not configured",
                total_duration_ms=0,
                cost_records=[]
            )
        
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
            
            # Build screenshots list for visual analysis
            screenshots_list = []
            if desktop_screenshot:
                # Create a simple dict instead of a type object
                screenshots_list.append({
                    'device_type': 'desktop',
                    'screenshot_url': desktop_screenshot.s3_url or desktop_screenshot.signed_url or ''
                })
            if mobile_screenshot:
                # Create a simple dict instead of a type object
                screenshots_list.append({
                    'device_type': 'mobile',
                    'screenshot_url': mobile_screenshot.s3_url or mobile_screenshot.signed_url or ''
                })
            
            # Create the results object
            results = ScreenshotResults(
                url=url,
                success=success,
                desktop_screenshot=desktop_screenshot,
                mobile_screenshot=mobile_screenshot,
                screenshots=screenshots_list,
                error_message=error_message,
                total_duration_ms=total_duration,
                cost_records=[]  # Exclude SQLAlchemy objects to avoid serialization issues
            )
            
            # Save to database if assessment_id is provided
            if assessment_id is not None:
                try:
                    async with AsyncSessionLocal() as db:
                        saved_screenshots = await save_screenshots_to_db(assessment_id, results, db)
                        logger.info(f"Saved {len(saved_screenshots)} screenshots to database for assessment {assessment_id}")
                except Exception as db_error:
                    logger.error(f"Failed to save screenshots to database: {db_error}")
                    # Don't fail the entire operation if database save fails
                    # The screenshots were captured successfully
            
            return results
            
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
        
        results = ScreenshotResults(
            url=url,
            success=False,
            error_message=str(e),
            total_duration_ms=total_duration,
            cost_records=[]  # Exclude SQLAlchemy objects to avoid serialization issues
        )
        
        # Save failed screenshot record to database if assessment_id is provided
        if assessment_id is not None:
            try:
                async with AsyncSessionLocal() as db:
                    saved_screenshots = await save_screenshots_to_db(assessment_id, results, db)
                    logger.info(f"Saved failed screenshot record to database for assessment {assessment_id}")
            except Exception as db_error:
                logger.error(f"Failed to save screenshot error to database: {db_error}")
        
        return results
    
    except Exception as e:
        # Update cost records with unexpected error
        end_time = time.time()
        total_duration = int((end_time - start_time) * 1000)
        
        for cost_record in cost_records:
            cost_record.response_status = "error"
            cost_record.response_time_ms = total_duration // 2
            cost_record.error_message = str(e)[:500]
        
        logger.error(f"Unexpected error in screenshot capture for {url}: {e}")
        
        results = ScreenshotResults(
            url=url,
            success=False,
            error_message=f"Screenshot capture failed: {str(e)}",
            total_duration_ms=total_duration,
            cost_records=[]  # Exclude SQLAlchemy objects to avoid serialization issues
        )
        
        # Save failed screenshot record to database if assessment_id is provided
        if assessment_id is not None:
            try:
                async with AsyncSessionLocal() as db:
                    saved_screenshots = await save_screenshots_to_db(assessment_id, results, db)
                    logger.info(f"Saved failed screenshot record to database for assessment {assessment_id}")
            except Exception as db_error:
                logger.error(f"Failed to save screenshot error to database: {db_error}")
        
        return results

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


async def upload_screenshot_to_s3(
    screenshot_metadata: ScreenshotMetadata,
    assessment_id: int,
    viewport: str
) -> Optional[str]:
    """
    Upload screenshot image data to S3 if configured.
    
    Args:
        screenshot_metadata: Screenshot metadata with raw image data
        assessment_id: Assessment ID for organizing files
        viewport: Viewport type (desktop/mobile)
        
    Returns:
        S3 URL if uploaded successfully, None otherwise
    """
    try:
        # Check if S3 is configured
        if not settings.AWS_S3_BUCKET_NAME:
            logger.debug("S3 not configured, skipping screenshot upload")
            return None
        
        # Check if we have raw image data
        if not hasattr(screenshot_metadata, '_raw_image_data'):
            logger.warning("No raw image data available for S3 upload")
            return None
        
        # Import S3 client (lazy import to avoid issues if not configured)
        from src.core.storage.s3_client import S3Client
        
        # Generate S3 key
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        s3_key = f"screenshots/assessment_{assessment_id}/{viewport}_{timestamp}.{screenshot_metadata.format}"
        
        # Initialize S3 client and upload
        s3_client = S3Client()
        
        # Upload the image data
        file_url = s3_client.upload_file_object(
            file_obj=io.BytesIO(screenshot_metadata._raw_image_data),
            key=s3_key,
            content_type=f"image/{screenshot_metadata.format}",
            metadata={
                "assessment_id": str(assessment_id),
                "viewport": viewport,
                "width": str(screenshot_metadata.width),
                "height": str(screenshot_metadata.height),
                "capture_timestamp": screenshot_metadata.capture_timestamp
            }
        )
        
        logger.info(f"Successfully uploaded screenshot to S3: {s3_key}")
        return file_url
        
    except Exception as e:
        logger.error(f"Failed to upload screenshot to S3: {e}")
        return None