# PRP-009: Score Calculator

## Task ID: PRP-009

## Wave: Foundation Infrastructure

## Business Logic

The LeadFactory audit platform requires a sophisticated scoring calculator that transforms raw technical assessment metrics into quantifiable dollar impact estimates for $399 audit reports. This scoring system leverages NAICS industry classification multipliers, geographic market adjustment factors, and proven revenue correlation formulas to convert technical data (PageSpeed scores, security issues, SEO metrics, UX assessments, visual analysis) into actionable business impact estimates with 95% statistical confidence intervals. The calculator provides the core value proposition by translating technical complexity into executive-level business insights that justify audit report pricing and demonstrate clear ROI for recommended improvements.

## Overview

Implement multi-layered scoring algorithm with industry-standard methodologies for:
- NAICS industry-specific multipliers applied to 6-digit classification codes with economic impact factors
- Geographic market adjustment using regional input-output analysis and local multiplier effects  
- Revenue impact calculation using proven formulas (Amazon's 1% revenue per 100ms improvement)
- Issue severity weighting with P1-P4 classification based on Impact-Urgency Matrix framework
- Statistical confidence intervals using 95% confidence threshold with bootstrapping validation
- Aggregate business score combining performance, security, SEO, UX, and visual assessment metrics
- Real-time calculation capability with sub-second response times for immediate report generation

## Dependencies

- **External**: NAICS classification data, regional economic multipliers, statistical libraries (scipy, numpy)
- **Internal**: PRP-001 (Lead Data Model) for industry/location data, All assessment PRPs (003-008) for raw metrics input
- **Blockers**: None

## Outcome-Focused Acceptance Criteria

1. **Scoring Calculator Operational**: `ScoreCalculator().calculate_impact(lead_id)` returns dollar impact estimates with confidence intervals for all technical issues identified
2. **NAICS Integration Complete**: Industry-specific multipliers applied based on 6-digit NAICS codes, economic impact factors properly weighted by sector characteristics
3. **Geographic Adjustment Functional**: Regional market factors adjust estimates based on local economic conditions, income levels, and market purchasing power variations
4. **Revenue Correlation Accurate**: Technical metrics converted to dollar impacts using proven formulas (page speed, Core Web Vitals, SEO rankings, UX issues)
5. **Confidence Intervals Provided**: All estimates include 95% confidence ranges using proper statistical validation, uncertainty quantified and communicated clearly
6. **Issue Prioritization Working**: P1-P4 severity classification with Impact-Urgency Matrix, critical issues weighted for immediate action recommendations
7. **Aggregate Score Generated**: Overall business score (0-100) combining all assessment dimensions with normalized weighting and clear interpretation
8. **Performance Requirements Met**: Sub-second calculation response times, handles 100+ concurrent scoring requests with proper caching strategies
9. **Validation Framework Active**: A/B testing integration for continuous scoring accuracy improvement, cross-industry validation across NAICS sectors
10. **Database Integration Complete**: Calculated scores stored in PostgreSQL with proper audit trails, score history tracking for trend analysis

## Integration Points

### Score Calculation Engine (Core Algorithm)
- **Location**: `src/scoring/calculator.py`, `src/scoring/models.py`
- **Dependencies**: scipy, numpy, NAICS data, regional multipliers
- **Functions**: calculate_impact(), apply_industry_multipliers(), adjust_geographic_factors(), generate_confidence_intervals()

### Industry Classification Service (NAICS Integration)
- **Location**: `src/scoring/industry_classifier.py`, `src/scoring/naics_data.py`
- **Dependencies**: NAICS classification data, industry multiplier tables
- **Functions**: classify_business(), get_industry_multipliers(), load_economic_factors()

### Geographic Adjustment Service (Market Factors)
- **Location**: `src/scoring/geographic_adjuster.py`, `src/scoring/regional_data.py`
- **Dependencies**: Regional economic data, input-output analysis multipliers
- **Functions**: get_market_factors(), calculate_local_multipliers(), adjust_for_region()

### Statistical Validation Framework (Confidence Calculation)
- **Location**: `src/scoring/statistics.py`, `src/scoring/confidence.py`
- **Dependencies**: scipy.stats, bootstrapping libraries, validation datasets
- **Functions**: calculate_confidence_intervals(), validate_estimates(), bootstrap_uncertainty()

## Implementation Requirements

### Score Calculation Engine Implementation

**Core Scoring Calculator**:
```python
import numpy as np
import logging
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime
from scipy import stats
from src.models.lead_models import Lead
from src.scoring.industry_classifier import IndustryClassifier
from src.scoring.geographic_adjuster import GeographicAdjuster
from src.scoring.statistics import StatisticalValidator

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
    calculation_timestamp: datetime
    processing_time: float
    validation_status: str

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
    
    def __init__(self):
        """Initialize scoring calculator with required services."""
        self.industry_classifier = IndustryClassifier()
        self.geographic_adjuster = GeographicAdjuster()
        self.statistical_validator = StatisticalValidator()
        
        logging.info("Score Calculator initialized with industry and geographic services")
    
    def calculate_impact(self, lead_id: int) -> BusinessImpactScore:
        """
        Calculate comprehensive business impact score for a lead.
        
        Args:
            lead_id: Database ID of the lead to score
            
        Returns:
            BusinessImpactScore: Complete impact assessment with confidence intervals
        """
        start_time = datetime.utcnow()
        
        try:
            # Load lead and assessment data
            lead_data = self._load_lead_data(lead_id)
            assessment_data = self._load_assessment_data(lead_id)
            
            # Classify business and get adjustment factors
            industry_code = self.industry_classifier.classify_business(
                naics_code=lead_data.get('naics_code'),
                business_description=lead_data.get('description', ''),
                url=lead_data.get('url', '')
            )
            
            industry_multiplier = self.industry_classifier.get_industry_multipliers(industry_code)
            geographic_factor = self.geographic_adjuster.get_market_factors(
                state=lead_data.get('state'),
                county=lead_data.get('county'),
                industry_code=industry_code
            )
            
            # Calculate component scores
            performance_score = self._calculate_performance_impact(
                assessment_data.get('pagespeed', {}),
                industry_multiplier,
                geographic_factor
            )
            
            security_score = self._calculate_security_impact(
                assessment_data.get('security', {}),
                industry_multiplier,
                geographic_factor
            )
            
            seo_score = self._calculate_seo_impact(
                assessment_data.get('semrush', {}),
                industry_multiplier,
                geographic_factor
            )
            
            ux_score = self._calculate_ux_impact(
                assessment_data.get('visual', {}),
                industry_multiplier,
                geographic_factor
            )
            
            visual_score = self._calculate_visual_impact(
                assessment_data.get('visual', {}),
                industry_multiplier,
                geographic_factor
            )
            
            # Calculate aggregate score and total impact
            component_scores = [performance_score, security_score, seo_score, ux_score, visual_score]
            overall_score = self._calculate_overall_score(component_scores)
            total_impact = sum(score.impact_estimate for score in component_scores)
            
            # Generate confidence intervals
            confidence_interval = self.statistical_validator.calculate_confidence_intervals(
                estimates=[score.impact_estimate for score in component_scores],
                confidence_level=0.95
            )
            
            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Create business impact score object
            business_score = BusinessImpactScore(
                lead_id=lead_id,
                overall_score=overall_score,
                total_impact_estimate=total_impact,
                confidence_interval=confidence_interval,
                performance_score=performance_score,
                security_score=security_score,
                seo_score=seo_score,
                ux_score=ux_score,
                visual_score=visual_score,
                industry_code=industry_code,
                industry_multiplier=industry_multiplier,
                geographic_factor=geographic_factor,
                market_adjustment=geographic_factor * industry_multiplier,
                calculation_timestamp=start_time,
                processing_time=processing_time,
                validation_status="validated"
            )
            
            # Store results in database
            self._store_score_results(business_score)
            
            logging.info(f"Business impact calculated for lead {lead_id}: ${total_impact:.2f} total impact")
            return business_score
            
        except Exception as e:
            logging.error(f"Score calculation failed for lead {lead_id}: {e}")
            raise
    
    def _calculate_performance_impact(
        self, 
        pagespeed_data: Dict[str, Any], 
        industry_multiplier: float,
        geographic_factor: float
    ) -> ScoreComponent:
        """Calculate performance-related business impact."""
        try:
            # Extract key performance metrics
            mobile_score = pagespeed_data.get('mobile_performance_score', 0)
            desktop_score = pagespeed_data.get('desktop_performance_score', 0)
            lcp_mobile = pagespeed_data.get('mobile_lcp', 0)
            lcp_desktop = pagespeed_data.get('desktop_lcp', 0)
            
            # Calculate performance issues and potential improvements
            mobile_improvement_potential = max(0, 90 - mobile_score) / 90
            desktop_improvement_potential = max(0, 90 - desktop_score) / 90
            
            # Apply revenue impact formulas from research
            # Assume baseline revenue of $100K annually for calculation
            baseline_revenue = 100000
            
            # Mobile performance impact (27% conversion increase per second improvement)
            mobile_speed_impact = 0
            if lcp_mobile > 2.5:  # Poor LCP
                seconds_improvement = lcp_mobile - 2.5
                mobile_speed_impact = baseline_revenue * self.PERFORMANCE_IMPACT_FORMULAS['mobile_speed'] * seconds_improvement
            
            # Desktop performance impact (1% revenue per 100ms improvement)
            desktop_speed_impact = 0
            if lcp_desktop > 2.5:
                ms_improvement = (lcp_desktop - 2.5) * 1000
                desktop_speed_impact = baseline_revenue * self.PERFORMANCE_IMPACT_FORMULAS['page_speed'] * (ms_improvement / 100)
            
            # Total performance impact
            raw_impact = mobile_speed_impact + desktop_speed_impact
            adjusted_impact = raw_impact * industry_multiplier * geographic_factor
            
            # Determine severity based on performance scores
            avg_score = (mobile_score + desktop_score) / 2
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
            if lcp_mobile > 2.5:
                recommendations.append("Reduce Largest Contentful Paint on mobile - optimize hero images and critical resources")
            
            # Calculate confidence interval (simplified - more complex in actual implementation)
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
            logging.error(f"Performance impact calculation failed: {e}")
            return ScoreComponent(
                name="performance",
                raw_score=0,
                impact_estimate=0,
                confidence_interval=(0, 0),
                severity="P4",
                recommendations=["Unable to calculate performance impact"]
            )
    
    def _calculate_security_impact(
        self,
        security_data: Dict[str, Any],
        industry_multiplier: float,
        geographic_factor: float
    ) -> ScoreComponent:
        """Calculate security-related business impact."""
        try:
            # Extract security metrics
            https_enabled = security_data.get('https_enforced', False)
            security_headers = security_data.get('security_headers', {})
            ssl_grade = security_data.get('ssl_grade', 'F')
            
            # Calculate security risk score
            security_issues = []
            raw_impact = 0
            
            if not https_enabled:
                security_issues.append("HTTPS not enforced - 14% conversion loss potential")
                raw_impact += 14000  # $14K impact on $100K baseline
            
            if not security_headers.get('hsts'):
                security_issues.append("Missing HSTS header - security vulnerability")
                raw_impact += 2000
            
            if not security_headers.get('csp'):
                security_issues.append("Missing Content Security Policy - XSS vulnerability")
                raw_impact += 5000
            
            if ssl_grade in ['D', 'E', 'F']:
                security_issues.append("Poor SSL configuration - trust issues")
                raw_impact += 8000
            
            # Apply industry and geographic adjustments
            adjusted_impact = raw_impact * industry_multiplier * geographic_factor
            
            # Determine severity
            if len(security_issues) >= 3:
                severity = "P1"  # Critical
            elif len(security_issues) >= 2:
                severity = "P2"  # High
            elif len(security_issues) >= 1:
                severity = "P3"  # Medium
            else:
                severity = "P4"  # Low
            
            # Generate recommendations
            recommendations = []
            if not https_enabled:
                recommendations.append("Implement HTTPS across entire site with proper redirects")
            if not security_headers.get('hsts'):
                recommendations.append("Add HSTS header to prevent protocol downgrade attacks")
            if not security_headers.get('csp'):
                recommendations.append("Implement Content Security Policy to prevent XSS attacks")
            
            # Simple confidence interval
            confidence_lower = adjusted_impact * 0.7
            confidence_upper = adjusted_impact * 1.3
            
            return ScoreComponent(
                name="security",
                raw_score=100 - len(security_issues) * 25,
                impact_estimate=adjusted_impact,
                confidence_interval=(confidence_lower, confidence_upper),
                severity=severity,
                recommendations=recommendations
            )
            
        except Exception as e:
            logging.error(f"Security impact calculation failed: {e}")
            return ScoreComponent(
                name="security",
                raw_score=0,
                impact_estimate=0,
                confidence_interval=(0, 0),
                severity="P4",
                recommendations=["Unable to calculate security impact"]
            )
    
    def _calculate_seo_impact(
        self,
        semrush_data: Dict[str, Any],
        industry_multiplier: float,
        geographic_factor: float
    ) -> ScoreComponent:
        """Calculate SEO-related business impact."""
        try:
            # Extract SEO metrics
            authority_score = semrush_data.get('authority_score', 0)
            organic_traffic = semrush_data.get('organic_traffic_estimate', 0)
            ranking_keywords = semrush_data.get('ranking_keywords_count', 0)
            technical_issues = semrush_data.get('technical_issues', [])
            
            # Calculate SEO improvement potential
            authority_potential = max(0, 80 - authority_score) / 80
            traffic_improvement_factor = 1.5  # Potential 50% traffic increase
            
            # Estimate revenue impact from SEO improvements
            # Assume $2 per organic visitor value
            visitor_value = 2.0
            current_monthly_value = organic_traffic * visitor_value
            improvement_potential = current_monthly_value * authority_potential * traffic_improvement_factor
            annual_impact = improvement_potential * 12
            
            # Technical issues impact
            technical_impact = len(technical_issues) * 1000  # $1K per major technical issue
            
            # Total SEO impact
            raw_impact = annual_impact + technical_impact
            adjusted_impact = raw_impact * industry_multiplier * geographic_factor
            
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
            if len(technical_issues) > 0:
                recommendations.append(f"Fix {len(technical_issues)} technical SEO issues affecting search rankings")
            
            # Confidence interval
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
            logging.error(f"SEO impact calculation failed: {e}")
            return ScoreComponent(
                name="seo",
                raw_score=0,
                impact_estimate=0,
                confidence_interval=(0, 0),
                severity="P4",
                recommendations=["Unable to calculate SEO impact"]
            )
    
    def _calculate_ux_impact(
        self,
        visual_data: Dict[str, Any],
        industry_multiplier: float,
        geographic_factor: float
    ) -> ScoreComponent:
        """Calculate UX-related business impact."""
        try:
            # Extract UX metrics
            overall_ux_score = visual_data.get('overall_ux_score', 0)
            critical_issues = visual_data.get('critical_issues', [])
            positive_elements = visual_data.get('positive_elements', [])
            
            # Convert 0-2 scale to 0-100 scale
            ux_percentage = (overall_ux_score / 2.0) * 100
            
            # Calculate UX improvement potential
            ux_improvement_potential = max(0, 85 - ux_percentage) / 85
            
            # UX impact on conversion rates (research-based)
            baseline_conversion = 0.02  # 2% baseline conversion rate
            baseline_revenue = 100000  # $100K baseline revenue
            
            # Poor UX can reduce conversions by up to 30%
            ux_conversion_impact = baseline_revenue * 0.30 * ux_improvement_potential
            
            # Critical issues have higher impact
            critical_issue_impact = len(critical_issues) * 2000  # $2K per critical UX issue
            
            # Total UX impact
            raw_impact = ux_conversion_impact + critical_issue_impact
            adjusted_impact = raw_impact * industry_multiplier * geographic_factor
            
            # Determine severity
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
            
            # Confidence interval
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
            logging.error(f"UX impact calculation failed: {e}")
            return ScoreComponent(
                name="ux",
                raw_score=0,
                impact_estimate=0,
                confidence_interval=(0, 0),
                severity="P4",
                recommendations=["Unable to calculate UX impact"]
            )
    
    def _calculate_visual_impact(
        self,
        visual_data: Dict[str, Any],
        industry_multiplier: float,
        geographic_factor: float
    ) -> ScoreComponent:
        """Calculate visual design-related business impact."""
        try:
            # This would typically be separate from UX, focusing on brand/visual elements
            # For this implementation, we'll create a simplified visual scoring
            
            rubric_scores = visual_data.get('rubric_scores', {})
            brand_score = rubric_scores.get('brand_cohesion', {}).get('score', 0)
            image_quality_score = rubric_scores.get('image_quality', {}).get('score', 0)
            visual_hierarchy_score = rubric_scores.get('visual_hierarchy', {}).get('score', 0)
            
            # Average visual scores (0-2 scale)
            avg_visual_score = (brand_score + image_quality_score + visual_hierarchy_score) / 3
            visual_percentage = (avg_visual_score / 2.0) * 100
            
            # Visual impact on brand perception and trust
            # Poor visuals can reduce trust and conversions
            visual_improvement_potential = max(0, 85 - visual_percentage) / 85
            baseline_revenue = 100000
            
            # Visual design impacts brand trust, which affects conversion rates
            visual_trust_impact = baseline_revenue * 0.15 * visual_improvement_potential
            
            adjusted_impact = visual_trust_impact * industry_multiplier * geographic_factor
            
            # Determine severity based on visual scores
            if avg_visual_score < 0.8:
                severity = "P2"  # High - visual issues hurt brand perception
            elif avg_visual_score < 1.2:
                severity = "P3"  # Medium
            else:
                severity = "P4"  # Low
            
            recommendations = []
            if brand_score < 1.5:
                recommendations.append("Improve brand consistency and professional visual presentation")
            if image_quality_score < 1.5:
                recommendations.append("Upgrade image quality and visual assets for better brand perception")
            if visual_hierarchy_score < 1.5:
                recommendations.append("Enhance visual hierarchy to improve user navigation and engagement")
            
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
            logging.error(f"Visual impact calculation failed: {e}")
            return ScoreComponent(
                name="visual",
                raw_score=0,
                impact_estimate=0,
                confidence_interval=(0, 0),
                severity="P4",
                recommendations=["Unable to calculate visual impact"]
            )
    
    def _calculate_overall_score(self, component_scores: List[ScoreComponent]) -> float:
        """Calculate overall business score from component scores."""
        # Weight components based on business impact potential
        weights = {
            'performance': 0.30,  # Performance has highest revenue correlation
            'seo': 0.25,          # SEO drives long-term organic growth
            'security': 0.20,     # Security affects trust and conversions
            'ux': 0.15,           # UX affects user engagement
            'visual': 0.10        # Visual affects brand perception
        }
        
        weighted_scores = []
        for score in component_scores:
            weight = weights.get(score.name, 0.2)  # Default weight
            weighted_score = score.raw_score * weight
            weighted_scores.append(weighted_score)
        
        return sum(weighted_scores)
    
    def _load_lead_data(self, lead_id: int) -> Dict[str, Any]:
        """Load lead data from database."""
        # Implementation would load from database
        # For now, return mock data
        return {
            'naics_code': '541511',  # Custom Computer Programming Services
            'description': 'Web development company',
            'url': 'https://example.com',
            'state': 'CA',
            'county': 'San Francisco'
        }
    
    def _load_assessment_data(self, lead_id: int) -> Dict[str, Any]:
        """Load assessment data from all PRP services."""
        # Implementation would load from database
        # For now, return mock assessment data
        return {
            'pagespeed': {
                'mobile_performance_score': 45,
                'desktop_performance_score': 72,
                'mobile_lcp': 4.2,
                'desktop_lcp': 2.8
            },
            'security': {
                'https_enforced': True,
                'security_headers': {'hsts': False, 'csp': False},
                'ssl_grade': 'B'
            },
            'semrush': {
                'authority_score': 35,
                'organic_traffic_estimate': 1200,
                'ranking_keywords_count': 45,
                'technical_issues': ['broken links', 'missing meta descriptions']
            },
            'visual': {
                'overall_ux_score': 1.3,
                'critical_issues': ['poor CTA visibility', 'confusing navigation'],
                'positive_elements': ['clear branding'],
                'rubric_scores': {
                    'brand_cohesion': {'score': 1.5},
                    'image_quality': {'score': 1.0},
                    'visual_hierarchy': {'score': 1.2}
                }
            }
        }
    
    def _store_score_results(self, business_score: BusinessImpactScore) -> None:
        """Store calculated scores in database."""
        # Implementation would store in database
        logging.info(f"Storing business impact score for lead {business_score.lead_id}")
        pass
```

### Industry Classification Service

**NAICS Industry Classifier**:
```python
import json
import logging
from typing import Dict, Optional
import requests
from src.core.config import settings

class IndustryClassifier:
    """NAICS industry classification and economic multiplier service."""
    
    def __init__(self):
        """Initialize with NAICS data and multiplier tables."""
        self.naics_data = self._load_naics_data()
        self.multiplier_data = self._load_multiplier_data()
        
    def classify_business(
        self, 
        naics_code: Optional[str] = None, 
        business_description: str = "", 
        url: str = ""
    ) -> str:
        """
        Classify business and return 6-digit NAICS code.
        
        Args:
            naics_code: Existing NAICS code if available
            business_description: Text description of business
            url: Business website URL for analysis
            
        Returns:
            str: 6-digit NAICS code
        """
        if naics_code and len(naics_code) == 6:
            return naics_code
        
        # Simple classification logic - would be more sophisticated in production
        if any(term in business_description.lower() for term in ['web', 'software', 'app']):
            return '541511'  # Custom Computer Programming Services
        elif any(term in business_description.lower() for term in ['retail', 'store', 'shop']):
            return '454110'  # Electronic Shopping and Mail-Order Houses
        elif any(term in business_description.lower() for term in ['restaurant', 'food', 'dining']):
            return '722513'  # Limited-Service Restaurants
        else:
            return '541990'  # All Other Professional, Scientific Services (default)
    
    def get_industry_multipliers(self, naics_code: str) -> float:
        """Get economic multiplier for NAICS industry code."""
        # Industry-specific multipliers based on economic impact research
        multipliers = {
            '541511': 1.8,  # Computer Programming - high value services
            '454110': 1.2,  # E-commerce - moderate multiplier
            '722513': 1.1,  # Restaurants - lower digital impact
            '541990': 1.5   # Professional services - default
        }
        
        return multipliers.get(naics_code, 1.0)
    
    def _load_naics_data(self) -> Dict:
        """Load NAICS classification data."""
        # In production, this would load from official NAICS data files
        return {}
    
    def _load_multiplier_data(self) -> Dict:
        """Load economic multiplier data."""
        # In production, this would load from RIMS II or similar data
        return {}
```

### Database Models Extension

**Score Storage Models**:
```python
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.models.base import BaseModel

class BusinessScore(BaseModel):
    """Database model for calculated business impact scores."""
    
    __tablename__ = 'business_scores'
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey('leads.id'), nullable=False, index=True)
    
    # Overall scoring results
    overall_score = Column(Float, nullable=False, comment="Overall business score 0-100")
    total_impact_estimate = Column(Float, nullable=False, comment="Total dollar impact estimate")
    confidence_lower = Column(Float, nullable=False, comment="95% confidence interval lower bound")
    confidence_upper = Column(Float, nullable=False, comment="95% confidence interval upper bound")
    
    # Component scores (JSON for flexibility)
    performance_score = Column(JSON, nullable=True, comment="Performance component scoring details")
    security_score = Column(JSON, nullable=True, comment="Security component scoring details")
    seo_score = Column(JSON, nullable=True, comment="SEO component scoring details")
    ux_score = Column(JSON, nullable=True, comment="UX component scoring details")
    visual_score = Column(JSON, nullable=True, comment="Visual component scoring details")
    
    # Classification and adjustment factors
    industry_code = Column(String(6), nullable=False, comment="6-digit NAICS industry code")
    industry_multiplier = Column(Float, nullable=False, comment="Industry-specific economic multiplier")
    geographic_factor = Column(Float, nullable=False, comment="Geographic market adjustment factor")
    market_adjustment = Column(Float, nullable=False, comment="Combined market adjustment multiplier")
    
    # Calculation metadata
    calculation_timestamp = Column(DateTime, nullable=False)
    processing_time = Column(Float, nullable=False, comment="Calculation duration in seconds")
    validation_status = Column(String(20), default='validated', comment="Statistical validation status")
    
    # Relationships
    lead = relationship("Lead", back_populates="business_score")
    
    def __repr__(self):
        return f"<BusinessScore(lead_id={self.lead_id}, score={self.overall_score}, impact=${self.total_impact_estimate:.2f})>"
    
    @property
    def performance_grade(self) -> str:
        """Return letter grade based on overall score."""
        if self.overall_score >= 90:
            return "A"
        elif self.overall_score >= 80:
            return "B"
        elif self.overall_score >= 70:
            return "C"
        elif self.overall_score >= 60:
            return "D"
        else:
            return "F"
    
    @property
    def priority_issues(self) -> List[str]:
        """Extract P1 and P2 priority issues from component scores."""
        priority_issues = []
        
        for component_name in ['performance_score', 'security_score', 'seo_score', 'ux_score', 'visual_score']:
            component_data = getattr(self, component_name)
            if component_data and component_data.get('severity') in ['P1', 'P2']:
                recommendations = component_data.get('recommendations', [])
                priority_issues.extend(recommendations)
        
        return priority_issues[:5]  # Top 5 priority issues
    
    @property
    def roi_potential(self) -> float:
        """Calculate ROI potential based on total impact estimate."""
        # Assume $5K investment for improvements
        investment_cost = 5000
        if investment_cost > 0:
            return (self.total_impact_estimate / investment_cost) * 100
        return 0.0
```

## Tests to Pass

1. **Score Calculator Tests**: `pytest tests/test_score_calculator.py -v` validates impact calculation, confidence intervals, and component scoring with ≥90% coverage
2. **NAICS Integration Tests**: `pytest tests/test_industry_classifier.py -v` validates industry classification, multiplier application, and 6-digit code handling
3. **Geographic Adjustment Tests**: `pytest tests/test_geographic_adjuster.py -v` validates regional multipliers, market factors, and location-based adjustments
4. **Revenue Formula Tests**: `pytest tests/test_revenue_formulas.py -v` validates Amazon's 1% per 100ms formula, Core Web Vitals impact, and conversion calculations
5. **Confidence Interval Tests**: `pytest tests/test_statistical_validation.py -v` validates 95% confidence calculation, bootstrapping, and uncertainty quantification
6. **Component Integration Tests**: `pytest tests/integration/test_scoring_pipeline.py -v` validates complete scoring pipeline from raw metrics to business impact
7. **Performance Tests**: Sub-second calculation response times, handles 100+ concurrent requests with proper caching and optimization
8. **Database Integration Tests**: Score results properly stored in PostgreSQL, audit trails maintained, score history tracking functional
9. **Validation Framework Tests**: A/B testing integration validates scoring accuracy, cross-industry validation across NAICS sectors
10. **Edge Case Tests**: Missing data handling, invalid inputs, extreme values, and error recovery scenarios

## Implementation Guide

### Phase 1: Core Algorithm Development (Days 1-4)
1. **Score Calculator Engine**: Implement main calculation logic with component scoring and aggregation
2. **Revenue Formula Integration**: Apply proven formulas for performance, SEO, and UX impact calculation
3. **Statistical Framework**: Implement confidence interval calculation with bootstrapping validation
4. **Data Validation**: Add input validation and error handling for missing or invalid data
5. **Performance Optimization**: Implement caching and optimization for sub-second response times

### Phase 2: Industry & Geographic Integration (Days 5-7)
1. **NAICS Classification**: Build industry classifier with 6-digit code support and economic multipliers
2. **Geographic Adjustment**: Implement regional market factors and local multiplier effects
3. **Multiplier Data**: Load and integrate economic multiplier data from RIMS II or equivalent sources
4. **Classification Logic**: Build business classification logic using description and URL analysis
5. **Validation Testing**: Test classification accuracy across different industry sectors

### Phase 3: Database & API Integration (Days 8-10)
1. **Database Models**: Create score storage models with JSON fields for component details
2. **Assessment Integration**: Connect with all assessment PRPs (003-008) for raw metric input
3. **API Endpoints**: Create FastAPI endpoints for score calculation and retrieval
4. **Audit Trails**: Implement score history tracking and change auditing
5. **Performance Monitoring**: Add logging, metrics, and monitoring for calculation performance

### Phase 4: Validation & Testing (Days 11-12)
1. **Statistical Validation**: Implement A/B testing framework for continuous scoring accuracy improvement
2. **Cross-Industry Testing**: Validate scoring accuracy across different NAICS sectors and business types
3. **Load Testing**: Verify performance under concurrent load with proper caching strategies
4. **Edge Case Testing**: Test with missing data, extreme values, and error scenarios
5. **Integration Testing**: Validate complete pipeline from assessment data to score storage

## Validation Commands

```bash
# Score calculator validation
python -c "from src.scoring.calculator import ScoreCalculator; calc = ScoreCalculator(); print('Calculator initialized successfully')"

# Business impact calculation
python -c "
from src.scoring.calculator import ScoreCalculator
calc = ScoreCalculator()
result = calc.calculate_impact(1)
print(f'Business Score: {result.overall_score:.1f}, Impact: ${result.total_impact_estimate:.2f}')
"

# NAICS classification validation
python -c "
from src.scoring.industry_classifier import IndustryClassifier
classifier = IndustryClassifier()
code = classifier.classify_business(business_description='web development company')
print(f'NAICS Code: {code}, Multiplier: {classifier.get_industry_multipliers(code)}')
"

# Database integration validation
psql -h localhost -U leadfactory -d leadfactory -c "SELECT lead_id, overall_score, total_impact_estimate FROM business_scores WHERE validation_status='validated' LIMIT 5;"

# Performance validation
python scripts/scoring_load_test.py --leads=100 --workers=4 --duration=300

# Statistical validation
python -c "
from src.scoring.statistics import StatisticalValidator
validator = StatisticalValidator()
ci = validator.calculate_confidence_intervals([1000, 1500, 2000], confidence_level=0.95)
print(f'95% Confidence Interval: ${ci[0]:.2f} - ${ci[1]:.2f}')
"

# Component scoring validation
python -c "
from src.scoring.calculator import ScoreCalculator
calc = ScoreCalculator()
# Test individual component calculation
performance_score = calc._calculate_performance_impact(
    {'mobile_performance_score': 45, 'desktop_performance_score': 72}, 1.8, 1.2
)
print(f'Performance Impact: ${performance_score.impact_estimate:.2f}, Severity: {performance_score.severity}')
"
```

## Rollback Strategy

### Emergency Procedures
1. **Calculation Failure**: Revert to v1 scoring algorithm with simplified business impact estimates
2. **Performance Issues**: Enable caching layer and reduce calculation complexity for basic scoring
3. **Data Quality Issues**: Implement fallback scoring with industry averages when assessment data incomplete
4. **Statistical Validation Failure**: Use simplified confidence intervals with fixed uncertainty ranges

### Detailed Rollback Steps
1. **Identify Issue**: Monitor dashboards show scoring failures >5% or calculation timeouts >2 seconds
2. **Immediate Response**: Switch to v1 scoring algorithm and preserve existing score data
3. **Data Preservation**: Ensure all calculated scores are backed up before system changes
4. **Issue Analysis**: Analyze scoring accuracy, performance metrics, and statistical validation results
5. **Gradual Recovery**: Test fixes with subset of leads before full system re-enablement
6. **Validation Testing**: Verify scoring accuracy and performance meet requirements before full deployment

## Success Criteria

1. **Scoring Algorithm Complete**: Multi-layered calculator transforms raw metrics into dollar impact estimates with statistical confidence
2. **NAICS Integration Working**: Industry-specific multipliers applied based on 6-digit classification with economic factor adjustments
3. **Geographic Adjustment Functional**: Regional market factors properly adjust estimates based on local economic conditions
4. **Revenue Correlation Accurate**: Proven formulas (Amazon's 1% per 100ms) correctly applied to technical performance metrics
5. **Confidence Intervals Provided**: 95% statistical confidence ranges calculated for all business impact estimates
6. **Performance Requirements Met**: Sub-second calculation response times with support for 100+ concurrent requests
7. **Database Integration Complete**: Score results stored in PostgreSQL with proper audit trails and history tracking
8. **Validation Framework Active**: A/B testing integration enables continuous scoring accuracy improvement

## Critical Context

### Revenue Impact Research Foundation
- **Amazon Formula**: 1% revenue increase per 100ms page load improvement (proven at scale)
- **Core Web Vitals**: 13% conversion increase per second LCP improvement, 42% mobile revenue from 23% speed increase
- **Security Impact**: HTTPS enforcement prevents 14% conversion loss, security headers affect trust metrics
- **SEO Revenue**: $2 per organic visitor value, authority improvements drive 50% traffic increases

### NAICS Industry Framework
- **6-Digit Classification**: Hierarchical system covering 20 industry sectors with specific economic multipliers
- **Economic Multipliers**: Regional input-output analysis provides county-level adjustment factors
- **Industry Specificity**: Computer programming (1.8x), E-commerce (1.2x), Professional services (1.5x) multipliers
- **Geographic Factors**: Local economic conditions, income levels, market purchasing power variations

### Statistical Validation Requirements
- **95% Confidence Intervals**: Standard business decision-making threshold with proper uncertainty quantification
- **Bootstrapping Methods**: Complex model validation using resampling techniques for reliability assessment
- **A/B Testing Integration**: Continuous scoring accuracy improvement through statistical hypothesis testing
- **Cross-Validation**: Consistency verification across different data subsets and industry sectors

### Business Value Integration
- **Executive Reporting**: Technical complexity translated into clear dollar impact estimates for decision-making
- **ROI Justification**: $399 audit report pricing supported by quantifiable improvement potential calculations
- **Priority Framework**: P1-P4 issue classification enables actionable improvement roadmaps for clients
- **Competitive Advantage**: Sophisticated scoring methodology differentiates platform from basic website analysis tools

## Definition of Done

- [ ] Score calculator implemented with multi-layered algorithm combining all assessment dimensions
- [ ] NAICS industry classification integrated with 6-digit codes and economic multiplier application
- [ ] Geographic market adjustment functional with regional input-output analysis multipliers
- [ ] Revenue impact formulas implemented using proven research (Amazon, Core Web Vitals studies)
- [ ] Statistical confidence intervals calculated using 95% threshold with bootstrapping validation
- [ ] Component scoring covers performance, security, SEO, UX, and visual assessment integration
- [ ] Database models store complete scoring results with audit trails and history tracking
- [ ] Unit tests written for all calculator methods and statistical functions with ≥90% coverage
- [ ] Integration tests validate complete scoring pipeline from raw metrics to business impact
- [ ] Performance testing confirms sub-second response times with concurrent request handling
- [ ] A/B testing framework enables continuous scoring accuracy validation and improvement
- [ ] Production testing validates scoring accuracy across different industry sectors and business types
- [ ] Code review completed with statistical methodology validation and business logic verification
- [ ] Documentation updated with scoring methodology, confidence interval calculation, and usage procedures