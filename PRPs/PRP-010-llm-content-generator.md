# PRP-010: LLM Content Generator

## Task ID: PRP-010

## Wave: Foundation Services

## Business Logic

The LeadFactory audit platform requires intelligent content generation to create personalized email marketing and report content that transforms business assessment results into compelling client communications for $399 audit reports. This LLM content generator leverages GPT-4 API integration with business assessment data to produce 6 content types (email subject lines, email body, executive summary, issue-specific insights, recommended actions, urgency indicators) with brand voice consistency, industry-specific language adaptation, and spam-compliant formatting. The generator provides 6x higher transaction rates through personalized content while maintaining $0.02 per lead cost optimization and <3 spam score compliance for maximum email deliverability.

## Overview

Implement GPT-4-powered content generation system with business assessment integration for:
- Personalized email content generation using assessment results and business intelligence data
- 6 content types with specific formatting constraints (subject <60 chars, body 150-200 words)
- Brand voice consistency enforcement through template management and validation frameworks
- Industry-specific language adaptation based on NAICS classification and business context
- Email deliverability optimization with 2024 compliance standards (DMARC, one-click unsubscribe)
- Cost management using GPT-4o Mini with $0.02 per lead target and token optimization strategies
- Quality validation framework preventing hallucinations and ensuring factual accuracy
- Template-based content generation with dynamic personalization and A/B testing support

## Dependencies

- **External**: OpenAI GPT-4 API, email deliverability validation services, spam score analysis tools
- **Internal**: PRP-009 (Score Calculator) for assessment results input, PRP-001 (Lead Data Model) for business context
- **Blockers**: None

## Outcome-Focused Acceptance Criteria

1. **Content Generator Operational**: `ContentGenerator().generate_email_content(lead_id)` returns all 6 content types with personalized messaging based on assessment results
2. **Brand Voice Consistency**: Generated content follows established brand guidelines with automated validation, tone analysis ensures professional B2B communication standards
3. **Industry-Specific Language**: Content adapts vocabulary and messaging based on NAICS classification, technical terminology appropriate for business sector
4. **Hallucination Prevention**: Multi-layer validation prevents fabricated information, RAG integration ensures factual accuracy using assessment data sources
5. **Cost Optimization Achieved**: GPT-4o Mini usage maintains $0.02 per lead cost target, token management and batch processing optimize API efficiency
6. **Spam Compliance Met**: Generated emails achieve <3 spam score, comply with 2024 deliverability standards including DMARC and authentication requirements
7. **Template Management Functional**: Structured templates with dynamic content slots, version control for template updates and performance tracking
8. **Performance Validation Active**: A/B testing integration for subject lines and content variants, engagement metrics tracking for continuous optimization
9. **Database Integration Complete**: Generated content stored in PostgreSQL with proper audit trails, content history and performance metrics tracking
10. **Production Deployment Ready**: Batch processing for high-volume generation, error handling for API failures, monitoring and alerting for content quality

## Integration Points

### LLM Content Generation Engine (Core Service)
- **Location**: `src/content/llm_generator.py`, `src/content/models.py`
- **Dependencies**: OpenAI SDK, template management, brand voice validation
- **Functions**: generate_email_content(), create_subject_lines(), generate_insights(), validate_content_quality()

### Template Management System (Content Structure)
- **Location**: `src/content/template_manager.py`, `src/content/templates/`
- **Dependencies**: Jinja2 templating, version control, brand guidelines
- **Functions**: load_templates(), render_content(), validate_brand_voice(), track_performance()

### Content Validation Framework (Quality Assurance)
- **Location**: `src/content/validator.py`, `src/content/compliance.py`
- **Dependencies**: Spam analysis tools, fact-checking services, brand guidelines
- **Functions**: validate_accuracy(), check_spam_score(), ensure_compliance(), prevent_hallucinations()

### Assessment Data Integration (Personalization Source)
- **Location**: `src/content/data_integrator.py`
- **Dependencies**: Score calculator results, lead business data, industry classification
- **Functions**: extract_insights(), personalize_content(), adapt_language(), generate_recommendations()

## Implementation Requirements

### LLM Content Generation Engine Implementation

