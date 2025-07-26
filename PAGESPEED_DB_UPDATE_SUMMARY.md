# PageSpeed Database Update Summary

## Overview
Updated the PageSpeed assessment implementation to save all data to the new database schema introduced for PRP-014 (Decomposed Assessment Results).

## Changes Made

### 1. Updated `src/assessments/pagespeed.py`
- Modified `assess_pagespeed()` function to accept an optional `assessment_id` parameter
- Added new `save_pagespeed_analysis_to_db()` function that:
  - Saves data to the `pagespeed_analysis` table with all Core Web Vitals and metadata
  - Stores all individual audits in the `pagespeed_audits` table
  - Captures screenshots in the `pagespeed_screenshots` table
  - Records DOM elements in the `pagespeed_elements` table
  - Tracks third-party entities in the `pagespeed_entities` table
  - Identifies performance opportunities in the `pagespeed_opportunities` table
- Added `extract_category_score()` helper function for category score extraction
- Maintains backward compatibility by still returning the original data structure

### 2. Updated `src/assessment/tasks.py`
- Modified `pagespeed_task()` to:
  - Get or create an assessment record at the beginning
  - Pass the `assessment_id` to the `assess_pagespeed()` function
  - Import `sync_get_or_create_assessment` from the orchestrator

### 3. Updated `src/assessment/decompose_metrics.py`
- Added `extract_pagespeed_metrics_from_db()` function that:
  - Queries the new `pagespeed_analysis` table for metrics
  - Returns properly formatted metrics for the `assessment_results` table
- Modified `decompose_and_store_metrics()` to:
  - First check the new database tables for PageSpeed data
  - Fall back to JSON extraction if no data found in new tables
- Improved `extract_pagespeed_metrics()` to handle None values properly

## Database Schema Used

### Primary Tables
1. **pagespeed_analysis** - Main analysis results for mobile/desktop
   - Core Web Vitals (FCP, LCP, CLS, TBT, TTI, Speed Index)
   - Category scores (Performance, Accessibility, Best Practices, SEO)
   - Lighthouse metadata and configuration

2. **pagespeed_audits** - Individual audit results
   - All Lighthouse audits with scores and details
   - Numeric values and display values
   - Warnings and error messages

3. **pagespeed_screenshots** - Full page and filmstrip screenshots
   - Base64 encoded image data or S3 URLs
   - Dimensions and timing information

4. **pagespeed_elements** - DOM element positioning
   - CSS selectors and HTML snippets
   - Bounding rectangles for visual analysis

5. **pagespeed_entities** - Third-party resource tracking
   - Entity names, categories, and performance impact
   - Transfer sizes and blocking times

6. **pagespeed_opportunities** - Performance improvement recommendations
   - Potential time and byte savings
   - Detailed recommendations

## Benefits

1. **Comprehensive Data Storage**: All PageSpeed data is now preserved in structured tables
2. **Query Performance**: Can query specific metrics without parsing JSON
3. **Data Analysis**: Enables cross-assessment comparisons and trend analysis
4. **Audit Trail**: Complete audit history with all details preserved
5. **Backward Compatibility**: Existing code continues to work with JSON storage

## Testing

Created `test_pagespeed_db.py` to verify:
- Data saves correctly to all new tables
- Metrics are properly extracted
- Both mobile and desktop results are stored
- All relationships are maintained

## Next Steps

1. Run database migrations to create the new tables
2. Test with real PageSpeed assessments
3. Update reporting to use the new structured data
4. Consider similar updates for other assessment types (SEMrush, Security, etc.)