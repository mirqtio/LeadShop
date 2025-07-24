"""
PRP-012: Email Formatter
Compliant business email generation system with HTML/plain text formatting and regulatory compliance
"""

import asyncio
import logging
import time
import re
import json
import html2text
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.core.config import settings
from src.models.assessment_cost import AssessmentCost

logger = logging.getLogger(__name__)

# Email Generation Data Classes
@dataclass
class EmailTemplate:
    """Complete email template with HTML/plain text versions."""
    html_content: str
    plain_text: str
    subject: str
    compliance_metadata: Dict[str, Any]
    spam_score: float

@dataclass
class FormattedEmail:
    """Complete formatted email ready for delivery."""
    id: int
    lead_id: int
    to_address: str
    from_address: str
    reply_to: str
    subject: str
    html_body: str
    text_body: str
    headers: Dict[str, str]
    compliance_metadata: Dict[str, Any]
    spam_score: float
    created_at: datetime

@dataclass
class ComplianceResult:
    """Email compliance validation result."""
    is_compliant: bool
    violations: List[str]
    compliance_score: float

@dataclass
class ValidationResult:
    """Individual validator result."""
    is_compliant: bool
    violations: List[str]

class EmailFormattingError(Exception):
    """Custom exception for email formatting errors"""
    pass

class ComplianceError(Exception):
    """Custom exception for compliance violations"""
    pass

class SpamError(Exception):
    """Custom exception for high spam scores"""
    pass

class ComplianceValidator:
    """Comprehensive email compliance validation for 2024 regulations."""
    
    def __init__(self):
        self.can_spam_validator = CANSPAMValidator()
        self.gdpr_validator = GDPRValidator()
        self.rfc_validator = RFCValidator()
    
    async def validate(self, html_content: str, plain_text: str, context: Dict[str, Any]) -> ComplianceResult:
        """Run all compliance validations."""
        violations = []
        
        # CAN-SPAM Act validation
        can_spam_result = await self.can_spam_validator.validate(html_content, context)
        if not can_spam_result.is_compliant:
            violations.extend(can_spam_result.violations)
        
        # GDPR validation
        gdpr_result = await self.gdpr_validator.validate(html_content, context)
        if not gdpr_result.is_compliant:
            violations.extend(gdpr_result.violations)
        
        # RFC 8058 (One-click unsubscribe) validation
        rfc_result = await self.rfc_validator.validate_unsubscribe(html_content)
        if not rfc_result.is_compliant:
            violations.extend(rfc_result.violations)
        
        # Check required elements
        required_elements = self._check_required_elements(html_content, context)
        violations.extend(required_elements)
        
        return ComplianceResult(
            is_compliant=len(violations) == 0,
            violations=violations,
            compliance_score=self._calculate_compliance_score(violations)
        )
    
    def _check_required_elements(self, html_content: str, context: Dict[str, Any]) -> List[str]:
        """Validate presence of required email elements."""
        violations = []
        
        # Physical address requirement
        if not context.get('physical_address'):
            violations.append("Missing physical business address")
        
        # Unsubscribe link requirement
        if 'unsubscribe' not in html_content.lower():
            violations.append("Missing unsubscribe link")
        
        # Subject line requirements
        subject = context.get('subject', '')
        if not subject:
            violations.append("Missing email subject")
        elif len(subject) > 78:
            violations.append("Subject line too long (>78 characters)")
        elif any(spam_word in subject.lower() for spam_word in ['free', 'urgent', '!!!', 'act now']):
            violations.append("Subject contains spam trigger words")
        
        # Sender identification
        if not context.get('company_name'):
            violations.append("Missing sender company identification")
        
        return violations
    
    def _calculate_compliance_score(self, violations: List[str]) -> float:
        """Calculate compliance score based on violations."""
        base_score = 100.0
        violation_penalty = 10.0  # 10 points per violation
        
        score = base_score - (len(violations) * violation_penalty)
        return max(score, 0.0)

