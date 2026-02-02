#!/bin/bash
# ITPE Topic Enhancement - Migration Test Script
# Tests database migrations from SQLite to PostgreSQL

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="${PROJECT_ROOT}/backend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "=========================================="
echo "ITPE Topic Enhancement Migration Test"
echo "=========================================="

# Check if PostgreSQL is running
log_info "Checking PostgreSQL connection..."
if docker-compose -f "${PROJECT_ROOT}/docker-compose.yml" exec -T postgres pg_isready -U itpe -d itpe &>/dev/null; then
    log_success "PostgreSQL is ready"
else
    log_error "PostgreSQL is not ready. Start Docker Compose first:"
    echo "  docker-compose up -d postgres"
    exit 1
fi

# Run Alembic migrations
log_info "Running Alembic migrations..."
cd "$BACKEND_DIR"

# Show current migration status
log_info "Current migration status:"
alembic current 2>/dev/null || log_warning "Could not get current status"

# Show migration history
log_info "Migration history:"
alembic history 2>/dev/null || log_warning "Could not get history"

# Upgrade to latest
log_info "Upgrading database to latest version..."
alembic upgrade head

# Verify migration
log_info "Verifying migration..."
alembic current

# Check database tables
log_info "Checking database tables..."
docker-compose -f "${PROJECT_ROOT}/docker-compose.yml" exec -T postgres psql -U itpe -d itpe -c "\dt" 2>/dev/null || \
log_warning "Could not list tables"

# Check row counts
log_info "Table row counts:"
for table in topics validations proposals references validation_tasks; do
    count=$(docker-compose -f "${PROJECT_ROOT}/docker-compose.yml" exec -T postgres psql -U itpe -d itpe -tAc "SELECT COUNT(*) FROM $table;" 2>/dev/null || echo "0")
    echo "  $table: $count rows"
done

log_success "=========================================="
log_success "Migration test completed successfully!"
log_success "=========================================="
