# PRP-011: Report Builder

## Task ID: PRP-011

## Wave: Foundation Services

## Business Logic

The LeadFactory audit platform requires professional HTML/PDF report generation to transform business assessment results into compelling, visually-rich audit reports that justify $399 pricing and demonstrate clear value to clients. This report builder leverages Refined Carbon design system with Jinja2 templating to create 6-section reports (hero with score, top 3 issues, financial impact, detailed findings, quick wins, methodology) with <10 second generation times, <2MB PDF optimization, and WCAG 2.1 AA accessibility compliance. The system integrates with AWS S3 for secure document storage and provides the essential deliverable that converts technical assessment data into professional business documents for client engagement and sales conversion.

## Overview

Implement professional report generation system with modern design standards for:
- 6-section report structure using Refined Carbon design system with responsive HTML/CSS grid layout
- HTML to PDF conversion using Puppeteer for superior rendering quality and full CSS3/JavaScript support
- Jinja2 template engine with inheritance patterns, macro libraries, and performance caching strategies
- File size optimization maintaining <2MB PDFs through automated compression without quality degradation
- WCAG 2.1 AA accessibility compliance with proper heading hierarchy, alt-text, and keyboard navigation
- AWS S3 Express One Zone integration for high-performance document storage and CDN delivery
- Sub-10 second generation performance through multi-tier caching and async processing architecture
- Professional business intelligence design principles with mobile-first responsive layouts

## Dependencies

- **External**: Puppeteer/Chrome headless, AWS S3 storage, Refined Carbon design system components
- **Internal**: PRP-000 (AWS S3 Bucket Setup) for document storage, PRP-010 (LLM Content Generator) for report content
- **Blockers**: None

## Outcome-Focused Acceptance Criteria

1. **Report Builder Operational**: `ReportBuilder().generate_report(lead_id)` creates professional HTML/PDF reports with all 6 sections and proper visual hierarchy
2. **Design System Compliance**: Generated reports match Refined Carbon design standards with consistent typography, color scheme, and component usage
3. **PDF Optimization Achieved**: All generated PDFs maintain <2MB file size through automated compression while preserving professional visual quality
4. **Accessibility Standards Met**: Reports comply with WCAG 2.1 AA requirements including proper heading structure, color contrast ratios ≥4.5:1, and screen reader compatibility
5. **Performance Requirements Met**: Report generation completes within 10 seconds including HTML rendering, PDF conversion, and S3 upload processes
6. **S3 Integration Functional**: Reports automatically uploaded to S3 with signed URLs, CDN optimization, and proper access control for client delivery
7. **Responsive Design Working**: HTML reports render correctly across devices (mobile, tablet, desktop) with appropriate layout adaptations
8. **Template Management Active**: Jinja2 templates with inheritance patterns, macro libraries, and version control for design consistency
9. **Database Integration Complete**: Report metadata stored in PostgreSQL with generation history, access tracking, and performance metrics
10. **Production Deployment Ready**: Containerized architecture with horizontal scaling, error handling, monitoring, and automated backup strategies

## Integration Points

### Report Generation Engine (Core Service)
- **Location**: `src/reports/builder.py`, `src/reports/models.py`
- **Dependencies**: Puppeteer, Jinja2, Refined Carbon CSS, image processing libraries
- **Functions**: generate_report(), create_html(), convert_to_pdf(), optimize_file_size(), upload_to_s3()

### Template Management System (Design Framework)
- **Location**: `src/reports/templates/`, `src/reports/template_manager.py`
- **Dependencies**: Jinja2 with inheritance, Refined Carbon components, responsive CSS grid
- **Functions**: load_templates(), render_sections(), apply_design_system(), validate_accessibility()

### PDF Processing Pipeline (Document Conversion)
- **Location**: `src/reports/pdf_processor.py`, `src/reports/optimization.py`
- **Dependencies**: Puppeteer Chrome headless, compression libraries, quality validators
- **Functions**: html_to_pdf(), compress_document(), validate_quality(), ensure_accessibility()

### S3 Document Storage (Cloud Integration)
- **Location**: `src/reports/storage_manager.py`
- **Dependencies**: AWS S3 SDK, CloudFront CDN, access control policies
- **Functions**: upload_document(), generate_signed_urls(), manage_access(), configure_cdn()

## Implementation Requirements

### Report Generation Engine Implementation

