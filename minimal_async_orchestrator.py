"""
Minimal async orchestrator with only working components
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import AsyncSessionLocal
from src.models.lead import Lead, Assessment
from src.assessments.pagespeed import assess_pagespeed
from src.assessments.security_analysis import assess_security_headers
from src.core.logging import get_logger

logger = get_logger(__name__)

class MinimalAsyncOrchestrator:
    """Minimal orchestrator with only working components"""
    
    def __init__(self):
        self.running_assessments: Dict[str, Dict[str, Any]] = {}
    
    async def execute_assessment(self, lead_id: int, assessment_id: Optional[int] = None) -> Dict[str, Any]:
        """Execute minimal assessment with working components"""
        task_id = f"minimal-{lead_id}-{datetime.now().timestamp()}"
        
        self.running_assessments[task_id] = {
            "status": "running",
            "progress": 0,
            "started_at": datetime.now(timezone.utc)
        }
        
        try:
            async with AsyncSessionLocal() as db:
                # Get lead info
                lead = await db.get(Lead, lead_id)
                if not lead:
                    raise ValueError(f"Lead {lead_id} not found")
                
                # Create assessment
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
                
                # Run working components
                results = {}
                
                # PageSpeed
                try:
                    logger.info("Running PageSpeed assessment...")
                    results["pagespeed"] = await asyncio.wait_for(
                        assess_pagespeed(lead.url), 
                        timeout=30
                    )
                    logger.info("PageSpeed completed")
                except Exception as e:
                    logger.error(f"PageSpeed failed: {e}")
                    results["pagespeed"] = None
                
                self.running_assessments[task_id]["progress"] = 50
                
                # Security
                try:
                    logger.info("Running Security assessment...")
                    results["security"] = await asyncio.wait_for(
                        assess_security_headers(lead.url), 
                        timeout=10
                    )
                    logger.info("Security completed")
                except Exception as e:
                    logger.error(f"Security failed: {e}")
                    results["security"] = None
                
                self.running_assessments[task_id]["progress"] = 100
                
                # Update assessment
                assessment.pagespeed_data = results.get("pagespeed")
                assessment.security_headers = results.get("security")
                
                # Calculate simple score
                scores = []
                if results.get("pagespeed"):
                    pagespeed_data = results["pagespeed"]
                    mobile_score = pagespeed_data.get("mobile_analysis", {}).get("core_web_vitals", {}).get("performance_score", 0)
                    scores.append(mobile_score)
                
                if results.get("security"):
                    security_data = results["security"]
                    if hasattr(security_data, 'security_score'):
                        scores.append(security_data.security_score)
                    elif isinstance(security_data, dict):
                        scores.append(security_data.get("security_score", 0))
                
                assessment.total_score = sum(scores) / len(scores) if scores else 0
                
                await db.commit()
                await db.refresh(assessment)
                
                # Update task status
                self.running_assessments[task_id]["status"] = "completed"
                self.running_assessments[task_id]["assessment_id"] = assessment_id
                
                return {
                    "task_id": task_id,
                    "assessment_id": assessment_id,
                    "status": "completed",
                    "results": results,
                    "score": assessment.total_score
                }
                
        except Exception as e:
            logger.error(f"Assessment failed: {str(e)}")
            self.running_assessments[task_id]["status"] = "failed"
            self.running_assessments[task_id]["error"] = str(e)
            raise
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a running task"""
        if task_id in self.running_assessments:
            return self.running_assessments[task_id]
        return {"status": "not_found"}

# Global orchestrator instance
minimal_orchestrator = MinimalAsyncOrchestrator()