"""
Unit tests for PRP-003 PageSpeed Integration
Tests PageSpeed client, Core Web Vitals extraction, and cost tracking
"""

import pytest
import httpx
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone

from src.assessments.pagespeed import (
    PageSpeedClient, 
    PageSpeedError, 
    CoreWebVitals, 
    PageSpeedResult,
    assess_pagespeed
)


class TestPageSpeedClient:
    """Test PageSpeed API client functionality"""
    
    @pytest.fixture
    def mock_api_response(self):
        """Mock successful PageSpeed API response"""
        return {
            "lighthouseResult": {
                "categories": {
                    "performance": {"score": 0.85},
                    "accessibility": {"score": 0.92},
                    "best-practices": {"score": 0.88},
                    "seo": {"score": 0.95}
                },
                "audits": {
                    "first-contentful-paint": {"numericValue": 1200.5},
                    "largest-contentful-paint": {"numericValue": 2800.3},
                    "cumulative-layout-shift": {"numericValue": 0.12},
                    "total-blocking-time": {"numericValue": 150.0},
                    "interactive": {"numericValue": 3200.8}
                }
            },
            "loadingExperience": {
                "metrics": {
                    "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 75},
                    "FIRST_CONTENTFUL_PAINT_MS": {"percentile": 1800},
                    "LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 3200}
                }
            }
        }
    
    @pytest.fixture
    def pagespeed_client(self):
        """Create PageSpeed client with test API key"""
        with patch.dict('os.environ', {'GOOGLE_PAGESPEED_API_KEY': 'test_key'}):
            return PageSpeedClient(api_key="test_key")
    
    def test_client_initialization(self):
        """Test client initializes with API key"""
        client = PageSpeedClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.COST_PER_CALL == 0.25
        assert client.FREE_QUOTA_DAILY == 25000
    
    def test_client_initialization_no_key(self):
        """Test client fails without API key"""
        with pytest.raises(PageSpeedError, match="API key not configured"):
            PageSpeedClient(api_key=None)
    
    @pytest.mark.asyncio
    async def test_analyze_url_success(self, pagespeed_client, mock_api_response):
        """Test successful URL analysis"""
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        
        with patch.object(pagespeed_client.client, 'get', return_value=mock_response) as mock_get:
            result = await pagespeed_client.analyze_url("https://example.com")
            
            # Verify API call
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == pagespeed_client.BASE_URL
            assert call_args[1]['params']['url'] == "https://example.com"
            assert call_args[1]['params']['strategy'] == "mobile"
            assert call_args[1]['params']['key'] == "test_key"
            
            # Verify result
            assert isinstance(result, PageSpeedResult)
            assert result.url == "https://example.com"
            assert result.strategy == "mobile"
            assert result.cost_cents == 0.25
            
            # Verify Core Web Vitals extraction
            cwv = result.core_web_vitals
            assert cwv.first_contentful_paint == 1200.5
            assert cwv.largest_contentful_paint == 2800.3
            assert cwv.cumulative_layout_shift == 0.12
            assert cwv.total_blocking_time == 150.0
            assert cwv.time_to_interactive == 3200.8
            assert cwv.performance_score == 85  # 0.85 * 100
    
    @pytest.mark.asyncio
    async def test_analyze_url_rate_limited(self, pagespeed_client):
        """Test rate limit error handling"""
        mock_response = Mock()
        mock_response.status_code = 429
        
        with patch.object(pagespeed_client.client, 'get', return_value=mock_response):
            with pytest.raises(PageSpeedError, match="Rate limit exceeded"):
                await pagespeed_client.analyze_url("https://example.com")
    
    @pytest.mark.asyncio
    async def test_analyze_url_invalid_url(self, pagespeed_client):
        """Test invalid URL error handling"""
        mock_response = Mock()
        mock_response.status_code = 400
        
        with patch.object(pagespeed_client.client, 'get', return_value=mock_response):
            with pytest.raises(PageSpeedError, match="Invalid URL"):
                await pagespeed_client.analyze_url("invalid-url")
    
    @pytest.mark.asyncio
    async def test_analyze_url_timeout(self, pagespeed_client):
        """Test timeout error handling"""
        with patch.object(pagespeed_client.client, 'get', side_effect=httpx.TimeoutException("Timeout")):
            with pytest.raises(PageSpeedError, match="timed out after 30 seconds"):
                await pagespeed_client.analyze_url("https://example.com")
    
    @pytest.mark.asyncio
    async def test_mobile_first_analysis(self, pagespeed_client, mock_api_response):
        """Test mobile-first analysis strategy"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_api_response
        
        with patch.object(pagespeed_client.client, 'get', return_value=mock_response) as mock_get:
            results = await pagespeed_client.analyze_mobile_first("https://example.com")
            
            # Should make mobile and desktop calls
            assert mock_get.call_count == 2
            
            # Verify both results returned
            assert "mobile" in results
            assert "desktop" in results
            assert results["mobile"].strategy == "mobile"
            assert results["desktop"].strategy == "desktop"
    
    @pytest.mark.asyncio
    async def test_mobile_first_desktop_fails(self, pagespeed_client, mock_api_response):
        """Test mobile-first when desktop analysis fails"""
        mobile_response = Mock()
        mobile_response.status_code = 200
        mobile_response.json.return_value = mock_api_response
        
        desktop_response = Mock()
        desktop_response.status_code = 500
        desktop_response.text = "Server error"
        
        with patch.object(pagespeed_client.client, 'get', side_effect=[mobile_response, desktop_response]):
            results = await pagespeed_client.analyze_mobile_first("https://example.com")
            
            # Should only have mobile results
            assert "mobile" in results
            assert "desktop" not in results
    
    def test_extract_core_web_vitals(self, pagespeed_client, mock_api_response):
        """Test Core Web Vitals extraction from API response"""
        cwv = pagespeed_client._extract_core_web_vitals(mock_api_response)
        
        assert isinstance(cwv, CoreWebVitals)
        assert cwv.first_contentful_paint == 1200.5
        assert cwv.largest_contentful_paint == 2800.3
        assert cwv.cumulative_layout_shift == 0.12
        assert cwv.total_blocking_time == 150.0
        assert cwv.time_to_interactive == 3200.8
        assert cwv.performance_score == 85
    
    def test_extract_core_web_vitals_missing_data(self, pagespeed_client):
        """Test Core Web Vitals extraction with missing data"""
        incomplete_response = {"lighthouseResult": {"categories": {}, "audits": {}}}
        
        cwv = pagespeed_client._extract_core_web_vitals(incomplete_response)
        
        # Should return empty metrics rather than fail
        assert isinstance(cwv, CoreWebVitals)
        assert cwv.first_contentful_paint is None
        assert cwv.performance_score is None


class TestPageSpeedAssessment:
    """Test high-level PageSpeed assessment function"""
    
    @pytest.mark.asyncio
    async def test_assess_pagespeed_success(self):
        """Test successful PageSpeed assessment"""
        mock_mobile_result = PageSpeedResult(
            url="https://example.com",
            strategy="mobile",
            core_web_vitals=CoreWebVitals(
                first_contentful_paint=1200.5,
                largest_contentful_paint=2800.3,
                performance_score=85
            ),
            lighthouse_result={"categories": {"performance": {"score": 0.85}}},
            analysis_timestamp=datetime.now(timezone.utc).isoformat(),
            analysis_duration_ms=5000,
            cost_cents=0.25
        )
        
        mock_desktop_result = PageSpeedResult(
            url="https://example.com",
            strategy="desktop",
            core_web_vitals=CoreWebVitals(performance_score=90),
            lighthouse_result={"categories": {"performance": {"score": 0.90}}},
            analysis_timestamp=datetime.now(timezone.utc).isoformat(),
            analysis_duration_ms=4500,
            cost_cents=0.25
        )
        
        with patch('src.assessments.pagespeed.get_pagespeed_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.analyze_mobile_first.return_value = {
                "mobile": mock_mobile_result,
                "desktop": mock_desktop_result
            }
            mock_get_client.return_value = mock_client
            
            result = await assess_pagespeed("https://example.com", "Test Company", lead_id=123)
            
            # Verify assessment data structure
            assert result["url"] == "https://example.com"
            assert result["company"] == "Test Company"
            assert result["primary_strategy"] == "mobile"
            assert result["performance_score"] == 85
            assert result["total_cost_cents"] == 0.5  # Mobile + desktop
            assert result["api_calls_made"] == 2
            
            # Verify mobile analysis is primary
            assert "mobile_analysis" in result
            assert "desktop_analysis" in result
            
            # Verify cost records created
            assert len(result["cost_records"]) == 2
            for cost_record in result["cost_records"]:
                assert cost_record.lead_id == 123
                assert cost_record.service_name == "pagespeed"
                assert cost_record.cost_cents == 0.25
    
    @pytest.mark.asyncio
    async def test_assess_pagespeed_error_tracking(self):
        """Test error tracking in PageSpeed assessment"""
        with patch('src.assessments.pagespeed.get_pagespeed_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.analyze_mobile_first.side_effect = PageSpeedError("API failed")
            mock_get_client.return_value = mock_client
            
            with pytest.raises(PageSpeedError):
                await assess_pagespeed("https://example.com", lead_id=123)


class TestCoreWebVitals:
    """Test Core Web Vitals model"""
    
    def test_core_web_vitals_creation(self):
        """Test Core Web Vitals model creation"""
        cwv = CoreWebVitals(
            first_contentful_paint=1200.5,
            largest_contentful_paint=2800.3,
            cumulative_layout_shift=0.12,
            total_blocking_time=150.0,
            time_to_interactive=3200.8,
            performance_score=85
        )
        
        assert cwv.first_contentful_paint == 1200.5
        assert cwv.largest_contentful_paint == 2800.3
        assert cwv.cumulative_layout_shift == 0.12
        assert cwv.total_blocking_time == 150.0
        assert cwv.time_to_interactive == 3200.8
        assert cwv.performance_score == 85
    
    def test_core_web_vitals_optional_fields(self):
        """Test Core Web Vitals with optional fields"""
        cwv = CoreWebVitals()
        
        assert cwv.first_contentful_paint is None
        assert cwv.largest_contentful_paint is None
        assert cwv.cumulative_layout_shift is None
        assert cwv.total_blocking_time is None
        assert cwv.time_to_interactive is None
        assert cwv.performance_score is None


@pytest.mark.integration
class TestPageSpeedIntegration:
    """Integration tests for PageSpeed (requires API key)"""
    
    @pytest.mark.skipif(
        not pytest.config.getoption("--integration"),
        reason="Integration tests require --integration flag"
    )
    @pytest.mark.asyncio
    async def test_real_pagespeed_api(self):
        """Test against real PageSpeed API (requires valid API key)"""
        import os
        api_key = os.getenv("GOOGLE_PAGESPEED_API_KEY")
        
        if not api_key:
            pytest.skip("GOOGLE_PAGESPEED_API_KEY not set")
        
        client = PageSpeedClient(api_key=api_key)
        
        try:
            result = await client.analyze_url("https://web.dev", strategy="mobile")
            
            assert result.url == "https://web.dev"
            assert result.strategy == "mobile"
            assert result.core_web_vitals.performance_score is not None
            assert result.cost_cents == 0.25
            
        finally:
            await client.close()