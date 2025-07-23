PROJECT: LeadFactory - Business Lead Assessment & Revenue Optimization System
GOAL: Build comprehensive lead processing pipeline with automated assessment and $399 report sales attribution
OWNER: Charlie Irwin

CONSTRAINTS:
- Use FastAPI + PostgreSQL for high-performance data processing
- Implement wave-based development approach (Foundation → Assessment → Campaign → Revenue)
- Follow PRP specifications exactly for all 13 product requirements
- Target 0.25-0.6% conversion rates for email campaigns
- All API operations must complete within 200ms
- Use Git best practices - commit every 30 minutes
- 90%+ test coverage for critical revenue attribution logic

DELIVERABLES (13 PRPs):
1. **Foundation Infrastructure**: Lead data model, PostgreSQL schema, FastAPI CRUD endpoints
2. **Assessment Pipeline**: PageSpeed, security, SEO, visual analysis, LLM insights integration
3. **Email Campaign System**: Template management, delivery tracking, engagement metrics
4. **Revenue Attribution**: Complete tracking from lead acquisition through $399 report sales
5. **Performance Optimization**: Sub-200ms API responses, 10K+ record pagination
6. **AWS Integration**: S3 storage, SES email delivery, infrastructure automation
7. **Data Provider Integration**: External lead acquisition and enrichment workflows
8. **Analytics Dashboard**: Campaign performance, conversion tracking, ROI analysis
9. **Report Generation**: Automated $399 assessment reports with PDF generation
10. **Quality Scoring**: Machine learning lead qualification and targeting optimization
11. **User Management**: Authentication, role-based access, team collaboration
12. **API Documentation**: OpenAPI specs, integration guides, webhook endpoints
13. **Deployment Pipeline**: Docker containerization, CI/CD, monitoring infrastructure

SUCCESS CRITERIA:
- Revenue attribution chain tracks every $399 sale back to source lead and campaign
- Email campaigns achieve 0.25-0.6% conversion rates with proper A/B testing
- Assessment pipeline processes leads without data loss across all analysis types
- API performance maintains <200ms response times under 10K+ record loads
- Database queries optimized with proper indexing for email/company lookups
- All PRP acceptance criteria met with comprehensive test coverage

ARCHITECTURE:
- **Backend**: FastAPI with SQLAlchemy ORM and PostgreSQL
- **Database**: PostgreSQL with Alembic migrations and JSON field support
- **Assessment Pipeline**: Async task queue for PageSpeed, security, SEO analysis
- **Email System**: AWS SES integration with delivery tracking
- **File Storage**: AWS S3 for assessment reports and media assets
- **Analytics**: Time-series data for campaign performance and revenue tracking
- **Infrastructure**: Docker containers with AWS deployment
- **Testing**: pytest with >90% coverage for revenue-critical functionality

DEVELOPMENT WORKFLOW:
1. Feature branch creation for each task
2. Regular commits every 30 minutes
3. Code review before merging
4. Automated testing on CI/CD
5. Staging environment for testing
6. Production deployment with monitoring

QUALITY STANDARDS:
- 90%+ test coverage for critical paths
- All code passes linting and type checking
- Performance benchmarks met
- Security best practices followed
- Accessibility standards (WCAG 2.1 AA)
- SEO optimization for public pages