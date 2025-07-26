"""Add visual analysis tables

Revision ID: 010
Revises: 009
Create Date: 2025-01-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    # Create visual_analysis_results table
    op.create_table(
        'visual_analysis_results',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=False),
        sa.Column('screenshot_id', sa.Integer(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('professional_score', sa.Float(), nullable=False),
        sa.Column('design_score', sa.Float(), nullable=False),
        sa.Column('usability_score', sa.Float(), nullable=False),
        sa.Column('mobile_score', sa.Float(), nullable=False),
        sa.Column('brand_score', sa.Float(), nullable=False),
        sa.Column('trust_score', sa.Float(), nullable=False),
        sa.Column('analysis_version', sa.String(20), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['screenshot_id'], ['screenshots.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_visual_analysis_results_assessment_id'), 'visual_analysis_results', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_visual_analysis_results_screenshot_id'), 'visual_analysis_results', ['screenshot_id'], unique=False)
    op.create_index(op.f('ix_visual_analysis_results_overall_score'), 'visual_analysis_results', ['overall_score'], unique=False)
    op.create_index(op.f('ix_visual_analysis_results_created_at'), 'visual_analysis_results', ['created_at'], unique=False)
    
    # Create visual_rubric_scores table
    op.create_table(
        'visual_rubric_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('visual_analysis_id', sa.Integer(), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),  # professional, design, usability, mobile, brand, trust
        sa.Column('subcategory', sa.String(100), nullable=False),  # specific aspect being scored
        sa.Column('score', sa.Float(), nullable=False),  # 0-10 scale
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('evidence', sa.Text(), nullable=True),
        sa.Column('recommendations', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['visual_analysis_id'], ['visual_analysis_results.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_visual_rubric_scores_visual_analysis_id'), 'visual_rubric_scores', ['visual_analysis_id'], unique=False)
    op.create_index(op.f('ix_visual_rubric_scores_category'), 'visual_rubric_scores', ['category'], unique=False)
    op.create_index(op.f('ix_visual_rubric_scores_score'), 'visual_rubric_scores', ['score'], unique=False)
    
    # Create visual_insights table
    op.create_table(
        'visual_insights',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('visual_analysis_id', sa.Integer(), nullable=False),
        sa.Column('insight_type', sa.String(50), nullable=False),  # issue, opportunity, strength, warning
        sa.Column('severity', sa.String(20), nullable=True),  # critical, high, medium, low
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('impact', sa.Text(), nullable=True),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('evidence_screenshot_id', sa.Integer(), nullable=True),
        sa.Column('evidence_coordinates', postgresql.JSON(), nullable=True),  # {x, y, width, height}
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['visual_analysis_id'], ['visual_analysis_results.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['evidence_screenshot_id'], ['screenshots.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_visual_insights_visual_analysis_id'), 'visual_insights', ['visual_analysis_id'], unique=False)
    op.create_index(op.f('ix_visual_insights_insight_type'), 'visual_insights', ['insight_type'], unique=False)
    op.create_index(op.f('ix_visual_insights_severity'), 'visual_insights', ['severity'], unique=False)
    op.create_index(op.f('ix_visual_insights_category'), 'visual_insights', ['category'], unique=False)
    op.create_index(op.f('ix_visual_insights_priority'), 'visual_insights', ['priority'], unique=False)
    
    # Create ux_metrics table
    op.create_table(
        'ux_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('visual_analysis_id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=True),
        sa.Column('metric_unit', sa.String(20), nullable=True),  # pixels, percentage, seconds, count
        sa.Column('benchmark_value', sa.Float(), nullable=True),
        sa.Column('benchmark_source', sa.String(100), nullable=True),
        sa.Column('performance_rating', sa.String(20), nullable=True),  # excellent, good, needs_improvement, poor
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['visual_analysis_id'], ['visual_analysis_results.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_ux_metrics_visual_analysis_id'), 'ux_metrics', ['visual_analysis_id'], unique=False)
    op.create_index(op.f('ix_ux_metrics_metric_name'), 'ux_metrics', ['metric_name'], unique=False)
    op.create_index(op.f('ix_ux_metrics_performance_rating'), 'ux_metrics', ['performance_rating'], unique=False)
    
    # Create visual_elements table for detected UI components
    op.create_table(
        'visual_elements',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('visual_analysis_id', sa.Integer(), nullable=False),
        sa.Column('screenshot_id', sa.Integer(), nullable=True),
        sa.Column('element_type', sa.String(50), nullable=False),  # cta, navigation, form, hero, footer, etc.
        sa.Column('element_subtype', sa.String(50), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('visibility_score', sa.Float(), nullable=True),
        sa.Column('accessibility_score', sa.Float(), nullable=True),
        sa.Column('location', postgresql.JSON(), nullable=True),  # {x, y, width, height}
        sa.Column('properties', postgresql.JSON(), nullable=True),  # color, size, text, etc.
        sa.Column('issues', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['visual_analysis_id'], ['visual_analysis_results.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['screenshot_id'], ['screenshots.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_visual_elements_visual_analysis_id'), 'visual_elements', ['visual_analysis_id'], unique=False)
    op.create_index(op.f('ix_visual_elements_element_type'), 'visual_elements', ['element_type'], unique=False)
    op.create_index(op.f('ix_visual_elements_quality_score'), 'visual_elements', ['quality_score'], unique=False)
    
    # Create color_analysis table
    op.create_table(
        'color_analysis',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('visual_analysis_id', sa.Integer(), nullable=False),
        sa.Column('primary_color', sa.String(7), nullable=True),  # Hex color
        sa.Column('secondary_color', sa.String(7), nullable=True),
        sa.Column('accent_color', sa.String(7), nullable=True),
        sa.Column('background_color', sa.String(7), nullable=True),
        sa.Column('text_color', sa.String(7), nullable=True),
        sa.Column('color_palette', postgresql.JSON(), nullable=True),  # Array of dominant colors
        sa.Column('contrast_ratio', sa.Float(), nullable=True),
        sa.Column('accessibility_compliant', sa.Boolean(), nullable=True),
        sa.Column('brand_consistency_score', sa.Float(), nullable=True),
        sa.Column('emotional_impact', sa.String(50), nullable=True),  # professional, playful, serious, etc.
        sa.Column('recommendations', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['visual_analysis_id'], ['visual_analysis_results.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index
    op.create_index(op.f('ix_color_analysis_visual_analysis_id'), 'color_analysis', ['visual_analysis_id'], unique=True)


def downgrade():
    # Drop indexes first
    op.drop_index(op.f('ix_color_analysis_visual_analysis_id'), table_name='color_analysis')
    op.drop_index(op.f('ix_visual_elements_quality_score'), table_name='visual_elements')
    op.drop_index(op.f('ix_visual_elements_element_type'), table_name='visual_elements')
    op.drop_index(op.f('ix_visual_elements_visual_analysis_id'), table_name='visual_elements')
    op.drop_index(op.f('ix_ux_metrics_performance_rating'), table_name='ux_metrics')
    op.drop_index(op.f('ix_ux_metrics_metric_name'), table_name='ux_metrics')
    op.drop_index(op.f('ix_ux_metrics_visual_analysis_id'), table_name='ux_metrics')
    op.drop_index(op.f('ix_visual_insights_priority'), table_name='visual_insights')
    op.drop_index(op.f('ix_visual_insights_category'), table_name='visual_insights')
    op.drop_index(op.f('ix_visual_insights_severity'), table_name='visual_insights')
    op.drop_index(op.f('ix_visual_insights_insight_type'), table_name='visual_insights')
    op.drop_index(op.f('ix_visual_insights_visual_analysis_id'), table_name='visual_insights')
    op.drop_index(op.f('ix_visual_rubric_scores_score'), table_name='visual_rubric_scores')
    op.drop_index(op.f('ix_visual_rubric_scores_category'), table_name='visual_rubric_scores')
    op.drop_index(op.f('ix_visual_rubric_scores_visual_analysis_id'), table_name='visual_rubric_scores')
    op.drop_index(op.f('ix_visual_analysis_results_created_at'), table_name='visual_analysis_results')
    op.drop_index(op.f('ix_visual_analysis_results_overall_score'), table_name='visual_analysis_results')
    op.drop_index(op.f('ix_visual_analysis_results_screenshot_id'), table_name='visual_analysis_results')
    op.drop_index(op.f('ix_visual_analysis_results_assessment_id'), table_name='visual_analysis_results')
    
    # Drop tables
    op.drop_table('color_analysis')
    op.drop_table('visual_elements')
    op.drop_table('ux_metrics')
    op.drop_table('visual_insights')
    op.drop_table('visual_rubric_scores')
    op.drop_table('visual_analysis_results')