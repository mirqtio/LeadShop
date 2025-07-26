"""
PRP-008: LLM Visual Analysis
GPT-4 Vision API client for professional UX assessment of website screenshots
"""

import asyncio
import logging
import time
import json
import base64
import io
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from urllib.parse import quote

import httpx
from PIL import Image
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import AsyncSessionLocal
from src.models.assessment_cost import AssessmentCost
from src.models.visual_analysis import VisualAnalysis, UXIssue, AnalysisStatus
from src.models.assessment_results import AssessmentResults

logger = logging.getLogger(__name__)

# Pydantic Models for Visual Analysis Data
class UXRubricScore(BaseModel):
    """Individual UX rubric scoring model."""
    name: str = Field(..., description="Rubric name")
    score: int = Field(..., ge=0, le=2, description="Score 0-2 scale")
    explanation: str = Field(..., min_length=20, description="Detailed explanation for score")
    recommendations: List[str] = Field(default_factory=list, description="Specific improvement recommendations")

class VisualAnalysisMetrics(BaseModel):
    """Complete visual analysis result model."""
    rubrics: List[UXRubricScore] = Field(..., description="All 9 UX rubric evaluations")
    overall_ux_score: float = Field(..., ge=0.0, le=2.0, description="Average UX score across all rubrics")
    desktop_analysis: Dict[str, Any] = Field(default_factory=dict, description="Desktop-specific insights")
    mobile_analysis: Dict[str, Any] = Field(default_factory=dict, description="Mobile-specific insights")
    critical_issues: List[str] = Field(default_factory=list, description="High-priority UX issues requiring immediate attention")
    positive_elements: List[str] = Field(default_factory=list, description="Well-executed UX elements to highlight")
    
    # Metadata
    analysis_timestamp: str = Field(..., description="When analysis was performed")
    api_cost_dollars: float = Field(0.0, description="OpenAI API cost for this analysis")
    processing_time_ms: int = Field(0, description="Analysis duration in milliseconds")
    
    @validator('rubrics')
    def validate_rubric_count(cls, v):
        if len(v) != 9:
            raise ValueError("Must evaluate exactly 9 UX rubrics")
        return v

class VisualAnalysisResults(BaseModel):
    """Complete visual analysis assessment results."""
    url: str = Field(..., description="Target website URL")
    success: bool = Field(..., description="Overall analysis success")
    metrics: Optional[VisualAnalysisMetrics] = Field(None, description="Visual analysis metrics data")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    total_duration_ms: int = Field(0, description="Total processing time")
    cost_records: List[Any] = Field(default_factory=list, description="Cost tracking records")
    
    class Config:
        arbitrary_types_allowed = True

class VisualAnalysisError(Exception):
    """Custom exception for visual analysis errors"""
    pass

