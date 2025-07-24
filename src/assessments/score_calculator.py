"""
PRP-009: Score Calculator
Multi-layered scoring algorithm that transforms raw technical metrics into business impact estimates
"""

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass

from src.core.config import settings
from src.models.assessment_cost import AssessmentCost

logger = logging.getLogger(__name__)

# Score Component Data Classes
@dataclass
class ScoreComponent:
    """Individual scoring component with confidence interval."""
    name: str
    raw_score: float
    impact_estimate: float
    confidence_interval: Tuple[float, float]
    severity: str  # P1, P2, P3, P4
    recommendations: List[str]

@dataclass
class BusinessImpactScore:
    """Complete business impact assessment result."""
    lead_id: int
    overall_score: float  # 0-100 scale
    total_impact_estimate: float  # Dollar amount
    confidence_interval: Tuple[float, float]  # 95% confidence range
    
    # Component scores
    performance_score: ScoreComponent
    security_score: ScoreComponent
    seo_score: ScoreComponent
    ux_score: ScoreComponent
    visual_score: ScoreComponent
    
    # Classification factors
    industry_code: str  # 6-digit NAICS
    industry_multiplier: float
    geographic_factor: float
    market_adjustment: float
    
    # Metadata
    calculation_timestamp: str
    processing_time_ms: int
    validation_status: str

class ScoreCalculatorError(Exception):
    """Custom exception for score calculation errors"""
    pass

