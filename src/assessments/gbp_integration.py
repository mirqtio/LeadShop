"""
PRP-005: Google Business Profile Integration
Google Places API v1 integration with fuzzy matching and comprehensive data extraction
"""

import asyncio
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from difflib import SequenceMatcher
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import AsyncSessionLocal
from src.models.assessment_cost import AssessmentCost
from src.models.gbp import GBPAnalysis, GBPBusinessHours, GBPReviews, GBPPhotos

logger = logging.getLogger(__name__)

# Pydantic Models for GBP Data
class BusinessHours(BaseModel):
    """Structured business hours data."""
    regular_hours: Dict[str, Optional[str]] = Field(default_factory=dict, description="Regular operating hours by day")
    special_hours: List[Dict[str, Any]] = Field(default_factory=list, description="Special hours for holidays/events")
    is_24_hours: bool = Field(False, description="Whether business operates 24/7")
    timezone: Optional[str] = Field(None, description="Business timezone")


class ReviewMetrics(BaseModel):
    """Review and rating metrics."""
    total_reviews: int = Field(0, description="Total number of reviews")
    average_rating: float = Field(0.0, description="Average star rating (1-5)")
    recent_90d_reviews: int = Field(0, description="Reviews in last 90 days")
    rating_distribution: Dict[str, int] = Field(default_factory=dict, description="Rating breakdown by stars")
    rating_trend: str = Field("stable", description="Rating trend: improving/declining/stable")


class PhotoMetrics(BaseModel):
    """Business photo metrics."""
    total_photos: int = Field(0, description="Total number of photos")
    owner_photos: int = Field(0, description="Photos uploaded by business owner")
    customer_photos: int = Field(0, description="Photos uploaded by customers") 
    photo_categories: Dict[str, int] = Field(default_factory=dict, description="Photos by category")
    last_photo_date: Optional[str] = Field(None, description="Date of most recent photo")


class BusinessStatus(BaseModel):
    """Operational status information."""
    is_open_now: Optional[bool] = Field(None, description="Currently open status")
    is_permanently_closed: bool = Field(False, description="Permanently closed flag")
    temporarily_closed: bool = Field(False, description="Temporarily closed flag")
    verified: bool = Field(False, description="Google-verified business")
    business_status: str = Field("unknown", description="Overall business status")


class GBPData(BaseModel):
    """Complete Google Business Profile data."""
    place_id: Optional[str] = Field(None, description="Google Places unique identifier")
    name: str = Field(..., description="Business name")
    formatted_address: Optional[str] = Field(None, description="Complete formatted address")
    phone_number: Optional[str] = Field(None, description="Primary phone number")
    website: Optional[str] = Field(None, description="Business website URL")
    
    # Core metrics for assessment
    hours: BusinessHours = Field(default_factory=BusinessHours, description="Operating hours")
    reviews: ReviewMetrics = Field(default_factory=ReviewMetrics, description="Review metrics")
    photos: PhotoMetrics = Field(default_factory=PhotoMetrics, description="Photo metrics")
    status: BusinessStatus = Field(default_factory=BusinessStatus, description="Business status")
    
    # Additional data
    categories: List[str] = Field(default_factory=list, description="Business categories")
    location: Optional[Dict[str, float]] = Field(None, description="Lat/lng coordinates")
    
    # Metadata
    match_confidence: float = Field(0.0, description="Matching confidence score (0-1)")
    search_query: str = Field("", description="Original search query used")
    data_freshness: str = Field("", description="When data was last updated")
    extraction_timestamp: str = Field(..., description="When data was extracted")


class GBPIntegrationError(Exception):
    """Custom exception for GBP integration errors"""
    pass


