#!/usr/bin/env python3
"""
Re-run decomposition for assessment to extract all available metrics
"""

import asyncio
from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.models.lead import Assessment
from src.assessment.decompose_metrics import decompose_and_store_metrics
from src.models.assessment_results import AssessmentResults

async def redecompose_assessment(assessment_id: int):
    async with AsyncSessionLocal() as db:
        # Get the assessment
        result = await db.execute(
            select(Assessment).where(Assessment.id == assessment_id)
        )
        assessment = result.scalar_one_or_none()
        
        if not assessment:
            print(f"❌ Assessment {assessment_id} not found")
            return
        
        print(f"📊 Assessment {assessment_id}:")
        print(f"  Status: {assessment.status}")
        print(f"  PageSpeed Score: {assessment.pagespeed_score}")
        print(f"  Security Score: {assessment.security_score}")
        
        # Check what data is available
        has_pagespeed = assessment.pagespeed_data is not None
        has_security = assessment.security_headers is not None
        has_gbp = assessment.gbp_data is not None
        has_semrush = assessment.semrush_data is not None
        has_visual = assessment.visual_analysis is not None
        
        print(f"\n📈 Available Data:")
        print(f"  PageSpeed: {'✅' if has_pagespeed else '❌'}")
        print(f"  Security: {'✅' if has_security else '❌'}")
        print(f"  GBP: {'✅' if has_gbp else '❌'}")
        print(f"  SEMrush: {'✅' if has_semrush else '❌'}")
        print(f"  Visual: {'✅' if has_visual else '❌'}")
        
        # Show GBP data if available
        if has_gbp and assessment.gbp_data:
            print(f"\n🏪 GBP Data:")
            if isinstance(assessment.gbp_data, dict):
                print(f"  Found: {assessment.gbp_data.get('found', False)}")
                print(f"  Confidence: {assessment.gbp_data.get('confidence', 0)}")
                print(f"  Rating: {assessment.gbp_data.get('rating', 'N/A')}")
                print(f"  Reviews: {assessment.gbp_data.get('total_reviews', 0)}")
        
        # Show SEMrush data if available
        if has_semrush and assessment.semrush_data:
            print(f"\n📊 SEMrush Data:")
            if isinstance(assessment.semrush_data, dict):
                print(f"  Success: {assessment.semrush_data.get('success', False)}")
                print(f"  Authority Score: {assessment.semrush_data.get('authority_score', 'N/A')}")
                print(f"  Organic Traffic: {assessment.semrush_data.get('organic_traffic_estimate', 'N/A')}")
        
        # Re-run decomposition
        print(f"\n🔄 Re-running decomposition...")
        result = await decompose_and_store_metrics(db, assessment_id)
        
        if result:
            # Get the metrics
            metrics = result.get_all_metrics()
            non_null = {k: v for k, v in metrics.items() if v is not None}
            
            print(f"\n✅ Decomposition complete: {len(non_null)} / 53 metrics extracted")
            
            # Show breakdown by category
            categories = {
                'PageSpeed': [k for k in non_null.keys() if 'First Contentful' in k or 'Largest Contentful' in k or 'Cumulative' in k or 'Speed' in k or 'Performance Score' in k],
                'Security': [k for k in non_null.keys() if 'HTTPS' in k or 'TLS' in k or 'Header' in k or 'robots' in k or 'sitemap' in k],
                'GBP': [k for k in non_null.keys() if 'hours' in k.lower() or 'review' in k.lower() or 'rating' in k.lower() or 'photos' in k.lower() or 'closed' in k.lower()],
                'SEMrush': [k for k in non_null.keys() if 'Site Health' in k or 'Domain Authority' in k or 'Organic Traffic' in k or 'Ranking Keywords' in k or 'Backlink' in k],
                'Visual': [k for k in non_null.keys() if 'visual' in k.lower() or 'Screenshot' in k],
                'Content': [k for k in non_null.keys() if 'content' in k.lower()]
            }
            
            for category, keys in categories.items():
                if keys:
                    print(f"\n{category} Metrics ({len(keys)}):")
                    for key in keys[:5]:  # Show first 5
                        print(f"  - {key}: {non_null[key]}")
                    if len(keys) > 5:
                        print(f"  ... and {len(keys) - 5} more")
        else:
            print(f"❌ Decomposition failed")

if __name__ == "__main__":
    # Try assessment 105 which is the most recent
    asyncio.run(redecompose_assessment(105))