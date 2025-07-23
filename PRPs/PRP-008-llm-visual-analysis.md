# PRP-008: LLM Visual Analysis

## Task ID: PRP-008

## Wave: Foundation Services  

## Business Logic

The LeadFactory audit platform requires AI-powered visual analysis of website screenshots to generate professional UX assessments for $399 audit reports. This LLM visual analysis service leverages GPT-4 Vision API to evaluate 9 critical UX rubrics (above-fold clarity, CTA prominence, trust signals, visual hierarchy, text readability, brand cohesion, image quality, mobile responsiveness, white space balance) with structured JSON scoring and actionable insights. The visual analyzer provides competitive advantage through automated professional-grade UX evaluation that supplements technical assessments with user experience insights for comprehensive business assessment reports.

## Overview

Implement GPT-4 Vision API client with structured UX assessment capabilities for:
- Automated evaluation of 9 UX rubrics using 0-2 scoring scale with detailed explanations
- Desktop (1920x1080) and mobile (390x844) screenshot analysis from PRP-006 integration
- Structured JSON output for database storage and report generation consistency
- Cost optimization using GPT-4o-mini at $0.01 per analysis with caching strategies
- Robust error handling for API timeouts, rate limits, and vision model failures
- Nielsen's 10 Heuristics framework integration for professional UX evaluation standards
- Performance monitoring with 30-second timeout limits and exponential backoff retry logic

## Dependencies

- **External**: OpenAI GPT-4 Vision API, image processing libraries, structured prompt engineering
- **Internal**: PRP-006 (ScreenshotOne Integration) for screenshot inputs, PRP-001 (Lead Data Model) for result storage
- **Blockers**: None

## Outcome-Focused Acceptance Criteria

1. **Visual Analyzer Operational**: `VisualAnalyzer().analyze_screenshots(desktop_url, mobile_url)` returns structured JSON with 9 UX rubrics scored 0-2 with explanations
2. **UX Rubrics Complete**: All 9 rubrics evaluated (above-fold clarity, CTA prominence, trust signals, visual hierarchy, text readability, brand cohesion, image quality, mobile responsiveness, white space balance)
3. **Scoring Accuracy Validated**: 0-2 scale scoring with consistent criteria, explanations justify each score with specific visual evidence
4. **Cost Management Effective**: GPT-4o-mini usage keeps analysis cost at $0.01 per lead, token consumption monitored and optimized
5. **JSON Structure Consistent**: Structured output follows schema for database storage, all fields properly typed and validated
6. **Performance Requirements Met**: 30-second timeout enforced, 95% success rate under normal conditions, proper error handling for failures
7. **Screenshot Integration Working**: Desktop and mobile screenshot URLs from PRP-006 processed correctly, handles missing or invalid images gracefully
8. **Database Storage Complete**: Analysis results stored in PostgreSQL via SQLAlchemy models with proper relationships to lead records
9. **Nielsen Framework Applied**: Professional UX evaluation using established heuristics, recommendations aligned with industry standards
10. **Production Deployment Ready**: Retry logic with exponential backoff, rate limiting compliance, monitoring and alerting for API failures

## Integration Points

### Visual Analysis Client (GPT-4 Vision API)
- **Location**: `src/services/visual/analyzer.py`, `src/services/visual/models.py`
- **Dependencies**: OpenAI SDK, Pydantic for response validation, image processing utilities
- **Functions**: analyze_screenshots(), evaluate_ux_rubrics(), generate_recommendations(), handle_vision_errors()

### Celery Task Integration (Assessment Pipeline)
- **Location**: `src/assessment/tasks/visual_analysis_task.py`
- **Dependencies**: Celery, Visual analyzer client, SQLAlchemy models
- **Functions**: visual_analysis_task(), process_visual_metrics(), aggregate_ux_scores()

### Visual Analysis Configuration (API & Prompts)
- **Location**: `src/core/config.py`, `src/services/visual/prompts.py`
- **Dependencies**: OpenAI API key management, structured prompt templates
- **Resources**: API key validation, timeout configuration, prompt versioning

