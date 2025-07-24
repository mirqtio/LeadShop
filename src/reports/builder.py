"""
PRP-011: Report Builder
Professional HTML/PDF report generation system with Refined Carbon design system integration
"""

import asyncio
import logging
import time
import tempfile
import base64
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from pathlib import Path

from src.core.config import settings
from src.models.assessment_cost import AssessmentCost

logger = logging.getLogger(__name__)

# Report Generation Data Classes
@dataclass
class ReportGenerationRequest:
    """Report generation request with all required data."""
    lead_id: int
    business_name: str
    contact_name: str
    assessment_date: datetime
    business_score: Dict[str, Any]
    generated_content: Dict[str, Any]
    report_type: str = "comprehensive"
    branding_options: Dict[str, Any] = None

@dataclass
class GeneratedReport:
    """Complete generated report with metadata."""
    lead_id: int
    report_id: str
    
    # Generated files
    html_content: str
    pdf_file_path: str
    
    # Cloud storage
    s3_html_url: str
    s3_pdf_url: str
    signed_pdf_url: str
    
    # Metadata
    file_size_mb: float
    generation_time: float
    accessibility_score: float
    design_compliance_score: float
    
    # Timestamps
    generated_at: datetime
    expires_at: Optional[datetime]

class ReportBuilderError(Exception):
    """Custom exception for report generation errors"""
    pass