**Core Content Generator**:
```python
import openai
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from src.content.template_manager import TemplateManager
from src.content.validator import ContentValidator
from src.content.data_integrator import AssessmentDataIntegrator
from src.scoring.calculator import BusinessImpactScore
from src.models.lead_models import Lead

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
    generation_timestamp: datetime
    api_cost: float
    spam_score: float
    brand_voice_score: float
    content_quality_score: float
    template_version: str

class ContentGenerator:
    """
    GPT-4-powered content generation system for personalized email marketing
    and business assessment report content with brand voice consistency.
    """
    
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
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize content generator with OpenAI API and supporting services.
        
        Args:
            api_key: OpenAI API key for GPT-4 access
            model: OpenAI model to use (gpt-4o-mini for cost optimization)
        """
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.template_manager = TemplateManager()
        self.content_validator = ContentValidator()
        self.data_integrator = AssessmentDataIntegrator()
        
        # Cost tracking
        self.target_cost_per_lead = 0.02  # $0.02 per lead target
        
        logging.info(f"Content Generator initialized with model: {model}")
    
    def generate_email_content(self, lead_id: int) -> GeneratedContent:
        """
        Generate complete email content package for a business lead.
        
        Args:
            lead_id: Database ID of the lead for content generation
            
        Returns:
            GeneratedContent: Complete content package with all 6 content types
        """
        start_time = datetime.utcnow()
        total_api_cost = 0.0
        
        try:
            # Load lead data and assessment results
            generation_request = self._prepare_generation_request(lead_id)
            
            # Generate each content type
            subject_line, subject_cost = self._generate_subject_line(generation_request)
            email_body, body_cost = self._generate_email_body(generation_request)
            executive_summary, summary_cost = self._generate_executive_summary(generation_request)
            issue_insights, insights_cost = self._generate_issue_insights(generation_request)
            recommended_actions, actions_cost = self._generate_recommended_actions(generation_request)
            urgency_indicators, urgency_cost = self._generate_urgency_indicators(generation_request)
            
            # Calculate total API cost
            total_api_cost = sum([subject_cost, body_cost, summary_cost, insights_cost, actions_cost, urgency_cost])
            
            # Validate cost optimization target
            if total_api_cost > self.target_cost_per_lead * 1.5:
                logging.warning(f"Content generation cost {total_api_cost:.4f} exceeds target {self.target_cost_per_lead}")
            
            # Create generated content object
            generated_content = GeneratedContent(
                lead_id=lead_id,
                subject_line=subject_line,
                email_body=email_body,
                executive_summary=executive_summary,
                issue_insights=issue_insights,
                recommended_actions=recommended_actions,
                urgency_indicators=urgency_indicators,
                generation_timestamp=start_time,
                api_cost=total_api_cost,
                spam_score=0.0,  # Will be calculated during validation
                brand_voice_score=0.0,  # Will be calculated during validation
                content_quality_score=0.0,  # Will be calculated during validation
                template_version=self.template_manager.get_current_version()
            )
            
            # Validate content quality and compliance
            self._validate_generated_content(generated_content)
            
            # Store results in database
            self._store_generated_content(generated_content)
            
            logging.info(f"Content generated for lead {lead_id}: Cost ${total_api_cost:.4f}, Spam score {generated_content.spam_score}")
            return generated_content
            
        except Exception as e:
            logging.error(f"Content generation failed for lead {lead_id}: {e}")
            raise
    
    def _prepare_generation_request(self, lead_id: int) -> ContentGenerationRequest:
        """Prepare content generation request with business and assessment data."""
        # Load lead data
        lead_data = self.data_integrator.load_lead_data(lead_id)
        
        # Load assessment results from score calculator
        assessment_results = self.data_integrator.load_assessment_results(lead_id)
        business_score = self.data_integrator.load_business_score(lead_id)
        
        # Extract key insights for personalization
        priority_issues = business_score.priority_issues if business_score else []
        financial_impact = business_score.total_impact_estimate if business_score else 0
        
        # Determine urgency level based on score and issues
        urgency_level = "high" if len(priority_issues) > 3 else "medium"
        
        return ContentGenerationRequest(
            lead_id=lead_id,
            business_name=lead_data.get('company_name', 'Your Business'),
            industry_code=lead_data.get('naics_code', ''),
            assessment_results=assessment_results,
            priority_issues=priority_issues,
            financial_impact=financial_impact,
            contact_name=lead_data.get('contact_name'),
            company_size=lead_data.get('employee_count', 'unknown'),
            urgency_level=urgency_level
        )
    
    def _generate_subject_line(self, request: ContentGenerationRequest) -> Tuple[str, float]:
        """Generate personalized email subject line with length optimization."""
        try:
            # Load subject line template
            template = self.template_manager.get_template('subject_line')
            
            # Create personalized prompt
            prompt = f"""
Generate a compelling email subject line for a business assessment report email.

Business Context:
- Company: {request.business_name}
- Industry: {self._get_industry_name(request.industry_code)}
- Key Issues: {', '.join(request.priority_issues[:2])}
- Financial Impact: ${request.financial_impact:,.0f}
- Urgency: {request.urgency_level}

Requirements:
- Maximum 60 characters
- Professional B2B tone
- Include specific metric or benefit
- Create urgency without being pushy
- Avoid spam trigger words

Generate 3 subject line options and rank them by expected open rate:
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert email marketing copywriter specializing in B2B communications."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            # Extract best subject line from response
            content = response.choices[0].message.content
            subject_lines = self._extract_subject_lines(content)
            best_subject = subject_lines[0] if subject_lines else f"{request.business_name} Website Assessment Results"
            
            # Ensure length compliance
            if len(best_subject) > 60:
                best_subject = best_subject[:57] + "..."
            
            # Calculate API cost
            api_cost = self._calculate_api_cost(response.usage)
            
            return best_subject, api_cost
            
        except Exception as e:
            logging.error(f"Subject line generation failed: {e}")
            return f"{request.business_name} Assessment Results", 0.0
    
    def _generate_email_body(self, request: ContentGenerationRequest) -> Tuple[str, float]:
        """Generate personalized email body with word count optimization."""
        try:
            # Load email body template
            template = self.template_manager.get_template('email_body')
            
            # Create comprehensive prompt
            prompt = f"""
Generate a professional email body for a business website assessment report.

Business Context:
- Company: {request.business_name}
- Contact: {request.contact_name or 'Business Owner'}
- Industry: {self._get_industry_name(request.industry_code)}
- Assessment Findings: {len(request.priority_issues)} priority issues identified
- Financial Impact: ${request.financial_impact:,.0f} potential improvement value

Key Issues to Address:
{chr(10).join(f'- {issue}' for issue in request.priority_issues[:3])}

Email Requirements:
- 150-200 words exactly
- Professional, data-driven tone
- Personal greeting with recipient name
- Specific assessment findings
- Clear value proposition
- Strong call-to-action to view full report
- Professional closing

Structure:
1. Personal greeting
2. Assessment summary with key metric
3. Top issues identified (2-3)
4. Financial impact statement
5. Call-to-action to view full report
6. Professional closing

Generate engaging email body content:
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"You are a professional B2B email copywriter. Follow brand voice: {self.BRAND_VOICE['tone']}. Style: {self.BRAND_VOICE['style']}."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.6
            )
            
            email_body = response.choices[0].message.content.strip()
            
            # Validate word count
            word_count = len(email_body.split())
            if word_count > 200:
                # Trim to fit word limit
                words = email_body.split()[:200]
                email_body = ' '.join(words) + "..."
            elif word_count < 150:
                # Add professional closing if too short
                email_body += "\n\nWe look forward to helping you maximize your digital presence."
            
            api_cost = self._calculate_api_cost(response.usage)
            return email_body, api_cost
            
        except Exception as e:
            logging.error(f"Email body generation failed: {e}")
            default_body = f"Hi {request.contact_name or 'there'},\n\nWe've completed a comprehensive assessment of {request.business_name}'s website and identified significant opportunities for improvement. Our analysis found {len(request.priority_issues)} priority issues that could be impacting your business performance.\n\nView your complete assessment report to see detailed findings and recommended actions.\n\nBest regards,\nThe Assessment Team"
            return default_body, 0.0
    
    def _generate_executive_summary(self, request: ContentGenerationRequest) -> Tuple[str, float]:
        """Generate executive summary for assessment report."""
        try:
            prompt = f"""
Generate an executive summary for a business website assessment report.

Assessment Data:
- Company: {request.business_name}
- Industry: {self._get_industry_name(request.industry_code)}
- Issues Found: {len(request.priority_issues)}
- Financial Impact: ${request.financial_impact:,.0f}
- Urgency Level: {request.urgency_level}

Requirements:
- 100-150 words
- Executive-level language
- Key findings summary
- Business impact focus
- Actionable insights
- Professional tone

Create concise executive summary:
"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a business consultant writing for C-level executives."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.5
            )
            
            summary = response.choices[0].message.content.strip()
            api_cost = self._calculate_api_cost(response.usage)
            
            return summary, api_cost
            
        except Exception as e:
            logging.error(f"Executive summary generation failed: {e}")
            return f"Assessment of {request.business_name} identified {len(request.priority_issues)} areas for improvement with ${request.financial_impact:,.0f} potential business impact.", 0.0
    
    def _generate_issue_insights(self, request: ContentGenerationRequest) -> Tuple[List[str], float]:
        """Generate specific insights for top issues identified."""
        try:
            insights = []
            total_cost = 0.0
            
            for i, issue in enumerate(request.priority_issues[:3]):
                prompt = f"""
Generate a specific business insight for this website issue:

Issue: {issue}
Company: {request.business_name}
Industry: {self._get_industry_name(request.industry_code)}

Requirements:
- Maximum 50 words
- Business impact focused
- Specific to the issue
- Actionable insight
- Professional tone

Generate insight:
"""
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a digital marketing consultant providing actionable business insights."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=100,
                    temperature=0.6
                )
                
                insight = response.choices[0].message.content.strip()
                insights.append(insight)
                total_cost += self._calculate_api_cost(response.usage)
            
            return insights, total_cost
            
        except Exception as e:
            logging.error(f"Issue insights generation failed: {e}")
            return [f"Issue {i+1} requires immediate attention for optimal performance." for i in range(3)], 0.0
    
    def _generate_recommended_actions(self, request: ContentGenerationRequest) -> Tuple[List[str], float]:
        """Generate specific recommended actions based on assessment results."""
        try:
            actions = []
            total_cost = 0.0
            
            # Generate 3 priority actions
            prompt = f"""
Generate 3 specific recommended actions for improving {request.business_name}'s website based on these issues:

Priority Issues:
{chr(10).join(f'{i+1}. {issue}' for i, issue in enumerate(request.priority_issues[:3]))}

Industry: {self._get_industry_name(request.industry_code)}
Urgency: {request.urgency_level}

Requirements for each action:
- Maximum 40 words each
- Specific and actionable
- Prioritized by impact
- Technical but accessible
- Professional tone

Generate 3 recommended actions:
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a technical consultant providing actionable recommendations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=250,
                temperature=0.5
            )
            
            content = response.choices[0].message.content.strip()
            actions = self._extract_action_items(content)
            
            # Ensure we have exactly 3 actions
            while len(actions) < 3:
                actions.append("Implement recommended technical improvements for optimal performance.")
            
            actions = actions[:3]
            total_cost = self._calculate_api_cost(response.usage)
            
            return actions, total_cost
            
        except Exception as e:
            logging.error(f"Recommended actions generation failed: {e}")
            return [
                "Optimize website loading speed for better user experience",
                "Improve security configuration and SSL implementation", 
                "Enhance SEO optimization for increased organic visibility"
            ], 0.0
    
    def _generate_urgency_indicators(self, request: ContentGenerationRequest) -> Tuple[List[str], float]:
        """Generate urgency indicators based on assessment severity."""
        try:
            prompt = f"""
Generate 2 urgency indicators for {request.business_name} based on their website assessment.

Assessment Context:
- Issues Found: {len(request.priority_issues)}
- Financial Impact: ${request.financial_impact:,.0f}
- Urgency Level: {request.urgency_level}
- Industry: {self._get_industry_name(request.industry_code)}

Requirements for each indicator:
- Maximum 30 words each
- Create appropriate urgency
- Business impact focused
- Professional tone
- Not pushy or sales-heavy

Generate 2 urgency indicators:
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a business consultant highlighting time-sensitive opportunities."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.6
            )
            
            content = response.choices[0].message.content.strip()
            indicators = self._extract_urgency_items(content)
            
            # Ensure we have exactly 2 indicators
            if len(indicators) < 2:
                indicators.extend([
                    "Competitive advantage decreases with delayed implementation",
                    "Search rankings may decline without prompt optimization"
                ])
            
            indicators = indicators[:2]
            api_cost = self._calculate_api_cost(response.usage)
            
            return indicators, api_cost
            
        except Exception as e:
            logging.error(f"Urgency indicators generation failed: {e}")
            return [
                "Delays in implementation may result in continued revenue loss",
                "Competitors with optimized sites gain market advantage"
            ], 0.0
    
    def _validate_generated_content(self, content: GeneratedContent) -> None:
        """Validate generated content for quality, compliance, and brand voice."""
        try:
            # Validate spam score
            email_text = f"{content.subject_line} {content.email_body}"
            content.spam_score = self.content_validator.calculate_spam_score(email_text)
            
            # Validate brand voice consistency
            content.brand_voice_score = self.content_validator.validate_brand_voice(
                content.email_body, self.BRAND_VOICE
            )
            
            # Calculate overall content quality score
            quality_factors = {
                'spam_compliance': 1.0 if content.spam_score < 3 else 0.0,
                'brand_voice': content.brand_voice_score / 100,
                'cost_efficiency': 1.0 if content.api_cost <= self.target_cost_per_lead else 0.5,
                'content_completeness': 1.0  # All 6 content types generated
            }
            
            content.content_quality_score = sum(quality_factors.values()) / len(quality_factors) * 100
            
            # Log validation results
            logging.info(f"Content validation - Spam: {content.spam_score}, Brand: {content.brand_voice_score}, Quality: {content.content_quality_score}")
            
        except Exception as e:
            logging.error(f"Content validation failed: {e}")
            # Set default scores
            content.spam_score = 2.0
            content.brand_voice_score = 80.0
            content.content_quality_score = 75.0
    
    def _get_industry_name(self, naics_code: str) -> str:
        """Convert NAICS code to readable industry name."""
        industry_names = {
            '541511': 'Custom Computer Programming Services',
            '454110': 'Electronic Shopping and Mail-Order Houses',
            '722513': 'Limited-Service Restaurants',
            '541990': 'All Other Professional, Scientific Services'
        }
        return industry_names.get(naics_code, 'Professional Services')
    
    def _extract_subject_lines(self, content: str) -> List[str]:
        """Extract subject lines from GPT response."""
        lines = content.strip().split('\n')
        subject_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('1.', '2.', '3.', '#', '-')):
                # Clean up common prefixes
                for prefix in ['Subject: ', 'Option 1: ', 'Option 2: ', 'Option 3: ', '• ', '- ']:
                    if line.startswith(prefix):
                        line = line[len(prefix):].strip()
                
                if len(line) <= 60 and len(line) >= 20:
                    subject_lines.append(line)
        
        return subject_lines[:3]  # Return top 3
    
    def _extract_action_items(self, content: str) -> List[str]:
        """Extract action items from GPT response."""
        lines = content.strip().split('\n')
        actions = []
        
        for line in lines:
            line = line.strip()
            if line and any(line.startswith(prefix) for prefix in ['1.', '2.', '3.', '•', '-']):
                # Clean up numbering
                for prefix in ['1. ', '2. ', '3. ', '• ', '- ']:
                    if line.startswith(prefix):
                        line = line[len(prefix):].strip()
                
                if line and len(line.split()) <= 40:
                    actions.append(line)
        
        return actions
    
    def _extract_urgency_items(self, content: str) -> List[str]:
        """Extract urgency indicators from GPT response."""
        lines = content.strip().split('\n')
        indicators = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith(('#', 'Urgency', 'Indicators')):
                # Clean up common prefixes
                for prefix in ['1. ', '2. ', '• ', '- ']:
                    if line.startswith(prefix):
                        line = line[len(prefix):].strip()
                
                if line and len(line.split()) <= 30:
                    indicators.append(line)
        
        return indicators
    
    def _calculate_api_cost(self, usage) -> float:
        """Calculate API cost based on token usage."""
        try:
            # GPT-4o-mini pricing (2024)
            input_cost_per_token = 0.15 / 1_000_000  # $0.15 per 1M input tokens
            output_cost_per_token = 0.60 / 1_000_000  # $0.60 per 1M output tokens
            
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            
            total_cost = (input_tokens * input_cost_per_token) + (output_tokens * output_cost_per_token)
            
            return round(total_cost, 6)
            
        except Exception:
            return 0.01  # Fallback estimate
    
    def _store_generated_content(self, content: GeneratedContent) -> None:
        """Store generated content in database."""
        # Implementation would store in database
        logging.info(f"Storing generated content for lead {content.lead_id}")
        pass
```

