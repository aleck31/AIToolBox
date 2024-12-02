#!/bin/bash
echo "Checking if port 8080 is in use..."
if lsof -i:8080 >/dev/null 2>&1; then
    echo "Found gunicorn processes on port 8080, stopping them..."
    pkill -9 gunicorn
    echo "Processes terminated"
else
    echo "No processes found on port 8080"
fi