**Core Report Builder**:
```python
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tempfile
import base64

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pyppeteer import launch
import boto3
from PIL import Image
import io

from src.reports.template_manager import TemplateManager
from src.reports.pdf_processor import PDFProcessor
from src.reports.storage_manager import S3StorageManager
from src.scoring.calculator import BusinessImpactScore
from src.content.llm_generator import GeneratedContent

@dataclass
class ReportGenerationRequest:
    """Report generation request with all required data."""
    lead_id: int
    business_name: str
    contact_name: str
    assessment_date: datetime
    business_score: BusinessImpactScore
    generated_content: GeneratedContent
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
    
    def __init__(self):
        """Initialize report builder with required services."""
        self.template_manager = TemplateManager()
        self.pdf_processor = PDFProcessor()
        self.storage_manager = S3StorageManager()
        
        # Browser instance for PDF generation
        self.browser = None
        
        logging.info("Report Builder initialized with Refined Carbon design system")
    
    async def generate_report(self, lead_id: int) -> GeneratedReport:
        """
        Generate complete HTML/PDF report with professional design and accessibility.
        
        Args:
            lead_id: Database ID of the lead for report generation
            
        Returns:
            GeneratedReport: Complete report package with cloud storage URLs
        """
        start_time = datetime.utcnow()
        
        try:
            # Prepare report generation request
            request = await self._prepare_generation_request(lead_id)
            
            # Generate HTML content
            html_content = await self._generate_html_report(request)
            
            # Convert to PDF with optimization
            pdf_file_path = await self._generate_pdf_report(html_content, request)
            
            # Validate file size and quality
            await self._validate_report_quality(pdf_file_path, html_content)
            
            # Upload to S3 with CDN optimization
            s3_urls = await self._upload_to_s3(html_content, pdf_file_path, request)
            
            # Calculate performance metrics
            generation_time = (datetime.utcnow() - start_time).total_seconds()
            file_size_mb = Path(pdf_file_path).stat().st_size / (1024 * 1024)
            
            # Validate performance targets
            if generation_time > self.MAX_GENERATION_TIME:
                logging.warning(f"Report generation exceeded target: {generation_time:.2f}s > {self.MAX_GENERATION_TIME}s")
            
            if file_size_mb > self.MAX_PDF_SIZE_MB:
                logging.warning(f"PDF file size exceeded target: {file_size_mb:.2f}MB > {self.MAX_PDF_SIZE_MB}MB")
            
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
            
            logging.info(f"Report generated for lead {lead_id}: {file_size_mb:.2f}MB, {generation_time:.2f}s")
            return report
            
        except Exception as e:
            logging.error(f"Report generation failed for lead {lead_id}: {e}")
            raise
        finally:
            # Cleanup temporary files
            if 'pdf_file_path' in locals() and Path(pdf_file_path).exists():
                Path(pdf_file_path).unlink()
    
    async def _prepare_generation_request(self, lead_id: int) -> ReportGenerationRequest:
        """Prepare report generation request with all required data."""
        # Load lead data
        lead_data = await self._load_lead_data(lead_id)
        
        # Load business score from calculator
        business_score = await self._load_business_score(lead_id)
        
        # Load generated content from content generator
        generated_content = await self._load_generated_content(lead_id)
        
        return ReportGenerationRequest(
            lead_id=lead_id,
            business_name=lead_data.get('company_name', 'Business'),
            contact_name=lead_data.get('contact_name', 'Business Owner'),
            assessment_date=datetime.utcnow(),
            business_score=business_score,
            generated_content=generated_content
        )
    
    async def _generate_html_report(self, request: ReportGenerationRequest) -> str:
        """Generate complete HTML report using Jinja2 templates and Refined Carbon design."""
        try:
            # Prepare template context
            context = {
                'business_name': request.business_name,
                'contact_name': request.contact_name,
                'assessment_date': request.assessment_date,
                'overall_score': request.business_score.overall_score,
                'total_impact': request.business_score.total_impact_estimate,
                'confidence_range': request.business_score.confidence_interval,
                
                # Section-specific data
                'hero_data': self._prepare_hero_data(request),
                'issues_data': self._prepare_issues_data(request),
                'impact_data': self._prepare_impact_data(request),
                'findings_data': self._prepare_findings_data(request),
                'quickwins_data': self._prepare_quickwins_data(request),
                'methodology_data': self._prepare_methodology_data(request),
                
                # Design system variables
                'design_system': self._get_design_system_config(),
                'responsive_breakpoints': self._get_responsive_breakpoints()
            }
            
            # Load main report template
            main_template = await self.template_manager.get_template('main_report.html')
            
            # Render complete HTML report
            html_content = await self.template_manager.render_template(
                template_name='main_report.html',
                context=context
            )
            
            # Validate HTML structure and accessibility
            await self._validate_html_structure(html_content)
            
            return html_content
            
        except Exception as e:
            logging.error(f"HTML report generation failed: {e}")
            raise
    
    async def _generate_pdf_report(self, html_content: str, request: ReportGenerationRequest) -> str:
        """Convert HTML to PDF using Puppeteer with optimization."""
        try:
            # Create temporary file for PDF output
            temp_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            pdf_path = temp_pdf.name
            temp_pdf.close()
            
            # Initialize browser if not already done
            if self.browser is None:
                self.browser = await launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
            
            # Create new page
            page = await self.browser.newPage()
            
            try:
                # Configure page for high-quality PDF
                await page.setViewport({'width': 1200, 'height': 800})
                
                # Load HTML content
                await page.setContent(html_content, {
                    'waitUntil': ['networkidle0', 'domcontentloaded']
                })
                
                # Generate PDF with professional settings
                await page.pdf({
                    'path': pdf_path,
                    'format': 'A4',
                    'printBackground': True,
                    'margin': {
                        'top': '20mm',
                        'right': '15mm',
                        'bottom': '20mm',
                        'left': '15mm'
                    },
                    'preferCSSPageSize': True,
                    'displayHeaderFooter': True,
                    'headerTemplate': await self._get_header_template(request),
                    'footerTemplate': await self._get_footer_template(request)
                })
                
            finally:
                await page.close()
            
            # Optimize PDF file size
            optimized_path = await self.pdf_processor.optimize_pdf(pdf_path)
            
            # Replace original with optimized version
            if optimized_path != pdf_path:
                Path(pdf_path).unlink()
                pdf_path = optimized_path
            
            return pdf_path
            
        except Exception as e:
            logging.error(f"PDF generation failed: {e}")
            raise
    
    async def _validate_report_quality(self, pdf_path: str, html_content: str) -> None:
        """Validate report quality against performance and accessibility standards."""
        try:
            # Validate PDF file size
            file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
            if file_size_mb > self.MAX_PDF_SIZE_MB:
                raise ValueError(f"PDF file size exceeds limit: {file_size_mb:.2f}MB > {self.MAX_PDF_SIZE_MB}MB")
            
            # Validate accessibility compliance
            accessibility_score = await self._calculate_accessibility_score(html_content)
            if accessibility_score < self.MIN_ACCESSIBILITY_SCORE:
                logging.warning(f"Accessibility score below target: {accessibility_score} < {self.MIN_ACCESSIBILITY_SCORE}")
            
            # Validate design compliance
            design_score = await self._calculate_design_compliance(html_content)
            if design_score < 80.0:
                logging.warning(f"Design compliance score low: {design_score}")
            
            logging.info(f"Report quality validation passed: {file_size_mb:.2f}MB, {accessibility_score:.1f}% accessible")
            
        except Exception as e:
            logging.error(f"Report quality validation failed: {e}")
            raise
    
    async def _upload_to_s3(self, html_content: str, pdf_path: str, request: ReportGenerationRequest) -> Dict[str, str]:
        """Upload report files to S3 with CDN optimization."""
        try:
            # Generate S3 keys
            timestamp = int(datetime.utcnow().timestamp())
            html_key = f"reports/{request.lead_id}/{timestamp}/report.html"
            pdf_key = f"reports/{request.lead_id}/{timestamp}/report.pdf"
            
            # Upload HTML file
            html_url = await self.storage_manager.upload_content(
                content=html_content,
                key=html_key,
                content_type='text/html',
                metadata={
                    'lead_id': str(request.lead_id),
                    'business_name': request.business_name,
                    'report_type': 'assessment_report'
                }
            )
            
            # Upload PDF file
            pdf_url = await self.storage_manager.upload_file(
                file_path=pdf_path,
                key=pdf_key,
                content_type='application/pdf',
                metadata={
                    'lead_id': str(request.lead_id),
                    'business_name': request.business_name,
                    'report_type': 'assessment_report'
                }
            )
            
            # Generate signed URL for secure client access
            signed_url = await self.storage_manager.generate_signed_url(
                key=pdf_key,
                expiration=3600 * 24 * 7  # 7 days
            )
            
            return {
                'html_url': html_url,
                'pdf_url': pdf_url,
                'signed_url': signed_url
            }
            
        except Exception as e:
            logging.error(f"S3 upload failed: {e}")
            raise
    
    def _prepare_hero_data(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Prepare data for hero section with overall score and key metrics."""
        return {
            'overall_score': request.business_score.overall_score,
            'performance_grade': self._calculate_letter_grade(request.business_score.overall_score),
            'total_impact': request.business_score.total_impact_estimate,
            'confidence_range': request.business_score.confidence_interval,
            'assessment_date': request.assessment_date.strftime('%B %d, %Y'),
            'business_name': request.business_name,
            'key_metrics': {
                'performance_score': request.business_score.performance_score.raw_score,
                'security_score': request.business_score.security_score.raw_score,
                'seo_score': request.business_score.seo_score.raw_score,
                'ux_score': request.business_score.ux_score.raw_score
            }
        }
    
    def _prepare_issues_data(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Prepare data for top 3 issues section with priority and impact."""
        priority_issues = []
        
        # Get top 3 highest-impact issues
        all_scores = [
            request.business_score.performance_score,
            request.business_score.security_score,
            request.business_score.seo_score,
            request.business_score.ux_score,
            request.business_score.visual_score
        ]
        
        # Sort by severity and impact
        sorted_scores = sorted(all_scores, key=lambda x: (
            self._severity_to_numeric(x.severity),
            x.impact_estimate
        ), reverse=True)
        
        for i, score in enumerate(sorted_scores[:3]):
            priority_issues.append({
                'rank': i + 1,
                'name': score.name.replace('_', ' ').title(),
                'severity': score.severity,
                'impact_estimate': score.impact_estimate,
                'confidence_range': score.confidence_interval,
                'description': self._get_issue_description(score),
                'recommendations': score.recommendations[:2]  # Top 2 recommendations
            })
        
        return {
            'priority_issues': priority_issues,
            'total_issues_found': len([s for s in all_scores if s.severity in ['P1', 'P2']]),
            'critical_count': len([s for s in all_scores if s.severity == 'P1']),
            'high_count': len([s for s in all_scores if s.severity == 'P2'])
        }
    
    def _prepare_impact_data(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Prepare financial impact data with industry context."""
        return {
            'total_impact': request.business_score.total_impact_estimate,
            'confidence_interval': request.business_score.confidence_interval,
            'industry_multiplier': request.business_score.industry_multiplier,
            'geographic_factor': request.business_score.geographic_factor,
            'industry_code': request.business_score.industry_code,
            'roi_potential': self._calculate_roi_potential(request.business_score),
            'payback_period': self._calculate_payback_period(request.business_score),
            'impact_breakdown': {
                'performance': request.business_score.performance_score.impact_estimate,
                'security': request.business_score.security_score.impact_estimate,
                'seo': request.business_score.seo_score.impact_estimate,
                'ux': request.business_score.ux_score.impact_estimate,
                'visual': request.business_score.visual_score.impact_estimate
            }
        }
    
    def _prepare_findings_data(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Prepare detailed findings data for all assessment areas."""
        return {
            'performance_findings': self._format_component_findings(request.business_score.performance_score),
            'security_findings': self._format_component_findings(request.business_score.security_score),
            'seo_findings': self._format_component_findings(request.business_score.seo_score),
            'ux_findings': self._format_component_findings(request.business_score.ux_score),
            'visual_findings': self._format_component_findings(request.business_score.visual_score),
            'methodology_notes': self._get_methodology_notes()
        }
    
    def _prepare_quickwins_data(self, request: ReportGenerationRequest) -> Dict[str, Any]:
        """Prepare quick wins data with actionable recommendations."""
        all_recommendations = []
        
        # Collect all recommendations from components
        for component in [
            request.business_score.performance_score,
            request.business_score.security_score,
            request.business_score.seo_score,
            request.business_score.ux_score,
            request.business_score.visual_score
        ]:
            for rec in component.recommendations:
                all_recommendations.append({
                    'category': component.name.replace('_', ' ').title(),
                    'recommendation': rec,
                    'effort': self._estimate_effort(rec),
                    'impact': self._estimate_impact(component.impact_estimate),
                    'priority': component.severity
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
        return {
            'assessment_components': [
                'PageSpeed Insights Performance Analysis',
                'Security Header and SSL Configuration Review',
                'SEMrush SEO and Domain Authority Assessment',
                'GPT-4 Vision UX and Visual Design Analysis',
                'Google Business Profile Local Presence Evaluation'
            ],
            'scoring_methodology': 'Multi-layered algorithm with industry-specific multipliers',
            'confidence_level': '95% statistical confidence intervals',
            'industry_adjustment': f"NAICS {request.business_score.industry_code} multiplier applied",
            'geographic_adjustment': f"{request.business_score.geographic_factor:.2f}x regional factor",
            'assessment_date': request.assessment_date,
            'data_sources': [
                'Google PageSpeed Insights API',
                'SEMrush Domain Analytics',
                'OpenAI GPT-4 Vision API',
                'Security header analysis',
                'Google Business Profile API'
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
    
    async def _calculate_accessibility_score(self, html_content: str) -> float:
        """Calculate WCAG 2.1 AA accessibility compliance score."""
        try:
            # Basic accessibility checks (would be more comprehensive in production)
            score = 100.0
            
            # Check for proper heading hierarchy
            if not self._validate_heading_hierarchy(html_content):
                score -= 20
            
            # Check for alt text on images
            if not self._validate_alt_text(html_content):
                score -= 15
            
            # Check for color contrast (simplified check)
            if not self._validate_color_contrast(html_content):
                score -= 25
            
            # Check for proper ARIA labels
            if not self._validate_aria_labels(html_content):
                score -= 10
            
            return max(score, 0.0)
            
        except Exception as e:
            logging.error(f"Accessibility score calculation failed: {e}")
            return 80.0  # Safe default
    
    async def _calculate_design_compliance(self, html_content: str) -> float:
        """Calculate Refined Carbon design system compliance score."""
        try:
            score = 100.0
            
            # Check for proper Carbon CSS classes
            if 'bx--' not in html_content and 'cds--' not in html_content:
                score -= 30  # No Carbon design system classes found
            
            # Check for responsive design patterns
            if '@media' not in html_content:
                score -= 20  # No responsive design
            
            # Check for proper typography
            if 'IBM Plex' not in html_content:
                score -= 10  # Not using Carbon typography
            
            return max(score, 0.0)
            
        except Exception as e:
            logging.error(f"Design compliance calculation failed: {e}")
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
    
    async def _store_report_metadata(self, report: GeneratedReport) -> None:
        """Store report metadata in database."""
        # Implementation would store in database
        logging.info(f"Storing report metadata for lead {report.lead_id}")
        pass
    
    async def _load_lead_data(self, lead_id: int) -> Dict[str, Any]:
        """Load lead data from database."""
        # Mock implementation - would load from database
        return {
            'company_name': 'Example Business',
            'contact_name': 'John Smith',
            'email': 'john@example.com'
        }
    
    async def _load_business_score(self, lead_id: int) -> BusinessImpactScore:
        """Load business score from calculator."""
        # Mock implementation - would load from database
        from src.scoring.calculator import ScoreComponent
        
        # Create mock business score for demonstration
        mock_score = type('MockBusinessScore', (), {})()
        mock_score.overall_score = 75.0
        mock_score.total_impact_estimate = 25000.0
        mock_score.confidence_interval = (20000.0, 30000.0)
        mock_score.industry_multiplier = 1.5
        mock_score.geographic_factor = 1.2
        mock_score.industry_code = '541511'
        
        # Mock component scores
        mock_score.performance_score = ScoreComponent(
            name="performance",
            raw_score=65.0,
            impact_estimate=8000.0,
            confidence_interval=(6500.0, 9500.0),
            severity="P2",
            recommendations=["Optimize image loading", "Enable browser caching"]
        )
        
        mock_score.security_score = ScoreComponent(
            name="security",
            raw_score=80.0,
            impact_estimate=5000.0,
            confidence_interval=(4000.0, 6000.0),
            severity="P3",
            recommendations=["Implement HTTPS", "Add security headers"]
        )
        
        mock_score.seo_score = ScoreComponent(
            name="seo",
            raw_score=70.0,
            impact_estimate=7000.0,
            confidence_interval=(5500.0, 8500.0),
            severity="P2",
            recommendations=["Improve meta descriptions", "Optimize for local search"]
        )
        
        mock_score.ux_score = ScoreComponent(
            name="ux",
            raw_score=75.0,
            impact_estimate=3000.0,
            confidence_interval=(2500.0, 3500.0),
            severity="P3",
            recommendations=["Improve navigation", "Enhance CTA visibility"]
        )
        
        mock_score.visual_score = ScoreComponent(
            name="visual",
            raw_score=85.0,
            impact_estimate=2000.0,
            confidence_interval=(1500.0, 2500.0),
            severity="P4",
            recommendations=["Update brand imagery", "Improve visual hierarchy"]
        )
        
        return mock_score
    
    async def _load_generated_content(self, lead_id: int) -> GeneratedContent:
        """Load generated content from content generator."""
        # Mock implementation - would load from database
        return None
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with browser cleanup."""
        if self.browser:
            await self.browser.close()
            self.browser = None
```

