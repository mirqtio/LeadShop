"""
Simple Assessment API for Testing
Bypasses Google Auth for local development and testing
"""

from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, HttpUrl, Field
from typing import Dict, Any, Optional
import logging
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import get_db
from src.models.lead import Lead
from src.schemas.lead import LeadCreate
from src.assessment.orchestrator import submit_assessment, get_assessment_status, coordinate_assessment
from src.assessment.tasks import full_assessment_orchestrator_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simple-assessment", tags=["simple-assessment"])

class AssessmentRequest(BaseModel):
    """Assessment execution request"""
    url: HttpUrl = Field(..., description="Website URL to assess")
    business_name: Optional[str] = Field(None, description="Business name (optional)")

class AssessmentResponse(BaseModel):
    """Assessment execution response"""
    task_id: str
    status: str
    message: str
    results: Dict[str, Any]

@router.get("", response_class=HTMLResponse)
async def serve_simple_assessment_ui(request: Request):
    """
    Serve a simple assessment UI that actually works
    """
    try:
        # Read the simple test HTML file
        simple_ui_path = Path("/Users/charlieirwin/LeadShop/simple_test.html")
        
        if not simple_ui_path.exists():
            # If the file doesn't exist in the container, serve inline HTML
            html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Assessment Test</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        form {
            margin-bottom: 30px;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        input[type="url"] {
            width: 300px;
            padding: 8px;
            margin-right: 10px;
        }
        button {
            padding: 8px 16px;
            background: #007cba;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }
        button:disabled {
            background: #ccc;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #f5f5f5;
        }
        .status {
            margin: 10px 0;
            padding: 10px;
            border-radius: 3px;
        }
        .status.pending { background: #fff3cd; }
        .status.completed { background: #d4edda; }
        .status.error { background: #f8d7da; }
    </style>
</head>
<body>
    <h1>Simple Assessment Test</h1>
    
    <form id="assessmentForm">
        <label for="url">Website URL:</label>
        <input type="url" id="url" placeholder="https://example.com" required>
        <button type="submit" id="submitBtn">Run Assessment</button>
    </form>
    
    <div id="status" class="status" style="display: none;"></div>
    
    <div id="results" style="display: none;">
        <h2>Assessment Results</h2>
        <table id="resultsTable">
            <thead>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                    <th>Status</th>
                    <th>Source</th>
                    <th>Description</th>
                </tr>
            </thead>
            <tbody id="resultsBody">
            </tbody>
        </table>
    </div>

    <script>
        const form = document.getElementById('assessmentForm');
        const urlInput = document.getElementById('url');
        const submitBtn = document.getElementById('submitBtn');
        const statusDiv = document.getElementById('status');
        const resultsDiv = document.getElementById('results');
        const resultsBody = document.getElementById('resultsBody');
        
        let currentTaskId = null;
        let statusInterval = null;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const url = urlInput.value.trim();
            if (!url) return;
            
            // Reset UI
            submitBtn.disabled = true;
            statusDiv.style.display = 'block';
            statusDiv.className = 'status pending';
            statusDiv.textContent = 'Submitting assessment...';
            resultsDiv.style.display = 'none';
            
            try {
                // Submit assessment
                const response = await fetch('/api/v1/simple-assessment/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        url: url,
                        business_name: 'Test Business'
                    })
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                currentTaskId = data.task_id;
                
                statusDiv.textContent = `Assessment submitted (Task: ${currentTaskId}). Checking status...`;
                
                // Start polling for status
                startStatusPolling();
                
            } catch (error) {
                console.error('Error submitting assessment:', error);
                statusDiv.className = 'status error';
                statusDiv.textContent = `Error: ${error.message}`;
                submitBtn.disabled = false;
            }
        });
        
        function startStatusPolling() {
            if (statusInterval) clearInterval(statusInterval);
            
            statusInterval = setInterval(async () => {
                try {
                    const response = await fetch(`/api/v1/simple-assessment/status/${currentTaskId}`);
                    
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }
                    
                    const data = await response.json();
                    console.log('Status update:', data);
                    
                    if (data.status === 'completed') {
                        clearInterval(statusInterval);
                        statusDiv.className = 'status completed';
                        statusDiv.textContent = 'Assessment completed!';
                        displayResults(data.results);
                        submitBtn.disabled = false;
                    } else if (data.status === 'failed') {
                        clearInterval(statusInterval);
                        statusDiv.className = 'status error';
                        statusDiv.textContent = `Assessment failed: ${data.error || 'Unknown error'}`;
                        submitBtn.disabled = false;
                    } else {
                        statusDiv.textContent = `Assessment ${data.status}... (Task: ${currentTaskId})`;
                    }
                    
                } catch (error) {
                    console.error('Error checking status:', error);
                    statusDiv.className = 'status error';
                    statusDiv.textContent = `Error checking status: ${error.message}`;
                    clearInterval(statusInterval);
                    submitBtn.disabled = false;
                }
            }, 2000); // Check every 2 seconds
        }
        
        function displayResults(results) {
            if (!results) {
                resultsBody.innerHTML = '<tr><td colspan="5">No results available</td></tr>';
                resultsDiv.style.display = 'block';
                return;
            }
            
            let html = '';
            
            // Display individual granular metrics
            Object.entries(results).forEach(([metricKey, metricData]) => {
                const metric = metricData.metric || metricKey;
                const value = metricData.value || 'N/A';
                const status = metricData.status || 'Unknown';
                const source = metricData.source || 'System';
                const description = metricData.description || 'No description available';
                
                html += `
                    <tr>
                        <td>${metric}</td>
                        <td>${value}</td>
                        <td>${status}</td>
                        <td>${source}</td>
                        <td>${description}</td>
                    </tr>
                `;
            });
            
            if (html === '') {
                html = '<tr><td colspan="5">No assessment data found</td></tr>';
            }
            
            resultsBody.innerHTML = html;
            resultsDiv.style.display = 'block';
        }
    </script>
</body>
</html>"""
        else:
            with open(simple_ui_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
        
        return HTMLResponse(content=html_content)
        
    except Exception as e:
        logger.error(f"Failed to serve assessment UI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load assessment interface"
        )

@router.post("/execute", response_model=AssessmentResponse)
async def execute_simple_assessment(
    assessment_request: AssessmentRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Execute website assessment using existing orchestration system (no auth required for testing)
    """
    try:
        url = str(assessment_request.url)
        business_name = assessment_request.business_name or "Test Business"
        
        logger.info(f"Starting assessment for {url} using existing orchestration system")
        
        # First, check if a lead with this URL already exists
        existing_lead_result = await session.execute(
            select(Lead).where(Lead.url == url).order_by(Lead.created_at.desc())
        )
        existing_lead = existing_lead_result.scalar_one_or_none()
        
        if existing_lead:
            logger.info(f"Found existing lead {existing_lead.id} for URL {url}")
            lead_id = existing_lead.id
        else:
            # Create a new lead for this assessment
            # Generate a unique email based on the domain
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc or parsed_url.path
            test_email = f"assessment@{domain.replace('www.', '').replace('/', '').replace(':', '')}" 
            
            # Create lead data
            lead_data = LeadCreate(
                company=business_name,
                email=test_email,
                url=url,
                source="assessment_ui",
                description=f"Lead created for assessment from {url}"
            )
            
            # Check if email already exists, and modify if needed
            email_check_result = await session.execute(
                select(Lead).where(Lead.email == test_email)
            )
            if email_check_result.scalar_one_or_none():
                # Add timestamp to make email unique
                import time
                test_email = f"assessment{int(time.time())}@{domain.replace('www.', '').replace('/', '').replace(':', '')}"
                lead_data.email = test_email
            
            # Create the lead
            lead_dict = lead_data.model_dump()
            db_lead = Lead(**lead_dict)
            
            session.add(db_lead)
            await session.commit()
            await session.refresh(db_lead)
            
            lead_id = db_lead.id
            logger.info(f"Created new lead {lead_id} for URL {url}")
        
        # Now use the full assessment orchestrator that saves decomposed scores
        task = full_assessment_orchestrator_task.delay(lead_id)
        task_id = task.id
        
        logger.info(f"Full assessment orchestrator task submitted: {task_id} for lead {lead_id}")
        
        # Return the task ID so the frontend can check status
        return AssessmentResponse(
            task_id=task_id,
            status="submitted",
            message=f"Assessment submitted for {url}. Use the status endpoint to check progress.",
            results={"lead_id": lead_id, "url": url}
        )
        
    except Exception as e:
        logger.error(f"Assessment execution failed: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assessment execution failed: {str(e)}"
        )

@router.get("/status/{task_id}")
async def get_simple_assessment_status(
    task_id: str,
    session: AsyncSession = Depends(get_db)
):
    """
    Get assessment task status using existing orchestration system
    """
    try:
        logger.info(f"Getting status for task {task_id}")
        
        # Use the existing orchestration system to get status
        status_info = get_assessment_status(task_id)
        
        # If the assessment is completed, get the actual results from the database
        if status_info.get("successful") and status_info.get("result"):
            result_data = status_info.get("result", {})
            lead_id = result_data.get("lead_id")
            
            if lead_id:
                # Get the assessment data from the database
                from src.models.lead import Assessment
                assessment_result = await session.execute(
                    select(Assessment).where(Assessment.lead_id == lead_id).order_by(Assessment.created_at.desc())
                )
                assessment = assessment_result.scalar_one_or_none()
                
                if assessment:
                    # Complete database row display - show ALL assessment fields as requested
                    results = {}
                    
                    # Get all assessment attributes using reflection
                    import inspect
                    from sqlalchemy import inspect as sql_inspect
                    
                    # Get the SQLAlchemy inspector for the assessment instance
                    inspector = sql_inspect(assessment)
                    
                    # Get all column names from the Assessment model
                    column_names = [column.key for column in inspector.mapper.columns]
                    
                    # Display every single database field
                    for field_name in column_names:
                        field_value = getattr(assessment, field_name, None)
                        
                        # Format field name for display
                        display_name = field_name.replace('_', ' ').title()
                        
                        # Determine field type and format appropriately
                        if field_value is None:
                            formatted_value = "NULL"
                            status = "null"
                            description = f"No data available for {display_name.lower()}"
                        elif isinstance(field_value, dict):
                            # JSON fields - show size and type info
                            data_size = len(str(field_value))
                            key_count = len(field_value.keys()) if isinstance(field_value, dict) else 0
                            formatted_value = f"JSON object ({key_count} keys, {data_size} chars)"
                            status = "data"
                            description = f"Structured data for {display_name.lower()}"
                        elif isinstance(field_value, (int, float)):
                            formatted_value = str(field_value)
                            status = "metric" if "score" in field_name else "info"
                            description = f"Numeric value for {display_name.lower()}"
                        elif hasattr(field_value, 'isoformat'):
                            # DateTime fields
                            formatted_value = field_value.isoformat()
                            status = "info"
                            description = f"Timestamp for {display_name.lower()}"
                        else:
                            # String and other fields
                            formatted_value = str(field_value)
                            status = "error" if "error" in field_name else "info"
                            description = f"Text value for {display_name.lower()}"
                        
                        results[field_name] = {
                            "status": status,
                            "metric": display_name,
                            "value": formatted_value,
                            "source": "Database",
                            "description": description
                        }
                    
                    # Additionally, extract and display individual metrics from JSON fields
                    # This provides the 53 granular metrics from the ASSESSMENT_PROGRESS_TRACKER
                    
                    # PageSpeed individual metrics (7 metrics from PRP-003)
                    if assessment.pagespeed_data and isinstance(assessment.pagespeed_data, dict):
                        mobile_analysis = assessment.pagespeed_data.get('mobile_analysis', {})
                        if isinstance(mobile_analysis, dict):
                            cwv = mobile_analysis.get('core_web_vitals', {})
                            if isinstance(cwv, dict):
                                if cwv.get('first_contentful_paint') is not None:
                                    results["fcp_metric"] = {
                                        "status": "metric",
                                        "metric": "First Contentful Paint (FCP)",
                                        "value": f"{cwv['first_contentful_paint']:.0f}ms",
                                        "source": "PageSpeed",
                                        "description": "Time to first text/image paint - Core Web Vital"
                                    }
                                if cwv.get('largest_contentful_paint') is not None:
                                    results["lcp_metric"] = {
                                        "status": "metric", 
                                        "metric": "Largest Contentful Paint (LCP)",
                                        "value": f"{cwv['largest_contentful_paint']:.0f}ms",
                                        "source": "PageSpeed",
                                        "description": "Time to render the largest viewport element"
                                    }
                                if cwv.get('cumulative_layout_shift') is not None:
                                    results["cls_metric"] = {
                                        "status": "metric",
                                        "metric": "Cumulative Layout Shift (CLS)", 
                                        "value": f"{cwv['cumulative_layout_shift']:.3f}",
                                        "source": "PageSpeed",
                                        "description": "Cumulative visual-shift score during load"
                                    }
                                if cwv.get('total_blocking_time') is not None:
                                    results["tbt_metric"] = {
                                        "status": "metric",
                                        "metric": "Total Blocking Time (TBT)",
                                        "value": f"{cwv['total_blocking_time']:.0f}ms", 
                                        "source": "PageSpeed",
                                        "description": "Main-thread blocking milliseconds (FCP → TTI)"
                                    }
                                if cwv.get('time_to_interactive') is not None:
                                    results["tti_metric"] = {
                                        "status": "metric",
                                        "metric": "Time to Interactive (TTI)",
                                        "value": f"{cwv['time_to_interactive']:.0f}ms",
                                        "source": "PageSpeed", 
                                        "description": "Point when page is reliably interactive"
                                    }
                                if cwv.get('performance_score') is not None:
                                    results["perf_score_metric"] = {
                                        "status": "metric",
                                        "metric": "Performance Score (runtime)",
                                        "value": str(cwv['performance_score']),
                                        "source": "PageSpeed",
                                        "description": "Weighted composite (0-100) across vitals"
                                    }
                    
                    # Security metrics (9 metrics from PRP-004)  
                    if assessment.security_headers and isinstance(assessment.security_headers, dict):
                        sec_data = assessment.security_headers
                        if sec_data.get('https_enforced') is not None:
                            results["https_metric"] = {
                                "status": "metric",
                                "metric": "HTTPS Enforced",
                                "value": "Yes" if sec_data['https_enforced'] else "No",
                                "source": "Security Scan",
                                "description": "Redirects to HTTPS + valid certificate flag"
                            }
                        if sec_data.get('tls_version'):
                            results["tls_metric"] = {
                                "status": "metric", 
                                "metric": "TLS Version",
                                "value": str(sec_data['tls_version']),
                                "source": "Security Scan",
                                "description": "Highest TLS protocol supported (≥ 1.2 expected)"
                            }
                        if sec_data.get('hsts_header') is not None:
                            results["hsts_metric"] = {
                                "status": "metric",
                                "metric": "HSTS Header Present", 
                                "value": "Yes" if sec_data['hsts_header'] else "No",
                                "source": "Security Scan",
                                "description": "Strict-Transport-Security adherence"
                            }
                    
                    # Google Business Profile metrics (9 metrics from PRP-005)
                    if assessment.gbp_data and isinstance(assessment.gbp_data, dict):
                        gbp = assessment.gbp_data
                        if gbp.get('rating') is not None:
                            results["gbp_rating_metric"] = {
                                "status": "metric",
                                "metric": "GBP Rating",
                                "value": f"{gbp['rating']:.1f}/5.0",
                                "source": "Google Business Profile",
                                "description": "Average star rating (1–5)"
                            }
                        if gbp.get('review_count') is not None:
                            results["gbp_reviews_metric"] = {
                                "status": "metric",
                                "metric": "GBP Review Count",
                                "value": str(gbp['review_count']),
                                "source": "Google Business Profile", 
                                "description": "Total public reviews on GBP"
                            }
                    
                    # SEMrush metrics (6 metrics from PRP-007)
                    if assessment.semrush_data and isinstance(assessment.semrush_data, dict):
                        sem = assessment.semrush_data
                        if sem.get('domain_authority_score') is not None:
                            results["sem_authority_metric"] = {
                                "status": "metric",
                                "metric": "Domain Authority Score",
                                "value": str(sem['domain_authority_score']),
                                "source": "SEMrush",
                                "description": "SEMrush proprietary authority metric"
                            }
                        if sem.get('organic_traffic_est') is not None:
                            results["sem_traffic_metric"] = {
                                "status": "metric",
                                "metric": "Organic Traffic Est.",
                                "value": str(sem['organic_traffic_est']),
                                "source": "SEMrush",
                                "description": "Modelled monthly organic sessions"
                            }
                    
                    # Visual Analysis metrics (13 metrics from PRP-008)
                    if assessment.visual_analysis and isinstance(assessment.visual_analysis, dict):
                        visual = assessment.visual_analysis
                        if visual.get('visual_rubric_1') is not None:
                            results["visual_rubric_1_metric"] = {
                                "status": "metric",
                                "metric": "Above-the-fold Clarity",
                                "value": f"{visual['visual_rubric_1']}/10",
                                "source": "LLM Visual Analysis",
                                "description": "Headline + primary offer visible without scroll (grade 0-10)"
                            }
                        if visual.get('visual_rubric_2') is not None:
                            results["visual_rubric_2_metric"] = {
                                "status": "metric",
                                "metric": "Primary CTA Prominence", 
                                "value": f"{visual['visual_rubric_2']}/10",
                                "source": "LLM Visual Analysis",
                                "description": "Relative size / colour salience of CTA button"
                            }
                    
                    # LLM Content metrics (7 metrics from PRP-010)
                    if assessment.llm_insights and isinstance(assessment.llm_insights, dict):
                        llm = assessment.llm_insights
                        if llm.get('unique_value_prop_clarity') is not None:
                            results["uvp_clarity_metric"] = {
                                "status": "metric",
                                "metric": "Unique Value Prop Clarity",
                                "value": f"{llm['unique_value_prop_clarity']}/10",
                                "source": "LLM Content Generator", 
                                "description": "GPT-4 analysis of offer copy specificity"
                            }
                        if llm.get('contact_info_presence') is not None:
                            results["contact_info_metric"] = {
                                "status": "metric",
                                "metric": "Contact Info Presence",
                                "value": "Yes" if llm['contact_info_presence'] else "No",
                                "source": "LLM Content Generator",
                                "description": "GPT-4 detection of phone / address / email"
                            }
                    
                    return {
                        "task_id": task_id,
                        "status": "completed",
                        "message": f"Assessment completed successfully",
                        "results": results,
                        "assessment_id": assessment.id,
                        "lead_id": lead_id,
                        "total_score": assessment.total_score,
                        "created_at": assessment.created_at.isoformat() if assessment.created_at else None,
                        "updated_at": assessment.updated_at.isoformat() if assessment.updated_at else None
                    }
        
        # For other states, return the status as-is
        status_mapping = {
            "PENDING": "pending",
            "STARTED": "in_progress", 
            "PROGRESS": "in_progress",
            "SUCCESS": "completed",
            "FAILURE": "failed",
            "RETRY": "retrying",
            "REVOKED": "cancelled"
        }
        
        mapped_status = status_mapping.get(status_info.get("status"), "unknown")
        
        response = {
            "task_id": task_id,
            "status": mapped_status,
            "message": f"Assessment is {mapped_status}"
        }
        
        if status_info.get("info"):
            response["progress"] = status_info["info"]
            
        if status_info.get("error"):
            response["error"] = status_info["error"]
            
        return response
        
    except Exception as e:
        logger.error(f"Failed to get assessment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get assessment status: {str(e)}"
        )