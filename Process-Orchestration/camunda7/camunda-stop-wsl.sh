#!/bin/bash
# camunda-stop-wsl.sh - Stop Camunda 7 in WSL

set -e

echo "Stopping Camunda 7 services..."

if [ ! -f "docker-compose.yaml" ] && [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yaml not found in current directory"
    exit 1
fi

docker-compose down

echo ""
echo "✅ Camunda 7 services stopped"
echo ""
echo "To remove volumes (delete all data):"
echo "  docker-compose down -v"
echo ""