### Template Management System

**Jinja2 Template Manager Implementation**:
```python
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape, meta
from datetime import datetime

class TemplateManager:
    """Advanced Jinja2 template management with Refined Carbon design system integration."""
    
    def __init__(self, templates_dir: str = "src/reports/templates"):
        """Initialize template manager with Jinja2 environment and Carbon components."""
        self.templates_dir = Path(templates_dir)
        
        # Create Jinja2 environment with enhanced features
        self.env = Environment(
            loader=FileSystemLoader([
                self.templates_dir,
                self.templates_dir / "components",
                self.templates_dir / "layouts"
            ]),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        # Add custom filters and functions
        self._add_custom_filters()
        self._add_global_functions()
        
        # Load template metadata and Carbon components
        self.template_metadata = self._load_template_metadata()
        self.carbon_components = self._load_carbon_components()
        
        logging.info(f"Template Manager initialized with {len(self.template_metadata)} templates")
    
    async def get_template(self, template_name: str) -> str:
        """Get template content by name with Carbon design system integration."""
        try:
            template_file = f"{template_name}"
            if not template_file.endswith('.html'):
                template_file += '.html'
            
            template_path = self.templates_dir / template_file
            
            if template_path.exists():
                return template_path.read_text()
            else:
                return self._get_default_template(template_name)
                
        except Exception as e:
            logging.error(f"Template loading failed for {template_name}: {e}")
            return self._get_default_template(template_name)
    
    async def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render template with context and Carbon design system variables."""
        try:
            # Add Carbon design system context
            enhanced_context = {
                **context,
                'carbon': self.carbon_components,
                'current_year': datetime.utcnow().year,
                'template_version': self.template_metadata.get('version', '1.0.0'),
                'accessibility': self._get_accessibility_helpers()
            }
            
            # Load and render template
            template = self.env.get_template(f"{template_name}.html")
            rendered_content = template.render(**enhanced_context)
            
            # Validate rendered content
            await self._validate_rendered_content(rendered_content)
            
            return rendered_content
            
        except Exception as e:
            logging.error(f"Template rendering failed for {template_name}: {e}")
            raise
    
    def _add_custom_filters(self) -> None:
        """Add custom Jinja2 filters for report generation."""
        
        @self.env.filter
        def currency(value):
            """Format value as currency."""
            try:
                return f"${float(value):,.2f}"
            except (ValueError, TypeError):
                return "$0.00"
        
        @self.env.filter
        def percentage(value):
            """Format value as percentage."""
            try:
                return f"{float(value):.1f}%"
            except (ValueError, TypeError):
                return "0.0%"
        
        @self.env.filter
        def grade_color(grade):
            """Get color class for letter grade."""
            color_map = {
                'A': 'success',
                'B': 'info', 
                'C': 'warning',
                'D': 'warning',
                'F': 'error'
            }
            return color_map.get(grade, 'neutral')
        
        @self.env.filter
        def severity_color(severity):
            """Get color class for issue severity."""
            color_map = {
                'P1': 'error',
                'P2': 'warning',
                'P3': 'info',
                'P4': 'neutral'
            }
            return color_map.get(severity, 'neutral')
    
    def _add_global_functions(self) -> None:
        """Add global functions available in all templates."""
        
        def carbon_icon(name, size=16):
            """Generate Carbon icon HTML."""
            return f'<svg class="cds--icon cds--icon--{size}" width="{size}" height="{size}"><use xlink:href="#icon-{name}"></use></svg>'
        
        def accessibility_label(text, level="info"):
            """Generate accessibility-compliant label."""
            return f'<span class="sr-only" aria-label="{text}" role="{level}">{text}</span>'
        
        def responsive_image(src, alt, sizes="(max-width: 672px) 100vw, 50vw"):
            """Generate responsive image with proper attributes."""
            return f'<img src="{src}" alt="{alt}" sizes="{sizes}" class="cds--img" loading="lazy">'
        
        # Add functions to Jinja2 environment
        self.env.globals.update({
            'carbon_icon': carbon_icon,
            'accessibility_label': accessibility_label,
            'responsive_image': responsive_image
        })
    
    def _load_carbon_components(self) -> Dict[str, Any]:
        """Load Carbon design system component configurations."""
        return {
            'grid': {
                'container': 'cds--grid',
                'row': 'cds--row',
                'col': 'cds--col',
                'breakpoints': {
                    'sm': 'cds--col-sm-4',
                    'md': 'cds--col-md-8', 
                    'lg': 'cds--col-lg-16'
                }
            },
            'typography': {
                'heading_01': 'cds--type-heading-01',
                'heading_02': 'cds--type-heading-02',
                'heading_03': 'cds--type-heading-03',
                'body_01': 'cds--type-body-01',
                'body_02': 'cds--type-body-02',
                'caption': 'cds--type-caption'
            },
            'colors': {
                'primary': 'cds--color-primary',
                'secondary': 'cds--color-secondary',
                'success': 'cds--color-success',
                'warning': 'cds--color-warning',
                'error': 'cds--color-error'
            }
        }
```

