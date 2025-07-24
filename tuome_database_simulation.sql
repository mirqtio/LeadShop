-- Tuome NYC Assessment Database Simulation
-- This shows what the data would look like when stored in PostgreSQL

-- 1. Lead Record
INSERT INTO leads (
    company, url, email, phone, address, city, state, zip_code, country,
    industry, employee_count, annual_revenue, lead_source, lead_status, notes,
    created_at, updated_at
) VALUES (
    'Tuome',
    'https://tuome.com',
    'contact@tuome.com',
    '+1 212-475-4645',
    '536 E 5th St',
    'New York',
    'NY',
    '10009',
    'US',
    'Restaurant',
    25,
    1500000,
    'comprehensive_assessment',
    'assessed',
    'NYC Asian fusion restaurant - full assessment completed',
    NOW(),
    NOW()
);

-- 2. Assessment Record with Comprehensive Data
INSERT INTO assessments (
    lead_id, status, total_score, pagespeed_score, security_score, mobile_score,
    pagespeed_data, security_headers, gbp_data,
    created_at, completed_at, assessment_duration_ms
) VALUES (
    (SELECT id FROM leads WHERE company = 'Tuome' AND city = 'New York'),
    'completed',
    84, -- Average of 78 + 75 + 100
    78,
    75, 
    100,
    -- PageSpeed JSON data
    '{
        "url": "https://tuome.com",
        "strategy": "mobile",
        "performance_score": 78,
        "core_web_vitals": {
            "first_contentful_paint": "1.2s",
            "largest_contentful_paint": "2.4s",
            "cumulative_layout_shift": "0.15",
            "total_blocking_time": "150ms",
            "time_to_interactive": "3.1s",
            "speed_index": "2.2s"
        },
        "opportunities": [
            "Enable text compression",
            "Properly size images", 
            "Eliminate render-blocking resources"
        ],
        "analysis_timestamp": "2024-01-20T15:30:00Z",
        "analysis_duration_ms": 2340
    }'::jsonb,
    -- Security Headers JSON data
    '{
        "url": "https://tuome.com",
        "scan_timestamp": "2024-01-20T15:32:00Z",
        "security_headers": {
            "hsts": "max-age=31536000; includeSubDomains",
            "csp": null,
            "x_frame_options": "DENY",
            "x_content_type_options": "nosniff",
            "referrer_policy": "strict-origin-when-cross-origin",
            "permissions_policy": null
        },
        "https_enforcement": {
            "scheme": "https",
            "enforced": true,
            "tls_version": "TLS 1.3",
            "certificate_valid": true,
            "hsts_enabled": true,
            "hsts_max_age": 31536000
        },
        "seo_signals": {
            "robots_txt": {
                "present": true,
                "status_code": 200,
                "size_bytes": 234,
                "has_sitemap_directive": true
            },
            "sitemap_xml": {
                "present": true,
                "status_code": 200,
                "size_bytes": 1567,
                "is_valid_xml": true
            }
        },
        "javascript_errors": {
            "error_count": 2,
            "warning_count": 5,
            "details": [
                {"type": "error", "text": "Uncaught TypeError: Cannot read property", "location": "main.js:45"},
                {"type": "warning", "text": "Deprecated API usage", "location": "analytics.js:12"}
            ]
        },
        "analysis_duration_ms": 1820
    }'::jsonb,
    -- Google Business Profile JSON data  
    '{
        "gbp_data": {
            "place_id": "ChIJ_____tuome_example_id",
            "name": "Tuome",
            "formatted_address": "536 E 5th St, New York, NY 10009, USA",
            "phone_number": "+1 212-475-4645",
            "website": "https://tuome.com",
            "hours": {
                "regular_hours": {
                    "monday": "17:30 - 22:00",
                    "tuesday": "17:30 - 22:00",
                    "wednesday": "17:30 - 22:00", 
                    "thursday": "17:30 - 22:00",
                    "friday": "17:30 - 23:00",
                    "saturday": "17:30 - 23:00",
                    "sunday": "17:30 - 22:00"
                },
                "is_24_hours": false,
                "timezone": "America/New_York"
            },
            "reviews": {
                "total_reviews": 487,
                "average_rating": 4.4,
                "recent_90d_reviews": 23,
                "rating_trend": "stable"
            },
            "photos": {
                "total_photos": 156,
                "owner_photos": 94,
                "customer_photos": 62,
                "photo_categories": {
                    "exterior": 23,
                    "interior": 48,
                    "food": 67,
                    "menu": 18
                }
            },
            "status": {
                "is_open_now": false,
                "is_permanently_closed": false,
                "temporarily_closed": false,
                "verified": true,
                "business_status": "operational"
            },
            "categories": ["Restaurant", "Asian Fusion"],
            "location": {
                "latitude": 40.7267,
                "longitude": -73.9864
            },
            "match_confidence": 0.92,
            "search_query": "Tuome New York NY",
            "extraction_timestamp": "2024-01-20T15:33:00Z"
        },
        "search_results_count": 3,
        "match_found": true,
        "match_confidence": 0.92,
        "analysis_duration_ms": 1240
    }'::jsonb,
    NOW(),
    NOW(),
    5400 -- Total time for all assessments
);