### Database Models (UX Assessment Storage)
- **Location**: `src/models/visual_models.py` (extends PRP-001)
- **Dependencies**: SQLAlchemy, PostgreSQL, JSON field support
- **Integration**: Visual analysis results stored with lead_id foreign key and normalized rubric structure

## Implementation Requirements

### Visual Analysis Client Implementation

**GPT-4 Vision UX Analyzer**:
```python
import asyncio
import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
import openai
import base64
import requests
from PIL import Image
import io
import json

class UXRubricScore(BaseModel):
    """Individual UX rubric scoring model."""
    name: str = Field(description="Rubric name")
    score: int = Field(ge=0, le=2, description="Score 0-2 scale")
    explanation: str = Field(min_length=20, description="Detailed explanation for score")
    recommendations: List[str] = Field(description="Specific improvement recommendations")

class VisualAnalysisResult(BaseModel):
    """Complete visual analysis result model."""
    rubrics: List[UXRubricScore] = Field(description="All 9 UX rubric evaluations")
    overall_ux_score: float = Field(ge=0.0, le=2.0, description="Average UX score across all rubrics")
    desktop_analysis: Dict[str, Any] = Field(description="Desktop-specific insights")
    mobile_analysis: Dict[str, Any] = Field(description="Mobile-specific insights")
    critical_issues: List[str] = Field(description="High-priority UX issues requiring immediate attention")
    positive_elements: List[str] = Field(description="Well-executed UX elements to highlight")
    api_cost: float = Field(ge=0.0, description="OpenAI API cost for this analysis")
    processing_time: float = Field(ge=0.0, description="Analysis duration in seconds")
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)

    @validator('rubrics')
    def validate_rubric_count(cls, v):
        if len(v) != 9:
            raise ValueError("Must evaluate exactly 9 UX rubrics")
        return v

class VisualAnalyzer:
    """
    GPT-4 Vision API client for professional UX assessment of website screenshots.
    
    Evaluates 9 critical UX rubrics using established Nielsen heuristics framework
    with structured JSON output for automated report generation and scoring.
    """
    
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
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", timeout: int = 30):
        """
        Initialize Visual Analyzer with OpenAI API configuration.
        
        Args:
            api_key: OpenAI API key for GPT-4 Vision access
            model: OpenAI model to use (gpt-4o-mini for cost optimization)
            timeout: Request timeout in seconds (default: 30)
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.timeout = timeout
        self.cost_per_analysis = 0.01  # Target cost optimization
        
        # Validate API connection
        self._validate_api_connection()
    
    def _validate_api_connection(self) -> None:
        """Validate OpenAI API connectivity and model access."""
        try:
            # Test basic API connectivity
            models = self.client.models.list()
            available_models = [model.id for model in models.data]
            
            if self.model not in available_models:
                raise ValueError(f"Model {self.model} not available. Available: {available_models}")
                
            logging.info(f"Visual Analyzer initialized with model: {self.model}")
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to OpenAI API: {e}")
    
    async def analyze_screenshots(self, desktop_url: str, mobile_url: str) -> VisualAnalysisResult:
        """
        Analyze desktop and mobile screenshots for UX assessment.
        
        Args:
            desktop_url: URL to desktop screenshot (1920x1080)
            mobile_url: URL to mobile screenshot (390x844)
            
        Returns:
            VisualAnalysisResult: Complete UX analysis with structured rubric scoring
        """
        start_time = datetime.utcnow()
        
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
            analysis_result = self._parse_vision_response(response)
            
            # Calculate processing metrics
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            analysis_result.processing_time = processing_time
            analysis_result.api_cost = self._calculate_api_cost(response)
            
            # Validate cost optimization target
            if analysis_result.api_cost > self.cost_per_analysis * 1.5:
                logging.warning(f"Analysis cost {analysis_result.api_cost} exceeds target {self.cost_per_analysis}")
            
            return analysis_result
            
        except Exception as e:
            logging.error(f"Visual analysis failed: {e}")
            raise
    
    async def _download_and_validate_image(self, image_url: str, image_type: str) -> str:
        """Download image and convert to base64 for API submission."""
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Validate image format and size
            image = Image.open(io.BytesIO(response.content))
            
            # Optimize image for API if needed
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
            
            logging.info(f"Downloaded and processed {image_type} image: {len(image_bytes)} bytes")
            return base64_image
            
        except Exception as e:
            raise ValueError(f"Failed to download {image_type} image from {image_url}: {e}")
    
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
      "score": 0-2,
      "explanation": "Detailed explanation of why this score was given with specific visual evidence",
      "recommendations": ["Specific actionable improvement suggestions"]
    }
    // ... repeat for all 9 rubrics
  ],
  "overall_ux_score": 0.0-2.0,
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

    async def _execute_vision_analysis(self, prompt: str, desktop_image: str, mobile_image: str) -> Any:
        """Execute GPT-4 Vision API call with error handling and retry logic."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                response = await asyncio.wait_for(
                    self._make_vision_request(prompt, desktop_image, mobile_image),
                    timeout=self.timeout
                )
                return response
                
            except asyncio.TimeoutError:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    logging.warning(f"Vision API timeout, retrying in {wait_time}s (attempt {retry_count + 1})")
                    await asyncio.sleep(wait_time)
                else:
                    raise TimeoutError(f"Vision API request timed out after {max_retries} attempts")
                    
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** retry_count
                    logging.warning(f"Vision API error: {e}, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                else:
                    raise
    
    async def _make_vision_request(self, prompt: str, desktop_image: str, mobile_image: str) -> Any:
        """Make actual API request to GPT-4 Vision."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
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
                max_tokens=2000,
                temperature=0.1  # Low temperature for consistent analysis
            )
            
            return response
            
        except Exception as e:
            logging.error(f"OpenAI API request failed: {e}")
            raise
    
    def _parse_vision_response(self, response: Any) -> VisualAnalysisResult:
        """Parse and validate GPT-4 Vision response into structured format."""
        try:
            # Extract content from OpenAI response
            content = response.choices[0].message.content
            
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
            
            # Convert to Pydantic model for validation
            analysis_result = VisualAnalysisResult(**parsed_data)
            
            # Calculate overall UX score
            if analysis_result.rubrics:
                total_score = sum(rubric.score for rubric in analysis_result.rubrics)
                analysis_result.overall_ux_score = round(total_score / len(analysis_result.rubrics), 2)
            
            return analysis_result
            
        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse JSON response: {e}")
            logging.error(f"Response content: {content}")
            raise ValueError(f"Invalid JSON in vision response: {e}")
            
        except Exception as e:
            logging.error(f"Failed to parse vision response: {e}")
            raise
    
    def _calculate_api_cost(self, response: Any) -> float:
        """Calculate approximate API cost based on token usage."""
        try:
            # GPT-4o-mini pricing (2024)
            input_cost_per_token = 0.15 / 1_000_000  # $0.15 per 1M input tokens
            output_cost_per_token = 0.60 / 1_000_000  # $0.60 per 1M output tokens
            
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            
            total_cost = (input_tokens * input_cost_per_token) + (output_tokens * output_cost_per_token)
            
            return round(total_cost, 4)
            
        except Exception as e:
            logging.warning(f"Could not calculate API cost: {e}")
            return 0.01  # Return estimate if calculation fails
```