### Database Models Extension

**Report Storage Models**:
```python
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from src.models.base import BaseModel

class GeneratedReport(BaseModel):
    """Database model for generated HTML/PDF reports."""
    
    __tablename__ = 'generated_reports'
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False, index=True)
    report_id = Column(String(100), nullable=False, unique=True, index=True)
    
    # File information
    html_content = Column(Text, nullable=True, comment="Generated HTML content")
    pdf_file_path = Column(String(500), nullable=True, comment="Local PDF file path")
    file_size_mb = Column(Float, nullable=False, comment="PDF file size in megabytes")
    
    # Cloud storage URLs
    s3_html_url = Column(String(1000), nullable=True, comment="S3 HTML file URL")
    s3_pdf_url = Column(String(1000), nullable=True, comment="S3 PDF file URL")
    signed_pdf_url = Column(String(1000), nullable=True, comment="Signed PDF URL for client access")
    
    # Quality metrics
    accessibility_score = Column(Float, nullable=False, comment="WCAG 2.1 AA compliance score")
    design_compliance_score = Column(Float, nullable=False, comment="Refined Carbon design compliance")
    generation_time = Column(Float, nullable=False, comment="Report generation time in seconds")
    
    # Timestamps
    generated_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=True, comment="Signed URL expiration time")
    
    # Status tracking
    is_accessible = Column(Boolean, default=True, comment="Whether report meets accessibility standards")
    is_optimized = Column(Boolean, default=True, comment="Whether PDF is size-optimized")
    
    # Relationships
    lead = relationship("Lead", back_populates="generated_reports")
    
    def __repr__(self):
        return f"<GeneratedReport(lead_id={self.lead_id}, size={self.file_size_mb:.2f}MB, accessibility={self.accessibility_score:.1f}%)>"
    
    @property
    def accessibility_grade(self) -> str:
        """Return letter grade for accessibility compliance."""
        if self.accessibility_score >= 95:
            return "A+"
        elif self.accessibility_score >= 90:
            return "A"
        elif self.accessibility_score >= 85:
            return "B"
        elif self.accessibility_score >= 80:
            return "C"
        else:
            return "F"
    
    @property
    def is_performance_compliant(self) -> bool:
        """Check if report meets performance requirements."""
        return (
            self.generation_time <= 10.0 and
            self.file_size_mb <= 2.0 and
            self.accessibility_score >= 85.0
        )
    
    @property
    def quality_summary(self) -> Dict[str, Any]:
        """Get comprehensive quality summary."""
        return {
            'accessibility_grade': self.accessibility_grade,
            'file_size_compliant': self.file_size_mb <= 2.0,
            'generation_time_compliant': self.generation_time <= 10.0,
            'design_compliant': self.design_compliance_score >= 80.0,
            'overall_quality': 'Excellent' if self.is_performance_compliant else 'Needs Improvement'
        }
```

