
# FastAPI + PostgreSQL CI/CD on On-Prem Kubernetes

A production-grade DevOps CI/CD workflow for a FastAPI application with PostgreSQL, deployed on an on-premises Kubernetes cluster. Features separate staging (CI/CD) and production (CD with canary deployment) environments with automated testing, security scanning, and database migrations.

## Architecture Overview
```
GitHub Repository
       ↓
   Jenkinsfile (CI/CD Pipeline)
       ↓
   ┌───────────────────────────────────┐
   │  Kubernetes Cluster (On-Prem)     │
   │                                   │
   │  ┌─────────────────────────────┐ │
   │  │  Namespace: staging         │ │
   │  │  - FastAPI Deployment       │ │
   │  │  - Service (ClusterIP)      │ │
   │  │  - PostgreSQL StatefulSet   │ │
   │  └─────────────────────────────┘ │
   │                                   │
   │  ┌─────────────────────────────┐ │
   │  │  Namespace: prod            │ │
   │  │  - FastAPI Deployment       │ │
   │  │  - FastAPI Canary Deploy    │ │
   │  │  - Service (with routing)   │ │
   │  │  - PostgreSQL StatefulSet   │ │
   │  └─────────────────────────────┘ │
   └───────────────────────────────────┘
```

## Repository Structure
```
fastapi_postgres_app/
├── app/
│   ├── main.py                         # FastAPI application entry point
│   ├── models.py                       # SQLAlchemy ORM models
│   ├── database.py                     # Database connection configuration
│   └── crud.py                         # CRUD operations
├── migrations/
│   └── 001_create_users_table.sql      # Database schema migration
├── k8s/
│   ├── postgres-statefulset.yaml       # PostgreSQL StatefulSet manifest
│   ├── app-deployment.yaml             # FastAPI Deployment manifest
│   └── app-service.yaml                # Kubernetes Service manifest
├── Dockerfile                           # Container image definition
├── requirements.txt                     # Python dependencies
└── Jenkinsfile                          # CI/CD pipeline definition
```

## CI/CD Pipeline Architecture

### Staging Pipeline (Full CI/CD)

**Trigger:** Automatic on push to `Staging` branch

**Pipeline Stages:**
```
┌─────────────────────────────────────────────────────────────────────┐
│ STAGING PIPELINE (CI/CD)                                            │
└─────────────────────────────────────────────────────────────────────┘

1. Checkout & Stash
   └─> Clone repository and stash source code

2. Validate Application
   └─> Python syntax check with compileall
   └─> Dependency installation test

3. Build, Scan & Push
   ├─> Build container image with Kaniko
   ├─> Save image as tar for scanning
   ├─> Security scan with Trivy (HIGH/CRITICAL)
   └─> Push validated image to Nexus registry

4. Database Migration (Conditional)
   ├─> Detect changes in migrations/ directory
   ├─> Compare with previous commit
   └─> Apply SQL migrations if changes detected

5. Deploy to Staging
   ├─> Create/update Nexus image pull secret
   ├─> Update deployment with new image tag
   └─> Wait for rollout completion
```

**Image Tagging:** `latest-${BUILD_NUMBER}` (e.g., `latest-42`)

### Production Pipeline (CD Only with Canary)

**Trigger:** Manual promotion from staging

**Pipeline Stages:**
```
┌─────────────────────────────────────────────────────────────────────┐
│ PRODUCTION PIPELINE (CD Only - NO BUILD)                            │
└─────────────────────────────────────────────────────────────────────┘

1. Checkout & Stash
   └─> Clone repository for migration files

2. Database Migration (Conditional + Manual Approval)
   ├─> Detect changes in migrations/ directory
   ├─> ⏸️  Manual approval required if changes detected
   └─> Apply SQL migrations to production DB

3. Deploy Canary (10% Traffic)
   ├─> Query Nexus for latest staging image tag
   ├─> Deploy to fastapi-app-canary deployment
   ├─> Scale canary to 1 replica
   └─> Monitor canary health

4. Promote to Production (Manual Approval)
   ├─> ⏸️  Manual approval required (30-minute timeout)
   ├─> Update main fastapi-app deployment
   ├─> Wait for rollout completion
   └─> Scale canary to 0 replicas
   └─> On failure/abort: Automatic canary rollback
```

**Image Source:** Pre-built images from Nexus (promoted from staging)

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Application** | FastAPI | REST API framework |
| **Database** | PostgreSQL 15 | Relational database with StatefulSet |
| **ORM** | SQLAlchemy | Database models and queries |
| **CI/CD** | Jenkins | Orchestration and automation |
| **Container Build** | Kaniko | Docker image building in Kubernetes |
| **Security Scanning** | Trivy | Vulnerability scanning |
| **Registry** | Nexus | Private Docker registry |
| **Orchestration** | Kubernetes | Container orchestration (on-prem) |

## Key Features

### 1. Build Once, Deploy Many
- Images built and tested in staging
- Same immutable artifact deployed to production
- No recompilation in production pipeline

### 2. Security-First Approach
- Pre-push vulnerability scanning with Trivy
- Blocks deployment on HIGH/CRITICAL vulnerabilities
- Image pull secrets managed securely

