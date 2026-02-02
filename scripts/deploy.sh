#!/bin/bash
# ITPE Topic Enhancement - Deployment Script
# Usage: ./scripts/deploy.sh [env]
#   env: development (default) | staging | production

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV=${1:-development}
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.yml"
ENV_FILE="${PROJECT_ROOT}/.env.${ENV}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        log_warning "Environment file not found: $ENV_FILE"
        log_info "Creating from .env.production.example..."

        if [ -f "${PROJECT_ROOT}/.env.production.example" ]; then
            cp "${PROJECT_ROOT}/.env.production.example" "$ENV_FILE"
            log_warning "Please update $ENV_FILE with your configuration before deploying"
            read -p "Press Enter to continue or Ctrl+C to exit..."
        else
            log_error ".env.production.example not found!"
            exit 1
        fi
    fi
}

# Stop existing containers
stop_containers() {
    log_info "Stopping existing containers..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
}

# Build and start containers
start_containers() {
    log_info "Building and starting containers for $ENV environment..."

    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build

    log_success "Containers started successfully"
}

# Wait for services to be healthy
wait_for_services() {
    log_info "Waiting for services to be healthy..."

    # Wait for PostgreSQL
    log_info "Waiting for PostgreSQL..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres pg_isready -U itpe -d itpe &>/dev/null; then
            log_success "PostgreSQL is ready"
            break
        fi
        sleep 2
        ((timeout-=2))
    done

    if [ $timeout -le 0 ]; then
        log_error "PostgreSQL health check timed out"
        return 1
    fi

    # Wait for Redis
    log_info "Waiting for Redis..."
    timeout=30
    while [ $timeout -gt 0 ]; do
        if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T redis redis-cli ping &>/dev/null; then
            log_success "Redis is ready"
            break
        fi
        sleep 2
        ((timeout-=2))
    done

    if [ $timeout -le 0 ]; then
        log_error "Redis health check timed out"
        return 1
    fi

    # Wait for Backend
    log_info "Waiting for Backend API..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -sf http://localhost:8000/health &>/dev/null; then
            log_success "Backend API is ready"
            break
        fi
        sleep 2
        ((timeout-=2))
    done

    if [ $timeout -le 0 ]; then
        log_error "Backend API health check timed out"
        return 1
    fi
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."

    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend alembic upgrade head

    log_success "Migrations completed successfully"
}

# Show container status
show_status() {
    log_info "Container status:"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
}

# Show logs
show_logs() {
    log_info "Recent logs:"
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs --tail=50
}

# Main deployment workflow
main() {
    log_info "=========================================="
    log_info "ITPE Topic Enhancement Deployment"
    log_info "Environment: $ENV"
    log_info "=========================================="

    # Check prerequisites
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Change to project directory
    cd "$PROJECT_ROOT"

    # Execute deployment steps
    check_env_file
    stop_containers
    start_containers
    wait_for_services

    # Only run migrations on first deployment or when explicitly requested
    if [ "$2" == "--migrate" ] || [ "$2" == "-m" ]; then
        run_migrations
    fi

    show_status

    log_success "=========================================="
    log_success "Deployment completed successfully!"
    log_success "=========================================="
    log_info "API available at: http://localhost:8000"
    log_info "Frontend available at: http://localhost:3000"
    log_info "API Documentation: http://localhost:8000/docs"
    log_info ""
    log_info "Use 'docker-compose logs -f' to view logs"
    log_info "Use './scripts/health-check.sh' to check service health"
}

# Handle script arguments
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "ITPE Topic Enhancement Deployment Script"
    echo ""
    echo "Usage: $0 [environment] [options]"
    echo ""
    echo "Environments:"
    echo "  development   Development environment (default)"
    echo "  staging       Staging environment"
    echo "  production    Production environment"
    echo ""
    echo "Options:"
    echo "  -m, --migrate  Run database migrations after deployment"
    echo "  -h, --help     Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 development          # Deploy development environment"
    echo "  $0 staging --migrate    # Deploy staging with migrations"
    echo "  $0 production -m        # Deploy production with migrations"
    exit 0
fi

# Run main function
main "$@"