## Tests to Pass

1. **Report Builder Tests**: `pytest tests/test_report_builder.py -v` validates complete report generation, HTML/PDF conversion, and S3 integration with ≥90% coverage
2. **Design System Tests**: `pytest tests/test_design_compliance.py -v` validates Refined Carbon component usage, responsive design, and visual consistency
3. **Accessibility Tests**: `pytest tests/test_accessibility.py -v` validates WCAG 2.1 AA compliance, heading hierarchy, color contrast, and screen reader compatibility
4. **Performance Tests**: Report generation completes within 10 seconds, PDF files stay under 2MB, S3 upload optimization verified
5. **Template Management Tests**: `pytest tests/test_template_manager.py -v` validates Jinja2 templating, inheritance patterns, and component rendering
6. **PDF Quality Tests**: `pytest tests/test_pdf_processor.py -v` validates PDF optimization, compression algorithms, and quality preservation
7. **S3 Integration Tests**: `pytest tests/test_s3_storage.py -v` validates file uploads, signed URL generation, CDN configuration, and access control
8. **Responsive Design Tests**: HTML reports render correctly across mobile, tablet, and desktop viewports with proper layout adaptation
9. **Integration Tests**: `pytest tests/integration/test_report_pipeline.py -v` validates complete report generation pipeline with real data
10. **Visual Regression Tests**: Automated screenshot comparison ensures design consistency across report generations