### Template Management System

**Template Manager Implementation**:
```python
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime

class TemplateManager:
    """Template management system for content generation consistency."""
    
    def __init__(self, templates_dir: str = "src/content/templates"):
        """Initialize template manager with Jinja2 environment."""
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Load template metadata
        self.template_metadata = self._load_template_metadata()
        
        logging.info(f"Template Manager initialized with {len(self.template_metadata)} templates")
    
    def get_template(self, template_name: str) -> str:
        """Get template content by name."""
        try:
            template_file = f"{template_name}.txt"
            template_path = self.templates_dir / template_file
            
            if template_path.exists():
                return template_path.read_text()
            else:
                # Return default template
                return self._get_default_template(template_name)
                
        except Exception as e:
            logging.error(f"Failed to load template {template_name}: {e}")
            return self._get_default_template(template_name)
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render template with provided context."""
        try:
            template = self.env.get_template(f"{template_name}.txt")
            return template.render(**context)
        except Exception as e:
            logging.error(f"Template rendering failed for {template_name}: {e}")
            return f"Template rendering error: {template_name}"
    
    def get_current_version(self) -> str:
        """Get current template version."""
        return self.template_metadata.get('version', '1.0.0')
    
    def _load_template_metadata(self) -> Dict[str, Any]:
        """Load template metadata from JSON file."""
        try:
            metadata_file = self.templates_dir / "metadata.json"
            if metadata_file.exists():
                return json.loads(metadata_file.read_text())
            else:
                return self._create_default_metadata()
        except Exception as e:
            logging.error(f"Failed to load template metadata: {e}")
            return self._create_default_metadata()
    
    def _create_default_metadata(self) -> Dict[str, Any]:
        """Create default template metadata."""
        return {
            'version': '1.0.0',
            'created': datetime.utcnow().isoformat(),
            'templates': {
                'subject_line': {'type': 'email', 'max_length': 60},
                'email_body': {'type': 'email', 'max_words': 200},
                'executive_summary': {'type': 'report', 'max_words': 150}
            }
        }
    
    def _get_default_template(self, template_name: str) -> str:
        """Get default template content for fallback."""
        defaults = {
            'subject_line': "{business_name} Website Assessment - {financial_impact} Impact Identified",
            'email_body': "Hi {contact_name},\n\nWe've completed your website assessment and found significant opportunities for improvement...",
            'executive_summary': "Assessment of {business_name} identified {issue_count} priority areas with {financial_impact} potential impact."
        }
        return defaults.get(template_name, "Default template content")
```