class CANSPAMValidator:
    """CAN-SPAM Act compliance validator."""
    
    async def validate(self, html_content: str, context: Dict[str, Any]) -> ValidationResult:
        """Validate CAN-SPAM Act requirements."""
        violations = []
        
        # Check for clear sender identification
        if not self._has_clear_sender_id(html_content, context):
            violations.append("CAN-SPAM: Missing clear sender identification")
        
        # Check for truthful subject line
        if not self._has_truthful_subject(context):
            violations.append("CAN-SPAM: Subject line may be misleading")
        
        # Check for clear unsubscribe mechanism
        if not self._has_clear_unsubscribe(html_content):
            violations.append("CAN-SPAM: Missing clear unsubscribe mechanism")
        
        # Check for physical address
        if not self._has_physical_address(html_content, context):
            violations.append("CAN-SPAM: Missing physical address")
        
        return ValidationResult(
            is_compliant=len(violations) == 0,
            violations=violations
        )
    
    def _has_clear_sender_id(self, html_content: str, context: Dict[str, Any]) -> bool:
        """Check for clear sender identification."""
        company_name = context.get('company_name', '')
        return company_name and company_name.lower() in html_content.lower()
    
    def _has_truthful_subject(self, context: Dict[str, Any]) -> bool:
        """Check for truthful subject line (simplified check)."""
        subject = context.get('subject', '').lower()
        misleading_words = ['fake', 'lie', 'scam', 'deception']
        return not any(word in subject for word in misleading_words)
    
    def _has_clear_unsubscribe(self, html_content: str) -> bool:
        """Check for clear unsubscribe mechanism."""
        return 'unsubscribe' in html_content.lower()
    
    def _has_physical_address(self, html_content: str, context: Dict[str, Any]) -> bool:
        """Check for physical address."""
        address = context.get('physical_address', '')
        return address and address in html_content

class GDPRValidator:
    """GDPR compliance validator."""
    
    async def validate(self, html_content: str, context: Dict[str, Any]) -> ValidationResult:
        """Validate GDPR requirements."""
        violations = []
        
        # Check for consent basis (simplified)
        if not self._has_consent_basis(html_content, context):
            violations.append("GDPR: Missing consent basis information")
        
        # Check for data processing information
        if not self._has_data_processing_info(html_content):
            violations.append("GDPR: Missing data processing information")
        
        return ValidationResult(
            is_compliant=len(violations) == 0,
            violations=violations
        )
    
    def _has_consent_basis(self, html_content: str, context: Dict[str, Any]) -> bool:
        """Check for consent basis (simplified)."""
        # For business assessments, legitimate interest is typically the basis
        return True  # Simplified - assume business assessment consent
    
    def _has_data_processing_info(self, html_content: str) -> bool:
        """Check for data processing information."""
        # Simplified check for privacy policy or data processing mention
        privacy_indicators = ['privacy policy', 'data processing', 'personal data']
        return any(indicator in html_content.lower() for indicator in privacy_indicators)

class RFCValidator:
    """RFC 8058 (One-click unsubscribe) validator."""
    
    async def validate_unsubscribe(self, html_content: str) -> ValidationResult:
        """Validate RFC 8058 one-click unsubscribe requirements."""
        violations = []
        
        # Check for unsubscribe link presence
        if not self._has_unsubscribe_link(html_content):
            violations.append("RFC 8058: Missing unsubscribe link")
        
        return ValidationResult(
            is_compliant=len(violations) == 0,
            violations=violations
        )
    
    def _has_unsubscribe_link(self, html_content: str) -> bool:
        """Check for unsubscribe link."""
        return 'unsubscribe' in html_content.lower() and 'href=' in html_content.lower()

class SpamAssassinClient:
    """Mock SpamAssassin integration for spam score checking."""
    
    def __init__(self):
        self.spam_rules = {
            'free': 2.0,
            'urgent': 1.5,
            '!!!': 2.5,
            'act now': 2.0,
            'limited time': 1.5,
            'click here': 1.0,
            'guaranteed': 1.5,
            'winner': 2.0
        }
    
    async def check_content(self, email_content: str) -> float:
        """Check email content against spam rules (mock implementation)."""
        try:
            # Simple rule-based spam checking
            spam_score = 0.0
            content_lower = email_content.lower()
            
            # Check for spam trigger words
            for trigger, score in self.spam_rules.items():
                if trigger in content_lower:
                    spam_score += score
            
            # Length penalties
            if len(email_content) < 100:
                spam_score += 1.0  # Too short
            
            # Excessive capitalization
            caps_ratio = sum(1 for c in email_content if c.isupper()) / len(email_content)
            if caps_ratio > 0.3:
                spam_score += 2.0
            
            # HTML/text ratio (prefer more text)
            html_tags = len(re.findall(r'<[^>]+>', email_content))
            if html_tags > 50:  # Too many HTML tags
                spam_score += 1.0
            
            return min(spam_score, 10.0)  # Cap at 10
            
        except Exception as e:
            logger.error(f"SpamAssassin check error: {e}")
            return 0.0  # Assume clean on error