## Implementation Guide

### Phase 1: Core Report Engine (Days 1-3)
1. **Report Builder Setup**: Implement main ReportBuilder class with Puppeteer PDF generation
2. **Template Foundation**: Set up Jinja2 template system with Refined Carbon design system integration
3. **HTML Generation**: Implement section-by-section HTML report generation with proper structure
4. **Basic PDF Conversion**: Add Puppeteer-based HTML to PDF conversion with quality settings
5. **File Size Optimization**: Implement PDF compression to meet <2MB requirement

### Phase 2: Design System Integration (Days 4-6)
1. **Refined Carbon Components**: Integrate Carbon design system CSS and component library
2. **Responsive Design**: Implement mobile-first responsive layouts with proper breakpoints
3. **Accessibility Compliance**: Add WCAG 2.1 AA compliance features (headings, alt-text, contrast)
4. **Visual Quality**: Implement design compliance validation and quality scoring
5. **Template Inheritance**: Build advanced Jinja2 template inheritance patterns

### Phase 3: Cloud Integration & Performance (Days 7-9)
1. **S3 Storage Integration**: Implement AWS S3 upload with proper access control and CDN
2. **Performance Optimization**: Add multi-tier caching and async processing for <10 second targets
3. **Signed URL Generation**: Create secure client access with expiration management
4. **Monitoring Integration**: Add performance metrics, logging, and error tracking
5. **Quality Validation**: Implement automated quality gates for accessibility and file size

