# PRP-000: AWS S3 Bucket Setup

## Task ID: PRP-000

## Wave: Foundation Infrastructure

## Business Logic

The LeadFactory system requires secure, scalable file storage for screenshot files, PDF reports, and temporary uploads. This foundational S3 bucket infrastructure enables file operations across the entire application with proper security, lifecycle management, and cost optimization.

## Overview

Create AWS S3 bucket `leadshop-assets` for secure file storage with:
- Proper IAM permissions and bucket policies
- CORS configuration for web application uploads
- Lifecycle rules for cost optimization
- Server-side encryption and access logging
- Integration with Python boto3 client
- Monitoring and cost alerts

## Dependencies

- **External**: AWS Account with appropriate IAM permissions for S3, IAM, and CloudWatch
- **Internal**: None (foundation component)
- **Blockers**: None

## Outcome-Focused Acceptance Criteria

1. **S3 Bucket Operational**: `aws s3 ls` shows `leadshop-assets` bucket exists and `boto3.client('s3').head_bucket(Bucket='leadshop-assets')` succeeds without error
2. **File Upload/Download**: Successfully upload 10MB test file via boto3, generate presigned URL, and verify public access within 30 seconds
3. **CORS Configuration**: Browser-based file upload from localhost:3000 and staging.leadfactory.com domains completes successfully
4. **Security Enforcement**: HTTP requests rejected, unauthorized access attempts fail with 403, public write attempts blocked
5. **Encryption Validation**: All uploaded objects encrypted at rest verified via `aws s3api head-object` command
6. **Cost Monitoring**: CloudWatch dashboard displays bucket usage metrics and alert triggers at $40 threshold
7. **Lifecycle Management**: Test files automatically transition to IA storage class after 30 days as configured
8. **Access Logging**: All S3 operations logged to `leadshop-security-logs` bucket with structured format
9. **Python Integration**: Application successfully loads AWS credentials from environment and performs file operations
10. **Performance**: File operations complete within SLA: upload <30s for 10MB, download <10s, presigned URL generation <1s

## Integration Points

### Infrastructure (Terraform)
- **Location**: `infrastructure/terraform/s3.tf`
- **Dependencies**: AWS provider, IAM module
- **Resources**: S3 bucket, bucket policies, IAM roles, CloudWatch alarms

### Python Application (boto3)  
- **Location**: `src/core/storage/s3_client.py`
- **Dependencies**: boto3, botocore, python-dotenv
- **Functions**: upload_file(), download_file(), generate_presigned_url()

### Web Frontend (CORS)
- **Location**: JavaScript upload components
- **Dependencies**: S3 bucket CORS policy
- **Integration**: Direct browser uploads to S3 with presigned URLs

### Environment Configuration
- **Location**: `.env` files (dev/staging/prod)  
- **Variables**: `AWS_S3_BUCKET_NAME`, `AWS_DEFAULT_REGION`, `AWS_ACCESS_KEY_ID`
- **Security**: AWS credentials via IAM roles (production) or env vars (development)

## Tests to Pass

1. **Infrastructure Tests**: `terraform plan` and `terraform apply` complete without errors in all environments
2. **Bucket Validation**: `aws s3 ls s3://leadshop-assets` returns bucket listing successfully
3. **Python Integration**: `python -c "import boto3; boto3.client('s3').head_bucket(Bucket='leadshop-assets')"` succeeds
4. **Upload/Download Cycle**: Upload 10MB test file, generate presigned URL, download via URL within 30 seconds
5. **CORS Browser Test**: JavaScript file upload from localhost:3000 completes without CORS errors
6. **Security Tests**: Unauthorized access attempts return 403, HTTP requests rejected with proper redirect
7. **Performance Tests**: File operations meet SLA requirements (upload <30s, download <10s, URL gen <1s)  
8. **Cost Monitoring**: CloudWatch alerts trigger correctly when usage exceeds $40 threshold
9. **Lifecycle Tests**: Test objects transition to IA storage class after configured period
10. **Logging Validation**: S3 access logs appear in security bucket with proper format and timing

## Implementation Guide

### Phase 1: Terraform Infrastructure (2 hours)
1. **Verify Dependencies**: Confirm AWS account access and required IAM permissions
2. **Environment Setup**: Configure Terraform backend and AWS provider for target region
3. **Bucket Creation**: Define S3 bucket resource with security defaults and encryption  
4. **IAM Configuration**: Create IAM roles and policies for application access with least privilege
5. **Policy Attachments**: Implement bucket policies for HTTPS-only access and public read restrictions
6. **CORS Setup**: Configure CORS rules for localhost and staging domain access
7. **Lifecycle Rules**: Define automatic transitions to IA storage and deletion policies
8. **Monitoring Setup**: Create CloudWatch alarms and cost monitoring dashboards