### Celery Task Integration

**Visual Analysis Task**:
```python
from celery import Task
from typing import Dict, Any
import logging
from datetime import datetime
from src.services.visual.analyzer import VisualAnalyzer, VisualAnalysisResult
from src.models.visual_models import VisualAssessment
from src.core.database import get_db_session
from src.core.config import settings
import asyncio

class VisualAnalysisTask(Task):
    """Celery task for GPT-4 Vision UX analysis with error handling and retry logic."""
    
    autoretry_for = (asyncio.TimeoutError, ConnectionError, ValueError)
    retry_backoff = True
    retry_kwargs = {'max_retries': 3}
    
    def __init__(self):
        self.visual_analyzer = None
    
    def _get_analyzer(self) -> VisualAnalyzer:
        """Initialize Visual Analyzer with lazy loading."""
        if self.visual_analyzer is None:
            self.visual_analyzer = VisualAnalyzer(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_VISION_MODEL,
                timeout=30
            )
        return self.visual_analyzer

@app.task(
    bind=True,
    base=VisualAnalysisTask,
    name='assessment.visual_analysis'
)
def visual_analysis_task(self, lead_id: int) -> Dict[str, Any]:
    """
    Execute GPT-4 Vision UX analysis for lead assessment.
    
    Args:
        lead_id: Database ID of the lead to analyze
        
    Returns:
        Dict containing visual analysis results and task metadata
    """
    try:
        # Get lead and screenshot data from database
        with get_db_session() as db:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                raise ValueError(f"Lead {lead_id} not found")
            
            # Get screenshot URLs from previous assessment
            screenshot_assessment = db.query(ScreenshotAssessment).filter(
                ScreenshotAssessment.lead_id == lead_id
            ).first()
            
            if not screenshot_assessment or not screenshot_assessment.desktop_screenshot_url:
                raise ValueError(f"Screenshots not available for lead {lead_id}")
            
            # Update visual assessment status
            visual_assessment = db.query(VisualAssessment).filter(
                VisualAssessment.lead_id == lead_id
            ).first()
            
            if not visual_assessment:
                visual_assessment = VisualAssessment(
                    lead_id=lead_id,
                    status='in_progress',
                    started_at=datetime.utcnow()
                )
                db.add(visual_assessment)
                db.commit()
            else:
                visual_assessment.status = 'in_progress'
                visual_assessment.started_at = datetime.utcnow()
                db.commit()
        
        # Execute visual analysis
        analyzer = self._get_analyzer()
        
        # Run async analysis in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            analysis_result = loop.run_until_complete(
                analyzer.analyze_screenshots(
                    desktop_url=screenshot_assessment.desktop_screenshot_url,
                    mobile_url=screenshot_assessment.mobile_screenshot_url
                )
            )
        finally:
            loop.close()
        
        # Store results in database
        with get_db_session() as db:
            visual_assessment = db.query(VisualAssessment).filter(
                VisualAssessment.lead_id == lead_id
            ).first()
            
            # Update with analysis results
            visual_assessment.rubric_scores = {
                rubric.name: {
                    "score": rubric.score,
                    "explanation": rubric.explanation,
                    "recommendations": rubric.recommendations
                }
                for rubric in analysis_result.rubrics
            }
            visual_assessment.overall_ux_score = analysis_result.overall_ux_score
            visual_assessment.desktop_analysis = analysis_result.desktop_analysis
            visual_assessment.mobile_analysis = analysis_result.mobile_analysis
            visual_assessment.critical_issues = analysis_result.critical_issues
            visual_assessment.positive_elements = analysis_result.positive_elements
            visual_assessment.api_cost = analysis_result.api_cost
            visual_assessment.processing_time = analysis_result.processing_time
            visual_assessment.status = 'completed'
            visual_assessment.completed_at = datetime.utcnow()
            
            db.commit()
        
        return {
            "lead_id": lead_id,
            "task": "visual_analysis",
            "status": "completed",
            "overall_ux_score": analysis_result.overall_ux_score,
            "rubric_count": len(analysis_result.rubrics),
            "critical_issues_count": len(analysis_result.critical_issues),
            "api_cost": analysis_result.api_cost,
            "processing_time": analysis_result.processing_time,
            "completed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as exc:
        # Log error and update database
        logging.error(f"Visual analysis failed for lead {lead_id}: {exc}")
        
        # Update error status in database
        try:
            with get_db_session() as db:
                visual_assessment = db.query(VisualAssessment).filter(
                    VisualAssessment.lead_id == lead_id
                ).first()
                if visual_assessment:
                    visual_assessment.status = 'failed'
                    visual_assessment.error_message = str(exc)
                    visual_assessment.failed_at = datetime.utcnow()
                    db.commit()
        except Exception as db_error:
            logging.error(f"Failed to update error status for lead {lead_id}: {db_error}")
        
        # Retry with exponential backoff
        if self.request.retries < 3:
            retry_countdown = 2 ** self.request.retries
            logging.info(f"Retrying visual analysis for lead {lead_id} in {retry_countdown}s")
            raise self.retry(countdown=retry_countdown)
        else:
            # Final failure
            raise
```

