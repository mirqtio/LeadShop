# LeadFactory CLAUDE.md

**Project Context**: Business Lead Assessment & Revenue Optimization System  
**Goal**: Build comprehensive lead processing pipeline with automated assessment and $399 report sales attribution  
**Owner**: Charlie Irwin  

## Quick Start Commands

### Development
- `python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000` - Run development server
- `docker-compose up --build` - Run full stack locally
- `pytest -v --cov=src tests/` - Run tests with coverage
- `alembic upgrade head` - Apply database migrations

### Testing
- Use `/assessment` route on VPS for assessment UI functionality
- Google OAuth integration requires valid Google client credentials
- Health check available at `/health` endpoint
- Simple health check at `/healthz` (no external dependencies)

### Deployment
- GitHub Actions workflow handles VPS deployment automatically
- SSH access: `ssh -i ~/.ssh/leadfactory_deploy leadfactory@165.227.86.250`
- Docker containers: `web` (FastAPI), `db` (PostgreSQL), `redis` (Celery broker)
- Ports: Web (8000), DB (5432), Redis (6379)

## Architecture Overview

**Backend**: FastAPI + SQLAlchemy + PostgreSQL  
**Assessment Pipeline**: Async Celery tasks for PageSpeed, security, SEO, visual analysis  
**Authentication**: Google OAuth 2.0 with JWT tokens  
**File Storage**: AWS S3 integration (configured via environment)  
**Email System**: SendGrid integration with delivery tracking  
**Monitoring**: Prometheus metrics at `/metrics` endpoint  

## Key Files & Components

### Core Application
- `src/main.py` - FastAPI application entry point with health checks
- `src/core/config.py` - Environment-based configuration with validation
- `src/core/database.py` - PostgreSQL connection and session management
- `src/api/v1/router.py` - API route aggregation
- `src/api/v1/assessment_ui.py` - Assessment UI endpoints and Google OAuth

### Assessment System
- `src/assessments/assessment_orchestrator.py` - Main assessment coordination
- `src/assessments/pagespeed_integration.py` - Google PageSpeed API integration
- `src/assessments/security_analysis.py` - Security vulnerability scanning
- `src/assessments/seo_analysis.py` - SEO assessment with scoring
- `src/assessments/visual_analysis.py` - Visual/UI analysis with screenshots
- `src/assessments/semrush_integration.py` - SEMrush domain analysis
- `src/assessments/gbp_integration.py` - Google Business Profile analysis

### Authentication & UI
- `src/auth/google.py` - Google OAuth authentication handler
- `assessment_ui.html` - Frontend UI with Google OAuth integration
- Real API integration with JWT token authentication

### Infrastructure
- `Dockerfile` - Python 3.11 container with Playwright browsers
- `docker-compose.yml` - Multi-container orchestration
- `requirements.txt` - Complete dependency stack for all 13 PRPs
- `.github/workflows/deploy.yml` - Automated VPS deployment

## Environment Configuration

Required environment variables (see `.env`):
- `SECRET_KEY` - JWT signing secret
- `DATABASE_URL` - PostgreSQL connection string
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `GOOGLE_PAGESPEED_API_KEY` - PageSpeed Insights API
- `SEMRUSH_API_KEY` - SEMrush domain analysis
- `OPENAI_API_KEY` - OpenAI integration for insights

VPS deployment configuration:
- `VPS_HOST`, `VPS_USER`, `VPS_PORT` - SSH connection details
- `GITHUB_TOKEN` - GitHub Actions deployment access

## Development Patterns

### Assessment Implementation
Each assessment follows standardized pattern:
```python
async def assess_[component](url: str, business_name: str) -> [Component]Metrics:
    # Implementation with error handling
    return metrics_object

class [Component]Metrics(BaseModel):
    # Pydantic model with validation
```

### API Endpoints
Protected endpoints require Bearer token authentication:
```python
@router.post("/endpoint")
async def endpoint(request: RequestModel, current_user: dict = Depends(get_current_user)):
    # Implementation
```

### Database Models
SQLAlchemy models with async session support:
```python
class Model(Base):
    __tablename__ = "table_name"
    # Fields with proper types and relationships
```

## Testing Strategy

- Unit tests for assessment functions with mock data
- Integration tests for API endpoints with test database
- End-to-end tests for complete assessment pipeline
- Performance tests for sub-200ms API response requirements
- 90%+ coverage target for revenue-critical functionality

## Known Issues & Solutions

### Import Errors
All import mismatches have been resolved through static analysis:
- Assessment orchestrator imports standardized to `assess_*` functions
- Function naming aligned across all assessment modules

### Deployment Health Checks
- `/health` - Full health check with database and Redis validation
- `/healthz` - Simple health check for load balancer probes
- Docker health check configured with 60s startup period

### Authentication Flow
1. Frontend gets Google OAuth token
2. POST to `/api/v1/assessment/auth/google` with token  
3. Backend validates with Google, returns JWT
4. Subsequent requests use `Authorization: Bearer <jwt_token>`

## Revenue Attribution Chain

**Goal**: Track every $399 sale back to source lead and campaign

1. Lead acquisition through data providers
2. Assessment pipeline execution with comprehensive scoring
3. Email campaign delivery with engagement tracking
4. Report generation and delivery
5. Revenue attribution with complete audit trail

## Performance Requirements

- API responses: <200ms target
- Database queries optimized with proper indexing
- Async task processing for assessment pipeline
- Connection pooling for database and Redis
- Caching strategy for repeated assessments

## Quality Standards

- All code passes linting and type checking
- Security best practices with input validation
- Error handling with proper logging and monitoring
- Accessibility standards (WCAG 2.1 AA) for UI components
- Professional documentation and API specifications