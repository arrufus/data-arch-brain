#!/bin/bash

# Stop script for Data Pipeline Test Environment

set -e

echo "======================================"
echo "Stopping Test Environment"
echo "======================================"
echo ""

# Check if containers are running
if ! docker-compose ps | grep -q "Up"; then
    echo "No containers are running."
    exit 0
fi

# Ask if user wants to delete volumes
echo "Do you want to delete all data volumes? (y/N)"
read -r response

if [[ "$response" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Stopping services and removing volumes..."
    docker-compose down -v
    echo ""
    echo "✓ Services stopped and all data deleted"
else
    echo ""
    echo "Stopping services (data will be preserved)..."
    docker-compose down
    echo ""
    echo "✓ Services stopped (data preserved)"
    echo "  Use 'docker-compose up -d' to restart with existing data"
fi

echo ""
echo "======================================"
echo "Environment Stopped"
echo "======================================"
echo ""