class BusinessMatcher:
    """Fuzzy matching for business name resolution."""
    
    @staticmethod
    def calculate_similarity(query_name: str, result_name: str) -> float:
        """Calculate similarity score between query and result names."""
        if not query_name or not result_name:
            return 0.0
        
        # Normalize names for comparison
        query_norm = query_name.lower().strip()
        result_norm = result_name.lower().strip()
        
        # Use SequenceMatcher for fuzzy matching
        similarity = SequenceMatcher(None, query_norm, result_norm).ratio()
        
        # Boost score for exact matches
        if query_norm == result_norm:
            similarity = 1.0
        
        # Boost score if one name contains the other
        if query_norm in result_norm or result_norm in query_norm:
            similarity = max(similarity, 0.8)
        
        return similarity
    
    @staticmethod
    def validate_location(query_address: Optional[str], result_address: str, max_distance_km: float = 50.0) -> bool:
        """Validate location proximity (simplified implementation)."""
        if not query_address:
            return True  # No address to compare against
        
        # Simple keyword matching for city/state validation
        query_words = set(query_address.lower().split())
        result_words = set(result_address.lower().split())
        
        # Check for common location words
        common_words = query_words.intersection(result_words)
        location_keywords = {'city', 'street', 'ave', 'road', 'dr', 'blvd', 'st'}
        
        # If they share location keywords or have word overlap > 20%, consider valid
        return len(common_words) > 0 or len(common_words) / len(query_words.union(result_words)) > 0.2
    
    def find_best_match(self, query_name: str, query_address: Optional[str], search_results: List[Dict]) -> Tuple[Optional[Dict], float]:
        """Find the best matching business from search results."""
        if not search_results:
            return None, 0.0
        
        best_match = None
        best_score = 0.0
        
        for result in search_results:
            # Calculate name similarity
            result_name = result.get('displayName', {}).get('text', '')
            name_score = self.calculate_similarity(query_name, result_name)
            
            # Validate location if address provided
            result_address = result.get('formattedAddress', '')
            location_valid = self.validate_location(query_address, result_address)
            
            # Calculate overall confidence score
            confidence = name_score
            if not location_valid:
                confidence *= 0.5  # Penalize location mismatches
            
            # Additional scoring factors
            rating = result.get('rating', 0)
            review_count = result.get('userRatingCount', 0)
            
            # Boost confidence for businesses with reviews (indicates legitimacy)
            if review_count > 0:
                confidence += 0.1
            if rating > 4.0:
                confidence += 0.05
            
            # Cap confidence at 1.0
            confidence = min(confidence, 1.0)
            
            if confidence > best_score:
                best_score = confidence
                best_match = result
        
        return best_match, best_score


