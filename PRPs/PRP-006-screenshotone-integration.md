# PRP-006: ScreenshotOne Integration

## Task ID: PRP-006

## Wave: Data Collection Services

## Business Logic

The LeadFactory audit platform requires automated screenshot capture for comprehensive visual analysis in $399 audit reports. ScreenshotOne integration enables capturing desktop (1920x1080) and mobile (390x844) viewport screenshots of target websites, providing UX assessment capabilities and visual evidence for professional audit reports. Screenshots are optimized as WebP format at 85% quality and stored in S3 with signed URLs for secure access.

## Overview

Integrate ScreenshotOne API for automated website screenshot capture with:
- Desktop (1920x1080) and mobile (390x844) viewport screenshots  
- WebP format optimization at 85% quality for file size control
- Direct S3 upload integration with signed URL generation
- Celery task integration for asynchronous processing
- Cost optimization with <$0.002 per screenshot target
- Retry logic and timeout handling (30-second limits)
- File size validation (<500KB) and quality assurance

## Dependencies

- **External**: ScreenshotOne API account with access key, active subscription
- **Internal**: PRP-000 (AWS S3 Bucket Setup), PRP-002 (Assessment Orchestrator)
- **Blockers**: None

## Outcome-Focused Acceptance Criteria

1. **Desktop Screenshot Capture**: Successfully capture 1920x1080 desktop screenshots via ScreenshotOne API and verify image dimensions and WebP format
2. **Mobile Screenshot Capture**: Successfully capture 390x844 mobile screenshots with proper mobile viewport emulation and touch interface simulation
3. **S3 Integration**: Screenshots automatically uploaded to S3 bucket with generated signed URLs for secure access within 60 seconds
4. **File Size Optimization**: All screenshots <500KB with WebP 85% quality maintaining visual clarity for audit analysis
5. **Timeout Handling**: 30-second timeout limit enforced with retry logic (3 attempts) and graceful failure handling
6. **Cost Tracking**: Screenshot capture costs monitored and logged with <$0.002 per screenshot target achieved
7. **Celery Integration**: Screenshot tasks queued asynchronously with proper error handling and result storage
8. **Quality Validation**: Captured screenshots meet visual quality standards for UX analysis and audit report inclusion
9. **Error Recovery**: Failed captures logged with specific error details and retry attempts tracked
10. **Performance**: Screenshot capture and S3 upload complete within 90 seconds total processing time

## Integration Points

### ScreenshotOne API Client
- **Location**: `src/services/screenshot/screenshotone_client.py`
- **Dependencies**: requests, python-dotenv, PIL (image validation)
- **Functions**: capture_desktop(), capture_mobile(), validate_image(), retry_capture()

### Celery Task Integration
- **Location**: `src/tasks/screenshot_tasks.py`
- **Dependencies**: Celery, screenshotone_client, s3_client
- **Tasks**: capture_website_screenshots.delay(), process_screenshot_batch.delay()

### S3 Storage Integration
- **Location**: `src/services/storage/screenshot_storage.py`
- **Dependencies**: boto3, PRP-000 S3 configuration
- **Functions**: upload_screenshot(), generate_signed_url(), validate_upload()

### Assessment Integration
- **Location**: `src/assessment/visual_analyzer.py`
- **Dependencies**: PRP-002 Assessment Orchestrator
- **Integration**: Screenshot data inclusion in assessment results and audit reports

## Tests to Pass

1. **API Connection**: ScreenshotOne API authentication and basic connectivity test with valid response
2. **Desktop Screenshot**: Capture 1920x1080 desktop screenshot of test website with proper dimensions
3. **Mobile Screenshot**: Capture 390x844 mobile screenshot with mobile viewport emulation active
4. **S3 Upload Integration**: Screenshot automatically uploaded to S3 with successful signed URL generation
5. **File Size Validation**: Screenshot file size <500KB with WebP format and 85% quality maintained
6. **Timeout Testing**: 30-second timeout properly enforced with graceful failure and retry logic
7. **Celery Task Execution**: Asynchronous screenshot tasks complete successfully with proper error handling
8. **Cost Tracking**: Screenshot costs properly calculated and logged with budget monitoring
9. **Error Handling**: Failed API calls and uploads handled gracefully with detailed error logging
10. **Performance Testing**: Complete screenshot-to-S3 workflow completes within 90-second SLA

## Implementation Guide

### Phase 1: ScreenshotOne API Client (2 hours)
1. **Environment Setup**: Configure ScreenshotOne API key and endpoint in environment variables
2. **API Client Creation**: Implement screenshotone_client.py with authentication and request handling
3. **Viewport Configuration**: Configure desktop (1920x1080) and mobile (390x844) viewport parameters
4. **Image Optimization**: Implement WebP format conversion with 85% quality setting
5. **Error Handling**: Add retry logic (3 attempts) and timeout handling (30 seconds)
6. **Validation Functions**: Create image dimension and file size validation

### Phase 2: S3 Storage Integration (1.5 hours)
1. **S3 Client Integration**: Connect to existing S3 bucket from PRP-000 for screenshot storage
2. **Upload Functions**: Implement screenshot upload with proper S3 path structure and metadata
3. **Signed URL Generation**: Create secure signed URLs for screenshot access with expiration
4. **File Organization**: Organize screenshots by assessment ID and timestamp for easy retrieval
5. **Storage Validation**: Verify successful uploads and file integrity in S3

