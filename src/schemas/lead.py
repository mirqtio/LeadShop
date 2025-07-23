"""
PRP-001: Pydantic Schemas for Lead Data Model & API
Request/response validation schemas for all CRUD operations
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, validator, ConfigDict


# Base schemas for shared fields
class TimestampMixin(BaseModel):
    """Mixin for created_at and updated_at timestamps"""
    created_at: datetime
    updated_at: Optional[datetime] = None


# Lead Schemas
class LeadBase(BaseModel):
    """Base lead schema with common fields"""
    company: str = Field(..., min_length=1, max_length=255, description="Company name")
    email: EmailStr = Field(..., description="Business email address")
    source: str = Field(..., min_length=1, max_length=100, description="Lead acquisition source")
    
    # Optional contact information
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    url: Optional[str] = Field(None, max_length=512, description="Company website URL")
    
    # Address information
    address: Optional[str] = Field(None, max_length=255, description="Street address")
    city: Optional[str] = Field(None, max_length=100, description="City")
    state: Optional[str] = Field(None, max_length=2, description="State abbreviation")
    zip_code: Optional[str] = Field(None, max_length=10, description="ZIP code")
    
    # Business classification
    naics_code: Optional[str] = Field(None, max_length=10, description="NAICS industry code")
    sic_code: Optional[str] = Field(None, max_length=10, description="SIC industry code")
    employee_size: Optional[int] = Field(None, ge=0, description="Number of employees")
    sales_volume: Optional[float] = Field(None, ge=0, description="Annual sales volume")
    
    # Lead quality
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Lead quality score (0-1)")

    @validator('state')
    def validate_state(cls, v):
        """Validate state is 2-character abbreviation"""
        if v is not None and len(v) != 2:
            raise ValueError('State must be 2-character abbreviation')
        return v.upper() if v else v
    
    @validator('email')
    def validate_email_domain(cls, v):
        """Basic email domain validation"""
        if '@' not in str(v):
            raise ValueError('Invalid email format')
        return str(v).lower()


class LeadCreate(LeadBase):
    """Schema for creating new leads"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "company": "Acme Corporation",
                "email": "contact@acme.com",
                "source": "data_provider",
                "phone": "555-123-4567",
                "url": "https://acme.com",
                "city": "San Francisco",
                "state": "CA",
                "zip_code": "94105",
                "employee_size": 50,
                "quality_score": 0.85
            }
        }
    )


class LeadUpdate(BaseModel):
    """Schema for updating existing leads"""
    company: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    url: Optional[str] = Field(None, max_length=512)
    address: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=2)
    zip_code: Optional[str] = Field(None, max_length=10)
    naics_code: Optional[str] = Field(None, max_length=10)
    sic_code: Optional[str] = Field(None, max_length=10)
    employee_size: Optional[int] = Field(None, ge=0)
    sales_volume: Optional[float] = Field(None, ge=0)
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)

    @validator('state')
    def validate_state(cls, v):
        if v is not None and len(v) != 2:
            raise ValueError('State must be 2-character abbreviation')
        return v.upper() if v else v


class LeadResponse(LeadBase, TimestampMixin):
    """Schema for lead API responses"""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


class LeadWithAssessments(LeadResponse):
    """Schema for lead response with assessment history"""
    assessments: List["AssessmentResponse"] = []
    sales: List["SaleResponse"] = []


