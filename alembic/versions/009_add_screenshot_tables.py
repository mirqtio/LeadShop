"""Add screenshot tables

Revision ID: 009
Revises: 008
Create Date: 2025-01-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    # Create screenshots table
    op.create_table(
        'screenshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('assessment_id', sa.Integer(), nullable=True),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('screenshot_type', sa.String(50), nullable=False),  # desktop, mobile, tablet
        sa.Column('viewport_width', sa.Integer(), nullable=True),
        sa.Column('viewport_height', sa.Integer(), nullable=True),
        sa.Column('device_scale_factor', sa.Float(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('s3_key', sa.String(), nullable=True),
        sa.Column('s3_bucket', sa.String(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('format', sa.String(10), nullable=True),  # png, jpg, webp
        sa.Column('quality', sa.Integer(), nullable=True),
        sa.Column('capture_time_ms', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['assessment_id'], ['assessments.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on assessment_id for faster lookups
    op.create_index(op.f('ix_screenshots_assessment_id'), 'screenshots', ['assessment_id'], unique=False)
    op.create_index(op.f('ix_screenshots_screenshot_type'), 'screenshots', ['screenshot_type'], unique=False)
    op.create_index(op.f('ix_screenshots_created_at'), 'screenshots', ['created_at'], unique=False)
    
    # Create screenshot_annotations table for visual elements
    op.create_table(
        'screenshot_annotations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('screenshot_id', sa.Integer(), nullable=False),
        sa.Column('annotation_type', sa.String(50), nullable=False),  # button, form, navigation, text, image, etc.
        sa.Column('x', sa.Integer(), nullable=False),
        sa.Column('y', sa.Integer(), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('attributes', postgresql.JSON(), nullable=True),  # color, font, size, etc.
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['screenshot_id'], ['screenshots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on screenshot_id
    op.create_index(op.f('ix_screenshot_annotations_screenshot_id'), 'screenshot_annotations', ['screenshot_id'], unique=False)
    op.create_index(op.f('ix_screenshot_annotations_annotation_type'), 'screenshot_annotations', ['annotation_type'], unique=False)
    
    # Create screenshot_comparisons table for A/B testing or before/after
    op.create_table(
        'screenshot_comparisons',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('screenshot_a_id', sa.Integer(), nullable=False),
        sa.Column('screenshot_b_id', sa.Integer(), nullable=False),
        sa.Column('comparison_type', sa.String(50), nullable=False),  # before_after, competitor, variant
        sa.Column('similarity_score', sa.Float(), nullable=True),
        sa.Column('differences', postgresql.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['screenshot_a_id'], ['screenshots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['screenshot_b_id'], ['screenshots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for comparisons
    op.create_index(op.f('ix_screenshot_comparisons_screenshot_a_id'), 'screenshot_comparisons', ['screenshot_a_id'], unique=False)
    op.create_index(op.f('ix_screenshot_comparisons_screenshot_b_id'), 'screenshot_comparisons', ['screenshot_b_id'], unique=False)


def downgrade():
    # Drop indexes first
    op.drop_index(op.f('ix_screenshot_comparisons_screenshot_b_id'), table_name='screenshot_comparisons')
    op.drop_index(op.f('ix_screenshot_comparisons_screenshot_a_id'), table_name='screenshot_comparisons')
    op.drop_index(op.f('ix_screenshot_annotations_annotation_type'), table_name='screenshot_annotations')
    op.drop_index(op.f('ix_screenshot_annotations_screenshot_id'), table_name='screenshot_annotations')
    op.drop_index(op.f('ix_screenshots_created_at'), table_name='screenshots')
    op.drop_index(op.f('ix_screenshots_screenshot_type'), table_name='screenshots')
    op.drop_index(op.f('ix_screenshots_assessment_id'), table_name='screenshots')
    
    # Drop tables
    op.drop_table('screenshot_comparisons')
    op.drop_table('screenshot_annotations')
    op.drop_table('screenshots')