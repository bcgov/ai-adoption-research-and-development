#!/bin/bash
# camunda-start-wsl.sh - Start Camunda 7 in WSL using Docker Compose

set -e

echo "=========================================="
echo "Camunda 7 Startup Script for WSL"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running."
    echo "   Please start Docker Desktop or Docker daemon."
    exit 1
fi

echo "✅ Docker is running"
echo ""

# Check if docker-compose.yml exists
if [ ! -f "docker-compose.yaml" ] && [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yaml not found in current directory"
    exit 1
fi

echo "Starting Camunda 7 services..."
echo ""

# Start services
docker-compose up -d

echo ""
echo "Waiting for services to start (this may take a minute)..."
echo ""

# Wait for services to be healthy
max_attempts=60
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose ps | grep -q "healthy"; then
        echo ""
        echo "✅ Services are starting up..."
        break
    fi
    attempt=$((attempt + 1))
    echo -n "."
    sleep 2
done

echo ""
echo ""

# Show status
echo "Service Status:"
echo "================"
docker-compose ps

echo ""
echo "=========================================="
echo "✅ Camunda 7 is running!"
echo "=========================================="
echo ""
echo "Access the following services:"
echo ""
echo "  Camunda Webapps & REST:  http://localhost:8080"
echo ""
echo "Default credentials:"
echo "  Username: demo"
echo "  Password: demo"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose down"
echo ""
echo "To stop and remove volumes:"
echo "  docker-compose down -v"
echo ""