### Phase 4: Testing & Production Readiness (Days 10-12)
1. **Unit Testing**: Write comprehensive unit tests for all report generation components
2. **Integration Testing**: Test complete report pipeline with real assessment data
3. **Performance Testing**: Validate generation times, file sizes, and concurrent usage
4. **Accessibility Testing**: Verify WCAG compliance with automated and manual testing
5. **Production Deployment**: Container orchestration, scaling, and monitoring setup

## Validation Commands

```bash
# Report builder validation
python -c "from src.reports.builder import ReportBuilder; builder = ReportBuilder(); print('Report Builder initialized successfully')"

# Report generation test
python -c "
import asyncio
from src.reports.builder import ReportBuilder
async def test():
    async with ReportBuilder() as builder:
        report = await builder.generate_report(1)
        print(f'Report generated: {report.file_size_mb:.2f}MB, {report.generation_time:.2f}s, {report.accessibility_score:.1f}% accessible')
asyncio.run(test())
"

# Template rendering validation
python -c "
import asyncio
from src.reports.template_manager import TemplateManager
async def test():
    tm = TemplateManager()
    content = await tm.render_template('hero_section', {'business_name': 'Test Co', 'overall_score': 85})
    print(f'Template rendered: {len(content)} characters')
asyncio.run(test())
"

# S3 storage validation
python -c "
import asyncio
from src.reports.storage_manager import S3StorageManager
async def test():
    storage = S3StorageManager()
    url = await storage.upload_content('test content', 'test.html', 'text/html')
    print(f'S3 upload successful: {url}')
asyncio.run(test())
"

# PDF quality validation
python scripts/pdf_quality_check.py --input reports/sample.pdf --check-size --check-accessibility

# Performance benchmarking
python scripts/report_performance_test.py --leads=10 --concurrent=3 --target-time=10

# Database integration validation
psql -h localhost -U leadfactory -d leadfactory -c "SELECT lead_id, file_size_mb, generation_time, accessibility_score FROM generated_reports WHERE is_performance_compliant=true LIMIT 5;"

# Accessibility compliance check
python scripts/accessibility_audit.py --html-file reports/sample.html --wcag-level AA
```

