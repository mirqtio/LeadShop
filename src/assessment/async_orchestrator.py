"""
Async-native assessment orchestrator
Replaces Celery with direct async execution
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.database import AsyncSessionLocal, get_db
from src.models.lead import Lead, Assessment
from src.models.assessment_results import AssessmentResults
from src.assessments.pagespeed import assess_pagespeed
from src.assessments.security_analysis import assess_security_headers
from src.assessments.semrush_integration import assess_semrush_domain
from src.assessments.gbp_integration import assess_google_business_profile
from src.assessments.screenshot_capture import capture_website_screenshots
from src.assessments.visual_analysis import assess_visual_analysis
from src.core.logging import get_logger

logger = get_logger(__name__)

class AsyncAssessmentOrchestrator:
    """Manages async assessment execution without Celery"""
    
    def __init__(self):
        self.running_assessments: Dict[str, Dict[str, Any]] = {}
    
    async def execute_assessment(self, lead_id: int, assessment_id: Optional[int] = None) -> Dict[str, Any]:
        """Execute full assessment pipeline asynchronously"""
        task_id = f"assessment-{lead_id}-{datetime.now().timestamp()}"
        
        # Track assessment progress
        self.running_assessments[task_id] = {
            "status": "running",
            "progress": 0,
            "components": {},
            "started_at": datetime.now(timezone.utc)
        }
        
        try:
            async with AsyncSessionLocal() as db:
                # Get lead info
                lead = await db.get(Lead, lead_id)
                if not lead:
                    raise ValueError(f"Lead {lead_id} not found")
                
                # Create or get assessment
                if not assessment_id:
                    assessment = Assessment(
                        lead_id=lead_id,
                        created_at=datetime.now(timezone.utc)
                    )
                    db.add(assessment)
                    await db.commit()
                    await db.refresh(assessment)
                    assessment_id = assessment.id
                else:
                    assessment = await db.get(Assessment, assessment_id)
                
                # Execute all assessment components concurrently
                results = await self._run_all_assessments(lead, assessment, db)
                
                # Update assessment with results
                assessment.pagespeed_data = results.get("pagespeed")
                assessment.security_headers = results.get("security")
                assessment.semrush_data = results.get("semrush")
                assessment.gbp_data = results.get("gbp")
                assessment.screenshots = results.get("screenshots")
                assessment.visual_analysis = results.get("visual")
                
                # Calculate overall score
                assessment.total_score = self._calculate_score(results)
                
                await db.commit()
                await db.refresh(assessment)
                
                # Update task status
                self.running_assessments[task_id]["status"] = "completed"
                self.running_assessments[task_id]["progress"] = 100
                self.running_assessments[task_id]["assessment_id"] = assessment_id
                
                return {
                    "task_id": task_id,
                    "assessment_id": assessment_id,
                    "status": "completed",
                    "results": results
                }
                
        except Exception as e:
            logger.error(f"Assessment failed: {str(e)}")
            self.running_assessments[task_id]["status"] = "failed"
            self.running_assessments[task_id]["error"] = str(e)
            raise
    
    async def _run_all_assessments(self, lead: Lead, assessment: Assessment, db: AsyncSession) -> Dict[str, Any]:
        """Run all assessment components concurrently"""
        url = lead.url
        business_name = lead.company
        
        # Extract domain from URL for SEMrush
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc or parsed_url.path
        
        # Create tasks for all components
        tasks = {
            "pagespeed": self._run_with_timeout(assess_pagespeed(url), 45),
            "security": self._run_with_timeout(assess_security_headers(url), 10),
            "semrush": self._run_with_timeout(assess_semrush_domain(domain, lead.id, assessment.id), 20),
            "gbp": self._run_with_timeout(assess_google_business_profile(business_name, lead.address, None, None, lead.id, assessment.id), 15),
            "screenshots": self._run_with_timeout(capture_website_screenshots(url, lead.id, assessment.id), 60),
        }
        
        # Run all tasks concurrently
        results = {}
        for name, task in tasks.items():
            try:
                result = await task
                results[name] = result
                logger.info(f"Component {name} completed successfully")
                
                # Update progress
                completed = len(results)
                total = len(tasks)
                progress = int((completed / total) * 100)
                # Find the task_id for this assessment
                for tid, data in self.running_assessments.items():
                    if data.get("assessment_id") == assessment.id:
                        self.running_assessments[tid]["progress"] = progress
                        break
                    
            except asyncio.TimeoutError:
                logger.error(f"Component {name} timed out")
                results[name] = None
            except Exception as e:
                logger.error(f"Component {name} failed: {str(e)}")
                results[name] = None
        
        # Visual analysis depends on screenshots
        if results.get("screenshots"):
            try:
                results["visual"] = await self._run_with_timeout(
                    assess_visual_analysis(url, lead.id, assessment.id), 30
                )
            except Exception as e:
                logger.error(f"Visual analysis failed: {str(e)}")
                results["visual"] = None
        else:
            results["visual"] = None
        
        return results
    
    async def _run_with_timeout(self, coro, timeout_seconds: int):
        """Run a coroutine with timeout"""
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    
    def _calculate_score(self, results: Dict[str, Any]) -> float:
        """Calculate overall assessment score"""
        scores = []
        
        # PageSpeed score
        if results.get("pagespeed"):
            pagespeed_data = results["pagespeed"]
            mobile_score = pagespeed_data.get("mobile_analysis", {}).get("core_web_vitals", {}).get("performance_score", 0)
            desktop_score = pagespeed_data.get("desktop_analysis", {}).get("core_web_vitals", {}).get("performance_score", 0)
            scores.append((mobile_score + desktop_score) / 2)
        
        # Security score
        if results.get("security"):
            security_score = results["security"].get("security_score", 0)
            scores.append(security_score)
        
        # SEMrush score (normalized)
        if results.get("semrush"):
            domain_score = results["semrush"].get("domain_score", 0)
            scores.append(domain_score)
        
        # GBP score (0 or 100 based on found)
        if results.get("gbp"):
            gbp_score = 100 if results["gbp"].get("found") else 0
            scores.append(gbp_score)
        
        # Visual analysis score
        if results.get("visual"):
            # Simple scoring based on presence
            scores.append(80)
        
        # Calculate average
        if scores:
            return sum(scores) / len(scores)
        return 0
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a running task"""
        if task_id in self.running_assessments:
            return self.running_assessments[task_id]
        return {"status": "not_found"}

# Global orchestrator instance
orchestrator = AsyncAssessmentOrchestrator()