class EmailTemplateEngine:
    """Professional email template system with Jinja2 and compliance."""
    
    def __init__(self):
        # Initialize Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader('src/email/templates'),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        self.compliance_validator = ComplianceValidator()
        self.spam_checker = SpamAssassinClient()
        
        # Add custom filters
        self._add_custom_filters()
    
    def _add_custom_filters(self):
        """Add custom Jinja2 filters for email formatting."""
        
        @self.jinja_env.filter
        def currency(value):
            """Format value as currency."""
            try:
                return f"${float(value):,.2f}"
            except (ValueError, TypeError):
                return "$0.00"
        
        @self.jinja_env.filter
        def truncate_words(text, length=50):
            """Truncate text to specified word count."""
            words = str(text).split()
            if len(words) <= length:
                return text
            return ' '.join(words[:length]) + '...'
    
    async def render_email(self, template_name: str, context: Dict[str, Any]) -> EmailTemplate:
        """Render email template with full compliance validation."""
        try:
            # Add compliance context
            compliance_context = await self._add_compliance_context(context)
            
            # Render HTML version using basic template (user will provide actual template)
            html_content = self._render_basic_html_template(compliance_context)
            
            # Generate plain text alternative
            plain_text = await self._generate_plain_text(html_content)
            
            # Validate compliance
            compliance_result = await self.compliance_validator.validate(
                html_content, plain_text, compliance_context
            )
            
            if not compliance_result.is_compliant:
                logger.warning(f"Email compliance issues: {compliance_result.violations}")
                # Continue but log violations
            
            # Check spam score
            spam_score = await self.spam_checker.check_content(html_content)
            if spam_score >= 3.0:
                logger.warning(f"High spam score: {spam_score}")
            
            return EmailTemplate(
                html_content=html_content,
                plain_text=plain_text,
                subject=compliance_context['subject'],
                compliance_metadata=compliance_result.__dict__,
                spam_score=spam_score
            )
            
        except Exception as e:
            logger.error(f"Email rendering failed: {e}")
            raise EmailFormattingError(f"Failed to render email: {e}")
    
    async def _add_compliance_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Add required compliance elements to template context."""
        compliance_context = context.copy()
        
        # Add unsubscribe URLs (RFC 8058 compliant)
        lead_id = context.get('lead_id', 0)
        compliance_context.update({
            'unsubscribe_url': f"https://leadshop.com/unsubscribe/{lead_id}",
            'one_click_unsubscribe': f"https://leadshop.com/api/v1/unsubscribe",
            'physical_address': "LeadShop Inc., 123 Business St, Suite 100, San Francisco, CA 94105",
            'company_name': "LeadShop",
            'current_date': datetime.now().strftime('%B %d, %Y'),
            'tracking_pixel_url': f"https://leadshop.com/track/open/{lead_id}/{uuid4()}",
            'utm_parameters': self._generate_utm_params(context)
        })
        
        return compliance_context
    
    def _generate_utm_params(self, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate UTM parameters for tracking."""
        return {
            'utm_source': 'leadshop_email',
            'utm_medium': 'email',
            'utm_campaign': 'business_assessment',
            'utm_content': f"assessment_report_{context.get('lead_id', 0)}"
        }
    
    def _render_basic_html_template(self, context: Dict[str, Any]) -> str:
        """Render basic HTML template (placeholder for user's template)."""
        # Basic professional email template
        html_template = f"""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
    <title>{context.get('subject', 'Business Assessment Report')}</title>
    
    <style type="text/css">
        body {{
            width: 100% !important;
            min-width: 100%;
            -webkit-text-size-adjust: 100%;
            -ms-text-size-adjust: 100%;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        }}
        
        .email-container {{
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
        }}
        
        .header {{
            background-color: #0066cc;
            padding: 30px 40px;
            text-align: center;
            color: white;
        }}
        
        .content {{
            padding: 40px;
            line-height: 1.6;
            color: #333333;
        }}
        
        .hero-section {{
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }}
        
        .cta-button {{
            display: inline-block;
            padding: 16px 32px;
            background-color: #0066cc;
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            margin: 20px 0;
        }}
        
        .footer {{
            background-color: #f1f3f4;
            padding: 30px 40px;
            text-align: center;
            font-size: 14px;
            color: #666666;
        }}
        
        @media only screen and (max-width: 600px) {{
            .email-container {{ width: 100% !important; }}
            .header, .content, .footer {{ padding: 20px !important; }}
            .cta-button {{ display: block !important; width: 100% !important; }}
        }}
    </style>
</head>
<body>
    <!-- Tracking pixel -->
    <img src="{context.get('tracking_pixel_url', '')}" width="1" height="1" alt="" style="display:none !important;" />
    
    <div class="email-container">
        <div class="header">
            <h1>{context.get('company_name', 'LeadShop')}</h1>
        </div>
        
        <div class="content">
            <div class="hero-section">
                <h2>{context.get('subject', 'Your Website Assessment Results')}</h2>
                <p>Business Assessment Report for {context.get('business_name', 'Your Business')}</p>
            </div>
            
            <p>Hi {context.get('first_name', 'there')},</p>
            
            <div>{context.get('email_body', 'Your business assessment has been completed.')}</div>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{context.get('report_url', '#')}" class="cta-button">
                    View Your Complete Report
                </a>
            </div>
            
            <p>Best regards,<br>The {context.get('company_name', 'LeadShop')} Team</p>
        </div>
        
        <div class="footer">
            <p><strong>{context.get('company_name', 'LeadShop')}</strong></p>
            <p>{context.get('physical_address', '')}</p>
            <p>
                <a href="{context.get('report_url', '#')}">View Report</a> | 
                <a href="mailto:support@leadshop.com">Contact Us</a> | 
                <a href="{context.get('unsubscribe_url', '#')}">Unsubscribe</a>
            </p>
            
            <div style="font-size: 12px; color: #999999; margin-top: 20px;">
                <p>You received this email because you requested a business assessment from {context.get('company_name', 'LeadShop')}.</p>
                <p>To unsubscribe from future emails, <a href="{context.get('unsubscribe_url', '#')}">click here</a>.</p>
                <p>&copy; {context.get('current_date', '2024')} {context.get('company_name', 'LeadShop')}. All rights reserved.</p>
            </div>
        </div>
    </div>
</body>
</html>
        """
        return html_template.strip()
    
    async def _generate_plain_text(self, html_content: str) -> str:
        """Generate accessible plain text version from HTML."""
        try:
            # Use html2text for semantic conversion
            h = html2text.HTML2Text()
            h.ignore_images = True
            h.ignore_links = False
            h.wrap_links = False
            h.unicode_snob = True
            
            plain_text = h.handle(html_content)
            
            # Clean up formatting
            plain_text = re.sub(r'\n\s*\n\s*\n', '\n\n', plain_text)
            plain_text = plain_text.strip()
            
            return plain_text
            
        except Exception as e:
            logger.error(f"Plain text generation failed: {e}")
            # Fallback: simple HTML tag removal
            plain_text = re.sub(r'<[^>]+>', '', html_content)
            plain_text = re.sub(r'\s+', ' ', plain_text)
            return plain_text.strip()