### 3. Database Migration Safety
- Automated detection of schema changes
- Conditional execution (only when needed)
- Manual approval required in production
- Rollback-ready with version control

### 4. Canary Deployment Strategy
- 10% traffic to canary deployment first
- Manual validation period (30 minutes)
- Automatic rollback on failure or timeout
- Zero-downtime deployments

### 5. GitOps-Ready
- Infrastructure as Code (IaC) in k8s/ directory
- Declarative Kubernetes manifests
- Version-controlled pipeline definitions

## Environment Configuration

### Staging Environment
- **Namespace:** `staging`
- **Registry:** `10.10.70.84:30051`
- **Image Tag Pattern:** `latest-${BUILD_NUMBER}`
- **DB Host:** `postgres-0.postgres.staging.svc.cluster.local`
- **Deployment:** Automatic on merge

### Production Environment
- **Namespace:** `prod`
- **Registry:** `10.10.70.84:30051`
- **Image Source:** Promoted from staging
- **DB Host:** `postgres-0.postgres.prod.svc.cluster.local`
- **Deployment:** Manual approval required

## Pipeline Execution Flow

### Staging Deployment
```bash
git push origin main
└─> Jenkins detects push
    └─> Runs staging pipeline
        └─> Validates → Builds → Scans → Pushes → Deploys
            └─> Image: nexus/fastapi-postgres-app:latest-42
```

### Production Deployment
```bash
Trigger production pipeline manually
└─> Queries Nexus for latest staging image
    └─> Deploys to canary (1 replica)
        └─> Manual validation
            └─> Promotes to main deployment
                └─> Scales down canary
```

## Deployment Commands

### Check Deployment Status
```bash
# Staging
kubectl get pods -n staging
kubectl rollout status deployment/fastapi-app -n staging

# Production
kubectl get pods -n prod
kubectl rollout status deployment/fastapi-app -n prod
kubectl rollout status deployment/fastapi-app-canary -n prod
```

### Manual Rollback
```bash
# Rollback to previous version
kubectl rollout undo deployment/fastapi-app -n prod

# Rollback to specific revision
kubectl rollout undo deployment/fastapi-app -n prod --to-revision=2
```

## Security Considerations

- **Image Scanning:** Trivy blocks deployments with HIGH/CRITICAL vulnerabilities
- **Registry Authentication:** Nexus credentials stored in Jenkins credentials store
- **Kubernetes Secrets:** Image pull secrets created automatically per namespace
- **Database Credentials:** Stored as Jenkins credentials, injected at runtime
- **Network Policies:** Namespace isolation (recommended to implement)
- **RBAC:** Service account permissions scoped per namespace

## Monitoring & Observability

- **Metrics:** Prometheus is installed and scraping metrics from FastAPI pods and PostgreSQL. Grafana dashboards are set up for API performance, DB metrics, and pod health.


## Prerequisites

- Kubernetes cluster (on-prem) with kubectl access
- Jenkins with Kubernetes plugin configured
- Nexus repository manager running at `10.10.70.84:30051`
- Docker registry credentials configured in Jenkins
- PostgreSQL credentials configured in Jenkins
- Git repository with webhook configured

## Getting Started

### 1. Clone the Repository
```bash
git clone 
cd fastapi_postgres_app
```

### 2. Configure Jenkins
- Add Nexus credentials (ID: `a4116a00-2da0-4947-9dcc-86ba51217d6d`)
- Add database credentials (ID: `STAGING_DB_CRED`)
- Configure Kubernetes cloud in Jenkins
- Create multibranch pipeline pointing to repository or single one for each ENV
- Add Gitee as SCM.

### 3. Deploy Infrastructure
```bash
# Deploy PostgreSQL StatefulSet
kubectl apply -f k8s/postgres-statefulset.yaml -n staging
kubectl apply -f k8s/postgres-statefulset.yaml -n prod

# Deploy application
kubectl apply -f k8s/app-deployment.yaml -n staging
kubectl apply -f k8s/app-service.yaml -n staging
```

### 4. Trigger Pipeline
```bash
git commit -m "Initial deployment"
git push origin main
```

## Benefits Summary

| Benefit | Impact |
|---------|--------|
| **Immutable Artifacts** | Same image tested in staging deployed to prod |
| **Faster Deployments** | Production pipeline ~60% faster (no build) |
| **Reduced Risk** | Canary deployments catch issues before full rollout |
| **Audit Trail** | Complete visibility from commit to production |
| **Automated Safety** | Vulnerability scanning blocks insecure images |
| **Database Safety** | Manual approvals prevent accidental schema changes |

## Troubleshooting

### Pipeline Fails at Image Scan
```bash
# Check Trivy scan results in Jenkins console
# Fix vulnerabilities in dependencies
# Update requirements.txt or base image
```

### Database Migration Fails
```bash
# Connect to PostgreSQL pod
kubectl exec -it postgres-0 -n staging -- psql -U  -d mydb

# Check migration status
\dt
SELECT * FROM schema_migrations;
```

### Canary Deployment Issues
```bash
# Check canary logs
kubectl logs -n prod -l app=fastapi-app-canary

# Force scale down canary
kubectl scale deployment/fastapi-app-canary --replicas=0 -n prod
```


---

**Built with ❤️ for production-grade DevOps practices**
