#!/bin/bash
echo "Active python environment"
source .venv/bin/activate

echo "Stopping existing aibox process..."
if lsof -i:8080 >/dev/null 2>&1; then
    echo "Found gunicorn processes on port 8080, stopping them..."
    pkill -9 gunicorn
    echo "Processes terminated"
else
    echo "No processes found on port 8080"
fi

echo "Start aibox app..."
gunicorn -c gunicorn.conf.py app:app --daemon

echo -n "Checking process status"
for i in {1..3}; do
    sleep 1
    echo -n "."
done
echo ""
lsof -i:8080