class VisualAnalyzer:
    """
    GPT-4 Vision API client for professional UX assessment of website screenshots.
    
    Evaluates 9 critical UX rubrics using established Nielsen heuristics framework
    with structured JSON output for automated report generation and scoring.
    """
    
    # OpenAI API Configuration
    MODEL = "gpt-4o-mini"  # Cost-optimized model
    COST_PER_ANALYSIS = 1.0  # $0.01 in cents (target cost optimization)
    TIMEOUT = 30  # 30 seconds
    MAX_RETRIES = 3
    
    # 9 Critical UX Rubrics for Assessment
    UX_RUBRICS = [
        "above_fold_clarity",
        "cta_prominence", 
        "trust_signals_presence",
        "visual_hierarchy",
        "text_readability",
        "brand_cohesion",
        "image_quality",
        "mobile_responsiveness",
        "white_space_balance"
    ]
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)
        
    async def _download_and_validate_image(self, image_url: str, image_type: str) -> str:
        """Download image and convert to base64 for API submission."""
        
        if not image_url:
            raise VisualAnalysisError(f"Missing {image_type} image URL")
        
        try:
            response = await self.client.get(image_url)
            response.raise_for_status()
            
            # Validate image format and size
            image = Image.open(io.BytesIO(response.content))
            
            # Optimize image for API if needed (max 2048x2048)
            if image.size[0] > 2048 or image.size[1] > 2048:
                image.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                
                # Convert back to bytes
                img_buffer = io.BytesIO()
                image.save(img_buffer, format='JPEG', quality=85)
                image_bytes = img_buffer.getvalue()
            else:
                image_bytes = response.content
            
            # Convert to base64
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            logger.info(f"Downloaded and processed {image_type} image: {len(image_bytes)} bytes")
            return base64_image
            
        except Exception as e:
            logger.error(f"Failed to download {image_type} image from {image_url}: {e}")
            raise VisualAnalysisError(f"Failed to download {image_type} image: {str(e)}")
    
    def _create_ux_analysis_prompt(self) -> str:
        """Create structured prompt for UX evaluation based on Nielsen's heuristics."""
        
        return """
Analyze these website screenshots (desktop and mobile) for UX quality assessment. Evaluate each of the 9 critical UX rubrics using a 0-2 scoring scale:

**UX Rubrics to Evaluate:**
1. **Above-fold clarity**: Is the main purpose/value proposition immediately clear?
2. **CTA prominence**: Are call-to-action buttons visually prominent and clear?
3. **Trust signals presence**: Are credibility indicators (testimonials, badges, contact info) visible?
4. **Visual hierarchy**: Is content organized with clear information hierarchy?
5. **Text readability**: Is text legible with proper contrast and sizing?
6. **Brand cohesion**: Is branding consistent and professional throughout?
7. **Image quality**: Are images high-quality, relevant, and properly sized?
8. **Mobile responsiveness**: Does mobile layout work effectively on small screens?
9. **White space balance**: Is spacing used effectively to avoid clutter?

**Scoring Scale:**
- 0: Poor/Major Issues - Significant problems that hurt user experience
- 1: Fair/Minor Issues - Some problems but functional
- 2: Good/Excellent - Meets or exceeds best practices

**Required JSON Output Format:**
```json
{
  "rubrics": [
    {
      "name": "above_fold_clarity",
      "score": 0,
      "explanation": "Detailed explanation of why this score was given with specific visual evidence",
      "recommendations": ["Specific actionable improvement suggestions"]
    },
    {
      "name": "cta_prominence",
      "score": 1,
      "explanation": "Detailed explanation of why this score was given with specific visual evidence",
      "recommendations": ["Specific actionable improvement suggestions"]
    },
    {
      "name": "trust_signals_presence",
      "score": 2,
      "explanation": "Detailed explanation of why this score was given with specific visual evidence",
      "recommendations": ["Specific actionable improvement suggestions"]
    },
    {
      "name": "visual_hierarchy",
      "score": 1,
      "explanation": "Detailed explanation of why this score was given with specific visual evidence",
      "recommendations": ["Specific actionable improvement suggestions"]
    },
    {
      "name": "text_readability",
      "score": 2,
      "explanation": "Detailed explanation of why this score was given with specific visual evidence",
      "recommendations": ["Specific actionable improvement suggestions"]
    },
    {
      "name": "brand_cohesion",
      "score": 1,
      "explanation": "Detailed explanation of why this score was given with specific visual evidence",
      "recommendations": ["Specific actionable improvement suggestions"]
    },
    {
      "name": "image_quality",
      "score": 2,
      "explanation": "Detailed explanation of why this score was given with specific visual evidence",
      "recommendations": ["Specific actionable improvement suggestions"]
    },
    {
      "name": "mobile_responsiveness",
      "score": 1,
      "explanation": "Detailed explanation of why this score was given with specific visual evidence",
      "recommendations": ["Specific actionable improvement suggestions"]
    },
    {
      "name": "white_space_balance",
      "score": 2,
      "explanation": "Detailed explanation of why this score was given with specific visual evidence",
      "recommendations": ["Specific actionable improvement suggestions"]
    }
  ],
  "overall_ux_score": 1.33,
  "desktop_analysis": {
    "strengths": ["Key UX strengths in desktop layout"],
    "weaknesses": ["Key UX issues in desktop layout"],
    "layout_effectiveness": "Overall desktop layout assessment"
  },
  "mobile_analysis": {
    "strengths": ["Key UX strengths in mobile layout"],
    "weaknesses": ["Key UX issues in mobile layout"], 
    "responsive_quality": "Mobile responsiveness assessment"
  },
  "critical_issues": ["High-priority UX problems requiring immediate attention"],
  "positive_elements": ["Well-executed UX elements worth highlighting"]
}
```

Base your evaluation on Nielsen's 10 Usability Heuristics and modern UX best practices. Provide specific, actionable feedback that would help improve the user experience.
"""

    async def _execute_vision_analysis(self, prompt: str, desktop_image: str, mobile_image: str) -> Dict[str, Any]:
        """Execute GPT-4 Vision API call with error handling and retry logic."""
        
        if not self.api_key:
            raise VisualAnalysisError("OpenAI API key not configured")
        
        max_retries = self.MAX_RETRIES
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = await self.client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.MODEL,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": prompt},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{desktop_image}",
                                            "detail": "high"
                                        }
                                    },
                                    {
                                        "type": "image_url", 
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{mobile_image}",
                                            "detail": "high"
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.1  # Low temperature for consistent analysis
                    },
                    timeout=self.TIMEOUT
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    logger.warning("OpenAI API rate limit hit")
                    raise VisualAnalysisError("API rate limit exceeded")
                else:
                    logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                    raise VisualAnalysisError(f"API request failed: {response.status_code}")
                    
            except httpx.TimeoutException:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    logger.warning(f"Vision API timeout, retrying in {wait_time}s (attempt {retry_count + 1})")
                    await asyncio.sleep(wait_time)
                else:
                    raise VisualAnalysisError(f"Vision API request timed out after {max_retries} attempts")
                    
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    logger.warning(f"Vision API error: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise VisualAnalysisError(f"Vision API request failed: {str(e)}")
    
    def _parse_vision_response(self, response: Dict[str, Any]) -> VisualAnalysisMetrics:
        """Parse and validate GPT-4 Vision response into structured format."""
        
        try:
            # Extract content from OpenAI response
            content = response["choices"][0]["message"]["content"]
            
            # Parse JSON from response
            # Look for JSON block in markdown if present
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                json_content = content[json_start:json_end].strip()
            else:
                # Try to parse entire content as JSON
                json_content = content.strip()
            
            parsed_data = json.loads(json_content)
            
            # Convert rubrics to proper models
            rubrics = []
            for rubric_data in parsed_data.get("rubrics", []):
                rubrics.append(UXRubricScore(**rubric_data))
            
            # Calculate overall UX score if not provided
            overall_ux_score = parsed_data.get("overall_ux_score")
            if overall_ux_score is None and rubrics:
                total_score = sum(rubric.score for rubric in rubrics)
                overall_ux_score = round(total_score / len(rubrics), 2)
            
            # Calculate API cost
            usage = response.get("usage", {})
            api_cost = self._calculate_api_cost(usage)
            
            metrics = VisualAnalysisMetrics(
                rubrics=rubrics,
                overall_ux_score=overall_ux_score or 0.0,
                desktop_analysis=parsed_data.get("desktop_analysis", {}),
                mobile_analysis=parsed_data.get("mobile_analysis", {}),
                critical_issues=parsed_data.get("critical_issues", []),
                positive_elements=parsed_data.get("positive_elements", []),
                analysis_timestamp=datetime.now(timezone.utc).isoformat(),
                api_cost_dollars=api_cost,
                processing_time_ms=0  # Will be set by caller
            )
            
            return metrics
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response content: {content}")
            raise VisualAnalysisError(f"Invalid JSON in vision response: {str(e)}")
            
        except Exception as e:
            logger.error(f"Failed to parse vision response: {e}")
            raise VisualAnalysisError(f"Response parsing failed: {str(e)}")
    
    def _calculate_api_cost(self, usage: Dict[str, Any]) -> float:
        """Calculate approximate API cost based on token usage."""
        
        try:
            # GPT-4o-mini pricing (2024)
            input_cost_per_token = 0.15 / 1_000_000  # $0.15 per 1M input tokens
            output_cost_per_token = 0.60 / 1_000_000  # $0.60 per 1M output tokens
            
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            
            total_cost = (input_tokens * input_cost_per_token) + (output_tokens * output_cost_per_token)
            
            return round(total_cost, 4)
            
        except Exception as e:
            logger.warning(f"Could not calculate API cost: {e}")
            return 0.01  # Return estimate if calculation fails
    
    async def analyze_screenshots(self, desktop_url: str, mobile_url: str) -> VisualAnalysisMetrics:
        """
        Analyze desktop and mobile screenshots for UX assessment.
        
        Args:
            desktop_url: URL to desktop screenshot (1920x1080)
            mobile_url: URL to mobile screenshot (390x844)
            
        Returns:
            VisualAnalysisMetrics: Complete UX analysis with structured rubric scoring
        """
        start_time = time.time()
        
        try:
            # Download and validate screenshots
            desktop_image = await self._download_and_validate_image(desktop_url, "desktop")
            mobile_image = await self._download_and_validate_image(mobile_url, "mobile")
            
            # Generate structured UX analysis prompt
            analysis_prompt = self._create_ux_analysis_prompt()
            
            # Execute GPT-4 Vision analysis
            response = await self._execute_vision_analysis(
                prompt=analysis_prompt,
                desktop_image=desktop_image,
                mobile_image=mobile_image
            )
            
            # Parse and validate response
            metrics = self._parse_vision_response(response)
            
            # Set processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            metrics.processing_time_ms = processing_time_ms
            
            # Validate cost optimization target
            if metrics.api_cost_dollars > self.COST_PER_ANALYSIS / 100 * 1.5:  # 1.5x tolerance
                logger.warning(f"Analysis cost ${metrics.api_cost_dollars:.4f} exceeds target ${self.COST_PER_ANALYSIS/100:.4f}")
            
            logger.info(f"Visual analysis completed: {metrics.overall_ux_score:.2f} UX score, ${metrics.api_cost_dollars:.4f} cost, {processing_time_ms}ms")
            return metrics
            
        except Exception as e:
            logger.error(f"Visual analysis failed: {e}")
            raise VisualAnalysisError(f"Visual analysis failed: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

async def save_visual_analysis_to_db(
    db: AsyncSession,
    assessment_id: int,
    screenshot_id: int,
    metrics: VisualAnalysisMetrics,
    url: str
) -> None:
    """
    Save visual analysis results to the database.
    
    Args:
        db: Database session
        assessment_id: ID of the assessment
        screenshot_id: ID of the screenshot analyzed
        metrics: Visual analysis metrics to save
        url: URL that was analyzed
    """
    try:
        # Create VisualAnalysis record
        visual_analysis = VisualAnalysis(
            assessment_id=assessment_id,
            screenshot_id=screenshot_id,
            analysis_timestamp=datetime.fromisoformat(metrics.analysis_timestamp),
            analysis_duration_ms=metrics.processing_time_ms,
            analyzer_version=VisualAnalyzer.MODEL,
            
            # Calculate overall scores from rubrics (convert 0-2 scale to 0-100)
            design_score=int(metrics.overall_ux_score * 50),  # Convert 0-2 to 0-100
            usability_score=int(metrics.overall_ux_score * 50),
            
            # Extract specific rubric scores
            visual_hierarchy_score=next(
                (r.score * 50 for r in metrics.rubrics if r.name == "visual_hierarchy"),
                None
            ),
            whitespace_usage_score=next(
                (r.score * 50 for r in metrics.rubrics if r.name == "white_space_balance"),
                None
            ),
            readability_score=next(
                (r.score * 50 for r in metrics.rubrics if r.name == "text_readability"),
                None
            ),
            cta_effectiveness_score=next(
                (r.score * 50 for r in metrics.rubrics if r.name == "cta_prominence"),
                None
            ),
            mobile_friendliness_score=next(
                (r.score * 50 for r in metrics.rubrics if r.name == "mobile_responsiveness"),
                None
            ),
            brand_consistency_score=next(
                (r.score * 50 for r in metrics.rubrics if r.name == "brand_cohesion"),
                None
            ),
            trust_score=next(
                (r.score * 50 for r in metrics.rubrics if r.name == "trust_signals_presence"),
                None
            ),
            
            # Store analysis insights
            strengths=metrics.positive_elements,
            weaknesses=metrics.critical_issues,
            desktop_analysis=metrics.desktop_analysis,
            mobile_analysis=metrics.mobile_analysis,
            
            # Store AI recommendations
            ai_recommendations=[
                {
                    "rubric": rubric.name,
                    "score": rubric.score,
                    "explanation": rubric.explanation,
                    "recommendations": rubric.recommendations
                }
                for rubric in metrics.rubrics
            ],
            
            # Status and cost
            status=AnalysisStatus.COMPLETED,
            analysis_cost_cents=metrics.api_cost_dollars * 100,  # Convert dollars to cents
            
            # Store raw data for future reference
            raw_analysis_data={
                "rubrics": [r.dict() for r in metrics.rubrics],
                "overall_ux_score": metrics.overall_ux_score,
                "desktop_analysis": metrics.desktop_analysis,
                "mobile_analysis": metrics.mobile_analysis,
                "critical_issues": metrics.critical_issues,
                "positive_elements": metrics.positive_elements
            }
        )
        
        db.add(visual_analysis)
        await db.flush()  # Get the ID for foreign key relationships
        
        # Create UXIssue records for critical issues
        for idx, issue in enumerate(metrics.critical_issues):
            ux_issue = UXIssue(
                visual_analysis_id=visual_analysis.id,
                issue_type="critical",
                issue_code=f"CRIT_{idx + 1}",
                title=issue[:255],  # Truncate if needed
                description=issue,
                severity="high",
                impact_score=80.0,  # High impact for critical issues
                affects_mobile=True,
                affects_desktop=True,
                recommendation="Address this critical issue to improve user experience"
            )
            db.add(ux_issue)
        
        # Create UXIssue records for low-scoring rubrics
        for rubric in metrics.rubrics:
            if rubric.score == 0:  # Poor score
                ux_issue = UXIssue(
                    visual_analysis_id=visual_analysis.id,
                    issue_type=rubric.name,
                    issue_code=rubric.name.upper(),
                    title=f"Poor {rubric.name.replace('_', ' ').title()}",
                    description=rubric.explanation,
                    severity="critical",
                    impact_score=90.0,
                    affects_mobile="mobile" in rubric.name or True,
                    affects_desktop=True,
                    recommendation="; ".join(rubric.recommendations) if rubric.recommendations else None
                )
                db.add(ux_issue)
            elif rubric.score == 1:  # Fair score
                ux_issue = UXIssue(
                    visual_analysis_id=visual_analysis.id,
                    issue_type=rubric.name,
                    issue_code=rubric.name.upper(),
                    title=f"Improve {rubric.name.replace('_', ' ').title()}",
                    description=rubric.explanation,
                    severity="medium",
                    impact_score=50.0,
                    affects_mobile="mobile" in rubric.name or True,
                    affects_desktop=True,
                    recommendation="; ".join(rubric.recommendations) if rubric.recommendations else None
                )
                db.add(ux_issue)
        
        # Update AssessmentResults table with visual rubric scores
        from sqlalchemy import select
        stmt = select(AssessmentResults).where(AssessmentResults.assessment_id == assessment_id)
        result = await db.execute(stmt)
        assessment_result = result.scalar_one_or_none()
        if assessment_result:
            # Map rubric names to database columns
            rubric_mapping = {
                "above_fold_clarity": "visual_above_fold_clarity",
                "cta_prominence": "visual_cta_prominence",
                "trust_signals_presence": "visual_trust_signals",
                "visual_hierarchy": "visual_hierarchy_contrast",
                "text_readability": "visual_text_readability",
                "brand_cohesion": "visual_brand_cohesion",
                "image_quality": "visual_image_quality",
                "mobile_responsiveness": "visual_mobile_responsive",
                "white_space_balance": "visual_clutter_balance"
            }
            
            for rubric in metrics.rubrics:
                if rubric.name in rubric_mapping:
                    setattr(assessment_result, rubric_mapping[rubric.name], rubric.score)
            
            # Also update the overall UX score (converted to 0-100 scale)
            assessment_result.visual_performance_score = int(metrics.overall_ux_score * 50)
        
        await db.commit()
        logger.info(f"Successfully saved visual analysis to database for assessment {assessment_id}")
        
    except Exception as e:
        logger.error(f"Failed to save visual analysis to database: {e}")
        await db.rollback()
        raise

async def assess_visual_analysis(
    url: str, 
    desktop_screenshot_url: str, 
    mobile_screenshot_url: str, 
    lead_id: int,
    assessment_id: Optional[int] = None,
    screenshot_id: Optional[int] = None
) -> VisualAnalysisResults:
    """
    Main entry point for visual UX analysis assessment.
    
    Args:
        url: Target website URL
        desktop_screenshot_url: Desktop screenshot URL from PRP-006
        mobile_screenshot_url: Mobile screenshot URL from PRP-006
        lead_id: Database ID of the lead
        assessment_id: Optional assessment ID for database persistence
        screenshot_id: Optional screenshot ID for database persistence
        
    Returns:
        Complete visual analysis assessment results with cost tracking
    """
    start_time = time.time()
    cost_records = []
    
    try:
        if not settings.OPENAI_API_KEY:
            raise VisualAnalysisError("OpenAI API key not configured")
        
        # Create cost tracking record
        cost_record = AssessmentCost.create_visual_cost(
            lead_id=lead_id,
            cost_cents=VisualAnalyzer.COST_PER_ANALYSIS,
            response_status="pending"
        )
        cost_records.append(cost_record)
        
        # Initialize visual analyzer
        visual_analyzer = VisualAnalyzer()
        
        try:
            # Perform visual analysis
            logger.info(f"Starting visual analysis for: {url}")
            metrics = await visual_analyzer.analyze_screenshots(desktop_screenshot_url, mobile_screenshot_url)
            
            # Update cost record with success
            end_time = time.time()
            cost_record.response_status = "success"
            cost_record.response_time_ms = int((end_time - start_time) * 1000)
            
            # Save to database if assessment_id is provided
            if assessment_id and screenshot_id:
                async with AsyncSessionLocal() as db:
                    await save_visual_analysis_to_db(
                        db=db,
                        assessment_id=assessment_id,
                        screenshot_id=screenshot_id,
                        metrics=metrics,
                        url=url
                    )
            
            logger.info(f"Visual analysis completed for {url}: {metrics.overall_ux_score:.2f} UX score, {len(metrics.rubrics)} rubrics")
            
            return VisualAnalysisResults(
                url=url,
                success=True,
                metrics=metrics,
                total_duration_ms=int((end_time - start_time) * 1000),
                cost_records=[]  # Exclude SQLAlchemy objects to avoid serialization issues
            )
            
        finally:
            await visual_analyzer.close()
            
    except VisualAnalysisError as e:
        # Update cost record with error
        end_time = time.time()
        cost_record.response_status = "error"
        cost_record.response_time_ms = int((end_time - start_time) * 1000)
        cost_record.error_message = str(e)[:500]
        
        logger.error(f"Visual analysis failed for {url}: {e}")
        
        return VisualAnalysisResults(
            url=url,
            success=False,
            error_message=str(e),
            total_duration_ms=int((end_time - start_time) * 1000),
            cost_records=[]  # Exclude SQLAlchemy objects to avoid serialization issues
        )
    
    except Exception as e:
        # Update cost record with unexpected error
        end_time = time.time()
        if cost_records:
            cost_record.response_status = "error"
            cost_record.response_time_ms = int((end_time - start_time) * 1000)
            cost_record.error_message = str(e)[:500]
        
        logger.error(f"Unexpected error in visual analysis for {url}: {e}")
        
        return VisualAnalysisResults(
            url=url,
            success=False,
            error_message=f"Visual analysis failed: {str(e)}",
            total_duration_ms=int((end_time - start_time) * 1000),
            cost_records=[]  # Exclude SQLAlchemy objects to avoid serialization issues
        )

# Add create_visual_cost method to AssessmentCost model
def create_visual_cost_method(cls, lead_id: int, cost_cents: float = 1.0, response_status: str = "success", response_time_ms: Optional[int] = None, error_message: Optional[str] = None):
    """
    Create cost record for visual analysis API call.
    
    Args:
        lead_id: ID of the lead being assessed
        cost_cents: Cost in cents (default $0.01)
        response_status: success, error, timeout, rate_limited
        response_time_ms: API response time in milliseconds
        error_message: Error message if applicable
        
    Returns:
        AssessmentCost instance
    """
    now = datetime.now(timezone.utc)
    
    return cls(
        lead_id=lead_id,
        service_name="openai_vision",
        api_endpoint="https://api.openai.com/v1/chat/completions",
        cost_cents=cost_cents,
        currency="USD",
        request_timestamp=now,
        response_status=response_status,
        response_time_ms=response_time_ms,
        api_quota_used=True,  # OpenAI API counts against quota
        rate_limited=False,
        retry_count=0,
        error_message=error_message,
        daily_budget_date=now.strftime("%Y-%m-%d"),
        monthly_budget_date=now.strftime("%Y-%m")
    )

# Monkey patch the method to AssessmentCost
AssessmentCost.create_visual_cost = classmethod(create_visual_cost_method)