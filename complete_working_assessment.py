"""
Complete Working Assessment System - All 8 Components
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from src.core.database import AsyncSessionLocal
from src.models.lead import Lead, Assessment
from src.assessments.pagespeed import assess_pagespeed
from src.assessments.security_analysis import assess_security_headers
from src.assessments.semrush_integration import assess_semrush_domain
from src.assessments.gbp_integration import assess_google_business_profile
from src.assessments.screenshot_capture import capture_website_screenshots
from src.assessments.visual_analysis import assess_visual_analysis
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Store assessment status
assessment_status = {}

class AssessmentRequest(BaseModel):
    url: str
    business_name: str

async def run_complete_assessment(lead_id: int, assessment_id: int):
    """Run all 8 assessment components"""
    try:
        async with AsyncSessionLocal() as db:
            lead = await db.get(Lead, lead_id)
            assessment = await db.get(Assessment, assessment_id)
            
            if not lead or not assessment:
                return
            
            url = lead.url
            business_name = lead.company
            
            # Parse domain for SEMrush
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
            
            # 3. SEMrush Analysis
            try:
                logger.info(f"Running SEMrush for {domain}")
                assessment_status[assessment_id]["components"]["semrush"] = "running"
                results["semrush"] = await asyncio.wait_for(
                    assess_semrush_domain(domain, lead_id, assessment_id), 
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
                    assess_google_business_profile(business_name, None, None, None, lead_id, assessment_id),
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
                    capture_website_screenshots(url, lead_id, assessment_id),
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
                results["visual"] = await asyncio.wait_for(
                    assess_visual_analysis(url, lead_id, assessment_id),
                    timeout=30
                )
                assessment_status[assessment_id]["components"]["visual"] = "completed"
                logger.info("Visual Analysis completed")
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
            
            # Save to database
            assessment.pagespeed_data = results.get("pagespeed")
            assessment.security_headers = results.get("security")
            assessment.semrush_data = results.get("semrush")
            assessment.gbp_data = results.get("gbp")
            assessment.screenshots = results.get("screenshots")
            assessment.visual_analysis = results.get("visual")
            assessment.total_score = overall_score
            assessment.content_generation = content
            
            await db.commit()
            
            assessment_status[assessment_id]["status"] = "completed"
            assessment_status[assessment_id]["progress"] = 100
            assessment_status[assessment_id]["score"] = overall_score
            assessment_status[assessment_id]["results"] = results
            
            logger.info(f"Assessment {assessment_id} completed with score {overall_score}")
            
    except Exception as e:
        logger.error(f"Assessment failed: {e}")
        assessment_status[assessment_id]["status"] = "failed"
        assessment_status[assessment_id]["error"] = str(e)

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Complete Working Assessment - All 8 Components</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555;
        }
        input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
        }
        button {
            background: #007bff;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover {
            background: #0056b3;
        }
        button:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 4px;
            display: none;
        }
        .status.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .progress {
            margin-top: 20px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            height: 30px;
            display: none;
        }
        .progress-bar {
            background: #007bff;
            height: 100%;
            width: 0%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .components {
            margin-top: 20px;
            display: none;
        }
        .component-status {
            display: inline-block;
            margin: 5px;
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
        }
        .component-status.pending {
            background: #e9ecef;
            color: #6c757d;
        }
        .component-status.running {
            background: #fff3cd;
            color: #856404;
        }
        .component-status.completed {
            background: #d4edda;
            color: #155724;
        }
        .component-status.failed {
            background: #f8d7da;
            color: #721c24;
        }
        .results {
            margin-top: 30px;
            display: none;
        }
        .result-component {
            background: #f8f9fa;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 5px;
            border: 1px solid #dee2e6;
        }
        .result-component.success {
            background: #d4edda;
            border-color: #c3e6cb;
        }
        .result-component h3 {
            margin: 0 0 15px 0;
            color: #495057;
        }
        .metric {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(0,0,0,0.1);
        }
        .metric:last-child {
            border-bottom: none;
        }
        .score {
            font-size: 2em;
            font-weight: bold;
            color: #28a745;
            text-align: center;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Complete Assessment System</h1>
        <p class="subtitle">All 8 Components: PageSpeed, Security, SEMrush, GBP, Screenshots, Visual Analysis, Score Calculation, Content Generation</p>
        
        <form id="assessmentForm">
            <div class="form-group">
                <label for="url">Website URL:</label>
                <input type="url" id="url" name="url" required value="https://www.example.com">
            </div>
            
            <div class="form-group">
                <label for="businessName">Business Name:</label>
                <input type="text" id="businessName" name="businessName" value="Example Business">
            </div>
            
            <button type="submit" id="submitBtn">Run Complete Assessment (8 Components)</button>
        </form>
        
        <div id="status" class="status"></div>
        
        <div id="progress" class="progress">
            <div id="progressBar" class="progress-bar">0%</div>
        </div>
        
        <div id="components" class="components">
            <h3>Component Status:</h3>
            <span class="component-status pending" id="comp-pagespeed">PageSpeed</span>
            <span class="component-status pending" id="comp-security">Security</span>
            <span class="component-status pending" id="comp-semrush">SEMrush</span>
            <span class="component-status pending" id="comp-gbp">GBP</span>
            <span class="component-status pending" id="comp-screenshots">Screenshots</span>
            <span class="component-status pending" id="comp-visual">Visual</span>
            <span class="component-status pending" id="comp-score">Score</span>
            <span class="component-status pending" id="comp-content">Content</span>
        </div>
        
        <div id="results" class="results">
            <h2>Assessment Results</h2>
            <div id="resultsContainer"></div>
        </div>
    </div>
    
    <script>
        const form = document.getElementById('assessmentForm');
        const submitBtn = document.getElementById('submitBtn');
        const statusDiv = document.getElementById('status');
        const progressDiv = document.getElementById('progress');
        const progressBar = document.getElementById('progressBar');
        const componentsDiv = document.getElementById('components');
        const resultsDiv = document.getElementById('results');
        const resultsContainer = document.getElementById('resultsContainer');
        
        let pollInterval;
        let currentAssessmentId;
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = {
                url: document.getElementById('url').value,
                business_name: document.getElementById('businessName').value
            };
            
            // Reset UI
            submitBtn.disabled = true;
            submitBtn.textContent = 'Starting Assessment...';
            statusDiv.className = 'status info';
            statusDiv.textContent = 'Starting complete assessment with all 8 components...';
            statusDiv.style.display = 'block';
            progressDiv.style.display = 'block';
            componentsDiv.style.display = 'block';
            resultsDiv.style.display = 'none';
            progressBar.style.width = '0%';
            progressBar.textContent = '0%';
            
            // Reset component status
            document.querySelectorAll('.component-status').forEach(el => {
                el.className = 'component-status pending';
            });
            
            try {
                const response = await fetch('/assess', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                currentAssessmentId = data.assessment_id;
                
                statusDiv.textContent = `Assessment started. Running all 8 components...`;
                submitBtn.textContent = 'Assessment Running...';
                
                // Start polling for results
                pollInterval = setInterval(checkStatus, 2000);
                
            } catch (error) {
                statusDiv.className = 'status error';
                statusDiv.textContent = `Error: ${error.message}`;
                submitBtn.disabled = false;
                submitBtn.textContent = 'Run Complete Assessment (8 Components)';
                progressDiv.style.display = 'none';
                componentsDiv.style.display = 'none';
            }
        });
        
        async function checkStatus() {
            if (!currentAssessmentId) return;
            
            try {
                const response = await fetch(`/status/${currentAssessmentId}`);
                const data = await response.json();
                
                // Update progress
                if (data.progress !== undefined) {
                    progressBar.style.width = `${data.progress}%`;
                    progressBar.textContent = `${data.progress}%`;
                }
                
                // Update component status
                if (data.components) {
                    Object.entries(data.components).forEach(([component, status]) => {
                        const el = document.getElementById(`comp-${component}`);
                        if (el) {
                            el.className = `component-status ${status}`;
                        }
                    });
                }
                
                if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    statusDiv.className = 'status success';
                    statusDiv.textContent = 'Assessment completed successfully!';
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Run Complete Assessment (8 Components)';
                    
                    // Mark score and content as completed
                    document.getElementById('comp-score').className = 'component-status completed';
                    document.getElementById('comp-content').className = 'component-status completed';
                    
                    // Display results
                    displayResults(data);
                    
                } else if (data.status === 'failed') {
                    clearInterval(pollInterval);
                    statusDiv.className = 'status error';
                    statusDiv.textContent = `Assessment failed: ${data.error || 'Unknown error'}`;
                    submitBtn.disabled = false;
                    submitBtn.textContent = 'Run Complete Assessment (8 Components)';
                }
            } catch (error) {
                console.error('Error checking status:', error);
            }
        }
        
        function displayResults(data) {
            resultsContainer.innerHTML = '';
            resultsDiv.style.display = 'block';
            
            // Overall Score
            const scoreDiv = document.createElement('div');
            scoreDiv.className = 'result-component success';
            scoreDiv.innerHTML = `
                <h3>📊 Overall Assessment Score</h3>
                <div class="score">${data.score ? data.score.toFixed(1) : '0'}/100</div>
            `;
            resultsContainer.appendChild(scoreDiv);
            
            // Component Results
            const components = [
                { key: 'pagespeed', name: 'PageSpeed Insights', icon: '⚡' },
                { key: 'security', name: 'Security Headers', icon: '🛡️' },
                { key: 'semrush', name: 'SEMrush Analysis', icon: '🔍' },
                { key: 'gbp', name: 'Google Business Profile', icon: '🏢' },
                { key: 'screenshots', name: 'Screenshots', icon: '📸' },
                { key: 'visual', name: 'Visual Analysis', icon: '🎨' }
            ];
            
            components.forEach(comp => {
                const div = document.createElement('div');
                const hasData = data.results && data.results[comp.key];
                div.className = hasData ? 'result-component success' : 'result-component';
                
                let content = `<h3>${comp.icon} ${comp.name}</h3>`;
                
                if (hasData) {
                    const result = data.results[comp.key];
                    
                    if (comp.key === 'pagespeed' && result.mobile_analysis) {
                        const mobile = result.mobile_analysis.core_web_vitals || {};
                        const desktop = result.desktop_analysis?.core_web_vitals || {};
                        content += `
                            <div class="metric">
                                <span>Mobile Score:</span>
                                <span>${mobile.performance_score || 'N/A'}/100</span>
                            </div>
                            <div class="metric">
                                <span>Desktop Score:</span>
                                <span>${desktop.performance_score || 'N/A'}/100</span>
                            </div>
                        `;
                    } else if (comp.key === 'security') {
                        content += `
                            <div class="metric">
                                <span>Security Score:</span>
                                <span>${result.security_score || 'N/A'}/100</span>
                            </div>
                            <div class="metric">
                                <span>HTTPS Enabled:</span>
                                <span>${result.https_enabled ? 'Yes' : 'No'}</span>
                            </div>
                        `;
                    } else if (comp.key === 'semrush') {
                        content += `
                            <div class="metric">
                                <span>Domain Score:</span>
                                <span>${result.domain_score || 'N/A'}</span>
                            </div>
                        `;
                    } else if (comp.key === 'gbp') {
                        content += `
                            <div class="metric">
                                <span>Business Found:</span>
                                <span>${result.found ? 'Yes' : 'No'}</span>
                            </div>
                        `;
                    } else if (comp.key === 'screenshots') {
                        content += `
                            <div class="metric">
                                <span>Screenshots Captured:</span>
                                <span>${Array.isArray(result) ? result.length : 0}</span>
                            </div>
                        `;
                    } else if (comp.key === 'visual') {
                        content += `
                            <div class="metric">
                                <span>Analysis Status:</span>
                                <span>Completed</span>
                            </div>
                        `;
                    }
                } else {
                    content += '<p>Failed or no data</p>';
                }
                
                div.innerHTML = content;
                resultsContainer.appendChild(div);
            });
            
            // Content Generation
            const contentDiv = document.createElement('div');
            contentDiv.className = 'result-component';
            contentDiv.innerHTML = `
                <h3>📝 Content Generation</h3>
                <p><strong>Summary:</strong> Assessment completed for ${document.getElementById('businessName').value}</p>
                <p><strong>Recommendation:</strong> ${data.score < 50 ? 'Website needs significant improvements' : data.score < 70 ? 'Website has room for optimization' : 'Website is performing well'}</p>
            `;
            resultsContainer.appendChild(contentDiv);
        }
    </script>
</body>
</html>
"""

