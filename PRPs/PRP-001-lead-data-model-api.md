# PRP-001: Lead Data Model & API

## Task ID: PRP-001

## Wave: Foundation Infrastructure

## Business Logic

The LeadFactory system requires a comprehensive data model for managing business leads acquired from data providers, storing assessment pipeline results, tracking email campaigns, and attributing revenue from $399 report sales. This foundational database schema and API layer enables all lead processing, assessment orchestration, and revenue optimization workflows across the entire application.

## Overview

Implement PostgreSQL database schema and FastAPI CRUD endpoints for:
- Business lead management with complete directory data (company, contact, classification)
- Assessment result storage for all pipeline outputs (PageSpeed, security, SEO, visual, AI analysis)
- Campaign tracking with email delivery metrics and engagement data
- Revenue attribution chain from lead acquisition through sale conversion
- Performance optimization with proper indexing and query patterns

## Dependencies

- **External**: PostgreSQL database server, FastAPI framework, SQLAlchemy ORM
- **Internal**: PRP-000 (AWS S3 Bucket Setup) for report file storage integration
- **Blockers**: None

## Outcome-Focused Acceptance Criteria

1. **Database Schema Operational**: `psql -c "\dt"` shows all four tables (leads, assessments, campaigns, sales) with proper relationships and foreign key constraints
2. **Lead CRUD Operations**: Successfully create lead via POST /api/v1/leads/, retrieve with GET, update via PUT, delete with proper cascade handling
3. **Email Uniqueness Enforced**: Duplicate email creation returns 400 error with "already exists" message, database constraint prevents duplicate entries
4. **Assessment Pipeline Integration**: Store complete assessment results including PageSpeed data, security headers, GBP data, SEMrush scores, visual analysis, and LLM insights in JSON fields
5. **Campaign Performance Tracking**: Record email metrics (sent, delivered, opened, clicked) and calculate conversion rates for 0.25-0.6% target optimization
6. **Revenue Attribution Chain**: Link lead → assessment → campaign → sale with complete transaction tracking and $399 report sales attribution
7. **API Performance**: All CRUD operations complete within 200ms for single records, list operations handle 10K+ records with pagination
8. **Query Optimization**: Database indexes ensure <100ms query performance for email lookups, company searches, and campaign filtering
9. **Data Validation**: Pydantic models validate all input data, proper HTTP status codes for errors, comprehensive API documentation via /docs
10. **Migration Reliability**: Alembic migrations run successfully with rollback capability, database schema matches SQLAlchemy model definitions exactly

## Integration Points

### Database Layer (SQLAlchemy Models)
- **Location**: `src/models/lead_models.py`, `src/models/assessment_models.py`
- **Dependencies**: SQLAlchemy, PostgreSQL, Alembic migrations
- **Resources**: Four primary tables with proper relationships and constraints

### FastAPI Application (CRUD Endpoints)
- **Location**: `src/api/v1/leads.py`, `src/api/v1/assessments.py`, `src/api/v1/campaigns.py`
- **Dependencies**: FastAPI, Pydantic, SQLModel for validation
- **Functions**: Full CRUD operations with proper error handling and documentation

## Implementation Requirements

### Database Schema Implementation

**SQLAlchemy Models with Type Safety**:
```python
class Lead(Base):
    __tablename__ = "leads"
    
    # Primary key and metadata
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
    
    # Business information
    company: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    url: Mapped[Optional[str]] = mapped_column(String(512))
    
    # Address information
    address: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(2))
    zip_code: Mapped[Optional[str]] = mapped_column(String(10))
    
    # Business classification
    naics_code: Mapped[Optional[str]] = mapped_column(String(10))
    sic_code: Mapped[Optional[str]] = mapped_column(String(10))
    employee_size: Mapped[Optional[int]]
    sales_volume: Mapped[Optional[float]]
    
    # Lead metadata
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    quality_score: Mapped[Optional[float]]
    
    # Relationships
    assessments: Mapped[List["Assessment"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )
    sales: Mapped[List["Sale"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan"
    )

class Assessment(Base):
    __tablename__ = "assessments"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Technical metrics
    pagespeed_score: Mapped[Optional[int]]
    security_score: Mapped[Optional[int]]
    mobile_score: Mapped[Optional[int]]
    seo_score: Mapped[Optional[int]]
    
    # Assessment results (JSON fields)
    pagespeed_data: Mapped[Optional[dict]] = mapped_column(JSON)
    security_headers: Mapped[Optional[dict]] = mapped_column(JSON)
    gbp_data: Mapped[Optional[dict]] = mapped_column(JSON)
    semrush_data: Mapped[Optional[dict]] = mapped_column(JSON)
    visual_analysis: Mapped[Optional[dict]] = mapped_column(JSON)
    llm_insights: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Assessment metadata
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relationships
    lead: Mapped["Lead"] = relationship(back_populates="assessments")

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Campaign metadata
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_line: Mapped[str] = mapped_column(String(255), nullable=False)
    send_date: Mapped[Optional[datetime]]
    
    # Performance metrics
    leads_targeted: Mapped[int] = mapped_column(default=0)
    emails_sent: Mapped[int] = mapped_column(default=0)
    emails_delivered: Mapped[int] = mapped_column(default=0)
    emails_opened: Mapped[int] = mapped_column(default=0)
    emails_clicked: Mapped[int] = mapped_column(default=0)
    
    # Revenue tracking
    leads_converted: Mapped[int] = mapped_column(default=0)
    revenue_generated: Mapped[float] = mapped_column(default=0.0)
    
    # Relationships
    sales: Mapped[List["Sale"]] = relationship(back_populates="campaign")

class Sale(Base):
    __tablename__ = "sales"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), nullable=False)
    campaign_id: Mapped[Optional[int]] = mapped_column(ForeignKey("campaigns.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    
    # Transaction details
    amount: Mapped[float] = mapped_column(nullable=False)
    payment_method: Mapped[str] = mapped_column(String(50))
    transaction_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Attribution
    attribution_source: Mapped[str] = mapped_column(String(100))
    
    # Relationships
    lead: Mapped["Lead"] = relationship(back_populates="sales")
    campaign: Mapped[Optional["Campaign"]] = relationship(back_populates="sales")
```