### Phase 3: Celery Task Integration (2 hours)
1. **Task Definition**: Create asynchronous screenshot capture tasks in screenshot_tasks.py
2. **Batch Processing**: Implement batch screenshot capture for multiple URLs efficiently
3. **Result Storage**: Store screenshot metadata and S3 URLs in assessment results
4. **Error Queue**: Implement failed task retry queue with exponential backoff
5. **Status Tracking**: Add task progress tracking and completion notifications

### Phase 4: Testing & Validation (1.5 hours)
1. **Unit Tests**: Create comprehensive test suite for all screenshot functions
2. **Integration Tests**: Test end-to-end screenshot capture and S3 storage workflow
3. **Performance Tests**: Validate 90-second SLA for complete screenshot processing
4. **Cost Testing**: Verify cost tracking accuracy and budget monitoring
5. **Error Testing**: Test failure scenarios and recovery mechanisms

## Validation Commands

```bash
# API connectivity validation
python -c "from src.services.screenshot.screenshotone_client import ScreenshotOneClient; client = ScreenshotOneClient(); print(client.test_connection())"

# Screenshot capture validation
python scripts/test_screenshot_capture.py --url="https://example.com" --desktop --mobile

# S3 integration validation
python -c "from src.services.storage.screenshot_storage import ScreenshotStorage; storage = ScreenshotStorage(); print(storage.test_upload())"

# Celery task validation
celery -A src.tasks.screenshot_tasks worker --loglevel=info &
python -c "from src.tasks.screenshot_tasks import capture_website_screenshots; result = capture_website_screenshots.delay('https://example.com'); print(result.get())"

# File size and quality validation
python scripts/validate_screenshot_quality.py --check-size --check-format --max-size=500KB

# Performance testing
python scripts/screenshot_performance_test.py --urls=10 --timeout=90

# Cost tracking validation
python scripts/screenshot_cost_analysis.py --period=24h --budget-check
```

## Rollback Strategy

### Emergency Procedures
1. **API Rate Limiting**: Implement circuit breaker pattern to prevent API quota exhaustion
2. **S3 Storage Full**: Implement cleanup policies for old screenshots and size monitoring
3. **Cost Overrun**: Disable screenshot capture and alert administrators immediately
4. **Quality Issues**: Fallback to alternative screenshot service or manual capture process

### Detailed Rollback Steps
1. **Identify Issue**: Determine if rollback needed due to cost, quality, or technical failure
2. **Stop New Tasks**: Halt all screenshot capture tasks and clear Celery queues
3. **Service Isolation**: Disable ScreenshotOne API client while preserving existing screenshots
4. **Data Preservation**: Ensure existing S3 screenshots remain accessible for current audits
5. **Fallback Mode**: Switch to manual screenshot process with admin notification
6. **Validation**: Verify audit reports can still be generated without new screenshots
7. **Documentation**: Record incident details and implement preventive measures

## Success Criteria

1. **API Integration Complete**: ScreenshotOne API client successfully captures both desktop and mobile screenshots
2. **S3 Storage Working**: Screenshots automatically stored in S3 with signed URLs generated reliably
3. **Quality Standards Met**: All screenshots meet <500KB size limit and visual quality requirements
4. **Performance Achieved**: 90-second SLA consistently met for complete screenshot processing workflow
5. **Cost Optimization**: Screenshot costs tracked and maintained under $0.002 per capture target
6. **Error Handling Robust**: Failed captures handled gracefully with detailed logging and retry logic
7. **Celery Integration**: Asynchronous processing working reliably with proper task management
8. **Testing Complete**: Comprehensive test suite passes with >95% coverage for all screenshot functions

## Critical Context

### ScreenshotOne Configuration
- **API Endpoint**: https://api.screenshotone.com/take
- **Authentication**: API key via environment variable SCREENSHOTONE_API_KEY
- **Viewport Settings**: desktop (1920x1080), mobile (390x844 iPhone 14)
- **Image Options**: WebP format, 85% quality, full page + above fold capture
- **Timeout Limits**: 30 seconds per capture with 3 retry attempts

### Cost Management
- **Target Cost**: <$0.002 per screenshot with monthly budget monitoring
- **Optimization**: Batch processing, smart caching, and retry limits
- **Monitoring**: Real-time cost tracking with alert thresholds
- **Budget Controls**: Automatic disable at 80% of monthly budget

### Integration Dependencies
- **S3 Bucket**: Uses leadshop-assets bucket from PRP-000 with screenshot/ prefix
- **Assessment Flow**: Integrates with PRP-002 Assessment Orchestrator for audit workflow
- **Task Queue**: Celery-based asynchronous processing for scalable screenshot capture
- **Quality Gates**: Visual quality validation ensures screenshots suitable for professional audit reports

### Technical Specifications
- **Desktop Screenshots**: 1920x1080 resolution, full page capture with lazy loading
- **Mobile Screenshots**: 390x844 resolution with mobile viewport and touch emulation
- **File Format**: WebP at 85% quality for optimal size/quality balance
- **Storage Path**: s3://leadshop-assets/screenshots/{assessment_id}/{timestamp}_{viewport}.webp
- **Signed URLs**: 24-hour expiration for secure audit report access