### Phase 2: Python Integration (1.5 hours)
1. **boto3 Client**: Create S3 client wrapper with environment-based credential loading
2. **Core Functions**: Implement upload_file(), download_file(), and generate_presigned_url() with error handling
3. **Environment Variables**: Configure AWS credentials and bucket name in application settings
4. **Error Handling**: Add retry logic and proper exception handling for network and permission failures
5. **Testing Integration**: Create test suite for all S3 operations with mock and real AWS testing

### Phase 3: Security & Validation (1.5 hours)
1. **Security Testing**: Validate HTTPS-only policy, unauthorized access blocking, and encryption
2. **Access Logging**: Configure and test S3 access logging to security bucket
3. **Performance Testing**: Benchmark file operations against SLA requirements
4. **CORS Validation**: Test browser-based uploads from approved domains
5. **Cost Monitoring**: Verify CloudWatch metrics and alert configuration

### Phase 4: Documentation & Rollback (1 hour)
1. **Technical Documentation**: Document bucket configuration, IAM policies, and integration patterns
2. **Operational Runbooks**: Create monitoring, alerting, and cost management procedures
3. **Rollback Testing**: Verify infrastructure rollback procedures and data recovery options
4. **Security Documentation**: Document security controls, compliance measures, and audit procedures

## Validation Commands

```bash
# Infrastructure validation
terraform plan -var-file="environments/dev.tfvars"
terraform apply -var-file="environments/dev.tfvars" -auto-approve
aws s3 ls s3://leadshop-assets

# Python integration validation  
python -c "import boto3; print(boto3.client('s3').head_bucket(Bucket='leadshop-assets'))"
python tests/test_s3_integration.py -v

# Security validation
aws s3api get-bucket-policy --bucket leadshop-assets
aws s3api get-bucket-cors --bucket leadshop-assets
aws s3api get-bucket-encryption --bucket leadshop-assets

# Performance validation
python scripts/s3_performance_test.py --file-size=10MB --iterations=5

# Cost monitoring validation
aws cloudwatch get-metric-statistics --namespace AWS/S3 --metric-name BucketSizeBytes --dimensions Name=BucketName,Value=leadshop-assets --start-time 2025-01-23T00:00:00Z --end-time 2025-01-23T23:59:59Z --period 3600 --statistics Maximum
```

## Rollback Strategy

### Emergency Procedures
1. **Security Incident**: Immediately block all public access via `aws s3api put-public-access-block`
2. **Cost Overrun**: Apply emergency lifecycle rules for immediate file cleanup and transition
3. **Infrastructure Failure**: Revert Terraform state to last known good configuration
4. **Application Integration**: Fallback to local file storage with error logging until S3 restored

### Detailed Rollback Steps
1. **Identify Issue**: Determine if rollback needed due to security, cost, performance, or functionality
2. **Isolate Impact**: Block problematic operations while preserving data integrity
3. **Terraform Revert**: `terraform plan -destroy` for full rollback or selective resource removal
4. **Data Recovery**: Use S3 versioning or cross-region backup if data corruption detected
5. **Application Fallback**: Switch to local storage mode with S3 operations disabled
6. **Validation**: Verify rollback success and application functionality without S3 dependency
7. **Documentation**: Record incident details and implement preventive measures

## Success Criteria

1. **Infrastructure Complete**: All Terraform resources created successfully in target AWS account
2. **Integration Working**: Python application successfully uploads, downloads, and manages S3 files
3. **Security Enforced**: All security policies active and validated through penetration testing
4. **Performance Met**: File operations consistently meet SLA requirements under load testing
5. **Monitoring Active**: CloudWatch dashboards operational with cost and usage alerts configured
6. **Documentation Complete**: Technical, operational, and security documentation published
7. **Rollback Tested**: Emergency procedures validated and recovery time objectives met
8. **CI Integration**: S3 operations included in automated testing pipeline with >95% success rate

## Critical Context

### AWS Account Configuration
- **Region**: us-east-1 (primary), configurable via environment variables
- **IAM Requirements**: S3 full access, CloudWatch metrics, IAM policy management
- **Cost Controls**: Monthly budget alerts, lifecycle rules for cost optimization
- **Security Baseline**: Encryption at rest, HTTPS-only access, access logging enabled

### Application Dependencies
- **Python Libraries**: boto3 ≥1.26.0, botocore, python-dotenv
- **Environment Variables**: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION, AWS_S3_BUCKET_NAME
- **Network Requirements**: HTTPS outbound to AWS S3 endpoints
- **Performance Expectations**: 30s upload SLA, 10s download SLA, 1s URL generation SLA

### Integration Patterns
- **Upload Flow**: Generate presigned POST URL → Browser direct upload → Success callback
- **Download Flow**: Generate presigned GET URL → Direct browser access → Content delivery
- **Batch Operations**: Parallel uploads with rate limiting and retry logic
- **Error Handling**: Graceful degradation to local storage with async S3 sync when available