### Database Models Extension

**Visual Assessment Models**:
```python
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.models.base import BaseModel

class VisualAssessment(BaseModel):
    """Database model for visual UX assessment results from GPT-4 Vision."""
    
    __tablename__ = 'visual_assessments'
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False, index=True)
    
    # UX scoring results (9 rubrics)
    rubric_scores = Column(JSON, nullable=True, comment="Structured scoring for all 9 UX rubrics")
    overall_ux_score = Column(Float, nullable=True, comment="Average UX score 0-2 scale")
    
    # Analysis insights
    desktop_analysis = Column(JSON, nullable=True, comment="Desktop-specific UX insights")
    mobile_analysis = Column(JSON, nullable=True, comment="Mobile-specific UX insights")
    critical_issues = Column(JSON, nullable=True, comment="High-priority UX issues list")
    positive_elements = Column(JSON, nullable=True, comment="Well-executed UX elements")
    
    # Task execution tracking
    status = Column(String(20), default='pending', comment="Task status: pending/in_progress/completed/failed")
    api_cost = Column(Float, nullable=True, comment="OpenAI API cost for analysis")
    processing_time = Column(Float, nullable=True, comment="Analysis duration in seconds")
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    lead = relationship("Lead", back_populates="visual_assessment")
    
    def __repr__(self):
        return f"<VisualAssessment(lead_id={self.lead_id}, ux_score={self.overall_ux_score}, status={self.status})>"
    
    @property
    def is_complete(self) -> bool:
        """Check if all required rubrics are scored."""
        if not self.rubric_scores:
            return False
        
        required_rubrics = [
            "above_fold_clarity", "cta_prominence", "trust_signals_presence",
            "visual_hierarchy", "text_readability", "brand_cohesion",
            "image_quality", "mobile_responsiveness", "white_space_balance"
        ]
        
        return all(rubric in self.rubric_scores for rubric in required_rubrics)
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage based on available rubric scores."""
        if not self.rubric_scores:
            return 0.0
        
        required_rubrics = [
            "above_fold_clarity", "cta_prominence", "trust_signals_presence",
            "visual_hierarchy", "text_readability", "brand_cohesion", 
            "image_quality", "mobile_responsiveness", "white_space_balance"
        ]
        
        completed_rubrics = sum(1 for rubric in required_rubrics if rubric in self.rubric_scores)
        return (completed_rubrics / len(required_rubrics)) * 100
    
    @property
    def performance_score(self) -> str:
        """Return letter grade based on overall UX score."""
        if self.overall_ux_score is None:
            return "N/A"
        elif self.overall_ux_score >= 1.8:
            return "A"
        elif self.overall_ux_score >= 1.5:
            return "B"
        elif self.overall_ux_score >= 1.0:
            return "C"
        elif self.overall_ux_score >= 0.5:
            return "D"
        else:
            return "F"
```

