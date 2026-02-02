# ITPE Topic Enhancement - Deployment Guide

This guide covers deployment of the ITPE Topic Enhancement system using Docker Compose with PostgreSQL and Redis.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- At least 4GB RAM available for Docker

## Quick Start

### 1. Start All Services

```bash
# Development deployment
./scripts/deploy.sh development

# Staging deployment with migrations
./scripts/deploy.sh staging --migrate

# Production deployment
./scripts/deploy.sh production --migrate
```

### 2. Check Service Health

```bash
./scripts/health-check.sh
```

### 3. Access Services

- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- API Documentation: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Ollama: http://localhost:11434

## Service Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Frontend   │─────▶│   Backend   │─────▶│ PostgreSQL  │
│  (Nginx)    │      │  (FastAPI)  │      │  (Primary)  │
└─────────────┘      └─────────────┘      └─────────────┘
                            │                     │
                            ▼                     ▼
                     ┌─────────────┐      ┌─────────────┐
                     │    Redis    │      │  Celery     │
                     │   (Cache)   │      │   Worker    │
                     └─────────────┘      └─────────────┘
                            │
                            ▼
                     ┌─────────────┐
                     │   Ollama    │
                     │  (LLM API)  │
                     └─────────────┘
```

## Environment Configuration

### Environment Files

- `.env.development` - Local development with Docker Compose
- `.env.production.example` - Production template (copy to `.env.production`)
- `backend/.env` - Backend-specific configuration (optional)

### Key Configuration Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
POSTGRES_DB=itpe
POSTGRES_USER=itpe
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_URL=redis://:password@host:6379/0
REDIS_PASSWORD=your_secure_password

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# LLM
LLM_PROVIDER=openai  # or ollama
OPENAI_API_KEY=your_openai_key
OLLAMA_BASE_URL=http://ollama:11434
```

## Database Migration

### Running Migrations

```bash
# After starting services
./scripts/test-migration.sh

# Or manually with Docker Compose
docker-compose exec backend alembic upgrade head

# Check migration status
docker-compose exec backend alembic current

# View migration history
docker-compose exec backend alembic history
```

### Migration from SQLite to PostgreSQL

The existing SQLite migration file is compatible with PostgreSQL. The same Alembic scripts work for both databases.

1. Update `DATABASE_URL` to use PostgreSQL dialect
2. Run `alembic upgrade head`
3. Verify with `alembic current`

## Docker Compose Services

### PostgreSQL

- **Image**: postgres:16-alpine
- **Port**: 5432
- **Data Volume**: postgres_data
- **Health Check**: pg_isready command

### Redis

- **Image**: redis:7-alpine
- **Port**: 6379
- **Data Volume**: redis_data
- **Persistence**: AOF enabled
- **Health Check**: redis-cli ping

### Backend

- **Build**: Multi-stage Dockerfile
- **Port**: 8000
- **Health Check**: HTTP /health endpoint
- **Depends On**: postgres, redis

### Frontend

- **Build**: Multi-stage Dockerfile (Nginx)
- **Port**: 3000
- **Health Check**: HTTP / endpoint

### Celery Worker

- **Command**: celery -A app.services.llm.worker worker
- **Concurrency**: 2
- **Depends On**: postgres, redis

### Ollama

- **Image**: ollama/ollama:latest
- **Port**: 11434
- **Models**: llama3.1:8b (configurable)

## Monitoring and Logs

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f redis

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Service Status

```bash
# Container status
docker-compose ps

# Resource usage
docker stats

# Service health
./scripts/health-check.sh
```

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is ready
docker-compose exec postgres pg_isready -U itpe -d itpe

# View PostgreSQL logs
docker-compose logs postgres

# Connect to PostgreSQL
docker-compose exec postgres psql -U itpe -d itpe
```

### Redis Connection Issues

```bash
# Check Redis is responding
docker-compose exec redis redis-cli ping

# View Redis logs
docker-compose logs redis

# Connect to Redis CLI
docker-compose exec redis redis-cli
```

### Backend API Issues

```bash
# Check backend health
curl http://localhost:8000/health

# View backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend
```

### Migration Issues

```bash
# Reset database (WARNING: destroys all data)
docker-compose exec postgres psql -U itpe -d itpe -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker-compose exec backend alembic upgrade head
```

## Data Persistence

### Volumes

- `postgres_data` - PostgreSQL data directory
- `redis_data` - Redis AOF file
- `obsidian_vault` - Obsidian vault mount
- `fb21_books` - FB21 books mount
- `ollama_data` - Ollama models

### Backup and Restore

```bash
# Backup PostgreSQL
docker-compose exec postgres pg_dump -U itpe itpe > backup.sql

# Restore PostgreSQL
cat backup.sql | docker-compose exec -T postgres psql -U itpe -d itpe

# Backup Redis
docker-compose exec redis redis-cli SAVE
docker cp itpe-redis:/data/dump.rdb ./redis_backup.rdb
```

## Production Deployment

### Security Checklist

1. Change all default passwords
2. Use strong random passwords (32+ characters)
3. Enable SSL/TLS for database connections
4. Restrict CORS origins to production domain only
5. Use environment-specific secrets manager
6. Enable container resource limits
7. Configure proper logging and monitoring

### Password Generation

```bash
# Generate secure passwords
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Resource Limits

Edit `docker-compose.yml` to add resource limits:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

## Development Workflow

### Local Development with SQLite

```bash
cd backend
# Use existing SQLite setup
uvicorn app.main:app --reload
```

### Local Development with Docker PostgreSQL

```bash
# Start PostgreSQL and Redis only
docker-compose up -d postgres redis

# Run backend locally with connected database
export DATABASE_URL=postgresql+asyncpg://itpe:dev_password@localhost:5432/itpe
cd backend
uvicorn app.main:app --reload
```

### Running Tests

```bash
# Run tests with SQLite (default)
cd backend
pytest

# Run tests with PostgreSQL
docker-compose up -d postgres
export DATABASE_URL=postgresql+asyncpg://itpe:dev_password@localhost:5432/itpe
pytest
```

## Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
