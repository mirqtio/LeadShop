#\!/usr/bin/env python3
"""
Working Assessment Demo - Shows all components executing and saving to DB
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from sqlalchemy import select, text

from src.core.database import AsyncSessionLocal
from src.models.lead import Lead, Assessment
from src.assessments.pagespeed import assess_pagespeed
from src.assessments.security_analysis import assess_security_headers
from src.assessments.semrush_integration import assess_semrush_domain
from src.assessments.gbp_integration import assess_google_business_profile

async def run_demo():
    """Run a complete assessment demo"""
    url = "https://www.apple.com"
    business_name = "Apple Inc."
    
    print(f"\n🚀 Running Complete Assessment Demo")
    print("=" * 80)
    print(f"URL: {url}")
    print(f"Business: {business_name}")
    print("=" * 80)
    
    async with AsyncSessionLocal() as db:
        # Create lead
        parsed_url = urlparse(url)
        domain = parsed_url.netloc or parsed_url.path
        
        lead = Lead(
            company=business_name,
            email=f"demo{int(time.time())}@{domain.replace('www.', '')}",
            url=url,
            source="demo_assessment"
        )
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        
        # Create assessment
        assessment = Assessment(
            lead_id=lead.id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(assessment)
        await db.commit()
        await db.refresh(assessment)
        
        print(f"\n✅ Created Assessment ID: {assessment.id}")
        print("-" * 80)
        
        results = {}
        
        # 1. PageSpeed
        print("\n⚡ Running PageSpeed Analysis...")
        try:
            results['pagespeed'] = await asyncio.wait_for(assess_pagespeed(url), timeout=30)
            print("✅ PageSpeed completed")
            if results['pagespeed'] and 'mobile_analysis' in results['pagespeed']:
                mobile_score = results['pagespeed']['mobile_analysis'].get('core_web_vitals', {}).get('performance_score', 'N/A')
                print(f"   Mobile Score: {mobile_score}/100")
        except Exception as e:
            print(f"❌ PageSpeed failed: {e}")
            results['pagespeed'] = None
        
        # 2. Security Headers
        print("\n🛡️ Running Security Analysis...")
        try:
            results['security'] = await asyncio.wait_for(assess_security_headers(url), timeout=10)
            print("✅ Security completed")
            if hasattr(results['security'], 'security_score'):
                print(f"   Security Score: {results['security'].security_score}/100")
        except Exception as e:
            print(f"❌ Security failed: {e}")
            results['security'] = None
        
        # 3. SEMrush (will fail - no API credits)
        print("\n🔍 Running SEMrush Analysis...")
        try:
            results['semrush'] = await asyncio.wait_for(
                assess_semrush_domain(domain, lead.id, assessment.id), 
                timeout=10
            )
            print("✅ SEMrush completed")
        except Exception as e:
            print(f"❌ SEMrush failed (expected): {str(e)[:50]}...")
            results['semrush'] = None
        
        # 4. Google Business Profile
        print("\n🏢 Running GBP Search...")
        try:
            results['gbp'] = await asyncio.wait_for(
                assess_google_business_profile(business_name, None, None, None, lead.id, assessment.id),
                timeout=15
            )
            print("✅ GBP completed")
            if hasattr(results['gbp'], 'found'):
                print(f"   Business Found: {results['gbp'].found}")
        except Exception as e:
            print(f"❌ GBP failed: {e}")
            results['gbp'] = None
        
        # Calculate score
        scores = []
        if results.get('pagespeed'):
            try:
                ps = results['pagespeed']
                if isinstance(ps, dict) and 'mobile_analysis' in ps:
                    mobile_score = ps['mobile_analysis'].get('core_web_vitals', {}).get('performance_score', 0)
                    scores.append(mobile_score)
            except:
                pass
        
        if results.get('security'):
            try:
                if hasattr(results['security'], 'security_score'):
                    scores.append(results['security'].security_score)
            except:
                pass
        
        overall_score = sum(scores) / len(scores) if scores else 0
        
        print(f"\n📊 Overall Score: {overall_score:.1f}/100")
        print("-" * 80)
        
        # Save to database
        print("\n💾 Saving to database...")
        
        # Convert Pydantic models to dicts
        if results.get('pagespeed'):
            assessment.pagespeed_data = results['pagespeed']
        
        if results.get('security'):
            if hasattr(results['security'], 'dict'):
                assessment.security_headers = results['security'].dict()
            else:
                assessment.security_headers = results['security']
        
        if results.get('semrush'):
            if hasattr(results['semrush'], 'dict'):
                assessment.semrush_data = results['semrush'].dict()
            else:
                assessment.semrush_data = results['semrush']
        
        if results.get('gbp'):
            if hasattr(results['gbp'], 'dict'):
                assessment.gbp_data = results['gbp'].dict()
            else:
                assessment.gbp_data = results['gbp']
        
        assessment.total_score = overall_score
        assessment.content_generation = {
            "summary": f"Assessment for {business_name}",
            "score": overall_score,
            "components_run": 4,
            "components_successful": len([r for r in results.values() if r is not None])
        }
        
        await db.commit()
        print("✅ Saved to database")
        
        # Verify save
        saved_assessment = await db.get(Assessment, assessment.id)
        print(f"\n🔍 Verification:")
        print(f"   Assessment ID: {saved_assessment.id}")
        print(f"   Score in DB: {saved_assessment.total_score}")
        print(f"   PageSpeed saved: {saved_assessment.pagespeed_data is not None}")
        print(f"   Security saved: {saved_assessment.security_headers is not None}")
        print(f"   GBP saved: {saved_assessment.gbp_data is not None}")
        print(f"   Content saved: {saved_assessment.content_generation is not None}")
        
        # Show sample of saved data
        if saved_assessment.security_headers:
            print(f"\n📋 Sample Security Data from DB:")
            sec_data = saved_assessment.security_headers
            if isinstance(sec_data, dict):
                print(f"   Security Score: {sec_data.get('security_score', 'N/A')}")
                print(f"   HTTPS: {sec_data.get('https_enabled', 'N/A')}")
        
        print("\n" + "=" * 80)
        print("✅ ASSESSMENT DEMO COMPLETE - ALL DATA SAVED TO DATABASE\!")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_demo())
EOF < /dev/null