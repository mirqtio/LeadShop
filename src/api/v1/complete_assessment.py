"""
Complete Assessment API - All 8 Components (FIXED)
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.database import AsyncSessionLocal, SyncSessionLocal
from src.models.lead import Lead, Assessment
from src.assessments.pagespeed import assess_pagespeed
from src.assessments.security_analysis import assess_security_headers
from src.assessments.semrush_integration import assess_semrush_domain
from src.assessments.gbp_integration import assess_google_business_profile
from src.assessments.screenshot_capture import capture_website_screenshots
from src.assessments.visual_analysis import assess_visual_analysis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/complete-assessment", tags=["complete-assessment"])

# Store assessment status
assessment_status = {}

class AssessmentRequest(BaseModel):
    url: str
    business_name: str

async def run_complete_assessment(lead_id: int, assessment_id: int):
    """Run all 8 assessment components"""
    try:
        # Get lead and assessment data first using sync session
        url = None
        business_name = None
        
        with SyncSessionLocal() as db:
            lead = db.query(Lead).filter(Lead.id == lead_id).first()
            assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
            
            if not lead or not assessment:
                return
            
            url = lead.url
            business_name = lead.company
        
        # Parse domain for SEMrush (outside db context)
        parsed_url = urlparse(url)
        domain = parsed_url.netloc or parsed_url.path
        
        results = {}
        assessment_status[assessment_id] = {"status": "running", "progress": 0, "components": {}}
        
        # 1. PageSpeed Analysis
        try:
            logger.info(f"Running PageSpeed for {url}")
            assessment_status[assessment_id]["components"]["pagespeed"] = "running"
            results["pagespeed"] = await asyncio.wait_for(assess_pagespeed(url), timeout=45)
            assessment_status[assessment_id]["components"]["pagespeed"] = "completed"
            logger.info("PageSpeed completed")
        except Exception as e:
            logger.error(f"PageSpeed failed: {e}")
            results["pagespeed"] = None
            assessment_status[assessment_id]["components"]["pagespeed"] = "failed"
        
        assessment_status[assessment_id]["progress"] = 15
        
        # 2. Security Headers
        try:
            logger.info(f"Running Security Headers for {url}")
            assessment_status[assessment_id]["components"]["security"] = "running"
            results["security"] = await asyncio.wait_for(assess_security_headers(url), timeout=10)
            assessment_status[assessment_id]["components"]["security"] = "completed"
            logger.info("Security completed")
        except Exception as e:
            logger.error(f"Security failed: {e}")
            results["security"] = None
            assessment_status[assessment_id]["components"]["security"] = "failed"
        
        assessment_status[assessment_id]["progress"] = 30
        
        # 3. SEMrush Analysis (will fail due to API limits, but that's ok)
        try:
            logger.info(f"Running SEMrush for {domain}")
            assessment_status[assessment_id]["components"]["semrush"] = "running"
            results["semrush"] = await asyncio.wait_for(
                assess_semrush_domain(domain, lead_id, None),  # Pass None to prevent SEMrush from saving to DB
                timeout=20
            )
            assessment_status[assessment_id]["components"]["semrush"] = "completed"
            logger.info("SEMrush completed")
        except Exception as e:
            logger.error(f"SEMrush failed: {e}")
            results["semrush"] = None
            assessment_status[assessment_id]["components"]["semrush"] = "failed"
        
        assessment_status[assessment_id]["progress"] = 45
        
        # 4. Google Business Profile
        try:
            logger.info(f"Running GBP for {business_name}")
            assessment_status[assessment_id]["components"]["gbp"] = "running"
            results["gbp"] = await asyncio.wait_for(
                assess_google_business_profile(business_name, None, None, None, lead_id, None),  # Pass None to prevent GBP from saving to DB
                timeout=15
            )
            assessment_status[assessment_id]["components"]["gbp"] = "completed"
            logger.info("GBP completed")
        except Exception as e:
            logger.error(f"GBP failed: {e}")
            results["gbp"] = None
            assessment_status[assessment_id]["components"]["gbp"] = "failed"
        
        assessment_status[assessment_id]["progress"] = 60
        
        # 5. Screenshot Capture
        try:
            logger.info(f"Running Screenshots for {url}")
            assessment_status[assessment_id]["components"]["screenshots"] = "running"
            results["screenshots"] = await asyncio.wait_for(
                capture_website_screenshots(url, lead_id, None),  # Pass None to prevent Screenshots from saving to DB
                timeout=60
            )
            assessment_status[assessment_id]["components"]["screenshots"] = "completed"
            logger.info("Screenshots completed")
        except Exception as e:
            logger.error(f"Screenshots failed: {e}")
            results["screenshots"] = None
            assessment_status[assessment_id]["components"]["screenshots"] = "failed"
        
        assessment_status[assessment_id]["progress"] = 75
        
        # 6. Visual Analysis
        try:
            logger.info(f"Running Visual Analysis for {url}")
            assessment_status[assessment_id]["components"]["visual"] = "running"
            
            # Visual analysis needs screenshot URLs - get from screenshots result
            desktop_url = None
            mobile_url = None
            
            if results.get("screenshots") and hasattr(results["screenshots"], 'screenshots'):
                screenshots = results["screenshots"].screenshots
                for screenshot in screenshots:
                    if isinstance(screenshot, dict):
                        if screenshot.get("device_type") == "desktop":
                            desktop_url = screenshot.get("screenshot_url")
                        elif screenshot.get("device_type") == "mobile":
                            mobile_url = screenshot.get("screenshot_url")
                    else:
                        if screenshot.device_type == "desktop":
                            desktop_url = screenshot.screenshot_url
                        elif screenshot.device_type == "mobile":
                            mobile_url = screenshot.screenshot_url
            
            if desktop_url and mobile_url:
                results["visual"] = await asyncio.wait_for(
                    assess_visual_analysis(url, desktop_url, mobile_url, lead_id, None),  # Pass None to prevent Visual from saving to DB
                    timeout=30
                )
                assessment_status[assessment_id]["components"]["visual"] = "completed"
                logger.info("Visual Analysis completed")
            else:
                logger.error("Visual Analysis skipped - missing screenshot URLs")
                results["visual"] = None
                assessment_status[assessment_id]["components"]["visual"] = "failed"
                
        except Exception as e:
            logger.error(f"Visual Analysis failed: {e}")
            results["visual"] = None
            assessment_status[assessment_id]["components"]["visual"] = "failed"
        
        assessment_status[assessment_id]["progress"] = 90
        
        # 7. Score Calculation
        scores = []
        
        # PageSpeed score
        if results.get("pagespeed"):
            try:
                mobile_score = results["pagespeed"].get("mobile_analysis", {}).get("core_web_vitals", {}).get("performance_score", 0)
                desktop_score = results["pagespeed"].get("desktop_analysis", {}).get("core_web_vitals", {}).get("performance_score", 0)
                scores.append((mobile_score + desktop_score) / 2)
            except:
                pass
        
        # Security score
        if results.get("security"):
            try:
                if hasattr(results["security"], 'security_score'):
                    scores.append(results["security"].security_score)
                elif isinstance(results["security"], dict):
                    scores.append(results["security"].get("security_score", 0))
            except:
                pass
        
        # SEMrush score (normalized to 100)
        if results.get("semrush"):
            try:
                if hasattr(results["semrush"], 'domain_score'):
                    scores.append(results["semrush"].domain_score)
                elif isinstance(results["semrush"], dict):
                    scores.append(results["semrush"].get("domain_score", 0))
            except:
                pass
        
        # GBP score (100 if found, 0 if not)
        if results.get("gbp"):
            try:
                found = False
                if hasattr(results["gbp"], 'found'):
                    found = results["gbp"].found
                elif isinstance(results["gbp"], dict):
                    found = results["gbp"].get("found", False)
                scores.append(100 if found else 0)
            except:
                pass
        
        # Visual score (80 if successful)
        if results.get("visual"):
            scores.append(80)
        
        overall_score = sum(scores) / len(scores) if scores else 0
        
        # 8. Content Generation (simple for demo)
        content = {
            "summary": f"Assessment completed for {business_name} ({url})",
            "recommendations": []
        }
        
        if overall_score < 50:
            content["recommendations"].append("Website needs significant improvements")
        elif overall_score < 70:
            content["recommendations"].append("Website has room for optimization")
        else:
            content["recommendations"].append("Website is performing well")
        
        # Helper function to convert Pydantic models to dicts
        def convert_to_dict(data):
            if data is None:
                return None
            
            # Handle Pydantic models
            if hasattr(data, 'dict'):
                result = data.dict()
            elif hasattr(data, 'model_dump'):
                result = data.model_dump()
            elif isinstance(data, dict):
                result = data
            elif isinstance(data, list):
                return [convert_to_dict(item) for item in data]
            elif isinstance(data, (str, int, float, bool)):
                return data
            elif isinstance(data, datetime):
                return data.isoformat()
            elif isinstance(data, type):
                # Handle type objects (this is the issue)
                return str(data)
            else:
                # For other objects, try to convert to dict or string
                try:
                    if hasattr(data, '__dict__'):
                        result = data.__dict__
                    else:
                        result = str(data)
                except:
                    result = str(data)
            
            # Recursively convert nested structures
            if isinstance(result, dict):
                cleaned_result = {}
                for key, value in result.items():
                    if isinstance(value, datetime):
                        cleaned_result[key] = value.isoformat()
                    elif isinstance(value, type):
                        cleaned_result[key] = str(value)
                    elif isinstance(value, dict):
                        cleaned_result[key] = convert_to_dict(value)
                    elif isinstance(value, list):
                        cleaned_result[key] = [convert_to_dict(item) for item in value]
                    else:
                        cleaned_result[key] = value
                return cleaned_result
            
            return result
        
        # Save to database - use sync session to avoid greenlet issues
        try:
            with SyncSessionLocal() as db2:
                # Get the assessment again in this session using a query
                assessment_to_update = db2.query(Assessment).filter(Assessment.id == assessment_id).first()
                
                if assessment_to_update:
                    # Convert each result separately to catch issues
                    try:
                        assessment_to_update.pagespeed_data = convert_to_dict(results.get("pagespeed"))
                    except Exception as e:
                        logger.error(f"Error converting pagespeed data: {e}")
                        assessment_to_update.pagespeed_data = None
                    
                    try:
                        assessment_to_update.security_headers = convert_to_dict(results.get("security"))
                    except Exception as e:
                        logger.error(f"Error converting security data: {e}")
                        assessment_to_update.security_headers = None
                    
                    try:
                        assessment_to_update.semrush_data = convert_to_dict(results.get("semrush"))
                    except Exception as e:
                        logger.error(f"Error converting semrush data: {e}")
                        assessment_to_update.semrush_data = None
                    
                    try:
                        assessment_to_update.gbp_data = convert_to_dict(results.get("gbp"))
                    except Exception as e:
                        logger.error(f"Error converting gbp data: {e}")
                        assessment_to_update.gbp_data = None
                    
                    try:
                        assessment_to_update.visual_analysis = convert_to_dict(results.get("visual"))
                    except Exception as e:
                        logger.error(f"Error converting visual data: {e}")
                        assessment_to_update.visual_analysis = None
                    
                    assessment_to_update.total_score = overall_score
                    
                    # Store the screenshots and content in a combined llm_insights field
                    llm_insights = {
                        "screenshots": convert_to_dict(results.get("screenshots")) or [],
                        "content_generation": content,
                        "assessment_summary": content["summary"],
                        "recommendations": content["recommendations"]
                    }
                    assessment_to_update.llm_insights = llm_insights
                    
                    db2.commit()
                    logger.info(f"Successfully saved assessment {assessment_id} to database")
                else:
                    logger.error(f"Assessment {assessment_id} not found in database")
        except Exception as db_error:
            logger.error(f"Database save failed: {db_error}")
            logger.error(f"Error type: {type(db_error).__name__}")
            # Continue anyway - we have the results in memory
        
        assessment_status[assessment_id]["status"] = "completed"
        assessment_status[assessment_id]["progress"] = 100
        assessment_status[assessment_id]["score"] = overall_score
        # Convert all results to dicts for JSON serialization
        assessment_status[assessment_id]["results"] = {
            k: convert_to_dict(v) for k, v in results.items()
        }
        
        logger.info(f"Assessment {assessment_id} completed with score {overall_score}")
        
    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        assessment_status[assessment_id]["status"] = "failed"
        assessment_status[assessment_id]["error"] = str(e)

@router.get("/", response_class=HTMLResponse)
async def complete_assessment_ui():
    """Serve complete assessment UI"""
    with open('/app/static/complete_assessment_ui.html', 'r') as f:
        return f.read()

@router.post("/assess")
async def start_assessment(request: AssessmentRequest):
    """Start complete assessment - runs synchronously to avoid async context issues"""
    try:
        url = request.url
        business_name = request.business_name
        
        # Create lead and assessment in database
        with SyncSessionLocal() as db:
            # Check if lead exists
            existing_lead = db.query(Lead).filter(Lead.url == url).order_by(Lead.created_at.desc()).first()
            
            if existing_lead:
                lead_id = existing_lead.id
            else:
                # Create new lead
                parsed_url = urlparse(url)
                domain = parsed_url.netloc or parsed_url.path
                test_email = f"complete{int(datetime.now().timestamp())}@{domain.replace('www.', '').replace('/', '').replace(':', '')}"
                
                lead = Lead(
                    company=business_name,
                    email=test_email,
                    url=url,
                    source="complete_assessment"
                )
                db.add(lead)
                db.commit()
                db.refresh(lead)
                lead_id = lead.id
            
            # Create assessment
            assessment = Assessment(
                lead_id=lead_id,
                created_at=datetime.now(timezone.utc)
            )
            db.add(assessment)
            db.commit()
            db.refresh(assessment)
            assessment_id = assessment.id
        
        # Initialize status
        assessment_status[assessment_id] = {"status": "running", "progress": 0, "components": {}}
        
        # Run assessment synchronously in the same async context
        # This will block until complete, but maintains proper async context
        try:
            await run_complete_assessment(lead_id, assessment_id)
            
            # Get final status
            final_status = assessment_status.get(assessment_id, {})
            
            return {
                "assessment_id": assessment_id,
                "status": final_status.get("status", "completed"),
                "score": final_status.get("score"),
                "message": f"Complete assessment finished for {url}"
            }
        except Exception as e:
            logger.error(f"Assessment execution failed: {e}")
            assessment_status[assessment_id]["status"] = "failed"
            assessment_status[assessment_id]["error"] = str(e)
            raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        logger.error(f"Failed to start assessment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{assessment_id}")
async def get_status(assessment_id: int):
    """Get assessment status"""
    # First check in-memory status
    if assessment_id in assessment_status:
        status_data = assessment_status[assessment_id].copy()
        
        # If completed or failed, also add database data
        if status_data.get("status") in ["completed", "failed"]:
            with SyncSessionLocal() as db:
                # Use a simple query with sync session
                assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
                
                if assessment:
                    # Add database fields to the response
                    status_data["database_saved"] = True
                    status_data["db_score"] = assessment.total_score
                    # Access all fields while in async context - force evaluation
                    try:
                        db_results = {
                            "pagespeed": assessment.pagespeed_data,
                            "security": assessment.security_headers,
                            "semrush": assessment.semrush_data,
                            "gbp": assessment.gbp_data,
                            "visual": assessment.visual_analysis,
                            "llm_insights": assessment.llm_insights
                        }
                        # Extract screenshots and content from llm_insights if present
                        if assessment.llm_insights:
                            db_results["screenshots"] = assessment.llm_insights.get("screenshots", [])
                            db_results["content"] = assessment.llm_insights.get("content_generation", {})
                        else:
                            db_results["screenshots"] = []
                            db_results["content"] = {}
                        
                        # Convert None to None explicitly to avoid lazy loading issues
                        status_data["db_results"] = {k: (v if v is not None else None) for k, v in db_results.items()}
                    except Exception as e:
                        logger.error(f"Error accessing assessment data: {e}")
                        status_data["db_results"] = {}
        
        return status_data
    else:
        # Check database for completed assessments
        with SyncSessionLocal() as db:
            assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
            if assessment and assessment.total_score is not None:
                # Force load all fields while in async context
                try:
                    # Access all fields to force loading
                    pagespeed_data = assessment.pagespeed_data
                    security_data = assessment.security_headers
                    semrush_data = assessment.semrush_data
                    gbp_data = assessment.gbp_data
                    visual_data = assessment.visual_analysis
                    llm_insights_data = assessment.llm_insights
                    score = assessment.total_score
                    
                    # Extract screenshots and content from llm_insights
                    screenshots_data = llm_insights_data.get("screenshots", []) if llm_insights_data else []
                    content_data = llm_insights_data.get("content_generation", {}) if llm_insights_data else {}
                    
                    return {
                        "status": "completed",
                        "progress": 100,
                        "score": score,
                        "database_saved": True,
                        "db_score": score,
                        "results": {
                            "pagespeed": pagespeed_data if pagespeed_data else None,
                            "security": security_data if security_data else None,
                            "semrush": semrush_data if semrush_data else None,
                            "gbp": gbp_data if gbp_data else None,
                            "screenshots": screenshots_data if screenshots_data else None,
                            "visual": visual_data if visual_data else None
                        },
                        "db_results": {
                            "pagespeed": pagespeed_data if pagespeed_data else None,
                            "security": security_data if security_data else None,
                            "semrush": semrush_data if semrush_data else None,
                            "gbp": gbp_data if gbp_data else None,
                            "screenshots": screenshots_data if screenshots_data else None,
                            "visual": visual_data if visual_data else None,
                            "content": content_data if content_data else None
                        },
                        "components": {
                            "pagespeed": "completed" if pagespeed_data else "failed",
                            "security": "completed" if security_data else "failed",
                            "semrush": "completed" if semrush_data else "failed",
                            "gbp": "completed" if gbp_data else "failed",
                            "screenshots": "completed" if screenshots_data else "failed",
                            "visual": "completed" if visual_data else "failed",
                            "score": "completed" if score is not None else "failed",
                            "content": "completed" if content_data else "failed"
                        }
                    }
                except Exception as e:
                    logger.error(f"Error reading assessment from database: {e}")
                    return {"status": "error", "error": str(e)}
        
        return {"status": "not_found"}