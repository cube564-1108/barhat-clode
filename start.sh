#!/bin/bash
# Quality Dashboard — Startup Script for Amvera

echo "=== Quality Dashboard Startup ==="
echo "Working directory: $(pwd)"
echo "Files in directory:"
ls -la

echo ""
echo "=== Checking for app.py ==="
if [ -f "app.py" ]; then
    echo "✓ app.py found"
    echo "Running: python3 app.py"
    python3 app.py
else
    echo "✗ app.py NOT found"
    echo "Searching for Python files:"
    find . -name "*.py" -type f 2>/dev/null
fi
