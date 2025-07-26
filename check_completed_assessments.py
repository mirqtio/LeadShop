#!/usr/bin/env python3
"""
Check completed assessments in the database
"""

import subprocess
import json

# Use docker exec to run the query
cmd = """docker exec leadfactory_app python -c "
import asyncio
import sys
sys.path.append('/app')
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, desc
from src.models.lead import Assessment
from datetime import datetime, timedelta

DATABASE_URL = 'postgresql+asyncpg://leadgen:leadgen123@db:5432/leadgen'

async def check_assessments():
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Get assessments from the last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        result = await session.execute(
            select(Assessment)
            .where(Assessment.created_at > one_hour_ago)
            .order_by(Assessment.created_at.desc())
            .limit(10)
        )
        assessments = result.scalars().all()
        
        if assessments:
            print('Recent assessments (last hour):')
            for a in assessments:
                print(f'ID: {a.id}')
                print(f'Business: {a.business_name}')
                print(f'URL: {a.url}')
                print(f'Status: {a.overall_status}')
                print(f'Created: {a.created_at}')
                print(f'Has results: {bool(a.results)}')
                print('---')
        else:
            print('No assessments found in the last hour')
            
        # Also check all-time
        result2 = await session.execute(
            select(Assessment)
            .order_by(Assessment.created_at.desc())
            .limit(5)
        )
        all_assessments = result2.scalars().all()
        
        if all_assessments:
            print('\\nLatest 5 assessments (all time):')
            for a in all_assessments:
                print(f'ID: {a.id}, Business: {a.business_name}, Created: {a.created_at}')

asyncio.run(check_assessments())
"
"""

print("🔍 Checking completed assessments...")
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

if result.returncode == 0:
    print(result.stdout)
else:
    print(f"❌ Error: {result.stderr}")