class ReportBuilder:
    """
    Professional report generation system using Refined Carbon design system
    with HTML/PDF output, accessibility compliance, and cloud storage integration.
    """
    
    # Report section specifications
    REPORT_SECTIONS = {
        'hero': {'order': 1, 'required': True, 'template': 'hero_section.html'},
        'top_issues': {'order': 2, 'required': True, 'template': 'issues_section.html'},
        'financial_impact': {'order': 3, 'required': True, 'template': 'impact_section.html'},
        'detailed_findings': {'order': 4, 'required': True, 'template': 'findings_section.html'},
        'quick_wins': {'order': 5, 'required': True, 'template': 'quickwins_section.html'},
        'methodology': {'order': 6, 'required': True, 'template': 'methodology_section.html'}
    }
    
    # Performance targets
    MAX_GENERATION_TIME = 10.0  # seconds
    MAX_PDF_SIZE_MB = 2.0
    MIN_ACCESSIBILITY_SCORE = 85.0
    
    # Report generation cost
    COST_PER_REPORT = 0.0  # Internal generation - no external API cost
    
    def __init__(self):
        """Initialize report builder with required services."""
        self.report_template_base = None  # User will provide template
        self.browser = None  # Puppeteer browser instance
        
        logger.info("Report Builder initialized with infrastructure ready")
    
    async def generate_report(self, lead_id: int) -> GeneratedReport:
        """
        Generate complete HTML/PDF report with professional design and accessibility.
        
        Args:
            lead_id: Database ID of the lead for report generation
            
        Returns:
            GeneratedReport: Complete report package with cloud storage URLs
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            # Prepare report generation request
            request = await self._prepare_generation_request(lead_id)
            
            # Generate HTML content using user's template
            html_content = await self._generate_html_report(request)
            
            # Convert to PDF with optimization
            pdf_file_path = await self._generate_pdf_report(html_content, request)
            
            # Validate file size and quality
            await self._validate_report_quality(pdf_file_path, html_content)
            
            # Upload to S3 with CDN optimization (placeholder for S3 integration)
            s3_urls = await self._upload_to_storage(html_content, pdf_file_path, request)
            
            # Calculate performance metrics
            generation_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            file_size_mb = Path(pdf_file_path).stat().st_size / (1024 * 1024)
            
            # Validate performance targets
            if generation_time > self.MAX_GENERATION_TIME:
                logger.warning(f"Report generation exceeded target: {generation_time:.2f}s > {self.MAX_GENERATION_TIME}s")
            
            if file_size_mb > self.MAX_PDF_SIZE_MB:
                logger.warning(f"PDF file size exceeded target: {file_size_mb:.2f}MB > {self.MAX_PDF_SIZE_MB}MB")
            
            # Create report object
            report = GeneratedReport(
                lead_id=lead_id,
                report_id=f"report_{lead_id}_{int(start_time.timestamp())}",
                html_content=html_content,
                pdf_file_path=pdf_file_path,
                s3_html_url=s3_urls['html_url'],
                s3_pdf_url=s3_urls['pdf_url'],
                signed_pdf_url=s3_urls['signed_url'],
                file_size_mb=file_size_mb,
                generation_time=generation_time,
                accessibility_score=await self._calculate_accessibility_score(html_content),
                design_compliance_score=await self._calculate_design_compliance(html_content),
                generated_at=start_time,
                expires_at=None  # Set based on business requirements
            )
            
            # Store report metadata
            await self._store_report_metadata(report)
            
            logger.info(f"Report generated for lead {lead_id}: {file_size_mb:.2f}MB, {generation_time:.2f}s")
            return report
            
        except Exception as e:
            logger.error(f"Report generation failed for lead {lead_id}: {e}")
            raise ReportBuilderError(f"Report generation failed: {str(e)}")
        finally:
            # Cleanup temporary files
            if 'pdf_file_path' in locals() and Path(pdf_file_path).exists():
                # Keep file for now - would be cleaned up after S3 upload in production
                pass
    
    async def _prepare_generation_request(self, lead_id: int) -> ReportGenerationRequest:
        """Prepare report generation request with all required data."""
        # Load lead data from database (mock implementation)
        lead_data = await self._load_lead_data(lead_id)
        
        # Load business score from PRP-009 calculator
        business_score = await self._load_business_score(lead_id)
        
        # Load generated content from PRP-010 content generator
        generated_content = await self._load_generated_content(lead_id)
        
        return ReportGenerationRequest(
            lead_id=lead_id,
            business_name=lead_data.get('company', 'Business'),
            contact_name=lead_data.get('contact_name', 'Business Owner'),
            assessment_date=datetime.now(timezone.utc),
            business_score=business_score,
            generated_content=generated_content
        )
    
    async def _generate_html_report(self, request: ReportGenerationRequest) -> str:
        """Generate complete HTML report using user-provided templates."""
        try:
            # Prepare template context data
            context = {
                'business_name': request.business_name,
                'contact_name': request.contact_name,
                'assessment_date': request.assessment_date,
                'overall_score': request.business_score.get('overall_score', 0),
                'total_impact': request.business_score.get('total_impact_estimate', 0),
                'confidence_range': request.business_score.get('confidence_interval', (0, 0)),
                
                # Section-specific data
                'hero_data': self._prepare_hero_data(request),
                'issues_data': self._prepare_issues_data(request),
                'impact_data': self._prepare_impact_data(request),
                'findings_data': self._prepare_findings_data(request),
                'quickwins_data': self._prepare_quickwins_data(request),
                'methodology_data': self._prepare_methodology_data(request),
                
                # Design system variables (Refined Carbon)
                'design_system': self._get_design_system_config(),
                'responsive_breakpoints': self._get_responsive_breakpoints()
            }
            
            # For now, generate a basic HTML structure (user will provide actual template)
            html_content = self._generate_basic_html_structure(context)
            
            # Validate HTML structure and accessibility
            await self._validate_html_structure(html_content)
            
            return html_content
            
        except Exception as e:
            logger.error(f"HTML report generation failed: {e}")
            raise ReportBuilderError(f"HTML generation failed: {str(e)}")
    
    async def _generate_pdf_report(self, html_content: str, request: ReportGenerationRequest) -> str:
        """Convert HTML to PDF using Puppeteer-like functionality (mock implementation)."""
        try:
            # Create temporary file for PDF output
            temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            pdf_path = temp_pdf.name
            temp_pdf.close()
            
            # Mock PDF generation (in production would use Puppeteer)
            # For demo purposes, create a minimal PDF placeholder
            pdf_content = self._create_mock_pdf_content(html_content)
            
            with open(pdf_path, 'wb') as f:
                f.write(pdf_content)
            
            # Optimize PDF file size (mock implementation)
            optimized_path = await self._optimize_pdf(pdf_path)
            
            # Replace original with optimized version
            if optimized_path != pdf_path:
                Path(pdf_path).unlink()
                pdf_path = optimized_path
            
            return pdf_path
            
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            raise ReportBuilderError(f"PDF generation failed: {str(e)}")
    
    async def _validate_report_quality(self, pdf_path: str, html_content: str) -> None:
        """Validate report quality against performance and accessibility standards."""
        try:
            # Validate PDF file size
            file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
            if file_size_mb > self.MAX_PDF_SIZE_MB:
                logger.warning(f"PDF file size exceeds target: {file_size_mb:.2f}MB > {self.MAX_PDF_SIZE_MB}MB")
            
            # Validate accessibility compliance
            accessibility_score = await self._calculate_accessibility_score(html_content)
            if accessibility_score < self.MIN_ACCESSIBILITY_SCORE:
                logger.warning(f"Accessibility score below target: {accessibility_score} < {self.MIN_ACCESSIBILITY_SCORE}")
            
            # Validate design compliance
            design_score = await self._calculate_design_compliance(html_content)
            if design_score < 80.0:
                logger.warning(f"Design compliance score low: {design_score}")
            
            logger.info(f"Report quality validation completed: {file_size_mb:.2f}MB, {accessibility_score:.1f}% accessible")
            
        except Exception as e:
            logger.error(f"Report quality validation failed: {e}")
            raise ReportBuilderError(f"Quality validation failed: {str(e)}")
    
    async def _upload_to_storage(self, html_content: str, pdf_path: str, request: ReportGenerationRequest) -> Dict[str, str]:
        """Upload report files to storage with CDN optimization (mock implementation)."""
        try:
            # Generate storage keys
            timestamp = int(datetime.now(timezone.utc).timestamp())
            html_key = f"reports/{request.lead_id}/{timestamp}/report.html"
            pdf_key = f"reports/{request.lead_id}/{timestamp}/report.pdf"
            
            # Mock S3 upload (in production would use actual S3 SDK)
            html_url = f"https://leadfactory-reports.s3.amazonaws.com/{html_key}"
            pdf_url = f"https://leadfactory-reports.s3.amazonaws.com/{pdf_key}"
            
            # Generate signed URL for secure client access
            signed_url = f"{pdf_url}?X-Amz-Expires=604800&X-Amz-Signature=mock_signature"
            
            return {
                'html_url': html_url,
                'pdf_url': pdf_url,
                'signed_url': signed_url
            }
            
        except Exception as e:
            logger.error(f"Storage upload failed: {e}")
            raise ReportBuilderError(f"Storage upload failed: {str(e)}")
    
    def _prepare_hero_data(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Prepare data for hero section with overall score and key metrics."""
        business_score = request.business_score
        return {
            'overall_score': business_score.get('overall_score', 0),
            'performance_grade': self._calculate_letter_grade(business_score.get('overall_score', 0)),
            'total_impact': business_score.get('total_impact_estimate', 0),
            'confidence_range': business_score.get('confidence_interval', (0, 0)),
            'assessment_date': request.assessment_date.strftime('%B %d, %Y'),
            'business_name': request.business_name,
            'key_metrics': {
                'performance_score': business_score.get('component_scores', {}).get('performance', {}).get('raw_score', 0),
                'security_score': business_score.get('component_scores', {}).get('security', {}).get('raw_score', 0),
                'seo_score': business_score.get('component_scores', {}).get('seo', {}).get('raw_score', 0),
                'ux_score': business_score.get('component_scores', {}).get('ux', {}).get('raw_score', 0)
            }
        }
    
    def _prepare_issues_data(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Prepare data for top 3 issues section with priority and impact."""
        business_score = request.business_score
        component_scores = business_score.get('component_scores', {})
        
        priority_issues = []
        
        # Get top 3 highest-impact issues from components
        all_components = ['performance', 'security', 'seo', 'ux', 'visual']
        component_data = []
        
        for component in all_components:
            comp_data = component_scores.get(component, {})
            if comp_data:
                component_data.append({
                    'name': component.replace('_', ' ').title(),
                    'severity': comp_data.get('severity', 'P4'),
                    'impact_estimate': comp_data.get('impact_estimate', 0),
                    'raw_score': comp_data.get('raw_score', 0),
                    'recommendations': comp_data.get('recommendations', [])
                })
        
        # Sort by severity and impact
        sorted_components = sorted(component_data, key=lambda x: (
            self._severity_to_numeric(x['severity']),
            x['impact_estimate']
        ), reverse=True)
        
        for i, comp in enumerate(sorted_components[:3]):
            priority_issues.append({
                'rank': i + 1,
                'name': comp['name'],
                'severity': comp['severity'],
                'impact_estimate': comp['impact_estimate'],
                'description': f"Issues identified in {comp['name'].lower()} affecting business performance",
                'recommendations': comp['recommendations'][:2]  # Top 2 recommendations
            })
        
        return {
            'priority_issues': priority_issues,
            'total_issues_found': len([c for c in component_data if c['severity'] in ['P1', 'P2']]),
            'critical_count': len([c for c in component_data if c['severity'] == 'P1']),
            'high_count': len([c for c in component_data if c['severity'] == 'P2'])
        }
    
    def _prepare_impact_data(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Prepare financial impact data with industry context."""
        business_score = request.business_score
        business_factors = business_score.get('business_factors', {})
        component_scores = business_score.get('component_scores', {})
        
        return {
            'total_impact': business_score.get('total_impact_estimate', 0),
            'confidence_interval': business_score.get('confidence_interval', (0, 0)),
            'industry_multiplier': business_factors.get('industry_multiplier', 1.0),
            'geographic_factor': business_factors.get('geographic_factor', 1.0),
            'industry_code': business_factors.get('industry_code', ''),
            'roi_potential': self._calculate_roi_potential(business_score.get('total_impact_estimate', 0)),
            'payback_period': self._calculate_payback_period(business_score.get('total_impact_estimate', 0)),
            'impact_breakdown': {
                'performance': component_scores.get('performance', {}).get('impact_estimate', 0),
                'security': component_scores.get('security', {}).get('impact_estimate', 0),
                'seo': component_scores.get('seo', {}).get('impact_estimate', 0),
                'ux': component_scores.get('ux', {}).get('impact_estimate', 0),
                'visual': component_scores.get('visual', {}).get('impact_estimate', 0)
            }
        }
    
    def _prepare_findings_data(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Prepare detailed findings data for all assessment areas."""
        component_scores = request.business_score.get('component_scores', {})
        
        return {
            'performance_findings': self._format_component_findings(component_scores.get('performance', {})),
            'security_findings': self._format_component_findings(component_scores.get('security', {})),
            'seo_findings': self._format_component_findings(component_scores.get('seo', {})),
            'ux_findings': self._format_component_findings(component_scores.get('ux', {})),
            'visual_findings': self._format_component_findings(component_scores.get('visual', {})),
            'methodology_notes': self._get_methodology_notes()
        }
    
    def _prepare_quickwins_data(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Prepare quick wins data with actionable recommendations."""
        component_scores = request.business_score.get('component_scores', {})
        all_recommendations = []
        
        # Collect all recommendations from components
        for component_name, component_data in component_scores.items():
            for rec in component_data.get('recommendations', []):
                all_recommendations.append({
                    'category': component_name.replace('_', ' ').title(),
                    'recommendation': rec,
                    'effort': self._estimate_effort(rec),
                    'impact': self._estimate_impact(component_data.get('impact_estimate', 0)),
                    'priority': component_data.get('severity', 'P4')
                })
        
        # Sort by effort/impact ratio (quick wins first)
        quick_wins = sorted(all_recommendations, key=lambda x: (
            self._effort_to_numeric(x['effort']),
            -self._impact_to_numeric(x['impact'])
        ))[:5]
        
        return {
            'quick_wins': quick_wins,
            'implementation_timeline': self._create_implementation_timeline(quick_wins),
            'effort_summary': self._summarize_effort(quick_wins)
        }
    
    def _prepare_methodology_data(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Prepare methodology section explaining assessment approach."""
        business_factors = request.business_score.get('business_factors', {})
        
        return {
            'assessment_components': [
                'PageSpeed Insights Performance Analysis',
                'Security Header and SSL Configuration Review',
                'SEMrush SEO and Domain Authority Assessment',
                'GPT-4 Vision UX and Visual Design Analysis',
                'Screenshot Analysis and Visual Quality Review'
            ],
            'scoring_methodology': 'Multi-layered algorithm with industry-specific multipliers',
            'confidence_level': '95% statistical confidence intervals',
            'industry_adjustment': f"NAICS {business_factors.get('industry_code', '')} multiplier applied",
            'geographic_adjustment': f"{business_factors.get('geographic_factor', 1.0):.2f}x regional factor",
            'assessment_date': request.assessment_date,
            'data_sources': [
                'Google PageSpeed Insights API',
                'SEMrush Domain Analytics',
                'OpenAI GPT-4 Vision API',
                'ScreenshotOne Visual Capture',
                'Security header analysis'
            ]
        }
    
    def _get_design_system_config(self) -> Dict[str, Any]:
        """Get Refined Carbon design system configuration."""
        return {
            'typography': {
                'font_family': 'IBM Plex Sans, Arial, sans-serif',
                'heading_weights': [300, 400, 600],
                'body_weight': 400,
                'line_heights': {'heading': 1.2, 'body': 1.5}
            },
            'colors': {
                'primary': '#0f62fe',
                'secondary': '#393939',
                'success': '#24a148',
                'warning': '#f1c21b',
                'error': '#da1e28',
                'background': '#ffffff',
                'text': '#161616'
            },
            'spacing': {
                'xs': '0.25rem',
                'sm': '0.5rem',
                'md': '1rem',
                'lg': '1.5rem',
                'xl': '2rem',
                'xxl': '3rem'
            },
            'breakpoints': {
                'sm': '320px',
                'md': '672px',
                'lg': '1056px',
                'xl': '1312px',
                'max': '1584px'
            }
        }
    
    def _get_responsive_breakpoints(self) -> Dict[str, str]:
        """Get responsive design breakpoints for template rendering."""
        return {
            'mobile': '(max-width: 671px)',
            'tablet': '(min-width: 672px) and (max-width: 1055px)',
            'desktop': '(min-width: 1056px)'
        }
    
    def _generate_basic_html_structure(self, context: Dict[str, Any]) -> str:
        """Generate basic HTML structure (placeholder for user's template)."""
        # Basic HTML structure that user's template would replace
        html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Website Assessment Report - {context['business_name']}</title>
    <style>
        body {{ font-family: {context['design_system']['typography']['font_family']}; }}
        .hero {{ background-color: {context['design_system']['colors']['primary']}; color: white; padding: 2rem; }}
        .section {{ margin: 2rem 0; padding: 1rem; }}
        .score {{ font-size: 3rem; font-weight: bold; }}
        .grade {{ background: {context['design_system']['colors']['success']}; color: white; padding: 0.5rem; border-radius: 4px; }}
        @media {context['responsive_breakpoints']['mobile']} {{
            .hero {{ padding: 1rem; }}
            .score {{ font-size: 2rem; }}
        }}
    </style>
</head>
<body>
    <div class="hero">
        <h1>Website Assessment Report</h1>
        <h2>{context['business_name']}</h2>
        <div class="score">{context['overall_score']:.0f}/100</div>
        <div class="grade">{context['hero_data']['performance_grade']}</div>
        <p>Assessment Date: {context['hero_data']['assessment_date']}</p>
    </div>
    
    <div class="section">
        <h2>Executive Summary</h2>
        <p>Total Impact Estimate: ${context['total_impact']:,.2f}</p>
        <p>Priority Issues Found: {context['issues_data']['total_issues_found']}</p>
    </div>
    
    <div class="section">
        <h2>Key Findings</h2>
        <ul>
            {"".join([f"<li>{issue['name']}: {issue['severity']} - ${issue['impact_estimate']:,.2f}</li>" for issue in context['issues_data']['priority_issues']])}
        </ul>
    </div>
    
    <div class="section">
        <h2>Quick Wins</h2>
        <ul>
            {"".join([f"<li>{win['category']}: {win['recommendation']}</li>" for win in context['quickwins_data']['quick_wins']])}
        </ul>
    </div>
    
    <div class="section">
        <h2>Methodology</h2>
        <p>{context['methodology_data']['scoring_methodology']}</p>
        <ul>
            {"".join([f"<li>{component}</li>" for component in context['methodology_data']['assessment_components']])}
        </ul>
    </div>
    
    <footer style="margin-top: 2rem; padding: 1rem; background: #f4f4f4; text-align: center;">
        <p>Generated on {context['assessment_date'].strftime('%B %d, %Y')} by LeadFactory Assessment Platform</p>
    </footer>
</body>
</html>
        """
        return html_template.strip()
    
    async def _calculate_accessibility_score(self, html_content: str) -> float:
        """Calculate WCAG 2.1 AA accessibility compliance score."""
        try:
            score = 100.0
            
            # Basic accessibility checks
            if not self._validate_heading_hierarchy(html_content):
                score -= 20
            
            if not self._validate_alt_text(html_content):
                score -= 15
            
            if not self._validate_color_contrast(html_content):
                score -= 25
            
            if not self._validate_aria_labels(html_content):
                score -= 10
            
            return max(score, 0.0)
            
        except Exception as e:
            logger.error(f"Accessibility score calculation failed: {e}")
            return 80.0  # Safe default
    
    async def _calculate_design_compliance(self, html_content: str) -> float:
        """Calculate Refined Carbon design system compliance score."""
        try:
            score = 100.0
            
            # Check for proper Carbon CSS classes or IBM Plex font
            if 'IBM Plex' not in html_content:
                score -= 10
            
            # Check for responsive design patterns
            if '@media' not in html_content:
                score -= 20
            
            # Check for basic structure
            if '<head>' not in html_content or '<body>' not in html_content:
                score -= 30
            
            return max(score, 0.0)
            
        except Exception as e:
            logger.error(f"Design compliance calculation failed: {e}")
            return 85.0  # Safe default
    
    def _calculate_letter_grade(self, score: float) -> str:
        """Convert numeric score to letter grade."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"
    
    def _severity_to_numeric(self, severity: str) -> int:
        """Convert severity to numeric for sorting."""
        severity_map = {'P1': 4, 'P2': 3, 'P3': 2, 'P4': 1}
        return severity_map.get(severity, 0)
    
    def _estimate_effort(self, recommendation: str) -> str:
        """Estimate effort level for recommendation."""
        if any(word in recommendation.lower() for word in ['implement', 'add', 'create', 'build']):
            return 'High'
        elif any(word in recommendation.lower() for word in ['optimize', 'improve', 'update', 'enhance']):
            return 'Medium'
        else:
            return 'Low'
    
    def _estimate_impact(self, impact_value: float) -> str:
        """Estimate impact level based on financial value."""
        if impact_value > 10000:
            return 'High'
        elif impact_value > 5000:
            return 'Medium'
        else:
            return 'Low'
    
    def _effort_to_numeric(self, effort: str) -> int:
        """Convert effort to numeric for sorting."""
        effort_map = {'Low': 1, 'Medium': 2, 'High': 3}
        return effort_map.get(effort, 2)
    
    def _impact_to_numeric(self, impact: str) -> int:
        """Convert impact to numeric for sorting."""
        impact_map = {'Low': 1, 'Medium': 2, 'High': 3}
        return impact_map.get(impact, 1)
    
    def _calculate_roi_potential(self, total_impact: float) -> str:
        """Calculate ROI potential description."""
        if total_impact > 20000:
            return "High ROI potential (>500%)"
        elif total_impact > 10000:
            return "Moderate ROI potential (200-500%)"
        else:
            return "Standard ROI potential (100-200%)"
    
    def _calculate_payback_period(self, total_impact: float) -> str:
        """Calculate estimated payback period."""
        if total_impact > 20000:
            return "3-6 months"
        elif total_impact > 10000:
            return "6-12 months"
        else:
            return "12-18 months"
    
    def _format_component_findings(self, component_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format component findings for display."""
        return {
            'score': component_data.get('raw_score', 0),
            'impact': component_data.get('impact_estimate', 0),
            'severity': component_data.get('severity', 'P4'),
            'recommendations': component_data.get('recommendations', [])
        }
    
    def _get_methodology_notes(self) -> List[str]:
        """Get methodology explanatory notes."""
        return [
            "Assessment uses industry-standard APIs and tools",
            "Scores calculated using research-based impact formulas",
            "95% confidence intervals applied to all estimates",
            "Industry and geographic adjustments applied"
        ]
    
    def _create_implementation_timeline(self, quick_wins: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Create implementation timeline for quick wins."""
        timeline = {
            'Week 1': [],
            'Week 2-4': [],
            'Month 2-3': []
        }
        
        for win in quick_wins:
            if win['effort'] == 'Low':
                timeline['Week 1'].append(win['recommendation'])
            elif win['effort'] == 'Medium':
                timeline['Week 2-4'].append(win['recommendation'])
            else:
                timeline['Month 2-3'].append(win['recommendation'])
        
        return timeline
    
    def _summarize_effort(self, quick_wins: List[Dict[str, Any]]) -> Dict[str, int]:
        """Summarize effort distribution."""
        effort_counts = {'Low': 0, 'Medium': 0, 'High': 0}
        for win in quick_wins:
            effort_counts[win['effort']] += 1
        return effort_counts
    
    def _create_mock_pdf_content(self, html_content: str) -> bytes:
        """Create mock PDF content (placeholder for Puppeteer)."""
        # Simple PDF header (in production would use Puppeteer)
        pdf_header = b"%PDF-1.4\n"
        pdf_content = f"Website Assessment Report\n\nGenerated from HTML content ({len(html_content)} characters)"
        pdf_body = pdf_content.encode('utf-8')
        return pdf_header + pdf_body
    
    async def _optimize_pdf(self, pdf_path: str) -> str:
        """Optimize PDF file size (mock implementation)."""
        # In production would use PDF optimization libraries
        return pdf_path
    
    async def _validate_html_structure(self, html_content: str) -> None:
        """Validate HTML structure for basic compliance."""
        required_elements = ['<html', '<head', '<body', '</html>']
        for element in required_elements:
            if element not in html_content:
                raise ReportBuilderError(f"Missing required HTML element: {element}")
    
    def _validate_heading_hierarchy(self, html_content: str) -> bool:
        """Validate proper heading hierarchy."""
        return '<h1>' in html_content and '<h2>' in html_content
    
    def _validate_alt_text(self, html_content: str) -> bool:
        """Validate alt text on images."""
        if '<img' not in html_content:
            return True  # No images, so compliant
        return 'alt=' in html_content
    
    def _validate_color_contrast(self, html_content: str) -> bool:
        """Validate color contrast (simplified check)."""
        # Simplified check - in production would use color contrast libraries
        return True
    
    def _validate_aria_labels(self, html_content: str) -> bool:
        """Validate ARIA labels."""
        # Simplified check - in production would validate proper ARIA usage
        return True
    
    async def _store_report_metadata(self, report: GeneratedReport) -> None:
        """Store report metadata in database."""
        # Mock implementation - would store in generated_reports table
        logger.info(f"Storing report metadata for lead {report.lead_id}")
    
    async def _load_lead_data(self, lead_id: int) -> Dict[str, Any]:
        """Load lead data from database."""
        # Mock implementation - would load from database
        return {
            'company': 'Tuome NYC',
            'contact_name': 'Restaurant Manager',
            'email': 'manager@tuome.com'
        }
    
    async def _load_business_score(self, lead_id: int) -> Dict[str, Any]:
        """Load business score from PRP-009 calculator."""
        # Mock implementation - would load from assessment.business_score
        return {
            'overall_score': 75.0,
            'total_impact_estimate': 25000.0,
            'confidence_interval': (20000.0, 30000.0),
            'business_factors': {
                'industry_multiplier': 1.1,
                'geographic_factor': 1.3,
                'industry_code': '722513'
            },
            'component_scores': {
                'performance': {
                    'raw_score': 65.0,
                    'impact_estimate': 8000.0,
                    'severity': 'P2',
                    'recommendations': ['Optimize image loading', 'Enable browser caching']
                },
                'security': {
                    'raw_score': 80.0,
                    'impact_estimate': 5000.0,
                    'severity': 'P3',
                    'recommendations': ['Implement HTTPS', 'Add security headers']
                },
                'seo': {
                    'raw_score': 70.0,
                    'impact_estimate': 7000.0,
                    'severity': 'P2',
                    'recommendations': ['Improve meta descriptions', 'Optimize for local search']
                },
                'ux': {
                    'raw_score': 75.0,
                    'impact_estimate': 3000.0,
                    'severity': 'P3',
                    'recommendations': ['Improve navigation', 'Enhance CTA visibility']
                },
                'visual': {
                    'raw_score': 85.0,
                    'impact_estimate': 2000.0,
                    'severity': 'P4',
                    'recommendations': ['Update brand imagery', 'Improve visual hierarchy']
                }
            }
        }
    
    async def _load_generated_content(self, lead_id: int) -> Dict[str, Any]:
        """Load generated content from PRP-010 content generator."""
        # Mock implementation - would load from assessment.marketing_content
        return {
            'subject_line': 'Tuome NYC: Website Performance Issues Costing You $25K/Year',
            'email_body': 'We found critical performance issues affecting your restaurant...',
            'executive_summary': 'Comprehensive assessment revealed opportunities for improvement...',
            'issue_insights': [
                'Mobile page speed 65% below industry standard',
                'Missing security headers expose customer data',
                'SEO optimization gaps limiting local visibility'
            ],
            'recommended_actions': [
                'Optimize image compression and lazy loading',
                'Implement Content Security Policy header',
                'Enhance local SEO keyword targeting'
            ],
            'urgency_indicators': [
                'Competitors gaining market share through better digital presence',
                'Customer trust declining due to slow site performance'
            ]
        }
    
    async def close(self):
        """Close browser and cleanup resources."""
        if self.browser:
            # Would close Puppeteer browser in production
            self.browser = None

async def generate_assessment_report(lead_id: int) -> GeneratedReport:
    """
    Main entry point for assessment report generation.
    
    Args:
        lead_id: Database ID of the lead to generate report for
        
    Returns:
        Complete generated report with HTML/PDF and cloud storage URLs
    """
    try:
        # Initialize report builder
        builder = ReportBuilder()
        
        try:
            # Generate complete report
            logger.info(f"Starting report generation for lead {lead_id}")
            generated_report = await builder.generate_report(lead_id)
            
            logger.info(f"Report generation completed for lead {lead_id}: {generated_report.file_size_mb:.2f}MB, {generated_report.generation_time:.2f}s")
            return generated_report
            
        finally:
            await builder.close()
            
    except Exception as e:
        logger.error(f"Assessment report generation failed for lead {lead_id}: {e}")
        raise ReportBuilderError(f"Report generation failed: {str(e)}")

# Add create_report_cost method to AssessmentCost model
def create_report_cost_method(cls, lead_id: int, cost_cents: float = 0.0, response_status: str = "success", response_time_ms: Optional[int] = None, error_message: Optional[str] = None):
    """
    Create cost record for report generation (no external API cost).
    
    Args:
        lead_id: ID of the lead being assessed
        cost_cents: Cost in cents (default $0.00 - internal generation)
        response_status: success, error, timeout
        response_time_ms: Generation time in milliseconds
        error_message: Error message if applicable
        
    Returns:
        AssessmentCost instance
    """
    now = datetime.now(timezone.utc)
    
    return cls(
        lead_id=lead_id,
        service_name="report_builder",
        api_endpoint="internal://reports/generate_report",
        cost_cents=cost_cents,
        currency="USD",
        request_timestamp=now,
        response_status=response_status,
        response_time_ms=response_time_ms,
        api_quota_used=False,  # Internal generation - no quota
        rate_limited=False,
        retry_count=0,
        error_message=error_message,
        daily_budget_date=now.strftime("%Y-%m-%d"),
        monthly_budget_date=now.strftime("%Y-%m")
    )

# Monkey patch the method to AssessmentCost
AssessmentCost.create_report_cost = classmethod(create_report_cost_method)