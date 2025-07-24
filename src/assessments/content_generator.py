"""
PRP-010: LLM Content Generator
GPT-4-powered content generation system for personalized email marketing and business reports
"""

import logging
import time
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

import httpx

from src.core.config import settings
from src.models.assessment_cost import AssessmentCost

logger = logging.getLogger(__name__)

# Content Generation Data Classes
@dataclass
class ContentGenerationRequest:
    """Content generation request with personalization data."""
    lead_id: int
    business_name: str
    industry_code: str
    assessment_results: Dict[str, Any]
    priority_issues: List[str]
    financial_impact: float
    contact_name: Optional[str] = None
    company_size: Optional[str] = None
    urgency_level: str = "medium"

@dataclass
class GeneratedContent:
    """Complete generated content package for email marketing."""
    lead_id: int
    
    # Email content
    subject_line: str
    email_body: str
    
    # Report content  
    executive_summary: str
    issue_insights: List[str]
    recommended_actions: List[str]
    urgency_indicators: List[str]
    
    # Metadata
    generation_timestamp: str
    api_cost_dollars: float
    spam_score: float
    brand_voice_score: float
    content_quality_score: float
    template_version: str
    processing_time_ms: int

class ContentGeneratorError(Exception):
    """Custom exception for content generation errors"""
    pass

