#!/bin/bash
###############################################################################
# PROJECT CLEANUP SCRIPT
# Removes generated files, caches, and resets to clean state
###############################################################################

echo "🧹 Cleaning up project..."
echo ""

# Stop all running services
echo "Stopping services..."
pkill -f "python src/serving/app.py" 2>/dev/null || true
pkill -f "python.*http.server.*8000" 2>/dev/null || true
docker-compose down 2>/dev/null || true

# Clean Python cache
echo "Cleaning Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
find . -type f -name "*.pyo" -delete 2>/dev/null || true

# Clean logs
echo "Cleaning logs..."
rm -f logs/*.log 2>/dev/null || true

# Clean batch output
echo "Cleaning batch output..."
rm -rf batch_output/*.parquet 2>/dev/null || true

# Clean Docker volumes (optional - uncomment if needed)
# echo "Cleaning Docker volumes..."
# docker-compose down -v

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "To restart the project:"
echo "  ./setup.sh"