## Tests to Pass

1. **Visual Analyzer Tests**: `pytest tests/test_visual_analyzer.py -v` validates GPT-4 Vision API integration, rubric scoring, and JSON output with ≥90% coverage
2. **UX Rubrics Tests**: `pytest tests/test_ux_rubrics.py -v` validates all 9 rubrics scored consistently, explanations provided, recommendations actionable
3. **Cost Management Tests**: Analysis cost stays within $0.01 target, token usage optimization verified, GPT-4o-mini model cost efficiency validated
4. **Screenshot Integration Tests**: `pytest tests/test_screenshot_analysis.py -v` validates integration with PRP-006 screenshot URLs, image download and processing
5. **JSON Structure Tests**: Structured output validates against Pydantic models, all required fields present, proper data types enforced
6. **Performance Tests**: 30-second timeout enforced, 95% success rate under normal load, retry logic with exponential backoff functional
7. **Celery Task Tests**: `pytest tests/test_visual_task.py -v` validates task execution, error handling, and database integration
8. **Database Integration Tests**: Visual assessment results properly stored in PostgreSQL, foreign key relationships maintained
9. **Error Handling Tests**: API timeouts, rate limits, and vision model failures handled gracefully with proper user feedback
10. **Nielsen Framework Tests**: UX evaluation aligns with established heuristics, professional standards maintained, recommendations follow best practices

## Implementation Guide