### FastAPI Endpoint Implementation

**Lead CRUD Operations**:
```python
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlmodel import select

router = APIRouter(prefix="/api/v1/leads", tags=["leads"])

@router.post("/", response_model=LeadResponse)
def create_lead(
    *, session: SessionDep, lead: LeadCreate
) -> Lead:
    """Create a new business lead with validation."""
    # Check for duplicate email
    existing = session.exec(select(Lead).where(Lead.email == lead.email)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Lead with this email already exists")
    
    db_lead = Lead.model_validate(lead)
    session.add(db_lead)
    session.commit()
    session.refresh(db_lead)
    return db_lead

@router.get("/{lead_id}", response_model=LeadWithAssessments)
def get_lead(
    *, session: SessionDep, lead_id: int
) -> Lead:
    """Retrieve lead with assessment history."""
    lead = session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    *, session: SessionDep, lead_id: int, lead_update: LeadUpdate
) -> Lead:
    """Update lead information."""
    lead = session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead_data = lead_update.model_dump(exclude_unset=True)
    for field, value in lead_data.items():
        setattr(lead, field, value)
    
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead

@router.get("/", response_model=List[LeadResponse])
def list_leads(
    *,
    session: SessionDep,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    source: Optional[str] = None,
    min_quality_score: Optional[float] = None
) -> List[Lead]:
    """List leads with filtering and pagination."""
    query = select(Lead)
    
    if source:
        query = query.where(Lead.source == source)
    if min_quality_score:
        query = query.where(Lead.quality_score >= min_quality_score)
    
    query = query.offset(offset).limit(limit)
    leads = session.exec(query).all()
    return leads

@router.delete("/{lead_id}")
def delete_lead(
    *, session: SessionDep, lead_id: int
) -> dict:
    """Soft delete lead with cascade handling."""
    lead = session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    session.delete(lead)
    session.commit()
    return {"ok": True}
```

**Assessment Operations**:
```python
@router.post("/api/v1/assessments/", response_model=AssessmentResponse)
def create_assessment(
    *, session: SessionDep, assessment: AssessmentCreate
) -> Assessment:
    """Store pipeline assessment results."""
    # Verify lead exists
    lead = session.get(Lead, assessment.lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    db_assessment = Assessment.model_validate(assessment)
    session.add(db_assessment)
    session.commit()
    session.refresh(db_assessment)
    return db_assessment

@router.get("/api/v1/assessments/{lead_id}", response_model=List[AssessmentResponse])
def get_lead_assessments(
    *, session: SessionDep, lead_id: int
) -> List[Assessment]:
    """Retrieve all assessments for a lead."""
    lead = session.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    assessments = session.exec(
        select(Assessment).where(Assessment.lead_id == lead_id)
    ).all()
    return assessments
```

### Database Migration Strategy

