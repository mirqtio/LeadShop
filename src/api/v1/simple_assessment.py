"""
Simple Assessment API - Synchronous execution with direct DB row display
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select, text

from src.core.database import SyncSessionLocal
from src.models.lead import Lead, Assessment
from src.models.screenshot import Screenshot
from src.assessments.pagespeed import assess_pagespeed
from src.assessments.security_analysis import assess_security_headers
from src.assessments.semrush_integration import assess_semrush_domain
from src.assessments.gbp_integration import assess_google_business_profile
from src.assessments.screenshot_capture import capture_website_screenshots
from src.assessments.visual_analysis import assess_visual_analysis

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/simple-assessment", tags=["simple-assessment"])

class AssessmentRequest(BaseModel):
    url: str
    business_name: str

@router.get("/", response_class=HTMLResponse)
async def simple_assessment_ui():
    """Serve simple assessment UI"""
    import os
    import time
    
    # Try different file paths
    file_paths = [
        '/app/simple_assessment_ui.html',
        'simple_assessment_ui.html',
        './simple_assessment_ui.html'
    ]
    
    content = None
    used_path = None
    for path in file_paths:
        if os.path.exists(path):
            logger.info(f"Found HTML file at: {path}")
            with open(path, 'r') as f:
                content = f.read()
            used_path = path
            break
    
    if content is None:
        logger.error(f"Could not find simple_assessment_ui.html in any of: {file_paths}")
        raise HTTPException(status_code=500, detail="UI file not found")
    
    # Check file modification time
    file_mtime = os.path.getmtime(used_path)
    logger.info(f"HTML file last modified: {datetime.fromtimestamp(file_mtime)}")
    
    # Add timestamp to prevent caching
    content = f"<!-- Served at {time.time()} from {used_path} -->\n" + content
    
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-File-Path": used_path,
            "X-File-Modified": str(file_mtime)
        }
    )

@router.get("/v2", response_class=HTMLResponse)
async def simple_assessment_ui_v2():
    """Serve simple assessment UI v2 - bypass cache"""
    import time
    try:
        with open('/app/simple_assessment_ui.html', 'r') as f:
            content = f.read()
    except:
        # Fallback for local development
        with open('simple_assessment_ui.html', 'r') as f:
            content = f.read()
    
    # Add timestamp comment to ensure it's fresh
    content = f"<!-- Generated at {time.time()} -->\n" + content
    
    return HTMLResponse(
        content=content,
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Timestamp": str(time.time())
        }
    )

@router.post("/assess")
async def run_simple_assessment(request: AssessmentRequest):
    """Run assessment synchronously and return complete DB row"""
    try:
        url = request.url
        business_name = request.business_name
        
        # Parse domain for SEMrush
        parsed_url = urlparse(url)
        domain = parsed_url.netloc or parsed_url.path
        
        # Create lead and assessment in database
        with SyncSessionLocal() as db:
            # Check if lead exists
            existing_lead = db.query(Lead).filter(Lead.url == url).order_by(Lead.created_at.desc()).first()
            
            if existing_lead:
                lead_id = existing_lead.id
            else:
                # Create new lead
                test_email = f"simple{int(datetime.now().timestamp())}@{domain.replace('www.', '').replace('/', '').replace(':', '')}"
                
                lead = Lead(
                    company=business_name,
                    email=test_email,
                    url=url,
                    source="simple_assessment"
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
        
        logger.info(f"Created assessment {assessment_id} for lead {lead_id}")
        
        # Run all components synchronously
        results = {}
        
        # 1. PageSpeed Analysis
        try:
            logger.info(f"Running PageSpeed for {url}")
            results["pagespeed"] = await assess_pagespeed(url)
        except Exception as e:
            logger.error(f"PageSpeed failed: {e}")
            results["pagespeed"] = {"error": str(e)}
        
        # 2. Security Headers
        try:
            logger.info(f"Running Security Headers for {url}")
            results["security"] = await assess_security_headers(url)
        except Exception as e:
            logger.error(f"Security failed: {e}")
            results["security"] = {"error": str(e)}
        
        # 3. SEMrush Analysis
        try:
            logger.info(f"Running SEMrush for {domain}")
            results["semrush"] = await assess_semrush_domain(domain, lead_id, None)
        except Exception as e:
            logger.error(f"SEMrush failed: {e}")
            results["semrush"] = {"error": str(e)}
        
        # 4. Google Business Profile
        try:
            logger.info(f"Running GBP for {business_name}")
            results["gbp"] = await assess_google_business_profile(business_name, None, None, None, lead_id, None)
        except Exception as e:
            logger.error(f"GBP failed: {e}")
            results["gbp"] = {"error": str(e)}
        
        # 5. Screenshot Capture
        try:
            logger.info(f"Running Screenshots for {url}")
            # Add timeout to prevent hanging
            results["screenshots"] = await asyncio.wait_for(
                capture_website_screenshots(url, lead_id, assessment_id),
                timeout=30  # 30 second timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Screenshots timed out after 30 seconds")
            results["screenshots"] = {"error": "Screenshot capture timed out"}
        except Exception as e:
            logger.error(f"Screenshots failed: {e}")
            results["screenshots"] = {"error": str(e)}
        
        # 6. Visual Analysis
        try:
            logger.info(f"Running Visual Analysis for {url}")
            # Process screenshots - upload to S3 instead of base64 URLs
            desktop_url = None
            mobile_url = None
            
            if results.get("screenshots"):
                screenshot_result_data = results["screenshots"]
                screenshots_list = []

                # Handle both object and dict for transition period
                if hasattr(screenshot_result_data, 'screenshots') and isinstance(screenshot_result_data.screenshots, list):
                    screenshots_list = screenshot_result_data.screenshots
                elif isinstance(screenshot_result_data, dict) and 'screenshots' in screenshot_result_data and isinstance(screenshot_result_data['screenshots'], list):
                    screenshots_list = screenshot_result_data['screenshots']

                # Import AWS S3 dependencies
                import boto3
                import uuid
                from datetime import datetime
                
                # Initialize S3 client
                s3_client = boto3.client('s3')
                bucket_name = os.getenv('S3_BUCKET_NAME', 'your-bucket-name')
                
                for screenshot in screenshots_list:
                    device_type = screenshot.get("device_type")
                    base64_data = screenshot.get("screenshot_url", "")
                    
                    if base64_data and "," in base64_data:
                        # Extract base64 data after comma
                        base64_string = base64_data.split(",")[1]
                        import base64
                        image_data = base64.b64decode(base64_string)
                        
                        # Generate S3 key with timestamp and assessment ID
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"screenshots/{assessment_id}/{device_type}_{timestamp}_{uuid.uuid4().hex[:8]}.png"
                        
                        # Upload to S3
                        try:
                            s3_client.put_object(
                                Bucket=bucket_name,
                                Key=filename,
                                Body=image_data,
                                ContentType='image/png',
                                ACL='public-read'
                            )
                            
                            # Generate S3 URL
                            s3_url = f"https://{bucket_name}.s3.amazonaws.com/{filename}"
                            
                            if device_type == "desktop":
                                desktop_url = s3_url
                            elif device_type == "mobile":
                                mobile_url = s3_url
                                
                            # Store screenshot record in database
                            screenshot_record = Screenshot(
                                assessment_id=assessment_id,
                                screenshot_type=device_type,
                                viewport_width=screenshot.get("viewport_width", 0),
                                viewport_height=screenshot.get("viewport_height", 0),
                                image_url=s3_url
                            )
                            db.add(screenshot_record)
                            db.commit()
                            
                        except Exception as e:
                            logger.error(f"Failed to upload screenshot to S3: {e}")
                            # Fallback to storing error message
                            screenshot_record = Screenshot(
                                assessment_id=assessment_id,
                                screenshot_type=device_type,
                                viewport_width=screenshot.get("viewport_width", 0),
                                viewport_height=screenshot.get("viewport_height", 0),
                                image_url=f"Error: {str(e)}"
                            )
                            db.add(screenshot_record)
                            db.commit()
            
            logger.info(f"Found desktop URL: {desktop_url is not None}, mobile URL: {mobile_url is not None}")
            
            if desktop_url and mobile_url:
                results["visual"] = await assess_visual_analysis(url, desktop_url, mobile_url, lead_id, None)
            else:
                results["visual"] = {"error": "No screenshots available for analysis", "desktop_url": desktop_url, "mobile_url": mobile_url}
        except Exception as e:
            logger.error(f"Visual Analysis failed: {e}")
            results["visual"] = {"error": str(e)}
        
        # Calculate overall score
        logger.info(f"Starting score calculation after all assessments")
        scores = []
        
        # PageSpeed score
        if results.get("pagespeed") and not isinstance(results["pagespeed"], dict):
            try:
                mobile_score = results["pagespeed"].mobile_analysis.core_web_vitals.performance_score
                desktop_score = results["pagespeed"].desktop_analysis.core_web_vitals.performance_score
                scores.append((mobile_score + desktop_score) / 2)
            except:
                pass
        
        # Security score
        if results.get("security"):
            try:
                if hasattr(results["security"], 'security_score'):
                    scores.append(results["security"].security_score)
                elif isinstance(results["security"], dict) and "security_score" in results["security"]:
                    scores.append(results["security"]["security_score"])
            except:
                pass
        
        # SEMrush score (normalized)
        if results.get("semrush") and hasattr(results["semrush"], 'domain_score'):
            scores.append(results["semrush"].domain_score)
        
        # GBP score (100 if found, 0 if not)
        if results.get("gbp") and hasattr(results["gbp"], 'found'):
            scores.append(100 if results["gbp"].found else 0)
        
        # Visual score (80 if successful)
        if results.get("visual") and not isinstance(results["visual"], dict):
            scores.append(80)
        
        overall_score = sum(scores) / len(scores) if scores else 0
        
        # Content generation
        content = {
            "summary": f"Assessment completed for {business_name} ({url})",
            "score": overall_score,
            "components_run": 8,
            "components_successful": len([r for r in results.values() if not isinstance(r, dict) or "error" not in r]),
            "recommendations": []
        }
        
        if overall_score < 50:
            content["recommendations"].append("Website needs significant improvements")
        elif overall_score < 70:
            content["recommendations"].append("Website has room for optimization")
        else:
            content["recommendations"].append("Website is performing well")
        
        # Convert results to serializable format
        def convert_to_dict(data):
            if data is None:
                return None
            if hasattr(data, 'dict'):
                return data.dict()
            elif hasattr(data, 'model_dump'):
                return data.model_dump()
            elif isinstance(data, dict):
                # Recursively handle dict values
                return {k: convert_to_dict(v) for k, v in data.items()}
            elif isinstance(data, list):
                # Handle lists
                return [convert_to_dict(item) for item in data]
            elif isinstance(data, datetime):
                # Handle datetime objects
                return data.isoformat()
            else:
                return str(data)
        
        # Save to database
        with SyncSessionLocal() as db:
            assessment_to_update = db.query(Assessment).filter(Assessment.id == assessment_id).first()
            
            if assessment_to_update:
                assessment_to_update.pagespeed_data = convert_to_dict(results.get("pagespeed"))
                assessment_to_update.security_headers = convert_to_dict(results.get("security"))
                assessment_to_update.semrush_data = convert_to_dict(results.get("semrush"))
                assessment_to_update.gbp_data = convert_to_dict(results.get("gbp"))
                assessment_to_update.visual_analysis = convert_to_dict(results.get("visual"))
                assessment_to_update.total_score = overall_score

                # Check if screenshots were successfully captured and saved
                if desktop_url or mobile_url:
                    assessment_to_update.screenshots_captured = True
                
                # Store screenshots and content in llm_insights
                llm_insights = {
                    "screenshots": convert_to_dict(results.get("screenshots")) or {},
                    "content_generation": content,
                    "assessment_summary": content["summary"],
                    "recommendations": content["recommendations"]
                }
                assessment_to_update.llm_insights = llm_insights
                
                db.commit()
                
                # Get the complete row as a dictionary
                db_row = {
                    "id": assessment_to_update.id,
                    "lead_id": assessment_to_update.lead_id,
                    "created_at": assessment_to_update.created_at.isoformat() if assessment_to_update.created_at else None,
                    "pagespeed_score": assessment_to_update.pagespeed_score,
                    "security_score": assessment_to_update.security_score,
                    "mobile_score": assessment_to_update.mobile_score,
                    "seo_score": assessment_to_update.seo_score,
                    "pagespeed_data": assessment_to_update.pagespeed_data,
                    "security_headers": assessment_to_update.security_headers,
                    "gbp_data": assessment_to_update.gbp_data,
                    "semrush_data": assessment_to_update.semrush_data,
                    "visual_analysis": assessment_to_update.visual_analysis,
                    "llm_insights": assessment_to_update.llm_insights,
                    "status": assessment_to_update.status,
                    "error_message": assessment_to_update.error_message,
                    "assessment_duration_ms": assessment_to_update.assessment_duration_ms,
                    "total_score": assessment_to_update.total_score
                }
                
                # Get screenshots from the database
                screenshots = db.query(Screenshot).filter(Screenshot.assessment_id == assessment_id).all()
                screenshot_data = []
                for screenshot in screenshots:
                    screenshot_data.append({
                        "id": screenshot.id,
                        "screenshot_type": screenshot.screenshot_type.value if screenshot.screenshot_type else None,
                        "viewport_width": screenshot.viewport_width,
                        "viewport_height": screenshot.viewport_height,
                        "image_url": screenshot.image_url,
                        "viewport_type": "Desktop" if screenshot.viewport_width > 1000 else "Mobile"
                    })
                
                logger.info(f"Assessment {assessment_id} completed successfully, decomposing metrics")
                
                # Import and call decompose_metrics to populate assessment_results table
                # Since we're already in an async context, we need to handle this differently
                from src.assessment.decompose_metrics import decompose_and_store_metrics
                from src.core.database import AsyncSessionLocal
                from src.models.assessment_results import AssessmentResults
                
                try:
                    # Use async session for decomposing
                    async with AsyncSessionLocal() as async_db:
                        assessment_results = await decompose_and_store_metrics(async_db, assessment_id)
                        
                    if assessment_results:
                        logger.info(f"Successfully decomposed metrics for assessment {assessment_id}")
                        # Get the decomposed metrics using sync session
                        assessment_results_sync = db.query(AssessmentResults).filter(
                            AssessmentResults.assessment_id == assessment_id
                        ).first()
                        
                        if assessment_results_sync:
                            db_row["decomposed_metrics"] = assessment_results_sync.get_all_metrics()
                        else:
                            db_row["decomposed_metrics"] = {}
                    else:
                        logger.warning(f"Failed to decompose metrics for assessment {assessment_id}")
                        db_row["decomposed_metrics"] = {}
                except Exception as e:
                    logger.error(f"Error decomposing metrics for assessment {assessment_id}: {e}")
                    db_row["decomposed_metrics"] = {}
                
                return {
                    "success": True,
                    "assessment_id": assessment_id,
                    "db_row": db_row,
                    "screenshots": screenshot_data
                }
        
    except Exception as e:
        logger.error(f"Assessment failed: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))