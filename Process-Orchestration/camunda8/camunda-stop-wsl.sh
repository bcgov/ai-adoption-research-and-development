#!/bin/bash
# camunda-stop-wsl.sh - Stop Camunda 8 in WSL

set -e

echo "Stopping Camunda 8 services..."

if [ ! -f "docker-compose.yml" ]; then
    echo "❌ docker-compose.yml not found in current directory"
    exit 1
fi

docker-compose down

echo ""
echo "✅ Camunda 8 services stopped"
echo ""
echo "To remove volumes (delete all data):"
echo "  docker-compose down -v"
echo ""