**Alembic Migration Files**:
```python
# migrations/versions/001_create_lead_tables.py
def upgrade():
    # Create leads table
    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('company', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(20)),
        sa.Column('url', sa.String(512)),
        sa.Column('address', sa.String(255)),
        sa.Column('city', sa.String(100)),
        sa.Column('state', sa.String(2)),
        sa.Column('zip_code', sa.String(10)),
        sa.Column('naics_code', sa.String(10)),
        sa.Column('sic_code', sa.String(10)),
        sa.Column('employee_size', sa.Integer()),
        sa.Column('sales_volume', sa.Float()),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('quality_score', sa.Float()),
    )
    
    # Create indexes
    op.create_index('ix_leads_email', 'leads', ['email'], unique=True)
    op.create_index('ix_leads_company', 'leads', ['company'])
    op.create_index('ix_leads_source', 'leads', ['source'])
    
    # Create assessments table
    op.create_table(
        'assessments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('pagespeed_score', sa.Integer()),
        sa.Column('security_score', sa.Integer()),
        sa.Column('mobile_score', sa.Integer()),
        sa.Column('seo_score', sa.Integer()),
        sa.Column('pagespeed_data', sa.JSON()),
        sa.Column('security_headers', sa.JSON()),
        sa.Column('gbp_data', sa.JSON()),
        sa.Column('semrush_data', sa.JSON()),
        sa.Column('visual_analysis', sa.JSON()),
        sa.Column('llm_insights', sa.JSON()),
        sa.Column('status', sa.String(50), default='pending'),
        sa.Column('error_message', sa.Text()),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id']),
    )
    
    # Create campaigns and sales tables
    op.create_table(
        'campaigns',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subject_line', sa.String(255), nullable=False),
        sa.Column('send_date', sa.DateTime()),
        sa.Column('leads_targeted', sa.Integer(), default=0),
        sa.Column('emails_sent', sa.Integer(), default=0),
        sa.Column('emails_delivered', sa.Integer(), default=0),
        sa.Column('emails_opened', sa.Integer(), default=0),
        sa.Column('emails_clicked', sa.Integer(), default=0),
        sa.Column('leads_converted', sa.Integer(), default=0),
        sa.Column('revenue_generated', sa.Float(), default=0.0),
    )
    
    op.create_table(
        'sales',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('lead_id', sa.Integer(), nullable=False),
        sa.Column('campaign_id', sa.Integer()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('payment_method', sa.String(50)),
        sa.Column('transaction_id', sa.String(100)),
        sa.Column('attribution_source', sa.String(100)),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id']),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id']),
    )

def downgrade():
    op.drop_table('sales')
    op.drop_table('campaigns')
    op.drop_table('assessments')
    op.drop_table('leads')
```

## Testing Requirements

### Unit Testing Strategy

**Model Validation Tests**:
```python
def test_lead_creation_with_required_fields():
    """Test lead creation with minimum required fields."""
    lead = Lead(
        company="Test Company",
        email="test@example.com",
        source="data_provider"
    )
    assert lead.company == "Test Company"
    assert lead.email == "test@example.com"
    assert lead.source == "data_provider"

def test_lead_email_uniqueness():
    """Test that duplicate emails are prevented."""
    # Implementation with database session and constraint testing

def test_assessment_lead_relationship():
    """Test assessment-lead foreign key relationship."""
    # Implementation with relationship testing
```

**API Integration Tests**:
```python
def test_create_lead_endpoint(client: TestClient):
    """Test lead creation via API endpoint."""
    lead_data = {
        "company": "Test Company",
        "email": "test@example.com",
        "source": "api_test"
    }
    response = client.post("/api/v1/leads/", json=lead_data)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"

def test_get_lead_with_assessments(client: TestClient):
    """Test retrieving lead with assessment history."""
    # Implementation with related data testing

def test_list_leads_with_filters(client: TestClient):
    """Test lead listing with source and quality filters."""
    # Implementation with pagination and filtering testing
```

**Revenue Attribution Tests**:
```python
def test_sale_attribution_chain():
    """Test complete attribution from lead to sale."""
    # Create lead, assessment, campaign, sale
    # Verify attribution chain integrity

def test_campaign_roi_calculation():
    """Test campaign ROI metrics calculation."""
    # Implementation with revenue tracking validation
```

## Acceptance Criteria

**Functional Requirements**:
- ✅ Lead CRUD operations with data validation and duplicate prevention
- ✅ Assessment result storage supporting all pipeline output formats
- ✅ Campaign creation and performance tracking with email metrics
- ✅ Revenue attribution chain from lead acquisition through sale conversion
- ✅ API pagination, filtering, and error handling with proper HTTP status codes
- ✅ Database schema with proper relationships, constraints, and indexes

**Performance Requirements**:
- ✅ API response times <200ms for single record operations
- ✅ List operations handle 10K+ records with pagination
- ✅ Database queries optimized with appropriate indexes
- ✅ JSON field queries performant for assessment data filtering

**Quality Requirements**:
- ✅ Unit test coverage ≥90% for models and business logic
- ✅ Integration test coverage ≥80% for API endpoints
- ✅ Database migration rollback capability for all schema changes
- ✅ API documentation auto-generated with OpenAPI/Swagger

**Business Requirements**:
- ✅ Support for 0.25-0.6% conversion rate tracking and optimization
- ✅ Revenue attribution accuracy for $399 report sales
- ✅ Lead quality scoring integration for campaign targeting
- ✅ Assessment pipeline result storage without data loss

## Definition of Done

- [ ] PostgreSQL schema implemented with all entities and relationships
- [ ] FastAPI CRUD endpoints implemented with proper validation
- [ ] Database migrations created with upgrade/downgrade capability
- [ ] Unit tests written for all models with ≥90% coverage
- [ ] Integration tests written for all API endpoints with ≥80% coverage
- [ ] API documentation generated and accessible via /docs endpoint
- [ ] Revenue attribution chain validated with end-to-end testing
- [ ] Performance benchmarks met for API response times
- [ ] Code review completed with security and architecture validation
- [ ] Documentation updated with API usage examples and business context