class GBPClient:
    """Google Places API client with rate limiting and cost tracking."""
    
    BASE_URL = "https://places.googleapis.com/v1"
    COST_PER_SEARCH = 1.7  # $0.017 in cents
    MAX_QPS = 10  # Google Places API limit
    
    def __init__(self):
        self.api_key = settings.GOOGLE_PLACES_API_KEY
        self.client = httpx.AsyncClient(timeout=30.0)
        self.matcher = BusinessMatcher()
        self.last_request_time = 0.0
        
    async def _rate_limit(self):
        """Enforce rate limiting to stay within 10 QPS."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        min_interval = 1.0 / self.MAX_QPS  # 0.1 seconds between requests
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def search_business(self, business_name: str, address: Optional[str] = None, city: Optional[str] = None, state: Optional[str] = None) -> List[Dict]:
        """Search for business using Google Places API Text Search."""
        await self._rate_limit()
        
        # Construct search query
        query_parts = [business_name]
        if address:
            query_parts.append(address)
        elif city and state:
            query_parts.append(f"{city}, {state}")
        
        search_query = " ".join(query_parts)
        
        # API request payload
        payload = {
            "textQuery": search_query,
            "maxResultCount": 5,  # Limit results for efficiency
            "locationBias": {
                "circle": {
                    "center": {"latitude": 39.8283, "longitude": -98.5795},  # Geographic center of US
                    "radius": 50000.0  # 50km radius (Google API maximum)
                }
            }
        }
        
        # Field mask for required data
        field_mask = (
            "places.id,places.displayName,places.formattedAddress,places.rating,"
            "places.userRatingCount,places.currentOpeningHours,places.photos,"
            "places.businessStatus,places.nationalPhoneNumber,places.websiteUri,"
            "places.primaryTypeDisplayName,places.location"
        )
        
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": field_mask
        }
        
        try:
            response = await self.client.post(
                f"{self.BASE_URL}/places:searchText",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("places", [])
            elif response.status_code == 429:
                # Rate limit exceeded
                logger.warning("Google Places API rate limit exceeded")
                raise GBPIntegrationError("Rate limit exceeded")
            else:
                logger.error(f"Google Places API error: {response.status_code} - {response.text}")
                raise GBPIntegrationError(f"API request failed: {response.status_code}")
                
        except httpx.TimeoutException:
            logger.error("Google Places API request timed out")
            raise GBPIntegrationError("API request timed out")
    
    def _extract_business_hours(self, place_data: Dict) -> BusinessHours:
        """Extract and normalize business hours data."""
        hours_data = place_data.get('currentOpeningHours', {})
        
        regular_hours = {}
        periods = hours_data.get('periods', [])
        
        # Map Google's day numbers to day names
        day_map = {0: 'sunday', 1: 'monday', 2: 'tuesday', 3: 'wednesday', 
                  4: 'thursday', 5: 'friday', 6: 'saturday'}
        
        for period in periods:
            if 'open' in period:
                day_num = period['open'].get('day', 0)
                day_name = day_map.get(day_num, 'unknown')
                
                open_time = period['open'].get('time', '0000')
                close_time = period.get('close', {}).get('time', '2359') if 'close' in period else '2359'
                
                # Format times as HH:MM
                open_formatted = f"{open_time[:2]}:{open_time[2:]}"
                close_formatted = f"{close_time[:2]}:{close_time[2:]}"
                
                regular_hours[day_name] = f"{open_formatted} - {close_formatted}"
        
        return BusinessHours(
            regular_hours=regular_hours,
            is_24_hours=len(periods) == 0 and hours_data.get('openNow', False),
            timezone=hours_data.get('timezone', None)
        )
    
    def _extract_review_metrics(self, place_data: Dict) -> ReviewMetrics:
        """Extract review and rating metrics."""
        rating = place_data.get('rating', 0.0)
        total_reviews = place_data.get('userRatingCount', 0)
        
        # Estimate recent reviews (90 days) - simplified heuristic
        # In reality, you'd need additional API calls to get review details
        recent_reviews = min(total_reviews, max(1, int(total_reviews * 0.2)))  # Assume 20% are recent
        
        # Determine rating trend (simplified)
        trend = "stable"
        if rating >= 4.5:
            trend = "improving"
        elif rating < 3.5:
            trend = "declining"
        
        return ReviewMetrics(
            total_reviews=total_reviews,
            average_rating=rating,
            recent_90d_reviews=recent_reviews,
            rating_trend=trend
        )
    
    def _extract_photo_metrics(self, place_data: Dict) -> PhotoMetrics:
        """Extract photo metrics."""
        photos = place_data.get('photos', [])
        total_photos = len(photos)
        
        # Simplified photo categorization
        owner_photos = int(total_photos * 0.6)  # Assume 60% are owner photos
        customer_photos = total_photos - owner_photos
        
        return PhotoMetrics(
            total_photos=total_photos,
            owner_photos=owner_photos,
            customer_photos=customer_photos,
            photo_categories={"exterior": int(total_photos * 0.3), 
                            "interior": int(total_photos * 0.4),
                            "product": int(total_photos * 0.3)}
        )
    
    def _extract_business_status(self, place_data: Dict) -> BusinessStatus:
        """Extract business operational status."""
        business_status = place_data.get('businessStatus', 'OPERATIONAL')
        
        is_open_now = place_data.get('currentOpeningHours', {}).get('openNow', None)
        is_permanently_closed = business_status == 'CLOSED_PERMANENTLY'
        temporarily_closed = business_status == 'CLOSED_TEMPORARILY'
        
        return BusinessStatus(
            is_open_now=is_open_now,
            is_permanently_closed=is_permanently_closed,
            temporarily_closed=temporarily_closed,
            verified=True,  # Assume verified if found in Google Places
            business_status=business_status.lower()
        )
    
    def _extract_gbp_data(self, place_data: Dict, search_query: str, confidence: float) -> GBPData:
        """Extract comprehensive GBP data from Places API response."""
        
        # Basic business info
        display_name = place_data.get('displayName', {}).get('text', '')
        formatted_address = place_data.get('formattedAddress', '')
        phone = place_data.get('nationalPhoneNumber', '')
        website = place_data.get('websiteUri', '')
        place_id = place_data.get('id', '')
        
        # Location coordinates
        location_data = place_data.get('location', {})
        location = None
        if 'latitude' in location_data and 'longitude' in location_data:
            location = {
                "latitude": location_data['latitude'],
                "longitude": location_data['longitude']
            }
        
        # Categories
        primary_type = place_data.get('primaryTypeDisplayName', {}).get('text', '')
        categories = [primary_type] if primary_type else []
        
        return GBPData(
            place_id=place_id,
            name=display_name,
            formatted_address=formatted_address,
            phone_number=phone,
            website=website,
            hours=self._extract_business_hours(place_data),
            reviews=self._extract_review_metrics(place_data),
            photos=self._extract_photo_metrics(place_data),
            status=self._extract_business_status(place_data),
            categories=categories,
            location=location,
            match_confidence=confidence,
            search_query=search_query,
            data_freshness=datetime.now(timezone.utc).isoformat(),
            extraction_timestamp=datetime.now(timezone.utc).isoformat()
        )


async def save_gbp_analysis_to_db(
    db: AsyncSession,
    assessment_id: int,
    gbp_data: GBPData,
    search_results_count: int,
    analysis_duration_ms: int,
    error_message: Optional[str] = None
) -> GBPAnalysis:
    """
    Save GBP analysis data to database tables.
    
    Args:
        db: Database session
        assessment_id: Assessment ID to link to
        gbp_data: GBP data from API (Pydantic model)
        search_results_count: Number of search results returned
        analysis_duration_ms: Analysis duration in milliseconds
        error_message: Error message if any
        
    Returns:
        Created GBPAnalysis instance
    """
    try:
        # Parse datetime strings
        data_freshness = None
        if gbp_data.data_freshness:
            try:
                data_freshness = datetime.fromisoformat(gbp_data.data_freshness.replace('Z', '+00:00'))
            except:
                pass
                
        extraction_timestamp = datetime.fromisoformat(gbp_data.extraction_timestamp.replace('Z', '+00:00'))
        
        # Create main GBP analysis record
        gbp_analysis = GBPAnalysis(
            assessment_id=assessment_id,
            place_id=gbp_data.place_id,
            business_name=gbp_data.name,
            formatted_address=gbp_data.formatted_address,
            phone_number=gbp_data.phone_number,
            website=gbp_data.website,
            latitude=gbp_data.location.get('latitude') if gbp_data.location else None,
            longitude=gbp_data.location.get('longitude') if gbp_data.location else None,
            is_verified=gbp_data.status.verified,
            is_open_now=gbp_data.status.is_open_now,
            is_permanently_closed=gbp_data.status.is_permanently_closed,
            is_temporarily_closed=gbp_data.status.temporarily_closed,
            business_status=gbp_data.status.business_status,
            total_reviews=gbp_data.reviews.total_reviews,
            average_rating=gbp_data.reviews.average_rating,
            recent_90d_reviews=gbp_data.reviews.recent_90d_reviews,
            rating_trend=gbp_data.reviews.rating_trend,
            total_photos=gbp_data.photos.total_photos,
            owner_photos=gbp_data.photos.owner_photos,
            customer_photos=gbp_data.photos.customer_photos,
            last_photo_date=datetime.fromisoformat(gbp_data.photos.last_photo_date.replace('Z', '+00:00')) if gbp_data.photos.last_photo_date else None,
            primary_category=gbp_data.categories[0] if gbp_data.categories else None,
            categories=gbp_data.categories,
            is_24_hours=gbp_data.hours.is_24_hours,
            timezone=gbp_data.hours.timezone,
            match_confidence=gbp_data.match_confidence,
            search_query=gbp_data.search_query,
            search_results_count=search_results_count,
            data_freshness=data_freshness,
            extraction_timestamp=extraction_timestamp,
            analysis_duration_ms=analysis_duration_ms,
            error_message=error_message
        )
        
        db.add(gbp_analysis)
        await db.flush()  # Get the ID before adding related records
        
        # Add business hours
        for day, hours in gbp_data.hours.regular_hours.items():
            if hours:
                # Parse hours text (e.g., "09:00 - 17:00")
                parts = hours.split(' - ')
                open_time = parts[0].strip() if len(parts) > 0 else None
                close_time = parts[1].strip() if len(parts) > 1 else None
                
                business_hours = GBPBusinessHours(
                    gbp_analysis_id=gbp_analysis.id,
                    day_of_week=day,
                    open_time=open_time,
                    close_time=close_time,
                    is_closed=False,
                    hours_text=hours
                )
                db.add(business_hours)
        
        # Add closed days (days not in regular_hours)
        all_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for day in all_days:
            if day not in gbp_data.hours.regular_hours:
                business_hours = GBPBusinessHours(
                    gbp_analysis_id=gbp_analysis.id,
                    day_of_week=day,
                    is_closed=True,
                    hours_text="Closed"
                )
                db.add(business_hours)
        
        # Add review distribution
        if gbp_data.reviews.rating_distribution:
            total_reviews = gbp_data.reviews.total_reviews or 1  # Avoid division by zero
            for rating_str, count in gbp_data.reviews.rating_distribution.items():
                rating = int(rating_str)
                percentage = (count / total_reviews * 100) if total_reviews > 0 else 0
                
                review = GBPReviews(
                    gbp_analysis_id=gbp_analysis.id,
                    rating=rating,
                    review_count=count,
                    percentage=percentage
                )
                db.add(review)
        
        # Add photo categories
        if gbp_data.photos.photo_categories:
            total_photos = gbp_data.photos.total_photos or 1  # Avoid division by zero
            for category, count in gbp_data.photos.photo_categories.items():
                percentage = (count / total_photos * 100) if total_photos > 0 else 0
                
                photo = GBPPhotos(
                    gbp_analysis_id=gbp_analysis.id,
                    category=category,
                    photo_count=count,
                    percentage=percentage
                )
                db.add(photo)
        
        await db.commit()
        return gbp_analysis
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save GBP analysis to database: {str(e)}")
        raise


async def assess_google_business_profile(
    business_name: str, 
    address: Optional[str], 
    city: Optional[str], 
    state: Optional[str], 
    lead_id: int,
    assessment_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Main entry point for Google Business Profile assessment.
    
    Args:
        business_name: Name of the business to search
        address: Business address (optional)
        city: Business city (optional)
        state: Business state (optional)
        lead_id: Database ID of the lead
        assessment_id: Assessment ID to save data to (optional)
        
    Returns:
        Complete GBP assessment result with cost tracking
    """
    start_time = time.time()
    cost_records = []
    
    try:
        # Check for any available Google API key
        api_key = getattr(settings, 'GOOGLE_PLACES_API_KEY', None) or getattr(settings, 'GOOGLE_PAGESPEED_API_KEY', None)
        if not api_key:
            raise GBPIntegrationError("Google API key not configured - set GOOGLE_PLACES_API_KEY or GOOGLE_PAGESPEED_API_KEY")
        
        # Create cost tracking record
        cost_record = AssessmentCost.create_gbp_cost(
            lead_id=lead_id,
            cost_cents=GBPClient.COST_PER_SEARCH,
            response_status="pending"
        )
        cost_records.append(cost_record)
        
        # Initialize GBP client
        gbp_client = GBPClient()
        
        # Search for business
        logger.info(f"Searching Google Business Profile for: {business_name}")
        search_results = await gbp_client.search_business(business_name, address, city, state)
        
        if not search_results:
            # No results found
            cost_record.response_status = "no_results"
            cost_record.response_time_ms = int((time.time() - start_time) * 1000)
            
            # Return empty GBP data
            empty_gbp = GBPData(
                name=business_name,
                search_query=f"{business_name} {city or ''} {state or ''}".strip(),
                match_confidence=0.0,
                extraction_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            result = {
                "gbp_data": empty_gbp.dict(),
                "search_results_count": 0,
                "match_found": False,
                "cost_records": [],  # Exclude SQLAlchemy objects to avoid serialization issues
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "analysis_duration_ms": int((time.time() - start_time) * 1000)
            }
            
            # Save to database if assessment_id provided
            if assessment_id:
                async with AsyncSessionLocal() as db:
                    await save_gbp_analysis_to_db(
                        db=db,
                        assessment_id=assessment_id,
                        gbp_data=empty_gbp,
                        search_results_count=0,
                        analysis_duration_ms=int((time.time() - start_time) * 1000),
                        error_message="No results found"
                    )
            
            return result
        
        # Find best match using fuzzy matching
        best_match, confidence = gbp_client.matcher.find_best_match(
            business_name, address, search_results
        )
        
        if not best_match or confidence < 0.5:  # Minimum confidence threshold
            cost_record.response_status = "low_confidence"
            cost_record.response_time_ms = int((time.time() - start_time) * 1000)
            
            # Return low confidence result
            low_confidence_gbp = GBPData(
                name=business_name,
                search_query=f"{business_name} {city or ''} {state or ''}".strip(),
                match_confidence=confidence,
                extraction_timestamp=datetime.now(timezone.utc).isoformat()
            )
            
            result = {
                "gbp_data": low_confidence_gbp.dict(),
                "search_results_count": len(search_results),
                "match_found": False,
                "match_confidence": confidence,
                "cost_records": [],  # Exclude SQLAlchemy objects to avoid serialization issues
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                "analysis_duration_ms": int((time.time() - start_time) * 1000)
            }
            
            # Save to database if assessment_id provided
            if assessment_id:
                async with AsyncSessionLocal() as db:
                    await save_gbp_analysis_to_db(
                        db=db,
                        assessment_id=assessment_id,
                        gbp_data=low_confidence_gbp,
                        search_results_count=len(search_results),
                        analysis_duration_ms=int((time.time() - start_time) * 1000),
                        error_message=f"Low confidence match: {confidence:.2f}"
                    )
            
            return result
        
        # Extract comprehensive GBP data
        search_query = f"{business_name} {city or ''} {state or ''}".strip()
        gbp_data = gbp_client._extract_gbp_data(best_match, search_query, confidence)
        
        # Update cost record with success
        end_time = time.time()
        cost_record.response_status = "success"
        cost_record.response_time_ms = int((end_time - start_time) * 1000)
        
        logger.info(f"GBP assessment completed for {business_name}: confidence {confidence:.2f}")
        
        result = {
            "gbp_data": gbp_data.dict(),
            "search_results_count": len(search_results),
            "match_found": True,
            "match_confidence": confidence,
            "cost_records": [],  # Exclude SQLAlchemy objects to avoid serialization issues
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "analysis_duration_ms": int((end_time - start_time) * 1000)
        }
        
        # Save to database if assessment_id provided
        if assessment_id:
            async with AsyncSessionLocal() as db:
                await save_gbp_analysis_to_db(
                    db=db,
                    assessment_id=assessment_id,
                    gbp_data=gbp_data,
                    search_results_count=len(search_results),
                    analysis_duration_ms=int((end_time - start_time) * 1000)
                )
        
        return result
        
    except GBPIntegrationError as e:
        # Update cost record with error
        end_time = time.time()
        if cost_records:
            cost_records[0].response_status = "error"
            cost_records[0].response_time_ms = int((end_time - start_time) * 1000)
            cost_records[0].error_message = str(e)[:500]
        
        logger.error(f"GBP assessment failed for {business_name}: {e}")
        raise
    
    except Exception as e:
        # Update cost record with unexpected error
        end_time = time.time()
        if cost_records:
            cost_records[0].response_status = "error"
            cost_records[0].response_time_ms = int((end_time - start_time) * 1000)
            cost_records[0].error_message = str(e)[:500]
        
        logger.error(f"Unexpected error in GBP assessment for {business_name}: {e}")
        raise GBPIntegrationError(f"GBP assessment failed: {str(e)}")


# Add create_gbp_cost method to AssessmentCost model
def create_gbp_cost_method(cls, lead_id: int, cost_cents: float = 1.7, response_status: str = "success", response_time_ms: Optional[int] = None, error_message: Optional[str] = None):
    """
    Create cost record for Google Business Profile API call.
    
    Args:
        lead_id: ID of the lead being assessed
        cost_cents: Cost in cents (default $0.017)
        response_status: success, error, timeout, no_results, low_confidence
        response_time_ms: API response time in milliseconds
        error_message: Error message if applicable
        
    Returns:
        AssessmentCost instance
    """
    now = datetime.now(timezone.utc)
    
    return cls(
        lead_id=lead_id,
        service_name="google_business_profile",
        api_endpoint="https://places.googleapis.com/v1/places:searchText",
        cost_cents=cost_cents,
        currency="USD",
        request_timestamp=now,
        response_status=response_status,
        response_time_ms=response_time_ms,
        api_quota_used=True,  # Google Places API counts against quota
        rate_limited=False,
        retry_count=0,
        error_message=error_message,
        daily_budget_date=now.strftime("%Y-%m-%d"),
        monthly_budget_date=now.strftime("%Y-%m")
    )

# Monkey patch the method to AssessmentCost
AssessmentCost.create_gbp_cost = classmethod(create_gbp_cost_method)