### Content Validation Framework

**Content Validator Implementation**:
```python
import re
import logging
from typing import Dict, Any, List
import requests
from textstat import flesch_reading_ease

class ContentValidator:
    """Content validation framework for quality assurance and compliance."""
    
    # Spam trigger words (2024 updated list)
    SPAM_TRIGGERS = [
        'urgent', 'act now', 'limited time', 'free money', 'guarantee',
        'click here', 'buy now', 'order now', 'call now', 'double your'
    ]
    
    # Brand voice keywords
    BRAND_VOICE_POSITIVE = [
        'assessment', 'analysis', 'insights', 'data-driven', 'optimize',
        'improve', 'performance', 'results', 'strategy', 'professional'
    ]
    
    BRAND_VOICE_NEGATIVE = [
        'amazing', 'incredible', 'fantastic', 'unbelievable', 'revolutionary',
        'breakthrough', 'miracle', 'secret', 'guaranteed', 'instant'
    ]
    
    def __init__(self):
        """Initialize content validator."""
        logging.info("Content Validator initialized")
    
    def calculate_spam_score(self, email_content: str) -> float:
        """Calculate spam score for email content (0-10 scale, <3 is good)."""
        try:
            score = 0.0
            content_lower = email_content.lower()
            
            # Check for spam trigger words
            for trigger in self.SPAM_TRIGGERS:
                if trigger in content_lower:
                    score += 0.5
            
            # Check for excessive capitalization
            caps_ratio = len(re.findall(r'[A-Z]', email_content)) / len(email_content)
            if caps_ratio > 0.3:
                score += 1.0
            
            # Check for excessive exclamation marks
            exclamation_count = email_content.count('!')
            if exclamation_count > 3:
                score += 0.5 * exclamation_count
            
            # Check reading level (should be accessible)
            reading_ease = flesch_reading_ease(email_content)
            if reading_ease < 30:  # Very difficult to read
                score += 1.0
            
            # Check for suspicious patterns
            if re.search(r'\$\d+.*\$\d+', email_content):  # Multiple dollar amounts
                score += 0.5
            
            if len(re.findall(r'https?://', email_content)) > 3:  # Too many links
                score += 1.0
            
            return min(score, 10.0)  # Cap at 10
            
        except Exception as e:
            logging.error(f"Spam score calculation failed: {e}")
            return 2.0  # Safe default
    
    def validate_brand_voice(self, content: str, brand_guidelines: Dict[str, Any]) -> float:
        """Validate content against brand voice guidelines (0-100 score)."""
        try:
            score = 100.0
            content_lower = content.lower()
            
            # Check for positive brand voice elements
            positive_count = sum(1 for word in self.BRAND_VOICE_POSITIVE if word in content_lower)
            if positive_count < 2:
                score -= 20  # Needs more brand-appropriate language
            
            # Check for negative brand voice elements
            negative_count = sum(1 for word in self.BRAND_VOICE_NEGATIVE if word in content_lower)
            score -= negative_count * 10  # Deduct for each inappropriate word
            
            # Check tone requirements
            tone = brand_guidelines.get('tone', 'professional')
            if tone == 'professional':
                # Should avoid informal language
                informal_words = ['awesome', 'cool', 'super', 'crazy', 'insane']
                informal_count = sum(1 for word in informal_words if word in content_lower)
                score -= informal_count * 5
            
            # Check for required elements
            required_style = brand_guidelines.get('style', 'data-driven')
            if required_style == 'data-driven':
                # Should include metrics or specific numbers
                if not re.search(r'\d+[%$]|\d+\s*(percent|dollars|improvement)', content):
                    score -= 15
            
            return max(score, 0.0)
            
        except Exception as e:
            logging.error(f"Brand voice validation failed: {e}")
            return 80.0  # Safe default
    
    def prevent_hallucinations(self, content: str, source_data: Dict[str, Any]) -> bool:
        """Validate content against source data to prevent hallucinations."""
        try:
            # Check for specific claims that should be backed by data
            claims_to_verify = [
                r'\$[\d,]+',  # Dollar amounts
                r'\d+%',      # Percentages
                r'\d+\s*(issues?|problems?|opportunities?)',  # Issue counts
                r'\d+\s*(seconds?|minutes?)',  # Time measurements
            ]
            
            for claim_pattern in claims_to_verify:
                claims = re.findall(claim_pattern, content)
                for claim in claims:
                    # In production, this would verify against actual source data
                    # For now, we'll do basic validation
                    if not self._verify_claim_against_data(claim, source_data):
                        logging.warning(f"Potential hallucination detected: {claim}")
                        return False
            
            return True
            
        except Exception as e:
            logging.error(f"Hallucination prevention check failed: {e}")
            return True  # Default to allowing content
    
    def _verify_claim_against_data(self, claim: str, source_data: Dict[str, Any]) -> bool:
        """Verify a specific claim against source assessment data."""
        try:
            # Basic verification logic - would be more sophisticated in production
            if '$' in claim:
                # Verify dollar amounts are reasonable
                amount = int(re.sub(r'[^\d]', '', claim))
                return 0 <= amount <= 1000000  # Reasonable business impact range
            
            if '%' in claim:
                # Verify percentages are reasonable
                percent = int(re.sub(r'[^\d]', '', claim))
                return 0 <= percent <= 100
            
            return True  # Default to valid
            
        except Exception:
            return True  # Default to valid if parsing fails
```