### Phase 1: Core Visual Analyzer (Days 1-3)
1. **OpenAI Integration**: Set up GPT-4 Vision API client with authentication and basic image processing
2. **UX Rubrics Framework**: Implement 9 UX rubrics evaluation with 0-2 scoring scale and structured output
3. **Prompt Engineering**: Develop structured prompts based on Nielsen's heuristics for consistent analysis
4. **Response Validation**: Add Pydantic models for response validation and data structure consistency
5. **Cost Optimization**: Implement GPT-4o-mini usage and token monitoring for $0.01 target cost

### Phase 2: Screenshot Integration (Days 4-6)
1. **Image Processing**: Implement screenshot download, validation, and optimization for API submission
2. **PRP-006 Integration**: Connect with ScreenshotOne integration for desktop and mobile screenshot inputs
3. **Error Handling**: Add robust error handling for image download failures, format issues, and API errors
4. **Performance Optimization**: Implement async processing and timeout handling for 30-second limits
5. **Retry Logic**: Add exponential backoff retry strategy for transient API failures

### Phase 3: Database & Task Integration (Days 7-9)
1. **Database Models**: Create visual assessment models with JSON field support for rubric storage
2. **Celery Task**: Implement visual_analysis_task with proper error handling and status tracking
3. **Assessment Pipeline**: Connect visual analysis to Assessment Orchestrator from PRP-002
4. **Status Monitoring**: Add real-time status updates and progress tracking for analysis completion
5. **Result Aggregation**: Implement result storage and retrieval for report generation

### Phase 4: Testing & Optimization (Days 10-12)
1. **Unit Testing**: Write comprehensive unit tests for analyzer, rubrics, and task functions
2. **Integration Testing**: Test complete visual analysis pipeline with real screenshots
3. **Performance Testing**: Validate timeout handling, success rates, and cost optimization
4. **Nielsen Compliance**: Verify UX evaluation methodology aligns with professional standards
5. **Production Testing**: Test with GPT-4 Vision API using actual screenshots and validate analysis quality

## Validation Commands

```bash
# Visual analyzer validation
python -c "from src.services.visual.analyzer import VisualAnalyzer; analyzer = VisualAnalyzer('${OPENAI_API_KEY}'); print('Analyzer initialized successfully')"

# Screenshot analysis validation  
python -c "
import asyncio
from src.services.visual.analyzer import VisualAnalyzer
analyzer = VisualAnalyzer('${OPENAI_API_KEY}')
result = asyncio.run(analyzer.analyze_screenshots('desktop_url', 'mobile_url'))
print(f'Analysis complete: {result.overall_ux_score} UX score, {len(result.rubrics)} rubrics')
"

# Celery task validation
python -c "from src.assessment.tasks.visual_analysis_task import visual_analysis_task; result = visual_analysis_task.delay(1); print(result.get())"

# Database integration validation
psql -h localhost -U leadfactory -d leadfactory -c "SELECT lead_id, overall_ux_score, status FROM visual_assessments WHERE status='completed' LIMIT 5;"

# Cost tracking validation
python -c "
from src.services.visual.analyzer import VisualAnalyzer
analyzer = VisualAnalyzer('${OPENAI_API_KEY}')
# Test with sample analysis
print(f'Target cost per analysis: ${analyzer.cost_per_analysis}')
"

# Performance validation
python scripts/visual_load_test.py --leads=50 --workers=2 --duration=300

# UX rubrics validation
python -c "
from src.services.visual.analyzer import VisualAnalyzer
print('Required UX rubrics:', VisualAnalyzer.UX_RUBRICS)
assert len(VisualAnalyzer.UX_RUBRICS) == 9, 'Must have exactly 9 rubrics'
print('✓ All 9 UX rubrics defined')
"
```

## Rollback Strategy

### Emergency Procedures
1. **API Failure**: Disable visual analysis task in Assessment Orchestrator, continue with other assessment types
2. **Cost Overrun**: Implement emergency cost limits to prevent budget exhaustion, switch to cached responses
3. **Performance Issues**: Increase timeout limits and reduce concurrent requests to prevent system overload
4. **Quality Issues**: Revert to manual UX assessment checklist until analysis quality improved