# Assessment Schemas
class AssessmentBase(BaseModel):
    """Base assessment schema"""
    lead_id: int = Field(..., description="Associated lead ID")
    
    # Technical scores (0-100)
    pagespeed_score: Optional[int] = Field(None, ge=0, le=100, description="PageSpeed score")
    security_score: Optional[int] = Field(None, ge=0, le=100, description="Security score")
    mobile_score: Optional[int] = Field(None, ge=0, le=100, description="Mobile score")
    seo_score: Optional[int] = Field(None, ge=0, le=100, description="SEO score")
    
    # JSON data fields
    pagespeed_data: Optional[Dict[str, Any]] = Field(None, description="PageSpeed raw data")
    security_headers: Optional[Dict[str, Any]] = Field(None, description="Security headers analysis")
    gbp_data: Optional[Dict[str, Any]] = Field(None, description="Google Business Profile data")
    semrush_data: Optional[Dict[str, Any]] = Field(None, description="SEMrush analysis data")
    visual_analysis: Optional[Dict[str, Any]] = Field(None, description="Visual analysis results")
    llm_insights: Optional[Dict[str, Any]] = Field(None, description="LLM-generated insights")
    
    # Status and metadata
    status: str = Field("pending", max_length=50, description="Assessment status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    assessment_duration_ms: Optional[int] = Field(None, ge=0, description="Processing duration")
    total_score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Composite score")

    @validator('status')
    def validate_status(cls, v):
        """Validate assessment status values"""
        allowed_statuses = ['pending', 'in_progress', 'completed', 'failed']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v


class AssessmentCreate(AssessmentBase):
    """Schema for creating new assessments"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "lead_id": 1,
                "pagespeed_score": 85,
                "security_score": 92,
                "mobile_score": 78,
                "seo_score": 88,
                "status": "completed",
                "total_score": 85.75
            }
        }
    )


class AssessmentUpdate(BaseModel):
    """Schema for updating assessments"""
    pagespeed_score: Optional[int] = Field(None, ge=0, le=100)
    security_score: Optional[int] = Field(None, ge=0, le=100)
    mobile_score: Optional[int] = Field(None, ge=0, le=100)
    seo_score: Optional[int] = Field(None, ge=0, le=100)
    pagespeed_data: Optional[Dict[str, Any]] = None
    security_headers: Optional[Dict[str, Any]] = None
    gbp_data: Optional[Dict[str, Any]] = None
    semrush_data: Optional[Dict[str, Any]] = None
    visual_analysis: Optional[Dict[str, Any]] = None
    llm_insights: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, max_length=50)
    error_message: Optional[str] = None
    assessment_duration_ms: Optional[int] = Field(None, ge=0)
    total_score: Optional[float] = Field(None, ge=0.0, le=100.0)


class AssessmentResponse(AssessmentBase, TimestampMixin):
    """Schema for assessment API responses"""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


# Campaign Schemas
class CampaignBase(BaseModel):
    """Base campaign schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Campaign name")
    subject_line: str = Field(..., min_length=1, max_length=255, description="Email subject line")
    send_date: Optional[datetime] = Field(None, description="Scheduled send date")
    
    # Email metrics
    leads_targeted: int = Field(0, ge=0, description="Number of leads targeted")
    emails_sent: int = Field(0, ge=0, description="Number of emails sent")
    emails_delivered: int = Field(0, ge=0, description="Number of emails delivered")
    emails_opened: int = Field(0, ge=0, description="Number of emails opened")
    emails_clicked: int = Field(0, ge=0, description="Number of emails clicked")
    
    # Revenue metrics
    leads_converted: int = Field(0, ge=0, description="Number of leads converted")
    revenue_generated: float = Field(0.0, ge=0.0, description="Total revenue generated")
    
    status: str = Field("draft", max_length=50, description="Campaign status")

    @validator('status')
    def validate_campaign_status(cls, v):
        """Validate campaign status values"""
        allowed_statuses = ['draft', 'scheduled', 'sending', 'sent', 'paused', 'completed']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v

    @validator('emails_delivered')
    def validate_delivery_count(cls, v, values):
        """Ensure delivered emails don't exceed sent emails"""
        if 'emails_sent' in values and v > values['emails_sent']:
            raise ValueError('Delivered emails cannot exceed sent emails')
        return v


class CampaignCreate(CampaignBase):
    """Schema for creating new campaigns"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Q1 2025 Website Assessment Campaign",
                "subject_line": "Free Website Performance Report - $399 Value",
                "leads_targeted": 1000,
                "status": "draft"
            }
        }
    )


class CampaignUpdate(BaseModel):
    """Schema for updating campaigns"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    subject_line: Optional[str] = Field(None, min_length=1, max_length=255)
    send_date: Optional[datetime] = None
    emails_sent: Optional[int] = Field(None, ge=0)
    emails_delivered: Optional[int] = Field(None, ge=0)
    emails_opened: Optional[int] = Field(None, ge=0)
    emails_clicked: Optional[int] = Field(None, ge=0)
    leads_converted: Optional[int] = Field(None, ge=0)
    revenue_generated: Optional[float] = Field(None, ge=0.0)
    status: Optional[str] = Field(None, max_length=50)


class CampaignResponse(CampaignBase, TimestampMixin):
    """Schema for campaign API responses with calculated metrics"""
    id: int
    open_rate: float = Field(..., description="Email open rate (0-1)")
    click_rate: float = Field(..., description="Email click rate (0-1)")
    conversion_rate: float = Field(..., description="Lead conversion rate (0-1)")
    revenue_per_lead: float = Field(..., description="Revenue per targeted lead")
    
    model_config = ConfigDict(from_attributes=True)


# Sale Schemas
class SaleBase(BaseModel):
    """Base sale schema"""
    lead_id: int = Field(..., description="Associated lead ID")
    campaign_id: Optional[int] = Field(None, description="Associated campaign ID")
    amount: float = Field(..., ge=0.0, description="Sale amount")
    payment_method: Optional[str] = Field(None, max_length=50, description="Payment method")
    transaction_id: Optional[str] = Field(None, max_length=100, description="Transaction ID")
    attribution_source: str = Field(..., max_length=100, description="Attribution source")
    status: str = Field("completed", max_length=50, description="Sale status")

    @validator('status')
    def validate_sale_status(cls, v):
        """Validate sale status values"""
        allowed_statuses = ['pending', 'completed', 'refunded', 'failed']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v


class SaleCreate(SaleBase):
    """Schema for creating new sales"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "lead_id": 1,
                "campaign_id": 1,
                "amount": 399.00,
                "payment_method": "stripe",
                "transaction_id": "txn_1234567890",
                "attribution_source": "email_campaign"
            }
        }
    )


class SaleUpdate(BaseModel):
    """Schema for updating sales"""
    amount: Optional[float] = Field(None, ge=0.0)
    payment_method: Optional[str] = Field(None, max_length=50)
    transaction_id: Optional[str] = Field(None, max_length=100)
    attribution_source: Optional[str] = Field(None, max_length=100)
    status: Optional[str] = Field(None, max_length=50)


class SaleResponse(SaleBase, TimestampMixin):
    """Schema for sale API responses"""
    id: int
    
    model_config = ConfigDict(from_attributes=True)


# List response schemas for pagination
class LeadListResponse(BaseModel):
    """Schema for paginated lead list responses"""
    items: List[LeadResponse]
    total: int
    offset: int
    limit: int
    has_more: bool


class AssessmentListResponse(BaseModel):
    """Schema for paginated assessment list responses"""
    items: List[AssessmentResponse]
    total: int
    offset: int
    limit: int
    has_more: bool


class CampaignListResponse(BaseModel):
    """Schema for paginated campaign list responses"""
    items: List[CampaignResponse]
    total: int
    offset: int
    limit: int
    has_more: bool


# Forward references resolution
LeadWithAssessments.model_rebuild()
CampaignResponse.model_rebuild()
AssessmentResponse.model_rebuild()
SaleResponse.model_rebuild()