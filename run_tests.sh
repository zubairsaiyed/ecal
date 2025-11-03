#!/bin/bash
# Run rotation tests to ensure no regressions

set -e

echo "=========================================="
echo "Running ECAL Rotation Tests"
echo "=========================================="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Run the rotation tests
echo "Running rotation tests..."
python3 test_rotation.py

echo ""
echo "=========================================="
echo "All tests passed! ✅"
echo "=========================================="

