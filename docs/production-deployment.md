# LandGrant Production Deployment Guide

## Overview

This document provides comprehensive instructions for deploying LandGrant to a production environment.

## Prerequisites

### Infrastructure Requirements

- **Compute**: GCP Cloud Run or GKE (recommended minimum: 2 vCPU, 4GB RAM per container)
- **Database**: Cloud SQL PostgreSQL 14+ (minimum: 2 vCPU, 8GB RAM, 100GB SSD)
- **Cache**: Cloud Memorystore Redis 6+ (minimum: 1GB)
- **Storage**: Cloud Storage bucket for documents and uploads
- **DNS**: Custom domain with SSL certificate

### Required Services

- Google Cloud Platform account with billing enabled
- SendGrid account (for email notifications)
- Twilio account (for SMS notifications)
- DocuSign developer account (for e-signatures)
- Mapbox account (for GIS mapping)

## Environment Configuration

### Backend Environment Variables

```bash
# Core Settings
ENVIRONMENT=production
APP_NAME=landgrant-api

# Database (Cloud SQL)
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@/landgrant?host=/cloudsql/PROJECT:REGION:INSTANCE

# Redis (Memorystore)
REDIS_URL=redis://10.x.x.x:6379/0

# Security
JWT_SECRET=<generate-256-bit-secret>
JWT_AUDIENCE=landgrant
JWT_ISSUER=https://api.landgrant.com
SESSION_SECRET=<generate-256-bit-secret>
ENCRYPTION_KEY=<generate-32-char-key>

# GCP
GCP_PROJECT=your-project-id
EVIDENCE_BUCKET=landgrant-evidence-prod

# Email (SendGrid)
SENDGRID_API_KEY=SG.xxxxx
NOTIFICATIONS_MODE=send

# SMS (Twilio)
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_FROM_NUMBER=+1234567890

# E-Sign (DocuSign)
DOCUSIGN_INTEGRATION_KEY=xxxxx
DOCUSIGN_SECRET_KEY=xxxxx
DOCUSIGN_ACCOUNT_ID=xxxxx
DOCUSIGN_BASE_URL=https://na4.docusign.net/restapi

# AI (Vertex AI)
GEMINI_ENABLED=true
GEMINI_MODEL=gemini-1.5-flash-001
GEMINI_LOCATION=us-central1

# Observability
ENABLE_OTLP=true
```

### Frontend Environment Variables

```bash
VITE_API_BASE_URL=https://api.landgrant.com
VITE_MAPBOX_TOKEN=pk.xxxxx
```

## Deployment Steps

### 1. Database Setup

```bash
# Create Cloud SQL instance
gcloud sql instances create landgrant-prod \
  --database-version=POSTGRES_14 \
  --tier=db-custom-2-8192 \
  --region=us-central1 \
  --storage-size=100 \
  --storage-type=SSD

# Create database
gcloud sql databases create landgrant --instance=landgrant-prod

# Create user
gcloud sql users create landgrant \
  --instance=landgrant-prod \
  --password=<secure-password>

# Run migrations
alembic upgrade head
```

### 2. Redis Setup

```bash
# Create Memorystore instance
gcloud redis instances create landgrant-cache \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_6_x
```

### 3. Backend Deployment (Cloud Run)

```bash
# Build container
gcloud builds submit --tag gcr.io/$PROJECT_ID/landgrant-api

# Deploy to Cloud Run
gcloud run deploy landgrant-api \
  --image gcr.io/$PROJECT_ID/landgrant-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "$(cat .env.production | xargs)" \
  --add-cloudsql-instances $PROJECT_ID:us-central1:landgrant-prod \
  --min-instances 2 \
  --max-instances 10 \
  --memory 4Gi \
  --cpu 2
```

### 4. Frontend Deployment

```bash
# Build frontend
cd frontend
npm run build

# Deploy to Cloud Run or Firebase Hosting
gcloud run deploy landgrant-frontend \
  --image gcr.io/$PROJECT_ID/landgrant-frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### 5. Configure DNS and SSL

1. Map custom domain to Cloud Run services
2. Enable managed SSL certificates
3. Configure Cloud Armor for DDoS protection

## Security Checklist

- [ ] All secrets stored in Secret Manager
- [ ] Database connections use SSL
- [ ] Cloud Armor policies configured
- [ ] VPC Service Controls enabled
- [ ] IAM roles follow least privilege
- [ ] Audit logging enabled
- [ ] CORS configured for production domains only
- [ ] Rate limiting enabled on API Gateway

## Monitoring Setup

### Cloud Monitoring

```bash
# Create uptime checks
gcloud monitoring uptime-check-configs create landgrant-api-health \
  --display-name="LandGrant API Health" \
  --http-check-path="/health/live" \
  --monitored-resource-type="uptime_url" \
  --hostname="api.landgrant.com"
```

### Alerting Policies

- API latency > 2s (p95)
- Error rate > 1%
- Database connection pool exhaustion
- Redis memory > 80%

## Backup Strategy

### Database

- Automated daily backups (retained 30 days)
- Point-in-time recovery enabled
- Cross-region backup replication

```bash
gcloud sql instances patch landgrant-prod \
  --backup-start-time=02:00 \
  --enable-point-in-time-recovery
```

### Documents

- Cloud Storage versioning enabled
- Cross-region replication for critical buckets

## Scaling Configuration

### Autoscaling Triggers

- CPU utilization > 60%
- Memory utilization > 70%
- Request latency > 1s

### Load Testing

Before production launch, run load tests:

```bash
cd backend
locust -f scripts/perf_test.py --headless -u 100 -r 20 --run-time 5m \
  --host https://api.landgrant.com
```

## Rollback Procedure

```bash
# List revisions
gcloud run revisions list --service landgrant-api

# Rollback to previous revision
gcloud run services update-traffic landgrant-api \
  --to-revisions=landgrant-api-00001-xxx=100
```

## Health Checks

| Endpoint | Expected | Description |
|----------|----------|-------------|
| `/health/live` | 200 | Basic liveness |
| `/health/invite` | 200 | Invite flow check |
| `/health/esign` | 200 | E-sign service check |

## Support Contacts

- **Infrastructure**: infra@company.com
- **Security**: security@company.com
- **On-call**: PagerDuty integration
