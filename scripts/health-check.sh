#!/bin/bash
# ITPE Topic Enhancement - Health Check Script
# Usage: ./scripts/health-check.sh

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Status tracking
FAILED_CHECKS=0
PASSED_CHECKS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_CHECKS++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED_CHECKS++))
}

# Check if container is running
check_container_running() {
    local container_name=$1
    if docker-compose -f "$COMPOSE_FILE" ps -q "$container_name" | grep -q .; then
        return 0
    else
        return 1
    fi
}

# Check if container is healthy
check_container_healthy() {
    local container_name=$1
    local health_status=$(docker-compose -f "$COMPOSE_FILE" ps "$container_name" | grep -oP "healthy|unhealthy|starting" || echo "")

    if [ "$health_status" == "healthy" ]; then
        return 0
    else
        return 1
    fi
}

# Check PostgreSQL connection
check_postgres() {
    log_info "Checking PostgreSQL connection..."

    if ! check_container_running "postgres"; then
        log_error "PostgreSQL container is not running"
        return 1
    fi

    if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U itpe -d itpe &>/dev/null; then
        local pg_version=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U itpe -d itpe -tAc "SELECT version();" | head -n 1)
        log_success "PostgreSQL is accepting connections"
        log_info "  Version: ${pg_version:0:50}..."

        # Check database size
        local db_size=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U itpe -d itpe -tAc "SELECT pg_size_pretty(pg_database_size('itpe'));")
        log_info "  Database Size: $db_size"

        # Check connection count
        local conn_count=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U itpe -d itpe -tAc "SELECT count(*) FROM pg_stat_activity;")
        log_info "  Active Connections: $conn_count"

        return 0
    else
        log_error "PostgreSQL is not accepting connections"
        return 1
    fi
}

# Check Redis connection
check_redis() {
    log_info "Checking Redis connection..."

    if ! check_container_running "redis"; then
        log_error "Redis container is not running"
        return 1
    fi

    if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping &>/dev/null; then
        log_success "Redis is responding to PING"

        # Get Redis info
        local redis_version=$(docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli INFO server | grep "redis_version" | cut -d: -f2 | tr -d '\r')
        log_info "  Version: $redis_version"

        # Check memory usage
        local used_memory=$(docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli INFO memory | grep "used_memory_human" | cut -d: -f2 | tr -d '\r')
        log_info "  Memory Usage: $used_memory"

        # Check key count
        local key_count=$(docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli DBSIZE | tr -d '\r')
        log_info "  Total Keys: $key_count"

        return 0
    else
        log_error "Redis is not responding"
        return 1
    fi
}

# Check Backend API
check_backend() {
    log_info "Checking Backend API..."

    if ! check_container_running "backend"; then
        log_error "Backend container is not running"
        return 1
    fi

    local health_response=$(curl -s http://localhost:8000/health 2>/dev/null || echo "")

    if [ -n "$health_response" ]; then
        log_success "Backend API is responding"

        # Parse JSON response
        local api_status=$(echo "$health_response" | grep -oP '"status":\s*"\K[^"]+' || echo "unknown")
        local api_version=$(echo "$health_response" | grep -oP '"version":\s*"\K[^"]+' || echo "unknown")

        log_info "  Status: $api_status"
        log_info "  Version: $api_version"

        # Check API documentation
        if curl -sf http://localhost:8000/docs &>/dev/null; then
            log_info "  API Documentation: Available at /docs"
        fi

        return 0
    else
        log_error "Backend API is not responding"
        return 1
    fi
}

# Check Frontend
check_frontend() {
    log_info "Checking Frontend..."

    if ! check_container_running "frontend"; then
        log_warning "Frontend container is not running (optional)"
        return 0
    fi

    if curl -sf http://localhost:3000 &>/dev/null; then
        log_success "Frontend is responding"
        return 0
    else
        log_error "Frontend is not responding"
        return 1
    fi
}

# Check Celery Worker
check_celery() {
    log_info "Checking Celery Worker..."

    if ! check_container_running "celery-worker"; then
        log_warning "Celery Worker container is not running (optional)"
        return 0
    fi

    # Check if celery worker is registered
    local celery_stats=$(docker-compose -f "$COMPOSE_FILE" exec -T celery-worker celery -A app.services.llm.worker inspect active 2>/dev/null || echo "")

    if [ -n "$celery_stats" ]; then
        log_success "Celery Worker is running"
        return 0
    else
        log_error "Celery Worker is not responding"
        return 1
    fi
}

# Check Ollama (optional)
check_ollama() {
    log_info "Checking Ollama Service..."

    if ! check_container_running "ollama"; then
        log_warning "Ollama container is not running (optional)"
        return 0
    fi

    if curl -sf http://localhost:11434/api/tags &>/dev/null; then
        log_success "Ollama API is responding"

        # Check available models
        local models=$(curl -s http://localhost:11434/api/tags | grep -oP '"name":\s*"\K[^"]+' | head -n 3 || echo "")
        if [ -n "$models" ]; then
            log_info "  Available Models:"
            echo "$models" | sed 's/^/    - /'
        fi

        return 0
    else
        log_error "Ollama API is not responding"
        return 1
    fi
}

# Display container resource usage
show_resource_usage() {
    log_info "Container Resource Usage:"
    docker-compose -f "$COMPOSE_FILE" exec -T docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || \
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep -E "itpe-|CONTAINER"
}

# Display recent errors
show_recent_errors() {
    log_info "Recent errors from backend logs:"
    docker-compose -f "$COMPOSE_FILE" logs --tail=50 backend 2>/dev/null | grep -i "error\|exception\|failed" | tail -n 5 || log_info "No recent errors found"
}

# Main health check workflow
main() {
    echo "=========================================="
    echo "ITPE Topic Enhancement Health Check"
    echo "=========================================="
    echo ""

    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Change to project directory
    cd "$PROJECT_ROOT"

    # Run health checks
    check_postgres
    check_redis
    check_backend
    check_frontend
    check_celery
    check_ollama

    echo ""
    echo "=========================================="
    echo "Health Check Summary"
    echo "=========================================="
    echo "Passed Checks: $PASSED_CHECKS"
    echo "Failed Checks: $FAILED_CHECKS"
    echo ""

    if [ $FAILED_CHECKS -eq 0 ]; then
        log_success "All services are healthy!"
        echo ""
        echo "Service URLs:"
        echo "  Backend API:     http://localhost:8000"
        echo "  Frontend:        http://localhost:3000"
        echo "  API Docs:        http://localhost:8000/docs"
        echo "  PostgreSQL:      localhost:5432"
        echo "  Redis:           localhost:6379"
        echo "  Ollama:          http://localhost:11434"
        exit 0
    else
        log_error "Some services are unhealthy!"
        echo ""
        show_resource_usage
        echo ""
        show_recent_errors
        exit 1
    fi
}

# Handle script arguments
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "ITPE Topic Enhancement Health Check Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --verbose      Show detailed output"
    echo ""
    echo "This script checks the health status of all services:"
    echo "  - PostgreSQL database connection"
    echo "  - Redis cache connection"
    echo "  - Backend API health endpoint"
    echo "  - Frontend web server"
    echo "  - Celery background worker (optional)"
    echo "  - Ollama LLM service (optional)"
    exit 0
fi

# Run main function
main "$@"