class ScoreCalculator:
    """
    Multi-layered scoring calculator that transforms raw technical metrics
    into quantifiable business impact estimates using industry-standard methodologies.
    """
    
    # Revenue impact formulas based on research
    PERFORMANCE_IMPACT_FORMULAS = {
        'page_speed': 0.01,  # 1% revenue increase per 100ms improvement
        'lcp_improvement': 0.13,  # 13% conversion increase per second LCP improvement
        'mobile_speed': 0.27,  # 27% conversion increase per second mobile improvement
        'core_web_vitals': 0.42  # 42% mobile revenue increase from 23% faster load
    }
    
    # Issue severity weights (P1=Critical, P4=Low)
    SEVERITY_WEIGHTS = {
        'P1': 1.0,  # Critical - immediate action required
        'P2': 0.7,  # High - plan within 24h
        'P3': 0.4,  # Medium - quick fixes needed
        'P4': 0.1   # Low - schedule when possible
    }
    
    # Industry-specific multipliers based on NAICS codes
    INDUSTRY_MULTIPLIERS = {
        '541511': 1.8,  # Computer Programming - high value services
        '454110': 1.2,  # E-commerce - moderate multiplier
        '722513': 1.1,  # Restaurants - lower digital impact
        '541990': 1.5,  # Professional services - default
        'default': 1.3  # Default multiplier for unknown industries
    }
    
    # Geographic adjustment factors by state (simplified)
    GEOGRAPHIC_FACTORS = {
        'CA': 1.4,  # California - high cost market
        'NY': 1.3,  # New York - high cost market
        'TX': 1.2,  # Texas - large market
        'FL': 1.1,  # Florida - growing market
        'default': 1.0  # Default for other states
    }
    
    # Component weights for overall score calculation
    COMPONENT_WEIGHTS = {
        'performance': 0.30,  # Performance has highest revenue correlation
        'seo': 0.25,          # SEO drives long-term organic growth
        'security': 0.20,     # Security affects trust and conversions
        'ux': 0.15,           # UX affects user engagement
        'visual': 0.10        # Visual affects brand perception
    }
    
    def __init__(self):
        """Initialize scoring calculator."""
        logger.info("Score Calculator initialized with business impact methodologies")
    
    def calculate_impact(self, lead_id: int, assessment_data: Dict[str, Any], lead_data: Dict[str, Any]) -> BusinessImpactScore:
        """
        Calculate comprehensive business impact score for a lead.
        
        Args:
            lead_id: Database ID of the lead to score
            assessment_data: All assessment results from PRPs 003-008
            lead_data: Lead information including industry and location
            
        Returns:
            BusinessImpactScore: Complete impact assessment with confidence intervals
        """
        start_time = time.time()
        
        try:
            # Get business classification and adjustment factors
            industry_code = self._classify_business(lead_data)
            industry_multiplier = self._get_industry_multiplier(industry_code)
            geographic_factor = self._get_geographic_factor(lead_data.get('state'))
            market_adjustment = industry_multiplier * geographic_factor
            
            # Calculate component scores
            performance_score = self._calculate_performance_impact(
                assessment_data.get('pagespeed_data', {}),
                market_adjustment
            )
            
            security_score = self._calculate_security_impact(
                assessment_data.get('security_data', {}),
                market_adjustment
            )
            
            seo_score = self._calculate_seo_impact(
                assessment_data.get('semrush_data', {}),
                market_adjustment
            )
            
            ux_score = self._calculate_ux_impact(
                assessment_data.get('visual_analysis', {}),
                market_adjustment
            )
            
            visual_score = self._calculate_visual_impact(
                assessment_data.get('visual_analysis', {}),
                market_adjustment
            )
            
            # Calculate aggregate score and total impact
            component_scores = [performance_score, security_score, seo_score, ux_score, visual_score]
            overall_score = self._calculate_overall_score(component_scores)
            total_impact = sum(score.impact_estimate for score in component_scores)
            
            # Generate confidence intervals (simplified - 95% confidence)
            confidence_interval = self._calculate_confidence_intervals(
                [score.impact_estimate for score in component_scores]
            )
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Create business impact score object
            business_score = BusinessImpactScore(
                lead_id=lead_id,
                overall_score=round(overall_score, 1),
                total_impact_estimate=round(total_impact, 2),
                confidence_interval=confidence_interval,
                performance_score=performance_score,
                security_score=security_score,
                seo_score=seo_score,
                ux_score=ux_score,
                visual_score=visual_score,
                industry_code=industry_code,
                industry_multiplier=industry_multiplier,
                geographic_factor=geographic_factor,
                market_adjustment=market_adjustment,
                calculation_timestamp=datetime.now(timezone.utc).isoformat(),
                processing_time_ms=processing_time_ms,
                validation_status="validated"
            )
            
            logger.info(f"Business impact calculated for lead {lead_id}: ${total_impact:.2f} total impact, {overall_score:.1f} score")
            return business_score
            
        except Exception as e:
            logger.error(f"Score calculation failed for lead {lead_id}: {e}")
            raise ScoreCalculatorError(f"Score calculation failed: {str(e)}")
    
    def _classify_business(self, lead_data: Dict[str, Any]) -> str:
        """Classify business and return 6-digit NAICS code."""
        
        # Use existing NAICS code if available
        naics_code = lead_data.get('naics_code')
        if naics_code and len(naics_code) == 6:
            return naics_code
        
        # Simple classification based on business description
        description = lead_data.get('description', '').lower()
        company = lead_data.get('company', '').lower()
        url = lead_data.get('url', '').lower()
        
        # Combine all text for analysis
        business_text = f"{description} {company} {url}"
        
        # Classification rules (simplified)
        if any(term in business_text for term in ['web', 'software', 'app', 'tech', 'development', 'programming']):
            return '541511'  # Custom Computer Programming Services
        elif any(term in business_text for term in ['retail', 'store', 'shop', 'ecommerce', 'e-commerce']):
            return '454110'  # Electronic Shopping and Mail-Order Houses
        elif any(term in business_text for term in ['restaurant', 'food', 'dining', 'cafe', 'catering']):
            return '722513'  # Limited-Service Restaurants
        elif any(term in business_text for term in ['consulting', 'marketing', 'agency', 'service']):
            return '541990'  # All Other Professional, Scientific Services
        else:
            return '541990'  # Default professional services
    
    def _get_industry_multiplier(self, naics_code: str) -> float:
        """Get industry-specific economic multiplier."""
        return self.INDUSTRY_MULTIPLIERS.get(naics_code, self.INDUSTRY_MULTIPLIERS['default'])
    
    def _get_geographic_factor(self, state: Optional[str]) -> float:
        """Get geographic market adjustment factor."""
        if not state:
            return self.GEOGRAPHIC_FACTORS['default']
        return self.GEOGRAPHIC_FACTORS.get(state.upper(), self.GEOGRAPHIC_FACTORS['default'])
    
    def _calculate_performance_impact(self, pagespeed_data: Dict[str, Any], market_adjustment: float) -> ScoreComponent:
        """Calculate performance-related business impact."""
        
        try:
            # Extract performance metrics from PRP-003 PageSpeed data
            mobile_score = pagespeed_data.get('mobile_performance_score', 0)
            desktop_score = pagespeed_data.get('desktop_performance_score', 0)
            mobile_lcp = pagespeed_data.get('mobile_lcp', 0)
            desktop_lcp = pagespeed_data.get('desktop_lcp', 0)
            
            # Calculate performance improvement potential
            avg_score = (mobile_score + desktop_score) / 2
            improvement_potential = max(0, 90 - avg_score) / 90
            
            # Apply revenue impact formulas from research
            baseline_revenue = 100000  # $100K baseline for calculation
            
            # Mobile performance impact (27% conversion increase per second improvement)
            mobile_impact = 0
            if mobile_lcp > 2.5:  # Poor LCP threshold
                seconds_improvement = mobile_lcp - 2.5
                mobile_impact = baseline_revenue * self.PERFORMANCE_IMPACT_FORMULAS['mobile_speed'] * seconds_improvement
            
            # Desktop performance impact (1% revenue per 100ms improvement)
            desktop_impact = 0
            if desktop_lcp > 2.5:
                ms_improvement = (desktop_lcp - 2.5) * 1000
                desktop_impact = baseline_revenue * self.PERFORMANCE_IMPACT_FORMULAS['page_speed'] * (ms_improvement / 100)
            
            # Total performance impact with market adjustment
            raw_impact = mobile_impact + desktop_impact
            adjusted_impact = raw_impact * market_adjustment
            
            # Determine severity based on performance scores
            if avg_score < 50:
                severity = "P1"  # Critical
            elif avg_score < 70:
                severity = "P2"  # High
            elif avg_score < 85:
                severity = "P3"  # Medium
            else:
                severity = "P4"  # Low
            
            # Generate recommendations
            recommendations = []
            if mobile_score < 70:
                recommendations.append("Optimize mobile page loading speed - compress images and minimize JavaScript")
            if desktop_score < 70:
                recommendations.append("Improve desktop performance - enable browser caching and optimize CSS delivery")
            if mobile_lcp > 2.5:
                recommendations.append("Reduce Largest Contentful Paint on mobile - optimize hero images and critical resources")
            if desktop_lcp > 2.5:
                recommendations.append("Improve desktop LCP - optimize above-the-fold content loading")
            
            # Calculate confidence interval (±20% uncertainty)
            confidence_lower = adjusted_impact * 0.8
            confidence_upper = adjusted_impact * 1.2
            
            return ScoreComponent(
                name="performance",
                raw_score=avg_score,
                impact_estimate=adjusted_impact,
                confidence_interval=(confidence_lower, confidence_upper),
                severity=severity,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Performance impact calculation failed: {e}")
            return self._create_error_component("performance")
    
    def _calculate_security_impact(self, security_data: Dict[str, Any], market_adjustment: float) -> ScoreComponent:
        """Calculate security-related business impact."""
        
        try:
            # Extract security metrics from PRP-004 Security data
            https_enforced = security_data.get('https_enforced', False)
            ssl_grade = security_data.get('ssl_grade', 'F')
            security_headers = security_data.get('security_headers', {})
            vulnerability_count = security_data.get('vulnerability_count', 0)
            
            # Calculate security risk and impact
            security_issues = []
            raw_impact = 0
            baseline_revenue = 100000
            
            # HTTPS not enforced - 14% conversion loss potential (research-based)
            if not https_enforced:
                security_issues.append("HTTPS not enforced")
                raw_impact += baseline_revenue * 0.14
            
            # Poor SSL grade affects trust
            if ssl_grade in ['D', 'E', 'F']:
                security_issues.append("Poor SSL configuration")
                raw_impact += baseline_revenue * 0.08  # 8% trust impact
            
            # Missing security headers
            if not security_headers.get('hsts'):
                security_issues.append("Missing HSTS header")
                raw_impact += 2000  # Fixed cost for security vulnerability
            
            if not security_headers.get('csp'):
                security_issues.append("Missing Content Security Policy")
                raw_impact += 3000  # Fixed cost for XSS vulnerability
            
            # Vulnerability count impact
            if vulnerability_count > 0:
                raw_impact += vulnerability_count * 1000  # $1K per vulnerability
            
            # Apply market adjustment
            adjusted_impact = raw_impact * market_adjustment
            
            # Determine severity
            if len(security_issues) >= 3 or vulnerability_count > 5:
                severity = "P1"  # Critical
            elif len(security_issues) >= 2 or vulnerability_count > 2:
                severity = "P2"  # High
            elif len(security_issues) >= 1 or vulnerability_count > 0:
                severity = "P3"  # Medium
            else:
                severity = "P4"  # Low
            
            # Generate recommendations
            recommendations = []
            if not https_enforced:
                recommendations.append("Implement HTTPS across entire site with proper redirects")
            if ssl_grade in ['D', 'E', 'F']:
                recommendations.append("Upgrade SSL configuration to achieve A+ grade")
            if not security_headers.get('hsts'):
                recommendations.append("Add HSTS header to prevent protocol downgrade attacks")
            if not security_headers.get('csp'):
                recommendations.append("Implement Content Security Policy to prevent XSS attacks")
            if vulnerability_count > 0:
                recommendations.append(f"Address {vulnerability_count} security vulnerabilities")
            
            # Calculate security score (0-100 based on issues)
            security_score = max(0, 100 - len(security_issues) * 20 - vulnerability_count * 10)
            
            # Confidence interval (±30% due to security impact uncertainty)
            confidence_lower = adjusted_impact * 0.7
            confidence_upper = adjusted_impact * 1.3
            
            return ScoreComponent(
                name="security",
                raw_score=security_score,
                impact_estimate=adjusted_impact,
                confidence_interval=(confidence_lower, confidence_upper),
                severity=severity,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Security impact calculation failed: {e}")
            return self._create_error_component("security")
    
    def _calculate_seo_impact(self, semrush_data: Dict[str, Any], market_adjustment: float) -> ScoreComponent:
        """Calculate SEO-related business impact."""
        
        try:
            # Extract SEO metrics from PRP-007 SEMrush data
            authority_score = semrush_data.get('authority_score', 0)
            organic_traffic = semrush_data.get('organic_traffic_estimate', 0)
            ranking_keywords = semrush_data.get('ranking_keywords_count', 0)
            technical_issues = semrush_data.get('technical_issues', [])
            
            # Calculate SEO improvement potential
            authority_potential = max(0, 80 - authority_score) / 80
            
            # Estimate revenue impact from SEO improvements
            # Research shows $2-5 per organic visitor value
            visitor_value = 3.0
            current_monthly_value = organic_traffic * visitor_value
            
            # Authority improvement can drive 50% traffic increase
            traffic_improvement_factor = 1.5
            improvement_potential = current_monthly_value * authority_potential * traffic_improvement_factor
            annual_seo_impact = improvement_potential * 12
            
            # Technical issues impact - each issue costs traffic/rankings
            technical_impact = len(technical_issues) * 1500  # $1.5K per major technical issue
            
            # Total SEO impact with market adjustment
            raw_impact = annual_seo_impact + technical_impact
            adjusted_impact = raw_impact * market_adjustment
            
            # Determine severity
            if authority_score < 30 or len(technical_issues) > 10:
                severity = "P1"  # Critical
            elif authority_score < 50 or len(technical_issues) > 5:
                severity = "P2"  # High
            elif authority_score < 70 or len(technical_issues) > 2:
                severity = "P3"  # Medium
            else:
                severity = "P4"  # Low
            
            # Generate recommendations
            recommendations = []
            if authority_score < 50:
                recommendations.append("Improve domain authority through high-quality backlink acquisition")
            if ranking_keywords < 100:
                recommendations.append("Expand keyword targeting and optimize for more search terms")
            if organic_traffic < 1000:
                recommendations.append("Increase organic traffic through content marketing and SEO optimization")
            if len(technical_issues) > 0:
                recommendations.append(f"Fix {len(technical_issues)} technical SEO issues affecting search rankings")
            
            # Confidence interval (±40% due to SEO uncertainty)
            confidence_lower = adjusted_impact * 0.6
            confidence_upper = adjusted_impact * 1.4
            
            return ScoreComponent(
                name="seo",
                raw_score=authority_score,
                impact_estimate=adjusted_impact,
                confidence_interval=(confidence_lower, confidence_upper),
                severity=severity,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"SEO impact calculation failed: {e}")
            return self._create_error_component("seo")
    
    def _calculate_ux_impact(self, visual_data: Dict[str, Any], market_adjustment: float) -> ScoreComponent:
        """Calculate UX-related business impact."""
        
        try:
            # Extract UX metrics from PRP-008 Visual Analysis data
            overall_ux_score = visual_data.get('overall_ux_score', 0)
            critical_issues = visual_data.get('critical_issues', [])
            positive_elements = visual_data.get('positive_elements', [])
            rubric_scores = visual_data.get('rubric_scores', {})
            
            # Convert 0-2 scale to 0-100 scale for consistency
            ux_percentage = (overall_ux_score / 2.0) * 100
            
            # Calculate UX improvement potential
            ux_improvement_potential = max(0, 85 - ux_percentage) / 85
            
            # UX impact on conversion rates (research-based)
            baseline_revenue = 100000
            
            # Poor UX can reduce conversions by up to 30%
            ux_conversion_impact = baseline_revenue * 0.30 * ux_improvement_potential
            
            # Critical issues have additional impact
            critical_issue_impact = len(critical_issues) * 2500  # $2.5K per critical UX issue
            
            # Total UX impact with market adjustment
            raw_impact = ux_conversion_impact + critical_issue_impact
            adjusted_impact = raw_impact * market_adjustment
            
            # Determine severity based on UX score and issues
            if len(critical_issues) > 3 or overall_ux_score < 0.8:
                severity = "P1"  # Critical
            elif len(critical_issues) > 1 or overall_ux_score < 1.2:
                severity = "P2"  # High
            elif len(critical_issues) > 0 or overall_ux_score < 1.6:
                severity = "P3"  # Medium
            else:
                severity = "P4"  # Low
            
            # Generate recommendations
            recommendations = []
            if overall_ux_score < 1.5:
                recommendations.append("Improve overall user experience design and visual hierarchy")
            if len(critical_issues) > 0:
                recommendations.append(f"Address {len(critical_issues)} critical UX issues affecting user engagement")
            if len(positive_elements) < 3:
                recommendations.append("Strengthen positive UX elements like clear CTAs and trust signals")
            
            # Check specific rubric issues
            cta_score = rubric_scores.get('cta_prominence', {}).get('score', 2)
            if cta_score < 1:
                recommendations.append("Improve call-to-action visibility and prominence")
            
            trust_score = rubric_scores.get('trust_signals_presence', {}).get('score', 2)
            if trust_score < 1:
                recommendations.append("Add trust signals like testimonials, badges, and contact information")
            
            # Confidence interval (±25% for UX uncertainty)
            confidence_lower = adjusted_impact * 0.75
            confidence_upper = adjusted_impact * 1.25
            
            return ScoreComponent(
                name="ux",
                raw_score=ux_percentage,
                impact_estimate=adjusted_impact,
                confidence_interval=(confidence_lower, confidence_upper),
                severity=severity,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"UX impact calculation failed: {e}")
            return self._create_error_component("ux")
    
    def _calculate_visual_impact(self, visual_data: Dict[str, Any], market_adjustment: float) -> ScoreComponent:
        """Calculate visual design-related business impact."""
        
        try:
            # Extract visual-specific metrics from PRP-008 data
            rubric_scores = visual_data.get('rubric_scores', {})
            
            # Focus on visual-specific rubrics
            brand_score = rubric_scores.get('brand_cohesion', {}).get('score', 0)
            image_quality_score = rubric_scores.get('image_quality', {}).get('score', 0)
            visual_hierarchy_score = rubric_scores.get('visual_hierarchy', {}).get('score', 0)
            white_space_score = rubric_scores.get('white_space_balance', {}).get('score', 0)
            
            # Calculate average visual score (0-2 scale)
            visual_scores = [brand_score, image_quality_score, visual_hierarchy_score, white_space_score]
            avg_visual_score = sum(score for score in visual_scores if score > 0) / max(1, len([s for s in visual_scores if s > 0]))
            visual_percentage = (avg_visual_score / 2.0) * 100
            
            # Visual impact on brand perception and trust
            visual_improvement_potential = max(0, 85 - visual_percentage) / 85
            baseline_revenue = 100000
            
            # Visual design impacts brand trust, which affects conversion rates
            # Research shows professional design can improve conversions by 15%
            visual_trust_impact = baseline_revenue * 0.15 * visual_improvement_potential
            
            # Apply market adjustment
            adjusted_impact = visual_trust_impact * market_adjustment
            
            # Determine severity based on visual scores
            if avg_visual_score < 0.8:
                severity = "P2"  # High - visual issues hurt brand perception
            elif avg_visual_score < 1.2:
                severity = "P3"  # Medium
            else:
                severity = "P4"  # Low
            
            # Generate recommendations
            recommendations = []
            if brand_score < 1.5:
                recommendations.append("Improve brand consistency and professional visual presentation")
            if image_quality_score < 1.5:
                recommendations.append("Upgrade image quality and visual assets for better brand perception")
            if visual_hierarchy_score < 1.5:
                recommendations.append("Enhance visual hierarchy to improve user navigation and engagement")
            if white_space_score < 1.5:
                recommendations.append("Optimize white space usage to reduce visual clutter and improve readability")
            
            # Confidence interval (±20% for visual impact)
            confidence_lower = adjusted_impact * 0.8
            confidence_upper = adjusted_impact * 1.2
            
            return ScoreComponent(
                name="visual",
                raw_score=visual_percentage,
                impact_estimate=adjusted_impact,
                confidence_interval=(confidence_lower, confidence_upper),
                severity=severity,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Visual impact calculation failed: {e}")
            return self._create_error_component("visual")
    
    def _calculate_overall_score(self, component_scores: List[ScoreComponent]) -> float:
        """Calculate overall business score from component scores."""
        
        weighted_scores = []
        for score in component_scores:
            weight = self.COMPONENT_WEIGHTS.get(score.name, 0.2)  # Default weight
            weighted_score = score.raw_score * weight
            weighted_scores.append(weighted_score)
        
        return sum(weighted_scores)
    
    def _calculate_confidence_intervals(self, estimates: List[float]) -> Tuple[float, float]:
        """Calculate 95% confidence intervals for impact estimates."""
        
        if not estimates:
            return (0.0, 0.0)
        
        total_estimate = sum(estimates)
        
        # Simplified confidence interval calculation
        # In production, would use proper statistical methods (bootstrapping, etc.)
        confidence_range = total_estimate * 0.25  # ±25% uncertainty
        
        lower_bound = max(0, total_estimate - confidence_range)
        upper_bound = total_estimate + confidence_range
        
        return (round(lower_bound, 2), round(upper_bound, 2))
    
    def _create_error_component(self, name: str) -> ScoreComponent:
        """Create error component when calculation fails."""
        
        return ScoreComponent(
            name=name,
            raw_score=0,
            impact_estimate=0,
            confidence_interval=(0, 0),
            severity="P4",
            recommendations=[f"Unable to calculate {name} impact - insufficient data"]
        )

async def calculate_business_score(lead_id: int, assessment_data: Dict[str, Any], lead_data: Dict[str, Any]) -> BusinessImpactScore:
    """
    Main entry point for business impact score calculation.
    
    Args:
        lead_id: Database ID of the lead
        assessment_data: Complete assessment results from all PRPs
        lead_data: Lead information including company, industry, location
        
    Returns:
        Complete business impact score with confidence intervals
    """
    try:
        # Initialize score calculator
        calculator = ScoreCalculator()
        
        # Calculate business impact score
        logger.info(f"Starting business impact calculation for lead {lead_id}")
        business_score = calculator.calculate_impact(lead_id, assessment_data, lead_data)
        
        logger.info(f"Business impact calculation completed for lead {lead_id}: ${business_score.total_impact_estimate:.2f} impact")
        return business_score
        
    except Exception as e:
        logger.error(f"Business score calculation failed for lead {lead_id}: {e}")
        raise ScoreCalculatorError(f"Business score calculation failed: {str(e)}")

# Add create_scoring_cost method to AssessmentCost model
def create_scoring_cost_method(cls, lead_id: int, cost_cents: float = 0.0, response_status: str = "success", response_time_ms: Optional[int] = None, error_message: Optional[str] = None):
    """
    Create cost record for score calculation (no external API cost).
    
    Args:
        lead_id: ID of the lead being assessed
        cost_cents: Cost in cents (default $0.00 - internal calculation)
        response_status: success, error, timeout
        response_time_ms: Calculation time in milliseconds
        error_message: Error message if applicable
        
    Returns:
        AssessmentCost instance
    """
    now = datetime.now(timezone.utc)
    
    return cls(
        lead_id=lead_id,
        service_name="score_calculator",
        api_endpoint="internal://scoring/calculate_impact",
        cost_cents=cost_cents,
        currency="USD",
        request_timestamp=now,
        response_status=response_status,
        response_time_ms=response_time_ms,
        api_quota_used=False,  # Internal calculation - no quota
        rate_limited=False,
        retry_count=0,
        error_message=error_message,
        daily_budget_date=now.strftime("%Y-%m-%d"),
        monthly_budget_date=now.strftime("%Y-%m")
    )

# Monkey patch the method to AssessmentCost
AssessmentCost.create_scoring_cost = classmethod(create_scoring_cost_method)