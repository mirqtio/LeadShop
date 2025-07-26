"""
Quick test to check screenshot data in database
"""
import asyncio
from sqlalchemy import select
from src.core.database import AsyncSessionLocal
from src.models.screenshot import Screenshot
from src.models.lead import Assessment

async def check_screenshots():
    async with AsyncSessionLocal() as db:
        # Get the most recent assessment with screenshots
        result = await db.execute(
            select(Assessment)
            .order_by(Assessment.id.desc())
            .limit(1)
        )
        assessment = result.scalar_one_or_none()
        
        if assessment:
            print(f"Assessment ID: {assessment.id}")
            
            # Get screenshots for this assessment
            result = await db.execute(
                select(Screenshot)
                .filter(Screenshot.assessment_id == assessment.id)
            )
            screenshots = result.scalars().all()
            
            print(f"Found {len(screenshots)} screenshots")
            for screenshot in screenshots:
                print(f"\nScreenshot ID: {screenshot.id}")
                print(f"Type: {screenshot.screenshot_type}")
                print(f"Viewport: {screenshot.viewport_width}x{screenshot.viewport_height}")
                print(f"Image URL length: {len(screenshot.image_url) if screenshot.image_url else 0}")
                print(f"Image URL preview: {screenshot.image_url[:100] if screenshot.image_url else 'None'}...")

if __name__ == "__main__":
    asyncio.run(check_screenshots())