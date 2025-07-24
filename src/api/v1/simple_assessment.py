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
                    <th>Component</th>
                    <th>Score</th>
                    <th>Status</th>
                    <th>Details</th>
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
                resultsBody.innerHTML = '<tr><td colspan="4">No results available</td></tr>';
                resultsDiv.style.display = 'block';
                return;
            }
            
            let html = '';
            
            // Display each component's results
            Object.entries(results).forEach(([component, data]) => {
                const score = data.data?.score || 'N/A';
                const status = data.status || 'Unknown';
                const description = data.description || data.component || component;
                
                html += `
                    <tr>
                        <td>${component.toUpperCase()}</td>
                        <td>${score}</td>
                        <td>${status}</td>
                        <td>${description}</td>
                    </tr>
                `;
            });
            
            if (html === '') {
                html = '<tr><td colspan="4">No assessment data found</td></tr>';
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
        
        # Now use the existing orchestration system
        task_id = submit_assessment(lead_id)
        
        logger.info(f"Assessment task submitted: {task_id} for lead {lead_id}")
        
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
                    # Format the results for the frontend
                    results = {}
                    
                    # PageSpeed results
                    if assessment.pagespeed_score is not None:
                        results["pagespeed"] = {
                            "status": "success",
                            "data": {
                                "score": assessment.pagespeed_score,
                                "raw_data": assessment.pagespeed_data
                            },
                            "component": "PageSpeed Analysis",
                            "description": "Performance metrics and Core Web Vitals"
                        }
                    
                    # Security results  
                    if assessment.security_score is not None:
                        results["security"] = {
                            "status": "success", 
                            "data": {
                                "score": assessment.security_score,
                                "headers": assessment.security_headers
                            },
                            "component": "Security Analysis",
                            "description": "Technical security scanning and vulnerability assessment"
                        }
                    
                    # Mobile results
                    if assessment.mobile_score is not None:
                        results["mobile"] = {
                            "status": "success",
                            "data": {
                                "score": assessment.mobile_score
                            },
                            "component": "Mobile Analysis", 
                            "description": "Mobile optimization assessment"
                        }
                    
                    # SEO results
                    if assessment.seo_score is not None:
                        results["seo"] = {
                            "status": "success",
                            "data": {
                                "score": assessment.seo_score,
                                "semrush_data": assessment.semrush_data
                            },
                            "component": "SEO & Competitive Analysis",
                            "description": "SEMrush domain analysis and competitive insights"
                        }
                    
                    # Visual analysis results
                    if assessment.visual_analysis:
                        results["visual"] = {
                            "status": "success",
                            "data": assessment.visual_analysis,
                            "component": "Visual & UX Analysis", 
                            "description": "Screenshot analysis and visual design assessment"
                        }
                    
                    # LLM insights
                    if assessment.llm_insights:
                        results["insights"] = {
                            "status": "success",
                            "data": assessment.llm_insights,
                            "component": "AI Insights",
                            "description": "AI-powered analysis and recommendations"
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