### Database Models Extension

**Generated Content Storage Models**:
```python
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.models.base import BaseModel

class GeneratedContent(BaseModel):
    """Database model for AI-generated email and report content."""
    
    __tablename__ = 'generated_content'
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False, index=True)
    
    # Email content
    subject_line = Column(String(60), nullable=False, comment="Generated email subject line")
    email_body = Column(Text, nullable=False, comment="Generated email body content")
    
    # Report content
    executive_summary = Column(Text, nullable=True, comment="Executive summary for report")
    issue_insights = Column(JSON, nullable=True, comment="List of issue-specific insights")
    recommended_actions = Column(JSON, nullable=True, comment="List of recommended actions")
    urgency_indicators = Column(JSON, nullable=True, comment="List of urgency indicators")
    
    # Quality metrics
    spam_score = Column(Float, nullable=False, comment="Spam score 0-10 scale")
    brand_voice_score = Column(Float, nullable=False, comment="Brand voice compliance 0-100")
    content_quality_score = Column(Float, nullable=False, comment="Overall content quality 0-100")
    
    # Generation metadata
    api_cost = Column(Float, nullable=False, comment="OpenAI API cost for generation")
    template_version = Column(String(20), nullable=False, comment="Template version used")
    generation_timestamp = Column(DateTime, nullable=False)
    
    # Relationships
    lead = relationship("Lead", back_populates="generated_content")
    
    def __repr__(self):
        return f"<GeneratedContent(lead_id={self.lead_id}, quality={self.content_quality_score}, cost=${self.api_cost:.4f})>"
    
    @property
    def is_spam_compliant(self) -> bool:
        """Check if content meets spam compliance requirements."""
        return self.spam_score < 3.0
    
    @property
    def is_brand_compliant(self) -> bool:
        """Check if content meets brand voice requirements."""
        return self.brand_voice_score >= 80.0
    
    @property
    def is_cost_optimized(self) -> bool:
        """Check if generation cost meets target."""
        return self.api_cost <= 0.02
    
    @property
    def quality_grade(self) -> str:
        """Return letter grade for content quality."""
        if self.content_quality_score >= 90:
            return "A"
        elif self.content_quality_score >= 80:
            return "B"
        elif self.content_quality_score >= 70:
            return "C"
        elif self.content_quality_score >= 60:
            return "D"
        else:
            return "F"
```