### Detailed Rollback Steps
1. **Identify Issue**: Monitor dashboards show visual analysis failure rate >10% or cost overruns
2. **Immediate Response**: Disable visual analysis task execution and preserve existing assessment data
3. **Service Isolation**: Continue other assessment types while isolating visual analysis issues
4. **Data Validation**: Verify existing visual assessment data integrity and backup if necessary
5. **Issue Resolution**: Test fixes in staging environment with mock data before re-enabling
6. **Gradual Recovery**: Re-enable visual analysis with monitoring for issue recurrence

## Success Criteria

1. **Visual Analyzer Complete**: GPT-4 Vision API client successfully evaluates all 9 UX rubrics with structured JSON output
2. **Cost Management Effective**: Analysis cost stays within $0.01 per lead with GPT-4o-mini optimization
3. **Screenshot Integration Working**: Desktop and mobile screenshot processing from PRP-006 functions correctly
4. **Database Storage Complete**: Visual assessment results properly stored in PostgreSQL with normalized structure
5. **Performance Requirements Met**: 30-second timeout enforced with 95% success rate and proper retry logic
6. **UX Framework Applied**: Nielsen's heuristics framework ensures professional evaluation standards
7. **Testing Coverage**: Unit tests ≥90% coverage, integration tests validate complete analysis pipeline
8. **Production Readiness**: Error handling, monitoring, and cost optimization suitable for production deployment

## Critical Context

### GPT-4 Vision API Capabilities
- **UX Analysis**: Object detection, layout analysis, text readability assessment, visual hierarchy evaluation
- **Cost Structure**: GPT-4o-mini at $0.15/1M input tokens, $0.60/1M output tokens for cost optimization
- **Performance**: 30-second timeout limits, retry logic for API reliability, structured prompt engineering
- **Image Requirements**: Desktop (1920x1080) and mobile (390x844) screenshots, JPEG format optimization

### Nielsen's UX Heuristics Integration
- **Professional Standards**: Established usability principles for consistent evaluation methodology
- **Scoring Framework**: 0-2 scale provides granular assessment with actionable recommendations
- **Industry Alignment**: UX evaluation methodology recognized by professional community
- **Quality Assurance**: Structured framework ensures consistent assessment quality across all leads

### Integration Dependencies
- **Screenshot Source**: Depends on PRP-006 ScreenshotOne integration for image inputs
- **Database Schema**: Visual assessment results stored via PRP-001 lead data model extension
- **Assessment Pipeline**: Integrates with PRP-002 Assessment Orchestrator for parallel processing
- **Report Generation**: Visual insights feed into comprehensive audit report compilation

### Business Value Metrics
- **Competitive Advantage**: AI-powered UX analysis differentiates $399 audit reports from basic assessments
- **Professional Quality**: GPT-4 Vision provides sophisticated analysis comparable to human UX experts
- **Scalability**: Automated assessment enables processing 100+ leads with consistent quality standards
- **Cost Efficiency**: $0.01 per analysis provides significant ROI on $399 audit report pricing
- **Market Positioning**: Advanced AI capabilities support premium pricing strategy for audit services

## Definition of Done

- [ ] GPT-4 Vision API client implemented with all 9 UX rubrics evaluation capabilities
- [ ] Cost optimization achieved with GPT-4o-mini maintaining $0.01 per analysis target
- [ ] Screenshot integration processes desktop and mobile images from PRP-006 correctly
- [ ] Structured JSON output validated with Pydantic models for database storage
- [ ] Celery task integration connects with Assessment Orchestrator for parallel processing
- [ ] Database models store visual assessment results with proper relationships
- [ ] Unit tests written for all analyzer methods and task functions with ≥90% coverage
- [ ] Integration tests validate complete visual analysis pipeline functionality
- [ ] Performance testing confirms timeout handling and success rate requirements
- [ ] Error handling covers API failures, timeouts, and image processing issues
- [ ] Nielsen's heuristics framework properly implemented for professional UX evaluation
- [ ] Production testing validates live API integration with real screenshot analysis
- [ ] Code review completed with security validation for API key management
- [ ] Documentation updated with visual analysis setup and monitoring procedures