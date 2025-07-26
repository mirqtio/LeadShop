#!/usr/bin/env python3
"""Simple test for SEMrush integration without full orchestrator"""

import asyncio
import logging
import os
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_semrush_only():
    """Test just the SEMrush integration"""
    
    # Test URL
    test_url = "https://www.example.com"
    parsed_url = urlparse(test_url)
    domain = parsed_url.netloc.replace('www.', '')
    
    print(f"\n🚀 Testing SEMrush integration for domain: {domain}")
    print("=" * 60)
    
    # Check if API key is set
    api_key = os.environ.get('SEMRUSH_API_KEY')
    if not api_key:
        print("⚠️  SEMRUSH_API_KEY not set in environment")
        print("Please set it to test the integration")
        return
    
    try:
        # Import and test SEMrush client directly
        from src.assessments.semrush_integration import SEMrushClient
        
        client = SEMrushClient()
        
        # Test API balance check
        balance = await client._check_api_balance()
        print(f"\nAPI Balance: {balance} units")
        
        # Test domain analysis
        print(f"\nAnalyzing domain: {domain}")
        metrics = await client.analyze_domain(domain)
        
        print(f"\nResults:")
        print(f"  Authority Score: {metrics.authority_score}")
        print(f"  Organic Traffic: {metrics.organic_traffic_estimate}")
        print(f"  Keywords Count: {metrics.ranking_keywords_count}")
        print(f"  Site Health: {metrics.site_health_score}%")
        print(f"  Backlink Toxicity: {metrics.backlink_toxicity_score}%")
        print(f"  Technical Issues: {len(metrics.technical_issues)}")
        
        if metrics.technical_issues:
            print(f"\nTechnical Issues Found:")
            for issue in metrics.technical_issues:
                print(f"  - [{issue.severity}] {issue.description}")
        
        print(f"\nAPI Cost: {metrics.api_cost_units} units")
        print(f"Processing Time: {metrics.extraction_duration_ms}ms")
        
        await client.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ Test completed")

if __name__ == "__main__":
    asyncio.run(test_semrush_only())