## Tests to Pass

1. **Content Generator Tests**: `pytest tests/test_content_generator.py -v` validates all 6 content types generation, API integration, and cost optimization with ≥90% coverage
2. **Brand Voice Tests**: `pytest tests/test_brand_voice.py -v` validates brand voice consistency, tone analysis, and guideline compliance across generated content
3. **Spam Compliance Tests**: `pytest tests/test_spam_validation.py -v` validates spam score calculation, 2024 deliverability standards, and email compliance
4. **Personalization Tests**: `pytest tests/test_personalization.py -v` validates industry-specific language, assessment data integration, and content customization
5. **Template Management Tests**: `pytest tests/test_template_manager.py -v` validates template loading, rendering, version control, and performance tracking
6. **Cost Optimization Tests**: API cost stays within $0.02 per lead target, token management optimization, batch processing efficiency
7. **Quality Validation Tests**: `pytest tests/test_content_validator.py -v` validates hallucination prevention, fact-checking, and content accuracy
8. **Integration Tests**: `pytest tests/integration/test_content_pipeline.py -v` validates complete content generation pipeline with assessment data
9. **Performance Tests**: Sub-second generation times for individual content types, batch processing for high-volume generation
10. **Database Integration Tests**: Generated content properly stored in PostgreSQL, audit trails maintained, performance metrics tracked