class ContentGenerator:
    """
    GPT-4-powered content generation system for personalized email marketing
    and business assessment report content with brand voice consistency.
    """
    
    # OpenAI API Configuration
    MODEL = "gpt-4o-mini"  # Cost-optimized model
    COST_PER_LEAD = 2.0  # $0.02 in cents (target cost optimization)
    TIMEOUT = 30  # 30 seconds
    MAX_RETRIES = 3
    
    # Content type specifications
    CONTENT_SPECS = {
        'subject_line': {'max_length': 60, 'min_length': 20},
        'email_body': {'max_words': 200, 'min_words': 150},
        'executive_summary': {'max_words': 150, 'min_words': 100},
        'issue_insights': {'count': 3, 'max_words_each': 50},
        'recommended_actions': {'count': 3, 'max_words_each': 40},
        'urgency_indicators': {'count': 2, 'max_words_each': 30}
    }
    
    # Brand voice guidelines
    BRAND_VOICE = {
        'tone': 'professional yet approachable',
        'style': 'data-driven and actionable',
        'avoid': ['jargon without explanation', 'overly technical language', 'sales-heavy language'],
        'include': ['specific metrics', 'clear next steps', 'business impact focus']
    }
    
    # Industry-specific language adaptations
    INDUSTRY_LANGUAGE = {
        '541511': {'terms': ['development', 'technical debt', 'performance optimization'], 'tone': 'technical'},
        '454110': {'terms': ['conversion rate', 'user experience', 'online presence'], 'tone': 'commercial'},
        '722513': {'terms': ['customer experience', 'brand reputation', 'local visibility'], 'tone': 'service-oriented'},
        'default': {'terms': ['business growth', 'operational efficiency', 'competitive advantage'], 'tone': 'professional'}
    }
    
    def __init__(self):
        """Initialize content generator with OpenAI API configuration."""
        self.api_key = settings.OPENAI_API_KEY
        self.client = httpx.AsyncClient(timeout=self.TIMEOUT)
        self.template_version = "v1.0"
        
        logger.info(f"Content Generator initialized with model: {self.MODEL}")
    
    async def generate_email_content(self, lead_id: int, business_data: Dict[str, Any], assessment_data: Dict[str, Any]) -> GeneratedContent:
        """
        Generate complete email content package for a business lead.
        
        Args:
            lead_id: Database ID of the lead for content generation
            business_data: Business information (company, industry, etc.)
            assessment_data: Assessment results from all PRPs
            
        Returns:
            GeneratedContent: Complete content package with all 6 content types
        """
        start_time = time.time()
        
        try:
            # Prepare generation request
            generation_request = self._prepare_generation_request(lead_id, business_data, assessment_data)
            
            # Generate all content types in a single API call for efficiency
            generated_content = await self._generate_all_content(generation_request)
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            generated_content.processing_time_ms = processing_time_ms
            
            # Validate content quality and cost
            await self._validate_generated_content(generated_content)
            
            logger.info(f"Content generation completed for lead {lead_id}: ${generated_content.api_cost_dollars:.4f} cost, {processing_time_ms}ms")
            return generated_content
            
        except Exception as e:
            logger.error(f"Content generation failed for lead {lead_id}: {e}")
            raise ContentGeneratorError(f"Content generation failed: {str(e)}")
    
    def _prepare_generation_request(self, lead_id: int, business_data: Dict[str, Any], assessment_data: Dict[str, Any]) -> ContentGenerationRequest:
        """Prepare content generation request with business context."""
        
        # Extract business information
        business_name = business_data.get('company', 'Your Business')
        industry_code = business_data.get('naics_code', 'default')
        contact_name = business_data.get('contact_name')
        
        # Extract assessment results and priority issues
        business_score = assessment_data.get('business_score', {})
        priority_issues = business_score.get('priority_recommendations', [])
        financial_impact = business_score.get('total_impact_estimate', 0)
        
        # Determine urgency level based on score
        overall_score = business_score.get('overall_score', 50)
        if overall_score < 40:
            urgency_level = "high"
        elif overall_score < 60:
            urgency_level = "medium"
        else:
            urgency_level = "low"
        
        return ContentGenerationRequest(
            lead_id=lead_id,
            business_name=business_name,
            industry_code=industry_code,
            assessment_results=assessment_data,
            priority_issues=priority_issues[:5],  # Top 5 issues
            financial_impact=financial_impact,
            contact_name=contact_name,
            urgency_level=urgency_level
        )
    
    async def _generate_all_content(self, request: ContentGenerationRequest) -> GeneratedContent:
        """Generate all content types in a single optimized API call."""
        
        if not self.api_key:
            raise ContentGeneratorError("OpenAI API key not configured")
        
        # Create comprehensive content generation prompt
        prompt = self._create_content_generation_prompt(request)
        
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
                            "role": "system",
                            "content": "You are a professional B2B marketing content writer specializing in website audit reports. Generate personalized, data-driven content that follows brand guidelines and avoids spam triggers."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.3,  # Lower temperature for consistent, professional content
                    "response_format": {"type": "json_object"}
                },
                timeout=self.TIMEOUT
            )
            
            if response.status_code == 200:
                response_data = response.json()
                return self._parse_content_response(request, response_data)
            elif response.status_code == 429:
                logger.warning("OpenAI API rate limit hit")
                raise ContentGeneratorError("API rate limit exceeded")
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                raise ContentGeneratorError(f"API request failed: {response.status_code}")
                
        except httpx.TimeoutException:
            logger.error("Content generation API timeout")
            raise ContentGeneratorError("Content generation request timed out")
        except Exception as e:
            logger.error(f"Content generation API error: {e}")
            raise ContentGeneratorError(f"Content generation failed: {str(e)}")
    
    def _create_content_generation_prompt(self, request: ContentGenerationRequest) -> str:
        """Create comprehensive prompt for all content types."""
        
        industry_lang = self.INDUSTRY_LANGUAGE.get(request.industry_code, self.INDUSTRY_LANGUAGE['default'])
        
        # Format priority issues
        issues_text = "\n".join([f"- {issue}" for issue in request.priority_issues[:3]])
        
        return f"""
Generate personalized email marketing content for a business website audit. Create ALL 6 content types in JSON format.

**Business Context:**
- Company: {request.business_name}
- Industry: {request.industry_code}
- Contact: {request.contact_name or 'Business Owner'}
- Financial Impact: ${request.financial_impact:,.2f}
- Urgency: {request.urgency_level}

**Key Issues Identified:**
{issues_text or "- General website optimization opportunities"}

**Brand Voice Guidelines:**
- Tone: {self.BRAND_VOICE['tone']}
- Style: {self.BRAND_VOICE['style']}
- Industry Focus: {industry_lang['tone']}

**Content Requirements:**

1. **Subject Line** (20-60 characters):
   - Personalized with company name
   - Action-oriented and urgency-appropriate
   - Spam-compliant (avoid ALL CAPS, excessive punctuation)

2. **Email Body** (150-200 words):
   - Professional greeting with contact name
   - Brief assessment summary with specific metrics
   - 2-3 key issues and business impact
   - Clear call-to-action
   - Professional closing

3. **Executive Summary** (100-150 words):
   - High-level assessment overview
   - Key performance indicators
   - Business impact summary
   - Executive-friendly language

4. **Issue Insights** (3 items, max 50 words each):
   - Specific technical findings
   - Business impact explanation
   - Data-driven insights

5. **Recommended Actions** (3 items, max 40 words each):
   - Actionable next steps
   - Priority-based ordering
   - Clear, implementable suggestions

6. **Urgency Indicators** (2 items, max 30 words each):
   - Time-sensitive issues
   - Competitive implications
   - Revenue impact timing

**Output Format (JSON):**
```json
{{
  "subject_line": "Personalized subject line here",
  "email_body": "Complete email body content...",
  "executive_summary": "Executive summary content...",
  "issue_insights": [
    "First insight...",
    "Second insight...",
    "Third insight..."
  ],
  "recommended_actions": [
    "First action...",
    "Second action...",
    "Third action..."
  ],
  "urgency_indicators": [
    "First urgency indicator...",
    "Second urgency indicator..."
  ]
}}
```

Generate professional, personalized content that drives engagement while maintaining spam compliance.
"""

    def _parse_content_response(self, request: ContentGenerationRequest, response_data: Dict[str, Any]) -> GeneratedContent:
        """Parse OpenAI response into GeneratedContent object."""
        
        try:
            # Extract content from response
            content = response_data["choices"][0]["message"]["content"]
            
            # Parse JSON content
            try:
                parsed_content = json.loads(content)
            except json.JSONDecodeError:
                # Fallback: extract JSON from markdown if present
                if '```json' in content:
                    json_start = content.find('```json') + 7
                    json_end = content.find('```', json_start)
                    json_content = content[json_start:json_end].strip()
                    parsed_content = json.loads(json_content)
                else:
                    raise ContentGeneratorError("Invalid JSON in content response")
            
            # Calculate API cost
            usage = response_data.get("usage", {})
            api_cost = self._calculate_api_cost(usage)
            
            # Estimate content quality scores (simplified)
            spam_score = self._estimate_spam_score(parsed_content.get("email_body", ""))
            brand_voice_score = self._estimate_brand_voice_score(parsed_content)
            content_quality_score = self._estimate_content_quality(parsed_content)
            
            return GeneratedContent(
                lead_id=request.lead_id,
                subject_line=parsed_content.get("subject_line", "Website Audit Results Available"),
                email_body=parsed_content.get("email_body", ""),
                executive_summary=parsed_content.get("executive_summary", ""),
                issue_insights=parsed_content.get("issue_insights", []),
                recommended_actions=parsed_content.get("recommended_actions", []),
                urgency_indicators=parsed_content.get("urgency_indicators", []),
                generation_timestamp=datetime.now(timezone.utc).isoformat(),
                api_cost_dollars=api_cost,
                spam_score=spam_score,
                brand_voice_score=brand_voice_score,
                content_quality_score=content_quality_score,
                template_version=self.template_version,
                processing_time_ms=0  # Will be set by caller
            )
            
        except Exception as e:
            logger.error(f"Failed to parse content response: {e}")
            raise ContentGeneratorError(f"Content parsing failed: {str(e)}")
    
    def _calculate_api_cost(self, usage: Dict[str, Any]) -> float:
        """Calculate API cost based on token usage."""
        
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
            return 0.02  # Return target estimate if calculation fails
    
    def _estimate_spam_score(self, email_body: str) -> float:
        """Estimate spam score based on content analysis (simplified)."""
        
        # Basic spam indicators
        spam_indicators = [
            ('FREE', 2.0), ('URGENT', 1.5), ('LIMITED TIME', 1.5),
            ('CLICK HERE', 1.0), ('!!!', 2.0), ('$$$', 2.0),
            ('GUARANTEE', 1.0), ('NO COST', 1.0)
        ]
        
        spam_score = 0.0
        email_upper = email_body.upper()
        
        for indicator, score in spam_indicators:
            if indicator in email_upper:
                spam_score += score
        
        # Length penalties
        if len(email_body.split()) < 50:
            spam_score += 1.0  # Too short
        elif len(email_body.split()) > 300:
            spam_score += 0.5  # Too long
        
        return min(spam_score, 10.0)  # Cap at 10
    
    def _estimate_brand_voice_score(self, content: Dict[str, Any]) -> float:
        """Estimate brand voice consistency score."""
        
        # Check for brand voice elements
        score = 8.0  # Start with good score
        
        email_body = content.get("email_body", "").lower()
        
        # Positive indicators
        if any(word in email_body for word in ['specific', 'data', 'results', 'assessment']):
            score += 0.5
        
        if any(word in email_body for word in ['recommend', 'suggest', 'next steps']):
            score += 0.5
        
        # Negative indicators
        if any(word in email_body for word in ['amazing', 'incredible', 'fantastic']):
            score -= 1.0  # Too sales-heavy
        
        if len([c for c in email_body if c.isupper()]) > len(email_body) * 0.1:
            score -= 1.0  # Too much uppercase
        
        return max(min(score, 10.0), 0.0)
    
    def _estimate_content_quality(self, content: Dict[str, Any]) -> float:
        """Estimate overall content quality score."""
        
        quality_score = 7.0  # Base score
        
        # Check completeness
        required_fields = ['subject_line', 'email_body', 'executive_summary', 'issue_insights', 'recommended_actions']
        complete_fields = sum(1 for field in required_fields if content.get(field))
        quality_score += (complete_fields / len(required_fields)) * 2.0  # Up to 2 points
        
        # Check length compliance
        subject_len = len(content.get('subject_line', ''))
        if 20 <= subject_len <= 60:
            quality_score += 0.5
        
        email_words = len(content.get('email_body', '').split())
        if 150 <= email_words <= 200:
            quality_score += 0.5
        
        return max(min(quality_score, 10.0), 0.0)
    
    async def _validate_generated_content(self, content: GeneratedContent) -> None:
        """Validate generated content quality and compliance."""
        
        # Check cost optimization
        if content.api_cost_dollars > self.COST_PER_LEAD / 100 * 1.5:  # 1.5x tolerance
            logger.warning(f"Content generation cost ${content.api_cost_dollars:.4f} exceeds target ${self.COST_PER_LEAD/100:.4f}")
        
        # Check spam score
        if content.spam_score > 3.0:
            logger.warning(f"High spam score {content.spam_score:.1f} - content may have deliverability issues")
        
        # Check content completeness
        if not all([content.subject_line, content.email_body, content.executive_summary]):
            logger.warning("Incomplete content generation - missing required fields")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