@app.post("/assess")
async def start_assessment(request: AssessmentRequest, background_tasks: BackgroundTasks):
    """Start complete assessment"""
    try:
        url = request.url
        business_name = request.business_name
        
        # Create lead and assessment in database
        async with AsyncSessionLocal() as db:
            # Check if lead exists
            existing_lead = await db.execute(
                select(Lead).where(Lead.url == url).order_by(Lead.created_at.desc()).limit(1)
            )
            existing_lead = existing_lead.scalar_one_or_none()
            
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
                await db.commit()
                await db.refresh(lead)
                lead_id = lead.id
            
            # Create assessment
            assessment = Assessment(
                lead_id=lead_id,
                created_at=datetime.now(timezone.utc)
            )
            db.add(assessment)
            await db.commit()
            await db.refresh(assessment)
            assessment_id = assessment.id
        
        # Run assessment in background
        background_tasks.add_task(run_complete_assessment, lead_id, assessment_id)
        
        return {
            "assessment_id": assessment_id,
            "status": "started",
            "message": f"Complete assessment started for {url}"
        }
        
    except Exception as e:
        logger.error(f"Failed to start assessment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{assessment_id}")
async def get_status(assessment_id: int):
    """Get assessment status"""
    if assessment_id in assessment_status:
        return assessment_status[assessment_id]
    else:
        # Check database
        async with AsyncSessionLocal() as db:
            assessment = await db.get(Assessment, assessment_id)
            if assessment and assessment.total_score is not None:
                return {
                    "status": "completed",
                    "progress": 100,
                    "score": assessment.total_score,
                    "results": {
                        "pagespeed": assessment.pagespeed_data,
                        "security": assessment.security_headers,
                        "semrush": assessment.semrush_data,
                        "gbp": assessment.gbp_data,
                        "screenshots": assessment.screenshots,
                        "visual": assessment.visual_analysis
                    }
                }
        
        return {"status": "not_found"}

if __name__ == "__main__":
    print("Starting Complete Assessment System...")
    print("Open http://localhost:8003 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8003)