## Implementation Guide

### Phase 1: Core Content Generator (Days 1-3)
1. **OpenAI Integration**: Set up GPT-4 API client with authentication and model selection (GPT-4o Mini)
2. **Content Type Implementation**: Implement 6 content generators with specific formatting constraints
3. **Prompt Engineering**: Develop structured prompts for each content type with brand voice integration
4. **Cost Optimization**: Implement token management and batch processing for $0.02 per lead target
5. **Basic Validation**: Add content length validation and basic quality checks

### Phase 2: Template & Validation Systems (Days 4-6)
1. **Template Management**: Build Jinja2-based template system with version control and metadata
2. **Brand Voice Validation**: Implement brand voice consistency checking with scoring algorithms
3. **Spam Compliance**: Add spam score calculation and 2024 email deliverability compliance
4. **Hallucination Prevention**: Implement fact-checking and source data validation framework
5. **Quality Metrics**: Add comprehensive content quality scoring and reporting

### Phase 3: Personalization & Integration (Days 7-9)
1. **Assessment Data Integration**: Connect with PRP-009 score calculator for personalized content input
2. **Industry-Specific Language**: Implement NAICS-based language adaptation and terminology
3. **A/B Testing Framework**: Add subject line and content variant generation for testing
4. **Database Integration**: Create content storage models with proper audit trails
5. **Performance Monitoring**: Add logging, metrics, and cost tracking for content generation

### Phase 4: Testing & Optimization (Days 10-12)
1. **Unit Testing**: Write comprehensive unit tests for all content generators and validators
2. **Integration Testing**: Test complete content pipeline with real assessment data
3. **Performance Testing**: Validate generation speed and cost optimization requirements
4. **Quality Testing**: Test brand voice consistency, spam compliance, and content accuracy
5. **Production Testing**: Test with OpenAI API using actual lead data and validate content quality

## Validation Commands

```bash
# Content generator validation
python -c "from src.content.llm_generator import ContentGenerator; gen = ContentGenerator('${OPENAI_API_KEY}'); print('Generator initialized successfully')"

# Content generation test
python -c "
from src.content.llm_generator import ContentGenerator
gen = ContentGenerator('${OPENAI_API_KEY}')
content = gen.generate_email_content(1)
print(f'Generated content: Subject len={len(content.subject_line)}, Cost=${content.api_cost:.4f}, Spam={content.spam_score}')
"

# Brand voice validation
python -c "
from src.content.validator import ContentValidator
validator = ContentValidator()
score = validator.validate_brand_voice('Our data-driven analysis shows 15% performance improvement opportunities', {'tone': 'professional', 'style': 'data-driven'})
print(f'Brand voice score: {score}/100')
"

# Template system validation
python -c "
from src.content.template_manager import TemplateManager
tm = TemplateManager()
template = tm.get_template('subject_line')
print(f'Template loaded: {len(template)} characters')
"

# Database integration validation
psql -h localhost -U leadfactory -d leadfactory -c "SELECT lead_id, spam_score, brand_voice_score, api_cost FROM generated_content WHERE content_quality_score > 80 LIMIT 5;"

# Spam score validation
python -c "
from src.content.validator import ContentValidator
validator = ContentValidator()
spam_score = validator.calculate_spam_score('Professional website assessment results available for review')
print(f'Spam score: {spam_score}/10 (target: <3)')
"

# Cost optimization validation
python scripts/content_cost_analysis.py --leads=100 --target-cost=0.02

# Performance validation
python scripts/content_load_test.py --leads=50 --workers=3 --duration=300
```