async def generate_marketing_content(lead_id: int, business_data: Dict[str, Any], assessment_data: Dict[str, Any]) -> GeneratedContent:
    """
    Main entry point for marketing content generation.
    
    Args:
        lead_id: Database ID of the lead
        business_data: Business information and context
        assessment_data: Complete assessment results from all PRPs
        
    Returns:
        Complete generated content package for email marketing
    """
    try:
        if not settings.OPENAI_API_KEY:
            raise ContentGeneratorError("OpenAI API key not configured")
        
        # Initialize content generator
        generator = ContentGenerator()
        
        try:
            # Generate marketing content
            logger.info(f"Starting content generation for lead {lead_id}")
            generated_content = await generator.generate_email_content(lead_id, business_data, assessment_data)
            
            logger.info(f"Content generation completed for lead {lead_id}: {len(generated_content.issue_insights)} insights, {len(generated_content.recommended_actions)} actions")
            return generated_content
            
        finally:
            await generator.close()
            
    except Exception as e:
        logger.error(f"Marketing content generation failed for lead {lead_id}: {e}")
        raise ContentGeneratorError(f"Content generation failed: {str(e)}")

# Add create_content_cost method to AssessmentCost model
def create_content_cost_method(cls, lead_id: int, cost_cents: float = 2.0, response_status: str = "success", response_time_ms: Optional[int] = None, error_message: Optional[str] = None):
    """
    Create cost record for content generation API call.
    
    Args:
        lead_id: ID of the lead being assessed
        cost_cents: Cost in cents (default $0.02)
        response_status: success, error, timeout, rate_limited
        response_time_ms: API response time in milliseconds
        error_message: Error message if applicable
        
    Returns:
        AssessmentCost instance
    """
    now = datetime.now(timezone.utc)
    
    return cls(
        lead_id=lead_id,
        service_name="openai_content",
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
AssessmentCost.create_content_cost = classmethod(create_content_cost_method)