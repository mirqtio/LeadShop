"""
SQLAlchemy models for security assessment data.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base


class SecurityAnalysis(Base):
    """Main security analysis results for an assessment."""
    __tablename__ = "security_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Basic security indicators (matching migration)
    has_https = Column(Boolean, nullable=False, default=False)
    ssl_grade = Column(String(10))
    security_score = Column(Integer, nullable=False, default=0, index=True)
    
    # Certificate details (matching migration)
    ssl_issuer = Column(String(255))
    ssl_expires = Column(DateTime(timezone=True))
    ssl_protocol = Column(String(20))
    ssl_cipher_suite = Column(String(100))
    
    # Analysis metadata (matching migration)
    analysis_timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now())
    analysis_duration_ms = Column(Integer)
    error_message = Column(Text)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Raw data storage (matching migration)
    raw_headers = Column(JSON)
    ssl_certificate_data = Column(JSON)
    
    # Relationships
    assessment = relationship("Assessment", back_populates="security_analysis")
    headers = relationship("SecurityHeader", back_populates="analysis", cascade="all, delete-orphan")
    vulnerabilities = relationship("SecurityVulnerability", back_populates="analysis", cascade="all, delete-orphan")
    cookies = relationship("SecurityCookie", back_populates="analysis", cascade="all, delete-orphan")
    recommendations = relationship("SecurityRecommendation", back_populates="analysis", cascade="all, delete-orphan")


class SecurityHeader(Base):
    """Security headers found during analysis."""
    __tablename__ = "security_headers"
    
    id = Column(Integer, primary_key=True, index=True)
    security_analysis_id = Column(Integer, ForeignKey("security_analysis.id", ondelete="CASCADE"), nullable=False, index=True)
    
    header_name = Column(String(100), nullable=False)
    header_value = Column(Text)
    is_present = Column(Boolean, nullable=False)
    is_secure = Column(Boolean, nullable=False)
    severity = Column(String(20))  # info, low, medium, high
    recommendation = Column(Text)
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    analysis = relationship("SecurityAnalysis", back_populates="headers")


class SecurityVulnerability(Base):
    """Security vulnerabilities detected during analysis."""
    __tablename__ = "security_vulnerabilities"
    
    id = Column(Integer, primary_key=True, index=True)
    security_analysis_id = Column(Integer, ForeignKey("security_analysis.id", ondelete="CASCADE"), nullable=False, index=True)
    
    vulnerability_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)  # critical, high, medium, low
    description = Column(Text, nullable=False)
    evidence = Column(Text)
    recommendation = Column(Text)
    cve_id = Column(String(50))
    owasp_category = Column(String(50))
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    analysis = relationship("SecurityAnalysis", back_populates="vulnerabilities")


class SecurityCookie(Base):
    """Cookie security analysis results."""
    __tablename__ = "security_cookies"
    
    id = Column(Integer, primary_key=True, index=True)
    security_analysis_id = Column(Integer, ForeignKey("security_analysis.id", ondelete="CASCADE"), nullable=False, index=True)
    
    cookie_name = Column(String(255), nullable=False, index=True)
    has_secure_flag = Column(Boolean, nullable=False, default=False)
    has_httponly_flag = Column(Boolean, nullable=False, default=False)
    has_samesite = Column(Boolean, nullable=False, default=False)
    samesite_value = Column(String(20))
    domain = Column(String(255))
    path = Column(String(255))
    expires = Column(DateTime(timezone=True))
    recommendation = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    analysis = relationship("SecurityAnalysis", back_populates="cookies")


class SecurityRecommendation(Base):
    """Security recommendations based on analysis."""
    __tablename__ = "security_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    security_analysis_id = Column(Integer, ForeignKey("security_analysis.id", ondelete="CASCADE"), nullable=False, index=True)
    
    category = Column(String(50), nullable=False, index=True)  # headers, ssl, cookies, content
    priority = Column(Integer, nullable=False, index=True)  # 1-10, higher is more important
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    implementation_guide = Column(Text)
    estimated_effort = Column(String(20))  # low, medium, high
    impact = Column(String(20))  # low, medium, high
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    analysis = relationship("SecurityAnalysis", back_populates="recommendations")