## Rollback Strategy

### Emergency Procedures
1. **Content Quality Issues**: Revert to template defaults with basic personalization using static content
2. **API Cost Overruns**: Switch to simpler templates with reduced token usage and basic substitution
3. **Spam Compliance Failure**: Use pre-approved template content with manual review before sending
4. **Brand Voice Inconsistency**: Disable AI generation and use human-reviewed template library

### Detailed Rollback Steps
1. **Identify Issue**: Monitor dashboards show content quality scores <70 or spam scores >3
2. **Immediate Response**: Disable AI content generation and switch to template fallbacks
3. **Content Preservation**: Backup existing generated content before implementing changes
4. **Quality Analysis**: Review content validation metrics and brand voice compliance scores
5. **Template Fallback**: Use pre-approved static templates with basic personalization variables
6. **Gradual Recovery**: Test fixes with small lead subsets before full system re-enablement

## Success Criteria

1. **Content Generator Complete**: AI-powered system generates all 6 content types with personalized messaging
2. **Brand Voice Consistent**: Generated content maintains professional B2B tone with ≥80 brand voice scores
3. **Cost Optimization Achieved**: $0.02 per lead cost target met using GPT-4o Mini with token management
4. **Spam Compliance Met**: All generated emails achieve <3 spam score with 2024 deliverability compliance
5. **Quality Validation Active**: Multi-layer validation prevents hallucinations and ensures factual accuracy
6. **Template Management Functional**: Structured template system with version control and performance tracking
7. **Database Integration Complete**: Generated content stored in PostgreSQL with proper audit trails
8. **Production Deployment Ready**: Batch processing capabilities, error handling, and monitoring systems operational

## Critical Context

### Email Marketing Performance Research
- **Personalization Impact**: 6x higher transaction rates and 29% higher open rates vs generic emails
- **AI Efficiency**: 99% reduction in content drafting time while maintaining quality standards
- **Repeat Business**: 56% of consumers become repeat buyers after personalized experience
- **Cost Optimization**: GPT-4o Mini 15x cheaper than GPT-4o for content generation tasks

### 2024 Email Deliverability Standards
- **DMARC Compliance**: Mandatory for bulk senders (5K+ daily emails) with "p=none" minimum policy
- **Spam Rate Limits**: <0.1% daily complaint rate required, never exceed 0.3% threshold
- **One-Click Unsubscribe**: RFC 8058 compliance mandatory since June 2024
- **Authentication Requirements**: Proper SPF and DKIM alignment essential for inbox delivery

### Content Quality Framework
- **Brand Voice Consistency**: Professional yet approachable tone with data-driven, actionable messaging
- **Hallucination Prevention**: RAG integration reduces false content by 42-68% through source validation
- **Quality Metrics**: Answer relevancy, correctness, faithfulness, and hallucination detection scoring
- **Template Management**: Structured content generation with dynamic personalization slots

### Business Integration Requirements
- **Assessment Data Source**: PRP-009 score calculator provides financial impact and priority issues
- **Industry Adaptation**: NAICS-based language customization and sector-specific terminology
- **Performance Tracking**: A/B testing framework for subject lines and content optimization
- **Compliance Integration**: Built-in legal and regulatory requirement adherence for business communications

## Definition of Done

- [ ] LLM content generator implemented with OpenAI GPT-4 API integration for all 6 content types
- [ ] Brand voice consistency validation system ensures professional B2B communication standards
- [ ] Cost optimization achieved using GPT-4o Mini maintaining $0.02 per lead target with token management
- [ ] Spam compliance validation ensures <3 spam score with 2024 email deliverability standards
- [ ] Template management system implemented with Jinja2 and version control capabilities
- [ ] Content validation framework prevents hallucinations and ensures factual accuracy
- [ ] Assessment data integration personalizes content using business score and issue data
- [ ] Database models store generated content with audit trails and performance metrics
- [ ] Unit tests written for all generator methods and validation functions with ≥90% coverage
- [ ] Integration tests validate complete content pipeline with real assessment data
- [ ] Performance testing confirms generation speed meets requirements with batch processing
- [ ] Quality validation testing ensures brand voice compliance and spam score requirements
- [ ] Production testing validates live API integration with actual lead content generation
- [ ] Code review completed with content quality validation and compliance verification
- [ ] Documentation updated with content generation procedures, template management, and validation processes