## Rollback Strategy

### Emergency Procedures
1. **Generation Failure**: Switch to HTML-only delivery without PDF conversion for immediate availability
2. **Performance Issues**: Enable aggressive caching and reduce template complexity for faster generation
3. **S3 Storage Issues**: Implement local file serving with temporary download links
4. **PDF Quality Problems**: Revert to simplified templates without complex layouts until issues resolved

### Detailed Rollback Steps
1. **Identify Issue**: Monitor dashboards show generation failures >5% or times >15 seconds
2. **Immediate Response**: Disable PDF generation and serve HTML reports with print-friendly CSS
3. **Service Preservation**: Maintain core functionality while isolating problematic components
4. **Quality Validation**: Verify HTML reports meet basic accessibility and design requirements
5. **Issue Resolution**: Test fixes in staging environment with comprehensive quality validation
6. **Gradual Recovery**: Re-enable PDF generation with monitoring for performance and quality metrics

## Success Criteria

1. **Report Generation Complete**: Professional HTML/PDF reports generated with all 6 sections and proper design system compliance
2. **Performance Requirements Met**: Generation completes within 10 seconds with PDF files optimized to <2MB size limit
3. **Accessibility Standards Achieved**: Reports comply with WCAG 2.1 AA requirements including proper structure and contrast ratios
4. **Design System Integration**: Refined Carbon components properly implemented with responsive layouts and professional appearance
5. **Cloud Storage Integration**: S3 upload with CDN optimization, signed URLs, and proper access control functional
6. **Template Management Operational**: Jinja2 templates with inheritance, components, and version control working correctly
7. **Database Integration Complete**: Report metadata stored with performance metrics, quality scores, and access tracking
8. **Production Deployment Ready**: Containerized architecture with scaling, monitoring, and automated quality validation

## Critical Context

### HTML to PDF Technology Selection
- **Puppeteer Advantage**: 3x faster than wkhtmltopdf with superior CSS3/JavaScript rendering quality
- **Performance Trade-off**: Higher resource usage (45% CPU vs 8%) but full modern web standards support
- **File Size Management**: 10x larger files require compression strategies to meet <2MB target
- **Container Strategy**: Docker containers with retry mechanisms for consistent PDF generation

### Refined Carbon Design System
- **Version**: Carbon v11 (Apache 2.0 license) with built-in WCAG 2.1 AA compliance
- **Typography**: IBM Plex font family with proper heading hierarchy and contrast ratios
- **Component Library**: Pre-built accessible components for grids, typography, and interactive elements
- **Responsive Framework**: Mobile-first design with defined breakpoints and adaptive layouts

### AWS S3 Performance Architecture
- **S3 Express One Zone**: Single-digit millisecond access with 10x performance improvement
- **Request Scaling**: 55,000 read requests/second capability with proper prefix distribution
- **CDN Integration**: CloudFront + ElastiCache for multi-tier caching and global delivery
- **Security**: Signed URLs with expiration management and proper access control policies

### Accessibility Requirements (WCAG 2.1 AA)
- **Legal Compliance**: Mandatory in US, EU, Australia, and Canada for business documents
- **Dual Standards**: Both WCAG and PDF/UA (ISO 14289) compliance required for PDFs
- **Color Contrast**: 4.5:1 minimum ratio with 7:1 preferred for enhanced readability
- **Quality Gates**: Automated validation with manual testing for comprehensive compliance

### Business Report Standards
- **Professional Layout**: 2-column responsive design with 50/50 text-to-visual ratio
- **Visual Hierarchy**: Maximum 6 colors with strategic highlighting and proper white space
- **Content Structure**: 6 sections following executive summary → detailed findings → actionable recommendations pattern
- **Quality Metrics**: Performance, accessibility, and design compliance scoring for continuous improvement

## Definition of Done

- [ ] Report builder implemented with Puppeteer-based HTML to PDF conversion for professional quality
- [ ] Refined Carbon design system integrated with responsive layouts and WCAG 2.1 AA compliance
- [ ] File size optimization achieved maintaining PDFs under 2MB through automated compression
- [ ] Performance targets met with report generation completing within 10 seconds consistently
- [ ] AWS S3 integration functional with signed URLs, CDN optimization, and proper access control
- [ ] Template management system implemented with Jinja2 inheritance and component libraries
- [ ] Accessibility compliance validated with automated testing and manual verification procedures
- [ ] Database models store report metadata with quality metrics and performance tracking
- [ ] Unit tests written for all builder components with ≥90% coverage including edge cases
- [ ] Integration tests validate complete report pipeline with real assessment data
- [ ] Performance testing confirms generation speed and concurrent usage requirements
- [ ] Visual regression testing ensures design consistency across report generations
- [ ] Production testing validates live S3 integration with actual report generation and delivery
- [ ] Code review completed with accessibility validation and performance optimization verification
- [ ] Documentation updated with report generation procedures, template management, and quality standards