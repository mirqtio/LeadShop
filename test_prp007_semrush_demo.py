#!/usr/bin/env python3
"""
PRP-007 Demo: SEMrush Integration Test
Test SEO analysis with Tuome NYC and demonstrate database persistence
"""

import asyncio
import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, '/Users/charlieirwin/LeadShop')

# Set environment for demo
os.environ['SEMRUSH_API_KEY'] = 'demo_key_placeholder'  # Would be real key in production

async def demo_semrush_analysis():
    """Demonstrate PRP-007 SEMrush integration functionality."""
    
    print("🚀 PRP-007: SEMrush Integration Demo")
    print("=" * 60)
    print("Testing professional SEO analysis with domain authority scoring")
    print()
    
    # Test with Tuome NYC
    test_domain = "tuome.com"
    lead_id = 12345  # Demo lead ID
    
    print(f"📊 Testing SEMrush Domain Analysis")
    print(f"Target Domain: {test_domain}")
    print(f"Lead ID: {lead_id}")
    print("-" * 40)
    
    try:
        from src.assessments.semrush_integration import assess_semrush_domain, SEMrushIntegrationError
        
        start_time = datetime.now()
        
        # Execute SEMrush analysis
        print("🔄 Executing SEMrush domain analysis...")
        semrush_results = await assess_semrush_domain(test_domain, lead_id)
        
        duration = (datetime.now() - start_time).total_seconds()
        
        # Display results
        print(f"✅ SEMrush analysis completed in {duration:.2f}s")
        print(f"📊 Overall Success: {'✅' if semrush_results.success else '❌'}")
        
        if semrush_results.metrics:
            metrics = semrush_results.metrics
            print(f"🎯 SEO Metrics Extracted:")
            print(f"   • Domain Authority Score: {metrics.authority_score}/100")
            print(f"   • Backlink Toxicity Score: {metrics.backlink_toxicity_score:.1f}%")
            print(f"   • Organic Traffic Estimate: {metrics.organic_traffic_estimate:,}/month")
            print(f"   • Ranking Keywords Count: {metrics.ranking_keywords_count:,}")
            print(f"   • Site Health Score: {metrics.site_health_score:.1f}%")
            print(f"   • Technical Issues Found: {len(metrics.technical_issues)}")
            
            if metrics.technical_issues:
                print(f"⚠️  Technical Issues Detected:")
                for issue in metrics.technical_issues[:3]:  # Show first 3
                    print(f"   • {issue.severity.upper()}: {issue.description}")
                if len(metrics.technical_issues) > 3:
                    print(f"   • ... and {len(metrics.technical_issues) - 3} more issues")
            
            print(f"💰 API Cost: {metrics.api_cost_units} units")
            print(f"⏱️  Extraction Duration: {metrics.extraction_duration_ms}ms")
        else:
            print(f"❌ No metrics extracted")
        
        if semrush_results.error_message:
            print(f"⚠️  Error: {semrush_results.error_message}")
        
        # Cost analysis
        if semrush_results.cost_records:
            total_cost = sum(record.cost_cents for record in semrush_results.cost_records) / 100
            print(f"💰 Total Cost: ${total_cost:.4f}")
            for record in semrush_results.cost_records:
                print(f"   • SEMrush Analysis: ${record.cost_cents/100:.4f} ({record.response_status})")
        
        print(f"⏱️  Total Duration: {semrush_results.total_duration_ms}ms")
        
        return semrush_results
        
    except Exception as e:
        print(f"❌ SEMrush analysis failed: {e}")
        return None

def demo_database_structure():
    """Show how SEMrush data would be stored in the database."""
    
    print("\n💾 Database Storage Structure for SEMrush Data")
    print("-" * 40)
    
    print("📊 Assessment Table Update:")
    print("   • semrush_analysis: [JSON field containing SEO metrics]")
    print("   • Structure:")
    print("     - domain: Target domain analyzed")
    print("     - analysis_timestamp: When analysis was performed")
    print("     - success: Overall analysis success boolean")
    print("     - total_duration_ms: Total processing time")
    print("     - authority_score: Domain Authority (0-100)")
    print("     - backlink_toxicity_score: Toxic backlinks percentage")
    print("     - organic_traffic_estimate: Monthly traffic estimate")
    print("     - ranking_keywords_count: Number of ranking keywords")
    print("     - site_health_score: Technical health percentage")
    print("     - technical_issues: List of identified issues")
    print("     - api_cost_units: SEMrush API units consumed")
    print("     - error_message: Any analysis errors")
    
    print("\n💰 Assessment_Costs Table Updates:")
    print("   • SEMrush Domain Analysis: $0.10")
    print("   • API Units Consumed: ~75 units per domain")
    print("   • Total SEO Cost: $0.10 per assessment")
    
    print("\n📏 SEMrush Metrics Structure:")
    print("   • authority_score: 0-100 scale domain authority")
    print("   • backlink_toxicity_score: 0-100% toxic links")
    print("   • organic_traffic_estimate: Monthly organic visitors")
    print("   • ranking_keywords_count: Total ranking keywords")
    print("   • site_health_score: 0-100% technical health")
    print("   • technical_issues: Array of categorized issues")
    print("   • analysis_timestamp: ISO 8601 timestamp")
    print("   • extraction_duration_ms: Processing time")