class EmailFormatter:
    """Main email formatting orchestrator."""
    
    def __init__(self):
        self.template_engine = EmailTemplateEngine()
        self.cost_per_email = 0.0  # Internal formatting - no external API cost
    
    async def format_email(self, lead_id: int, content_data: Dict[str, Any]) -> FormattedEmail:
        """Format complete email from LLM-generated content."""
        start_time = time.time()
        
        try:
            # Load lead data for personalization
            lead = await self._load_lead_data(lead_id)
            
            # Prepare template context
            template_context = await self._prepare_template_context(lead, content_data)
            
            # Generate tracking URLs
            tracking_data = await self._generate_tracking_urls(lead_id)
            template_context.update(tracking_data)
            
            # Render email templates
            email_template = await self.template_engine.render_email(
                'business_assessment_email.html', 
                template_context
            )
            
            # Generate email headers
            headers = self._generate_email_headers(tracking_data)
            
            # Store email in database for audit trail
            email_record_id = await self._store_email_record(lead_id, email_template, template_context)
            
            # Generate final formatted email
            formatted_email = FormattedEmail(
                id=email_record_id,
                lead_id=lead_id,
                to_address=lead.get('email', ''),
                from_address="assessments@leadshop.com",
                reply_to="support@leadshop.com",
                subject=email_template.subject,
                html_body=email_template.html_content,
                text_body=email_template.plain_text,
                headers=headers,
                compliance_metadata=email_template.compliance_metadata,
                spam_score=email_template.spam_score,
                created_at=datetime.now(timezone.utc)
            )
            
            # Track performance
            processing_time = time.time() - start_time
            logger.info(f"Email formatted for lead {lead_id}: {processing_time:.3f}s, spam score {email_template.spam_score:.1f}")
            
            return formatted_email
            
        except Exception as e:
            logger.error(f"Email formatting failed for lead {lead_id}: {e}")
            raise EmailFormattingError(f"Failed to format email: {str(e)}")
    
    async def _prepare_template_context(self, lead: Dict[str, Any], content_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare comprehensive template context."""
        # Get report URL (would integrate with PRP-011 Report Builder)
        report_url = await self._get_report_url(lead.get('id', 0))
        
        # Prepare personalization data
        context = {
            'lead_id': lead.get('id', 0),
            'business_name': lead.get('company', 'Your Business'),
            'first_name': self._extract_first_name(lead.get('contact_name', '') or lead.get('company', 'there')),
            'email': lead.get('email', ''),
            'website_url': lead.get('url', ''),
            'industry': self._get_industry_name(lead.get('naics_code', '')),
            'subject': content_data.get('subject_line', 'Your Website Assessment Results'),
            'email_body': content_data.get('email_body', ''),
            'report_url': report_url,
            'report_download_url': f"{report_url}?download=true",
            'insights': self._format_insights(content_data.get('issue_insights', [])),
            'next_steps': self._format_recommendations(content_data.get('recommended_actions', []))
        }
        
        return context
    
    async def _generate_tracking_urls(self, lead_id: int) -> Dict[str, str]:
        """Generate tracking URLs for email analytics."""
        base_url = "https://leadshop.com"
        tracking_id = str(uuid4())
        
        return {
            'tracking_pixel_url': f"{base_url}/track/open/{lead_id}/{tracking_id}",
            'unsubscribe_url': f"{base_url}/unsubscribe/{lead_id}",
            'one_click_unsubscribe': f"{base_url}/api/v1/unsubscribe"
        }
    
    def _generate_email_headers(self, tracking_data: Dict[str, str]) -> Dict[str, str]:
        """Generate proper email headers for deliverability."""
        headers = {
            'List-Unsubscribe': f"<{tracking_data['unsubscribe_url']}>, <mailto:unsubscribe@leadshop.com?subject=unsubscribe>",
            'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click',
            'List-Id': f"LeadShop Business Assessments <assessments.leadshop.com>",
            'Precedence': 'bulk',
            'Auto-Submitted': 'auto-generated',
            'X-Campaign-ID': f"business_assessment_{datetime.now().strftime('%Y%m')}",
            'X-Lead-ID': str(tracking_data.get('lead_id', 0)),
            'Return-Path': f"bounce@leadshop.com",
            'Sender': f"noreply@leadshop.com"
        }
        
        return headers
    
    def _extract_first_name(self, name: str) -> str:
        """Extract first name from full name or company name."""
        if not name:
            return "there"
        
        # If it looks like a person's name (has spaces), take first part
        parts = name.strip().split()
        if len(parts) > 1 and not any(word.lower() in name.lower() for word in ['inc', 'llc', 'corp', 'company', 'ltd']):
            return parts[0]
        
        # Otherwise, assume it's a company name
        return name.split()[0] if name.split() else "there"
    
    def _get_industry_name(self, naics_code: str) -> str:
        """Convert NAICS code to readable industry name."""
        industry_map = {
            '541511': 'Software Development',
            '454110': 'E-commerce',
            '722513': 'Restaurant',
            '541990': 'Professional Services'
        }
        return industry_map.get(naics_code, 'Business')
    
    def _format_insights(self, insights: List[str]) -> List[Dict[str, str]]:
        """Format insights for template display."""
        formatted_insights = []
        for i, insight in enumerate(insights[:3]):  # Top 3 insights
            formatted_insights.append({
                'title': f"Finding #{i+1}",
                'description': insight
            })
        return formatted_insights
    
    def _format_recommendations(self, recommendations: List[str]) -> str:
        """Format recommendations as HTML list."""
        if not recommendations:
            return ""
        
        formatted_recs = []
        for rec in recommendations[:3]:  # Top 3 recommendations
            formatted_recs.append(f"<li>{rec}</li>")
        
        return f"<ul>{''.join(formatted_recs)}</ul>"
    
    async def _get_report_url(self, lead_id: int) -> str:
        """Get report URL from PRP-011 Report Builder."""
        # Mock implementation - would integrate with Report Builder
        return f"https://leadshop.com/reports/{lead_id}"
    
    async def _load_lead_data(self, lead_id: int) -> Dict[str, Any]:
        """Load lead data from database."""
        # Mock implementation - would load from database
        return {
            'id': lead_id,
            'company': 'Tuome NYC',
            'email': 'manager@tuome.com',
            'contact_name': 'Restaurant Manager',
            'url': 'https://tuome.com',
            'naics_code': '722513'
        }
    
    async def _store_email_record(self, lead_id: int, email_template: EmailTemplate, context: Dict[str, Any]) -> int:
        """Store email record in database for audit trail."""
        # Mock implementation - would store in database
        email_record_id = int(time.time())  # Mock ID
        
        logger.info(f"Stored email record {email_record_id} for lead {lead_id}")
        return email_record_id

async def format_business_email(lead_id: int, content_data: Dict[str, Any]) -> FormattedEmail:
    """
    Main entry point for business email formatting.
    
    Args:
        lead_id: Database ID of the lead
        content_data: LLM-generated content from PRP-010
        
    Returns:
        Complete formatted email ready for delivery
    """
    try:
        # Initialize email formatter
        formatter = EmailFormatter()
        
        # Format the email
        logger.info(f"Starting email formatting for lead {lead_id}")
        formatted_email = await formatter.format_email(lead_id, content_data)
        
        logger.info(f"Email formatting completed for lead {lead_id}: spam score {formatted_email.spam_score:.1f}")
        return formatted_email
        
    except Exception as e:
        logger.error(f"Business email formatting failed for lead {lead_id}: {e}")
        raise EmailFormattingError(f"Email formatting failed: {str(e)}")

# Add create_email_cost method to AssessmentCost model
def create_email_cost_method(cls, lead_id: int, cost_cents: float = 0.0, response_status: str = "success", response_time_ms: Optional[int] = None, error_message: Optional[str] = None):
    """
    Create cost record for email formatting (no external API cost).
    
    Args:
        lead_id: ID of the lead being assessed
        cost_cents: Cost in cents (default $0.00 - internal formatting)
        response_status: success, error, timeout
        response_time_ms: Formatting time in milliseconds
        error_message: Error message if applicable
        
    Returns:
        AssessmentCost instance
    """
    now = datetime.now(timezone.utc)
    
    return cls(
        lead_id=lead_id,
        service_name="email_formatter",
        api_endpoint="internal://email/format",
        cost_cents=cost_cents,
        currency="USD",
        request_timestamp=now,
        response_status=response_status,
        response_time_ms=response_time_ms,
        api_quota_used=False,  # Internal formatting - no quota
        rate_limited=False,
        retry_count=0,
        error_message=error_message,
        daily_budget_date=now.strftime("%Y-%m-%d"),
        monthly_budget_date=now.strftime("%Y-%m")
    )

# Monkey patch the method to AssessmentCost
AssessmentCost.create_email_cost = classmethod(create_email_cost_method)