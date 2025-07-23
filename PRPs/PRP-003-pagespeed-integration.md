# PRP-003: PageSpeed Integration

## Task ID: PRP-003

## Wave: Foundation Infrastructure

## Business Logic

The LeadFactory AI-powered audit platform requires comprehensive website performance analysis using Google PageSpeed Insights API v5 to capture Core Web Vitals for $399 audit reports. Website performance directly impacts SEO rankings, user conversion rates, and business revenue. This integration provides critical performance metrics including First Contentful Paint (FCP), Largest Contentful Paint (LCP), Cumulative Layout Shift (CLS), Total Blocking Time (TBT), and Time to Interactive (TTI) that form the foundation of actionable website improvement recommendations for business clients.

## Overview

Implement comprehensive PageSpeed Insights API v5 integration for capturing all Core Web Vitals and performance metrics:
- Mobile-first performance assessment with desktop fallback capability
- Complete Core Web Vitals extraction (FCP, LCP, CLS, TBT, TTI, Overall Performance Score)
- API key rotation and rate limiting management (25K requests/day free tier)
- Cost tracking and optimization ($0.0025 per call beyond free tier)
- Celery task integration for asynchronous processing within assessment orchestrator
- Robust error handling with 30-second timeout and retry logic

## Dependencies

- **External**: Google PageSpeed Insights API v5, Celery for async processing
- **Internal**: PRP-002 (Assessment Orchestrator) for task coordination and session management
- **Blockers**: None

## Outcome-Focused Acceptance Criteria

1. **Core Web Vitals Capture**: All 6 critical metrics (FCP, LCP, CLS, TBT, TTI, Performance Score) extracted and stored in assessment results with mobile and desktop variants
2. **API Integration Operational**: PageSpeed client successfully analyzes URLs with proper authentication, returns structured data within 30-second timeout
3. **Mobile-First Implementation**: Primary analysis uses mobile strategy, desktop analysis optional but available, mobile scores prioritized in reports
4. **Cost Tracking Accuracy**: Each API call tracked at $0.0025 with daily quota monitoring, cost attribution per assessment session
5. **Error Handling Robustness**: Failed requests logged with error details, graceful degradation for API timeouts, retry logic for transient failures
6. **Rate Limiting Compliance**: Respects 25K daily limit and 50 requests/second burst limit, implements exponential backoff for rate limit errors
7. **Assessment Orchestrator Integration**: Celery tasks coordinate with PRP-002 orchestrator, proper session management and result storage
8. **Data Storage Comprehensive**: Raw PageSpeed data stored in JSONB fields, extracted metrics in structured columns for fast querying
9. **API Key Rotation**: Support for multiple API keys with automatic rotation, secure credential management
10. **Performance Optimization**: Assessment completion within 35 seconds (30s API + 5s processing), parallel desktop/mobile analysis when requested

## Integration Points

### PageSpeed Client Enhancement (d0_gateway/providers/pagespeed.py)
- **Location**: `d0_gateway/providers/pagespeed.py`
- **Dependencies**: Google PageSpeed Insights API v5, rate limiting, cost tracking
- **Functions**: Enhanced analyze_url(), API key rotation, comprehensive error handling

### Assessment Service Integration (d3_assessment/pagespeed.py)
- **Location**: `d3_assessment/pagespeed.py`
- **Dependencies**: PageSpeed client, assessment models, Celery integration
- **Functions**: Mobile-first assessment workflow, Core Web Vitals extraction, cost calculation

### Celery Task Implementation
- **Location**: `d3_assessment/tasks/pagespeed_tasks.py`
- **Dependencies**: Celery, PRP-002 orchestrator, session management
- **Functions**: Asynchronous PageSpeed analysis, result storage, error handling

### Assessment Models Extension (d3_assessment/models.py)
- **Location**: `d3_assessment/models.py`
- **Dependencies**: SQLAlchemy, JSONB storage, cost tracking models
- **Resources**: Enhanced AssessmentResult with PageSpeed data fields, AssessmentCost integration

## Test Coverage Requirements

### Unit Tests (tests/unit/d3_assessment/)
- **PageSpeed Client Tests**: API calls, authentication, rate limiting, error scenarios
- **Assessment Service Tests**: Core Web Vitals extraction, mobile-first logic, cost calculation
- **Model Tests**: Data storage, field validation, relationship integrity

### Integration Tests (tests/integration/d3_assessment/)
- **Live API Integration**: Real PageSpeed API calls (using test quota), complete data flow
- **Celery Integration**: Task execution, result storage, orchestrator coordination
- **Error Handling Integration**: Timeout scenarios, rate limiting, API failures

### Performance Tests (tests/performance/)
- **API Response Time**: 30-second timeout validation, performance under load
- **Cost Optimization**: Quota usage tracking, batch processing efficiency
- **Concurrent Processing**: Multiple assessment handling, rate limit compliance

## Business Requirements

### Performance Impact Analysis
- **Core Web Vitals Standards**: LCP <2.5s (good), CLS <0.1 (good), TBT <200ms (good)
- **SEO Impact**: Performance scores directly affect Google search rankings
- **Conversion Impact**: 1-second delay can reduce conversions by 7%
- **Audit Value**: Performance improvements demonstrate clear ROI for $399 reports

### Cost Optimization Strategy
- **Free Tier Management**: 25K requests/day optimization, request deduplication
- **Paid Tier Planning**: $4 per 1K requests beyond free tier, budget tracking
- **Assessment Efficiency**: Intelligent caching, bulk processing capabilities
- **ROI Tracking**: Cost per assessment vs. report sale value analysis

### Data Quality Assurance
- **Metrics Accuracy**: Validate Core Web Vitals against Google standards
- **Report Reliability**: Consistent results for audit report generation
- **Error Recovery**: Graceful handling of API failures, partial data acceptance
- **Data Freshness**: Timestamp tracking, cache invalidation strategies

## Implementation Phases

### Phase 1: Core Integration (Week 1)
- Enhance PageSpeed client with API key rotation
- Implement mobile-first assessment service
- Core Web Vitals extraction and storage
- Basic error handling and timeout management

### Phase 2: Orchestrator Integration (Week 1)
- Celery task implementation for async processing
- Integration with PRP-002 assessment orchestrator
- Session management and result coordination
- Cost tracking and quota management

### Phase 3: Optimization & Testing (Week 1)
- Comprehensive test coverage (unit + integration)
- Performance optimization and rate limiting
- Error handling refinement and monitoring
- Documentation and deployment preparation

## Success Metrics

- **Functional**: 100% Core Web Vitals capture rate, <1% API failure rate
- **Performance**: 95% of assessments complete within 35 seconds
- **Cost**: Maintain <$0.01 per assessment average cost (including free tier)
- **Quality**: Zero data corruption, 99.9% result storage accuracy
- **Integration**: Seamless orchestrator coordination, proper session management

## Risk Mitigation

### API Reliability Risks
- **Mitigation**: Retry logic, timeout handling, graceful degradation
- **Monitoring**: API response time tracking, error rate alerting
- **Fallback**: Alternative performance measurement tools if needed

### Cost Overrun Risks
- **Mitigation**: Daily quota monitoring, intelligent caching, request optimization
- **Controls**: Cost alerts, automatic throttling, budget limits
- **Tracking**: Per-session cost attribution, ROI analysis

### Integration Complexity Risks
- **Mitigation**: Phased implementation, comprehensive testing, documentation
- **Validation**: Integration tests with orchestrator, end-to-end workflow testing
- **Support**: Clear error messages, detailed logging, troubleshooting guides