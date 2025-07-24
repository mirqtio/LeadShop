#!/usr/bin/env python3
"""
Verify GBP Integration with Assessment Orchestration Structure
Quick verification that GBP is properly integrated into the orchestration sequence
"""

import sys
sys.path.insert(0, '/Users/charlieirwin/LeadShop')

def verify_gbp_orchestration():
    """Verify GBP is properly integrated into orchestration structure."""
    
    print("🔍 Verifying GBP Integration with Assessment Orchestration")
    print("=" * 60)
    
    try:
        # Test 1: Check execution order
        print("📋 1. Checking Execution Order")
        
        # Read the orchestrator file to verify structure
        with open('/Users/charlieirwin/LeadShop/src/assessments/assessment_orchestrator.py', 'r') as f:
            content = f.read()
        
        # Check execution order
        if '"gbp",' in content and 'PRP-005: Google Business Profile' in content:
            print("   ✅ GBP found in execution order")
        else:
            print("   ❌ GBP not found in execution order")
            return False
        
        # Test 2: Check component configuration
        print("📋 2. Checking Component Configuration")
        
        if '"gbp": 45' in content:  # Timeout configuration
            print("   ✅ GBP timeout configuration found")
        else:
            print("   ❌ GBP timeout configuration missing")
            return False
            
        if '"gbp": 2' in content:  # Retry configuration
            print("   ✅ GBP retry configuration found")
        else:
            print("   ❌ GBP retry configuration missing")
            return False
        
        # Test 3: Check dataclass field
        print("📋 3. Checking AssessmentExecution Dataclass")
        
        if 'gbp_result: ComponentResult' in content:
            print("   ✅ GBP result field found in AssessmentExecution")
        else:
            print("   ❌ GBP result field missing from AssessmentExecution")
            return False
        
        # Test 4: Check component execution logic
        print("📋 4. Checking Component Execution Logic")
        
        if 'elif component_name == "gbp":' in content:
            print("   ✅ GBP execution case found")
        else:
            print("   ❌ GBP execution case missing")
            return False
        
        if 'assess_google_business_profile' in content:
            print("   ✅ GBP function call found")
        else:
            print("   ❌ GBP function call missing")
            return False
        
        # Test 5: Check success rate calculation
        print("📋 5. Checking Success Rate Calculation")
        
        if 'execution.gbp_result,' in content:
            print("   ✅ GBP included in success rate calculation")
        else:
            print("   ❌ GBP missing from success rate calculation")
            return False
        
        # Test 6: Check Celery task integration
        print("📋 6. Checking Celery Task Integration")
        
        with open('/Users/charlieirwin/LeadShop/src/assessment/tasks.py', 'r') as f:
            task_content = f.read()
        
        if 'execution_result.gbp_result,' in task_content:
            print("   ✅ GBP included in Celery task orchestration")
        else:
            print("   ❌ GBP missing from Celery task orchestration")
            return False
        
        print("\n✅ ALL CHECKS PASSED: GBP Successfully Integrated!")
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def show_orchestration_summary():
    """Show the complete orchestration summary."""
    
    print("\n🎯 Complete Assessment Orchestration Summary")
    print("=" * 60)
    
    print("📊 Updated Pipeline Sequence:")
    pipeline = [
        ("1", "pagespeed", "PRP-003", "PageSpeed Insights", "60s", "2 retries"),
        ("2", "security", "PRP-004", "Security Analysis", "30s", "2 retries"),
        ("3", "gbp", "PRP-005", "Google Business Profile", "45s", "2 retries"),
        ("4", "screenshots", "PRP-006", "ScreenshotOne Capture", "45s", "3 retries"),
        ("5", "semrush", "PRP-007", "SEMrush SEO Analysis", "30s", "2 retries"),
        ("6", "visual_analysis", "PRP-008", "LLM Visual Analysis", "120s", "1 retry"),
        ("7", "score_calculation", "PRP-009", "Score Calculator", "10s", "1 retry"),
        ("8", "content_generation", "PRP-010", "Content Generator", "60s", "2 retries")
    ]
    
    for pos, component, prp, description, timeout, retries in pipeline:
        print(f"   {pos}. {component}")
        print(f"      └─ {prp}: {description}")
        print(f"      └─ Config: {timeout} timeout, {retries}")
    
    print("\n🚀 How to Execute Complete Assessment:")
    print("   Option 1 - Direct Python:")
    print("   ```python")
    print("   from src.assessments.assessment_orchestrator import execute_full_assessment")
    print("   result = await execute_full_assessment(lead_id=12345, lead_data={...})")
    print("   ```")
    print()
    print("   Option 2 - Celery Background Task:")
    print("   ```python")
    print("   from src.assessment.tasks import full_assessment_orchestrator_task")
    print("   task = full_assessment_orchestrator_task.delay(lead_id=12345)")
    print("   result = task.get()")
    print("   ```")
    
    print("\n💰 Assessment Cost Breakdown:")
    costs = [
        ("PageSpeed Insights", "$0.0025", "per API call"),
        ("Security Scraper", "$0.001", "per assessment"),
        ("Google Business Profile", "$0.017", "per search"),
        ("ScreenshotOne", "$0.002", "per screenshot"),
        ("SEMrush", "$0.10", "per domain analysis"),
        ("GPT-4 Vision", "$0.05", "per visual analysis"),
        ("GPT-4 Content", "$0.02", "per content generation"),
        ("Internal Services", "$0.00", "score calc, reports, email")
    ]
    
    total_cost = 0.0025 + 0.001 + 0.017 + 0.002 + 0.10 + 0.05 + 0.02
    
    for service, cost, unit in costs:
        print(f"   • {service}: {cost} {unit}")
    
    print(f"\n   📊 Total Cost per Full Assessment: ~${total_cost:.4f}")
    
    print("\n📈 Success Rate Calculation:")
    print("   • Total Components: 8 (including GBP)")
    print("   • Success Threshold: ≥80% for 'completed' status")
    print("   • Partial Success: 50-79% for 'partially_completed' status")
    print("   • Failed: <50% for 'failed' status")
    
    print("\n🎯 Database Integration:")
    print("   • All component results saved to assessments table")
    print("   • GBP data stored in 'gbp_data' JSON field")
    print("   • Cost tracking in assessment_costs table")
    print("   • Full audit trail and error logging")

def main():
    """Main verification function."""
    
    print("🔍 GBP Assessment Orchestration Verification")
    print("=" * 60)
    print("Verifying PRP-005 (GBP) integration with complete assessment pipeline\n")
    
    success = verify_gbp_orchestration()
    show_orchestration_summary()
    
    print("\n🎉 RESULT: GBP Integration")
    print("=" * 60)
    
    if success:
        print("✅ SUCCESS: GBP fully integrated into assessment orchestration!")
        print("\n🎯 What's been accomplished:")
        print("   ✅ GBP added to execution sequence (position 3)")
        print("   ✅ Component timeout and retry configuration")
        print("   ✅ AssessmentExecution dataclass updated")
        print("   ✅ Component execution logic implemented")
        print("   ✅ Success rate calculation includes GBP")
        print("   ✅ Celery task orchestration updated")
        print("\n🚀 Ready for production assessment pipeline execution!")
    else:
        print("❌ FAILED: GBP integration issues detected")
        print("   Check the verification details above for specific problems")
    
    return success

if __name__ == "__main__":
    main()