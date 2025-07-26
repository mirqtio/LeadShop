-- Add missing columns to assessment_results table

-- Missing PageSpeed columns
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS pagespeed_speed_index INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS pagespeed_performance_score INTEGER;

-- Missing Security columns  
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS security_https_enforced BOOLEAN;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS security_tls_version VARCHAR(50);
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS security_hsts_header_present BOOLEAN;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS security_csp_header_present BOOLEAN;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS security_xframe_options_header BOOLEAN;

-- Missing Technical columns
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS tech_robots_txt_found BOOLEAN;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS tech_sitemap_xml_found BOOLEAN;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS tech_broken_internal_links_count INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS tech_js_console_errors_count INTEGER;

-- Missing GBP columns
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS gbp_hours JSON;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS gbp_review_count INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS gbp_rating FLOAT;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS gbp_photos_count INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS gbp_total_reviews INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS gbp_avg_rating FLOAT;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS gbp_recent_90d INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS gbp_rating_trend VARCHAR(50);
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS gbp_is_closed BOOLEAN;

-- Missing Screenshot columns
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS screenshots_captured BOOLEAN;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS screenshots_quality_assessment INTEGER;

-- Missing SEMrush columns
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS semrush_site_health_score INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS semrush_backlink_toxicity_score INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS semrush_organic_traffic_est INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS semrush_ranking_keywords_count INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS semrush_domain_authority_score INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS semrush_top_issue_categories JSON;

-- Missing Visual columns
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_performance_score INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_accessibility_score INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_best_practices_score INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_seo_score INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_above_fold_clarity INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_cta_prominence INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_trust_signals INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_hierarchy_contrast INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_text_readability INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_brand_cohesion INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_image_quality INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_mobile_responsive INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS visual_clutter_balance INTEGER;

-- Missing Content columns
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS content_unique_value_prop_clarity INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS content_contact_info_presence INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS content_next_step_clarity INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS content_social_proof_presence INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS content_quality_score INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS content_brand_voice_consistency INTEGER;
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS content_spam_score_assessment INTEGER;

-- Error tracking
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS error_components TEXT;

-- Timestamp
ALTER TABLE assessment_results ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();