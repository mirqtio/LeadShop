"""Add SEMrush analysis tables

Revision ID: 011
Revises: 010
Create Date: 2025-01-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    # Create semrush_analysis table for domain metrics
    op.create_table(
        'semrush_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(255), nullable=False),
        sa.Column('site_health_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('backlink_toxicity_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('organic_traffic_estimate', sa.BigInteger(), nullable=True),
        sa.Column('paid_traffic_estimate', sa.BigInteger(), nullable=True),
        sa.Column('ranking_keywords_count', sa.Integer(), nullable=True),
        sa.Column('domain_authority_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('trust_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('backlinks_total', sa.Integer(), nullable=True),
        sa.Column('referring_domains', sa.Integer(), nullable=True),
        sa.Column('referring_ips', sa.Integer(), nullable=True),
        sa.Column('referring_subnets', sa.Integer(), nullable=True),
        sa.Column('organic_search_positions', sa.Integer(), nullable=True),
        sa.Column('paid_search_positions', sa.Integer(), nullable=True),
        sa.Column('organic_cost_estimate', sa.Float(), nullable=True),  # USD
        sa.Column('paid_cost_estimate', sa.Float(), nullable=True),  # USD
        sa.Column('analysis_timestamp', sa.DateTime(), nullable=False),
        sa.Column('api_credits_used', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for semrush_analysis
    op.create_index(op.f('ix_semrush_analysis_assessment_id'), 'semrush_analysis', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_semrush_analysis_domain'), 'semrush_analysis', ['domain'], unique=False)
    op.create_index(op.f('ix_semrush_analysis_site_health_score'), 'semrush_analysis', ['site_health_score'], unique=False)
    op.create_index(op.f('ix_semrush_analysis_domain_authority_score'), 'semrush_analysis', ['domain_authority_score'], unique=False)
    op.create_index(op.f('ix_semrush_analysis_created_at'), 'semrush_analysis', ['created_at'], unique=False)
    
    # Create semrush_technical_issues table for SEO issues
    op.create_table(
        'semrush_technical_issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('semrush_analysis_id', sa.Integer(), nullable=False),
        sa.Column('issue_type', sa.String(100), nullable=False),  # crawlability, https, sitemap, etc.
        sa.Column('issue_category', sa.String(50), nullable=False),  # errors, warnings, notices
        sa.Column('severity', sa.String(20), nullable=False),  # critical, high, medium, low
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('affected_pages', sa.Integer(), nullable=True),
        sa.Column('first_detected', sa.DateTime(), nullable=True),
        sa.Column('fix_priority', sa.Integer(), nullable=True),  # 1-10
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('example_urls', postgresql.JSON(), nullable=True),  # Array of example URLs
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['semrush_analysis_id'], ['semrush_analysis.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for semrush_technical_issues
    op.create_index(op.f('ix_semrush_technical_issues_semrush_analysis_id'), 'semrush_technical_issues', ['semrush_analysis_id'], unique=False)
    op.create_index(op.f('ix_semrush_technical_issues_issue_type'), 'semrush_technical_issues', ['issue_type'], unique=False)
    op.create_index(op.f('ix_semrush_technical_issues_issue_category'), 'semrush_technical_issues', ['issue_category'], unique=False)
    op.create_index(op.f('ix_semrush_technical_issues_severity'), 'semrush_technical_issues', ['severity'], unique=False)
    op.create_index(op.f('ix_semrush_technical_issues_fix_priority'), 'semrush_technical_issues', ['fix_priority'], unique=False)
    
    # Create semrush_keywords table for keyword metrics
    op.create_table(
        'semrush_keywords',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('semrush_analysis_id', sa.Integer(), nullable=False),
        sa.Column('keyword', sa.String(255), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('previous_position', sa.Integer(), nullable=True),
        sa.Column('position_change', sa.Integer(), nullable=True),
        sa.Column('search_volume', sa.Integer(), nullable=True),
        sa.Column('keyword_difficulty', sa.Integer(), nullable=True),  # 0-100
        sa.Column('cpc', sa.Float(), nullable=True),  # Cost per click in USD
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('traffic_percentage', sa.Float(), nullable=True),
        sa.Column('traffic_estimate', sa.Integer(), nullable=True),
        sa.Column('traffic_cost', sa.Float(), nullable=True),
        sa.Column('competition_level', sa.Float(), nullable=True),  # 0-1
        sa.Column('results_count', sa.BigInteger(), nullable=True),
        sa.Column('trend', postgresql.JSON(), nullable=True),  # Monthly search volume trend
        sa.Column('serp_features', postgresql.JSON(), nullable=True),  # Featured snippets, etc.
        sa.Column('intent', sa.String(50), nullable=True),  # informational, transactional, navigational, commercial
        sa.Column('is_branded', sa.Boolean(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['semrush_analysis_id'], ['semrush_analysis.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for semrush_keywords
    op.create_index(op.f('ix_semrush_keywords_semrush_analysis_id'), 'semrush_keywords', ['semrush_analysis_id'], unique=False)
    op.create_index(op.f('ix_semrush_keywords_keyword'), 'semrush_keywords', ['keyword'], unique=False)
    op.create_index(op.f('ix_semrush_keywords_position'), 'semrush_keywords', ['position'], unique=False)
    op.create_index(op.f('ix_semrush_keywords_search_volume'), 'semrush_keywords', ['search_volume'], unique=False)
    op.create_index(op.f('ix_semrush_keywords_traffic_estimate'), 'semrush_keywords', ['traffic_estimate'], unique=False)
    
    # Create semrush_backlinks table for backlink analysis
    op.create_table(
        'semrush_backlinks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('semrush_analysis_id', sa.Integer(), nullable=False),
        sa.Column('source_url', sa.Text(), nullable=False),
        sa.Column('source_domain', sa.String(255), nullable=False),
        sa.Column('target_url', sa.Text(), nullable=False),
        sa.Column('anchor_text', sa.Text(), nullable=True),
        sa.Column('link_type', sa.String(50), nullable=True),  # text, image, redirect, form
        sa.Column('link_attribute', sa.String(50), nullable=True),  # dofollow, nofollow, sponsored, ugc
        sa.Column('first_seen', sa.DateTime(), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('is_new', sa.Boolean(), nullable=True),
        sa.Column('is_lost', sa.Boolean(), nullable=True),
        sa.Column('source_page_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('source_domain_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('source_trust_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('toxicity_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('spam_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['semrush_analysis_id'], ['semrush_analysis.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for semrush_backlinks
    op.create_index(op.f('ix_semrush_backlinks_semrush_analysis_id'), 'semrush_backlinks', ['semrush_analysis_id'], unique=False)
    op.create_index(op.f('ix_semrush_backlinks_source_domain'), 'semrush_backlinks', ['source_domain'], unique=False)
    op.create_index(op.f('ix_semrush_backlinks_toxicity_score'), 'semrush_backlinks', ['toxicity_score'], unique=False)
    op.create_index(op.f('ix_semrush_backlinks_source_domain_score'), 'semrush_backlinks', ['source_domain_score'], unique=False)
    
    # Create semrush_competitors table for competitor analysis
    op.create_table(
        'semrush_competitors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('semrush_analysis_id', sa.Integer(), nullable=False),
        sa.Column('competitor_domain', sa.String(255), nullable=False),
        sa.Column('competition_level', sa.Float(), nullable=False),  # 0-1
        sa.Column('common_keywords', sa.Integer(), nullable=True),
        sa.Column('competitor_organic_traffic', sa.BigInteger(), nullable=True),
        sa.Column('competitor_paid_traffic', sa.BigInteger(), nullable=True),
        sa.Column('competitor_authority_score', sa.Integer(), nullable=True),
        sa.Column('traffic_overlap', sa.Float(), nullable=True),  # Percentage
        sa.Column('keyword_overlap', sa.Float(), nullable=True),  # Percentage
        sa.Column('gap_keywords', sa.Integer(), nullable=True),  # Keywords competitor ranks for but we don't
        sa.Column('winning_keywords', sa.Integer(), nullable=True),  # Keywords we rank better for
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['semrush_analysis_id'], ['semrush_analysis.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for semrush_competitors
    op.create_index(op.f('ix_semrush_competitors_semrush_analysis_id'), 'semrush_competitors', ['semrush_analysis_id'], unique=False)
    op.create_index(op.f('ix_semrush_competitors_competitor_domain'), 'semrush_competitors', ['competitor_domain'], unique=False)
    op.create_index(op.f('ix_semrush_competitors_competition_level'), 'semrush_competitors', ['competition_level'], unique=False)
    
    # Create semrush_audit_summary table for site audit summary
    op.create_table(
        'semrush_audit_summary',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('semrush_analysis_id', sa.Integer(), nullable=False),
        sa.Column('crawled_pages', sa.Integer(), nullable=True),
        sa.Column('issues_total', sa.Integer(), nullable=True),
        sa.Column('errors_count', sa.Integer(), nullable=True),
        sa.Column('warnings_count', sa.Integer(), nullable=True),
        sa.Column('notices_count', sa.Integer(), nullable=True),
        sa.Column('healthy_pages', sa.Integer(), nullable=True),
        sa.Column('broken_pages', sa.Integer(), nullable=True),
        sa.Column('redirected_pages', sa.Integer(), nullable=True),
        sa.Column('blocked_pages', sa.Integer(), nullable=True),
        sa.Column('crawl_depth_avg', sa.Float(), nullable=True),
        sa.Column('page_load_time_avg', sa.Float(), nullable=True),  # seconds
        sa.Column('response_time_avg', sa.Float(), nullable=True),  # milliseconds
        sa.Column('page_size_avg', sa.Float(), nullable=True),  # KB
        sa.Column('duplicate_content_ratio', sa.Float(), nullable=True),  # percentage
        sa.Column('thin_content_pages', sa.Integer(), nullable=True),
        sa.Column('missing_meta_titles', sa.Integer(), nullable=True),
        sa.Column('missing_meta_descriptions', sa.Integer(), nullable=True),
        sa.Column('missing_h1_tags', sa.Integer(), nullable=True),
        sa.Column('duplicate_titles', sa.Integer(), nullable=True),
        sa.Column('duplicate_descriptions', sa.Integer(), nullable=True),
        sa.Column('https_implementation_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('mobile_friendliness_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('core_web_vitals_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('structured_data_items', sa.Integer(), nullable=True),
        sa.Column('internal_linking_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('crawlability_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('indexability_score', sa.Integer(), nullable=True),  # 0-100
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['semrush_analysis_id'], ['semrush_analysis.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index for semrush_audit_summary
    op.create_index(op.f('ix_semrush_audit_summary_semrush_analysis_id'), 'semrush_audit_summary', ['semrush_analysis_id'], unique=True)


def downgrade():
    # Drop indexes first
    op.drop_index(op.f('ix_semrush_audit_summary_semrush_analysis_id'), table_name='semrush_audit_summary')
    op.drop_index(op.f('ix_semrush_competitors_competition_level'), table_name='semrush_competitors')
    op.drop_index(op.f('ix_semrush_competitors_competitor_domain'), table_name='semrush_competitors')
    op.drop_index(op.f('ix_semrush_competitors_semrush_analysis_id'), table_name='semrush_competitors')
    op.drop_index(op.f('ix_semrush_backlinks_source_domain_score'), table_name='semrush_backlinks')
    op.drop_index(op.f('ix_semrush_backlinks_toxicity_score'), table_name='semrush_backlinks')
    op.drop_index(op.f('ix_semrush_backlinks_source_domain'), table_name='semrush_backlinks')
    op.drop_index(op.f('ix_semrush_backlinks_semrush_analysis_id'), table_name='semrush_backlinks')
    op.drop_index(op.f('ix_semrush_keywords_traffic_estimate'), table_name='semrush_keywords')
    op.drop_index(op.f('ix_semrush_keywords_search_volume'), table_name='semrush_keywords')
    op.drop_index(op.f('ix_semrush_keywords_position'), table_name='semrush_keywords')
    op.drop_index(op.f('ix_semrush_keywords_keyword'), table_name='semrush_keywords')
    op.drop_index(op.f('ix_semrush_keywords_semrush_analysis_id'), table_name='semrush_keywords')
    op.drop_index(op.f('ix_semrush_technical_issues_fix_priority'), table_name='semrush_technical_issues')
    op.drop_index(op.f('ix_semrush_technical_issues_severity'), table_name='semrush_technical_issues')
    op.drop_index(op.f('ix_semrush_technical_issues_issue_category'), table_name='semrush_technical_issues')
    op.drop_index(op.f('ix_semrush_technical_issues_issue_type'), table_name='semrush_technical_issues')
    op.drop_index(op.f('ix_semrush_technical_issues_semrush_analysis_id'), table_name='semrush_technical_issues')
    op.drop_index(op.f('ix_semrush_analysis_created_at'), table_name='semrush_analysis')
    op.drop_index(op.f('ix_semrush_analysis_domain_authority_score'), table_name='semrush_analysis')
    op.drop_index(op.f('ix_semrush_analysis_site_health_score'), table_name='semrush_analysis')
    op.drop_index(op.f('ix_semrush_analysis_domain'), table_name='semrush_analysis')
    op.drop_index(op.f('ix_semrush_analysis_assessment_id'), table_name='semrush_analysis')
    
    # Drop tables
    op.drop_table('semrush_audit_summary')
    op.drop_table('semrush_competitors')
    op.drop_table('semrush_backlinks')
    op.drop_table('semrush_keywords')
    op.drop_table('semrush_technical_issues')
    op.drop_table('semrush_analysis')