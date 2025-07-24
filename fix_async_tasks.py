#!/usr/bin/env python3
"""
Fix async issues in tasks.py for Celery worker compatibility
"""

import re

# Read the original file
with open('src/assessment/tasks.py', 'r') as f:
    content = f.read()

# 1. Fix get_lead_url async pattern
async_get_lead_pattern = r'''        # Get lead information
        async def get_lead_url\(\):
            async with get_db\(\) as db:
                result = await db\.execute\(select\(Lead\)\.where\(Lead\.id == lead_id\)\)
                lead = result\.scalar_one_or_none\(\)
                if not lead:
                    raise AssessmentError\(f"Lead \{lead_id\} not found"\)
                if not lead\.url:
                    raise AssessmentError\(f"Lead \{lead_id\} has no URL for .*?"\)
                return lead\.url, lead\.company
        
        url, company = asyncio\.run\(get_lead_url\(\)\)'''

sync_get_lead_replacement = '''        # Get lead information using sync database access
        from src.core.database import SyncSessionLocal
        
        with SyncSessionLocal() as session:
            result = session.execute(select(Lead).where(Lead.id == lead_id))
            lead = result.scalar_one_or_none()
            if not lead:
                raise AssessmentError(f"Lead {lead_id} not found")
            if not lead.url:
                raise AssessmentError(f"Lead {lead_id} has no URL for assessment")
            url, company = lead.url, lead.company'''

content = re.sub(async_get_lead_pattern, sync_get_lead_replacement, content, flags=re.DOTALL)

# 2. Fix asyncio.run API calls - convert to proper async loop handling
asyncio_run_pattern = r'(\w+_results) = asyncio\.run\((\w+)\(([^)]+)\)\)'

def replace_asyncio_run(match):
    var_name = match.group(1)
    func_name = match.group(2)
    params = match.group(3)
    
    return f'''# Execute {func_name} - convert async to sync for Celery
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                {var_name} = loop.run_until_complete({func_name}({params}))
            finally:
                loop.close()'''

content = re.sub(asyncio_run_pattern, replace_asyncio_run, content)

# 3. Add sync imports at the top
utils_import_pattern = r'from \.utils import \(\n    update_assessment_field, \n    update_assessment_status, \n    ASSESSMENT_STATUS,\n    AssessmentError\n\)'

utils_import_replacement = '''from .utils import (
    update_assessment_field, 
    update_assessment_status,
    sync_update_assessment_field,
    sync_update_assessment_status,
    ASSESSMENT_STATUS,
    AssessmentError
)'''

content = re.sub(utils_import_pattern, utils_import_replacement, content)

# 4. Fix database update calls - replace asyncio.run with sync versions
# This is more complex, so let's do a simpler replacement
content = content.replace('asyncio.run(update_assessment_field(', 'sync_update_assessment_field(')
content = content.replace('asyncio.run(update_assessment_status(', 'sync_update_assessment_status(')

# 5. Fix function signature issues - remove extra parameters from sync calls
# Look for patterns like sync_update_assessment_field(a,b,c,d,e) and fix to proper format
def fix_sync_field_calls(content):
    # Pattern to match sync_update_assessment_field calls with too many params
    pattern = r'sync_update_assessment_field\(\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^,]+),\s*([^)]+)\s*\)'
    
    def replace_field_call(match):
        lead_id = match.group(1).strip()
        field1 = match.group(2).strip()
        value1 = match.group(3).strip()
        field2 = match.group(4).strip()
        value2 = match.group(5).strip()
        
        # Return two separate calls
        return f'''sync_update_assessment_field({lead_id}, {field1}, {value1})
        sync_update_assessment_field({lead_id}, {field2}, {value2})'''
    
    return re.sub(pattern, replace_field_call, content)

content = fix_sync_field_calls(content)

# Write the fixed content
with open('src/assessment/tasks.py', 'w') as f:
    f.write(content)

print("Fixed async issues in tasks.py")