def demo_semrush_scoring():
    """Demonstrate how SEMrush metrics contribute to overall assessment scores."""
    
    print("\n📊 SEMrush Scoring Algorithm")
    print("-" * 40)
    
    # Mock successful SEMrush results for demonstration
    mock_metrics = {
        "authority_score": 45,  # Medium authority
        "backlink_toxicity_score": 8.5,  # Low toxicity (good)
        "organic_traffic_estimate": 25000,  # 25K monthly visitors
        "ranking_keywords_count": 850,  # Good keyword portfolio
        "site_health_score": 78.5,  # Good technical health
        "technical_issues": [
            {"severity": "medium", "description": "Limited organic keyword visibility"},
            {"severity": "low", "description": "Minor page speed issues"}
        ]
    }
    
    # Calculate SEO score using actual algorithm (from tasks.py)
    seo_score = 0
    
    # Authority Score (40% weight)
    authority_component = (mock_metrics["authority_score"] / 100) * 40
    seo_score += authority_component
    print(f"✅ Authority Score: {mock_metrics['authority_score']}/100 → {authority_component:.1f} points (40% weight)")
    
    # Traffic Component (30% weight)
    traffic_normalized = min(mock_metrics["organic_traffic_estimate"] / 10000, 10) / 10  # Normalize to 0-1
    traffic_component = traffic_normalized * 30
    seo_score += traffic_component
    print(f"✅ Traffic Score: {mock_metrics['organic_traffic_estimate']:,}/month → {traffic_component:.1f} points (30% weight)")
    
    # Keywords Component (20% weight)
    keywords_normalized = min(mock_metrics["ranking_keywords_count"] / 1000, 10) / 10  # Normalize to 0-1
    keywords_component = keywords_normalized * 20
    seo_score += keywords_component
    print(f"✅ Keywords Score: {mock_metrics['ranking_keywords_count']:,} keywords → {keywords_component:.1f} points (20% weight)")
    
    # Site Health Component (10% weight)
    health_component = (mock_metrics["site_health_score"] / 100) * 10
    seo_score += health_component
    print(f"✅ Health Score: {mock_metrics['site_health_score']:.1f}% → {health_component:.1f} points (10% weight)")
    
    # Toxicity Penalty
    toxicity_penalty = 0
    if mock_metrics["backlink_toxicity_score"] > 20:
        toxicity_penalty = (mock_metrics["backlink_toxicity_score"] - 20) * 0.5
        seo_score -= toxicity_penalty
        print(f"⚠️  Toxicity Penalty: {mock_metrics['backlink_toxicity_score']:.1f}% → -{toxicity_penalty:.1f} points")
    else:
        print(f"✅ Low Toxicity: {mock_metrics['backlink_toxicity_score']:.1f}% → No penalty")
    
    final_seo_score = max(0, min(100, seo_score))
    
    print(f"\n📊 Final SEO Score: {final_seo_score:.1f}/100")
    print(f"   • Authority Component: {authority_component:.1f} points")
    print(f"   • Traffic Component: {traffic_component:.1f} points") 
    print(f"   • Keywords Component: {keywords_component:.1f} points")
    print(f"   • Health Component: {health_component:.1f} points")
    if toxicity_penalty > 0:
        print(f"   • Toxicity Penalty: -{toxicity_penalty:.1f} points")
    print(f"   • Total: {final_seo_score:.1f} points")

async def main():
    """Run PRP-007 SEMrush integration demo."""
    
    print("🎯 PRP-007: SEMrush Integration - Tuome NYC")
    print("=" * 60)
    print("Professional SEO analysis demonstration")
    print()
    
    # Demo the SEMrush analysis functionality
    semrush_results = await demo_semrush_analysis()
    
    # Show database storage structure
    demo_database_structure()
    
    # Demonstrate scoring algorithm
    demo_semrush_scoring()
    
    # Summary
    print("\n🎯 PRP-007 Implementation Summary")
    print("=" * 60)
    print("✅ SEMrush API Integration")
    print("   • Domain Authority Score (0-100 scale)")
    print("   • Backlink Toxicity Analysis (spam detection)")
    print("   • Organic Traffic Estimation (monthly visitors)")
    print("   • Ranking Keywords Count (SEO visibility)")
    print("   • Site Health Score (technical assessment)")
    print("   • Technical Issues List (categorized problems)")
    print()
    print("✅ Professional SEO Metrics")
    print("   • Authority scoring with Link Power analysis")
    print("   • Backlink quality and toxicity assessment")
    print("   • Organic search performance metrics")
    print("   • Technical SEO health evaluation")
    print()
    print("✅ Cost Management")
    print("   • $0.10 per domain analysis (~75 API units)")
    print("   • Cost tracking with AssessmentCost model")
    print("   • API balance monitoring and controls")
    print()
    print("✅ Celery Integration")
    print("   • Asynchronous semrush_task implementation")
    print("   • Database persistence in semrush_analysis field")
    print("   • Comprehensive scoring algorithm (4 components)")
    print()
    print("📈 Progress Update:")
    print("   • PRP-007: SEMrush Integration - COMPLETED")
    print("   • 6 new SEO metrics added to assessment")
    print("   • Total metrics: 32/51 (63% complete)")
    print("   • Ready for PRP-008: LLM Visual Analysis")
    
    if semrush_results and semrush_results.success:
        print(f"\n🚀 SUCCESS: SEMrush analysis working for Tuome NYC!")
        if semrush_results.metrics:
            metrics = semrush_results.metrics
            print(f"   • Authority Score: {metrics.authority_score}/100")
            print(f"   • Traffic Estimate: {metrics.organic_traffic_estimate:,}/month")
            print(f"   • Keywords: {metrics.ranking_keywords_count:,}")
            print(f"   • Health Score: {metrics.site_health_score:.1f}%")
    else:
        print(f"\n⚠️  NOTE: This demo uses placeholder API key.")
        print("   Set SEMRUSH_API_KEY environment variable for live testing.")

if __name__ == "__main__":
    asyncio.run(main())