-- 3. Cost Tracking Records
INSERT INTO assessment_costs (
    lead_id, service_name, api_endpoint, cost_cents, currency,
    request_timestamp, response_status, response_time_ms,
    api_quota_used, rate_limited, retry_count,
    daily_budget_date, monthly_budget_date
) VALUES 
-- PageSpeed API Cost
(
    (SELECT id FROM leads WHERE company = 'Tuome' AND city = 'New York'),
    'google_pagespeed',
    'https://www.googleapis.com/pagespeedonline/v5/runPagespeed',
    0.25, -- $0.0025
    'USD',
    NOW(),
    'success',
    2340,
    true,
    false,
    0,
    DATE(NOW()),
    TO_CHAR(NOW(), 'YYYY-MM')
),
-- Technical Scraper Cost
(
    (SELECT id FROM leads WHERE company = 'Tuome' AND city = 'New York'),
    'technical_scraper',
    'playwright_scraper',
    0.10, -- $0.001
    'USD',
    NOW(),
    'success',
    1820,
    false,
    false,
    0,
    DATE(NOW()),
    TO_CHAR(NOW(), 'YYYY-MM')
),
-- Google Places API Cost
(
    (SELECT id FROM leads WHERE company = 'Tuome' AND city = 'New York'),
    'google_business_profile',
    'https://places.googleapis.com/v1/places:searchText',
    1.70, -- $0.017
    'USD',
    NOW(),
    'success',
    1240,
    true,
    false,
    0,
    DATE(NOW()),
    TO_CHAR(NOW(), 'YYYY-MM')
);

-- Query to verify the complete assessment
SELECT 
    l.company,
    l.city,
    l.state,
    l.url,
    a.total_score,
    a.pagespeed_score,
    a.security_score,
    a.mobile_score,
    a.status,
    -- Extract specific metrics from JSON data
    a.pagespeed_data->>'performance_score' as pagespeed_performance,
    a.pagespeed_data->'core_web_vitals'->>'largest_contentful_paint' as lcp,
    a.security_headers->'https_enforcement'->>'enforced' as https_enforced,
    a.security_headers->'security_headers'->>'hsts' as hsts_header,
    a.gbp_data->'gbp_data'->>'name' as gbp_business_name,
    a.gbp_data->'gbp_data'->'reviews'->>'total_reviews' as gbp_reviews,
    a.gbp_data->'gbp_data'->'reviews'->>'average_rating' as gbp_rating,
    -- Cost summary
    (SELECT SUM(cost_cents)/100 FROM assessment_costs WHERE lead_id = l.id) as total_cost_usd
FROM leads l
JOIN assessments a ON l.id = a.lead_id
WHERE l.company = 'Tuome' AND l.city = 'New York';

-- Query to show all 25 metrics that would be extracted
SELECT 
    '1. First Contentful Paint' as metric,
    a.pagespeed_data->'core_web_vitals'->>'first_contentful_paint' as value,
    'PageSpeed' as source
FROM assessments a
JOIN leads l ON a.lead_id = l.id
WHERE l.company = 'Tuome'

UNION ALL

SELECT 
    '2. Largest Contentful Paint',
    a.pagespeed_data->'core_web_vitals'->>'largest_contentful_paint',
    'PageSpeed'
FROM assessments a JOIN leads l ON a.lead_id = l.id WHERE l.company = 'Tuome'

UNION ALL

SELECT 
    '3. Cumulative Layout Shift',
    a.pagespeed_data->'core_web_vitals'->>'cumulative_layout_shift',
    'PageSpeed'
FROM assessments a JOIN leads l ON a.lead_id = l.id WHERE l.company = 'Tuome'

-- ... (would continue for all 25 metrics)

UNION ALL

SELECT 
    '24. GBP Rating Trend',
    a.gbp_data->'gbp_data'->'reviews'->>'rating_trend',
    'Google Business Profile'
FROM assessments a JOIN leads l ON a.lead_id = l.id WHERE l.company = 'Tuome'

UNION ALL

SELECT 
    '25. Business Permanently Closed',
    a.gbp_data->'gbp_data'->'status'->>'is_permanently_closed',
    'Google Business Profile'
FROM assessments a JOIN leads l ON a.lead_id = l.id WHERE l.company = 'Tuome';

-- Summary statistics
SELECT 
    'Assessment Summary' as report_section,
    COUNT(*) as total_leads_assessed,
    AVG(total_score) as avg_total_score,
    AVG(pagespeed_score) as avg_pagespeed_score,
    AVG(security_score) as avg_security_score,
    AVG(mobile_score) as avg_mobile_score,
    SUM((SELECT SUM(cost_cents) FROM assessment_costs WHERE lead_id = assessments.lead_id))/100 as total_cost_usd
FROM assessments
JOIN leads ON assessments.lead_id = leads.id
WHERE leads.company = 'Tuome';

/*
Expected Results Summary:
- Lead: Tuome, New York, NY
- Total Score: 84/100
- PageSpeed Score: 78/100 (Good performance with optimization opportunities)
- Security Score: 75/100 (HTTPS enforced, some headers missing)
- Mobile Score: 100/100 (Complete GBP profile with high ratings)
- Total Cost: $0.0205 per assessment
- Data Points: 25 comprehensive metrics captured
- Status: Ready for $399 audit report generation
*/